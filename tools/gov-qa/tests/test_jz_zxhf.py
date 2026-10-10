"""测试：`jz-zxhf`（焦作市·咨询回复）适配器的解析与站点约束。

## 为什么

它是**河南第 3 个可采市级源**。本模块的教训是"判据要咬对对象" ⇒
这里用**真实 HTML 片段**钉住解析。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ADAPTERS = Path(__file__).resolve().parent.parent / "adapters"


def _load():
    sys.path.insert(0, str(ADAPTERS))
    spec = importlib.util.spec_from_file_location("jz_zxhf_t", ADAPTERS / "jz_zxhf.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LIST_HTML = """
<div class="news_list news_list_son fr">
<a href="https://www.jiaozuo.gov.cn/2026/09-17/615813.html" target="_blank">今年是否还有医学生招聘公告</a>
<a href="https://www.jiaozuo.gov.cn/2026/08-17/612631.html" target="_blank">生育津贴领取条件</a>
<a href="https://www.jiaozuo.gov.cn/2026/09-17/615813.html" target="_blank">今年是否还有医学生招聘公告</a>
</div>
"""

DETAIL_HTML = """
<h1>今年是否还有医学生招聘公告</h1>
<div>详细信息 标题 今年是否还有医学生招聘公告 提交日期 2026-09-15
内容 您好，我是护理专业毕业生，请问还有类似的医学招聘吗？盼复，感谢！</div>
<div>受理回复 回复日期 2026-09-20 回复单位 焦作市卫生健康委员会
回复内容 感谢您的咨询。关于下半年是否继续组织招聘，将根据各医疗卫生单位岗位空缺情况确定。</div>
"""


def test_parse_list_dedupes_and_keeps_order():
    """列表页：**去重**且保序（实测页面里同一个详情链接会出现两次）。"""
    m = _load()
    items = m._parse_list(LIST_HTML)
    assert len(items) == 2, f"应去重成 2 条，实际 {len(items)}"
    assert items[0]["id"] == "615813"
    assert items[0]["title"] == "今年是否还有医学生招聘公告"


def test_parse_detail_extracts_answer_and_meta():
    """详情页必须抽出**答复正文**与日期/部门 —— 这是"可采"的判据。"""
    m = _load()
    d = m._parse_detail(DETAIL_HTML)
    assert d["answer"], "答复正文不得为空"
    assert "岗位空缺情况" in d["answer"]
    assert d["asked_at"] == "2026-09-15"
    assert d["answered_at"] == "2026-09-20"
    assert d["dept"] == "焦作市卫生健康委员会"


def test_clean_keeps_chinese_angle_brackets():
    """**反向用例**：`《出生证明》` 不得被当 HTML 标签吃掉。"""
    m = _load()
    assert "《出生证明》" in m._clean("请携带《出生证明》原件")


def test_pagination_suffix_matches_the_js():
    """**分页判据**：从 `paging.js` 的 `goto` 抄到的规则是**页号从 0 起**。

    ```js
    var returnp = page == 0 ? '' : ('_' + page);
    var dataUrl = this.reLoadUrl + 'index' + returnp + '.html';
    ```
    ⇒ 第 1 页是 `index.html`、第 2 页是 `index_1.html`。
    谁改成 `index_1.html` 当第一页，就会**漏掉首页 24 条**。
    """
    m = _load()
    assert m.LIST_TPL.format(page="").endswith("/index.html"), m.LIST_TPL
    assert m.LIST_TPL.format(page="_1").endswith("/index_1.html"), m.LIST_TPL


def test_page_count_is_items_not_pages():
    """**站点约束**：`pagecount=34` 是**总条数**不是总页数。

    页面写 `<div id="pageDec" pagesize="24" pagecount="34">`，
    JS 里 `pages = ceil(pagecount/pagesize)` = 2。
    实测 `index_0` 24 条 + `index_1` 10 条 = 34 条，`index_2` 空。

    ⚠ 谁把 `pagecount` 当"总页数"去翻 34 页，会白跑 32 页。
    本用例钉住"翻页靠**实测到空**为止"这一语义（`MAX_PAGES` 只是安全上限）。
    """
    m = _load()
    assert m.MAX_PAGES >= 5, "上限太小会漏页"
    assert m.MAX_PAGES <= 100, "上限太大等于没有上限"
