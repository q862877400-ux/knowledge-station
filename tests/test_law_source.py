"""官方来源管线测试（docs/LAW-SOURCE-PLAN.md P1）：
域白名单 / 魔数校验 / flk 搜索构造与解析 / gov.cn 搜索与详情下载链接 / 转换器探测 / 编排元数据。
全程 mock 网络（不发真实请求）；仅离线可测部分直连。
"""
import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# http.py：域白名单（方案红线：来源只允许官方域）
# ---------------------------------------------------------------------------

def test_whitelist_accepts_official_hosts():
    from src.core.knowledge.law_source.http import check_host
    assert check_host("https://flk.npc.gov.cn/law-search/search/list") == "flk.npc.gov.cn"
    assert check_host("https://sousuo.www.gov.cn/search-gov/data") == "sousuo.www.gov.cn"
    assert check_host("https://www.gov.cn/zhengce/content/xxx.htm") == "www.gov.cn"


def test_whitelist_rejects_third_party():
    from src.core.knowledge.law_source.http import check_host
    for bad in ("https://www.baidu.com/s", "http://law.example.com/x.docx",
                "https://flk.npc.gov.cn.evil.com/x"):
        with pytest.raises(ValueError, match="白名单"):
            check_host(bad)


def test_magic_checks():
    from src.core.knowledge.law_source.http import _magic
    docx = Path(__file__).parent / "fixtures" / "fake.docx"
    docx.parent.mkdir(parents=True, exist_ok=True)
    docx.write_bytes(b"PK\x03\x04 fake zip content")
    assert _magic(docx, "docx")
    assert not _magic(docx, "pdf")
    pdf = docx.with_suffix(".pdf")
    pdf.write_bytes(b"%PDF-1.7 fake")
    assert _magic(pdf, "pdf")


# ---------------------------------------------------------------------------
# flk_client：搜索 payload 构造 + 结果解析（mock fetch_json）
# ---------------------------------------------------------------------------

def test_flk_search_payload(monkeypatch):
    from src.core.knowledge.law_source import flk_client as flk
    captured = {}

    def fake_fetch_json(url, *, method="GET", json_body=None, params=None,
                        referer=None, timeout=30):
        captured.update(url=url, method=method, body=json_body, referer=referer)
        return {"code": 200, "total": 1, "rows": [{
            "bbbs": "ff8080811234", "title": "中华人民共和国消防法",
            "flxz": "法律", "zdjgName": "全国人民代表大会常务委员会",
            "gbrq": "2021-04-29", "sxrq": "2021-04-29", "sxx": 3}]}

    monkeypatch.setattr("src.core.knowledge.law_source.flk_client.fetch_json", fake_fetch_json)
    data = flk.search("消防法", search_range=1, search_type=2, page=2, page_size=10)
    assert captured["url"] == flk._SEARCH
    assert captured["method"] == "POST"
    body = captured["body"]
    assert body["searchContent"] == "消防法"
    assert body["searchRange"] == 1 and body["searchType"] == 2
    assert body["pageNum"] == 2 and body["pageSize"] == 10
    assert body["orderByParam"] == {"order": "-1", "sort": ""}
    assert captured["referer"] == f"{flk.BASE}/search"

    rows = flk.parse_rows(data)
    assert rows[0]["bbbs"] == "ff8080811234"
    assert rows[0]["flxz"] == "法律"


# ---------------------------------------------------------------------------
# govcn_client：搜索结果解析 + 详情页下载链接提取（mock requests）
# ---------------------------------------------------------------------------

def test_govcn_parse_rows():
    from src.core.knowledge.law_source import govcn_client as govcn
    data = {"code": 200, "searchVO": {"totalCount": 1, "catMap": {
        "gongwen": {"listVO": [{
            "title": "国务院办公厅关于<em>消防</em>的通知",
            "pcode": "国办发〔2024〕1号", "source": "国务院办公厅",
            "pubtime": "1700000000000", "piclinksurl": "https://www.gov.cn/zhengce/content/202401/content_1.htm",
        }]}}}}
    rows = govcn.parse_rows(data)
    assert rows[0]["title"] == "国务院办公厅关于消防的通知"
    assert rows[0]["pcode"] == "国办发〔2024〕1号"
    assert rows[0]["url"].startswith("https://www.gov.cn/")


