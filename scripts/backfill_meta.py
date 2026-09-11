"""存量元数据回填 CLI（2026-08-29 标准化流程收口）。

入库时修复（封面日期/standard_type 推断/CCS 查询）此前只对新导入生效——
存量文档永不回填（GB/T 34406 用户实测：发布/生效日期恒空白）。本脚本把
pipeline 的元数据规则对全库存量幂等重放：只填空值、只纠错误默认，不覆盖
任何已有非空数据；每次写库写 event_log 审计。

规则（与 pipeline 同源）：
  1. 封面日期：published_at / effective_from 为空 → PDF 前 2 页 NFKC 提取
     （pipeline._COVER_PUB / _COVER_EFF，含全角数字 + PUA 连字符容错）。
  2. legal_hierarchy：standard_no 含 /T→GB/T、/Z→GB/Z（此前全库默认 'GB'）；
     仅修正标准号可判定而存储值为 'GB' 的行。
  3. standard_type：legal_hierarchy GB/Z→guiding、含 /T→recommended、
     其余→mandatory；仅纠正被默认值坑掉的 mandatory（pipeline._std_type）。
  4. ccs_code / ccs_name：为空 → fetch_ccs（cssn 官方渠道；网络失败静默
     降级本地表，与入库口径一致）。--skip-ccs 可离线跑。

用法：
  python scripts/backfill_meta.py            # dry-run：只报告将回填什么
  python scripts/backfill_meta.py --apply    # 实际回填 + 审计
  python scripts/backfill_meta.py --apply --skip-ccs
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unicodedata
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.ingestion.pipeline import _COVER_EFF, _COVER_PUB, _hier_from_no, _std_type  # noqa: E402

DB = str(Path.home() / "AppData/Roaming/KnowledgeStation/database/knowledge.db")


def _cover_dates(pdf_path: str) -> tuple[str | None, str | None]:
    """封面日期提取（前 2 页，NFKC 归一；与 pipeline._cover_date 同规则）。"""
    pub = eff = None
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None, None
    try:
        for pno in range(min(2, len(doc))):
            text = unicodedata.normalize("NFKC", doc[pno].get_text("text") or "")
            if pub is None and (m := _COVER_PUB.search(text)):
                pub = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            if eff is None and (m := _COVER_EFF.search(text)):
                eff = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            if pub and eff:
                break
    finally:
        doc.close()
    return pub, eff


def main(apply: bool = False, skip_ccs: bool = False,
         doc_filter: str | None = None, ccs_delay: float = 0.5) -> int:
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    sql = ("SELECT doc_id, standard_no, standard_name, legal_hierarchy, standard_type,"
           " published_at, effective_from, ccs_code, file_path FROM doc_meta"
           " WHERE file_path IS NOT NULL")
    params: tuple = ()
    if doc_filter:
        sql += " AND standard_no LIKE ?"
        params = (f"%{doc_filter}%",)
    docs = db.execute(sql, params).fetchall()
    print(f"文档总数: {len(docs)}（apply={apply}, skip_ccs={skip_ccs}）", flush=True)

    n_pub = n_eff = n_type = n_hier = 0
    ccs_todo: list[sqlite3.Row] = []
    for d in docs:
        updates: dict[str, object] = {}
        # 1) 封面日期（只填空）
        if d["standard_no"].upper().startswith(("GB", "DB", "T/")) and (
                not d["published_at"] or not d["effective_from"]):
            pub, eff = _cover_dates(d["file_path"])
            if pub and not d["published_at"]:
                updates["published_at"] = pub
            if eff and not d["effective_from"]:
                updates["effective_from"] = eff
        # 2) legal_hierarchy（standard_no 可判定而存储值为粗粒度 'GB'）
        want_hier = _hier_from_no(d["standard_no"], d["legal_hierarchy"] or "GB")
        if d["legal_hierarchy"] == "GB" and want_hier != "GB":
            updates["legal_hierarchy"] = want_hier
        # 3) standard_type（按修正后层级推断；只纠错误默认 mandatory）
        want = _std_type(updates.get("legal_hierarchy") or d["legal_hierarchy"])
        if d["standard_type"] == "mandatory" and want != "mandatory":
            updates["standard_type"] = want
        if updates:
            n_pub += 1 if "published_at" in updates else 0
            n_eff += 1 if "effective_from" in updates else 0
            n_hier += 1 if "legal_hierarchy" in updates else 0
            n_type += 1 if "standard_type" in updates else 0
            sets = ", ".join(f"{k}=?" for k in updates)
            print(f"[{'回填' if apply else '待回填'}] {d['standard_no']}: {updates}", flush=True)
            if apply:
                db.execute(f"UPDATE doc_meta SET {sets}, updated_at=datetime('now',"
                           "'localtime') WHERE doc_id=?", (*updates.values(), d["doc_id"]))
                db.execute(
                    "INSERT INTO event_log (event_type, actor, target_type, target_id,"
                    " metadata) VALUES ('backfill_meta','script','doc',?,?)",
                    (d["doc_id"], json.dumps(updates, ensure_ascii=False)))
        # 3) CCS（只填空；网络操作最后批量）
        if not d["ccs_code"]:
            ccs_todo.append(d)

    if not skip_ccs and ccs_todo:
        print(f"\nCCS 待回填: {len(ccs_todo)} 条（cssn 渠道，失败降级本地表）", flush=True)
        from src.core.knowledge.ccs_fetcher import fetch_ccs
        for idx, d in enumerate(ccs_todo):
            if ccs_delay and idx % 10 == 0:
                print(f"  … CCS 进度 {idx}/{len(ccs_todo)}", flush=True)
            try:
                ccs = fetch_ccs(d["standard_no"], d["standard_name"])
            except Exception as e:
                print(f"  [fail] {d['standard_no']}: {e}", flush=True)
                ccs = None
            if ccs_delay:
                import time as _t
                _t.sleep(ccs_delay)
            name = getattr(ccs, "name", None) or (ccs.get("name") if isinstance(ccs, dict) else None)
            code = getattr(ccs, "code", None) or (ccs.get("code") if isinstance(ccs, dict) else None)
            print(f"  [{'回填' if apply else '待回填'}] {d['standard_no']}: CCS={code} {name}")
            if apply and code:
                db.execute("UPDATE doc_meta SET ccs_code=?, ccs_name=?, updated_at="
                           "datetime('now','localtime') WHERE doc_id=?",
                           (code, name, d["doc_id"]))
                db.execute(
                    "INSERT INTO event_log (event_type, actor, target_type, target_id,"
                    " metadata) VALUES ('backfill_meta','script','doc',?,?)",
                    (d["doc_id"], json.dumps({"ccs_code": code}, ensure_ascii=False)))
    elif ccs_todo:
        print(f"\nCCS 待回填: {len(ccs_todo)} 条（--skip-ccs 跳过）")

    db.commit()
    db.close()
    print(f"\n完成：发布日期 {n_pub}，实施日期 {n_eff}，legal_hierarchy {n_hier}，"
          f"standard_type {n_type}，CCS {len(ccs_todo)}（未跑/失败见上），apply={apply}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="实际写库（缺省 dry-run）")
    ap.add_argument("--skip-ccs", action="store_true", help="跳过 CCS 网络查询")
    ap.add_argument("--doc", default=None, help="只处理 standard_no 含此子串的文档")
    ap.add_argument("--ccs-delay", type=float, default=0.5,
                    help="CCS 网络查询间隔秒（默认 0.5，防 cssn 限速封禁）")
    a = ap.parse_args()
    sys.exit(main(apply=a.apply, skip_ccs=a.skip_ccs, doc_filter=a.doc,
                  ccs_delay=a.ccs_delay))
