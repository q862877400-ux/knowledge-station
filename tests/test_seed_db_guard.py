"""种子库的回归护栏 —— 把「它能复现已知缺陷」这件事钉住。

**为什么这个测试必须存在**：
种子库是"在真库上验证"的唯一可行载体（`var/data` 72 GB 进不了版本控制）。
它一旦被改坏（少拷了受害标准、FTS 没重建、目录树不完整），
`resolve_clause` 那条跨标准误命中就**再也复现不了**，而不会有任何东西报错。

⇒ 本文件钉三件事：
1. 种子库存在且规模合理（不能变成空库，也不能膨胀回几百 MB）；
2. **缺陷现场完整**：9 部受害标准 + 3 部被误命中的别家标准都在；
3. **缺陷能复现**：在种子库上查 `GBZ 188-2025 / 5.22.3` 会串到别家标准。

⚠ 第 3 条是**钉住一个 bug 的存在**，不是钉住正确行为。
将来修了那个兜底，这条会红 —— 那时**必须同步改成「查不到就该 None」**，
而不是删掉它（删掉就等于把现场永久丢掉）。
"""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "tests" / "fixtures" / "seed" / "knowledge-seed.db"

#: 缺陷现场：9 部"受害标准"（查不存在的条款号会被串到别家）+ 3 部"别家标准"
VICTIM_STANDARDS = [
    "GBZ 188-2025", "GBZ 24-2025", "GBZ 215-2025", "GBZ 336-2025", "GBZ 337-2025",
    "GBZ 15-2024", "GBZ 37-2024", "GB/T 144-2024", "GB/T 150.4-2024",
]
OTHER_STANDARDS = ["GB 6675.2-2025", "GB/T 13537-2024", "GB 16556-2025"]
#: 年份宽容的正向样本（改兜底时不能改坏）
FORWARD_SAMPLES = ["GB 3608-2025", "GB 30871-2022"]


@pytest.fixture(scope="module")
def seed_db() -> Path:
    if not SEED.exists():
        pytest.skip(
            f"种子库不存在：{SEED}。用 `python scripts/make-seed-db.py --docs 60` 生成"
            "（需要本机有 var/data/database/knowledge.db）。")
    return SEED


def test_seed_db_exists_and_size_is_sane(seed_db: Path) -> None:
    """规模合理：不能是空库，也不能膨胀到没法进版本控制。"""
    size_mb = seed_db.stat().st_size / 1e6
    assert 5 <= size_mb <= 120, f"种子库 {size_mb:.1f} MB，超出 5~120 MB 的合理区间"


def test_seed_db_has_all_required_standards(seed_db: Path) -> None:
    """缺陷现场必须完整 —— 少一部标准，那条 bug 就复现不了。"""
    conn = sqlite3.connect(f"file:{seed_db}?mode=ro", uri=True)
    try:
        have = {r[0] for r in conn.execute("SELECT standard_no FROM doc_meta")}
    finally:
        conn.close()
    missing = [s for s in VICTIM_STANDARDS + OTHER_STANDARDS + FORWARD_SAMPLES
               if s not in have]
    assert missing == [], f"种子库缺这些必含标准（缺陷现场不完整）：{missing}"


def test_seed_db_fts_is_populated(seed_db: Path) -> None:
    """FTS 必须是**真插入**过的，不是空壳。

    `clause_fts` 是独立 FTS5 表（无 `content=`）⇒ `INSERT INTO x(x) VALUES('rebuild')`
    会静默返回 0 行。种子库生成脚本第一版就踩了这个坑。
    """
    conn = sqlite3.connect(f"file:{seed_db}?mode=ro", uri=True)
    try:
        n_clause = conn.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
        n_fts = conn.execute("SELECT COUNT(*) FROM clause_fts").fetchone()[0]
        # 抽一条确认能查到（空壳表 count 也会是 0，所以必须真查一次）
        hit = conn.execute(
            "SELECT COUNT(*) FROM clause_fts WHERE clause_fts MATCH '甲醇'").fetchone()[0]
    finally:
        conn.close()
    assert n_fts == n_clause, f"clause_fts {n_fts} != clause_revision {n_clause}"
    assert hit > 0, "FTS 里查不到「甲醇」⇒ 分词或插入口径不对"


