# -*- coding: utf-8 -*-
"""图/公式/表图三条**渲染端点**的 HTTP 契约（§10.78 补 §10.75 登记的缺口）。

为什么补：§10.75 把这五条（figure/formula/table-image/tree/assets）从 `async def` 改成 `def`
（丢线程池），其中 `/figure` 由量具真跑出过 200 + PNG，`/assets`、`/tree` 有仓内测试，
而 **`/formula` 与 `/table-image` 一条 HTTP 测试都没有**——"改了但要重新验一遍"这件事
不能靠"形状一样"糊过去。

判据都是**确定性**的（不写"200 或 404 都算过"那种软断言）：
  · `/table-image` **真造一份 middle.json**（schema 简单：`pdf_info[].page_size` +
    `para_blocks[].{type,bbox}`）⇒ 断言 200 + `image/png` + `X-Frac-*` 三个还原头；
  · 无产物 / 越界 / 页不存在 ⇒ 断言**具体错误码**（前端按码隐藏占位，码变了就是破坏契约）；
  · `/formula` ⇒ 断言 `doc_not_found` / `clause_not_found` / `formula_not_found` 三级，
    以及 **缺 `clause` 查询参数 = 422**（它是必填的，FastAPI 直接拒）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

HDR = {"Authorization": "Bearer test-token-123"}
DOC = "doc_render_api"
PAGE_W, PAGE_H = 595.0, 842.0
#: middle.json 里表格的 bbox（MinerU 内部像素坐标；这里直接给"页内中部"一块）
TABLE_BBOX = [100.0, 200.0, 400.0, 500.0]


def _make_pdf(path: Path) -> Path:
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.insert_text((56, 72), "第 1 页 正文（渲染端点契约测试）", fontname="china-s", fontsize=11)
    doc.save(str(path))
    doc.close()
    return path


def _write_middle(data_dir: Path) -> None:
    """写一份最小可用的 middle.json（`parse_out/<doc>/…/x_middle.json`）。"""
    auto = data_dir / "parse_out" / DOC / "mineru" / "bench" / "auto"
    auto.mkdir(parents=True, exist_ok=True)
    (auto / "bench_middle.json").write_text(json.dumps({
        "pdf_info": [{
            "page_idx": 0,
            "page_size": [PAGE_W, PAGE_H],
            "para_blocks": [
                {"type": "table", "bbox": TABLE_BBOX},
                {"type": "interline_equation", "bbox": [120.0, 600.0, 300.0, 640.0]},
            ],
        }],
    }, ensure_ascii=False), encoding="utf-8")


@pytest.fixture()
def render_doc(_isolate_data_dir, db):
    """种一行 doc_meta（指向真 PDF）+ 写 middle.json。"""
    from src.core.storage.sqlite_db import get_db_connection
    from src.core.config import get_settings

    pdf = _make_pdf(get_settings().data_dir / "render_api.pdf")
    conn = get_db_connection()
    conn.execute("DELETE FROM doc_meta WHERE doc_id=?", (DOC,))
    conn.execute("DELETE FROM clause_revision WHERE doc_id=?", (DOC,))
    conn.execute(
        "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (DOC, "GB RENDER-2025", "渲染契约", "RENDER", "r1", "[]", str(pdf), "h_render"))
    conn.execute(
        "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
        " clause_key, clause_number, content_text, content_markdown, page_start, page_end)"
        " VALUES ('cr_render','r1',?,'k_render','4.1','公式：E = mc^2','', 1, 1)", (DOC,))
    conn.commit()
    _write_middle(get_settings().data_dir)
    return pdf


class TestTableImage:
    def test_渲染成功_带比例还原头(self, client, render_doc):
        """有 middle.json + 页码/序号合法 ⇒ 200 + PNG + 三个 X-Frac-* 头。"""
        c, _ = client
        r = c.get(f"/api/v1/documents/{DOC}/table-image/1/0", headers=HDR)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "image/png"
        for h in ("X-Frac-X0", "X-Frac-W", "X-Frac-H"):
            assert h in r.headers, (h, dict(r.headers))
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n", "必须是真 PNG 字节"

    def test_无深度产物_错误码是_table_geo_not_found(self, client, render_doc):
        """删掉 middle.json ⇒ 404 `table_geo_not_found`（前端按码隐藏占位）。"""
        from src.core.config import get_settings
        from src.core import middle_geo
        for p in (get_settings().data_dir / "parse_out" / DOC).rglob("*_middle.json"):
            p.unlink()
        middle_geo._cache.clear()
        c, _ = client
        r = c.get(f"/api/v1/documents/{DOC}/table-image/1/0", headers=HDR)
        assert r.status_code == 404
        assert r.json()["error"] == "table_geo_not_found", r.json()
        _write_middle(get_settings().data_dir)      # 复位，别影响后续用例
        middle_geo._cache.clear()

    def test_序号越界_错误码是_table_not_found(self, client, render_doc):
        c, _ = client
        r = c.get(f"/api/v1/documents/{DOC}/table-image/1/9", headers=HDR)
        assert r.status_code == 404
        assert r.json()["error"] == "table_not_found", r.json()

    def test_未知文档_错误码是_doc_not_found(self, client, render_doc):
        c, _ = client
        r = c.get("/api/v1/documents/doc_nope/table-image/1/0", headers=HDR)
        assert r.status_code == 404
        assert r.json()["error"] == "doc_not_found", r.json()


class TestFormula:
    def test_未知文档(self, client, render_doc):
        c, _ = client
        r = c.get("/api/v1/documents/doc_nope/formula/1?clause=4.1", headers=HDR)
        assert r.status_code == 404
        assert r.json()["error"] == "doc_not_found", r.json()

    def test_条款不存在(self, client, render_doc):
        c, _ = client
        r = c.get(f"/api/v1/documents/{DOC}/formula/1?clause=9.9", headers=HDR)
        assert r.status_code == 404
        assert r.json()["error"] == "clause_not_found", r.json()

    def test_渲染成功_返回_PNG(self, client, render_doc):
        """有 middle.json 的 `interline_equation` 块 ⇒ fno=1 **真的渲染成功**。

        ⚠ 我原本以为这条只能钉"失败契约"（怕造不出稳定命中），实测**能命中**：
        `locate_eq_by_number` 按全局序取第 1 个公式块 ⇒ 200 + PNG。
        所以这条就按**成功**钉（比"200 或 404 都算过"的软断言强得多）。
        """
        c, _ = client
        r = c.get(f"/api/v1/documents/{DOC}/formula/1?clause=4.1", headers=HDR)
        assert r.status_code == 200, r.text[:200]
        assert r.headers["content-type"] == "image/png"
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n", "必须是真 PNG 字节"
        for h in ("X-Frac-X0", "X-Frac-W", "X-Frac-H"):
            assert h in r.headers, (h, dict(r.headers))

    def test_公式序号不存在_错误码是_formula_not_found(self, client, render_doc):
        """不存在的公式序号（99）⇒ 明确 404（前端按码隐藏占位）。"""
        c, _ = client
        r = c.get(f"/api/v1/documents/{DOC}/formula/99?clause=4.1", headers=HDR)
        assert r.status_code == 404, r.text[:200]
        assert r.json()["error"] == "formula_not_found", r.json()

    def test_缺_clause_参数是_422(self, client, render_doc):
        """`clause` 是必填查询参数：漏传应当是 422（不是 500、也不是 200）。"""
        c, _ = client
        r = c.get(f"/api/v1/documents/{DOC}/formula/1", headers=HDR)
        assert r.status_code == 422, r.text
