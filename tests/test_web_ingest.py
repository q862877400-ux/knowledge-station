"""部委公告 → 知识库正文入库（切片②）测试：效力档判定 / 正文抽取 / 真入库 / 去重 / 诚实归因。

全部离线：transport 注入（零联网）+ conftest 的 KS_DATA_DIR 会话隔离。
"""
from __future__ import annotations

from src.core.update import web_ingest


class _FakeTransport:
    def __init__(self, pages: dict[str, tuple[int, str]]):
        self.pages = pages
        self.calls: list[str] = []

    def fetch(self, url: str, **kw):
        self.calls.append(url)
        return self.pages.get(url, (404, "not found"))


_DETAIL = """<html><head><title>应急管理部令（第23号）社会消防技术服务管理规定</title></head>
<body>
<div class="nav">首页 机构 新闻</div>
<script>var x = 1;</script>
<div class="TRS_Editor">
<p>第一条 为了加强社会消防技术服务管理，制定本规定。</p>
<p>第二条 本规定适用于在中华人民共和国境内从事社会消防技术服务活动的机构。</p>
</div>
<div class="footer">版权所有</div></body></html>"""

_ANNOUNCE_NO_CLAUSE = """<html><body><div class="TRS_Editor">
<p>为推动危险化学品经营许可证管理改革，现就有关事项公告如下：自本公告发布之日起施行。</p>
</div></body></html>"""


def test_web_i01_classify_status_priority():
    """效力档判定：**先认"征求意见稿"**（标题里同时出现"办法"也要判成仅参考）。"""
    assert web_ingest.classify_status("关于公开征求《危险化学品经营许可证管理办法(修订征求意见稿)》意见的通知") == "draft"
    assert web_ingest.classify_status("应急管理部关于公开征求《中华人民共和国自然灾害防治法（草案征求意见稿）》意见的通知") == "draft"
    assert web_ingest.classify_status("中华人民共和国应急管理部令（第23号）社会消防技术服务管理规定") == "effective"
    assert web_ingest.classify_status("商务部等5部门关于调整《向特定国家（地区）出口易制毒化学品管理目录》的公告") == "effective"
    assert web_ingest.classify_status("关于废止 AQ 3016—2008 等三项行业标准的公告") == "withdrawn"
    # 层级也认征求意见稿这一档
    assert web_ingest.classify_hierarchy("关于公开征求《森林草原火灾数据统计规范》（征求意见稿）意见的通知") == "征求意见稿"
    assert web_ingest.classify_hierarchy("中华人民共和国应急管理部令（第23号）社会消防技术服务管理规定") == "规章"


def test_web_i02_extract_body_text_drops_chrome():
    """正文抽取：**去掉导航/脚本/页脚**，只留正文，且段落之间保留换行。"""
    text = web_ingest.extract_body_text(_DETAIL)
    assert "第一条 为了加强社会消防技术服务管理" in text
    assert "第二条 本规定适用于" in text
    assert "var x = 1" not in text and "版权所有" not in text and "首页 机构 新闻" not in text
    assert "\n" in text
    assert web_ingest.page_title(_DETAIL).startswith("应急管理部令（第23号）")
    assert web_ingest.extract_body_text("") == ""


def test_web_i03_ingest_writes_document_with_source_url(db):
    """真入库：**令/规章**那种有"第X条"的正文走 `law_text` 通道，
    落库带**来源 URL**（溯源）与**效力档**，条款切分说得清；重复入库去重。"""
    url = "https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/202609/t20260921_717182.shtml"
    tp = _FakeTransport({url: (200, _DETAIL)})
    out = web_ingest.ingest_announcement("中华人民共和国应急管理部令（第23号）社会消防技术服务管理规定",
                                        url, published_date="2026-09-21", transport=tp)
    assert out["status"] == "ingested", out
    assert out["legal_status"] == "effective"
    assert out["ingest"]["status"] not in ("error", "duplicate"), out["ingest"]

    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    row = conn.execute("SELECT doc_id, standard_no, doc_type, source_url, legal_status"
                       " FROM doc_meta WHERE source_url=?", (url,)).fetchone()
    assert row is not None, "doc_meta 里应当有一行带这个来源 URL"
    assert row["source_url"] == url and row["legal_status"] == "effective"
    assert row["doc_type"] == "法律法规"
    n = conn.execute("SELECT COUNT(*) c FROM clause_revision WHERE doc_id=?", (row["doc_id"],)).fetchone()["c"]
    assert n >= 2, f"两条'第X条'应当切出来（实测 {n}）"

    # 同一条再入一次 ⇒ 按正文哈希去重（不新建文档）
    again = web_ingest.ingest_announcement("中华人民共和国应急管理部令（第23号）社会消防技术服务管理规定",
                                          url, transport=tp)
    assert again["status"] == "ingested" and again["ingest"]["status"] == "duplicate", again
    total = conn.execute("SELECT COUNT(*) c FROM doc_meta WHERE source_url=?", (url,)).fetchone()["c"]
    assert total == 1, "去重后仍然只该有一行"


def test_web_i04_no_clause_announcement_uses_single_clause(db):
    """**没有"第X条"的公告**（政府站常见）也要能入库：整篇作一条（编号"全文"），
    否则业主那张表里大半条目会被"未识别到条文"挡在门外。"""
    url = "https://www.mem.gov.cn/gk/tzgg/202609/t20260922_717309.shtml"
    tp = _FakeTransport({url: (200, _ANNOUNCE_NO_CLAUSE)})
    out = web_ingest.ingest_announcement("商务部等5部门关于调整《向特定国家（地区）出口易制毒化学品管理目录》的公告",
                                        url, published_date="2026-09-22", transport=tp)
    assert out["status"] == "ingested", out
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    row = conn.execute("SELECT doc_id FROM doc_meta WHERE source_url=?", (url,)).fetchone()
    assert row is not None
    n = conn.execute("SELECT COUNT(*) c FROM clause_revision WHERE doc_id=?", (row["doc_id"],)).fetchone()["c"]
    assert n == 1, f"整篇作一条（实测 {n}）"


def test_web_i05_draft_refused_honestly_and_failures(db):
    """**征求意见稿**：切片③ 的枚举迁移还没做 ⇒ 必须**如实拒绝**（不写非法值、也不静默丢）；
    取不到页 / 空正文同样诚实归因。"""
    draft_url = "https://www.mem.gov.cn/gk/tzgg/202609/t20260921_717221.shtml"
    tp = _FakeTransport({draft_url: (200, _ANNOUNCE_NO_CLAUSE)})
    out = web_ingest.ingest_announcement("关于公开征求《危险化学品经营许可证管理办法(修订征求意见稿)》意见的通知",
                                        draft_url, transport=tp)
    assert out["status"] == "skipped" and out["reason"] == "draft_pending_schema", out
    assert out["legal_status"] == "draft"
    from src.core.storage.sqlite_db import get_db_connection
    assert get_db_connection().execute(
        "SELECT COUNT(*) c FROM doc_meta WHERE source_url=?", (draft_url,)).fetchone()["c"] == 0

    missing = web_ingest.ingest_announcement("某公告", "https://x.example.com/none.shtml", transport=tp)
    assert missing["status"] == "failed" and missing["reason"] == "http_404", missing

    empty_url = "https://x.example.com/empty.shtml"
    tp2 = _FakeTransport({empty_url: (200, "<html><body><div class='c'></div></body></html>")})
    empty = web_ingest.ingest_announcement("某公告", empty_url, transport=tp2)
    assert empty["status"] == "skipped" and empty["reason"] == "empty_body", empty