def _resolve_on_seed(seed_db: Path, tmp_path: Path, monkeypatch,
                     standard_no: str, clause_number: str):
    """在**种子库副本**上跑真的 `resolve_clause`（不碰生产库）。

    ⚠ **切换数据目录前必须先关旧连接**：`get_db_connection()` 按线程缓存，
    前面用例留下的连接会指向旧库 ⇒ 读到空库（全跑红、单跑绿的典型形态）。
    """
    from src.core.storage.sqlite_db import (
        close_all_connections, close_thread_connection)

    data_dir = tmp_path / "data"
    (data_dir / "database").mkdir(parents=True, exist_ok=True)
    shutil.copy2(seed_db, data_dir / "database" / "knowledge.db")
    close_thread_connection()
    close_all_connections()
    monkeypatch.setenv("KS_DATA_DIR", str(data_dir))
    from src.core import config
    config.reset_settings()
    from src.core.storage import clause_repo
    try:
        return clause_repo.resolve_clause(standard_no, clause_number)
    finally:
        close_thread_connection()
        close_all_connections()
        config.reset_settings()


def test_cross_standard_false_hit_is_fixed(
        seed_db: Path, tmp_path: Path, monkeypatch) -> None:
    """**跨标准误命中已修**（wiki §四 #2，2026-10-23）。

    历史：`GBZ 188-2025` 里没有 `5.22.3`，但年份兜底正则把 `2025` 当成标准号主体，
    用 `LIKE '%2025%'` 去搜 ⇒ 串到 `GB 6675.2-2025`（玩具安全标准）。
    真库 8,983 部里 9 部会误命中，全是职业健康/安全类标准。

    修法：`clause_repo._standard_body()` 先剥尾部年份再抽主体；
    抽不到就**不兜底**（返回 None）。

    ⚠ **这条测试的前身是「钉住缺陷存在」**（`assert got is not None`）。
    修完之后按当初写下的约定改成了 `assert got is None` —— **没有删掉它**。
    现场记录见 `docs/uniformity/README.md` §3.1。
    """
    got = _resolve_on_seed(seed_db, tmp_path, monkeypatch, "GBZ 188-2025", "5.22.3")
    assert got is None, (
        f"跨标准误命中又出现了：查 GBZ 188-2025 / 5.22.3（不存在）返回了 "
        f"{got.standard_no if got else None}。兜底的 _standard_body 判据被改坏了。")


def test_all_victim_standards_no_longer_cross_hit(
        seed_db: Path, tmp_path: Path, monkeypatch) -> None:
    """那 **9 部受害标准**逐个验：查不存在的条款号**一律不许串到别家**。

    这是"修一个点"和"修一类"的区别 —— 只验 `GBZ 188-2025` 一部，
    将来换个标准号写法又会漏。真库实测这 9 部是全部受害面。
    """
    bad = []
    for no in VICTIM_STANDARDS:
        got = _resolve_on_seed(seed_db, tmp_path, monkeypatch, no, "5.22.3")
        if got is not None and got.standard_no != no:
            bad.append(f"{no} → {got.standard_no}")
    assert bad == [], f"仍有 {len(bad)} 部标准跨标准误命中：{bad}"


def test_year_tolerance_forward_path_still_works(
        seed_db: Path, tmp_path: Path, monkeypatch) -> None:
    """年份宽容的**正向**路径：旧版号要能宽松到现行版（修兜底时不能改坏）。"""
    got = _resolve_on_seed(seed_db, tmp_path, monkeypatch, "GB 3608-2019", "4.1")
    assert got is not None, "年份宽容失效了：GB 3608-2019 应宽松到 GB 3608-2025"
    assert got.standard_no == "GB 3608-2025"
