"""排版还原 B3/B5 管线测试：页界入库 + 行级 bbox + 行级 span。

用户验收口径（2026-09-01）：
「原文哪里换页我就哪里换页，哪里换行我就哪里换行，而且不能是强行加回车」
——页界编码（clause_revision.page_breaks）与行级高亮（source_span 行级 bbox）
必须与 content_text 行号严格对齐。
"""
import json
from pathlib import Path

import pytest

from src.core.ingestion.pipeline import (
    MidItem, build_clause_models, load_middle_items, split_items_into_clauses)


def _mk_middle_multiline(tmp_path: Path) -> Path:
    """合成 3 页 middle.json（行框齐全）：条款 5.2.1 跨页 0→1，5.2.2 在页 1，
    5.3 在页 2；页 2 的 5.4 块内混入整行家具（标准号）。"""
    def _ln(content: str, bbox: list[float]) -> dict:
        return {"bbox": bbox, "spans": [{"type": "text", "content": content}]}

    mj = {"pdf_info": [
        {"page_idx": 0, "page_size": [595.0, 841.0], "para_blocks": [
            {"type": "text", "bbox": [60.0, 700.0, 530.0, 740.0], "lines": [
                _ln("5.2.1 动火作业应有专人监护，", [60.0, 700.0, 530.0, 720.0]),
                _ln("作业前应清除易燃物品。", [60.0, 722.0, 530.0, 740.0]),
            ]},
            {"type": "text", "bbox": [60.0, 650.0, 530.0, 670.0], "lines": [
                _ln("监护人员应持证上岗。", [60.0, 650.0, 530.0, 670.0]),
            ]},
        ], "discarded_blocks": [
            {"type": "header", "bbox": [200.0, 20.0, 400.0, 40.0], "lines": [
                {"spans": [{"type": "text", "content": "GB 30871—2022"}]}]},
        ]},
        {"page_idx": 1, "page_size": [595.0, 841.0], "para_blocks": [
            {"type": "text", "bbox": [60.0, 740.0, 530.0, 760.0], "lines": [
                _ln("但节假日或夜间作业除外。", [60.0, 740.0, 530.0, 760.0]),
            ]},
            {"type": "table", "bbox": [60.0, 400.0, 530.0, 600.0], "blocks": [
                {"type": "table_caption", "lines": [
                    {"spans": [{"type": "text", "content": "表 5.2.1 动火分级"}]}]},
                {"type": "table_body", "lines": [
                    {"spans": [{"type": "table",
                                "html": "<table><tr><td>级别</td></tr></table>"}]}]},
            ]},
            {"type": "text", "bbox": [60.0, 300.0, 530.0, 340.0], "lines": [
                _ln("5.2.2 动火分析合格标准：", [60.0, 300.0, 530.0, 320.0]),
                _ln("可燃气体浓度不大于 0.5%。", [60.0, 322.0, 530.0, 340.0]),
            ]},
        ], "discarded_blocks": []},
        {"page_idx": 2, "page_size": [595.0, 841.0], "para_blocks": [
            {"type": "text", "bbox": [60.0, 700.0, 530.0, 720.0], "lines": [
                _ln("5.3 其他要求按 GB 50016 的规定执行。",
                    [60.0, 700.0, 530.0, 720.0]),
            ]},
            {"type": "text", "bbox": [60.0, 600.0, 530.0, 660.0], "lines": [
                _ln("5.4 配置的灭火器应符合产品标准。", [60.0, 600.0, 530.0, 620.0]),
                _ln("GB 30871—2025", [60.0, 622.0, 530.0, 640.0]),
                _ln("施工现场应设置消防通道。", [60.0, 642.0, 530.0, 660.0]),
            ]},
        ], "discarded_blocks": []},
    ]}
    p = tmp_path / "multiline_middle.json"
    p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.fixture()
def _built(tmp_path):
    """load → split → build 一次，供多个用例复用。"""
    items, page_sizes = load_middle_items(_mk_middle_multiline(tmp_path))
    clauses = split_items_into_clauses(items)
    models, _edges = build_clause_models(
        "d1", "GB 30871-2022", "standard", clauses, page_sizes)
    by_no = {m.clause_number: m for m in models}
    return by_no, clauses


