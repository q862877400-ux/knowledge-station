"""渠道台账**人工维护**的写侧（§11.0 R6d）：新增 / 复核编辑 / 启停 / 删除 + 留痕。

为什么要单独一组用例：这一侧是"人写台账"的入口，两个风险都不小——

① **人能把只有探针才该产出的健康度字段写进去**（`state`/`last_ok_at`/…）＝凭空造证据。
   所以本文件钉住"这些键一律 **422 出声拒绝**"——**不是**静默丢弃
   （静默丢弃会让人以为写成功了，而面板上那条"上次成功"会被错读成真探过）；
② **人改了却没有痕迹**：审查场景要能回答"谁、什么时候、把哪条改成了什么"。
   所以每条断言都去 `event_log` 里核**同一条改动**留下的那行（与改动同事务）。

删除那条还额外钉一件事：`channel/deleted` 的 `before_state` 里必须有**删除前整行快照**——
"删得掉条目，删不掉证据"。
"""
from __future__ import annotations

import json

HDR = {"Authorization": "Bearer test-token-123"}
BASE = "/api/v1/channels"


def _audit_rows(db, event_type: str) -> list[dict]:
    return [dict(r) for r in db.execute(
        "SELECT * FROM event_log WHERE event_type=? ORDER BY rowid",
        (event_type,)).fetchall()]


def _create(client, **body) -> dict:
    c, _ = client
    payload = {"name": "渠道用例", **body}
    r = c.post(BASE, json=payload, headers=HDR)
    assert r.status_code == 200, r.text
    return r.json()["data"]


class Test人工新增:
    def test_新增成功_默认值正确_并留一条痕迹(self, client, db):
        row = _create(client, name="某省住建厅公告", url="https://example.org/zw")
        cid = row["channel_id"]
        assert cid.startswith("user:"), cid
        assert row["wiring"] == "user"          # 人加的，与适配器/种子区分开
        assert row["verification"] == "unverified"  # 人工录入 ≠ 已核实
        assert int(row["enabled"]) == 1
        assert row["state"] == "unknown"        # 没探过就是 unknown，不许凭空造
        assert row["last_ok_at"] is None

        rows = _audit_rows(db, "channel/created")
        assert len(rows) == 1, rows
        ev = rows[0]
        assert ev["actor"] == "user"
        assert ev["target_type"] == "update_channel"
        assert ev["target_id"] == cid
        assert "name" in json.loads(ev["metadata"])["fields"]

    def test_缺name与非法字段都出声拒绝(self, client, db):
        c, _ = client
        # ⚠ 库是**会话共享**的 ⇒ 这里只能比"尝试前后有没有多出痕迹"，
        # 不能断言绝对条数（我第一版写的 `== []` 与用例执行顺序绑定 = 假红/假绿）。
        before = len(_audit_rows(db, "channel/created"))

        r = c.post(BASE, json={"url": "https://example.org/x"}, headers=HDR)
        assert r.status_code == 422
        assert r.json()["error"] == "channel_name_required"

        # ① 健康度字段：探针产出，人工不能写
        r = c.post(BASE, json={"name": "x", "state": "ok", "last_ok_at": "2026-01-01"},
                   headers=HDR)
        assert r.status_code == 422
        body = r.json()
        assert body["error"] == "illegal_channel_field"
        assert "state" in body["message"] and "last_ok_at" in body["message"]
        assert "probe" in body["message"], body["message"]   # 要指路，不能只说"不行"

        # ② 未知键：拼错字段名不许静默丢
        r = c.post(BASE, json={"name": "x", "url_typo": "https://e.org"}, headers=HDR)
        assert r.status_code == 422
        assert r.json()["error"] == "illegal_channel_field"

        # ③ id 前缀契约
        r = c.post(BASE, json={"name": "x", "channel_id": "随便写的"}, headers=HDR)
        assert r.status_code == 422
        assert r.json()["error"] == "illegal_channel_id"

        # 失败的写不许留半边痕迹（这四条都被上面的校验挡在写库之前）
        assert len(_audit_rows(db, "channel/created")) == before

    def test_新增的渠道出现在列表与小结里(self, client):
        row = _create(client, name="只此一条的用例渠道")
        c, _ = client
        r = c.get(BASE, params={"wiring": "user"}, headers=HDR)
        assert r.status_code == 200
        data = r.json()["data"]
        ids = [it["channel_id"] for it in data["items"]]
        assert row["channel_id"] in ids
        mine = [it for it in data["items"] if it["channel_id"] == row["channel_id"]][0]
        assert mine["has_probe_target"] is False    # 人加的渠道还没配探针目标
        assert data["summary"]["by_wiring"]["user"] >= 1


