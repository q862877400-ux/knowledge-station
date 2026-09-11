"""公告发现测试（契约增量见 pipeline/03「公告发现」节）：URL 归一化/SSRF/解析启发式/
源 CRUD 校验/扫描编排（transport 注入零联网）/去重幂等/首扫基线/时间闸。

全部离线（conftest KS_DATA_DIR 会话隔离 + fake transport），唯一前缀防共享库串扰。
"""
from __future__ import annotations

import time

import pytest

from src.core.update import announce
from src.core.update.channels.base import (
    UPD_ANNOUNCE_SCAN_ALREADY_RUNNING,
    UPD_ANNOUNCE_SOURCE_NOT_FOUND,
    UPD_ILLEGAL_SOURCE_PAYLOAD,
    UpdateError,
)


@pytest.fixture(autouse=True)
def _clean_announce_state(db):
    """同文件用例共享库：每用例前后清空源配置/扫描状态/已见公告，防串扰。"""
    from src.core.storage.sqlite_db import get_db_connection, write_transaction

    def _clean():
        announce._write_json_key(announce.SOURCES_KEY, [])
        announce._write_json_key(announce.STATE_KEY, {})
        with write_transaction() as txn:
            txn.execute("DELETE FROM announcement_observed")
    _clean()
    yield
    _clean()

# ---------------------------------------------------------------- 工具
class _FakeTransport:
    """按 URL 返回固定页面；未命中 URL → 404。记录调用清单。"""

    def __init__(self, pages: dict[str, tuple[int, str]]):
        self.pages = pages
        self.calls: list[str] = []

    def fetch(self, url: str, **kw):
        self.calls.append(url)
        return self.pages.get(url, (404, "not found"))


def _page(*links: tuple[str, str]) -> str:
    """拼一个最小列表页：<a href>text</a> 序列。"""
    return "<html><body>" + "".join(
        f'<a href="{href}">{text}</a>' for href, text in links) + "</body></html>"


def _wait_done(timeout_s: float = 8.0) -> dict:
    """轮询等待 daemon 扫描线程到终态（done/failed），返回最终 state。"""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        state = announce.get_scan_state()
        if state.get("status") in ("done", "failed"):
            return state
        time.sleep(0.05)
    raise AssertionError(f"扫描未在 {timeout_s}s 内到终态: {announce.get_scan_state()}")


# ---------------------------------------------------------------- URL 归一化
def test_ann_n01_normalize_url_variants():
    """尾斜杠/默认端口/大写 host/追踪参数/fragment 归一为同串 → 同 hash；
    非追踪 query 保留且按 key 排序（带 query 与无 query 是不同 URL）。"""
    base = announce.normalize_url("https://WWW.Example.com/a/list/")
    no_query = [
        "https://www.example.com/a/list",
        "https://www.example.com:443/a/list/",
    ]
    for v in no_query:
        assert announce.normalize_url(v) == base, v
        assert announce.url_hash(v) == announce.url_hash(base)
    # 追踪参数剔除 + 其余 query 排序：同 query 变体归一为同串
    base_q = announce.normalize_url("https://www.example.com/a/list?id=1&id=2")
    with_query = [
        "https://www.example.com/a/list?utm_source=x&id=2&id=1",
        "https://www.example.com/a/list?utm_medium=y&id=2&utm_campaign=z&id=1#top",
    ]
    for v in with_query:
        assert announce.normalize_url(v) == base_q, v
        assert announce.url_hash(v) == announce.url_hash(base_q)
    # 非默认端口保留；query 按 key 排序
    assert announce.normalize_url("http://h.cn:8080/p?b=2&a=1") == "http://h.cn:8080/p?a=1&b=2"


def test_ann_n02_private_url_rejected():
    """SSRF：内网 IP/loopback/.local/非 http(s) → True；公网 IP → False（域名解析 mock）。"""
    import socket

    bad = ["http://127.0.0.1/x", "http://192.168.1.1/x", "http://10.0.0.1/x",
           "http://172.16.0.9/x", "http://169.254.169.254/meta", "http://0.0.0.0/x",
           "http://[::1]/x", "http://myhost.local/x", "ftp://example.com/x",
           "file:///etc/passwd", ""]
    for u in bad:
        assert announce.is_private_url(u), u
    # 公网 IP 直接放行
    assert announce.is_private_url("http://8.8.8.8/x") is False
    # 域名按解析结果判：mock getaddrinfo 返回内网地址 → 拒绝
    orig = socket.getaddrinfo

    def fake_getaddrinfo(host, *a, **kw):
        return [(socket.AF_INET, None, None, "", ("192.168.0.1", 0))]

    try:
        socket.getaddrinfo = fake_getaddrinfo
        assert announce.is_private_url("https://www.example.com/x") is True
    finally:
        socket.getaddrinfo = orig


