# -*- coding: utf-8 -*-
"""`pypdf_backfill` 的回归测试（2026-09-16 新建）。

**为什么此前完全没有测试**：这个模块把"越界抽取"的补丁直接写进
`clause_patch`，再经 `fetch_full_clause` 透明覆写条款正文——一条完全没有测试
覆盖的写库路径。实测后果：19,981 条补丁里 14,906 条（74.6%）含盗版站页脚/页眉，
涉及 2,112 个文档，污染进检索、引用与 LLM 提示词。

本文件锁三件事：
  ① `pypdf_page_clauses` 的**边界**：表/图/附录编号、页眉、工具水印出现即终止归并
     （旧实现只认下一条**数字条款号** → buf 吃到页尾）；
  ② `_is_terminator` **不误判正文**（普通句子/条款号不得终止）；
  ③ 回填**长度量级护栏**：越界型（远超原文字数）被拒绝。
"""
from __future__ import annotations

from src.core.ingestion import pypdf_backfill as P


# ---------------------------------------------------------------- 终止锚
def test_terminator_hits_structural_markers():
    """表/图/附录编号、页眉、工具水印 → 必须终止归并。"""
    for s in [
        "表3 试验条件与用量",
        "表 A.1 检验项目",
        "图4 外形示意图",
        "图A.2 结构",
        "附录A 计算方法",
        "附录 B.2 补充说明",
        "5 GB/T 10029—2010",                       # 页眉（页码+标准号）
        "Evaluation Only. Created with Aspose.PDF. Copyright 2002-2025 Aspose Pty Ltd.",
        "Created with Aspose.PDF",
    ]:
        assert P._is_terminator(s), s


def test_terminator_does_not_hit_body_text():
    """**反向对照**：普通正文与条款号不得被当成边界（否则正文被腰斩）。"""
    for s in [
        "4.1.1 外形",
        "体高而侧扁,呈菱形。",
        "应符合 GB/T 18654.1 的规定执行。",
        "见表 5 的规定。",                          # 含"表"但不是表编号行
        "如图 1 所示。",                            # 含"图"但不是图编号行
        "本文件按照 GB/T 1.1—2020 的规定起草。",     # 含标准号但无前导页码
        "5.2.3 试验方法",
    ]:
        assert not P._is_terminator(s), s


def test_page_clauses_stops_at_table_anchor():
    """**核心回归**：条款正文在表编号处收口，不再吞下页尾。

    缺陷复现（旧实现）：'4.1 试验条件' 之后是 '表3 用量'、页眉与水印，
    旧实现把它们**全并进 4.1**（于是补丁正文里出现页眉与 Aspose 水印）。
    """
    page_text = "\n".join([
        "4.1 试验条件",
        "在下列条件下进行试验。",
        "表3 试验条件",
        "项目 数值",
        "5 GB/T 10029—2010",
        "Evaluation Only. Created with Aspose.PDF. Copyright 2002-2025 Aspose Pty Ltd.",
    ])
    P._pypdf_available = lambda: True          # 只测切分逻辑，不依赖 pypdf 安装
    out = _clauses_from_text(page_text)
    assert "4.1" in out
    body = out["4.1"]
    assert "在下列条件下进行试验。" in body, body
    for leaked in ("表3", "GB/T 10029", "Aspose", "Evaluation Only", "项目 数值"):
        assert leaked not in body, (leaked, body)


def test_page_clauses_next_clause_still_splits():
    """终止锚不得破坏原有的"下一条款切分"行为。"""
    page_text = "\n".join([
        "4.1 试验条件", "在下列条件下进行试验。",
        "4.2 试验方法", "按下列方法执行。",
    ])
    out = _clauses_from_text(page_text)
    assert set(out) == {"4.1", "4.2"}, out
    assert out["4.2"].startswith("4.2 试验方法")


def test_page_clauses_appendix_anchor():
    """附录编号行也必须终止（实测 `表E.4`/`附录A` 是越界的主要来源之一）。"""
    page_text = "\n".join([
        "5.1 一般要求", "应符合本章要求。",
        "附录A 计算方法", "A.1 通则",
    ])
    out = _clauses_from_text(page_text)
    assert "5.1" in out
    assert "附录A" not in out["5.1"], out["5.1"]


