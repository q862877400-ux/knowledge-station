"""合规护栏（jev_guard）回归用例：**2026-09-24 真机实测的 20 条中文样本**。

这些样本不是编的，是本机跑 Jev 时一条条试出来的：
- 10 条**该触发**（含 8 条**词表抓不到**的隐性合规：自动点"已阅读并同意"、工伤私了、
  过期认证先用着、身份证号发公开站、无人值守产线、车间摄像头…）；
- 10 条**不该触发**的纯技术话（这 9~10 条正是词表瘦身前 **9/9 误触发**的那批）。

判据用**假 transport**（`system_one` 被 monkeypatch）⇒ 零联网、零花费、可离线跑。
⚠ **本文件不调真 Jev**：真机复核走 `scripts/verify-jev-guard-live.py`（人工跑、要 Key）。
"""
from __future__ import annotations

import pytest

from src.core.llm import jev_guard
from src.core.llm import jev_client

#: (输入, 期望判定) —— 期望值来自 2026-09-24 本机真机结果，不是设计意图
SHOULD_TRIGGER = [
    "动火作业怎么分级？",
    "这个项目需要办理什么许可？",
    "储罐区设置有哪些法规要求？",
    "GB 30871 对特殊作业有什么要求？",
    "我想让程序自动帮用户点『已阅读并同意』的服务协议",
    "员工在车间摔伤了想私下赔钱私了不走工伤流程",
    "供应商说他那个零件有认证但证书过期了，先用着等换证",
    "我打算把客户名单连上身份证号一起发到公开文档站",
    "这条产线想改成全自动，晚上没人值守",
    "我们想用摄像头在生产车间做疲劳识别，员工会反感吗",
]
SHOULD_NOT_TRIGGER = [
    "帮我写个快速排序的 Python 实现",
    "这个函数的圈复杂度怎么降？",
    "前端路由必须懒加载，否则首屏白屏",
    "重构这段代码不得引入新的依赖，怎么做",
    "数据库事务隔离级别设错了会怎样，必须怎么配",
    "用 git 不得在主干上直接提交，这条规范对吗",
    "这个 API 的标准错误码应该怎么设计",
    "文档里禁止使用 emoji，这是什么规范",
    "单元测试覆盖率必须达到 80% 吗",
    "这个 API 报 502，是不是该加个重试中间件",
]


@pytest.fixture(autouse=True)
def _clean_breaker():
    """熔断状态是**模块级全局**（生产就该如此）⇒ 每个用例前后各清一次，
    否则用例顺序会互相污染（本次实测：前一个用例留下的 streak 让下一个的熔断断言假红）。"""
    jev_client.reset_breaker_for_tests()
    yield
    jev_client.reset_breaker_for_tests()


#: 实测里落在**中间档**（review）的三条：既不该"静默"，也不该"触发"。
#: ⚠ 这是**实测事实**不是设计意图——Jev 对这三条（都含泛义务/泛规定词）给了
#:   needs_standard 0.45/0.63/0.60：高于 review 0.35、低于 action 0.70。
#:   上一版我误把它们算成"误触发"，改判据前先分清是**判据错**还是**读数错**（七条清单第 1 条）。
EXPECT_REVIEW = [
    "用 git 不得在主干上直接提交，这条规范对吗",
    "文档里禁止使用 emoji，这是什么规范",
    "单元测试覆盖率必须达到 80% 吗",
]


