"""span 坐标系通用自动校准测试（R-B，pipeline/13-round3.md）。

用 fitz 生成已知几何的测试 PDF（顶部原点基线 y 已知），覆盖：
① 两页三行文本的 vote_origin 双解释判定 + 无行 None；
② calibrate_new 幂等（翻转为底部原点后二次调用零变化）；
③ 50140 复验式：条款块中段碎片 bbox 最近行投票一致，不再分裂；
④ 存量路径 calibrate：rowid 精确 UPDATE + event_log 审计 + 复跑不双翻；
⑤ dry-run 零写库与空数据安全返回。
"""
import json
import sqlite3

import fitz

from src.core.ingestion.span_calibration import (
    calibrate,
    calibrate_new,
    page_line_centers,
    vote_origin,
)


def _make_pdf(path, pages, base_y=100.0, step=100.0) -> str:
    """构造测试 PDF：每页写已知 ASCII 文本行（fitz 顶部原点，基线 y = base_y + i*step）。

    pages: 每页一个行文本列表（空列表 = 无文字层页面）。
    """
    doc = fitz.open()
    for lines in pages:
        page = doc.new_page()
        for i, text in enumerate(lines):
            page.insert_text((72, base_y + i * step), text, fontsize=12)
    doc.save(str(path))
    doc.close()
    return str(path)


def test_page_line_centers_and_vote_top_bottom_none(tmp_path):
    """①两页 PDF 三行已知文本：top-origin bbox 判 top；翻转后判 bottom；无行返回 None。"""
    pdf_path = _make_pdf(tmp_path / "two_pages.pdf", [
        ["ALPHA LINE ONE", "BRAVO LINE TWO", "CHARLIE LINE THREE"],
        ["DELTA LINE FOUR", "ECHO LINE FIVE", "FOXTROT LINE SIX"],
        [],  # 无文字层页
    ])
    doc = fitz.open(pdf_path)
    try:
        h = doc[0].rect.height
        centers = page_line_centers(doc[0])
        assert len(centers) == 3 and centers == sorted(centers)

        # 顶部原点 bbox（罩第一行：直读即贴真实行）→ 判 top
        assert vote_origin(doc[0], [70, 88, 300, 104]) == "top"
        # 同一区域翻转成底部原点存储后（H−y）：换算解释贴行、直读落到下方留白 → 判 bottom
        assert vote_origin(doc[0], [70, round(h - 104, 2), 300, round(h - 88, 2)]) == "bottom"

        # 第二页独立构建行中心表，同样成立
        assert vote_origin(doc[1], [70, 188, 300, 204]) == "top"
        assert vote_origin(doc[1], [70, round(h - 204, 2), 300, round(h - 188, 2)]) == "bottom"

        # 无文字行 → None（不可投票）
        assert vote_origin(doc[2], [70, 88, 300, 104]) is None
    finally:
        doc.close()


def test_calibrate_new_idempotent(tmp_path):
    """②纯函数版：顶部原点翻为底部原点后二次调用零变化；已正确则一次即零改动。"""
    pdf_path = _make_pdf(tmp_path / "calib.pdf", [["AAA ONE", "BBB TWO", "CCC THREE"]])
    doc = fitz.open(pdf_path)
    h = doc[0].rect.height
    doc.close()

    spans_top = [{"span_id": "s1", "page_number": 1, "bbox": [70, 88, 300, 104]},
                 {"span_id": "s2", "page_number": 1, "bbox": [70, 188, 300, 204]}]
    out = calibrate_new(pdf_path, spans_top)
    assert out == spans_top  # 返回归一后的 span 列表
    assert all(a is b for a, b in zip(out, spans_top))  # 元素原地归一（同一对象）
    assert [s["bbox"] for s in spans_top] == [
        [70, round(h - 104, 2), 300, round(h - 88, 2)],
        [70, round(h - 204, 2), 300, round(h - 188, 2)]]

    snap = [list(s["bbox"]) for s in spans_top]
    calibrate_new(pdf_path, spans_top)  # 二次调用幂等
    calibrate_new(pdf_path, spans_top)
    assert [s["bbox"] for s in spans_top] == snap

    # 已是底部原点（正确）的 span：投票全 bottom，零改动
    good = [70, round(h - 104, 2), 300, round(h - 88, 2)]
    spans_ok = [{"page_number": 1, "bbox": list(good)}]
    calibrate_new(pdf_path, spans_ok)
    assert spans_ok[0]["bbox"] == good


