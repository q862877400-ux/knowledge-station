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
    from src.core.storage.sqlite_db import close_connections_under, close_thread_connection
    close_thread_connection()
    try:
        yield td
    finally:
        config.reset_settings()
        close_thread_connection()
        # ⚠ **只关指向自己那个临时目录的连接**（`close_connections_under`）——
        #   这里**不能**用 `close_all_connections()`：那是**全局**动作，会把**别的模块**
        #   正握着的连接一起关掉，而它们（批量导入的后台线程 / AnyIO worker）会拿到
        #   `Cannot operate on a closed database`，症状出现在**别人**的用例上。
        #   整场收尾那次全局关闭由 `tests/conftest.py` 的会话级 fixture 负责。
        close_connections_under(td)
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
            # 每一轮再收一次（持有句柄的可能是"还没被回收的连接对象"）。
            close_connections_under(td)
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
    assert [f for f, _k, _t in forms] == ["full", "compact", "core", "bare"], forms
    assert dict((f, k) for f, k, _t in forms)["full"] == "GB/T 1094.3-2017"   # 空格留着
    assert dict((f, k) for f, k, _t in forms)["compact"] == "GBT1094.3-2017"
    assert dict((f, k) for f, k, _t in forms)["core"] == "1094.3"             # 含分部号
    assert dict((f, k) for f, k, _t in forms)["bare"] == "1094"               # 最宽（最吵）
    # 全角斜杠要折成半角（真库 92% 的号写全角）
    assert dict((f, k) for f, k, _t in
                cf.keyword_forms("GB／T 50493-2019"))["full"] == "GB/T 50493-2019"
    # 没有分部号时 core 与 bare 相同 ⇒ 去重（省一次请求）
    assert [f for f, _k, _t in cf.keyword_forms("GB 30871-2022")] == \
        ["full", "compact", "core"]


def test_keyword_form_target_is_also_cleaned():
    """**关键词与匹配目标必须一起抠干净**（真机实测抓到的我自己的缺陷，回归哨兵）。

    第一版只把关键词抠干净、匹配目标还留着原串：站点明明回了 `GB 5009.12-2023`
    （`a825=X09`）排第一，而归一号是 `GB5009.12-2023食品安全国家标准` ⇒ **永不相等**，
    报成"查无"。⇒ 这条钉住"每个形式的目标都是抠干净的那个号"。
    """
    for form, _kw, target in cf.keyword_forms("GB 5009.12-2023食品安全国家标准"):
        assert target == "GB 5009.12-2023", (form, target)
    # 抠干净之后**同一份应答**必须能挑中（这才是"扣了关键词也要能挑中"）。
    # ⚠ 假传输按**真机行为**只在 `clean` 那个关键词上给行：真站点拿带中文的整串
    #   搜不出它（这就是当初为什么抠关键词），拿 `GB 5009.12-2023` 搜它排第一。
    tr = FakeTransport(official=lambda kw: (
        _api_rows(_row("GB 5009.12-2023", "X09", "卫生、安全、劳动保护"))
        if kw == "GB 5009.12-2023" else {}))
    got = cf.resolve_ccs("GB 5009.12-2023食品安全国家标准", transport=tr)
    assert got["outcome"] == "found", got
    assert got["code"] == "X09"
    assert got["keyword_form"] == "clean"
    assert got["matched_no"] == "GB 5009.12-2023"


def test_keyword_forms_strip_trailing_junk():
    """**尾部杂字**要能抠掉（真机 380 篇实测：真库标准号字段混着中文）。

    `GB 5009.12-2023食品安全国家标准` 这种写法拿整串去搜当然搜不到；
    抠成 `GB 5009.12-2023` 就搜得到。号本身干净时 `clean` 与 `full` 同形、被去重。
    """
    forms = dict((f, k) for f, k, _t in cf.keyword_forms("GB 5009.12-2023食品安全国家标准"))
    assert forms["full"] == "GB 5009.12-2023食品安全国家标准"
    assert forms["clean"] == "GB 5009.12-2023"
    forms2 = dict((f, k) for f, k, _t in
                  cf.keyword_forms("GB/T 27668-2023显微镜光学显微术术语(1)"))
    assert forms2["clean"] == "GB/T 27668-2023"
    # 只加空格也是有效的一档（真机实测：`GB/T1.1-2020` 靠 clean 那档才中）
    assert dict((f, k) for f, k, _t in cf.keyword_forms("GB/T1.1-2020"))["clean"] \
        == "GB/T 1.1-2020"
    # 老写法（两位年代）要能抠出数字主体，并多试一次"补成四位"
    f3 = dict((f, k) for f, k, _t in cf.keyword_forms("GB 228-87"))
    assert "core" in f3 and f3["core"] == "228"
    assert f3["year4"] == "GB 228-1987"


def test_two_digit_year_year4_form_matches():
    """两位年代（`GB 228-87` = 1987 版）靠 `year4` 那档命中，且目标也是四位号。"""
    tr = FakeTransport(official=lambda kw: _api_rows(
        _row("GB 228-1987", "H22", "金属材料") if kw == "GB 228-1987" else {}))
    got = cf.resolve_ccs("GB 228-87", transport=tr)
    assert got["outcome"] == "found", got
    assert got["keyword_form"] == "year4" and got["matched_no"] == "GB 228-1987"


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


def test_lowercase_site_code_becomes_readable_uppercase_tag(db):
    """站点给**小写** ``a825`` 时，写出来的标签必须是**读得出来**的大写码。

    真机 380 篇实测抓到的（5 篇：``k73`` / ``w31`` / ``y54`` / ``c73`` / ``k24``）。
    读侧 ``doc_catalog`` 的解析正则是 ``^([A-Z])(\\d{2})`` —— 小写标签写进去，
    分类树**读不出来**，那篇照样落进"其他标准"兜底桶，等于白补。
    ⇒ 这条从**链路**一直钉到**分类树**（两端一起钉，防哪一端单独放松）。
    """
    tr = FakeTransport(official=lambda kw: _api_rows(_row("GB/T 32486-2016", "k73", "特殊灯具")))
    got = cf.resolve_ccs("GB/T 32486-2016", transport=tr)
    assert got["outcome"] == "found" and got["code"] == "K73", got
    assert got["major"] == "K"
    tag = cf.ccs_to_tag(got, "GB/T 32486-2016")
    assert tag == "CCS:K73 特殊灯具", tag
    # 读侧真的认得（不是"写进去了但树里读不出"）
    from src.core.knowledge.doc_catalog import classify_document
    cl = classify_document({
        "standard_no": "GB/T 32486-2016", "standard_name": "特殊灯具",
        "doc_type": "standard", "legal_hierarchy": "GB", "domain_tags": [tag]})
    assert cl["level2"].startswith("K "), cl
    assert cl["level4"].startswith("K73"), cl


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


