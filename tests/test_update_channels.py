"""更新渠道适配器表驱动测试（pipeline/04a §2 INS-B 系列；全部离线零联网）。

- Mock 表驱动（04a §0）：应答全部来自 ``tests/fixtures/update_channels.json``，
  ``MockChannelTransport`` 注入四渠道适配器；同一 key 应答按 seq 依次弹出、
  耗尽复用末条；``delay_s`` 超出 ``timeout`` 预算即模拟超时（INS-A-05 口径）。
- INS-B-07：参数化遍历全组合（≥12 行）——每组 ChannelResult 字段唯一确定，
  重跑一轮逐位一致（dataclass 全字段相等）；错误场景两轮异常码一致。
- 四色桶（04a §4）：effective/upcoming→green，superseded→yellow，
  withdrawn→red，查无→gray；命中但状态非法→warn（告警桶，不进四色）。
- INS-C-01 / pipeline/05 §3：captcha 用例只返回标记（recordable=False），
  仓储层硬闸拒绝落库（UPD-1002），update_change_event / event_log 零脏行。
"""
from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

import pytest

from src.core.update.channels import (
    ADAPTER_CLASSES,
    CHANGE_TYPES,
    ChannelResult,
    LEGAL_STATUSES,
    UpdateError,
    recordable,
)
from src.core.update.channels.base import DEFAULT_TIMEOUT_S

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "update_channels.json"
#: captcha 场景（只返回标记，绝不写库——04a INS-C-01）
CAPTCHA_KEYS = ("ogb_captcha_flag", "ogb_captcha_text_feature")


def _load_cases() -> list[dict]:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return data["cases"]


CASES: list[dict] = _load_cases()


# ---------------------------------------------------------------- mock 传输层
class MockChannelTransport:
    """表驱动 mock 传输（零联网）：respond 按 seq 弹出、耗尽复用末条。"""

    def __init__(self, responds: list[dict] | None = None):
        ordered = sorted(responds or [], key=lambda r: r.get("seq", 0))
        self._responses = [r.get("respond", {}) for r in ordered]
        self._cursor = 0
        self.calls: list[dict] = []   # 上游调用记录（供确定性断言）

    def _next(self) -> dict:
        if not self._responses:
            return {}
        respond = self._responses[min(self._cursor, len(self._responses) - 1)]
        self._cursor += 1
        return respond

    def fetch(self, url: str, **kw):  # noqa: ANN001 — 与 transport 契约一致
        self.calls.append({"url": url, **kw})
        respond = self._next()
        if "raise" in respond:
            if respond["raise"] == "Timeout":
                raise TimeoutError(f"mock timeout: {url}")
            raise RuntimeError(f'mock raise: {respond["raise"]}')
        delay_s = respond.get("delay_s")
        if delay_s is not None and float(delay_s) > float(kw.get("timeout", DEFAULT_TIMEOUT_S)):
            raise TimeoutError(f"mock delay {delay_s}s 超过预算 {kw.get('timeout')}s: {url}")
        if respond.get("captcha"):  # §0 顶层 captcha 形态（fixture 内嵌于 body）
            return int(respond.get("http", 200)), {"captcha": True}
        return int(respond.get("http", 200)), respond.get("body")


@dataclasses.dataclass
class ProbeOutcome:
    """单轮探测结果：ChannelResult 或归一异常（UPD-1xxx），附上游调用数。"""

    result: ChannelResult | None
    error_code: str | None
    message: str | None
    calls: int


def _probe_once(case: dict) -> ProbeOutcome:
    """用该 case 的 mock 矩阵独立构建适配器并探测一次（每轮全新实例）。"""
    transport = MockChannelTransport(case.get("responds") or [])
    adapter = ADAPTER_CLASSES[case["channel"]](transport=transport)
    try:
        result = adapter.probe(case["standard_no"], case.get("standard_name", ""))
    except UpdateError as exc:
        return ProbeOutcome(None, exc.code, str(exc), len(transport.calls))
    return ProbeOutcome(result, None, None, len(transport.calls))


