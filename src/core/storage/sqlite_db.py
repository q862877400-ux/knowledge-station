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