def test_calibrate_new_supports_source_span_model(tmp_path):
    """pipeline 接入形态：SourceSpanModel 对象同样原地归一为底部原点。"""
    from src.core.domain.models import SourceSpanModel
    pdf_path = _make_pdf(tmp_path / "model.pdf", [["MODEL ROW ONE", "MODEL ROW TWO"]])
    doc = fitz.open(pdf_path)
    h = doc[0].rect.height
    doc.close()
    m = SourceSpanModel(span_id="span_x", page_number=1, bbox=[70, 88, 300, 104])
    calibrate_new(pdf_path, [m])
    assert m.bbox == [70, round(h - 104, 2), 300, round(h - 88, 2)]
    doc = fitz.open(pdf_path)
    try:
        assert vote_origin(doc[0], m.bbox) == "bottom"  # 归一后自证底部原点
    finally:
        doc.close()


def test_fragment_vote_no_split_50140_style(tmp_path):
    """③50140 复验式：条款块中段碎片 bbox 用最近行投票一致判定，不再分裂。

    页面文字集中在顶部半页（镜像区留白）：碎片无论取块内哪一段，
    直读解释的最近文字行都归属自身 → 全体一致判 top（旧法拿碎片中心比块首行，
    碎片越靠后偏差越大导致票数分裂）。
    """
    pdf_path = _make_pdf(tmp_path / "frag.pdf", [[
        "PREFACE ONE", "PREFACE TWO", "PREFACE THREE",
        "5.2.1 CLAUSE HEAD", "CLAUSE BODY A", "CLAUSE BODY B",
    ]], base_y=80.0, step=55.0)
    doc = fitz.open(pdf_path)
    try:
        h = doc[0].rect.height
        # 条款块中段碎片（MinerU 行级碎片形态：单行 / 跨两行的窄条 bbox）
        frags = [[70, 230, 420, 254],   # HEAD 单行（块首）
                 [70, 285, 420, 368],   # BODY A+B 跨两行（块中）
                 [70, 340, 420, 364]]   # BODY B 单行（块尾）
        votes = {vote_origin(doc[0], f) for f in frags}
        assert votes == {"top"}  # 一致判定，不再分裂

        # calibrate_new 文档级多数决：全量翻转后逐条复投仍一致收敛为 bottom
        spans = [{"page_number": 1, "bbox": list(f)} for f in frags]
        calibrate_new(pdf_path, spans)
        assert [vote_origin(doc[0], s["bbox"]) for s in spans] == ["bottom"] * 3
        assert spans[-1]["bbox"] == [70, round(h - 364, 2), 420, round(h - 340, 2)]
    finally:
        doc.close()


_DB_SCHEMA = """
CREATE TABLE clause_revision (clause_revision_id TEXT PRIMARY KEY, doc_id TEXT,
    content_text TEXT);
CREATE TABLE source_span (span_id TEXT PRIMARY KEY, clause_revision_id TEXT,
    page_number INTEGER, bbox_json TEXT, span_type TEXT DEFAULT 'text',
    sort_order INTEGER DEFAULT 0);
CREATE TABLE event_log (event_id TEXT PRIMARY KEY, event_type TEXT, actor TEXT,
    target_type TEXT, target_id TEXT, before_state TEXT, after_state TEXT,
    metadata TEXT, created_at TEXT DEFAULT (datetime('now')));
"""

_DB_CONTENT = "DB ROW ONE DB ROW TWO DB ROW THREE"


