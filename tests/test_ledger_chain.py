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
        assert lc.ledger_fallback_chain(rows, roster=("b", "a"), known={"a", "b"}) == ("b", "a")


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
    def test_名单里有代码里没有的适配器要报出来且不进链(self):
        """独立复核 b29 抓到的欠账：`known` 参数原先承诺过却没用（`_ = known` 是死代码）。

        现在 fail-closed：名单里没有适配器的名字**不进链**，并由 `roster_missing_in_code` 点名。
        """
        rows = [_row("ch:official_gb")]
        chain = lc.ledger_fallback_chain(rows, roster=("official_gb", "nope_x"),
                                         known={"official_gb"})
        assert chain == ("official_gb",), "没有适配器的名单成员不许留在链里"
        rep = lc.ledger_chain_report(rows, roster=("official_gb", "nope_x"),
                                     known={"official_gb"})
        assert [m["adapter"] for m in rep["roster_missing_in_code"]] == ["nope_x"]

    def test_名单重复成员去重且要告警(self):
        """复核 b29-fix 的 a：不去重的话链里会出现两次同名（巡检白跑一遍）而没人知道。"""
        rows = [_row("ch:official_gb"), _row("ch:govcn")]
        chain = lc.ledger_fallback_chain(rows, roster=("official_gb", "official_gb", "govcn"))
        assert chain == ("official_gb", "govcn")
        rep = lc.ledger_chain_report(rows, roster=("official_gb", "official_gb", "govcn"))
        assert rep["roster_duplicates"] == ["official_gb"]

    def test_名单成员在台账里没有行要提一句(self):
        """复核 b29-fix 的 b：按设计 fail-open 保留，但不能一个字都不说。"""
        rep = lc.ledger_chain_report([], roster=("official_gb", "govcn"))
        assert rep["chain"] == ["official_gb", "govcn"]
        assert {r["adapter"] for r in rep["roster_not_in_ledger"]} == {"official_gb", "govcn"}

    @pytest.mark.parametrize("row_kw", [
        {"wiring": "BROKEN"}, {"wiring": "broken "}, {"wiring": " Broken"},
        {"enabled": "0"}, {"enabled": False}, {"enabled": "FALSE"}, {"enabled": " False "},
    ])
    def test_写法差异也要被挡住(self, row_kw):
        """复核 b29-fix 的 c：`BROKEN` / `'0'` 这类写法差异过去会让"已知失效"照旧留在链里
        —— 那正是"配置写错伪装成渠道可用"。（`'FALSE'` 是 b29-fix2 补的：同一个函数里
        `_wiring` 会小写、`_enabled_off` 不会——口径不一致是最难查的那类。）"""
        rows = [_row("ch:official_gb", **row_kw)]
        assert lc.ledger_fallback_chain(rows, roster=("official_gb",)) == ()

    @pytest.mark.parametrize("kw", [
        {"enabled": None}, {"enabled": True}, {"enabled": 1}, {"enabled": "1"},
    ])
    def test_这些不算停用(self, kw):
        """`None`（没写）/`True`/`1`/`'1'` 都不是"停用"——别把缺失读成人工意图。"""
        rows = [_row("ch:official_gb", **kw)]
        assert lc.ledger_fallback_chain(rows, roster=("official_gb",)) == ("official_gb",)

    def test_生成器名单也照收(self):
        """复核 b29-fix2 的坑：生成器只能消费一次，而 report 要遍历它好几遍 ⇒ 入口先固化。"""
        rows = [_row("ch:official_gb"), _row("ch:govcn")]
        gen = (n for n in ("official_gb", "govcn"))
        rep = lc.ledger_chain_report(rows, roster=gen, known={"official_gb", "govcn"})
        assert rep["chain"] == ["official_gb", "govcn"]
        assert rep["roster_candidates"] == []          # 名单里的成员不该被误报成"可提升候选"

    def test_重复成员的报告不重复列(self):
        rows: list[dict] = []
        rep = lc.ledger_chain_report(rows, roster=("official_gb", "official_gb"),
                                     known={"official_gb"})
        assert rep["roster_duplicates"] == ["official_gb"]
        assert len(rep["roster_not_in_ledger"]) == 1   # 同一个成员只提一次

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

    @pytest.mark.parametrize("cid", ["ch:dbba", "ch:hbba"])
    def test_专用渠道在候选里而不在链里(self, cid):
        """前缀专用渠道（DB→dbba、行标→hbba）**不在泛查兜底链里**，所以是"可提升候选"。

        ⚠ 2026-09-18（R6c-3b）之后这条**换了参数**：原来点的是 `ch:ndls`，
        而 R6c-3b 把 `ndls` 正式插进了兜底链（量出来的：`govcn` 在标准号上 1/10、`ndls` 6/10）
        ⇒ 它从"候选"**毕业**成"链上成员"。所以现在改用两根仍是前缀专用、且**不在**兜底链里的渠道，
        并另加一条用例正面钉住 ndls 的毕业（见下一条）：
        改参数而不是删用例，是因为"候选报告"这个能力本身还要继续被守。
        """
        cr.seed_channels()
        rep = lc.ledger_chain_report()
        assert cid in {c["channel_id"] for c in rep["roster_candidates"]}
        assert cid not in rep["chain"]

    def test_ndls_已毕业进兜底链(self):
        """R6c-3b：`ndls` 从"可提升候选"变成"链上成员"，这条正面钉住它别再被挪走。"""
        cr.seed_channels()
        rep = lc.ledger_chain_report()
        assert "ch:ndls" not in {c["channel_id"] for c in rep["roster_candidates"]}
        assert "ndls" in rep["chain"]


