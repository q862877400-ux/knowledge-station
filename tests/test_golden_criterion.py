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


def test_standard_no_with_trailing_chinese_still_matches():
    """真库有 **7 篇** `standard_no` 尾部带中文（复核 2026-09-25 的 P1）。

    旧判据用「键**相等**」⇒ 这种串的 `standard_key` 退化成整串、与提问算出的键不等
    ⇒ **权重最高（2.0）的精确通道对这 7 篇整条失效**（复核实测 base 通道 A n=1 / frozen n=0）。
    修法是把判据改成「键**包含**」。本用例把"相等会失效、包含才成立"两件事一起钉住。
    """
    sno = "GB/T 27668-2023显微镜光学显微术术语(1)"
    key = standard_key("GB/T 27668-2023")
    assert key in canon_standard_no(sno)          # 包含 ⇒ 成立
    assert standard_key(sno) != key               # 相等 ⇒ 正是旧判据失效的原因


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
