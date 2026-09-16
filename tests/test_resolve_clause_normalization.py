"""`resolve_clause` 条款号输入归一的回归（2026-09-17）。

背景（独立复核发现）：`/api/v1/clauses/resolve` 与 `clause_repo.resolve_clause`
**原本对条款号不做任何归一** —— SQL 是 `cr.clause_number = ?` 原样比较。实测生产库
520,504 条 `clause_number` 里**全角 0 条**，而 `normalize_clause_number` 只用在
**入库**（`pipeline.py` 7 处）与引用抽取（`classifier.py:171`），**从不用在查询入口**。
后果：用户或模型写出「５．２．１」「05.2.1」「 5.2.1 」时查不到本该命中的条款
（取证场景下 = 漏掉一条依据）。

修法必须是**纯增量**：先按原样查，只在查不到时用归一形式重试。原因见
`test_exact_form_wins_over_normalized_form` —— 库里真实存在 `'06'`/`'08'` 两条
**带前导零**的条款，若无条件归一，这两条会变成查不到。
"""
import pytest


@pytest.fixture()
def seeded(db):
    """两份文档：GB/T 10029-2010（含 5.2.1 / 06 / 6 / 表引用）与对照标准。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction

    for doc_id in ("nz1", "nz2"):
        if db.execute("SELECT 1 FROM doc_meta WHERE doc_id=?", (doc_id,)).fetchone():
            clause_repo.delete_document(doc_id)

    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="nz1", standard_no="GB/T 10029-2010", standard_name="归一测试",
            short_code="nz", current_revision_id="r", domain_tags=[], file_path="a.pdf",
            file_hash="hnz1"))
        clause_repo.insert_document(conn, dict(
            doc_id="nz2", standard_no="GB/T 99999-2010", standard_name="对照",
            short_code="nz2", current_revision_id="r", domain_tags=[], file_path="b.pdf",
            file_hash="hnz2"))
        rows = [
            # 常规半角条款
            ("n1", "nz1", "5.2.1", "封闭楼梯间宜设置乙级防火门。"),
            # 库里真实存在的「带前导零」条款（生产库实测仅 '06'/'08' 属此类）
            ("n2", "nz1", "06", "前导零条款 06 的正文。"),
            # 同标准下另有一条 '6'，用来验证原样优先
            ("n3", "nz1", "6", "半角条款 6 的正文。"),
            # 内容里出现「表2」，用于表格引用 fallback
            ("n4", "nz1", "4.1", "具体要求见表2 的规定。"),
            ("n5", "nz2", "5.2.1", "对照标准里的同名条款。"),
        ]
        for cid, doc_id, num, text in rows:
            conn.execute(
                "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
                " clause_key, clause_number, content_text, knowledge_type, modality,"
                " modality_strength, page_start, page_end)"
                " VALUES (?,?,?,?,?,?,'rule','宜',2,1,1)",
                (cid, "r", doc_id, "k" + cid, num, text))
            conn.execute(
                "INSERT INTO clause_fts (clause_revision_id, clause_number, standard_no, title,"
                " content_segmented, modality, subject, behavior_scope_segmented)"
                " VALUES (?,?,'','','', '', '', '')",
                (cid, num))
    yield db


def _num(res):
    return None if res is None else res.clause_number


def test_fullwidth_clause_number_resolves(seeded):
    """全角条款号必须能解析到半角那条（原实现返回 None）。"""
    from src.core.storage import clause_repo
    got = clause_repo.resolve_clause("GB/T 10029-2010", "５．２．１")
    assert got is not None, "全角条款号应可解析"
    assert _num(got) == "5.2.1"


def test_whitespace_and_leading_zero_tolerated(seeded):
    from src.core.storage import clause_repo
    assert _num(clause_repo.resolve_clause("GB/T 10029-2010", " 5.2.1 ")) == "5.2.1"
    assert _num(clause_repo.resolve_clause("GB/T 10029-2010", "05.2.1")) == "5.2.1"


def test_exact_form_wins_over_normalized_form(seeded):
    """**这条是修法的护栏**：库里同时有 '06' 与 '6' 时，查 '06' 必须命中 '06'。

    若无条件归一（先归一再查），查询 '06' 会被改写成 '6'，命中错误的条款 ——
    生产库实测有 2 条这种带前导零的条款，所以「原样优先、失败才归一」是必须的。
    """
    from src.core.storage import clause_repo
    assert _num(clause_repo.resolve_clause("GB/T 10029-2010", "06")) == "06"
    assert _num(clause_repo.resolve_clause("GB/T 10029-2010", "6")) == "6"


def test_table_reference_with_space_resolves(seeded):
    """「表 2」中间带空格也要进表格引用 fallback（归一后为「表2」）。"""
    from src.core.storage import clause_repo
    got = clause_repo.resolve_clause("GB/T 10029-2010", "表 2")
    assert got is not None and _num(got) == "4.1"


def test_no_false_positive_for_absent_clause(seeded):
    """归一不能把不存在的条款号"变"出来。"""
    from src.core.storage import clause_repo
    assert clause_repo.resolve_clause("GB/T 10029-2010", "９．９．９") is None
    assert clause_repo.resolve_clause("GB/T 10029-2010", "9.9.9") is None


def test_standard_number_still_disambiguates(seeded):
    """同一条款号在不同标准下不得串号（原样优先不应破坏精确匹配）。"""
    from src.core.storage import clause_repo
    a = clause_repo.resolve_clause("GB/T 10029-2010", "5.2.1")
    b = clause_repo.resolve_clause("GB/T 99999-2010", "5.2.1")
    assert a is not None and b is not None
    assert a.doc_id == "nz1" and b.doc_id == "nz2"


def test_resolve_route_accepts_fullwidth(seeded, client):
    """走真端点的同一路径（客户端可能把全角原样送上来）。"""
    c, token = client
    r = c.get("/api/v1/clauses/resolve",
              params={"standard_no": "GB/T 10029-2010", "clause_number": "５．２．１"},
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["clause_number"] == "5.2.1"
