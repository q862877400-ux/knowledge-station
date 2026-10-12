"""下载新版附件的**审批门**（spec 011 第 ③ 条，2026-10-12）。

## 为什么需要这一层（而不是直接下载）

`govcn_announce.archive_pdf()` 的下载能力**早就做好了**（curl_cffi chrome 指纹 +
`%PDF` 魔数 + 大小 >1024 校验，测试 `tests/test_govcn_archive.py`），
但**从来没接进生产链路** —— 实测 `update_change_event.archived_pdf_path` **0 / 6,471**，
`%APPDATA%\\KnowledgeStation\\announcements\\` 是**空目录**，`archive_pdf` 的调用点
**只有测试**。

本模块把"发现新版本"与"下载附件"接起来，**但必须经审批门** ——
`docs/NOT-DOING.md` 第 20 条写死：

> **仍然必须由人决定、仍然无旁路**，只是可以把"一份文档缺的十几部"**合并成一次问**。
> **不许**演化成"自动下载"或"默认同意"

⇒ 所以本模块的契约是：**`handle_download(approved=False)` 绝不下载**；
只有 `approved=True` 才调 `_do_download`。

## 判据不在这里（一个事实一个归属层）

- **`%PDF` 魔数 + 大小校验**：唯一所有者在 `govcn_announce.archive_pdf`，
  本模块**不另写一份**（`tests/test_channel_system_wiring.py` 有结构判据钉住）。
- **CCS 分类**：唯一所有者在 `ccs_fetcher`。
- **问句措辞**：唯一所有者在本模块（`download_ask_reason`）。

## 业主口径（2026-10-12）

> 「评审就是询问啊，又不是让用户全文看一遍，只是把抓下来的文件的来源和形态告诉用户，
> 让用户考虑是否下载，是本次引用还是入库」

⇒ 问句只给**来源 + 形态 + 用途**三样，**不给全文**。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _source_of(url: str) -> str:
    """从 URL 取主机名（问句里给用户看"从哪来"）。取不到就回原串。"""
    try:
        host = urlparse(str(url or "")).hostname or ""
    except Exception:  # noqa: BLE001
        host = ""
    return host or str(url or "")


def download_ask_reason(change: dict[str, Any]) -> str:
    """弹框问句（**唯一所有者**）：说清**来源 + 形态 + 用途**，不贴全文。

    业主口径（2026-10-12）：「只是把抓下来的文件的来源和形态告诉用户，
    让用户考虑是否下载，是本次引用还是入库」。
    """
    no = str(change.get("standard_no") or "").strip() or "（未知标准号）"
    title = str(change.get("title") or change.get("standard_name") or "").strip()
    url = str(change.get("evidence_url") or change.get("pdf_url") or "").strip()
    host = _source_of(url) if url else "（无来源地址）"

    head = f"要把《{title}》" if title else "要把这份文件"
    return (f"{head}（标准号 {no}）下载进知识库吗？\n"
            f"  来源：{host}\n"
            f"  形态：PDF 附件\n"
            f"  用途：同意后下载并留档，可作为该标准的原文依据；拒绝则不下载。\n"
            f"（你不需要通读全文，只要看来源和形态决定。）")


def handle_download(change: dict[str, Any], *, approved: bool) -> dict[str, Any]:
    """按审批结果处置。**`approved=False` 绝不下载**（NOT-DOING 第 20 条）。

    返回（**如实，不静默**）：
    - 拒绝：`{"downloaded": False, "reason": "用户拒绝下载", "ask": <问句>}`
    - 同意：`{"downloaded": True, "path": ..., ...}` 或
      `{"downloaded": False, "reason": <失败原因>}`

    ⚠ **不抛异常**：下载失败是**结果**不是异常（与 `harvest.collect_url` 同口径）——
    调用方（巡检线程）不该因为一份附件下不下来就崩。
    """
    ask = download_ask_reason(change)
    if not approved:
        logger.info("用户拒绝下载附件: %s", change.get("standard_no"))
        return {"downloaded": False, "reason": "用户拒绝下载", "ask": ask}
    try:
        out = _do_download(change)
    except Exception as exc:  # noqa: BLE001 — 下载失败是结果不是异常
        logger.warning("附件下载失败 %s: %s: %s",
                       change.get("standard_no"), type(exc).__name__, exc)
        return {"downloaded": False, "reason": f"{type(exc).__name__}: {exc}",
                "ask": ask}
    ok = bool((out or {}).get("ok"))
    if not ok:
        return {"downloaded": False, "ask": ask,
                "reason": str((out or {}).get("reason") or "下载未成功")}
    return {"downloaded": True, "ask": ask, "path": (out or {}).get("path")}


def _do_download(change: dict[str, Any]) -> dict[str, Any]:
    """真正去下（**复用** `govcn_announce.archive_pdf` 的实现与校验）。

    ⚠ 本函数**不自己写 `%PDF` 校验** —— 那是 `archive_pdf` 的唯一职责。
    这里只负责"把 change 里的信息喂给它"，**并识别它的占位回退**。

    ## ⚠⚠ 为什么要识别占位（2026-10-12 实测发现的真缺陷）

    `archive_pdf()` **无论成败都返回一个路径** —— 下载失败/内容不是 PDF 时，
    它回退写一个 **132 字节的最小合法 PDF 占位**（`_MINIMAL_PDF`），
    照样 `return str(path)`。它的 docstring 写明这是刻意的：
    "保证巡检链路不因存档失败中断"。

    ⇒ 但**调用方若只看"有没有路径"就会把占位当成功** —— 实测：
    拿一个返回 HTML 的详情页地址喂进去，`archive_pdf` 返回了路径，
    我第一版就据此报 `downloaded=True`（**假绿**：盘上是个 132 字节空壳，
    真 PDF 是 6.3 MB）。

    ⇒ 判据：**文件比占位大**才算真下到东西。占位的确切字节数是
    `govcn_announce._MINIMAL_PDF`（唯一所有者），这里**引用它**，不另抄一份。
    """
    from src.core.update.channels.govcn_announce import (
        GovcnAnnounceAdapter, _MINIMAL_PDF,
    )

    ch = GovcnAnnounceAdapter()
    # archive_pdf 要求"先 probe 命中"才肯归档（它自己会抛 UpdateError）。
    # 这里把巡检拿到的 evidence_url 当成命中信息喂进去。
    url = str(change.get("pdf_url") or change.get("evidence_url") or "").strip()
    if not url:
        return {"ok": False, "reason": "没有可下载的附件地址"}
    ch._last_hit = {"pdf_url": url, "title": change.get("title") or "",
                    "no": change.get("standard_no") or ""}
    path = ch.archive_pdf(str(change.get("standard_no") or ""))

    # ⚠ 识别占位回退：拿盘上的文件与 _MINIMAL_PDF 比字节数。
    #   相等（或更小）⇒ 那是占位，**不是真下载到的内容** ⇒ 如实报失败。
    try:
        size = Path(path).stat().st_size if path else 0
    except OSError:
        size = 0
    if size <= len(_MINIMAL_PDF):
        return {"ok": False, "path": path,
                "reason": (f"下载未成功（盘上是 {size} 字节的占位空壳，"
                           f"不是真 PDF）—— 该地址可能返回的是网页而非附件")}
    return {"ok": True, "path": path}
