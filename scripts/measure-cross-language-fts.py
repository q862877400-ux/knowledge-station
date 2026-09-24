"""量「按字找」在非中文资料上还灵不灵 —— 换一种资料集就能重跑的一把尺子。

背景（为什么必须有这个脚本）：
    生产的检索表 `clause_fts` 用 FTS5 `tokenize='ascii'`（见 src/core/storage/schema.sql:107-117），
    入库前用 `segment_for_fts`（jieba）切分（见 src/core/text_utils.py:1360）。中文没有词形变化，
    所以"同一个词的不同写法算两个词"这件事在中文库上**永远不会自己暴露**；一旦资料换成英文
    开发文档/技术手册就立刻暴露。这个脚本就是用来量它的。

测法（全自动，不手挑例子）：
    1) 读一个真实资料集的文本，按空行切成段。
    2) 用仓里**生产代码本体**（segment_for_fts / fts_match_expr）建内存 FTS5 表，
       DDL 与 clause_fts 逐字一致。
    3) 从语料真实词表里，用词尾变化规则自动生成「同一个词的两种写法」候选对 (A, B)，
       两种写法都必须在语料词表里真实出现才算一对。
    4) 找出只含 A 形（不含 B 形）的段落，然后**用 B 形去搜**，量两个不同的东西：
         ① 能不能匹配上（不看排名）—— 这一栏量的是「词汇桥接成不成立」；
         ② 能不能排进前 5     —— 这一栏量的是「排序好不好」。
       这两件事必须分开：混在一起会把结论带偏（本脚本第一版就是这么错的）。
       注意 ② 在"单词查询 + 上千段"下是**最苛刻的测法**，远低于真实提问效果，
       它的用途只是横向比较几种分词口径，不能当生产效果的预估。

    5) 对照三种口径：
         ascii  —— 生产现状
         porter —— 重建索引用词形还原
         前缀   —— 索引不动，只在提问时把英文词换成「词干*」

    6) 中文安全对照：porter 会不会改坏中文词、会不会改坏标识符/哈希。

已知边界（别把这个脚本的结论放大）：
    - 语料是我给的目录，不是生产的 522k 条；这里量的是**分词口径**这类通用性质，
      不是产量指标。
    - 「同词两写法」候选对是**词尾规则**生成的，规则不完美；但测量不依赖规则正确
      （porter 若没归到同一词干，它那一栏的数字自己就会低）。

用法：
    .venv\\Scripts\\python.exe scripts\\measure-cross-language-fts.py <资料目录> [文件通配]
    不传目录时用默认的 DSH 官方文档目录（本机路径，换机器要改）。
"""
from __future__ import annotations

import glob
import sqlite3
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.core.text_utils import fts_match_expr, segment_for_fts  # noqa: E402

# 本机默认语料：DSH 官方开发文档（英文为主）。换机器/换资料集时用命令行参数覆盖。
DEFAULT_CORPUS = Path(r"D:\AI\DSH\deepseek-harness\docs")

# clause_fts 的 DDL 逐字取自 src/core/storage/schema.sql:107-117，只把 tokenize 参数化。
DDL = """
CREATE VIRTUAL TABLE {tbl} USING fts5(
    clause_revision_id UNINDEXED,
    clause_number,
    standard_no,
    title,
    content_segmented,
    modality UNINDEXED,
    subject UNINDEXED,
    behavior_scope_segmented,
    tokenize = {tok}
);
"""

W = 78


def head(t: str) -> None:
    print("=" * W)
    print(t)
    print("=" * W)


def chunk_text(text: str, size: int = 1000) -> list[str]:
    """按空行切段再拼到 ~size 字，不跨段切断。"""
    paras = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n")]
    out, buf = [], ""
    for p in paras:
        if not p:
            continue
        if len(buf) + len(p) + 2 > size and buf:
            out.append(buf)
            buf = p
        else:
            buf = (buf + "\n\n" + p) if buf else p
    if buf:
        out.append(buf)
    return out


