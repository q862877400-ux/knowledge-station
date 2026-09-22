# -*- coding: utf-8 -*-
"""CCS 三层链 + 查询台账 + 「补全分类号」自愈机制（2026-09-22 业主口径「修机制不是补数据」）。

## 这组用例在守什么（每一类都配了**反向**用例）

1. **链的顺序与来源**：① 官方接口 → ② 网页抓取 → ③ 本地兜底。命中必须说清是**哪一层**、
   哪种**关键词形式**；**反向**：官方那一层答上了就**不许**再去抓网页（`scrape_calls == 0`）——
   否则"来源 = 官方接口"这句话就是假的。
2. **关键词形式**：完整号 → 去空格变体 → 数字主体（含分部号）→ 数字首段；不许只试一种。
3. **失败必须分类，不许混**：「发不出去」不许说成「官方查无」。三条互斥结论
   `network_failed` / `not_found` / `parse_failed` 各有一条用例，且都断言**不是**另一个。
4. **网页抓取的块边界锚在标准号上**（旧实现锚在**标题**上 ⇒ 20 条一条都挑不中，
   真机取证见 `ccs_fetcher` 模块头第 3 条）—— 这条是回归哨兵。
5. **入库那条路留痕**：真跑一次入库 ⇒ `doc_ccs_state` 真有这一行；**反向**：把三层全掐掉
   ⇒ 台账**如实**记 `not_found`/`network_failed`，**不是**"什么都没有"（旧实现是静默 None）。
6. **自愈机制真的落库**：「补全分类号」跑完 ⇒ `doc_meta.domain_tags` 里**真的多了一条**
   `CCS:…`（**反向哨兵**见 `test_backfill_writes_through_to_db` 的断言：只改内存的话它必红）。
7. **幂等 / 可重跑 / 可中断 / 失败清单**：重跑一遍 = 0 篇；按停之后 `cancelled` 如实；
   没补到的逐篇进 `failures`（不合并成一句"部分失败"）。
8. **接口外形**：`/kb/ccs/{summary,plan,backfill,backfill/status,backfill/cancel}` 的字段与
   409（已有批次在跑，**不排队**）；「待分类」每篇带 `ccs_outcome` / `ccs_reason`
   （界面「没有建议要写明为什么」的依据）。

⚠ 全部在**本模块私有的临时数据目录** + `tmp_path` 上跑：真库 2.2GB / 6417 篇，
  一根手指都不碰（`KS_DATA_DIR` 指向 `%TEMP%` 下的私有目录，跑完即弃）。
⚠ **零真实网络**：所有网络层都用**注入的假 transport**（契约 `fetch(url, **kw) ->
  (status, body)`）。用例挂住等待网络 = 用例本身的缺陷。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fitz                                            # noqa: E402
import pytest                                          # noqa: E402

from src.core.ingestion import parser_worker          # noqa: E402
from src.core.ingestion import pipeline as pipeline_mod  # noqa: E402
from src.core.knowledge import ccs_backfill as bf      # noqa: E402
from src.core.knowledge import ccs_store               # noqa: E402
from src.core.knowledge import ccs_fetcher as cf       # noqa: E402


# ═══════════════════════════ 私有临时数据目录 ═══════════════════════════

@pytest.fixture(scope="module", autouse=True)
def _own_data_dir():
    """本模块私有的临时数据目录（照 `tests/test_ks_answer.py` 的先例；跑完即还原）。

    ⚠ 清理**自建目录时不许静默失败**（`conftest.py` 的会话级 fixture 已经立过这条规矩）：
    这里退避重试，最后仍清不掉就抛 `AssertionError` 把路径报出来 —— 不许用
    `ignore_cleanup_errors=True` 把失败吞掉（那正是 `%TEMP%` 里积压 1833 个
    `ks_test_*` 的成因）。
    """
    td = Path(tempfile.mkdtemp(prefix="ks_ccs_"))
    old = os.environ.get("KS_DATA_DIR")
    os.environ["KS_DATA_DIR"] = str(td)
    from src.core import config
    config.reset_settings()
    from src.core.storage.sqlite_db import (close_all_connections,
                                           close_thread_connection)
    close_thread_connection()
    try:
        yield td
    finally:
        config.reset_settings()
        close_thread_connection()
        close_all_connections()
        import gc
        gc.collect()
        if old is None:
            os.environ.pop("KS_DATA_DIR", None)
        else:
            os.environ["KS_DATA_DIR"] = old
        last: OSError | None = None
        for delay in (0.0, 0.2, 0.5, 1.0, 2.0, 3.0):
            if delay:
                time.sleep(delay)
            # 每一轮都再关一次 + 收一次垃圾：持有句柄的可能是"还没被回收的连接对象"
            # （`gc.collect()` 与 conftest 的会话级 fixture 同一手法）。
            close_all_connections()
            gc.collect()
            try:
                shutil.rmtree(td)
                last = None
                break
            except OSError as e:                        # noqa: PERF203
                last = e
        if last is not None:
            raise AssertionError(
                "本模块的临时数据目录没清掉（清理失败**不许静默**）："
                f"{td} —— {type(last).__name__}: {last}")


@pytest.fixture(autouse=True)
def _offline_embedder(monkeypatch):
    """向量引擎强制离线（与 `test_ks_answer` / `test_filing_state_pipeline` 同一手法）。

    不打的实测后果：`insert_clauses_in_txn` 会去 huggingface **下模型** ⇒ 用例挂在网络等待里。
    """
    from src.core.retrieval import embedder as _emb
    monkeypatch.setattr(_emb, "is_available", lambda: False)
    yield


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch):
    """**默认断网**：真 transport 一旦被用上就当场报错，而不是悄悄去打 cssn。

    这条是"零真实网络"的机械保证：`_default_transport()` 被替换成一个**抛异常**的假 transport
    （只有显式注入了假 transport 的用例才走得到网络层）。全量 pytest 时不许因为本文件而联网。
    """
    class _Refuse:
        def fetch(self, url, **kw):                     # noqa: ANN001, ANN003
            raise AssertionError(
                f"本文件不许打真实网络（试图请求 {url}）—— 请注入假 transport")
    monkeypatch.setattr(cf, "_default_transport", lambda: _Refuse())
    yield


# ═══════════════════════════ 假 transport ═══════════════════════════

class FakeTransport:
    """按 **URL 分派**的假传输（契约同 `channels.base`：`fetch(url, **kw) -> (status, body)`）。

    官方接口（``/api/standards/list``）与网页列表页（``/api/cssn/list``）各一份应答，
    并按调用次数排序返回（"关键词形式第几次命中"可以精确断言）。
    """

    def __init__(self, official=None, scrape=None, official_error=None,
                 scrape_error=None):
        self.official = official
        self.scrape = scrape
        self.official_error = official_error
        self.scrape_error = scrape_error
        self.official_calls: list[str] = []
        self.scrape_calls: list[str] = []

    def fetch(self, url, **kw):                         # noqa: ANN001, ANN003
        kw_params = kw.get("params") or {}
        keyword = str(kw_params.get("keyword") or "")
        if url == cf._CSSN_API:
            self.official_calls.append(keyword)
            if self.official_error is not None:
                raise self.official_error
            body = self.official
            return 200, (body(keyword) if callable(body) else body)
        if url == cf._CSSN_LIST:
            self.scrape_calls.append(keyword)
            if self.scrape_error is not None:
                raise self.scrape_error
            body = self.scrape
            return 200, (body(keyword) if callable(body) else body)
        raise AssertionError(f"假 transport 不认识这个 URL: {url}")


def _api_rows(*rows: dict) -> dict:
    """官方 JSON 应答（形状照 `channels/cssn.py` 的 docstring）。"""
    return {"code": 0, "count": len(rows), "results": list(rows)}


def _row(no: str, ccs: str = "", name: str = "") -> dict:
    return {"a100": no, "a825": ccs, "a825name": name, "a000": "现行", "a298": name}


def _html(*items: tuple[str, str, str]) -> str:
    """HTML 列表页（每条 = (标准号, 标题, CCS 原文)）。

    ⚠ **条目顺序照真机**：号（``ph_list_title``）在前、标题与 ``【CCS分类】`` 在后
    —— 这正是旧实现锚错元素的地方（见 `ccs_fetcher` 模块头第 3 条）。
    """
    parts = []
    for no, title, ccs in items:
        parts.append(
            '<div class="ph_list"><div class="ph_list_t clearfix">'
            f'<p class="ph_list_title">{no}</p></a></div></div>'
            f'<h3><strong class="ph_img_contenta301">{title}</strong></h3>'
            '<ul class="clearfix ph_list_li">'
            f'<li><strong class="blue">【CCS分类】</strong>{ccs}</li>'
            '<li><strong class="blue">【ICS分类】</strong>29.180</li></ul>')
    return "<!DOCTYPE html><html><body>" + "".join(parts) + "</body></html>"


# ═══════════════════════════ 1. 关键词形式 ═══════════════════════════

def test_keyword_forms_ordered_full_to_bare():
    """形式由**精确到宽泛**、且去重（业主：「完整标准号容易搜不到」⇒ 不许只赌一种）。"""
    forms = cf.keyword_forms("GB/T 1094.3-2017")
    assert [f for f, _ in forms] == ["full", "compact", "core", "bare"], forms
    assert dict(forms)["full"] == "GB/T 1094.3-2017"      # 空格必须留着
    assert dict(forms)["compact"] == "GBT1094.3-2017"
    assert dict(forms)["core"] == "1094.3"                # 含分部号
    assert dict(forms)["bare"] == "1094"                  # 最宽（也最吵）
    # 全角斜杠要折成半角（真库 92% 的号写全角）
    assert dict(cf.keyword_forms("GB／T 50493-2019"))["full"] == "GB/T 50493-2019"
    # 没有分部号时 core 与 bare 相同 ⇒ 去重（省一次请求）
    assert [f for f, _ in cf.keyword_forms("GB 30871-2022")] == \
        ["full", "compact", "core"]


def test_keyword_forms_strip_trailing_junk():
    """**尾部杂字**要能抠掉（真机 380 篇实测：真库标准号字段混着中文）。

    `GB 5009.12-2023食品安全国家标准` 这种写法拿整串去搜当然搜不到；
    抠成 `GB 5009.12-2023` 就搜得到。号本身干净时 `clean` 与 `full` 同形、被去重。
    """
    forms = dict(cf.keyword_forms("GB 5009.12-2023食品安全国家标准"))
    assert forms["full"] == "GB 5009.12-2023食品安全国家标准"
    assert forms["clean"] == "GB 5009.12-2023"
    forms2 = dict(cf.keyword_forms("GB/T 27668-2023显微镜光学显微术术语(1)"))
    assert forms2["clean"] == "GB/T 27668-2023"
    # 老写法（两位年代）也要能抠出数字主体
    assert "core" in dict(cf.keyword_forms("GB 228-87"))


def test_not_a_standard_no_is_not_applicable():
    """**不像标准号的字段 ⇒ `not_applicable`，而且一次网络都不打。**

    真机 380 篇实测：里面混着 **7 篇法规**（`中华人民共和国民法典`、`安全生产法(2021修正)`、
    `消防法(2021修正全本)`…）被标成了 `doc_type='standard'`。分类号是标准体系的东西，
    对法规**永远没有** —— 拿它们去搜是白打网络，结论写"官方查无"也不对（那不是"没有这个号"）。
    """
    tr = FakeTransport(official=_api_rows(), scrape=_html())
    got = cf.resolve_ccs("中华人民共和国民法典", transport=tr)
    assert got["outcome"] == "not_applicable", got
    assert tr.official_calls == [] and tr.scrape_calls == [], \
        "不像标准号的字段不该打网络（永远不会有结果）"
    assert "不适用" in got["reason"]
    assert cf.looks_like_standard_no("GB 5009.12-2023食品安全国家标准") is True
    assert cf.looks_like_standard_no("消防法(2021修正全本)") is False


def test_other_edition_match_is_rejected_not_used():
    """**年份不同的他版不许当命中**（真机实测抓到的真缺陷，会打错标签）。

    实测现场：``GBZ 337-2025``（职业性腕管综合征诊断标准）的数字主体 ``337``
    在站点上撞到 ``GB 337-1984``（无机酸、碱）—— 差 41 年、毫无关系。
    照旧接受的话，这一篇会被打上"无机酸碱"的分类号。
    """
    tr = FakeTransport(official=lambda kw: _api_rows(
        _row("GB 337-1984", "G11", "无机酸、碱")))
    got = cf.resolve_ccs("GBZ 337-2025", transport=tr)
    assert got["outcome"] == "not_found", got
    assert got["code"] is None, f"取了年份不同的他版的分类号：{got}"
    assert any(a["result"] == "other_edition" for a in got["attempts"]), got["attempts"]
    # 反例（同年份、跨前缀）：这一档**必须**留着 —— 强制转推荐后库里只剩 GB/T 版
    tr2 = FakeTransport(official=lambda kw: _api_rows(
        _row("GB/T 1094.2-2013", "K41", "变压器")))
    ok = cf.resolve_ccs("GB 1094.2-2013", transport=tr2)
    assert ok["outcome"] == "found" and ok["code"] == "K41"
    assert ok["matched_no"] == "GB/T 1094.2-2013"


# ═══════════════════════════ 2. 链的顺序 + 来源 ═══════════════════════════

def test_official_api_hit_reports_source_and_form():
    """正例：官方接口命中 ⇒ `source=official_api` 且**记下**是哪种关键词形式命中的。"""
    tr = FakeTransport(official=_api_rows(_row("GB/T 1094.3-2017", "K41", "变压器")))
    got = cf.resolve_ccs("GB/T 1094.3-2017", transport=tr)
    assert got["outcome"] == "found", got
    assert got["code"] == "K41" and got["sub"] == "变压器"
    assert got["source"] == "official_api"
    assert got["keyword_form"] == "full"
    assert got["source_label"] == "官方接口"
    assert got["matched_no"] == "GB/T 1094.3-2017"
    # 命中的那一次尝试也留在流水里（审计要能看出"是这一形式中的"）
    assert any(a["result"] == "hit" and a["layer"] == "official_api"
               for a in got["attempts"])


def test_official_hit_never_calls_web_scrape():
    """**反向**：官方接口通了就**不许**再抓网页。

    没有这一条，"来源 = 官方接口"只是我们自己写上去的一句话 —— 而真相是两层都问了。
    """
    tr = FakeTransport(official=_api_rows(_row("GB 30871-2022", "C65", "劳动安全技术综合")),
                       scrape=_html(("GB 30871-2022", "危险化学品企业特殊作业安全规范",
                                     "C65劳动安全技术综合")))
    got = cf.resolve_ccs("GB 30871-2022", transport=tr)
    assert got["outcome"] == "found" and got["source"] == "official_api"
    assert tr.official_calls == ["GB 30871-2022"]
    assert tr.scrape_calls == [], \
        f"官方已经答上了，网页那一层却被问了：{tr.scrape_calls}"


def test_official_empty_falls_back_to_web_scrape():
    """**官方接口永远返回空 ⇒ 必须回退到网页抓取，且来源记为 `web_scrape`**。

    这正是业主说的那个场景（"有时候官方接口可能不返回一些老标准的数据"），
    也是变异①要的行为：网页抓取是**备选**，不是装饰。
    """
    tr = FakeTransport(
        official=_api_rows(),                     # 答了，但一条都没有
        scrape=_html(("GB/T 12998-1991", "水质采样技术指导", "Z12环境监测")))
    got = cf.resolve_ccs("GB/T 12998-1991", transport=tr)
    assert got["outcome"] == "found", got
    assert got["source"] == "web_scrape", got
    assert got["code"] == "Z12" and got["sub"] == "环境监测"
    assert got["keyword_form"] == "full"
    assert tr.scrape_calls, "官方查无之后必须去抓网页（备选路线不能是死的）"
    # 官方那几次尝试照样留痕（"前面几层为什么没中"）—— 这一批号没有分部号、
    # 也没有尾部杂字 ⇒ full/compact/core 三种形式各留一条 no_match（bare 被去重）。
    off = [a for a in got["attempts"] if a["layer"] == "official_api"]
    assert [a["keyword_form"] for a in off] == ["full", "compact", "core"]
    assert all(a["result"] == "no_match" for a in off), off


def test_keyword_form_escalates_when_full_form_misses():
    """完整号搜不到时**继续试**别的形式，并把**真正中的那种**记下来。

    ⚠ 造的是"完整号这条查询返回空表、数字主体那条才给结果"的应答 —— 真机上
    `1094.2-2013`/`1094` 这类宽形式的召回确实不同。
    """
    def official(keyword: str) -> dict:
        if keyword == "1094.3":
            return _api_rows(_row("GB/T 1094.3-2017", "K41", "变压器"))
        return _api_rows()

    tr = FakeTransport(official=official)
    got = cf.resolve_ccs("GB/T 1094.3-2017", transport=tr)
    assert got["outcome"] == "found" and got["code"] == "K41"
    assert got["keyword_form"] == "core"
    assert tr.official_calls == ["GB/T 1094.3-2017", "GBT1094.3-2017", "1094.3"]


# ═══════════════════════════ 3. 网页抓取的块边界（回归哨兵） ═══════════════════════════

def test_html_block_anchored_on_standard_no_not_title():
    """网页块必须按**标准号**（`ph_list_title`）切：号↔标题↔CCS 三者对得上。

    旧实现按 `a301`（**标题**）切块、再拿标准号去**标题文本**里找 ⇒ 永不相等
    （真机取证：同一页里 `GB/T 1094.3-2017` 的 CCS 明明在，20 条一条都挑不中）。
    """
    html = _html(
        ("GB/T 1094.3-2017", "电力变压器 第3部分：绝缘水平", "K41变压器"),
        ("GB/T 34136-2017", "机械电气安全", "J07电子计算机应用"),
    )
    items = cf._parse_html_items(html)
    assert [i["a100"] for i in items] == ["GB/T 1094.3-2017", "GB/T 34136-2017"]
    assert items[0]["ccs"] == "K41变压器"
    assert items[1]["ccs"] == "J07电子计算机应用"
    # 关键：第 0 条的 CCS **不是**下一条的（错位就会串号）
    assert items[0]["a298"].startswith("电力变压器")
    assert items[1]["a298"].startswith("机械电气安全")


# ═══════════════════════════ 4. 本地兜底（第③层：零网络） ═══════════════════════════

def test_local_table_hit_needs_no_network():
    """人工核实表命中 ⇒ `source=local_table`，且**一次网络都不打**。"""
    tr = FakeTransport(official=_api_rows(), scrape=_html())
    got = cf.resolve_ccs("GB 30871-2022", transport=tr)
    assert got["outcome"] == "found" and got["source"] == "local_table"
    assert got["code"] == "C65"
    assert got["matched_no"] == "GB 30871-2022"


def test_seed_file_hit_needs_no_network(tmp_path):
    """种子文件命中 ⇒ `source=seed_file`（批量入库那条路：命中即零网络）。"""
    seed = tmp_path / "ccs_seed.json"
    # 键的形状 = `_seed_key`（只折全角斜杠与空格、**保留半角斜杠**），与
    # `std_bulk_import.write_ccs_seed` 同一约定。
    seed.write_text(json.dumps({"GB/T12998-1991": {"code": "Z12", "sub": "环境监测"}},
                               ensure_ascii=False), encoding="utf-8")
    tr = FakeTransport(official=_api_rows(), scrape=_html())
    got = cf.resolve_ccs("GB/T 12998-1991", transport=tr, seed_path=seed)
    assert got["outcome"] == "found" and got["source"] == "seed_file"
    assert got["code"] == "Z12"


def test_use_network_false_is_local_only():
    """`use_network=False` ⇒ 只走本地（批量场景/离线重跑的口径）。"""
    got = cf.resolve_ccs("GB 30871-2022", use_network=False)
    assert got["outcome"] == "found" and got["source"] == "local_table"
    miss = cf.resolve_ccs("GB/T 99999-1999", use_network=False)
    assert miss["outcome"] == "not_found" and miss["code"] is None


# ═══════════════════════════ 5. 失败分类（三条互斥，不许混） ═══════════════════════════

def test_transport_error_is_network_failed_not_not_found():
    """**三层里网络层全炸 ⇒ `network_failed`**，绝不是"官方查无"。

    这是本次重做要修的那个真毛病：旧实现 `except Exception: return None`，
    本机 httpx 构造失败（`NO_VROXY` 含 `[::1]`）⇒ 0.1 秒返回 None，
    看上去像"官方就是没有这个号"。
    """
    tr = FakeTransport(official_error=RuntimeError("Invalid port: ':1]'"),
                       scrape_error=RuntimeError("Invalid port: ':1]'"))
    got = cf.resolve_ccs("GB/T 1094.3-2017", transport=tr)
    assert got["outcome"] == "network_failed", got
    assert got["outcome"] != "not_found", "发不出去被说成了官方查无（本次要修的正是这个）"
    assert got["code"] is None
    assert "网络" in got["reason"], got["reason"]
    assert "查无" not in got["reason"], got["reason"]


def test_answered_but_no_such_number_is_not_found():
    """站点答了、解得出条目、里面确实没有这个号 ⇒ `not_found`（**不是** network_failed）。"""
    tr = FakeTransport(
        official=_api_rows(_row("GB/T 34136-2017", "J07", "电子计算机应用")),
        scrape=_html(("GB/T 34136-2017", "机械电气安全", "J07电子计算机应用")))
    got = cf.resolve_ccs("GB/T 99999-1999", transport=tr)
    assert got["outcome"] == "not_found", got
    assert got["code"] is None and got["found"] is False
    assert "查无" in got["reason"], got["reason"]
    # 逐层"为什么没中"都在流水里（"前面几层为什么没命中"要能说出来）
    assert any(a["layer"] == "official_api" and a["result"] == "no_match"
               for a in got["attempts"])
    assert any(a["layer"] == "web_scrape" and a["result"] == "no_match"
               for a in got["attempts"])
    assert any(a["layer"] == "local_table" for a in got["attempts"])


def test_broken_html_structure_is_parse_failed():
    """**两层都答了、却一层都读不出** ⇒ `parse_failed`，如实说"读不出条目"。

    ⚠ 注意口径：只要**有一层**答得清清楚楚（官方回了条目列表、里面没有这个号），
    结论就是 `not_found`（那条另有用例钉住）—— 读不出的细节留在 attempts 里。
    本用例造的是**两层都读不出**：官方回的 JSON 形状不对 + 网页锚点一条都没有。
    """
    tr = FakeTransport(official="<html>不是 JSON</html>",
                       scrape="<html><body>改版了</body></html>")
    got = cf.resolve_ccs("GB/T 1094.3-2017", transport=tr)
    assert got["outcome"] == "parse_failed", got
    assert "读不出" in got["reason"] or "结构" in got["reason"], got["reason"]


def test_official_answers_clearly_so_not_found_even_if_scrape_broken():
    """官方答得清清楚楚（条目列表里没有这个号）⇒ `not_found`，**不因网页那层读不出而改口**。

    这条钉的是"结论看**有没有一层答清楚**，不要求每一层都答上"：
    把次要的解析问题拿来盖住主要结论（"官方明说了没有这个号"）是另一种不诚实。
    读不出的细节照样留在 `attempts` 里（下面那条断言）。
    """
    tr = FakeTransport(official=_api_rows(_row("GB/T 34136-2017", "J07", "电子计算机应用")),
                       scrape="<html><body>改版了</body></html>")
    got = cf.resolve_ccs("GB/T 99999-1999", transport=tr)
    assert got["outcome"] == "not_found", got
    assert any(a["layer"] == "web_scrape" and a["result"] == "unparsable"
               for a in got["attempts"]), got["attempts"]


def test_matched_number_without_ccs_says_so():
    """站点**有这个号**、但那一行/那一条**没有分类号** ⇒ `parse_failed` 且原因说清是哪种。"""
    tr = FakeTransport(official=_api_rows(_row("GB/T 1094.3-2017", "", "")),
                       scrape=_html(("GB/T 1094.3-2017", "电力变压器", "")))
    got = cf.resolve_ccs("GB/T 1094.3-2017", transport=tr)
    assert got["outcome"] == "parse_failed", got
    assert "分类号" in got["reason"], got["reason"]
    # 流水里明确写着"号命中了、这一行 a825 是空的"（不是"没这个号"）
    assert any(a["result"] == "no_ccs_field" for a in got["attempts"])


def test_empty_standard_no_is_not_a_network_failure():
    """没有标准号 ⇒ 如实说"没有号"，**不许**记成网络失败（那会误导人去查网络）。"""
    got = cf.resolve_ccs("", transport=FakeTransport())
    assert got["outcome"] == "not_found"
    assert "没有标准号" in got["reason"]


# ═══════════════════════════ 6. 台账（ccs_store） ═══════════════════════════

def test_record_and_apply_tag_are_idempotent(db):
    """写台账 / 追加标签：**幂等**，且**不动**已有的别的标签。"""
    _seed_doc("doc_ccs_a", "GB/T 90110-2020", ["消防"])
    got = {"outcome": "found", "code": "K41", "sub": "变压器",
           "source": "official_api", "keyword_form": "full",
           "matched_no": "GB/T 90110-2020", "attempts": [{"layer": "official_api"}]}
    first = ccs_store.apply_ccs_tag("doc_ccs_a", "CCS:K41 变压器", result=got)
    assert first["applied"] is True
    assert ccs_store.ccs_tag_of(_tags_of(db, "doc_ccs_a")) == "CCS:K41 变压器"
    assert "消防" in _tags_of(db, "doc_ccs_a"), "别的标签被抹掉了（红线）"
    # 再来一次：**不重复追加**
    second = ccs_store.apply_ccs_tag("doc_ccs_a", "CCS:K41 变压器", result=got)
    assert second["applied"] is False
    assert _tags_of(db, "doc_ccs_a").count("CCS:K41 变压器") == 1
    row = ccs_store.get_ccs_state("doc_ccs_a")
    assert row is not None
    assert row["outcome"] == "found" and row["source"] == "official_api"
    assert row["applied_at"] is not None
    assert json.loads(row["attempts_json"])[0]["layer"] == "official_api"


def test_record_failure_keeps_reason_and_leaves_tags_alone(db):
    """未命中 ⇒ 台账记 `outcome` + `reason` + 流水，**domain_tags 一个字都不动**。"""
    _seed_doc("doc_ccs_b", "GB/T 90111-2020", [])
    ccs_store.record_ccs_lookup("doc_ccs_b", {
        "outcome": "network_failed", "reason": "查询失败：两个站点一个都没答上",
        "attempts": [{"layer": "official_api", "result": "network_error",
                      "detail": "InvalidURL"}]})
    row = ccs_store.get_ccs_state("doc_ccs_b")
    assert row is not None
    assert row["outcome"] == "network_failed"
    assert "没答上" in row["reason"]
    assert row["applied_at"] is None
    assert _tags_of(db, "doc_ccs_b") == []


def test_record_rejects_unknown_outcome(db):
    """不认识的结论**当场报错**（不许静默写进一个没定义的状态）。"""
    _seed_doc("doc_ccs_c", "GB/T 90112-2020", [])
    from src.core.exceptions import KnowledgeStationError
    with pytest.raises(KnowledgeStationError):
        ccs_store.record_ccs_lookup("doc_ccs_c", {"outcome": "maybe"})


# ═══════════════════════════ 7. 自愈机制（补全分类号） ═══════════════════════════

def test_plan_finds_only_missing_ones(db):
    """候选**算出来**：只挑 `doc_type='standard'` 且 `domain_tags` 里没有 `CCS:` 的。

    ⚠ 拿一个**名叫 `CCS:` 的非标准文档**当反例（`doc_type='法律法规'`）：它不该进候选
    —— 判据既要看"有没有标签"，也要看"是不是标准"。
    """
    _seed_doc("doc_ccs_p1", "GB/T 90120-2020", [])
    _seed_doc("doc_ccs_p2", "GB/T 90121-2020", ["CCS:K41 变压器"])
    _seed_doc("doc_ccs_p3", "GB/T 90122-2020", ["消防"])
    _seed_doc("doc_ccs_p4", "法律-90123", [], doc_type="法律法规")
    plan = bf.plan_ccs_backfill(doc_ids=["doc_ccs_p1", "doc_ccs_p2", "doc_ccs_p3",
                                         "doc_ccs_p4"])
    ids = {c["doc_id"] for c in plan["candidates"]}
    assert ids == {"doc_ccs_p1", "doc_ccs_p3"}, plan
    assert plan["total"] == 2


def test_backfill_writes_through_to_db(db, monkeypatch):
    """**核心**：自愈跑完 ⇒ `domain_tags` 里**真的多了一条** `CCS:…` + 台账有来源。

    ## 反向哨兵（"只改内存不落库"必红的依据）
    断言读的是**库里的行**（`_tags_of` 直接 `SELECT domain_tags`），不是模块内存里的变量；
    所以把 `apply_ccs_tag` 换成"只改内存"（或不写库）时这条**必红**。
    """
    _seed_doc("doc_ccs_w1", "GB/T 90130-2020", [])
    _seed_doc("doc_ccs_w2", "GB/T 90131-2020", [])
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: (
        {"outcome": "found", "code": "K41", "sub": "变压器", "source": "official_api",
         "keyword_form": "full", "matched_no": no, "attempts": []}
        if no == "GB/T 90130-2020" else
        {"outcome": "not_found", "code": None, "source": None, "reason": "查无",
         "attempts": []}))
    # ⚠ 打的就是 `ccs_fetcher.resolve_ccs`：`ccs_backfill._run` 是在**函数体内**
    #   `from ... import resolve_ccs`，所以换掉模块属性就够（不需要再打别处一份）。
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_w1", "doc_ccs_w2"], pause_s=0.0)
    assert out["queued"] == 2, out
    _wait_done()
    st = bf.ccs_backfill_status()
    assert st["done"] == 2, st
    assert st["found"] == 1 and st["not_found"] == 1, st
    assert st["applied"] == 1
    # ① 标签**真的落库了**
    assert _tags_of(db, "doc_ccs_w1") == ["CCS:K41 变压器"]
    assert _tags_of(db, "doc_ccs_w2") == []
    # ② 来源**真的记下来了**
    w1_state = ccs_store.get_ccs_state("doc_ccs_w1")
    assert w1_state is not None and w1_state["source"] == "official_api"
    # ③ 没补到的进失败清单（逐篇带原因，不许静默）
    assert [f["doc_id"] for f in st["failures"]] == ["doc_ccs_w2"]
    assert st["failures"][0]["reason"] == "查无"


def test_backfill_rerun_is_noop(db, monkeypatch):
    """**可重跑 / 幂等**：已经有分类号的篇不再进候选 ⇒ 再跑一遍 = 0 篇。"""
    _seed_doc("doc_ccs_r1", "GB/T 90140-2020", [])
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: (
        {"outcome": "found", "code": "Z12", "sub": "环境监测", "source": "local_table",
         "keyword_form": None, "matched_no": no, "attempts": []}))
    first = bf.start_ccs_backfill(doc_ids=["doc_ccs_r1"], pause_s=0.0)
    assert first["queued"] == 1
    _wait_done()
    assert _tags_of(db, "doc_ccs_r1") == ["CCS:Z12 环境监测"]
    # 再跑一遍：候选里已经没有它了
    again = bf.start_ccs_backfill(doc_ids=["doc_ccs_r1"], pause_s=0.0)
    assert again["queued"] == 0, again
    assert _tags_of(db, "doc_ccs_r1").count("CCS:Z12 环境监测") == 1


def test_backfill_all_layers_dead_records_failure_in_db(db, monkeypatch):
    """**变异②的口径**：三层全掐掉 ⇒ 台账必须**如实记**失败，而不是"什么都没有"。

    这里让 `resolve_ccs` 直接给 `network_failed`（真实的"三层全掐"在链那一层已经有用例
    覆盖：`test_transport_error_is_network_failed_not_found`）—— 本用例守的是**落库**：
    那种结论要能在库里查到，界面才说得清"为什么这一篇没有建议"。
    """
    _seed_doc("doc_ccs_d1", "GB/T 90150-2020", [])
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "network_failed", "code": None, "source": None,
        "reason": "查询失败：两个站点一个都没答上（网络不通或被拦）",
        "attempts": [{"layer": "official_api", "result": "network_error"}]})
    bf.start_ccs_backfill(doc_ids=["doc_ccs_d1"], pause_s=0.0)
    _wait_done()
    row = ccs_store.get_ccs_state("doc_ccs_d1")
    assert row is not None, "三层都失败时台账里**什么都没有** —— 那就是静默"
    assert row["outcome"] == "network_failed"
    assert "没答上" in row["reason"]
    assert _tags_of(db, "doc_ccs_d1") == []
    assert [f["outcome"] for f in bf.ccs_backfill_status()["failures"]] \
        == ["network_failed"]


def test_backfill_cancel_is_honest(db, monkeypatch):
    """**可中断**：按停 ⇒ 标志置上、没轮到的进 `skipped_list`，`cancelled` 如实。"""
    _seed_doc("doc_ccs_x1", "GB/T 90160-2020", [])
    _seed_doc("doc_ccs_x2", "GB/T 90161-2020", [])
    seen: list[str] = []

    def slow(no, name="", **kw):                        # noqa: ANN001, ANN003
        seen.append(no)
        bf.cancel_ccs_backfill()                        # 第一篇跑的时候就按停
        return {"outcome": "not_found", "code": None, "source": None,
                "reason": "查无", "attempts": []}

    monkeypatch.setattr(cf, "resolve_ccs", slow)
    bf.start_ccs_backfill(doc_ids=["doc_ccs_x1", "doc_ccs_x2"], pause_s=0.0)
    _wait_done()
    st = bf.ccs_backfill_status()
    assert st["cancel_requested"] is True
    assert st["cancelled"] is True, st
    assert st["skipped"] == 1 and len(st["skipped_list"]) == 1, st
    assert len(seen) == 1, f"按停之后还在继续跑：{seen}"


def test_backfill_busy_is_refused_not_queued(db, monkeypatch, ):
    """**同一时刻只跑一批**：已有批次在跑 ⇒ `RuntimeError('ccs_backfill_busy')`（**不排队**）。"""
    _seed_doc("doc_ccs_busy", "GB/T 90170-2020", [])
    release: list[int] = []

    def hang(no, name="", **kw):                        # noqa: ANN001, ANN003
        for _ in range(200):
            if release:
                break
            time.sleep(0.01)
        return {"outcome": "not_found", "code": None, "reason": "查无", "attempts": []}

    monkeypatch.setattr(cf, "resolve_ccs", hang)
    bf.start_ccs_backfill(doc_ids=["doc_ccs_busy"], pause_s=0.0)
    try:
        with pytest.raises(RuntimeError, match="ccs_backfill_busy"):
            bf.start_ccs_backfill(doc_ids=["doc_ccs_busy"], pause_s=0.0)
    finally:
        release.append(1)
        bf.cancel_ccs_backfill()
        _wait_done()


# ═══════════════════════════ 8. 接口外形 ═══════════════════════════

def _api(client, token, method, path, **kw):            # noqa: ANN001, ANN003
    from _kb_folder_api_fixtures import api
    return api(client, token, method, path, **kw)


def test_api_ccs_summary_and_plan(client, db):
    """`/kb/ccs/summary` 与 `/kb/ccs/plan`：只读、字段齐、**不联网**。"""
    from _kb_folder_api_fixtures import data_of
    c, token = client
    _seed_doc("doc_ccs_api1", "GB/T 90180-2020", [])
    s = data_of(_api(c, token, "get", "/api/v1/kb/ccs/summary"))
    assert s["missing"] >= 1
    assert set(s["by_outcome"]) == {"found", "not_found", "network_failed", "parse_failed",
                                    "not_applicable"}
    assert s["outcome_labels"]["not_found"] and s["source_labels"]["web_scrape"]
    assert s["max_batch"] > 0 and s["sources"][0] == "official_api"
    assert "backfill" in s and s["backfill"]["total"] >= 0
    p = data_of(_api(c, token, "get", "/api/v1/kb/ccs/plan"))
    assert any(x["doc_id"] == "doc_ccs_api1" for x in p["candidates"]), p
    assert p["already_have"] >= 0


def test_api_ccs_backfill_runs_and_reports_status(client, db, monkeypatch):
    """`POST /kb/ccs/backfill` ⇒ 后台真跑；`status` 给 done/total + 失败清单。"""
    from _kb_folder_api_fixtures import data_of
    c, token = client
    _seed_doc("doc_ccs_api2", "GB/T 90181-2020", [])
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: (
        {"outcome": "found", "code": "K41", "sub": "变压器", "source": "official_api",
         "keyword_form": "full", "matched_no": no, "attempts": []}))
    out = data_of(_api(c, token, "post", "/api/v1/kb/ccs/backfill",
                       json={"doc_ids": ["doc_ccs_api2"], "limit": 10}))
    assert out["queued"] == 1, out
    _wait_done()
    st = data_of(_api(c, token, "get", "/api/v1/kb/ccs/backfill/status"))
    assert st["running"] is False and st["done"] == 1 and st["found"] == 1, st
    assert st["missing"] is not None
    assert _tags_of(db, "doc_ccs_api2") == ["CCS:K41 变压器"]


def test_api_inbox_reports_ccs_reason(client, db):
    """「待分类」每篇带 `ccs_outcome` / `ccs_reason` —— 界面「没有建议要写明为什么」的依据。"""
    from _kb_folder_api_fixtures import data_of
    c, token = client
    _seed_doc("doc_ccs_api3", "GB/T 90182-2020", [])
    ccs_store.record_ccs_lookup("doc_ccs_api3", {
        "outcome": "not_found", "reason": "查无：答话的站点里都没有这个标准号",
        "attempts": []})
    page = data_of(_api(c, token, "get", "/api/v1/kb/inbox", params={"limit": 200}))
    row = next((r for r in page["items"] if r["doc_id"] == "doc_ccs_api3"), None)
    assert row is not None, "这一篇不在「待分类」里（没归位就该在）"
    assert row["ccs_outcome"] == "not_found", row
    assert row["ccs_outcome_label"] == "查无（答话的站点里都没有这个号）"
    assert "查无" in row["ccs_reason"]
    assert row["ccs_tag"] is None
    # 反面：另一篇**没查过** ⇒ 如实是 null（不许编一个理由）
    _seed_doc("doc_ccs_api4", "GB/T 90183-2020", [])
    page2 = data_of(_api(c, token, "get", "/api/v1/kb/inbox", params={"limit": 200}))
    row2 = next((r for r in page2["items"] if r["doc_id"] == "doc_ccs_api4"), None)
    assert row2 is not None and row2["ccs_outcome"] is None, row2


def test_api_ccs_plan_rejects_bad_limit(client, db):
    """非法 `limit` ⇒ 422（不许静默按默认值跑）。"""
    c, token = client
    r = _api(c, token, "get", "/api/v1/kb/ccs/plan", params={"limit": "-5"})
    assert r.status_code == 422, r.text


# ═══════════════════════════ 9. 入库那条路（真跑一次） ═══════════════════════════

REAL_BLOCKS = [
    "1 范围",
    "本标准规定了危险化学品企业特殊作业的安全要求。",
    "2 规范性引用文件",
    "下列文件对于本文件的应用是必不可少的。",
    "3 术语和定义",
    "3.1 特殊作业 指在生产经营过程中可能对操作者造成伤害的作业。",
    "4 基本要求",
    "4.1 作业前应进行风险辨识并办理作业审批手续。",
]


def _write_pdf(path: Path, first_line: str = "GB/T 39999-2020") -> Path:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), first_line)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def synthetic_parser(monkeypatch):
    """把解析器换成合成 blocks（真链路，只有"从 PDF 抠 blocks"这一步是假的）。"""
    def _install(blocks: list[str]) -> None:
        def _fake(pdf_path, output_dir, timeout=900, force_deep=False,   # noqa: ANN001
                  deep_fallback=True):
            return {"blocks": [{"text": t, "page_number": 1,
                                "bbox": [60.0, 600.0, 530.0, 720.0]} for t in blocks],
                    "geometries": {1: {"width": 595.0, "height": 842.0, "rotation": 0}},
                    "deep_output": None, "is_ocr": False}
        monkeypatch.setattr(pipeline_mod, "run_parser_isolated", _fake)
        monkeypatch.setattr(parser_worker, "run_parser_isolated", _fake)
    return _install


def test_ingest_records_ccs_source(db, tmp_path, synthetic_parser, monkeypatch):
    """真跑一次入库 ⇒ 标签进 `domain_tags`、**来源进台账**（"每篇都要能说出是哪一层命中的"）。"""
    synthetic_parser(REAL_BLOCKS)
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "found", "code": "C65", "sub": "劳动安全技术综合",
        "source": "web_scrape", "keyword_form": "compact",
        "matched_no": "GB/T 90200-2020", "attempts": [
            {"layer": "official_api", "keyword_form": "full", "result": "no_match",
             "detail": "应答 0 条"},
            {"layer": "web_scrape", "keyword_form": "compact", "result": "hit",
             "detail": "GB/T 90200-2020 (exact)"}]})
    pdf = _write_pdf(tmp_path / "ccs_ok.pdf", "GB/T 90200-2020")
    out = pipeline_mod.run_full_ingest(pdf, "GB/T 90200-2020", "测试标准 90200")
    assert out["status"] == "ok", out
    assert _tags_of(db, out["doc_id"]) == ["CCS:C65 劳动安全技术综合"]
    row = ccs_store.get_ccs_state(out["doc_id"])
    assert row is not None, "入库成功却没写分类号台账（那就还是静默）"
    assert row["source"] == "web_scrape"
    assert row["keyword_form"] == "compact"
    assert row["matched_no"] == "GB/T 90200-2020"
    attempts = json.loads(row["attempts_json"])
    assert [a["layer"] for a in attempts] == ["official_api", "web_scrape"]


def test_ingest_records_failure_not_silence(db, tmp_path, synthetic_parser, monkeypatch):
    """**反向（本次重做的核心）**：那条链失败时，台账**必须**留下结论与原因。

    旧实现是 `except Exception: pass  # 失败静默降级` ⇒ 真库 380 篇标准"静默地"没有分类号。
    这里把那 380 篇的现场复现出来：链返回未命中 ⇒ 台账有行、`outcome` 与 `reason` 都在，
    而 `domain_tags` 保持空（**降级可以，必须留痕**）。
    """
    synthetic_parser(REAL_BLOCKS)
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "network_failed", "code": None, "source": None,
        "reason": "查询失败：两个站点一个都没答上（网络不通或被拦）",
        "attempts": [{"layer": "official_api", "result": "network_error",
                      "detail": "InvalidURL: Invalid port: ':1]'"}]})
    pdf = _write_pdf(tmp_path / "ccs_fail.pdf", "GB/T 90201-2020")
    out = pipeline_mod.run_full_ingest(pdf, "GB/T 90201-2020", "测试标准 90201")
    assert out["status"] == "ok", out
    assert _tags_of(db, out["doc_id"]) == []
    row = ccs_store.get_ccs_state(out["doc_id"])
    assert row is not None, "链失败时台账里什么都没有 —— 那就是旧的静默降级"
    assert row["outcome"] == "network_failed"
    assert "没答上" in row["reason"]
    assert "InvalidURL" in row["attempts_json"]
    # 入库本身没被拖垮（降级照旧）
    assert out["total_clauses"] > 0


# ═══════════════════════════ 工具 ═══════════════════════════

def _seed_doc(doc_id: str, standard_no: str, tags: list[str],
              doc_type: str = "standard") -> None:
    """直接写一行 `doc_meta`（走**唯一所有者** `clause_repo.insert_document`）。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    with write_transaction() as conn:
        clause_repo.insert_document(conn, {
            "doc_id": doc_id, "standard_no": standard_no,
            "standard_name": f"测试 {standard_no}", "short_code": standard_no,
            "current_revision_id": f"rev_{doc_id}", "doc_type": doc_type,
            "legal_hierarchy": "GB", "standard_type": "mandatory",
            "domain_tags": tags, "file_path": f"C:/tmp/{doc_id}.pdf",
            "file_hash": f"hash_{doc_id}"})


def _tags_of(db, doc_id: str) -> list[str]:            # noqa: ANN001
    """**从库里读**（不是从内存读）—— 这一条是"只改内存不落库必红"的依据。"""
    row = db.execute("SELECT domain_tags FROM doc_meta WHERE doc_id=?",
                     (doc_id,)).fetchone()
    assert row is not None, f"库里没有这一篇：{doc_id}"
    return list(json.loads(row[0] or "[]"))


def _wait_done(timeout_s: float = 20.0) -> None:
    """等后台线程跑完（超时就抛 —— **不许**用 sleep 假装跑完了）。"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if not bf.ccs_backfill_status()["running"]:
            return
        time.sleep(0.05)
    raise AssertionError("后台补全线程超时还没结束（用例不该挂在这里）")
