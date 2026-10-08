"""E9 / P2 诊断·第 1 刀：**候选列能不能当"筛子"，把正确条文从第 4,322 名提上来？**

## 为什么做这个
- 总纲 P2 的口径是「**先诊断、后改法**」；`NEXT-DEV-PLAN §三序 4` 要求"先量收益、再决定改不改"。
- 上一批（P2 诊断·第 0 刀，见交接单 ①C）只回答了"**库里有没有现成的相关性列**" —— 答案是没有：
  有分辨力的列全是"类型/质量/时效"属性。**但"没有相关性列"不等于"这些列当筛子没有收益"**，
  这是两个不同的问题，本实验量的是后者。
- `exp-8-fullrank` 给的靶子：正确条文（headline 120 条）向量**全库 120/120 都召回了**，
  但**中位名次 = 4,322 / 663,634**（前 0.65%），`Top1000` 只覆盖 30.0%。
  ⇒ 若有一列能把检索空间缩到 x%，名次中位预期 ≈ 4,322·x（**前提：筛选与相关性独立**）。

## 冻结口径（先写死，跑完不许改）
- **参考空间** = `clause_vec` 的全部行（= 当前向量检索实际扫描的空间）。**分母以脚本实测为准，不写死**。
- **考卷** = `benchmark-v2.jsonl` 的 headline **120** 条
  （`v2.bucket=="keep"` 且无 `gold_multi_def`/`gold_dup_text`，与 exp-8 完全同一口径）；
  **金标 = 去重后的 `v2.gold_cr_id`**（120 条提问只落在 **64** 个不同条款上，去重后按条款算）。
  副口径：**按提问条数加权**（同一金标条款被多条提问共用时算多票）—— 两个口径都要报，防"去重口径"单独成立。
  另一副口径：全量 **171** 条（仅报金标条款数，不单独跑）。
- **只测"可当筛子用"的列**。**明确排除文档身份类**（`standard_no` / `doc_id` / `standard_name`）——
  那是**泄漏**（知道答案在哪篇才筛得动），不是可用信号。命中文档身份列的话只作为上界登记。
- **判据（机械、只看数）**：
  · 对每一列，按"该值的金标密度（gold/该值行数）降序"贪心纳入取值，
    求出**金标存活率 ≥ 95% 时所需的最小库保留率 `r95`**（同理 `r99`）。
  · **提速倍数 = 1 / r95**（筛选与相关性独立时，名次期望等比缩小）。
  · **随机基线 = 0.95**：随机扔掉 5% 的库，金标也活 95% ⇒ 某列的 `r95` 若 ≈0.95 就是**零信号**。
  · 报"金标密度最高的取值"及其**富集倍数** = (金标占比)/(库占比)。
- **上界声明（必须一起读）**：取值排序是在**同一份金标**上拟合的 ⇒ `r95` 是**样本内 oracle 上界**，
  **不是**一个能直接上线的方案。所以结论只在"**连上界都没收益**"时才具有决定力。
- **只读**（`mode=ro`）；**不改任何生产代码**；**不写库**。

## 报什么
每列：取值数 / 覆盖率 / 金标密度最高的取值 / 富集倍数 / `r95` / `r99` / 提速倍数；
末尾：贪心选 2 列的联合 `r95`；以及"随机基线"对照行。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-9-col-prior\\measure.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))
BENCH = ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
OUT = HERE / "result.json"

# 候选列：仅"条款/文档的属性列"，不含任何文档身份列（见 docstring 冻结口径）
SQL = """
SELECT v.clause_revision_id,
       cr.knowledge_type, cr.type_confidence, cr.is_suspicious, cr.modality_strength,
       cr.content_type, cr.is_mandatory, cr.clause_number,
       length(coalesce(cr.content_text, '')) AS clen,
       dm.legal_status, dm.legal_hierarchy, dm.standard_type, dm.doc_type,
       dm.quality_grade, dm.effective_from