class Test巡检真的按台账走:
    """§11.0 R6h：把台账接进**巡检**（在这之前 `ledger_chain` 只被快照脚本用，巡检不读它）。

    业主的诉求原话里有「渠道**可人工维护**」——如果台账里停用一条渠道而巡检照旧问它，
    那"可维护"就是假的。这个类就是钉住"**人工动作真的改变巡检行为**"。
    """

    def test_人工停用让巡检不再问它(self):
        """`enabled=0` ⇒ 该渠道**从巡检的链里消失**（不只是面板上显示停用）。"""
        rows = [_row("ch:official_gb"), _row("ch:ndls", enabled=0), _row("ch:govcn")]
        chain = lc.chain_for_number("GB/T 1234-2020", rows)
        assert "ndls" not in chain
        assert chain == ("official_gb", "govcn")

    def test_known_broken_让巡检不再问它(self):
        rows = [_row("ch:official_gb"), _row("ch:ndls", wiring="broken"), _row("ch:govcn")]
        assert "ndls" not in lc.chain_for_number("GB/T 1234-2020", rows)

    def test_前缀首选也受台账管(self):
        """前缀首选（HJ→`mee`）同样受过滤：人工停用它，HJ 号就退回泛查链。

        这条守的是"**过滤是加在整条链上的**，不是只加在兜底段"——
        只过滤兜底段的话，前缀首选会变成一条**绕过人工意图**的后门。
        """
        rows = [_row("ch:mee", enabled=0), _row("ch:official_gb"), _row("ch:ndls"), _row("ch:govcn")]
        chain = lc.chain_for_number("HJ 1234-2020", rows)
        assert chain[0] != "mee"
        assert chain == ("official_gb", "ndls", "govcn")

    def test_没有台账行时不过滤也不读库(self):
        """`rows=None` ⇒ 原样返回 `select_chain`（**不读库、不 I/O**）。

        为什么这条重要：`chain_for_number` 被 `inspector._probe_number` 调用，
        而那个函数的纪律是"**只触网**"。这里若偷偷读库，"只触网"就名存实亡，
        且 DB 故障会变成热路径上的隐藏依赖。用"把 repo 打桩成会炸"来正面钉住不读库。
        """
        from src.core.update.channels.routing import select_chain

        def _boom(*_a, **_kw):
            raise AssertionError("rows=None 时不该读库")

        monkey = pytest.MonkeyPatch()
        monkey.setattr(cr, "list_channels", _boom)
        try:
            assert lc.chain_for_number("GB/T 1234-2020", None) == select_chain("GB/T 1234-2020")
        finally:
            monkey.undo()

    def test_台账缺该行则保留_fail_open(self):
        """台账里**查不到**某成员 ⇒ 保留（fail-open）：没 seed 的库不该让巡检失去整条链。"""
        rows = [_row("ch:official_gb")]          # 只有一条；ndls/govcn 没有行
        assert lc.chain_for_number("GB/T 1234-2020", rows) == ("official_gb", "ndls", "govcn")

    def test_不做加法_只做减法(self):
        """台账 `wired` 但**不在** `select_chain` 里的渠道，不会因为这个函数进链。

        （提升是行为改变：泛查链变长 = 每号更多请求 —— 那要单独一步决定。）
        ⚠ R7 之后这条的准确说法是：**凭 `wired` 不构成加法**；构成加法的只有**号段声明**
        （见 `Test号段加法`）。这个用例里 `ttbz` 没有任何号段 ⇒ 照旧不进链。
        """
        rows = [_row("ch:ttbz"), _row("ch:official_gb"), _row("ch:ndls"), _row("ch:govcn")]
        # GB/T 号上 ttbz 不是前缀首选、也不在兜底链里 ⇒ 即便台账说 wired 也不出现
        assert "ttbz" not in lc.chain_for_number("GB/T 1234-2020", rows)


