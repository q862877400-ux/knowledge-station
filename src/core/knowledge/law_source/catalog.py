"""法规总目录（LAW_CATALOG_ONDEMAND_PLAN.md 任务 1）：flk 全量清单 → 本地 SQLite 目录。

职责边界：
- 只拉「标题清单」（搜索接口 rows 元数据），不拉正文/不下载文件（正文按需下载是任务 3）；
- 全量遍历：enum_data() 动态取分类叶子 code（勿硬编码），逐分类空词分页
  （searchContent="" = 全库，pageSize=100，order 固定降序——升序会 500，见 flk_client.search）；
- 账本 law_manifest.json（data_dir 下）：每 bbbs 记 title/sxx/fetched_at，
  支持断点（分类级 done 标记）与增量（已入库且 title/sxx 未变则跳过写库）；
- 对账：GET /law-search/index/aggregateData 分类计数核对，差异只记 warning 不失败。
  **实测核实：该端点不返回 JSON（返 SPA HTML / 405），故失败仅 debug 静默跳过，不误报**
  （完整性由爬取时每分类 search 的 remote_total 顶满 + 翻页保险丝告警保证）。
- 存储：SQLite law_catalog 表，幂等迁移建表（参考 clause_repo.ensure_content_hash_column 先例）。

已知坑（照抄自 docs/REALTIME_VALIDITY_VERIFY_RESEARCH.md §1.1）：
- sxx 权威映射：1=已废止 2=已修改 3=现行有效 4=尚未生效；
- flk 站点有 JA3/TLS 指纹 WAF：本机 requests 握手可能 SSLEOFError（任务 2 的
  CurlCffiTransport 通道解决）；届时 refresh_catalog 在 enum_data 处抛 RuntimeError 属预期。
"""
from __future__ import annotations

import json
import logging
import math
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.core.config import get_settings
from src.core.knowledge.law_source import flk_client
from src.core.knowledge.law_source.http import fetch_json
from src.core.storage.sqlite_db import get_db_connection, write_transaction

logger = logging.getLogger(__name__)

# sxx 时效状态码权威映射（docs/REALTIME_VALIDITY_VERIFY_RESEARCH.md §1.1 表）
SXX_LABELS: dict[int, str] = {1: "已废止", 2: "已修改", 3: "现行有效", 4: "尚未生效"}

# aggregateData 接口不在 flk_client 内（避免改动既有文件），直接走共享 http 层（白名单/限速同源）
_AGGREGATE_URL = "https://flk.npc.gov.cn/law-search/index/aggregateData"

PAGE_SIZE = 100          # 单页上限（官方接口实测支持 100）
_BATCH_WRITE = 200       # 攒批写库阈值
ManifestCb = Callable[[dict], None]


def sxx_label(sxx: int | str | None) -> str:
    """sxx 数字 → 展示文案；未知值原样标注（不猜）。"""
    if isinstance(sxx, (int, str)) and sxx != "":
        try:
            return SXX_LABELS.get(int(sxx), f"未知({sxx})")
        except (TypeError, ValueError):
            return f"未知({sxx})"
    return f"未知({sxx})"


