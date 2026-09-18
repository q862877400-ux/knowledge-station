# -*- coding: utf-8 -*-
"""五类能力表测试（`src/core/update/channel_answers.py` + `channel_answers.json`，§11.0 R6c）。

守四件：
  1. **覆盖齐全**：台账 131 条在表里都有声明（缺一条就等于 R6c 的"按问题选渠道"漏一条）；
  2. **词表封闭**：只许出现五类词，不许各写各的（"发布" vs "发布日期"这种分歧最难查）；
  3. **口径可执行**：把 R6c-1 定的两条口径钉成用例——
     ① **mock/fixture 才供数的字段不算能力**（`ch:discover_search` 是反例）；
     ② `category='tool'` 的代码仓库**不参与五类**（规则，不是"没查"）；
  4. **能力 ≠ 可用性**：`channels_for(only_ok=True)` 要能把探针判死的渠道滤掉，
     但**不能**因此把声明本身改掉（两者是两根轴）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.storage import channel_repo as cr
from src.core.update import channel_answers as ca

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _clean_channel_table(db):
    db.execute("DELETE FROM update_channel")
    db.commit()
    yield


@pytest.fixture()
def table():
    return ca.load_answers()


class Test覆盖与词表:
    def test_台账每一条都有声明(self, table):
        ids = {c["channel_id"] for c in json.loads(
            (ROOT / "src" / "core" / "update" / "channel_seed.json").read_text(encoding="utf-8")
        )["channels"]}
        assert set(table) == ids, f"缺：{sorted(ids - set(table))}；多：{sorted(set(table) - ids)}"

    def test_只许出现五类词(self, table):
        bad = {cid: [a for a in (e.get("answers") or []) if a not in ca.CLASSES]
               for cid, e in table.items()}
        bad = {k: v for k, v in bad.items() if v}
        assert bad == {}, f"这些渠道写了五类之外的词：{bad}"

    def test_每条都有出处与置信(self, table):
        for cid, e in table.items():
            assert (e.get("basis") or "").strip(), f"{cid} 缺 basis（追不回原处）"
            assert e.get("confidence") in ("high", "medium", "low"), f"{cid} 置信取值非法"
            assert e.get("source"), f"{cid} 缺 source"

    def test_五类就是设计稿那五个(self):
        assert ca.CLASSES == ("发布", "修订", "废止", "现行性", "编号核验")


class Test口径:
    def test_mock才供数的字段不算能力(self, table):
        """R6c-1 口径①：`discover.py` 卡片契约读 `item["status"]`，但只有 mock 会填。

        这条**必须**钉住：否则以后有人看到"代码里有 status 字段"就给这条渠道声明能力，
        而真实通路根本不解析（R1 的 G6/G14 是同一条教训）。
        """
        e = table["ch:discover_search"]
        assert e["answers"] == []
        assert e["confidence"] == "medium"          # "未确认"，不是"硬否定"

    def test_工具类一律不参与五类(self, table):
        """口径②：代码仓库/工具不是采集通路——它们是**规则判空**或**逐条判空**，不是"我们没查"。

        ⚠ 来源有两种：`seed:law-cn:*` 那 7 条被 C 组**逐条查过**（basis 里写了
        "查无此物/闭源/外法域"），`tool:*` 那批走 D 组规则——两者都合法，
        但**都必须有出处**，不许出现"没登记的 tool"。
        """
        tools = [c["channel_id"] for c in json.loads(
            (ROOT / "src" / "core" / "update" / "channel_seed.json").read_text(encoding="utf-8")
        )["channels"] if c.get("category") == "tool"]
        assert tools, "种子里应当有 tool 类渠道"
        for cid in tools:
            assert table[cid]["answers"] == [], cid
            assert table[cid]["source"] in ("R6c-1-D-rule", "R6c-1-C"), cid
        assert any(table[cid]["source"] == "R6c-1-D-rule" for cid in tools), "规则那批也要在"

    def test_r1_那批是调研期声明_标_medium(self, table):
        r1 = [e for e in table.values() if e["source"] == "R1-seed"]
        assert r1 and all(e["confidence"] == "medium" for e in r1)
        assert all("未逐条复核" in e["basis"] for e in r1)


class Test查询:
    def test_channels_for_错误类名要抛(self):
        with pytest.raises(ValueError, match="不是五类之一"):
            ca.channels_for("发布日期")

    def test_能答现行性的渠道包含真实通路(self, table):
        ids = ca.channels_for("现行性", table=table)
        assert "ch:ndls" in ids and "ch:official_gb" in ids
        assert not any(cid.startswith("tool:") for cid in ids)

    def test_未登记的渠道返回空而不抛(self, table):
        assert ca.answers_of("ch:不存在的", table) == []

    def test_only_ok_会滤掉探针判死的渠道(self, table):
        """能力与可用性是两根轴：声明不改，但选渠道时要能滤。"""
        ids_all = ca.channels_for("现行性", table=table)
        rows = [{"channel_id": cid, "state": "down" if cid == "ch:ndls" else "ok"}
                for cid in ids_all]
        ids_ok = ca.channels_for("现行性", table=table, rows=rows, only_ok=True)
        assert "ch:ndls" in ids_all and "ch:ndls" not in ids_ok
        assert set(ids_ok) <= set(ids_all)

    def test_coverage_小结(self, table):
        s = ca.coverage(table)
        assert s["total"] == len(table)
        assert set(s["per_class"]) == set(ca.CLASSES)
        assert sum(s["answers_per_channel"].values()) == len(table)

    def test_真库默认路径能读(self):
        cr.seed_channels()
        tbl = ca.load_answers()
        assert ca.answers_of("ch:official_gb", tbl), "官方国标渠道至少要能答一类"