# ---------------------------------------------------------------- 解析启发式
def test_ann_n03_parse_normal_page_with_date_and_stdno():
    """正常页：条目抽取/相对链接绝对化/日期变体归一/标准号识别/噪音过滤
    （含真实噪音：页脚备案号、document.write 拼接的 JS 片段、尾部时间戳剥离）。"""
    js_junk = '<a href="/js1">document.write("+(i+1)+");</a>'
    beian = '<a href="/beian">京公网安备11040102700086号</a>' \
            '<a href="/icp">京ICP备18056520号-2</a>'
    html = _page(
        ("/news/a1", "关于发布 GB 30871-2022 的公告 2026-09-01"),
        ("./a2.html", "某标准废止公告（2026年9月2日）"),
        ("/a3", "GB/T 1234.5-2020 第1号修改单 2026.9.3"),
        ("/t4", "关于印发特种作业操作证电子证照标准的通知 2021-10-18 11:11"),
        ("/next", "下一页"),
        ("/login", "请登录"),
        ("/logo.png", "网站标识"),
        ("javascript:void(0)", "点击展开"),
    ) + js_junk + beian
    items, diag = announce.parse_list_page(html, "https://gov.cn/bzgg/")
    assert diag["js_shell_suspected"] is False
    by_url = {it["url"]: it for it in items}
    # 相对路径 ./a2.html 相对于列表页目录 bzgg/ 解析
    assert "https://gov.cn/news/a1" in by_url
    assert by_url["https://gov.cn/bzgg/a2.html"]["published_date"] == "2026-09-02"
    assert by_url["https://gov.cn/a3"]["published_date"] == "2026-09-03"
    assert by_url["https://gov.cn/news/a1"]["standard_no"] == "GB 30871-2022"
    # 尾部日期时间戳剥离（日期本身仍被识别）
    assert by_url["https://gov.cn/t4"]["title"] == "关于印发特种作业操作证电子证照标准的通知"
    assert by_url["https://gov.cn/t4"]["published_date"] == "2021-10-18"
    # 噪音（下一页/登录/备案号/JS 片段）与静态资源（logo.png）/js 伪协议被滤
    assert len(items) == 4
    assert all("下一页" not in it["title"] for it in items)
    assert all("备案" not in it["title"] for it in items)
    assert all("document" not in it["title"] for it in items)


def test_ann_n04_parse_empty_and_js_shell():
    """空页 → parse_empty 语义交由调用方；大页面无文本链接 → js_shell_suspected。"""
    items, diag = announce.parse_list_page("<html><body>没有内容</body></html>",
                                           "https://gov.cn/x")
    assert items == [] and diag["parsed"] == 0
    assert diag["js_shell_suspected"] is False

    big_shell = "<html><body>" + "<div>壳</div>" * 6000 + "</body></html>"  # >40KB
    items, diag = announce.parse_list_page(big_shell, "https://gov.cn/y")
    assert items == [] and diag["js_shell_suspected"] is True


def test_ann_n05_parse_item_cap_50():
    """每页条目上限 50（truncated 标记）——防导航页误判成万条目。"""
    html = _page(*[(f"/p{i}", f"某某公告事项条目编号第{i}号 2026-09-01")
                   for i in range(80)])
    items, diag = announce.parse_list_page(html, "https://gov.cn/many")
    assert len(items) == 50 and diag["truncated"] is True


def test_ann_n06_parse_illegal_date_left_blank():
    """非法日期（2026-13-45）诚实留空，不猜测。"""
    html = _page(("/a", "某标准批准发布公告 2026-13-45"))
    items, _ = announce.parse_list_page(html, "https://gov.cn/z")
    assert items[0]["published_date"] is None


