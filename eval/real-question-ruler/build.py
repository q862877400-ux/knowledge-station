# -*- coding: utf-8 -*-
"""造「真人问答召回尺子」（spec 010）。

## 这是什么

从 415,742 条**真人问答**里，挑出"答复点名了库内文件"的那些（**可当考卷**），
经**五道机械过滤 + 分层抽样**，产出 **500 条**召回尺子。

## 判据只有一个所有者（FR-002）

"答复点名的文件在不在库里"这条判据**不在这里重写** ——
直接从 `tools/gov-qa/measure-locate-rate.py` **动态加载**
（那个文件名带连字符，不能普通 import）。
⇒ 两个工具的数字**天然一致**，不会各写一份正则而分叉。

## 五道过滤（各自计数，FR-004/005/007）

| # | 过滤 | 判据 |
|---|---|---|
| F1 | 非考卷 | 答复没点名任何库内文件 |
| F2 | 投诉/举报 | 22 个特征词命中 `question`（这类**没有对错标准**） |
| F3 | 问句过长 | `len(question) > 200`（那是**来信全文**，不是提问） |
| F4 | 问句过短 | `len(question) < 8`（多半是标题） |
| F5 | 重复 | 同 `question` 只留 1 条（记 `dup_count`） |

## 分层抽样（FR-003）

按 `source` 分层；每层配额 ∝ **候选数的平方根**（避免大源通吃，也避免小源挤爆）；
层内固定种子随机抽。种子写进产物元数据 ⇒ **可复现**。

## 用法
    .venv\\Scripts\\python eval/real-question-ruler/build.py            # 造尺子
    .venv\\Scripts\\python eval/real-question-ruler/build.py --n 100     # 改规模
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DB = Path(__import__("os").environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

#: 加载官方判据模块（FR-002：一个判据一个所有者）
_LOCATE = REPO / "tools" / "gov-qa" / "measure-locate-rate.py"


def _load_official():
    spec = importlib.util.spec_from_file_location("_ks_locate_rate", _LOCATE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ks_locate_rate"] = mod
    spec.loader.exec_module(mod)
    return mod


LOC = _load_official()

#: 投诉/举报特征词（这类**没有对错标准**，答复是"已督促整改"，不是"依据某条法规"）
#: ⚠ 与方案稿 §五 坑 1 同一张表；筛掉不是删掉 —— 归到另一堆，见 stats 的 excluded。
COMPLAINT = ("投诉", "举报", "辱骂", "态度", "不作为", "推诿", "拒不开门", "乱收费",
             "噪音", "扰民", "违建", "拖欠", "索赔", "纠纷", "上访", "信访", "曝光",
             "我反映", "我要举报", "投诉电话", "处理结果", "迟迟不")

#: 问句长度上下限
MIN_Q = 8
MAX_Q = 200

#: 固定种子（写进产物元数据 ⇒ 可复现）
SEED = 20261012

#: 默认规模
DEFAULT_N = 500


def is_complaint(q: str) -> bool:
    return any(w in q for w in COMPLAINT)


def load_lib() -> dict[str, str]:
    """标准名 → 标准号（**复用官方 load_lib**，口径不分叉）。"""
    return LOC.load_lib(DB)


def load_doc_ids() -> dict[str, str]:
    """标准名（norm 后）→ doc_id，供尺子记录 gold_doc_id。"""
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    out = {}
    for doc_id, nm in c.execute("SELECT doc_id, standard_name FROM doc_meta"):
        if nm:
            out[LOC.norm(nm)] = doc_id
    c.close()
    return out


def doc_text_index(doc_ids: set[str]) -> dict[str, str]:
    """doc_id → 该文档全部条款正文（拼接，用于"零重合"判据）。

    ⚠ **口径说明（必须写进 README）**：gold 到**文档级**，所以"零重合"是拿
    **整篇文档的全文**比的 —— 这与 `eval/lay-phrasing/` 拿**单条条文**比
    **不是一回事**，两边的数字**不许互相引用**。
    """
    if not doc_ids:
        return {}
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    out: dict[str, list[str]] = defaultdict(list)
    q = ",".join("?" * len(doc_ids))
    for doc_id, txt in c.execute(
            f"SELECT doc_id, content_text FROM clause_revision WHERE doc_id IN ({q})",
            tuple(doc_ids)):
        if txt:
            out[doc_id].append(txt)
    c.close()
    return {k: "".join(v) for k, v in out.items()}


def _bigrams(s: str) -> set[str]:
    """字符二元组（"≥2 字公共子串"的可算近似：有公共二元组 ⇔ 有长度 ≥2 的公共子串）。"""
    s = re.sub(r"\s+", "", s or "")
    return {s[i:i + 2] for i in range(len(s) - 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description="造真人问答召回尺子")
    ap.add_argument("--n", type=int, default=DEFAULT_N, help="目标条数")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default=str(HERE / "ruler-v1.jsonl"))
    ap.add_argument("--stats", default=str(HERE / "stats-v1.json"))
    args = ap.parse_args()

    lib = load_lib()
    print(f"[m] 库内标准名: {len(lib):,}")

    files = sorted(LOC.DATA.glob("*.jsonl"))
    print(f"[m] 数据文件: {len(files)}")

    # ---- 五道过滤，各自计数 ----
    excl = Counter()
    total = 0
    cands: list[dict] = []
    for f in files:
        for ln in f.open(encoding="utf-8", errors="replace"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                excl["行解析失败"] += 1
                continue
            total += 1
            ans = r.get("answer") or ""
            q = (r.get("question") or "").strip()

            # F1：答复点名了库内文件吗
            names = LOC.DOC_RE.findall(ans) + LOC.STD_RE.findall(ans)
            hits = []
            for name in names:
                no = LOC.find_std(lib, name)
                if no:
                    hits.append({"name": name, "lib_no": no,
                                 "weak": any(w in name for w in LOC.WEAK)})
            if not hits:
                excl["F1 非考卷（没点名库内文件）"] += 1
                continue

            # F2：投诉/举报
            if is_complaint(q):
                excl["F2 投诉/举报（无对错标准）"] += 1
                continue

            # F3：问句过长
            if len(q) > MAX_Q:
                excl["F3 问句过长（>200 字，是来信全文）"] += 1
                continue

            # F4：问句过短
            if len(q) < MIN_Q:
                excl["F4 问句过短（<8 字，多半是标题）"] += 1
                continue

            uniq = sorted({h["lib_no"] for h in hits})
            src = str(r.get("source") or "")
            rid = str(r.get("id") or "")
            cands.append({
                "source": r.get("source"),
                "id": r.get("id"),
                # ⚠ **追溯键用 (source, id)，不是 url**（2026-10-12 实测）：
                #   `url` 有 9,174 条为 None，且 163 个 url 重复（最高 ×8,045）⇒
                #   拿 url 当键会**指向错记录**（实测 25 条 question 对不上）。
                #   `id` 单独也不唯一（10,374 个重复，占 22,236 条）。
                #   实测唯一覆盖全部 415,742 条的键是 **`(source, id)`**（重复 0）。
                "trace_key": f"{src}|{rid}",
                "url": r.get("url"),
                "dept": r.get("dept"),
                "question": q,
                "q_len": len(q),
                "gold_std": uniq,
                "gold_weak": all(h["weak"] for h in hits),
                "has_clause_ref": bool(LOC.CLAUSE_RE.search(ans)),
            })

    print(f"\n[m] 总记录 {total:,}")
    for k in sorted(excl):
        print(f"      {k:<38} {excl[k]:>9,}")
    print(f"      ⇒ 过五道过滤后: {len(cands):,}")

    # ---- F5：去重（同 question 只留 1 条，记 dup_count）----
    by_q: dict[str, list[dict]] = defaultdict(list)
    for c in cands:
        by_q[c["question"]].append(c)
    dedup = []
    for q, group in by_q.items():
        rec = group[0]
        rec["dup_count"] = len(group)
        dedup.append(rec)
    excl["F5 重复问题（同题只留 1 条）"] = len(cands) - len(dedup)
    print(f"\n[m] 去重后: {len(dedup):,}（去掉 {len(cands) - len(dedup):,} 条重复）")

    # ---- 分层抽样（按 source，配额 ∝ sqrt(候选数)）----
    rng = random.Random(args.seed)
    strata: dict[str, list[dict]] = defaultdict(list)
    for c in dedup:
        strata[str(c["source"])].append(c)
    weights = {s: len(v) ** 0.5 for s, v in strata.items()}
    wsum = sum(weights.values()) or 1.0
    quota = {s: max(1, round(args.n * w / wsum)) for s, w in weights.items()}

    picked: list[dict] = []
    for s, items in sorted(strata.items()):
        k = min(quota[s], len(items))
        picked.extend(rng.sample(items, k))
    # 配额取整会偏离目标，按需补齐/裁剪
    pool = [c for c in dedup if c not in picked]
    rng.shuffle(pool)
    while len(picked) < args.n and pool:
        picked.append(pool.pop())
    if len(picked) > args.n:
        rng.shuffle(picked)
        picked = picked[: args.n]

    print(f"[m] 抽样 {len(picked):,} 条（目标 {args.n}）")

    # ---- 补 gold_doc_id 与口语度分层 ----
    doc_ids_by_name = load_doc_ids()
    for c in picked:
        ids = []
        for no in c["gold_std"]:
            for nm, did in doc_ids_by_name.items():
                if lib.get(nm) == no:
                    ids.append(did)
                    break
        c["gold_doc_id"] = sorted(set(ids))
    idx = doc_text_index({d for c in picked for d in c["gold_doc_id"]})
    for c in picked:
        gold_text = "".join(idx.get(d, "") for d in c["gold_doc_id"])
        gb = _bigrams(gold_text)
        qb = _bigrams(c["question"])
        if not (qb & gb):
            c["layering"] = "zero_overlap"
        else:
            c["layering"] = "has_overlap"
        # 含术语（问句里出现库内标准名）
        if any(nm and nm in LOC.norm(c["question"]) for nm in lib):
            c["layering_term"] = "has_term"
        else:
            c["layering_term"] = "no_term"

    picked.sort(key=lambda x: (str(x["source"]), str(x["id"])))

    # ---- 写产物 ----
    out = Path(args.out)
    with out.open("w", encoding="utf-8") as fh:
        for c in picked:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")

    src_dist = Counter(str(c["source"]) for c in picked)
    lay_dist = Counter(c["layering"] for c in picked)
    stats = {
        "generated_from": {
            "data_files": len(files),
            "total_records": total,
            "db": str(DB),
        },
        "filters": dict(excl),
        "candidates_after_filters": len(cands),
        "after_dedup": len(dedup),
        "sampled": len(picked),
        "target_n": args.n,
        "seed": args.seed,
        "source_distribution": dict(src_dist.most_common()),
        "max_source_share": (max(src_dist.values()) / len(picked)) if picked else 0.0,
        "n_sources": len(src_dist),
        "layering": dict(lay_dist),
        "layering_term": dict(Counter(c["layering_term"] for c in picked)),
        "complaint_in_ruler": sum(1 for c in picked if is_complaint(c["question"])),
        "over_maxlen_in_ruler": sum(1 for c in picked if len(c["question"]) > MAX_Q),
    }
    Path(args.stats).write_text(json.dumps(stats, ensure_ascii=False, indent=2),
                                encoding="utf-8")

    print(f"\n[m] 产物: {out}")
    print(f"[m] 统计: {args.stats}")
    print(f"[m] 最大单一 source 占比: {stats['max_source_share']*100:.1f}%"
          f"  覆盖 source: {stats['n_sources']}")
    print(f"[m] 投诉类混入: {stats['complaint_in_ruler']}  >200 字混入: {stats['over_maxlen_in_ruler']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
