"""全量数据包导出/导入（阶段六·批次4）：F-26 数据打包/还原 + 成功简报。

职责（pipeline/02 §1 data_package.py；§3 ``POST /api/v1/data/package/export·import``；
FRB F-26「全量数据+设置打包/还原；成功各出简报（法规数/批注数/收藏数…）」）：
- ``export_package(dest_dir) -> (path, manifest)``：``VACUUM INTO`` 打包 DB 快照
  （与 backup.create_snapshot 同一快照 SQL 语义）＋ 拷贝关键目录清单——
  公告存档 PDF（update_change_event.archived_pdf_path ∪ doc_type='announcement'
  的 file_path，缺失件记 warning 不阻塞）＋ quarantine 隔离区清单（只列清单，
  不拷损坏件本体）；app_config 存于库内随快照自带。manifest JSON 含七项简报
  计数 ``{docs, clauses, annotations, bookmarks, obligations, changes,
  announcements}``（逐表 COUNT，取自快照本身）与 SHA-256 ``db_checksum``
  （沿用 backup 校验和红线口径）。
- ``import_package(src_path, mode='strict', conn=None) -> manifest``：校验顺序
  （前 7 步零副作用，任何拒绝都发生在第一个写动作之前）：
  manifest 存在且格式合法 → db 文件存在 → db_checksum 匹配（不匹配拒绝且
  不落任何数据）→ 同 checksum 幂等闸（重复导入第二次拒绝并明示）→
  目标库非空拒绝（UPD-3003）→ 通过后先自动做当前库快照备份
  （backup.create_snapshot('manual')），再从包内快照统计导入简报并登记台账。
- **整体替换语义**：本模块只负责校验+准备+简报；替换执行由
  scripts/restore_package.py（离线 CLI，引擎停止时）完成：停写→替换 db→完整性验证→台账。

错误码：UPD-3003 目标库非空（批次4指令指定）；其余用描述性码（package_*），
不占用 pipeline/05 §2 的 UPD 数字段位。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from src.core.config import get_settings
from src.core.storage import backup
from src.core.storage.sqlite_db import get_db_connection
from src.core.update.channels.base import UpdateError, upd_log
from src.core.update.inspector import get_config, set_config

# ---------------------------------------------------------------- 常量
#: 导入台账 app_config 键（同 checksum 包幂等闸的数据源）
REGISTRY_KEY = "data_package.imported"
#: 目标库非空拒绝（批次4指令指定码位）
UPD_TARGET_NOT_EMPTY = "UPD-3003"
E_MANIFEST_MISSING = "package_manifest_missing"
E_DB_MISSING = "package_db_missing"
E_CHECKSUM_MISMATCH = "package_checksum_mismatch"
E_ALREADY_IMPORTED = "package_already_imported"
E_BAD_MODE = "package_bad_mode"
PACKAGE_FORMAT = "ks-data-package"
DB_NAME = "knowledge.db"
#: 简报计数七项（F-26 简报结构冻结）
BRIEF_KEYS = ("docs", "clauses", "annotations", "bookmarks",
              "obligations", "changes", "announcements")

_BRIEF_SQL: dict[str, str] = {
    "docs": "SELECT COUNT(*) FROM doc_meta",
    "clauses": "SELECT COUNT(*) FROM clause_revision",
    "annotations": "SELECT COUNT(*) FROM user_annotation",
    "bookmarks": "SELECT COUNT(*) FROM user_bookmark",
    "obligations": "SELECT COUNT(*) FROM legal_obligation",
    "changes": "SELECT COUNT(*) FROM update_change_event",
    "announcements": "SELECT COUNT(*) FROM doc_meta WHERE doc_type='announcement'",
}
#: strict 模式「目标库非空」判定：任一业务表有行即视为非空
_EMPTY_TARGET_SQL = """
SELECT (SELECT COUNT(*) FROM doc_meta)
     + (SELECT COUNT(*) FROM clause_revision)
     + (SELECT COUNT(*) FROM user_annotation)
     + (SELECT COUNT(*) FROM user_bookmark)
     + (SELECT COUNT(*) FROM legal_obligation)
     + (SELECT COUNT(*) FROM update_change_event)
     + (SELECT COUNT(*) FROM watch_list)
     + (SELECT COUNT(*) FROM project_list)
     + (SELECT COUNT(*) FROM review_task)
