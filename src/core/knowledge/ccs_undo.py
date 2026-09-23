"""「补全分类号」的**补前精确回退记录**（2026-09-24，业主点名第①条「补之前自动备份一次，留回退说明」）。

════════ 为什么不是 ``backup.create_snapshot()``（一次全库快照）════════

实测：真库一份 ``create_snapshot()`` = **2.2 GB**（`knowledge.db` 的实际大小）。补分类号
是**可以按很多次**的动作（一次 50 篇、或"全部补完"分页），每按一次做一次全库快照
⇒ 2.2 GB × N，把数据盘撑爆是迟早的事。而这件事真正会改的东西**极小**：
只在 ``doc_meta.domain_tags`` 里加/换一条 ``CCS:…``，再更新 ``doc_ccs_state`` 的那一行。

⇒ 所以这里是**精确回退记录**：只记**这一批会改的那几篇**的改前样子（``domain_tags`` 原文 +
``updated_at`` 原文 + ``doc_ccs_state`` 整行，没有就记 null）。业主的原话是"补之前自动备份一次，
留回退说明" —— 精确记录满足它，且不制造 ×N 的 2.2 GB。

⚠ ``updated_at`` 是**第三处**要退的东西（复核 F2，2026-09-24 补）：写标签那一步的 UPDATE
带 ``datetime('now')``，所以只退 ``domain_tags`` 与台账**不够**"逐字回到改前"。

════════ 三条纪律 ════════

1. **先备份、后写库**：:func:`write_undo_journal` 在**起后台线程之前**调用；写盘失败
   ⇒ 抛错、**这一批一篇都不写**（``ccs_backfill.start_ccs_backfill`` 拿到异常就放锁退出）。
   "补前有备份"是承诺，不是装饰。
2. **一批一份**：一次补全 = 一个 ``ccs-undo-<时间戳>-p<pid>.json``；只写一次。
3. **回退要真能退**：:func:`revert_ccs_backfill_journal` 按记录把 ``domain_tags`` 与
   ``doc_ccs_state`` **逐字恢复**（原文写回、没有的行删掉），并返回**真做出来的数字**
   （恢复了几篇 / 跳过了几篇 / 各是为什么）。**幂等**：再调一次全是"已经是改前的样子"。

════════ 放在哪 ════════

与既有快照**同一个备份目录** —— 唯一所有者是 ``storage/backup.py::_backups_dir()``
（它尊重 ``KS_BACKUP_DIR`` 覆盖）。本模块**绝不**自己拼 ``data_dir/backups``：那样在
"备份重定向到另一块盘" 的部署里，回退记录会落到数据盘上（数据盘坏了就一起没了）。
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.exceptions import KnowledgeStationError
from src.core.storage.sqlite_db import get_db_connection, write_transaction

logger = logging.getLogger("ks.knowledge.ccs_undo")

#: 回退记录的文件名前缀（备份目录里一眼看得出是谁、什么时候）
JOURNAL_PREFIX = "ccs-undo-"
#: 落盘格式的版本（将来形状变了，回退函数要能认出"这不是我认识的格式"而不是瞎恢复）
JOURNAL_VERSION = 1
#: 记录的种类标记（同一目录里可能还有别的东西，认错文件就是灾难）
JOURNAL_KIND = "ccs-backfill-undo"

#: ``doc_ccs_state`` 的列（回退要**整行**写回；与 ``schema.sql`` 一字不差，顺序也照它）
_STATE_COLUMNS: tuple[str, ...] = (
    "doc_id", "outcome", "source", "keyword_form", "matched_no", "ccs_code",
    "ccs_name", "reason", "attempts_json", "checked_at", "applied_at",
)


def _err(msg: str, code: str) -> KnowledgeStationError:
    return KnowledgeStationError(msg, code=code)


#: 哨兵：记录里**没有这一项**（老格式）—— 与"这一项的值是 None"必须区分开。
#: 用途见 ``updated_at``（老记录没有它 ⇒ 回退时**不碰**那一列，而不是写个 NULL 上去）。
_UNSET: Any = object()


def journal_dir() -> Path:
    """回退记录与快照**同一个备份目录**（唯一所有者：``backup._backups_dir()``）。

    调的是那个私有函数是**故意的**：备份目录的规则（含 ``KS_BACKUP_DIR`` 覆盖）只能有
    一个所有者，本模块抄一份规则 = 迟早漂移（`backup.py` 自己的 docstring 就是这么写的）。
    """
    from src.core.storage import backup
    return backup._backups_dir()


def _new_journal_path() -> Path:
    """备份目录下一个新名字：看得出时间 + 进程（同一秒连开两批也不会撞）。"""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"{JOURNAL_PREFIX}{stamp}-p{os.getpid()}"
    d = journal_dir()
    path = d / f"{base}.json"
    n = 2
    while path.exists():                                    # 同秒多批：加序号，不覆盖
        path = d / f"{base}-{n}.json"
        n += 1
    return path


def write_undo_journal(items: list[dict], *, scope: str = "library",
                       force: bool = False, limit: int = 0,
                       db_path: Any = None) -> dict:
    """把这些篇的**改前样子**写进备份目录（一次，补之前）。

    ``items`` = 本批**将要尝试**的每一篇（``{doc_id, standard_no, …}``）——在"全部补完"
    模式下就是分页后**一共**要跑的那么多篇（一份记录覆盖整批，不是一页一份）。

    返回 ``{"path", "doc_count", "created_at"}``；**写不成抛
    ``ccs_undo_failed``**（调用方据此拒绝开始写库）。
    """
    ids = [str(it.get("doc_id") or "") for it in items]
    conn = get_db_connection(db_path)
    records: list[dict] = []
    for it in items:
        doc_id = str(it.get("doc_id") or "")
        row = conn.execute("SELECT domain_tags, updated_at FROM doc_meta WHERE doc_id=?",
                           (doc_id,)).fetchone()
        st = conn.execute("SELECT * FROM doc_ccs_state WHERE doc_id=?",
                          (doc_id,)).fetchone()
        records.append({
            "doc_id": doc_id,
            "standard_no": str(it.get("standard_no") or ""),
            # existed=False：计划之后、备份之前这一篇被删了。**如实记下来**，
            # 回退时跳过它（不重建一篇已经被删的文档 —— 那是另一件事，得有另一条指令）。
            "existed": row is not None,
            "domain_tags": (row["domain_tags"] if row is not None else None),
            # ⚠ ``updated_at`` 也要记（复核 F2，2026-09-24）：写标签那一步会把它刷成
            # "现在"（``ccs_store.apply_ccs_tag`` 的 UPDATE 带 ``datetime('now')``），
            # 不记它就做不到"逐字回到改前"（复核现场：改前 2001-01-01 00:00:00，
            # 补后与回退后都是 2026-09-23 17:45:50）。**别拿"某次探针里它没变"当反证**
            # —— 那只是同秒巧合，不是"这一列不会变"。
            "updated_at": (row["updated_at"] if row is not None else None),
            "ccs_state": (dict(st) if st is not None else None),
        })
    created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "kind": JOURNAL_KIND,
        "journal_version": JOURNAL_VERSION,
        "created_at": created,
        "pid": os.getpid(),
        "batch": {"scope": scope, "force": bool(force), "limit": int(limit or 0),
                  "doc_count": len(records)},
        "records": records,
    }
    path = _new_journal_path()
    tmp = path.with_name(path.name + ".part")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())          # 落盘才算"备份完成"（fsync 前的写入断电就没了）
        os.replace(tmp, path)             # 原子换名：要么整份在，要么没有（不给人半份）
    except OSError as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:                                     # 清理失败不改判结论
            logger.warning("回退记录的半成品文件没删掉: %s", tmp)
        raise _err(f"补前回退记录写不成（{type(exc).__name__}: {exc}）"
                   f"—— 没有备份就不补，一篇都没写", "ccs_undo_failed") from exc
    logger.info("补分类号：回退记录 %s（%d 篇）", path, len(records))
    return {"path": str(path), "doc_count": len(records), "created_at": created}


def latest_journal_path() -> Path | None:
    """备份目录里**最近写的那一份**回退记录（按修改时间；没有就是 None）。"""
    d = journal_dir()
    found = sorted(d.glob(f"{JOURNAL_PREFIX}*.json"),
                   key=lambda p: (p.stat().st_mtime, p.name))
    return found[-1] if found else None


def load_undo_journal(journal_path: str | Path | None = None) -> tuple[Path, dict]:
    """读一份回退记录（``None`` = 取最近那一份）。文件不在/格式不对 ⇒ 明确报错。"""
    if journal_path is None:
        path = latest_journal_path()
        if path is None:
            raise _err(f"备份目录里没有回退记录（{journal_dir()} 下没有 "
                       f"{JOURNAL_PREFIX}*.json）—— 没有可回退的东西",
                       "ccs_undo_journal_missing")
    else:
        path = Path(journal_path)
        if not path.exists():
            raise _err(f"回退记录不存在: {path}", "ccs_undo_journal_missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _err(f"回退记录读不出来（{type(exc).__name__}: {exc}）: {path}",
                   "ccs_undo_journal_broken") from exc
    if not isinstance(payload, dict) or payload.get("kind") != JOURNAL_KIND:
        raise _err(f"这不是「补全分类号」的回退记录: {path}", "ccs_undo_journal_broken")
    if int(payload.get("journal_version") or 0) != JOURNAL_VERSION:
        raise _err(f"回退记录版本不认识（{payload.get('journal_version')!r}）: {path}",
                   "ccs_undo_journal_broken")
    return path, payload


def _state_key(state: dict | None) -> dict:
    """台账行按**本表列**归一（比较/写回都只认这 11 列）。"""
    if state is None:
        return {}
    return {c: state.get(c) for c in _STATE_COLUMNS}


def revert_ccs_backfill_journal(journal_path: str | Path | None = None,
                                db_path: Any = None) -> dict:
    """按回退记录把 ``domain_tags``、``updated_at`` 与 ``doc_ccs_state`` **恢复到改前**（一个事务）。

    ``journal_path`` 省略 = 备份目录里**最近那一份**（:func:`latest_journal_path`）。

    返回**真做出来的数字**：``{journal_path, doc_count, restored, skipped,
    restored_docs:[{doc_id, restored:[…]}], skipped_docs:[{doc_id, reason}],
    skipped_reasons:{原因: 几篇}}``。

    判据是"库里现在的样子 vs 记录里的改前样子"**逐字比**：

    * 已经一样 ⇒ 记为 ``skipped``（理由"已经是改前的样子"）—— 所以**回退两次是安全的**；
    * ``domain_tags`` 不一样 ⇒ 把记录里的**原文**写回；
    * ``updated_at`` 不一样 ⇒ 把记录里的原文写回（复核 F2：写标签那一步会刷这一列，
      不把它退回去就**不是**"逐字回到改前"）。老格式的记录没有这一项 ⇒ **不碰它**
      （``updated_at`` 键缺席时跳过，宁可不退也不写一个猜的值）；
    * ``doc_ccs_state`` 不一样 ⇒ 改前没有这一行就**删掉**，改前有就整行写回；
    * 改前库里已经没有这一篇（``existed=False``）或现在被删了 ⇒ ``skipped`` 并写明理由
      （**不重建**一篇被删掉的文档 —— 那是另一件事）。
    """
    path, payload = load_undo_journal(journal_path)
    records = payload.get("records") or []
    restored: list[dict] = []
    skipped: list[dict] = []
    with write_transaction(db_path) as conn:
        for rec in records:
            doc_id = str(rec.get("doc_id") or "")
            if not doc_id:
                skipped.append({"doc_id": "", "reason": "记录里没有 doc_id（跳过）"})
                continue
            if not rec.get("existed"):
                skipped.append({"doc_id": doc_id,
                                "reason": "改前库里就已经没有这一篇（不重建被删的文档）"})
                continue
            cur = conn.execute("SELECT domain_tags, updated_at FROM doc_meta WHERE doc_id=?",
                               (doc_id,)).fetchone()
            if cur is None:
                skipped.append({"doc_id": doc_id,
                                "reason": "改前有、现在库里没有这一篇了（不重建被删的文档）"})
                continue
            pre_tags = rec.get("domain_tags")
            pre_state = rec.get("ccs_state")
            cur_state_row = conn.execute("SELECT * FROM doc_ccs_state WHERE doc_id=?",
                                         (doc_id,)).fetchone()
            cur_state = dict(cur_state_row) if cur_state_row is not None else None
            tags_same = (cur["domain_tags"] == pre_tags)
            state_same = (_state_key(cur_state) == _state_key(pre_state))
            # 老格式记录没有 updated_at 这一项 ⇒ 不碰那一列（pre_updated 为 _UNSET）
            pre_updated = rec["updated_at"] if "updated_at" in rec else _UNSET
            updated_same = (pre_updated is _UNSET) or (cur["updated_at"] == pre_updated)
            if tags_same and state_same and updated_same:
                skipped.append({"doc_id": doc_id, "reason": "已经是改前的样子（不重复动）"})
                continue
            did: list[str] = []
            if not tags_same:
                conn.execute("UPDATE doc_meta SET domain_tags=? WHERE doc_id=?",
                             (pre_tags, doc_id))
                did.append("domain_tags")
            if not updated_same:
                conn.execute("UPDATE doc_meta SET updated_at=? WHERE doc_id=?",
                             (pre_updated, doc_id))
                did.append("updated_at")
            if not state_same:
                if pre_state is None:
                    conn.execute("DELETE FROM doc_ccs_state WHERE doc_id=?", (doc_id,))
                    did.append("doc_ccs_state（改前没有这一行 ⇒ 删掉）")
                else:
                    cols = ",".join(_STATE_COLUMNS)
                    ph = ",".join("?" * len(_STATE_COLUMNS))
                    sets = ",".join(f"{c}=excluded.{c}" for c in _STATE_COLUMNS
                                    if c != "doc_id")
                    conn.execute(
                        f"INSERT INTO doc_ccs_state({cols}) VALUES ({ph})"
                        f" ON CONFLICT(doc_id) DO UPDATE SET {sets}",
                        tuple(pre_state.get(c) for c in _STATE_COLUMNS))
                    did.append("doc_ccs_state")
            restored.append({"doc_id": doc_id,
                             "standard_no": str(rec.get("standard_no") or ""),
                             "restored": did})
    reasons: dict[str, int] = {}
    for s in skipped:
        reasons[s["reason"]] = reasons.get(s["reason"], 0) + 1
    return {"journal_path": str(path), "doc_count": len(records),
            "restored": len(restored), "skipped": len(skipped),
            "restored_docs": restored, "skipped_docs": skipped,
            "skipped_reasons": reasons}
