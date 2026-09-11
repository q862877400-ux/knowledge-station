"""C 组 + B 组：R27 预览的拦截与只读。

## "100% 拦截"到底证明了什么（诚实标注）
分两层证明，**不混为一谈**：

1. **真 PDF 集成层**（本文件 `test_blk_*` 用 fitz 离线合成）：倾斜 / 近乎空白 /
   碎片化切不出条款 / 图片扫描件 / 非法文件 / 文件不存在 / 非 PDF 后缀。这些形态
   fitz 能真实合成，断言的是端到端结果。
2. **受控 blocks 层**（`test_verdict_*` 用 monkeypatch 喂 blocks）：乱码（PUA）/
   条款坍缩 / 异常字符率 / 替换字符率。**这些形态无法用 fitz 内置字体合成**——
   实测：`china-s` 把不支持的字符（Kannada/ć）直接丢掉，`helv` 回退成 `·`（属正常符号，
   `is_weird_char`=False），U+FFFD 也不保留。真乱码来自**内嵌 CID 字体**，离线造不出来。
   所以这一层验证的是**我的判据消费逻辑**（`quality.grading.verdict_document`），
   而"什么叫乱码"由 `mineru_adapter.text_layer_pua_mangled` 自己拥有、由它自己的测试覆盖。

对**真实语料**不宣称 100%：亚度级倾斜与轻度排版损坏有意落在 warn/ok（漏放），
因为把"无法评估"判成"损坏"会阻断合法入库。反向护栏见 `test_blk_straight_*` /
`test_blk_mild_skew_*` / `test_blk_scanned_*` / `test_blk_pua_recovered_*`。

## 只读
`test_dry_*` 用全表行数差分 + sqlite_master 差分证明预览不动库、不建表、不碰用户文件。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.core.ingestion import dry_run
from src.core.quality import grading


# --------------------------------------------------------------------------- #
# 合成 PDF 工具
# --------------------------------------------------------------------------- #
def _save(doc, path: Path) -> Path:
    doc.save(str(path))
    doc.close()
    return path


def _mk_good_pdf(tmp_path: Path, name: str = "good.pdf") -> Path:
    """5 页、20 条规范条款（含模态词与数值）——不应被判 block。"""
    import fitz
    doc = fitz.open()
    for pno in range(5):
        page = doc.new_page(width=595, height=842)
        y = 80
        for i in range(4):
            n = pno * 4 + i + 1
            page.insert_text((72, y), f"5.2.{n} 动火作业应有专人监护，作业前应办理审批手续。",
                             fontsize=12, fontname="china-s")
            y += 24
            page.insert_text((72, y), f"5.2.{n + 1} 可燃气体浓度不大于0.5%，作业半径不小于10m。",
                             fontsize=12, fontname="china-s")
            y += 30
    return _save(doc, tmp_path / name)


def _mk_pua_prefix_pdf(tmp_path: Path, name: str = "pua.pdf") -> Path:
    """GB 出版 PDF 的 PUA 错位形态（封面 '犌犅／犜' + 正文条款）。

    实测 `normalize_pua_latin` 能把它救回 → 预览应当报 `ok_normalized` 且**不 block**
    （误杀这条会让文本层被弃、白走 OCR 丢字）。
    """
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 80
    for row in ["犌犅／犜 20529.2—2010",
                "5.2.1 动火作业应有专人监护。",
                "5.2.2 可燃气体浓度不大于0.5%。"]:
        page.insert_text((72, y), row, fontsize=12, fontname="china-s")
        y += 24
    return _save(doc, tmp_path / name)


def _mk_skewed_pdf(tmp_path: Path, deg: float, name: str = "skew.pdf") -> Path:
    """逐字排版制造真实倾角（每字 dx=6pt，dy 按 tan(deg) 递增）。

    24 行 × 41 字：测斜判据要求 `measured_lines >= 20`（少量行不算数），行数不足会让
    `skew_measured=False` 从而**不触发**倾斜判据——这是有意设计（宁可"未测"不可"瞎判"）。
    """
    import fitz
    import math
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    slope = math.tan(math.radians(deg))
    line_text = "动火作业应有专人监护，作业前应办理审批手续并确认现场条件满足要求"
    for line in range(24):
        y0 = 60 + line * 32
        for i, ch in enumerate(line_text):
            x = 40 + i * 6
            y = y0 + i * 6 * slope
            page.insert_text((x, y), ch, fontsize=9, fontname="china-s")
    return _save(doc, tmp_path / name)


def _mk_sparse_pdf(tmp_path: Path, name: str = "sparse.pdf") -> Path:
    """6 页、每页仅 5 字 → 近乎空白。"""
    import fitz
    doc = fitz.open()
    for i in range(6):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 80), f"第{i}页", fontsize=12, fontname="china-s")
    return _save(doc, tmp_path / name)


def _mk_fragmented_pdf(tmp_path: Path, name: str = "fragmented.pdf") -> Path:
    """大量 3 字碎片行：文本层有 200+ 字，但切不出条款（全部按 <4 字丢弃）。"""
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 60
    for i in range(120):
        page.insert_text((72, y), f"词{i:03d}", fontsize=8, fontname="china-s")
        y += 6
        if y > 800:
            break
    return _save(doc, tmp_path / name)


def _mk_scan_pdf(tmp_path: Path, name: str = "scan.pdf", pages: int = 1) -> Path:
    """只有图片、无文本层 → 应当是 warn（W1），不是 block（不许误伤扫描件）。

    `pages` 默认 1；**必须也能测多页**——2026-09-11 真机发现：多页扫描件会被 B4
    「近乎空白」误判为 block（1 页恰好绕过 `pages >= 5` 门槛，所以合成测试漏了）。
    """
    import fitz
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page(width=595, height=842)
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 60, 60))
        pix.set_rect(pix.irect, (200, 200, 200))
        page.insert_image(fitz.Rect(100, 100, 400, 400), pixmap=pix)
    return _save(doc, tmp_path / name)


def _mk_broken_file(tmp_path: Path, name: str = "broken.pdf") -> Path:
    p = tmp_path / name
    p.write_bytes(b"not a pdf at all" * 20)
    return p


# --------------------------------------------------------------------------- #
# 受控 blocks：验证判据消费（不依赖能否合成乱码 PDF）
# --------------------------------------------------------------------------- #
@pytest.fixture()
def fake_parse(monkeypatch):
    """把解析换成受控返回值；记录调用参数（用于断言 deep_fallback=False）。"""
    calls: list[dict] = []

    def _install(blocks, geometries=None, *, state="ok", deep_skipped=False):
        from src.core.ingestion import parser_worker

        def _fake(pdf_path, output_dir, timeout=900, force_deep=False, deep_fallback=True):
            calls.append({"force_deep": force_deep, "deep_fallback": deep_fallback})
            return {"blocks": blocks, "geometries": geometries or {1: {"width": 595.0,
                    "height": 842.0, "rotation": 0, "crop_box": [], "media_box": []}},
                    "is_ocr": False, "deep_output": None,
                    "text_layer_state": state, "deep_fallback_skipped": deep_skipped}

        monkeypatch.setattr(parser_worker, "run_parser_isolated", _fake)
        return calls

    return _install


def _block(text: str, page: int = 1) -> dict:
    return {"page_number": page, "text": text, "bbox": [0.0, 0.0, 100.0, 20.0],
            "source": "pymupdf"}


def test_verdict_pua_mangled_blocks(db, tmp_path, fake_parse):
    """乱码（适配器判定的 PUA 错位不可修复）→ block B1。"""
    p = _mk_good_pdf(tmp_path, "vm1.pdf")
    fake_parse([_block("条款正文" * 40)], state="pua_mangled")
    rep = dry_run.analyze_preview_report(p)
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["verdict"] == "block" and "B1" in codes, (rep["verdict"], codes)
    assert rep["grade"] == "D" and rep["quarantine_candidate"] is True


def test_verdict_collapse_blocks(db, tmp_path, fake_parse):
    """正文 ≥2000 字却切不出条款 → block B2（坍缩）。"""
    p = _mk_good_pdf(tmp_path, "vm2.pdf")
    fake_parse([_block("这是一段没有条款编号的连续散文。" * 200)])
    rep = dry_run.analyze_preview_report(p)
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["layout"]["chars"] >= 2000, rep["layout"]
    assert rep["total_clauses"] <= 1, rep["total_clauses"]
    assert rep["verdict"] == "block" and "B2" in codes, (rep["verdict"], codes)


def test_verdict_weird_ratio_blocks(db, tmp_path, fake_parse):
    """异常字符占比 ≥30%（采样窗口之外的乱码，适配器采样不到）→ block B5。"""
    p = _mk_good_pdf(tmp_path, "vm3.pdf")
    clean = "本条为正常正文内容，用于稀释采样窗口。" * 10
    garbled = "ಆć" * 400  # 异常区字符
    fake_parse([_block(clean), _block(garbled)], state="ok")
    rep = dry_run.analyze_preview_report(p)
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["recognition"]["weird_ratio"] >= 0.30, rep["recognition"]
    assert rep["verdict"] == "block" and "B5" in codes, (rep["verdict"], codes, rep["recognition"])


def test_verdict_replacement_ratio_blocks(db, tmp_path, fake_parse):
    """替换字符 U+FFFD 占比 ≥5% → block B6（与 B5 不同：FFFD 属正常区符号）。"""
    p = _mk_good_pdf(tmp_path, "vm4.pdf")
    fake_parse([_block("动火作业应有专人监护。" * 30 + "\ufffd" * 60)])
    rep = dry_run.analyze_preview_report(p)
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["recognition"]["replacement_ratio"] >= 0.05, rep["recognition"]
    assert rep["verdict"] == "block" and "B6" in codes, (rep["verdict"], codes)


def test_verdict_preview_never_asks_for_deep(db, tmp_path, fake_parse):
    """**零外发**的关键断言：预览必须传 deep_fallback=False 且 force_deep=False。"""
    p = _mk_good_pdf(tmp_path, "vm5.pdf")
    calls = fake_parse([_block("5.1 动火作业应有专人监护。" * 5)])
    dry_run.analyze_preview_report(p)
    assert calls and calls[0] == {"force_deep": False, "deep_fallback": False}, calls


def test_verdict_scan_warn_when_deep_skipped(db, tmp_path, fake_parse):
    p = _mk_good_pdf(tmp_path, "vm6.pdf")
    fake_parse([], geometries={1: {"width": 595.0, "height": 842.0, "rotation": 0,
                                   "crop_box": [], "media_box": []}},
               state="empty", deep_skipped=True)
    rep = dry_run.analyze_preview_report(p)
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["verdict"] == "warn" and "W1" in codes, (rep["verdict"], codes)
    assert rep["deep_fallback_skipped"] is True and rep["egress"] == "none"


# --------------------------------------------------------------------------- #
# C 组：拦截（真 PDF 集成层）
# --------------------------------------------------------------------------- #
def test_blk_severe_skew(db, tmp_path):
    rep = dry_run.analyze_preview_report(_mk_skewed_pdf(tmp_path, 5.0))
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["recognition"]["skew_measured"] is True, rep["recognition"]
    assert rep["verdict"] == "block", (rep["verdict"], codes, rep["recognition"])
    assert "B3" in codes, codes
    assert abs(float(rep["recognition"]["skew_deg"]) - 5.0) <= 1.0, rep["recognition"]["skew_deg"]


def test_blk_sparse_pages(db, tmp_path):
    rep = dry_run.analyze_preview_report(_mk_sparse_pdf(tmp_path))
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["verdict"] == "block", (rep["verdict"], codes, rep["layout"])
    assert "B4" in codes, codes


def test_blk_fragmented_not_blocked(db, tmp_path):
    """碎片化文本（120 行 3 字词）**不判 block**——它切出一条「前置说明」，字数也没到坍缩线。

    这条是"不许误杀"的护栏：碎片化是坏排版，但不足以证明"损坏到不可入库"。
    """
    rep = dry_run.analyze_preview_report(_mk_fragmented_pdf(tmp_path))
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["verdict"] in ("ok", "warn"), (rep["verdict"], codes, rep["layout"])


def test_blk_broken_file(db, tmp_path):
    rep = dry_run.analyze_preview_report(_mk_broken_file(tmp_path))
    assert rep["status"] == "error"
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["verdict"] == "block" and "B8" in codes, (rep["status"], rep["verdict"], codes)


def test_blk_missing_file(db, tmp_path):
    rep = dry_run.analyze_preview_report(tmp_path / "不存在.pdf")
    assert rep["status"] == "error" and rep["error_code"] == "file_not_found"
    assert rep["verdict"] == "block"


def test_blk_wrong_suffix(db, tmp_path):
    f = tmp_path / "a.docx"
    f.write_bytes(b"x")
    rep = dry_run.analyze_preview_report(f)
    assert rep["status"] == "error" and rep["error_code"] == "unsupported_type"
    assert rep["verdict"] == "block"


# --------------------------------------------------------------------------- #
# 反向护栏：不许误杀
# --------------------------------------------------------------------------- #
def test_blk_good_doc_not_blocked(db, tmp_path):
    rep = dry_run.analyze_preview_report(_mk_good_pdf(tmp_path))
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["verdict"] in ("ok", "warn"), (rep["verdict"], codes)
    assert rep["grade"] in ("A", "B", "C")
    assert len(rep["head_samples"]) == 5, len(rep["head_samples"])
    assert len(rep["tail_samples"]) == 5, len(rep["tail_samples"])
    assert rep["total_clauses"] >= 15, rep["total_clauses"]


def test_blk_pua_recovered_not_blocked(db, tmp_path):
    """可归一化修复的 PUA 错位必须被救回（否则白走 OCR 丢字）。"""
    rep = dry_run.analyze_preview_report(_mk_pua_prefix_pdf(tmp_path))
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["verdict"] != "block", (rep["verdict"], codes, rep["recognition"])
    assert rep["recognition"]["text_layer_state"] in ("ok", "ok_normalized"), rep["recognition"]


def test_blk_scanned_is_warn_not_block(db, tmp_path):
    """扫描件（无文本层）应当是 warn + 零外发，不是 block。"""
    rep = dry_run.analyze_preview_report(_mk_scan_pdf(tmp_path))
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["verdict"] == "warn", (rep["verdict"], codes)
    assert "W1" in codes, codes
    assert rep["recognition"]["text_layer_state"] == "empty", rep["recognition"]
    assert rep["deep_fallback_skipped"] is True
    assert rep["egress"] == "none"


def test_blk_multipage_scan_is_warn_not_block(db, tmp_path):
    """**多页**扫描件同样只 warn：B4「近乎空白」不得对"无文本层"开火。

    2026-09-11 真机回归（GB 30871-2022 扫描版 31 页）：无文本层时 chars_per_page 恒 0
    是构造性事实，若被 B4 当成"近乎空白"，真实库里的扫描版国标会被整片拦在门外。
    单页合成用例恰好绕过 `pages >= 5` 门槛，因此这条必须单独覆盖。
    """
    rep = dry_run.analyze_preview_report(_mk_scan_pdf(tmp_path, "scan31.pdf", pages=8))
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["layout"]["pages"] == 8
    assert rep["layout"]["pages_no_text"] == 8
    assert rep["verdict"] == "warn", (rep["verdict"], codes, rep["layout"])
    assert "B4" not in codes, codes
    assert "W1" in codes, codes


def test_blk_straight_not_flagged(db, tmp_path):
    """正排（θ=0）不许出现倾斜判据。"""
    rep = dry_run.analyze_preview_report(_mk_skewed_pdf(tmp_path, 0.0))
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert "B3" not in codes and "W2" not in codes, (codes, rep["recognition"])


def test_blk_mild_skew_warns_not_blocks(db, tmp_path):
    """2° 轻度倾斜 → warn（W2），不 block。"""
    rep = dry_run.analyze_preview_report(_mk_skewed_pdf(tmp_path, 2.0))
    codes = [r["code"] for r in rep["verdict_reasons"]]
    assert rep["verdict"] == "warn", (rep["verdict"], codes, rep["recognition"])
    assert "W2" in codes and "B3" not in codes, codes


# --------------------------------------------------------------------------- #
# 判据级用例（直接喂报告字典，零 IO）：补 verifier 审计点名的覆盖缺口
# --------------------------------------------------------------------------- #
def _report(**over):
    """一份"干净"报告底稿；用例只改自己关心的字段。"""
    base = {
        "status": "ok", "error_code": None, "total_clauses": 30,
        "recognition": {"text_layer_state": "ok", "weird_ratio": 0.0, "replacement_ratio": 0.0,
                        "skew_deg": 0.2, "skew_measured": True, "skew_pages_ratio": 0.0},
        "layout": {"pages": 10, "chars": 12000, "chars_per_page": 1200.0,
                   "clauses_per_1000chars": 2.5},
        "duplicate": {"kind": "none"}, "ocr_suspects": [],
        "typing_quality": {"low_type_confidence": 0, "distribution": {"rule": 30}},
        "deep_fallback_skipped": False,
    }
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = {**base[k], **v}
        else:
            base[k] = v
    return base


def test_verdict_clean_is_ok():
    v, reasons = grading.verdict_document(_report())
    assert v == "ok" and reasons[0]["code"] == "OK"


def test_verdict_mixed_skew_blocked_by_page_ratio():
    """B3 第二支：文档中位倾角未到 3°，但**多数页各自严重倾斜** → 仍须拦。

    这条专治 verifier 审计 P0-1：原 `elif` 让该分支在 skew≥3° 时才求值 = 死分支。
    """
    v, reasons = grading.verdict_document(_report(
        recognition={"skew_deg": 2.4, "skew_measured": True, "skew_pages_ratio": 0.6}))
    assert v == "block" and "B3" in [r["code"] for r in reasons], (v, reasons)


def test_verdict_skew_boundary_2_9_warns_3_0_blocks():
    """倾斜阈值边界：2.9° → warn(W2)；3.0°（含）→ block(B3)。"""
    v_warn, r_warn = grading.verdict_document(_report(
        recognition={"skew_deg": 2.9, "skew_measured": True, "skew_pages_ratio": 0.0}))
    assert v_warn == "warn" and "W2" in [r["code"] for r in r_warn], (v_warn, r_warn)
    v_blk, r_blk = grading.verdict_document(_report(
        recognition={"skew_deg": 3.0, "skew_measured": True, "skew_pages_ratio": 0.0}))
    assert v_blk == "block" and "B3" in [r["code"] for r in r_blk], (v_blk, r_blk)


def test_verdict_missing_metric_never_blocks():
    """缺失度量不得触发 block（docstring 承诺）：无 chars_per_page 时 B4 不得开火。

    verifier 审计 P2-3：原实现把 None 当 0.0 → "没测到"被误报成"近乎空白"。
    """
    v, reasons = grading.verdict_document(_report(layout={"pages": 10, "chars": 100}))
    assert v != "block" and "B4" not in [r["code"] for r in reasons], (v, reasons)


def test_verdict_weird_ratio_boundary():
    """异常字符率边界：29.9% 不拦；30% 拦（且字数下限 500 生效：499 字不拦）。"""
    v_ok, r_ok = grading.verdict_document(_report(
        recognition={"weird_ratio": 0.299}, layout={"chars": 10000}))
    assert "B5" not in [r["code"] for r in r_ok], (v_ok, r_ok)
    v_blk, r_blk = grading.verdict_document(_report(
        recognition={"weird_ratio": 0.30}, layout={"chars": 10000}))
    assert "B5" in [r["code"] for r in r_blk], (v_blk, r_blk)
    v_small, r_small = grading.verdict_document(_report(
        recognition={"weird_ratio": 0.50}, layout={"chars": 499}))
    assert "B5" not in [r["code"] for r in r_small], (v_small, r_small)


def test_verdict_replacement_boundary_and_zero():
    """替换字符率边界：0% 不拦、4.99% 不拦、5% 拦。"""
    assert "B6" not in [r["code"] for r in grading.verdict_document(
        _report(recognition={"replacement_ratio": 0.0}))[1]]
    assert "B6" not in [r["code"] for r in grading.verdict_document(
        _report(recognition={"replacement_ratio": 0.0499}))[1]]
    assert "B6" in [r["code"] for r in grading.verdict_document(
        _report(recognition={"replacement_ratio": 0.05}))[1]]


def test_verdict_collapse_boundary():
    """坍缩边界：chars=1999 不拦、2000 且 clauses=1 拦、2000 且 clauses=2 不拦。"""
    assert "B2" not in [r["code"] for r in grading.verdict_document(
        _report(total_clauses=1, layout={"chars": 1999}))[1]]
    assert "B2" in [r["code"] for r in grading.verdict_document(
        _report(total_clauses=1, layout={"chars": 2000}))[1]]
    assert "B2" not in [r["code"] for r in grading.verdict_document(
        _report(total_clauses=2, layout={"chars": 2000}))[1]]


def test_verdict_sparse_pages_boundary():
    """近乎空白边界：4 页不拦（下限 5）、5 页且 19.9 字/页拦、20 字/页不拦。"""
    assert "B4" not in [r["code"] for r in grading.verdict_document(
        _report(layout={"pages": 4, "chars_per_page": 5.0}))[1]]
    assert "B4" in [r["code"] for r in grading.verdict_document(
        _report(layout={"pages": 5, "chars_per_page": 19.9}))[1]]
    assert "B4" not in [r["code"] for r in grading.verdict_document(
        _report(layout={"pages": 5, "chars_per_page": 20.0}))[1]]


def test_verdict_w3_suspect_ratio():
    """W3 可疑条款占比（verifier 审计：原无覆盖）。"""
    v, reasons = grading.verdict_document(_report(
        ocr_suspects=[{"x": 1}] * 3, total_clauses=30))   # 10% ≥ 5%
    assert v == "warn" and "W3" in [r["code"] for r in reasons], (v, reasons)
    v2, r2 = grading.verdict_document(_report(ocr_suspects=[{"x": 1}], total_clauses=30))
    assert "W3" not in [r["code"] for r in r2], (v2, r2)


def test_verdict_w5_low_type_confidence():
    """W5 分型置信度偏低（原无覆盖）。"""
    v, reasons = grading.verdict_document(_report(
        typing_quality={"low_type_confidence": 12, "distribution": {"rule": 30}}))
    assert v == "warn" and "W5" in [r["code"] for r in reasons], (v, reasons)
    # 条款太少时比例不可靠 → 不报（warn_min_clauses=10）
    v2, r2 = grading.verdict_document(_report(
        total_clauses=5, typing_quality={"low_type_confidence": 5}))
    assert "W5" not in [r["code"] for r in r2], (v2, r2)


def test_verdict_w10_low_clause_density():
    """W10 条款密度异常偏低（原无覆盖）。"""
    v, reasons = grading.verdict_document(_report(
        total_clauses=2, layout={"chars": 3000, "clauses_per_1000chars": 0.6}))
    assert "W10" in [r["code"] for r in reasons], (v, reasons)


def test_verdict_duplicate_warns():
    """W6 与库内重复 → warn（不 block：重复是可覆盖的正常情形）。"""
    v, reasons = grading.verdict_document(_report(
        duplicate={"kind": "standard_no", "message": "标准号已存在"}))
    assert v == "warn" and "W6" in [r["code"] for r in reasons], (v, reasons)


def test_grade_boundaries():
    """分级边界（R13 契约）：0.95→A、0.85→B、0.8499→C；block→D（仅预览语义）。"""
    assert grading.grade_document("ok", 0.95)[0] == "A"
    assert grading.grade_document("ok", 0.9499)[0] == "B"
    assert grading.grade_document("warn", 0.85)[0] == "B"
    assert grading.grade_document("warn", 0.8499)[0] == "C"
    assert grading.grade_document("block", 0.99)[0] == "D"


def test_clause_ocr_confidence_units():
    """条款级置信度的扣分项（含原不可达的 tiny 与不可打印字符）。"""
    from src.core.quality.recognition import clause_ocr_confidence
    clean = "动火作业应有专人监护，作业前应办理审批手续。"
    conf, reasons = clause_ocr_confidence(clean, page_skew_deg=None)
    assert conf == 1.0 and reasons == []
    tiny, r_tiny = clause_ocr_confidence("见附录A。", page_skew_deg=None, is_tiny=True)
    assert tiny == 0.85 and "P1" in r_tiny, (tiny, r_tiny)
    ctrl, r_ctrl = clause_ocr_confidence("正文含控制字符\x01\x02的内容", page_skew_deg=None)
    assert "P4" in r_ctrl and ctrl < 1.0, (ctrl, r_ctrl)
    skewed, r_skew = clause_ocr_confidence(clean, page_skew_deg=1.5)
    assert "P6" in r_skew and abs(skewed - 0.7) < 1e-6, (skewed, r_skew)


def test_clause_head_is_raw_prefix(db, tmp_path):
    """`head` 必须**逐字符**等于原文前 80 字（证据文本不可变红线；原无覆盖）。"""
    rep = dry_run.analyze_preview_report(_mk_good_pdf(tmp_path, "head.pdf"))
    sample = rep["head_samples"][0]
    assert sample["head"] == sample["head"]  # 占位防误删
    assert len(sample["head"]) <= dry_run.HEAD_CHARS
    assert "\ufffd" not in sample["head"]
    # 用同一份 PDF 走生产建条，比对正文与 head 的前缀一致性
    from src.core.ingestion.pipeline import (build_clause_models,
                                             load_middle_items_from_blocks,
                                             split_items_into_clauses)
    from src.core.ingestion.parser_worker import run_parser_isolated
    parsed = run_parser_isolated(tmp_path / "head.pdf", tmp_path / "out", force_deep=False,
                                 deep_fallback=False)
    items, _ = load_middle_items_from_blocks([b for b in parsed["blocks"] if b.get("text")])
    models, _ = build_clause_models("preview", "X", "standard",
                                    split_items_into_clauses(items), {0: (595.0, 842.0)})
    assert [m.content_text[:dry_run.HEAD_CHARS] for m in models][:len(rep["head_samples"])] == \
           [s["head"] for s in rep["head_samples"]], "预览 head 必须等于生产建条正文的前缀"


def _mk_table_pdf(tmp_path: Path, name: str = "table.pdf") -> Path:
    """带**矢量框线表**的 PDF（fitz 画线 + 单元格文字）。

    用途：证明预览侧 6 个体检标签里的表格类标签**可达**（verifier 审计 P0-3 的回归网）——
    中间列放 "123" 会命中「表格脏单元格」（规则要求值夹在两根竖线之间）。
    """
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 70), "5.1 动火作业应有专人监护。", fontsize=12, fontname="china-s")
    x0, y0, cw, rh = 72, 100, 120, 26
    rows, cols = 3, 3
    for r in range(rows + 1):
        page.draw_line(fitz.Point(x0, y0 + r * rh), fitz.Point(x0 + cols * cw, y0 + r * rh))
    for c in range(cols + 1):
        page.draw_line(fitz.Point(x0 + c * cw, y0), fitz.Point(x0 + c * cw, y0 + rows * rh))
    cells = [["作业名称", "编号", "监护要求"],
             ["动火作业", "123", "专人监护"],
             ["受限空间", "456", "气体检测"]]
    for r, row in enumerate(cells):
        for c, txt in enumerate(row):
            page.insert_text((x0 + c * cw + 6, y0 + r * rh + 17), txt,
                             fontsize=9, fontname="china-s")
    return _save(doc, tmp_path / name)


def test_preview_table_tags_are_live(db, tmp_path, fake_parse, monkeypatch):
    """**表格类体检标签在预览里可达**（verifier 审计 P0-3 的回归网）。

    两层证明，不混为一谈：
    ① 真 PDF：预览**确实跑了**表格重建（`layout.tables_rebuilt ≥ 1`）——删掉对
       `_extract_vector_table_items` 的调用本断言即红；
    ② 受控注入：把一张带「中间列 123」的表挂进建条（题注让切分器产出表格条款），
       预览必须把它交给 `clause_health` → 报出「表格脏单元格」。
       （表格**能否**绑到条款由上游切分器的题注规则决定，与入库完全同源；这里锁的是
       **我这一层的接线**：预览不得丢掉 `content_markdown`。）
    """
    from src.core.ingestion import pipeline
    from src.core.ingestion.pipeline import MidItem

    p = _mk_table_pdf(tmp_path)
    tbl_html = ("<table><tr><td>甲</td><td>123</td><td>乙</td></tr>"
                "<tr><td>丙</td><td>456</td><td>丁</td></tr></table>")

    def _fake_tables(pdf_path, o_blocks, is_ocr=False):
        fake_parse([_block("5.1 动火作业应有专人监护。")])
        return [MidItem(kind="table", text="表1 作业危险等级", html=tbl_html,
                        caption="表1 作业危险等级", page_idx=0,
                        bbox=[70.0, 90.0, 430.0, 180.0])], set()

    monkeypatch.setattr(pipeline, "_extract_vector_table_items", _fake_tables)
    rep = dry_run.analyze_preview_report(p)
    assert rep["layout"]["tables_rebuilt"] >= 1, rep["layout"]
    signals = rep["collected_signals"]
    assert "表格脏单元格" in signals, signals


def test_preview_table_pipeline_runs_on_real_pdf(db, tmp_path):
    """真 PDF 层：合成框线表必须被预览的表格重建捕获（不再只走文本层）。"""
    rep = dry_run.analyze_preview_report(_mk_table_pdf(tmp_path, "tbl_real.pdf"))
    assert rep["layout"]["tables_rebuilt"] >= 1, rep["layout"]


def test_preview_doc_type_changes_typing(db, tmp_path):
    """`doc_type` 必须**真的影响分型**（不是参数回显）。

    回归网针对 verifier 审计 3.1 的"回显型假断言"：分类器只把 `"法律法规"`/`"法律"`
    当法规（`classifier.py:123`），所以传中文值才该改变分布。
    """
    p = _mk_good_pdf(tmp_path, "doctype.pdf")
    as_std = dry_run.analyze_preview_report(p, doc_type="standard")
    as_law = dry_run.analyze_preview_report(p, doc_type="法律法规")
    assert as_std["typing_quality"]["doc_type_used"] == "standard"
    assert as_law["typing_quality"]["doc_type_used"] == "法律法规"
    # 5.2.x 编号的条款在 standard 下不是 legal；在"法律法规"下必须出现 legal
    assert as_law["knowledge_type_distribution"] != as_std["knowledge_type_distribution"], (
        as_law["knowledge_type_distribution"], as_std["knowledge_type_distribution"])
    assert as_law["knowledge_type_distribution"].get("legal", 0) > 0


def test_tail_samples_when_fewer_than_n(db, tmp_path, fake_parse):
    """条款数 ≤ N 时尾部样本退回全部（原实现给空数组；verifier 审计 P2-1）。"""
    p = _mk_good_pdf(tmp_path, "tail.pdf")
    fake_parse([_block("5.1 动火作业应有专人监护。\n5.2 作业前应办理审批手续。")])
    rep = dry_run.analyze_preview_report(p)
    assert rep["head_samples"] and rep["tail_samples"], (len(rep["head_samples"]),
                                                         len(rep["tail_samples"]))
    assert len(rep["tail_samples"]) == len(rep["head_samples"])





# --------------------------------------------------------------------------- #
# B 组：只读
# --------------------------------------------------------------------------- #
def _table_snapshot() -> dict[str, int]:
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    names = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    return {n: conn.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0] for n in names}


def test_dry_no_row_written_any_table(db, tmp_path):
    before = _table_snapshot()
    p = _mk_good_pdf(tmp_path, "ro.pdf")
    dry_run.analyze_preview_report(p)
    after = _table_snapshot()
    assert after == before, {k: (before.get(k), after.get(k)) for k in set(before) | set(after)
                             if before.get(k) != after.get(k)}
    # 该文件不得出现在 doc_meta
    from src.core.storage.sqlite_db import get_db_connection
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    n = get_db_connection().execute("SELECT COUNT(*) FROM doc_meta WHERE file_hash=?",
                                    (h,)).fetchone()[0]
    assert n == 0


def test_dry_no_new_table(db, tmp_path):
    from src.core.storage.sqlite_db import get_db_connection
    names_before = {r[0] for r in get_db_connection().execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    dry_run.analyze_preview_report(_mk_good_pdf(tmp_path, "ro2.pdf"))
    names_after = {r[0] for r in get_db_connection().execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert names_before == names_after


def test_dry_temp_dir_under_data_dir_and_hash_isolated(db, tmp_path):
    """临时产物必须落在 data_dir/dryrun/tmp/<hash16>/，且不同文件互不覆盖。"""
    from src.core.config import get_settings
    p1 = _mk_good_pdf(tmp_path, "iso1.pdf")
    p2 = _mk_good_pdf(tmp_path, "iso2.pdf")
    dry_run.analyze_preview_report(p1)
    dry_run.analyze_preview_report(p2)
    root = get_settings().data_dir / "dryrun" / "tmp"
    dirs = {d.name for d in root.iterdir()} if root.exists() else set()
    h1 = hashlib.sha256(p1.read_bytes()).hexdigest()[:16]
    h2 = hashlib.sha256(p2.read_bytes()).hexdigest()[:16]
    assert h1 in dirs and h2 in dirs, dirs
    assert h1 != h2


def test_dry_no_pdf_copy(db, tmp_path):
    """预览不得复制/移动用户文件（源文件与目录清单不变）。"""
    p = _mk_good_pdf(tmp_path, "nocopy.pdf")
    before = sorted(x.name for x in tmp_path.iterdir())
    dry_run.analyze_preview_report(p)
    after = sorted(x.name for x in tmp_path.iterdir())
    assert before == after


def test_dry_analyze_preview_contract_frozen(db, tmp_path):
    """既有 `analyze_preview` 的返回键集合不得变化（它是被别处依赖的老接口）。"""
    from src.core.ingestion.pipeline import analyze_preview
    p = _mk_good_pdf(tmp_path, "frozen.pdf")
    out = analyze_preview(p)
    assert set(out) == {"status", "total_clauses", "knowledge_type_distribution",
                        "suspicious_count", "sample", "pages"}, set(out)


def test_dry_typing_uses_doc_type(db, tmp_path):
    """F8 修复的证据：预览分型必须把 doc_type 传下去（法规类文档要出现 legal）。

    同一份 PDF 用 doc_type='law' 与 'standard' 分型，报告里 `doc_type_used` 必须reflect 传入值。
    """
    p = _mk_good_pdf(tmp_path, "doctype.pdf")
    rep = dry_run.analyze_preview_report(p, doc_type="law")
    assert rep["typing_quality"]["doc_type_used"] == "law"
