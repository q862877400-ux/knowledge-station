"""「点开即核验」verify_law 单测（任务 2）。

全程 mock ``flk_client.detail``（monkeypatch 模块属性），禁止真实网络。
覆盖矩阵：
  现行/废止/已修改/尚未生效 映射与分级 TTL · 官方未标注 · 查无 60s 负缓存 ·
  异常降级（绝不抛）· 超时降级 · 未知 sxx 告警不猜测 · 缓存命中不重复打接口 ·
  TTL 过期重查 · JSON 落盘温启动回装 · 并发单飞合并。
"""
import logging
import threading
import time
from types import SimpleNamespace

import pytest

BBBS = "ff8081817ab22e0c017abd909312060a"
EVIDENCE = f"https://flk.npc.gov.cn/detail?id={BBBS}"


class FakeDetail:
    """FlkDetail 形状的最小替身（raw 默认非空 = 详情正常返回）。"""

    def __init__(self, sxx=None, title="中华人民共和国消防法", raw=None, **extra):
        self.sxx = sxx
        self.title = title
        self.raw = {"data": "nonempty"} if raw is None else raw
        self.zdjgName = extra.get("zdjgName", "全国人民代表大会常务委员会")
        self.gbrq = extra.get("gbrq", "2021-04-29")
        self.sxrq = extra.get("sxrq", "2021-04-29")


@pytest.fixture()
def vcache():
    """每用例隔离：清内存缓存 + 删落盘文件（conftest 已把 data_dir 重定向到临时目录）。"""
    from src.core.config import get_settings
    from src.core.knowledge.law_source import verify as V
    V.reset_verify_cache()
    path = get_settings().data_dir / V.CACHE_FILENAME
    path.unlink(missing_ok=True)
    yield V
    V.reset_verify_cache()
    path.unlink(missing_ok=True)


def _mock_detail(monkeypatch, responder):
    """安装 flk_client.detail 替身并统计调用（verify.py 运行期属性访问，补丁必生效）。"""
    calls = {"n": 0, "bbbs": []}

    def wrapper(bbbs):
        calls["n"] += 1
        calls["bbbs"].append(bbbs)
        return responder(bbbs)

    monkeypatch.setattr("src.core.knowledge.law_source.flk_client.detail", wrapper)
    return calls


def _ttl_of(vcache, bbbs: str) -> int:
    ent = vcache._MEM[bbbs]
    return int(round(ent["expires_at"] - ent["cached_at"]))


def _expire(vcache, bbbs: str) -> None:
    """白盒把条目拨到已过期（避免真实 sleep 24h）。"""
    vcache._MEM[bbbs]["expires_at"] = time.time() - 1


# ---------------------------------------------------------------------------
# 映射：四枚举状态 + 附加证据字段
# ---------------------------------------------------------------------------

def test_effective_mapping_payload_contract(vcache, monkeypatch):
    calls = _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=3))
    r = vcache.verify_law(BBBS)
    assert calls["n"] == 1 and calls["bbbs"] == [BBBS]
    assert r["status"] == "effective"
    assert r["status_text"] == "现行有效"
    assert r["evidence_url"] == EVIDENCE
    assert r["checked_at"] and "T" in r["checked_at"]      # ISO 时间戳
    assert r["cached"] is False and r["retryable"] is False
    assert r["sxx"] == 3
    assert r["title"] == "中华人民共和国消防法"
    assert r["issuer"] == "全国人民代表大会常务委员会"
    assert r["published_date"] == "2021-04-29"
    assert r["effective_date"] == "2021-04-29"


@pytest.mark.parametrize("sxx,status,text", [
    (1, "withdrawn", "已废止"),
    (2, "superseded", "已修改"),
    (4, "upcoming", "尚未生效"),
])
def test_status_mapping_strict(vcache, monkeypatch, sxx, status, text):
    calls = _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=sxx))
    r = vcache.verify_law(BBBS)
    assert r["status"] == status and r["status_text"] == text
    assert calls["n"] == 1