def _fake_scores(text: str) -> dict:
    """按**实测过的分数**回放，让判据在没有网络时也能验"阈值切在哪"。

    ⚠ 这是回放不是模型：它钉的是**我们的阈值与归并逻辑**，不是 Jev 的准确率
    （后者靠 `verify-jev-guard-live.py` 在真机上量）。
    """
    measured = {
        "帮我写个快速排序的 Python 实现": (0.01, 0.01, 0.00, 0.0),
        "这个函数的圈复杂度怎么降？": (0.03, 0.02, 0.00, 0.0),
        "前端路由必须懒加载，否则首屏白屏": (0.02, 0.04, 0.01, 0.0),
        "重构这段代码不得引入新的依赖，怎么做": (0.03, 0.03, 0.01, 0.0),
        "数据库事务隔离级别设错了会怎样，必须怎么配": (0.05, 0.08, 0.01, 0.0),
        "用 git 不得在主干上直接提交，这条规范对吗": (0.45, 0.04, 0.01, 0.0),
        "这个 API 的标准错误码应该怎么设计": (0.10, 0.04, 0.01, 0.0),
        "文档里禁止使用 emoji，这是什么规范": (0.63, 0.04, 0.01, 0.0),
        "单元测试覆盖率必须达到 80% 吗": (0.60, 0.04, 0.01, 0.0),
        "这个 API 报 502，是不是该加个重试中间件": (0.03, 0.04, 0.01, 0.0),
        "动火作业怎么分级？": (0.96, 0.27, 0.08, 0.7),
        "这个项目需要办理什么许可？": (0.97, 0.32, 0.06, 0.3),
        "储罐区设置有哪些法规要求？": (0.97, 0.50, 0.09, 0.3),
        "GB 30871 对特殊作业有什么要求？": (0.98, 0.28, 0.09, 0.3),
        "我想让程序自动帮用户点『已阅读并同意』的服务协议": (0.89, 0.91, 0.04, 2.2),
        "员工在车间摔伤了想私下赔钱私了不走工伤流程": (0.98, 0.91, 0.97, 2.6),
        "供应商说他那个零件有认证但证书过期了，先用着等换证": (0.94, 0.80, 0.22, 2.5),
        "我打算把客户名单连上身份证号一起发到公开文档站": (0.96, 0.98, 0.25, 2.4),
        "这条产线想改成全自动，晚上没人值守": (0.80, 0.71, 0.07, 1.4),
        "我们想用摄像头在生产车间做疲劳识别，员工会反感吗": (0.92, 0.84, 0.09, 1.6),
    }
    a, b, c, sev = measured[text]
    return {"answers": {
        "needs_standard": {"type": "noul", "noul": a},
        "implicit_risk": {"type": "noul", "noul": b},
        "liability": {"type": "noul", "noul": c},
        "severity": {"type": "score", "score": sev},
    }, "model": "jev-1.13.0"}


@pytest.fixture()
def fake_jev(monkeypatch):
    def _fake(state, questions, **kw):
        text = (state or {}).get("message", "")
        return _fake_scores(text)
    monkeypatch.setattr(jev_client, "system_one", _fake)
    monkeypatch.setattr(jev_guard.get_settings(), "jev_api_key", "test-key", raising=False)
    return _fake


def test_guard_triggers_on_all_ten_measured_hits(fake_jev):
    """该触发的 10 条**一条不漏**（含 8 条隐性合规——词表对它们 1/8）。"""
    missed = []
    for text in SHOULD_TRIGGER:
        out = jev_guard.judge(text)
        if out is None or out["verdict"] != jev_guard.VERDICT_TRIGGER:
            missed.append((text, out))
    assert not missed, f"漏触发 {len(missed)} 条：{missed}"


def test_guard_silent_on_all_ten_technical_messages(fake_jev):
    """**不该触发的 10 条技术话一条都不许"触发"**（词表瘦身前 9/9 误触发）。

    ⚠ 判据是"不许触发"而不是"必须静默"：实测里其中 **3 条落在 review 档**（中间档，
    见 `EXPECT_REVIEW`）——那是设计内的第三档，不是误触发。7 条真静默的另有一条断言钉住。
    """
    fired = []
    for text in SHOULD_NOT_TRIGGER:
        out = jev_guard.judge(text)
        if out is not None and out["verdict"] == jev_guard.VERDICT_TRIGGER:
            fired.append((text, out))
    assert not fired, f"误触发 {len(fired)} 条：{fired}"


def test_guard_three_technical_ones_land_in_review(fake_jev):
    """实测的三条**中间档**：不静默、不触发——这正是"review 阈值"存在的理由。"""
    for text in EXPECT_REVIEW:
        out = jev_guard.judge(text)
        assert out["verdict"] == jev_guard.VERDICT_REVIEW, (text, out)
    # 剩下 7 条必须真静默
    for text in SHOULD_NOT_TRIGGER:
        if text in EXPECT_REVIEW:
            continue
        assert jev_guard.judge(text)["verdict"] == jev_guard.VERDICT_SILENT, text


