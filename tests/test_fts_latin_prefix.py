"""P3.1：英文词形变化那道缺口的判据（提问侧"词干 + 前缀"，**索引零改动**）。

**这个文件管什么**：
* 中英混排下，**中文与标准号/标识符一个字节都不许变**（这是能不能默认开的前提）；
* 英文词形变化真的能对上了 —— **用真 FTS5 表端到端验**，不是只看表达式长什么样；
* 反例：全大写缩写、太短的虚词、带数字的标识符**都不许**被扩写。

**为什么必须有**（2026-09-25 实测，`scripts/measure-cross-language-fts.py`）：
生产索引 `tokenize='ascii'` 不做词形还原。中文没有词形变化，所以这个缺口
**在中文库上永远不会自己暴露**；换成英文开发文档立刻暴露——同一段只含
`extinguisher`，拿 `extinguishers` 去搜，命中 **0/291 = 0.0%**。
提问侧改成"词干 + 前缀"后 **285/291 = 97.9%**，索引一个字不用重建。
代价是候选池**中位放大 3.3 倍**，所以扩写条件写得很窄（见 `_latin_prefix_token`）。
"""
from __future__ import annotations

import sqlite3

from src.core.text_utils import fts_match_expr

# ── 一、中文与标识符：新旧口径必须**逐字节相同** ────────────────────────────
CJK_QUERIES = [
    "动火作业怎么分级",
    "GB 30871-2022",
    "安全帽的佩戴要求",
    "个人信息保护法 第四十九条",
    "住宿标准是多少",
    "危险化学品储罐区与明火点的距离",
]

#: 走完规则 3 会得到**空表达式**的查询（全是单字符 token）。
#: 这是 docstring 里**早就写明的已知代价**，由调用方 `if not expr.strip(): return []` 兜。
#: 单独列出来，免得混在上面的"正常查询"里让断言互相打架（**本条用例第一版就是这么红的**）。
EMPTY_EXPR_QUERIES = ["5.2.3", "a", "", None]


def test_chinese_and_standard_numbers_are_byte_identical_under_both_modes():
    """默认口径（开前缀）**不许**动到中文查询与标准号查询。

    这是"能不能默认开"的**唯一前提**：你那 52 万条中文条款的检索行为不能变。
    """
    for q in CJK_QUERIES:
        assert fts_match_expr(q, latin_prefix=True) == fts_match_expr(q, latin_prefix=False), q


def test_chinese_expression_contains_no_prefix_star():
    for q in CJK_QUERIES:
        assert "*" not in fts_match_expr(q), q


# ── 二、英文词形变化：拿真 FTS5 表端到端验 ─────────────────────────────────
def _table_with(doc: str) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE VIRTUAL TABLE t USING fts5(body, tokenize='ascii')")
    conn.execute("INSERT INTO t(body) VALUES(?)", (doc,))
    return conn


def _matches(conn: sqlite3.Connection, expr: str) -> bool:
    row = conn.execute("SELECT rowid FROM t WHERE t MATCH ?", (expr,)).fetchone()
    return row is not None


def test_english_inflection_is_findable_only_with_the_prefix_mode():
    """同段只有 `extinguisher`，用 `extinguishers` 搜：
    旧口径**必空**、新口径**必中** —— 两个方向都要断言，只断言"新口径能中"是半个判据。"""
    conn = _table_with("The extinguisher shall be inspected monthly.")
    old = fts_match_expr("extinguishers", latin_prefix=False)
    new = fts_match_expr("extinguishers", latin_prefix=True)
    assert not _matches(conn, old), f"旧口径本不该命中，实测命中了：{old!r}"
    assert _matches(conn, new), f"新口径没命中：{new!r}"


def test_english_plural_and_gerund_and_past_are_all_covered():
    """三个方向各测一次（复数 / 进行式 / 过去式），别只测一个就下"英文能搜了"的结论。"""
    cases = [
        ("The valve is closed during maintenance.", "valves"),
        ("The system is testing the pump.", "tested"),
        ("The operator inspected the vessel.", "inspecting"),
    ]
    for doc, q in cases:
        conn = _table_with(doc)
        assert _matches(conn, fts_match_expr(q)), f"{q!r} 没命中 {doc!r}"