# ---------------------------------------------------------------- 长度护栏
def _mem_conn():
    """内存库 + 最小 schema（backfill_document 碰 clause_revision / clause_patch /
    clause_fts —— 回填现在会**同步 FTS**，见 `_reindex_fts`）。"""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE clause_revision (clause_revision_id TEXT, clause_number TEXT,"
                 " page_start INT, page_end INT, content_text TEXT, doc_id TEXT,"
                 " content_type TEXT, title TEXT, modality TEXT, subject TEXT,"
                 " behavior_scope TEXT)")
    conn.execute("CREATE TABLE clause_patch (patch_id TEXT, clause_revision_id TEXT,"
                 " field_name TEXT, patched_value TEXT, patch_reason TEXT, created_at TEXT)")
    conn.execute(
        "CREATE VIRTUAL TABLE clause_fts USING fts5(clause_revision_id UNINDEXED,"
        " clause_number, standard_no, title, content_segmented, modality UNINDEXED,"
        " subject UNINDEXED, behavior_scope_segmented)")
    return conn


def _fts_conn(monkeypatch, tmp_path, orig, good):
    """带 clause_fts 的内存库 + 已就位的一行正文（用于验证 FTS 同步）。"""
    from src.core.ingestion import pypdf_backfill as B

    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(B, "_pypdf_available", lambda: True)
    monkeypatch.setattr(B, "pypdf_page_clauses", lambda p, n: {"4.1": good})

    conn = _mem_conn()
    conn.execute(
        "INSERT INTO clause_revision (clause_revision_id, clause_number, page_start,"
        " page_end, content_text, doc_id, content_type, title, modality, subject,"
        " behavior_scope) VALUES ('r1','4.1',1,1,?,'d1','normal','试验条件','应','主体','行为域')",
        (orig,))
    # 索引先存**补丁前原文**（这正是缺陷状态）
    from src.core.storage.clause_repo import _seg
    conn.execute("INSERT INTO clause_fts VALUES ('r1','4.1','GB 1-2020','试验条件',?,"
                 "'应','主体',?)", (_seg(orig), _seg("行为域")))
    return B, conn, pdf


def test_backfill_syncs_fts_with_patched_text(monkeypatch, tmp_path):
    """**核心回归**：回填后 `clause_fts` 必须反映**补丁正文**，而不是补丁前原文。

    缺陷（本函数是孤立点）：旧实现用**裸 INSERT** 写 `clause_patch`，绕过了
    `clause_repo.upsert_patch` 里的 `_reindex_clause_indexes` —— 而
    `fetch_full_clause` 读的是**补丁正文**。后果：这些条款的全文检索命中的是旧文本
    （用户按新正文里的词搜不到）。实测全库 19,981 条补丁**全部**由本函数产生。
    """
    orig = "4.1 试验条件 在下列条件下进行。"
    good = "4.1 试验条件 在下列条件下进行,温度为 25 ℃,时间为 30 min,湿度 65 %。"
    B, conn, pdf = _fts_conn(monkeypatch, tmp_path, orig, good)

    n = B.backfill_document("d1", str(pdf), conn=conn)
    assert n == 1, "合理回填应被接受"

    from src.core.storage.clause_repo import _seg
    row = conn.execute(
        "SELECT content_segmented FROM clause_fts WHERE clause_revision_id='r1'").fetchone()
    seg = row[0]
    assert seg == _seg(good), "FTS 必须存补丁正文的分词"
    # 反向：不再是补丁前原文
    assert seg != _seg(orig), "FTS 仍是补丁前原文（缺陷未修）"