def test_guard_review_band_does_not_trigger(fake_jev, monkeypatch):
    """中间档：分数落在 review 与 action 之间 ⇒ review，**不**触发。"""
    from src.core.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "jev_guard_review_threshold", 0.35, raising=False)
    monkeypatch.setattr(s, "jev_guard_action_threshold", 0.90, raising=False)
    # "用 git 不得…" 实测 needs_standard=0.45 ⇒ 旧阈值(0.70)下不触发、0.90 下更不该触发
    out = jev_guard.judge("用 git 不得在主干上直接提交，这条规范对吗")
    assert out["verdict"] == jev_guard.VERDICT_REVIEW, out


def test_guard_severity_escalates_review_to_trigger(fake_jev, monkeypatch):
    """严重度越线 ⇒ 把 review 升级成触发（官方护栏蓝本的 severity 通道）。"""
    from src.core.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "jev_guard_action_threshold", 0.99, raising=False)
    # 这条 needs_standard=0.89 <0.99（本来只 review），但 severity=2.2 ≥ 2.0 ⇒ 必须升级
    out = jev_guard.judge("我想让程序自动帮用户点『已阅读并同意』的服务协议")
    assert out["signals"]["severity"] >= s.jev_guard_severity_block
    assert out["verdict"] == jev_guard.VERDICT_TRIGGER, out


def test_guard_degrades_to_none_when_jev_unavailable(monkeypatch):
    """**Jev 挂 ⇒ 返回 None（调用方退回词表）**，绝不让合规护航整体失效。"""
    def _boom(*_a, **_k):
        raise jev_client.JevUnavailable("测试：不可用")
    monkeypatch.setattr(jev_client, "system_one", _boom)
    monkeypatch.setattr(jev_guard.get_settings(), "jev_api_key", "test-key", raising=False)
    assert jev_guard.judge("动火作业怎么分级？") is None


def test_guard_degrades_when_key_missing(monkeypatch):
    """没配 Key ⇒ 直接 None（不联网、不报错）。"""
    monkeypatch.setattr(jev_guard.get_settings(), "jev_api_key", "", raising=False)
    assert jev_guard.judge("动火作业怎么分级？") is None


def test_guard_rejects_malformed_answer(monkeypatch):
    """响应不合契约（缺 noul / 类型不对）⇒ 当不可用，**不猜**。"""
    monkeypatch.setattr(jev_guard.get_settings(), "jev_api_key", "test-key", raising=False)
    monkeypatch.setattr(jev_client, "system_one",
                        lambda *a, **k: {"answers": {"needs_standard": {"noul": "高"}}, "model": "x"})
    assert jev_guard.judge("动火作业怎么分级？") is None


def test_guard_questions_all_have_criteria(fake_jev):
    """**每道 Noul 都必须带 criteria**（官方硬要求；本项目不写 criteria 时判错过 3 条）。"""
    for key in ("needs_standard", "implicit_risk", "liability"):
        q = jev_guard._QUESTIONS[key]
        assert q["type"] == "noul", key
        assert set(q.get("criteria") or {}) == {"true", "false"}, f"{key} 缺 criteria"
        assert (q["criteria"]["true"] or "").strip() and (q["criteria"]["false"] or "").strip(), key
    sev = jev_guard._QUESTIONS["severity"]
    assert sev["type"] == "score" and len(sev["criteria"]) >= 3


