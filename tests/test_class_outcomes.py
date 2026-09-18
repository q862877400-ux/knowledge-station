# -*- coding: utf-8 -*-
"""五类结论组装测试（`src/core/update/channels/class_outcomes.py`，§11.0 R6c-4）。

守四件（对应"为什么不写五条事件、而是记进 latest_info"的三条量测）：
  1. **"是哪根棒答的"才算答了**——候选里有别的棒**不算**已经查过（这是"让业主以为查过了"的源头）；
  2. **`not_probed` 与"答不出来"必须分开**：前者是"没问"，后者才配进 `unanswerable`；
  3. **给不出这一类要的字段 ⇒ `not_answered`**（`channel_gave_no_field`），
     不许拿别的字段顶上（`发布` 不许拿实施日期顶——那是 R6c-3c/3e 修掉的错标）；
  4. `completeness` 如实带出 b35 逐条核出的 supported/partial，且**不参与排序**。
"""
from __future__ import annotations

import pytest

from src.core.update import channel_answers as ca
from src.core.update.channels import class_outcomes as co
from src.core.update.channels.base import ChannelResult


def _rep(**per_class) -> dict:
    """造一份 `route_report` 形状：{类: {channels, reason, ...}}。

    ⚠ **没点名的类默认给一个候选**（而不是默认"没有候选/no_capability"）——
    我第一版默认成后者，于是"没点名"的类全被算进 `unanswerable`，
    把几条精确集合断言搞成假红（**测试脚手架的默认值也是被测语义的一部分**）。
    """
    out = {}
    for cls in ca.CLASSES:
        got = per_class.get(cls, ("ch:official_gb",))
        if isinstance(got, str):        # 只给 reason（空候选）
            out[cls] = {"channels": [], "reason": got, "declared": [],
                        "on_chain": [], "dropped_down": [], "unanswerable": True}
        else:
            out[cls] = {"channels": list(got), "reason": "ok", "declared": list(got),
                        "on_chain": list(got), "dropped_down": [], "unanswerable": False}
    return out


class Test结论抽取:
    def test_发布要发布日期_没有就不算答(self):
        """⚠ 不许拿实施日期顶发布——那正是 R6c-3c/3e 修掉的错标。"""
        no_pub = ChannelResult(channel="official_gb", found=True,
                               effective_date="2019-03-01")
        assert co.conclusion_for("发布", no_pub) is None
        both = ChannelResult(channel="official_gb", found=True,
                             effective_date="2019-03-01", published_date="2018-11-19")
        assert co.conclusion_for("发布", both) == {"date": "2018-11-19"}

    def test_修订三态都算答了(self):
        """**否定的结论也是结论**：`no_change` = "没有被代替"，是 `修订` 类的答案。"""
        none_ = ChannelResult(channel="ndls", found=True, change_type="no_change")
        assert co.conclusion_for("修订", none_) == {"change": "no_change",
                                                    "new_version": None}
        new = ChannelResult(channel="ndls", found=True, change_type="new_version",
                            latest_version="GB/T 1-2024")
        assert co.conclusion_for("修订", new) == {"change": "new_version",
                                                  "new_version": "GB/T 1-2024"}
        # 渠道根本没给 change_type（例如 mee）⇒ 这一类它答不了
        assert co.conclusion_for("修订", ChannelResult(channel="mee", found=True)) is None

    def test_废止_现行也是结论_非废止时无废止日期(self):
        """⚠ 这一条是**拿真机演示改出来的**：我第一版只在 `withdrawn` 时才算答了，
        于是"现行"的标准在 `废止` 类上被判 `not_answered` —— 可"现行"正是"没有废止"的依据。
        按第一版口径，几乎每个号都会有两个"没答出来"，"有未答不算 done"就会把绝大多数号判成没做完。
        """
        eff = ChannelResult(channel="ndls", found=True, legal_status="effective")
        assert co.conclusion_for("废止", eff) == {"state": "effective",
                                                  "withdrawn_date": None}
        wd = ChannelResult(channel="ndls", found=True, legal_status="withdrawn",
                           effective_date="2026-07-01")
        assert co.conclusion_for("废止", wd) == {"state": "withdrawn",
                                                 "withdrawn_date": "2026-07-01"}
        # 完全没给状态（mee 就是）⇒ 这一类它答不了
        assert co.conclusion_for("废止", ChannelResult(channel="mee", found=True)) is None

    def test_现行性与编号核验(self):
        r = ChannelResult(channel="official_gb", found=True, legal_status="effective",
                          latest_version="GB 18218-2018")
        assert co.conclusion_for("现行性", r) == {"state": "effective"}
        assert co.conclusion_for("编号核验", r) == {"exists": True,
                                                    "authority_version": "GB 18218-2018"}

    def test_非法类名要抛(self):
        with pytest.raises(ValueError, match="不是五类之一"):
            co.conclusion_for("发布日期", ChannelResult(channel="x", found=True))