def test_load_middle_items_line_boxes_aligned(tmp_path):
    """B5 底座：MidItem.line_boxes 与 text 行序列一一对齐（行界=line）。"""
    items, _ = load_middle_items(_mk_middle_multiline(tmp_path))
    blk = next(i for i in items if "5.2.1" in i.text)
    lns = blk.text.split("\n")
    assert lns == ["5.2.1 动火作业应有专人监护，", "作业前应清除易燃物品。"]
    assert len(blk.line_boxes) == len(lns), "行框数须等于行数（1:1 对齐）"
    assert blk.line_boxes[0] == [60.0, 700.0, 530.0, 720.0]
    assert blk.line_boxes[1] == [60.0, 722.0, 530.0, 740.0]


def test_split_rows_page_attribution(_built):
    """B3 采集：SplitClause.rows 逐行携带 0-based 页号（跨页拼接行页号正确）。"""
    _by_no, clauses = _built
    c521 = next(c for c in clauses if c.number == "5.2.1")
    pages = [p for _, p, _ in c521.rows]
    assert pages == [0, 0, 0, 1], "但书行（页1）拼接后页号须为 1"
    assert c521.rows[3][0] == "但节假日或夜间作业除外。"
    # 行框随行走（拼接行取自身块的行框）
    assert c521.rows[3][2] == [60.0, 740.0, 530.0, 760.0]
    c522 = next(c for c in clauses if c.number == "5.2.2")
    assert [p for _, p, _ in c522.rows] == [1, 1]


def test_build_page_breaks_run_start(_built):
    """B3 页界编码：run-start [[行号, PDF页], ...]，行号 = content_text 0-based
    行索引，首条目恒 [0, 首行页]。"""
    by_no, _clauses = _built
    m521 = by_no["5.2.1"]
    assert m521.page_breaks == [[0, 1], [3, 2]], \
        "第 4 行（0-based 3）起跨入 PDF 第 2 页"
    # 行号必须落在 content_text 的行序列内（对齐红线）
    lns = m521.content_text.split("\n")
    assert lns[3] == "但节假日或夜间作业除外。"
    m522 = by_no["5.2.2"]
    assert m522.page_breaks == [[0, 2]]  # page_idx 1 → PDF 第 2 页
    m53 = by_no["5.3"]
    assert m53.page_breaks == [[0, 3]]  # 页 3 = page_idx 2 + 1


def test_build_row_pipeline_furniture_strip(_built):
    """家具剥离在 rows 上做：整行标准号丢弃后行号收缩，页界编码仍与
    content_text 严格对齐（不许漂移）。"""
    by_no, _clauses = _built
    m54 = by_no["5.4"]
    assert "GB 30871—2025" not in m54.content_text, "整行家具须剥离"
    lns = m54.content_text.split("\n")
    assert lns == ["5.4 配置的灭火器应符合产品标准。", "施工现场应设置消防通道。"]
    assert m54.page_breaks == [[0, 3]]


def test_build_line_spans_full_no_cap(_built):
    """B5：行级 span 全量入库（退役 [:8] 封顶），bbox=折行行框、sort_order
    顺序；表格保留块级 span。"""
    by_no, _clauses = _built
    m521 = by_no["5.2.1"]
    text_spans = [s for s in m521.source_spans if s.span_type == "text"]
    assert len(text_spans) == 4, "4 个正文行 → 4 个行级 span（旧 [:8] 也不触顶，"
    "此处验证的是逐行 bbox 而非块级）"
    assert text_spans[0].bbox == [60.0, 700.0, 530.0, 720.0], "首 span=首行框"
    assert text_spans[3].bbox == [60.0, 740.0, 530.0, 760.0], "拼接行取自身行框"
    assert text_spans[3].page_number == 2
    assert [s.sort_order for s in m521.source_spans] == list(
        range(len(m521.source_spans))), "sort_order 顺序枚举"
    tbl = [s for s in m521.source_spans if s.span_type == "table"]
    assert len(tbl) == 1 and tbl[0].bbox == [60.0, 400.0, 530.0, 600.0]