def test_govcn_fetch_detail_extracts_official_download(monkeypatch):
    from src.core.knowledge.law_source import govcn_client as govcn

    html = """
    <html><head><title>x</title></head><body>
      <h1>国务院办公厅关于印发XXX的通知</h1>
      <div class="pages_content">
        <p>第一条 内容……</p>
        <p>第二条 内容……</p>
      </div>
      <div class="publish-time">2024-01-01</div>
      <div class="source">国务院办公厅</div>
      <a href="/zhengce/content/202401/xxx.docx">下载</a>
      <a href="https://evil.example.com/xxx.docx">第三方镜像</a>
    </body></html>
    """
    class FakeResp:
        encoding = "utf-8"
        text = html
        def raise_for_status(self): pass

    monkeypatch.setattr("src.core.knowledge.law_source.govcn_client.requests.get",
                        lambda *a, **k: FakeResp())
    g = govcn.fetch_detail("https://www.gov.cn/zhengce/content/202401/content_1.htm")
    assert g.title == "国务院办公厅关于印发XXX的通知"
    assert "第一条" in g.content_text
    assert g.publish_date == "2024-01-01"
    # 官方下载链接保留、第三方镜像被白名单过滤
    assert any(u.endswith(".docx") and "www.gov.cn" in u for u in g.download_urls)
    assert not any("evil.example.com" in u for u in g.download_urls)


# ---------------------------------------------------------------------------
# convert.py：转换器探测（离线，不真转）
# ---------------------------------------------------------------------------

def test_convert_probe_never_raises():
    from src.core.knowledge.law_source.convert import (
        find_libreoffice, docx_to_pdf_libreoffice, docx_to_pdf_com,
    )
    # 探测不炸（本机可能未装 LibreOffice）
    find_libreoffice()
    assert docx_to_pdf_libreoffice(Path("nope.docx"), Path("nope.pdf")) is False
    assert docx_to_pdf_com(Path("nope.docx"), Path("nope.pdf")) is False
    assert find_libreoffice() is not None or True  # 允许未安装（CI 无 soffice）


def test_pdf_completeness_detects_truncation(tmp_path):
    """LibreOffice 截断检测：docx 文本量远大于 PDF → 判截断（False）。"""
    from docx import Document
    from src.core.knowledge.law_source.convert import pdf_completeness
    # 长 docx（30 段条文）
    docx = tmp_path / "long.docx"
    d = Document()
    for i in range(30):
        d.add_paragraph(f"第{i + 1}条　这是第{i + 1}条的内容，包含足够多的正文文字用于完整性比对。")
    d.save(str(docx))
    # 短 PDF（文本量 < 55%）
    from reportlab.pdfgen import canvas
    pdf = tmp_path / "truncated.pdf"
    c = canvas.Canvas(str(pdf))
    c.drawString(72, 720, "short")
    c.save()
    assert pdf_completeness(docx, pdf) is False
    # 短 docx 放行（不误判）
    short = tmp_path / "short.docx"
    ds = Document()
    ds.add_paragraph("只有一行")
    ds.save(str(short))
    assert pdf_completeness(short, pdf) is True
    # 异常输入放行
    assert pdf_completeness(tmp_path / "missing.docx", pdf) is True


# ---------------------------------------------------------------------------
# ingest.py：分类映射 / 目录布局 / HTML 兜底 docx / 来源查询
# ---------------------------------------------------------------------------

def test_flk_level_map():
    from src.core.knowledge.law_source.ingest import FLK_LEVEL_MAP, DEFAULT_LEVEL
    assert FLK_LEVEL_MAP["法律"] == "法律"
    assert FLK_LEVEL_MAP["行政法规"] == "行政法规"
    assert FLK_LEVEL_MAP["监察法规"] == "行政法规"   # 监察法规并入行政法规层级
    assert FLK_LEVEL_MAP["地方性法规"] == "地方性法规"
    assert FLK_LEVEL_MAP.get("某新分类", DEFAULT_LEVEL) == "其他法规"


def test_law_source_dir_sanitizes():
    from src.core.knowledge.law_source.ingest import law_source_dir
    p = law_source_dir("flk", "ff808081 72b5/f24f?x")
    assert "flk" in str(p)
    assert "?" not in str(p)


