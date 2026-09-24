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
    assert seen["timeout"] == jev_client.JEV_TIMEOUT_S, "必须有超时上限（每条消息都可能走）"
    jev_client.reset_breaker_for_tests()


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
