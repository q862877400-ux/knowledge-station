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


class Test号段列与读写:
    """§11.0 R7：`segments_json`（号段）必须**真的在表里**、能写能读、且列进补列清单。

    为什么单列一个类：迁移是"新库直接带列、老库 PRAGMA 补列"两条路（`schema.sql` 与
    `sqlite_db._CHANNEL_EXTRA_COLS`）。只改一处的话，**老库会在写号段时报
    `no such column`**，而本地开发用的都是新库 ⇒ 这个错只会在别人机器上出现。
    """

    def test_表里真的有号段列(self, db):
        cols = {r[1] for r in db.execute("PRAGMA table_info(update_channel)").fetchall()}
        assert "segments_json" in cols

    def test_补列清单必须包含号段列(self):
        from src.core.storage.sqlite_db import _CHANNEL_EXTRA_COLS
        assert "segments_json" in {c for c, _ in _CHANNEL_EXTRA_COLS}

    def test_写入读回_并归一(self, db):
        row = cr.upsert_channel("ch:seg_demo", {"name": "号段演示", "category": "other",
                                                "segments_json": [" HJ ", "HJ", "GB 50"]})
        assert json.loads(row["segments_json"]) == ["HJ", "GB 50"]
        assert cr.parse_segments(cr.get_channel("ch:seg_demo") or {}) == ("HJ", "GB 50")

    def test_写入坏形状要抛且不动原值(self, db):
        cr.upsert_channel("ch:seg_demo2", {"name": "号段演示2", "category": "other",
                                           "segments_json": ["HJ"]})
        with pytest.raises(ValueError):
            cr.upsert_channel("ch:seg_demo2", {"segments_json": "HJ"})
        assert cr.parse_segments(cr.get_channel("ch:seg_demo2") or {}) == ("HJ",)

    def test_种子导入也能带号段(self, db):
        """种子（`_DESCRIPTIVE`）与人工写走同一条校验 ⇒ 不允许多一条绕过路径。"""
        assert "segments_json" in cr._DESCRIPTIVE


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

    def test_每条都带_has_probe_target(self, client):
        """R6：面板要能分开「⚪ 无探针」与「⚪ 还没探过」——否则灰行读不出该不该动手。

        判据落在**探针目标表**上（唯一所有者），不是另存一份到数据库。
        """
        from src.core.update import channel_probe as cp
        c, token = client
        cr.seed_channels()
        targets = cp.load_targets()
        assert targets, "目标表不该是空的（R6 之后有 100+ 条）"
        items = c.get("/api/v1/channels?limit=2000", headers=self._hdr(token)).json()["data"]["items"]
        assert items and all("has_probe_target" in i for i in items)
        # 与目标表逐条对齐（不是"大部分对"）
        for i in items:
            assert i["has_probe_target"] == (i["channel_id"] in targets), i["channel_id"]
        # 两个方向都要有实例（否则这条断言没意义）
        assert any(i["has_probe_target"] for i in items)
        assert any(not i["has_probe_target"] for i in items)

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

    def test_兜底链现状_web_已摘除_govcn_已换棒(self):
        """R1 的 G6 抓出**两根**死兜底棒；R5b 把 `govcn` 换成真接口，R5c 把 `web` **摘出链外**。

        ⚠ 这条判据**被有意改过两次**（每次都改在 ledger 里写明）：R2 时是"两根都 broken"，
        只改一根时也**不许**留旧断言——那等于"宁可显示失效也不承认修好"，与"宁可虚报"同样错。
        现在的口径：`web`=unwired（**不在链上**，不是"在链上但不工作"）、`govcn`=wired 且 note 写明边界。
        """
        rows = {r["channel_id"]: r for r in cr.load_seed()}
        assert rows["ch:web"]["wiring"] == "unwired", "web 不在链上 ⇒ 口径应是未接线"
        assert "摘除" in (rows["ch:web"].get("note") or ""), rows["ch:web"].get("note")
        assert rows["ch:govcn"]["wiring"] == "wired", "govcn 换棒后应当是 wired"
        note = rows["ch:govcn"].get("note") or ""
        assert "换棒" in note and "政策文件库" in note, f"换棒说明缺失：{note}"

    def test_降级链里不再有已知失效的渠道(self):
        """链上的每一棒都必须是"能用"的：`broken` 在种子里应为 0。

        为什么值得单钉：`broken` 是"在链上但实测不工作"——它会让覆盖率虚高（R1 的教训）。
        若将来又出现 broken>0，要么修它、要么把它摘出链外，**不许留着**。
        """
        rows = cr.load_seed()
        broken = [r["channel_id"] for r in rows if r["wiring"] == "broken"]
        assert broken == [], f"链上又出现了已知失效的渠道：{broken}"
        from src.core.update.channels.routing import _FALLBACK
        assert "web" not in _FALLBACK, "web 又被放回降级链了"

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

    # ── §11.0 R7-数据轮（2026-09-19）：**号段的种子契约** ────────────────────────
    # 死号段为什么不能只在真库上量：`tests/conftest.py` 把测试库隔离到**空临时库**
    # （真库 6417 个号那张表在用例里不存在）。所以"写了却一个号都不命中"这道护栏只能落在
    # **种子契约**这一层：形状 + 大小写 + 拿"真库形状"的号表量一遍已声明的号段。
    # 真库全量的那一遍由 `scripts/chain-snapshot.py` 留证据（它是唯一能读真库的入口）。

    #: 真库号段的**真实形状**（R7-数据轮实测：GB/T 6129 · GB+5 位 148 · GB+4 位 119 · GBZ 12）
    #: ⚠ **口径（复核 corr3 B4，2026-09-20 补；只加口径，断言与数值一字未改）**：这里的 `GB/T 6129`
    #: 是**未折全角**统计；**折叠全角**（仓库 `_fold_segment` 把 `GB／T 14308-2010` 折成 `GB/T…`）是 **6130**。
    #: 两个数并存不是矛盾 —— 口径说明见 `docs/CHANNEL-COVERAGE-PLAN.md` 的 R7-数据轮"更正后的形状"。
    #: 本节只拿它当"号长什么样"的样本，**不依赖**是 6129 还是 6130；别据此改断言。
    _REAL_SHAPES = ("GB/T 30871-2022", "GB/T 14308-2010", "GB 5009.11-2024",
                    "GB 50493-2019", "GB 30871-2022", "GBZ 1-2010")

    def test_种子号段形状与大小写(self):
        """每条的 `segments_json` 必须是**非空字符串数组**、无前后空白/重复；`ch:` 名字要有适配器。

        ⚠ **大小写为什么也在这里断言**：`routing._fold_segment` 刻意**不折大小写**（标准号本身大写），
        所以 `gb` / `hj` 这种写法**永远不命中**——而"手滑会静默失效"正是 R7 要挡的那种失败。
        单字符号段（如 `T`）免检：它同时是很多号段的合法前缀。
        ⚠ **适配器那一条**（`ch:` 名字必须在 `routing._fold_segment` 的那套名字里）：号段的加法
        fail-closed——代码里没有的适配器**永不进链**，写了号段只会让人以为接上了。
        """
        from src.core.update.channels.ledger_chain import _adapter_names
        known = _adapter_names()
        declared = 0
        for r in cr.load_seed():
            if "segments_json" not in r:
                continue
            segs = cr.check_segments(r["segments_json"])       # 形状不合法当场抛（写路径口径）
            assert segs == list(r["segments_json"]), f"{r['channel_id']} 号段未归一（空白/重复）"
            declared += 1
            for seg in segs:
                assert seg == seg.strip() and seg, f"{r['channel_id']} 号段带空白或为空：{seg!r}"
                if len(seg) > 1:
                    assert seg == seg.upper(), \
                        f"{r['channel_id']} 号段 {seg!r} 含小写 ⇒ **永远不命中**（折叠不折大小写）"
            if r["channel_id"].startswith("ch:"):
                assert r["channel_id"][3:] in known, \
                    f"{r['channel_id']} 声明了号段，但代码里没有这个适配器（fail-closed：永不进链）"
        assert declared == 0, (
            "随包种子今天**零号段声明**（R7-数据轮的裁定：能填的两条证据不足、覆盖清楚的几条"
            "库里一个号都没有 ⇒ 填了就是死号段）。要填就必须同时把这条断言改成实际条数，"
            "并先给出「这条渠道管哪些号段」的调研证据（见 CHANNEL-COVERAGE-PLAN 的 R7-数据轮）")

    def test_已声明号段不许是死号段(self):
        """拿**真库形状**的号表量每一个已声明的号段：一个号都不命中 ⇒ 红。

        这就是"死号段"判据的**种子侧**版本（真库侧在全快照里）。今天 0 条声明 ⇒ 天然绿；
        将来有人填错（例如给 `ttbz` 填 `TZ/`、给 `std_samr_hb` 填 `行标`）就当场红。
        ⚠ 这不是"多此一举"：死号段的表现是**那条渠道永远不进链**，而台账上看不出是"写错了"
        还是"今天没料"——与 R7 的 `segments_report['dead']` 是同一道护栏的两个入口。
        """
        from src.core.update.channels.routing import segment_matches
        dead = []
        for r in cr.load_seed():
            for seg in cr.check_segments(r.get("segments_json")):
                if not any(segment_matches(no, seg) for no in self._REAL_SHAPES):
                    dead.append((r["channel_id"], seg))
        assert dead == [], (
            f"这些号段在真库真实形状的号表上**一个号都不命中**（写法错 ⇒ 渠道永不进链）：{dead}")