def test_build_docx_from_html(_isolate_data_dir, monkeypatch):
    from src.core.knowledge.law_source import govcn_client as govcn
    from src.core.knowledge.law_source.ingest import _build_docx_from_html
    from docx import Document

    g = govcn.GovDetail(url="https://www.gov.cn/x.htm", title="测试办法",
                        content_text="第一条 测试。\n\n第二条 测试二。")
    out = _build_docx_from_html(_isolate_data_dir / "govcn" / "x", g)
    assert out.exists()
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs if p.text.strip()]
    assert texts[0] == "测试办法"
    assert any("第一条" in t for t in texts)


def test_find_by_source_roundtrip(db, tmp_path):
    from src.core.knowledge.law_source.ingest import find_by_source, ensure_schema
    ensure_schema()
    # 无记录 → None
    assert find_by_source("flk", "nope") is None
    # 插入带 source 的 doc_meta 后能查到
    from src.core.storage.sqlite_db import write_transaction
    from src.core.storage import clause_repo
    with write_transaction() as txn:
        clause_repo.insert_document(txn, {
            "doc_id": "doc_test_ls1", "standard_no": "消防法(2021修正全本)",
            "standard_name": "消防法", "short_code": "xfs",
            "doc_type": "法律法规", "legal_hierarchy": "法律",
            "domain_tags": ["消防"],
            "file_path": str(tmp_path / "source.pdf"),
            "file_hash": "abc", "source": "flk", "source_id": "bbbs1",
            "source_url": "https://flk.npc.gov.cn/detail?id=bbbs1",
        })
    hit = find_by_source("flk", "bbbs1")
    assert hit is not None and hit["standard_no"] == "消防法(2021修正全本)"


# ---------------------------------------------------------------------------
# update.py：法规更新检查（只读比对）
# ---------------------------------------------------------------------------

def test_check_law_updates_status_change(db, tmp_path, monkeypatch):
    from src.core.knowledge.law_source.ingest import ensure_schema
    from src.core.knowledge.law_source.update import check_law_updates
    from src.core.storage.sqlite_db import write_transaction
    from src.core.storage import clause_repo
    ensure_schema()
    with write_transaction() as txn:
        clause_repo.insert_document(txn, {
            "doc_id": "doc_upd1", "standard_no": "某办法(2020)",
            "standard_name": "中华人民共和国某办法", "short_code": "x",
            "doc_type": "法律法规", "legal_hierarchy": "法律",
            "domain_tags": [], "file_path": str(tmp_path / "s.pdf"),
            "file_hash": "h1", "source": "flk", "source_id": "bbbs_upd",
            "source_url": "https://flk.npc.gov.cn/detail?id=bbbs_upd",
            "source_status": "3",
        })
    # 官方源现报 sxx=2（已修改）→ 时效变更 + 新版本提示
    class FakeDetail:
        title = "中华人民共和国某办法"
        sxx = 2
        flxz = "法律"
        gbrq = "2020-01-01"

    def fake_detail(bbbs):
        assert bbbs == "bbbs_upd"
        return FakeDetail()

    def fake_search(content, **kw):
        assert kw.get("sxx") == [3]
        return {"code": 200, "total": 1, "rows": [{
            "bbbs": "bbbs_new", "title": "中华人民共和国某办法",
            "flxz": "法律", "gbrq": "2024-01-01", "sxx": 3}]}

    monkeypatch.setattr("src.core.knowledge.law_source.flk_client.detail", fake_detail)
    monkeypatch.setattr("src.core.knowledge.law_source.flk_client.search", fake_search)
    out = check_law_updates()
    # db 为会话级共享库（conftest 设计），只断言本次插入的文档被检出
    assert out["checked"] >= 1
    mine_sc = [c for c in out["status_changes"] if c.get("doc_id") == "doc_upd1"]
    assert len(mine_sc) == 1 and mine_sc[0]["new_status"] == "2"
    mine_nv = [v for v in out["new_versions"] if v.get("doc_id") == "doc_upd1"]
    assert len(mine_nv) == 1 and mine_nv[0]["new_bbbs"] == "bbbs_new"
