"""法规总目录测试（LAW_CATALOG_ONDEMAND_PLAN.md 任务 1）。

全程 mock 网络（flk_client.enum_data/search + catalog.fetch_json），零真实请求。
覆盖：全量遍历分页 / 去重（批内 pending 与账本增量两条路径）/ aggregateData 对账
warning / 分页查询过滤 / manifest 断点与增量跳过（title/sxx 变更才更新）/ 枚举叶子
解析 / sxx 映射。

注意：conftest 的库为会话级共享库（KS_DATA_DIR 单临时目录），涉及全局计数的断言
一律用「基线 + 本次增量」或唯一标记词隔离，不写死全库总数。
"""
import json

import pytest


# ---------------------------------------------------------------------------
# fake 源数据构造
# ---------------------------------------------------------------------------
def _mk_rows(prefix: str, start: int, n: int, *, title_mark: str,
             flxz: str = "法律", gbrq: str | None = "2024-01-01", sxx: int | None = 3):
    return [{"bbbs": f"{prefix}{i:05d}", "title": f"{title_mark}第{i}号测试法",
             "flxz": flxz, "gbrq": gbrq or "", "sxrq": "2024-03-01", "sxx": sxx}
            for i in range(start, start + n)]


FAKE_ENUM = {"data": {"flfgCode": [
    {"code": "", "name": "全部"},                       # 聚合占位，应被跳过
    {"code": "flfg-A", "name": "法律(父)", "children": [
        {"code": "flfg-A1", "name": "法律T1"},
        {"code": "flfg-A2", "name": "法律解释T1"},
    ]},
    {"code": "flfg-B", "name": "行政法规T1"},
]}}


def _patch_flk(monkeypatch, enum: dict, pages_by_code: dict[str, list[list[dict]]],
               calls: list | None = None):
    """patch flk_client.enum_data/search；search 按 分类→页 返回并记录调用。"""
    from src.core.knowledge.law_source import flk_client as flk_mod
    monkeypatch.setattr(flk_mod, "enum_data", lambda: enum)

    def fake_search(content, **kw):
        if calls is not None:
            calls.append({"content": content, **kw})
        assert content == ""                      # 空词=全库（任务契约）
        assert kw.get("page_size") == 100         # 固定大页遍历
        pages = pages_by_code[kw["category_ids"][0]]
        page_no = kw["page"]
        rows = pages[page_no - 1] if page_no <= len(pages) else []
        total = sum(len(p) for p in pages)
        return {"code": 200, "total": total, "rows": rows}

    monkeypatch.setattr(flk_mod, "search", fake_search)


def _patch_aggregate(monkeypatch, payload: dict, urls: list | None = None):
    from src.core.knowledge.law_source import catalog as cat

    def fake_fetch_json(url, **kw):
        if urls is not None:
            urls.append(url)
        if "aggregateData" in url:
            return payload
        raise AssertionError(f"catalog 不应发起其他网络请求: {url}")

    monkeypatch.setattr(cat, "fetch_json", fake_fetch_json)


def _by_cat() -> dict[str, int]:
    """库内 `law_catalog` 按分类计数（**与生产同一句 SQL**，用来取"基线"）。

    ⚠ 为什么必须有它：`refresh_catalog()` 的 `by_category` 是**全表**分组计数
    （`catalog.py` 里那句 `SELECT category, COUNT(*) … GROUP BY category`），而 conftest 的库
    是**会话级共享**的 ⇒ 断言写死全表字典就会变成"**顺序依赖的假绿**"：
    `pytest tests/test_law_source_api.py tests/test_law_catalog.py`（api 文件在前，它会往
    `law_catalog` 里留下一行 `API测试`）时，`test_refresh_full_crawl_dedup_and_result` **红**；
    而全量跑/按字母序（`law_catalog` 在前）**绿**。本文件开头的纪律早就写了
    "涉及全局计数的断言一律用「基线 + 本次增量」"——这条断言当时没照做，2026-09-18 已改齐。
    """
    from src.core.storage.sqlite_db import get_db_connection
    return {r["category"] or "": r["n"] for r in get_db_connection().execute(
        "SELECT category, COUNT(*) AS n FROM law_catalog GROUP BY category").fetchall()}