def test_sxx_string_form_normalized(vcache, monkeypatch):
    """官方偶发字符串形态（\"3\"）也应归一映射，不误判为未知。"""
    d = FakeDetail(sxx="3")
    _mock_detail(monkeypatch, lambda b: d)
    r = vcache.verify_law(BBBS)
    assert r["status"] == "effective" and r["sxx"] == 3


# ---------------------------------------------------------------------------
# 分级 TTL：现行 24h / 废止·已修改 7d / 尚未生效 6h / 未标注 12h / 查无 60s
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sxx,expect_ttl", [
    (3, 24 * 3600),
    (1, 7 * 24 * 3600),
    (2, 7 * 24 * 3600),
    (4, 6 * 3600),
])
def test_graded_ttl_by_status(vcache, monkeypatch, sxx, expect_ttl):
    _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=sxx))
    vcache.verify_law(BBBS)
    assert _ttl_of(vcache, BBBS) == expect_ttl


def test_unmarked_uses_12h_ttl(vcache, monkeypatch):
    """详情非空但官方未标注时效 → unmarked，不从可访问性推断。"""
    calls = _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=None))
    r = vcache.verify_law(BBBS)
    assert r["status"] == "unmarked"
    assert r["status_text"] == "官方未标注效力状态"
    assert _ttl_of(vcache, BBBS) == 12 * 3600
    assert calls["n"] == 1


def test_not_found_negative_cache_60s(vcache, monkeypatch):
    """详情 data 为空 → 查无；60s 负缓存内不重打接口，过期后重查。"""
    calls = _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=None, raw={}))
    r1 = vcache.verify_law(BBBS)
    assert r1["status"] == "not_found"
    assert r1["status_text"] == "官方库未收录"
    assert _ttl_of(vcache, BBBS) == 60
    # 负缓存窗口内：第二次不再打接口
    r2 = vcache.verify_law(BBBS)
    assert r2["status"] == "not_found" and r2["cached"] is True
    assert calls["n"] == 1
    # 过期后：重新查
    _expire(vcache, BBBS)
    vcache.verify_law(BBBS)
    assert calls["n"] == 2


def test_minimal_mock_without_raw_treated_as_not_found(vcache, monkeypatch):
    """无 raw 属性且无 sxx 的最小对象 → 无可判定信息，按查无处理（不猜）。"""
    ns = SimpleNamespace(sxx=None, title="")
    _mock_detail(monkeypatch, lambda b: ns)
    r = vcache.verify_law(BBBS)
    assert r["status"] == "not_found"


# ---------------------------------------------------------------------------
# 降级语义：异常 / 超时 / 未知 sxx —— 一律 unverified 且不缓存、绝不上抛
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("boom", [
    RuntimeError("network down"),
    ValueError("http 500"),
    KeyError("resp"),
])
def test_exception_degrades_to_unverified_never_cached(vcache, monkeypatch, boom):
    def responder(b):
        raise boom

    calls = _mock_detail(monkeypatch, responder)
    for _ in range(2):  # 第二次也走网络（异常不缓存），同样降级
        r = vcache.verify_law(BBBS)
        assert r["status"] == "unverified"
        assert r["status_text"] == "未核验"
        assert r["retryable"] is True and r["cached"] is False
    assert calls["n"] == 2


def test_timeout_degrades_within_budget(vcache, monkeypatch):
    """上游卡死 > 单请求超时 → 截断降级 unverified（总耗时受预算约束）。"""
    import src.core.knowledge.law_source.verify as V

    def slow(bbbs):
        time.sleep(0.8)
        return FakeDetail(sxx=3)

    _mock_detail(monkeypatch, slow)
    monkeypatch.setattr(V, "REQUEST_TIMEOUT_S", 0.15)
    t0 = time.monotonic()
    r = vcache.verify_law(BBBS)
    elapsed = time.monotonic() - t0
    assert r["status"] == "unverified" and r["retryable"] is True
    assert r.get("reason") == "timeout"
    assert elapsed < 2.0          # 远小于上游 0.8s+ 的卡死时长被截断
    assert BBBS not in vcache._MEM  # 不缓存


