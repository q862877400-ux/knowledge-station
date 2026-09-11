"""gov.cn 公告检索 + PDF 存档适配器（govcn，F-02 降级链末端 / F-03 公告存档）。

命中公告时给 ``evidence_url``，并可 ``archive_pdf()`` 把公告 PDF 存档到
``<data_dir>/announcements/``（入库 ``doc_meta.doc_type='announcement'`` 由后续批次接线）。

mock 应答契约（离线表驱动）：
``{"http":200,"body":{"announcements":[{"title","url","date","pdf_url","no"}]}}``
命中规则：title 归一后包含标准号，或包含标准名（口语化公告标题兜底）。
"""
from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import Any

from src.core.config import get_settings
from src.core.update.channels.base import (
    UPD_ANNOUNCEMENT_NOT_FOUND,
    ChannelAdapter,
    ChannelResult,
    UpdateError,
    derive_change_type,
    norm_no,
    upd_log,
)

_STD_TOKEN_RE = re.compile(r"[A-Z]{1,4}(?:/[A-Z]{1,4})?\s*\d{4,5}\s*-\s*\d{4}")


def _clean_version(raw: str) -> str:
    """版本号排版归一：贴着 - / 的空白收敛、多空白合一（比较仍走 norm_no）。"""
    v = re.sub(r"\s*-\s*", "-", raw)
    v = re.sub(r"\s*/\s*", "/", v)
    return re.sub(r"\s+", " ", v).strip()

#: 最小合法 PDF 占位（可被 PDF 读取器打开为空文档）；仅当下载失败/无 pdf_url 时回退
_MINIMAL_PDF = (b"%PDF-1.4\n"
                b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
                b"trailer<</Size 3/Root 1 0 R>>\n%%EOF\n")


class GovcnAnnounceAdapter(ChannelAdapter):
    """公告渠道：发布/废止公告即证据；命中后记录 _last_hit 供 archive_pdf 使用。"""

    name = "govcn"
    SEARCH_URL = "https://sousuo.www.gov.cn/sousuo/search.shtml"

    def __init__(self, transport=None):  # noqa: ANN001 — 接口签名冻结
        super().__init__(transport)
        self._last_hit: dict | None = None

    # ------------------------------------------------------------ probe
    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        t0 = perf_counter()
        query = f"{standard_no} {standard_name}".strip()
        status, body = self._fetch(self.SEARCH_URL, params={"q": query})

        announcements: list[Any] = []
        if isinstance(body, dict):
            announcements = body.get("announcements") or []
        hit = self._pick(announcements, standard_no, standard_name)
        if hit is None:
            return self._miss(t0, standard_no, status, note=f"matches={len(announcements)}")

        title = str(hit.get("title") or "")
        version_m = _STD_TOKEN_RE.search(title)
        version = (_clean_version(str(hit.get("no") or ""))
                   or (_clean_version(version_m.group(0)) if version_m else None))

        if "废止" in title:
            legal_status: str | None = "withdrawn"
        elif version and norm_no(version) == norm_no(standard_no):
            legal_status = "effective"   # 公告指向的正是当前库内版本 → 现行
        else:
            legal_status = "upcoming"    # 新发布公告：已发布待施行（INS-D-02 按 🟢 对待）

        result = ChannelResult(
            channel=self.name,
            found=True,
            change_type=derive_change_type(standard_no, version, legal_status),
            legal_status=legal_status,
            latest_version=version,
            effective_date=(str(hit["date"]).strip() or None) if hit.get("date") else None,
            evidence_url=hit.get("url") or None,
            raw={"http": status, "announcement": hit},
        )
        self._last_hit = dict(hit)
        return self._log_probe(t0, standard_no, result)

    def _pick(self, announcements: list[Any], standard_no: str,
              standard_name: str) -> dict | None:
        target = norm_no(standard_no)
        name_norm = norm_no(standard_name)
        for a in announcements:
            if not isinstance(a, dict):
                continue
            title_norm = norm_no(str(a.get("title") or ""))
            if target and target in title_norm:
                return a
            if name_norm and name_norm in title_norm:
                return a
        return None

    # ------------------------------------------------------------ F-03 存档
    def archive_pdf(self, standard_no: str) -> str:
        """归档最近一次命中的公告 PDF 到 <data_dir>/announcements/，返回绝对路径。

        2026-08-26（P2-②）：实现真实下载（curl_cffi chrome 指纹 + %PDF 魔数校验），
        取代旧"最小合法占位 PDF"（此前 F-03 存档是空文件占位）。下载失败/无 pdf_url
        才回退占位并 WARN（保证巡检链路不因存档失败中断）。
        """
        if not self._last_hit:
            raise UpdateError("无已命中的公告可归档（须先 probe 命中）",
                              code=UPD_ANNOUNCEMENT_NOT_FOUND)
        data_dir = get_settings().data_dir / "announcements"
        data_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", standard_no).strip("_") or "announce"
        path = Path(data_dir) / f"{safe}.pdf"
        url = str(self._last_hit.get("pdf_url") or "").strip()
        if url:
            try:
                fetch_bytes = getattr(self.transport, "fetch_bytes", None)
                if fetch_bytes is not None:
                    status, content = fetch_bytes(url, timeout=30.0)
                    if status == 200 and content[:4] == b"%PDF" and len(content) > 1024:
                        path.write_bytes(content)
                        upd_log(self.trace_id, f"channel.{self.name}", "INFO",
                                "pdf_archived", standard_no=standard_no,
                                path=str(path), bytes=len(content))
                        return str(path)
                    upd_log(self.trace_id, f"channel.{self.name}", "WARN",
                            "pdf_download_unusable", standard_no=standard_no,
                            http=status, bytes=len(content or b""))
                else:
                    upd_log(self.trace_id, f"channel.{self.name}", "WARN",
                            "transport_no_fetch_bytes_fallback_placeholder",
                            standard_no=standard_no)
            except Exception as e:  # noqa: BLE001 - 存档失败不中断巡检
                upd_log(self.trace_id, f"channel.{self.name}", "WARN",
                        "pdf_download_failed_fallback_placeholder",
                        standard_no=standard_no, error=f"{type(e).__name__}: {e}")
        else:
            upd_log(self.trace_id, f"channel.{self.name}", "WARN",
                    "no_pdf_url_fallback_placeholder", standard_no=standard_no)
        # 回退：最小合法占位 PDF（可被 PDF 读取器打开为空文档），保证调用方拿到文件
        path.write_bytes(_MINIMAL_PDF)
        upd_log(self.trace_id, f"channel.{self.name}", "INFO", "pdf_archived_placeholder",
                standard_no=standard_no, path=str(path))
        return str(path)
