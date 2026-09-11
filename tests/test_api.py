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
