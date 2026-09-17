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
    # ⚠ 逐表 DROP 必须**先关外键**（2026-09-17 材料平面引入 FK 后暴露）：
    # `sqlite_master` 是**创建顺序**，而 material_project 建在 material 之前 ⇒ 先 DROP
    # 被引用者、引用者还在，`PRAGMA foreign_keys=ON` 下直接 `FOREIGN KEY constraint failed`
    # （当时 10 个用例在 setup 阶段 ERROR）。"一次删光所有表"本来就与外键顺序无关，
    # 关掉外键再删才是正确做法；建完 schema 再打开。
    conn.execute("PRAGMA foreign_keys=OFF")
    for (t,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
        conn.execute(f'DROP TABLE IF EXISTS "{t}"')
    conn.commit()
    init_schema()
    conn.execute("PRAGMA foreign_keys=ON")

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


def test_null_legal_status_is_not_silently_excluded(seeded_db):
    """**NULL（未核验）≠ 已废止**：它也要能被精确命中抓到。

    ⚠ 这条是**独立复核 b8 的 LOW**：`NOT IN ('withdrawn','superseded')` 对 NULL 求值是
    **NULL**（不是 true）⇒ 未核验的条款（采集件走 Track L 入库后 `legal_status IS NULL`）
    会被**静默排除**在精确命中与模态召回之外。有意思的是：这恰好是**与 §10.44 相反的
    方向**——上层（`fetch_full_clause`）已经如实带出 NULL，而这条 SQL 通道又把它筛掉了，
    于是"未核验"在两条通道上得到两种待遇。
    反向断言同样重要：**已废止的仍然要被排除**（修复不能把那条边界一起放松）。
    """
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    clause_repo.insert_document(conn, dict(
        doc_id="d9", standard_no="GB 99999-2099", standard_name="采集件标准",
        short_code="GB99999", current_revision_id="r9", legal_status=None,
        file_path="collected.pdf", file_hash="h9"))
    clause_repo.insert_clauses([
        _clause("c9", "9.9.9", "采集件条款正文", doc="d9",
                standard="GB 99999-2099", legal_status_of_doc=None)])
    try:
        found = [r.clause_revision_id for r in
                 perform_hybrid_search("查 9.9.9", top_k=5, channels=["exact"])]
        assert "c9" in found, "未核验（NULL）的条款被静默排除了"
        # 模态通道同款 SQL，也要能命中
        model = perform_hybrid_search("查 9.9.9", top_k=5, channels=["modality"],
                                      modality_filter="严禁")
        assert isinstance(model, list)      # 只是别因为 NULL 报错/空集合异常
        gone = [r.clause_revision_id for r in
                perform_hybrid_search("查 6.4.2", top_k=5, channels=["exact"])]
        assert "c3" not in gone, "已废止条款不能被放回来"
    finally:
        clause_repo.delete_document("d9")


def test_unverified_clause_does_not_outrank_an_effective_one(seeded_db):
    """**未核验不许在通道内占优**（复核 b9 的 LOW-3，2026-09-18 修）。

    背景是同一条 SQL 上两个方向相反的修复：`NOT IN (…)` 对 NULL 求值是 NULL ⇒
    未核验条款曾被**静默排除**（b8 的 LOW，已修，把它们**放进来**）；而 SQLite 的
    `ORDER BY x` 把 **NULL 排在最前**，`rank` 又直接决定 `CHANNEL_WEIGHTS/(RRF_K+rank+1)`
    ⇒ 刚被放进来的未核验条款反而拿到**通道内最好的名次**。两个方向必须一致：
    §10.44 的口径是"未核验不得承重"。
    """
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    clause_repo.insert_document(conn, dict(
        doc_id="d11", standard_no="GB 11111-2020", standard_name="已核验标准",
        short_code="GB11111", current_revision_id="r11", legal_status="effective",
        file_path="verified.pdf", file_hash="h11"))
    clause_repo.insert_document(conn, dict(
        doc_id="d12", standard_no="GB 22222-2021", standard_name="采集件标准",
        short_code="GB22222", current_revision_id="r12", legal_status=None,
        file_path="collected.pdf", file_hash="h12"))
    clause_repo.insert_clauses([
        _clause("c11", "7.7.7", "正文甲", doc="d11", standard="GB 11111-2020"),
        _clause("c12", "7.7.7", "正文乙", doc="d12",
                standard="GB 22222-2021", legal_status_of_doc=None)])
    try:
        rows = [r.clause_revision_id for r in
                perform_hybrid_search("查 7.7.7", top_k=5, channels=["exact"])]
        assert "c11" in rows and "c12" in rows, rows
        assert rows.index("c11") < rows.index("c12"), (
            f"未核验条款排在已核验有效条款之前 ⇒ 通道内权重给反了: {rows}")
    finally:
        clause_repo.delete_document("d11")
        clause_repo.delete_document("d12")


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
