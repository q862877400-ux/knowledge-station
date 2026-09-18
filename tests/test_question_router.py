# -*- coding: utf-8 -*-
"""按问题选渠道测试（`src/core/update/channels/question_router.py`，§11.0 R6c-3）。

守五件事（对应设计稿 §3.2.1 的验收用例 1–5）：
  1. **候选 = 能答这一类 ∩ 在链上**——不在链上的渠道**不许**进候选（否则巡检会去问一条
     根本没接线的渠道，现场表现是"每号都多打几个请求、还都 miss"）；
  2. **两根轴分开**：`only_ok` 只是"今天别选它"，**不许**动能力表的声明；
  3. **顺序 = 链的顺序**（前缀专用渠道在前）；
  4. **空候选要能说清是哪一种**（`no_capability` / `off_chain` / `all_down`）——
     混成一个理由会让业主以为"查过了"（设计稿：该写 `unanswerable`，不是 `not_found`）；
  5. **`tool:` 永不出现**，且与本模块的"独立复算"对得上（`channel_answers` 是上限）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.core.storage import channel_repo as cr
from src.core.update import channel_answers as ca
from src.core.update.channels import question_router as qr
from src.core.update.channels.routing import first_route, select_chain

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def table():
    return ca.load_answers()


def _rows(states: dict[str, str]) -> list[dict[str, str]]:
    return [{"channel_id": cid, "state": st} for cid, st in states.items()]


class Test规则:
    def test_缺省就是五类_顺序按词表(self, table):
        got = qr.channels_for(table=table, only_ok=False)
        assert list(got) == list(ca.CLASSES)

    def test_候选顺序就是链的顺序(self, table):
        """前缀专用渠道天然排在兜底棒前面（T/ 号 → ttbz 第一）。"""
        for no, first in [("T/CECS 1000-2021", "ch:ttbz"),
                          ("GB 18218-2018", "ch:ndls"),
                          ("DB44/T 1234-2020", "ch:dbba"),
                          ("HJ 1234-2020", "ch:mee")]:
            got = qr.channels_for(["发布"], no, table=table, only_ok=False)
            chain = [qr._to_channel_id(x) for x in select_chain(no)]
            assert got["发布"][0] == first, no
            assert got["发布"] == [c for c in chain if c in got["发布"]], no

    def test_不在链上的渠道不进候选(self, table):
        """`ch:cssn` 声明能答"废止"，但它不在任何链上 ⇒ 候选里没有它，声明里还有它。

        ⚠ 这两句都要断言：只断言"没进候选"会把"声明丢了"也放过。
        """
        rep = qr.route_report(["废止"], "GB 18218-2018", table=table, only_ok=False)
        assert "ch:cssn" in rep["废止"]["declared"]
        assert "ch:cssn" not in rep["废止"]["channels"]
        assert "ch:cssn" not in rep["废止"]["on_chain"]

    def test_only_ok_滤掉判死_但不动声明(self, table):
        """设计稿验收 2：台账判死 ⇒ 从候选消失；能力表声明**不受影响**（两根轴）。"""
        no = "GB 18218-2018"
        alive = qr.channels_for(["废止"], no, table=table, only_ok=False)["废止"]
        assert "ch:ndls" in alive
        rows = _rows({cid: ("down" if cid == "ch:ndls" else "ok") for cid in alive})
        got = qr.channels_for(["废止"], no, table=table, rows=rows, only_ok=True)["废止"]
        assert "ch:ndls" not in got and set(got) <= set(alive)
        assert "废止" in ca.answers_of("ch:ndls", table), "声明被改掉了"

    def test_unknown_与无探针不滤(self, table):
        """没有证据说它死了 ⇒ 不能滤（滤掉等于凭空缩链）。"""
        no = "GB 18218-2018"
        base = qr.channels_for(["现行性"], no, table=table, only_ok=False)["现行性"]
        rows = _rows({cid: "unknown" for cid in base})
        assert qr.channels_for(["现行性"], no, table=table, rows=rows)["现行性"] == base

    def test_tool_永不出现(self, table):
        """规则 5：`tool:` 的 `answers` 本来就是空的（规则 1 排除它）；这里把它钉住。"""
        for no in ["GB 18218-2018", "T/CECS 1000-2021", "DB44/T 1234-2020"]:
            for cls, ids in qr.channels_for(standard_no=no, table=table, only_ok=False).items():
                assert not [cid for cid in ids if cid.startswith("tool:")], (no, cls)

    def test_链注入两种写法都认(self, table):
        """`ndls` 与 `ch:ndls` 是同一根棒（换链源那天不会因一个前缀判成"不在链上"）。"""
        bare = qr.channels_for(["发布"], table=table, chain=("ndls", "govcn"), only_ok=False)
        pref = qr.channels_for(["发布"], table=table, chain=("ch:ndls", "ch:govcn"), only_ok=False)
        assert bare == pref == {"发布": ["ch:ndls", "ch:govcn"]}

    def test_链保序去重(self, table):
        got = qr.channels_for(["发布"], table=table,
                              chain=("ndls", "ch:ndls", "govcn", "ndls"), only_ok=False)
        assert got["发布"] == ["ch:ndls", "ch:govcn"]


class Test空候选三种原因:
    """设计稿验收 3：某类没渠道能答 ⇒ 空列表 + **原因分开**（调用方据此写 unanswerable）。"""

    def test_no_capability(self):
        rep = qr.route_report(["废止"], table={"ch:ndls": {"answers": []}},
                              chain=("ch:ndls",), only_ok=False)
        assert rep["废止"]["channels"] == [] and rep["废止"]["reason"] == "no_capability"
        assert rep["废止"]["declared"] == []

    def test_off_chain(self):
        rep = qr.route_report(["废止"], table={"ch:cssn": {"answers": ["废止"]}},
                              chain=("ch:ndls",), only_ok=False)
        assert rep["废止"]["channels"] == [] and rep["废止"]["reason"] == "off_chain"
        assert rep["废止"]["declared"] == ["ch:cssn"]

    def test_all_down(self):
        rep = qr.route_report(["废止"], table={"ch:ndls": {"answers": ["废止"]}},
                              chain=("ch:ndls",),
                              rows=_rows({"ch:ndls": "down"}), only_ok=True)
        assert rep["废止"]["channels"] == [] and rep["废止"]["reason"] == "all_down"
        assert rep["废止"]["dropped_down"] == ["ch:ndls"]

    def test_有候选就是ok且不算unanswerable(self, table):
        rep = qr.route_report(["废止"], "GB 18218-2018", table=table, only_ok=False)
        assert rep["废止"]["reason"] == "ok" and rep["废止"]["unanswerable"] is False
        assert qr.unanswerable_classes(rep) == []

    def test_unanswerable_classes只点名空的那些(self):
        rep = {"发布": {"unanswerable": False}, "废止": {"unanswerable": True}}
        assert qr.unanswerable_classes(rep) == ["废止"]


class Test入参:
    def test_非法类别抛(self, table):
        with pytest.raises(ValueError, match="不是五类之一"):
            qr.channels_for(["发布日期"], table=table, only_ok=False)

    def test_传单个字符串要说清楚(self, table):
        """`"废止"` 会被逐字拆成 `'废'`/`'止'`，报"不是五类之一"很费解 ⇒ 单独拦。

        ⚠ 这条用例是**我自己踩坑之后补的**：我先把标准号写成了第一个位置参数，
        原来的报错只说"不是五类之一：'H'"，看不出是位置错了。现在提示里带了"标准号放第二个"。
        """
        with pytest.raises(TypeError, match="不是字符串"):
            qr.channels_for("废止", table=table, only_ok=False)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="第二个位置参数"):
            qr.channels_for("HJ 1234-2020", table=table, only_ok=False)  # type: ignore[arg-type]

    def test_重复类别去重(self, table):
        got = qr.channels_for(["废止", "废止", "发布"], "GB 18218-2018",
                              table=table, only_ok=False)
        assert list(got) == ["废止", "发布"]

    def test_空类别列表返回空dict(self, table):
        assert qr.channels_for([], table=table, only_ok=False) == {}


class Test真机对照:
    """设计稿验收 1/4/5：真实号 + 独立复算（不调本模块的内部函数）。"""

    NUMBERS = ("GB 18218-2018", "AQ 3028-2008", "T/CECS 1000-2021")

    def test_废止候选非空且无tool(self, table):
        for no in self.NUMBERS:
            ids = qr.channels_for(["废止"], no, table=table, only_ok=False)["废止"]
            assert ids, no
            assert not [cid for cid in ids if cid.startswith("tool:")], no

    def test_与独立复算逐条一致(self, table):
        """独立复算：直接读 JSON + `select_chain` + `first_route`，**不用**本模块的内部函数。

        ⚠ 规则自 §11.0 R6c-4c 起是"**专门渠道先，其余按能力判定排**（`partial` 靠后）"，
        所以复算里也要体现这三步：① 能力∩链；② 前缀专门渠道置顶；③ 其余按 verdict 稳定排序。
        写在这里是**独立实现**（不是调 `_order_by_ability`），否则这条用例就成了回声。
        """
        raw = json.loads((ROOT / "src" / "core" / "update" / "channel_answers.json")
                         .read_text(encoding="utf-8"))["channels"]
        for no in self.NUMBERS:
            chain = [f"ch:{n}" for n in select_chain(no)]
            head = f"ch:{first_route(no)}" if first_route(no) else None
            got = qr.channels_for(standard_no=no, table=table, only_ok=False)
            for cls in ca.CLASSES:
                cands = [cid for cid in chain if cls in (raw.get(cid, {}).get("answers") or [])]
                front = [head] if head and head in cands else []
                tail = [c for c in cands if c not in front]
                want = front + sorted(
                    tail, key=lambda c: 1 if (raw.get(c, {}).get("answers_detail", {})
                                              .get(cls, {}).get("verdict") == "partial") else 0)
                assert got[cls] == want, (no, cls)
                # 能力表（answers-matrix 的输出）是**上限**：路由结果必须是它的子集
                assert set(got[cls]) <= set(ca.channels_for(cls, table=table)), (no, cls)

    def test_废止类会先问真拿得到废止日期的那根(self):
        """§11.0 R6c-4c 的**全部收益**就在这一条上：`废止` 类把 `ndls` 排到 `official_gb` 之前。

        b35 逐条核代码的结论：`official_gb` 的"废止"只有**状态串**（无废止日期，判 `partial`），
        而 `ndls` 的废止日期是**一等字段**（判 `supported`）。对 `GB/T` 这种没有前缀专门渠道的号，
        链序本来是 `official_gb` 在前 ⇒ 按类问会问到那根答不全的棒。
        """
        for no in ("GB/T 38496-2020", "GBZ 37-2024", "GB/T 1.1-2020"):
            got = qr.channels_for(["废止"], no, only_ok=False)["废止"]
            assert got[0] == "ch:ndls", (no, got)
            assert got.index("ch:ndls") < got.index("ch:official_gb"), (no, got)

    def test_前缀专门渠道不被能力排序降级(self):
        """⚠ 我第一版按判定**全局**排序，结果 HJ 号的"发布"先去问 `official_gb`——**把专门渠道降级**。

        `mee` 对 HJ 号是专门渠道；它对"发布"判 `partial`（列是实施时间），
        但"专门渠道先"是路由设计的原则 ⇒ 规则必须是"**专门渠道先，其余按能力排**"。
        """
        got = qr.channels_for(["发布"], "HJ 819-2017", only_ok=False)["发布"]
        assert got[0] == "ch:mee", got
        # 而尾巴里仍然按能力排（official_gb 的发布是 supported，排在 ndls 前——两者都 supported，保持链序）
        assert got[1:] == ["ch:official_gb", "ch:ndls", "ch:govcn"], got

    def test_注入链也要保专门渠道在先(self):
        """⚠ 复核 b37 的 A①：我第一版只在 `chain is None` 时算 `keep_first`，
        于是**注入链那条路**（R6c-4 的台账驱动链要走的就是它）会把专门渠道降级。

        用 `chain=("mee","official_gb","ndls","govcn")` 模拟台账给的链：HJ 号的「发布」
        必须仍以 `ch:mee` 打头。
        """
        got = qr.channels_for(["发布"], "HJ 819-2017", table=ca.load_answers(),
                              chain=("mee", "official_gb", "ndls", "govcn"),
                              only_ok=False)["发布"]
        assert got[0] == "ch:mee", got

    def test_注入同一条链结果必须逐位相同(self):
        """**注入链不变式**（复核 b38 的开放项⑤）：把自然链原样注入，结果必须一字不差。

        这条是 R6c-4"台账驱动链"要走的接口，而"注入路径把专门渠道在先关掉"那个 bug（b37 的 A①）
        正是它能抓到的。哨兵脚本 `scripts/five-class-order-diff.py` 里也跑同一条不变式。
        """
        table = ca.load_answers()
        for no in ("GB/T 38496-2020", "HJ 819-2017", "T/CECS 1000-2021", "XYZ 1-2020",
                   "GB 18218-2018"):
            natural = qr.channels_for(standard_no=no, table=table, only_ok=False)
            injected = qr.channels_for(standard_no=no, table=table,
                                       chain=select_chain(no), only_ok=False)
            assert natural == injected, no

    def test_未审计的棒不越过partial(self):
        """⚠ 复核 b37 的 A②：我第一版把"没审计（None）"与 `supported` 同键，
        于是 `None` 会**越过** `partial` 前移，而 docstring 写的是"`None` 不参与排序"。

        现在三档：`supported=0 / None=1 / partial=2`（组内仍按链序）。
        """
        table = ca.load_answers()
        # 造一条注入链：supported（ndls）、**无审计**（任取一条 R1 种子渠道，它声明废止但没 answers_detail）、
        # partial（official_gb）。未审计那根应当**留在中间**（既不越过 supported，也不被 partial 反超）。
        unaudited = next(cid for cid, v in table.items()
                         if "废止" in (v.get("answers") or []) and "answers_detail" not in v)
        got = qr.channels_for(["废止"], "XYZ 1-2020", table=table,
                              chain=("official_gb", unaudited, "ndls"),
                              only_ok=False)["废止"]
        assert got == ["ch:ndls", unaudited, "ch:official_gb"], got

    def test_已知缺口已被兜底链补掉_HJ不再一判死就丢两类(self, table):
        """**记录型用例：它按设计红过一次，这里是红过之后**有意**改成的样子。**

        2026-09-18 R6c-3 时它断言的是：`mee`（HJ）只声明能答"发布"，
        HJ 的链 = mee→official_gb→govcn ⇒ `official_gb` 一判死，"修订/编号核验"就**没有候选**
        （原因 `all_down`），也就是**单点故障**。
        同一天 R6c-3b 把 `ndls` 插进兜底链（量出来的：`govcn` 在标准号上 1/10、`ndls` 6/10）
        ⇒ 这条用例**如约变红**，我把它改成断言"缺口已被补掉"。
        ⚠ 若哪天链又变短，这条会再红——那正是它存在的意义。
        """
        rows = _rows({"ch:official_gb": "down", "ch:govcn": "ok", "ch:mee": "ok"})
        rep = qr.route_report(standard_no="HJ 1234-2020", table=table, rows=rows, only_ok=True)
        assert rep["修订"]["reason"] == "ok"
        assert "ch:ndls" in rep["修订"]["channels"], "兜底链里必须还有状态权威"
        assert rep["编号核验"]["reason"] == "ok"
        assert rep["修订"]["dropped_down"] == ["ch:official_gb"]
        assert qr.unanswerable_classes(rep) == []


class Test人用脚本:
    """`scripts/question-route.py` 是给人看的入口——它坏了不会有人发现，所以用一条用例钉住。

    ⚠ 为什么**开子进程**跑而不是 import 它：脚本会往 `sys.path` 插仓库根、重设 `sys.stdout` 编码，
    在同一个进程里 import 会影响别的用例（"修一个坏一个"那种）。子进程还能顺带证明
    "命令行参数这条路是通的"（我第一版就是参数/表名写错，只有真跑才知道）。
    """

    def test_json_模式能跑通且是合法json(self, db):
        cr.seed_channels()
        r = subprocess.run(  # noqa: S603 —— 参数是固定列表，无 shell
            [sys.executable, str(ROOT / "scripts" / "question-route.py"),
             "--json", "GB 18218-2018"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT), timeout=60)
        assert r.returncode == 0, r.stderr[-800:]
        data = json.loads(r.stdout)
        assert set(data) == {"GB 18218-2018"}
        assert data["GB 18218-2018"]["废止"]["reason"] == "ok"
        assert data["GB 18218-2018"]["废止"]["channels"]
