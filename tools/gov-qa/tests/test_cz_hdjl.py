"""测试：`cz-hdjl`（池州市·留言选登）适配器的解析与站点约束。

## 为什么

它是**安徽第 2 个可采市级源**。本模块的教训是"判据要咬对对象" ⇒
这里用**真实 HTML 片段**钉住解析，并钉住**分页形态不能照抄别市**这条。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ADAPTERS = Path(__file__).resolve().parent.parent / "adapters"


def _load():
    sys.path.insert(0, str(ADAPTERS))
    spec = importlib.util.spec_from_file_location("cz_hdjl_t", ADAPTERS / "cz_hdjl.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LIST_HTML = """
<div class="search-main">
<a href="/InFeedback/show/60010.html" target="_blank">商转公问题咨询</a>
<a href="/InFeedback/show/59353.html" target="_blank">公积金提取问题</a>
<a href="/InFeedback/show/60010.html" target="_blank">商转公问题咨询</a>
</div>
<pagination currentpage="1" pagesize="10" pagecount="13" total="128"></pagination>
"""

DETAIL_HTML = """
<h1 class="u-lgtit f-tac  f-md-mb10">商转公问题咨询</h1>
<div class="message_con clearfix f-mt30">
  <div class="message_title font18 lx_title"><span>留言</span></div>
  <div class="message_nr"><div class="message_nr_text font18"><p>
我想办理商转公，需要什么办理条件？
</p></div></div>
  <div class="message_info">
    <span>留言类型：咨询</span>&nbsp;&nbsp;
    <span>留言时间：2025-11-11 11:29</span>
  </div>
</div>
<div class="message_con f-clearfix f-mt30">
  <div class="message_title font18 hf_title"><span>回复</span></div>
  <div class="message_nr"><div class="message_nr_text font18">
    <p>网友您好：</p><p>根据《关于恢复商业性个人住房贷款转住房公积金贷款业务实施办法》…</p>
    <p>您可以直接拨打我市住房公积金业务服务电话0566-3220093详细咨询。</p>
  </div></div>
</div>
"""


def test_parse_list_dedupes_and_keeps_order():
    """列表页：**去重**且保序（实测同一详情链接可能出现两次）。"""
    m = _load()
    items = m._parse_list(LIST_HTML)
    assert len(items) == 2, f"应去重成 2 条，实际 {len(items)}"
    assert items[0]["id"] == "60010"
    assert items[0]["title"] == "商转公问题咨询"
    assert items[0]["url"].endswith("/InFeedback/show/60010.html")


def test_parse_total_reads_pagination_attrs():
    """**站点自报**：从 `<pagination … pagecount="13" total="128">` 取。"""
    m = _load()
    meta = m._parse_total(LIST_HTML)
    assert meta.get("pagecount") == 13, meta
    assert meta.get("total") == 128, meta
    assert meta.get("pagesize") == 10, meta


def test_parse_detail_extracts_question_and_answer():
    """详情页必须抽出**留言正文**与**回复正文** —— 这是"可采"的判据。"""
    m = _load()
    d = m._parse_detail(DETAIL_HTML)
    assert "商转公" in (d["question"] or ""), d
    assert d["answer"], "回复正文不得为空"
    assert "0566-3220093" in d["answer"], d
    assert d["asked_at"] == "2025-11-11 11:29", d
    assert d["msg_type"] == "咨询", d
    assert d["title"] == "商转公问题咨询"


def test_pagination_starts_at_one_not_zero():
    """**分页形态不能照抄别市**（2026-10-10 实测对照）。

    | 市 | 形态 |
    |---|---|
    | 焦作 `jz-zxhf` | `index.html` / `index_1.html`（**从 0 起**）|
    | 池州 `cz-hdjl` | `page_1.html` / `page_2.html`（**从 1 起**）|

    谁把池州改成"从 0 起"，`page_0.html` 会 404 ⇒ **漏掉首页 10 条**。
    """
    m = _load()
    assert m.LIST_TPL.format(page=1).endswith("/page_1.html"), m.LIST_TPL
    assert m.LIST_TPL.format(page=2).endswith("/page_2.html"), m.LIST_TPL


def test_clean_strips_comments_and_keeps_brackets():
    m = _load()
    got = m._clean("<!--c--> <p>回复《出生证明》</p>")
    assert "<!--" not in got and "-->" not in got, f"注释没剥：{got!r}"
    assert "《出生证明》" in got, f"书名号被吃了：{got!r}"


def test_real_treats_literal_null_as_absent():
    m = _load()
    assert m._real("null") == ""
    assert m._real(None) == ""
    assert m._real("真内容") == "真内容"