# ---------------------------------------------------------------- 判定辅助
def _bucket_of(result: ChannelResult) -> str:
    """结果 → 四色桶（04a §4 映射）；命中但状态非法归 warn 告警桶。"""
    if result.captcha:
        return "captcha"
    if not result.found:
        return "gray"
    if result.legal_status == "withdrawn":
        return "red"
    if result.legal_status == "superseded":
        return "yellow"
    if result.legal_status in ("effective", "upcoming"):
        return "green"
    return "warn"


def _expect_bucket(expect: dict) -> str:
    """fixture expect 子集 → 同口径期望桶。"""
    if "error_code" in expect:
        return "error"
    if expect.get("captcha"):
        return "captcha"
    if not expect.get("found"):
        return "gray"
    status = expect.get("legal_status")
    if status == "withdrawn":
        return "red"
    if status == "superseded":
        return "yellow"
    if status in ("effective", "upcoming"):
        return "green"
    return "warn"


def _assert_expect_subset(result: ChannelResult, expect: dict) -> None:
    for field_name, expected in expect.items():
        if field_name == "error_code":
            continue
        actual = getattr(result, field_name)
        if expected == "@any":  # 哨兵：仅要求非空
            assert actual, f"{field_name}: 期望非空(@any)，实际 {actual!r}"
        else:
            assert actual == expected, f"{field_name}: 期望 {expected!r} 实际 {actual!r}"


# ---------------------------------------------------------------- 接线不变量（§11.0 R2）
def test_每个链上的渠道名都能在适配套表里查到():
    """**接线不变量**：`routing.select_chain()` 返回的每个渠道名，都必须在
    `inspector._build_adapters()` 的字典里**查得到**。

    为什么要有这条（§11.0 R2 实测缺陷）：注册表的键取自**文件名**（`ttzb`），而
    适配器自己的 `name` 是 `ttbz`、`routing` 链里写的也是 `ttbz` ⇒ 原先按注册键建字典，
    `_probe_number` 按链里的名字查不到该渠道，**静默跳过**——团体标准一路永远走不到
    专用渠道，现场只表现为"没搜到"。

    ⚠ 这条用**穷举前置路由 + 兜底链**两处，而不是只测 `ttbz` 一个号：任何"链里写了
    但字典里没有"的名字都会红（数据驱动，加了新前缀也自动覆盖）。
    """
    from src.core.update.channels.routing import _FALLBACK, _PREFIX_ROUTE
    from src.core.update.inspector import _build_adapters

    built = _build_adapters(transport=None)
    chain_names = sorted({ch for _, ch in _PREFIX_ROUTE} | set(_FALLBACK))
    missing = [name for name in chain_names if name not in built]
    assert not missing, (
        f"这些渠道在 routing 链里被引用、但适配套表里查不到 ⇒ 会被静默跳过：{missing}"
        f"（表里的键={sorted(built)}）")
    # 反向也钉一下：注册了但没进字典的（不该存在——除非类 import 失败被跳过）
    registry_names = {getattr(cls, "name", None) or key
                      for key, cls in ADAPTER_CLASSES.items() if cls is not None}
    assert registry_names <= set(built), f"注册了但没建出来：{sorted(registry_names - set(built))}"


def test_ttzb_那一个渠道的键与名不一致要按名建表():
    """具体到那个不一致的渠道：字典里必须能按 `ttbz`（链里的名字）取到。"""
    from src.core.update.inspector import _build_adapters

    built = _build_adapters(transport=None)
    assert "ttbz" in built, "团标渠道又变成查不到了（注册键 ttzb ≠ 适配器名 ttbz）"
    assert built["ttbz"].__class__.__name__ == "TtzbAdapter"


# ---------------------------------------------------------------- httpx 回退自检（§11.0 R5d）
def test_httpx_自检能看出本机是否可用():
    """`httpx_usable()` 必须**既**能报可用、也能把不可用的原因变成一句人话。"""
    from src.core.update.channels.base import httpx_usable

    ok, why = httpx_usable()
    assert isinstance(ok, bool) and isinstance(why, str)
    # 可用时不给原因；不可用时原因不能是空的（否则日志里等于没说）
    assert why == "" if ok else len(why) > 5, (ok, why)


