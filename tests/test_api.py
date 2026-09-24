"""T07' API 壳测试：随机端口+token、/health、401、SSE 事件顺序。"""
import json

import pytest

from src.core.api.server import create_app  # noqa: F401 - 契约引用


def test_health_no_token(client):
    c, _ = client
    r = c.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("healthy", "degraded")
    assert body["db_status"] == "ok"


def test_missing_token_401(client):
    c, _ = client
    r = c.get("/api/v1/nonexistent")
    assert r.status_code == 401


def test_wrong_token_401(client):
    c, _ = client
    r = c.post("/api/v1/chat/completions", json={"query": "x"},
               headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_sse_event_order(client):
    c, token = client
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": "防火间距", "query_mode": "guess"},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        assert r.status_code == 200
        events = []
        for line in r.iter_lines():
            if line.startswith("event: "):
                events.append(line[len("event: "):])
    # 冻结顺序: evidence → status → delta+ → verification → done
    assert events[0] == "evidence"
    assert events[1] == "status"
    assert events[-2] == "verification"
    assert events[-1] == "done"
    assert any(e == "delta" for e in events)


def test_resolve_clause_marks_basis_scope(client, db):
    """定位端点必须把「能否作为依据」做成**机器可读**字段（红线：只引现行版）。

    2026-09-16（iteration-6 自查 §8.1 修正版）：`/api/v1/clauses/resolve` 是**定位**
    工具，它**故意不过滤**非现行版 —— 用户点名问旧版时必须能解析到并说明差异
    （决策 22 的括号部分）。此前「非 effective 不得作依据」只写在
    `plugin/src/chatmode.js:153` 的取证提示词里，属**提示词级约束**；而
    `hybrid_engine` 的 exact 通道对同一红线是**硬过滤** —— 同一红线两条路径强度不同。

    本用例钉住补齐后的代码级标记 `basis_scope`/`basis_notice`
    （与既有 `folder_scope`/`scope_notice` 同款），并确认**点名问旧版仍可解析**
    （即修复没有退化成"一律 404"）。
    """
    from src.core.domain.models import ClauseRevisionModel
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    for d in ("rs_cur", "rs_old"):
        if db.execute("SELECT 1 FROM doc_meta WHERE doc_id=?", (d,)).fetchone():
            clause_repo.delete_document(d)
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="rs_cur", standard_no="GB RS-2022", standard_name="RS(现行)",
            short_code="rs2022", current_revision_id="r", domain_tags=["测试"],
            file_path="c.pdf", file_hash="hrs1"))
        clause_repo.insert_document(conn, dict(
            doc_id="rs_old", standard_no="GB RS-2014", standard_name="RS(已废止)",
            short_code="rs2014", current_revision_id="r", legal_status="withdrawn",
            domain_tags=["测试"], file_path="o.pdf", file_hash="hrs2"))
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id="rs_c1", doc_id="rs_cur", clause_key="rsk1",
            standard_no="GB RS-2022", clause_number="5.2.1",
            content_text="现行版条文。", knowledge_type="rule",
            modality="应", modality_strength=3, page_start=1, page_end=1),
        ClauseRevisionModel(
            clause_revision_id="rs_o1", doc_id="rs_old", clause_key="rsk2",
            standard_no="GB RS-2014", clause_number="5.2.1",
            content_text="已废止版条文。", knowledge_type="rule",
            modality="宜", modality_strength=2, page_start=1, page_end=1),
    ])
    c, token = client
    h = {"Authorization": f"Bearer {token}"}

    r1 = c.get("/api/v1/clauses/resolve",
               params={"standard_no": "GB RS-2022", "clause_number": "5.2.1"},
               headers=h)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()["data"]
    assert d1["legal_status"] == "effective"
    assert d1["basis_scope"] == "usable"
    assert "basis_notice" not in d1, "现行版不应带禁令说明"

    r2 = c.get("/api/v1/clauses/resolve",
               params={"standard_no": "GB RS-2014", "clause_number": "5.2.1"},
               headers=h)
    assert r2.status_code == 200, "点名问旧版必须仍可解析（不得因红线退化为 404）"
    d2 = r2.json()["data"]
    assert d2["legal_status"] == "withdrawn"
    assert d2["basis_scope"] == "locate_only"
    assert "不得写入依据区" in d2["basis_notice"]


def test_resolve_clause_reference_tier_speaks_chinese(client, db):
    """新增的 `reference` 档（征求意见稿等**仅参考**件）也必须给**中文**禁令说明。

    ⚠ 这条抓的是"内部英文标识漏到界面上"：`server.py` 的兜底是
    `_label.get(str(ls), str(ls))` —— 少登记一个档，业主就会在界面上看到
    "该条为「reference」"（最高指令：跟业主说话不许用内部叫法）。
    """
    from src.core.domain.models import ClauseRevisionModel
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    if db.execute("SELECT 1 FROM doc_meta WHERE doc_id='rs_ref'").fetchone():
        clause_repo.delete_document("rs_ref")
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="rs_ref", standard_no="征求意见稿·危化品经营许可办法",
            standard_name="危化品经营许可办法(修订征求意见稿)", short_code="zqyj",
            current_revision_id="r", legal_status="reference",
            domain_tags=["测试"], file_path="d.pdf", file_hash="hrs3"))
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id="rs_r1", doc_id="rs_ref", clause_key="rsk3",
            standard_no="征求意见稿·危化品经营许可办法", clause_number="全文",
            content_text="征求意见稿全文。", knowledge_type="rule",
            modality="应", modality_strength=3, page_start=1, page_end=1),
    ])
    c, token = client
    r = c.get("/api/v1/clauses/resolve",
              params={"standard_no": "征求意见稿·危化品经营许可办法",
                      "clause_number": "全文"},
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["legal_status"] == "reference"
    assert d["basis_scope"] == "locate_only", "仅参考件不得算作可用依据"
    assert "reference" not in d["basis_notice"], \
        f"内部英文标识漏到界面上了：{d['basis_notice']}"
    assert "参考资料" in d["basis_notice"] and "不得写入依据区" in d["basis_notice"]
