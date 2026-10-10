"""测试：`tl-hdjl`（铜陵市·信件公开）适配器的解析与站点约束。

## 为什么

它是**安徽第 1 个可采市级源**。它与开封**同一套平台但四处不同** ⇒
本组用例把那四处钉住，**防止有人"照抄开封"**。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ADAPTERS = Path(__file__).resolve().parent.parent / "adapters"


def _load():
    sys.path.insert(0, str(ADAPTERS))
    spec = importlib.util.spec_from_file_location("tl_hdjl_t", ADAPTERS / "tl_hdjl.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_api_prefix_has_no_u():
    """**核心判据**：铜陵的接口前缀是 `/api/mail/`（**不带 `u`**）。

    开封是 `/uapi/mail/`（**多一个 `u`**）。照抄开封会打到 404/非 JSON
    （实测铜陵 `/uapi/mail/list` 返回 **566KB 的 HTML**，不是 JSON）。
    """
    m = _load()
    assert "/uapi/" not in m.LIST_API, f"铜陵不能用 uapi 前缀：{m.LIST_API}"
    assert m.LIST_API.endswith("/api/mail/list"), m.LIST_API
    assert m.DETAIL_API.endswith("/api/mail/detail"), m.DETAIL_API


def test_uses_own_site_id_not_kf_qd_id():
    """铜陵**没有 `qdId`**，列表 `siteId` 参数用 `useObj.siteId`。

    谁把开封的 `qdId`（`1736686125818318848`）抄过来，就会返回 `total:0`。
    """
    m = _load()
    assert m.SITE_ID == "1691623558897848320", m.SITE_ID
    assert m.SITE_ID != "1736686125818318848", "不得用开封的 qdId"
    assert m.TENANT_ID == "1676766850592583680", m.TENANT_ID
    assert m.TENANT_ID != "1735586219994349568", "不得用开封的 tenantId"


def test_dept_of_handles_python_style_single_quotes():
    """**实测的坑**：`metadataList` 的键值用**单引号**（Python 字面量风格），
    `json.loads` 会失败 ⇒ 必须能兜住。"""
    m = _load()
    raw = ("[{'metadataId': '1', 'formType': 'text', "
           "'metadataValue': '铜陵市总工会', 'name': '答复单位'}]")
    got = m._dept_of(raw)
    assert got == "铜陵市总工会", f"单引号格式没兜住：{got!r}"
    # 标准 JSON 也要能处理
    assert m._dept_of('[{"name":"答复单位","metadataValue":"X"}]') == "X"
    assert m._dept_of(None) is None
    assert m._dept_of("不是任何格式") is None


def test_clean_strips_comments_and_keeps_brackets():
    m = _load()
    got = m._clean("<!--c--> <p>答复《出生证明》</p>")
    assert "<!--" not in got and "-->" not in got, f"注释没剥：{got!r}"
    assert "《出生证明》" in got, f"书名号被吃了：{got!r}"


def test_clean_strips_site_side_stray_closing_tags():
    """**实测的坑**：站方原始 HTML 末尾带**孤立闭合标签**。

    `replyContent` 的**原始值**末尾就写着
    `</铜陵市人民政府关于支持创业就业人员购(租)房的实施意见>`
    —— 那是**站方自己**的畸形 HTML（只有闭合、没有开头，
    "标签名"是**中文文档名**）。**不是我的剥标签漏了**（真标签确实剥掉了）。

    全库有 **32 条**这种。正常 HTML 标签名只能是 ASCII 字母数字 ⇒
    尖括号里以 `/` 开头且含中文的，单独清掉。
    """
    m = _load()
    raw = "答复完成 <br> </铜陵市人民政府关于支持创业就业人员购(租)房的实施意见>"
    got = m._clean(raw)
    assert "铜陵市人民政府" not in got, f"孤立闭合标签没清掉：{got!r}"
    assert "答复完成" in got
    # 反向：正常的 HTML 标签仍要剥，中文书名号仍要留
    assert m._clean("<p>答复</p>") == "答复"
    assert "《出生证明》" in m._clean("请携带《出生证明》原件")


def test_real_treats_literal_null_as_absent():
    m = _load()
    assert m._real("null") == ""
    assert m._real(None) == ""
    assert m._real("真内容") == "真内容"


def test_page_size_and_pause_are_reasonable():
    m = _load()
    assert 1 <= m.PAGE_SIZE <= 100, f"PAGE_SIZE={m.PAGE_SIZE} 不合理"
    assert m.PAUSE >= 0.2, f"PAUSE={m.PAUSE} 太激进"
