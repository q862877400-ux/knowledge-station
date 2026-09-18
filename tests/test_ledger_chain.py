# -*- coding: utf-8 -*-
"""台账驱动的降级链测试（`src/core/update/channels/ledger_chain.py`，§11.0 R6c）。

守三件（每一件都对应一次真实的判断）：
  1. **成员资格是显式名单**：台账里 `wiring='wired'` **不等于**兜底成员——
     第一版规则把 5 条前缀专用渠道拖进泛查链，快照显示 9/9 个样例号都变（见模块 docstring）；
  2. **台账只做它能作准的两件事**：硬过滤（`enabled=0` / `wiring='broken'`）与报告；
     **探针 `state` 不过滤**（链随探针抖动是另一件事，要单独决策）；
  3. **代码与台账不一致不许静默**：台账说 wired、代码里没有该适配器 ⇒ 必须报出来（G23 的教训）。

全部离线（`rows` 用注入的假台账），不读真库、不触网；真机那一次由 `scripts/chain-snapshot.py` 留证据。
"""
from __future__ import annotations

import pytest

from src.core.storage import channel_repo as cr
from src.core.update.channels import ledger_chain as lc
from src.core.update.channels.routing import fallback_chain


def _row(cid: str, **kw) -> dict:
    base = {"channel_id": cid, "name": cid, "wiring": "wired", "enabled": 1, "state": "ok"}
    base.update(kw)
    return base


@pytest.fixture(autouse=True)
def _clean_channel_table(db):
    """真库用例要一张干净的表（测试库 data_dir 是**会话级**的，模块之间会互相污染——
    `test_channel_repo.py` 第一次运行就因这个红过 7 条）。顺带 `db` 也保证 schema 已建。"""
    db.execute("DELETE FROM update_channel")
    db.commit()
    yield


class Test过滤:
    def test_人工停用不进链(self):
        rows = [_row("ch:official_gb"), _row("ch:govcn", enabled=0)]
        assert lc.ledger_fallback_chain(rows, roster=("official_gb", "govcn")) == ("official_gb",)

    def test_known_broken_不进链(self):
        rows = [_row("ch:official_gb"), _row("ch:govcn", wiring="broken")]
        assert lc.ledger_fallback_chain(rows, roster=("official_gb", "govcn")) == ("official_gb",)

    def test_探针说_down_也不过滤(self):
        """R6a 实测：down 的 13 条里混着瞬时/WAF/我方 TLS 指纹 ⇒ 按一次探针踢渠道会让链抖动。"""
        rows = [_row("ch:official_gb", state="down"), _row("ch:govcn", state="down")]
        assert lc.ledger_fallback_chain(rows, roster=("official_gb", "govcn")) == \
            ("official_gb", "govcn")

    def test_台账里没有的成员保留_fail_open(self):
        """没 seed 的库不该让巡检失去整条链；要停用请用 enabled=0（显式动作）。"""
        assert lc.ledger_fallback_chain([], roster=("official_gb", "govcn")) == \
            ("official_gb", "govcn")

    def test_顺序就是名单顺序(self):
        rows = [_row("ch:a"), _row("ch:b")]
        assert lc.ledger_fallback_chain(rows, roster=("b", "a")) == ("b", "a")


class Test成员资格不是wired:
    def test_wired_不等于兜底成员(self):
        """核心回归：`wiring='wired'` 的专用渠道**不许**被自动塞进兜底链。"""
        rows = [_row("ch:official_gb"), _row("ch:govcn"), _row("ch:ndls"), _row("ch:dbba")]
        assert lc.ledger_fallback_chain(rows, roster=("official_gb", "govcn")) == \
            ("official_gb", "govcn")

    def test_候选要被报出来而不是被悄悄提升(self):
        rows = [_row("ch:official_gb"), _row("ch:govcn"), _row("ch:ndls"), _row("seed:law-cn:x")]
        rep = lc.ledger_chain_report(rows, roster=("official_gb", "govcn"),
                                     known={"official_gb", "govcn", "ndls"})
        assert [c["channel_id"] for c in rep["roster_candidates"]] == ["ch:ndls"]
        assert rep["chain"] == ["official_gb", "govcn"]      # 链没被改动


class Test一致性报告:
    def test_台账说wired但代码里没有适配器要报出来(self):
        rows = [_row("ch:official_gb"), _row("ch:ghost")]
        rep = lc.ledger_chain_report(rows, roster=("official_gb",),
                                     known={"official_gb", "govcn"})
        assert [m["channel_id"] for m in rep["missing_in_code"]] == ["ch:ghost"]

    def test_非适配器渠道不参与缺失判定(self):
        """`seed:law-cn:*` / `tool:*` 本来就不是适配器名，不该被报成"台账/代码不一致"。"""
        rows = [_row("seed:law-cn:x", wiring="wired"), _row("tool:y", wiring="wired")]
        rep = lc.ledger_chain_report(rows, roster=("official_gb",),
                                     known={"official_gb"})
        assert rep["missing_in_code"] == []
        assert rep["roster_candidates"] == []

    def test_wired_且探针_down_要报出来(self):
        rows = [_row("ch:official_gb", state="down", last_error_code="endpoint_gone",
                     consecutive_failures=2)]
        rep = lc.ledger_chain_report(rows, roster=("official_gb",), known={"official_gb"})
        assert rep["wired_but_probe_down"][0]["channel_id"] == "ch:official_gb"
        assert rep["chain"] == ["official_gb"]


class Test真库:
    """一条真库用例：缺省 roster（=今天的兜底链）在真库上应当**无差异**。"""

    def test_缺省名单下真库过滤后等于今天的链(self):
        cr.seed_channels()
        assert lc.ledger_fallback_chain() == fallback_chain()

    def test_真库报告里不含种子外的噪音(self):
        cr.seed_channels()
        rep = lc.ledger_chain_report()
        assert rep["chain"] == list(fallback_chain())
        assert all(m["channel_id"] for m in rep["missing_in_code"]) is True

    @pytest.mark.parametrize("cid", ["ch:ndls", "ch:dbba"])
    def test_专用渠道在候选里而不在链里(self, cid):
        cr.seed_channels()
        rep = lc.ledger_chain_report()
        assert cid in {c["channel_id"] for c in rep["roster_candidates"]}
        assert cid not in rep["chain"]
