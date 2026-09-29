"""分析业主给的两批生成结果（V2 完整 500 / V1 半批 85）+ 上一轮 v1 提示词的旧数据。

四件事：
  ① 规矩核验：说法里有没有偷用术语/2 字片段/英文。
  ② **本批主角**：有多少术语**根本没有外行入口**——两个口径对照：
     a) 生成时自己写空的（v2 新机制）；
     b) 机械口径：说法与定义条款**零个 2 字重合**。
  ③ 真搜（按字找）：任一条说法能不能把术语的定义条款搜进前 5 / 前 20。
  ④ **提示词 v1 → v2 是否修好了"给概念下定义"**：机械判据 = 说法里有没有疑问标记。
     v2 明确要求"第一人称问句"，v1 没有 ⇒ 无疑问标记的比例应明显下降。
     对照用的是**上一轮旧格式数据**（var/tmp/lay-50.jsonl，50 术语 × 2 条）。

用法：
    python analyze-gen.py          # 只跑便宜的部分（②③ 的按字找 + ④）
    python analyze-gen.py --vec    # 追加向量路（约 27 分钟，建议后台跑）
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
from src.core.text_utils import fts_match_expr  # noqa: E402

D = REPO / "var" / "tmp"
DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
TERM_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*)?\s*"
    r"([\u4e00-\u9fff][\u4e00-\u9fff（）()·、\-]{2,15}?)\s*"
    r"([A-Za-z][A-Za-z \-/(),]{2,60}?)\s*"
    r"(?=[\u4e00-\u9fff（])"
)
# 疑问标记：v2 要求"第一人称问句"，没有这些标记的基本就是陈述句/定义
QMARK = ("吗", "呢", "吧", "？", "?", "怎么", "为什么", "为啥", "多少", "几", "哪",
         "什么", "是否", "算不算", "要不要", "合不合规", "会不会", "能不能", "可不可以",
         "该不该", "有没有", "行不行", "对不对", "多久", "多长", "多重", "算不算")


def load(p: Path) -> list[dict]:
    rows, bad = [], 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            bad += 1
    if bad:
        print(f"  ⚠ {p.name}: {bad} 行解析失败（文件像是被截断）")
    return rows


def texts_of(r: dict) -> list[tuple[str, str]]:
    """兼容两种格式：老格式 lay=["说法"]；新格式 lay=[{"text":...,"register":...}]。"""
    out = []
    for x in r.get("lay") or []:
        if isinstance(x, str):
            out.append((x, "(未标)"))
        elif isinstance(x, dict):
            out.append((str(x.get("text") or ""), str(x.get("register") or "(未标)")))
    return [(t, g) for t, g in out if t.strip()]


def has_qmark(t: str) -> bool:
    return any(m in t for m in QMARK)


def subs2(s: str) -> set[str]:
    return {s[i:i + 2] for i in range(len(s) - 1)}


def main() -> int:
    want_vec = "--vec" in sys.argv
    V2 = load(D / "gen-V2.jsonl")
    V1 = load(D / "gen-V1.jsonl")
    OLD = load(D / "lay-50.jsonl")          # 上一轮 v1 提示词的旧数据
    t500 = {l.strip() for l in (D / "terms-500.txt").read_text(encoding="utf-8").splitlines() if l.strip()}

    print("=" * 78)
    print("① 规模与规矩核验")
    print("=" * 78)
    for name, rows in (("V2(500)", V2), ("V1(半批)", V1), ("旧数据(v1提示词)", OLD)):
        lay = sum(len(texts_of(r)) for r in rows)
        print(f"  {name:<16} 术语 {len(rows):>3} / 说法 {lay:>4}")

    # 规矩核验（V2 为主）
    viol_whole = viol_sub = viol_en = 0
    n_lay = 0
    for r in V2:
        t = r["term"]
        sb = subs2(t)
        for tx, _g in texts_of(r):
            n_lay += 1
            if t in tx:
                viol_whole += 1
            elif sb & subs2(tx):
                viol_sub += 1
            if re.search(r"[A-Za-z]{3,}", tx):
                viol_en += 1
    print(f"  V2 规矩核验（共 {n_lay} 条）：用了术语本体 {viol_whole}；"
          f"撞 2 字片段 {viol_sub}；出现英文 {viol_en}")

    print()
    print("=" * 78)
    print("② 有多少术语根本没有外行入口（本批主角）")
    print("=" * 78)
    empty = [r["term"] for r in V2 if not texts_of(r)]
    print(f"  a) 生成时**自己写空**的：{len(empty)}/{len(V2)} = {len(empty)/len(V2):.1%}")

    # 找定义条款
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    want = {r["term"] for r in V2} | {r["term"] for r in V1} | {r["term"] for r in OLD}
    define: dict[str, set[str]] = defaultdict(set)
    dtext: dict[str, list[str]] = defaultdict(list)
    t0 = time.time()
    for cid, txt in conn.execute("SELECT clause_revision_id, content_text FROM clause_revision"):
        m = TERM_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in want:
            define[t].add(cid)
            dtext[t].append(txt or "")
    print(f"  （扫全库找定义条款，{time.time()-t0:.0f}s；"
          f"{len(define)}/{len(want)} 个术语找到定义）")

    def hookless(rows: list[dict]) -> tuple[list[str], list[str]]:
        zero, with_hook = [], []
        for r in rows:
            t = r["term"]
            if t not in define:
                continue
            srcs = dtext[t]
            hooked = False
            for tx, _g in texts_of(r):
                ss = subs2(tx)
                if any(ss & subs2(s) for s in srcs):
                    hooked = True
                    break
            (with_hook if hooked else zero).append(t)
        return zero, with_hook

    z2, h2 = hookless(V2)
    print(f"  b) 机械口径**零个 2 字重合**：{len(z2)}/{len(z2)+len(h2)} = "
          f"{len(z2)/max(len(z2)+len(h2),1):.1%}")

    both = sorted(set(empty) & set(z2))
    only_empty = sorted(set(empty) - set(z2))
    only_mech = [t for t in z2 if t not in set(empty)]
    print()
    print(f"  两个口径交叉（都指「没入口」的 = {len(both)} 个）：")
    print(f"    只被生成方判为空的 {len(only_empty)} 个：{only_empty[:12]}")
    print(f"    只被机械口径判为无重合的 {len(only_mech)} 个（写了说法，但一个 2 字都对不上）")

    print()
    print("=" * 78)
    print("③ 真搜（按字找）：任一条说法能不能把定义条款搜进前 5 / 前 20")
    print("=" * 78)

    def fts_ids(q: str, k: int) -> set[str]:
        expr = fts_match_expr(q)
        if not expr.strip():
            return set()
        try:
            cur = conn.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (expr, k))
            return {r[0] for r in cur.fetchall()}
        except sqlite3.OperationalError:
            return set()

    def arm(rows: list[dict], label: str) -> dict:
        res = {"5": 0, "20": 0, "n": 0}
        for r in rows:
            t = r["term"]
            if t not in define:
                continue
            tgt = define[t]
            ok5 = ok20 = False
            for tx, _g in texts_of(r):
                if not ok5:
                    ok5 = bool(tgt & fts_ids(tx, 5))
                if not ok20:
                    ok20 = bool(tgt & fts_ids(tx, 20))
                if ok5 and ok20:
                    break
            res["n"] += 1
            res["5"] += int(ok5)
            res["20"] += int(ok20)
        if res["n"]:
            print(f"  {label:<22} 前5 {res['5']:>3}/{res['n']} = {res['5']/res['n']:.1%}"
                  f"   前20 {res['20']:>3}/{res['n']} = {res['20']/res['n']:.1%}")
        return res

    arm(V2, "V2 大白话·按字找")
    arm(V1, "V1 大白话·按字找")
    # 上限：用术语本身
    up = {"5": 0, "20": 0, "n": 0}
    for t in sorted({r["term"] for r in V2}):
        if t not in define:
            continue
        up["n"] += 1
        up["5"] += int(bool(define[t] & fts_ids(t, 5)))
        up["20"] += int(bool(define[t] & fts_ids(t, 20)))
    print(f"  {'上限：术语本身':<20} 前5 {up['5']:>3}/{up['n']} = {up['5']/up['n']:.1%}"
          f"   前20 {up['20']:>3}/{up['n']} = {up['20']/up['n']:.1%}")

    print()
    print("=" * 78)
    print("④ 提示词 v1 → v2：\"给概念下定义\"修好了吗（机械判据＝有没有疑问标记）")
    print("=" * 78)
    for name, rows in (("旧数据(v1 提示词)", OLD), ("V2(新提示词)", V2)):
        tot = stmt = 0
        for r in rows:
            for tx, _g in texts_of(r):
                tot += 1
                stmt += int(not has_qmark(tx))
        print(f"  {name:<18} 共 {tot:>4} 条，其中**没有疑问标记**（像陈述/定义）{stmt:>4} 条 = {stmt/max(tot,1):.1%}")
    regs = Counter(g for r in V2 for _t, g in texts_of(r))
    print(f"  V2 的人群分布：{dict(regs)}")

    if want_vec:
        import sqlite_vec
        from src.core.retrieval import embedder
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        def vec_ids(q: str, k: int) -> set[str]:
            blob = sqlite_vec.serialize_float32(embedder.embed_query(q))
            try:
                cur = conn.execute(
                    "SELECT clause_revision_id FROM clause_vec WHERE embedding MATCH ? "
                    "AND k = ? ORDER BY distance", (blob, k))
                return {r[0] for r in cur.fetchall()}
            except sqlite3.OperationalError:
                return set()

        print()
        print("=" * 78)
        print("⑤ 真搜（向量）：同样的两条臂")
        print("=" * 78)
        for name, rows in (("V2 大白话·向量", V2), ("V1 大白话·向量", V1)):
            res = {"5": 0, "20": 0, "n": 0}
            t1 = time.time()
            for r in rows:
                t = r["term"]
                if t not in define:
                    continue
                tgt = define[t]
                ok5 = ok20 = False
                for tx, _g in texts_of(r):
                    if not ok5:
                        ok5 = bool(tgt & vec_ids(tx, 5))
                    if not ok20:
                        ok20 = bool(tgt & vec_ids(tx, 20))
                    if ok5 and ok20:
                        break
                res["n"] += 1
                res["5"] += int(ok5)
                res["20"] += int(ok20)
            print(f"  {name:<22} 前5 {res['5']:>3}/{res['n']} = {res['5']/res['n']:.1%}"
                  f"   前20 {res['20']:>3}/{res['n']} = {res['20']/res['n']:.1%}"
                  f"   （{time.time()-t1:.0f}s）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
