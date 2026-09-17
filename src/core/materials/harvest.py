# -*- coding: utf-8 -*-
"""材料平面：**网页采集器**（Phase C 第四步，2026-09-17）。

## 这一段补的是什么
§10.22 有"自采入口"（`collect.collect_text`），§10.23/§10.24 有 Track L 的决策与入库，
但**没有任何东西真的去抓**——"能自己搜集材料"还只是半句话。本模块是那个"抓"：
给一个 URL，**按既有纪律**取回正文，交给 `collect_text` 登记（**一律 pending**）。

## 三条纪律，全部**复用**既有所有者（不新写第二份）
1. **SSRF 检查**走 `update.announce.is_private_url`（那个模块的 docstring 写明
   "用户拍板严格版，**无豁免开关**"）。本模块**不提供**"允许内网"的参数——
   那等于给严格版开后门。测试要打本地服务时，用 `monkeypatch` 换掉那个函数，
   **不在生产代码里留开关**。
   ⚠ **闸门必须在"发起每一跳之前"生效**：独立复核（2026-09-17）实测默认传输**跟随 302**
   ⇒ 一个公网 URL 可用 `Location: http://169.254.169.254/…` 把请求引向内网，而闸门只在
   最前面判过一次。故本模块**显式关掉重定向跟随**（`_fetch_without_redirects`），
   把"重定向"变成一个**可见的结果**；只有**同主机**的 http→https 升级会重试一次
   （主机没变 ⇒ 不可能被引向内网）。
2. **抓取**走 `update.channels.base.default_transport()`（curl_cffi 浏览器指纹，
   httpx 兜底），契约 `fetch(url, timeout=…, allow_redirects=…) -> (status, body)`。
   **不自造 HTTP 客户端**（重定向 kwarg 的名字差异由那个模块翻译）。
3. **HTML→文本**走 `text_utils.html_to_text`（页面级规范实现；见那里关于
   "与 `clause_health_html_to_text` 的精确关系"的说明）。

## 界线（谁负责什么）
- 本模块**只做"一次抓取 + 登记"**，**不是爬虫**：不排队、不重试、不递归跟链接、
  不限速、不做 robots/ToS 判断。**采集预算与频率上限仍未定**（方案 §11.4），
  所以这里刻意不提供批量入口——要批量，先定预算。
- 抓回来的东西**默认不可信**（交给 `collect_text` ⇒ T3 起、pending、`ephemeral`）。
- **不解析 PDF/附件**：正文非 HTML（如 PDF）时如实说明"没抓到正文"，
  而不是把二进制当文本塞进材料。判据现在有**两条**（2026-09-17 复核之后加强）：
  ① **Content-Type 白名单**（网页/纯文本/XML 放行，脚本/样式/接口/附件拒收）；
  ② **真实字节**的 magic（`text_utils.looks_like_binary_bytes`）。
  ⚠ 早先的版本只能靠**转换后的文本**猜（Content-Type 在传输层丢了）——那条限制**已经不成立**
  （传输层新增了 `fetch_page`，一次请求同时给出 headers/text/raw）；剩下的局限是：
  签名判据只看**开头**、无签名的二进制认不出、Content-Type 撒谎且无签名的组合仍会溜过。

## 诚实边界
- 只在拿到 **2xx** 且正文（`str`）非空时才登记；其它情况如实返回 `status`/`reason`，
  **不建立空材料**（空材料会变成"盲签对象"）。
- 两种"空正文"**分开报**：取回就是空的 ⇒ "响应为空"；取回来了但 HTML→文本之后为空
  ⇒ 明确说"原文非空，转换后为空"（否则排查方向会被带偏）。
- **不跟随重定向**（见上）；同主机 http→https 自动试一次，仍被重定向就如实拒绝并
  要求给**最终地址**。
- 标题优先用调用方给的；否则从 `<title>` 取（粗正则）；再否则用 URL。
- `is_private_url` 自带已知局限（DNS rebinding 的 TOCTOU 窗口不设防，
  理由见其 docstring）——本模块**继承**那个局限，不另行声称更强。
- **Content-Type 拿不到**这件事**已解决**（`fetch_page` 契约，2026-09-17 复核的 MEDIUM）：
  现在按响应头的白名单 + 真实字节判。剩余局限（诚实登记）：白名单是**人工列举**的
  （新类型要显式加）、Content-Type 撒谎且**无签名**的组合仍会溜过、charset 转换仍由
  传输层负责（`charset=gbk` 之类**未被真实测试验证**）。
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse, urlsplit, urlunsplit

from src.core.materials import collect as co
from src.core.text_utils import html_to_text, looks_like_binary, looks_like_binary_bytes
from src.core.update import announce as _announce

#: 单页超时（与公告扫描同量级；采集是一次性动作，不必更宽）。
PAGE_TIMEOUT_S = 15.0

#: 正文上限（字符）。**为什么要有**：把整站塞进材料会让切片与提示词都失控；
#: 截断是**显式**的（返回值里带 `truncated`），不静默丢。
MAX_TEXT_CHARS = 200_000

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def page_title(html: str) -> str | None:
    """从 `<title>` 取标题（粗；取不到返回 None）。"""
    m = _TITLE_RE.search(html or "")
    if m is None:
        return None
    title = html_to_text(m.group(1), limit=200).strip()
    return title or None


def _fetch_without_redirects(tp: Any, url: str, timeout: float) -> tuple[int, Any, Any, Any]:
    """抓一跳，**明确不跟随重定向**（`allow_redirects=False`），并把四样都拿回来。

    返回 `(status, headers, text, raw_bytes)`——headers 与 raw 是 Content-Type 白名单
    与"真实字节"magic 判据的输入（见 `_content_type_ok` / `looks_like_binary_bytes`）。

    ## 为什么必须显式关掉（2026-09-17 独立复核的 HIGH，实测可达）
    默认的 curl_cffi `Session` 会**跟随** 302，而 SSRF 闸门只在**发起前**判过原始 URL
    一次 ⇒ 一个公网地址只要返回 `302 Location: http://169.254.169.254/…`，引擎就会
    **真的向云元数据端点发起连接**（复核实测 curl 52/28），闸门被整条绕过。
    关掉跟随之后，"重定向"变成一个**可见的结果**（3xx），由调用方决定怎么办。

    ⚠ **契约是严格的**：transport 没有 `fetch_page` 就**抓不了**（如实报错），
    而不是"退回 `fetch` 继续登记"。理由：退回去就意味着"在拿不到 Content-Type 与真实
    字节的情况下把材料登记进评审队列"——那正是复核报的那条 MEDIUM，不能因为"换了个
    传输层"就悄悄复活。测试替身实现 `fetch_page` 同样只需一行。
    重定向 kwarg 的名字差异由 transport 自己翻译（curl_cffi 用 `allow_redirects`、
    httpx 用 `follow_redirects`——见 `update.channels.base`）。
    """
    page = getattr(tp, "fetch_page", None)
    if page is None:
        raise TypeError(
            "这个 transport 没有 fetch_page(url, timeout=…, allow_redirects=…) —— "
            "采集需要 Content-Type 与真实字节才能判断“这是不是网页正文”；"
            "拒绝在拿不到它们的情况下登记材料（见 harvest 模块头注）")
    return page(url, timeout=timeout, allow_redirects=False)


#: 允许当"网页正文"处理的 Content-Type（**白名单**，不是黑名单）。
#:
#: 为什么是白名单：黑名单永远漏（独立复核实测 11 条样本里 9 条能溜过去）。
#: - 放：`text/html` / `application/xhtml+xml`（网页）、`text/plain`（纯文本通知/公告）、
#:   `application/xml` / `text/xml`（政府站点的 XML 公告）。
#: - **不放**：`text/css` 与 `*javascript`（样式/脚本文件）、`application/json`（接口）、
#:   `application/pdf`、`image/*`、`application/zip`（附件）。
_PAGE_CONTENT_TYPES = (
    "text/html", "application/xhtml+xml", "text/plain", "application/xml", "text/xml",
)


def _content_type_of(headers: Any) -> str | None:
    """从响应头取 Content-Type 的**主类型**（小写；取不到返回 None）。

    ⚠ **键名大小写不敏感**（2026-09-17 复核 E 的 LOW）：HTTP 头名本来就不区分大小写，
    而第一版只查 `headers["content-type"]`。默认传输会把键小写化，所以生产路径没暴露；
    但**替身或未来的传输层**传 `Content-Type` 时，白名单会被**整道静默跳过**
    （表现是"JS/CSS 又能进材料了"，且没有任何报错）。这里自己兜住，不依赖调用方。
    """
    if not isinstance(headers, dict):
        return None
    low = {str(k).lower(): v for k, v in headers.items()}
    raw = low.get("content-type")
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw.split(";", 1)[0].strip().lower() or None


def _content_type_ok(ctype: str | None) -> bool:
    """这个 Content-Type 能不能当网页正文？`None`（服务端没给）交给字节判据。"""
    return ctype is None or ctype in _PAGE_CONTENT_TYPES



def _https_upgrade(url: str) -> str | None:
    """`http://x/y` → `https://x/y`（**只改协议**）；不是 http 就没有可升级的。

    为什么"同主机升级"不算跟随重定向：**主机没变** ⇒ `is_private_url` 的结论不变，
    这条请求**不可能**被引向内网。而 `.gov` 站点 http→https 的 301/302 很常见，
    不试一次会把大量正常页面当成"重定向"丢掉（P1 与 P2 的折中：安全性不受影响）。
    """
    parts = urlsplit(url)
    if parts.scheme.lower() != "http" or not parts.hostname:
        return None
    host = parts.hostname
    port = parts.port
    netloc = host if port in (None, 80) else f"{host}:{port}"
    return urlunsplit(("https", netloc, parts.path, parts.query, parts.fragment))


def collect_url(project_id: str, url: str, *, title: str | None = None,
                source_tier: str | None = None, transport: Any = None,
                timeout: float = PAGE_TIMEOUT_S,
                published_at: str | None = None,
                note: str | None = None) -> dict[str, Any]:
    """抓一个 URL 并登记为**待评审**材料。**返回体恒带 `collected` 布尔**。

    返回形状（成功）：`{collected: True, material: {...}, status: 200, truncated: bool}`；
    失败：`{collected: False, reason: "...", status?: int}` —— **失败不建材料**。

    ⚠ **没有 `allow_private` 之类的开关**（见模块头注第 1 条）。
    """
    target = str(url or "").strip()
    if not target:
        return {"collected": False, "reason": "URL 为空"}

    # ① SSRF 闸门（**唯一判据的所有者**在 announce；这里只调用）
    if _announce.is_private_url(target):
        return {"collected": False, "reason": "URL 被 SSRF 纪律拒绝（仅 http/https 且禁内网/保留地址）"}

    # ② 抓取（复用既有 transport；测试可注入）。**不跟随重定向** + 同主机 http→https 重试。
    tp = transport if transport is not None else _default_transport()
    fetched = target
    try:
        status, headers, body, raw = _fetch_without_redirects(tp, fetched, timeout)
        if 300 <= int(status) < 400:
            upgraded = _https_upgrade(fetched)
            if upgraded is not None:
                status, headers, body, raw = _fetch_without_redirects(tp, upgraded, timeout)
                fetched = upgraded            # 留痕用**实际抓到的**地址
    except Exception as exc:  # noqa: BLE001 — 网络异常/契约不符如实回报，不抛给上层
        return {"collected": False, "reason": f"抓取失败：{exc}"}

    if 300 <= int(status) < 400:
        # **不跟随**重定向（独立复核 2026-09-17 的 HIGH）：跟随会让公网 URL 把请求
        # 引向内网（实测 302 → 169.254.169.254 真的连上了），而闸门只在发起前判一次。
        return {"collected": False, "status": int(status),
                "reason": f"HTTP {int(status)} 重定向——**不跟随**（跟随会绕过 SSRF 闸门："
                          "实测一个公网 URL 可用 302 把请求引向内网元数据端点）。"
                          "同主机 http→https 已自动试过一次；请给出**最终地址**"}
    if int(status) < 200 or int(status) >= 300:
        return {"collected": False, "status": int(status),
                "reason": f"HTTP {status}（不登记未成功取回的页面）"}

    # ③ Content-Type 白名单（独立复核 2026-09-17 的 MEDIUM）：JS/CSS/JSON 接口这些
    # **不是网页正文**的响应，以前会被当成正文登记进材料（复核 11 条样本里 9 条溜过去了）。
    ctype = _content_type_of(headers)
    if not _content_type_ok(ctype):
        return {"collected": False, "status": int(status),
                "reason": f"响应不是网页正文（Content-Type: {ctype}）——"
                          "本模块只收网页/纯文本/XML 公告，不收脚本、样式、接口数据与附件"}
    # ④ **真实字节**的 magic（不是转换后的文本）：PNG/JPEG/ELF/OLE2 这些非 UTF-8 首字节
    # 在 `resp.text` 里早被替换成 U+FFFD，只有 raw 才认得出（复核的 REFUTED 那条）。
    if looks_like_binary_bytes(raw):
        return {"collected": False, "status": int(status),
                "reason": "响应不是文本（真实字节是 PDF/图片/压缩包等二进制容器）"
                          "——本模块不解析附件（Content-Type 可能没写对，故按字节判）"}

    if not isinstance(body, str):
        # 非文本对象（例如 transport 把 JSON 解析成了 dict）：**不把非文本当正文**
        return {"collected": False, "status": int(status),
                "reason": f"响应不是文本（{type(body).__name__}）——本模块不解析 PDF/JSON 附件"}

    text = html_to_text(body)
    if not text.strip():
        # ⚠ 两种"空"要**分开**（独立复核 2026-09-17 指出的归因误导）：原文本身没有内容，
        # 与"转换后没剩下东西"（例如脚本/样式剥离过头）是**不同**的故障，原因串必须能区分。
        return {"collected": False, "status": int(status),
                "reason": ("页面没有可提取的正文（响应为空）" if not (body or "").strip()
                           else "页面没有可提取的正文（原文非空，但 HTML→文本后为空"
                                "——可能是只有标签/脚本/样式的页面）")}
    # ⑤ 文本层面的兜底（字节判据的补充）：登记门 `collect_text` 也调同一判据，
    # 这里提前以**页面的**语境给出更具体的理由。
    if looks_like_binary(text):
        return {"collected": False, "status": int(status),
                "reason": "响应不是文本（看起来是 PDF/图片/压缩包等二进制容器）"
                          "——本模块不解析 PDF/附件"}

    truncated = len(text) > MAX_TEXT_CHARS
    if truncated:
        text = text[:MAX_TEXT_CHARS]

    resolved_title = ((title or "").strip() or page_title(body)
                      or urlparse(fetched).path or fetched)

    note_parts = [p for p in [note] if p]
    # 把 Content-Type 记进判级说明：评审人看得到"这条是怎么来的"，也能自己复核
    # 白名单判得对不对（判据可见 = 可审计）。
    note_parts.append(f"自采：HTTP {int(status)} 来自 {urlparse(fetched).hostname or '?'}"
                      + (f"（Content-Type: {ctype}）" if ctype else "（服务端未给 Content-Type）")
                      + ("（同主机 http→https 升级后取到）" if fetched != target else "")
                      + ("（正文已截断到上限）" if truncated else ""))

    material = co.collect_text(
        project_id, title=resolved_title, text=text, url=fetched,
        source_tier=source_tier, published_at=published_at,
        note="；".join(note_parts),
    )
    return {"collected": True, "status": int(status), "truncated": truncated,
            "material": material, "duplicate": bool(material.get("duplicate"))}


def _default_transport() -> Any:
    """延后导入：`update.channels.base` 会拉起 curl_cffi/httpx，离线场景不必付这个代价。"""
    from src.core.update.channels.base import default_transport
    return default_transport()