def test_unknown_sxx_warns_and_does_not_guess(vcache, monkeypatch, caplog):
    """未知 sxx → unverified + WARN 告警，不猜测、不缓存。"""
    _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=99))
    with caplog.at_level(logging.WARNING, logger="ks.law.verify"):
        r = vcache.verify_law(BBBS)
    assert r["status"] == "unverified" and r["retryable"] is True
    assert any("illegal_flk_sxx" in rec.message for rec in caplog.records)
    assert BBBS not in vcache._MEM


def test_bool_sxx_is_not_mapped(vcache, monkeypatch):
    """bool 是 int 子类：True/False 不得误判成 1/0 映射。"""
    _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=True))
    r = vcache.verify_law(BBBS)
    assert r["status"] == "unverified"


def test_empty_bbbs_no_network(vcache, monkeypatch):
    calls = _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=3))
    for bad in ("", "   ", None):
        r = vcache.verify_law(bad)
        assert r["status"] == "unverified" and r["retryable"] is False
    assert calls["n"] == 0


# ---------------------------------------------------------------------------
# 缓存命中 / TTL 过期重查 / 落盘温启动 / 单飞
# ---------------------------------------------------------------------------

def test_cache_hit_second_call_skips_network(vcache, monkeypatch):
    calls = _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=3))
    r1 = vcache.verify_law(BBBS)
    assert r1["cached"] is False
    for i in range(3):  # 连续三次全部走缓存，上游只被打一次
        r = vcache.verify_law(BBBS)
        assert r["status"] == "effective" and r["cached"] is True
        assert r["evidence_url"] == EVIDENCE
    assert calls["n"] == 1


def test_ttl_expiry_refetches(vcache, monkeypatch):
    calls = _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=3))
    vcache.verify_law(BBBS)
    _expire(vcache, BBBS)               # 拨快时钟到过期（免真实等待）
    r2 = vcache.verify_law(BBBS)
    assert calls["n"] == 2
    assert r2["cached"] is False and r2["status"] == "effective"


def test_disk_persistence_warm_restart(vcache, monkeypatch, tmp_path):
    """落盘写穿 + 进程重启模拟（清内存）：温启动后仍命中缓存、不打接口。"""
    from src.core.config import get_settings
    calls = _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=3))
    vcache.verify_law(BBBS)
    cache_file = get_settings().data_dir / vcache.CACHE_FILENAME
    assert cache_file.exists()
    vcache.reset_verify_cache()          # 模拟重启：内存清空、落盘标记复位
    r = vcache.verify_law(BBBS)
    assert calls["n"] == 1               # 温启动回装，未再打接口
    assert r["status"] == "effective" and r["cached"] is True


def test_corrupt_cache_file_is_cold_start(vcache, monkeypatch):
    from src.core.config import get_settings
    f = get_settings().data_dir / vcache.CACHE_FILENAME
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("{broken json!!", encoding="utf-8")
    calls = _mock_detail(monkeypatch, lambda b: FakeDetail(sxx=3))
    r = vcache.verify_law(BBBS)
    assert r["status"] == "effective" and calls["n"] == 1  # 坏文件静默跳过


def test_singleflight_merges_concurrent_calls(vcache, monkeypatch):
    """同 bbbs 并发 N 路 → 上游只被打一次，全部拿到同一结论。"""
    start = threading.Barrier(4)         # 四个调用线程同时进入 verify_law

    def responder(bbbs):
        time.sleep(0.25)                 # 上游慢一点，等锁方必然落在缓存窗口内
        return FakeDetail(sxx=3)

    _mock_detail(monkeypatch, responder)
    results: list[dict] = []
    errs: list[Exception] = []

    def worker():
        try:
            start.wait(timeout=5)
            results.append(vcache.verify_law(BBBS))
        except Exception as e:  # noqa: BLE001 — 收集而非让断言静默通过
            errs.append(e)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert errs == []
    assert len(results) == 4
    assert {r["status"] for r in results} == {"effective"}
    assert sum(1 for r in results if r["cached"]) == 3   # 仅首跑 fresh，其余命中