# ---------------------------------------------------------------------------
# 枚举叶子解析 / sxx 映射 / 对账解析
# ---------------------------------------------------------------------------

def test_extract_category_leaves_skips_placeholder_and_dedups():
    from src.core.knowledge.law_source.catalog import extract_category_leaves
    cats = extract_category_leaves(FAKE_ENUM)
    # 只有叶子（无 children），「全部」占位与父节点被跳过
    assert cats == [("flfg-A1", "法律T1"), ("flfg-A2", "法律解释T1"),
                    ("flfg-B", "行政法规T1")]
    assert extract_category_leaves({"data": {}}) == []


def test_sxx_label_mapping():
    from src.core.knowledge.law_source.catalog import sxx_label
    assert sxx_label(1) == "已废止"
    assert sxx_label("2") == "已修改"
    assert sxx_label(3) == "现行有效"
    assert sxx_label(4) == "尚未生效"
    assert "9" in sxx_label(9) and "未知" in sxx_label(None)


def test_parse_aggregate_tolerant_shapes():
    from src.core.knowledge.law_source.catalog import parse_aggregate
    m = parse_aggregate({"code": 200, "data": {
        "catList": [{"name": "法律", "count": 1373}, {"code": "xz", "num": 964}]}})
    assert m == {"法律": 1373, "xz": 964}
    assert parse_aggregate({"code": 200}) == {}


# ---------------------------------------------------------------------------
# 全量遍历 / 去重 / 对账
# ---------------------------------------------------------------------------

def test_refresh_full_crawl_dedup_and_result(monkeypatch):
    from src.core.knowledge.law_source import catalog as cat

    # A1 共 250 条（3 页：100/100/50）→ 处理到第 2 页即触发 200 攒批落盘，
    # 因此 idx<200 的行在后续分类出现重复时走「账本增量」路径而非批内去重。
    a_pages = [_mk_rows("bbA", 0, 100, title_mark="消防T1类"),
               _mk_rows("bbA", 100, 100, title_mark="消防T1类"),
               _mk_rows("bbA", 200, 50, title_mark="消防T1类")]
    # A2：2 条新法规 + 1 条与 A1 同 bbbs 的重复行（title/sxx 须与账本一致 → 走账本增量跳过）
    b2_rows = _mk_rows("bbC", 0, 2, title_mark="解释T1类")
    b2_rows.append({"bbbs": "bbA00042", "title": "消防T1类第42号测试法",
                    "flxz": "法律", "gbrq": "2024-01-01",
                    "sxrq": "2024-03-01", "sxx": 3})   # 跨分类重复 → 账本命中，skip 不重写
    b3_rows = _mk_rows("bbB", 0, 30, title_mark="行政T1类")
    dup = dict(b3_rows[0])                         # 同页重复 → 批内 pending_keys 去重
    b3_rows.append(dup)

    search_calls: list[dict] = []
    _patch_flk(monkeypatch, FAKE_ENUM, {
        "flfg-A1": a_pages, "flfg-A2": [b2_rows], "flfg-B": [b3_rows],
    }, calls=search_calls)
    agg_urls: list[str] = []
    # 本地预期入库：A1=250、A2=3-1(账本重复)=2、B=30(同页重复不入库) → 对账一致零警告
    _patch_aggregate(monkeypatch, {"code": 200, "data": {"catList": [
        {"name": "法律T1", "count": 250},
        {"name": "法律解释T1", "count": 2},
        {"name": "行政法规T1", "count": 30},
    ]}}, urls=agg_urls)

    baseline = cat.query_catalog(page_size=1)["total"]   # 会话共享库基线
    baseline_by_cat = _by_cat()                          # 同上：按分类的基线（见 `_by_cat`）
    events: list[dict] = []
    out = cat.refresh_catalog(events.append)
    stages = [e["stage"] for e in events]
    assert stages[:2] == ["enum", "crawl"] and stages[-2:] == ["reconcile", "done"]

    # 分页调用形态：每分类从第 1 页起、空词、pageSize=100；A1 共 250 条 → 3 页
    first_by_cat: dict[tuple, int] = {}
    for c in search_calls:
        first_by_cat.setdefault(tuple(c["category_ids"]), c["page"])
    assert all(v == 1 for v in first_by_cat.values()) and len(first_by_cat) == 3
    assert sum(1 for c in search_calls if c["category_ids"] == ["flfg-A1"]) == 3
    assert agg_urls == [cat._AGGREGATE_URL]

    assert out["total"] == baseline + 282
    # `by_category` 是**全表**分组计数 ⇒ 只能断言"本次增量"（基线相减，非零项）
    delta_by_cat = {k: v - baseline_by_cat.get(k, 0)
                    for k, v in out["by_category"].items()
                    if v - baseline_by_cat.get(k, 0) != 0}
    assert delta_by_cat == {"法律T1": 250, "行政法规T1": 30, "法律解释T1": 2}
    assert out["warnings"] == []                   # 对账一致 + 无抓取失败
    assert out["duplicate_seen"] == 1              # 同页重复走 pending 去重
    assert out["skipped"] == 1                     # 跨分类重复走账本增量跳过
    assert out["fetched"] == 282

    # 账本落盘且逐 bbbs 记 title/sxx/fetched_at；分类级断点已记 done
    mf = json.loads(cat.manifest_path().read_text(encoding="utf-8"))
    ent = mf["laws"]["bbA00042"]
    assert ent["sxx"] == 3 and ent["fetched_at"] and "消防" in ent["title"]
    assert mf["categories"]["flfg-A1"]["done"] is True
    # 库里可查、bbbs 唯一
    hit = cat.query_catalog(q="消防T1类第42号测试法")
    assert hit["total"] == 1 and hit["items"][0]["bbbs"] == "bbA00042"


