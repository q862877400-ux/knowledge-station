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
        # ⚠ 两种成因要说得出来（复核 b9 的 INFO-5）：这一份是"压根没有派生文本"
        assert "没有派生文本" in h["why"], h["why"]

    def test_no_chunks_with_text_says_which_cause(self, project, tmp_path):
        """`no_locators` 的**另一种**成因：有派生文本、但切块没产出（INFO-5）。"""
        pid = project["project_id"]
        m = mr.add_material(pid, "零切片材料", origin="user",
                            derived_text_hash="h", parser_fingerprint="kind=.txt;plain=1")
        h = lo.locator_health(mr.get_material(m["material_id"]))
        assert h["status"] == "no_locators", h
        assert "切块没产出" in h["why"], h["why"]
        assert "没有派生文本" not in h["why"], h["why"]

    def test_pdf_cheap_check_refuses_to_claim_ok(self, project, tmp_path, monkeypatch):
        """PDF 的完整指纹含**只有解析后才知道**的 text_layer/ocr ⇒ 便宜比对**不许说 ok**。

        ⚠ 这个 fixture 必须写**真的文件**（2026-09-18 改）：原先给的是不存在的路径，
        于是 MEDIUM-1 修好之后它会先落进"源文件不在"那条分支——**测试还在绿，却不再测它宣称的东西**
        （正是本仓反复强调的"假绿"）。现在先写文件，才真的走到 PDF 前缀比对那一段。
        """
        pid = project["project_id"]
        p = tmp_path / "x.pdf"
        p.write_bytes(b"%PDF-1.4 placeholder")
        m = mr.add_material(pid, "PDF 材料", origin="user", raw_path=str(p),
                            content_hash=mi.file_hash(p),
                            derived_text_hash="h", parser_fingerprint="kind=.pdf;pymupdf=1")
        mr.add_chunks(m["material_id"], [{"text": "甲", "char_start": 0, "char_end": 1}])
        monkeypatch.setattr(lo, "current_fingerprint_for",
                            lambda _m: "kind=.pdf;pymupdf=1")
        h = lo.locator_health(mr.get_material(m["material_id"]))
        assert h["status"] == "unknown", h
        assert "重解析比对" in h["why"], h["why"]