# ---------------------------------------------------------------- 源 CRUD 校验
def test_ann_n07_source_crud_validation(db, monkeypatch):
    """CRUD 校验矩阵：缺字段/内网拒绝 → UPD-3008；重复 URL/上限 → 3008；
    改 URL 重置基线；删不存在 → UPD-2005。"""
    # 域名解析 mock 成公网，隔离 DNS
    import socket
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda host, *a, **kw: [(socket.AF_INET, None, None, "",
                                                 ("93.184.216.34", 0))])
    src = announce.add_source("应急部公告", "https://www.mem.gov.cn/bzgg/")
    assert src["enabled"] is True and src["first_scan_done"] is False
    # 重复 URL（归一化后）
    with pytest.raises(UpdateError) as ei:
        announce.add_source("另一个", "https://www.mem.gov.cn/bzgg")
    assert ei.value.code == UPD_ILLEGAL_SOURCE_PAYLOAD
    # 内网拒绝
    with pytest.raises(UpdateError) as ei:
        announce.add_source("内网", "http://192.168.1.1/ann")
    assert ei.value.code == UPD_ILLEGAL_SOURCE_PAYLOAD
    # 缺字段
    with pytest.raises(UpdateError) as ei:
        announce.add_source("", "https://www.mem.gov.cn/other/")
    assert ei.value.code == UPD_ILLEGAL_SOURCE_PAYLOAD
    # 改 URL：已基线的源 → 重置基线（rebaselined:true）；未基线的源改 URL 不算 rebaseline
    upd = announce.update_source(src["id"], {"url": "https://www.mem.gov.cn/bzgg2/"})
    assert upd["rebaselined"] is False, "源从未基线过（first_scan_done=False），改 URL 不触发重置"
    # 手动置已基线后再改 URL → rebaselined:true
    sources = announce.get_sources()
    for s in sources:
        if s["id"] == src["id"]:
            s["first_scan_done"] = True
    announce._write_json_key(announce.SOURCES_KEY, sources)
    upd2 = announce.update_source(src["id"], {"url": "https://www.mem.gov.cn/bzgg3/"})
    assert upd2["rebaselined"] is True and upd2["first_scan_done"] is False
    # 改 name 不动基线
    upd3 = announce.update_source(src["id"], {"name": "改名"})
    assert upd3["rebaselined"] is False
    # 删不存在
    with pytest.raises(UpdateError) as ei:
        announce.remove_source("src_missing")
    assert ei.value.code == UPD_ANNOUNCE_SOURCE_NOT_FOUND
    left = announce.remove_source(src["id"])
    assert all(s["id"] != src["id"] for s in left)


def test_ann_n08_source_cap_50(db, monkeypatch):
    """源数量上限 50。"""
    import socket
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda host, *a, **kw: [(socket.AF_INET, None, None, "",
                                                 ("93.184.216.34", 0))])
    for i in range(announce.SOURCES_MAX):
        announce.add_source(f"源{i}", f"https://h{i}.example.com/ann/")
    with pytest.raises(UpdateError) as ei:
        announce.add_source("超出", "https://overflow.example.com/ann/")
    assert ei.value.code == UPD_ILLEGAL_SOURCE_PAYLOAD


# ---------------------------------------------------------------- 扫描编排（transport 注入）
def _mk_scan_world(monkeypatch, pages: dict[str, tuple[int, str]]):
    """造源 + fake transport：返回 (transport, urls)。域名解析一律 mock 公网。"""
    import socket
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda host, *a, **kw: [(socket.AF_INET, None, None, "",
                                                 ("93.184.216.34", 0))])
    transport = _FakeTransport(pages)
    return transport


