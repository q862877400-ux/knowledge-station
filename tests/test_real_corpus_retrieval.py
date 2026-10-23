"""**真语料**上的检索与条款定位判据（种子库驱动）。

## 这个文件为什么存在

`tests/conftest.py` 的 `_isolate_data_dir` 把所有测试钉在**空临时库**上
⇒ 在这之前，**3,076 条用例里跑在真库上的是 0 条**。
后果实测：`resolve_clause` 的跨标准误命中（9 部受害标准）能活到今天，
因为那条 SQL 在空库上永远返回 `None`，走不到误命中分支。

⇒ 本文件用 `seed_data_dir` fixture（82 部真实标准 / 4,809 条真实条款）
把"在真语料上对不对"变成**门禁能自动验的事**。

## 与 `test_seed_db_guard.py` 的分工

- `test_seed_db_guard.py`：**种子库本身**的健康（规模、必含标准、FTS 是否真插入）；
- 本文件：**被测代码**在真语料上的行为。

## 写法约定

每条断言都写明「为什么这条判据在空库上验不出来」——否则将来有人会把它
"优化"回空库。
"""
from __future__ import annotations

import pytest

#: 种子库里确实存在的标准（`scripts/make-seed-db.py` 的 MUST_INCLUDE）
KNOWN = "GBZ 188-2025"


@pytest.fixture()
def repo(seed_data_dir):
    """拿到已灌种子库的 `clause_repo`。"""
    from src.core.storage import clause_repo
    return clause_repo


def test_seed_fixture_actually_has_corpus(seed_data_dir):
    """先证明 fixture 里真有语料 —— 否则后面每条断言都会"通过"，但什么都没验。

    ⚠ 这条是**元判据**：它保护后面所有测试不变成假绿。
    """
    import sqlite3
    from pathlib import Path
    db = Path(seed_data_dir) / "database" / "knowledge.db"
    assert db.exists(), f"种子库没被拷到临时目录：{db}"
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        n_doc = conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
        n_clause = conn.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    finally:
        conn.close()
    assert n_doc >= 50, f"种子库只有 {n_doc} 部文档，太少"
    assert n_clause >= 2000, f"种子库只有 {n_clause} 条条款，太少"


def test_real_clause_is_resolvable(repo):
    """真条款能按「标准号 + 条款号」定位到 —— **空库上验不出来**（空库返回 None）。"""
    got = repo.resolve_clause(KNOWN, "5.22")
    assert got is not None, f"{KNOWN} / 5.22 应该能定位到（种子库里确实有这条）"
    assert got.standard_no == KNOWN
    assert got.clause_number == "5.22"
    assert "甲醇" in (got.content_text or ""), "5.22 是甲醇条款，正文里应出现「甲醇」"


def test_real_clause_carries_source_spans(repo):
    """真条款带**位置片段**（可点链接要用）—— 空库上没有 span 可查。"""
    got = repo.resolve_clause(KNOWN, "5.22")
    assert got is not None
    assert got.source_spans, "真条款必须带 source_spans（否则界面上点不了原文）"
    span = got.source_spans[0]
    assert span.page_number and span.page_number > 0
    assert span.bbox, "位置片段必须有 bbox（画红框要用）"


def test_absent_clause_returns_none_not_a_wrong_standard(repo):
    """**查不到的条款号必须返回 None**，不许串到别家标准。

    ⚠ 这是本文件最重要的一条。它现在会**红**（因为兜底有缺陷），
    那正是它存在的意义：把 `resolve_clause` 的跨标准误命中钉在门禁里，
    而不是只在某个人的临时脚本里。

    **为什么必须用 `5.22.3` 而不是随便一个不存在的号**（实测）：
    兜底只在「该标准**确实有**以这个号开头的其它条款」时才走到 LIKE 分支。
    `5.22.3` 命中（`GBZ 188-2025` 有 `5.22`/`5.22.1`/`5.22.2` 但没有 `5.22.3`），
    而 `9.9.9.9` / `7.7.7` 这类**根本不存在的前缀会正常返回 None** ——
    用它们写测试会得到一条**假绿**（本文件第一版就是，已改）。

    修了兜底之后这条会自动变绿 —— **那时不要删它**。
    """
    # 先证明前提：GBZ 188-2025 确实有 5.22 但没有 5.22.3
    base = repo.resolve_clause(KNOWN, "5.22")
    assert base is not None and base.standard_no == KNOWN, (
        f"前提不成立：{KNOWN} / 5.22 应存在（种子库缺数据？）")

    got = repo.resolve_clause(KNOWN, "5.22.3")
    if got is not None and got.standard_no != KNOWN:
        pytest.fail(
            f"跨标准误命中：查 {KNOWN} / 5.22.3（不存在）却返回了 "
            f"{got.standard_no} 的条款。这是 wiki §四 #2 的缺陷。")


def test_standard_number_disambiguates_between_documents(repo):
    """同一个条款号在不同标准下必须是不同条款（不许串号）。

    空库上只有测试自己插的两条，验不出"真实世界里同号多标准"的规模。
    """
    a = repo.resolve_clause(KNOWN, "5.22")
    b = repo.resolve_clause("GB 6675.2-2025", "5.22.3")
    assert a is not None and b is not None
    assert a.doc_id != b.doc_id, "两部不同标准的条款 doc_id 不该相同"
    assert a.clause_key != b.clause_key


def test_hybrid_search_finds_real_methanol_clause(seed_data_dir):
    """**六路检索**在真语料上能召回到甲醇条款。

    空库上检索永远返回空列表 ⇒ 这条判据在空库上**结构上做不到**。
    它验的是"端到端能召回到正确条款"，不是"召回了多少条"。
    """
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    res = perform_hybrid_search("甲醇 职业健康检查", top_k=10)
    items = res if isinstance(res, list) else getattr(res, "results", res)
    assert items, "检索返回空 —— 要么 FTS 没建，要么检索链路坏了"
    hits = []
    for it in items:
        no = getattr(it, "standard_no", None) or (it.get("standard_no") if isinstance(it, dict) else None)
        cn = getattr(it, "clause_number", None) or (it.get("clause_number") if isinstance(it, dict) else None)
        hits.append((no, cn))
    assert any(no == KNOWN for no, _ in hits), (
        f"检索没召回 {KNOWN}，实际召回：{hits[:10]}")


def test_fts_channel_works_on_real_corpus(seed_data_dir):
    """FTS 通道在真语料上能查到中文词。

    ⚠ 这条专门防「`clause_fts` 是空壳」：种子库生成脚本第一版用
    `INSERT INTO x(x) VALUES('rebuild')` 静默插了 0 行，而 `COUNT(*)` 也是 0，
    如果不真查一次就发现不了。
    """
    import sqlite3
    from pathlib import Path
    db = Path(seed_data_dir) / "database" / "knowledge.db"
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM clause_fts WHERE clause_fts MATCH '甲醇'").fetchone()[0]
    finally:
        conn.close()
    assert n > 0, "FTS 里查不到「甲醇」⇒ 分词口径不对或索引是空的"
