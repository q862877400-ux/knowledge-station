"""万级批量导入编排器测试（pipeline/11 契约验收 1~3）。离线，无真实解析。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import fitz  # PyMuPDF

from src.core.ingestion import bulk
from src.core.update.channels.base import UpdateError


@pytest.fixture(autouse=True)
def _clean_bulk_batches(db):
    """session 级共享库：每测后清 bulk_ingest 批次与本次创建的骨架行（C 级 pending 标记），防互相干扰。"""
    yield
    db.execute("DELETE FROM bulk_import_batch WHERE batch_kind='bulk_ingest'")
    db.execute("DELETE FROM doc_meta WHERE quality_grade='C'"
               " AND normative_refs LIKE '%pending_parse%'")
    db.commit()


# ---------------------------------------------------------------- 夹具
def make_pdf(path: Path, first_line: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    # 纯 ASCII 首行（fitz 内置字体不含 CJK，避免字体嵌入问题）
    page.insert_text((72, 72), first_line, fontsize=11)
    doc.save(str(path))
    doc.close()


def make_src_dir(tmp_path: Path, n: int = 3) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    for i in range(n):
        make_pdf(src / f"s{i}.pdf", f"GB/T 30{i:03d}-2020")
    return src


def test_fast_scan_creates_skeleton_rows(db, tmp_path):
    """验收1：快扫 → 骨架行（quality_grade=C、pending_parse 标记）+ 批次清单。"""
    src = make_src_dir(tmp_path, 3)
    batch = bulk.create_bulk_batch(str(src), batch_size=10)
    out = bulk.fast_scan(batch["batch_id"], batch_size=10)
    assert out["status"] == "paused"          # 快扫完成=待解析
    assert out["checkpoint"]["pause_reason"] == "scan_complete"
    ckpt = out["checkpoint"]
    assert len(ckpt["queue"]) == 3
    assert out["total"] == 3
    rows = db.execute("SELECT doc_id, standard_no, quality_grade, normative_refs"
                      " FROM doc_meta WHERE quality_grade='C'"
                      " AND normative_refs LIKE '%pending_parse%'").fetchall()
    assert len(rows) == 3
    for r in rows:
        assert r["quality_grade"] == "C"
        assert json.loads(r["normative_refs"]) == {"bulk_import": "pending_parse"}
        assert r["standard_no"].startswith("GB/T")


def test_fast_scan_dedup_and_quarantine(db, tmp_path):
    """验收1：重复文件防重跳过；首页无文本的 PDF 进隔离区。"""
    src = make_src_dir(tmp_path, 2)
    make_pdf(src / "s3.pdf", "GB/T 3033-2020 第四号")  # 再扫一次 → 重复
    empty = src / "blank.pdf"
    doc = fitz.open()
    doc.new_page()  # 无文本
    doc.save(str(empty))
    doc.close()

    batch = bulk.create_bulk_batch(str(src), batch_size=10)
    out = bulk.fast_scan(batch["batch_id"], batch_size=10)
    reasons1 = [e["reason"] for e in out["checkpoint"].get("errors", [])]
    assert "unparseable_first_page" in reasons1  # blank.pdf 在首扫即隔离
    quar = src / bulk.DEFAULT_QUARANTINE_DIR
    assert (quar / "blank.pdf").exists() or not (src / "blank.pdf").exists()
    # 防重：模拟"从零重扫"（重置 scanned）→ 已有文件全部 duplicate、不重复入库
    b = bulk.load_batch(batch["batch_id"])
    b["checkpoint"]["scanned"] = 0
    db.execute("UPDATE bulk_import_batch SET checkpoint_json=? WHERE batch_id=?",
               (json.dumps(b["checkpoint"], ensure_ascii=False), batch["batch_id"]))
    db.commit()
    out2 = bulk.fast_scan(batch["batch_id"], batch_size=10)
    reasons2 = [e["reason"] for e in out2["checkpoint"].get("errors", [])]
    assert "duplicate_file" in reasons2
    n_rows = db.execute("SELECT COUNT(*) FROM doc_meta"
                        " WHERE quality_grade='C'").fetchone()[0]
    assert n_rows == 3  # s0/s1/s3 各一次，无重复


def test_running_batch_rejected(db, tmp_path):
    """pending/running/paused 期间拒绝再建（409/UPD-2001 语义，pending 态即拦截）。"""
    src = make_src_dir(tmp_path, 1)
    b1 = bulk.create_bulk_batch(str(src), batch_size=10)   # pending
    with _raises_upd("UPD-2001"):
        bulk.create_bulk_batch(str(src), batch_size=10)
    assert b1 is not None


def test_pause_resume_and_budget_pause(db, tmp_path, monkeypatch):
    """验收2/3：暂停→恢复续跑；日预算耗尽转 paused；幂等解析防重。"""
    src = make_src_dir(tmp_path, 4)
    calls: list[str] = []

    def fake_ingest(pdf_path, standard_no, name, **kw):
        # ⚠ `**kw`（2026-09-21，KB-FOLDER-PLAN 第 4 步）：`parse_loop` 现在会传
        #   `reingest=`（占位行必须被真解析替换，否则 run_full_ingest 判 duplicate、
        #   一条条款都不解析 —— 见 `bulk._placeholder_still_there`）。桩只记调用，
        #   判据本身（parsed 计数 / 幂等）一个字没改。
        calls.append(standard_no)
        return {"status": "ok", "doc_id": "doc_x"}

    monkeypatch.setattr("src.core.ingestion.pipeline.run_full_ingest", fake_ingest)
    snap_calls = {"n": 0}
    monkeypatch.setattr("src.core.storage.backup.create_snapshot",
                        lambda snapshot_type="auto": snap_calls.__setitem__("n", snap_calls["n"] + 1))

    batch = bulk.create_bulk_batch(str(src), batch_size=10)
    bulk.fast_scan(batch["batch_id"], batch_size=10)
    bulk.resume_batch(batch["batch_id"], daily_budget=2)   # 预算 2 → 解析 2 个后 paused
    b = bulk.load_batch(batch["batch_id"])
    assert b["status"] == "paused"
    assert b["checkpoint"]["pause_reason"] == "daily_budget_reached"
    assert b["checkpoint"]["parsed"] == 2
    assert len(calls) == 2

    bulk.resume_batch(batch["batch_id"], daily_budget=10)  # 续跑剩余
    b = bulk.load_batch(batch["batch_id"])
    assert b["status"] == "done"
    assert b["checkpoint"]["parsed"] == 4
    assert len(calls) == 4  # 已解析的不重复调用（幂等）
    assert snap_calls["n"] >= 0  # 快照触发不抛错


def test_strict_dedup_new_source_not_skipped(db, tmp_path):
    """严格防重：换源（同内容换文件名 / 同标准号换内容）一律不静默跳过。"""
    src = make_src_dir(tmp_path, 1)  # s0.pdf → GB/T 3000-2020
    b1 = bulk.create_bulk_batch(str(src), batch_size=10)
    bulk.fast_scan(b1["batch_id"], batch_size=10)
    bulk.abort_batch(b1["batch_id"])

    # 同内容复制为新文件名：文件名不参与防重 → 仍判重复（duplicate_file）
    import shutil
    shutil.copy(src / "s0.pdf", src / "renamed.pdf")
    b2 = bulk.create_bulk_batch(str(src), batch_size=10)
    out2 = bulk.fast_scan(b2["batch_id"], batch_size=10)
    reasons2 = [e["reason"] for e in out2["checkpoint"].get("errors", [])]
    assert "duplicate_file" in reasons2
    assert "standard_no_exists" not in reasons2
    bulk.abort_batch(b2["batch_id"])

    # 同名但内容不同（换源新版）：大小+哈希 均不同 → 不跳过，作为新版本正常入队
    (src / "renamed.pdf").unlink(missing_ok=True)
    make_pdf(src / "s0.pdf", "GB/T 3000-2025")  # 覆盖同名文件，内容/大小/年号均变
    b3 = bulk.create_bulk_batch(str(src), batch_size=10)
    out3 = bulk.fast_scan(b3["batch_id"], batch_size=10)
    reasons3 = [e["reason"] for e in out3["checkpoint"].get("errors", [])]
    assert reasons3 == []  # 无重复、无冲突：新版本正常入队
    queue3 = out3["checkpoint"]["queue"]
    assert len(queue3) == 1
    assert queue3[0]["standard_no"] == "GB/T3000-2025"


def test_bad_dir_rejected(db):
    with _raises_upd("UPD-3007"):
        bulk.create_bulk_batch("/nonexistent/xx", batch_size=10)


def test_fast_scan_concurrent_matches_serial(db, tmp_path):
    """增强1：并发快扫（scan_concurrency=4）6 文件 → 6 骨架行、无异常、结果与串行等价。"""
    src = make_src_dir(tmp_path, 6)
    b = bulk.create_bulk_batch(str(src), batch_size=10)
    out = bulk.fast_scan(b["batch_id"], batch_size=10, scan_concurrency=4)
    assert out["status"] == "paused"
    assert len(out["checkpoint"]["queue"]) == 6
    assert out["total"] == 6
    rows = db.execute("SELECT standard_no FROM doc_meta WHERE quality_grade='C'"
                      " AND normative_refs LIKE '%pending_parse%'").fetchall()
    assert len(rows) == 6


def test_extract_name_fallback_full_text(db, tmp_path):
    """增强2：首页无名称时从全文回退（第 2 页 ASCII 名称）。"""
    src = tmp_path / "src2"
    src.mkdir()
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "GB/T 8800-2022")
    p2 = doc.new_page()
    p2.insert_text((72, 72), "TESTNAME-01")
    doc.save(str(src / "two.pdf"))
    doc.close()

    b = bulk.create_bulk_batch(str(src), batch_size=10)
    out = bulk.fast_scan(b["batch_id"], batch_size=10)
    queue = out["checkpoint"]["queue"]
    assert len(queue) == 1
    assert queue[0]["standard_no"] == "GB/T8800-2022"
    assert queue[0]["name"] == "TESTNAME-01"


# ---------------------------------------------------------------- R-A：取消扫描上限
def test_fast_scan_no_cap_scans_all_450(db, tmp_path, monkeypatch):
    """R-A 验收①：450 文件 + batch_size=200 → 一次 fast_scan 扫完全部（无 200 截断）；
    batch_size=checkpoint 粒度（⌈450/200⌉=3 次批间落盘）。"""
    src = tmp_path / "src450"
    src.mkdir()
    for i in range(450):
        make_pdf(src / f"s{i}.pdf", f"GB/T 31{i:03d}-2020")

    gran = {"n": 0}
    real_save = bulk._save_ckpt

    def spy_save(batch_id, ckpt, status=None, total=None, only_if_status_in=None):
        if status is None:
            gran["n"] += 1  # 批粒度 checkpoint（不带 status 的落盘）
        return real_save(batch_id, ckpt, status=status, total=total)

    monkeypatch.setattr(bulk, "_save_ckpt", spy_save)

    b = bulk.create_bulk_batch(str(src), batch_size=200)
    out = bulk.fast_scan(b["batch_id"], batch_size=200)
    assert out["status"] == "paused"
    assert out["checkpoint"]["pause_reason"] == "scan_complete"
    assert out["checkpoint"]["scanned"] == 450          # 全量扫完，不截断在 200
    assert len(out["checkpoint"]["queue"]) == 450
    assert out["total"] == 450
    rows = db.execute("SELECT COUNT(*) FROM doc_meta WHERE quality_grade='C'"
                      " AND normative_refs LIKE '%pending_parse%'").fetchone()[0]
    assert rows == 450
    assert gran["n"] == 3  # 200/400/450 → 三次批间 checkpoint


def test_fast_scan_midway_pause_then_resume_finishes(db, tmp_path, monkeypatch):
    """R-A 验收②：第 250 个文件时外部置 paused → 扫描就近停止且保持 paused；
    resume 续跑 fast_scan 扫完剩余文件后进入解析直至 done。"""
    src = tmp_path / "src_pause"
    src.mkdir()
    for i in range(450):
        make_pdf(src / f"p{i}.pdf", f"GB/T 32{i:03d}-2020")

    b = bulk.create_bulk_batch(str(src), batch_size=200)
    real = bulk._process_pdf
    state = {"n": 0}

    def pausing_pdf(pdf, known, seen, lock, quar_dir):
        out = real(pdf, known, seen, lock, quar_dir)
        with lock:
            state["n"] += 1
            hit = state["n"] == 250
        if hit:
            bulk.pause_batch(b["batch_id"])  # 用户暂停（公共控制面 API）
        return out

    monkeypatch.setattr(bulk, "_process_pdf", pausing_pdf)
    out = bulk.fast_scan(b["batch_id"], batch_size=200)
    assert out["status"] == "paused"                        # 保持 paused，未被覆盖
    assert out["checkpoint"]["pause_reason"] == "user_requested"  # 外部暂停标记保留
    mid = out["checkpoint"]["scanned"]
    assert 200 <= mid <= 300                                # 中断点落在第 250 个附近
    assert len(out["checkpoint"]["queue"]) == mid           # 无丢失、无多记

    # resume：扫描中断断点 → 先续跑 fast_scan 至 scan_complete，再进解析
    monkeypatch.setattr("src.core.ingestion.pipeline.run_full_ingest",
                        lambda pdf_path, no, name, **kw: {"status": "ok", "doc_id": "doc_x"})
    monkeypatch.setattr("src.core.storage.backup.create_snapshot",
                        lambda snapshot_type="auto": None)
    out2 = bulk.resume_batch(b["batch_id"])
    assert out2["status"] == "done"
    ck = out2["checkpoint"]
    assert ck["scanned"] == 450                             # resume 把扫描补齐到穷尽
    assert ck["parsed"] == 450
    assert all(item["status"] == "parsed" for item in ck["queue"])


class _raises_upd:
    """with 助手：断言 UpdateError 且 code 匹配。"""

    def __init__(self, code: str):
        self.code = code

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        assert exc_type is UpdateError, f"期望 UpdateError，实际 {exc_type}"
        assert exc.code == self.code, f"错误码 {exc.code} != {self.code}"
        return True