# ═══════════ 10. 补前备份 / 精确回退（业主 2026-09-24 点名第①条） ═══════════
#
# 判据分两层：① **先备份、后写库**（第一次网络查询发生时，回退记录已经在盘上、
# 库里一个标签都还没写）；② **回退真能退**（domain_tags 与台账**逐字**回到改前），
# 并且**反向**：没被这一批选中的篇、别的标签，一行都不许动。

def _journals() -> list[Path]:
    """备份目录里现有的 ``ccs-undo-*.json``（按名字排序）。"""
    from src.core.knowledge import ccs_undo
    return sorted(ccs_undo.journal_dir().glob("ccs-undo-*.json"))


def test_undo_journal_is_written_before_the_first_write(db, monkeypatch):
    """**先备份、后写库**：第一次网络查询发生时，回退记录**已经在盘上**、
    且库里**一个 CCS 标签都还没写**。

    反向哨兵：把"写盘前先备份"那一步短路（或挪到起线程之后）⇒ 本用例必红。
    """
    _seed_doc("doc_ccs_u1", "GB/T 90300-2020", ["消防"])
    _seed_doc("doc_ccs_u2", "GB/T 90301-2020", [])
    pre = {"doc_ccs_u1": _raw_tags(db, "doc_ccs_u1"),
           "doc_ccs_u2": _raw_tags(db, "doc_ccs_u2")}
    before = {p.name for p in _journals()}
    seen: list[dict] = []

    def watch(no, name="", **kw):                       # noqa: ANN001, ANN003
        new = [p for p in _journals() if p.name not in before]
        seen.append({"no": no, "journals": [p.name for p in new],
                     "raw_u1": _raw_tags(db, "doc_ccs_u1"),
                     "raw_u2": _raw_tags(db, "doc_ccs_u2")})
        return {"outcome": "found", "code": "K41", "sub": "变压器",
                "source": "official_api", "keyword_form": "full",
                "matched_no": no, "attempts": []}

    monkeypatch.setattr(cf, "resolve_ccs", watch)
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_u1", "doc_ccs_u2"], pause_s=0.0)
    assert out["undo_journal"], out
    _wait_done()
    assert len(seen) == 2, seen
    assert all(s["journals"] for s in seen), \
        f"第一次查询发生时回退记录还不在盘上：{seen}"
    # **第一次查询发生时，整批的备份已在盘上、两篇都还是改前的样子**（一个字都没写）
    assert seen[0]["raw_u1"] == pre["doc_ccs_u1"], f"备份前就写了：{seen[0]}"
    assert seen[0]["raw_u2"] == pre["doc_ccs_u2"], f"备份前就写了：{seen[0]}"
    # 轮到自己那一篇时，它自己也还是改前的样子
    assert seen[1]["raw_u2"] == pre["doc_ccs_u2"], f"自己的备份还没写就动手了：{seen[1]}"
    # 第一篇的查询时刻：**整批两篇都还没有 CCS 标签**（备份在前、写库在后）
    assert "CCS:" not in seen[0]["raw_u1"] and "CCS:" not in seen[0]["raw_u2"]
    raw_before = pre["doc_ccs_u1"]
    payload = json.loads(Path(out["undo_journal"]).read_text(encoding="utf-8"))
    assert [r["doc_id"] for r in payload["records"]] == ["doc_ccs_u1", "doc_ccs_u2"]
    assert payload["records"][0]["domain_tags"] == raw_before, payload["records"][0]
    assert payload["records"][0]["ccs_state"] is None
    assert payload["records"][1]["domain_tags"] == "[]"
    assert payload["batch"]["doc_count"] == 2 and payload["pid"] > 0
    assert payload["created_at"] and payload["kind"] == "ccs-backfill-undo"
    # **状态接口如实下发路径**（业主点名：留回退说明要看得见）
    assert bf.ccs_backfill_status()["undo_journal"] == out["undo_journal"]
    assert _tags_of(db, "doc_ccs_u1") == ["消防", "CCS:K41 变压器"]


def test_undo_journal_honours_ks_backup_dir(db, monkeypatch, tmp_path):
    """回退记录落在**既有快照那个备份目录**，并**尊重 ``KS_BACKUP_DIR`` 覆盖**
    （自己拼 ``data_dir/backups`` 会让"备份在另一块盘"的部署把回退记录丢在数据盘上）。"""
    from src.core import config
    from src.core.knowledge import ccs_undo
    ext = tmp_path / "ext-backups"
    monkeypatch.setenv("KS_BACKUP_DIR", str(ext))
    _seed_doc("doc_ccs_u3", "GB/T 90302-2020", [])
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "found", "code": "K41", "sub": "变压器",
        "source": "official_api", "keyword_form": "full",
        "matched_no": no, "attempts": []})
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_u3"], pause_s=0.0)
    _wait_done()
    p = Path(out["undo_journal"])
    assert p.parent == ext, f"没尊重 KS_BACKUP_DIR：{p}"
    assert ccs_undo.journal_dir() == ext
    assert p.exists() and p.name.startswith("ccs-undo-")
    assert config.get_settings().data_dir / "backups" != ext


def test_backfill_refuses_to_start_when_journal_write_fails(db, monkeypatch):
    """**回退记录写不成 ⇒ 一篇都不写、当场报错**（"备份失败但照写"是明令禁止的）。"""
    from src.core.exceptions import KnowledgeStationError
    _seed_doc("doc_ccs_u4", "GB/T 90303-2020", [])
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "found", "code": "K41", "sub": "变压器", "source": "official_api",
        "keyword_form": "full", "matched_no": no, "attempts": []})
    from src.core.knowledge import ccs_undo as _undo
    real_write = _undo.write_undo_journal
    refuse = {"on": True}

    def flaky_write(*a, **kw):                          # noqa: ANN002, ANN003
        if refuse["on"]:
            raise KnowledgeStationError("磁盘满了（用例造的）", code="ccs_undo_failed")
        return real_write(*a, **kw)

    monkeypatch.setattr(_undo, "write_undo_journal", flaky_write)
    with pytest.raises(KnowledgeStationError) as ei:
        bf.start_ccs_backfill(doc_ids=["doc_ccs_u4"], pause_s=0.0)
    assert ei.value.code == "ccs_undo_failed"
    # 库**一个字节都没改**：没标签、没台账行
    assert _tags_of(db, "doc_ccs_u4") == []
    assert ccs_store.get_ccs_state("doc_ccs_u4") is None
    # 而且锁放掉了（不许因为"备份失败"把「补全分类号」永久锁死）
    assert bf._LOCK.locked() is False
    assert bf.ccs_backfill_status()["running"] is False
    # 备份恢复得了之后立刻还能起一批（证明锁真放掉了）
    refuse["on"] = False
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_u4"], pause_s=0.0)
    assert out["queued"] == 1
    _wait_done()
    assert _tags_of(db, "doc_ccs_u4") == ["CCS:K41 变压器"]