def test_两个栈都不可用时日志点名原因(monkeypatch):
    """`curl_cffi` 缺 + httpx 构造失败 ⇒ **ERROR 且点名**，而不是一条 WARN 就回退。

    背景（本机实测，§11.0 R3d 的 G27）：`NO_PROXY` 含 `[::1]` 时 httpx 0.28.1 连 `Client()`
    都构造不出来 ⇒ 那种环境里**每个渠道都会失败**，而原实现只打一条 WARN ⇒ 现场只看到
    "每条都失败"，症状离原因很远。这条用例钉住"当场点名"。
    """
    from src.core.update.channels import base

    logs: list[tuple] = []
    monkeypatch.setattr(base, "upd_log", lambda *a, **k: logs.append((a, k)))
    monkeypatch.setattr(base, "httpx_usable", lambda: (False, "InvalidURL: Invalid port: ':1]'"))

    class _NoCurl:
        def __init__(self):
            raise ImportError("No module named 'curl_cffi'")

    monkeypatch.setattr(base, "CurlCffiTransport", _NoCurl)
    t = base.default_transport()
    assert isinstance(t, base.HttpxTransport), "回退仍要给一个可用对象（不许抛，否则引擎起不来）"
    assert logs, "自检失败必须留下日志"
    args, _kw = logs[0]
    assert args[2] == "ERROR", args
    assert "both_transports_unusable" in args[3], args
    assert "::1" in args[3], "日志里要带可操作的成因提示"


def test_httpx_可用时只打_WARN(monkeypatch):
    from src.core.update.channels import base

    logs: list[tuple] = []
    monkeypatch.setattr(base, "upd_log", lambda *a, **k: logs.append((a, k)))
    monkeypatch.setattr(base, "httpx_usable", lambda: (True, ""))

    class _NoCurl:
        def __init__(self):
            raise ImportError("No module named 'curl_cffi'")

    monkeypatch.setattr(base, "CurlCffiTransport", _NoCurl)
    base.default_transport()
    assert logs and logs[0][0][2] == "WARN", logs


# ---------------------------------------------------------------- govcn 换棒（§11.0 R5b）
def _govcn_body(rows):
    """真接口响应形状（`searchVO.catMap.*.listVO`）——与 `law_source.govcn_client.parse_rows`
    读的字段一致；**故意带 `<em>` 高亮**（真响应就有，`parse_rows` 负责剥掉）。"""
    return {"searchVO": {"catMap": {"gongwen": {
        "catName": "国务院文件",
        "listVO": rows,
    }}}}


class _StubTransport:
    def __init__(self, status, body):
        self.status = status
        self.body = body
        self.calls: list[tuple[str, dict]] = []

    def fetch(self, url, **kw):
        self.calls.append((url, kw))
        return self.status, self.body


def test_govcn_真接口命中_按摘要里的标准号():
    """**换棒的实证**（R1 的 G6：旧实现只解 mock dict ⇒ 真实网络恒 miss）。

    真接口按 `searchfield=content` 检索时，标准号通常出现在 **summary** 里 ——
    所以 `_pick` 必须同时看标题与摘要，否则把真命中判成 miss。
    """
    from src.core.update.channels.govcn_announce import GovcnAnnounceAdapter

    t = _StubTransport(200, _govcn_body([{
        "title": "国务院关于废止部分<em>标准</em>的决定",
        "summary": "……自本决定发布之日起，GB/T 30871-2022 等标准停止执行……",
        "url": "https://www.gov.cn/zhengce/content/2026/x.htm",
        "pubtime": "2026-05-01", "pcode": "国发〔2026〕1号", "source": "国务院",
    }]))
    out = GovcnAnnounceAdapter(transport=t).probe("GB/T 30871-2022",
                                                 "危险化学品企业特殊作业安全规范")
    assert out.found is True, "摘要里含标准号却判成 miss —— 换棒等于没换"
    assert out.evidence_url == "https://www.gov.cn/zhengce/content/2026/x.htm"
    assert out.legal_status == "withdrawn"          # 标题含「废止」
    url, kw = t.calls[0]
    assert url.endswith("/search-gov/data"), f"没打真接口：{url}"
    assert kw.get("params", {}).get("searchfield") == "content", kw
    assert kw["params"]["t"] == "zhengcelibrary"