def test_client_pins_model_version(monkeypatch):
    """**模型名钉死版本**，不用会漂移的别名（官方：调过阈值就别用别名）。"""
    assert jev_client.JEV_MODEL == "jev-1.13.0"
    seen = {}

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"answers": {"a": {"noul": 0.5}}, "model": "jev-1.13.0"}
    def _post(url, headers=None, json=None, timeout=None):
        seen.update({"url": url, "payload": json, "timeout": timeout})
        return _Resp()

    monkeypatch.setattr(jev_client, "_read_key", lambda: "k")
    monkeypatch.setattr(jev_client.requests, "post", _post)
    monkeypatch.setattr(jev_client, "record_egress", lambda **k: "dump_x")
    jev_client.reset_breaker_for_tests()
    body = jev_client.system_one({"m": "x"}, {"a": jev_client.noul("?", yes="y", no="n")})
    assert body["answers"]["a"]["noul"] == 0.5
    assert seen["payload"]["model"] == "jev-1.13.0"
    assert seen["url"] == jev_client.JEV_ENDPOINT
    # ⚠ **钉死 2s 这个字面值**（独立复核 MED-4：原先断言 `== JEV_TIMEOUT_S`，
    #   把它从 2 改成 20 用例照样绿 ⇒ 根本没守住"每条消息最多等多久"）。
    assert jev_client.JEV_TIMEOUT_S == 2.0, (
        f"每条用户消息最多等 {jev_client.JEV_TIMEOUT_S}s；调大前先重跑 20 条中文样本")
    assert seen["timeout"] == 2.0, seen["timeout"]
    jev_client.reset_breaker_for_tests()


def _resp(body, status=200):
    class _R:
        def __init__(self):
            self.status_code = status
            self.text = "err" if status != 200 else ""
        def json(self):
            if self.status_code != 200:
                raise ValueError("非 200 响应不该被 json()")
            return body
    return _R()


def _patch_post(monkeypatch, body, status=200):
    monkeypatch.setattr(jev_client, "_read_key", lambda: "k")
    monkeypatch.setattr(jev_client, "record_egress", lambda **k: "dump_x")
    monkeypatch.setattr(jev_client.requests, "post", lambda *_a, **_k: _resp(body, status))
    jev_client.reset_breaker_for_tests()


def test_client_rejects_bad_values(monkeypatch):
    """**坏值不许当判定**（独立复核 MED-2：`True` / `1.1` / 模型别名都曾被当合法）。

    - `bool` 是 Python `int` 的子类 ⇒ 朴素 `isinstance(v, (int,float))` 会放行 `True`；
    - 概率越界（1.1）必须拒；
    - 回包 `model` 漂成**别名**（`jev-latest`）必须拒：阈值是按 `jev-1.13.0` 量的。
    """
    q = {"a": jev_client.noul("?", yes="y", no="n")}
    for bad in ({"answers": {"a": {"noul": True}}, "model": jev_client.JEV_MODEL},
                {"answers": {"a": {"noul": 1.1}}, "model": jev_client.JEV_MODEL},
                {"answers": {"a": {"noul": -0.1}}, "model": jev_client.JEV_MODEL},
                {"answers": {"a": {"noul": 0.5}}, "model": "jev-latest"},
                {"answers": {"a": {"noul": 0.5}}},                    # 缺 model
                {"answers": {"b": {"noul": 0.5}}, "model": jev_client.JEV_MODEL},  # 键不对
                {"answers": {}, "model": jev_client.JEV_MODEL}):
        _patch_post(monkeypatch, bad)
        with pytest.raises(jev_client.JevUnavailable):
            jev_client.system_one("s", q)


def test_client_score_range_is_levels_not_unit_interval(monkeypatch):
    """⚠ **Score 不是 0~1**（2026-09-24 真机踩到：我的校验把三个字段一起按 0~1 判，
    而官方 Score 回的是**档位下标 0..档数−1** ⇒ 第一轮真机就把带 Score 的那次全判非法、
    隐性的 6 条全落熔断窗内——实测 miss 6/10）。

    现在：4 档量表回 `score=2.4` 必须**放行**；回 `score=9.0` 必须拒。
    """
    levels = ["无", "轻微", "严重", "特别严重"]
    q = {"s": jev_client.score("有多严重？", levels)}
    _patch_post(monkeypatch, {"answers": {"s": {"type": "score", "score": 2.4,
                                               "confidence": 0.9}}, "model": jev_client.JEV_MODEL})
    body = jev_client.system_one("x", q)          # 2.4 在 4 档量表的 [0,3] 内 ⇒ 合法
    assert body["answers"]["s"]["score"] == 2.4
    jev_client.reset_breaker_for_tests()
    # 越界（9.0 > 3）必须拒
    _patch_post(monkeypatch, {"answers": {"s": {"type": "score", "score": 9.0,
                                               "confidence": 0.9}}, "model": jev_client.JEV_MODEL})
    with pytest.raises(jev_client.JevUnavailable):
        jev_client.system_one("x", q)
    jev_client.reset_breaker_for_tests()
    # 负档位也拒
    _patch_post(monkeypatch, {"answers": {"s": {"type": "score", "score": -1.0,
                                               "confidence": 0.9}}, "model": jev_client.JEV_MODEL})
    with pytest.raises(jev_client.JevUnavailable):
        jev_client.system_one("x", q)
    jev_client.reset_breaker_for_tests()


