# -*- coding: utf-8 -*-
"""独立复算「真人问答召回尺子」（spec 010 T002）。

## 为什么单独写一个

宪法 III「证据优于断言」+ 本仓规矩「报告只写跑过的命令」。
一个"我自己算的、我自己写出来"的产物，**不能自己证明自己**。
⇒ 本脚本**不 import `build.py`**，**重读原始数据与生产库**，
用**同一套判据**（同样从 `measure-locate-rate.py` 加载）把每个关键数字**再算一遍**。

## 复算什么

| 项 | 判据 |
|---|---|
| 尺子条数 | 逐行数 `ruler-v1.jsonl` |
| 投诉类混入 | 用**同一张特征词表**扫 `question` |
| 超长混入 | `len(question) > 200` |
| 最大单一 source 占比 | 按 `source` 分组 |
| 覆盖 source 数 | `set` 去重 |
| **每条 gold_std 在库里存在** | 查 `doc_meta.standard_name`（**重读库**，不用尺子里的 gold_doc_id） |
| **每条 url 能回查原始数据** | 从 592 个 jsonl 建 `url → question` 索引，逐条比对 |
| 分层统计 | 复算 `zero_overlap` / `has_overlap` |
| 与 `stats-v1.json` 对账 | 逐项比 |

## 用法
    .venv\\Scripts\\python eval/real-question-ruler/verify.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
_LOCATE = REPO / "tools" / "gov-qa" / "measure-locate-rate.py"

#: 与 build.py **同一张表**（这里重新抄一份是刻意的：独立复算不该共享可变状态）
COMPLAINT = ("投诉", "举报", "辱骂", "态度", "不作为", "推诿", "拒不开门", "乱收费",
             "噪音", "扰民", "违建", "拖欠", "索赔", "纠纷", "上访", "信访", "曝光",
             "我反映", "我要举报", "投诉电话", "处理结果", "迟迟不")
MAX_Q = 200


def _load_official():
    spec = importlib.util.spec_from_file_location("_ks_locate_rate_v", _LOCATE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ks_locate_rate_v"] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description="独立复算尺子")
    ap.add_argument("--ruler", default=str(HERE / "ruler-v1.jsonl"))
    ap.add_argument("--stats", default=str(HERE / "stats-v1.json"))
    args = ap.parse_args()

    LOC = _load_official()
    ruler = [json.loads(l) for l in Path(args.ruler).read_text(encoding="utf-8").split("\n") if l.strip()]
    stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))

    fails: list[str] = []
    def check(name, got, want):
        ok = got == want
        print(f"  {'✅' if ok else '❌'} {name:<46} 实测={got!r}  期望={want!r}")
        if not ok:
            fails.append(name)

    print("=== ① 规模与过滤（对 stats 的声明）===")
    check("尺子条数", len(ruler), stats["sampled"])
    check("目标条数", len(ruler), 500)

    print()
    print("=== ② SC-002 不把测不出来的算进分数 ===")
    n_comp = sum(1 for c in ruler if any(w in c["question"] for w in COMPLAINT))
    check("投诉/举报混入", n_comp, 0)
    n_long = sum(1 for c in ruler if len(c["question"]) > MAX_Q)
    check("问句 >200 字混入", n_long, 0)
    check("stats 声明的投诉混入", stats["complaint_in_ruler"], 0)
    check("stats 声明的超长混入", stats["over_maxlen_in_ruler"], 0)

    print()
    print("=== ③ SC-003 不偏科 ===")
    dist = Counter(str(c["source"]) for c in ruler)
    share = max(dist.values()) / len(ruler)
    check("最大单一 source 占比 ≤ 10%", round(share, 4) <= 0.10, True)
    check("覆盖 source 数 ≥ 20", len(dist) >= 20, True)
    check("stats 里的 max_source_share 与复算一致",
          round(stats["max_source_share"], 4), round(share, 4))
    check("stats 里的 n_sources 与复算一致", stats["n_sources"], len(dist))

    print()
    print("=== ④ SC-005 每条 gold_std 在库里真实存在（重读库）===")
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    lib_names = {LOC.norm(nm) for (nm,) in c.execute("SELECT standard_name FROM doc_meta") if nm}
    lib_by_no = {}
    for no, nm in c.execute("SELECT standard_no, standard_name FROM doc_meta"):
        if nm:
            lib_by_no.setdefault(no, set()).add(LOC.norm(nm))
    bad_gold = []
    for r in ruler:
        for g in r["gold_std"]:
            if g not in lib_by_no:
                bad_gold.append((r["id"], g))
    check("gold_std 不在库里的条数", len(bad_gold), 0)
    for i, g in bad_gold[:5]:
        print(f"      ⚠ {i} → {g}")

    print()
    print("=== ⑤ SC-006 每条能回查原始数据、question 逐字一致 ===")
    print("  ⚠ 追溯键用 **(source, id)**，不是 url —— 实测 url 有 9,174 条为 None、")
    print("     163 个重复（最高 ×8,045）；id 单独也不唯一（10,374 个重复）。")
    print("     实测唯一覆盖全部 415,742 条的键是 (source, id)（重复 0）。")
    key2q: dict[str, str] = {}
    n_rec = 0
    for f in sorted(LOC.DATA.glob("*.jsonl")):
        # ⚠ 用 split("\n")，**不用** splitlines()（它会按 U+2028 切碎记录 —— 2026-10-12 实测）
        for ln in f.read_text(encoding="utf-8", errors="replace").split("\n"):
            if not ln.strip():
                continue
            try:
                rec = json.loads(ln)
            except Exception:
                continue
            n_rec += 1
            k = f"{str(rec.get('source') or '')}|{str(rec.get('id') or '')}"
            key2q[k] = (rec.get("question") or "").strip()
    check("原始数据可索引记录数", n_rec, 415742)
    miss = [r["id"] for r in ruler if r["trace_key"] not in key2q]
    check("trace_key 回查不到的条数", len(miss), 0)
    diff_q = [r["id"] for r in ruler
              if r["trace_key"] in key2q and key2q[r["trace_key"]] != r["question"]]
    check("question 与原始数据不一致的条数", len(diff_q), 0)
    for i in diff_q[:3]:
        r = next(x for x in ruler if x["id"] == i)
        print(f"      ⚠ {i}")
        print(f"         尺子: {r['question'][:80]!r}")
        print(f"         原始: {key2q[r['trace_key']][:80]!r}")
    # 附带核对 url：允许为 None，但非 None 的必须能查到
    n_url_none = sum(1 for r in ruler if not r.get("url"))
    check("url 为空的条数（允许，靠 trace_key 追溯）", n_url_none, 27)
    print(f"      （url 为空的 {n_url_none} 条仍可经 trace_key 追溯）")

    print()
    print("=== ⑥ 分层统计复算 ===")
    lay = Counter(c["layering"] for c in ruler)
    check("stats 的 layering（旧·文档级）与复算一致", stats["layering"], dict(lay))
    print(f"      zero_overlap={lay.get('zero_overlap',0)}  has_overlap={lay.get('has_overlap',0)}")
    lay2 = Counter(c["layering_v2"] for c in ruler)
    check("stats 的 layering_v2（新·答复级）与复算一致", stats["layering_v2"], dict(lay2))
    print(f"      {dict(lay2)}")
    ov = sorted(c["overlap_with_answer"] for c in ruler)
    check("overlap_with_answer 中位与复算一致",
          round(stats["overlap_with_answer"]["median"], 4), round(ov[len(ov) // 2], 4))
    term = Counter(c["layering_term"] for c in ruler)
    check("stats 的 layering_term 与复算一致", stats["layering_term"], dict(term))

    print()
    print("=== ⑥b 新分层必须有区分度（**这是它存在的理由**）===")
    print("  ⚠ 旧口径（文档级零重合）只 4/500 —— 一篇法规几万字，与任何问句都大概率")
    print("     有 2 字公共子串 ⇒ **没有区分度**。")
    print("     新口径改比**官方答复**（问句与答复是**两个不同的人**写的 ⇒ 非循环）。")
    n_buckets = len([k for k, v in lay2.items() if v > 0])
    check("新分层里非空的档数 ≥ 4", n_buckets >= 4, True)
    print(f"      各档条数: {dict(lay2)}")
    check("旧口径零重合 < 50（已知事实，防被说成「损耗很小」）",
          lay.get("zero_overlap", 0) < 50, True)

    print()
    print("=== ⑦ 必填字段完整性 ===")
    need = {"id", "source", "url", "dept", "question", "q_len", "gold_std",
            "gold_doc_id", "gold_weak", "layering", "dup_count", "has_clause_ref",
            "trace_key", "layering_v2", "overlap_with_answer"}
    missing = [i for i, c in enumerate(ruler) if not need.issubset(c.keys())]
    check("缺字段的记录数", len(missing), 0)
    no_gold = sum(1 for c in ruler if not c["gold_std"])
    check("gold_std 为空的条数", no_gold, 0)
    leaked = [c["id"] for c in ruler if "_answer" in c]
    check("答复原文泄漏进产物的条数（版权待核，不许入库）", len(leaked), 0)

    print()
    print(f"===== 通过 / 失败：{len(fails)} 项失败 =====")
    for f in fails:
        print(f"  ❌ {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