def test_ann_n09_scan_baseline_then_dedup(db, monkeypatch):
    """首扫基线（不计新）→ 二扫去重 0 新 → 换源同 URL 两行隔离。"""
    url = "https://www.mem.gov.cn/bzgg/"
    page = _page(
        ("/art/1", "关于发布 GB 30871-2022 的公告 2026-09-01"),
        ("/art/2", "某行业标准废止公告 2026-09-02"),
        ("/art/3", "某某标准批准发布公告"),
    )
    transport = _mk_scan_world(monkeypatch, {url: (200, page)})
    src = announce.add_source("应急部公告", url)

    # 第一轮（首扫基线）
    out = announce.request_scan(force=True, trigger="manual", transport=transport)
    assert out["status"] == "started"
    state = _wait_done()
    assert state["status"] == "done" and state["items_seen"] == 3
    assert state["baseline_count"] == 3 and state["new_count"] == 0
    ps = state["per_source"][0]
    assert ps["status"] == "ok" and ps["baseline_items"] == 3
    rows = announce.list_items(limit=10)
    assert rows["total"] == 3 and rows["items"][0]["source_name"] == "应急部公告"
    # 排序 = 发布日期 DESC（真机回归：first_seen 是"我们何时见到"，单页扫描
    # 按 HTML 顺序插入，按它排会把页面上最旧的排到最前）；无日期排最后
    assert rows["items"][0]["published_date"] == "2026-09-02"
    assert rows["items"][-1]["published_date"] is None
    # 某行标题识别出标准号（零 LLM 正则；不假设具体行）
    assert any(r["standard_no"] == "GB 30871-2022" for r in rows["items"])
    # 源基线已标记
    assert announce.get_sources()[0]["first_scan_done"] is True

    # 第二轮：同页全见过 → 0 新（去重幂等），行数不变
    out2 = announce.request_scan(force=True, trigger="manual", transport=transport)
    assert out2["status"] == "started"
    state2 = _wait_done()
    assert state2["new_count"] == 0 and state2["baseline_count"] == 0
    assert announce.list_items(limit=10)["total"] == 3
    # last_seen 刷新不插行：同 id 行仍 3
    assert state2["scan_id"] != state["scan_id"]

    # 源改 URL（换页）→ 重置基线 → 再扫 = 新页面全量记基线（旧记录保留留档）
    url2 = "https://www.mem.gov.cn/bzgg2/"
    transport.pages[url2] = (200, _page(("/x", "新页面公告事项甲 2026-09-06"),
                                        ("/y", "新页面公告事项乙 2026-09-06")))
    announce.update_source(src["id"], {"url": url2})
    assert announce.get_sources()[0]["first_scan_done"] is False
    out3 = announce.request_scan(force=True, trigger="manual", transport=transport)
    assert out3["status"] == "started"
    state3 = _wait_done()
    assert state3["baseline_count"] == 2 and state3["new_count"] == 0
    assert announce.list_items(limit=10)["total"] == 5  # 3 旧档 + 2 新基线


def test_ann_n10_scan_new_items_and_recent(db, monkeypatch):
    """列表页新增条目 → new_count 与 recent（≤5）正确；时间闸 force=false → skipped。"""
    url = "https://www.mem.gov.cn/gk/"
    pages = {url: (200, _page(("/1", "第一条公告事项标题 2026-09-01"),
                              ("/2", "第二条公告事项标题 2026-09-02")))}
    transport = _mk_scan_world(monkeypatch, pages)
    announce.add_source("测试源", url)
    announce.request_scan(force=True, trigger="manual", transport=transport)
    _wait_done()

    pages[url] = (200, _page(("/1", "第一条公告事项标题 2026-09-01"),
                             ("/2", "第二条公告事项标题 2026-09-02"),
                             ("/3", "第三条新公告事项标题 2026-09-05")))
    announce.request_scan(force=True, trigger="manual", transport=transport)
    state = _wait_done()
    assert state["new_count"] == 1
    assert len(state["recent"]) == 1
    # title 保留列表页原文（含缀尾日期），前缀匹配即可
    assert state["recent"][0]["title"].startswith("第三条新公告事项标题")
    # announcement_observed 总行 3（2 基线 + 1 新）
    assert announce.list_items(limit=10)["total"] == 3

    # 时间闸：force=false 且 6h 内扫过 → skipped（不重扫）
    out = announce.request_scan(force=False, trigger="after_inspection",
                                transport=transport)
    assert out["status"] == "skipped"


def test_ann_n11_scan_failure_honesty(db, monkeypatch):
    """失败诚实：http 500 / 验证码页 / JS 壳 / 空 parse —— 每源 failed+reason，
    绝不假装 0 新；其余源照常。"""
    ok_url = "https://ok.example.com/ann/"
    waf_url = "https://waf.example.com/ann/"
    shell_url = "https://shell.example.com/ann/"
    err_url = "https://err.example.com/ann/"
    big_shell = "<html><body>" + "<div>壳</div>" * 6000 + "</body></html>"
    transport = _mk_scan_world(monkeypatch, {
        ok_url: (200, _page(("/a", "正常源公告事项标题 2026-09-01"))),
        waf_url: (200, "<html>请输入验证码 captcha</html>"),
        shell_url: (200, big_shell),
        err_url: (500, "server error"),
    })
    for name, u in (("正常源", ok_url), ("WAF源", waf_url),
                    ("壳源", shell_url), ("错源", err_url)):
        announce.add_source(name, u)
    announce.request_scan(force=True, trigger="manual", transport=transport)
    state = _wait_done()
    assert state["status"] == "done"
    by_name = {p["name"]: p for p in state["per_source"]}
    assert by_name["正常源"]["status"] == "ok" and by_name["正常源"]["new_items"] == 0
    assert by_name["正常源"]["baseline_items"] == 1
    assert by_name["WAF源"]["status"] == "failed" and by_name["WAF源"]["reason"] == "waf_captcha"
    assert by_name["壳源"]["status"] == "failed" and by_name["壳源"]["reason"] == "js_shell_suspected"
    assert by_name["错源"]["status"] == "failed" and by_name["错源"]["reason"] == "http_500"
    # 正常源照常落库
    assert announce.list_items(limit=10)["total"] == 1