def test_reconcile_mismatch_records_warning(monkeypatch):
    from src.core.knowledge.law_source import catalog as cat
    enum = {"data": {"x": [{"code": "flfg-R", "name": "法律T2"}]}}
    _patch_flk(monkeypatch, enum, {"flfg-R": [_mk_rows("bbR", 0, 5, title_mark="目录T2")]})
    _patch_aggregate(monkeypatch, {"code": 200, "data": {
        "catList": [{"name": "法律T2", "count": 99}]}})   # 远端虚高 → 必须出 warning
    out = cat.refresh_catalog()
    assert cat.query_catalog(q="目录T2")["total"] == 5
    assert any("对账差异" in w and "法律T2" in w and "99" in w for w in out["warnings"])


def test_single_category_failure_degrades_to_warning(monkeypatch):
    from src.core.knowledge.law_source import catalog as cat
    from src.core.knowledge.law_source import flk_client as flk_mod

    enum = {"data": {"x": [{"code": "flfg-F1", "name": "分类F1"},
                           {"code": "flfg-F2", "name": "分类F2"}]}}
    ok_rows = _mk_rows("bbF2", 0, 2, title_mark="F2条例")

    def flaky_search(content, **kw):
        if kw["category_ids"] == ["flfg-F1"]:
            raise RuntimeError("模拟官方接口抖动")
        return {"code": 200, "total": 2, "rows": ok_rows}
    monkeypatch.setattr(flk_mod, "enum_data", lambda: enum)
    monkeypatch.setattr(flk_mod, "search", flaky_search)
    _patch_aggregate(monkeypatch, {"code": 200})

    out = cat.refresh_catalog()
    assert cat.query_catalog(category="分类F2")["total"] == 2   # F2 正常入库
    assert any("分类F1" in w and "失败" in w for w in out["warnings"])
    assert not any("对账差异" in w for w in out["warnings"])
    # 失败分类不标 done（断点语义：下次运行整分类重来）
    mf = json.loads(cat.manifest_path().read_text(encoding="utf-8"))
    assert mf["categories"]["flfg-F1"]["done"] is False
    assert mf["categories"]["flfg-F2"]["done"] is True