def test_revert_restores_tags_and_ledger_verbatim(db, monkeypatch):
    """**回退真能退**：``domain_tags`` 与 ``doc_ccs_state`` **逐字**回到改前。

    两篇各代表一种改前样子：一篇**改前没有任何台账行**（回退要把它删掉）、
    一篇**改前就有台账行**（回退要整行写回原值，连 ``checked_at``/``reason`` 都不许变）。
    """
    from src.core.knowledge import ccs_undo
    _seed_doc("doc_ccs_rv1", "GB/T 90310-2020", ["消防"])
    _seed_doc("doc_ccs_rv2", "GB/T 90311-2020", ["通用"])
    ccs_store.record_ccs_lookup("doc_ccs_rv2", {
        "outcome": "not_found", "reason": "改前就查过：查无",
        "attempts": [{"layer": "official_api", "result": "no_match"}]})
    raw_before = {d: _raw_tags(db, d) for d in ("doc_ccs_rv1", "doc_ccs_rv2")}
    state_before = {d: ccs_store.get_ccs_state(d)
                    for d in ("doc_ccs_rv1", "doc_ccs_rv2")}
    assert state_before["doc_ccs_rv1"] is None and state_before["doc_ccs_rv2"]

    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: (
        {"outcome": "found", "code": "K41", "sub": "变压器",
         "source": "official_api", "keyword_form": "full",
         "matched_no": no, "attempts": []}
        if no == "GB/T 90310-2020" else
        {"outcome": "not_found", "code": None, "source": None,
         "reason": "补的时候查无", "attempts": []}))
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_rv1", "doc_ccs_rv2"], pause_s=0.0)
    _wait_done()
    # 改完了：一篇多了标签与台账行，另一篇台账被改写
    assert _tags_of(db, "doc_ccs_rv1") == ["消防", "CCS:K41 变压器"]
    assert ccs_store.get_ccs_state("doc_ccs_rv1") is not None
    assert ccs_store.get_ccs_state("doc_ccs_rv2")["reason"] == "补的时候查无"

    res = ccs_undo.revert_ccs_backfill_journal(out["undo_journal"])
    assert res["restored"] == 2 and res["skipped"] == 0, res
    for d in ("doc_ccs_rv1", "doc_ccs_rv2"):
        assert _raw_tags(db, d) == raw_before[d], f"{d} 的 domain_tags 没逐字回到改前"
        assert ccs_store.get_ccs_state(d) == state_before[d], \
            f"{d} 的台账没逐字回到改前"


def test_revert_twice_is_safe(db, monkeypatch):
    """**回退两次是安全的**（幂等）：第二次一篇都不动，如实记"已经是改前的样子"。"""
    from src.core.knowledge import ccs_undo
    _seed_doc("doc_ccs_rv3", "GB/T 90312-2020", ["消防"])
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "found", "code": "Z12", "sub": "环境监测",
        "source": "local_table", "keyword_form": None,
        "matched_no": no, "attempts": []})
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_rv3"], pause_s=0.0)
    _wait_done()
    first = ccs_undo.revert_ccs_backfill_journal(out["undo_journal"])
    assert first["restored"] == 1 and first["skipped"] == 0, first
    snapshot = (_raw_tags(db, "doc_ccs_rv3"), ccs_store.get_ccs_state("doc_ccs_rv3"))
    second = ccs_undo.revert_ccs_backfill_journal(out["undo_journal"])
    assert second["restored"] == 0 and second["skipped"] == 1, second
    assert "已经是改前的样子" in second["skipped_docs"][0]["reason"]
    assert (_raw_tags(db, "doc_ccs_rv3"), ccs_store.get_ccs_state("doc_ccs_rv3")) \
        == snapshot
    # 默认路径（不传参）取的是**最近那一份**记录 —— 也是刚写的这一份
    assert Path(ccs_undo.latest_journal_path()).name == Path(out["undo_journal"]).name


def test_revert_does_not_touch_docs_outside_the_batch(db, monkeypatch):
    """**反向判据**：回退只动这一批记录里的篇 —— 没被选中的篇（含"也是缺号"的那些）
    的 ``domain_tags`` 与台账**一行都不许变**。

    这三篇是"同库里、同一种缺号状态"的对照：只有 ``rb1`` 进了这一批。
    """
    from src.core.knowledge import ccs_undo
    _seed_doc("doc_ccs_rb1", "GB/T 90320-2020", [])
    _seed_doc("doc_ccs_rb2", "GB/T 90321-2020", [])              # 同样缺号，没被选中
    _seed_doc("doc_ccs_rb3", "GB/T 90322-2020", ["CCS:K41 变压器"])  # 已经有号，没被选中
    others = ("doc_ccs_rb2", "doc_ccs_rb3")
    raw_before = {d: _raw_tags(db, d) for d in others}
    state_before = {d: ccs_store.get_ccs_state(d) for d in others}

    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "found", "code": "C65", "sub": "劳动安全技术综合",
        "source": "official_api", "keyword_form": "full",
        "matched_no": no, "attempts": []})
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_rb1"], pause_s=0.0)
    _wait_done()
    assert _tags_of(db, "doc_ccs_rb1") == ["CCS:C65 劳动安全技术综合"]
    ccs_undo.revert_ccs_backfill_journal(out["undo_journal"])
    assert _tags_of(db, "doc_ccs_rb1") == []
    assert ccs_store.get_ccs_state("doc_ccs_rb1") is None
    for d in others:
        assert _raw_tags(db, d) == raw_before[d], f"{d} 不在这一批里，却被回退动了"
        assert ccs_store.get_ccs_state(d) == state_before[d], f"{d} 的台账被回退动了"


# ═══════ 11. 「为什么停」+「还剩多少」拆开说（业主 2026-09-24 点名第②条） ═══════

