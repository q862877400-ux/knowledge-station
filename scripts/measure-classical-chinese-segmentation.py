"""P3.2 尺子：古籍/文言资料上，「切分方式」到底要不要换（字级？领域词典？）。

背景（为什么要有这把尺子）：
    `scripts/measure-cross-language-fts.py` 的 ④ 栏对古籍语料量到的那个 0.0% **不是中文侧的数字**
    —— 它只能从拉丁字母词里造「同词两写法」候选对，而古籍文件里只有 Gutenberg 的英文版权页有拉丁词
    （该脚本 §三·补 自己写明了这条局限）。所以「古籍 30.2% 的中文 token 被切成单字」这件事
    **一直只有分母、没有命中率**，P3.2 的判据（单字占比 + 检索命中率）缺了后半截。
    本脚本补的就是这后半截：在**中文侧**量「切分口径换不换」。

测法（全自动，不手挑例子）：
    语料：`var/fixtures/general-corpus/sanguo.txt`（三國志演義，Project Gutenberg #23950，
          繁體、文言、1.86 MB）—— 与 cross-language 尺子 D 行**同一份文件**，数字可对。
    1) 三种**切分口径**各建一张内存 FTS5 表，DDL 与生产 `clause_fts` 逐字一致（`tokenize='ascii'`）：
         A 现状     —— `segment_for_fts`（jieba `cut_for_search`，词典是现代汉语）
         B 字级     —— 每个汉字一个 token（查询侧对应"所有字都要出现"，即 AND 共现）
         C 领域词典 —— jieba + `load_userdict`（词典**只从语料前半段**挖，见下）
    2) 查询集**自动**从语料里挖：n=2/3/4 的汉字 n-gram，出现 ≥3 次；
       ⚠ **只在语料后半段挖查询词**，而 C 的词典**只从语料前半段挖**
       ⇒ 词典与考卷**不相交**，C 的收益构造上不可能来自"把答案塞进词典"（同 E3b 的留一法）。
    3) 每个查询词：目标 = 含该词的段落集合；量 recall@5 / recall@20 / MRR。

    4) 另立一节量**繁简轴**（**不是切分问题**，但同一份语料上它比切分致命得多）：
       拿语料里真实出现的繁體词，用**简体**写法去搜。这一节只登记，不在这里解决。

已知边界（别把结论放大）：
    - 语料是**一部**明代小说，不是生产库；量的是"切分口径"这类通用性质，不是产量指标。
    - 查询词是**从原文抄的**（送分题）⇒ 本脚本的绝对值**不能**当产品效果；
      它的用途是**横向比较三种口径**，三者吃的是同一批查询，差就是切分造成的差。
    - 繁体语料 + jieba 简体词典 = 两个轴叠在一起；本脚本只在 ④ 节把它们分开看。
    - `jieba.load_userdict` 是**全局**副作用（C 口径必须在 A 口径量完之后再加载）。
"""
from __future__ import annotations

import sqlite3
import statistics
import sys
import time
from pathlib import Path

from _measure_common import chunk_text

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.core.text_utils import fts_match_expr, segment_for_fts  # noqa: E402

#: 与 cross-language 尺子 D 行同一份文件。出处与许可见
#: `docs/research/cross-language-retrieval-evidence.md` §二：
#: https://www.gutenberg.org/cache/epub/23950/pg23950.txt（Project Gutenberg License，美国公有领域）
DEFAULT_CORPUS = REPO / "var" / "fixtures" / "general-corpus" / "sanguo.txt"