def test_client_score_range_unknown_scale_does_not_reject(monkeypatch):
    """**量表档数拿不到时，不判 `score` 的值域**（独立复核 2026-09-24 MED 抓到的假严）。

    复核实测：`criteria_missing` + `score=2.4` ⇒ 我这一版**REJECT**（退回按 0~1 判），
    而源码注释写的是"没传就只查是数值"——**注释与行为不符**，且这正是把 Score 当概率的
    同一个错换条路径复发（Score 回的永远是档位下标，不是概率）。

    ⇒ 档数未知时只保留"必须是数值（排除 bool）"；`noul`/`confidence` 仍按 0~1 判。
    """
    # 提问里**没有** criteria 列表（拿不到档数）⇒ score 只查类型
    _patch_post(monkeypatch, {"answers": {"s": {"type": "score", "score": 2.4,
                                               "confidence": 0.9}},
                               "model": jev_client.JEV_MODEL})
    body = jev_client.system_one("x", {"s": {"type": "score", "instructions": "多严重？"}})
    assert body["answers"]["s"]["score"] == 2.4, "档数未知时不该按 0~1 拒（假严）"
    jev_client.reset_breaker_for_tests()
    # 仍然拒"不是数值"（bool 也拒）
    for bad in (True, "高", None):
        _patch_post(monkeypatch, {"answers": {"s": {"type": "score", "score": bad,
                                                   "confidence": 0.9}},
                                   "model": jev_client.JEV_MODEL})
        with pytest.raises(jev_client.JevUnavailable):
            jev_client.system_one("x", {"s": {"type": "score", "instructions": "多严重？"}})
        jev_client.reset_breaker_for_tests()
    # confidence 仍按 0~1 判（档数未知也不放松 confidence）
    _patch_post(monkeypatch, {"answers": {"s": {"type": "score", "score": 1.0,
                                               "confidence": 1.4}},
                               "model": jev_client.JEV_MODEL})
    with pytest.raises(jev_client.JevUnavailable):
        jev_client.system_one("x", {"s": {"type": "score", "instructions": "多严重？"}})
    jev_client.reset_breaker_for_tests()


def test_client_rejects_bad_confidence(monkeypatch):
    """Choice 的 `confidence` 必须在 0~1（`jev_ingest` 的 clear/review 门控靠它）。

    （`score` 的量表值域由上一条专门测：**它不是 0~1**。）
    """
    _patch_post(monkeypatch, {
        "answers": {"k": {"type": "choice", "choice": "admin", "confidence": 1.4}},
        "model": jev_client.JEV_MODEL})
    with pytest.raises(jev_client.JevUnavailable):
        jev_client.system_one("s", {"k": jev_client.choice("?", {"admin": "a", "other": "b"})})