def test_missing_split_partitions_and_tracks_each_bucket(db):
    """``missing_split`` **五桶之和 == total**，且每一桶按台账 ``outcome`` 如实归类。

    用**增量**判（会话级临时库里还有别的用例的篇）：新造的 5 篇各进一桶，各 +1。
    """
    bf.missing_ccs_split()                        # 预热（顺便证明没行时也不炸）
    before = bf.missing_ccs_split()
    _seed_doc("doc_ccs_sp1", "GB/T 90330-2020", [])          # 从来没查过
    _seed_doc("doc_ccs_sp2", "GB/T 90331-2020", [])
    ccs_store.record_ccs_lookup("doc_ccs_sp2", {
        "outcome": "not_found", "reason": "查无", "attempts": []})
    _seed_doc("doc_ccs_sp3", "GB/T 90332-2020", [])
    ccs_store.record_ccs_lookup("doc_ccs_sp3", {
        "outcome": "network_failed", "reason": "一个站点都没答上", "attempts": []})
    _seed_doc("doc_ccs_sp4", "GB/T 90333-2020", [])
    ccs_store.record_ccs_lookup("doc_ccs_sp4", {
        "outcome": "not_applicable", "reason": "号不像标准号", "attempts": []})
    _seed_doc("doc_ccs_sp5", "GB/T 90334-2020", [])
    ccs_store.record_ccs_lookup("doc_ccs_sp5", {
        "outcome": "found", "code": "K41", "sub": "变压器",
        "source": "official_api", "attempts": []})           # 台账说 found、标签却不在
    after = bf.missing_ccs_split()
    assert after["never_checked"] - before["never_checked"] == 1, (before, after)
    assert after["checked_not_found"] - before["checked_not_found"] == 1
    assert after["checked_failed"] - before["checked_failed"] == 1
    assert after["not_applicable"] - before["not_applicable"] == 1
    assert after["found_but_untagged"] - before["found_but_untagged"] == 1
    assert after["total"] - before["total"] == 5, (before, after)
    # 五桶必须把 total 解释干净（少一篇就是"谁都说不清去哪了"）
    assert (after["never_checked"] + after["checked_not_found"]
            + after["checked_failed"] + after["not_applicable"]
            + after["found_but_untagged"]) == after["total"], after
    assert after["total"] == bf.missing_ccs_count(), \
        "拆开的数字和 '还缺几篇' 对不上（现算的两次读数不一致）"


def test_stop_reason_limit_selected_done_and_no_candidates(db, monkeypatch):
    """**为什么停：各是各的值**（业主要求"不许合并成一个结束"）。

    * 到量（``limit``）；* 勾选的跑完（``selected_done``）；* 一开始就没候选
      （``no_candidates``，**不**说成"跑完了"）。
    """
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "not_found", "code": None, "source": None,
        "reason": "查无", "attempts": []})
    _seed_doc("doc_ccs_sr1", "GB/T 90340-2020", [])
    _seed_doc("doc_ccs_sr2", "GB/T 90341-2020", [])
    out = bf.start_ccs_backfill(limit=1, pause_s=0.0)
    assert out["queued"] == 1 and out["plan"]["truncated"] is True, out
    _wait_done()
    st = bf.ccs_backfill_status()
    assert st["stop_reason"] == bf.STOP_LIMIT, st
    assert st["stop_reason_label"] == bf.STOP_REASON_LABELS[bf.STOP_LIMIT]
    assert st["truncated"] is True and st["plan_total"] > 1

    _seed_doc("doc_ccs_sr3", "GB/T 90342-2020", [])
    _seed_doc("doc_ccs_sr4", "GB/T 90343-2020", [])
    out2 = bf.start_ccs_backfill(doc_ids=["doc_ccs_sr3", "doc_ccs_sr4"], pause_s=0.0)
    assert out2["queued"] == 2
    _wait_done()
    st2 = bf.ccs_backfill_status()
    assert st2["stop_reason"] == bf.STOP_SELECTED_DONE, st2
    assert st2["stop_reason_label"] and st2["stop_reason"] != bf.STOP_EXHAUSTED

    # 一开始就没候选：给一篇已经有分类号的（``force=False`` ⇒ 它不是候选）
    _seed_doc("doc_ccs_sr5", "GB/T 90344-2020", ["CCS:K41 变压器"])
    out3 = bf.start_ccs_backfill(doc_ids=["doc_ccs_sr5"], pause_s=0.0)
    assert out3["queued"] == 0 and out3["undo_journal"] is None, out3
    st3 = bf.ccs_backfill_status()
    assert st3["stop_reason"] == bf.STOP_NO_CANDIDATES, st3
    assert st3["stop_reason_label"] and st3["running"] is False


def test_selected_batch_cut_by_limit_says_limit_not_selected_done(db, monkeypatch):
    """**F1（复核 MED，2026-09-24 修）**：勾选批次被 ``limit`` 截过 ⇒ 说"到量"，
    且**没轮到的那几篇一行都没动**（反向判据）。

    为什么今天就能发生：路由**永远**把默认 ``limit=50`` 一起传下来
    （``routes_kb_folders.py``）⇒ "勾 60 篇只跑 50 篇、剩 10 篇一行没动"。
    那一刻说 ``selected_done``（"勾选的那几篇跑完了"）就是**界面说假话**。
    """
    _seed_doc("doc_ccs_f1a", "GB/T 90400-2020", [])
    _seed_doc("doc_ccs_f1b", "GB/T 90401-2020", [])
    _seed_doc("doc_ccs_f1c", "GB/T 90402-2020", [])
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "found", "code": "K41", "sub": "变压器", "source": "official_api",
        "keyword_form": "full", "matched_no": no, "attempts": []})
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_f1a", "doc_ccs_f1b", "doc_ccs_f1c"],
                               limit=2, pause_s=0.0)
    assert out["queued"] == 2 and out["plan"]["total"] == 3, out
    assert out["plan"]["truncated"] is True
    _wait_done()
    st = bf.ccs_backfill_status()
    assert st["stop_reason"] == bf.STOP_LIMIT, st          # ← 不是 selected_done
    assert st["stop_reason_label"] == bf.STOP_REASON_LABELS[bf.STOP_LIMIT]
    assert st["scope"] == "selected" and st["truncated"] is True, st
    # 反向：没轮到的那一篇没标签、没台账；轮到的两篇真补上了
    left = {"doc_ccs_f1a", "doc_ccs_f1b", "doc_ccs_f1c"} - {
        r["doc_id"] for r in st["results"]}
    assert len(left) == 1, st["results"]
    untouched = left.pop()
    assert _tags_of(db, untouched) == [], f"{untouched} 没轮到却被写了标签"
    assert ccs_store.get_ccs_state(untouched) is None, f"{untouched} 没轮到却落了台账"
    assert st["missing_split"]["total"] == st["missing"] >= 1, st