class Test号段加法:
    """§11.0 R7（2026-09-19）：**号段→渠道**成为台账里可维护的事实，链按它做加法。

    为什么要这个字段：R6g 量出"有适配器的 13 条里只有 3 条在链上"，根因是号段→渠道此前只
    硬编码在 `routing._PREFIX_ROUTE`（代码）里 —— 台账（业主能改的那层）无从表达。
    加法的三条纪律（每条都有一次真实的判断在背后）：

      1. **只加尾巴**：路由链的顺序一个字节都不动（否则"先问谁"被悄悄改了）；
      2. **只加路由链里没有的**：路由链里有、但被人工停用/标 broken 的，**不许**被号段加回来
         —— 否则"人工停用"会被自己的号段配置绕过；
      3. **代码里没有的适配器不进链**（fail-closed），并由报告点名。
    """

    def _seg(self, cid, segs, **kw):
        import json
        return _row(cid, segments_json=json.dumps(segs, ensure_ascii=False), **kw)

    def test_号段命中就多一根尾巴(self):
        """`mee` 声明 `GB` ⇒ GB 号在泛查链之后多问一根 `mee`（今天它一条 GB 号都到不了）。"""
        rows = [_row("ch:official_gb"), _row("ch:ndls"), _row("ch:govcn"), self._seg("ch:mee", ["GB"])]
        assert lc.chain_for_number("GB 30871-2022", rows) == \
            ("ndls", "official_gb", "govcn", "mee")

    def test_只加尾巴_路由链顺序不动(self):
        rows = [_row("ch:official_gb"), _row("ch:ndls"), _row("ch:govcn"), self._seg("ch:mee", ["GB"])]
        chain = lc.chain_for_number("GB 30871-2022", rows)
        assert chain[:3] == ("ndls", "official_gb", "govcn"), "路由链的顺序不许被加法改动"

    def test_号段不许把人工停用的渠道加回来(self):
        """**加法与过滤的正确交互**：`ndls` 被停用、但它也声明了 `GB` ⇒ 不许被加回链尾巴。

        没这条环检查的话，"人工停用一条渠道"会被它自己的号段配置默默撤销 ——
        而且是在**链的尾部**，现场更难看出来（它仍会被问到，只是排在后面）。
        """
        rows = [_row("ch:official_gb"), _row("ch:govcn"),
                self._seg("ch:ndls", ["GB"], enabled=0),
                self._seg("ch:ndls_broken", ["GB"], wiring="broken")]
        chain = lc.chain_for_number("GB 30871-2022", rows)
        assert chain == ("official_gb", "govcn")

    def test_号段不命中就没尾巴(self):
        rows = [_row("ch:official_gb"), _row("ch:ndls"), _row("ch:govcn"), self._seg("ch:mee", ["HJ"])]
        assert lc.chain_for_number("GB 30871-2022", rows) == ("ndls", "official_gb", "govcn")

    def test_代码里没有的适配器不进链(self):
        rows = [_row("ch:official_gb"), _row("ch:govcn"), self._seg("ch:nope_x", ["GB"])]
        # ⚠ 台账里没有 `ndls` 的行 ⇒ fail-open 保留（与有没有号段无关）；关键是 `nope_x` 不进链
        chain = lc.chain_for_number("GB 30871-2022", rows)
        assert chain == ("ndls", "official_gb", "govcn")
        assert "nope_x" not in chain

    def test_已经在前缀首选里的渠道不会重复出现(self):
        """`HJ` 号本来就首选 `mee`，`mee` 又声明 `HJ` ⇒ 链里只出现一次（去重）。"""
        rows = [_row("ch:official_gb"), _row("ch:ndls"), _row("ch:govcn"), self._seg("ch:mee", ["HJ"])]
        chain = lc.chain_for_number("HJ 1234-2020", rows)
        assert chain == ("mee", "official_gb", "ndls", "govcn")

    def test_rows_None_时也不做加法且不读库(self):
        """没有台账行 ⇒ 既不过滤也不加法（fail-open 的同一条口径）。"""
        from src.core.update.channels.routing import select_chain

        def _boom(*_a, **_kw):
            raise AssertionError("rows=None 时不该读库")

        monkey = pytest.MonkeyPatch()
        monkey.setattr(cr, "list_channels", _boom)
        try:
            assert lc.chain_for_number("GB 30871-2022", None) == select_chain("GB 30871-2022")
        finally:
            monkey.undo()

    @pytest.mark.parametrize("seg,no,want", [
        (["GB50"], "GB 50123-2019", True),      # 台账写 GB50 也能命中带空格的号
        (["GB 50"], "GB50123-2019", True),      # 反过来同样成立（两侧同一折叠口径）
        (["T/"], "T/ZSA 328-2026", True),
        (["T/"], "GB/T 14308-2010", False),     # ⚠ 团标 T/ 不许命中 GB/T（折空白不会把 GB 抹掉）
        (["GB"], "GB/T 14308-2010", True),
    ])
    def test_号段匹配口径(self, seg, no, want):
        import json
        rows = [_row("ch:official_gb"), _row("ch:govcn"),
                _row("ch:mee", segments_json=json.dumps(seg))]
        assert (("mee" in lc.chain_for_number(no, rows)) is want)

    def test_号段顺序确定_同一库上可复现(self):
        """尾巴顺序 = 台账顺序（`list_channels` 的 ORDER BY category,name）⇒ 链不抖。"""
        import json
        rows = [_row("ch:official_gb"), _row("ch:govcn"),
                _row("ch:mee", segments_json=json.dumps(["GB"])),
                _row("ch:dbba", segments_json=json.dumps(["GB"]))]
        first = lc.chain_for_number("GB 30871-2022", rows)
        assert first == lc.chain_for_number("GB 30871-2022", rows)
        assert first[-2:] == ("mee", "dbba")