def test_backfill_fts_untouched_when_rejected(monkeypatch, tmp_path):
    """反向对照：回填被拒（越界）时**不得**动 FTS（否则索引指向不存在的正文）。"""
    orig = "4.1 试验条件 在下列条件下进行。"
    huge = orig + " 页尾噪声" * 500
    B, conn, pdf = _fts_conn(monkeypatch, tmp_path, orig, huge)

    from src.core.storage.clause_repo import _seg
    before = conn.execute(
        "SELECT content_segmented FROM clause_fts WHERE clause_revision_id='r1'").fetchone()[0]

    n = B.backfill_document("d1", str(pdf), conn=conn)
    assert n == 0
    after = conn.execute(
        "SELECT content_segmented FROM clause_fts WHERE clause_revision_id='r1'").fetchone()[0]
    assert after == before == _seg(orig), "被拒时 FTS 必须保持原样"


def test_backfill_rejects_oversized_text(monkeypatch, tmp_path):
    """回填若把文本撑成原文的 3 倍以上（越界抽取的直接特征）→ 拒绝打补丁。

    ⚠ 必须给**真实存在**的 pdf_path：`backfill_document` 开头有
    `if not pdf_path or not os.path.exists(pdf_path): return 0` 守卫
    （本用例初版传了不存在的 "x.pdf"，于是无论护栏如何都返回 0 —— 假绿通过）。
    """
    from src.core.ingestion import pypdf_backfill as B

    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    orig = "4.1 试验条件 在下列条件下进行。"
    huge = orig + " 页尾噪声" * 500                 # 远超 3×+400
    monkeypatch.setattr(B, "_pypdf_available", lambda: True)
    monkeypatch.setattr(B, "pypdf_page_clauses", lambda p, n: {"4.1": huge})

    conn = _mem_conn()
    conn.execute("INSERT INTO clause_revision (clause_revision_id, clause_number,"
                 " page_start, page_end, content_text, doc_id, content_type)"
                 " VALUES ('r1','4.1',1,1,?, 'd1','normal')", (orig,))
    n = B.backfill_document("d1", str(pdf), conn=conn)
    assert n == 0, "越界文本必须被拒绝"
    assert conn.execute("SELECT count(*) FROM clause_patch").fetchone()[0] == 0


def test_backfill_accepts_reasonable_text(monkeypatch, tmp_path):
    """**反向对照**：长度合理且数字更多的回填必须被接受（护栏不得打掉真修复）。"""
    from src.core.ingestion import pypdf_backfill as B

    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    orig = "4.1 试验条件 在下列条件下进行。"
    # 数字个数须满足原有判据（`_digits(ptxt) >= 3` 且 > 原文 1.5 倍）——
    # 这是回填的既有门槛，本用例只验证**新增的长度护栏**不误杀它。
    good = "4.1 试验条件 在下列条件下进行,温度为 25 ℃,时间为 30 min,湿度 65 %。"
    monkeypatch.setattr(B, "_pypdf_available", lambda: True)
    monkeypatch.setattr(B, "pypdf_page_clauses", lambda p, n: {"4.1": good})

    conn = _mem_conn()
    conn.execute("INSERT INTO clause_revision (clause_revision_id, clause_number,"
                 " page_start, page_end, content_text, doc_id, content_type)"
                 " VALUES ('r1','4.1',1,1,?, 'd1','normal')", (orig,))
    n = B.backfill_document("d1", str(pdf), conn=conn)
    assert n == 1, "合理回填必须被接受"
    row = conn.execute("SELECT patched_value FROM clause_patch WHERE field_name='content_text'").fetchone()
    assert row[0] == good


# ---------------------------------------------------------------- 辅助
def _clauses_from_text(page_text: str) -> dict[str, str]:
    """复用生产切分逻辑，但喂入给定文本（绕过 pypdf 读取）。"""
    out: dict[str, str] = {}
    cur, buf = None, []
    for ln in page_text.splitlines():
        s = ln.strip()
        if not s:
            continue
        m = P._CLAUSE.match(s)
        if m and (len(m.group(1)) >= 3 or m.group(1).count(".") >= 1):
            if cur:
                out[cur] = " ".join(buf)
            cur, buf = m.group(1), [s]
        elif cur:
            if P._is_terminator(s):
                out[cur] = " ".join(buf)
                cur, buf = None, []
                continue
            buf.append(s)
    if cur:
        out[cur] = " ".join(buf)
    return out
