"""SQLite 连接管理与初始化（WAL + 外键 + busy_timeout + sqlite-vec 扩展）。"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from src.core.config import get_settings
from src.core.exceptions import StorageError

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

_local = threading.local()

#: 跨线程登记「这份连接挂在**哪个线程**的 `_local` 的**哪把键**上」——
#: 只给 `close_all_connections()` 用（`_local` 是线程局部代理，**直接**拿别的线程那份是拿不到的；
#: 但建连接的那一刻就在那个线程里，可以顺手 `vars(_local)` 把它那份**字典对象**抓下来，
#: 主线程之后改这个字典，拥有它的线程**看得见** —— 2026-09-22 用
#: `var/tmp/probe-threadlocal-handoff.py` 实测过：摘掉键之后那个线程再读就是 AttributeError）。
#: ⚠ `sqlite3.Connection` **不支持 weakref**（实测 `TypeError: cannot create weak reference`），
#: 所以这里只能存强引用；登记表在 `close_thread_connection()` / `close_all_connections()`
#: 里随关随清（建连接时也顺手剔掉已被关掉的登记），不会无限涨。
_registry: list[tuple[sqlite3.Connection, dict[str, object], str]] = []
_registry_lock = threading.Lock()


def _register(conn: sqlite3.Connection, owner: dict[str, object], key: str) -> None:
    with _registry_lock:
        # 顺手剔掉"键已经不在那个字典里（或已被换掉）"的旧登记：那是已经被关掉/替换掉的连接。
        _registry[:] = [e for e in _registry if e[1].get(e[2]) is e[0]]
        _registry.append((conn, owner, key))


def load_vec_extension(conn: sqlite3.Connection) -> bool:
    """加载 sqlite-vec 扩展；失败时返回 False（检索自动降级，见 R30）。"""
    try:
        import sqlite_vec  # type: ignore[import-untyped]  # sqlite-vec 无 stub；忽略配置之外的双保险
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except Exception:
        return False


def _configure(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # 2026-08-28 修复：5000→60000ms。三分片并发入库（每本文档事务含
    # FTS + 向量插入，单事务可达数秒）时 5s 排队必然超时 → 60% 入库
    # 报 database is locked。写锁竞争是瞬态的，60s 足够 absorbs。
    conn.execute("PRAGMA busy_timeout=60000")


def get_db_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """线程局部连接。默认使用配置中心的库路径。"""
    path = db_path or get_settings().db_path
    key = "conn_default" if db_path is None else f"conn_{path}"
    conn = getattr(_local, key, None)
    if conn is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), check_same_thread=False)
        _configure(conn)
        setattr(_local, key, conn)
        _register(conn, vars(_local), key)
    return conn


@contextmanager
def write_transaction(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """短事务上下文：由单写者队列调用，普通代码不应直接绕过队列写库。

    ⚠ **`except BaseException`，不是 `Exception`**（2026-09-18，独立复核 b32 的 4.5 实测）：
    `KeyboardInterrupt` **不是** `Exception` 的子类，所以写成 `except Exception` 时
    Ctrl-C 打在事务中间**不会回滚**——事务留在连接上，随后的"写后核对"读的是**未提交状态**，
    可能打印/落盘一份"从未真正入库的成功"，而真正的落库与否要等连接关闭才见分晓。
    数据本身不会半写（连接关闭时 SQLite 会回滚），但**诊断会撒谎**，而"以为写成功了"是更贵的错。
    改成 `BaseException` 后：中断 → 回滚 → 原样抛出（对 `Exception` 那条路的语义一字未变）。
    """
    conn = get_db_connection(db_path)
    if conn.in_transaction:  # 清理遗留的隐式事务，保证 BEGIN IMMEDIATE 可执行
        conn.commit()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def init_schema(db_path: Path | None = None) -> None:
    conn = get_db_connection(db_path)
    load_vec_extension(conn)
    try:
        conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        _ensure_doc_meta_columns(conn)
        _ensure_bookmark_folder_columns(conn)
        _ensure_channel_columns(conn)
        conn.commit()
    except sqlite3.Error as e:
        raise StorageError(f"初始化 schema 失败: {e}") from e


#: doc_meta 增量列（2026-08-27 体检回流）：已有库 ALTER 补列；幂等（PRAGMA 缺才 ADD）
_DOC_META_EXTRA_COLS: list[tuple[str, str]] = [
    ("published_at", "TEXT"),   # 官方发布日期（cssn a101）
    ("ccs_code", "TEXT"),       # CCS 分类代码（cssn a825）
    ("ccs_name", "TEXT"),       # CCS 分类名称（cssn a825name）
    ("ics", "TEXT"),            # ICS 分类名称（cssn a826name）
    ("withdrawn_date", "TEXT"), # 废止日期（cssn a206 / ndls a206）
]


def _ensure_doc_meta_columns(conn) -> None:
    """给既有知识库 doc_meta 补新增列（CREATE IF NOT EXISTS 不会改已有表）。
    幂等：仅对缺列执行 ALTER TABLE ADD COLUMN；并发/重复调用安全。
    """
    existing = {r[1] for r in conn.execute("PRAGMA table_info(doc_meta)").fetchall()}
    for col, ddl_type in _DOC_META_EXTRA_COLS:
        if col not in existing:
            conn.execute(f"ALTER TABLE doc_meta ADD COLUMN {col} {ddl_type}")


#: 收藏夹迁移（2026-10 收藏目录）：既有 user_bookmark / user_doc_bookmark 补 folder_id
#: 列。schema.sql 的新库直接带列；老库 CREATE IF NOT EXISTS 不会改表 → PRAGMA 补列。
#: folder_id 不设表级 FK（补列 ALTER 无法加约束）——应用层（user_data）负责引用完整，
#: 删夹时 UPDATE ... SET folder_id=NULL（收藏回「未分类」，绝不连坐删收藏）。
_BOOKMARK_FOLDER_COLUMNS: list[tuple[str, str, str]] = [
    ("user_bookmark", "folder_id", "TEXT"),
    ("user_doc_bookmark", "folder_id", "TEXT"),
]


def _ensure_bookmark_folder_columns(conn) -> None:
    """幂等：仅对缺列执行 ALTER TABLE ADD COLUMN。"""
    for table, col, ddl_type in _BOOKMARK_FOLDER_COLUMNS:
        existing = {r[1] for r in conn.execute(
            f"PRAGMA table_info({table})").fetchall()}
        if col not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl_type}")


#: 渠道台账补列（§11.0 R7，2026-09-19）：`segments_json` = 号段（号段→渠道的**可维护事实**）。
#: schema.sql 的新库直接带列；老库 CREATE IF NOT EXISTS 不会改表 → PRAGMA 补列。
_CHANNEL_EXTRA_COLS: list[tuple[str, str]] = [
    ("segments_json", "TEXT"),
]


def _ensure_channel_columns(conn) -> None:
    """幂等：仅对缺列执行 ALTER TABLE ADD COLUMN（与上面两条同形）。"""
    existing = {r[1] for r in conn.execute("PRAGMA table_info(update_channel)").fetchall()}
    for col, ddl_type in _CHANNEL_EXTRA_COLS:
        if col not in existing:
            conn.execute(f"ALTER TABLE update_channel ADD COLUMN {col} {ddl_type}")


def list_tables(db_path: Path | None = None) -> list[str]:
    conn = get_db_connection(db_path)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def close_thread_connection() -> None:
    for key in list(vars(_local)):
        conn = getattr(_local, key, None)
        if isinstance(conn, sqlite3.Connection):
            conn.close()
            delattr(_local, key)
            _forget(conn)


def _forget(conn: sqlite3.Connection) -> None:
    """把这份连接从跨线程登记表里摘掉（关掉它的时候调）。"""
    with _registry_lock:
        _registry[:] = [e for e in _registry if e[0] is not conn]


def close_all_connections() -> int:
    """把**所有线程**上登记的库连接都关掉，返回关掉的个数。

    ## 为什么需要它（2026-09-22 实测，不是推测）

    `close_thread_connection()` 只关**调用线程**那一份。而 FastAPI 的**同步**路由是跑在
    AnyIO 线程池的 worker 线程里的 —— 那些线程自己会 `get_db_connection()` 建一份并一直握着
    （线程池线程活得比用例长）。后果：Windows 上临时数据目录**删不掉**
    （`PermissionError: [WinError 32] ... knowledge.db`），而各处的
    `TemporaryDirectory(..., ignore_cleanup_errors=True)` 会把这条失败**静默吞掉** ——
    实测每跑一次 `tests/test_kb_scope_retrieval.py` 就漏一个 ~2.6 MB 的 `ks_scope_*` 目录，
    会话级那个 `ks_test_*` 目录同样漏（2026-09-22 清点时 `%TEMP%` 里已积压上千个）。

    ⚠ **关的同时必须把那个线程 `_local` 里的键摘掉**：不摘的话，那个（会被复用的）线程
    下次 `get_db_connection()` 拿到的是**已关闭**的连接，报
    `Cannot operate on a closed database`。摘键靠建连接时抓下来的那份字典对象，
    实测在那个线程里立刻可见（见 `_registry` 的注释）。

    用途：整进程优雅退场、以及测试收尾（测试库要能真删掉）。
    """
    with _registry_lock:
        entries, _registry[:] = list(_registry), []
    closed = 0
    for conn, owner, key in entries:
        if owner.get(key) is conn:
            owner.pop(key, None)          # 先摘键再关：别让别的线程捞到一个正在关的连接
        try:
            conn.close()
            closed += 1
        except sqlite3.Error:
            # 已经关掉的连接再 close() 是 no-op；真出错也只影响"关得干净不干净"，
            # 这里如实计数、不假装成功（调用方按 `closed` 与自己的清单对账）。
            continue
    return closed