class Test号段报告:
    """号段的三类欠账必须**被算出来**（写错与没写的现场表现都是静默）。"""

    def _seg(self, cid, segs, **kw):
        import json
        return _row(cid, segments_json=json.dumps(segs, ensure_ascii=False), **kw)

    def test_死号段被点名(self):
        """写了 `T/` 而真库里一个 T/ 号都没有 ⇒ 必须报出来（否则"渠道永不进链"没人知道）。"""
        rows = [self._seg("ch:ttbz", ["T/"])]
        rep = lc.segments_report(rows, ["GB 30871-2022"], known={"ttbz", "official_gb"})
        assert [d["segment"] for d in rep["dead"]] == ["T/"]
        assert rep["sample_size"] == 1

    def test_没给号表就说判不准_不假装没欠账(self):
        """**不给号表**（`[]`）⇒ `dead`/`gained` 一律不下结论，并在 `note` 里说清。

        ⚠ 复核 2026-09-19 抓到：我嘴上说"一个数字都不给"，代码却把 `numbers_gained` 写成 `0`
        —— 而 `0` 会被读成"量过了、没有"。现在它是 `None`（"没量"与"量出来是 0"必须能分开读）。
        """
        rows = [self._seg("ch:ttbz", ["T/"])]
        rep = lc.segments_report(rows, [])
        assert rep["dead"] == [] and rep["gained"] == {}
        assert rep["numbers_gained"] is None, "没给号表必须是 None，不能是 0"
        assert "T/" in rows[0]["segments_json"]
        assert "判不准" in rep["note"]

    def test_有适配器却到不了也没号段要列成待办(self):
        """这就是 R6g 那 10 条的形状：有适配器、今天任何号都到不了、也没声明号段。"""
        rows = [_row("ch:official_gb"), _row("ch:ndls"), _row("ch:govcn"), _row("ch:mee")]
        rep = lc.segments_report(rows, ["GB 30871-2022"], known={"official_gb", "ndls",
                                                                 "govcn", "mee"})
        assert [u["adapter"] for u in rep["unreachable_no_segments"]] == ["mee"]

    def test_号段带来的号数按号去重(self):
        """多个号段命中同一个号只算一次（否则"带来多少号"虚高）。"""
        import json
        rows = [self._seg("ch:mee", ["GB", "GB 3"])]
        rep = lc.segments_report(rows, ["GB 30871-2022"], known={"mee"})
        assert rep["gained"] == {"mee": 1}
        assert rep["numbers_gained"] == 1

    def test_被排除的行不计入带来多少号(self):
        """人工停用的渠道不该在"带来多少号"里贡献数字（那是虚高）。"""
        rows = [self._seg("ch:mee", ["GB"], enabled=0)]
        rep = lc.segments_report(rows, ["GB 30871-2022"], known={"mee"})
        assert rep["gained"] == {} and rep["declared"][0]["excluded"] is True


class Test号段形状校验:
    def test_非数组被拒(self):
        with pytest.raises(ValueError):
            cr.check_segments("HJ")

    @pytest.mark.parametrize("bad", [[""], ["  "], [None], [1], ["HJ", ""]])
    def test_空项或非字符串被拒(self, bad):
        with pytest.raises(ValueError):
            cr.check_segments(bad)

    def test_归一_去空白_保序去重(self):
        assert cr.check_segments([" HJ ", "HJ", "GB 50"]) == ["HJ", "GB 50"]

    def test_None_表示清空(self):
        assert cr.check_segments(None) == []

    def test_读路径容错_坏值给空元组而不是抛(self):
        """库里的历史脏数据不许把巡检弄炸（写路径拒绝、读路径容错）。"""
        assert cr.parse_segments({"segments_json": "{ not json"}) == ()
        assert cr.parse_segments({"segments_json": '{"a":1}'}) == ()
        assert cr.parse_segments({"segments_json": None}) == ()
        assert cr.parse_segments({"segments_json": '["HJ", 7, " "]'}) == ("HJ",)
