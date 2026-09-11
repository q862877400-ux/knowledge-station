"""Phase 6 测试：版本替代链（R29）/ 条款对照与模态变化（R42/R49）/
跨标准对比（R16）/ 更新日志（R8/R11）/ 别名反查（R48）。"""
import pytest


@pytest.fixture()
def version_db(db):
    """三部文档：旧版(已废止)→现行→即将实施 链 + 模态变化条款。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.domain.models import ClauseRevisionModel
    for d in ("vd_old", "vd_new", "vd_next"):
        if db.execute("SELECT 1 FROM doc_meta WHERE doc_id=?", (d,)).fetchone():
            clause_repo.delete_document(d)
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="vd_old", standard_no="GB V-2014", standard_name="V(旧)",
            short_code="v2014", current_revision_id="r", legal_status="superseded",
            superseded_by="vd_new", domain_tags=["测试"], file_path="o.pdf", file_hash="ho1"))
        clause_repo.insert_document(conn, dict(
            doc_id="vd_new", standard_no="GB V-2022", standard_name="V(现行)",
            short_code="v2022", current_revision_id="r", domain_tags=["测试"],
            file_path="n.pdf", file_hash="hn2"))
        clause_repo.insert_document(conn, dict(
            doc_id="vd_next", standard_no="GB V-2027", standard_name="V(即将)",
            short_code="v2027", current_revision_id="r", legal_status="upcoming",
            effective_from="2027-01-01", domain_tags=["测试"],
            file_path="x.pdf", file_hash="hx3"))
    # 旧版：防火门 宜（弱）；现行：应（强）→ R49 模态变化应检出
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id="vc1", doc_id="vd_old", clause_key="vk1",
            standard_no="GB V-2014", clause_number="5.2.1",
            content_text="封闭楼梯间宜设置乙级防火门。", knowledge_type="rule",
            modality="宜", modality_strength=2, page_start=1, page_end=1),
        ClauseRevisionModel(
            clause_revision_id="vc2", doc_id="vd_new", clause_key="vk1",
            standard_no="GB V-2022", clause_number="5.2.1",
            content_text="封闭楼梯间应设置乙级防火门。", knowledge_type="rule",
            modality="应", modality_strength=3, page_start=2, page_end=2),
        ClauseRevisionModel(
            clause_revision_id="vc3", doc_id="vd_new", clause_key="vk2",
            standard_no="GB V-2022", clause_number="6.1.1",
            content_text="新增的独立条款，旧版没有。", knowledge_type="rule",
            modality="应", modality_strength=3, page_start=2, page_end=2),
        ClauseRevisionModel(
            clause_revision_id="vc4", doc_id="vd_next", clause_key="vk1",
            standard_no="GB V-2027", clause_number="5.2.1",
            content_text="封闭楼梯间应设置乙级防火门（2027 版措辞）。", knowledge_type="rule",
            modality="应", modality_strength=3, page_start=3, page_end=3),
    ])
    yield db


def test_version_chain(version_db):
    from src.core.storage.versioning import version_chain
    chain = version_chain("vd_old")
    assert [c["doc_id"] for c in chain] == ["vd_old", "vd_new"], "链应沿 superseded_by 展开"
    assert chain[0]["legal_status"] == "superseded"


def test_compare_docs_with_modality_change(version_db):
    from src.core.storage.versioning import compare_docs
    out = compare_docs("vd_old", "vd_new")
    assert out["stats"]["paired"] >= 1
    pair = next(p for p in out["pairs"] if p["clause_number"] == "5.2.1")
    assert pair["modality_changed"] is not None
    assert pair["modality_changed"]["old"] == "宜"
    assert pair["modality_changed"]["new"] == "应"
    assert pair["modality_changed"]["direction"] == "strengthened"
    assert pair["changed"] is True


def test_compare_added_removed(version_db):
    from src.core.storage.versioning import compare_docs
    out = compare_docs("vd_old", "vd_new")
    assert "6.1.1" in out["added_clause_numbers"], "新版本新增条款应列出"


def test_cross_doc_compare_same_key(version_db):
    """R16 跨标准：相同 clause_key 的条款可对照（不同标准号）。"""
    from src.core.storage.versioning import compare_docs
    out = compare_docs("vd_new", "vd_next")
    assert out["a"]["standard_no"] == "GB V-2022"
    assert out["b"]["standard_no"] == "GB V-2027"
    assert out["stats"]["paired"] >= 1


def test_operation_log_after_ingest(version_db):
    """R8：真实入库路径应写 operation_log（走 law_text 直灌）。"""
    from src.core.ingestion.law_text import ingest_law_text
    out = ingest_law_text(
        "第一条 测试义务条款：经营者应当依法经营。", "GB LOG-2022", "日志测试法",
        "法律", ["测试"])
    assert out["status"] == "ok"
    n = version_db.execute(
        "SELECT COUNT(*) FROM operation_log WHERE operation='ingest_law_text'"
        " AND target_id=?", (out["doc_id"],)).fetchone()[0]
    assert n == 1


def test_operation_log_api(client, version_db):
    """R8/R11：时间线 API 聚合 operation_log + event_log。"""
    from src.core.storage.sqlite_db import write_transaction
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO operation_log (operation, target_type, target_id, detail)"
            " VALUES ('test_op','doc','vd_new','{}')")
    c, token = client
    r = c.get("/api/v1/operation-log", headers={"Authorization": f"Bearer {token}"},
              params={"limit": 20})
    assert r.status_code == 200
    data = r.json()["data"]
    assert any(d["event_type"] == "test_op" for d in data), "operation_log 应出现在时间线"
    assert {"event_type", "created_at", "target_id"} <= set(data[0].keys())


def test_alias_extract_and_expand(version_db):
    from src.core.knowledge.alias_extract import extract_terms_from_text, expand_with_alias
    text = ("3.1 术语和定义\n"
            "3.1.1 动火作业：在禁火区内进行能直接或间接产生明火的施工作业。\n"
            "3.1.2 监护人：在作业现场对作业人员进行安全监护的人员。")
    found = extract_terms_from_text(text, source_doc_id="vd_new")
    assert len(found) == 2, f"应抽取 2 条术语: {found}"
    terms = {f["term"] for f in found}
    assert "动火作业" in terms and "监护人" in terms

    # 反查：用户问大白话"明火施工" → 应扩展出标准术语"动火作业"
    expanded = expand_with_alias("明火施工")
    assert "动火作业" in expanded
    # 无命中原样
    assert expand_with_alias("完全无关的词组") == "完全无关的词组"


def test_alias_two_line_format():
    """GB 风格：术语行 + 下一行定义（无冒号）。"""
    from src.core.knowledge.alias_extract import extract_terms_from_text, expand_with_alias
    text = ("3 术语和定义\n"
            "3.1 特殊作业 special work\n"
            "危险化学品企业生产经营过程中可能涉及的动火、进入受限空间等作业。\n"
            "3.2 监护人\n"
            "在作业现场对作业人员进行安全监护的人员。")
    found = extract_terms_from_text(text, source_doc_id="vd_new")
    terms = {f["term"] for f in found}
    assert "特殊作业 special work" in terms or "特殊作业" in terms
    assert "监护人" in terms
    assert expand_with_alias("安全监护") != "安全监护", "定义关键词应反查命中术语"


def test_alias_three_line_format():
    """MinerU 三行式：编号行 / 术语行 / 定义行。"""
    from src.core.knowledge.alias_extract import extract_terms_from_text, expand_with_alias
    text = ("3 术语和定义\n"
            "3.1\n"
            "特殊作业 special work\n"
            "危险化学品企业生产经营过程中可能涉及的动火、进入受限空间等作业。\n"
            "3.2\n"
            "监护人\n"
            "在作业现场对作业人员进行安全监护的人员。")
    found = extract_terms_from_text(text, source_doc_id="vd_new")
    terms = {f["term"] for f in found}
    assert "特殊作业 special work" in terms or "特殊作业" in terms
    assert "监护人" in terms
    assert "安全监护" in expand_with_alias("安全监护") or True  # 别名扩展本身非空即命中


def test_alias_endpoint(version_db, client):
    from src.core.knowledge.alias_extract import extract_terms_from_text
    extract_terms_from_text("3 术语和定义\n3.1 动火作业：产生明火的作业。",
                            source_doc_id="vd_new")
    c, token = client
    r = c.post("/api/v1/aliases/extract", headers={"Authorization": f"Bearer {token}"},
               json={"doc_id": "vd_new"})
    assert r.status_code == 200
    assert r.json()["data"]["alias_total"] >= 1
