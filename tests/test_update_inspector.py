"""巡检编排器测试（pipeline/04a §1 巡检编排 / §3 验证码 / §4 三色判定 + 批次2万级分层预算）。

全部离线零联网：``InspectTransport`` 注入三渠道适配器（channels/base transport 契约），
应答表按 (channel, standard_no) 路由、seq 弹出耗尽复用末条；暂停注入走非阻塞
``request_pause``（可在 mock 回调线程安全调用）。

与 04a 文档的两处以批次2指令为准的差异（inspector.py 模块头已声明）：
- superseded（被代替）→ 🔴red（指令：废止/替代→superseded|withdrawn/red）；D-03 按红断言；
- upcoming 命中新版 → new_version/yellow（指令：新版→new_version/yellow），
  current_legal_status 如实落 'upcoming'、不触发废止对比（D-02 精神保留）。

会话级库注意：doc_id/standard_no/change_id 全部带用例前缀，避免跨用例残留串扰。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from src.core.update import (
    UpdateError,
    create_inspect_batch,
    get_inspect_batch,
    inspector,
    pause_batch,
    request_pause,
    resume_batch,
    run_batch,
    select_standard_nos,
)
from src.core.update.scheduler import UpdateScheduler

T0 = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)


# ================================================================ mock 传输层
class InspectTransport:
    """(channel, standard_no) 路由的表驱动 mock：seq 弹出、耗尽复用末条。"""

    def __init__(self):
        self._scripts: dict[tuple[str, str], list[dict]] = {}
        self.calls: list[dict] = []
        self._lock = threading.Lock()
        self._active = 0
        self.max_active = 0
        self.hooks = []  # callable(transport)，fetch 开始时触发（暂停注入点）

    def configure(self, channel: str, standard_no: str, responses: list[dict]):
        self._scripts[(channel, standard_no)] = list(responses)

    @staticmethod
    def _route(url: str) -> str:
        if "openstd" in url:
            return "official_gb"
        if "bing" in url:
            return "web"
        return "govcn"

    @staticmethod
    def _parse_no(url: str, kw: dict) -> str:
        params = kw.get("params") or {}
        if "searchText" in params:
            return str(params["searchText"]).strip()
        q = str(params.get("q", "")).strip()
        return q.split()[0] if q.split() else ""

    def starts(self, standard_no: str | None = None, channel: str | None = None):
        return [c for c in self.calls
                if c["event"] == "start"
                and (standard_no is None or c["standard_no"] == standard_no)
                and (channel is None or c["channel"] == channel)]

    def fetch(self, url: str, **kw):  # noqa: ANN001 — 与 transport 契约一致
        channel = self._route(url)
        no = self._parse_no(url, kw)
        with self._lock:
            self._active += 1
            self.max_active = max(self.max_active, self._active)
            self.calls.append({"event": "start", "channel": channel,
                               "standard_no": no})
        try:
            for hook in self.hooks:
                hook(self)
            respond = (self._scripts.get((channel, no)) or [{}])[0]
            script = self._scripts.get((channel, no))
            if script and len(script) > 1:
                script.pop(0)
                respond = script[0]
            if "raise" in respond:
                if respond["raise"] == "Timeout":
                    raise TimeoutError(f"mock timeout: {url}")
                raise RuntimeError(f'mock raise: {respond["raise"]}')
            delay_s = respond.get("delay_s")
            if delay_s is not None and float(delay_s) > float(kw.get("timeout", 30)):
                raise TimeoutError(f"mock delay {delay_s}s 超预算: {url}")
            if "sleep" in respond:
                time.sleep(float(respond["sleep"]))
            if respond.get("captcha"):
                return 200, {"captcha": True}
            return int(respond.get("http", 200)), respond.get("body")
        finally:
            with self._lock:
                self._active -= 1
                self.calls.append({"event": "end", "channel": channel,
                                   "standard_no": no})


# ---------------------------------------------------------------- 应答构造器
def bump_year(no: str, year: str) -> str:
    """仅换尾部年代（同主体新版）：GB/T X 0001-2020 → GB/T X 0001-2025。"""
    import re
    return re.sub(r"\d{4}$", year, no)


def r_eff(no: str) -> dict:
    return {"http": 200, "body": {"rows": [
        {"code": no, "name": "标准", "state": "现行",
         "url": f"https://openstd.samr.gov.cn/gb/std?id={no}", "date": "2020-01-01"}]}}


def r_new(old: str) -> dict:
    new = bump_year(old, "2025")
    return {"http": 200, "body": {"rows": [
        {"code": new, "name": "标准", "state": "现行",
         "url": "https://openstd.samr.gov.cn/gb/std?id=new", "date": "2025-05-01"}]}}


def r_upcoming(old: str) -> dict:
    new = bump_year(old, "2026")
    return {"http": 200, "body": {"rows": [
        {"code": new, "name": "标准", "state": "即将实施",
         "url": "https://openstd.samr.gov.cn/gb/std?id=new", "date": "2026-01-01"}]}}


def r_state(no: str, state: str) -> dict:
    return {"http": 200, "body": {"rows": [
        {"code": no, "name": "标准", "state": state,
         "url": "https://openstd.samr.gov.cn/gb/std?id=x"}]}}


R_MISS = {"http": 200, "body": {"rows": [], "total": 0}}
R_CAPTCHA = {"http": 200, "body": {"captcha": True, "msg": "请输入验证码"}}


# ---------------------------------------------------------------- 库内夹具
def add_doc(db, prefix: str, idx: int, watch: bool = False,
            doc_bookmark: bool = False) -> dict:
    doc_id = f"{prefix}_d{idx}"
    no = f"GB/T {prefix.upper()} {idx:04d}-2020"
    db.execute(
        "INSERT INTO doc_meta(doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (doc_id, no, f"标准{idx}", f"C{idx}", "r1", "[]", f"{doc_id}.pdf",
         hashlib.sha256(doc_id.encode()).hexdigest()))
    if watch:
        db.execute("INSERT INTO watch_list(watch_id, doc_id) VALUES (?,?)",
                   (f"w_{doc_id}", doc_id))
    if doc_bookmark:
        db.execute("INSERT INTO user_doc_bookmark(doc_bookmark_id, doc_id)"
                   " VALUES (?,?)", (f"dmb_{doc_id}", doc_id))
    return {"doc_id": doc_id, "standard_no": no, "standard_name": f"标准{idx}"}


def seed_inspected(db, item: dict, change_type: str = "no_change"):
    """预置一次历史巡检事件（使 doc 归入 tier1 / 已首检集合）。"""
    db.execute("INSERT OR IGNORE INTO update_check_batch(batch_id, trigger_type,"
               " status, total) VALUES ('upd_seedpool','manual','done',1)")
    db.execute(
        "INSERT INTO update_change_event(change_id, batch_id, doc_id, standard_no,"
        " change_type, current_legal_status, source_channel)"
        " VALUES (?,?,?,?,?,?, 'official_gb')",
        (f"chg_seed_{item['doc_id']}", "upd_seedpool", item["doc_id"],
         item["standard_no"], change_type, "effective"))


def mk_items(*items: dict) -> list[dict]:
    return [{"doc_id": it["doc_id"], "standard_no": it["standard_no"],
             "standard_name": it.get("standard_name", "")} for it in items]


def cfg_all(t: InspectTransport, items: list[dict], resp: dict,
            channels=("official_gb", "web", "govcn")):
    for it in items:
        for ch in channels:
            t.configure(ch, it["standard_no"], [resp])


def event_rows(db, event_type: str, target_id: str | None = None,
               **meta_like) -> list[sqlite3.Row]:
    rows = db.execute("SELECT * FROM event_log WHERE event_type=?"
                      " ORDER BY rowid", (event_type,)).fetchall()
    out = []
    for r in rows:
        if target_id is not None and r["target_id"] != target_id:
            continue
        try:
            meta = json.loads(r["metadata"] or "{}")
        except (TypeError, ValueError):
            meta = {}
        if all(meta.get(k) == v for k, v in meta_like.items()):
            out.append(r)
    return out


def change_events(db, standard_no: str) -> list[sqlite3.Row]:
    return db.execute("SELECT * FROM update_change_event WHERE standard_no=?"
                      " ORDER BY rowid", (standard_no,)).fetchall()


@pytest.fixture()
def t():
    return InspectTransport()


# ================================================================ INS-A 巡检编排
def test_ins_a_01_smoke_five_effective_done(db, t):
    """/INS-A-01 5 号全现行：pending→running→done，checked=total=5，green=5 余 0。"""
    items = [add_doc(db, "a01", i) for i in range(1, 6)]
    cfg_all(t, items, {}, channels=("web", "govcn"))
    for it in items:
        t.configure("official_gb", it["standard_no"], [r_eff(it["standard_no"])])
    batch = create_inspect_batch(tier="tier0", trigger="manual", items=mk_items(*items))
    assert batch["status"] == "pending" and batch["total"] == 5
    done = run_batch(batch["batch_id"], transport=t)
    assert done["status"] == "done" and done["finished_at"]
    assert (done["checked"], done["total"]) == (5, 5)
    assert done["green_count"] == 5
    assert done["red_count"] == done["yellow_count"] == done["gray_count"] == 0
    # ANOM-001 回归：04a §0 四色恒等式逐批断言（真实聚合路径，done 批次必兑现）
    assert (done["red_count"] + done["yellow_count"]
            + done["green_count"] + done["gray_count"]) == done["total"]
    # 镜像锚行同步（update_change_event 外键落点）
    anchor = db.execute("SELECT * FROM update_check_batch WHERE batch_id=?",
                        (batch["batch_id"],)).fetchone()
    assert anchor["status"] == "done" and anchor["green_count"] == 5
    assert (anchor["red_count"] + anchor["yellow_count"]
            + anchor["green_count"] + anchor["gray_count"]) == anchor["total"]
    # 事件全量落库且外键直查可用
    ev = db.execute("SELECT count(*) FROM update_change_event WHERE batch_id=?",
                    (batch["batch_id"],)).fetchone()[0]
    assert ev == 5


def test_ins_a_02_concurrency_two_pairwise(db, t):
    """/INS-A-02 峰值并发恒=2，按清单序两两成组推进。"""
    items = [add_doc(db, "a02", i) for i in range(1, 11)]
    # 应答带短 sleep：放大探测窗口，使并发水位可观测（否则微秒级完成测不到重叠）
    for it in items:
        no = it["standard_no"]
        t.configure("official_gb", no, [{**r_eff(no), "sleep": 0.03}])
        t.configure("web", it["standard_no"], [])
        t.configure("govcn", it["standard_no"], [])
    batch = create_inspect_batch(tier="tier0", items=mk_items(*items))
    run_batch(batch["batch_id"], transport=t)
    assert t.max_active == 2, "峰值并发必须恰为 2"
    # 统一坐标：全部用全量 calls 列表的先后位置比较
    first_start, first_end = {}, {}
    for i, c in enumerate(t.calls):
        if c["event"] == "start":
            first_start.setdefault(c["standard_no"], i)
        else:
            first_end.setdefault(c["standard_no"], i)
    seq = [it["standard_no"] for it in items]
    n1, n2, n3 = seq[0], seq[1], seq[2]
    third_at = first_start[n3]
    assert first_start[n1] < third_at and first_start[n2] < third_at
    assert first_end[n1] < third_at and first_end[n2] < third_at, \
        "第 3 号必须在 1/2 号完成后才启动（成组推进）"


def test_ins_a_03_pause_resume_monotonic(db, t):
    """/INS-A-03 running 中 pause → paused → resume 续跑，checked 单调不回退。"""
    items = [add_doc(db, "a03", i) for i in range(1, 7)]
    cfg_all(t, items, {})
    for it in items:
        t.configure("official_gb", it["standard_no"], [r_eff(it["standard_no"])])
    batch = create_inspect_batch(tier="tier0", items=mk_items(*items))
    bid = batch["batch_id"]

    def slow_then_pause(tr: InspectTransport):  # 第 4 次探测开始时请求暂停
        if len(tr.starts()) >= 4:
            request_pause(bid)

    t.hooks.append(slow_then_pause)
    t.hooks.append(lambda tr: time.sleep(0.005))  # 放大块窗口，稳定命中边界
    paused = run_batch(bid, transport=t)
    assert paused["status"] == "paused"
    checked_at_pause = paused["checked"]
    assert checked_at_pause >= 2

    t.hooks.clear()
    done = resume_batch(bid, transport=t)
    assert done["status"] == "done"
    assert done["checked"] >= checked_at_pause and done["checked"] == 6


def test_ins_a_04_resume_from_checkpoint_no_dup_events(db, t):
    """/INS-A-04 跑到 3/10 断点（模拟进程重启），resume 自第 4 号续扫且无重复事件。"""
    items = [add_doc(db, "a04", i) for i in range(1, 11)]
    cfg_all(t, items, {})
    for it in items:
        t.configure("official_gb", it["standard_no"], [r_eff(it["standard_no"])])
    batch = create_inspect_batch(tier="tier0", items=mk_items(*items))
    bid = batch["batch_id"]

    def stop_at_three(tr: InspectTransport):
        if len(tr.starts()) >= 3:
            request_pause(bid)

    t.hooks.append(stop_at_three)
    paused = run_batch(bid, transport=t, max_workers=3)
    assert paused["status"] == "paused" and paused["checked"] == 3
    ckpt = json.loads(paused["checkpoint_json"])
    queued_left = [q["standard_no"] for q in ckpt["queue"]]
    assert queued_left == [it["standard_no"] for it in items[3:]]

    # —— 进程重启语义：内存句柄已清空，仅凭 DB checkpoint 续跑 ——
    assert inspector.request_pause(bid) is False  # 无活动句柄
    t.hooks.clear()  # 摘除暂停钩子，模拟重启后无外部干预
    done = resume_batch(bid, transport=t, max_workers=3)
    assert done["status"] == "done" and done["checked"] == 10
    # 前 3 号只探测过一次（无重扫）
    for it in items[:3]:
        assert len(t.starts(it["standard_no"])) == 1
        assert len(change_events(db, it["standard_no"])) == 1, "无重复 chg_ 新增"
    # 第 4~10 号各恰一次
    for it in items[3:]:
        assert len(t.starts(it["standard_no"])) == 1


def test_ins_a_05_timeout_retry3_then_failed(db, t):
    """/INS-A-05 单号 delay31>30s：预算 3 次耗尽记 failed，不阻塞他号、不误降级；
    含未判定号的批次终态 failed（ANOM-001 回归：done⟺四色恒等式）。"""
    items = [add_doc(db, "a05", i) for i in range(1, 4)]
    slow = items[1]
    for it in items:
        t.configure("web", it["standard_no"], [])
        t.configure("govcn", it["standard_no"], [])
        t.configure("official_gb", it["standard_no"],
                    [{"delay_s": 31}] if it is slow else [r_eff(it["standard_no"])])
    batch = create_inspect_batch(tier="tier0", items=mk_items(*items))
    done = run_batch(batch["batch_id"], transport=t)
    assert done["status"] == "failed" and done["finished_at"]  # 有号未判定绝不 done
    assert done["checked"] == 3
    assert done["green_count"] == 2  # 失败号不入四色
    assert done["green_count"] + done["red_count"] + \
        done["yellow_count"] + done["gray_count"] == 2
    # 重试=3 次全部打在 official_gb，预算耗尽不降级（web/govcn 零调用）
    assert len(t.starts(slow["standard_no"], "official_gb")) == 3
    assert t.starts(slow["standard_no"], "web") == []
    fails = event_rows(db, "update/probe_failed", target_id=batch["batch_id"],
                       standard_no=slow["standard_no"])
    assert len(fails) == 1
    meta = json.loads(fails[0]["metadata"])
    assert meta["code"] == "UPD-1001" and meta["attempts"] == 3


def test_ins_a_06_resume_missing_batch_404(db):
    """/INS-A-06 不存在的 batch_id：UPD-2003 且零副作用。"""
    before = db.execute("SELECT count(*) FROM bulk_import_batch").fetchone()[0]
    with pytest.raises(UpdateError) as ei:
        resume_batch("bul_missing_a06")
    assert ei.value.code == "UPD-2003"
    after = db.execute("SELECT count(*) FROM bulk_import_batch").fetchone()[0]
    assert before == after


def test_ins_a_07_chaos_persistent_error_reaches_terminal(db, t):
    """/INS-A-07 第 2 号持续异常：终态 done+finished_at，无挂死，审计齐全。"""
    items = [add_doc(db, "a07", i) for i in range(1, 4)]
    boom = items[1]
    for it in items:
        resp = [{"raise": "Boom"}] if it is boom else [r_eff(it["standard_no"])]
        t.configure("official_gb", it["standard_no"], resp)
        t.configure("web", it["standard_no"], resp)
        t.configure("govcn", it["standard_no"], resp)
    batch = create_inspect_batch(tier="tier0", items=mk_items(*items))
    done = run_batch(batch["batch_id"], transport=t)
    assert done["status"] in ("done", "failed") and done["finished_at"]
    assert done["checked"] == 3 and done["green_count"] == 2
    assert event_rows(db, "update/probe_failed", standard_no=boom["standard_no"])
    assert event_rows(db, "update/change_detected")  # 正常号审计在
    ckpt = json.loads(done["checkpoint_json"])
    assert any(e["standard_no"] == boom["standard_no"] for e in ckpt["errors"])


def test_ins_a_08_sqlite_exception_isolated(db, t, monkeypatch):
    """/INS-A-08 中途注入一次 SQLite 异常：异常号隔离，其余照跑，批次可达 done。"""
    items = [add_doc(db, "a08", i) for i in range(1, 5)]
    victim = items[1]
    cfg_all(t, items, {})
    for it in items:
        t.configure("official_gb", it["standard_no"], [r_eff(it["standard_no"])])
    batch = create_inspect_batch(tier="tier0", items=mk_items(*items))

    orig_commit = inspector._commit_outcome
    state = {"hit": False}

    def flaky_commit(bid, tier, out):
        if out.standard_no == victim["standard_no"] and not state["hit"]:
            state["hit"] = True
            raise sqlite3.OperationalError("injected sqlite failure")
        return orig_commit(bid, tier, out)

    monkeypatch.setattr(inspector, "_commit_outcome", flaky_commit)
    done = run_batch(batch["batch_id"], transport=t)
    # 受害号被隔离后本批无判定结果 → 终态 failed（ANOM-001：done⟺恒等式，
    # 04a A-08「可达终态不挂死」语义保留，done 让位于 §0 全局不变量）
    assert done["status"] == "failed" and done["finished_at"]
    assert done["checked"] == 3 and done["green_count"] == 3  # 4 号批隔离 1 号
    assert len(change_events(db, victim["standard_no"])) == 0  # 未写脏行
    for it in items:
        if it is not victim:
            assert len(change_events(db, it["standard_no"])) == 1  # 事件未丢
    ckpt = json.loads(done["checkpoint_json"])
    assert any(e["standard_no"] == victim["standard_no"] for e in ckpt["errors"])


def test_ins_a_09_terminal_batch_refuses_restart(db, t):
    """/INS-A-09 终态批次：check/resume 拒绝重启，重复 pause 幂等返回同状态。"""
    items = [add_doc(db, "a09", i) for i in range(1, 4)]
    cfg_all(t, items, {})
    for it in items:
        t.configure("official_gb", it["standard_no"], [r_eff(it["standard_no"])])
    batch = create_inspect_batch(tier="tier0", items=mk_items(*items))
    bid = batch["batch_id"]
    done = run_batch(bid, transport=t)
    calls_before = len(t.calls)

    with pytest.raises(UpdateError) as ei:
        run_batch(bid, transport=t)
    assert ei.value.code == "UPD-3005"
    with pytest.raises(UpdateError) as ei:
        resume_batch(bid, transport=t)
    assert ei.value.code == "UPD-3005"
    again = pause_batch(bid)  # 幂等：返回同状态，无副作用
    assert again["status"] == "done" and again["checked"] == 3
    assert len(t.calls) == calls_before, "终态后零新增探测"


def test_anom001_all_channels_unreachable_failed_not_done(db, t):
    """/ANOM-001 回归：三渠道全程不可达（生产 SSL EOF 场景）→ 批次终态 failed，
    checked 含未判定号但零色桶零事件；修复前此处为 done+0+0+0+0≠total 假绿。"""
    items = [add_doc(db, "anm", i) for i in range(1, 4)]
    for it in items:  # 全渠道全异常：复现生产 UPD-1001/1004 全灭路径（含降级链耗尽）
        t.configure("official_gb", it["standard_no"], [{"raise": "Timeout"}])
        t.configure("web", it["standard_no"], [{"raise": "Timeout"}])
        t.configure("govcn", it["standard_no"], [{"raise": "Timeout"}])
    batch = create_inspect_batch(tier="tier0", items=mk_items(*items))
    done = run_batch(batch["batch_id"], transport=t)
    assert done["status"] == "failed" and done["finished_at"]
    assert done["checked"] == done["total"] == 3   # 已处理计入 checked…
    colors = (done["red_count"] + done["yellow_count"]
              + done["green_count"] + done["gray_count"])
    assert colors == 0                             # …但未判定号不入任何色桶
    # §0 全局不变量：done 必满足四色恒等式（本批存在未判定号故必为 failed）
    if done["status"] == "done":
        assert colors == done["total"], "done 批次违反四色恒等式"
    # 锚行镜像一致 + 审计齐全：逐号 probe_failed、update_change_event 零写入
    anchor = db.execute("SELECT * FROM update_check_batch WHERE batch_id=?",
                        (batch["batch_id"],)).fetchone()
    assert anchor["status"] == "failed" and anchor["checked"] == 3
    for it in items:
        fails = event_rows(db, "update/probe_failed",
                           target_id=batch["batch_id"],
                           standard_no=it["standard_no"])
        assert len(fails) == 1 and json.loads(fails[0]["metadata"])["attempts"] == 3
    assert db.execute("SELECT count(*) FROM update_change_event WHERE batch_id=?",
                      (batch["batch_id"],)).fetchone()[0] == 0
    ckpt = json.loads(done["checkpoint_json"])
    assert len(ckpt["errors"]) == 3 and ckpt["pause_reason"] is None


# ================================================================ INS-C 验证码半自动
def _captcha_scene(db, t, n_docs: int, captcha_idx: list[int],
                   prefix: str = "cap"):
    items = [add_doc(db, prefix, i) for i in range(1, n_docs + 1)]
    for i, it in enumerate(items, start=1):
        resp = R_CAPTCHA if i in captcha_idx else r_eff(it["standard_no"])
        t.configure("official_gb", it["standard_no"], [resp])
        t.configure("web", it["standard_no"], [])
        t.configure("govcn", it["standard_no"], [])
    return items, create_inspect_batch(tier="tier0",
                                       items=mk_items(*items))


def test_ins_c_01_captcha_pauses_not_gray(db, t):
    """/INS-C-01 captcha=true：批次 paused、该号不计 gray/failed、聚合告警落库。"""
    items, batch = _captcha_scene(db, t, 3, captcha_idx=[2], prefix="c01")
    done = run_batch(batch["batch_id"], transport=t)
    assert done["status"] == "paused"
    ckpt = json.loads(done["checkpoint_json"])
    assert ckpt["pause_reason"] == "captcha"
    assert ckpt["queue"][0]["standard_no"] == items[1]["standard_no"]
    assert done["checked"] == 1 and done["green_count"] == 1
    assert done["gray_count"] == 0  # 不误记 gray/failed
    assert len(change_events(db, items[1]["standard_no"])) == 0  # 不写事件
    waits = event_rows(db, "update/captcha_wait", target_id=batch["batch_id"])
    assert len(waits) == 1
    meta = json.loads(waits[0]["metadata"])
    assert meta["code"] == "UPD-1002"
    assert meta["standard_nos"] == [items[1]["standard_no"]]
    assert "验证码" in meta["message"]


def test_ins_c_02_resume_retries_same_number_first(db, t):
    """/INS-C-02 过点后 resume：同一号优先补查成功，批次续跑至 done。"""
    items, batch = _captcha_scene(db, t, 3, captcha_idx=[2], prefix="c02")
    bid = batch["batch_id"]
    paused = run_batch(bid, transport=t)
    assert paused["status"] == "paused"
    boundary = len(t.calls)  # 第一轮结束位置（resume 前采样）
    t.configure("official_gb", items[1]["standard_no"],
                [r_eff(items[1]["standard_no"])])  # 模拟用户已过点
    done = resume_batch(bid, transport=t)
    assert done["status"] == "done" and done["checked"] == 3
    assert done["green_count"] == 3
    # 补查顺序：恢复后首个探测即挂起号
    first_after = next(c for c in t.calls[boundary:] if c["event"] == "start")
    assert first_after["standard_no"] == items[1]["standard_no"]
    assert len(event_rows(db, "update/captcha_wait",
                          target_id=bid)) == 1  # 未新增告警


def test_ins_c_03_scheduler_never_auto_resumes_captcha(db, t):
    """/INS-C-03 paused 批次等一个调度周期：定时器不得自动 resume 验证码/人工暂停。"""
    items, batch = _captcha_scene(db, t, 1, captcha_idx=[1], prefix="c03")
    paused = run_batch(batch["batch_id"], transport=t)
    assert paused["status"] == "paused"
    # 人工暂停批次同样不可被调度器碰
    user_items = [add_doc(db, "c03u", 1)]
    ub = create_inspect_batch(tier="tier0", items=mk_items(*user_items))
    pause_batch(ub["batch_id"])

    sched = UpdateScheduler(resume_kwargs={"transport": t})
    actions = sched.tick(now=T0 + timedelta(days=9))
    assert actions["resumed"] == []
    assert get_inspect_batch(batch["batch_id"])["status"] == "paused"
    assert get_inspect_batch(ub["batch_id"])["status"] == "paused"


def test_ins_c_04_three_captchas_one_aggregated_pause(db, t):
    """/INS-C-04 连续 3 号验证码：合并单次暂停一条告警；resume 后逐号补查不漏。"""
    items = [add_doc(db, "c04", i) for i in range(1, 5)]
    for i, it in enumerate(items, start=1):
        resp = R_CAPTCHA if i <= 3 else r_eff(it["standard_no"])
        t.configure("official_gb", it["standard_no"], [resp])
        t.configure("web", it["standard_no"], [])
        t.configure("govcn", it["standard_no"], [])
    batch = create_inspect_batch(tier="tier0", items=mk_items(*items))
    paused = run_batch(batch["batch_id"], transport=t, max_workers=3)
    assert paused["status"] == "paused"
    waits = event_rows(db, "update/captcha_wait", target_id=batch["batch_id"])
    assert len(waits) == 1, "三个验证码号合并为一条聚合提示"
    meta = json.loads(waits[0]["metadata"])
    assert sorted(meta["standard_nos"]) == sorted(
        it["standard_no"] for it in items[:3])

    for it in items:  # 过点：全部放行正常应答
        t.configure("official_gb", it["standard_no"], [r_eff(it["standard_no"])])
    done = resume_batch(batch["batch_id"], transport=t)
    assert done["status"] == "done" and done["green_count"] == 4
    for it in items:  # 逐号补查，一个不漏
        assert len(t.starts(it["standard_no"], "official_gb")) >= 1


def test_ins_c_05_interleaved_pause_resume_state_machine(db, t):
    """/INS-C-05 交错 pause×2 / resume×2：无非法迁移，resume 生效一次不重复扫描。"""
    items, batch = _captcha_scene(db, t, 2, captcha_idx=[], prefix="c05")
    bid = batch["batch_id"]
    p1 = pause_batch(bid)   # pending → paused
    p2 = pause_batch(bid)   # 重复 pause 幂等同状态
    assert p1["status"] == p2["status"] == "paused"
    done = resume_batch(bid, transport=t)      # 生效一次
    with pytest.raises(UpdateError) as ei:     # 第二次 resume：终态拒绝重启
        resume_batch(bid, transport=t)
    assert ei.value.code == "UPD-3005"
    assert done["status"] == "done" and done["checked"] == 2
    assert len(t.starts()) == 2, "扫描恰好执行一轮"


# ================================================================ INS-D 三色判定映射
def test_ins_d_01_effective_green(db, t):
    """/INS-D-01 现行 → green，current_legal_status='effective' 落库。"""
    it = add_doc(db, "d01", 1)
    no = it["standard_no"]
    t.configure("official_gb", no, [r_eff(no)])
    t.configure("web", no, [])
    t.configure("govcn", no, [])
    done = run_batch(create_inspect_batch(tier="tier0", items=mk_items(it))["batch_id"],
                     transport=t)
    assert (done["green_count"], done["checked"]) == (1, 1)
    ev = change_events(db, no)[0]
    assert ev["change_type"] == "no_change"
    assert ev["current_legal_status"] == "effective"
    assert ev["source_channel"] == "official_gb"


def test_ins_d_02_upcoming_treated_current(db, t):
    """/INS-D-02 upcoming 有新版：legal_status 如实 'upcoming'，不触废止对比流程；
    色按批次2指令「新版→yellow」（04a §4 的 🟢 口径以指令为准让位）。"""
    it = add_doc(db, "d02", 1)
    no = it["standard_no"]
    t.configure("official_gb", no, [r_upcoming(no)])
    t.configure("web", no, [])
    t.configure("govcn", no, [])
    done = run_batch(create_inspect_batch(tier="tier0", items=mk_items(it))["batch_id"],
                     transport=t)
    ev = change_events(db, no)[0]
    assert ev["change_type"] == "new_version"
    assert ev["current_legal_status"] == "upcoming"
    assert done["yellow_count"] == 1 and done["red_count"] == 0
    assert json.loads(ev["latest_info_json"])["version"] == bump_year(no, "2026")


def test_ins_d_03_superseded_red_per_directive(db, t):
    """/INS-D-03 被代替(superseded) → 红（批次2指令：废止/替代→red；
    04a §4 头注 🟡 口径已被批次2指令取代）。change_type=superseded。"""
    it = add_doc(db, "d03", 1)
    no = it["standard_no"]
    t.configure("official_gb", no, [r_state(no, "被代替")])
    t.configure("web", no, [])
    t.configure("govcn", no, [])
    done = run_batch(create_inspect_batch(tier="tier0", items=mk_items(it))["batch_id"],
                     transport=t)
    ev = change_events(db, no)[0]
    assert ev["change_type"] == "superseded"
    assert ev["current_legal_status"] == "superseded"
    assert done["red_count"] == 1 and done["yellow_count"] == 0


def test_ins_d_04_withdrawn_red(db, t):
    """/INS-D-04 废止 → red + change_type=withdrawn。"""
    it = add_doc(db, "d04", 1)
    no = it["standard_no"]
    t.configure("official_gb", no, [r_state(no, "废止")])
    t.configure("web", no, [])
    t.configure("govcn", no, [])
    done = run_batch(create_inspect_batch(tier="tier0", items=mk_items(it))["batch_id"],
                     transport=t)
    ev = change_events(db, no)[0]
    assert done["red_count"] == 1
    assert ev["change_type"] == "withdrawn" and ev["current_legal_status"] == "withdrawn"


def test_四棒链的最后一棒不被预算截断(db):
    """§11.0 R6c-3e：**链长 4 > MAX_ATTEMPTS(3) 时最后一棒以前永远探不到**（复核 b34 实测）。

    背景：R6c-3b 把 `ndls` 插进兜底链后，`mee`/`dbba`/`hbba`/`ttbz` 四族的链长变成 4；
    而 `_probe_number` 的尝试预算写的是 `attempts_left = MAX_ATTEMPTS`（3），它同时充当
    "重试预算"与"能试几根棒" ⇒ **第 4 根（govcn）从来没被执行过**
    （复核的 A/B：旧链 probed=[mee,official_gb,govcn]，新链 probed=[mee,official_gb,ndls]）。
    真库 6417 行的链长今天全是 3 ⇒ 0 行受影响，但那是**潜伏回归**。
    修法：预算取 `max(MAX_ATTEMPTS, len(可用链))` —— 链的意义就是把棒都试一遍。
    """
    from src.core.update import inspector as insp
    from src.core.update.channels.base import ChannelResult
    from src.core.update.channels.routing import select_chain

    class _MissAdapter:
        def __init__(self, name: str) -> None:
            self.name = name
            self.calls = 0

        def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
            self.calls += 1
            return ChannelResult(channel=self.name, found=False)   # 干净未命中

    no = "HJ 1234-2020"
    chain = select_chain(no)
    assert len(chain) == 4, chain          # 这条用例的前提就是"四棒"
    adapters = {c: _MissAdapter(c) for c in chain}
    out = insp._probe_number(adapters, {"standard_no": no, "standard_name": "生态标准"})
    assert [adapters[c].calls for c in chain] == [1, 1, 1, 1], \
        f"链 {chain} 里有一根没被探到：{[adapters[c].calls for c in chain]}"
    assert out.kind == "judged" and out.change_type == "not_found"


def test_单根链的重试预算不变(db):
    """改预算是 `max(MAX_ATTEMPTS, len(链))` ⇒ **短链行为一字不变**（单根链仍有 3 次预算）。

    这条防的是"为了修长链把重试语义改了"：INS-A-05 的口径是"按重试=3 次后记 failed"。
    """
    from src.core.update import inspector as insp
    from src.core.update.channels.base import ChannelResult, UpdateError

    class _BoomAdapter:
        def __init__(self, name: str) -> None:
            self.name = name
            self.calls = 0

        def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
            self.calls += 1
            raise UpdateError("渠道炸了", code="UPD-9999")

    ad = _BoomAdapter("official_gb")
    out = insp._probe_number({"official_gb": ad},
                             {"standard_no": "XYZ 1-2020", "standard_name": "x"})
    assert ad.calls == insp.MAX_ATTEMPTS, ad.calls
    assert out.kind == "failed"


def test_某根棒抛异常不挤掉后面的棒(db):
    """§11.0 R6c-3f（复核 b36 的 D-新问题）：**全链共享重试池**会让异常吃掉后面的棒。

    复核实测过的旧行为：第 1 根抛 1 次 ⇒ `[2,1,1,0]`，第 4 根从没被问过，
    **却照样返回 not_found/gray** ——把"没问"当成"没有"。

    本步两端一起改：预算 ≥ 链长（无异常时每根都问到）**且**"没问完就不下 not_found 结论"。
    这条用例钉住的是后半段：抛 1 次异常会多吃 1 次预算 ⇒ 4 根问不完 ⇒ 结果是 **failed**
    （而不是 not_found），并且**如实说出问到了几根**。
    """
    from src.core.update import inspector as insp
    from src.core.update.channels.base import ChannelResult, UpdateError
    from src.core.update.channels.routing import select_chain

    class _FlakyAdapter:
        """第 1 次抛异常、之后干净未命中（模拟一次瞬时故障）。"""

        def __init__(self, name: str) -> None:
            self.name = name
            self.calls = 0

        def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
            self.calls += 1
            if self.calls == 1:
                raise UpdateError("瞬时故障", code="UPD-9999")
            return ChannelResult(channel=self.name, found=False)

    no = "HJ 1234-2020"
    chain = select_chain(no)
    adapters = {c: _FlakyAdapter(c) for c in chain}
    out = insp._probe_number(adapters, {"standard_no": no, "standard_name": "x"})
    calls = [adapters[c].calls for c in chain]
    assert calls[0] == 2, calls                  # 第 1 根：抛 1 次 + 未命中 1 次（共吃 2 次预算）
    assert out.kind == "failed", out             # ⚠ **不是 not_found**：后面还有棒没问
    assert out.change_type is None
    assert "没问完" in (out.error_msg or ""), out.error_msg
    assert sum(calls) == 4                       # 预算用光（4）就停，不越界多打


def test_全链都抛异常才算failed(db):
    """每根棒各自重试到上限；全链都抛 ⇒ 没有"干净未命中" ⇒ hard-fail（不是 not_found）。"""
    from src.core.update import inspector as insp
    from src.core.update.channels.base import ChannelResult, UpdateError

    class _Boom:
        def __init__(self, name: str) -> None:
            self.name = name
            self.calls = 0

        def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
            self.calls += 1
            raise UpdateError("一直炸", code="UPD-9999")

    no = "HJ 1234-2020"
    ad = _Boom("mee")
    out = insp._probe_number({"mee": ad}, {"standard_no": no, "standard_name": "x"})
    assert ad.calls == insp.MAX_ATTEMPTS
    assert out.kind == "failed"


def test_五类结论记进同一条事件(db, t):
    """§11.0 R6c-4c：**五类结论记进那一条事件的 `latest_info`**（不新增列、不写 ×5 条）。

    为什么不是"每类一条事件"：`update_change_event.change_type` 有 CHECK 约束（只 5 个值），
    去重键是 `(doc_id, standard_no, change_type)` ⇒ 五类里同为 `no_change` 的会被压成一条、
    类的信息静默丢失；`latest_info` 是免费文本，五类结论放这里既不撞约束也不 ×5 事件量
    （设计与量测见 `docs/CHANNEL-R6C-DESIGN.md` §3.2.2）。
    """
    it = add_doc(db, "r6c4", 1)
    no = it["standard_no"]
    t.configure("official_gb", no, [r_eff(no)])
    run_batch(create_inspect_batch(tier="tier0", items=mk_items(it))["batch_id"],
              transport=t)
    ev = change_events(db, no)[0]
    info = json.loads(ev["latest_info_json"])
    classes = info.get("classes")
    assert classes is not None, info
    assert set(classes) == {"发布", "修订", "废止", "现行性", "编号核验"}
    # official_gb 命中并给了"现行" ⇒ 现行性与废止/修订都答得了（否定结论也是结论）
    assert classes["现行性"]["status"] == "answered"
    assert classes["现行性"]["conclusion"] == {"state": "effective"}
    assert classes["废止"]["status"] == "answered"
    assert classes["废止"]["channel"] == "ch:official_gb"
    # b35 的判定如实带出（official_gb 的废止只有状态串、没有废止日期 ⇒ partial）
    assert classes["废止"]["completeness"] == "partial"
    # ⚠ mock 契约里**没有发布日期字段**（只有 `date`）⇒「发布」这一类它给不了东西：
    # 记 `channel_gave_no_field` 并进 `unanswered`（**不是**"没答"被吞掉，也不是拿实施日期顶）。
    assert classes["发布"]["status"] == "not_answered"
    assert classes["发布"]["reason"] == "channel_gave_no_field"
    assert info["classes_unanswered"] == ["发布"]


def test_灰号的五类记录说清为什么没答(db, t):
    """整链都没命中（灰）也要能回答"五类各自为什么没答"（§11.0 R6c-4c）。"""
    it = add_doc(db, "r6c4b", 1)
    no = it["standard_no"]
    for ch in ("official_gb", "ndls", "govcn"):
        t.configure(ch, no, [R_MISS])
    run_batch(create_inspect_batch(tier="tier0", items=mk_items(it))["batch_id"],
              transport=t)
    ev = change_events(db, no)[0]
    assert ev["change_type"] == "not_found"
    classes = json.loads(ev["latest_info_json"]).get("classes")
    assert classes is not None
    # 灰号：五类都没答；链上**有**能答的棒 ⇒ 记 not_probed（"没问出来"），不是结构性缺口
    assert all(v["status"] == "not_answered" for v in classes.values())
    assert classes["废止"]["reason"] == "not_probed"


def test_ins_d_05_all_channels_miss_gray(db, t):
    """/INS-D-05 三渠道查无 → gray，legal_status 保持 NULL，末渠道 govcn 兜底。"""
    it = add_doc(db, "d05", 1)
    no = it["standard_no"]
    t.configure("official_gb", no, [R_MISS])
    t.configure("web", no, [{"http": 200, "body": {"results": []}}])
    t.configure("govcn", no, [{"http": 200, "body": {"announcements": []}}])
    done = run_batch(create_inspect_batch(tier="tier0", items=mk_items(it))["batch_id"],
                      transport=t)
    ev = change_events(db, no)[0]
    assert done["gray_count"] == 1
    assert ev["change_type"] == "not_found"
    assert ev["current_legal_status"] is None
    assert ev["source_channel"] == "govcn"


def test_ins_d_06_illegal_enum_rejected_not_silent(db, t):
    """/INS-D-06 非法枚举：CHECK 拒绝+回滚零脏行；未知状态串转告警不猜测。"""
    import pytest as _pytest
    db.execute("INSERT INTO update_check_batch(batch_id) VALUES('upd_d06')")
    with _pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO update_change_event(change_id, batch_id,"
                   " standard_no, change_type, current_legal_status, source_channel)"
                   " VALUES('chg_d06_bad','upd_d06','GB X-2020','no_change',"
                   "'draft','official_gb')")
    left = db.execute("SELECT count(*) FROM update_change_event"
                      " WHERE change_id='chg_d06_bad'").fetchone()[0]
    assert left == 0
    # 编排层：官方返回非法状态串 draft → 渠道层告警、legal_status=NULL 落库（不猜测）
    it = add_doc(db, "d06b", 1)
    no = it["standard_no"]
    t.configure("official_gb", no, [r_state(no, "draft")])
    t.configure("web", no, [])
    t.configure("govcn", no, [])
    run_batch(create_inspect_batch(tier="tier0", items=mk_items(it))["batch_id"],
              transport=t)
    ev = change_events(db, no)[0]
    assert ev["current_legal_status"] is None
    assert ev["change_type"] == "no_change"  # 版本一致按现行对待，未静默丢弃


def test_ins_d_07_replay_dedup_counts_not_doubled(db, t):
    """/INS-D-07 相同 mock 序列重放判定：跨批同 doc 同结论跳过建行，计数不翻倍。"""
    items = [add_doc(db, "d07", i) for i in range(1, 4)]
    cfg_all(t, items, {})
    for it in items:
        t.configure("official_gb", it["standard_no"], [r_eff(it["standard_no"])])
    b1 = run_batch(create_inspect_batch(tier="tier0",
                                        items=mk_items(*items))["batch_id"],
                   transport=t)
    assert b1["green_count"] == 3
    total_ev = db.execute("SELECT count(*) FROM update_change_event").fetchone()[0]
    b2 = run_batch(create_inspect_batch(tier="tier0",
                                        items=mk_items(*items))["batch_id"],
                   transport=t)
    assert b2["status"] == "done" and b2["green_count"] == 3  # 四色计数不翻倍
    total_after = db.execute("SELECT count(*) FROM update_change_event").fetchone()[0]
    assert total_after == total_ev, "同 doc 同 change_type 重放不得新增 chg_ 行"


def test_ins_d_08_mixed_twenty_identity(db, t):
    """/INS-D-08 20 号混合四态：恒等式成立，已知样本判定全部正确。"""
    plan = (["effective"] * 8 + ["new_version"] * 4 + ["superseded"] * 4
            + ["withdrawn"] * 2 + ["not_found"] * 2)
    order = (0, 8, 16, 4, 12, 18, 2, 10, 14, 6, 19, 1, 9, 17, 5, 13, 3, 11, 15, 7)
    kinds = [plan[i] for i in order]  # 固定确定性乱序
    items = [add_doc(db, "d08", i + 1) for i in range(20)]
    for it, kind in zip(items, kinds):
        no = it["standard_no"]
        if kind == "effective":
            resp = r_eff(no)
        elif kind == "new_version":
            resp = r_upcoming(no)
        elif kind == "superseded":
            resp = r_state(no, "被代替")
        elif kind == "withdrawn":
            resp = r_state(no, "废止")
        else:
            resp = R_MISS
        t.configure("official_gb", no, [resp])
        t.configure("web", no, [])
        t.configure("govcn", no, [])
    batch = create_inspect_batch(tier="tier0", items=mk_items(*items))
    done = run_batch(batch["batch_id"], transport=t)
    colors = (done["red_count"] + done["yellow_count"]
              + done["green_count"] + done["gray_count"])
    assert colors == done["total"] == 20, "四色恒等式"
    assert (done["green_count"], done["yellow_count"], done["red_count"],
            done["gray_count"]) == (8, 4, 6, 2)
    # 抽验 ≥3 个已知样本
    by_kind = {}
    for it, kind in zip(items, kinds):
        by_kind.setdefault(kind, []).append(it)
    ev = change_events(db, by_kind["effective"][0]["standard_no"])[0]
    assert ev["change_type"] == "no_change"
    ev = change_events(db, by_kind["superseded"][0]["standard_no"])[0]
    assert ev["change_type"] == "superseded"
    ev = change_events(db, by_kind["not_found"][0]["standard_no"])[0]
    assert ev["change_type"] == "not_found"


def test_retry_within_channel_before_degrade(db, t):
    """/INS-B-06 编排层复核：前 2 次异常第 3 次命中 → 不提前降级仍由 official_gb 完成。"""
    it = add_doc(db, "b06", 1)
    no = it["standard_no"]
    t.configure("official_gb", no, [{"raise": "Timeout"}, {"raise": "Timeout"},
                                    r_eff(no)])
    t.configure("web", no, [])
    t.configure("govcn", no, [])
    done = run_batch(create_inspect_batch(tier="tier0", items=mk_items(it))["batch_id"],
                     transport=t)
    assert done["green_count"] == 1
    ev = change_events(db, no)[0]
    assert ev["source_channel"] == "official_gb"
    assert t.starts(no, "web") == []


# ================================================================ 分层与万级预算
def test_tier_selection_watch_and_first_check(db):
    """tier0 = watch_list ∪ 未首检；tier1 = 其余滚动。"""
    w = add_doc(db, "tieW", 1, watch=True)
    f = add_doc(db, "tief", 2)
    i1 = add_doc(db, "tiei", 3)
    n = add_doc(db, "tien", 4)
    seed_inspected(db, i1)
    seed_inspected(db, n)
    tier0 = {r["standard_no"] for r in select_standard_nos("tier0")}
    tier1 = {r["standard_no"] for r in select_standard_nos("tier1")}
    assert {w["standard_no"], f["standard_no"]} <= tier0
    assert {i1["standard_no"], n["standard_no"]} <= tier1
    assert not ({w["standard_no"], f["standard_no"]} & tier1)


def test_tier_selection_doc_bookmark(db):
    """增强③遗留（B 方案）：user_doc_bookmark（标准收藏）并入 tier0 高频巡检；
    已首检的收藏标准不再落入 tier1 滚动层。纯书签域独立于 watch_list。"""
    bm = add_doc(db, "tieb", 1, doc_bookmark=True)   # 已收藏
    bmw = add_doc(db, "tieb", 2, watch=True)          # watch_list 对照
    both = add_doc(db, "tieb", 3, watch=True, doc_bookmark=True)
    plain = add_doc(db, "tieb", 4)                    # 未收藏未 watch
    for it in (bm, bmw, both, plain):
        seed_inspected(db, it)  # 全部"已首检"——收藏/关注是进 tier0 的唯一理由
    tier0 = {r["standard_no"] for r in select_standard_nos("tier0")}
    tier1 = {r["standard_no"] for r in select_standard_nos("tier1")}
    # 已首检的收藏/关注标准 → tier0
    assert bm["standard_no"] in tier0, "标准收藏应入 tier0"
    assert bmw["standard_no"] in tier0
    assert both["standard_no"] in tier0
    # 同时被 tier1 排除（不重复滚动）
    assert not ({bm["standard_no"], bmw["standard_no"], both["standard_no"]} & tier1)
    # 无收藏无关注的已首检标准 → 仅 tier1
    assert plain["standard_no"] in tier1
    assert plain["standard_no"] not in tier0
    # 取消收藏（删除 user_doc_bookmark 行）→ 回 tier1（已首检）
    db.execute("DELETE FROM user_doc_bookmark WHERE doc_id=?", (bm["doc_id"],))
    tier0b = {r["standard_no"] for r in select_standard_nos("tier0")}
    tier1b = {r["standard_no"] for r in select_standard_nos("tier1")}
    assert bm["standard_no"] not in tier0b
    assert bm["standard_no"] in tier1b


def test_budget_override_stop_and_next_day_resume(db, t, monkeypatch):
    """万级预算：覆盖值=3，当日达预算停留待次日，次日调度器恢复续跑。"""
    inspector.set_config("inspect.daily_full_sweep_budget", "3")
    inspector.set_config("inspect.budget_date", inspector._today())
    inspector.set_config("inspect.budget_used", "0")
    items = [add_doc(db, "bud", i) for i in range(1, 6)]
    for it in items:
        seed_inspected(db, it)  # 归 tier1（滚动层）
        t.configure("official_gb", it["standard_no"], [r_eff(it["standard_no"])])
        t.configure("web", it["standard_no"], [])
        t.configure("govcn", it["standard_no"], [])
    batch = create_inspect_batch(tier="tier1", items=mk_items(*items))
    paused = run_batch(batch["batch_id"], transport=t)
    assert paused["status"] == "paused"
    ckpt = json.loads(paused["checkpoint_json"])
    assert ckpt["pause_reason"] == "budget"
    assert paused["checked"] == 3 and len(ckpt["queue"]) == 2
    assert inspector.budget_used_today() == 3
    assert inspector.budget_remaining() == 0
    # 当日立即 resume：额度仍为 0 → 原地停留
    again = resume_batch(batch["batch_id"], transport=t)
    assert again["status"] == "paused"
    assert again["checked"] == 3

    # —— 次日：日期翻转清零额度，调度器自动恢复续跑至 done ——
    tomorrow = (datetime.strptime(inspector._today(), "%Y-%m-%d")
                + timedelta(days=1)).strftime("%Y-%m-%d")
    monkeypatch.setattr(inspector, "_today", lambda: tomorrow)
    sched = UpdateScheduler(resume_kwargs={"transport": t})
    actions = sched.tick(now=T0 + timedelta(days=40))
    assert batch["batch_id"] in actions["resumed"]
    done = get_inspect_batch(batch["batch_id"])
    assert done["status"] == "done" and done["checked"] == 5
    assert inspector.budget_used_today() == 2  # 新一天重新计账


def test_budget_default_500_when_unconfigured(db):
    """默认 daily_full_sweep_budget=500（35k ÷ 500 ≈ 70 天一轮）。"""
    db.execute("DELETE FROM app_config WHERE config_key='inspect.daily_full_sweep_budget'")
    db.commit()
    assert inspector.daily_budget_limit() == 500
    inspector.set_config("inspect.daily_full_sweep_budget", "800")
    assert inspector.daily_budget_limit() == 800
    inspector.set_config("inspect.daily_full_sweep_budget", "oops")
    assert inspector.daily_budget_limit() == 500  # 非法值回退默认
    db.execute("DELETE FROM app_config WHERE config_key='inspect.daily_full_sweep_budget'")
    db.commit()


# ================================================================ 调度器
def _make_iso(dt: datetime) -> str:
    """与 sqlite `datetime('now')` 同形的 UTC 串（`YYYY-MM-DD HH:MM:SS`）。

    必须同形：被测代码用 `scheduler._parse_created_at` 以
    `strptime(..., "%Y-%m-%d %H:%M:%S")` 解析；ISO 的 `T`/`+00:00` 会解析失败 → None。
    """
    return dt.astimezone(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


def _backdate_all_scheduled(db, days: int = 30):
    """把 scheduled 批次回拨到「**测试自己的现在（T0）**」之前。

    ⚠ 2026-09-16 修复时间炸弹（**不是被测代码缺陷**）：
    旧实现回拨的是**相对挂钟**的 `datetime('now','-30 days')`，而本文件的 `T0`
    是**硬编码固定日期** `2026-08-24 12:00Z`。两者之差随真实时间一天天变小，
    到 **today > T0 + 23 天**（即 2026-09-16 12:00Z 起）时：

        (T0 - last) = (T0 - today) + 30d  <  7d 阈值

    → `_create_scheduled_batches` 判定"周期未到" → `created=[]` → 断言红。
    即该用例**必然会在某一天自行变红**，与任何代码改动无关
    （已用 `git stash` 在 HEAD 上复现 2 红确认）。

    修法：回拨锚到 **T0**，使 `(T0 - last)` 恒为 `days`，与挂钟彻底解耦。
    """
    stamp = _make_iso(T0 - timedelta(days=days))
    db.execute("UPDATE bulk_import_batch SET created_at=?"
               " WHERE trigger_type='scheduled'", (stamp,))
    db.execute("UPDATE update_check_batch SET created_at=?"
               " WHERE trigger_type='scheduled'", (stamp,))


def test_scheduler_creates_due_batches_once(db):
    """schedule_days 到期自动建批（scheduled），周期内不重复建。"""
    _backdate_all_scheduled(db)
    inspector.set_config("update.schedule_days", "7")
    sched = UpdateScheduler()
    first = sched.tick(now=T0)
    assert len(first["created"]) == 2  # 默认双层 tier0+tier1
    rows = [get_inspect_batch(b) for b in first["created"]]
    assert {r["tier"] for r in rows} == {"tier0", "tier1"}
    assert all(r["trigger_type"] == "scheduled" for r in rows)
    assert db.execute(
        "SELECT count(*) FROM bulk_import_batch WHERE batch_kind='inspect'"
        " AND trigger_type='scheduled'").fetchone()[0] >= 2
    second = sched.tick(now=T0 + timedelta(hours=1))
    assert second["created"] == [], "周期内不得重复建批"


def test_scheduler_backdated_due_again(db):
    """距上次 scheduled 建 ≥N 天再次到期。"""
    _backdate_all_scheduled(db)
    inspector.set_config("update.schedule_days", "7")
    sched = UpdateScheduler()
    acts = sched.tick(now=T0)
    assert len(acts["created"]) == 2
    # 把刚建的批回拨 8 天（锚 T0，同样与挂钟解耦）→ 再 tick 应再建
    db.execute("UPDATE bulk_import_batch SET created_at=?"
               " WHERE trigger_type='scheduled'", (_make_iso(T0 - timedelta(days=8)),))
    acts2 = sched.tick(now=T0 + timedelta(days=40))
    assert len(acts2["created"]) == 2
    assert not set(acts2["created"]) & set(acts["created"])


def test_scheduler_disabled_when_zero(db):
    """schedule_days≤0 视为关闭调度。"""
    _backdate_all_scheduled(db)
    inspector.set_config("update.schedule_days", "0")
    acts = UpdateScheduler().tick(now=T0)
    assert acts["created"] == [] and acts["resumed"] == []


def test_scheduler_thread_lifecycle(db):
    """轮询线程 start/stop 存活冒烟（2s 模式，测试用 50ms 加速）。"""
    inspector.set_config("update.schedule_days", "0")
    sched = UpdateScheduler(poll_interval=0.05)
    sched.start()
    time.sleep(0.2)
    sched.stop()
    assert sched._thread is None


def test_tier0_includes_subscribed_domain_docs(db):
    """F-13/A15：订阅'消防'后，已首检的消防域标准被重新提入 tier0；化工域不进。"""
    from src.core.update import inspector
    from src.core.update import subscriptions

    def _ins(doc_id: str, no: str, name: str, tags_json: str) -> dict:
        db.execute(
            "INSERT INTO doc_meta(doc_id, standard_no, standard_name, short_code,"
            " current_revision_id, domain_tags, file_path, file_hash)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (doc_id, no, name, "S" + doc_id[-1], "r1", tags_json,
             f"{doc_id}.pdf", "h" + doc_id[-1]))
        item = {"doc_id": doc_id, "standard_no": no, "standard_name": name}
        seed_inspected(db, item)  # 已首检 → 默认归 tier1，隔离订阅效果
        return item

    fire = _ins("doc_sub1", "GB/T SUB 0001-2020", "消防标准", '["消防"]')
    chem = _ins("doc_sub2", "GB/T SUB 0002-2020", "化工标准", '["化工"]')

    # 基线（显式空订阅=全关）：两者都不在 tier0（已首检、非 watch、无订阅）
    subscriptions.set_subscriptions([])
    ids0 = {d["doc_id"] for d in inspector.select_standard_nos("tier0")}
    assert fire["doc_id"] not in ids0 and chem["doc_id"] not in ids0

    subscriptions.set_subscriptions(["消防"])
    try:
        ids1 = {d["doc_id"] for d in inspector.select_standard_nos("tier0")}
        assert fire["doc_id"] in ids1
        assert chem["doc_id"] not in ids1
    finally:
        subscriptions.set_subscriptions(list(subscriptions.DOMAIN_VOCAB))  # 复原全开


def test_inspect_lists_exclude_laws(db):
    """法规（doc_type='法律法规'）不进查号巡检（无国标号，时效走 flk 溯源检查）。"""
    from src.core.update import inspector

    db.execute(
        "INSERT INTO doc_meta(doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash, doc_type)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        ("doc_law_x", "消防法(2021修正全本)", "消防法", "XF", "r1", '["消防","法律"]',
         "doc_law_x.pdf", "hlaw", "法律法规"))
    # 未首检 → 若不过滤会进 tier0
    for tier in ("tier0", "tier1"):
        ids = {d["doc_id"] for d in inspector.select_standard_nos(tier)}
        assert "doc_law_x" not in ids, f"{tier} 不应包含法规"
    # 领域订阅"消防"也不得把法规提入 tier0
    from src.core.update import subscriptions
    subscriptions.set_subscriptions(["消防"])
    try:
        ids = {d["doc_id"] for d in inspector.select_standard_nos("tier0")}
        assert "doc_law_x" not in ids
    finally:
        subscriptions.set_subscriptions(list(subscriptions.DOMAIN_VOCAB))