def test_calibrate_db_rowid_update_and_audit(tmp_path):
    """④存量路径（带内真值裁决）：rowid 精确 UPDATE + event_log 审计；复跑不双翻。"""
    pdf_path = _make_pdf(tmp_path / "db.pdf",
                         [["DB ROW ONE", "DB ROW TWO", "DB ROW THREE"]])
    conn = sqlite3.connect(":memory:")
    conn.executescript(_DB_SCHEMA)
    conn.execute("INSERT INTO clause_revision VALUES ('clrev_1', 'doc_1', ?)",
                 (_DB_CONTENT,))
    for i, (y0, y1) in enumerate([(88.0, 104.0), (188.0, 204.0), (288.0, 304.0)]):
        conn.execute("INSERT INTO source_span VALUES (?,?,?,?,?,?)",
                     (f"s{i}", "clrev_1", 1, json.dumps([70, y0, 300, y1]), "text", i))

    res = calibrate("doc_1", pdf_path, conn)
    assert res["flipped"] is True and res["verdict"] == "top_flip"
    doc = fitz.open(pdf_path)
    h = doc[0].rect.height
    rows = conn.execute("SELECT bbox_json FROM source_span ORDER BY sort_order").fetchall()
    assert json.loads(rows[0][0]) == [70, round(h - 104, 2), 300, round(h - 88, 2)]
    assert json.loads(rows[2][0]) == [70, round(h - 304, 2), 300, round(h - 288, 2)]
    assert conn.execute("SELECT COUNT(*) FROM event_log WHERE"
                        " event_type='repair/span_origin_flipped'").fetchone()[0] == 1

    # 复跑：已底部原点 → 带内真值判 bottom_keep，零改动、不重复审计
    res2 = calibrate("doc_1", pdf_path, conn)
    assert res2["flipped"] is False and res2["verdict"] == "bottom_keep"
    rows2 = conn.execute("SELECT bbox_json FROM source_span ORDER BY sort_order").fetchall()
    assert [json.loads(r[0]) for r in rows2] == [json.loads(r[0]) for r in rows]
    assert conn.execute("SELECT COUNT(*) FROM event_log").fetchone()[0] == 1
    doc.close()
    conn.close()


def test_calibrate_dry_run_and_empty_safe(tmp_path):
    """⑤dry-run 只报告零写库；无 span / 无行页安全返回不翻转。"""
    pdf_path = _make_pdf(tmp_path / "dry.pdf", [["DRY ROW ONE"], []])  # 第 2 页空白
    conn = sqlite3.connect(":memory:")
    conn.executescript(_DB_SCHEMA)
    conn.execute("INSERT INTO clause_revision VALUES ('clrev_1', 'doc_1', ?)",
                 ("DRY ROW ONE",))
    conn.execute("INSERT INTO source_span VALUES ('s0','clrev_1',1,?,'text',0)",
                 (json.dumps([70, 88, 300, 104]),))

    res = calibrate("doc_1", pdf_path, conn, apply=False)  # dry-run
    assert res["flipped"] is False and res["verdict"] == "top_flip"
    assert conn.execute("SELECT bbox_json FROM source_span").fetchone()[0] \
        == json.dumps([70, 88, 300, 104])  # 零写库
    assert conn.execute("SELECT COUNT(*) FROM event_log").fetchone()[0] == 0

    # 无 span 文档：安全空返回
    conn.execute("INSERT INTO clause_revision VALUES ('clrev_2', 'doc_2', 'X')")
    res_empty = calibrate("doc_2", pdf_path, conn)
    assert res_empty["flipped"] is False
    # 有 span 但落在无文字层页 → 带内真值无法判定（unknown）不翻转
    conn.execute("INSERT INTO source_span VALUES ('s9','clrev_2',2,?,'text',0)",
                 (json.dumps([70, 88, 300, 104]),))
    res_unknown = calibrate("doc_2", pdf_path, conn)
    assert res_unknown["flipped"] is False and res_unknown["verdict"] == "unknown"
    conn.close()


def _mk_conn(content, spans):
    """内存库：content 挂两条款（clrev_1/clrev_2），spans=[(cid, page, y0, y1, sort)]。"""
    conn = sqlite3.connect(":memory:")
    conn.executescript(_DB_SCHEMA)
    for cid in ("clrev_1", "clrev_2"):
        conn.execute("INSERT INTO clause_revision VALUES (?, 'doc_1', ?)", (cid, content))
    for i, (cid, pno, y0, y1) in enumerate(spans):
        conn.execute("INSERT INTO source_span VALUES (?,?,?,?,?,?)",
                     (f"s{i}", cid, pno, json.dumps([70, y0, 300, y1]), "text", i))
    return conn


