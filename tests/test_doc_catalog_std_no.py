# -*- coding: utf-8 -*-
"""`_is_standard_no` 的**边界形态普查**（复核 b9 的 LOW-1/LOW-2，2026-09-18）。

为什么单独一组用例：这个判据决定**每一份文档挂标准树还是法规树**（生产库 6417 行，
实测一次"枚举漏一类"就翻了 **5879 行 = 91.6%**）。它历史上换过三种写法：

  1. `\\b` —— **对**，但过不了"无空格接数字"（`GB88888-2088` 是归一形，`GB` 与 `8`
     都是词字符 ⇒ 边界不成立）⇒ 被当成法规；
  2. `(?=[\\s/／]|\\d|$)` —— 救了无空格那种，却把 `\\b` 本来接受的**一整类非词分隔符**
     丢了（`-`、`—`、全角字母…）⇒ 全角斜杠那一类在生产库是**常态** ⇒ 大面积回退；
  3. 现在：`(?![A-Za-z])`（**一般规则**）+ NFKC 归一。

所以这里**枚举"第 1 种写法接受过的全部形态"**：任何人再把它换成枚举类，
只要漏掉一类，这些用例就会红——把"一般规则被换成枚举"这件事变成**必然留下证据**的改动。
"""
from __future__ import annotations

import pytest

from src.core.knowledge.doc_catalog import _is_standard_no

#: 必须判成**标准**的形态（每一种都对应一个真实或曾经出错的输入）。
IS_STANDARD = [
    ("GB 50016-2014", "常见带空格写法"),
    ("GB/T 3608-2008", "推荐性国标（带斜杠）"),
    ("GB88888-2088", "**无空格**接数字（换成 `\\b` 就是为它红的）"),
    ("GBZ1-2010", "职业卫生标准（前缀后面跟字母，但它在名单里）"),
    ("GBT 1234-2020", "`GBT` 缩写形态"),
    ("DB11/T 1234-2020", "地方标准：`DB` 后接**数字**"),
    ("DB11／T 1234-2020", "地方标准：**全角斜杠**（生产库常态，LOW-1 实测 5879 行）"),
    ("GB-T 1234", "**半角连字符**（`\\b` 接受过，枚举版丢了）"),
    ("GB—T 1234", "**破折号**（同上）"),
    ("GB　/T 1234", "**全角空格**"),
    ("ＧＢ 50016-2014", "**全角字母**前缀（靠 NFKC 归一救回）"),
    ("GB", "退化输入：光杆 `GB`（原行为当标准）"),
    ("GB/T", "退化输入：光杆 `GB/T`"),
]

#: 必须判成**法规**的形态（不能因为"放宽边界"就一起放松）。
NOT_STANDARD = [
    ("", "空串"),
    ("中华人民共和国安全生产法", "法规名"),
    ("GBX 1234", "`GB` 后面跟**另一个字母** ⇒ 不是这些标准的编号"),
    ("DBX 1234", "同上（`DB` + 字母）"),
    ("JGZ 1", "同上（前缀 + 字母）"),
    ("中华人民共和国民法典", "法规名"),
]


@pytest.mark.parametrize("raw,why", IS_STANDARD)
def test_forms_that_must_count_as_standard(raw, why):
    assert _is_standard_no(raw), f"{raw!r}（{why}）被判成了法规"


@pytest.mark.parametrize("raw,why", NOT_STANDARD)
def test_forms_that_must_not_count_as_standard(raw, why):
    assert not _is_standard_no(raw), f"{raw!r}（{why}）被判成了标准"


def test_classify_document_uses_the_same_judgement():
    """**接线断言**：`classify_document` 必须走这条判据（不能自己再写一份判断）。"""
    from src.core.knowledge import doc_catalog

    std = doc_catalog.classify_document({"standard_no": "GB—T 1234", "standard_name": "x"})
    law = doc_catalog.classify_document({"standard_no": "中华人民共和国安全生产法"})
    assert std["top"] == "std", std
    assert law["top"] == "law", law