def test_aggregate_fetch_failure_is_silent_and_catalog_usable(monkeypatch):
    """aggregateData 端点已核实不返回 JSON（SPA HTML/405）；失败静默跳过，目录仍可用。"""
    from src.core.knowledge.law_source import catalog as cat

    _patch_flk(monkeypatch, {"data": {"x": [{"code": "flfg-G", "name": "G分类"}]}},
               {"flfg-G": [_mk_rows("bbG", 0, 3, title_mark="G法")]})

    def boom(url, **kw):
        raise RuntimeError("网络断了")
    monkeypatch.setattr(cat, "fetch_json", boom)
    out = cat.refresh_catalog()
    assert not any("对账不可用" in w for w in out["warnings"])   # 静默，不误报为目录缺陷
    assert cat.query_catalog(q="G法")["total"] == 3


# ---------------------------------------------------------------------------
# 分页查询：模糊 / 过滤 / 排序 / 切片
# ---------------------------------------------------------------------------

def test_query_pagination_filters_and_order():
    from src.core.knowledge.law_source import catalog as cat
    from src.core.storage.sqlite_db import write_transaction

    cat.ensure_catalog_schema()
    mark = "目录Q4独占词"
    rows = []
    for i in range(7):
        rows.append((f"{mark}条例{i}", f"bbQ4-{i}", "部门规章Q4",
                     3 if i % 2 == 0 else 1, "Q4分类",
                     f"2023-0{i + 1}-01" if i < 6 else "",   # 一条空日期沉底
                     "2024-01-01"))
    with write_transaction() as txn:
        for r in rows:
            txn.execute(
                "INSERT OR IGNORE INTO law_catalog (title,bbbs,flxz,sxx,category,gbrq,sxrq)"
                " VALUES (?,?,?,?,?,?,?)", r)

    full = cat.query_catalog(q=mark, page_size=3)
    assert full["total"] == 7 and len(full["items"]) == 3
    assert set(full["items"][0].keys()) == {"title", "bbbs", "flxz", "sxx",
                                            "category", "gbrq", "sxrq"}
    assert full["pages"] == 3
    p3 = cat.query_catalog(q=mark, page_size=3, page=3)
    assert len(p3["items"]) == 1                    # 尾页只剩 1 条
    # 公布日期新→旧，空日期最后
    dates = [it["gbrq"] for it in full["items"]]
    assert dates[:2] == sorted(dates[:2], reverse=True) and dates[-1] != ""

    only_eff = cat.query_catalog(q=mark, sxx=3, page_size=200)
    assert only_eff["total"] == 4 and all(it["sxx"] == 3 for it in only_eff["items"])
    by_str = cat.query_catalog(q=mark, sxx="1", page_size=200)
    assert by_str["total"] == 3                     # 字符串 sxx 同样生效
    by_cat = cat.query_catalog(q=mark, category="Q4分类", page_size=200)
    assert by_cat["total"] == 7 and by_cat["items"][0]["category"] == "Q4分类"
    assert "Q4分类" in by_cat["categories"]          # facet 下拉数据源
    miss = cat.query_catalog(q="绝不存在的标题XYZQ4")
    assert miss["total"] == 0 and miss["items"] == []


# ---------------------------------------------------------------------------
# manifest 断点与增量跳过
# ---------------------------------------------------------------------------

