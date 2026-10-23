"""`_standard_body` / `_std_body_hits` 的单元判据（2026-10-23 修跨标准误命中时补）。

## 为什么单独测这两个纯函数

`resolve_clause` 的年份宽容兜底原来用 `re.search(r"(\\d{4,5})", ...)` ——
它**没有前缀约束**，先命中 4 位年份 ⇒ `GBZ 188-2025` 抽出 `2025`
⇒ 兜底 `LIKE '%2025%'` ⇒ 串到 `GB 6675.2-2025`（玩具标准）。

修法拆成两个纯函数，正是为了**能被单独钉住**（原来那条逻辑埋在 `create_app`
外的一个闭包里，只能靠端到端测，成本高且覆盖不了边界）。

## 判据分三组

1. **抽对主体**：各种写法都要抽到「号」而不是「年」；
2. **抽不到就不兜**：形态不像标准号的串返回 `None`；
3. **数字边界**：`24` 不许命中 `13537`（`GBZ 24` 串到 `GB/T 13537` 的根因）。
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def body():
    from src.core.storage.clause_repo import _standard_body
    return _standard_body


@pytest.fixture()
def hits():
    from src.core.storage.clause_repo import _std_body_hits
    return _std_body_hits


# ── 组 1：抽对主体（这些是**旧实现抽错**的，每一行都对应一个真实现场）────────
@pytest.mark.parametrize("standard_no,expected", [
    # 旧实现抽到年份的（真库实测 36 部，其中 9 部会误命中）
    ("GBZ 188-2025", "188"),
    ("GBZ 1-2010", "1"),
    ("GB/T 150.4-2024", "150.4"),
    ("GB/T 1.1-2020", "1.1"),
    ("GB 150.1-2011", "150.1"),
    ("GB 6675.2-2025", "6675.2"),
    # 旧实现**碰巧对**的（不能改坏）
    ("GB 30871-2022", "30871"),
    ("GB 3608-2019", "3608"),
    ("GB 3608-2025", "3608"),
    ("AQ 3028-2008", "3028"),
    ("GB 16556-2025", "16556"),
    ("GB/T 13537-2024", "13537"),
    ("GB/T 20801.1-2020", "20801.1"),
    # 前缀带数字的（第一版正则 `[A-Z]*` 会抽成 11，已修）
    ("DB11/T 1322.1-2017", "1322.1"),
    # 团体标准（3 位序号，前导零要保住）
    ("T/CCSAS 001-2022", "001"),
    # 没有年份
    ("GB 1234", "1234"),
    # 尾部带中文（真库有 4 篇这种）
    ("GB 1234-2020 附录A", "1234"),
    # 全角
    ("GB／T 1234—2020", "1234"),
    # 小写
    ("gb 30871-2022", "30871"),
])
def test_extracts_standard_body_not_year(body, standard_no, expected):
    assert body(standard_no) == expected, (
        f"{standard_no} 应抽到 {expected}，实际 {body(standard_no)}")


# ── 组 2：抽不到就不兜（不许猜）────────────────────────────────────────
@pytest.mark.parametrize("standard_no", [
    "",
    None,
    "个人信息保护法",          # 法规名，没有标准号主体
    "中华人民共和国安全生产法",
])
def test_returns_none_when_no_body(body, standard_no):
    assert body(standard_no) is None, (
        f"{standard_no!r} 不该抽出主体（应返回 None ⇒ 调用方不兜底）")


# ── 组 3：数字边界（`24` 不许命中 `13537`）─────────────────────────────
def test_body_hits_respects_numeric_boundary(hits):
    """`GBZ 24-2025` 的主体 `24` **不许**命中 `GB/T 13537-2024`。

    这是实测踩到的第二个根因：抽对了主体（`24`）之后，
    `LIKE '%24%'` 仍会命中 `13537` 里的 `24` ⇒ 串号。
    真库 9 部受害标准里 `GBZ 24` / `GBZ 37` 就是栽在这里。
    """
    assert hits("GB/T 13537-2024", "24") is False, "24 不许命中 13537"
    assert hits("GB/T 13537-2024", "37") is False, "37 不许命中 13537"
    assert hits("GB 124-2020", "24") is False, "24 不许命中 124"
    assert hits("GB 2400-2020", "24") is False, "24 不许命中 2400"


def test_body_hits_accepts_exact_and_prefixed(hits):
    """边界判据不许把**该命中**的挡掉。"""
    assert hits("GB 24-2020", "24") is True
    assert hits("GB 240-2020", "240") is True
    assert hits("GB 188-2025", "188") is True
    assert hits("GBZ 188-2025", "188") is True
    assert hits("GB/T 150.4-2024", "150.4") is True


def test_body_hits_handles_none(hits):
    assert hits(None, "24") is False
    assert hits("GB 24-2020", "") is False