def test_breaker_reopens_after_cooldown(monkeypatch):
    """**冷却一过、下一次失败会重新开熔断**（独立复核 MED-1 实测的洞：
    原实现只在 streak **恰好等于**阈值时刷新 `opened_at` ⇒ 冷却过后再失败多少次都开不了）。

    这里不用真等 60s：直接推进模块里的 `_opened_at` 模拟"冷却已过"。
    """
    class _Resp:
        status_code = 500
        text = "boom"
    monkeypatch.setattr(jev_client, "_read_key", lambda: "k")
    monkeypatch.setattr(jev_client, "record_egress", lambda **k: "dump_x")
    monkeypatch.setattr(jev_client.requests, "post", lambda *_a, **_k: _Resp())
    jev_client.reset_breaker_for_tests()
    q = {"a": jev_client.noul("?", yes="y", no="n")}
    for _ in range(jev_client.JEV_BREAKER_FAILS):
        with pytest.raises(jev_client.JevUnavailable):
            jev_client.system_one("s", q)
    assert jev_client.breaker_open() is True
    # 冷却期已过（把 opened_at 往前推）⇒ 不再短路
    jev_client._opened_at -= jev_client.JEV_BREAKER_COOLDOWN_S + 1
    assert jev_client.breaker_open() is False
    # 冷却后**再失败一次** ⇒ 必须**重新**开熔断（旧实现这里不会）
    with pytest.raises(jev_client.JevUnavailable):
        jev_client.system_one("s", q)
    assert jev_client.breaker_open() is True, "冷却后的失败没有重新开熔断（MED-1 未修）"
    jev_client.reset_breaker_for_tests()


def test_every_egress_is_audited(monkeypatch):
    """**每一次外发都审计**（独立复核 MED-6：原先只有成功路径登记 ⇒ HTTP 503 那次查不到）。

    而且审计**不是只读**（`record_egress` 会写 `debug_dump` 表并清旧行）——源码里
    原来的"只读"说法不准确，已改。
    """
    seen: list[dict] = []
    calls = {"n": 0}

    class _Resp:
        def __init__(self, status):
            self.status_code = status
            self.text = "" if status == 200 else "err"
        def json(self):
            if self.status_code != 200:
                raise ValueError("非 200 响应不该被 json()")
            return {"answers": {"a": {"noul": 0.5}}, "model": jev_client.JEV_MODEL}

    def _post(*_a, **_k):
        calls["n"] += 1
        return _Resp(200 if calls["n"] == 1 else 503)

    monkeypatch.setattr(jev_client, "_read_key", lambda: "k")
    monkeypatch.setattr(jev_client.requests, "post", _post)
    monkeypatch.setattr(jev_client, "record_egress", lambda **k: seen.append(k) or "dump_x")
    jev_client.reset_breaker_for_tests()
    q = {"a": jev_client.noul("?", yes="y", no="n")}
    jev_client.system_one("s", q)                       # 成功
    with pytest.raises(jev_client.JevUnavailable):     # HTTP 503
        jev_client.system_one("s", q)
    assert calls["n"] == 2, calls
    assert len(seen) == 2, f"成功与失败都要审计（实测 {len(seen)} 次）"
    assert seen[0]["response_meta"]["outcome"] == "ok", seen[0]
    assert seen[1]["response_meta"]["outcome"] == "http_503", seen[1]
    jev_client.reset_breaker_for_tests()


def test_audit_failure_does_not_break_decision(monkeypatch):
    """审计写失败**不反噬**判断结果（审计比判断重要，但不能让外部服务把护栏带崩）。"""
    def _boom(**_k):
        raise RuntimeError("db down")
    _patch_post(monkeypatch, {"answers": {"a": {"noul": 0.5}}, "model": jev_client.JEV_MODEL})
    monkeypatch.setattr(jev_client, "record_egress", _boom)
    body = jev_client.system_one("s", {"a": jev_client.noul("?", yes="y", no="n")})
    assert body["answers"]["a"]["noul"] == 0.5
    jev_client.reset_breaker_for_tests()


def test_compliance_guard_endpoint_contract(client, monkeypatch):
    """端点契约（独立复核 MED-5：禁掉 `if verdict is None` 那支，26 条测试仍全绿 ⇒ 没钉住）。

    三条都要钉：① 缺 `text` ⇒ 422；② Jev 不可用 ⇒ **200 + `available=false`**
    （不是 500，也**不是**"判定为不触发"）；③ 正常 ⇒ 真把 verdict 透出去。
    """
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/laws/compliance-guard", json={}, headers=h)
    assert r.status_code == 422, r.text
    # `json_error` 的信封是 `error` 存**字符串 code**（server.py:332）——别当 dict 取。
    assert r.json()["error"] == "missing_text", r.text

    monkeypatch.setattr(jev_guard, "judge", lambda _t: None)
    r2 = c.post("/api/v1/laws/compliance-guard", json={"text": "动火作业怎么分级？"}, headers=h)
    assert r2.status_code == 200, r2.text
    assert r2.json()["data"] == {"available": False, "verdict": "unknown"}, r2.text

    monkeypatch.setattr(jev_guard, "judge",
                        lambda _t: {"verdict": "trigger", "signals": {"a": 0.9}, "model": "x"})
    r3 = c.post("/api/v1/laws/compliance-guard", json={"text": "动火作业怎么分级？"}, headers=h)
    assert r3.status_code == 200 and r3.json()["data"]["available"] is True, r3.text
    assert r3.json()["data"]["verdict"] == "trigger", r3.text