def test_the_reverse_direction_also_works():
    """文档是**长形**、提问是**词干形**时也要能中（前缀查询天生覆盖这一向）。"""
    conn = _table_with("All extinguishers must be tagged.")
    assert _matches(conn, fts_match_expr("extinguisher"))


# ── 三、反例：不该被扩写的都不许扩写 ────────────────────────────────────────
def test_acronyms_and_identifiers_are_not_expanded():
    """全大写缩写、哈希、配置键都不许被改写（`porter` 在这些东西上是**破坏性**的，
    实测原词存活率只有 61.6%，消失的正是哈希/编号/配置键）。"""
    for q in ["ISO 9001", "API KEY ROTATION", "SHA256",
              "0116b1f89c05221d56b0ba35c83d302bf4857bc7277d247e9bbaf74b27d2c66e"]:
        assert fts_match_expr(q, latin_prefix=True) == fts_match_expr(q, latin_prefix=False), q


def test_short_function_words_are_not_expanded():
    """`the`/`and`/`to` 这类虚词做前缀查询只会灌候选池，判据里明确放过它们。"""
    for q in ["the and to of", "for"]:
        assert fts_match_expr(q, latin_prefix=True) == fts_match_expr(q, latin_prefix=False), q


def test_short_stems_are_not_expanded():
    """**词干太短**的不扩写（词面够长也不行）。

    复核 2026-09-25 打回时实测：第一版只判**词面**长度，于是
    `uses`→`"us"*`、`being`→`"be"*`、`harness`→`"har"*` 全都放过去了；
    在真语料上 `be*` 把候选池放大 **35.8×**、`us*` **8.0×**。
    现在词干长度下限 4（`_MIN_STEM`）。⚠ 词面 ≥4 但词干 <4 的形态正是本条的靶子。
    """
    for q in ["uses", "using", "being", "doing", "harness", "harnesses", "opted", "ties"]:
        assert fts_match_expr(q, latin_prefix=True) == fts_match_expr(q, latin_prefix=False), q


def test_internal_capitals_are_not_expanded():
    """**有内部大写**的标识符/缩写不扩写（`RoHS`/`camelCase`/`backgroundColor`/`MAYBECAPS`）。

    复核打回时实测：第一版用"非全大写"，挡不住**混合大小写**这一整类。
    """
    for q in ["RoHS", "camelCase", "backgroundColor", "MAYBECAPS mixedCASE",
              "API KEY ROTATION", "ISO 9001"]:
        assert fts_match_expr(q, latin_prefix=True) == fts_match_expr(q, latin_prefix=False), q


def test_sentence_initial_capital_is_still_expanded():
    """句首大写的普通词**要**放行（否则英文提问一半都白搭）。"""
    assert fts_match_expr("Extinguishers shall be tagged") != \
        fts_match_expr("Extinguishers shall be tagged", latin_prefix=False)
    assert '"extinguish"*' in fts_match_expr("Extinguishers shall be tagged")


def test_known_false_hit_proper_noun_is_pinned():
    """**钉住一个已知的误命中，不许它悄悄变化。**

    `Redis` 与 `Extinguishers` 的大小写形态**无法区分**（都是首字母大写），
    所以形状判据挡不住它：`Redis` → `"redi"*`，会命中 `redirect`
    （复核 2026-09-25 给了可复现的例子）。**这是已知边界，不是没发现。**
    本条把现状钉住：哪天规则变了（变好或变坏），这里会红，逼人重新评估而不是放任漂移。
    """
    expr = fts_match_expr("Redis 缓存怎么配")
    assert '"redi"*' in expr, "规则变了：请重新评估 'Redis→redi* 命中 redirect' 这个已知边界"


