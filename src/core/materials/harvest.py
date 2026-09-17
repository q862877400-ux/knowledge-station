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
2. **抓取**走 `update.channels.base.default_transport()`（curl_cffi 浏览器指纹，
   httpx 兜底），契约 `fetch(url, timeout=…) -> (status, body)`。**不自造 HTTP 客户端**。
3. **HTML→文本**走 `text_utils.html_to_text`（页面级规范实现；见那里关于
   "与 `clause_health_html_to_text` 的精确关系"的说明）。

## 界线（谁负责什么）
- 本模块**只做"一次抓取 + 登记"**，**不是爬虫**：不排队、不重试、不递归跟链接、
  不限速、不做 robots/ToS 判断。**采集预算与频率上限仍未定**（方案 §11.4），
  所以这里刻意不提供批量入口——要批量，先定预算。
- 抓回来的东西**默认不可信**（交给 `collect_text` ⇒ T3 起、pending、`ephemeral`）。
- **不解析 PDF/附件**：正文非 HTML（如 PDF）时如实说明"没抓到正文"，
  而不是把二进制当文本塞进材料。⚠ 判据是**开头签名**（`text_utils.looks_like_binary`）——
  传输层已经把 Content-Type 丢了（见那里），所以这是启发式：**没有签名**的二进制认不出。

## 诚实边界
- 只在拿到 **2xx** 且正文（`str`）非空时才登记；其它情况如实返回 `status`/`reason`，
  **不建立空材料**（空材料会变成"盲签对象"）。
- 标题优先用调用方给的；否则从 `<title>` 取（粗正则）；再否则用 URL。
- `is_private_url` 自带已知局限（DNS rebinding 的 TOCTOU 窗口不设防，
  理由见其 docstring）——本模块**继承**那个局限，不另行声称更强。
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from src.core.materials import collect as co
from src.core.text_utils import html_to_text, looks_like_binary
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

    # ② 抓取（复用既有 transport；测试可注入）
    tp = transport if transport is not None else _default_transport()
    try:
        status, body = tp.fetch(target, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — 网络异常如实回报，不抛给上层
        return {"collected": False, "reason": f"抓取失败：{exc}"}

    if int(status) < 200 or int(status) >= 300:
        return {"collected": False, "status": int(status),
                "reason": f"HTTP {status}（不登记未成功取回的页面）"}
    if not isinstance(body, str):
        # JSON / 二进制（PDF 等）：**不把非文本当正文**
        return {"collected": False, "status": int(status),
                "reason": f"响应不是文本（{type(body).__name__}）——本模块不解析 PDF/JSON 附件"}

    text = html_to_text(body)
    if not text.strip():
        return {"collected": False, "status": int(status), "reason": "页面没有可提取的正文"}
    # 传输层把响应统一压成 `str`（Content-Type 在那里就丢了），所以"这不是网页正文"
    # 只能靠**开头字节**认——判据的所有者在 `text_utils.looks_like_binary`。
    # 实测踩到：`/x.pdf` 的 `%PDF-1.7` 头会被 `html_to_text` 原样当正文，
    # 登记成一条"看起来有内容、其实一个字都读不了"的材料（比空材料更坏）。
    if looks_like_binary(text):
        return {"collected": False, "status": int(status),
                "reason": "响应不是文本（看起来是 PDF/图片/压缩包等二进制容器）"
                          "——本模块不解析 PDF/附件"}

    truncated = len(text) > MAX_TEXT_CHARS
    if truncated:
        text = text[:MAX_TEXT_CHARS]

    resolved_title = (title or "").strip() or page_title(body) or urlparse(target).path or target

    note_parts = [p for p in [note] if p]
    note_parts.append(f"自采：HTTP {int(status)} 来自 {urlparse(target).hostname or '?'}"
                      + ("（正文已截断到上限）" if truncated else ""))

    material = co.collect_text(
        project_id, title=resolved_title, text=text, url=target,
        source_tier=source_tier, published_at=published_at,
        note="；".join(note_parts),
    )
    return {"collected": True, "status": int(status), "truncated": truncated,
            "material": material, "duplicate": bool(material.get("duplicate"))}


def _default_transport() -> Any:
    """延后导入：`update.channels.base` 会拉起 curl_cffi/httpx，离线场景不必付这个代价。"""
    from src.core.update.channels.base import default_transport
    return default_transport()