FROM clause_vec v
LEFT JOIN clause_revision cr ON cr.clause_revision_id = v.clause_revision_id
LEFT JOIN doc_meta dm ON dm.doc_id = cr.doc_id
"""

COLS = ["knowledge_type", "type_confidence", "is_suspicious", "modality_strength",
        "content_type", "is_mandatory", "clause_number_shape", "content_len_bucket",
        "legal_status", "legal_hierarchy", "standard_type", "doc_type",
        "quality_grade", "effective_year"]


def clause_shape(no: str | None) -> str:
    """把条款号归成形态桶（不看具体数字，避免变成身份列）。"""
    if not no:
        return "空"
    s = str(no).strip()
    if not s:
        return "空"
    if s[0].isdigit():
        return f"数字-{s.count('.') + 1}段"
    if s.startswith("图"):
        return "图"
    if s.startswith("表"):
        return "表"
    if s.startswith("附"):
        return "附录"
    return "其他"


def len_bucket(n: int | None) -> str:
    if n is None:
        return "空"
    if n == 0:
        return "0"
    if n < 40:
        return "<40"
    if n < 100:
        return "40-99"
    if n < 300:
        return "100-299"
    if n < 1000:
        return "300-999"
    return ">=1000"


def main() -> int:
    rows = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
    head = [r for r in rows
            if (r.get("v2") or {}).get("bucket") == "keep"
            and not ({"gold_multi_def", "gold_dup_text"} & set((r.get("v2") or {}).get("flags", [])))]
    gold_head = sorted({r["v2"]["gold_cr_id"] for r in head})
    gold_all = sorted({r["v2"]["gold_cr_id"] for r in rows})
    # 副口径：按"提问条数"加权（同一个金标条款被多条提问共用时算多票）
    gold_w = Counter(r["v2"]["gold_cr_id"] for r in head)
    print(f"[E9] headline {len(head)} 条 ⇒ 去重金标条款 {len(gold_head)} 个；全量 171 ⇒ {len(gold_all)} 个",
          flush=True)

    con = sqlite3.connect("file:" + str(DB) + "?mode=ro", uri=True)
    from src.core.storage.sqlite_db import load_vec_extension
    if not load_vec_extension(con):
        raise RuntimeError("sqlite-vec 扩展加载失败：clause_vec 无法读取")
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM clause_vec")
    total = cur.fetchone()[0]
    print(f"[E9] 参考空间 clause_vec = {total} 行；库 = {DB}（mode=ro）", flush=True)

    # 逐行取属性，按列累积（不整表读进内存：属性列小，但 66 万行仍需流式）
    per_col: dict[str, Counter] = {c: Counter() for c in COLS}
    per_col_gold: dict[str, Counter] = {c: Counter() for c in COLS}
    per_col_goldw: dict[str, Counter] = {c: Counter() for c in COLS}
    gold_set = set(gold_head)
    n_gold_seen = 0
    seen = 0
    for cid, kt, tc, susp, ms, ct, mand, cno, clen, ls, lh, st, dt, qg, eff in cur.execute(SQL):
        seen += 1
        vals = {
            "knowledge_type": kt, "type_confidence": tc, "is_suspicious": susp,
            "modality_strength": ms, "content_type": ct, "is_mandatory": mand,
            "clause_number_shape": clause_shape(cno), "content_len_bucket": len_bucket(clen),
            "legal_status": ls, "legal_hierarchy": lh, "standard_type": st, "doc_type": dt,
            "quality_grade": qg, "effective_year": (str(eff)[:4] if eff else None),
        }
        is_gold = cid in gold_set
        w = gold_w.get(cid, 0)
        if is_gold:
            n_gold_seen += 1
        for c in COLS:
            v = vals[c]
            key = "∅NULL" if v is None or v == "" else str(v)
            per_col[c][key] += 1
            if is_gold:
                per_col_gold[c][key] += 1
                per_col_goldw[c][key] += w
    con.close()
    print(f"[E9] 扫描 {seen} 行；命中金标条款 {n_gold_seen}/{len(gold_head)}", flush=True)

    def _r(cnt: Counter, gcnt: Counter, thr: float, order_keys: list[str]) -> float | None:
        ng = sum(gcnt.values())
        if not ng:
            return None
        n = sum(cnt.values())
        kept_c = kept_g = 0
        for k in order_keys:
            kept_c += cnt[k]
            kept_g += gcnt[k]
            if kept_g / ng >= thr:
                break
        return round(kept_c / n, 6) if n else None

    def pareto(col: str) -> dict:
        cnt = per_col[col]
        gcnt = per_col_gold[col]
        gwcnt = per_col_goldw[col]
        n = sum(cnt.values())
        ng = sum(gcnt.values())
        vals = sorted(cnt.keys(), key=lambda k: (-(gcnt[k] / cnt[k] if cnt[k] else 0.0), -gcnt[k]))
        out = {"n_values": len(vals), "n_null_or_empty": cnt.get("∅NULL", 0),
               "top": []}
        for k in vals[:6]:
            share_c = cnt[k] / n if n else 0.0
            share_g = gcnt[k] / ng if ng else 0.0
            out["top"].append({
                "value": k, "corpus": cnt[k], "gold": gcnt[k],
                "share_corpus": round(share_c, 6), "share_gold": round(share_g, 6),
                "enrichment": round(share_g / share_c, 3) if share_c else None})
        # 贪心纳入：按金标密度降序，累计到金标存活率 >= 阈值
        for thr in (0.95, 0.99):
            r = _r(cnt, gcnt, thr, vals)
            out[f"r{int(thr*100)}"] = r
            out[f"speedup{int(thr*100)}"] = round(1 / r, 3) if r else None
        # 副口径：按提问条数加权（取值排序仍按条款密度，只看"够不够"）
        out["r95_query_weighted"] = _r(cnt, gwcnt, 0.95, vals)
        out["speedup95_query_weighted"] = (round(1 / out["r95_query_weighted"], 3)
                                           if out["r95_query_weighted"] else None)
        return out

    report = {"frozen": "口径见 measure.py docstring（跑前写死）",
              "corpus": {"space": "clause_vec", "rows": total},
              "gold": {"headline_queries": len(head), "headline_gold_clauses": len(gold_head),
                       "all_gold_clauses": len(gold_all),
                       "gold_clauses_seen_in_corpus": n_gold_seen},
              "random_baseline": {"r95": 0.95, "r99": 0.99,
                                  "note": "随机扔 5% 的库，金标也活 95% ⇒ r95≈0.95 = 零信号"},
              "median_vector_rank_headline": 4322,
              "columns": {}}
    for c in COLS:
        report["columns"][c] = pareto(c)

    # 贪心选 2 列联合：只在 r95 最好的 4 列里两两组合（避免组合爆炸），第二次扫描建联合计数
    order = sorted(COLS, key=lambda c: (report["columns"][c]["r95"] or 9))
    best = order[:4]
    pairs = [(best[i], best[j]) for i in range(len(best)) for j in range(i + 1, len(best))]
    joint: dict[tuple[str, str], Counter] = {p: Counter() for p in pairs}
    joint_g: dict[tuple[str, str], Counter] = {p: Counter() for p in pairs}
    con = sqlite3.connect("file:" + str(DB) + "?mode=ro", uri=True)
    load_vec_extension(con)
    for cid, kt, tc, susp, ms, ct, mand, cno, clen, ls, lh, st, dt, qg, eff in con.execute(SQL):
        vals = {
            "knowledge_type": kt, "type_confidence": tc, "is_suspicious": susp,
            "modality_strength": ms, "content_type": ct, "is_mandatory": mand,
            "clause_number_shape": clause_shape(cno), "content_len_bucket": len_bucket(clen),
            "legal_status": ls, "legal_hierarchy": lh, "standard_type": st, "doc_type": dt,
            "quality_grade": qg, "effective_year": (str(eff)[:4] if eff else None),
        }
        is_gold = cid in gold_set
        for (a, b) in pairs:
            k = ("∅NULL" if vals[a] in (None, "") else str(vals[a]),
                 "∅NULL" if vals[b] in (None, "") else str(vals[b]))
            joint[(a, b)][k] += 1
            if is_gold:
                joint_g[(a, b)][k] += 1
    con.close()
    combo = []
    for (a, b) in pairs:
        cnt, gcnt = joint[(a, b)], joint_g[(a, b)]
        n, ng = sum(cnt.values()), sum(gcnt.values())
        ks = sorted(cnt.keys(), key=lambda k: (-(gcnt[k] / cnt[k] if cnt[k] else 0.0), -gcnt[k]))
        row = {"pair": [a, b], "n_values": len(ks)}
        for thr in (0.95, 0.99):
            kc = kg = 0
            for k in ks:
                kc += cnt[k]
                kg += gcnt[k]
                if ng and kg / ng >= thr:
                    break
            r = kc / n if n else None
            row[f"r{int(thr*100)}"] = round(r, 6) if r is not None else None
            row[f"speedup{int(thr*100)}"] = round(1 / r, 3) if r else None
        combo.append(row)
    combo.sort(key=lambda x: (x["r95"] or 9))
    report["pair_combinations"] = combo

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n[E9] ==== 候选列当筛子：金标存活 ≥95% 时库能缩到多少 ====")
    print(f"  {'列':22s} {'取值数':>6s} {'NULL':>7s} {'最富集取值':>18s} {'富集':>8s} "
          f"{'r95':>8s} {'提速':>7s} {'r95(加权)':>10s}")
    for c in order:
        r = report["columns"][c]
        t = r["top"][0] if r["top"] else {}
        print(f"  {c:22s} {r['n_values']:6d} {r['n_null_or_empty']:7d} "
              f"{str(t.get('value'))[:18]:>18s} {str(t.get('enrichment')):>8s} "
              f"{str(r['r95']):>8s} {str(r['speedup95']):>7s} {str(r['r95_query_weighted']):>10s}")
    print(f"  {'[随机基线]':22s} {'-':>6s} {'-':>7s} {'-':>18s} {'1.0':>8s} {'0.95':>8s} {'1.053':>7s} {'0.95':>10s}")
    print(f"\n[E9] ==== 最优 2 列联合（样本内 oracle 上界） ====")
    for p in report["pair_combinations"]:
        print(f"  {'×'.join(p['pair']):46s} r95={p['r95']}  提速={p['speedup95']}×")
    print("\n[E9] 达标所需（中位名次 4,322）：Top1000 需 4.32×；Top100 需 43.2×；Top20 需 216.1×")
    print(f"\n[E9] 已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