def load_corpus(root: Path, pattern: str) -> list[tuple[str, str]]:
    files = sorted(Path(p) for p in glob.glob(str(root / "**" / pattern), recursive=True))
    rows: list[tuple[str, str]] = []
    for f in files:
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for c in chunk_text(txt):
            rows.append((str(f), c))
    return rows


def build(conn: sqlite3.Connection, tbl: str, tok: str, rows: list[tuple[str, str]]) -> float:
    t0 = time.time()
    conn.execute(DDL.format(tbl=tbl, tok=tok))
    conn.executemany(
        f"INSERT INTO {tbl}(clause_revision_id,clause_number,standard_no,title,"
        f"content_segmented,modality,subject,behavior_scope_segmented) VALUES(?,?,?,?,?,?,?,?)",
        [(f"r{i}", "", "", "", segment_for_fts(text), "", "", "") for i, (_s, text) in enumerate(rows)],
    )
    return time.time() - t0


def vocab(conn: sqlite3.Connection, tbl: str) -> set[str]:
    conn.execute(f"CREATE VIRTUAL TABLE v_{tbl} USING fts5vocab({tbl}, 'row')")
    # ⚠ fts5vocab 第二参数只能是 'row'/'col'/'instance'，不是 'vocab'。
    return {t for (t,) in conn.execute(f"SELECT term FROM v_{tbl}")}


def search(conn: sqlite3.Connection, tbl: str, q: str, k: int = 5) -> list[int]:
    expr = fts_match_expr(q)
    if not expr.strip():
        return []
    try:
        cur = conn.execute(
            f"SELECT rowid FROM {tbl} WHERE {tbl} MATCH ? ORDER BY bm25({tbl}) LIMIT ?", (expr, k)
        )
        return [r[0] for r in cur.fetchall()]
    except sqlite3.OperationalError as e:
        print(f"    [MATCH 报错] {q!r} -> {expr!r}: {e}")
        return []


def exists(conn: sqlite3.Connection, tbl: str, q: str, rowid: int) -> bool:
    """这个段落**能不能**被 q 匹配上（不看排名）。"""
    expr = fts_match_expr(q)
    if not expr.strip():
        return False
    cur = conn.execute(
        f"SELECT 1 FROM {tbl} WHERE {tbl} MATCH ? AND rowid = ? LIMIT 1", (expr, rowid)
    )
    return cur.fetchone() is not None


