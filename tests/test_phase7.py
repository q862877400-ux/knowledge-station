"""Phase 7 测试：差距分析（R-L11~13）/ 义务导出（R-L10）。"""
import pytest


@pytest.fixture()
def gap_db(db):
    """种入义务条款（应当型，两个领域）+ 一份覆盖一半义务的制度。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.domain.models import ClauseRevisionModel
    if db.execute("SELECT 1 FROM doc_meta WHERE doc_id='gd1'").fetchone():
        clause_repo.delete_document("gd1")
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="gd1", standard_no="GB GAP-2022", standard_name="G",
            short_code="g", current_revision_id="r", domain_tags=["消防"],
            file_path="g.pdf", file_hash="hg1"))
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id="g1", doc_id="gd1", clause_key="gk1",
            standard_no="GB GAP-2022", clause_number="4.1",
            content_text="消防通道应当保持畅通，不得堆放杂物。",
            knowledge_type="rule", modality="应当", modality_strength=3,
            page_start=1, page_end=1),
        ClauseRevisionModel(
            clause_revision_id="g2", doc_id="gd1", clause_key="gk2",
            standard_no="GB GAP-2022", clause_number="4.2",
            content_text="灭火器应当定期检查并保持完好有效。",
            knowledge_type="rule", modality="应当", modality_strength=3,
            page_start=1, page_end=1),
        ClauseRevisionModel(
            clause_revision_id="g3", doc_id="gd1", clause_key="gk3",
            standard_no="GB GAP-2022", clause_number="4.3",
            content_text="疏散指示标志应当清晰可见，应急照明应当完好。",
            knowledge_type="rule", modality="应当", modality_strength=3,
            page_start=1, page_end=1),
    ])
    yield db


POLICY_COVERING = ("第一章 消防管理总则\n"
                   "本公司消防通道应当保持畅通，禁止堆放任何杂物。\n"
                   "第二章 器材管理\n"
                   "灭火器每月检查一次，保持完好有效。\n"
                   "第三章 附则\n本制度自发布之日起施行。")
POLICY_SPARSE = ("第一章 行政管理制度\n"
                 "员工应当遵守考勤纪律。\n本制度自发布之日起施行。")


def test_import_policy_sections(gap_db):
    from src.core.compliance.gap_analysis import import_internal_policy
    out = import_internal_policy("消防管理制度", POLICY_COVERING)
    assert out["policy_id"].startswith("pol_")
    assert len(out["sections"]) >= 2, "应按章节切分"


def test_build_obligations(gap_db):
    from src.core.compliance.gap_analysis import build_obligations
    n = build_obligations()
    assert n >= 3
    rows = gap_db.execute("SELECT COUNT(*) FROM legal_obligation").fetchone()[0]
    assert rows >= 3


def test_gap_analysis_verdicts(gap_db):
    from src.core.compliance.gap_analysis import (
        import_internal_policy, build_obligations, run_gap_analysis)
    build_obligations()
    pol = import_internal_policy("消防管理制度", POLICY_COVERING)
    out = run_gap_analysis(pol["policy_id"])
    verdicts = {r["verdict"] for r in out["results"]}
    assert "green" in verdicts, "消防通道义务应被制度覆盖"
    assert "yellow" in verdicts, "灭火器义务部分覆盖"
    # 疏散指示/应急照明未覆盖 → 红或黄
    assert out["counts"]["red"] + out["counts"]["yellow"] + out["counts"]["green"] ==         len(out["results"])
    row = gap_db.execute(
        "SELECT red_count, yellow_count, green_count FROM review_task WHERE task_id=?",
        (out["task_id"],)).fetchone()
    assert row["red_count"] == out["counts"]["red"]


def test_gap_analysis_red_when_no_coverage(gap_db):
    from src.core.compliance.gap_analysis import (
        import_internal_policy, build_obligations, run_gap_analysis)
    build_obligations()
    pol = import_internal_policy("行政制度", POLICY_SPARSE)
    out = run_gap_analysis(pol["policy_id"])
    reds = [r for r in out["results"] if r["verdict"] == "red"]
    assert len(reds) >= 2, "消防类义务在无关制度中应判缺失(red)"
    assert all("整改" in r["suggestion"] or "新增" in r["suggestion"] for r in reds)


def test_gap_api_flow(gap_db, client):
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    from src.core.compliance.gap_analysis import build_obligations
    build_obligations()
    r = c.post("/api/v1/compliance/policies", headers=h,
               json={"policy_name": "API制度", "policy_text": POLICY_COVERING})
    pid = r.json()["data"]["policy_id"]
    r = c.post("/api/v1/compliance/gap-analysis", headers=h, json={"policy_id": pid})
    assert r.status_code == 200
    data = r.json()["data"]
    assert "counts" in data and "results" in data
    # 报告导出（R-L13 Word）
    r = c.post(f"/api/v1/export/review/{data['task_id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["name"].endswith(".docx")


def test_obligation_export_docx(gap_db, client):
    from src.core.compliance.obligation import generate_obligation_list
    out = generate_obligation_list("消防管理", top_k=5)
    c, token = client
    r = c.post(f"/api/v1/export/obligations/{out['list_id']}",
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["name"].endswith(".docx")


@pytest.mark.parametrize("path", ["/api/v1/export/citations"])
def test_export_citations_body_contract(client, path):
    """`POST /export/citations` 的 **HTTP 层**契约（§10.76）。

    为什么补这一组：这条端点此前**没有 HTTP 测试**，而本步改了它**取 body 的方式**
    （`async def` + `await request.json()` → `def` + 签名取 body，因为随后就要跑
    python-docx 落盘、必须留在线程池里）。改法带一个**语义变化**，必须钉住：

    * **没有 body** ⇒ 照常 200（`citation_text` 是空证据块的文本、`docx` 为 None）；
    * **非法 JSON** ⇒ **422**（以前被 `except` 吞成空 body 照常 200 —— 这是有意的收紧，
      与 §10.71 的 `/report/effect/export` 同口径）。
    """
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    r = c.post(path, headers=h)
    assert r.status_code == 200, r.text
    assert "citation_text" in r.json()["data"]
    # 有证据时的正常路径（给一个真实条款 id）
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    row = conn.execute("SELECT clause_revision_id FROM clause_revision LIMIT 1").fetchone()
    if row is not None:
        r2 = c.post(path, headers=h,
                    json={"query": "消防", "clause_revision_ids": [row["clause_revision_id"]]})
        assert r2.status_code == 200, r2.text
        assert r2.json()["data"]["docx"]
    bad = c.post(path, content=b"{not json",
                 headers={**h, "Content-Type": "application/json"})
    assert bad.status_code == 422, bad.text