def test_decide_stop_reason_truth_table(monkeypatch):
    """**七个值互斥且各是各的**：决策函数按优先级取一个（不许有"两个都对"的糊账）。

    这一条是上一条的**真值表**：``exhausted`` / ``hard_cap`` / ``cancelled`` 在
    会话级临时库里造不出稳定现场，所以直接钉决策函数（纯函数，没有 IO）。

    ⚠ **``truncated=True`` + ``scope='selected'`` 必须是 ``limit``**（复核 F1，2026-09-24）：
    路由永远把默认 ``limit=50`` 一起传给勾选批次 ⇒ "勾了 60 篇只跑 50 篇"时**剩 10 篇
    一行没动**，那一刻说 ``selected_done``（"勾选的那几篇跑完了"）就是**界面说假话**。
    这条组合以前被本真值表**冻成了错规格**（绿着骗人），现在钉死成 ``limit``。
    """
    monkeypatch.setitem(bf._PROGRESS, "cancelled", False)
    monkeypatch.setitem(bf._PROGRESS, "hard_capped", False)
    monkeypatch.setitem(bf._PROGRESS, "scope", "library")
    monkeypatch.setitem(bf._PROGRESS, "truncated", False)
    assert bf._decide_stop_reason() == bf.STOP_EXHAUSTED
    monkeypatch.setitem(bf._PROGRESS, "truncated", True)
    assert bf._decide_stop_reason() == bf.STOP_LIMIT
    # ↑ 这一档**先于** scope 判：勾选的批次被量截过 ⇒ 说"到量"，不说"勾选的跑完了"
    monkeypatch.setitem(bf._PROGRESS, "scope", "selected")
    assert bf._decide_stop_reason() == bf.STOP_LIMIT, \
        "被 limit 截过的勾选批次说成了 selected_done（界面会说假话）"
    monkeypatch.setitem(bf._PROGRESS, "truncated", False)
    assert bf._decide_stop_reason() == bf.STOP_SELECTED_DONE
    monkeypatch.setitem(bf._PROGRESS, "scope", "all")
    assert bf._decide_stop_reason() == bf.STOP_EXHAUSTED
    monkeypatch.setitem(bf._PROGRESS, "hard_capped", True)
    assert bf._decide_stop_reason() == bf.STOP_HARD_CAP
    monkeypatch.setitem(bf._PROGRESS, "cancelled", True)
    assert bf._decide_stop_reason() == bf.STOP_CANCELLED
    # 七个值两两不同，且每个都有中文说法（界面靠后端下发，不自己编）
    values = {bf.STOP_NO_CANDIDATES, bf.STOP_EXHAUSTED, bf.STOP_LIMIT,
              bf.STOP_HARD_CAP, bf.STOP_SELECTED_DONE, bf.STOP_CANCELLED,
              bf.STOP_ERROR}
    assert len(values) == 7
    assert values <= set(bf.STOP_REASON_LABELS)
    assert len(set(bf.STOP_REASON_LABELS.values())) == 7, "七种「为什么停」的说法不许重样"


def test_revert_also_restores_updated_at(db, monkeypatch):
    """**F2（复核 MED，2026-09-24 修）**：回退要把 ``updated_at`` 也**逐字**退回去。

    复核现场：改前 ``2001-01-01 00:00:00`` → 补后 / 回退后都是 ``2026-09-23 17:45:50``
    （``domain_tags`` 已逐字回退，只有这一列没回）。这里把那个现场造出来：先把
    ``updated_at`` 钉到 2001 年（**不与"现在"同秒** —— "同秒巧合"当不了反证），
    补完必须真的变过，回退必须逐字回来；再退一次仍然幂等。
    """
    from src.core.knowledge import ccs_undo
    _seed_doc("doc_ccs_ua1", "GB/T 90410-2020", [])
    db.execute("UPDATE doc_meta SET updated_at=? WHERE doc_id=?",
               ("2001-01-01 00:00:00", "doc_ccs_ua1"))
    db.commit()
    before = _raw_updated_at(db, "doc_ccs_ua1")
    assert before == "2001-01-01 00:00:00", before
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "found", "code": "K41", "sub": "变压器", "source": "official_api",
        "keyword_form": "full", "matched_no": no, "attempts": []})
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_ua1"], pause_s=0.0)
    _wait_done()
    assert _raw_updated_at(db, "doc_ccs_ua1") != before, \
        "这一批根本没动 updated_at？那这条用例证明不了什么"
    res = ccs_undo.revert_ccs_backfill_journal(out["undo_journal"])
    assert res["restored"] == 1, res
    assert "updated_at" in res["restored_docs"][0]["restored"], res
    assert _raw_updated_at(db, "doc_ccs_ua1") == before, "updated_at 没逐字回到改前"
    # 幂等：``updated_at`` 也算在"是不是改前的样子"里
    second = ccs_undo.revert_ccs_backfill_journal(out["undo_journal"])
    assert second["restored"] == 0 and second["skipped"] == 1, second


def test_db_path_is_honoured_by_the_worker_thread(db, tmp_path, monkeypatch):
    """**F3（复核 LOW，2026-09-24 修）**：``db_path`` 必须一路传到**干活线程**。

    旧样子：``db_path`` 只喂给 plan 与回退记录，干活线程写的是**默认库**
    ⇒ 回退记录描述的是 X、改动落在 Y（复核探针 7）。生产路由不传 ``db_path``，
    所以它是**陷阱**不是现患 —— 这里开第二个库把它钉死；顺带钉住"``str`` 形状的
    ``db_path`` 不再在 ``path.parent`` 上 AttributeError"。
    """
    from src.core.storage.sqlite_db import get_db_connection, init_schema
    other = tmp_path / "other.db"
    init_schema(other)
    _seed_doc("doc_ccs_other", "GB/T 90420-2020", [], db_path=other)
    assert db.execute("SELECT 1 FROM doc_meta WHERE doc_id=?",
                      ("doc_ccs_other",)).fetchone() is None, "基线：默认库里没有这一篇"
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "found", "code": "K41", "sub": "变压器", "source": "official_api",
        "keyword_form": "full", "matched_no": no, "attempts": []})
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_other"], db_path=other, pause_s=0.0)
    assert out["queued"] == 1, out
    _wait_done()
    oc = get_db_connection(other)
    assert json.loads(oc.execute("SELECT domain_tags FROM doc_meta WHERE doc_id=?",
                                 ("doc_ccs_other",)).fetchone()[0]) \
        == ["CCS:K41 变压器"], "标签没落在 db_path 指的库里"
    assert ccs_store.get_ccs_state("doc_ccs_other", db_path=other) is not None
    # 反向：默认库**一个字节都没动**
    assert db.execute("SELECT 1 FROM doc_meta WHERE doc_id=?",
                      ("doc_ccs_other",)).fetchone() is None
    # str 形状也认（复核 F3 的第二半：以前会在 sqlite_db 的 path.parent 上 AttributeError）
    assert bf.missing_ccs_count(db_path=str(other)) == 0
    assert ccs_store.ccs_tag_of(oc.execute(
        "SELECT domain_tags FROM doc_meta WHERE doc_id=?",
        ("doc_ccs_other",)).fetchone()[0]) == "CCS:K41 变压器"