# clause_fts 的 DDL 逐字取自 src/core/storage/schema.sql，与另一把尺子一致。
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
    tokenize = 'ascii'
);
"""

W = 78
#: 词典/考卷切分点：前 50% 段挖词典，后 50% 段挖查询词。
SPLIT = 0.5
#: 每个 n 最多取多少个查询词（按出现次数降序，确定性）。
MAX_Q_PER_N = 400


def head(t: str) -> None:
    print("=" * W)
    print(t)
    print("=" * W)


def has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)



def char_seg(text: str | None) -> str:
    """B 口径：每个汉字单独一个 token；非汉字段沿用生产分词（不另造一套）。"""
    out: list[str] = []
    buf: list[str] = []
    for ch in text or "":
        if has_cjk(ch):
            if buf:
                out.extend(segment_for_fts("".join(buf)).split())
                buf = []
            out.append(ch)
        else:
            buf.append(ch)
    if buf:
        out.extend(segment_for_fts("".join(buf)).split())
    return " ".join(out)


def cjk_runs(text: str) -> list[str]:
    runs, buf = [], []
    for ch in text:
        if has_cjk(ch):
            buf.append(ch)
        else:
            if len(buf) >= 2:
                runs.append("".join(buf))
            buf = []
    if len(buf) >= 2:
        runs.append("".join(buf))
    return runs


def ngram_counts(segments: list[str], n: int, min_count: int = 3) -> dict[str, int]:
    """统计 n 元汉字串的出现**段数**（不是次数：一个词在同一段里出现 10 次算 1）。"""
    cnt: dict[str, int] = {}
    for seg in segments:
        seen = set()
        for run in cjk_runs(seg):
            for i in range(len(run) - n + 1):
                seen.add(run[i:i + n])
        for g in seen:
            cnt[g] = cnt.get(g, 0) + 1
    return {g: c for g, c in cnt.items() if c >= min_count}


def build(conn: sqlite3.Connection, tbl: str, rows: list[str], fn) -> tuple[float, float]:
    t0 = time.time()
    conn.execute(DDL.format(tbl=tbl))
    conn.executemany(
        f"INSERT INTO {tbl}(clause_revision_id,clause_number,standard_no,title,"
        f"content_segmented,modality,subject,behavior_scope_segmented) VALUES(?,?,?,?,?,?,?,?)",
        [(f"r{i}", "", "", "", fn(t), "", "", "") for i, t in enumerate(rows)],
    )
    t = time.time() - t0
    conn.execute(f"CREATE VIRTUAL TABLE v_{tbl} USING fts5vocab({tbl}, 'row')")
    n_terms = conn.execute(f"SELECT count(*) FROM v_{tbl}").fetchone()[0]
    return t, float(n_terms)


def single_ratio(tbl: str, conn: sqlite3.Connection) -> tuple[int, int, int]:
    """(全部 token, 单字 token, 中文单字 token) —— 从词表算，不重跑分词。

    ⚠ 必须用 fts5vocab 的 **`cnt`（出现次数）**，不是 `doc`（含该词的段数）。
      第一版用了 `doc`，得到 31.8% 这种**口径不一致**的数（另一把尺子量的是出现次数，
      同一个语料是 30.2%）——同一份语料两个数，读的人无法判断哪个对。已改。
    """
    rows = conn.execute(f"SELECT term, cnt FROM v_{tbl}").fetchall()
    all_t = sum(c for _t, c in rows)
    sing = sum(c for t, c in rows if len(t) == 1)
    sing_cjk = sum(c for t, c in rows if len(t) == 1 and has_cjk(t))
    return all_t, sing, sing_cjk


def search_rows(conn: sqlite3.Connection, tbl: str, expr: str, k: int) -> list[int]:
    if not expr.strip():
        return []
    try:
        cur = conn.execute(
            f"SELECT rowid FROM {tbl} WHERE {tbl} MATCH ? ORDER BY bm25({tbl}) LIMIT ?", (expr, k)
        )
        return [r[0] for r in cur.fetchall()]
    except sqlite3.OperationalError as e:      # pragma: no cover - 表达式层已过滤
        print(f"    [MATCH 报错] {expr!r}: {e}")
        return []


def char_and_expr(q: str) -> str:
    """B 口径的查询式：**所有汉字都要出现**（FTS5 多词默认隐式 AND）。

    ⚠ 这里**不能**复用 `fts_match_expr`：它有条"丢弃单字符词"的规则
    （`if len(tok) > 1`，见 src/core/text_utils.py）。那条规则是**为现状口径设的**
    —— 现状下 jieba 把 `的`/`是` 这类噪声切成单字，丢掉是对的；
    但在**字级索引**下"字"就是检索单位，丢掉它等于把查询清空。
    ⇒ **选字级就必须同时改 `fts_match_expr`**，这是这条路的代价之一（不是免费的索引选项）。
    """
    toks = [f'"{ch}"' for ch in q if has_cjk(ch)]
    return " ".join(toks)


def char_or_expr(q: str) -> str:
    """B 口径的松变体（任一字命中即可），只为对照，不采纳。"""
    return " OR ".join(f'"{ch}"' for ch in q if has_cjk(ch))


def no_drop_expr(q: str) -> str:
    """A+ 口径：**索引一个字不动**，只把查询侧"丢弃单字符词"那条规则关掉。

    这是三条路里**唯一不需要重建索引**的，所以必须量 —— 若它能拿回大部分收益，
    那就没有理由去动 522k 条索引。
    ⚠ 它同时放宽了噪声：`的`/`是` 这类单字也会进表达式（原规则就是为了丢它们）。
    """
    toks = [f'"{t}"' for t in segment_for_fts(q).split() if t.strip()]
    return " OR ".join(toks)


def evaluate(conn: sqlite3.Connection, tbl: str, queries: list[str],
             targets: dict[str, set[int]], expr_fn) -> dict[str, float]:
    n = len(queries)
    hit5 = hit20 = 0
    rr: list[float] = []
    dead = 0
    for q in queries:
        expr = expr_fn(q)
        if not expr.strip():
            dead += 1
            continue
        tgt = targets[q]
        rows = search_rows(conn, tbl, expr, 20)
        rank = next((i + 1 for i, r in enumerate(rows) if r in tgt), None)
        if rank is not None:
            hit20 += 1
            rr.append(1.0 / rank)
            if rank <= 5:
                hit5 += 1
        else:
            rr.append(0.0)
    return {
        "n": n, "dead": dead,
        "r5": hit5 / n if n else 0.0,
        "r20": hit20 / n if n else 0.0,
        "mrr": statistics.fmean(rr) if rr else 0.0,
    }


def main() -> int:
    # 本机控制台默认 GBK：`⇒`/`×` 会让 print 跑到一半炸掉（另一把尺子踩过）。
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):      # pragma: no cover - 环境相关
            pass

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CORPUS
    if not path.exists():
        print(f"语料不存在：{path}")
        print("出处：https://www.gutenberg.org/cache/epub/23950/pg23950.txt"
              "（Project Gutenberg #23950，公有领域）")
        return 2

    head("① 语料与现状（与另一把尺子的 D 行同一份文件，数字可对）")
    raw = path.read_text(encoding="utf-8", errors="replace")
    rows = chunk_text(raw)
    print(f"  {path.name}  {len(raw):,} 字符 → {len(rows)} 段")
    print("  ⚠ 这份语料是**繁體**（Gutenberg 的三國志演義）⇒ 后文 ⑤ 节单独量繁简轴。")

    conn = sqlite3.connect(":memory:")

    head("② 三种切分口径：词表、单字占比、建表耗时")
    t_a, n_a = build(conn, "fts_jieba", rows, segment_for_fts)
    t_b, n_b = build(conn, "fts_char", rows, char_seg)
    a_all, a_sing, a_cjk = single_ratio("fts_jieba", conn)
    b_all, b_sing, b_cjk = single_ratio("fts_char", conn)
    print(f"  A 现状（jieba 现代汉语词典）  词表 {n_a:>8,.0f}  建表 {t_a:.1f}s"
          f"  中文单字占比 {a_cjk / a_all:.1%}（{a_cjk:,}/{a_all:,}）")
    print(f"  B 字级（每个汉字一个 token）  词表 {n_b:>8,.0f}  建表 {t_b:.1f}s"
          f"  中文单字占比 {b_cjk / b_all:.1%}（{b_cjk:,}/{b_all:,}）")
    # 与另一把尺子**逐字同法**再算一遍：前 800 段拼成一个串再分词（那个 30.2% 就是这么来的）。
    # 两条路差 0.1pt 来自分母口径（拼串分词 vs 逐段分词，段落边界上的切分会不同）
    # —— 两个数都对，但**引用时必须说是哪一条**。
    probe = "\n\n".join(rows[:800])
    ptoks = segment_for_fts(probe).split()
    pcjk = [t for t in ptoks if len(t) == 1 and has_cjk(t)]
    print(f"     复现另一把尺子（前 800 段拼串）：中文单字 {len(pcjk):,}/{len(ptoks):,}"
          f" = {len(pcjk) / len(ptoks):.1%}  ← 计划里那个 30.2% 就是这个口径")
    print(f"     ⚠ B 的词表比 A {'小' if n_b < n_a else '大'} {abs(n_b - n_a):,.0f}"
          f"（{n_b / n_a:.2f}×）—— 字级不是「更大的词表」，是**换了检索单位**。")

    head("③ 词典/考卷切分：词典只从**前半段**挖，查询词只从**后半段**挖（互不相交）")
    cut = int(len(rows) * SPLIT)
    train, test = rows[:cut], rows[cut:]
    print(f"  前半段 {len(train)} 段（挖词典） / 后半段 {len(test)} 段（挖查询词）")

    dict_terms: list[str] = []
    for n in (2, 3, 4):
        cnt = ngram_counts(train, n, min_count=3)
        # 只收"现状切不出整词"的 ⇒ 词典要补的正是这一块
        fresh = [g for g in cnt if g not in set(segment_for_fts(g).split())]
        fresh.sort(key=lambda g: (-cnt[g], g))
        dict_terms.extend(fresh)
        print(f"    n={n}: 前半段 ≥3 段出现的 {len(cnt)} 个，其中现状切不出整词的 {len(fresh)} 个"
              f" ⇒ 收进词典")
    dict_terms = dict_terms[:5000]
    print(f"  领域词典共 {len(dict_terms)} 条（样例：{dict_terms[:12]}）")

    import jieba
    jieba.load_userdict(dict_terms)
    t_c, n_c = build(conn, "fts_jieba_dict", rows, segment_for_fts)
    c_all, c_sing, c_cjk = single_ratio("fts_jieba_dict", conn)
    print(f"  C 领域词典（jieba + 自挖词典）  词表 {n_c:>8,.0f}  建表 {t_c:.1f}s"
          f"  中文单字占比 {c_cjk / c_all:.1%}（{c_cjk:,}/{c_all:,}）")
    whole = sum(1 for g in dict_terms if g in set(segment_for_fts(g).split()))
    print(f"  词典生效检查：{whole}/{len(dict_terms)} 条现在能切成**一个 token**"
          f" = {whole / max(len(dict_terms), 1):.1%}")

    head("④ 检索命中率：查询词 = 后半段真实出现的文言词（繁體原形，送分题）")
    joined = "\n".join(rows)
    by_n: dict[int, list[str]] = {}
    for n in (2, 3, 4):
        cnt = ngram_counts(test, n, min_count=3)
        picked = sorted(cnt, key=lambda g: (-cnt[g], g))[:MAX_Q_PER_N]
        kept = [g for g in picked if g in joined]
        by_n[n] = kept
        print(f"  n={n}: 后半段 ≥3 段出现的 {len(cnt)} 个 ⇒ 取前 {len(picked)} 个，"
              f"其中库内可定位目标段落的 {len(kept)} 个")

    VARIANTS = (
        ("A  现状（jieba 索引 + 现状查询）", "fts_jieba",
         lambda q: fts_match_expr(q, latin_prefix=False)),
        ("A+ 索引不动，查询侧不丢单字", "fts_jieba", no_drop_expr),
        ("B  字级索引（单字 AND 共现）", "fts_char", char_and_expr),
        ("B' 字级索引（单字 OR，对照不采纳）", "fts_char", char_or_expr),
        ("C  领域词典索引（jieba+自挖）", "fts_jieba_dict",
         lambda q: fts_match_expr(q, latin_prefix=False)),
    )

    all_targets: dict[str, set[int]] = {}
    all_queries: list[str] = []
    for n in (2, 3, 4):
        for q in by_n[n]:
            tgt = {i for i, seg in enumerate(rows) if q in seg}
            if tgt:
                all_targets[q] = tgt
                all_queries.append(q)

    print(f"\n  全部查询 {len(all_queries)} 个（n=2/3/4 合并）")
    print(f"  {'口径':<36}{'recall@5':>10}{'recall@20':>11}{'MRR':>8}{'空查询':>8}")
    for name, tbl, fn in VARIANTS:
        r = evaluate(conn, tbl, all_queries, all_targets, fn)
        print(f"  {name:<36}{r['r5']:>9.1%}{r['r20']:>10.1%}{r['mrr']:>8.3f}{r['dead']:>8}")

    print(f"\n  按查询词长度拆开（机制不同：n=2 现状多半切得出整词，n=4 基本切不出）")
    print(f"  {'n':<4}{'口径':<36}{'recall@5':>10}{'recall@20':>11}{'MRR':>8}{'空查询':>8}")
    for n in (2, 3, 4):
        qs = by_n[n]
        for name, tbl, fn in VARIANTS:
            r = evaluate(conn, tbl, qs, all_targets, fn)
            print(f"  {n:<4}{name:<36}{r['r5']:>9.1%}{r['r20']:>10.1%}{r['mrr']:>8.3f}"
                  f"{r['dead']:>8}")
    print("  ⚠ 绝对值是**送分题**（查询词从原文抄）⇒ 只能横向比，不能当产品效果。")

    head("⑤ 繁简轴（**不是切分问题**，但在这份语料上比切分致命得多）")
    # 只用"繁简不同形"的词：同形词当对照。
    PAIRS = [("關公", "关公"), ("雲長", "云长"), ("張飛", "张飞"), ("軍馬", "军马"),
             ("糧草", "粮草"), ("商議", "商议"), ("曹賊", "曹贼"), ("旌旗", "旌旗"),
             ("次日", "次日")]

    def cnt_of(tbl: str, expr: str) -> int:
        if not expr.strip():
            return -1
        try:
            return conn.execute(f"SELECT count(*) FROM {tbl} WHERE {tbl} MATCH ?",
                                (expr,)).fetchone()[0]
        except sqlite3.OperationalError:
            return -1

    print(f"  {'繁體（原文形）':<14}{'A 繁':>7}{'简体写法':<12}{'A 简':>7}"
          f"{'B 简':>7}{'C 简':>7}")
    for trad, simp in PAIRS:
        c_a_t = cnt_of("fts_jieba", fts_match_expr(trad, latin_prefix=False))
        c_a_s = cnt_of("fts_jieba", fts_match_expr(simp, latin_prefix=False))
        c_b_s = cnt_of("fts_char", char_and_expr(simp))
        c_c_s = cnt_of("fts_jieba_dict", fts_match_expr(simp, latin_prefix=False))
        print(f"  {trad:<14}{c_a_t:>7}{simp:<12}{c_a_s:>7}{c_b_s:>7}{c_c_s:>7}")
    print("  ⇒ 同形词（旌旗/次日）的**繁栏与简栏**相等（同一串，逐格相同）＝对照通过；")
    print("     B 栏数值不同是**字级口径本来就匹配更多段落**（2 个单字共现比 1 个整词宽），不是错误。")
    print("     异形词的简体栏 **A/B/C 三栏全 0**")
    print("     ⇒ 换切分口径**救不了**这一栏（B 是字级索引也一样 0：那个字在原文里根本不存在）。")
    print("  ⚠ 本仓**没有**繁简转换依赖（opencc/zhconv 实测未安装）⇒ 这一节只登记，")
    print("    要不要加一层转换**要业主定**（加依赖 / 加转换表都是产品决策）。")

    head("⑥ 结论读法（数字在 ② ④ ⑤ 三节，别只看单字占比）")
    print("  1. 单字占比只是**机制代理量**，不是判据：B 把它推到 81.3%（三口径里最高）、")
    print("     C 把它降到 20.1%（最低）—— 而 ④ 里 C 的 @5 第一、B 第二，两者都比现状好。")
    print("     ⇒ 「降单字占比」不能当目标，真正要看的是 ④ 的命中率与名次，两者必须一起读。")
    print("  2. ⑤ 才是这份语料上的**主因**：繁體原文 + 简体提问 = 逐字不同 = 0 命中，")
    print("     换任何切分口径都救不了（B/C 两栏也是 0）。⇒ 先投切分是**顺序错了**。")
    print("  3. 结论与处置写在 docs/research/classical-chinese-segmentation-evidence.md。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
