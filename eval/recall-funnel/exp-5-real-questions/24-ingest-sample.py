"""入库试跑 · 步骤 2：**小样本**先跑（法规 + MinerU OCR 的国标），逐步验。

## 硬护栏（本脚本最重要的一段）
开始任何写操作**之前**，断言 `get_settings().db_path` 落在 `var/tmp/ingest-trial/` 之下；
不在就**立刻退出**。真库路径一个字节都不许被写。

## 两批料，走同一个入口 `law_text.ingest_law_text`
 · **法规**（`D:\\AI\\work space\\标准\\法律法规\\**\\<名>(YYYY-MM-DD).md`）
   ⇒ `split_law_text` 按「第X条」切；`doc_type="法律法规"`；
 · **国标 OCR**（`…\\GB\\**\\<标准号> <名>.mineru-4.0.10-vlm\\markdown.md`）
   ⇒ 先 `split_law_text`，切不出则 `split_gb_text` 按 `3.1 / 4.2 / A.1` 切；
   `doc_type="standard"`（**库内 6417 行 doc_meta 全是 standard**，写成法律法规会与全库不一致）；
   `standard_type` 按标准号判 mandatory/recommended；`short_code` 与 docx_ingest 同口径。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\24-ingest-sample.py --n-law 8 --n-gb 8
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "ingest-sample-result.json"
sys.path.insert(0, str(ROOT))          # 让 `import src.*` 生效

TRIAL = ROOT / "var" / "tmp" / "ingest-trial" / "data"
# ⚠ 必须在 import src.* **之前**设好，引擎据此定位库与模型缓存
os.environ["KS_DATA_DIR"] = str(TRIAL)
os.environ.setdefault("KS_MODELS_DIR", str(Path(os.environ["APPDATA"]) / "KnowledgeStation" / "models"))
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

LAW_ROOT = Path("D:/AI/work space/标准/法律法规")
GB_ROOT = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
SUFFIX = ".mineru-4.0.10-vlm"

#: 优先挑与 EHS 真实提问相关的法规（业主 11 条真问题暴露的就是这类）
LAW_PRIORITY = ["劳动法", "职业病防治法", "环境保护法", "特种设备安全法",
                "社会保险法", "行政处罚法", "矿山安全法", "劳动合同法"]

STD_RE = re.compile(r"^(GB(?:/T|/Z)?\s*\d+(?:\.\d+)?\s*-\s*\d{4})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-law", type=int, default=8)
    ap.add_argument("--n-gb", type=int, default=8)
    ap.add_argument("--only", choices=("law", "gb", "both"), default="both")
    args = ap.parse_args()

    # ---------- 硬护栏 ----------
    from src.core.config import get_settings
    dbp = get_settings().db_path.resolve()
    trial_root = TRIAL.resolve()
    print(f"[guard] 引擎将写入：{dbp}")
    if trial_root not in dbp.parents:
        print(f"[guard] ⛔ 目标不在试跑副本下（应在 {trial_root} 之下）—— **拒绝执行**")
        return 2
    print(f"[guard] ✅ 目标在试跑副本下，真库不会被写")

    import sqlite3
    from src.core.ingestion.law_text import ingest_law_text

    conn = sqlite3.connect(f"file:{dbp.as_posix()}?mode=ro", uri=True)
    before = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("doc_meta", "clause_revision")}
    conn.close()
    print(f"[before] doc_meta={before['doc_meta']}  clause_revision={before['clause_revision']}")

    results = []

    # ---------- A. 法规 ----------
    if args.only in ("law", "both"):
        all_md = [p for p in LAW_ROOT.rglob("*.md")]
        picked = []
        for key in LAW_PRIORITY:                       # 先挑 EHS 相关的
            hit = next((p for p in all_md if p.stem.startswith(key + "(")), None)
            if hit:
                picked.append(hit)
            if len(picked) >= args.n_law:
                break
        for p in sorted(all_md):                       # 不够再按目录顺序补
            if len(picked) >= args.n_law:
                break
            if p not in picked:
                picked.append(p)
        print(f"\n[A] 法规：共 {len(all_md)} 个 md，本次取 {len(picked)} 个")
        for p in picked:
            name = re.sub(r"\(\d{4}-\d{2}-\d{2}\)$", "", p.stem)
            m = re.search(r"\((\d{4}-\d{2}-\d{2})\)$", p.stem)
            text = p.read_text(encoding="utf-8", errors="ignore")
            try:
                r = ingest_law_text(text, standard_no=f"{name}(OCR采集)",
                                    standard_name=name,
                                    legal_hierarchy="法律",
                                    effective_from=(m.group(1) if m else None),
                                    source_marker=f"lawrefbook://{p.relative_to(LAW_ROOT).as_posix()}",
                                    source_url="https://github.com/RanKKI/LawRefBook")
                results.append({"kind": "law", "file": p.name, "status": r.get("status"),
                                "clauses": r.get("clauses"), "doc_id": r.get("doc_id")})
                print(f"    {p.name[:52]:52s} → {r.get('status')}  条数={r.get('clauses')}")
            except Exception as e:                                          # noqa: BLE001
                results.append({"kind": "law", "file": p.name, "error": f"{type(e).__name__}: {e}"})
                print(f"    {p.name[:52]:52s} → ⛔ {type(e).__name__}: {e}")

    # ---------- B. 国标 OCR ----------
    if args.only in ("gb", "both"):
        dirs = [d for d in GB_ROOT.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)
                and (d / "markdown.md").exists()]
        print(f"\n[B] 国标 OCR：共 {len(dirs)} 本已出，本次取 {args.n_gb} 本")
        for d in dirs[:args.n_gb]:
            stem = d.name[: -len(SUFFIX)]
            mm = STD_RE.match(stem)
            if not mm:
                results.append({"kind": "gb", "dir": d.name, "error": "文件名里认不出标准号"})
                print(f"    {stem[:64]:64s} → ⛔ 认不出标准号")
                continue
            std_no = re.sub(r"\s+", " ", mm.group(1)).strip()
            std_name = stem[mm.end():].strip() or std_no
            stype = "recommended" if "/T" in std_no.upper() or "/Z" in std_no.upper() else "mandatory"
            text = (d / "markdown.md").read_text(encoding="utf-8", errors="ignore")
            try:
                r = ingest_law_text(
                    text, standard_no=std_no, standard_name=std_name,
                    legal_hierarchy="GB", doc_type="standard",
                    standard_type=stype, legal_status="effective",
                    short_code=std_no.replace(" ", "").replace("-", ""),
                    source_marker=f"mineru-ocr://{d.name}/markdown.md",
                )
                results.append({"kind": "gb", "std_no": std_no, "name": std_name,
                                "style": stype, "status": r.get("status"),
                                "clauses": r.get("clauses"), "doc_id": r.get("doc_id")})
                print(f"    {std_no:22s} {std_name[:34]:34s} → {r.get('status')}  条数={r.get('clauses')}")
            except Exception as e:                                          # noqa: BLE001
                results.append({"kind": "gb", "std_no": std_no, "error": f"{type(e).__name__}: {e}"})
                print(f"    {std_no:22s} → ⛔ {type(e).__name__}: {e}")

    # ---------- 复核 ----------
    conn = sqlite3.connect(f"file:{dbp.as_posix()}?mode=ro", uri=True)
    after = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("doc_meta", "clause_revision")}
    new_docs = conn.execute(
        "SELECT COUNT(*) FROM doc_meta WHERE standard_no LIKE '%(OCR采集)'"
        " OR file_path LIKE 'mineru-ocr://%'").fetchone()[0]
    print(f"\n[after ] doc_meta={after['doc_meta']}  clause_revision={after['clause_revision']}")
    print(f"[delta ] 新增文档 {after['doc_meta']-before['doc_meta']}，"
          f"新增条款 {after['clause_revision']-before['clause_revision']}")
    print(f"[check ] 其中本次标记的来源（OCR采集/mineru-ocr）= {new_docs}")
    conn.close()

    OUT.write_text(json.dumps({
        "why": "入库试跑（小样本）：法规 markdown + MinerU OCR 国标，走 law_text.ingest_law_text",
        "guard": {"engine_db": str(dbp), "trial_root": str(trial_root), "passed": True},
        "before": before, "after": after,
        "delta": {"docs": after["doc_meta"] - before["doc_meta"],
                  "clauses": after["clause_revision"] - before["clause_revision"]},
        "results": results,
        "boundary": ["小样本，只判方向；真库未被写（引擎指向副本，且有护栏断言）。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
