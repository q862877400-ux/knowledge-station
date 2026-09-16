"""存量语料修复器（决断 2+3，2026-09-15 立）。

背景：本轮 6 处根因修复只对**新入库**生效；修复前入库的文档仍带旧缺陷。
- 决断 2：17 部含重复条款号 → 重导（条款头闸门治本）
- 决断 3：Gate A 纯扫描件 → 重导（吃 glue/frac/图例三处 OCR 通道修复的收益）

设计：可续跑（repair_state.json 逐条落盘）、去重（两集合按 doc_id 并集）、
逐条重试 2 次、失败不中断、逐条记账到 repair_log.jsonl。
用 doc_meta 里已有的 standard_no/standard_name（权威），不从文件名猜。

用法：python var/ocr-loop/repair_corpus.py [--limit N] [--only dup|scan]
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
VARDIR = Path(__file__).resolve().parent
ROOT = VARDIR.parents[1]
sys.path.insert(0, str(ROOT))
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
STATE = VARDIR / "repair_state.json"
LOG = VARDIR / "repair_log.jsonl"


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(s: dict) -> None:
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(STATE)


# ---------------------------------------------------------------- 先验护栏
# 2026-09-15（收敛循环首轮实测）：全库重导会把**权威语料整体重写**。样本 6 部
# 里就有 1 部（GB/T 12706.4-2020）因条款头闸门缺陷从 53 条塌成 3 条、正文
# 6489→4886 字。若没有先验护栏，260 部批量重导就是一次**静默的语料损坏**。
# 护栏：复用产物只跑「解析+切分」（不落库）预测条款数，灾难性下降则**拒绝重导
# 该文档**并记账——宁可少导一部，不可悄悄毁一部。
PREFLIGHT_MIN_DOC = 5      # 少于 5 条的文档不适用比例护栏（小样本无统计意义）
PREFLIGHT_RATIO = 0.6      # 预测 < 现状 60% 即判灾难性下降


def current_clause_count(doc_id: str) -> int:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        r = conn.execute("SELECT COUNT(*) FROM clause_revision WHERE doc_id=?",
                         (doc_id,)).fetchone()
        return int(r[0]) if r else 0
    finally:
        conn.close()


def predict_clauses(parse_dir: Path, pdf: Path) -> int | None:
    """先验预测：复用产物 → 解析 + 切分（**零 OCR、零落库**）→ 条款数。

    只调用规范所有者里的函数（`_cached_parse_result` / `load_middle_items*` /
    `split_items_into_clauses`），不另写判据。
    """
    from src.core.ingestion.middle_locator import find_middle_files
    from src.core.ingestion.pipeline import (_cached_parse_result,
                                             load_middle_items,
                                             load_middle_items_from_blocks,
                                             split_items_into_clauses)
    res = _cached_parse_result(parse_dir, pdf)
    if res is None:
        return None
    try:
        if res.get("blocks"):
            items, _ = load_middle_items_from_blocks(
                [b for b in res["blocks"] if b.get("text")])
        else:
            files = find_middle_files(Path(res["deep_output"]))
            if not files:
                return None
            items, _ = load_middle_items(files[0])
        return len(split_items_into_clauses(items))
    except Exception:  # noqa: BLE001 —— 预测失败不阻塞（按"无预测"处理）
        return None


def parse_dir_of(doc_id: str) -> Path:
    from src.core.config import get_settings
    return Path(get_settings().data_dir) / "parse_out" / doc_id


def dup_targets() -> list[tuple[str, str, str, str]]:
    """含重复条款号的文档 → [(doc_id, standard_no, standard_name, reason)]。"""
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT c.doc_id, d.standard_no, d.standard_name FROM clause_revision c "
        "JOIN doc_meta d ON c.doc_id=d.doc_id GROUP BY c.doc_id, c.clause_number "
        "HAVING COUNT(*)>1").fetchall()
    out: dict[str, tuple[str, str, str, str]] = {}
    for r in rows:
        out[r["doc_id"]] = (r["doc_id"], r["standard_no"], r["standard_name"],
                            "dup_clause_number")
    conn.close()
    return list(out.values())


def scan_targets() -> list[tuple[str, str, str, str]]:
    """Gate A 纯扫描件 → 同上形态。

    目标集格式（var/tmp/gate_a_targetset.json）：{"target": [[doc_id, no, name], ...]}
    ——初版只认 list / docs / targets 键，漏了 "target"，实测 0 命中后补齐；三元组
    直接用 doc_id（权威），不再按号回查。
    """
    p = ROOT / "var" / "tmp" / "gate_a_targetset.json"
    if not p.exists():
        print(f"[warn] Gate A 目标集缺失：{p}")
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = data.get("target") or data.get("docs") or data.get("targets") or []
    else:
        items = data
    out: list[tuple[str, str, str, str]] = []
    for it in items:
        if isinstance(it, (list, tuple)) and len(it) >= 3:
            out.append((str(it[0]), str(it[1]), str(it[2]), "gate_a_scan"))
        elif isinstance(it, dict) and it.get("doc_id"):
            out.append((str(it["doc_id"]), str(it.get("standard_no") or ""),
                        str(it.get("standard_name") or ""), "gate_a_scan"))
    return out


def resolve_pdf(doc_id: str, standard_no: str) -> Path | None:
    """定位源 PDF：doc_meta.file_path 直取；无扩展名/不存在则在库内按号搜索。"""
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    row = conn.execute("SELECT file_path FROM doc_meta WHERE doc_id=?", (doc_id,)).fetchone()
    conn.close()
    cands: list[Path] = []
    if row and row[0]:
        cands.append(Path(row[0]))
        if not Path(row[0]).suffix:
            cands.append(Path(str(row[0]) + ".pdf"))
    squashed = standard_no.replace(" ", "").replace("/", "／")
    lib = Path(r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT")
    for seg in lib.iterdir() if lib.exists() else []:
        if not seg.is_dir():
            continue
        for pat in (f"*{squashed}*", f"*{squashed.replace('／', '/')}*"):
            cands.extend(sorted(seg.glob(pat)))
    for c in cands:
        if c.exists() and c.is_file() and c.stat().st_size > 1024:
            return c
    return None


def textfix_targets() -> list[tuple[str, str, str, str]]:
    """文本级已修家族的遗留文档 → 重导目标。

    家族（本会话已修、只对新入库生效）：spaced-run（逐字符拉开）、
    unit-midspace（单位内空格）、split-value（数值劈开）、pua-residue（PUA
    分隔符）、dot-leader（公式编号引导点线）。判据复用 audit_text（与审计同
    口径，避免两套标准）。
    ⚠ 新增修复族时必须同步加进本集合——否则该族文档不会被重导（2026-09-15
    实测：dot-leader 修复后漏加，残留 35 部未降）。
    """
    sys.path.insert(0, str(VARDIR))
    import audit_text as A
    families = {"spaced-run", "unit-midspace", "split-value", "pua-residue",
                "dot-leader"}
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    hits: dict[str, tuple[str, str, set]] = {}
    for r in conn.execute(
            "SELECT d.doc_id, d.standard_no, d.standard_name, c.content_text "
            "FROM clause_revision c JOIN doc_meta d ON c.doc_id=d.doc_id "
            "WHERE c.content_type='normal'"):
        got = set(A.audit_clause(r["content_text"])) & families
        if got:
            prev = hits.get(r["doc_id"])
            hits[r["doc_id"]] = (r["standard_no"], r["standard_name"],
                                 got | (prev[2] if prev else set()))
    conn.close()
    return [(did, no, name, "textfix:" + ",".join(sorted(got)))
            for did, (no, name, got) in hits.items()]


def all_targets() -> list[tuple[str, str, str, str]]:
    """**全库所有文档** → 全量重导目标（收敛循环 v2 的「从 0 再扫」）。

    配合 `--reuse`（复用缓存解析产物）使用：零 OCR、零云额度，259 部约 10–20
    分钟；不配合 `--reuse` 则是真重 OCR（贵，只在改动了 OCR 本身时用）。
    """
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT doc_id, standard_no, standard_name FROM doc_meta "
        "ORDER BY standard_no").fetchall()
    conn.close()
    return [(r["doc_id"], r["standard_no"], r["standard_name"], "all_docs")
            for r in rows]


def main() -> None:
    args = sys.argv[1:]
    limit = None
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    only = args[args.index("--only") + 1] if "--only" in args else "all"
    reuse = "--reuse" in args          # 复用缓存产物：零 OCR（收敛循环默认）
    reset = "--reset" in args          # 清状态重跑（全量循环每轮都要真跑）

    targets: dict[str, tuple[str, str, str, str]] = {}
    if only in ("all", "dup"):
        for t in dup_targets():
            targets[t[0]] = t
    if only in ("all", "scan"):
        for t in scan_targets():
            targets.setdefault(t[0], t)
    if only in ("all", "textfix"):
        for t in textfix_targets():
            targets.setdefault(t[0], t)
    if only == "all_docs":
        for t in all_targets():
            targets.setdefault(t[0], t)
    state = {} if reset else load_state()
    if reset:
        save_state({})
    pending = [t for t in targets.values() if state.get(t[0], {}).get("status") != "ok"]
    if limit:
        pending = pending[:limit]
    print(f"[repair] 目标 {len(targets)} 部 · 待处理 {len(pending)} 部 "
          f"（已 ok {sum(1 for v in state.values() if v.get('status') == 'ok')}）"
          f"{' · 复用产物零 OCR' if reuse else ' · 真重 OCR'}")
    if not pending:
        print("[repair] 无待处理")
        return

    from src.core.ingestion.pipeline import run_full_ingest

    ok = fail = skip = 0
    for i, (doc_id, std_no, name, reason) in enumerate(pending, 1):
        pdf = resolve_pdf(doc_id, std_no)
        if pdf is None:
            print(f"[{i}/{len(pending)}] 跳过（源 PDF 未找到）: {std_no}")
            state[doc_id] = {"status": "no_source", "reason": reason,
                             "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
            save_state(state)
            skip += 1
            continue
        print(f"[{i}/{len(pending)}] {std_no} | {reason} | {pdf.name[:44]}")
        # 先验护栏（仅复用模式）：预测条款数，灾难性下降 → 拒导并记账
        if reuse:
            old_n = current_clause_count(doc_id)
            pred = predict_clauses(parse_dir_of(doc_id), pdf)
            if (pred is not None and old_n >= PREFLIGHT_MIN_DOC
                    and pred < max(3, int(old_n * PREFLIGHT_RATIO))):
                msg = (f"先验护栏：条款 {old_n} → 预测 {pred} "
                       f"（下降 >{(1 - PREFLIGHT_RATIO) * 100:.0f}%），拒绝重导")
                print(f"    ⛔ {msg}")
                state[doc_id] = {"status": "preflight_regression", "reason": reason,
                                 "old_clauses": old_n, "pred_clauses": pred,
                                 "message": msg,
                                 "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
                save_state(state)
                with open(LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": state[doc_id]["ts"], "doc_id": doc_id,
                                        "standard_no": std_no, "reason": reason,
                                        "ingest_status": "preflight_regression",
                                        "old_clauses": old_n, "pred_clauses": pred,
                                        "message": msg}, ensure_ascii=False) + "\n")
                skip += 1
                continue
        t0 = time.monotonic()
        res: dict = {}
        for attempt in (1, 2):
            try:
                res = run_full_ingest(pdf, std_no, name, reingest=True,
                                      reuse_parse=reuse)
            except Exception as e:  # noqa: BLE001
                res = {"status": "error", "message": f"{type(e).__name__}: {str(e)[:160]}"}
            if res.get("status") in ("ok", "duplicate"):
                break
            if attempt == 1:
                print(f"    重试（{str(res.get('message'))[:70]}）")
                time.sleep(30)
        wall = round(time.monotonic() - t0, 1)
        st = res.get("status")
        state[doc_id] = {"status": "ok" if st in ("ok", "duplicate") else "failed",
                         "ingest_status": st, "wall_s": wall,
                         "message": (res.get("message") or "")[:160],
                         "reason": reason, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
        save_state(state)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": state[doc_id]["ts"], "doc_id": doc_id,
                                "standard_no": std_no, "reason": reason,
                                "ingest_status": st, "wall_s": wall,
                                "message": state[doc_id]["message"]},
                               ensure_ascii=False) + "\n")
        if st in ("ok", "duplicate"):
            ok += 1
            print(f"    ok ({wall}s)")
        else:
            fail += 1
            print(f"    FAILED ({wall}s): {state[doc_id]['message'][:80]}")

    print(f"[repair] 完成：ok={ok} failed={fail} skip={skip}")


if __name__ == "__main__":
    main()
