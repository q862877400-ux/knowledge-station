"""万级批量导入编排器（pipeline/06 + 11 契约落地）。

三阶段：
  1) fast_scan：os.walk 收 *.pdf → PyMuPDF 首页抽 标准号/名称/年代 → file_hash 防重
     → 骨架行入库（quality_grade='C' + normative_refs 标记 pending_parse）→ 失败件进隔离区
  2) parse_loop：按 checkpoint 队列逐件调 run_full_ingest，日预算 bulk.parse_daily_budget=2000，
     每 5 批自动 VACUUM INTO 快照（backup.py）
  3) 首检入列：解析成功的 standard_no 天然落入巡检 tier0（未首检口径）

状态机复用 bulk_import_batch（batch_kind='bulk_ingest'）：pending→running→paused/done/failed；
checkpoint_json = {queue:[{path,standard_no?,name?,hash?,status}], errors:[], pause_reason, parsed, scanned}。
写路径一律 write_transaction；审计 event_log event_type='bulk/batch_*'（pipeline/05 §1）。
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
from typing import Any
from ulid import ULID

import fitz  # PyMuPDF

from src.core.storage.sqlite_db import get_db_connection, write_transaction
from src.core.text_utils import store_standard_name, store_standard_no

# ---------------------------------------------------------------- 常量（pipeline/06 §2）
DEFAULT_BATCH_SIZE = 200          # bulk.batch_size
DEFAULT_SCAN_CONCURRENCY = 2      # bulk.scan_concurrency（快扫线程数）
DEFAULT_PARSE_DAILY_BUDGET = 2000  # bulk.parse_daily_budget
SNAPSHOT_EVERY_BATCHES = 5        # bulk.snapshot_every_batches
DEFAULT_QUARANTINE_DIR = "quarantine"

#: 骨架行 pending 标记（存 doc_meta.normative_refs，不新增列——契约零变更）
PENDING_MARKER = {"bulk_import": "pending_parse"}

#: 标准号/名称/年代 首页提取正则（快扫级，容忍 OCR 残字）
_NO_RE = re.compile(r"(GB/T|GB|DB\d{2}|JGJ|CJ|AQ|HJ|WS|YY|JB|HG|DL|SY|GA|QB|FZ|TSG|JT/T|TB|MT|NB)[\s/]?T?[\s-]?\d{3,5}(?:\.\d+)?[\s-]?\d{4}")
_YEAR_RE = re.compile(r"(19|20)\d{2}")
_NAME_RE = re.compile(r"^[\u4e00-\u9fa5A-Za-z0-9（）()·、—\- ]{2,60}$")

_lock = threading.Lock()


# ---------------------------------------------------------------- 批次控制面
def create_bulk_batch(src_dir: str, batch_size: int = DEFAULT_BATCH_SIZE,
                      reingest: bool = False) -> dict:
    """新建 bulk_ingest 批次（running 中批次存在则 409/UPD-2001）。

    ``reingest``（2026-09-21，KB-FOLDER-PLAN 第 4 步的「重来一次」开关）落在 checkpoint 里，
    由 ``parse_loop`` 逐件透传给 **既有** 的 ``run_full_ingest(..., reingest=True)`` 路径
    （不另写一套解析）。语义 = "明知库里已有同号/同文件的登记，也**覆盖重导**"
    —— 那正是那两篇被隐藏文档（正文条款为零 ⇒ ``catalog_hidden=1``）唯一走得通的回头路。
    默认 ``False``（**不覆盖**），保持原行为。
    """
    from src.core.update.channels.base import (
        UpdateError, UPD_BATCH_ALREADY_RUNNING, UPD_BAD_PAYLOAD)

    src = Path(src_dir)
    if not src.is_dir():
        raise UpdateError(f"目录不存在: {src}", code=UPD_BAD_PAYLOAD)
    conn = get_db_connection()
    running = conn.execute(
        "SELECT batch_id FROM bulk_import_batch WHERE batch_kind='bulk_ingest'"
        " AND status IN ('pending','running','paused')").fetchone()
    if running:
        raise UpdateError(f"已有运行中的导入批次: {running['batch_id']}",
                          code=UPD_BATCH_ALREADY_RUNNING)
    batch_id = f"bul_{ULID()}"
    ckpt: dict[str, Any] = {"queue": [], "errors": [], "pause_reason": None,
                            "parsed": 0, "scanned": 0, "src_dir": str(src),
                            "reingest": bool(reingest),
                            #: 状态行没写进去的文件（随终态持久化；见 parse_loop 里的说明）
                            "filing_state_missing": []}
    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO bulk_import_batch (batch_id, batch_kind, trigger_type,"
            " status, total, tier, checkpoint_json) VALUES (?,?,?,?,?,?,?)",
            (batch_id, "bulk_ingest", "manual", "pending", 0, "tier1",
             json.dumps(ckpt, ensure_ascii=False)))
        txn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type,"
            " target_id, after_state) VALUES (?,?,?,?,?,?)",
            (str(ULID()), "bulk/batch_created", "user", "bulk_import_batch", batch_id,
             json.dumps({"src_dir": str(src), "batch_size": batch_size,
                         "reingest": bool(reingest)}, ensure_ascii=False)))
    return _reload(batch_id)


def load_batch(batch_id: str) -> dict | None:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM bulk_import_batch WHERE batch_id=?", (batch_id,)).fetchone()
    if row is None:
        return None
    out = dict(row)
    try:
        out["checkpoint"] = json.loads(out.pop("checkpoint_json") or "{}")
    except (TypeError, ValueError):
        out["checkpoint"] = {}
    return out


def _reload(batch_id: str) -> dict:
    """_save_ckpt 刚写完行后的重载——行必存在；None 即状态库损坏，宁可炸也不撒谎。"""
    b = load_batch(batch_id)
    assert b is not None, f"bulk batch vanished after write: {batch_id}"
    return b

def _batch_status(batch_id: str) -> str | None:
    """轻量状态读（不做 checkpoint JSON 解析）：供扫描循环高频轮询外部暂停标志。

    R-A（pipeline/13）：快扫取消数量上限后，批间暂停检测必须廉价——只查 status 列；
    批次不存在返回 None（视同已停止）。
    """
    conn = get_db_connection()
    row = conn.execute(
        "SELECT status FROM bulk_import_batch WHERE batch_id=?", (batch_id,)).fetchone()
    return row["status"] if row else None


def _save_ckpt(batch_id: str, ckpt: dict, status: str | None = None,
               total: int | None = None,
               only_if_status_in: tuple[str, ...] | None = None) -> None:
    """落 checkpoint（可选改状态）。

    ``only_if_status_in``：**条件状态写**（乙1 竞态修复，2026-09-22）——只许从列出的
    现状态迁入，SQL 侧原子判。根治两类复活：① ``fast_scan`` 起手写 ``'running'`` 与
    ``abort_batch`` 的终态写对撞（检查通过后、写出前被中止 ⇒ 中止被顶回 ``running``）；
    ② 工作线程的收尾写把用户中止的 ``failed(aborted_by_user)`` 顶成 ``done``。
    状态未迁成时 checkpoint 照落（进度不丢、状态不许复活）。"""
    with write_transaction() as txn:
        cond = ""
        args: tuple = ()
        if only_if_status_in is not None:
            marks = ",".join("?" for _ in only_if_status_in)
            cond = f" AND status IN ({marks})"
            args = tuple(only_if_status_in)
        if status and total is not None:
            txn.execute("UPDATE bulk_import_batch SET status=?, total=?,"
                        f" checkpoint_json=? WHERE batch_id=?{cond}",
                        (status, total, json.dumps(ckpt, ensure_ascii=False), batch_id) + args)
        elif status:
            txn.execute(f"UPDATE bulk_import_batch SET status=?, checkpoint_json=? WHERE batch_id=?{cond}",
                        (status, json.dumps(ckpt, ensure_ascii=False), batch_id) + args)
        else:
            txn.execute("UPDATE bulk_import_batch SET checkpoint_json=? WHERE batch_id=?",
                        (json.dumps(ckpt, ensure_ascii=False), batch_id))


# ---------------------------------------------------------------- 快扫（阶段一）
def _extract_first_page(pdf_path: Path) -> tuple[str | None, str | None]:
    """PyMuPDF 提取 → (标准号, 名称)。首页无名称时从全文回退（增强2）；失败返回 (None, None)。"""
    try:
        doc = fitz.open(str(pdf_path))
        try:
            if doc.page_count < 1:
                return None, None
            text = doc[0].get_text("text")[:4000]
            full = "".join(doc[i].get_text("text")
                           for i in range(doc.page_count))[:20000]
        finally:
            doc.close()
    except Exception:
        return None, None
    no = _NO_RE.search(text)
    name: str | None = None
    for line in text.splitlines():
        line = line.strip()
        if line and _NAME_RE.match(line) and len(line) >= 4:
            name = line
            break
    if name is None and no is not None:
        # 首页无名称 → 全文回退（排除标准号行本身）
        no_line = no.group(0).replace(" ", "")
        for line in full.splitlines():
            line = line.strip()
            if not line or len(line) < 4 or not _NAME_RE.match(line):
                continue
            if no_line and no_line in line.replace(" ", ""):
                continue
            name = line
            break
    return (no.group(0).replace(" ", "") if no else None), name


#: 公开别名（2026-09-11）：R27 入库预览复用同一「首页身份提取」实现（反熵，不另造正则）。
extract_first_page_identity = _extract_first_page


def _process_pdf(pdf: Path, known: set[tuple[int, str]],
                 seen: set[tuple[int, str]], lock: threading.Lock,
                 quar_dir: Path) -> dict:
    """单个文件的快扫处理（供线程池并发调用）。

    防重判定（业主口径 2026-08-24）：**文件大小 + 内容哈希 二元组完全一致**才跳过；
    文件名不参与（换名不改内容的副本视为重复）；任一不同（换源/换文件）都不跳过。
    """
    fname = pdf.name  # 仅用于隔离区/路径记录，不参与防重键
    fsize = pdf.stat().st_size
    fhash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    fkey = (fsize, fhash)
    with lock:
        if fkey in known or fkey in seen:
            return {"error": {"path": str(pdf), "reason": "duplicate_file"}}
    no, name = _extract_first_page(pdf)
    if no is None:
        try:
            quar_dir.mkdir(parents=True, exist_ok=True)
            pdf.rename(quar_dir / pdf.name)
        except OSError:
            pass
        return {"error": {"path": str(pdf), "reason": "unparseable_first_page"}}
    doc_id = f"doc_{ULID()}"
    # 存储形收口（§11.0 R6c-2d）：`no` 今天是 `_NO_RE`（字符类 `[/\s]`）抽出来的、**产不出全角**，
    # 但"今天产不出"不等于"以后产不出"——凡是写 doc_meta 的 standard_no/short_code/standard_name
    # 的入口都过同一个 `store_standard_no`（规则一个所有者，入口逐个点名）。`short_code` 由**折过的** no 派生。
    no = store_standard_no(no)
    # ⚠ 名称列**只折斜杠**（`store_standard_name`）：名称里的全角 `－` 是中文连接号，折它是改内容
    #   （§11.0 R6c-3d，复核 b33 用真库 5 行反例证伪了我原来对名称也用 store_standard_no）
    name = store_standard_name(name or no)
    try:
        with write_transaction() as txn:
            txn.execute(
                "INSERT INTO doc_meta(doc_id, standard_no, standard_name,"
                " short_code, current_revision_id, legal_hierarchy, legal_status,"
                " quality_grade, domain_tags, normative_refs, file_path, file_hash)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (doc_id, no, name or no, re.sub(r"\s", "", no),
                 f"rev_{ULID()}", "GB", "effective", "C", "[]",
                 json.dumps(PENDING_MARKER, ensure_ascii=False),
                 str(pdf), fhash))
    except sqlite3.IntegrityError:
        # 同标准号已存在：区分"真重复文件"与"换源新文件"（不静默跳过）
        conn = get_db_connection()
        exist = conn.execute(
            # 查重也用存储形（§11.0 R6c-3d）：两边一起折，`／` 与 `/` 才能真正算同一个号
            "SELECT file_hash FROM doc_meta WHERE standard_no=?",
            (store_standard_no(no),)).fetchone()
        reason = "duplicate_file" if (exist and exist["file_hash"] == fhash) \
            else "standard_no_exists"
        return {"error": {"path": str(pdf), "reason": reason}}
    with lock:
        seen.add(fkey)
    return {"entry": {"path": str(pdf), "doc_id": doc_id, "standard_no": no,
                      "name": name or no, "hash": fhash, "status": "pending"}}


def _known_files() -> set[tuple[int, str]]:
    """既有文档的 (文件大小, 内容哈希) 二元组指纹集（严格防重口径，文件名不参与）。"""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT file_path, file_hash FROM doc_meta").fetchall()
    out: set[tuple[int, str]] = set()
    for r in rows:
        p = Path(r["file_path"])
        try:
            size = p.stat().st_size
        except OSError:
            continue  # 文件已不在磁盘：指纹不可判定，不参与防重
        out.add((size, r["file_hash"]))
    return out


def fast_scan(batch_id: str, batch_size: int = DEFAULT_BATCH_SIZE,
              scan_concurrency: int = DEFAULT_SCAN_CONCURRENCY) -> dict:
    """阶段一：快扫目录建清单（线程池并发，默认 scan_concurrency=2）。

    R-A（pipeline/13）：循环扫描直到文件穷尽，**取消 200 上限**；batch_size 语义 =
    checkpoint 粒度——每处理 batch_size 个文件落一次 _save_ckpt（断点续扫）；
    每个微批（=scan_concurrency 个文件）边界轮询批次状态：已被外部置 paused
    （用户终止/暂停）→ 立即停止扫描并返回，保持 paused 与外部 pause_reason。
    """
    batch = load_batch(batch_id)
    if batch is None:
        raise ValueError(f"批次不存在: {batch_id}")
    if batch["status"] in ("done", "failed", "running"):
        return batch
    ckpt = batch["checkpoint"]
    src = Path(ckpt.get("src_dir", ""))
    # 乙1：'running' 只许从 pending/paused 迁入（原子条件写）——写出后复读一次状态，
    # 被 abort 抢先 ⇒ 不是 running ⇒ 原样返回，不开工（复活窗口就此关闭）。
    _save_ckpt(batch_id, ckpt, "running", only_if_status_in=("pending", "paused"))
    if _batch_status(batch_id) != "running":
        return _reload(batch_id)
    try:
        known = _known_files()
        quar_dir = src / DEFAULT_QUARANTINE_DIR
        files = [p for p in src.rglob("*.pdf") if p.is_file()]
        scanned = ckpt.get("scanned", 0)
        step = max(1, int(batch_size))      # checkpoint 粒度（非扫描上限）
        mw = max(1, int(scan_concurrency))  # 有界并发，与文件总量无关
        lock = threading.Lock()
        seen: set[tuple[int, str]] = set()

        def _drain(results: list[dict]) -> None:
            nonlocal scanned
            for r in results:
                scanned += 1
                if "error" in r:
                    ckpt.setdefault("errors", []).append(r["error"])
                else:
                    ckpt.setdefault("queue", []).append(r["entry"])
            ckpt["scanned"] = scanned

        stopped = False
        with ThreadPoolExecutor(max_workers=mw) as pool:
            while scanned < len(files):
                if _batch_status(batch_id) != "running":  # 批边界：外部已暂停/终止
                    stopped = True
                    break
                chunk = files[scanned:scanned + step]
                aborted = False
                for i in range(0, len(chunk), mw):
                    sub = chunk[i:i + mw]
                    _drain(list(pool.map(
                        lambda p: _process_pdf(p, known, seen, lock, quar_dir), sub)))
                    if _batch_status(batch_id) != "running":  # 微批边界暂停检测
                        aborted = True
                        break
                if aborted:
                    stopped = True
                    break
                _save_ckpt(batch_id, ckpt)  # R-A：每处理一批（batch_size 个）落一次 checkpoint
        if stopped:
            # 扫描中途被外部暂停：保持 paused 与外部 pause_reason，只持久化本扫进度增量
            cur = load_batch(batch_id)
            if cur is not None:
                ckpt["pause_reason"] = (cur.get("checkpoint") or {}).get("pause_reason")
            _save_ckpt(batch_id, ckpt)
            return _reload(batch_id)
        # 快扫完成 → paused(scan_complete)：等 resume 进入解析（running 态留给解析期）
        ckpt["pause_reason"] = "scan_complete"
        _save_ckpt(batch_id, ckpt, "paused", total=len(ckpt.get("queue", [])))
        return _reload(batch_id)
    except Exception:
        _save_ckpt(batch_id, ckpt, "failed")
        raise


# ---------------------------------------------------------------- 解析循环（阶段二）
def _write_item_state(doc_id: Any, stage: str | None = None, **fields: Any) -> bool:
    """写队列项的处理状态（走入库侧那一个出口，见 ``pipeline._write_filing_state``）。

    返回 ``False`` = 没写成（那行已经不存在 —— 例如 ``reingest`` 把占位行替换掉了，
    或者状态表写不进去）。**不许**因为写状态失败就让整批解析失败。
    """
    if not doc_id:
        return False
    from src.core.ingestion.pipeline import _write_filing_state
    return _write_filing_state(str(doc_id), stage, **fields)


def _placeholder_still_there(item: dict[str, Any]) -> bool:
    """这一项对应的**快扫占位行**还在吗（= 这一项是本次导入自己的占位）？

    判据与 ``_process_pdf`` 写进去的形状一致：doc_id 命中 **且** ``file_hash`` 等于
    这一次要解析的那个文件的哈希。

    ⚠ 为什么需要它（2026-09-21 实测的真缺陷，第 4 步顺路修）：快扫会**先建一行占位**
    ``doc_meta``（``quality_grade='C'`` + ``normative_refs=pending_parse``）并把它的
    ``file_hash`` 写成这个文件的哈希；而 ``run_full_ingest`` 第一步就按 ``file_hash``
    查重 ⇒ 它撞上**自己这行占位**、返回 ``duplicate``、**一条条款都不解析**，进度却报
    ``parsed``。实测（副本库）：``resume`` 跑完 ``status=done / parsed=1 / clause_revision=0``、
    库里只剩那行占位。占位行是**本次导入自己**的东西（不是用户资产）⇒ 真解析必须带
    ``reingest=True`` 把它替换掉（那条路径本来就在 ``run_full_ingest`` 里，没有另写一套）。
    """
    doc_id = str(item.get("doc_id") or "")
    if not doc_id:
        return False
    conn = get_db_connection()
    row = conn.execute("SELECT file_hash FROM doc_meta WHERE doc_id=?", (doc_id,)).fetchone()
    if row is None:
        return False
    return bool(item.get("hash")) and row["file_hash"] == item.get("hash")


def parse_loop(batch_id: str, daily_budget: int = DEFAULT_PARSE_DAILY_BUDGET) -> dict:
    """逐件调 run_full_ingest；日预算截断；每 5 件快照；终态 done/failed 诚实裁决。

    ⚠ **处理状态在这里写"开始识别"与"失败"**（KB-FOLDER-PLAN §16.补2.1 的硬前置）：
    队列项的 doc_meta 行是快扫时先建好的 ⇒ 这里是**唯一**能在"解析开始之前"就把
    ``stage='recognizing'`` 写下来的地方（"成功"由 ``run_full_ingest`` 自己写在**它建的
    那一行**上；那条路径也是 docx / 法规 / CLI 共用的）。
    """
    from src.core.ingestion.pipeline import run_full_ingest
    from src.core.storage.backup import create_snapshot

    batch = load_batch(batch_id)
    if batch is None or batch["status"] != "running":
        return batch or {}
    ckpt = batch["checkpoint"]
    queue = ckpt.get("queue", [])
    errors: list[dict] = ckpt.get("errors", [])
    parsed = ckpt.get("parsed", 0)
    #: 「状态行没写进去」的文件清单（2026-09-21 第 5 步挂账 ③a）。
    #: ⚠ 原来只往 `errors` 里塞一条 —— 而 `errors` 是**排障用的杂项**，批次终态
    #: （`done` / `failed`）与 `GET /ingest/bulk/{id}` 都**看不出来**有文件的状态没落库
    #: ⇒ 界面没法如实告诉业主"这批里有文件的状态没写进去"。现在单独记一份、随终态持久化。
    state_missing: list[str] = list(ckpt.get("filing_state_missing") or [])
    #: 批次级的「重来一次」开关（create_bulk_batch 写进 checkpoint；缺省 False = 不覆盖）。
    batch_reingest = bool(ckpt.get("reingest"))
    budget_left = daily_budget
    for item in queue:
        if budget_left <= 0:
            ckpt["pause_reason"] = "daily_budget_reached"
            _save_ckpt(batch_id, ckpt, "paused")
            return _reload(batch_id)
        if item.get("status") in ("parsed", "failed"):
            continue
        budget_left -= 1
        # ── 「开始识别」：解析开始**之前**，如实把这一篇标成识别中 ──
        _write_item_state(item.get("doc_id"), "recognizing")
        item_reingest = batch_reingest or _placeholder_still_there(item)
        try:
            out = run_full_ingest(Path(item["path"]), item["standard_no"], item["name"],
                                  reingest=item_reingest)
            if out.get("status") in ("ok", "duplicate", "standard_exists"):
                item["status"] = "parsed"
                parsed += 1
                if out.get("status") == "ok" and not out.get("filing_state_written", True):
                    errors.append({"path": item["path"],
                                   "reason": "filing_state_not_written"})
                    # 进**终态**（见上面 state_missing 的注释）：界面据此如实说明
                    # "这一批里有 N 篇的状态没写进库"。
                    if item["path"] not in state_missing:
                        state_missing.append(item["path"])
            else:
                item["status"] = "failed"
                reason = str(out.get("status", "error"))
                errors.append({"path": item["path"], "reason": reason})
                # 解析没成 ⇒ 占位行还在（reingest 的删除只发生在解析成功之后）⇒
                # 把"识别失败 + 为什么"写在这一行上，别让它永远停在「识别中」。
                _write_item_state(item.get("doc_id"), "failed",
                                  failure_kind=str(out.get("message") or reason))
        except Exception as exc:  # noqa: BLE001
            item["status"] = "failed"
            errors.append({"path": item["path"], "reason": f"{type(exc).__name__}: {exc}"})
            _write_item_state(item.get("doc_id"), "failed",
                              failure_kind=f"解析中断（{type(exc).__name__}）")
        ckpt["parsed"] = parsed
        ckpt["filing_state_missing"] = state_missing
        if parsed % SNAPSHOT_EVERY_BATCHES == 0:
            try:
                create_snapshot(snapshot_type="auto")
            except Exception:  # 快照失败不阻塞导入
                pass
    remaining = [i for i in queue if i.get("status") not in ("parsed", "failed")]
    # 乙1：收尾写只许从活态迁入——用户中止的终态（failed/aborted_by_user）不许被顶成 done。
    _save_ckpt(batch_id, ckpt, "done" if not remaining else "failed",
               only_if_status_in=("running", "paused", "pending"))
    return _reload(batch_id)


# ---------------------------------------------------------------- 控制面
def pause_batch(batch_id: str) -> dict:
    batch = load_batch(batch_id)
    if batch is None:
        raise ValueError(f"批次不存在: {batch_id}")
    ckpt = batch["checkpoint"]
    ckpt["pause_reason"] = "user_requested"
    _save_ckpt(batch_id, ckpt, "paused")
    return _reload(batch_id)


def abort_batch(batch_id: str) -> dict:
    """终止批次（人工清场出口）：pending/running/paused → failed(pause_reason=aborted_by_user)；
    幂等：已 done/failed 的返回现状。终止后同目录可立即新建批次。"""
    batch = load_batch(batch_id)
    if batch is None:
        raise ValueError(f"批次不存在: {batch_id}")
    if batch["status"] in ("done", "failed"):
        return batch
    ckpt = batch["checkpoint"]
    ckpt["pause_reason"] = "aborted_by_user"
    with write_transaction() as txn:
        txn.execute("UPDATE bulk_import_batch SET status='failed', checkpoint_json=?"
                    " WHERE batch_id=?", (json.dumps(ckpt, ensure_ascii=False), batch_id))
        txn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type,"
            " target_id, after_state) VALUES (?,?,?,?,?,?)",
            (str(ULID()), "bulk/batch_aborted", "user", "bulk_import_batch",
             batch_id,
             json.dumps({"reason": "aborted_by_user", "prev_status": batch["status"]},
                        ensure_ascii=False)))
    return _reload(batch_id)


def _unscanned_remaining(batch: dict) -> bool:
    """R-A：判断扫描目录是否还有未扫文件（现场重列，兼容中断期间新增/删减）。"""
    ckpt = batch.get("checkpoint") or {}
    src = Path(ckpt.get("src_dir", ""))
    if not src.is_dir():
        return False
    files = [p for p in src.rglob("*.pdf") if p.is_file()]
    return ckpt.get("scanned", 0) < len(files)


def resume_batch(batch_id: str, daily_budget: int = DEFAULT_PARSE_DAILY_BUDGET) -> dict:
    """恢复批次（R-A 语义）：还有未扫文件（paused=扫描中断）→ 先续跑 fast_scan
    直到 scan_complete，再进入 parse_loop；快扫已完成的 paused 直接进解析。"""
    batch = load_batch(batch_id)
    if batch is None:
        raise ValueError(f"批次不存在: {batch_id}")
    if batch["status"] == "done":
        return batch
    if _unscanned_remaining(batch):
        out = fast_scan(batch_id)
        if (out.get("checkpoint") or {}).get("pause_reason") != "scan_complete":
            return out  # 中途又被外部暂停/其他状态：原样返回，不强行进解析
        batch = out
    _save_ckpt(batch_id, batch["checkpoint"], "running")
    return parse_loop(batch_id, daily_budget)


__all__ = ["create_bulk_batch", "load_batch", "fast_scan", "parse_loop",
           "pause_batch", "resume_batch", "abort_batch", "DEFAULT_BATCH_SIZE"]
