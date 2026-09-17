# -*- coding: utf-8 -*-
"""材料解析与切片测试（Phase A 第二步）。

最关键的一条是**保真不变量**：每块的 `char_start/char_end` 在规范全文上必须**逐字**取回
该块文本（`text[start:end] == chunk["text"]`）。因为"引用能点回原文位置"完全建立在这个
契约上——区间一旦对不上，引用就是假的。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.core.ingestion import material_ingest as mi
from src.core.storage import material_repo as mr


@pytest.fixture()
def project(db):
    return mr.create_project("材料测试")


def _make_txt(p: Path, body: str) -> Path:
    p.write_text(body, encoding="utf-8")
    return p


def _make_docx(p: Path, paras: list[str]) -> Path:
    from docx import Document
    d = Document()
    for t in paras:
        d.add_paragraph(t)
    d.save(str(p))
    return p


def _make_pdf(p: Path, pages: list[str]) -> Path:
    import fitz
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 100), text, fontname="china-s", fontsize=12)
    doc.save(str(p))
    doc.close()
    return p


# ------------------------------------------------------------------ 切片算法
class TestChunking:
    def test_offsets_round_trip_exactly(self):
        """**保真不变量（最强口径）**：全文[块.start:块.end] **逐字**等于块文本。

        不用 `.strip()` 兜底——区间必须**收紧到实际内容**，否则"引用点回原文"会有偏差。
        """
        text = ("第一段：营业收入 100 亿元。\n"
                "第二段：净利润 10 亿元。\n"
                "\n"
                "第三段：风险提示若干。\n")
        spans = [(0, len(text), 1)]
        chunks = mi.chunk_text(text, spans, max_chars=40)
        assert chunks, "应至少切出一块"
        for c in chunks:
            assert text[c["char_start"]:c["char_end"]] == c["text"]

    def test_chunk_spanning_blank_line_keeps_original_separators(self):
        """跨空行/跨页的块必须**原样保留**原文分隔符（2026-09-17 被验收测试抓到的 bug：
        原先用 `"\\n".join(行)` 重建，把页间的 `"\\n\\n"` 压成了 `"\\n"` ⇒ 区间对不上）。"""
        text = "甲段\n\n乙段"
        chunks = mi.chunk_text(text, [(0, len(text), 1)], max_chars=1000)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text            # 含空行本身
        assert text[chunks[0]["char_start"]:chunks[0]["char_end"]] == chunks[0]["text"]

    def test_short_lines_pack_into_one_chunk(self):
        text = "\n".join(f"第{i}行内容" for i in range(5))
        chunks = mi.chunk_text(text, [(0, len(text), 1)], max_chars=1000)
        assert len(chunks) == 1

    def test_max_chars_splits(self):
        text = "\n".join(f"这是第{i}行的内容，占一些字数" for i in range(40))
        chunks = mi.chunk_text(text, [(0, len(text), 1)], max_chars=60)
        assert len(chunks) > 1
        for c in chunks:
            # 允许单行本身超限时硬切的段，故只断言"没有把多段无脑堆到远超上限"
            assert len(c["text"]) <= max(60, len(max(text.split("\n"), key=len)))
            assert text[c["char_start"]:c["char_end"]] == c["text"]

    def test_overlong_single_line_is_hard_split(self):
        text = "甲" * 250
        chunks = mi.chunk_text(text, [(0, len(text), 1)], max_chars=100)
        assert len(chunks) == 3
        assert "".join(c["text"] for c in chunks) == text
        for c in chunks:
            assert text[c["char_start"]:c["char_end"]] == c["text"]

    def test_blank_text_yields_nothing(self):
        assert mi.chunk_text("   \n\n  ", [(0, 7, 1)]) == []

    def test_page_mapping(self):
        pages = [(1, "甲" * 30), (2, "乙" * 30)]
        text, spans = mi.build_document(pages)
        # 第 2 页文本的起点应落在第 2 页区间内
        second_start = spans[1][0]
        assert mi.page_of(second_start, spans) == 2
        assert mi.page_of(0, spans) == 1
        assert mi.page_of(10, spans) == 1

    def test_build_document_spans_self_consistent(self):
        pages = [(1, "aaa"), (3, "bbbb")]
        text, spans = mi.build_document(pages)
        for start, end, page in spans:
            assert text[start:end]  # 区间内确有内容
        assert text == "aaa\n\nbbbb"


# ------------------------------------------------------------------ 解析各格式
class TestExtract:
    def test_txt(self, tmp_path):
        p = _make_txt(tmp_path / "a.txt", "第一行\n第二行")
        assert mi.extract_pages(p) == [(1, "第一行\n第二行")]

    def test_docx_is_page_1(self, tmp_path):
        p = _make_docx(tmp_path / "a.docx", ["段落一", "段落二"])
        pages = mi.extract_pages(p)
        assert len(pages) == 1 and pages[0][0] == 1     # docx 没有页概念，不许编造
        assert "段落一" in pages[0][1] and "段落二" in pages[0][1]

    def test_pdf_keeps_page_numbers(self, tmp_path):
        p = _make_pdf(tmp_path / "a.pdf", ["Page one text", "Page two text"])
        pages = mi.extract_pages(p)
        assert [n for n, _ in pages] == [1, 2]

    def test_empty_txt_gives_no_pages(self, tmp_path):
        p = _make_txt(tmp_path / "empty.txt", "   \n  ")
        assert mi.extract_pages(p) == []


# ------------------------------------------------------------------ 收件入库
class TestIngest:
    def test_txt_becomes_pending_material_with_offsets(self, project, tmp_path):
        p = _make_txt(tmp_path / "财报摘要.txt", "营业收入 100 亿元\n净利润 10 亿元")
        m = mi.ingest_material_file(project["project_id"], p)
        assert m["review_status"] == "pending"          # 硬门前提
        assert m["origin"] == "user"
        assert m["source_tier"] == "T1"                 # 用户自有原件
        assert m["chunk_count"] >= 1
        # 切片的区间必须能在**材料全文**上取回（材料全文由 raw_path 重新解析得到）
        pages = mi.extract_pages(Path(m["raw_path"]))
        text, spans = mi.build_document(pages)
        for c in mr.material_chunks(m["material_id"]):
            assert text[c["char_start"]:c["char_end"]] == c["text"]

    def test_title_strips_duplicate_suffix(self, project, tmp_path):
        p = _make_txt(tmp_path / "年报(1).txt", "内容")
        m = mi.ingest_material_file(project["project_id"], p)
        assert m["title"] == "年报"

    def test_duplicate_content_is_not_registered_twice(self, project, tmp_path):
        body = "同一份材料的内容"
        a = _make_txt(tmp_path / "x.txt", body)
        b = _make_txt(tmp_path / "y.txt", body)
        m1 = mi.ingest_material_file(project["project_id"], a)
        m2 = mi.ingest_material_file(project["project_id"], b)
        assert m2["duplicate"] is True
        assert m2["material_id"] == m1["material_id"]
        assert len(mr.list_materials(project["project_id"])) == 1

    def test_file_outside_project_dir_is_copied_in(self, project, tmp_path):
        """材料平面要自包含：外面来的文件复制进项目目录（独立存储）。"""
        p = _make_txt(tmp_path / "外部.txt", "外部内容")
        m = mi.ingest_material_file(project["project_id"], p)
        stored = Path(m["raw_path"])
        assert stored.parent == mr.materials_dir(project["project_id"])
        assert stored.exists()

    def test_file_already_in_project_dir_is_referenced_in_place(self, project):
        d = mr.materials_dir(project["project_id"])
        p = _make_txt(d / "已就位.txt", "就位内容")
        m = mi.ingest_material_file(project["project_id"], p)
        assert Path(m["raw_path"]) == p

    def test_unparsable_pdf_is_registered_but_flagged(self, project, tmp_path):
        """扫描件（无文本层）：**仍登记**（用户得看得见），但如实说明没解析出文本。

        不许假装可用，也不许把它悄悄丢掉——两种情况都会让用户以为"我放进去了"。
        """
        import fitz
        doc = fitz.open()
        doc.new_page()          # 空白页 = 无文本层
        p = tmp_path / "扫描件.pdf"
        doc.save(str(p))
        doc.close()
        m = mi.ingest_material_file(project["project_id"], p, deep_fallback=False)
        assert m["chunk_count"] == 0
        assert "扫描件" in (m["tier_reason"] or "")

    def test_unsupported_suffix_rejected(self, project, tmp_path):
        p = tmp_path / "x.bin"
        p.write_bytes(b"\x00\x01")
        with pytest.raises(ValueError):
            mi.ingest_material_file(project["project_id"], p)

    def test_project_dir_ingest_is_batch_and_ok(self, project):
        d = mr.materials_dir(project["project_id"])
        _make_txt(d / "a.txt", "内容甲")
        _make_txt(d / "b.md", "内容乙")
        _make_docx(d / "c.docx", ["内容丙"])
        out = mi.ingest_project_dir(project["project_id"])
        assert len(out) == 3
        assert all(o.get("status") != "error" for o in out)
        assert len(mr.list_materials(project["project_id"])) == 3

    def test_scan_is_stable_and_filtered(self, project):
        d = mr.materials_dir(project["project_id"])
        _make_txt(d / "b.txt", "b")
        _make_txt(d / "a.txt", "a")
        (d / "ignore.bin").write_bytes(b"x")
        names = [p.name for p in mi.scan_project_dir(project["project_id"])]
        assert names == ["a.txt", "b.txt"]

    def test_ingested_material_is_not_usable_until_approved(self, project, tmp_path):
        """端到端串一遍硬门：收件 → 仍是 pending → 批准后才进 approved_materials。"""
        d = mr.materials_dir(project["project_id"])
        _make_txt(d / "m.txt", "内容")
        mi.ingest_project_dir(project["project_id"])
        pid = project["project_id"]
        assert mr.approved_materials(pid) == []          # 未经评审不得使用
        m = mr.list_materials(pid)[0]
        mr.set_review(m["material_id"], "approved", note="看过")
        assert [x["material_id"] for x in mr.approved_materials(pid)] == [m["material_id"]]


# ------------------------------------------------------------------ Phase A 验收
class TestPhaseAAcceptance:
    """方案 §9 的 Phase A 验收：**放一份 PDF → 评审通过 → 提问 → 引用能点回该 PDF 的位置**。

    这条把"平面"的四个部件串起来跑一遍（收件 → 切片 → 评审硬门 → 检索 → 引用字段），
    并逐字验证"点回原文"是真的：用引用里的 `char_start/char_end` 在**重新解析出的全文**上
    取回文本，必须与命中切片一致；`page` 必须落在该 PDF 的真实页上。
    """

    def test_pdf_gate_search_and_citation_point_back(self, project):
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        _make_pdf(d / "年度报告.pdf", ["营业收入为一百亿元", "净利润为十亿元"])

        # ① 收件：进材料平面，默认 pending
        ingested = mi.ingest_project_dir(pid)
        # 成功项不带 "status" 键（只有失败项才有 status="error"）——故用 .get
        assert len(ingested) == 1 and ingested[0].get("status") != "error"
        mid = ingested[0]["material_id"]
        assert mr.approved_materials(pid) == []

        # ② 未批准时**搜不到**（硬门）
        assert mr.search_materials(pid, "营业收入") == []

        # ③ 评审通过
        assert mr.set_review(mid, "approved", note="核对过原件")

        # ④ 提问式检索：能命中，且字段足够标注
        hits = mr.search_materials(pid, "营业收入")
        assert hits, "批准后应能检索到"
        h = hits[0]
        assert h["material_id"] == mid
        assert h["title"] == "年度报告"
        assert h["page"] == 1                       # 该 PDF 第 1 页
        assert h["tier_label"] == mr.TIER_LABELS["T1"]

        # ⑤ **点回原文位置是真的**：用引用区间在重新解析的全文上取回同一段文本
        pages = mi.extract_pages(Path(mr.get_material(mid)["raw_path"]))
        text, spans = mi.build_document(pages)
        assert text[h["char_start"]:h["char_end"]].strip() == h["text"]
        assert mi.page_of(h["char_start"], spans) == h["page"]

    def test_scan_pdf_needs_explicit_deep_and_is_flagged(self, project):
        """扫描件（无文本层）在**默认不外发**下拿不到内容 —— 但材料仍登记并如实标注。

        这就是"既不假装可用、也不悄悄丢掉"的端到端体现。
        """
        import fitz
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        doc = fitz.open()
        doc.new_page()
        doc.save(str(d / "扫描件.pdf"))
        doc.close()
        out = mi.ingest_project_dir(pid)[0]
        assert out["chunk_count"] == 0
        assert "扫描件" in (out["tier_reason"] or "")
        mr.set_review(out["material_id"], "approved")
        # 没有切片 ⇒ 即使批准了也搜不到内容（不是把空内容当依据）
        assert mr.search_materials(pid, "营业收入") == []