def test_govcn_真接口空结果算_miss_不算命中():
    from src.core.update.channels.govcn_announce import GovcnAnnounceAdapter

    t = _StubTransport(200, _govcn_body([]))
    out = GovcnAnnounceAdapter(transport=t).probe("GB/T 30871-2022")
    assert out.found is False


def test_govcn_旧的_mock_契约仍然可用():
    """离线 fixture 走的是 mock 分支（`{"announcements": [...]}`）——换棒**不许**把它弄坏。"""
    from src.core.update.channels.govcn_announce import GovcnAnnounceAdapter

    t = _StubTransport(200, {"announcements": [{
        "title": "关于 GB/T 30871-2022 的公告", "url": "https://x/1", "date": "2026-01-01",
    }]})
    out = GovcnAnnounceAdapter(transport=t).probe("GB/T 30871-2022")
    assert out.found is True and out.evidence_url == "https://x/1"


# ---------------------------------------------------------------- 测试
def test_fixture_matrix_contract():
    """fixture 自检：≥12 行组合（INS-B-07 口径）、key 唯一、渠道与必填段齐全。"""
    assert len(CASES) >= 12
    keys = [c["key"] for c in CASES]
    assert len(keys) == len(set(keys)), "case key 必须唯一"
    for case in CASES:
        assert case["channel"] in ADAPTER_CLASSES, f"未知渠道 {case['channel']}"
        assert {"standard_no", "responds", "expect"} <= set(case)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["key"])
def test_channel_matrix_deterministic_and_idempotent(case):
    """INS-B-07：逐组合断言字段唯一确定 + 两轮重跑逐位一致。"""
    first, second = _probe_once(case), _probe_once(case)
    expect = case["expect"]

    if "error_code" in expect:  # 错误场景：两轮异常码/消息确定且一致
        assert first.result is None and second.result is None
        assert first.error_code == second.error_code == expect["error_code"]
        assert first.message == second.message
        assert first.calls == second.calls == 1
        return

    r1, r2 = first.result, second.result
    assert r1 is not None and r2 is not None
    # 重跑幂等：dataclass 全字段（含 raw）逐位一致
    assert dataclasses.asdict(r1) == dataclasses.asdict(r2)
    # 字段唯一确定：fixture expect 子集逐一命中
    _assert_expect_subset(r1, expect)
    # 枚举域约束：change_type / legal_status 不越界
    assert r1.channel == case["channel"]
    assert r1.change_type is None or r1.change_type in CHANGE_TYPES
    assert r1.legal_status is None or r1.legal_status in LEGAL_STATUSES
    # (source_channel, change_type, 色) 三元组按 expect 口径唯一确定
    assert (r1.channel, r1.change_type, _bucket_of(r1)) == \
           _combo_tuple_from_expect(case)
    # 单轮上游调用数确定：所有渠道恰一次（laws_db 骨架期零调用假设已随 F-22 真机实现退役）
    expected_calls = 1
    assert first.calls == second.calls == expected_calls
    # captcha 用例只返回标记，不允许落库
    if case["key"] in CAPTCHA_KEYS:
        assert r1.captcha is True and recordable(r1) is False


def _combo_tuple_from_expect(case: dict) -> tuple:
    return (case["channel"], case["expect"].get("change_type"),
            _expect_bucket(case["expect"]))


def test_combo_tuple_stable_across_rounds():
    """全矩阵遍历：(channel, change_type, 色) 元组两轮恒等，无不确定场景。"""
    non_error = [c for c in CASES if "error_code" not in c["expect"]]
    tuples_round1, tuples_round2 = {}, {}
    for case in non_error:
        outcome = _probe_once(case)
        assert outcome.result is not None
        result = outcome.result
        tup = (result.channel, result.change_type, _bucket_of(result))
        tuples_round1[case["key"]] = tup
        rerun = _probe_once(case).result
        tuples_round2[case["key"]] = (rerun.channel, rerun.change_type,
                                      _bucket_of(rerun))
    assert tuples_round1 == tuples_round2
    assert len(tuples_round1) == len(non_error)