def test_manifest_incremental_skip_and_sxx_change(monkeypatch):
    from src.core.knowledge.law_source import catalog as cat

    pages = {"flfg-M": [_mk_rows("bbM", 0, 120, title_mark="目录M法")]}
    _patch_flk(monkeypatch, {"data": {"x": [{"code": "flfg-M", "name": "M分类"}]}},
               pages)
    _patch_aggregate(monkeypatch, {"code": 200, "data": {
        "catList": [{"name": "M分类", "count": 120}]}})

    base = cat.query_catalog(page_size=1)["total"]      # 会话共享库基线
    r1 = cat.refresh_catalog()
    assert r1["fetched"] == 120 and r1["skipped"] == 0
    assert cat.query_catalog(q="目录M法", page_size=1)["total"] == 120   # M 类恰 120

    # 二次刷新：远端清单不变 → 全部命中账本跳过，不产生任何写库
    r2 = cat.refresh_catalog()
    assert r2["skipped"] == 120 and r2["written"] == 0 and r2["fetched"] == 0
    assert cat.query_catalog(q="目录M法", page_size=1)["total"] == 120   # 未重复写
    assert r2["total"] == base + 120                   # 全库总量 = 基线 + M 增量（防串扰）

    # 官方时效变化（现行→废止）：仅该条被重新写入，其余仍跳过
    pages["flfg-M"][0][7]["sxx"] = 1
    pages["flfg-M"][0][7]["title"] = "目录M法第7号测试法（已废止版本）"
    r3 = cat.refresh_catalog()
    assert r3["fetched"] == 1 and r3["skipped"] == 119
    row = cat.query_catalog(q="目录M法第7号测试法（已废止版本）", page_size=10)
    assert row["total"] == 1 and row["items"][0]["sxx"] == 1

    # force=True：无视账本全量重写（DB 与账本不同步时的修复通道）
    r4 = cat.refresh_catalog(force=True)
    assert r4["fetched"] == 120 and r4["written"] == 120


def test_progress_events_shape(monkeypatch):
    from src.core.knowledge.law_source import catalog as cat
    _patch_flk(monkeypatch, {"data": {"x": [{"code": "flfg-P", "name": "P分类"}]}},
               {"flfg-P": [_mk_rows("bbP", 0, 3, title_mark="P法")]})
    _patch_aggregate(monkeypatch, {"code": 200})
    seen: list[dict] = []
    out = cat.refresh_catalog(seen.append)
    crawl = [e for e in seen if e["stage"] == "crawl"]
    assert crawl and crawl[0]["category"] == "P分类" and crawl[0]["page"] == 1
    done = seen[-1]
    assert done["stage"] == "done" and done["total"] == out["total"]


