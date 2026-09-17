# -*- coding: utf-8 -*-
"""`dry_run` 的**同文件解析串行**（§10.77）。

背景（§10.73 登记的连带风险）：dryrun 的临时目录按**源文件哈希**命名 ⇒ 同一文件的两个并发
预览写同一个目录；显式走深通道时那个落地目录还会被**读回**（layout.json + images）⇒
理论上有撕裂读。这个并发在改动前就存在（jobs 的 worker 线程 vs 同步请求），§10.73 把预览
端点改成 `def`（线程池）之后变宽（两次点击即可）。

判据是**行为级**：拿一个替身解析器记录"同时在解析的有几个"，然后真的开两个线程。
  · **同一文件** ⇒ 并发峰值必须是 1（串行）；
  · **不同文件**（且分片不同）⇒ 允许并发（证明不是用"全局一把锁"糊过去的）。
"""
from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path

import pytest

from src.core.ingestion import dry_run


def _stripe_of(tmp_dir: Path) -> int:
    key = hashlib.sha256(str(tmp_dir).encode("utf-8")).digest()
    return int.from_bytes(key[:4], "big") % dry_run._PARSE_LOCK_STRIPES


class _FakeParser:
    """替身解析器：记录并发峰值与调用次数，每次停 `hold` 秒。"""

    def __init__(self, hold: float = 0.25) -> None:
        self.lock = threading.Lock()
        self.live = 0
        self.peak = 0
        self.calls = 0
        self.hold = hold

    def __call__(self, path, output_dir, timeout=900, force_deep=False, deep_fallback=True):
        with self.lock:
            self.live += 1
            self.calls += 1
            self.peak = max(self.peak, self.live)
        try:
            time.sleep(self.hold)
            return {"blocks": [], "geometries": {}, "text_layer_state": "empty"}
        finally:
            with self.lock:
                self.live -= 1


def _make_pdf(path: Path, text: str) -> Path:
    """造一份**真 PDF**（假字节过不了体检里的 fitz 解析，第一步就抛）。"""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((56, 72), text, fontname="china-s", fontsize=11)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def tmp_pdfs(tmp_path):
    from src.core.storage.sqlite_db import init_schema
    init_schema()                      # 预览报告会查重（读 doc_meta）
    a = _make_pdf(tmp_path / "same_a.pdf", "同一份内容")
    b = tmp_path / "same_b.pdf"
    b.write_bytes(a.read_bytes())      # **逐字节相同** ⇒ 同一 hash ⇒ 同一临时目录
    return a, b


def _run_pair(p1: Path, p2: Path) -> _FakeParser:
    """两个线程同时预览两份文件，返回替身解析器的统计。

    ⚠ 替身要打在 **`parser_worker.run_parser_isolated`** 上：`analyze_preview_report` 里是
    `from src.core.ingestion.parser_worker import run_parser_isolated`（函数内导入），
    所以补 `dry_run.run_parser_isolated` 这个名字**根本不存在**——第一次就是这么"绿不了"的
    （实测 calls=0，正是"我以为在测，其实没走到"的形状）。
    """
    from src.core.ingestion import parser_worker
    fake = _FakeParser()
    original = parser_worker.run_parser_isolated
    parser_worker.run_parser_isolated = fake
    try:
        threads = [threading.Thread(target=dry_run.analyze_preview_report, args=(p,))
                   for p in (p1, p2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
    finally:
        parser_worker.run_parser_isolated = original
    assert fake.calls == 2, f"两次预览都该真的走到解析，实际 {fake.calls} 次"
    return fake


def test_同一份源文件的并发预览被串行化(tmp_pdfs):
    """同一 content ⇒ 同一 `<hash16>` 目录 ⇒ 必须串行（并发峰值 = 1）。"""
    a, b = tmp_pdfs
    fake = _run_pair(a, b)
    assert fake.peak == 1, (
        f"同一文件的两次预览并发峰值 = {fake.peak}（应串行）——"
        "临时目录按 hash 命名，并发写/读回会互相踩")


def test_不同文件的并发预览允许并行(tmp_pdfs, tmp_path):
    """**反向断言**：不同文件（分片不同）不许被一把全局锁串起来。

    为什么重要：把上面那条修成"全局一把锁"也能让它变绿，但那样**批量预览与手动预览会互相等**
    ——那是拿吞吐换安全，属于本仓一直在防的"顺手把别的也牺牲掉"。
    """
    from src.core.config import get_settings

    a, _ = tmp_pdfs
    base = get_settings().data_dir / "dryrun" / "tmp"
    want = _stripe_of(base / str(dry_run._sha256_file(a))[:16])
    other = None
    # 挑一份**真 PDF**、且分片与 a 不同（确定性：sha256 固定，撞了就换内容）
    for i in range(200):
        cand = _make_pdf(tmp_path / f"cand{i}.pdf", f"另一份内容 {i}")
        if _stripe_of(base / dry_run._sha256_file(cand)[:16]) != want:
            other = cand
            break
    assert other is not None, "200 次都没撞出不同分片——分片函数或常量变了？"

    class _Slow(_FakeParser):
        pass

    from src.core.ingestion import parser_worker
    fake = _Slow(hold=0.4)
    original = parser_worker.run_parser_isolated
    parser_worker.run_parser_isolated = fake
    try:
        threads = [threading.Thread(target=dry_run.analyze_preview_report, args=(p,))
                   for p in (a, other)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
    finally:
        parser_worker.run_parser_isolated = original
    assert fake.calls == 2
    assert fake.peak == 2, (
        f"不同文件被串行化了（并发峰值 {fake.peak}）——锁应当是**分片**的，不是全局一把")
