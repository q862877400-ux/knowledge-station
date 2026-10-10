"""测试：`kf-hdjl`（开封市·信件公开）适配器的解析与站点约束。

## 为什么

它是**河南第 5 个可采市级源**。本模块的教训是"判据要咬对对象" ⇒
这里用**真实响应片段**钉住解析，并钉住本轮踩到的**三个参数陷阱**
（错任一个都返回 `total:0` —— **看起来像"没有数据"**）。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ADAPTERS = Path(__file__).resolve().parent.parent / "adapters"


def _load():
    sys.path.insert(0, str(ADAPTERS))
    spec = importlib.util.spec_from_file_location("kf_hdjl_t", ADAPTERS / "kf_hdjl.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_site_id_param_is_qd_id_not_site_id():
    """**核心判据**：列表的 `siteId` 参数传的是 **`qdId`**。

    `config.js` 里 `userIdObj` 同时有 `siteId` 与 `qdId` 两个 19 位 id，
    而 `zmhd.js::getMailList` 用的是 **`siteId: defaultConfig.userIdObj.qdId`**。
    我第一版传了 `userIdObj.siteId` ⇒ 接口返回 `total:0`
    —— **看起来像"这个站没有数据"**。
    """
    m = _load()
    assert m.QD_ID == "1736686125818318848", (
        f"列表的 siteId 参数必须是 qdId，实际 QD_ID={m.QD_ID!r}")
    assert m.QD_ID != "1735601820788891648", (
        "QD_ID 不得等于 userIdObj.siteId（那会返回 total:0）")


def test_clean_strips_html_comments_and_keeps_brackets():
    """`content` / `replyContent` 都是 HTML ⇒ 必须剥标签，且两个都不能少。

    - HTML 注释要剥（窄正则吃不掉 `<!--…-->`）
    - 中文书名号要留（宽正则会误吃 `《…》`）
    """
    m = _load()
    got = m._clean("<!--c--> <p>答复《出生证明》</p>")
    assert "<!--" not in got and "-->" not in got, f"注释没剥：{got!r}"
    assert "《出生证明》" in got, f"书名号被吃了：{got!r}"
    assert "答复" in got


def test_dept_of_reads_metadata_list():
    """`metadataList` 是 **JSON 字符串**，要从里面取「答复单位」。"""
    m = _load()
    raw = ('[{"metadataId":"1","name":"答复单位","value":"开封市图书馆"},'
           '{"metadataId":"2","name":"其他","value":"x"}]')
    assert m._dept_of(raw) == "开封市图书馆"
    assert m._dept_of(None) is None
    assert m._dept_of("不是 JSON") is None
    assert m._dept_of("[]") is None


def test_real_treats_literal_null_as_absent():
    m = _load()
    assert m._real("null") == ""
    assert m._real(None) == ""
    assert m._real("真内容") == "真内容"


def test_page_size_and_pause_are_reasonable():
    """站点约束：分页大小与请求间隔都要克制。"""
    m = _load()
    assert 1 <= m.PAGE_SIZE <= 100, f"PAGE_SIZE={m.PAGE_SIZE} 不合理"
    assert m.PAUSE >= 0.2, f"PAUSE={m.PAUSE} 太激进"