def test_mixed_query_keeps_chinese_intact_and_expands_only_the_english_word():
    expr = fts_match_expr("灭火器的 extinguishers 要求")
    assert '"灭火器"' in expr or "灭火器" in expr
    assert "extinguish" in expr
    assert "*" in expr
    # 中文那部分必须与旧口径一致（逐词比，不比整串，因为英文词确实变了）
    old = fts_match_expr("灭火器的 extinguishers 要求", latin_prefix=False)
    assert set(old.split(" OR ")) - set(expr.split(" OR ")) == {'"extinguishers"'}
    assert set(expr.split(" OR ")) - set(old.split(" OR ")) == {'"extinguish"*'}


# ── 四、表达式本身不许把 FTS5 语法搞坏 ─────────────────────────────────────
def test_expression_is_always_valid_fts5_syntax():
    """口径错的典型症状是**静默无命中**（报错被兜底 except 吞掉），
    所以这里直接对真表跑一遍，语法错就抛出来。

    ⚠ **空表达式是例外，而且它是"调用方的义务"、不是本函数的保证**：
    `'5.2.3'`／`'a'`／空串／`None` 走完规则 3 会得到**空串**，空串交给 FTS5
    就是 `syntax error near ""`（**本条用例第一版就是这么红的，留痕**）。
    本函数 docstring 的规则 3 早写明这个已知代价，各调用方都靠
    `if not expr.strip(): return []` 兜住。所以这里分开断言：
    非空 ⇒ 必须语法合法；空 ⇒ 明确记下"必须由调用方兜"。
    """
    conn = _table_with("placeholder text")
    non_empty = CJK_QUERIES + ["extinguishers", "ISO 9001", "GB 30871-2022 fire"]
    for q in non_empty:
        expr = fts_match_expr(q)
        assert expr.strip(), q
        conn.execute("SELECT rowid FROM t WHERE t MATCH ?", (expr,)).fetchall()

    empties = [q for q in EMPTY_EXPR_QUERIES if not fts_match_expr(q).strip()]
    assert len(empties) == len(EMPTY_EXPR_QUERIES), "前提变了：这几个查询本该全部产出空表达式"
    import pytest
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("SELECT rowid FROM t WHERE t MATCH ?", ("",)).fetchall()


def test_prefix_star_only_ever_follows_a_quoted_token():
    """`"abc"*` 是合法前缀查询；裸 `*` 或 `abc*`（未加引号）在本仓口径里不出现。"""
    for q in ["extinguishers ISO 9001 GB 30871-2022 动火作业", "testing testing"]:
        expr = fts_match_expr(q)
        for part in expr.split(" OR "):
            assert not part.endswith("*") or part[:-1].endswith('"'), part


# ── 五、多线程：这是生产真正跑它的方式 ─────────────────────────────────────
def test_stem_helper_is_usable_from_many_threads():
    """**判据（不是普通用例）**：本函数由 FastAPI 的**同步路由**调用，那些路由跑在
    AnyIO 的**工作线程池**里 ⇒ 必须能被多个线程同时调用。

    ⚠ 这条是**补写的**：第一版实现用一个模块级 SQLite 连接取词干，
    8 线程跑 200 次调用**第二次就炸**——
    `SQLite objects created in a thread can only be used in that same thread`。
    而这类异常在生产上极可能被上层的兜底 `except` 吞成"没有命中"（静默失效），
    所以必须有一条守在这儿。现在实现改成每线程一个连接（`threading.local()`）。
    """
    import concurrent.futures as cf

    queries = ["extinguishers", "GB 30871-2022", "动火作业怎么分级",
               "testing valves", "ISO 9001", "inspected"] * 40
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        out = list(ex.map(fts_match_expr, queries))
    assert len(out) == len(queries)
    # 同一条查询在不同线程上必须给出**同一个**表达式（缓存跨线程共用，不能各算各的）
    for q in set(queries):
        exprs = {e for s, e in zip(queries, out) if s == q}
        assert len(exprs) == 1, (q, exprs)


def test_stem_helper_itself_is_thread_safe():
    """直接压那条取词干的路径（不经过 jieba），把它单独钉住。"""
    import concurrent.futures as cf

    from src.core.text_utils import _porter_stem

    words = ["extinguishers", "valves", "testing", "inspected", "configured"] * 30
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        out = list(ex.map(_porter_stem, words))
    assert len(out) == len(words)
    assert len({s for s, w in zip(out, words)}) == 5
