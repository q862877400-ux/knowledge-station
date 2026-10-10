"""法规历次版本链测试（spec 006 US2 / T032）。

覆盖：
- `flk_client.history()` 解析 `lsyg`：多版本降序 / 空 `lsyg` 返空 /
  `gbrq` 为 null 沉底 / `highLight` 归一成 `highlight` / 非 list 容错；
- **网络失败必须抛异常**（MUST NOT 用 `[]` 冒充"无版本"）；
- HTTP 端点三条分支：缺参 422 / 正常 200 / 官方不可达 502。

全程 mock，零真实请求。
"""
from __future__ import annotations

import pytest

from src.core.knowledge.law_source import flk_client


def _detail_with(lsyg, bbbs="b1"):
    """造一个 detail 替身（history 只读 raw['lsyg']）。"""
    class _D:
        raw = {"lsyg": lsyg}
    return _D()


# ------------------------------------------------------------------ history()

def test_history_sorted_desc(monkeypatch):
    """多版本 ⇒ 按 gbrq 降序。"""
    monkeypatch.setattr(flk_client, "detail", lambda b: _detail_with([
        {"bbbs": "old", "title": "T", "gbrq": "2010-02-11", "highLight": False},
        {"bbbs": "new", "title": "T", "gbrq": "2026-09-19", "highLight": True},
        {"bbbs": "mid", "title": "T", "gbrq": "2018-05-01", "highLight": False},
    ]))
    out = flk_client.history("x")
    assert [r["bbbs"] for r in out] == ["new", "mid", "old"]


def test_history_null_gbrq_sinks(monkeypatch):
    """★ gbrq 实测可为 null ⇒ 必须沉底且不抛错。"""
    monkeypatch.setattr(flk_client, "detail", lambda b: _detail_with([
        {"bbbs": "a", "title": "T", "gbrq": None, "highLight": False},
        {"bbbs": "b", "title": "T", "gbrq": "2024-04-07", "highLight": True},
    ]))
    out = flk_client.history("x")
    assert [r["bbbs"] for r in out] == ["b", "a"]
    assert out[1]["gbrq"] == ""


def test_history_highlight_normalised(monkeypatch):
    """官方字段名是 highLight（驼峰）⇒ 输出归一成 highlight。"""
    monkeypatch.setattr(flk_client, "detail", lambda b: _detail_with([
        {"bbbs": "a", "title": "T", "gbrq": "2024-01-01", "highLight": True}]))
    out = flk_client.history("x")
    assert out[0]["highlight"] is True
    assert "highLight" not in out[0]


def test_history_empty_when_no_lsyg(monkeypatch):
    """没有 lsyg ⇒ 空列表（这是"确实没有历次版本"，不是失败）。"""
    for empty in ([], None):
        monkeypatch.setattr(flk_client, "detail", lambda b, e=empty: _detail_with(e))
        assert flk_client.history("x") == []


def test_history_tolerates_non_list(monkeypatch):
    """lsyg 不是 list（接口结构变了）⇒ 返空，不炸。"""
    monkeypatch.setattr(flk_client, "detail", lambda b: _detail_with({"weird": 1}))
    assert flk_client.history("x") == []


def test_history_skips_non_dict_items(monkeypatch):
    """链上混进非 dict 项 ⇒ 跳过该项，其余照常。"""
    monkeypatch.setattr(flk_client, "detail", lambda b: _detail_with([
        "junk", {"bbbs": "a", "title": "T", "gbrq": "2024-01-01", "highLight": False}]))
    out = flk_client.history("x")
    assert len(out) == 1 and out[0]["bbbs"] == "a"


def test_history_raises_on_network_failure(monkeypatch):
    """★ 网络失败 MUST 抛异常 —— 绝不用 [] 冒充"无版本"（spec FR-007）。"""
    def boom(b):
        raise RuntimeError("反爬挑战页")
    monkeypatch.setattr(flk_client, "detail", boom)
    with pytest.raises(RuntimeError):
        flk_client.history("x")


# ------------------------------------------------------------------ HTTP 端点

def test_history_endpoint_missing_bbbs(client):
    c, token = client
    r = c.get("/api/v1/laws/history",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422
    assert r.json()["error"] == "missing_bbbs"


def test_history_endpoint_ok(monkeypatch, client):
    c, token = client
    monkeypatch.setattr("src.core.knowledge.law_source.flk_client.history",
                        lambda b: [{"bbbs": "a", "title": "T",
                                    "gbrq": "2026-09-19", "highlight": True}])
    r = c.get("/api/v1/laws/history?bbbs=b1",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["count"] == 1 and data["versions"][0]["bbbs"] == "a"


def test_history_endpoint_502_on_failure(monkeypatch, client):
    """★ 官方不可达 ⇒ 502，**不是** 200 + 空链（否则前端无法区分）。"""
    c, token = client

    def boom(b):
        raise RuntimeError("反爬挑战页")
    monkeypatch.setattr("src.core.knowledge.law_source.flk_client.history", boom)
    r = c.get("/api/v1/laws/history?bbbs=b1",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 502
    assert r.json()["error"] == "history_fetch_failed"


def test_history_endpoint_empty_is_200(monkeypatch, client):
    """确实无历次版本 ⇒ 200 + 空链（与 502 明确区分）。"""
    c, token = client
    monkeypatch.setattr("src.core.knowledge.law_source.flk_client.history",
                        lambda b: [])
    r = c.get("/api/v1/laws/history?bbbs=b1",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"]["versions"] == []
