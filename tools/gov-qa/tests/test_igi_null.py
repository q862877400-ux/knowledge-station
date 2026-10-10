"""测试：IGI 引擎不得把字面 `"null"` 当正文（spec 005 T205）。

## 为什么

IGI 接口把「没有正文」编码成**字符串 `"null"`**（不是 JSON `null`）。
原写法 `clean(CONTENT) or clean(HTMLCONTENT) or title` 里，
`clean("null")` 返回 **truthy** 的 `"null"` ⇒ **fallback 永远不执行**
⇒ `question` 落成字面 `"null"`。

实测 `shannan-igi-*` 152 条中招，而真标题就在 `extra.title` 里。

⇒ 修法：新增 `_real()`，把 `null/none/undefined/空串` 一律当"没有"。
谁把 `_real` 改回 `clean`，本文件必红。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ADAPTERS = Path(__file__).resolve().parent.parent / "adapters"


def _load_igi():
    sys.path.insert(0, str(ADAPTERS))
    spec = importlib.util.spec_from_file_location(
        "_igi_common_test", ADAPTERS / "_igi_common.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_real_treats_literal_null_as_absent():
    """`_real("null")` 必须是空串 —— 否则 `or` 不会回落到真标题。"""
    m = _load_igi()
    assert m._real("null") == ""
    assert m._real("NULL") == ""
    assert m._real("None") == ""
    assert m._real("undefined") == ""
    assert m._real("") == ""
    assert m._real(None) == ""


def test_real_keeps_genuine_content():
    """**反向用例**：真内容不得被吃掉（判据不能恒空）。"""
    m = _load_igi()
    assert m._real("山南实习岗位") == "山南实习岗位"
    assert m._real("  <p>正文</p>  ").strip() == "正文"


def test_nullish_falls_through_to_title():
    """复现原始 bug 形态：`_real(...) or _real(...) or title` 必须回落到标题。"""
    m = _load_igi()
    title = "拖欠农民工工资"
    got = m._real("null") or m._real(None) or title
    assert got == title, f"应回落到标题，实际 {got!r}"


def test_old_clean_would_have_failed():
    """**反证**：用旧的 `clean(...) or ...` 写法确实会拿到 `'null'`。

    这条不是在测实现，而是把"为什么需要 `_real`"钉成可执行的证据 ——
    若哪天 `clean` 自己开始过滤 `null`，这条会红，提醒我们去合并两条路径。
    """
    m = _load_igi()
    old_style = m.clean("null") or m.clean(None) or "真标题"
    assert old_style == "null", (
        "`clean` 现在也会过滤 null 了？那两条路径应合并，本用例需重写")
