"""T04 检索测试：六通道命中、RRF 排序、时效过滤、向量检索。"""
import pytest

from src.core.domain.models import ClauseRevisionModel
from src.core.storage import clause_repo
from src.core.storage.sqlite_db import init_schema, get_db_connection, close_thread_connection


def _clause(cid: str, no: str, text: str, doc: str = "d1", standard: str = "GB 50016-2022",
            modality: str | None = None, subject: str | None = None,
            behavior_scope: str | None = None, ktype: str = "rule",
            legal_status_of_doc: str = "effective") -> ClauseRevisionModel:
    return ClauseRevisionModel(
        clause_revision_id=cid, doc_id=doc, clause_key=f"key_{cid}",
        standard_no=standard, clause_number=no, title=None, content_text=text,
        knowledge_type=ktype, modality=modality,
        modality_strength={"严禁": 5, "不应": 4, "应": 3, "可以": 1}.get(modality),
        subject=subject, behavior_scope=behavior_scope,
        legal_status=legal_status_of_doc, page_start=1, page_end=1)


@pytest.fixture(scope="session")
def seeded_db(_isolate_data_dir):
    from src.core import config
    config.reset_settings()
    # 独占干净库：逐表 DROP 再建（DELETE sqlite_master 会残留数据页且连接缓存失效，禁用）
    conn = get_db_connection()
    from src.core.storage.sqlite_db import load_vec_extension
    load_vec_extension(conn)  # DROP clause_vec 虚拟表需要 vec0 扩展
    for (t,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
        conn.execute(f'DROP TABLE IF EXISTS "{t}"')
    conn.commit()
    init_schema()

    docs = [
        dict(doc_id="d1", standard_no="GB 50016-2022", standard_name="建筑设计防火规范",
             short_code="GB50016", current_revision_id="r1", domain_tags=["建筑", "消防"],
             file_path="gb.pdf", file_hash="h1"),
        dict(doc_id="d2", standard_no="民法典", standard_name="中华人民共和国民法典",
             short_code="民F", current_revision_id="r2", domain_tags=["合同"],
             file_path="minfadian.pdf", file_hash="h2"),
        dict(doc_id="d3", standard_no="GB 50016-2014", standard_name="建筑设计防火规范(旧)",
             short_code="GB50016-2014", current_revision_id="r3",
             legal_status="superseded", superseded_by="d1",
             domain_tags=["建筑"], file_path="gb_old.pdf", file_hash="h3"),
    ]
    for d in docs:
        clause_repo.insert_document(conn, d)

    clause_repo.insert_clauses([
        _clause("c1", "5.2.3", "高层民用建筑之间的防火间距不应小于13m"),
        _clause("c2", "6.4.2", "封闭楼梯间应设置乙级防火门"),
        _clause("c3", "6.4.2", "封闭楼梯间应设置乙级防火门", doc="d3",
                standard="GB 50016-2014", legal_status_of_doc="superseded"),
        _clause("c4", "第496条", "格式条款是当事人为了重复使用而预先拟定的条款", doc="d2",
                standard="民法典", ktype="legal", subject="当事人",
                behavior_scope="合同 格式条款"),
        _clause("c5", "第29条", "处理敏感个人信息应当取得个人的单独同意", doc="d2",
                standard="民法典", ktype="legal", modality="应当", subject="个人信息处理者",
                behavior_scope="个人信息 敏感个人信息 单独同意"),
        _clause("c6", "3.2.1", "严禁采用可燃材料作保温层", modality="严禁"),
    ])
    yield conn
    close_thread_connection()
    config.reset_settings()


def test_exact_channel_hit(seeded_db):
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    res = perform_hybrid_search("查 5.2.3", top_k=5, channels=["exact"])
    assert [r.clause_revision_id for r in res] == ["c1"]


def test_exact_superseded_excluded(seeded_db):
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    res = perform_hybrid_search("查 6.4.2", top_k=5, channels=["exact"])
    ids = [r.clause_revision_id for r in res]
    assert "c3" not in ids, "默认检索不应返回已废止条款"
    assert "c2" in ids
    res_all = perform_hybrid_search("查 6.4.2", top_k=5, channels=["exact"],
                                    include_superseded=True)
    assert "c3" in [r.clause_revision_id for r in res_all]


def test_fts_channel(seeded_db):
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    res = perform_hybrid_search("防火间距 多少", top_k=5, channels=["fts"])
    assert any(r.clause_revision_id == "c1" for r in res)


def test_modality_channel(seeded_db):
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    res = perform_hybrid_search("严禁 可燃材料", top_k=5,
                                channels=["modality"], modality_filter="严禁")
    assert any(r.clause_revision_id == "c6" for r in res)


def test_legal_element_channel(seeded_db):
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    res = perform_hybrid_search("经营者的义务", top_k=5,
                                channels=["legal_element"], subject_filter="个人信息处理者")
    assert any(r.clause_revision_id == "c5" for r in res)


def test_behavior_scope_channel(seeded_db):
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    res = perform_hybrid_search("人脸数据收集合规", top_k=5,
                                channels=["behavior_scope"],
                                behavior_scope_filter="敏感个人信息")
    assert any(r.clause_revision_id == "c5" for r in res)


def test_vec_channel(seeded_db):
    pytest.importorskip("fastembed")
    from src.core.retrieval import embedder
    if not embedder.is_available():
        pytest.skip("向量引擎不可用 (R30 降级路径)")
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    res = perform_hybrid_search("两栋楼之间防止火灾蔓延的间距要求", top_k=5, channels=["vec"])
    assert res, "向量检索应有结果"
    assert any(r.clause_revision_id == "c1" for r in res[:3]), "语义查询应命中防火间距条款"


def test_rrf_exact_beats_fts(seeded_db):
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    res = perform_hybrid_search("5.2.3 防火间距", top_k=3,
                                channels=["exact", "fts"])
    assert res[0].clause_revision_id == "c1", "精确命中应置顶"


def test_query_modality_extraction(seeded_db):
    from src.core.retrieval.hybrid_engine import extract_modality_from_query
    assert extract_modality_from_query("哪些情况严禁使用") == "严禁"
    assert extract_modality_from_query("防火间距") is None


def test_search_with_details(seeded_db):
    from src.core.retrieval.hybrid_engine import search_with_details
    out = search_with_details("严禁使用可燃材料", top_k=3,
                              channels=["exact", "fts", "modality"])
    assert out["debug"]["modality_filter"] == "严禁"
    assert out["debug"]["result_count"] >= 1