def test_build_spans_fallback_when_line_boxes_missing():
    """行框整体缺失（旧 middle.json 无 line.bbox）→ 回退块级 span（宁粗不高灭），
    与 test_pipeline 既有断言（块级 bbox 直存）同轨。"""
    from src.core.ingestion.pipeline import MidItem
    items = [MidItem(kind="text", text="5.9.1 无行框条款甲。\n第二行内容。",
                     page_idx=4, bbox=[10.0, 20.0, 30.0, 40.0])]
    clauses = split_items_into_clauses(items)
    models, _ = build_clause_models("d", "GB T-2022", "standard", clauses, {})
    m = models[0]
    assert [s.span_type for s in m.source_spans] == ["text"]
    assert m.source_spans[0].bbox == [10.0, 20.0, 30.0, 40.0], "回退块级 bbox"
    assert m.source_spans[0].page_number == 5


def test_build_truncation_rowwise():
    """[:4000] 截断在 rows 上做：整行入账、末行可截半，截断后行号/页界不漂移。"""
    from src.core.ingestion.pipeline import MidItem
    long_line = "甲" * 5000
    items = [
        MidItem(kind="text", text="5.9.2 超长条款。", page_idx=0,
                bbox=[60.0, 700.0, 530.0, 720.0]),
        MidItem(kind="text", text=long_line, page_idx=0,
                bbox=[60.0, 650.0, 530.0, 690.0]),
        MidItem(kind="text", text="截断后不应出现。", page_idx=1,
                bbox=[60.0, 600.0, 530.0, 640.0]),
    ]
    clauses = split_items_into_clauses(items)
    models, _ = build_clause_models("d", "GB T-2022", "standard", clauses, {})
    m = models[0]
    assert len(m.content_text) <= 4000
    assert "截断后不应出现" not in m.content_text
    assert m.page_breaks == [[0, 1]]
    assert m.content_text.split("\n")[-1] == "甲" * (4000 - len("5.9.2 超长条款。") - 1)


def test_build_uncaptioned_table_identity():
    """B4：无题注表格条款（绑定全失配落单）不被 <4 守卫整表丢弃，
    title=「表(未识别题注，第N页)」，表体走 content_markdown。"""
    items = [MidItem(
        kind="table", html="<table><tr><td>A</td><td>B</td></tr></table>",
        caption="", page_idx=2, bbox=[60.0, 400.0, 530.0, 600.0])]
    clauses = split_items_into_clauses(items)
    assert len(clauses) == 1 and clauses[0].number.startswith("表")
    models, _ = build_clause_models("d", "GB T-2022", "standard", clauses, {})
    m = models[0]
    assert m.title == "表(未识别题注，第3页)", "给可读表格身份（B4）"
    assert m.table_summary is None
    assert m.content_markdown and "<table>" in m.content_markdown
    assert m.page_breaks == [[0, 3]]
    tbl = [s for s in m.source_spans if s.span_type == "table"]
    assert tbl and tbl[0].bbox == [60.0, 400.0, 530.0, 600.0]


def test_storage_roundtrip_page_breaks(db):
    """存储面：insert_clauses 写 page_breaks JSON → fetch_full_clause 读回一致；
    NULL（存量）读回 None。"""
    from src.core.domain.models import ClauseRevisionModel
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction

    if db.execute("SELECT 1 FROM doc_meta WHERE doc_id='pb1'").fetchone():
        clause_repo.delete_document("pb1")
    with write_transaction() as c:
        clause_repo.insert_document(c, dict(
            doc_id="pb1", standard_no="GB PB-2025", standard_name="页界测试",
            short_code="pb1", current_revision_id="r", domain_tags=[],
            file_path="pb.pdf", file_hash="hpb"))
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id="pb1c1", doc_id="pb1", clause_key="pb1k1",
            standard_no="GB PB-2025", clause_number="5.2.1",
            content_text="第一行。\n第二行。\n第三行。", knowledge_type="rule",
            modality="应", modality_strength=3, page_start=1, page_end=2,
            page_breaks=[[0, 1], [2, 2]]),
        ClauseRevisionModel(
            clause_revision_id="pb1c2", doc_id="pb1", clause_key="pb1k2",
            standard_no="GB PB-2025", clause_number="5.2.2",
            content_text="存量条款无页界。", knowledge_type="rule",
            modality="应", modality_strength=3, page_start=1, page_end=1),
    ])
    conn = db
    got = clause_repo.fetch_full_clause(conn, "pb1c1")
    assert got.page_breaks == [[0, 1], [2, 2]]
    got2 = clause_repo.fetch_full_clause(conn, "pb1c2")
    assert got2.page_breaks is None, "存量（NULL）读回 None，不编造页界"