def test_ann_n12_scan_409_running_gate(db, monkeypatch):
    """409 双闸：进程内已有扫描登记 → request_scan 抛 UPD-2006。
    （CPython GIL 下 set.add/discard 单操作原子，无需持 _SCAN_LOCK——该锁不可重入。）"""
    url = "https://gate.example.com/ann/"
    transport = _mk_scan_world(monkeypatch, {url: (200, _page(("/a", "门控公告事项标题")))} )
    announce.add_source("门控源", url)
    announce._announce_runs.add("asc_fake_running")
    try:
        with pytest.raises(UpdateError) as ei:
            announce.request_scan(force=True, trigger="manual", transport=transport)
        assert ei.value.code == UPD_ANNOUNCE_SCAN_ALREADY_RUNNING
    finally:
        announce._announce_runs.discard("asc_fake_running")


def test_ann_n13_scan_stale_recovered(db, monkeypatch):
    """僵尸扫描自愈：state running 但进程内无登记 → 新扫描照常开（记审计）。"""
    url = "https://stale.example.com/ann/"
    transport = _mk_scan_world(monkeypatch, {url: (200, _page(("/a", "僵尸后公告事项标题")))} )
    announce.add_source("僵尸源", url)
    # 伪造僵尸 state
    announce._write_json_key(announce.STATE_KEY, {
        "scan_id": "asc_dead", "status": "running", "started_at": "2026-09-01 00:00:00",
        "finished_at": None})
    out = announce.request_scan(force=True, trigger="manual", transport=transport)
    assert out["status"] == "started"
    state = _wait_done()
    assert state["status"] == "done" and state["scan_id"] != "asc_dead"


def test_ann_n14_disabled_source_skipped(db, monkeypatch):
    """禁用源不抓取（不进 per_source 清单也不发 HTTP）。"""
    url = "https://off.example.com/ann/"
    transport = _mk_scan_world(monkeypatch, {url: (200, _page(("/a", "禁用源公告标题")))})
    src = announce.add_source("停用源", url)
    announce.update_source(src["id"], {"enabled": False})
    announce.request_scan(force=True, trigger="manual", transport=transport)
    state = _wait_done()
    assert state["sources_total"] == 0
    assert url not in transport.calls
    assert announce.list_items(limit=10)["total"] == 0


# ---------------------------------------------------------------- Excel 导出（P1）
def test_ann_x15_export_reopenable(db, monkeypatch):
    """xlsx 落 exports、openpyxl 重开：源状态 sheet（逐源行）+ 明细全量行数。"""
    from openpyxl import load_workbook

    from src.core.exports.report_export import _exports_dir

    url = "https://www.mem.gov.cn/ex/"
    transport = _mk_scan_world(monkeypatch, {url: (200, _page(
        ("/a", "第一条公告事项标题 2026-09-01"),
        ("/b", "第二条公告事项标题 2026-09-02")))})
    announce.add_source("导出测试源", url)
    announce.request_scan(force=True, trigger="manual", transport=transport)
    _wait_done()

    out = announce.export_announce_xlsx()
    assert out.exists() and out.suffix == ".xlsx"
    assert out.parent == _exports_dir()
    wb = load_workbook(str(out), data_only=True)
    assert wb.sheetnames == ["最近扫描", "公告明细"]
    wd = wb["公告明细"]
    assert wd.max_row == 1 + 2, "明细 = 2 条已见公告"
    first = [c.value for c in list(wd.iter_rows(min_row=2))[0]]
    assert first[0] == "导出测试源" and "公告事项标题" in str(first[1])
    # 发布日期 DESC：09-02 在前
    assert first[3] == "2026-09-02"
    ws = wb["最近扫描"]
    assert ws["A3"].value == "扫描编号"


def test_ann_x16_export_empty(db):
    """空库/从未扫描：同样出文件，明细仅表头。"""
    from openpyxl import load_workbook

    out = announce.export_announce_xlsx()
    wb = load_workbook(str(out), data_only=True)
    assert wb.sheetnames == ["最近扫描", "公告明细"]
    assert wb["公告明细"].max_row == 1
    assert "尚未完成过扫描" in str(wb["最近扫描"]["B3"].value) or wb["最近扫描"]["B3"].value is None
