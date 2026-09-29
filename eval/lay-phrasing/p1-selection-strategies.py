"""P1 下一刀：攻"选中术语"这一步（当前瓶颈，top-1 仅 16.4%）。

已证：纯翻译（选中 1 个术语）> 混合（术语+大白话）。那**多选几个**呢？
量四个策略，同一批 1,651 条非 A 说法，**靶子=术语的定义条款**：

  S1  top-1            ：现状基线
  S2  top-3 扇出        ：选中 3 个术语，各查一次，结果并起来
  S3  top-5 扇出        ：同上，5 个
  S4  top-1 但先**排除**容易混的近邻（按术语之间的相似度去掉 top-2 相邻项）

⚠ "扇出"的结果条数会变多（前 5/前 20 的含义随之变化），所以本脚本额外报
   **"正确答案是否出现在返回集合里"（召回口径，不看名次）**——那才是"选对没"的真问题。
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
from src.core.retrieval.embedder import embed_batch  # noqa: E402
from src.core.text_utils import fts_match_expr, segment_for_fts  # noqa: E402

D = REPO / "var" / "tmp"
KS_DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
TERM_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*)?\s*"
    r"([\u4e00-\u9fff][\u4e00-\u9fff（）()·、\-]{2,15}?)\s*"
    r"([A-Za-z][A-Za-z \-/(),]{2,60}?)\s*"
    r"(?=[\u4e00-\u9fff（])"
)
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")


def words(text: str) -> set[str]:
    return {w for w in segment_for_fts(text or "").split() if CJK.match(w)}


def main() -> int:
    import numpy as np

    rows = [json.loads(l) for l in (D / "gen-V2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    terms = sorted({r["term"] for r in rows})
    tw = {t: words(t) for t in terms}

    ks = sqlite3.connect(f"file:{KS_DB}?mode=ro", uri=True)
    print("扫定义条款…", flush=True)
    define: dict[str, set[str]] = {t: set() for t in terms}
    for cid, txt in ks.execute("SELECT clause_revision_id, content_text FROM clause_revision"):
        m = TERM_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in define:
            define[t].add(cid)

    cases = []
    for r in rows:
        t = r["term"]
        if not define.get(t):
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx or (words(tx) & tw[t]):
                continue
            cases.append((t, tx))
    n = len(cases)
    print(f"非 A 档 {n} 条；候选术语 {len(terms)}", flush=True)

    T = np.asarray(embed_batch(terms), dtype=np.float32)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    Q = np.asarray(embed_batch([c[1] for c in cases]), dtype=np.float32)
    Q /= np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9
    S = Q @ T.T                                  # (n, n_terms)
    order = np.argsort(-S, axis=1)
    term_term = T @ T.T                          # 术语之间的相似度（用来剔近邻）
    print(f"  嵌入完成；术语间相似度 中位 {np.median(term_term[np.triu_indices(len(terms),1)]):.3f}", flush=True)

    def fts(q: str, k: int) -> list[str]:
        expr = fts_match_expr(q)
        if not expr.strip():
            return []
        try:
            return [r[0] for r in ks.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (expr, k)).fetchall()]
        except sqlite3.OperationalError:
            return []

    strat = {k: [0, 0, 0] for k in ("S1", "S2", "S3", "S4")}   # 前5 / 前20 / 命中集合
    t0 = time.time()
    for i, (gold, _phrase) in enumerate(cases):
        tgt = define[gold]
        ranked = [terms[j] for j in order[i]]
        # S4：top-1 但先剔掉与 top-1 术语**高度相似**的近邻（相似度 > 中位 + 3 倍 MAD 之类，用固定阈值 0.90）
        near = [terms[j] for j in order[i] if float(term_term[order[i][0], j]) >= 0.90][:5]
        near = [t for t in near if t != ranked[0]] or ranked[1:2]
        picks = {"S1": ranked[:1], "S2": ranked[:3], "S3": ranked[:5], "S4": near[:1]}
        for name, ps in picks.items():
            got: list[str] = []
            for t in ps:
                got.extend(fts(t, 5))
            seen, uniq = set(), []
            for g in got:
                if g not in seen:
                    seen.add(g)
                    uniq.append(g)
            strat[name][0] += int(bool(tgt & set(uniq[:5])))
            strat[name][1] += int(bool(tgt & set(uniq[:20])))
            strat[name][2] += int(bool(tgt & set(uniq)))
        if (i + 1) % 400 == 0:
            print(f"  {i+1}/{n}  {time.time()-t0:.0f}s", flush=True)

    print()
    print("=" * 78)
    print(f"选择策略对照（{n} 条，" + f"每术语查 5 条）")
    print("=" * 78)
    print(f"{'策略':<28}{'前5':>8}{'前20':>8}{'命中集合(召回)':>16}")
    for name, label in (("S1", "S1 top-1（现状）"), ("S2", "S2 top-3 扇出"),
                        ("S3", "S3 top-5 扇出"), ("S4", "S4 top-1 剔近邻")):
        a, b, c = strat[name]
        print(f"{label:<28}{a/n:>8.1%}{b/n:>8.1%}{c/n:>16.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
