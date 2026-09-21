"""知识库多级目录的读写层（KB-FOLDER-PLAN 第 1 步：只做「存」的那一层）。

方案真源：``docs/KB-FOLDER-PLAN.md``（§3 数据形状 / §四 能力清单 / §二 三条自定规则）。
本模块**只有引擎侧函数**：不含界面、不含 HTTP 接口（那是方案 §五的第 2/3 步）。

════ 两套父子关系怎么分工（方案 §3 同时定了 ``parent_id`` 与 ``item_kind='folder'``）════

* ``folder.parent_id`` = **主位置**（唯一）。``parent_id IS NULL`` ⇔ 该目录**在顶层出现**
  （方案 §3 原文口径）。挪动/改名改的是它，深度与"落在哪儿"也由它决定。
* ``folder_member(item_kind='folder')`` = **全部**父子边（可多条）。复制目录会让同一个
  子目录同时挂在两个上级下（"同一份挂两处"，方案 §三复制语义），只有它能表达。
* 不变式（本模块的写函数维护）：``F.parent_id = P`` ⇒ 必有成员行 ``(P,'folder',F)``。
* 读路径（列表/子树/范围）**只认 ``folder_member``**，再把 ``parent_id`` 作为**并集**
  走一遍 —— 历史数据漂移也读得到；遍历用 ``seen``/``visiting`` 去重 ⇒ **即使库里已有环
  也会终止**（不靠"不会有环"这个假设活命）。

════ 写函数逐一强制的不变量 ════

* **无环**：把目录挪进它自己或它的任何下级 ⇒ 拒绝（``folder_cycle``）。
* **同名同层拒绝（含根层）** ⇒ ``folder_name_conflict``；名字/路径有上限 ⇒ 可读报错。
* **删目录分三种情形**（方案 §二第 2 条，业主 2026-09-21 选定"先问一句"这版）：
  空目录**直接删**；非空目录**必须**由调用方给出模式 —— ``reparent``（只删这个目录，
  直接成员挪到上一层）或 ``purge``（删这棵子树，**只有"在别处也不出现了"的文件才真删**）。
  ``mode=None`` 且非空 ⇒ 可读报错（**不**默认选一种）；一级目录**没有上一层** ⇒
  ``reparent`` 对它明确报错（**不**静默改成 purge）。
* **归属是多对多**：复制目录**不**拷成员内容，只让新目录指向**同一批** ``item_id``。

════ 已知取舍（写在这里，免得日后当 bug 查）════

1. 挪动目录会连它在**原主位置**的那条成员边一起移走。若那个位置本来就是"复制出来的
   一处"，那一处也会一并消失 —— 两种边落在同一张表里，**无法区分来路**。
2. 排序按名字的 **Unicode 码位**（``ORDER BY name``），不是拼音。稳定但不合中文语感，
   方案只要求"按名字排"，拼音序要额外的排序键，留到有需求时再说。
3. 读函数（``list_folder`` / ``folder_scope`` / 两个状态列表）**不开写事务**：它们是
   只读的，在 2.2 GB 真库上抢写锁会把入库挡在后面。写函数一律走
   ``write_transaction``（BEGIN IMMEDIATE，单写者纪律）。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from ulid import ULID

from src.core.exceptions import KnowledgeStationError
from src.core.storage.sqlite_db import get_db_connection, write_transaction

#: 目录名长度上限（实测真库最长分类名 28 字符 ⇒ 60 有充裕余量）
MAX_NAME_LEN = 60
#: 层数上限（方案要求"无限层级"，但"不限"= 可以构造任意深的路径 ⇒ 给一个远大于实用值的上限）
MAX_DEPTH = 12
#: 完整路径（各级名字用 `/` 连起来）长度上限
MAX_PATH_LEN = 240

ITEM_KINDS: tuple[str, ...] = ("folder", "file")

#: 删非空目录的两种模式（方案 §二第 2 条）；空目录不需要模式
DELETE_MODES: tuple[str, ...] = ("reparent", "purge")

#: 处理状态五枚举 —— 与 schema.sql 的 CHECK 一字不差
STAGES: tuple[str, ...] = ("queued", "recognizing", "confirming", "filed", "failed")
STAGE_LABELS: dict[str, str] = {
    "queued": "排队中",
    "recognizing": "识别中",
    "confirming": "待确认",
    "filed": "已归位",
    "failed": "识别失败",
}
#: 还没归位的状态（「待分类」列表口径；**无状态行 = 从未处理，按 queued 算**）
UNFILED_STAGES: tuple[str, ...] = ("queued", "recognizing", "confirming", "failed")

#: set_filing_state 允许写的字段（白名单，防拼错列名静默写空）
_STATE_FIELDS: tuple[str, ...] = (
    "confidence", "failure_kind", "suggested_folder_id", "suggest_new_path",
    "placed_folder_id", "placed_by", "placed_at", "last_error",
)

_BAD_NAME_CHARS: tuple[str, ...] = ("\\", "\x00")
# ⚠ 名字里**允许斜杠**（2026-09-21 预览实测）：CCS 区间名本身就带 `/`
#   （`P15/19 工程抗震、工程防火、人防工程`、`A00/09 标准化管理与一般规定`…），
#   而它们是**真实存在的** L3 目录名 —— 禁掉斜杠等于禁掉现有分类树。
#   安全前提：目录一律靠 folder_id 引用，**从不按路径解析**，所以名字里的斜杠
#   没有解析歧义；"显示出来的路径"用 ` › ` 连接（见 folder_filing_plan）。


def _err(msg: str, code: str) -> KnowledgeStationError:
    return KnowledgeStationError(msg, code=code)


def _doc_columns(conn: sqlite3.Connection) -> list[str]:
    """doc_meta 的实际列集（不同库版本列数不同 ⇒ 不写 ``SELECT *``）。"""
    return [r[1] for r in conn.execute("PRAGMA table_info(doc_meta)").fetchall()]


def _visible_clause(conn: sqlite3.Connection, alias: str = "d") -> str:
    """"这篇文档在目录里可见"的判据。

    ``doc_meta.catalog_hidden`` **不在 schema.sql 里**（它是 ``clause_repo`` 的增量列，
    生产由 ``create_app`` → ``ensure_additive_columns()`` 补上）。列在就用它过滤，
    列不在就当全可见 —— 直接写死列名会让"只跑过 init_schema 的库"当场报
    ``no such column``，而那不是本模块的错，却长得像。
    """
    if "catalog_hidden" in _doc_columns(conn):
        return f"COALESCE({alias}.catalog_hidden, 0) = 0"
    return "1 = 1"


# ──────────────────────────────── 校验与内部工具 ────────────────────────────────

def _clean_name(raw: Any) -> str:
    """目录名校验：非空、有长度上限、不含路径分隔符/控制字符。"""
    name = str(raw if raw is not None else "").strip()
    if not name:
        raise _err("目录名不能为空", "invalid_folder_name")
    if len(name) > MAX_NAME_LEN:
        raise _err(f"目录名过长：{len(name)} 字符，上限 {MAX_NAME_LEN} 字符",
                   "invalid_folder_name")
    if name in (".", ".."):
        raise _err("目录名不能是 . 或 ..", "invalid_folder_name")
    for ch in _BAD_NAME_CHARS:
        if ch in name:
            raise _err("目录名不能含 \\ 或空字符", "invalid_folder_name")
    if any(ord(c) < 32 for c in name):
        raise _err("目录名不能含换行等控制字符", "invalid_folder_name")
    return name


def _folder_row(conn: sqlite3.Connection, folder_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT folder_id, parent_id, name, sort, created_at FROM folder"
        " WHERE folder_id=?", (folder_id,)).fetchone()
    if row is None:
        raise _err(f"目录不存在: {folder_id}", "folder_not_found")
    return row


def _ancestors(conn: sqlite3.Connection, folder_id: str) -> list[str]:
    """从**顶层往下**到 ``folder_id`` 的祖先链（不含自身）。遇到环当场报错。"""
    chain: list[str] = []
    seen: set[str] = set()
    cur = _folder_row(conn, folder_id)["parent_id"]
    while cur is not None:
        if cur in seen:
            raise _err("目录层级里存在环，数据已损坏", "folder_cycle")
        seen.add(cur)
        chain.append(cur)
        if len(chain) > MAX_DEPTH * 4:
            raise _err("目录层级异常深（疑似环）", "folder_cycle")
        cur = _folder_row(conn, cur)["parent_id"]
    chain.reverse()
    return chain


def _depth_of(conn: sqlite3.Connection, folder_id: str) -> int:
    """层级：顶层目录 = 1。"""
    return len(_ancestors(conn, folder_id)) + 1


def _path_names(conn: sqlite3.Connection, folder_id: str | None) -> list[str]:
    """``folder_id`` 的完整名字路径（从顶层往下）；None（顶层容器）= 空列表。"""
    if folder_id is None:
        return []
    chain = _ancestors(conn, folder_id) + [folder_id]
    return [_folder_row(conn, fid)["name"] for fid in chain]


def _folder_edges(conn: sqlite3.Connection) -> dict[str, set[str]]:
    """container → 下级目录集合（成员边 ∪ ``parent_id``，两源并集）。"""
    edges: dict[str, set[str]] = {}
    for r in conn.execute(
            "SELECT folder_id, item_id FROM folder_member WHERE item_kind='folder'"):
        edges.setdefault(r["folder_id"], set()).add(r["item_id"])
    for r in conn.execute(
            "SELECT parent_id, folder_id FROM folder WHERE parent_id IS NOT NULL"):
        edges.setdefault(r["parent_id"], set()).add(r["folder_id"])
    return edges


def _file_edges(conn: sqlite3.Connection) -> dict[str, set[str]]:
    """container → **直接**放在这一级的文件集合。"""
    edges: dict[str, set[str]] = {}
    for r in conn.execute(
            "SELECT folder_id, item_id FROM folder_member WHERE item_kind='file'"):
        edges.setdefault(r["folder_id"], set()).add(r["item_id"])
    return edges


def _subtree_ids(conn: sqlite3.Connection, root_ids: Iterable[str],
                 edges: dict[str, set[str]] | None = None) -> set[str]:
    """root_ids 及其**所有下级**的目录 id（seen 去重 ⇒ 有环也会终止）。"""
    edges = _folder_edges(conn) if edges is None else edges
    seen: set[str] = set()
    stack = list(root_ids)
    while stack:
        fid = stack.pop()
        if fid in seen:
            continue
        seen.add(fid)
        stack.extend(edges.get(fid, ()))
    return seen


def _subtree_height(conn: sqlite3.Connection, root: str,
                    edges: dict[str, set[str]] | None = None,
                    memo: dict[str, int] | None = None,
                    visiting: set[str] | None = None) -> int:
    """子树**高度**（含自己）：只有自己 = 1。

    递归深度由写路径强制的 ``MAX_DEPTH`` 兜住；``visiting`` 保证**即使库里有环也返回**
    （环处收口成 1），读/校验路径不因坏数据挂死。
    """
    if edges is None:
        edges = _folder_edges(conn)
    if memo is None:
        memo = {}
    if visiting is None:
        visiting = set()
    if root in memo:
        return memo[root]
    if root in visiting:
        return 1
    visiting.add(root)
    height = 1
    for child in edges.get(root, ()):
        height = max(height, 1 + _subtree_height(conn, child, edges, memo, visiting))
    visiting.discard(root)
    memo[root] = height
    return height


def _subtree_suffix_len(conn: sqlite3.Connection, root: str, names: dict[str, str],
                        edges: dict[str, set[str]] | None = None,
                        memo: dict[str, int] | None = None,
                        visiting: set[str] | None = None) -> int:
    """子树里最长的一段"从某个下级到末级"的名字片段长度（算完整路径长度用）。"""
    if edges is None:
        edges = _folder_edges(conn)
    if memo is None:
        memo = {}
    if visiting is None:
        visiting = set()
    if root in memo:
        return memo[root]
    if root in visiting:
        return 0
    visiting.add(root)
    best = 0
    for child in edges.get(root, ()):
        best = max(best, len(names.get(child, "")) + 1
                   + _subtree_suffix_len(conn, child, names, edges, memo, visiting))
    visiting.discard(root)
    memo[root] = best
    return best


def _assert_path_len(conn: sqlite3.Connection, parent_id: str | None, name: str,
                     suffix_len: int = 0) -> None:
    """新建/改名/挪动后的**完整路径**长度必须在 MAX_PATH_LEN 以内。"""
    total = sum(len(n) + 1 for n in _path_names(conn, parent_id)) + len(name) + suffix_len
    if total > MAX_PATH_LEN:
        raise _err(f"目录路径过长：约 {total} 字符，上限 {MAX_PATH_LEN} 字符",
                   "invalid_folder_name")


def _assert_name_free(conn: sqlite3.Connection, parent_id: str | None, name: str,
                      exclude_id: str | None = None) -> None:
    """同名同层拒绝（含根层）。DB 侧另有两条件部分唯一索引兜底（见 schema.sql）。"""
    if parent_id is None:
        row = conn.execute("SELECT folder_id FROM folder WHERE parent_id IS NULL AND name=?",
                           (name,)).fetchone()
    else:
        row = conn.execute("SELECT folder_id FROM folder WHERE parent_id=? AND name=?",
                           (parent_id, name)).fetchone()
    if row is not None and row["folder_id"] != exclude_id:
        raise _err(f"同一层已有同名目录: {name}", "folder_name_conflict")


def _unique_name(conn: sqlite3.Connection, parent_id: str | None, base: str) -> str:
    """在 parent_id 这一层给 base 找一个不冲突的名字（复制目录用，最多试 99 次）。"""
    for i in range(100):
        cand = base if i == 0 else (f"{base} (副本)" if i == 1 else f"{base} (副本{i})")
        if parent_id is None:
            dup = conn.execute("SELECT 1 FROM folder WHERE parent_id IS NULL AND name=?",
                               (cand,)).fetchone()
        else:
            dup = conn.execute("SELECT 1 FROM folder WHERE parent_id=? AND name=?",
                               (parent_id, cand)).fetchone()
        if dup is None:
            return _clean_name(cand)
    raise _err(f"同一层同名副本过多: {base}", "folder_name_conflict")


def _assert_folder_attach_ok(conn: sqlite3.Connection, container_id: str,
                             child_id: str) -> None:
    """把 child 挂进 container 的共性校验（自挂 / 成环）。"""
    if child_id == container_id:
        raise _err("不能把目录挂进它自己", "folder_cycle")
    if container_id in _subtree_ids(conn, [child_id]):
        raise _err("不能把目录挪进它的下级里（会成环）", "folder_cycle")


def _check_item_exists(conn: sqlite3.Connection, item_kind: str, item_id: str) -> None:
    if item_kind == "folder":
        _folder_row(conn, item_id)
        return
    if conn.execute("SELECT 1 FROM doc_meta WHERE doc_id=?", (item_id,)).fetchone() is None:
        raise _err(f"文档不存在: {item_id}", "doc_not_found")


def _create_folder_in_tx(conn: sqlite3.Connection, name: str, parent_id: str | None,
                         sort: int = 0) -> dict:
    """事务内建目录（调用方已开事务；create_folder 与 copy_folder 共用这一份）。"""
    clean = _clean_name(name)
    if parent_id is not None:
        _folder_row(conn, parent_id)
        if _depth_of(conn, parent_id) + 1 > MAX_DEPTH:
            raise _err(f"目录层数超过上限 {MAX_DEPTH} 层", "folder_depth_exceeded")
    _assert_name_free(conn, parent_id, clean)
    _assert_path_len(conn, parent_id, clean)
    fid = f"fld_{ULID()}"
    conn.execute("INSERT INTO folder(folder_id, parent_id, name, sort) VALUES (?,?,?,?)",
                 (fid, parent_id, clean, int(sort or 0)))
    if parent_id is not None:
        conn.execute("INSERT INTO folder_member(folder_id, item_kind, item_id) VALUES (?,?,?)",
                     (parent_id, "folder", fid))
    return {"folder_id": fid, "parent_id": parent_id, "name": clean, "sort": int(sort or 0)}


def _add_member_in_tx(conn: sqlite3.Connection, folder_id: str, item_kind: str,
                      item_id: str) -> bool:
    """事务内加成员；已挂在这一处则不加（多对多下重复挂同一处没有意义）。返回是否新加。"""
    if item_kind not in ITEM_KINDS:
        raise _err(f"item_kind 只能是 {ITEM_KINDS}，收到 {item_kind!r}", "invalid_item_kind")
    _folder_row(conn, folder_id)
    _check_item_exists(conn, item_kind, item_id)
    if item_kind == "folder":
        _assert_folder_attach_ok(conn, container_id=folder_id, child_id=item_id)
    cur = conn.execute(
        "INSERT OR IGNORE INTO folder_member(folder_id, item_kind, item_id) VALUES (?,?,?)",
        (folder_id, item_kind, item_id))
    return cur.rowcount > 0


# ─────────────────────────── 目录：建 / 改名 / 挪 / 复制 / 删 ───────────────────────────

def create_folder(name: str, parent_id: str | None = None, sort: int = 0,
                  db_path: Path | None = None) -> dict:
    """建目录（在 ``parent_id`` 下；``None`` = 顶层）。同名同层拒绝，层数/路径超限拒绝。"""
    with write_transaction(db_path) as conn:
        return _create_folder_in_tx(conn, name, parent_id, sort)


def rename_folder(folder_id: str, new_name: str, db_path: Path | None = None) -> dict:
    """改目录名（**只改库里的名字**，不动磁盘文件 —— 方案 §二第 1 条）。"""
    clean = _clean_name(new_name)
    with write_transaction(db_path) as conn:
        row = _folder_row(conn, folder_id)
        _assert_name_free(conn, row["parent_id"], clean, exclude_id=folder_id)
        names = {r["folder_id"]: r["name"] for r in
                 conn.execute("SELECT folder_id, name FROM folder")}
        _assert_path_len(conn, row["parent_id"], clean,
                         suffix_len=_subtree_suffix_len(conn, folder_id, names))
        conn.execute("UPDATE folder SET name=? WHERE folder_id=?", (clean, folder_id))
        return {"folder_id": folder_id, "name": clean, "parent_id": row["parent_id"]}


def move_folder(folder_id: str, new_parent_id: str | None,
                db_path: Path | None = None) -> dict:
    """挪目录到 ``new_parent_id`` 下（``None`` = 挪到顶层）。

    拒绝：挪进它自己 / 挪进它的任何下级（``folder_cycle``）、同名冲突、层数或路径超限。
    见模块头「已知取舍 1」：它在**原主位置**的那条成员边会一并移走。
    """
    with write_transaction(db_path) as conn:
        row = _folder_row(conn, folder_id)
        edges = _folder_edges(conn)
        if new_parent_id is not None:
            _folder_row(conn, new_parent_id)
            _assert_folder_attach_ok(conn, container_id=new_parent_id, child_id=folder_id)
            base_depth = _depth_of(conn, new_parent_id)
        else:
            base_depth = 0
        height = _subtree_height(conn, folder_id, edges)
        if base_depth + height > MAX_DEPTH:
            raise _err(
                f"挪过去会到第 {base_depth + height} 层，超过上限 {MAX_DEPTH} 层",
                "folder_depth_exceeded")
        _assert_name_free(conn, new_parent_id, row["name"], exclude_id=folder_id)
        names = {r["folder_id"]: r["name"] for r in
                 conn.execute("SELECT folder_id, name FROM folder")}
        _assert_path_len(conn, new_parent_id, row["name"],
                         suffix_len=_subtree_suffix_len(conn, folder_id, names, edges))
        old_parent = row["parent_id"]
        conn.execute("UPDATE folder SET parent_id=? WHERE folder_id=?",
                     (new_parent_id, folder_id))
        if old_parent is not None:
            conn.execute(
                "DELETE FROM folder_member WHERE folder_id=? AND item_kind='folder'"
                " AND item_id=?", (old_parent, folder_id))
        if new_parent_id is not None:
            conn.execute(
                "INSERT OR IGNORE INTO folder_member(folder_id, item_kind, item_id)"
                " VALUES (?,?,?)", (new_parent_id, "folder", folder_id))
        return {"folder_id": folder_id, "parent_id": new_parent_id, "name": row["name"]}


def copy_folder(folder_id: str, new_parent_id: str | None = None,
                new_name: str | None = None, db_path: Path | None = None) -> dict:
    """复制目录：**新建一个目录，装着和原来一样的东西**（方案 §三复制语义）。

    成员是**同一份**：新目录的成员行指向**同一个** ``item_id``（下级目录也是同一个
    目录，不各拷一份）。原目录后来加了东西，复制出来的那份**不会跟着变**。
    ``new_name`` 省略时自动取一个不冲突的名字（``原名`` → ``原名 (副本)`` → …）。
    """
    with write_transaction(db_path) as conn:
        src = _folder_row(conn, folder_id)
        name = (_unique_name(conn, new_parent_id, src["name"]) if new_name is None
                else _clean_name(new_name))
        created = _create_folder_in_tx(conn, name, new_parent_id, src["sort"] or 0)
        conn.execute(
            "INSERT INTO folder_member(folder_id, item_kind, item_id, added_at)"
            " SELECT ?, item_kind, item_id, added_at FROM folder_member WHERE folder_id=?",
            (created["folder_id"], folder_id))
        n = conn.execute("SELECT COUNT(*) FROM folder_member WHERE folder_id=?",
                         (created["folder_id"],)).fetchone()[0]
        created["copied_members"] = int(n)
        created["copied_from"] = folder_id
        return created


def delete_folder(folder_id: str, mode: str | None = None,
                  db_path: Path | None = None) -> dict:
    """删目录（方案 §二第 2 条："先问一句"三个情形）。

    * 空目录 ⇒ **直接删**（``mode`` 忽略，返回 ``mode='empty'``）。
    * 非空 + ``mode='reparent'`` ⇒ 只删这个目录，把它的**直接成员**挪到**上一层**：
      子目录改挂到上一层（``parent_id`` 改成被删目录的 ``parent_id``）；文件在这一层的
      归属换成上一层的归属；**本来就已经在上一层里的只去掉这一层的归属，不加重复行**。
    * 非空 + ``mode='purge'`` ⇒ 删这个目录**及它下面所有目录**；文件**只从这些目录里拿掉**
      —— 还挂在别处的保留；**只有"在所有目录里都不再出现"的文件才真的删掉**
      （走既有的 ``doc_delete.delete_documents``，含级联与审计）。
    * 非空 + ``mode=None`` ⇒ 报可读的中文错（**不替调用方选**）。
    * 一级目录（``parent_id IS NULL``）没有上一层 ⇒ ``reparent`` **明确报错**，
      **不**静默降级成 purge。
    """
    if mode is not None and mode not in DELETE_MODES:
        raise _err(f"mode 只能是 {DELETE_MODES} 之一，收到 {mode!r}", "invalid_delete_mode")

    orphan_ids: list[str] = []
    result: dict[str, Any] = {}
    with write_transaction(db_path) as conn:
        row = _folder_row(conn, folder_id)
        parent_id = row["parent_id"]
        direct = conn.execute(
            "SELECT item_kind, item_id FROM folder_member WHERE folder_id=?",
            (folder_id,)).fetchall()
        if not direct:
            conn.execute(
                "DELETE FROM folder_member WHERE item_kind='folder' AND item_id=?",
                (folder_id,))
            conn.execute("DELETE FROM folder WHERE folder_id=?", (folder_id,))
            return {"folder_id": folder_id, "mode": "empty", "removed": True,
                    "reparented_subfolders": 0, "reparented_files": 0,
                    "purged_folders": 0, "unfiled_docs": 0}

        if mode is None:
            raise _err(
                f"目录非空（{len(direct)} 个直接成员）；请二选一："
                "「只删这个目录，里面的东西移到上一层」= mode='reparent'，"
                "或「连里面的文件一起删」= mode='purge'",
                "folder_delete_mode_required")

        if mode == "reparent":
            if parent_id is None:
                raise _err(
                    "一级目录没有上一层，只能选择连里面的文件一起删（mode='purge'），"
                    "或取消", "folder_top_level_no_parent")
            n_sub = n_file = 0
            for m in direct:
                kind, item = m["item_kind"], m["item_id"]
                if kind == "folder":
                    # 上一层可能已有同名目录 ⇒ 给可读报错，别让 DB 抛 IntegrityError
                    _assert_name_free(conn, parent_id, _folder_row(conn, item)["name"],
                                      exclude_id=item)
                conn.execute(
                    "DELETE FROM folder_member WHERE folder_id=? AND item_kind=? AND item_id=?",
                    (folder_id, kind, item))
                already = conn.execute(
                    "SELECT 1 FROM folder_member WHERE folder_id=? AND item_kind=? AND item_id=?",
                    (parent_id, kind, item)).fetchone()
                if already is None:      # 已经在上一层里的 ⇒ 只去掉这一层的归属
                    conn.execute(
                        "INSERT INTO folder_member(folder_id, item_kind, item_id)"
                        " VALUES (?,?,?)", (parent_id, kind, item))
                if kind == "folder":
                    n_sub += 1
                    if _folder_row(conn, item)["parent_id"] == folder_id:
                        conn.execute("UPDATE folder SET parent_id=? WHERE folder_id=?",
                                     (parent_id, item))
                else:
                    n_file += 1
            conn.execute("DELETE FROM folder_member WHERE item_kind='folder' AND item_id=?",
                         (folder_id,))
            conn.execute("DELETE FROM folder WHERE folder_id=?", (folder_id,))
            return {"folder_id": folder_id, "mode": "reparent", "removed": True,
                    "new_parent_id": parent_id,
                    "reparented_subfolders": n_sub, "reparented_files": n_file,
                    "purged_folders": 0, "unfiled_docs": 0}

        # ---- mode == 'purge' ----
        subtree = _subtree_ids(conn, [folder_id])
        placeholders = ",".join("?" * len(subtree))
        args = sorted(subtree)
        docs_in_subtree = {
            r["item_id"] for r in conn.execute(
                f"SELECT item_id FROM folder_member WHERE item_kind='file'"
                f" AND folder_id IN ({placeholders})", args)}
        conn.execute(
            f"DELETE FROM folder_member WHERE folder_id IN ({placeholders})", args)
        conn.execute(f"DELETE FROM folder WHERE folder_id IN ({placeholders})", args)
        # 从**别的**目录指向这棵子树的悬空成员边
        conn.execute(
            f"DELETE FROM folder_member WHERE item_kind='folder' AND item_id IN ({placeholders})",
            args)
        # **只有"在所有目录里都不再出现"的文件才真删**（其余只是丢了这些目录里的归属）。
        # ⚠ 别把方向搞反：下面这条查询返回的是**还活着**的那些（别处仍有成员行），
        #   真删的是它的**补集**。反过来的话就是"把子树里的文件都删了"——那是错的。
        if docs_in_subtree:
            dph = ",".join("?" * len(docs_in_subtree))
            dargs = sorted(docs_in_subtree)
            survivors = {r["item_id"] for r in conn.execute(
                "SELECT DISTINCT m.item_id FROM folder_member m"
                f" WHERE m.item_kind='file' AND m.item_id IN ({dph})", dargs)}
            orphans = sorted(docs_in_subtree - survivors)
            kept = len(docs_in_subtree) - len(orphans)
        else:
            orphans, kept = [], 0
        result = {"folder_id": folder_id, "mode": "purge", "removed": True,
                  "purged_folders": len(subtree),
                  "reparented_subfolders": 0, "reparented_files": 0,
                  "unfiled_docs": kept,                 # 只是丢了归属，文件留着
                  "deleted_docs": 0}
        orphan_ids = orphans                        # 哪都不在了 ⇒ 下面真删

    # 真删必须在上面的事务**提交之后**做：doc_delete 自带 write_transaction（不可嵌套）。
    # ⚠ 必须把 db_path 传下去 —— 否则它会落到**默认库**，而 purge 可能正跑在真库副本上。
    if orphan_ids:
        from src.core.storage.doc_delete import MAX_BATCH, delete_documents
        deleted_docs = 0
        for i in range(0, len(orphan_ids), MAX_BATCH):
            deleted_docs += delete_documents(orphan_ids[i:i + MAX_BATCH],
                                             db_path=db_path)["deleted_docs"]
        with write_transaction(db_path) as conn:
            ph = ",".join("?" * len(orphan_ids))
            conn.execute(f"DELETE FROM doc_filing_state WHERE doc_id IN ({ph})", orphan_ids)
        result["deleted_docs"] = deleted_docs
    return result


def describe_folder_delete(folder_id: str, db_path: Path | None = None) -> dict:
    """删目录**前**"先问一句"要的数字（只读；界面照这些数字问业主）。

    ``reparent_available=False`` ⇔ 一级目录（没有上一层，只给 purge 与取消）。
    ``files_would_be_deleted`` = purge 之后**在任何目录里都不再出现**的文件数
    （才是会真删的那些）；``files_kept_elsewhere`` = 还挂在别处、只是丢归属的。
    """
    conn = get_db_connection(db_path)
    row = _folder_row(conn, folder_id)
    subtree = _subtree_ids(conn, [folder_id])
    ph = ",".join("?" * len(subtree))
    args = sorted(subtree)
    docs = {r["item_id"] for r in conn.execute(
        f"SELECT item_id FROM folder_member WHERE item_kind='file'"
        f" AND folder_id IN ({ph})", args)}
    if docs:
        dph = ",".join("?" * len(docs))
        # 还挂在**这棵子树之外**的目录里的（这些 purge 后只是丢归属，不真删）
        survivors = {r["item_id"] for r in conn.execute(
            f"SELECT DISTINCT item_id FROM folder_member WHERE item_kind='file'"
            f" AND item_id IN ({dph}) AND folder_id NOT IN ({ph})",
            sorted(docs) + args)}
    else:
        survivors = set()
    direct_sub = conn.execute(
        "SELECT COUNT(*) FROM folder_member WHERE folder_id=? AND item_kind='folder'",
        (folder_id,)).fetchone()[0]
    direct_file = conn.execute(
        "SELECT COUNT(*) FROM folder_member WHERE folder_id=? AND item_kind='file'",
        (folder_id,)).fetchone()[0]
    return {
        "folder": dict(row),
        "is_empty": (direct_sub + direct_file) == 0,
        "direct_subfolder_count": int(direct_sub),
        "direct_file_count": int(direct_file),
        "subtree_folder_count": len(subtree),
        "subtree_file_count": len(docs),
        "reparent_available": row["parent_id"] is not None,
        "files_kept_elsewhere": len(survivors),
        "files_would_be_deleted": len(docs) - len(survivors),
    }


# ─────────────────────────── 成员：加 / 移 / 复制 / 挪 ───────────────────────────

def add_member(folder_id: str, item_kind: str, item_id: str,
               db_path: Path | None = None) -> dict:
    """把一个成员（文件或子目录）放进目录。已在那处则不加（``added=False``）。"""
    with write_transaction(db_path) as conn:
        added = _add_member_in_tx(conn, folder_id, item_kind, item_id)
        return {"folder_id": folder_id, "item_kind": item_kind, "item_id": item_id,
                "added": added}


def remove_member(folder_id: str, item_kind: str, item_id: str,
                  db_path: Path | None = None) -> dict:
    """**从这一处拿掉**（删一行成员行 —— 不是删文件；别的目录里那份不动）。"""
    if item_kind not in ITEM_KINDS:
        raise _err(f"item_kind 只能是 {ITEM_KINDS}，收到 {item_kind!r}", "invalid_item_kind")
    with write_transaction(db_path) as conn:
        _folder_row(conn, folder_id)
        cur = conn.execute(
            "DELETE FROM folder_member WHERE folder_id=? AND item_kind=? AND item_id=?",
            (folder_id, item_kind, item_id))
        return {"folder_id": folder_id, "item_kind": item_kind, "item_id": item_id,
                "removed": cur.rowcount > 0}


def copy_member(item_kind: str, item_id: str, to_folder_id: str,
                db_path: Path | None = None) -> dict:
    """把一个成员**再挂到另一处**（同一个 item，多一行成员行）。"""
    with write_transaction(db_path) as conn:
        added = _add_member_in_tx(conn, to_folder_id, item_kind, item_id)
        return {"to_folder_id": to_folder_id, "item_kind": item_kind,
                "item_id": item_id, "added": added}


def move_member(item_kind: str, item_id: str, from_folder_id: str, to_folder_id: str,
                db_path: Path | None = None) -> dict:
    """把成员从一处**挪到**另一处（加新行 + 删原行，同一个事务）。"""
    if item_kind not in ITEM_KINDS:
        raise _err(f"item_kind 只能是 {ITEM_KINDS}，收到 {item_kind!r}", "invalid_item_kind")
    with write_transaction(db_path) as conn:
        _folder_row(conn, from_folder_id)
        _add_member_in_tx(conn, to_folder_id, item_kind, item_id)
        conn.execute(
            "DELETE FROM folder_member WHERE folder_id=? AND item_kind=? AND item_id=?",
            (from_folder_id, item_kind, item_id))
        return {"from_folder_id": from_folder_id, "to_folder_id": to_folder_id,
                "item_kind": item_kind, "item_id": item_id}


# ─────────────────────────── 批量入口（一次性归位用） ───────────────────────────

def build_folder_tree(nodes: list[dict], memberships: list[dict] | None = None,
                      states: list[dict] | None = None,
                      db_path: Path | None = None) -> dict:
    """**一个事务**里把"目录树 + 归属 + 状态"建起来（全成或全败）。

    这是给"现有数据一次性归位"用的批量入口。为什么不能拿 ``create_folder`` /
    ``add_member`` 各调几千次：① 在 2.2 GB 真库上几千次单条事务又慢又占写锁；
    ② 方案 §七要求保留"归属表整表清掉重来"的整体回退 —— 那需要**整批原子**。

    * ``nodes``: ``[{"key","name","parent_key"|None,"sort"?}]``，**父必须排在子之前**。
    * ``memberships``: ``[{"folder_key","item_kind","item_id"}]``（``folder_key`` 指向 nodes 的 key）。
    * ``states``: ``[{"doc_id","stage","placed_folder_key"?,"confidence"?,"placed_by"?}]``。

    校验一条都没省：名字/层数/路径/同名同层/成环/引用存在性全走同一套内部函数。
    返回 ``{"folders_created","members_added","members_skipped","states_set","key_to_id"}``。
    """
    key_to_id: dict[str, str] = {}
    added = skipped = states_set = 0
    with write_transaction(db_path) as conn:
        for node in nodes:
            key = str(node["key"])
            if key in key_to_id:
                raise _err(f"目录 key 重复: {key}", "invalid_folder_key")
            pkey = node.get("parent_key")
            if pkey is None:
                parent_id: str | None = None
            else:
                if pkey not in key_to_id:
                    raise _err(f"上级目录还没建（nodes 必须父先子后）: {pkey}",
                               "invalid_folder_key")
                parent_id = key_to_id[str(pkey)]
            created = _create_folder_in_tx(conn, node["name"], parent_id,
                                           int(node.get("sort") or 0))
            key_to_id[key] = created["folder_id"]
        for m in (memberships or []):
            fkey = str(m["folder_key"])
            if fkey not in key_to_id:
                raise _err(f"成员指向不存在的目录 key: {fkey}", "invalid_folder_key")
            if _add_member_in_tx(conn, key_to_id[fkey], m["item_kind"], str(m["item_id"])):
                added += 1
            else:
                skipped += 1
        for s in (states or []):
            doc_id = str(s["doc_id"])
            stage = s.get("stage")
            if stage is not None and stage not in STAGES:
                raise _err(f"stage 只能是 {STAGES}，收到 {stage!r}", "invalid_stage")
            if conn.execute("SELECT 1 FROM doc_meta WHERE doc_id=?", (doc_id,)).fetchone() is None:
                raise _err(f"文档不存在: {doc_id}", "doc_not_found")
            placed_key = s.get("placed_folder_key")
            placed_id = None
            if placed_key is not None:
                if str(placed_key) not in key_to_id:
                    raise _err(f"归位指向不存在的目录 key: {placed_key}", "invalid_folder_key")
                placed_id = key_to_id[str(placed_key)]
            placed_at = None
            if placed_id is not None:
                placed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO doc_filing_state(doc_id, stage, confidence, placed_folder_id,"
                " placed_by, placed_at) VALUES (?,?,?,?,?,?)"
                " ON CONFLICT(doc_id) DO UPDATE SET"
                "   stage=excluded.stage,"
                "   confidence=COALESCE(excluded.confidence, confidence),"
                "   placed_folder_id=COALESCE(excluded.placed_folder_id, placed_folder_id),"
                "   placed_by=COALESCE(excluded.placed_by, placed_by),"
                "   placed_at=COALESCE(excluded.placed_at, placed_at),"
                "   updated_at=datetime('now')",
                (doc_id, stage or "queued", s.get("confidence"), placed_id,
                 s.get("placed_by"), placed_at))
            states_set += 1
    return {"folders_created": len(key_to_id), "members_added": added,
            "members_skipped": skipped, "states_set": states_set, "key_to_id": key_to_id}


# ─────────────────────────── 列某一级的内容（文件分页） ───────────────────────────

def list_folder(folder_id: str | None = None, file_offset: int = 0, file_limit: int = 50,
                unfiled: bool = True, db_path: Path | None = None) -> dict:
    """列**某一级**的内容：**先下级目录、再这一级直接放的文件**（文件分页）。

    ``folder_id=None`` = 库的顶层；顶层的"文件" = **还没进任何目录**的文件
    （``unfiled=False`` 时顶层只列目录）。方案 §一「待分类」是这批东西的另一个视角
    —— 真正的待分类判定看 ``doc_filing_state``（见 ``list_pending_filing``）。

    每个下级目录带 ``file_count_deep``：**含更深层**的文件数（去重：一个文件挂在
    子树里多处只算一次）；``folder_count_deep`` 同理。
    """
    offset = max(0, int(file_offset))
    limit = int(file_limit)
    if limit <= 0:
        raise _err("file_limit 必须 > 0", "invalid_pagination")
    conn = get_db_connection(db_path)
    cols = _doc_columns(conn)
    if folder_id is None:
        folder = None
        breadcrumb: list[dict] = []
        sub_rows = conn.execute(
            "SELECT folder_id, parent_id, name, sort, created_at FROM folder"
            " WHERE parent_id IS NULL ORDER BY name").fetchall()
    else:
        row = _folder_row(conn, folder_id)
        folder = dict(row)
        breadcrumb = [dict(_folder_row(conn, fid))
                      for fid in _ancestors(conn, folder_id)] + [dict(row)]
        sub_rows = conn.execute(
            "SELECT folder_id, parent_id, name, sort, created_at FROM folder"
            " WHERE folder_id IN ("
            "   SELECT item_id FROM folder_member WHERE folder_id=? AND item_kind='folder'"
            "   UNION SELECT folder_id FROM folder WHERE parent_id=?"
            ") ORDER BY name", (folder_id, folder_id)).fetchall()

    edges = _folder_edges(conn)
    file_edges = _file_edges(conn)
    subfolders = []
    for r in sub_rows:
        subtree = _subtree_ids(conn, [r["folder_id"]], edges)
        deep_files: set[str] = set()
        for fid in subtree:
            deep_files |= file_edges.get(fid, set())
        subfolders.append({
            "folder_id": r["folder_id"], "parent_id": r["parent_id"], "name": r["name"],
            "sort": r["sort"], "created_at": r["created_at"],
            "file_count_deep": len(deep_files),
            "file_count_direct": len(file_edges.get(r["folder_id"], set())),
            "folder_count_deep": len(subtree),
        })

    dcols = ", ".join(f"d.{c}" for c in cols)
    state_cols = ("COALESCE(s.stage,'queued') AS stage, s.confidence AS confidence,"
                  " s.failure_kind AS failure_kind,"
                  " s.suggested_folder_id AS suggested_folder_id")
    join = " LEFT JOIN doc_filing_state s ON s.doc_id = d.doc_id"
    if folder_id is None:
        if not unfiled:
            files: list[dict] = []
            total = 0
        else:
            base = (f"FROM doc_meta d{join}"
                    f" WHERE {_visible_clause(conn)}"
                    "   AND NOT EXISTS (SELECT 1 FROM folder_member m"
                    "                    WHERE m.item_kind='file' AND m.item_id = d.doc_id)")
            total = conn.execute(f"SELECT COUNT(*) {base}").fetchone()[0]
            files = [dict(r) for r in conn.execute(
                f"SELECT {dcols}, {state_cols} {base}"
                " ORDER BY d.standard_no LIMIT ? OFFSET ?", (limit, offset)).fetchall()]
    else:
        base = (f"FROM folder_member m JOIN doc_meta d ON d.doc_id = m.item_id{join}"
                " WHERE m.folder_id=? AND m.item_kind='file'")
        total = conn.execute(f"SELECT COUNT(*) {base}", (folder_id,)).fetchone()[0]
        files = [dict(r) for r in conn.execute(
            f"SELECT {dcols}, {state_cols} {base}"
            " ORDER BY d.standard_no LIMIT ? OFFSET ?",
            (folder_id, limit, offset)).fetchall()]

    return {
        "folder": folder,
        "breadcrumb": breadcrumb,
        "subfolders": subfolders,
        "files": files,
        "files_total": int(total),
        "file_offset": offset,
        "file_limit": limit,
        "has_more": offset + len(files) < int(total),
    }


# ─────────────────────────── 范围集合（范围提问用） ───────────────────────────

def folder_scope(folder_ids: str | Iterable[str], db_path: Path | None = None) -> dict:
    """某一级（或**多选若干目录的并集**）**及其所有下级**的集合。

    返回 ``{"folder_ids": set, "doc_ids": set, "roots": list}``：``doc_ids`` 是子树里
    出现过的全部文件（一个文件挂多处只算一次）。目录不存在 ⇒ 当场报
    ``folder_not_found`` —— **绝不静默返回空范围**（空范围会让"在此范围内提问"悄悄
    变成全库提问，那是最坏的一种静默降级）。
    """
    roots = [folder_ids] if isinstance(folder_ids, str) else list(folder_ids)
    if not roots:
        raise _err("范围不能为空", "invalid_scope")
    if len(roots) > 200:
        raise _err(f"一次最多并集 200 个目录，收到 {len(roots)}", "invalid_scope")
    conn = get_db_connection(db_path)
    for fid in roots:
        _folder_row(conn, fid)
    sub = _subtree_ids(conn, roots)
    file_edges = _file_edges(conn)
    docs: set[str] = set()
    for fid in sub:
        docs |= file_edges.get(fid, set())
    return {"folder_ids": sub, "doc_ids": docs, "roots": list(roots)}


# ─────────────────────────── 文件处理状态 ───────────────────────────

def set_filing_state(doc_id: str, stage: str | None = None, db_path: Path | None = None,
                     **fields: Any) -> dict:
    """写文件处理状态（幂等 upsert）。只改**传进来**的字段，没传的保持原值。

    ``stage`` 必须是五枚举之一；``**fields`` 限 ``_STATE_FIELDS`` 白名单。
    """
    if stage is not None and stage not in STAGES:
        raise _err(f"stage 只能是 {STAGES}，收到 {stage!r}", "invalid_stage")
    bad = set(fields) - set(_STATE_FIELDS)
    if bad:
        raise _err(f"不认识的字段: {sorted(bad)}（可用: {list(_STATE_FIELDS)}）",
                   "invalid_state_field")
    with write_transaction(db_path) as conn:
        if conn.execute("SELECT 1 FROM doc_meta WHERE doc_id=?", (doc_id,)).fetchone() is None:
            raise _err(f"文档不存在: {doc_id}", "doc_not_found")
        conn.execute("INSERT OR IGNORE INTO doc_filing_state(doc_id) VALUES (?)", (doc_id,))
        sets = ["updated_at=datetime('now')"]
        args: list[Any] = []
        if stage is not None:
            sets.append("stage=?")
            args.append(stage)
        for k, v in fields.items():
            sets.append(f"{k}=?")
            args.append(v)
        args.append(doc_id)
        conn.execute(f"UPDATE doc_filing_state SET {', '.join(sets)} WHERE doc_id=?", args)
        row = conn.execute("SELECT * FROM doc_filing_state WHERE doc_id=?",
                           (doc_id,)).fetchone()
        return dict(row)


def get_filing_state(doc_id: str, db_path: Path | None = None) -> dict | None:
    conn = get_db_connection(db_path)
    row = conn.execute("SELECT * FROM doc_filing_state WHERE doc_id=?", (doc_id,)).fetchone()
    return dict(row) if row is not None else None


def mark_filed(doc_id: str, folder_id: str, placed_by: str = "system",
               confidence: float | None = None, db_path: Path | None = None) -> dict:
    """确认归位：把文件**放进**目录 + 状态置 ``filed`` + 记"谁在什么时候放进了哪个目录"。"""
    with write_transaction(db_path) as conn:
        _folder_row(conn, folder_id)
        _add_member_in_tx(conn, folder_id, "file", doc_id)
        conn.execute(
            "INSERT INTO doc_filing_state(doc_id, stage) VALUES (?, 'filed')"
            " ON CONFLICT(doc_id) DO UPDATE SET stage='filed'", (doc_id,))
        sets = ["placed_folder_id=?", "placed_by=?", "placed_at=datetime('now')",
                "updated_at=datetime('now')"]
        args: list[Any] = [folder_id, placed_by]
        if confidence is not None:
            sets.append("confidence=?")
            args.append(confidence)
        args.append(doc_id)
        conn.execute(f"UPDATE doc_filing_state SET {', '.join(sets)} WHERE doc_id=?", args)
        row = conn.execute("SELECT * FROM doc_filing_state WHERE doc_id=?",
                           (doc_id,)).fetchone()
        return dict(row)


def list_pending_filing(offset: int = 0, limit: int = 100,
                        db_path: Path | None = None) -> dict:
    """「待分类」列表：**还没归位**的文件（含从未处理过的：无状态行按 ``queued`` 算）。"""
    offset = max(0, int(offset))
    limit = int(limit)
    if limit <= 0:
        raise _err("limit 必须 > 0", "invalid_pagination")
    conn = get_db_connection(db_path)
    dcols = ", ".join(f"d.{c}" for c in _doc_columns(conn))
    ph = ",".join("?" * len(UNFILED_STAGES))
    base = ("FROM doc_meta d LEFT JOIN doc_filing_state s ON s.doc_id = d.doc_id"
            f" WHERE {_visible_clause(conn)}"
            f"   AND COALESCE(s.stage, 'queued') IN ({ph})")
    args: list[Any] = list(UNFILED_STAGES)
    total = conn.execute(f"SELECT COUNT(*) {base}", args).fetchone()[0]
    rows = conn.execute(
        f"SELECT {dcols}, COALESCE(s.stage,'queued') AS stage, s.confidence AS confidence,"
        " s.failure_kind AS failure_kind, s.suggested_folder_id AS suggested_folder_id,"
        " s.suggest_new_path AS suggest_new_path, s.placed_folder_id AS placed_folder_id"
        f" {base} ORDER BY d.standard_no LIMIT ? OFFSET ?",
        args + [limit, offset]).fetchall()
    return {"items": [dict(r) for r in rows], "total": int(total),
            "offset": offset, "limit": limit}


def list_document_states(offset: int = 0, limit: int = 100,
                         db_path: Path | None = None) -> dict:
    """**所有文件**的处理状态（方案 §一最后几条：不只待分类，全都要能看状态）。"""
    offset = max(0, int(offset))
    limit = int(limit)
    if limit <= 0:
        raise _err("limit 必须 > 0", "invalid_pagination")
    conn = get_db_connection(db_path)
    dcols = ", ".join(f"d.{c}" for c in _doc_columns(conn))
    base = "FROM doc_meta d LEFT JOIN doc_filing_state s ON s.doc_id = d.doc_id"
    total = conn.execute(f"SELECT COUNT(*) {base}").fetchone()[0]
    rows = conn.execute(
        f"SELECT {dcols}, COALESCE(s.stage,'queued') AS stage, s.confidence AS confidence,"
        " s.failure_kind AS failure_kind, s.placed_folder_id AS placed_folder_id,"
        " s.placed_at AS placed_at, s.last_error AS last_error"
        f" {base} ORDER BY d.standard_no LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    return {"items": [dict(r) for r in rows], "total": int(total),
            "offset": offset, "limit": limit}
