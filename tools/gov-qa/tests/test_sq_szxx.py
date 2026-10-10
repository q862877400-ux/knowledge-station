"""测试：`sq-szxx`（商丘市·市长信箱）适配器的解析与站点约束。

## 为什么

它是**河南第 1 个可采的市级源**（河南 18 个零记录市此前一条都没有）。
本模块的教训是"判据要咬对对象" ⇒ 这里用**真实 HTML 片段**钉住解析，
并钉住**站点 CC 防护的约束**（每秒不能多于 1 次请求）。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ADAPTERS = Path(__file__).resolve().parent.parent / "adapters"


def _load():
    sys.path.insert(0, str(ADAPTERS))
    spec = importlib.util.spec_from_file_location("sq_szxx_t", ADAPTERS / "sq_szxx.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


#: 真实列表页片段（2026-10-10 实测结构，已缩简）
LIST_HTML = """
<table class="letterList">
<thead><tr><th class="num">编号</th><th class="title">信件主题</th>
<th class="open">公开状态</th><th class="dep">办理部门</th>
<th class="state">办理状态</th><th class="date">信件日期</th><th class="clicks">点击数</th></tr></thead>
<tbody>
<tr class="openLetter ">
  <td class="num">1</td>
  <td class="ico"><img src="/x.png" alt="公开信件"></td>
  <td class="title petitioncontent"><a title="关于井盖下陷的问题" href="/petition/22880">关于井盖下陷的问题 </a></td>
  <td class="open">已公开</td>
  <td class="dep">睢阳区人民政府</td>
  <td class="state">已办结</td>
  <td class="date">2026-09-20</td>
  <td class="clicks">503</td>
</tr>
</tbody></table>
"""

#: 真实详情页片段（`trName` 部门/日期 + `trResults` 答复正文）
DETAIL_HTML = """
<table class="detailTable">
<thead><tr><th colspan="4">办理结果</th></tr></thead>
<tbody>
<tr class="trName">
  <td class="tdName">回复部门</td><td class="tdCon">睢阳区人民政府</td>
  <td class="tdName">回复日期</td><td class="tdCon">2026-09-24</td>
</tr>
<tr class="trResults">
  <td class="tdName">办理结果</td>
  <td class="tdCon" colspan="3">您好！您的来信已收悉。经睢阳区住房和城乡建设局核实，
  香君路井盖塌陷问题属实。该局已第一时间组织工作人员赴现场处置。</td>
</tr>
</tbody></table>
"""


def test_parse_list_extracts_all_fields():
    """列表页必须抽出 id / 标题 / 部门 / 状态 / 日期 / 点击数。"""
    m = _load()
    items = m._parse_list(LIST_HTML)
    assert len(items) == 1, items
    it = items[0]
    assert it["id"] == "22880"
    assert it["title"] == "关于井盖下陷的问题"
    assert it["dept"] == "睢阳区人民政府"
    assert it["state"] == "已办结"
    assert it["date"] == "2026-09-20"
    assert it["open_state"] == "已公开"


def test_parse_detail_extracts_answer():
    """详情页必须抽出**答复正文** —— 这是"可采"的判据。"""
    m = _load()
    d = m._parse_detail(DETAIL_HTML)
    assert d["answer"], "答复正文不得为空"
    assert "睢阳区住房和城乡建设局" in d["answer"]
    assert d["reply_dept"] == "睢阳区人民政府"
    assert d["reply_date"] == "2026-09-24"


def test_clean_keeps_chinese_angle_brackets():
    """**反向用例**：`《出生证明》` 这类中文尖括号不得被当 HTML 标签吃掉。

    （本模块已踩过的坑：通用 `<[^>]+>` 会把 `《…》` 误当标签。）
    """
    m = _load()
    got = m._clean("请携带《出生证明》原件")
    assert "《出生证明》" in got, got


def test_real_treats_literal_null_as_absent():
    """`null` 一律当"没有"（IGI 那次的教训，这里统一用 `_real`）。"""
    m = _load()
    assert m._real("null") == ""
    assert m._real(None) == ""
    assert m._real("真内容") == "真内容"


def test_site_rate_limit_is_respected():
    """**站点约束判据**：`PAUSE` 必须 > 1 秒。

    站点 CC 防护页**明文写着**「每秒不能多于 1 次页面请求」。
    我第一版设 `PAUSE = 1.0`（正好 1 次/秒）⇒ 连抓十几条后**全站 403**。
    ⇒ 这条钉住"间隔必须留余量"。谁改回 <=1.0，必红。
    """
    m = _load()
    assert m.PAUSE > 1.0, (
        f"PAUSE={m.PAUSE} 太激进 —— 站点明文要求「每秒不能多于 1 次」，"
        f"实测 1.0 会触发全站 403")
