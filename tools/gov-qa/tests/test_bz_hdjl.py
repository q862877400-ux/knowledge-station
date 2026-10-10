"""测试：`bz-hdjl`（亳州市·信件选登）适配器的解析与站点约束。

## 为什么

它是**安徽第 3 个可采市级源**。本组用例钉住**表格式详情**的抽取，
以及本轮最重要的一条：**"首页是登录页" ≠ 这个入口不可采**。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ADAPTERS = Path(__file__).resolve().parent.parent / "adapters"


def _load():
    sys.path.insert(0, str(ADAPTERS))
    spec = importlib.util.spec_from_file_location("bz_hdjl_t", ADAPTERS / "bz_hdjl.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LIST_HTML = """
<div class="search-main">
<a href="/InFeedback/show/260404037005058.html">我市科技类校外培训机构审批条件有哪些？</a>
<a href="/InFeedback/show/260415037006007.html">住房公积金贷款</a>
<a href="/InFeedback/show/260404037005058.html">我市科技类校外培训机构审批条件有哪些？</a>
</div>
<pagination currentpage="1" pagesize="12" pagecount="14" total="163"></pagination>
"""

#: 真实结构：`u-tit` 是字段名、紧邻的 `u-item`/`u-desc` 是值
DETAIL_HTML = """
<section class="m-maildetail">
<table class="table table-bordered"><tbody>
<tr><td class="u-tit" align="center" bgcolor="#f5f5f5"><div>信件标题</div></td>
    <td colspan="4">我市科技类校外培训机构审批条件有哪些？</td></tr>
<tr><td class="u-tit" align="center"><div>信件来源</div></td>
    <td class="u-item">政府网站</td>
    <td class="u-tit" align="center"><div>来信时间</div></td>
    <td class="u-item">2026-04-02 08:31</td></tr>
<tr><td class="u-tit" align="center"><div>信件内容</div></td>
    <td class="u-desc" colspan="4">我市科技类校外培训机构审批条件有哪些？</td></tr>
<tr><td class="u-tit" align="center"><div>办理部门</div></td>
    <td class="u-item">市科技局</td>
    <td class="u-tit" align="center"><div>办理时间</div></td>
    <td class="u-item">2026-04-07 17:12</td></tr>
<tr><td class="u-tit" align="center"><div>回复内容</div></td>
    <td class="u-desc" colspan="4">市科技局承办并予以答复，现答复如下：
    开办资金一般不少于人民币30万元。如有疑问，请联系市科技局，联系电话：5606917。</td></tr>
</tbody></table></section>
"""


def test_parse_list_dedupes_and_keeps_order():
    m = _load()
    items = m._parse_list(LIST_HTML)
    assert len(items) == 2, f"应去重成 2 条，实际 {len(items)}"
    assert items[0]["id"] == "260404037005058"
    assert "培训机构" in items[0]["title"]


def test_parse_total_reads_pagination_attrs():
    """站点自报 `pagecount=14 total=163`。"""
    m = _load()
    meta = m._parse_total(LIST_HTML)
    assert meta.get("pagecount") == 14, meta
    assert meta.get("total") == 163, meta
    assert meta.get("pagesize") == 12, meta


def test_fields_pairs_tit_with_item():
    """**核心判据**：`u-tit`（字段名）必须与**紧邻的** `u-item`/`u-desc`（值）配对。

    表里一行可能有两个 `u-tit`（如「办理部门」+「办理时间」）
    ⇒ 必须按**位置**切段，不能按行切。
    """
    m = _load()
    f = m._fields(DETAIL_HTML)
    assert f.get("信件标题") == "我市科技类校外培训机构审批条件有哪些？", f
    assert f.get("信件来源") == "政府网站", f
    assert f.get("来信时间") == "2026-04-02 08:31", f
    assert f.get("办理部门") == "市科技局", f
    assert f.get("办理时间") == "2026-04-07 17:12", f


def test_parse_detail_extracts_question_and_answer():
    """必须抽出**信件内容**与**回复内容** —— 这是"可采"的判据。"""
    m = _load()
    d = m._parse_detail(DETAIL_HTML)
    assert "培训机构" in (d["question"] or ""), d
    assert d["answer"], "回复内容不得为空"
    assert "5606917" in d["answer"], d
    assert d["asked_at"] == "2026-04-02 08:31", d
    assert d["answered_at"] == "2026-04-07 17:12", d
    assert d["dept"] == "市科技局", d
    assert d["title"] == "我市科技类校外培训机构审批条件有哪些？", d


def test_pagination_starts_at_one():
    """分页从 1 起（与池州同族，与焦作相反）。"""
    m = _load()
    assert m.LIST_TPL.format(page=1).endswith("/page_1.html"), m.LIST_TPL


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
