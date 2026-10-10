"""测试：`zk-zxsq`（周口市·咨询受理）适配器的解析与站点约束。

## 为什么

它是**河南第 4 个可采市级源**。本模块的教训是"判据要咬对对象" ⇒
这里用**真实响应片段**钉住解析，并钉住本轮踩到的 **CSRF token** 陷阱。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ADAPTERS = Path(__file__).resolve().parent.parent / "adapters"


def _load():
    sys.path.insert(0, str(ADAPTERS))
    spec = importlib.util.spec_from_file_location("zk_zxsq_t", ADAPTERS / "zk_zxsq.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


#: 真实页面片段：**`value` 在 `id` 之前**（我第一版正则按 `id` 在前写 ⇒ 抠到空串）
TOKEN_HTML = '<input type="hidden" value="e6e532ba4e444881a4728defd757cd53" id="loadMailboxsDataToken"> '

DETAIL_HTML = """
<div class="content-mid">
  <div class="title"><span>关于购房补贴以及手续问题</span></div>
  <div>来信内容 网友您好，我想咨询购房补贴的发放条件。提交时间 2026-08-01</div>
  <div>回复时间 2026-08-05 09:47:45 回复内容 网友您好，关于您咨询的问题，现回复如下：
  该情况不影响您的购房补贴发放。如有其他疑问，您可拨打周口市住房保障和房地产业发展中心大厅
  （联系电话： 0394-8221088 ）进行咨询，感谢您的理解与支持。</div>
</div>
"""


def test_token_regex_handles_value_before_id():
    """**核心判据**：`loadMailboxsDataToken` 的 `value` 在 `id` **之前**。

    我第一版按 `id` 在前写正则 ⇒ 抠到空串 ⇒ 接口返回
    `{"rows":[],"total":-1}` —— **看起来像"没有数据"**。
    """
    m = _load()
    mt = m.TOKEN_RE.search(TOKEN_HTML)
    assert mt, "必须能从 `value` 在 `id` 之前的写法里抠出 token"
    assert mt.group(1) == "e6e532ba4e444881a4728defd757cd53"


def test_parse_detail_extracts_answer():
    """详情页必须抽出**答复正文**与回复时间 —— 这是"可采"的判据。"""
    m = _load()
    d = m._parse_detail(DETAIL_HTML)
    assert d["answer"], "答复正文不得为空"
    assert "0394-8221088" in d["answer"]
    assert d["answered_at"] == "2026-08-05 09:47:45"


def test_clean_strips_html_comments():
    """**HTML 注释必须被剥掉**（2026-10-10 实测的真缺陷）。

    窄正则 `</?[A-Za-z][^>]*>` **吃不掉** `<!--…-->`（`<!--` 不以字母开头）
    ⇒ 周口答复里混进了 `<!--47个文件要求meta-->`。
    修法是**在剥标签之前先剥注释**。
    """
    m = _load()
    got = m._clean("<!--47个文件要求meta--> 真实答复内容")
    assert "<!--" not in got and "-->" not in got, f"注释没剥干净：{got!r}"
    assert "真实答复内容" in got


def test_clean_keeps_chinese_angle_brackets():
    """**反向用例**：`《出生证明》` 不得被当 HTML 标签吃掉。"""
    m = _load()
    assert "《出生证明》" in m._clean("请携带《出生证明》原件")


def test_page_size_is_bounded():
    m = _load()
    assert 1 <= m.PAGE_SIZE <= 50, f"PAGE_SIZE={m.PAGE_SIZE} 不合理"