def test_broken_domain_tags_is_refused_not_silently_wiped(db, monkeypatch):
    """**F4（复核 LOW，2026-09-24 修）**：``domain_tags`` 非空却不是 JSON 数组 ⇒ **拒改**，
    不许"坏值当空"把别的标签整片冲掉（探针 6：``'消防、通用'`` → ``'["CCS:K41 变压器"]'``）。

    真库当前 0 命中（复核只读核过）⇒ 这是**潜伏口**；但标签被冲掉是**不可逆**的，
    所以写路径**宁可拒改、不许猜**（读路径仍然宽松，界面照常显示）。
    """
    from src.core.exceptions import KnowledgeStationError
    _seed_doc("doc_ccs_f4", "GB/T 90430-2020", [])
    db.execute("UPDATE doc_meta SET domain_tags=? WHERE doc_id=?",
               ("消防、通用", "doc_ccs_f4"))
    db.commit()
    assert _raw_tags(db, "doc_ccs_f4") == "消防、通用"
    # ① 直接调写路径：拒改 + 明确错误码，原文**一个字没变**
    with pytest.raises(KnowledgeStationError) as ei:
        ccs_store.apply_ccs_tag("doc_ccs_f4", "CCS:K41 变压器")
    assert ei.value.code == "invalid_domain_tags"
    assert _raw_tags(db, "doc_ccs_f4") == "消防、通用"
    # ② 走整批：这一篇如实记 "拒绝改它"，旁边的正常篇照常补上（不许一篇坏值拖垮整批）
    _seed_doc("doc_ccs_f4b", "GB/T 90431-2020", [])
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "found", "code": "K41", "sub": "变压器", "source": "official_api",
        "keyword_form": "full", "matched_no": no, "attempts": []})
    bf.start_ccs_backfill(doc_ids=["doc_ccs_f4", "doc_ccs_f4b"], pause_s=0.0)
    _wait_done()
    row = ccs_store.get_ccs_state("doc_ccs_f4")
    assert row is not None and row["outcome"] == "parse_failed", row
    assert "拒绝改它" in row["reason"], row
    assert json.loads(row["attempts_json"])[0]["result"] == "domain_tags_unparsable", row
    assert _raw_tags(db, "doc_ccs_f4") == "消防、通用", "坏值被冲掉了（不可逆）"
    assert _tags_of(db, "doc_ccs_f4b") == ["CCS:K41 变压器"]


def test_stop_reason_exhausted_when_plan_had_no_remainder(db, monkeypatch):
    """``exhausted`` = **候选扫完了**（计划里没有剩余候选），不是"全库都补上了"。

    ⚠ 造现场：注入一个"只有 1 篇候选、且没有截断"的计划 —— 会话级临时库里
    永远还有别的用例留下的缺号篇，真实的"全库零候选"造不出来。
    """
    _seed_doc("doc_ccs_ex1", "GB/T 90345-2020", [])
    monkeypatch.setattr(bf, "plan_ccs_backfill", lambda **kw: {
        "candidates": [{"doc_id": "doc_ccs_ex1", "standard_no": "GB/T 90345-2020",
                        "standard_name": "测试 GB/T 90345-2020"}],
        "total": 1, "already_have": 0, "limit": kw.get("limit") or 0,
        "truncated": False})
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "not_found", "code": None, "source": None,
        "reason": "查无", "attempts": []})
    out = bf.start_ccs_backfill(limit=50, pause_s=0.0)
    assert out["queued"] == 1
    _wait_done()
    st = bf.ccs_backfill_status()
    assert st["stop_reason"] == bf.STOP_EXHAUSTED, st
    # 如实：还剩多少照样现算下发（"候选扫完"不等于"全库补完"）
    assert st["missing"] and st["missing_split"]["total"] == st["missing"]


def test_all_mode_pages_serially_and_stops_at_hard_cap(db, monkeypatch):
    """**「全部补完」**：按 ``MAX_BACKFILL_DOCS`` 一页一页串行，撞硬上限就停，**如实说**。

    反向判据（三条）：① 同一篇**不许被查两次**（候选名单只取一次，重查失败篇
    会让"全部"变成死循环）；② 到上限后**没被选中的篇一篇都不许动**（标签净增 == 上限）；
    ③ 停的是 ``hard_cap``，**不是** ``exhausted``（不许假装补完）。
    """
    monkeypatch.setattr(bf, "MAX_BACKFILL_DOCS", 1)       # 一页一篇 ⇒ 分页真的在走
    monkeypatch.setattr(bf, "MAX_BACKFILL_ALL", 2)        # 硬上限 2 篇
    _seed_doc("doc_ccs_al1", "GB/T 90350-2020", [])
    _seed_doc("doc_ccs_al2", "GB/T 90351-2020", [])
    _seed_doc("doc_ccs_al3", "GB/T 90352-2020", [])
    seen: list[str] = []

    def spy(no, name="", **kw):                          # noqa: ANN001, ANN003
        seen.append(no)
        return {"outcome": "found", "code": "K41", "sub": "变压器",
                "source": "official_api", "keyword_form": "full",
                "matched_no": no, "attempts": []}

    monkeypatch.setattr(cf, "resolve_ccs", spy)
    missing_before = bf.missing_ccs_count()
    out = bf.start_ccs_backfill(all_docs=True, pause_s=0.0)
    assert out["queued"] == 2, out
    assert out["pages"] == 2 and out["hard_capped"] is True, out
    assert out["plan"]["total"] > 2, out                    # 候选比上限多 ⇒ 确实有"还剩"
    _wait_done()
    st = bf.ccs_backfill_status()
    assert st["stop_reason"] == bf.STOP_HARD_CAP, st
    assert st["stop_reason_label"] == bf.STOP_REASON_LABELS[bf.STOP_HARD_CAP]
    assert st["page"] == 2 and st["pages"] == 2
    assert len(seen) == 2 and len(set(seen)) == 2, f"有篇被查了不止一次：{seen}"
    # 反向：只有这 2 篇真的补上了（第 3 篇及别的都没被动）
    assert bf.missing_ccs_count() == missing_before - 2, "到上限之后还在改库"
    assert st["missing"] == bf.missing_ccs_count()
    mine = {"GB/T 90350-2020": "doc_ccs_al1",
            "GB/T 90351-2020": "doc_ccs_al2",
            "GB/T 90352-2020": "doc_ccs_al3"}
    for no, doc in mine.items():
        if no in seen:
            assert _tags_of(db, doc) == ["CCS:K41 变压器"], doc
        else:
            assert _tags_of(db, doc) == [], f"{doc} 没被这一批选中，却被写上了标签"
            assert ccs_store.get_ccs_state(doc) is None, f"{doc} 没被选中却落了台账"
    assert len([no for no in mine if no in seen]) <= 2