def test_并发ensure_catalog_schema在缺列旧表上不抛异常(client):
    """§10.87（独立复核 b16 的 INFO-3）：32 线程并发建表/补列，不许抛 `duplicate column name`。

    为什么必须有这条：`GET /api/v1/laws/catalog` 在 §10.86 从 `async def` 改成 `def` 之后
    **可以并发进来**（anyio 池 16 个线程），而"`PRAGMA table_info` 看到缺列 → `ALTER TABLE
    ADD COLUMN`"是**读-改-写竞态**。b16 的实测（`var/tmp/probe-ddl-race.py`，本次也复现）：
    修复前 32 线程 **31/32 抛 `OperationalError: duplicate column name: category`**
    （`query_catalog` 不 catch、路由只 catch `TypeError/ValueError` ⇒ 用户看到 500）；
    修复后（`write_transaction()` 串行化 + 幂等兜底）同一探针连跑 28 次全 0 异常。

    ⚠ 判据是**确定性**的（不靠计时）：任何一条线程抛出即红；并回读最终列确认迁移完成。
    ⚠ 为了让竞态**真的有机会发生**，这里把 GIL 切换间隔压到 1µs（`sys.setswitchinterval`）——
    否则 32 条线程可能被 GIL 串行化到"第一条已经迁完、其余走只读快路径"，竞态就测不出来
    （§10.87 实测：不压切换间隔时，把两层修法都撤掉的变异也测不出来）。
    """
    import sys as _sys
    import threading

    from src.core.knowledge.law_source import catalog as cat
    from src.core.storage.sqlite_db import get_db_connection

    c, _ = client                                    # 建 app（顺带初始化 schema）
    assert c.get("/api/v1/health").status_code == 200
    conn = get_db_connection()
    conn.execute("DROP TABLE IF EXISTS law_catalog")
    conn.execute("CREATE TABLE law_catalog (title TEXT, bbbs TEXT NOT NULL UNIQUE,"
                 " flxz TEXT, sxx INTEGER, gbrq TEXT, sxrq TEXT,"
                 " updated_at TEXT DEFAULT (datetime('now')))")   # 旧版：缺 category
    conn.commit()

    n = 32
    errors: list[str] = []
    lock = threading.Lock()
    barrier = threading.Barrier(n)

    def worker() -> None:
        barrier.wait()                               # 尽量让 32 条同时冲进去
        try:
            cat.ensure_catalog_schema()
        except Exception as e:                       # noqa: BLE001 - 记下来再断言
            with lock:
                errors.append(f"{type(e).__name__}: {e}")

    old_interval = _sys.getswitchinterval()
    _sys.setswitchinterval(1e-6)                     # 逼出交错（见 docstring）
    try:
        ths = [threading.Thread(target=worker) for _ in range(n)]
        for t in ths:
            t.start()
        for t in ths:
            # ⚠ 带超时的 join（独立复核 b17 的 INFO）：某条线程若卡在锁上，测试不该无限挂住
            # （那会变成"CI 卡死"而不是"红"）。30s 足够——正常迁移是毫秒级。
            t.join(30)
    finally:
        _sys.setswitchinterval(old_interval)
    alive = [t for t in ths if t.is_alive()]
    assert not alive, f"有 {len(alive)} 条线程 30s 内没结束（卡在锁上了？）"
    assert not errors, f"并发补列竞态复现（{len(errors)}/{n}）：{errors[:3]}"
    cols = {r[1] for r in conn.execute("PRAGMA table_info(law_catalog)").fetchall()}
    assert {"category", "updated_at"} <= cols, cols


def test_稳态下ensure_catalog_schema不拿写锁(client):
    """§10.87：表/列/索引都齐（**稳态**）时，它必须走**只读快路径**，不碰写锁。

    为什么这条必要：`ensure_catalog_schema()` 被 `query_catalog()` **每个请求**调用，
    而 `GET /api/v1/laws/catalog` 是一条**纯读**端点。本步第一版修法把整个函数收进
    `write_transaction()`（`BEGIN IMMEDIATE`）⇒ **每次翻目录都要先拿写锁**，把一条读端点的
    延迟绑到"当前有没有别的写者"上（`busy_timeout=60s` ⇒ 理论上可以等几十秒）。
    所以加了"⓪ 只读快路径"（`PRAGMA table_info` + `PRAGMA index_list` 都齐就直接返回）。

    判据（**确定性**，靠"另一个连接持写锁 + 本连接 busy_timeout 很短"）：若它仍走写路径，
    `BEGIN IMMEDIATE` 会在 300ms 后抛 `database is locked` ⇒ 红。
    """
    import sqlite3

    from src.core.knowledge.law_source import catalog as cat
    from src.core.storage.sqlite_db import get_db_connection, get_settings

    c, _ = client
    assert c.get("/api/v1/health").status_code == 200
    cat.ensure_catalog_schema()                        # 先迁到稳态（表、列、索引都齐）

    conn = get_db_connection()
    conn.execute("PRAGMA busy_timeout=300")            # 本连接：等锁最多 0.3s
    other = sqlite3.connect(str(get_settings().db_path), timeout=30)
    try:
        other.execute("PRAGMA journal_mode=WAL")
        other.execute("BEGIN IMMEDIATE")               # 另一个写者持锁
        other.execute("UPDATE law_catalog SET title = title WHERE 0")
        cat.ensure_catalog_schema()                    # 稳态 ⇒ 只读快路径 ⇒ 立刻返回
    finally:
        other.rollback()
        other.close()
        conn.execute("PRAGMA busy_timeout=60000")      # 还原，别泄给后面的用例
