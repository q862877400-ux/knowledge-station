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


def test_modality_channel_ranks_verified_before_unverified(seeded_db):
    """模态通道（D）的**通道内名次**必须是确定的，且未核验不占优（复核 b9 的 INFO-6）。

    背景：这条 SQL 原先**完全没有 ORDER BY**，而 `rank` 直接决定
    `CHANNEL_WEIGHTS/(RRF_K+rank+1)` ⇒ 权重分配**由 SQLite 的返回次序决定**（未定义），
    同一查询的排序**不可复现、也无法断言**。

    构造方式刻意让"不写 ORDER BY"排错：**先插入未核验那一份**（自然/rowid 次序会它在前），
    于是只有真的写了排序、且排序把未核验沉底，`c22` 才会排在 `c21` 前面。
    ⚠ 判别力说明：这条断言的判别力依赖 SQLite 的访问路径（这里是按 `clause_revision`
    的 rowid 顺序扫）。规划器若改成从 `doc_meta` 驱动，可能出现**假绿**——所以真正的护栏是
    "语句里现在就写着 ORDER BY"，本用例只是它的**行为侧**证据。
    """
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    clause_repo.insert_document(conn, dict(
        doc_id="d21", standard_no="GB 33333-2020", standard_name="采集件标准",
        short_code="GB33333", current_revision_id="r21", legal_status=None,
        file_path="collected.pdf", file_hash="h21"))
    clause_repo.insert_document(conn, dict(
        doc_id="d22", standard_no="GB 44444-2020", standard_name="已核验标准",
        short_code="GB44444", current_revision_id="r22", legal_status="effective",
        file_path="verified.pdf", file_hash="h22"))
    try:
        clause_repo.insert_clauses([
            _clause("c21", "8.8.8", "未核验的严禁条款", doc="d21",
                    modality="严禁", standard="GB 33333-2020", legal_status_of_doc=None),
            _clause("c22", "8.8.9", "已核验的严禁条款", doc="d22",
                    modality="严禁", standard="GB 44444-2020"),
        ])
        rows = [r.clause_revision_id for r in perform_hybrid_search(
            "严禁 测试", top_k=10, channels=["modality"], modality_filter="严禁")]
        assert "c21" in rows and "c22" in rows, rows
        assert rows.index("c22") < rows.index("c21"), (
            f"未核验条款在模态通道里排在已核验有效条款之前 ⇒ 通道内名次未定义/给反了: {rows}")
        # 同一条查询跑两次必须给出**同一个序列**（权重分配可复现）
        again = [r.clause_revision_id for r in perform_hybrid_search(
            "严禁 测试", top_k=10, channels=["modality"], modality_filter="严禁")]
        assert again == rows, (rows, again)
    finally:
        clause_repo.delete_document("d21")
        clause_repo.delete_document("d22")


def test_legal_element_channel_order_is_deterministic(seeded_db):
    """法理要素通道（E）**同族缺陷、自查发现**：它原先也没有 ORDER BY。

    判别方式：按 **id 倒序**插入（先 `c992` 再 `c991`）⇒ 若真的按 `clause_revision_id`
    排序，返回顺序必然与插入顺序**相反**；不写 ORDER BY 时这里会给出插入顺序 ⇒ 红。
    （这条只钉"确定性"，**不**钉"未核验沉底"——E 没有 JOIN `doc_meta`，给不了那个偏好，
    见 `hybrid_engine.py` 里那段诚实边界。）
    """
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    clause_repo.insert_document(conn, dict(
        doc_id="d31", standard_no="GB 55555-2020", standard_name="要素测试标准",
        short_code="GB55555", current_revision_id="r31", legal_status="effective",
        file_path="e.pdf", file_hash="h31"))
    try:
        clause_repo.insert_clauses([
            _clause("c992", "9.9.2", "主体条款乙", doc="d31", ktype="legal",
                    subject="测试主体X", standard="GB 55555-2020"),
            _clause("c991", "9.9.1", "主体条款甲", doc="d31", ktype="legal",
                    subject="测试主体X", standard="GB 55555-2020"),
        ])
        rows = [r.clause_revision_id for r in perform_hybrid_search(
            "测试主体X", top_k=10, channels=["legal_element"], subject_filter="测试主体X")]
        assert rows[:2] == ["c991", "c992"], (
            f"通道内顺序不是按 id（说明没有 ORDER BY，顺序未定义）: {rows}")
    finally:
        clause_repo.delete_document("d31")


def test_legal_element_channel_ranks_verified_before_unverified(seeded_db):
    """法理要素通道（E）也要"未核验沉底 + 确定"（§10.65 补齐；§10.58 只补了确定性）。

    构造让"没有 ORDER BY / 只按 id"都排错：**先插入未核验那份、且它的 id 更小**
    （`c990` < `c991`）⇒ 自然顺序与"按 id"顺序都把未核验排前面；只有真的按
    "状态优先、再 id"排，已核验的 `c991` 才会在前。
    """
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    clause_repo.insert_document(conn, dict(
        doc_id="d41", standard_no="GB 66666-2020", standard_name="采集件标准",
        short_code="GB66666", current_revision_id="r41", legal_status=None,
        file_path="c.pdf", file_hash="h41"))
    clause_repo.insert_document(conn, dict(
        doc_id="d42", standard_no="GB 77777-2020", standard_name="已核验标准",
        short_code="GB77777", current_revision_id="r42", legal_status="effective",
        file_path="v.pdf", file_hash="h42"))
    try:
        clause_repo.insert_clauses([
            _clause("c990", "9.9.0", "未核验的主体条款", doc="d41", ktype="legal",
                    subject="测试主体Y", standard="GB 66666-2020", legal_status_of_doc=None),
            _clause("c991", "9.9.1", "已核验的主体条款", doc="d42", ktype="legal",
                    subject="测试主体Y", standard="GB 77777-2020"),
        ])
        rows = [r.clause_revision_id for r in perform_hybrid_search(
            "测试主体Y", top_k=10, channels=["legal_element"], subject_filter="测试主体Y")]
        assert "c990" in rows and "c991" in rows, rows
        assert rows.index("c991") < rows.index("c990"), (
            f"未核验条款在法理要素通道里排在已核验有效条款之前 ⇒ 通道内名次给反了: {rows}")
    finally:
        clause_repo.delete_document("d41")
        clause_repo.delete_document("d42")


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