def test_calibrate_both_hit_uses_direction_no_double_flip(tmp_path):
    """v2 回归：采样 span 落在镜像对称区（两种解释都命中）时，已正确的文档**不得**被翻转。

    旧版把 both 计入 top_hits → 已底部原点文档被误翻（2026-08-25 安全生产法翻 2 次的根因）。
    页面中部文本 + 底部原点存储 → both-hit；阅读方向递减（dec=2）→ 必须 bottom_keep 零改动。
    """
    pdf_path = _make_pdf(tmp_path / "both.pdf",
                         [["AAA MID ONE", "BBB MID TWO", "CCC MID THREE", "DDD MID FOUR"]],
                         base_y=350.0, step=50.0)
    doc = fitz.open(pdf_path)
    h = doc[0].rect.height
    doc.close()
    spans = [
        ("clrev_1", 1, round(h - 410, 2), round(h - 350, 2)),
        ("clrev_1", 1, round(h - 500, 2), round(h - 440, 2)),
        ("clrev_2", 1, round(h - 360, 2), round(h - 340, 2)),
        ("clrev_2", 1, round(h - 460, 2), round(h - 440, 2)),
    ]
    content = "AAA MID ONE BBB MID TWO CCC MID THREE DDD MID FOUR"
    conn = _mk_conn(content, spans)
    before = [json.loads(r[0]) for r in
              conn.execute("SELECT bbox_json FROM source_span ORDER BY sort_order")]
    res = calibrate("doc_1", pdf_path, conn)
    assert res["samples"]["both"] >= 2, res["samples"]   # 确认确实落在 both 区
    assert res["verdict"] == "bottom_keep" and res["flipped"] is False
    after = [json.loads(r[0]) for r in
             conn.execute("SELECT bbox_json FROM source_span ORDER BY sort_order")]
    assert after == before  # 零改动
    assert conn.execute("SELECT COUNT(*) FROM event_log").fetchone()[0] == 0
    conn.close()


def test_calibrate_direction_vote_flips_when_text_unverifiable(tmp_path):
    """v2 回归：无文字层页（模拟乱码/纯扫描件）带内文字无法判定 → 阅读方向证据兜底：
    两条款各 2 span、y 严格递增（顶部原点信号）→ 翻转；复跑幂等 bottom_keep。"""
    pdf_path = _make_pdf(tmp_path / "dir.pdf", [[]])  # 无文字层页
    doc = fitz.open(pdf_path)
    h = doc[0].rect.height
    doc.close()
    spans = [
        ("clrev_1", 1, 88.0, 104.0), ("clrev_1", 1, 188.0, 204.0),
        ("clrev_2", 1, 288.0, 304.0), ("clrev_2", 1, 388.0, 404.0),
    ]
    conn = _mk_conn("X Y Z", spans)
    res = calibrate("doc_1", pdf_path, conn)
    assert res["samples"]["none"] >= 2 and res["samples"]["direction_inc"] >= 2
    assert res["verdict"] == "top_flip" and res["flipped"] is True
    rows = conn.execute("SELECT bbox_json FROM source_span ORDER BY sort_order").fetchall()
    assert json.loads(rows[0][0]) == [70, round(h - 104, 2), 300, round(h - 88, 2)]
    # 复跑幂等：翻转后方向递减 → bottom_keep，零改动不重复审计
    res2 = calibrate("doc_1", pdf_path, conn)
    assert res2["verdict"] == "bottom_keep" and res2["flipped"] is False
    rows2 = conn.execute("SELECT bbox_json FROM source_span ORDER BY sort_order").fetchall()
    assert [json.loads(r[0]) for r in rows2] == [json.loads(r[0]) for r in rows]
    conn.close()


def test_calibrate_new_uses_direction_with_groups(tmp_path):
    """pipeline 形态：calibrate_new 传入条款分组后，方向判别生效（无文字层也能翻）。"""
    pdf_path = _make_pdf(tmp_path / "new_dir.pdf", [[]])
    doc = fitz.open(pdf_path)
    h = doc[0].rect.height
    doc.close()
    s1 = {"page_number": 1, "bbox": [70, 88, 300, 104], "sort_order": 0}
    s2 = {"page_number": 1, "bbox": [70, 188, 300, 204], "sort_order": 1}
    s3 = {"page_number": 1, "bbox": [70, 288, 300, 304], "sort_order": 0}
    s4 = {"page_number": 1, "bbox": [70, 388, 300, 404], "sort_order": 1}
    spans = [s1, s2, s3, s4]
    calibrate_new(pdf_path, spans, groups=[[s1, s2], [s3, s4]])  # inc=2 → 全量翻转
    assert [s["bbox"] for s in spans] == [
        [70, round(h - 104, 2), 300, round(h - 88, 2)],
        [70, round(h - 204, 2), 300, round(h - 188, 2)],
        [70, round(h - 304, 2), 300, round(h - 288, 2)],
        [70, round(h - 404, 2), 300, round(h - 388, 2)],
    ]
    # 幂等：已是底部原点 → 方向递减 → 零改动
    snap = [list(s["bbox"]) for s in spans]
    calibrate_new(pdf_path, spans, groups=[[s1, s2], [s3, s4]])
    assert [s["bbox"] for s in spans] == snap