def variants(w: str) -> set[str]:
    """词尾变化规则。规则不完美，但测量不依赖它正确（见模块头部说明）。"""
    v: set[str] = {w + "s", w + "es", w + "ed", w + "ing", w + "ly"}
    if w.endswith("e"):
        v |= {w + "d", w[:-1] + "ing", w[:-1] + "ed"}
    if len(w) > 3 and w.endswith("y") and w[-2] not in "aeiou":
        v |= {w[:-1] + "ies", w[:-1] + "ied", w[:-1] + "ier"}
    for suf, rep in (("ing", ""), ("ed", ""), ("es", ""), ("s", ""),
                     ("ation", "e"), ("ion", "e"), ("ment", ""), ("er", ""), ("ly", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            v.add(w[: -len(suf)] + rep)
    return v


def has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CORPUS
    pattern = sys.argv[2] if len(sys.argv) > 2 else "*.md"
    if not root.exists():
        print(f"资料目录不存在：{root}")
        return 2

    head("① 生产分词在这份资料上长什么样（用仓里函数本体）")
    for s in ["The retrieval pipeline uses a reranker to configure the harness.",
              "检索流水线会重排候选。"]:
        print(f"  原文 : {s}")
        print(f"  jieba: {segment_for_fts(s)}")
        try:
            print(f"  MATCH: {fts_match_expr(s)}")
        except Exception as e:  # noqa: BLE001
            print(f"  MATCH: <报错 {type(e).__name__}: {e}>")
        print()

    head(f"② 装语料：{root}  ({pattern})")
    rows = load_corpus(root, pattern)
    if not rows:
        print("  没有读到任何段落，检查目录/通配符。")
        return 2
    print(f"  段数 {len(rows)}")

    # 分词碎片率：jieba 的词典是现代汉语，遇到文言/专业术语/外文会把词碎成单字。
    # 单字占比越高，说明"按字找"在这份资料上切得越差。这一栏对纯中文资料同样有意义
    # （前面的词形对照只对拉丁字母资料有意义）。
    probe = "\n\n".join(t for _s, t in rows[:800])
    toks = segment_for_fts(probe).split()
    if toks:
        singles = [t for t in toks if len(t) == 1]
        cjk_single = [t for t in singles if has_cjk(t)]
        print(f"  分词碎片率：单字 token {len(singles)}/{len(toks)} = {len(singles) / len(toks):.1%}"
              f"（其中中文单字 {len(cjk_single)} 个）")

    conn = sqlite3.connect(":memory:")
    t_a = build(conn, "fts_ascii", "'ascii'", rows)
    t_p = build(conn, "fts_porter", "'porter'", rows)
    print(f"  fts_ascii 建表 {t_a:.1f}s / fts_porter 建表 {t_p:.1f}s")

    head("③ 从语料真实词表里自动生成「同一个词两种写法」候选对")
    ascii_terms = vocab(conn, "fts_ascii")
    porter_terms = vocab(conn, "fts_porter")
    print(f"  ascii 词表 {len(ascii_terms)} 个 / porter 词干表 {len(porter_terms)} 个"
          f" ⇒ 压缩 {1 - len(porter_terms) / max(len(ascii_terms), 1):.1%}")

    pairs: list[tuple[str, str]] = []
    for w in sorted(ascii_terms):
        if len(w) < 6 or not w.isalpha():
            continue
        for b in sorted(variants(w)):
            if b != w and b in ascii_terms:
                pairs.append((w, b))  # 段落含 w，用 b 去搜
    print(f"  候选对数 {len(pairs)}")
    if not pairs:
        print("  这份资料里没有拉丁字母词形变化（纯中文资料属于正常结果）。")
        return 0

    head("④ 段落含 A 形，用 B 形去搜：三种口径对照")
    step = max(1, len(pairs) // 300)
    trials = pairs[::step][:300]
    print(f"  抽样试验 {len(trials)} 组")

    r = {"ascii_cov": 0, "porter_cov": 0, "ascii_top": 0, "porter_top": 0}
    checked: list[tuple[str, int]] = []
    for a, b in trials:
        hits_a = set(search(conn, "fts_ascii", a, k=50))
        if not hits_a:
            continue
        # 目标 = 只含 A 形的段落（ascii 搜得到 A、搜不到 B ⇒ 确实没有 B 形）
        target = hits_a - set(search(conn, "fts_ascii", b, k=2000))
        if not target:
            continue
        tgt = sorted(target)[0]
        r["ascii_cov"] += int(exists(conn, "fts_ascii", b, tgt))
        r["porter_cov"] += int(exists(conn, "fts_porter", b, tgt))
        r["ascii_top"] += int(tgt in set(search(conn, "fts_ascii", b, k=5)))
        r["porter_top"] += int(tgt in set(search(conn, "fts_porter", b, k=5)))
        checked.append((b, tgt))

    n = len(checked)
    if not n:
        print("  没有有效试验组。")
        return 0

    print(f"  有效试验 {n} 组")
    print("    ① 能不能匹配上（不看排名）：")
    print(f"       ascii （生产现状）  {r['ascii_cov']}/{n} = {r['ascii_cov'] / n:.1%}")
    print(f"       porter（重建索引）  {r['porter_cov']}/{n} = {r['porter_cov'] / n:.1%}")

    # 第三条路：索引一个字不动，只在提问时把词换成「词干*」前缀查询。
    # 词干用 SQLite 自带 porter 分词器取，不引入第二套实现（口径唯一这条规矩照旧）。
    conn.execute("CREATE VIRTUAL TABLE stem1 USING fts5(w, tokenize='porter')")
    conn.execute("CREATE VIRTUAL TABLE stem1_v USING fts5vocab(stem1, 'row')")
    cache: dict[str, str] = {}

    def stem_of(w: str) -> str:
        if w not in cache:
            conn.execute("DELETE FROM stem1")
            conn.execute("INSERT INTO stem1(w) VALUES(?)", (w,))
            row = conn.execute("SELECT term FROM stem1_v LIMIT 1").fetchone()
            cache[w] = row[0] if row else w
        return cache[w]

    def pref(q: str) -> str:
        return f'"{stem_of(q)}"*'

    pc = pt = 0
    for b, tgt in checked:
        try:
            cur = conn.execute(
                "SELECT 1 FROM fts_ascii WHERE fts_ascii MATCH ? AND rowid = ? LIMIT 1", (pref(b), tgt)
            )
            pc += int(cur.fetchone() is not None)
            cur = conn.execute(
                "SELECT rowid FROM fts_ascii WHERE fts_ascii MATCH ? ORDER BY bm25(fts_ascii) LIMIT 5",
                (pref(b),),
            )
            pt += int(tgt in {x[0] for x in cur.fetchall()})
        except sqlite3.OperationalError as e:
            print(f"    [前缀 MATCH 报错] {b!r} -> {pref(b)!r}: {e}")
    print(f"       前缀* （索引不动）  {pc}/{n} = {pc / n:.1%}")

    print("    ② 排进前 5（⚠ 单词查询下最苛刻，只用于横向比较，不是生产效果）")
    print(f"       ascii （生产现状）  {r['ascii_top']}/{n} = {r['ascii_top'] / n:.1%}")
    print(f"       porter（重建索引）  {r['porter_top']}/{n} = {r['porter_top'] / n:.1%}")
    print(f"       前缀* （索引不动）  {pt}/{n} = {pt / n:.1%}")

    ratios, exacts, prefs = [], [], []
    for b, _t in checked[:60]:
        try:
            e = conn.execute("SELECT count(*) FROM fts_ascii WHERE fts_ascii MATCH ?",
                             (fts_match_expr(b),)).fetchone()[0]
            p = conn.execute("SELECT count(*) FROM fts_ascii WHERE fts_ascii MATCH ?",
                             (pref(b),)).fetchone()[0]
        except sqlite3.OperationalError:
            continue
        if e:
            exacts.append(e)
            prefs.append(p)
            ratios.append(p / e)
    if ratios:
        print("    ③ 前缀的代价：候选池放大倍数"
              f" 中位 {statistics.median(ratios):.1f}× / 最大 {max(ratios):.0f}×")
        print(f"       精确词命中段数中位 {statistics.median(exacts):.0f}；"
              f"前缀命中段数中位 {statistics.median(prefs):.0f}")

    head("⑤ 反向对照：porter 会不会改坏中文词 / 标识符")
    lost = ascii_terms - porter_terms
    new = porter_terms - ascii_terms
    lost_cjk = [w for w in lost if has_cjk(w)]
    print(f"  消失 {len(lost)} 个词，其中**含中文**的 {len(lost_cjk)} 个")
    print(f"  新增 {len(new)} 个词，其中含中文的 {len([w for w in new if has_cjk(w)])} 个")
    print(f"  原词存活率 {sum(1 for w in ascii_terms if w in porter_terms)}/{len(ascii_terms)}"
          f" = {sum(1 for w in ascii_terms if w in porter_terms) / len(ascii_terms):.2%}")
    print(f"    （消失的词里非中文的例子，通常正是哈希/编号/配置键：{sorted(lost)[:5]}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
