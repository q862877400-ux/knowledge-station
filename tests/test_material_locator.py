# -*- coding: utf-8 -*-
"""引用**锚点稳定性**测试（`src/core/materials/locator.py`，方案 §12 未决第 5 条）。

守的是**"引用指向的位置还有效吗"能被判定**，而不是"看起来正常"：
  · 入库时记下派生全文哈希 + 解析器指纹；
  · 便宜比对（指纹）只能给 `ok`/`stale`/`unknown`；给 **`ok` 也要说清"未发现变化"
    不等于"保证一致"**；
  · 真正的保证是**重解析比对**（`match`），而它必须在派生文本变了时给 `mismatch`；
  · 网页材料（没有留存源文件）**必须**回 `unavailable`——**不是 ok**；
  · 老材料（NULL）**必须**回 `unknown`——**不假装 ok**。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.core.ingestion import material_ingest as mi
from src.core.materials import collect as co
from src.core.materials import locator as lo
from src.core.storage import material_repo as mr


@pytest.fixture()
def project(db):
    return mr.create_project("锚点稳定性测试")


def _txt(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


class TestIngestRecordsTheProvenance:
    def test_file_material_records_hash_and_fingerprint(self, project, tmp_path):
        """入库必须记下**派生全文哈希 + 解析器指纹**（否则锚点无从判定）。"""
        pid = project["project_id"]
        m = mi.ingest_material_file(pid, _txt(tmp_path, "a.txt", "住宿标准八百元。"))
        assert m["derived_text_hash"], m
        assert m["parser_fingerprint"], m
        assert m["parser_fingerprint"].startswith("kind=.txt"), m["parser_fingerprint"]
        # 不变量：`derived_text_hash` 是**派生全文**（`build_document` 的输出）的哈希
        # ⚠ 对纯文本文件，源字节与派生文本**可能恰好相同**（没有解析变换）⇒ 它与
        #   `content_hash` 相等是**正常**的，不是"记错了"——所以这里断言的是**算法那条不变量**，
        #   而不是"两个哈希必须不同"（那是错的期望）。
        pages = mi.extract_pages(Path(m["raw_path"]))
        text, _spans = mi.build_document(pages)
        assert m["derived_text_hash"] == mi.text_hash(text), m

    def test_web_material_records_the_collect_fingerprint(self, project):
        """网页材料的指纹是**采集通道**那一个（它没有源文件可重解析）。"""
        pid = project["project_id"]
        m = co.collect_text(pid, title="报道", text="住宿标准八百元。",
                            url="https://a.example/1")
        assert m["parser_fingerprint"] == co.COLLECT_PARSER_FINGERPRINT
        assert m["derived_text_hash"] == m["content_hash"], "网页材料的派生文本就是采到的正文"

    def test_no_text_means_no_derived_hash(self, project, tmp_path):
        """解析不出文本 ⇒ `derived_text_hash` 存 **NULL**（不是"空文本的哈希"）。"""
        pid = project["project_id"]
        m = mi.ingest_material_file(pid, _txt(tmp_path, "empty.txt", "   \n  \n"))
        assert m["derived_text_hash"] is None, m
        assert m["parser_fingerprint"], "指纹仍然要有（它记录的是'解析过'这件事）"


class TestCheapHealth:
    def test_untouched_material_is_ok_but_the_wording_is_honest(self, project, tmp_path):
        pid = project["project_id"]
        m = mi.ingest_material_file(pid, _txt(tmp_path, "b.txt", "甲。乙。丙。"))
        h = lo.locator_health(m)
        assert h["status"] == "ok", h
        assert "未发现变化" in h["why"] and "保证" in h["why"], h["why"]

    def test_old_material_without_provenance_is_unknown_not_ok(self, project, tmp_path):
        """2026-09-17 之前的材料没有这两列 ⇒ **unknown**（不假装 ok）。"""
        pid = project["project_id"]
        m = mr.add_material(pid, "老材料", origin="user")       # 不传 provenance
        mr.add_chunks(m["material_id"], [{"text": "甲", "char_start": 0, "char_end": 1}])
        h = lo.locator_health(mr.get_material(m["material_id"]))
        assert h["status"] == "unknown", h
        assert "不知道" in h["why"], h["why"]

    def test_changed_fingerprint_is_stale(self, project, tmp_path, monkeypatch):
        """指纹变了 ⇒ `stale`（**不是**"已经坏了"——要说清要复算）。"""
        pid = project["project_id"]
        m = mi.ingest_material_file(pid, _txt(tmp_path, "c.txt", "甲。"))
        monkeypatch.setattr(mi, "_provenance_fingerprint",
                            lambda *a, **kw: "kind=.txt;plain=2")
        h = lo.locator_health(mr.get_material(m["material_id"]))
        assert h["status"] == "stale", h
        assert "需要复算" in h["why"] and "不代表一定坏" in h["why"], h["why"]

    def test_no_chunks_means_no_locators(self, project, tmp_path):
        pid = project["project_id"]
        m = mi.ingest_material_file(pid, _txt(tmp_path, "empty2.txt", ""))
        h = lo.locator_health(m)
        assert h["status"] == "no_locators", h

    def test_pdf_cheap_check_refuses_to_claim_ok(self, project, tmp_path, monkeypatch):
        """PDF 的完整指纹含**只有解析后才知道**的 text_layer/ocr ⇒ 便宜比对**不许说 ok**。"""
        pid = project["project_id"]
        m = mr.add_material(pid, "PDF 材料", origin="user", raw_path=str(tmp_path / "x.pdf"),
                            derived_text_hash="h", parser_fingerprint="kind=.pdf;pymupdf=1")
        mr.add_chunks(m["material_id"], [{"text": "甲", "char_start": 0, "char_end": 1}])
        monkeypatch.setattr(lo, "current_fingerprint_for",
                            lambda _m: "kind=.pdf;pymupdf=1")
        h = lo.locator_health(mr.get_material(m["material_id"]))
        assert h["status"] == "unknown", h
        assert "重解析比对" in h["why"], h["why"]


class TestStrongReverify:
    def test_unchanged_source_matches(self, project, tmp_path):
        """源文件没变 ⇒ 重解析**逐字节一致**（这才是真正的保证）。"""
        pid = project["project_id"]
        m = mi.ingest_material_file(pid, _txt(tmp_path, "d.txt", "甲。乙。丙。"))
        r = lo.reverify_material_locators(m["material_id"])
        assert r["status"] == "match", r
        assert r["recomputed"] == r["recorded"]

    def test_changed_parser_output_is_a_mismatch(self, project, tmp_path, monkeypatch):
        """**解析器变了**（模拟：重解析得到不同文本）⇒ `mismatch`，且措辞点明"区间已失效"。"""
        pid = project["project_id"]
        m = mi.ingest_material_file(pid, _txt(tmp_path, "e.txt", "甲。乙。"))
        # 模拟"换了解析器"：重解析时给出的文本不同（真实场景是 fitz/MinerU 版本变化）
        monkeypatch.setattr(mi, "extract_pages_with_provenance",
                            lambda *a, **kw: ([(1, "甲。乙丙。")], "kind=.txt;plain=1"))
        r = lo.reverify_material_locators(m["material_id"])
        assert r["status"] == "mismatch", r
        assert "已失效" in r["why"], r["why"]

    def test_web_material_cannot_be_reverified(self, project):
        """没有留存源文件 ⇒ `unavailable`（**不是 ok**）。"""
        pid = project["project_id"]
        m = co.collect_text(pid, title="报道", text="住宿八百元。",
                            url="https://a.example/2")
        r = lo.reverify_material_locators(m["material_id"])
        assert r["status"] == "unavailable", r
        assert "不是 ok" in r["why"], r["why"]

    def test_missing_material_raises(self, db):
        with pytest.raises(ValueError, match="材料不存在"):
            lo.reverify_material_locators("mat_不存在")


class TestProjectSummary:
    def test_counts_and_attention_list(self, project, tmp_path):
        pid = project["project_id"]
        mi.ingest_material_file(pid, _txt(tmp_path, "f.txt", "甲。"))
        old = mr.add_material(pid, "老材料", origin="user")
        mr.add_chunks(old["material_id"], [{"text": "甲", "char_start": 0, "char_end": 1}])
        s = lo.project_locator_summary(pid)
        assert s["counts"]["ok"] == 1 and s["counts"]["unknown"] == 1, s["counts"]
        assert any(a["material_id"] == old["material_id"] for a in s["attention"]), s["attention"]
        assert "重解析比对" in s["note"], s["note"]


def test_bootstrap_guarantees_the_material_columns():
    """**引导契约**：`init_schema()` + 两个 ensure 之后，两张表的追加列都在。

    为什么要有这条：`schema.sql` 只是 `CREATE TABLE IF NOT EXISTS`，
    **老库**不会长出新列（材料表这两列就是本步新加的）。
    """
    from src.core.storage.sqlite_db import get_db_connection, init_schema
    from src.core.storage.clause_repo import ensure_additive_columns
    from src.core.storage.material_repo import ensure_additive_columns as ensure_mat

    if True:  # 与本文件其它用例同一个会话库；ensure 是幂等的
        init_schema()
        ensure_additive_columns()
        ensure_mat()
    conn = get_db_connection()
    have = {r[1] for r in conn.execute("PRAGMA table_info(material)").fetchall()}
    assert {"derived_text_hash", "parser_fingerprint"} <= have, sorted(have)