def test_api_page_break_divider(client, db):
    """渲染面：page_breaks 非空 → 页号切换处插 <div class="page-break"
    data-page="N">（不增删正文行）；存量 NULL → 零分隔（零行为变化）。"""
    c, token = client
    from src.core.domain.models import ClauseRevisionModel
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction

    if db.execute("SELECT 1 FROM doc_meta WHERE doc_id='pb2'").fetchone():
        clause_repo.delete_document("pb2")
    with write_transaction() as txn:
        clause_repo.insert_document(txn, dict(
            doc_id="pb2", standard_no="GB PB2-2025", standard_name="渲染测试",
            short_code="pb2", current_revision_id="r", domain_tags=[],
            file_path="pb2.pdf", file_hash="hpb2"))
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id="pb2c1", doc_id="pb2", clause_key="pb2k1",
            standard_no="GB PB2-2025", clause_number="5.2.1",
            content_text="第一行内容。\n第二行内容。\n第三行内容。",
            knowledge_type="rule", modality="应", modality_strength=3,
            page_start=1, page_end=2, page_breaks=[[0, 1], [2, 2]]),
        ClauseRevisionModel(
            clause_revision_id="pb2c2", doc_id="pb2", clause_key="pb2k2",
            standard_no="GB PB2-2025", clause_number="5.2.2",
            content_text="存量条款。\n没有页界信息。",
            knowledge_type="rule", modality="应", modality_strength=3,
            page_start=1, page_end=1),
    ])
    r = c.get("/api/v1/documents/pb2/clauses",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    data = r.json()["data"]["clauses"]
    by_no = {cl["clause_number"]: cl for cl in data}
    html = by_no["5.2.1"]["content_html"]
    # 换页处（第 2 行 → 第 2 页）插分隔，且不吞正文
    assert '<div class="page-break" data-page="2"></div>' in html
    assert html.count("<p>") == 3, "三个正文行 → 三个 <p>（不增删正文行）"
    assert html.index("第二行内容。") < html.index("page-break") < \
        html.index("第三行内容。"), "分隔标记落在页界行之间"
    # 存量零行为变化
    legacy = by_no["5.2.2"]["content_html"]
    assert "page-break" not in legacy
    assert legacy.count("<p>") == 2


# ===== C2 插图入库 + C3 middle.json 兜底（2026-09-01 排版还原批次1） =====

_SHA_A = "a" * 64
_SHA_B = "b" * 64


def _mk_middle_with_image(tmp_path: Path) -> Path:
    """合成含 image 块的 middle.json：页 0 首块 = 无题注插图（current None →
    独立落单）；页 1 = 5.2.1 正文「如图1所示」+ 图1 题注插图（引用绑定）+
    一个图名不合规的插图（build 不渲染）。"""
    def _ln(content: str, bbox: list[float]) -> dict:
        return {"bbox": bbox, "spans": [{"type": "text", "content": content}]}

    mj = {"pdf_info": [
        {"page_idx": 0, "page_size": [595.0, 841.0], "para_blocks": [
            {"type": "image", "bbox": [80.0, 300.0, 500.0, 500.0], "blocks": [
                {"type": "image_body", "bbox": [80.0, 300.0, 500.0, 480.0],
                 "lines": [{"spans": [{"type": "image",
                                       "image_path": f"images/{_SHA_B}.jpg"}]}]},
            ]},
        ], "discarded_blocks": []},
        {"page_idx": 1, "page_size": [595.0, 841.0], "para_blocks": [
            {"type": "text", "bbox": [60.0, 700.0, 530.0, 720.0], "lines": [
                _ln("5.2.1 动火作业分级如图1所示。", [60.0, 700.0, 530.0, 720.0]),
            ]},
            {"type": "image", "bbox": [80.0, 400.0, 500.0, 620.0], "blocks": [
                {"type": "image_body", "bbox": [80.0, 400.0, 500.0, 600.0],
                 "lines": [{"spans": [{"type": "image",
                                       "image_path": f"images/{_SHA_A}.jpg"}]}]},
                {"type": "image_caption", "bbox": [80.0, 604.0, 500.0, 620.0],
                 "lines": [{"spans": [{"type": "text",
                                       "content": "图1 动火分级流程图"}]}]},
            ]},
            {"type": "image", "bbox": [80.0, 100.0, 500.0, 300.0], "blocks": [
                {"type": "image_body", "bbox": [80.0, 100.0, 500.0, 280.0],
                 "lines": [{"spans": [{"type": "image",
                                       "image_path": "images/not_hash.jpg"}]}]},
            ]},
        ], "discarded_blocks": []},
    ]}
    p = tmp_path / "img_middle.json"
    p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")
    return p


def test_pipeline_image_load_bind_figure_html(tmp_path):
    """C2：image 块进 MidItem；图N 按文内引用绑进 5.2.1；无题注独立落单得
    「图(未识别题注，第N页)」身份；figure_html 产 asset-embed 占位；
    content_text 零污染（插图不进正文行）。"""
    items, page_sizes = load_middle_items(_mk_middle_with_image(tmp_path))
    img_items = [i for i in items if i.kind == "image"]
    assert len(img_items) == 3, "image 块须进 MidItem（此前被整体跳过）"
    assert img_items[1].image_path == f"images/{_SHA_A}.jpg"
    assert img_items[1].caption == "图1 动火分级流程图"
    clauses = split_items_into_clauses(items)
    c521 = next(c for c in clauses if c.number == "5.2.1")
    bound = [it for it in c521.items if it.kind == "image"]
    assert len(bound) == 2, "图1 引用绑定 + 无题注插图物理就近绑定"
    solo = [c for c in clauses if c.number.startswith("图")]
    assert len(solo) == 1, "页 0 无题注插图（无 current）独立落单"
    models, _ = build_clause_models(
        "d1", "GB 30871-2022", "standard", clauses, page_sizes)
    m521 = next(m for m in models if m.clause_number == "5.2.1")
    fh = m521.figure_html or ""
    assert f'data-asset="{_SHA_A}.jpg"' in fh and 'class="asset-embed"' in fh
    assert "not_hash.jpg" not in fh, "图名不合规不渲染（白名单与 /assets 同款）"
    assert m521.content_text == "5.2.1 动火作业分级如图1所示。"
    m_solo = next(m for m in models if m.clause_number.startswith("图"))
    assert m_solo.title == "图(未识别题注，第1页)"
    assert f'data-asset="{_SHA_B}.jpg"' in (m_solo.figure_html or "")


def test_locate_middle_figure_fallback(tmp_path):
    """C3：/figure 文字层锚定失败 → middle.json image_caption 匹配图号取
    预裁剪插图；防穿越（../../ 逃逸拒绝）与未命中（图2）返回 None。"""
    from src.core.figure_locator import locate_middle_figure

    root = tmp_path / "parse_out" / "docX"
    img_dir = root / "mineru" / "auto" / "images"
    img_dir.mkdir(parents=True)
    (img_dir / f"{_SHA_A}.jpg").write_bytes(b"\xff\xd8fakejpg")
    (img_dir / f"{_SHA_B}.jpg").write_bytes(b"\xff\xd8fakejpg")

    def _img_block(caption: str | None, rel: str) -> dict:
        blocks = [{"type": "image_body", "bbox": [80, 400, 500, 600],
                   "lines": [{"spans": [{"type": "image", "image_path": rel}]}]}]
        if caption is not None:
            blocks.append({"type": "image_caption", "bbox": [80, 604, 500, 620],
                           "lines": [{"spans": [{"type": "text",
                                                 "content": caption}]}]})
        return {"type": "image", "bbox": [80, 400, 500, 620], "blocks": blocks}

    mj = {"pdf_info": [{"page_idx": 0, "page_size": [595.0, 841.0],
                        "para_blocks": [
                            # 穿越块在前：../../ 解析出 parse_root 之外 → 拒绝，
                            # 落到下一个合法 图1 块（首个命中必须仍是好文件）
                            _img_block("图1（续）", "../../outside/evil.jpg"),
                            _img_block("图1 动火分级流程图", f"images/{_SHA_A}.jpg"),
                            _img_block("图A.1 判别图", f"images/{_SHA_B}.jpg"),
                        ], "discarded_blocks": []}]}
    (root / "mineru" / "auto" / "x_middle.json").write_text(
        json.dumps(mj, ensure_ascii=False), encoding="utf-8")

    hit = locate_middle_figure(root, "1")
    assert hit is not None and hit.name == f"{_SHA_A}.jpg", "图1 → 预裁剪 jpg（穿越块被拒）"
    assert hit.suffix.lower() == ".jpg"
    assert locate_middle_figure(root, "A.1") is not None, "附图号 A.1 同样命中"
    assert locate_middle_figure(root, "2") is None, "未命中图号 → None"
    assert locate_middle_figure(tmp_path / "nope", "1") is None, "无 parse_root → None"


def test_locate_middle_figure_bare_image_path(tmp_path):
    """24276 实测回归：image_path 裸文件名（无 images/ 前缀）、物理文件在
    middle.json 同级 images/ 子目录 → 也能命中（MinerU 新旧产物双形态）。"""
    from src.core.figure_locator import locate_middle_figure

    root = tmp_path / "parse_out" / "docX"
    auto = root / "mineru" / "auto"
    (auto / "images").mkdir(parents=True)
    (auto / "images" / f"{_SHA_A}.jpg").write_bytes(b"\xff\xd8fakejpg")
    mj = {"pdf_info": [{"page_idx": 0, "page_size": [595.0, 841.0],
                        "para_blocks": [
                            {"type": "image", "bbox": [80, 400, 500, 620],
                             "blocks": [
                                 {"type": "image_body",
                                  "bbox": [80, 400, 500, 600],
                                  "lines": [{"spans": [{"type": "image",
                                                        "image_path": f"{_SHA_A}.jpg"}]}]},
                                 {"type": "image_caption",
                                  "bbox": [80, 604, 500, 620],
                                  "lines": [{"spans": [{"type": "text",
                                                        "content": "图 A.1 示例1,不带通风口和内部水平隔板但有裸露侧面的外壳的计算"}]}]},
                             ]}]}]}
    (auto / "x_middle.json").write_text(
        json.dumps(mj, ensure_ascii=False), encoding="utf-8")
    hit = locate_middle_figure(root, "A.1")
    assert hit is not None and hit.name == f"{_SHA_A}.jpg", "裸 image_path 命中 images/ 子目录"
    assert locate_middle_figure(root, "A.2") is None, "未命中图号仍 None"


def test_strip_keeps_caption_lines_with_table_tokens():
    """24276 实测回归：图题行 token（不带通风口/有效散热面积/1,25）与系数表
    列值天然重叠 → 覆盖判定误杀整行；行级白名单放行（页界 run-start 不随行
    陪葬），表格 token 泄漏流仍被剔，交叉引用句不受白名单影响。"""
    from src.core.text_utils import strip_embedded_table_text

    md = ("<table><tr><td>外壳类型</td><td>温度分布系数c</td></tr>"
          "<tr><td>不带通风口</td><td>1,25</td></tr></table>")
    cap4 = "图 4 不带通风口，有效散热面积A ₁ > 1 , 2 5 m ²的外壳的温度分布系数c"
    cap8 = "图 8 不带通风口，有效散热面积Ac≤1.25 m²的外壳的温度分布系数c"
    out = strip_embedded_table_text("6 设计评估\n" + cap4 + "\n" + cap8, md)
    assert cap4 in out and cap8 in out, "图题行（拉丁变量收尾）整行放行"
    leak = "带通风口 1,25 温度分布系数c 外壳类型"
    assert strip_embedded_table_text(leak, md) == "", "纯表格 token 流不放行"
    kept_ref = strip_embedded_table_text("图1所示的装置见表1。", md)
    assert "图1所示" in kept_ref, "句末标点收尾的交叉引用句不走图题白名单"