class Test人工复核编辑:
    def test_改描述性字段_留痕带改前改后(self, client, db):
        row = _create(client, name="待改渠道", url="https://old.example.org")
        cid = row["channel_id"]
        c, _ = client
        r = c.patch(f"{BASE}/{cid}", json={"url": "https://new.example.org",
                                          "note": "改过链接"},
                    headers=HDR)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["url"] == "https://new.example.org"

        rows = _audit_rows(db, "channel/updated")
        assert len(rows) == 1, rows
        ev = rows[0]
        assert ev["actor"] == "user" and ev["target_id"] == cid
        assert json.loads(ev["before_state"])["url"] == "https://old.example.org"
        assert json.loads(ev["after_state"])["url"] == "https://new.example.org"

    def test_编辑不许碰健康度_启停要走去自己的端点(self, client):
        row = _create(client, name="另一条")
        cid = row["channel_id"]
        c, _ = client
        r = c.patch(f"{BASE}/{cid}", json={"state": "ok"}, headers=HDR)
        assert r.status_code == 422 and r.json()["error"] == "illegal_channel_field"

        r = c.patch(f"{BASE}/{cid}", json={"enabled": False}, headers=HDR)
        assert r.status_code == 422
        assert r.json()["error"] == "use_enabled_endpoint"   # 语义与留痕都不同 ⇒ 指路

        r = c.patch(f"{BASE}/{cid}", json={}, headers=HDR)
        assert r.status_code == 422 and r.json()["error"] == "empty_patch"

        r = c.patch(f"{BASE}/user:不存在的渠道", json={"note": "x"}, headers=HDR)
        assert r.status_code == 404 and r.json()["error"] == "channel_not_found"

    def test_探针跑过之后人工改链接不清空健康度(self, client, db):
        """人工改的是"描述性字段"，**不许**顺手把实测状态抹掉（`overwrite_health=False`）。"""
        row = _create(client, name="有过探针记录的渠道")
        cid = row["channel_id"]
        from src.core.storage import channel_repo as cr
        cr.record_probe(cid, state="ok", latency_ms=123)

        c, _ = client
        r = c.patch(f"{BASE}/{cid}", json={"url": "https://moved.example.org"}, headers=HDR)
        assert r.status_code == 200, r.text
        after = r.json()["data"]
        assert after["state"] == "ok" and after["last_ok_at"] is not None
        assert after["latency_ms"] == 123


class Test人工启停与删除:
    def test_启停留痕(self, client, db):
        row = _create(client, name="待停用渠道")
        cid = row["channel_id"]
        c, _ = client
        r = c.post(f"{BASE}/{cid}/enabled", json={"enabled": False}, headers=HDR)
        assert r.status_code == 200, r.text
        assert int(r.json()["data"]["enabled"]) == 0

        r = c.post(f"{BASE}/{cid}/enabled", json={"enabled": "no"}, headers=HDR)
        assert r.status_code == 422 and r.json()["error"] == "illegal_enabled"

        rows = _audit_rows(db, "channel/enabled")
        assert len(rows) == 1, rows
        assert json.loads(rows[0]["before_state"]) == {"enabled": 1}
        assert json.loads(rows[0]["after_state"]) == {"enabled": 0}

    def test_删除留痕带删除前整行快照(self, client, db):
        row = _create(client, name="将被删除的渠道", url="https://gone.example.org")
        cid = row["channel_id"]
        c, _ = client
        r = c.delete(f"{BASE}/{cid}", headers=HDR)
        assert r.status_code == 200, r.text
        assert r.json()["data"] == {"deleted": True, "channel_id": cid}

        assert c.get(f"{BASE}/{cid}", headers=HDR).status_code == 404
        assert c.delete(f"{BASE}/{cid}", headers=HDR).status_code == 404  # 幂等：再删就 404

        rows = _audit_rows(db, "channel/deleted")
        assert len(rows) == 1, rows
        before = json.loads(rows[0]["before_state"])
        # 删得掉条目，删不掉证据：痕迹里留着删除前那一行
        assert before["channel_id"] == cid
        assert before["name"] == "将被删除的渠道"
        assert before["url"] == "https://gone.example.org"
        assert rows[0]["actor"] == "user"