def test_all_mode_refuses_doc_ids_and_allows_zero_limit(db, monkeypatch):
    """``all`` 与勾选篇目**不能同时用**（两件事）；``all`` 时 ``limit`` 不再是必填 1~200。"""
    _seed_doc("doc_ccs_al4", "GB/T 90353-2020", [])
    with pytest.raises(ValueError, match="不能同时用"):
        bf.start_ccs_backfill(doc_ids=["doc_ccs_al4"], all_docs=True, pause_s=0.0)
    monkeypatch.setattr(bf, "MAX_BACKFILL_ALL", 1)
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "not_found", "code": None, "source": None,
        "reason": "查无", "attempts": []})
    out = bf.start_ccs_backfill(all_docs=True, limit=0, pause_s=0.0)
    assert out["queued"] == 1 and out["hard_capped"] is True, out
    _wait_done()
    assert bf.ccs_backfill_status()["stop_reason"] == bf.STOP_HARD_CAP


# ═══════ 12. 复核抓到的真缺陷：HIGH-1 / MED-1 / MED-2 / MED-5 / LOW-4 / LOW-5 ═══════

def test_apply_ccs_tag_replaces_instead_of_appending(db):
    """**HIGH-1**：同一篇**只许有一条** ``CCS:`` 标签 —— 换号是**替换**（就地），不是追加。

    旧实现 append 第二条，而读侧只取第一条 ⇒ 刷新静默无效、台账与树打架。
    """
    _seed_doc("doc_ccs_rep1", "GB/T 90360-2020", ["消防", "CCS:K41 变压器"])
    first = ccs_store.apply_ccs_tag("doc_ccs_rep1", "CCS:C65 劳动安全技术综合")
    assert first["applied"] is True, first
    assert first["replaced"] == "CCS:K41 变压器", first
    tags = _tags_of(db, "doc_ccs_rep1")
    assert tags == ["消防", "CCS:C65 劳动安全技术综合"], tags
    assert sum(1 for t in tags if t.startswith("CCS:")) == 1, tags
    assert "消防" in tags, "别的标签被动了（红线）"
    # 同一个号再来一次：一个字都不改（幂等）
    second = ccs_store.apply_ccs_tag("doc_ccs_rep1", "CCS:C65 劳动安全技术综合")
    assert second["applied"] is False
    assert _tags_of(db, "doc_ccs_rep1").count("CCS:C65 劳动安全技术综合") == 1
    # 历史遗留的多条也收成一条（修既有错数据）
    _seed_doc("doc_ccs_rep2", "GB/T 90361-2020", ["CCS:K41 变压器", "消防", "CCS:Z12 环境监测"])
    third = ccs_store.apply_ccs_tag("doc_ccs_rep2", "CCS:C65 劳动安全技术综合")
    tags2 = _tags_of(db, "doc_ccs_rep2")
    assert third["applied"] is True
    assert [t for t in tags2 if t.startswith("CCS:")] == ["CCS:C65 劳动安全技术综合"], tags2
    assert "消防" in tags2, tags2


def test_force_refresh_tag_and_tree_read_the_same_code(db, monkeypatch):
    """**HIGH-1 的端到端判据**：``force=True``（刷新）之后，**台账与分类树读到同一个码**。

    ⚠ 旧实现下这条必红：刷新 append 出第二条 ``CCS:C65``，而 ``doc_catalog``
    读第一条（还是 ``K41``）⇒ 台账说 C65、树挂在 K41。
    """
    from src.core.knowledge.doc_catalog import classify_document
    _seed_doc("doc_ccs_rep3", "GB/T 90362-2020", ["消防", "CCS:K41 变压器"])
    ccs_store.record_ccs_lookup("doc_ccs_rep3", {
        "outcome": "found", "source": "official_api", "keyword_form": "full",
        "matched_no": "GB/T 90362-2020", "code": "K41", "sub": "变压器",
        "reason": "", "attempts": []})
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "found", "code": "C65", "sub": "劳动安全技术综合",
        "source": "official_api", "keyword_form": "full",
        "matched_no": no, "attempts": []})
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_rep3"], force=True, pause_s=0.0)
    assert out["queued"] == 1, out
    _wait_done()
    tags = _tags_of(db, "doc_ccs_rep3")
    assert tags == ["消防", "CCS:C65 劳动安全技术综合"], tags
    row = ccs_store.get_ccs_state("doc_ccs_rep3")
    assert row["ccs_code"] == "C65", row
    cl = classify_document({"standard_no": "GB/T 90362-2020", "standard_name": "测试",
                            "doc_type": "standard", "legal_hierarchy": "GB",
                            "domain_tags": tags})
    assert cl["level4"].startswith("C65"), cl
    # 台账的码 == 树的码（同一件事一个来源）
    assert cl["level4"].split()[0] == row["ccs_code"]


def test_backfill_classifies_exceptions_by_type_not_all_network(db, monkeypatch):
    """**MED-1 + MED-2**：异常**按类型如实归类并落台账** —— 代码缺陷**不许**冒充网络问题。

    旧实现是 ``except Exception`` 一律记 ``network_failed``（复核实测：``RuntimeError``
    ⇒ ``outcome=network_failed``），把"我们自己的 bug"说成"网络不通"。
    """
    _seed_doc("doc_ccs_ec1", "GB/T 90370-2020", [])
    _seed_doc("doc_ccs_ec2", "GB/T 90371-2020", [])

    def broken(no, name="", **kw):                      # noqa: ANN001, ANN003
        if no == "GB/T 90370-2020":
            raise ConnectionError("网络断了（用例造的）")
        raise RuntimeError("boom（用例造的代码缺陷）")

    monkeypatch.setattr(cf, "resolve_ccs", broken)
    bf.start_ccs_backfill(doc_ids=["doc_ccs_ec1", "doc_ccs_ec2"], pause_s=0.0)
    _wait_done()
    net = ccs_store.get_ccs_state("doc_ccs_ec1")
    inner = ccs_store.get_ccs_state("doc_ccs_ec2")
    assert net is not None and inner is not None, "异常路径**必须落台账**（否则就是静默）"
    assert net["outcome"] == "network_failed", net
    assert "网络层出错" in net["reason"]
    assert inner["outcome"] == "parse_failed", inner
    assert "内部出错" in inner["reason"] and "RuntimeError" in inner["reason"]
    assert "网络层出错" not in inner["reason"]
    # 流水里**逐字**看得出是内部错误（审计与界面能分开看）
    att = json.loads(inner["attempts_json"])
    assert att[0]["layer"] == "internal" and att[0]["result"] == "internal_error", att
    assert "boom" in att[0]["detail"]
    net_att = json.loads(net["attempts_json"])
    assert net_att[0]["result"] == "network_error", net_att
    # 状态里的失败清单也如实（两种结论各是各的），且 last_error 不再是恒 None 的死字段
    st = bf.ccs_backfill_status()
    outcomes = {f["doc_id"]: f["outcome"] for f in st["failures"]}
    assert outcomes["doc_ccs_ec1"] == "network_failed"
    assert outcomes["doc_ccs_ec2"] == "parse_failed"
    assert st["last_error"], "last_error 是个恒为 None 的死字段（LOW-5）"


