# -*- coding: utf-8 -*-
"""渠道台账仓储测试（`src/core/storage/channel_repo.py`，§11.0 R2）。

守四条（都是 R1 实测教训换来的口径，不是形式）：
  1. **注册数 ≠ 能力数**：`wiring` 与 `verification` 分开、`summary()` 必须两个数都报；
  2. **类别词表归一**：调研文档有 30 种写法，必须收敛到 canonical enum，且原文不丢；
  3. **种子导入不覆盖运行期健康度**（否则"复检一次种子"就把实测结果抹了）；
  4. **三态语义**：`suspicious`（HTTP 200 但没抓到预期内容）**也算失败**——R1 的 G14；
     `unknown` 只更新"尝试过"，不许当成成功或失败。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.storage import channel_repo as cr


@pytest.fixture(autouse=True)
def _clean_channel_table(db):
    """每个用例先清空 `update_channel`。

    ⚠ 为什么必须清：测试库的 data_dir 是**会话级**的（`conftest._isolate_data_dir`），
    同一个文件被本模块所有用例共用 ⇒ 前一个用例建的 `t:a` 会让后一个用例的
    "新建应抛错"变成"更新不抛错"、`list_channels()` 里也会多出别的用例的行。
    （本文件的第一次运行就是这么红的——7 条假红，根因是**用例之间互相污染**，
    不是产品代码的问题。清表是最小且确定的隔离手段。）
    """
    conn = db
    conn.execute("DELETE FROM update_channel")
    conn.commit()
    yield


class TestCategoryNormalization:
    """30 种原始写法 → canonical；未知一律 other 且不丢原文。"""

    @pytest.mark.parametrize("raw,expect", [
        ("法律", "law"), ("行政法规", "law"), ("部门规章", "law"), ("地方性法规", "law"),
        ("地方政府规章", "law"), ("司法解释", "law"), ("规范性文件", "law"),
        ("国标", "std_gb"), ("国家标准（全门类）", "std_gb"),
        ("行标", "std_hb"), ("行业标准", "std_hb"), ("部委行业标准公告", "std_hb"),
        ("地标", "std_db"), ("地方标准", "std_db"),
        ("团标", "std_tb"), ("团体标准", "std_tb"),
        ("国际", "std_intl"),
        ("聚合入口", "aggregator"), ("跨门类标准状态权威", "aggregator"),
        ("工具项目", "tool"),
        ("通用网页兜底", "internal"), ("用户配置公告源", "internal"),
    ])
    def test_已知写法都能归一(self, raw, expect):
        assert cr.normalize_category(raw) == expect

    def test_未知写法落_other_且调用方保留原文(self, db):
        assert cr.normalize_category("某个我没见过的新类别") == "other"
        assert cr.normalize_category(None) == "other"
        # category_raw 保留证据；category 由它推导
        row = cr.upsert_channel("t:raw", {"name": "X", "category_raw": "某个我没见过的新类别"})
        assert row["category"] == "other"
        assert row["category_raw"] == "某个我没见过的新类别"


class TestCrud:
    def test_插入_读取_列出_删除(self, db):
        cr.upsert_channel("t:a", {"name": "甲", "category": "std_gb", "wiring": "wired"})
        cr.upsert_channel("t:b", {"name": "乙", "category": "law", "wiring": "unwired"})
        assert cr.get_channel("t:a")["name"] == "甲"
        assert [c["channel_id"] for c in cr.list_channels()] == ["t:b", "t:a"]  # 按 category,name
        assert [c["channel_id"] for c in cr.list_channels(category="std_gb")] == ["t:a"]
        assert [c["channel_id"] for c in cr.list_channels(wiring="unwired")] == ["t:b"]
        assert cr.get_channel("t:nope") is None
        assert cr.delete_channel("t:b") is True
        assert cr.delete_channel("t:b") is False

    def test_拼错字段要抛而不是静默丢(self, db):
        with pytest.raises(ValueError, match="unknown_channel_field"):
            cr.upsert_channel("t:a", {"name": "甲", "categroy": "law"})  # 故意拼错

    def test_非法类别要抛(self, db):
        with pytest.raises(ValueError, match="illegal_channel_category"):
            cr.upsert_channel("t:a", {"name": "甲", "category": "nonsense"})

    def test_缺_name_的新建要抛(self, db):
        with pytest.raises(ValueError, match="channel_name_required"):
            cr.upsert_channel("t:a", {"category": "law"})

    def test_更新保留未提到的字段(self, db):
        cr.upsert_channel("t:a", {"name": "甲", "category": "law", "url": "https://x/"})
        cr.upsert_channel("t:a", {"name": "甲改名"})
        row = cr.get_channel("t:a")
        assert row["name"] == "甲改名" and row["url"] == "https://x/" and row["category"] == "law"

    def test_启停不删数据(self, db):
        cr.upsert_channel("t:a", {"name": "甲", "category": "law"})
        assert cr.set_enabled("t:a", False)["enabled"] == 0
        assert len(cr.list_channels(enabled_only=True)) == 0
        assert len(cr.list_channels()) == 1        # 停用≠删除（历史健康度是证据）
        with pytest.raises(ValueError, match="channel_not_found"):
            cr.set_enabled("t:nope", True)


class TestHealthSemantics:
    """三态 + 计数：这一组的语义直接决定面板上"有效性"三个字是什么意思。"""

    def test_ok_清零失败计数并记_last_ok(self, db):
        cr.upsert_channel("t:a", {"name": "甲", "category": "law"})
        cr.record_probe("t:a", state="down", error="connection reset", error_code="UPD-1004")
        assert cr.get_channel("t:a")["consecutive_failures"] == 1
        row = cr.record_probe("t:a", state="ok", latency_ms=123)
        assert row["state"] == "ok" and row["consecutive_failures"] == 0
        assert row["last_ok_at"] and row["last_try_at"] and row["latency_ms"] == 123

    def test_suspicious_也算失败(self, db):
        """R1 的 G14：应急部标准页 465B、bzw 列表页"共0条" —— **200 不等于有数据**。"""
        cr.upsert_channel("t:a", {"name": "甲", "category": "std_hb"})
        row = cr.record_probe("t:a", state="suspicious", error="HTTP 200 但没命中预期锚点",
                              error_code="probe_no_anchor")
        assert row["state"] == "suspicious"
        assert row["consecutive_failures"] == 1     # 不是 0 —— 它没成功
        assert row["last_ok_at"] is None

    def test_unknown_只记尝试(self, db):
        cr.upsert_channel("t:a", {"name": "甲", "category": "law"})
        row = cr.record_probe("t:a", state="unknown")
        assert row["state"] == "unknown"
        assert row["last_try_at"] and row["last_ok_at"] is None
        assert row["consecutive_failures"] == 0

    def test_非法状态与不存在的渠道都要抛(self, db):
        cr.upsert_channel("t:a", {"name": "甲", "category": "law"})
        with pytest.raises(ValueError, match="illegal_channel_state"):
            cr.record_probe("t:a", state="fine")
        with pytest.raises(ValueError, match="channel_not_found"):
            cr.record_probe("t:nope", state="ok")

    def test_summary_把注册数与能力数分开报(self, db):
        """本模块最重要的一条口径：total 是台账条数，by_wiring['wired'] 才是能干活条数。"""
        cr.upsert_channel("t:a", {"name": "甲", "category": "std_gb", "wiring": "wired"})
        cr.upsert_channel("t:b", {"name": "乙", "category": "std_gb", "wiring": "unwired"})
        cr.upsert_channel("t:c", {"name": "丙", "category": "std_gb", "wiring": "broken"})
        s = cr.summary()
        assert s["total"] == 3 and s["by_wiring"]["wired"] == 1
        assert s["by_wiring"]["unwired"] == 1 and s["by_wiring"]["broken"] == 1


class TestSeed:
    """种子导入：幂等 + **不覆盖运行期健康度**。"""

    def _seed_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "seed.json"
        p.write_text(json.dumps({"channels": [
            {"channel_id": "ch:x", "name": "甲", "category": "std_gb", "wiring": "wired",
             "verification": "verified", "url": "https://a/"},
            {"channel_id": "ch:y", "name": "乙", "category": "law", "wiring": "unwired"},
        ]}, ensure_ascii=False), encoding="utf-8")
        return p

    def test_导入幂等且不覆盖健康度(self, db, tmp_path):
        seed = self._seed_file(tmp_path)
        first = cr.seed_channels(seed)
        assert first == {"inserted": 2, "updated": 0, "total": 2}
        cr.record_probe("ch:x", state="down", error="WAF 412", error_code="UPD-1004")
        before = cr.get_channel("ch:x")
        second = cr.seed_channels(seed)             # 再导一次（模拟复检/升级后重灌）
        assert second == {"inserted": 0, "updated": 2, "total": 2}
        after = cr.get_channel("ch:x")
        assert (after["state"], after["last_error"], after["consecutive_failures"]) == \
               (before["state"], before["last_error"], before["consecutive_failures"])
        assert after["state"] == "down" and after["consecutive_failures"] == 1

    def test_显式_overwrite_health_才覆盖(self, db, tmp_path):
        """`overwrite_health=True` = 允许 payload 里的健康度字段落库（默认一律不落）。"""
        p = tmp_path / "seed2.json"
        p.write_text(json.dumps({"channels": [
            {"channel_id": "ch:x", "name": "甲", "category": "std_gb",
             "state": "unknown", "last_error": None},
        ]}, ensure_ascii=False), encoding="utf-8")
        cr.seed_channels(p)
        cr.record_probe("ch:x", state="down", error="WAF")
        assert cr.get_channel("ch:x")["state"] == "down"
        cr.seed_channels(p)                          # 默认：不动健康度
        assert cr.get_channel("ch:x")["state"] == "down"
        cr.seed_channels(p, overwrite_health=True)   # 显式要求才覆盖
        assert cr.get_channel("ch:x")["state"] == "unknown"

    def test_种子文件缺失或格式坏要抛(self, db, tmp_path):
        with pytest.raises(FileNotFoundError):
            cr.load_seed(tmp_path / "nope.json")
        bad = tmp_path / "bad.json"
        bad.write_text('{"channels": []}', encoding="utf-8")
        with pytest.raises(ValueError):
            cr.load_seed(bad)


class TestApi:
    """`/api/v1/channels`（R2b，只读）。⚠ 两条纪律：参数错要 422（不是空结果）、
    `summary` 与 `items` 必须同一次返回（两个口径不同的数字最会骗人）。

    ⚠ `client` fixture 给的是 `(TestClient, token)` **元组**（`conftest.py:53`）——
    直接 `client.get(...)` 会 AttributeError（本轮就踩了一次）。
    """

    @staticmethod
    def _hdr(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def test_列表带_summary_且能按类别筛选(self, client):
        c, token = client
        cr.seed_channels()
        r = c.get("/api/v1/channels?category=std_gb", headers=self._hdr(token))
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["summary"]["total"] >= 100
        assert all(i["category"] == "std_gb" for i in body["items"])
        # 能力数与台账数**同时**在响应里（口径分开）
        assert body["summary"]["by_wiring"]["wired"] >= 1

    def test_非法筛选值要_422_而不是空结果(self, client):
        c, token = client
        for q in ("category=nonsense", "wiring=fine", "state=healthy", "verification=maybe"):
            r = c.get(f"/api/v1/channels?{q}", headers=self._hdr(token))
            assert r.status_code == 422, f"{q} 应 422（空结果会让人以为库里没有）"
            # 引擎的错误体形状：{"code": <status>, "status": "error", "error": <code>, "message": …}
            assert r.json()["error"] == "illegal_channel_filter"

    def test_limit_越界要_422(self, client):
        c, token = client
        assert c.get("/api/v1/channels?limit=0", headers=self._hdr(token)).status_code == 422
        assert c.get("/api/v1/channels?limit=99999",
                     headers=self._hdr(token)).status_code == 422

    def test_单条详情_不存在要_404(self, client):
        c, token = client
        cr.upsert_channel("t:one", {"name": "甲", "category": "law"})
        ok = c.get("/api/v1/channels/t:one", headers=self._hdr(token))
        assert ok.status_code == 200 and ok.json()["data"]["name"] == "甲"
        assert c.get("/api/v1/channels/t:nope", headers=self._hdr(token)).status_code == 404

    def test_探测端点_不存在的_id_要_404(self, client):
        """`POST /api/v1/channels/probe`：ids 里有台账里没有的 → 404（不是静默跳过）。"""
        c, token = client
        r = c.post("/api/v1/channels/probe", headers=self._hdr(token),
                   json={"ids": ["c:nope"], "persist": False})
        assert r.status_code == 404
        assert r.json()["error"] == "channel_not_found"

    def test_探测端点_ids_类型不对要_422(self, client):
        c, token = client
        r = c.post("/api/v1/channels/probe", headers=self._hdr(token),
                   json={"ids": "c:one", "persist": False})
        assert r.status_code == 422
        assert r.json()["error"] == "illegal_ids"

    def test_探测端点_只探配了目标的渠道(self, client):
        """⚠ 关键口径：不传 ids 时**只探有探针目标的**（今天 28 条），绝不盲探 131 条。
        这里用一个"台账里有、但探针表里没有"的渠道来钉：它必须仍是 unknown。"""
        c, token = client
        cr.seed_channels()
        cr.upsert_channel("t:no-target", {"name": "没配探针", "category": "law"})
        r = c.post("/api/v1/channels/probe", headers=self._hdr(token),
                   json={"persist": True, "ids": ["t:no-target"]})
        # 显式点名一个**没配目标**的渠道：它不该被探（probe_url 空 ⇒ unknown，不计失败）
        assert r.status_code == 200
        assert r.json()["data"]["results"][0]["state"] == "unknown"
        assert cr.get_channel("t:no-target")["consecutive_failures"] == 0


class TestShippedSeed:
    """随包发布的种子（`src/core/update/channel_seed.json`）本身的契约。"""

    def test_种子可读且_id_唯一(self):
        rows = cr.load_seed()
        assert len(rows) >= 100, f"R1 调研出 131 条，种子不该只剩 {len(rows)}"
        ids = [r["channel_id"] for r in rows]
        assert len(ids) == len(set(ids)), "channel_id 有重复"
        for r in rows:
            assert r["category"] in cr.CATEGORIES, f"{r['channel_id']} 类别非法：{r['category']}"

    def test_两根死兜底棒在种子里是_broken(self):
        """R1 的 G6（父代理已复核代码）：web/govcn 只解 mock 的 dict，真实 HTML 恒 miss。

        若哪天有人把它们改回 wired，这条会红 —— 那时必须同时改掉本用例并说明
        "真实 HTML 解析已经补上了"（不许悄悄改口径）。
        """
        rows = {r["channel_id"]: r for r in cr.load_seed()}
        for cid in ("ch:web", "ch:govcn"):
            assert rows[cid]["wiring"] == "broken", f"{cid} 又被当成能用的渠道了"
            assert "miss" in (rows[cid].get("note") or "")

    def test_接线名字不一致的渠道已在种子里记明(self):
        """R2 发现 G23（注册表键 `ttzb` vs 适配器名 `ttbz`）。

        ⚠ **本用例的判据在 R2b 改过一次**：R2 时它断言 `wiring == 'broken'`（那时字典按
        注册键建，链里的 `ttbz` 查不到）；R2b 把 `_build_adapters` 改成**按 `name` 建表**后
        这条渠道真的能用了 ⇒ 现在断言它 **wired**，同时**仍要求 note 里写明名字不一致**
        （卫生问题没消失，只是不再致命——不许把修复顺带粉饰成"原本没问题"）。
        """
        rows = {r["channel_id"]: r for r in cr.load_seed()}
        row = rows["ch:ttbz"]
        assert row["wiring"] == "wired", "G23 修完后团标渠道应当是 wired"
        assert "不一致" in (row.get("note") or ""), "名字不一致这条卫生提示必须留着"
        assert "ttzb" in (row.get("note") or "")

    def test_能力数远小于台账条数(self):
        """口径用例：如果哪天这两个数相等，说明有人把"调研到"当成了"能干活"。"""
        cr.seed_channels()
        s = cr.summary()
        assert s["total"] > s["by_wiring"]["wired"]
        assert s["by_wiring"]["wired"] <= 13, "在链上的适配器最多 13 个（注册总数）"
