"""钉住评测器的命中判据：必须是 **(标准号, 条款号) 对**，不能只比条款号。

为什么要单独一条（2026-09-25 独立复核 P1）：这个判据改动**原先零测试覆盖**。
全仓唯一按"只比 clause_number"断言的检索判据在 `tests/test_golden_set.py`，
而它是一道**三重死闸**——① `skipif` 写成 `not (… and False)`（恒真、永远 skip）；
② `tests/conftest.py` 的 `_isolate_data_dir` 是**会话级 autouse**，把数据目录指向空临时库，
所以它 `init_schema()` 建出来的永远是空库、`has_gb` 恒 False ⇒ 必然 skip；
③ 它被同时登记进 `scripts/gates-baseline.json` 的 `environmental_skip_nodeids` 与 `skip_nodeids`。
⇒ **它从不运行**，本判据此前没有任何东西守着。

本文件只做**纯函数级**断言：不起库、不检索、不联网、不写盘。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.run_benchmark import _hit  # noqa: E402
from src.core.retrieval.hybrid_engine import _STD_IN_QUERY_RE  # noqa: E402
from src.core.text_utils import canon_standard_no, standard_key  # noqa: E402


# ── 判据本体 ────────────────────────────────────────────────────────────────

def test_same_clause_number_in_another_standard_is_not_a_hit():
    """**核心用例**：同一条款号、不同标准 ⇒ 必须判不中。这正是旧判据的那个洞。"""
    returned = [("55037-2022", "3.1")]      # 搜回来的是 GB 55037-2022 的 3.1
    expected = {("3028-2008", "3.1")}       # 期望的是 AQ 3028-2008 的 3.1
    assert _hit(returned, expected) is False


def test_matching_pair_is_a_hit():
    assert _hit([("3028-2008", "3.1")], {("3028-2008", "3.1")}) is True


def test_any_expected_answer_counts():
    """金标一条题可以有多个可接受答案，命中任一即可。"""
    assert _hit([("x-2020", "9.9"), ("3028-2008", "4.2")],
                {("3028-2008", "3.1"), ("3028-2008", "4.2")}) is True


def test_empty_expect_is_never_a_hit():
    assert _hit([("3028-2008", "3.1")], set()) is False


def test_order_of_returned_pairs_does_not_matter():
    pairs = [("a-2020", "1"), ("3028-2008", "3.1"), ("b-2021", "2")]
    assert _hit(pairs, {("3028-2008", "3.1")}) is True


# ── 标准号归一：两边都过 standard_key 之后才比 ──────────────────────────────

def test_standard_key_normalisation_equates_case_and_dashes():
    assert standard_key("AQ 3028-2008") == standard_key("aq3028\u20142008")


# ── 标准号与文档的匹配判据（**词边界包含**，第二轮复核 P0 的两侧反例）────────

def test_key_matches_standard_no_with_trailing_chinese():
    """真库 4 篇 `standard_no` 尾部带中文 ⇒ 判据必须允许"键是前缀部分"。

    旧判据用「键**相等**」⇒ 这种串的 `standard_key` 退化成整串、与提问算出的键不等
    ⇒ **权重最高（2.0）的通道 A 对这 4 篇整条失效**（复核实测 base 通道 A n=0）。
    """
    from src.core.retrieval.hybrid_engine import _std_key_hits_doc
    assert _std_key_hits_doc("5009.12-2023", "GB 5009.12-2023食品安全国家标准") is True
    assert _std_key_hits_doc("27668-2023", "GB/T 27668-2023显微镜光学显微术术语(1)") is True


def test_key_does_not_match_a_longer_number_that_merely_ends_with_it():
    """**核心反例**：裸「包含」过头——`2033-2008` 是 `GBT12033-2008` 的子串。

    第二轮复核实测端到端：提问点名 `GB/T 2033-2008`，裸包含时**第 1 名返回
    `GB/T 12033-2008`**（正是上一批要关掉的那类假命中）。数字左边界把它挡住。
    本用例在"把判据改回裸包含"的变异下**必红**。
    """
    from src.core.retrieval.hybrid_engine import _std_key_hits_doc
    assert _std_key_hits_doc("2033-2008", "GB/T 12033-2008") is False
    assert _std_key_hits_doc("247-2008", "GB/T 10247-2008") is False
    assert _std_key_hits_doc("7718-2011", "GB/T 27718-2011") is False
    # 但真正那本必须命中
    assert _std_key_hits_doc("2033-2008", "GB/T 2033-2008") is True


def test_empty_key_never_matches():
    from src.core.retrieval.hybrid_engine import _std_key_hits_doc
    assert _std_key_hits_doc("", "GB 30871-2022") is False


#: 真库实测存在的 5 组**后缀碰撞**（键是另一部标准号的子串）：
#: 这是**快照库里一对都没有**的东西 —— 快照 19 篇，真库 6,797 篇。
#: 第四轮复核的"残余 1"就是靠这个事实躲过所有测试的。
COLLISION_PAIRS = (
    ("2033-2008", "GB/T 12033-2008"),
    ("247-2008", "GB/T 10247-2008"),
    ("7718-2011", "GB/T 27718-2011"),
    ("144-2024", "GB/T 30144-2024"),
    ("151-2014", "GB/T 31151-2014"),
)


def test_row_filter_helper_is_boundary_based_not_bare_containment():
    """**打在行筛函数上**（第四轮复核的"残余 1"）。

    复核实测：把**调用点**的判据换成**裸包含**（`k in canon_standard_no(...)`）时，
    全部测试**仍然全绿** —— 因为①纯函数用例测的是 `_std_key_hits_doc`、绕开了调用点；
    ②**快照库里一对后缀碰撞都没有**，而真库有 5 对。
    ⇒ 这个变异在真库上会**真的放回第二轮 P0-2 那类假命中**，两把尺子都看不见。
    本用例用真库那 5 对（写成字面量，不依赖库）把这一层钉死。
    """
    from src.core.retrieval.hybrid_engine import _rows_matching_standard_keys
    for key, other in COLLISION_PAIRS:
        # 裸包含会在这里误留下另一部标准；词边界必须把它剔掉
        assert _rows_matching_standard_keys([("cid", other)], {key}) == [], \
            f"行筛失效：{key} 不该命中 {other}"
        # 真身仍要留下
        real = f"GB/T {key}"
        assert _rows_matching_standard_keys([("cid", real)], {key}) == [("cid", real)]
    # 认不出标准号 ⇒ 原样返回（历史行为一字不改）
    rows = [("cid", "x")]
    assert _rows_matching_standard_keys(rows, set()) == rows


def test_known_standard_keys_drops_what_the_library_does_not_have():
    """**库里没有的标准号不许筛**（否则会把权重最高的通道 A 整条清空）。

    `FY2021-2022` 这种形态正则拦不住（见下一条用例），真正的防线是这道守卫。
    """
    from src.core.retrieval.hybrid_engine import _known_standard_keys
    lib = ["GB 30871-2022", "AQ 3028-2008"]
    assert _known_standard_keys({"2021-2022", "ABC123-4567"}, lib) == set()
    assert _known_standard_keys({"30871-2022"}, lib) == {"30871-2022"}


def test_unknown_standard_in_query_behaves_exactly_like_no_standard(tmp_path):
    """**打在调用点上**：删掉引擎里那道守卫，本用例会红。

    为什么需要它：上面几条只测纯函数——第二轮复核实测"把存在性守卫整块删掉"时
    测试**全绿**（守卫的调用点零覆盖）。这条用真检索比对两次返回，
    守卫没了就会让第二位提问的精确通道被清空 ⇒ 两次返回不再相同。
    """
    import shutil

    import pytest

    from src.core.retrieval.hybrid_engine import perform_hybrid_search, set_db_override
    from src.core.storage.sqlite_db import get_db_connection, load_vec_extension

    snap = ROOT / "eval" / "golden" / "knowledge-snapshot.db"
    if not snap.exists():
        pytest.skip("快照库缺失（先跑 eval/golden/build_golden.py）")
    db = tmp_path / "snap.db"
    shutil.copy2(snap, db)          # 拷副本：get_db_connection 会写 WAL，别脏了仓库
    set_db_override(str(db))
    try:
        conn = get_db_connection(db)
        load_vec_extension(conn)
        # ⚠ **只留精确通道**（`channels=["exact"]`）：否则加了 "ZZ 9999-2099" 之后
        # FTS/向量通道拿到的查询串也变了，返回本来就会不同 —— 那样测的就不是守卫了。
        # （第一版就是这么写错的：两条提问的 token 不同 ⇒ 不隔离通道 ⇒ 假红。）
        plain = [r.clause_revision_id for r in
                 perform_hybrid_search("第3.1条", top_k=10, channels=["exact"], rerank=False)]
        weird = [r.clause_revision_id for r in
                 perform_hybrid_search("ZZ 9999-2099 第3.1条", top_k=10,
                                       channels=["exact"], rerank=False)]
        assert plain, "哨兵：前一次检索不该为空（否则本用例没走到被测路径）"
        assert weird == plain, "库里没有的标准号不该改变检索结果（守卫失效了？）"
    finally:
        set_db_override(None)


def test_row_filter_actually_scopes_to_the_named_standard(tmp_path):
    """**行筛**本身也要有覆盖（第三轮复核的变异 C 盲区）。

    上面那条用例打的是**守卫**（"库里没有 ⇒ 不筛"）。复核实测：把守卫**与行筛一起**删掉时，
    它**全绿** —— 因为那时 `want_keys` 非空却没有任何过滤，两次检索又变得相同。
    本用例直接把行筛钉死：**点名一部标准，返回里就不许出现别的标准**。

    会空转的情形（快照里没有跨标准重号的条款）已用 `skip` 明确挡出来，不静默通过。
    """
    import shutil

    import pytest

    from src.core.retrieval.hybrid_engine import perform_hybrid_search, set_db_override
    from src.core.storage.sqlite_db import get_db_connection, load_vec_extension

    snap = ROOT / "eval" / "golden" / "knowledge-snapshot.db"
    if not snap.exists():
        pytest.skip("快照库缺失（先跑 eval/golden/build_golden.py）")
    db = tmp_path / "snap.db"
    shutil.copy2(snap, db)
    set_db_override(str(db))
    try:
        conn = get_db_connection(db)
        load_vec_extension(conn)
        # 找一个**至少在 2 部标准里都出现**的条款号——否则"只返回点名那本"会空转成立
        row = conn.execute(
            "SELECT cr.clause_number FROM clause_revision cr"
            " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
            " GROUP BY cr.clause_number"
            " HAVING count(DISTINCT dm.standard_no) >= 2 LIMIT 1").fetchone()
        if not row:
            pytest.skip("快照库里没有跨标准重号的条款 ⇒ 本用例会空转，显式跳过")
        num = row[0]
        std = conn.execute(
            "SELECT dm.standard_no FROM clause_revision cr"
            " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
            " WHERE cr.clause_number = ? LIMIT 1", (num,)).fetchone()[0]
        res = perform_hybrid_search(f"{std} 第{num}条", top_k=50,
                                    channels=["exact"], rerank=False)
        # ⚠ **第二个哨兵**（第四轮复核的"残余 2"）：不点名标准时，该条款号必须**真的跨多部标准**
        # ——否则本用例的鉴别力会依赖 `top_k` 的大小：`top_k=1` 时"只返回点名那部"**恒真**，
        # 删掉行筛也照样全绿（复核实测 TOPK1+A / TOPK1+C 都是 15 passed）。
        un = perform_hybrid_search(f"第{num}条", top_k=50, channels=["exact"], rerank=False)
        un_stds = {r.standard_no for r in un}
        assert len(un_stds) >= 2, (
            f"哨兵：条款号 {num} 在不点名标准时应跨多部标准，实得 {un_stds}"
            " ⇒ 本用例会因 top_k 变小而恒真")
        assert res, f"哨兵：点名 {std} 第{num}条 不该返回空（用例没走到被测路径？）"
        got = {r.standard_no for r in res}
        assert got == {std}, f"行筛失效：点名 {std} 却返回了 {got}"
    finally:
        set_db_override(None)



# ── 从提问里认标准号的正则 ─────────────────────────────────────────────────

def test_regex_finds_real_standard_numbers():
    assert _STD_IN_QUERY_RE.findall("查 AQ 3028-2008 第3.1条") == ["AQ 3028-2008"]
    assert _STD_IN_QUERY_RE.findall("GB/T 10029\u20142010 第3.1条") == ["GB/T 10029\u20142010"]


def test_regex_does_not_treat_clause_numbers_or_years_or_doc_numbers_as_standards():
    """条款号 / 年份 / 文号 / 表号 / 日期区间都不许被当成标准号。"""
    for text in ("见 5.2.3 的规定", "2022年发布", "2021年规划财务工作要点",
                 "见附件 A1-2020 的第3.1条", "GB 5-2022 第5.2条"):
        assert _STD_IN_QUERY_RE.findall(text) == [], f"不该认出来：{text!r}"


def test_regex_alone_is_not_the_defence_for_lookalike_tokens():
    """**诚实登记**：`FY2021-2022` 这种"字母+4位数字+连字符+4位数字"**形态上确实像**标准号，
    本正则拦不住它。真正的防线不在正则，而在 `hybrid_engine` 通道 A 里的
    **"必须先在 `doc_meta` 里验证这部标准真的存在，否则不筛"**那道闸。
    这条用例把"正则不是防线"钉成事实，防以后有人误以为收紧正则就够了。"""
    assert _STD_IN_QUERY_RE.findall("FY2021-2022 第5.2条") == ["FY2021-2022"]