def test_captcha_marker_only_never_writes_db(db):
    """INS-C-01：captcha 结果只返回标记；仓储硬闸 UPD-1002 拒绝，零脏行零误计数。"""
    from src.core.update import change_repo

    # 共享会话级库（conftest）：用增量断言，禁止绝对计数（13.3 约定）
    base_changes = db.execute("SELECT COUNT(*) FROM update_change_event").fetchone()[0]
    base_events = db.execute(
        "SELECT COUNT(*) FROM event_log WHERE event_type='update/change_detected'"
    ).fetchone()[0]

    batch = change_repo.create_batch(trigger="manual", total=1)

    # 正向对照：非 captcha 的合法事件可正常入库（证明硬闸只挡 captcha）
    change_repo.append_change({
        "batch_id": batch["batch_id"],
        "standard_no": "GB 99999-2099",
        "change_type": "not_found",
        "source_channel": "official_gb",
    })

    for key in CAPTCHA_KEYS:
        case = next(c for c in CASES if c["key"] == key)
        outcome = _probe_once(case)
        assert outcome.result is not None and outcome.result.captcha is True
        assert recordable(outcome.result) is False
        with pytest.raises(UpdateError) as excinfo:
            change_repo.append_change({
                "batch_id": batch["batch_id"],
                "standard_no": case["standard_no"],
                "change_type": "not_found",
                "source_channel": case["channel"],
                "captcha": True,
            })
        assert excinfo.value.code == "UPD-1002"

    # 库内零污染：captcha 未产生任何变更行/审计行，批次未误记 gray/checked
    delta_changes = db.execute("SELECT COUNT(*) FROM update_change_event").fetchone()[0] - base_changes
    delta_events = db.execute(
        "SELECT COUNT(*) FROM event_log WHERE event_type='update/change_detected'"
    ).fetchone()[0] - base_events
    assert delta_changes == 1
    assert delta_events == 1
    after = change_repo.get_batch(batch["batch_id"])
    assert (after["checked"], after["gray_count"], after["red_count"]) == (0, 0, 0)


# ---------------------------------------------------------------- 可选联网用例（默认 skip）
@pytest.mark.skipif(not os.environ.get("RUN_LIVE"),
                    reason="可选联网用例：设 RUN_LIVE=1 才实跑（ANOM-002 回归验证）")
def test_live_openstd_homepage_default_transport_200():
    """RUN_LIVE=1 时经新默认 transport（curl_cffi 指纹优先）GET openstd 首页断言 200。

    ANOM-002：该站点按 JA3 TLS 指纹掐 Python 握手，httpx 必 SSL UNEXPECTED_EOF；
    默认 transport 已切 curl_cffi impersonate chrome，此用例即其真实回归。
    """
    from src.core.update.channels.base import default_transport

    status, body = default_transport().fetch(
        "https://openstd.samr.gov.cn/bzgk/gb/", timeout=DEFAULT_TIMEOUT_S)
    assert status == 200
    assert isinstance(body, str) and body  # 首页为 HTML 文本，非空即视为真实响应


