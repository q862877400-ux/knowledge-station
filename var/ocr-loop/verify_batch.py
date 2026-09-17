# -*- coding: utf-8 -*-
"""批次体检（2026-09-15 立）：一条命令回答"这批 VLM 产物能用吗"。

**为什么需要它**：此前每发现一个问题就写一个一次性探针（`probe_class.py`、
`probe_quality.py`、`probe_product_mix.py`、`probe_toc_reverse.py` …），
下一个人不知道该跑哪个、也拼不出全貌。本工具把它们整合成**单一入口**，
按"能不能用"的顺序给出结论 + 数值 + 反例样本。

检查顺序（先看整体可用性，再看具体缺陷）：
  1. 覆盖     —— 有多少部真有 VLM 产物（GAP/文本层兜底各多少）
  2. 塌缩     —— 条款数与正文量是否异常（单文档灾难性退化）
  3. 质量标记 —— 空/超短条款、PUA、目录行残留（**只在条款层判断**）
  4. 类分布   —— 判据命中（`audit_text` + `classify`），标出达线类
  5. 判据校准提示 —— 每类的命中是否经所有者处理仍在（区分真缺陷/仪器误报）

用法：
  python var/ocr-loop/verify_batch.py                # 当前批
  python var/ocr-loop/verify_batch.py --limit 50     # 抽检前 50 部（快）
  python var/ocr-loop/verify_batch.py --class pua-residue   # 单类取证明细
只读：不写库、不动 parse_out、不调云。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import artifact_index as AI                                    # noqa: E402
import corpus_docs as CD                                       # noqa: E402
import evolve as E                                             # noqa: E402
from src.core.ingestion.middle_locator import find_middle_files  # noqa: E402
from src.core.ingestion.pipeline import (build_clause_models,    # noqa: E402
                                         load_middle_items,
                                         split_items_into_clauses)
from src.core.text_utils import (clean_clause_text,             # noqa: E402
                                 strip_watermark_lines)

PUA = re.compile(r"[\ue000-\uf8ff]")
DOTS = re.compile(r"(?:…{2,}|[.．]{3,})\s*\d{1,3}\s*$", re.M)
FIX_LINE = 3


def _warn_if_not_current_batch(evaluating: Path) -> None:
    """**目标错位警告**（2026-09-16 立）。

    **为什么必须喊出来**：本工具默认评估 `corpus_docs.work_list()`，即
    **静态语料清单 `fresh_corpus_work.json`**（或因 `KS_CORPUS_LIST` 指定的清单），
    **不是 driver 正在跑的当前批**。我本轮就踩了这个坑：批次 13 因
    `dot-leader` 达线停链，我跑 `verify_batch.py --class dot-leader` 取证，
    它却评估了另一个 231 部的清单并打印「**无达线类 → 本批可继续推进**」——
    **与 driver 的判定直接相反**。若不设 `KS_CORPUS_LIST`，就会把
    "另一个语料零命中"误读成"当前批零缺陷"，进而放行一个真达线类。

    只加**告警**、不改语义：把"评估的是哪个清单"与"driver 在跑哪个"并列印出，
    并给出可直接复制的定向命令。
    """
    cb = HERE / "evolve" / "current_batch.json"
    try:
        cur = json.loads(cb.read_text(encoding="utf-8")).get("list") or ""
    except Exception:  # noqa: BLE001
        return
    if not cur:
        return
    cur_name = Path(str(cur)).name
    if cur_name == evaluating.name:
        return
    print()
    print("⚠⚠ **正在评估的清单 ≠ driver 的当前批** —— 下面的结论不适用于当前批！")
    print(f"     正在评估：{evaluating.name}")
    print(f"     driver 当前批：{cur_name}")
    print("     要看当前批请显式定向：")
    print(f"       $env:KS_CORPUS_LIST='{HERE / 'evolve' / cur_name}'")
    print("       python var/ocr-loop/verify_batch.py --class <类名>")
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--class", dest="cls", default="")
    a = ap.parse_args()

    idx = AI.load()
    docs = CD.work_docs()
    if a.limit:
        docs = docs[:a.limit]
    amb = AI.ambiguous_stems(docs)
    print(f"=== 批次体检 · {len(docs)} 部 · "
          f"清单 {CD.work_list().name} ===")
    _warn_if_not_current_batch(CD.work_list())

    cov: Counter = Counter()
    cls_docs: dict[str, set] = defaultdict(set)
    flagged: list[str] = []
    ev_by_cls: dict[str, list[str]] = defaultdict(list)
    total_clauses = total_chars = 0
    n_eval = 0

    for d in docs:
        rec = E.evaluate_doc(d, idx, HERE / "evolve" / "scratch", amb)
        art = rec.get("artifact", {})
        pb = art.get("parse_backend", "unknown")
        if art.get("kind") == "blocks":
            cov["文本层兜底（无 VLM 产物）"] += 1
        elif rec.get("verdict") == "GAP":
            cov["无产物 GAP"] += 1
        else:
            cov[f"VLM 产物({pb})"] += 1
        if rec.get("verdict") == "GAP":
            continue
        n_eval += 1
        for c in (rec.get("classes") or {}):
            cls_docs[c].add(d["std_no"])
            for e in (rec.get("evidence") or {}).get(c, []):
                if len(ev_by_cls[c]) < 6:
                    ev_by_cls[c].append(f"[{d['std_no'][:30]} {e.get('clause')}] "
                                        f"{e.get('frag', '')[:96]!r}")
        # 条款层质量（不用 item 层现象，避免"产物里有≠条款里有"的误报）
        r = AI.resolve(d, idx, amb)
        if not r.get("dir"):
            continue
        mids = find_middle_files(Path(r["dir"]))
        if not mids:
            continue
        items, ps = load_middle_items(mids[0])
        # 与入库同参（2026-09-17）：切分层与清洗链都要拿到本文档标准号，
        # 否则"页码 + 标准号"那一族判据无法消歧 —— 上面这层 `clean_clause_text`
        # 是对**已清洗过的** model 文本再洗一遍，不传标准号时那第二遍会把
        # 入库刻意保留的表格末格删掉（继承自父版本的"不幂等"那 4 行）。
        models, _ = build_clause_models("q", d["std_no"], "standard",
                                        split_items_into_clauses(items, standard_no=d["std_no"]), ps)
        texts = [clean_clause_text(m.content_text or "", own_standard_no=d["std_no"])
                 for m in models]
        total_clauses += len(texts)
        total_chars += sum(len(t) for t in texts)
        flags = []
        if sum(len(t) for t in texts) < 200:
            flags.append("正文过少")
        short = sum(1 for t in texts if len(t.strip()) < 10)
        if texts and short > len(texts) * 0.3:
            flags.append(f"空/短条款{short}/{len(texts)}")
        if any(PUA.search(t) for t in texts):
            flags.append("PUA")
        if any(DOTS.search(t) for t in texts):
            flags.append("目录行")
        if any(strip_watermark_lines(t) != t for t in texts):
            flags.append("水印")
        if flags:
            flagged.append(f"{d['std_no'][:48]:<50} " + " ".join(flags))

    print("\n[1] 覆盖")
    for k, v in cov.most_common():
        print(f"    {k:<26} {v}")
    vlm_n = sum(v for k, v in cov.items() if k.startswith("VLM"))
    print(f"    → VLM 产物占 **{vlm_n}/{len(docs)}**"
          f"（评估口径 {n_eval} 部）")
    print("\n[2] 规模")
    print(f"    条款总数 {total_clauses:,} · 正文字符 {total_chars:,}"
          f" · 均 {total_chars / max(total_clauses, 1):.0f} 字符/条")
    print("\n[3] 条款层质量标记")
    if flagged:
        for s in flagged[:15]:
            print("    ", s)
        if len(flagged) > 15:
            print(f"     …另有 {len(flagged) - 15} 部")
    else:
        print("     （无）")
    print("\n[4] 类分布（判据命中，按部数）")
    ranked = sorted(cls_docs.items(), key=lambda kv: -len(kv[1]))
    if not ranked:
        print("     （无命中）")
    for c, s in ranked:
        mark = "  ⚠达线" if len(s) >= FIX_LINE else ""
        print(f"    {c:<30} {len(s):>3} 部{mark}")
    if a.cls and ev_by_cls.get(a.cls):
        print(f"\n[5] 类 `{a.cls}` 命中原文")
        for s in ev_by_cls[a.cls]:
            print("    ", s)
    print("\n[结论] " + ("有达线类 → 应进修复流程（arbiter plan）"
                       if any(len(s) >= FIX_LINE for s in cls_docs.values())
                       else "无达线类 → 本批可继续推进"))


if __name__ == "__main__":
    main()