def manifest_path() -> Path:
    return get_settings().data_dir / "law_manifest.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# 幂等迁移（参考 clause_repo.ensure_content_hash_column 先例：PRAGMA 检查 + 补列）
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS law_catalog (
    title TEXT,                             -- 法规标题
    bbbs TEXT NOT NULL UNIQUE,              -- flk 唯一标识
    flxz TEXT,                              -- 行级分类（法律/行政法规/…，官方 rows 自带）
    sxx INTEGER,                            -- 时效 1废止 2已修改 3现行 4未生效
    category TEXT,                          -- 抓取时的枚举分类叶子名（目录分组）
    gbrq TEXT,                              -- 公布日期 YYYY-MM-DD
    sxrq TEXT,                              -- 施行日期 YYYY-MM-DD
    updated_at TEXT DEFAULT (datetime('now'))
);
"""


_CATALOG_COLUMNS = ("category", "updated_at")
_CATALOG_INDEXES = ("idx_law_catalog_title", "idx_law_catalog_cat", "idx_law_catalog_sxx")


def ensure_catalog_schema(conn=None) -> None:
    """幂等迁移建表 law_catalog + 索引；旧表缺列时 PRAGMA 检查后补列。

    ⚠ **并发安全**（§10.87，独立复核 b16 的 INFO-3）：`GET /api/v1/laws/catalog` 在 §10.86
    从 `async def` 改成 `def` 之后**可以并发进来**（anyio 池 16 个线程），而
    "`PRAGMA table_info` 看到缺列 → `ALTER TABLE ADD COLUMN`"是**读-改-写竞态**：
    b16 实测 32 线程并发在"旧库缺列"分支上 **31/32 抛 `sqlite3.OperationalError:
    duplicate column name: category`**（`query_catalog` 不 catch、路由只 catch
    `TypeError/ValueError` ⇒ 会变成 500）。改前它在事件循环里**串行**执行，走不到这个竞态。

    修法（三层）：
      ⓪ **只读快路径**：这条函数被 `query_catalog()` **每个请求**调用，而它在稳态下什么都不用做
         ⇒ 先用 `PRAGMA table_info` + `PRAGMA index_list`（**都是读**）确认"表/列/索引都齐"
         就直接返回。**不拿写锁**——否则每次翻法规目录都要 `BEGIN IMMEDIATE`，把一条纯读端点的
         延迟绑到"当前有没有别的写者"上（那是本步第一版修法自己引入的问题，已改掉）。
      ① 需要迁移时，整个迁移收进 `write_transaction()`（`BEGIN IMMEDIATE`）⇒ 同一时刻只有一个
         写者做读-改-写，竞态从根上消失；
      ② 仍对 `duplicate column name` 兜底 —— 迁移本来就该容忍"别人已经补上了"。
    ⚠ 调用方显式传了 `conn` 时不再套一层（SQLite 不支持嵌套 `BEGIN`），只做 ②；
    `conn` 已在事务里时同理（`write_transaction` 会先提交遗留的隐式事务，那会破坏调用方的事务）。
    """
    c = conn if conn is not None else get_db_connection()
    if _catalog_schema_current(c):
        return                                  # ⓪ 稳态：纯读检查后直接返回，不拿写锁
    if conn is None:
        with write_transaction() as w:
            _catalog_migration(w)
        return
    _catalog_migration(conn)


def _catalog_schema_current(conn) -> bool:
    """表、两列、三条索引都在吗？（**只读**；表不存在 ⇒ False）"""
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(law_catalog)").fetchall()}
        if not cols or not set(_CATALOG_COLUMNS) <= cols:
            return False
        idx = {r[1] for r in conn.execute("PRAGMA index_list(law_catalog)").fetchall()}
        return set(_CATALOG_INDEXES) <= idx
    except sqlite3.Error:                        # pragma: no cover - 库坏了就交给迁移去报错
        return False


def _catalog_migration(conn) -> None:
    conn.execute(_DDL)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(law_catalog)").fetchall()}
    for col in _CATALOG_COLUMNS:      # 存量旧版本表补列（新增列一律可空，幂等）
        if col in cols:
            continue
        try:
            conn.execute(f"ALTER TABLE law_catalog ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError as e:
            # 并发下另一个写者刚好补上了同一列 ⇒ 目标状态已达成，按幂等处理
            if "duplicate column name" not in str(e):
                raise
            logger.debug("law_catalog.%s 已由并发写者补上（幂等跳过）", col)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_law_catalog_title ON law_catalog(title)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_law_catalog_cat ON law_catalog(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_law_catalog_sxx ON law_catalog(sxx)")
    conn.commit()


# ---------------------------------------------------------------------------
# 枚举解析：动态取分类叶子 code（tolerant walker，兼容字段名漂移）
# ---------------------------------------------------------------------------

_CODE_KEYS = ("codeId", "code", "i", "id", "key")   # 真实 flk 用 codeId；测试/旧格式用 code
_NAME_KEYS = ("name", "n", "label", "mc")
_CHILD_KEYS = ("children", "c", "child", "sub", "items")
_AGGREGATE_NAMES = {"全部", "请选择", "-", ""}     # 聚合占位节点，非真实分类


def _pick(d: dict, keys: tuple[str, ...]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def extract_category_leaves(enum_data: dict) -> list[tuple[str, str]]:
    """enum_data() 响应 → [(叶子code, 名称)]；递归收集无 children 的节点。

    兼容多种键名（code/i/id + name/n/label）；跳过「全部/请选择」聚合节点与重码。
    """
    leaves: dict[str, str] = {}
    seen_order: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for it in node:
                walk(it)
            return
        if not isinstance(node, dict):
            return
        children = _pick(node, _CHILD_KEYS)
        code = _pick(node, _CODE_KEYS)
        name = _pick(node, _NAME_KEYS)
        if children:
            walk(children)
            return
        if code and name and str(name) not in _AGGREGATE_NAMES:
            code, name = str(code), str(name)
            if code not in leaves:
                leaves[code] = name
                seen_order.append(code)
            return
        for v in node.values():          # 容器节点（如 flfgCode 包裹层）继续下钻
            walk(v)

    # 顶层可能是 {"data": {...}} 包裹，也可能直接是字典树
    root = enum_data.get("data", enum_data) if isinstance(enum_data, dict) else enum_data
    # 真实 flk 响应 data 含 flfgfl(分类)/zdjgfl(机关)/flcaStatus(时效) 三棵树，
    # 只取分类树（flfgCodeId 是 flfgCodeId 搜索键），避免机关/时效 code 混入分类。
    # 测试/旧格式用 flfgCode 键；无这两个键则原样下钻。
    if isinstance(root, dict):
        root = root.get("flfgfl") or root.get("flfgCode") or root
    walk(root)
    return [(c, leaves[c]) for c in seen_order]


# ---------------------------------------------------------------------------
# 账本 manifest
# ---------------------------------------------------------------------------

def _load_manifest() -> dict:
    p = manifest_path()
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(m, dict) and m.get("version") == 1:
            m.setdefault("categories", {})
            m.setdefault("laws", {})
            return m
    except FileNotFoundError:
        pass
    except Exception as e:  # noqa: BLE001 账本损坏 → 重置（目录数据在 SQLite，可重建）
        logger.warning("law_manifest.json 读取失败，重置账本: %s", e)
    return {"version": 1, "updated_at": "", "categories": {}, "laws": {}}


def _save_manifest(m: dict) -> None:
    p = manifest_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    m["updated_at"] = _now()
    tmp = p.with_suffix(".json.part")
    tmp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)   # .part 原子替换，断电不留半截账本


# ---------------------------------------------------------------------------
# 对账：aggregateData 分类计数（形状未知 → 容忍式提取 (名称/code → 计数)）
# ---------------------------------------------------------------------------

_COUNT_KEYS = ("count", "num", "cnt", "total", "sl")


def parse_aggregate(data: dict) -> dict[str, int]:
    """aggregateData 响应 → {分类名或code: 计数}；找不到任何计数对返回 {}。"""
    out: dict[str, int] = {}

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for it in node:
                walk(it)
            return
        if not isinstance(node, dict):
            return
        cnt = _pick(node, _COUNT_KEYS)
        if isinstance(cnt, (int, float)) and not isinstance(cnt, bool):
            key = _pick(node, _NAME_KEYS) or _pick(node, _CODE_KEYS)
            if key is not None:
                out[str(key)] = int(cnt)
                return
        for v in node.values():
            walk(v)

    walk(data.get("data", data) if isinstance(data, dict) else data)
    return out


def _reconcile_warnings(agg_map: dict[str, int], cats: list[tuple[str, str]],
                        local_by_cat: dict[str, int]) -> list[str]:
    warnings: list[str] = []
    for code, name in cats:
        remote = agg_map.get(name, agg_map.get(code))
        local = local_by_cat.get(name, 0)
        if remote is not None and remote != local:
            warnings.append(f"对账差异[{name}]: 远端 {remote} vs 本地 {local}")
    return warnings


# ---------------------------------------------------------------------------
# 刷新主流程
# ---------------------------------------------------------------------------

def _norm_sxx(v: Any) -> int | None:
    if isinstance(v, bool):          # 避免 int(True)==1 误判为 sxx=1"已废止"
        return None
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def refresh_catalog(progress_cb: ManifestCb | None = None,
                    *, force: bool = False) -> dict:
    """全量遍历 flk 清单入 law_catalog。返回 {total, by_category, warnings, ...}。

    progress_cb(dict)：阶段事件 enum/crawl/reconcile/done（集成方可用于 SSE 进度）。
    force=True：忽略账本增量跳过（DB 与账本不同步时用）。
    单分类失败只记 warning 继续（断点续传语义：下次运行该分类重来，幂等 upsert 兜底）。
    """
    t0 = time.time()
    progress = progress_cb or (lambda _p: None)
    ensure_catalog_schema()
    warnings: list[str] = []

    enums = flk_client.enum_data()
    cats = extract_category_leaves(enums)
    if not cats:
        raise RuntimeError("enum_data 未解析到任何分类叶子（flk 接口结构变更？）")
    progress({"stage": "enum", "categories": len(cats)})

    manifest = _load_manifest()
    cat_state = manifest["categories"]
    law_state: dict[str, dict] = manifest["laws"]

    pending: list[dict] = []           # 待写库行缓冲
    pending_keys: set[str] = set()     # 同批去重（跨页/跨分类重叠）
    fetched = skipped = dup_seen = written = 0

    def flush() -> None:
        nonlocal written, pending, pending_keys
        if not pending:
            return
        with write_transaction() as txn:
            for r in pending:
                # 列名加引号：SQLite 对未引号列名的 upsert SET 解析存在歧义
                # （实测 3.53 报 no such column: excluded.flsxz，引号后正常）
                txn.execute(
                    """INSERT INTO law_catalog
                       (title, bbbs, flxz, sxx, category, gbrq, sxrq, updated_at)
                       VALUES (?,?,?,?,?,?,?,?)
                       ON CONFLICT(bbbs) DO UPDATE SET
                         "title"=excluded."title", "flxz"=excluded."flxz",
                         "sxx"=excluded."sxx", "gbrq"=excluded."gbrq",
                         "sxrq"=excluded."sxrq", "updated_at"=excluded."updated_at"
                     """,
                    (r["title"], r["bbbs"], r["flxz"], r["sxx"], r["category"],
                     r["gbrq"], r["sxrq"], r["updated_at"]))
        for r in pending:   # 写库成功后才记账（账本是 DB 的镜像承诺）
            law_state[r["bbbs"]] = {"title": r["title"], "sxx": r["sxx"],
                                    "fetched_at": r["updated_at"]}
        written += len(pending)
        pending, pending_keys = [], set()

    for idx, (code, name) in enumerate(cats, 1):
        page, cat_fetched = 1, 0
        try:
            while True:
                data = flk_client.search("", search_range=1, search_type=2,
                                         category_ids=[code],
                                         page=page, page_size=PAGE_SIZE)
                total = int(data.get("total") or 0)
                rows = [r for r in flk_client.parse_rows(data) if r.get("bbbs")]
                if not rows:
                    break
                for r in rows:
                    bbbs = str(r["bbbs"])
                    if bbbs in pending_keys:
                        dup_seen += 1
                        continue
                    sxx = _norm_sxx(r.get("sxx"))
                    title = r.get("title") or ""
                    prev = law_state.get(bbbs)
                    if prev and not force and prev.get("title") == title \
                            and prev.get("sxx") == sxx:
                        skipped += 1          # 已入库且 title/sxx 未变 → 增量跳过
                        continue
                    fetched += 1
                    pending.append({
                        "bbbs": bbbs, "title": title, "flxz": r.get("flxz"),
                        "sxx": sxx, "category": name, "gbrq": r.get("gbrq"),
                        "sxrq": r.get("sxrq"), "updated_at": _now(),
                    })
                    pending_keys.add(bbbs)
                    if len(pending) >= _BATCH_WRITE:
                        flush()
                cat_fetched += len(rows)
                progress({"stage": "crawl", "category": name, "page": page,
                          "got": cat_fetched, "remote_total": total})
                if cat_fetched >= total or len(rows) < PAGE_SIZE:
                    break
                page += 1
                # 翻页保险丝：超出理论页数+2 视为接口异常，防 WAF 软拦下的无限翻页
                if page > math.ceil(total / PAGE_SIZE) + 1:
                    msg = f"分类[{name}]翻页超限（total={total}），提前终止"
                    warnings.append(msg)
                    logger.warning(msg)
                    break
        except Exception as e:  # noqa: BLE001 单分类失败不断全局（断点续传）
            flush()
            msg = f"分类[{name}]抓取失败: {e}"
            warnings.append(msg)
            logger.warning(msg)
            # 失败分类不标 done（下次运行整分类重来，upsert 幂等兜底）
            cat_state[code] = {"name": name, "done": False, "fetched": cat_fetched,
                               "error": str(e)[:200], "finished_at": _now()}
            _save_manifest(manifest)
            continue
        cat_state[code] = {"name": name, "done": True, "fetched": cat_fetched,
                           "finished_at": _now()}
        _save_manifest(manifest)      # 分类级断点落盘
    flush()
    _save_manifest(manifest)

    # 对账（best-effort：aggregateData 交叉核对，防漏旁路；官方该端点不返回 JSON
    # （返回 SPA HTML / 405），故失败仅 debug 记录，绝不误报为目录缺陷——完整性已由
    # 爬取时每分类 search 的 remote_total 顶满 + 翻页保险丝告警保证）。
    progress({"stage": "reconcile"})
    agg_map: dict[str, int] = {}
    try:
        agg_raw = fetch_json(_AGGREGATE_URL, referer=f"{flk_client.BASE}/")
        agg_map = parse_aggregate(agg_raw)
    except Exception as e:  # noqa: BLE001 — 官方无 JSON 端点，静默跳过而非误报
        logger.debug("aggregateData 对账不可用（忽略）: %s", e)
    conn = get_db_connection()
    local_by_cat = {r["category"] or "": r["n"] for r in conn.execute(
        "SELECT category, COUNT(*) AS n FROM law_catalog GROUP BY category").fetchall()}
    warnings.extend(_reconcile_warnings(agg_map, cats, local_by_cat))

    by_cat = {k: v for k, v in sorted(local_by_cat.items(), key=lambda kv: -kv[1])}
    total = sum(local_by_cat.values())
    out = {"total": total, "by_category": by_cat, "warnings": warnings,
           "fetched": fetched, "skipped": skipped, "duplicate_seen": dup_seen,
           "written": written, "elapsed_sec": round(time.time() - t0, 1)}
    progress({"stage": "done", **out})
    return out


# ---------------------------------------------------------------------------
# 分页查询
# ---------------------------------------------------------------------------

def query_catalog(q: str = "", category: str = "", sxx: Any = "",
                  page: int = 1, page_size: int = 50) -> dict:
    """本地目录分页查询（标题模糊 + 分类/效力过滤）。

    返回 {items:[{title,bbbs,flxz,sxx,category,gbrq,sxrq}], total, page, page_size,
          pages, categories}；categories 为可选 facet（集成端透传给前端下拉即可，
    无则前端自行降级）。排序：公布日期新→旧（空日期沉底），bbbs 稳定次序。

    分页决策（2026-08-26）：维持 OFFSET——排序键 gbrq 可空（NULL 沉底语义）使
    keyset 条件复杂易错；3 万条目录本地 SQLite OFFSET 深翻页 <50ms 非实际瓶颈。
    若目录到百万级再改：ORDER BY (gbrq, bbbs) 键集 + NULL 分支显式处理。
    """
    ensure_catalog_schema()
    page = max(1, int(page))
    page_size = min(max(1, int(page_size)), 200)

    where: list[str] = []
    params: list[object] = []
    q = (q or "").strip()
    if q:
        where.append("title LIKE ?")
        params.append(f"%{q}%")
    category = (category or "").strip()
    if category:
        where.append("category = ?")
        params.append(category)
    sxx_n = _norm_sxx(sxx if sxx != "" else None)
    if sxx_n is not None:
        where.append("sxx = ?")
        params.append(sxx_n)
    cond = (" WHERE " + " AND ".join(where)) if where else ""

    conn = get_db_connection()
    total = conn.execute(
        f"SELECT COUNT(*) FROM law_catalog{cond}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT title, bbbs, flxz, sxx, category, gbrq, sxrq FROM law_catalog{cond}
            ORDER BY gbrq DESC, bbbs ASC LIMIT ? OFFSET ?""",
        [*params, page_size, (page - 1) * page_size]).fetchall()
    categories = [r[0] or "" for r in conn.execute(
        "SELECT DISTINCT category FROM law_catalog ORDER BY category").fetchall()]
    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, math.ceil(total / page_size)),
        "categories": categories,
    }