def test_change_signals_endpoint_contract(client, db):
    """`/laws/change-signals` 的契约（2026-09-24 真机核查时补的）。

    ⚠ **为什么单列**：`/laws/compliance-guard` 那条有契约判据，`change-signals` 原先**没有**
    ——而"非法 `signal` 值给 422"恰好是最容易被改成"静默当全部返回"的那种
    （改了会让按档筛选悄悄退化成"返回所有"）。

    ⚠ **判据必须走真 `create_app`**（`client` fixture 提供）：先前我拿一个"返回字典的假
    `json_error` 桩"写核查脚本，结果**状态码被桩吃掉**、4xx 看起来像 200，
    差点报"引擎有 bug"——**代码是对的，脚本骗了我自己**。
    """
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/v1/laws/change-signals", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert set(d["by_signal"]) <= {"draft", "repealed", "revised", "issued"}, d
    for it in d["items"]:
        assert it["change_signal"] in ("draft", "repealed", "revised", "issued"), it
        assert it["doc_id"] and it["standard_no"], it
    r2 = c.get("/api/v1/laws/change-signals", params={"signal": "repealed"}, headers=h)
    assert r2.status_code == 200, r2.text
    assert all(i["change_signal"] == "repealed" for i in r2.json()["data"]["items"]), r2.text
    r3 = c.get("/api/v1/laws/change-signals", params={"signal": "瞎写"}, headers=h)
    assert r3.status_code == 422, f"非法 signal 必须 422（不许静默当'全部'）：{r3.status_code}"
    assert r3.json()["error"] == "invalid_signal", r3.text


def test_compliance_guard_is_heavy_path():
    """2s 外网 ⇒ 吃重活令牌（MED-3；`tests/test_threadpool_bound.py` 也逐条列了它）。"""
    from src.core.api import server
    assert server.is_heavy_path("/api/v1/laws/compliance-guard")
    # 廉价端点**不许**被顺手关进闸门（§10.82「闸门自己造排队」）
    assert not server.is_heavy_path("/api/v1/laws/catalog")
    assert not server.is_heavy_path("/api/v1/laws/sources")


def test_client_breaker_trips_after_repeated_failures(monkeypatch):
    """连续失败到阈值 ⇒ 熔断，后续**不再发请求**（省掉每条消息一次超时）。"""
    calls = {"n": 0}

    class _Resp:
        status_code = 500
        text = "boom"

    def _post(*_a, **_k):
        calls["n"] += 1
        return _Resp()

    monkeypatch.setattr(jev_client, "_read_key", lambda: "k")
    monkeypatch.setattr(jev_client.requests, "post", _post)
    jev_client.reset_breaker_for_tests()
    # ⚠ 每次失败**各自**断言一次（第一版把整个循环裹进一个 pytest.raises，
    # 于是第 1 次失败就跳出循环、熔断永远到不了阈值 ⇒ 假红）。
    for i in range(jev_client.JEV_BREAKER_FAILS):
        with pytest.raises(jev_client.JevUnavailable):
            jev_client.system_one("s", {"a": jev_client.noul("?", yes="y", no="n")})
    assert jev_client.breaker_open() is True, f"第 {jev_client.JEV_BREAKER_FAILS} 次失败后应熔断"
    with pytest.raises(jev_client.JevUnavailable):
        jev_client.system_one("s", {"a": jev_client.noul("?", yes="y", no="n")})
    assert calls["n"] == jev_client.JEV_BREAKER_FAILS, "熔断后不该再发请求"
    jev_client.reset_breaker_for_tests()