class TestSourceFileIdentity:
    """**输入**这一轴（独立复核 b9 的 MEDIUM-1，2026-09-18 修）。

    只比"解析器指纹"会漏掉整个这一类：指纹是从**后缀**推出来的，所以
    "用户把更新版放回项目目录再扫一次"（**正常操作**）与"源文件被删"都不会让指纹变动。
    旧实现于是在这两种情况下报 `ok`（"未发现变化"）——而本模块的立论正是
    "**看起来很正常的错引用比报错危险得多**"。
    """

    def test_deleted_source_file_is_not_ok(self, project, tmp_path):
        pid = project["project_id"]
        m = mi.ingest_material_file(pid, _txt(tmp_path, "del.txt", "甲。乙。"))
        Path(m["raw_path"]).unlink()          # 材料目录被清理 / 文件被移走
        h = lo.locator_health(mr.get_material(m["material_id"]))
        assert h["status"] == "unknown", h
        assert "源文件不在" in h["why"], h["why"]
        assert h["source_bytes_match"] is None, h

    def test_replaced_source_file_is_stale_not_ok(self, project, tmp_path):
        """换成另一份同名文件 ⇒ `stale`，且**说清是源文件变了**（不是"解析器变了"）。"""
        pid = project["project_id"]
        m = mi.ingest_material_file(pid, _txt(tmp_path, "rep.txt", "甲。乙。"))
        Path(m["raw_path"]).write_text("完全不同的内容。", encoding="utf-8")
        h = lo.locator_health(mr.get_material(m["material_id"]))
        assert h["status"] == "stale", h
        assert h["source_bytes_match"] is False, h
        assert "源文件字节已变" in h["why"], h["why"]
        assert "需要复算" in h["why"], h["why"]

    def test_replaced_pdf_is_stale_not_unknown(self, project, tmp_path, monkeypatch):
        """PDF 也一样：**字节变了就是 stale**，不许因为"指纹前缀相同"停在 unknown。"""
        pid = project["project_id"]
        p = tmp_path / "r.pdf"
        p.write_bytes(b"%PDF-1.4 first")
        m = mr.add_material(pid, "PDF", origin="user", raw_path=str(p),
                            content_hash=mi.file_hash(p),
                            derived_text_hash="h", parser_fingerprint="kind=.pdf;pymupdf=1")
        mr.add_chunks(m["material_id"], [{"text": "甲", "char_start": 0, "char_end": 1}])
        monkeypatch.setattr(lo, "current_fingerprint_for", lambda _m: "kind=.pdf;pymupdf=1")
        assert lo.locator_health(mr.get_material(m["material_id"]))["status"] == "unknown"
        p.write_bytes(b"%PDF-1.4 second")     # 用户把更新版放回同一个文件名
        h = lo.locator_health(mr.get_material(m["material_id"]))
        assert h["status"] == "stale", h
        assert "源文件字节已变" in h["why"], h["why"]

    def test_unchanged_source_still_ok(self, project, tmp_path):
        """**反向对照**：文件真的没变时必须仍然给 `ok`。

        没有这一条，上面三条"不是 ok"的断言可能只是"永远不是 ok"——
        反向对照正是把"判据坏成正/负两个方向"分别钉住。
        """
        pid = project["project_id"]
        m = mi.ingest_material_file(pid, _txt(tmp_path, "same.txt", "甲。乙。"))
        h = lo.locator_health(mr.get_material(m["material_id"]))
        assert h["status"] == "ok", h
        assert h["source_bytes_match"] is True, h

    def test_web_material_has_no_source_axis(self, project):
        """网页件没有源文件 ⇒ 这一轴**不参与**（不是"源文件不在"的告警）。"""
        pid = project["project_id"]
        m = co.collect_text(pid, title="报道", text="住宿八百元。", url="https://a.example/3")
        h = lo.locator_health(mr.get_material(m["material_id"]))
        assert h["status"] == "ok", h
        assert h["source_bytes_match"] is None, h


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

    def test_text_then_blank_reparse_is_a_mismatch(self, project, tmp_path, monkeypatch):
        """入库时**有**文本、现在重解析**一个字都得不到** ⇒ **确定的失效**。

        独立复核 b9 的 MEDIUM-2：原先这条无条件回 `unavailable`（"验不了"），
        而 `unavailable` **不是** health 状态 ⇒ 界面与报告**一个标记都不出**。
        触发场景很真实：存留文件被截断、被换成扫描件、PDF 文本层丢了。
        """
        pid = project["project_id"]
        m = mi.ingest_material_file(pid, _txt(tmp_path, "trunc.txt", "甲。乙。"))
        monkeypatch.setattr(mi, "extract_pages_with_provenance",
                            lambda *a, **kw: ([], "kind=.txt;plain=1"))
        r = lo.reverify_material_locators(m["material_id"])
        assert r["status"] == "mismatch", r
        assert "必然失效" in r["why"], r["why"]

    def test_missing_material_raises(self, db):
        with pytest.raises(ValueError, match="材料不存在"):
            lo.reverify_material_locators("mat_不存在")


class TestProjectSummary:
    def test_one_crashing_material_does_not_kill_the_whole_overview(self, project, tmp_path,
                                                                    monkeypatch):
        """**一份材料的判据挂掉，不该毁掉整个项目总览**（INFO-3 的同型问题，2026-09-18 修）。

        旧写法让异常直接冒出去 ⇒ 端点 500 / 界面把总览失败**静默吞掉**（面板对它
        `.catch(()=>{})`）⇒ 用户看到一份**一个 ⚠ 都没有**的材料列表，读起来像"全部健康"。
        现在：那一份单独标 `health_error`（**不是**健康状态），其余照常给结论。
        """
        pid = project["project_id"]
        good = mi.ingest_material_file(pid, _txt(tmp_path, "ok2.txt", "甲。乙。"))
        bad = mi.ingest_material_file(pid, _txt(tmp_path, "bad2.txt", "丙。丁。"))
        real = lo.locator_health

        def _maybe_boom(m):
            if m["material_id"] == bad["material_id"]:
                raise RuntimeError("模拟判据崩溃")
            return real(m)

        monkeypatch.setattr(lo, "locator_health", _maybe_boom)
        s = lo.project_locator_summary(pid)
        assert s["statuses"][bad["material_id"]] == "health_error", s["statuses"]
        assert s["counts"].get("health_error") == 1, s["counts"]
        assert s["statuses"][good["material_id"]] == "ok", s["statuses"]
        hit = [a for a in s["attention"] if a["material_id"] == bad["material_id"]]
        assert hit and "计算失败" in hit[0]["why"], s["attention"]
        # 取值域本身**不**包含它（`locator_health` 永远不会返回 `health_error`）
        assert "health_error" not in lo.HEALTH_STATUSES
        assert "health_error" in s["note"], s["note"]
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