"""

_ANNOUNCEMENT_PATHS_SQL = """
SELECT DISTINCT p AS path FROM (
    SELECT archived_pdf_path AS p FROM update_change_event
     WHERE archived_pdf_path IS NOT NULL AND TRIM(archived_pdf_path) <> ''
    UNION
    SELECT file_path AS p FROM doc_meta
     WHERE doc_type = 'announcement'
       AND file_path IS NOT NULL AND TRIM(file_path) <> ''
) ORDER BY path
"""


# ================================================================ 公共小工具
def brief_counts(conn: sqlite3.Connection) -> dict:
    """七项简报计数（逐表 COUNT；conn 可为活动库连接或只读快照连接）。"""
    return {k: int(conn.execute(sql).fetchone()[0]) for k, sql in _BRIEF_SQL.items()}


def _file_sha256(path: Path) -> str:
    """SHA-256 文件指纹（与 backup._checksum 同一口径：64KB 分块）。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _connect_ro(path: Path) -> sqlite3.Connection:
    """以只读 URI 打开 sqlite 文件（绝不产生 -wal/-shm 副文件写入）。"""
    uri = f"file:{quote(path.resolve().as_posix())}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ================================================================ 导出
def export_package(dest_dir: str | Path) -> tuple[Path, dict]:
    """全量打包到 dest_dir 下的 ``ks_data_package_<时间戳>/``，返回 (目录, manifest)。

    包内容：knowledge.db（VACUUM INTO 快照）＋ manifest.json ＋
    files/announcements/*（公告 PDF）＋ files/quarantine_manifest.json（隔离清单）。
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pkg = dest / f"ks_data_package_{stamp}"
    n = 1
    while pkg.exists():  # 同秒重名避让
        pkg = dest / f"ks_data_package_{stamp}_{n}"
        n += 1
    pkg.mkdir()
    files_dir = pkg / "files"
    files_dir.mkdir()

    conn = get_db_connection()
    snap_path = pkg / DB_NAME
    conn.execute("VACUUM INTO ?", (str(snap_path),))  # 与 backup 同一在线备份语义
    checksum = _file_sha256(snap_path)

    snap = _connect_ro(snap_path)
    try:
        counts = brief_counts(snap)
        files: list[str] = [DB_NAME]
        copied, warnings = _copy_announcement_pdfs(snap, files_dir)
        files.extend(copied)
    finally:
        snap.close()

    quarantine = _quarantine_listing()
    qfile = files_dir / "quarantine_manifest.json"
    qfile.write_text(json.dumps(quarantine, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    files.append("files/quarantine_manifest.json")

    manifest = {
        "format": PACKAGE_FORMAT,
        "version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "db_file": DB_NAME,
        "db_checksum": checksum,
        "counts": counts,
        "brief_keys": list(BRIEF_KEYS),
        "files": files,
        "quarantine": quarantine,
        "warnings": warnings,
        "notes": {
            "app_config": "系统设置存于库内 app_config 表，随 DB 快照自带，无需单独打包",
            "standards_pdf": "标准正文 PDF 不入包（体积考量），仅公告存档 PDF 随包",
        },
    }
    (pkg / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    upd_log("-", "data_package", "INFO", "package_exported",
            path=str(pkg), docs=counts["docs"], checksum=checksum[:16])
    return pkg, manifest


def _copy_announcement_pdfs(snap: sqlite3.Connection,
                            files_dir: Path) -> tuple[list[str], list[str]]:
    """拷贝公告存档 PDF 到 files/announcements/；缺失件记 warning 不阻塞。"""
    rows = snap.execute(_ANNOUNCEMENT_PATHS_SQL).fetchall()
    ann_dir = files_dir / "announcements"
    rels: list[str] = []
    warns: list[str] = []
    used: set[str] = set()
    for r in rows:
        src = Path(r["path"])
        if not src.exists():
            warns.append(f"公告 PDF 缺失，跳过: {src}")
            continue
        ann_dir.mkdir(parents=True, exist_ok=True)
        name = src.name
        if name.lower() in used:  # 跨目录同名避让
            name = f"{src.stem}_{len(used)}{src.suffix}"
        used.add(name.lower())
        shutil.copy2(src, ann_dir / name)
        rels.append(f"files/announcements/{name}")
    return rels, warns


def _quarantine_listing() -> list[dict]:
    """quarantine 隔离区清单（只列条目，不拷损坏件本体）。"""
    qdir = get_settings().data_dir / "quarantine"
    if not qdir.exists():
        return []
    out: list[dict] = []
    for f in sorted(qdir.rglob("*")):
        if f.is_file():
            st = f.stat()
            out.append({
                "name": f.relative_to(qdir).as_posix(),
                "size_bytes": st.st_size,
                "modified_at": datetime.fromtimestamp(st.st_mtime).isoformat(
                    timespec="seconds"),
            })
    return out


# ================================================================ 导入
def import_package(src_path: str | Path, mode: str = "strict",
                   conn: sqlite3.Connection | None = None) -> dict:
    """校验数据包并准备导入（整体替换语义），成功返回含导入简报的 manifest。

    - ``src_path``：包目录或其中 manifest.json 路径；
    - ``mode``：当前仅 'strict'（目标库必须为空库）；
    - ``conn``：目标库连接覆盖（默认取活动库连接；测试注入空库演练用）。

    全部校验通过后：自动做当前库快照备份 → 从包内快照统计导入简报 →
    登记台账；替换执行见 scripts/restore_package.py（离线 CLI，引擎停止时）。
    """
    if mode != "strict":
        raise UpdateError(f"暂不支持的导入模式: {mode}（当前仅 strict）",
                          code=E_BAD_MODE)

    # ---- 第 1~3 步：manifest / 格式 / db 文件（零副作用） ----
    p = Path(src_path)
    pkg = p if p.is_dir() else p.parent
    mpath = pkg / "manifest.json"
    if not mpath.exists():
        raise UpdateError(f"数据包缺少 manifest.json: {pkg}",
                          code=E_MANIFEST_MISSING)
    try:
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        raise UpdateError(f"manifest.json 无法解析: {e}",
                          code=E_MANIFEST_MISSING) from e
    if not isinstance(manifest, dict) or manifest.get("format") != PACKAGE_FORMAT:
        raise UpdateError(f"非本系统数据包格式: {manifest.get('format')!r}",
                          code=E_MANIFEST_MISSING)
    db_path = pkg / str(manifest.get("db_file") or DB_NAME)
    if not db_path.exists():
        raise UpdateError(f"数据包缺少库快照文件: {db_path}", code=E_DB_MISSING)

    # ---- 第 4 步：校验和红线（沿 backup.restore：不匹配拒绝且不落任何数据） ----
    actual = _file_sha256(db_path)
    if actual != manifest.get("db_checksum"):
        raise UpdateError("数据包校验和不匹配（文件损坏或被篡改），拒绝导入",
                          code=E_CHECKSUM_MISMATCH)

    # ---- 第 5 步：幂等闸——同 checksum 包重复导入第二次拒绝并明示 ----
    for item in _load_registry():
        if item.get("checksum") == actual:
            raise UpdateError(
                f"该数据包已导入过（checksum={actual[:16]}…，"
                f"导入于 {item.get('imported_at')}），重复导入已拒绝",
                code=E_ALREADY_IMPORTED)

    # ---- 第 6 步：strict 目标库非空 → UPD-3003 拒绝（零副作用） ----
    target = conn if conn is not None else get_db_connection()
    if _target_nonempty(target):
        raise UpdateError("目标数据库非空，strict 导入已拒绝（UPD-3003）："
                          "请先清空/重置知识库后再导入", code=UPD_TARGET_NOT_EMPTY)

    # ---- 第 7 步起：全部闸门已过 → 先自动做当前库快照备份 ----
    snap = backup.create_snapshot("manual")

    ro = _connect_ro(db_path)
    try:
        counts = brief_counts(ro)
    finally:
        ro.close()
    imported_at = datetime.now().astimezone().isoformat(timespec="seconds")
    _append_registry({"checksum": actual, "imported_at": imported_at,
                      "package": str(pkg), "counts": counts})
    upd_log("-", "data_package", "INFO", "package_import_prepared",
            checksum=actual[:16], docs=counts["docs"])

    # 替换执行（2026-08-26，P2-② 接线）：引擎停止时用 scripts/restore_package.py
    # 离线执行（校验→备份→覆盖→完整性验证→幂等台账）；不在引擎进程内做
    # "停写→换库→重连"（连接/线程风险高，见 restore_package.py 头注）。
    return {**manifest, "counts": counts, "status": "prepared", "mode": mode,
            "snapshot_id": snap["snapshot_id"],
            "restore_note": ("替换由 scripts/restore_package.py 离线执行（引擎停止时）："
                             "校验→备份→覆盖 knowledge.db→完整性验证→幂等台账")}


def _target_nonempty(conn: sqlite3.Connection) -> bool:
    return int(conn.execute(_EMPTY_TARGET_SQL).fetchone()[0]) > 0


def _load_registry() -> list[dict]:
    raw = get_config(REGISTRY_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def _append_registry(item: dict) -> None:
    reg = _load_registry()
    reg.append(item)
    set_config(REGISTRY_KEY, json.dumps(reg, ensure_ascii=False))