class Test组装:
    def test_答的棒在候选里才算answered(self):
        rep = _rep(废止=["ch:ndls", "ch:official_gb"])
        out = co.build_classes(rep, channel_id="ch:ndls",
                               result=ChannelResult(channel="ndls", found=True,
                                                    legal_status="withdrawn",
                                                    effective_date="2026-07-01"))
        assert out["classes"]["废止"]["status"] == "answered"
        assert out["classes"]["废止"]["channel"] == "ch:ndls"
        assert out["unanswered"] and "废止" not in out["unanswered"]

    def test_候选在但没轮到它_记not_probed而不是答不出来(self):
        """第一棒命中了 ⇒ 这一类的候选**根本没被问过**。

        ⚠ 与"问了但没给字段"是两件事，**必须分开**（我第一版把两者混在一条用例里，
        被断言当场纠正）：
        - **答的棒不在该类的候选里** ⇒ `not_probed`（没问）；
        - **答的棒在该类候选里、但这根棒没给该类要的字段** ⇒ `channel_gave_no_field`（问了没给）。
        两者都是 `not_answered`，但**都不能说成"查过了"**。
        """
        # 修订的候选只有 ndls；而这次是 official_gb 命中的 ⇒ ndls 没被问过
        rep = _rep(修订=["ch:ndls"])
        out = co.build_classes(rep, channel_id="ch:official_gb",
                               result=ChannelResult(channel="official_gb", found=True,
                                                    change_type="no_change"))
        entry = out["classes"]["修订"]
        assert entry["status"] == "not_answered" and entry["reason"] == "not_probed"
        assert entry["candidates"] == ["ch:ndls"]
        # ⚠ not_probed **不**进 unanswerable（它不是结构性缺口），但必须在 unanswered 里
        assert "修订" in out["unanswered"] and "修订" not in out["unanswerable"]

    def test_答的棒在候选里但没给字段_记channel_gave_no_field(self):
        """对照上一条：候选里**有**答的这根棒，所以是"问了、没给"，不是"没问"。

        用 `mee` 的"发布"举例最准：它命中了、也在候选里，但它的列是**实施时间**，
        拿不出发布日期 ⇒ `channel_gave_no_field`（**没有** `candidates` 字段，
        因为"候选是谁"这件事对"没给字段"不重要）。
        """
        rep = _rep(发布=["ch:mee"])
        out = co.build_classes(rep, channel_id="ch:mee",
                               result=ChannelResult(channel="mee", found=True,
                                                    effective_date="2017-06-01"))
        assert out["classes"]["发布"]["reason"] == "channel_gave_no_field"
        assert "candidates" not in out["classes"]["发布"]

    def test_问了但没给这一类要的字段(self):
        """`mee` 对"发布"答不了：它的列是**实施时间**，而这一条**不许拿实施日期顶发布**。"""
        rep = _rep(发布=["ch:mee", "ch:official_gb"])
        out = co.build_classes(rep, channel_id="ch:mee",
                               result=ChannelResult(channel="mee", found=True,
                                                    effective_date="2017-06-01"))
        entry = out["classes"]["发布"]
        assert entry["status"] == "not_answered"
        assert entry["reason"] == "channel_gave_no_field"
        assert entry["completeness"] == "partial"      # b35 对 mee 的发布判定

    def test_渠道给了否定结论也算answered(self):
        """对照上一条：`official_gb` 说"现行" ⇒ `废止` 类**答了**（否定的答案），带 partial。"""
        rep = _rep(废止=["ch:official_gb", "ch:ndls"])
        out = co.build_classes(rep, channel_id="ch:official_gb",
                               result=ChannelResult(channel="official_gb", found=True,
                                                    legal_status="effective",
                                                    change_type="no_change"))
        entry = out["classes"]["废止"]
        assert entry["status"] == "answered"
        assert entry["conclusion"] == {"state": "effective", "withdrawn_date": None}
        assert entry["completeness"] == "partial"      # b35 判 official_gb 的废止=partial

    def test_空候选的原因原样带出(self):
        rep = _rep(编号核验="off_chain")
        out = co.build_classes(rep, channel_id="ch:ndls",
                               result=ChannelResult(channel="ndls", found=True))
        assert out["classes"]["编号核验"]["reason"] == "off_chain"
        assert out["unanswerable"] == ["编号核验"]

    def test_三类结构性原因都算unanswerable(self):
        rep = _rep(发布="no_capability", 修订="off_chain", 废止="all_down")
        out = co.build_classes(rep, channel_id="ch:ndls",
                               result=ChannelResult(channel="ndls", found=True))
        assert set(out["unanswerable"]) == {"发布", "修订", "废止"}

    def test_真表跑一遍_结论与判定都对得上(self):
        """用**真能力表**跑一次（不注入 table）：`completeness` 应当来自 b35 的审计。"""
        table = ca.load_answers()
        assert (table["ch:official_gb"].get("answers_detail") or {}).get("废止", {}).get(
            "verdict") == "partial"
        assert (table["ch:ndls"].get("answers_detail") or {}).get("废止", {}).get(
            "verdict") == "supported"
        rep = _rep(废止=["ch:official_gb", "ch:ndls"])
        out = co.build_classes(rep, channel_id="ch:ndls",
                               result=ChannelResult(channel="ndls", found=True,
                                                    legal_status="withdrawn",
                                                    effective_date="2026-07-01"),
                               table=table)
        assert out["classes"]["废止"]["completeness"] == "supported"

    def test_词表封闭(self):
        assert co.STATUSES == ("answered", "not_answered")
        assert "not_probed" in co.REASONS and "ok" in co.REASONS
        assert co.UNANSWERABLE_REASONS == {"no_capability", "off_chain", "all_down"}
