"""Task 10.0 外发审计测试：record_egress 落库 / chat 链路自动记录 / 审计 API / 导出。"""
import json

import pytest


def test_record_egress_writes_dump(db):
    from src.core.llm.egress_audit import record_egress
    dump_id = record_egress(
        service="vision", endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1",
        payload={"image": "<bytes>", "prompt": "识别图中规范要求"},
        response_meta={"status": 200}, query="图中条款")
    assert dump_id.startswith("dump_")
    row = db.execute(
        "SELECT trigger_type, query, prompt, logs FROM debug_dump WHERE dump_id=?",
        (dump_id,)).fetchone()
    assert row["trigger_type"] == "egress"
    assert row["query"] == "图中条款"
    logs = json.loads(row["logs"])
    assert logs["service"] == "vision"
    assert logs["payload_bytes"] > 0


def test_chat_flow_leaves_egress_record(client):
    """chat 链路每次提问自动落外发记录（user_export，含 prompt/llm_output）。"""
    c, token = client
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": "防火间距", "top_k": 1},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        assert r.status_code == 200
        for _ in r.iter_lines():
            pass
    from src.core.llm.egress_audit import query_egress
    data = query_egress(limit=5)
    assert data["total"] >= 1
    hit = next((i for i in data["items"] if i["query"] == "防火间距"), None)
    assert hit is not None, "chat 外发记录必须可聚合"
    assert hit["service"] == "deepseek-chat"
    assert isinstance(hit["prompt_preview"], str)


def test_egress_audit_api(client):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    # 无 token 401
    assert c.get("/api/v1/egress/audit").status_code == 401
    r = c.get("/api/v1/egress/audit", headers=headers, params={"limit": 3})
    assert r.status_code == 200
    data = r.json()["data"]
    assert set(data) == {"total", "items"}
    assert data["total"] >= 0
    if data["items"]:
        it = data["items"][0]
        assert {"dump_id", "created_at", "service", "query",
                "prompt_preview", "response_preview"} <= set(it.keys())


def test_egress_query_keyset_cursor(db):
    """keyset 深翻页（2026-08-26）：按 (created_at, dump_id) 键集翻页无重复无遗漏。
    cursor 语义：取上一页末条的 created_at|dump_id，下一页返回更旧记录。"""
    from src.core.llm.egress_audit import query_egress, record_egress
    for i in range(3):
        record_egress("deepseek", f"https://api.test/{i}",
                      {"n": i}, query=f"q{i}", response_meta={"status": 200})
    page1 = query_egress(limit=2)
    assert len(page1["items"]) == 2
    last = page1["items"][-1]
    cursor = f"{last['created_at']}|{last['dump_id']}"
    page2 = query_egress(limit=2, cursor=cursor)
    ids1 = {i["dump_id"] for i in page1["items"]}
    ids2 = {i["dump_id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2), "keyset 翻页不得与上一页重复"
    assert len(ids2) >= 1, "keyset 翻页应继续返回更旧记录"
    # 与 OFFSET 路径行为一致（同一排序下的后续页）
    page1_off = query_egress(limit=2, offset=0)
    page2_off = query_egress(limit=2, offset=2)
    assert ids1 == {i["dump_id"] for i in page1_off["items"]}
    assert ids2 == {i["dump_id"] for i in page2_off["items"]}


def test_egress_audit_export(client):
    from src.core.llm.egress_audit import record_egress
    from src.core.storage.sqlite_db import get_db_connection
    record_egress(service="test", endpoint="https://example.com/v1",
                  payload={"q": "x"}, query="导出测试")
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/v1/egress/audit/export", headers=headers)
    assert r.status_code == 200
    name = r.json()["data"]["name"]
    assert name.startswith("egress-audit-") and name.endswith(".json")
    # 经下载接口取回内容校验
    r2 = c.get("/api/v1/export/download", headers=headers, params={"name": name})
    assert r2.status_code == 200
    payload = json.loads(r2.content)
    assert payload["total"] >= 1
    assert any("导出测试" in it["query"] for it in payload["items"])