# ---------------------------------------------------------------- ANOM-003 回归：真实 HTML 解析分支
# 结构采样自 openstd /bzgk/std/std_list 真实响应（2026-08-24 抓取）：
# 服务端渲染 <table>，行为 标准号链接 | mytxt 名称 | 强标|推荐 | 状态 span | 发布日期 | 实施日期。
REAL_OPENSTD_HTML = """
<div class="table-responsive">
<table class="table"><tbody>
<tr>
<td>1</td>
<td style="text-align: left;"><a href="javascript:void(0)" onclick="showInfo('561B95121C30853A6B45CA9471F39239');">GB 30871-2022</a></td>
<td></td><td> </td>
<td class="mytxt" style="text-align: left; padding: 0 8px 0 8px;"><a href="javascript:void(0)" style="color: gray;" onclick="showInfo('561B95121C30853A6B45CA9471F39239');">危险化学品企业特殊作业安全规范</a></td>
<td> 强标 </td>
<td> <span class="text-success" style="font-size:13px;">现行</span> </td>
<td>2022-03-15</td><td> 2022-10-01 </td>
<td><button class="btn btn-sm btn-default" onclick="showInfo('561B95121C30853A6B45CA9471F39239');" class="detail">查看详细</button></td>
</tr>
<tr>
<td>2</td>
<td style="text-align: left;"><a href="javascript:void(0)" onclick="showInfo('ABCDEF');">GB 50016-2014</a></td>
<td></td><td> </td>
<td class="mytxt" style="text-align: left; padding: 0 8px 0 8px;"><a href="javascript:void(0)" onclick="showInfo('ABCDEF');">建筑设计防火规范</a></td>
<td> 强标 </td>
<td> <span class="text-warning" style="font-size:13px;">被代替</span> </td>
<td>2014-08-27</td><td> 2015-05-01 </td>
<td><button class="btn btn-sm btn-default" onclick="showInfo('ABCDEF');">查看详细</button></td>
</tr>
</tbody></table></div>
"""


def test_official_gb_parses_real_openstd_html():
    """ANOM-003 回归：真实 HTML 结果表 → ChannelResult 正确（现行→effective/no_change、被代替→superseded）。"""
    from src.core.update.channels.official_gb import OfficialGbAdapter

    transport = MockChannelTransport(
        [{"seq": 1, "respond": {"http": 200, "body": REAL_OPENSTD_HTML}}])
    adapter = OfficialGbAdapter(transport=transport)

    r1 = adapter.probe("GB 30871-2022")
    assert r1.found is True
    assert r1.legal_status == "effective"
    assert r1.change_type == "no_change"
    assert r1.latest_version == "GB 30871-2022"
    assert r1.effective_date == "2022-03-15"
    assert r1.evidence_url == "showInfo:561B95121C30853A6B45CA9471F39239"

    r2 = adapter.probe("GB 50016-2014")
    assert r2.found is True
    assert r2.legal_status == "superseded"
    assert r2.change_type == "superseded"

    # 库内无此号（响应里没有）→ 诚实 miss
    r3 = adapter.probe("GB 55037-2022")
    assert r3.found is False
    assert r3.legal_status is None


class TestNormNoFullWidth:
    """§11.0 R6c-2a 实测的根因：真库 **92%** 的标准号写全角斜杠 `／`，而站点返回半角 `/`。

    原先 `norm_no` 只剥半角 ⇒ 同一个号两边归一出 `GBT17098-1997` 与 `GB／T17098-1997`，
    **永不相等** ⇒ "按归一号挑行"的匹配全线失手。
    真机 A/B（同一批号两种写法各跑一遍）：**全角 0/6 命中、半角 5/6 命中**。
    """

    def test_全角与半角斜杠归一到同一个号(self):
        from src.core.update.channels.base import norm_no
        assert norm_no("GB／T 17098-1997") == norm_no("GB/T 17098-1997") == "GBT17098-1997"
        assert norm_no("GB／T 1.1-2020") == norm_no("GB/T 1.1-2020")
        # 半角行为不许变（既有大量用例依赖它）
        assert norm_no("GB/T 3608-2008") == norm_no("GBT3608-2008".replace("GBT", "GB/T"))
        assert norm_no(None) == "" and norm_no("  ") == ""

    def test_按归一号挑行时全角目标能命半角行(self):
        """这条是"匹配失手"的最小复现：目标写全角、站点返回半角。"""
        from src.core.update.channels.base import pick_row_by_norm
        rows = [{"code": "GB/T 17098-1997", "status": "现行"}]
        assert pick_row_by_norm(rows, "GB／T 17098-1997") == rows[0]
        assert pick_row_by_norm(rows, "GB/T 17098-1997") == rows[0]
