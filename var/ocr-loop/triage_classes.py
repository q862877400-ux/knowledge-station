# -*- coding: utf-8 -*-
"""类级批量甄别器（只读）：看清每个类**到底命中了什么原文**。

动因：收敛循环前两轮的触发类（`ocr-wide-space-units`、`appendix-table-lowconf`）
经样例复核**全是仪器误报**。逐类跑 `evidence` 太慢，且看不到"判据匹配到的那一段
文本"。本工具一次评估 N 部文档，对每个命中打印：类名 · 条款号 · **匹配到的子串**
（判据 `pattern.search().group(0)`）· 上下文片段。

判读口径（一眼可判）：
- 匹配串本身是合法国标排版 → **仪器误报**（改判据/去重/加必要条件）
- 匹配串是 OCR 损伤（数字被劈开、PUA、点线、单位拆字）→ **真缺陷**（修管线）
- 匹配串是识别层难度（表格区低置信）→ **已知限制**（登记，不进修复线）
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import artifact_index as AI        # noqa: E402
import audit_text as A             # noqa: E402
import classify as C               # noqa: E402
import evolve as E                 # noqa: E402


def main() -> None:
    args = sys.argv[1:]
    n = int(args[args.index("--docs") + 1]) if "--docs" in args else 8
    per_cls = int(args[args.index("--per") + 1]) if "--per" in args else 3
    only = args[args.index("--class") + 1] if "--class" in args else ""
    std_only = args[args.index("--std-no") + 1] if "--std-no" in args else ""

    from src.core.ingestion.pipeline import (build_clause_models,
                                             load_middle_items,
                                             load_middle_items_from_blocks,
                                             split_items_into_clauses)
    from src.core.ingestion.middle_locator import find_middle_files

    pats = {name: pat for name, pat in A.CHECKS}
    pats.update({name: pat for name, pat in (
        ("spurious-clause-number-numunit", C._RE_NUM_UNIT),
        ("ocr-wide-space-units", C._RE_WIDE_SPACE),
        ("mfr-unit-misread", C._RE_MFR_UNIT),
        ("punctuation-substitution", C._RE_PUNCT_SUB),
        ("toc-ingested-as-clauses", C._RE_TOC_LINE),
    )})

    idx = AI.load()
    docs = E.doc_list()[:n]
    if std_only:
        docs = [d for d in E.doc_list() if d["std_no"] == std_only]
    samples: dict[str, list] = defaultdict(list)
    cls_docs: dict[str, set] = defaultdict(set)
    for d in docs:
        art = AI.resolve_to_parse_dir(d, idx)
        if art["dir"] is None:
            continue
        res = E._cached(Path(art["dir"]), d.get("file_path"))
        if not res:
            continue
        try:
            if res.get("deep_output"):
                mids = find_middle_files(Path(res["deep_output"]))
                if not mids:
                    continue
                items, ps = load_middle_items(mids[0])
            else:
                items, _ = load_middle_items_from_blocks(res["blocks"])
                ps = {int(k) - 1: (float(v["width"]), float(v["height"]))
                      for k, v in (res.get("geometries") or {}).items()}
            models, _ = build_clause_models("probe", d["std_no"], "standard",
                                            split_items_into_clauses(items), ps)
        except Exception:  # noqa: BLE001
            continue
        for m in models:
            txt = m.content_text or ""
            got = ([(c, "audit") for c in A.audit_clause(txt)]
                   + [(c, "classify") for c in C.classify_clause(
                       m.clause_number or "", txt, m.ocr_confidence or 1.0)])
            for cls, _src in got:
                cls_docs[cls].add(d["std_no"])
                pat = pats.get(cls)
                mt = ""
                ctx = txt[:110]
                if pat is not None:
                    mm = pat.search(txt)
                    if mm:
                        mt = mm.group(0)[:60]
                        # 匹配处上下文（±55 字）——判断真假命中必需
                        a = max(0, mm.start() - 55)
                        b = min(len(txt), mm.end() + 55)
                        ctx = ("…" if a else "") + txt[a:b] + ("…" if b < len(txt) else "")
                if len(samples[cls]) < per_cls:
                    samples[cls].append({"std_no": d["std_no"],
                                         "clause": m.clause_number,
                                         "match": mt,
                                         "conf": round(m.ocr_confidence or 0, 3),
                                         "ctx": ctx})

    order = sorted(cls_docs, key=lambda c: -len(cls_docs[c]))
    print(f"评估 {len(docs)} 部 · 命中类 {len(order)}\n")
    for cls in order:
        if only and only != cls:
            continue
        print(f"── {cls}（{len(cls_docs[cls])} 部）")
        for s in samples[cls]:
            print(f"   [{s['std_no']} {s['clause']}] match={s['match']!r} "
                  f"conf={s['conf']}")
            print(f"      {s['ctx']!r}")
        print()


if __name__ == "__main__":
    main()
