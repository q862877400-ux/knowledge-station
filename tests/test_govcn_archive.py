"""govcn_announce.archive_pdf 真实下载测试（2026-08-26，P2-②）。

修复前：archive_pdf 恒写"最小占位 PDF"（F-03 公告存档是空文件）；
修复后：有 pdf_url 时经 transport.fetch_bytes 下载并校验 %PDF 魔数，失败才回退占位。
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.update.channels.govcn_announce import GovcnAnnounceAdapter


class MockBytesTransport:
    def __init__(self, status=200, content=None):
        # 真实 PDF >1KB；默认 mock 一个超过大小守卫的合法头
        self._status = status
        self._content = (content if content is not None
                         else b"%PDF-1.4\n" + b"0" * 2048 + b"\n%%EOF")
        self.calls = []

    def fetch(self, url, **kw):
        return 200, {"announcements": []}

    def fetch_bytes(self, url, **kw):
        self.calls.append(url)
        return self._status, self._content


@pytest.fixture()
def announce(tmp_path, monkeypatch):
    import src.core.update.channels.govcn_announce as mod
    monkeypatch.setattr(mod, "get_settings",
                        lambda: SimpleNamespace(data_dir=tmp_path))
    return tmp_path


def _hit():
    return {"title": "关于发布 GB 1-2020 的公告", "pdf_url": "https://gov.cn/x.pdf",
            "no": "GB 1-2020", "url": "https://gov.cn/a.html", "date": "2026-01-01"}


def test_archive_downloads_real_pdf(announce):
    real = b"%PDF-1.4\n%real content\n" + b"0" * 2048 + b"\n%%EOF"
    t = MockBytesTransport(content=real)
    a = GovcnAnnounceAdapter(transport=t)
    a._last_hit = _hit()
    p = Path(a.archive_pdf("GB 1-2020"))
    assert p.exists()
    assert p.read_bytes() == real
    assert t.calls == ["https://gov.cn/x.pdf"]


def test_archive_falls_back_placeholder_on_bad_content(announce):
    t = MockBytesTransport(content=b"<html>not a pdf</html>")
    a = GovcnAnnounceAdapter(transport=t)
    a._last_hit = _hit()
    p = Path(a.archive_pdf("GB 1-2020"))
    assert p.read_bytes().startswith(b"%PDF")  # 占位（仍可被 PDF 工具识别）
    assert p.read_bytes() != b"<html>not a pdf</html>"


def test_archive_falls_back_placeholder_without_url(announce):
    a = GovcnAnnounceAdapter(transport=MockBytesTransport())
    hit = _hit()
    hit["pdf_url"] = ""
    a._last_hit = hit
    p = Path(a.archive_pdf("GB 1-2020"))
    assert p.read_bytes().startswith(b"%PDF")