def test_run_loop_error_does_not_wedge_running_and_lock(db, monkeypatch):
    """**MED-5**：循环体外的异常**不许**把 ``running`` 与锁永久卡死。

    旧实现没有 try/finally ⇒ 异常一出，``running`` 永远是 True、锁永不释放，
    用户只能重启进程。反向哨兵：把 ``try/finally`` 去掉 ⇒ 本用例必红（跑不回来）。
    """
    _seed_doc("doc_ccs_lk1", "GB/T 90380-2020", [])
    _seed_doc("doc_ccs_lk2", "GB/T 90381-2020", [])
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "not_found", "code": None, "source": None,
        "reason": "查无", "attempts": []})
    orig = bf._update_counts
    boom = {"on": True}

    def flaky(rec):                                     # noqa: ANN001
        if boom["on"]:
            raise RuntimeError("boom（用例造的：循环体外出错）")
        return orig(rec)

    monkeypatch.setattr(bf, "_update_counts", flaky)
    out = bf.start_ccs_backfill(doc_ids=["doc_ccs_lk1", "doc_ccs_lk2"], pause_s=0.0)
    assert out["queued"] == 2
    _wait_flag(lambda: not bf.ccs_backfill_status()["running"], timeout_s=5.0)
    st = bf.ccs_backfill_status()
    assert st["stop_reason"] == bf.STOP_ERROR, st
    assert "boom" in (st["last_error"] or ""), st
    assert bf._LOCK.locked() is False, "循环体外出错之后锁没放掉（永久卡死）"
    # 恢复之后还能立刻再起一批（这才是"没卡死"）
    boom["on"] = False
    out2 = bf.start_ccs_backfill(doc_ids=["doc_ccs_lk1"], pause_s=0.0)
    assert out2["queued"] == 1
    _wait_done()
    assert ccs_store.get_ccs_state("doc_ccs_lk1") is not None
    assert bf.ccs_backfill_status()["stop_reason"] == bf.STOP_SELECTED_DONE


# ═══════════════════════════ 13. 接口外形（本批新增字段） ═══════════════════════════

def test_api_ccs_summary_reports_stop_reasons_and_split(client, db):
    """``/kb/ccs/summary`` 把"还剩多少（拆开）"与"为什么停"的说法**由后端下发**。"""
    from _kb_folder_api_fixtures import data_of
    c, token = client
    _seed_doc("doc_ccs_api5", "GB/T 90390-2020", [])
    s = data_of(_api(c, token, "get", "/api/v1/kb/ccs/summary"))
    assert s["max_all"] > 0 and s["max_batch"] > 0 and s["default_batch"] > 0
    assert set(s["stop_reason_labels"]) == {
        "no_candidates", "exhausted", "limit", "hard_cap", "selected_done",
        "cancelled", "error"}
    assert s["missing_split"]["total"] == s["missing"] >= 1
    assert (s["missing_split"]["never_checked"] + s["missing_split"]["checked_not_found"]
            + s["missing_split"]["checked_failed"] + s["missing_split"]["not_applicable"]
            + s["missing_split"]["found_but_untagged"]) == s["missing_split"]["total"]
    assert "undo_journal" in s["backfill"]


def test_api_ccs_backfill_all_flag(client, db, monkeypatch):
    """``POST /kb/ccs/backfill {"all": true}``：分页跑到硬上限并**如实**说停在硬上限；
    与勾选篇目同时用 ⇒ 422（不静默取一个）。"""
    from _kb_folder_api_fixtures import data_of
    c, token = client
    monkeypatch.setattr(bf, "MAX_BACKFILL_DOCS", 1)
    monkeypatch.setattr(bf, "MAX_BACKFILL_ALL", 1)
    _seed_doc("doc_ccs_api6", "GB/T 90391-2020", [])
    monkeypatch.setattr(cf, "resolve_ccs", lambda no, name="", **kw: {
        "outcome": "not_found", "code": None, "source": None,
        "reason": "查无", "attempts": []})
    out = data_of(_api(c, token, "post", "/api/v1/kb/ccs/backfill",
                       json={"all": True, "limit": 0}))
    assert out["queued"] == 1 and out["hard_capped"] is True, out
    assert out["undo_journal"], "「全部补完」也必须先写回退记录"
    _wait_done()
    st = data_of(_api(c, token, "get", "/api/v1/kb/ccs/backfill/status"))
    assert st["stop_reason"] == "hard_cap" and st["stop_reason_label"], st
    r = _api(c, token, "post", "/api/v1/kb/ccs/backfill",
             json={"all": True, "doc_ids": ["doc_ccs_api6"]})
    assert r.status_code == 422, r.text


# ═══════════════════════════ 工具 ═══════════════════════════

def _seed_doc(doc_id: str, standard_no: str, tags: list[str],
              doc_type: str = "standard", db_path=None) -> None:  # noqa: ANN001
    """直接写一行 `doc_meta`（走**唯一所有者** `clause_repo.insert_document`）。

    ``db_path`` 省略 = 会话级临时库（默认）；给了就写**那个**库（F3 用第二个库）。
    """
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    with write_transaction(db_path) as conn:
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


def _raw_tags(db, doc_id: str) -> str | None:          # noqa: ANN001
    """``domain_tags`` 的**原文**（不解析）—— "逐字回到改前"要按字节比。"""
    row = db.execute("SELECT domain_tags FROM doc_meta WHERE doc_id=?",
                     (doc_id,)).fetchone()
    assert row is not None, f"库里没有这一篇：{doc_id}"
    return row[0]


def _raw_updated_at(db, doc_id: str) -> str | None:     # noqa: ANN001
    """``doc_meta.updated_at`` 的原文（F2：回退的**第三处**也要逐字比）。"""
    row = db.execute("SELECT updated_at FROM doc_meta WHERE doc_id=?",
                     (doc_id,)).fetchone()
    assert row is not None, f"库里没有这一篇：{doc_id}"
    return row[0]


def _wait_flag(pred, timeout_s: float = 20.0) -> None:  # noqa: ANN001
    """等一个条件成真（超时抛 —— **不许**用 sleep 假装它成真了）。"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if pred():
            return
        time.sleep(0.05)
    raise AssertionError(f"条件在 {timeout_s}s 内没成真（用例不该挂在这里）")


def _wait_done(timeout_s: float = 20.0) -> None:
    """等后台线程跑完（超时就抛 —— **不许**用 sleep 假装跑完了）。"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if not bf.ccs_backfill_status()["running"]:
            return
        time.sleep(0.05)
    raise AssertionError("后台补全线程超时还没结束（用例不该挂在这里）")
