"""middle_schema 契约测试（MinerU 4.0 结构变更根因修复配套，2026-10-07）。

锁定四件事：
 ① 3.4 产物**原样返回**（同一对象；既有调用方行为一字不变）；
 ② 4.0 产物归一成 3.4 形状（映射逐条：页尺寸/标题/表格 html/公式/丢弃块）；
 ③ **未知结构大声报错**，绝不静默返回空；
 ④ 端到端：`pipeline.load_middle_items` 吃 4.0 产物**不再返回 0 条**（本修复的验收路径）。

## 变异验证（本文件为什么这么写）
 · 把 `normalize_middle` 的 4.0 分支改回 `return mj` ⇒ `TestConvert40` 全红；
 · 把 `detect_schema` 的未知分支改成 `return SCHEMA_34`（静默） ⇒
   `TestGuard::test_unknown_shape_raises` 与 `test_load_middle_items_raises_not_silent` 全红；
 · 把 `_convert_40_to_34` 的 `pages`→`pdf_info` 那行删掉 ⇒ 端到端用例红。
"""
import json

import pytest

from src.core.ingestion.middle_schema import (
    SCHEMA_34, SCHEMA_40, MiddleSchemaError, detect_schema, load_middle_json,
    normalize_middle)


def _mj34() -> dict:
    return {"pdf_info": [{"page_idx": 0, "page_size": [595.0, 841.0],
                          "para_blocks": [{"type": "text",
                                           "lines": [{"spans": [{"type": "text",
                                                                 "content": "3.1 范围"}]}]}]}]}


def _mj40() -> dict:
    """一本最小但要覆盖各块型的 MinerU 4.0 产物。"""
    return {
        "schema": "docvortex.middle",
        "schema_version": "2.0",
        "is_full_document": True,
        "pages": [{
            "page_idx": 0,
            "blocks": [
                {"type": "header", "index": 0, "bbox": [0, 0, 1, 1],
                 "content": [{"type": "text", "content": "ICS 29.180"}]},
                {"type": "doc_title", "index": 1, "bbox": [1, 2, 3, 4], "level": 1,
                 "content": [{"type": "text", "content": "中华人民共和国国家标准"}]},
                {"type": "paragraph_title", "index": 2, "bbox": [1, 2, 3, 4], "level": 2,
                 "content": [{"type": "text", "content": "7 技术要求"}]},
                {"type": "text", "index": 3, "bbox": [1, 2, 3, 4],
                 "content": [{"type": "text", "content": "7.1 一般要求 "},
                             {"type": "equation_inline", "content": "\\frac{1}{2}"},
                             {"type": "text", "content": " 应符合表 1。"}]},
                # 4.0 的 content 会**嵌套**（实测 GB 39800.8-2024 触发过 TypeError）
                {"type": "text", "index": 4, "bbox": [1, 2, 3, 4],
                 "content": [{"type": "text", "content": [{"type": "text", "content": "嵌套文本"}]}]},
                {"type": "equation", "index": 5, "bbox": [1, 2, 3, 4],
                 "content": "I = \\frac {U}{Z}"},
                {"type": "table", "index": 6, "bbox": [1, 2, 3, 4],
                 "content": [{"type": "table_caption", "content": "表 1 短路阻抗"},
                             {"type": "table_body",
                              "content": "<table><tr><td>25~630</td><td>4.0</td></tr></table>"}]},
                {"type": "image", "index": 7, "bbox": [1, 2, 3, 4],
                 "content": [{"type": "image_caption", "content": "图 1 结构"},
                             {"type": "image_body", "image_path": "images/page_0_image_7.jpg"}]},
                {"type": "chart", "index": 8, "bbox": [1, 2, 3, 4],
                 "content": [{"type": "chart_caption", "content": "图 2 曲线"}]},
                {"type": "page_number", "index": 9, "bbox": [0, 0, 1, 1],
                 "content": [{"type": "text", "content": "1"}]},
                {"type": "footer", "index": 10, "bbox": [0, 0, 1, 1],
                 "content": [{"type": "text", "content": "页脚"}]},
            ],
        }],
        "extensions": {"mineru": {"tier": "standard", "parse_mode": "ocr"},
                       "docvortex_layout": {"version": 1,
                                            "pages": [{"page_idx": 0,
                                                       "width_pt": 2455.0,
                                                       "height_pt": 3465.0}]}},
        "metadata": {"file_suffix": "pdf"},
    }


class TestDetect:
    def test_detects_34(self):
        assert detect_schema(_mj34()) == SCHEMA_34

    def test_detects_40(self):
        assert detect_schema(_mj40()) == SCHEMA_40

    def test_pdf_info_wins_when_both(self):
        # 两个键都在时以 3.4 为准（历史行为优先，避免把老产物误归一）
        both = dict(_mj34(), pages=[{"page_idx": 0, "blocks": []}])
        assert detect_schema(both) == SCHEMA_34

    def test_unknown_shape_raises(self):
        with pytest.raises(MiddleSchemaError, match="无法识别"):
            detect_schema({"foo": 1})

    def test_non_dict_raises(self):
        with pytest.raises(MiddleSchemaError):
            detect_schema(["not", "a", "dict"])

    def test_empty_object_raises(self):
        with pytest.raises(MiddleSchemaError):
            detect_schema({})


class TestNormalize34:
    def test_identity_same_object(self):
        mj = _mj34()
        assert normalize_middle(mj) is mj          # 不复制、不改写

    def test_no_mutation_of_input(self):
        mj = _mj34()
        before = json.dumps(mj, sort_keys=True)
        normalize_middle(mj)
        assert json.dumps(mj, sort_keys=True) == before


class TestConvert40:
    def test_root_key_is_pdf_info(self):
        out = normalize_middle(_mj40())
        assert "pdf_info" in out and len(out["pdf_info"]) == 1
        assert out["pdf_info"][0]["page_idx"] == 0

    def test_page_size_from_docvortex_layout(self):
        # 不取 docvortex_layout 就拿不到真实页尺寸（会退化成默认 595x841）
        assert normalize_middle(_mj40())["pdf_info"][0]["page_size"] == [2455.0, 3465.0]

    def test_discarded_blocks_excluded_from_para_blocks(self):
        pg = normalize_middle(_mj40())["pdf_info"][0]
        assert [b["type"] for b in pg["discarded_blocks"]] == ["header", "page_number", "footer"]
        assert not ({"header", "footer", "page_number"} &
                    {b["type"] for b in pg["para_blocks"]})

    def test_title_types_mapped(self):
        types = [b["type"] for b in normalize_middle(_mj40())["pdf_info"][0]["para_blocks"]]
        assert "title" in types
        assert "doc_title" not in types and "paragraph_title" not in types

    def test_inline_equation_kept(self):
        # 丢了行内公式 ⇒ 正文会变成"7.1 一般要求  应符合表 1。"（内容缺失）
        para = normalize_middle(_mj40())["pdf_info"][0]["para_blocks"]
        text_block = next(b for b in para if b["type"] == "text"
                          and any(s["type"] == "text" and "一般要求" in s.get("content", "")
                                  for ln in b["lines"] for s in ln["spans"]))
        kinds = [s["type"] for ln in text_block["lines"] for s in ln["spans"]]
        assert "inline_equation" in kinds

    def test_standalone_equation_block(self):
        para = normalize_middle(_mj40())["pdf_info"][0]["para_blocks"]
        eq = [b for b in para if any(s["type"] == "interline_equation"
                                     for ln in b.get("lines", []) for s in ln["spans"])]
        assert eq, "独立公式块必须变成带 interline_equation 的文本块"

    def test_nested_content_flattened(self):
        # 不展平 ⇒ _spans_rows_scored 的 "".join(parts) 收到 list ⇒ TypeError
        para = normalize_middle(_mj40())["pdf_info"][0]["para_blocks"]
        flat = [s for b in para for ln in b.get("lines", []) for s in ln["spans"]]
        assert all(isinstance(s.get("content", ""), str)
                   for s in flat if s["type"] in ("text", "inline_equation"))

    def test_table_caption_and_html(self):
        para = normalize_middle(_mj40())["pdf_info"][0]["para_blocks"]
        tbl = next(b for b in para if b["type"] == "table")
        assert [s["type"] for s in tbl["blocks"]] == ["table_caption", "table_body"]
        html = tbl["blocks"][1]["lines"][0]["spans"][0]["html"]
        assert html.startswith("<table>") and "4.0" in html

    def test_image_body_path(self):
        para = normalize_middle(_mj40())["pdf_info"][0]["para_blocks"]
        img = next(b for b in para if b["type"] == "image")
        body = next(s for s in img["blocks"] if s["type"] == "image_body")
        assert body["lines"][0]["spans"][0]["image_path"] == "images/page_0_image_7.jpg"

    def test_chart_caption_kept(self):
        para = normalize_middle(_mj40())["pdf_info"][0]["para_blocks"]
        chart = [b for b in para if b["type"] == "chart"]
        assert chart and chart[0]["blocks"][0]["type"] == "chart_caption"

    def test_empty_pages_ok(self):
        out = normalize_middle({"pages": [{"page_idx": 0, "blocks": []}]})
        assert out["pdf_info"][0]["para_blocks"] == []

    def test_missing_docvortex_falls_back(self):
        out = normalize_middle({"pages": [{"page_idx": 0, "blocks": []}]})
        assert out["pdf_info"][0]["page_size"] == [595.0, 841.0]


class TestLoadJson:
    def test_reads_and_normalizes_40(self, tmp_path):
        p = tmp_path / "m.json"
        p.write_text(json.dumps(_mj40()), encoding="utf-8")
        assert load_middle_json(p)["pdf_info"][0]["page_size"] == [2455.0, 3465.0]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(MiddleSchemaError, match="读取/解析失败"):
            load_middle_json(tmp_path / "nope.json")

    def test_bad_json_raises(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{ not json", encoding="utf-8")
        with pytest.raises(MiddleSchemaError):
            load_middle_json(p)

    def test_unknown_shape_raises(self, tmp_path):
        p = tmp_path / "x.json"
        p.write_text(json.dumps({"whatever": 1}), encoding="utf-8")
        with pytest.raises(MiddleSchemaError, match="无法识别"):
            load_middle_json(p)


class TestGuard:
    """**本修复的验收路径**：4.0 能被消费，未知结构大声报错（不静默返回空）。"""

    def test_load_middle_items_consumes_40(self, tmp_path):
        from src.core.ingestion.pipeline import load_middle_items
        p = tmp_path / "m.json"
        p.write_text(json.dumps(_mj40()), encoding="utf-8")
        items, page_sizes = load_middle_items(p)
        assert items, "4.0 产物必须产出条目（修复前此处恒为 []，即静默 0 条）"
        assert page_sizes[0] == (2455.0, 3465.0)
        assert any(it.kind == "table" and it.html for it in items)

    def test_load_middle_items_splits_40_into_clauses(self, tmp_path):
        from src.core.ingestion.pipeline import load_middle_items, split_items_into_clauses
        mj = _mj40()
        mj["pages"][0]["blocks"].append(
            {"type": "text", "index": 11, "bbox": [1, 2, 3, 4],
             "content": [{"type": "text", "content": "7.2 检验方法 按 GB/T 1 进行。"}]})
        p = tmp_path / "m.json"
        p.write_text(json.dumps(mj), encoding="utf-8")
        items, _ = load_middle_items(p)
        nums = [c.number for c in split_items_into_clauses(items)]
        assert "7.1" in nums and "7.2" in nums

    def test_load_middle_items_raises_not_silent(self, tmp_path):
        """未知结构必须**抛**，不许像修复前那样 `mj.get("pdf_info", [])` 静默给空。"""
        from src.core.ingestion.pipeline import load_middle_items
        p = tmp_path / "m.json"
        p.write_text(json.dumps({"schema": "something.else", "data": []}), encoding="utf-8")
        with pytest.raises(MiddleSchemaError):
            load_middle_items(p)

    def test_cloud_guard_accepts_40(self, tmp_path):
        from src.core.ingestion.mineru_cloud import _validate_middle
        p = tmp_path / "m.json"
        p.write_text(json.dumps(_mj40()), encoding="utf-8")
        _validate_middle(p)          # 不抛 = 通过

    def test_cloud_guard_rejects_unknown(self, tmp_path):
        from src.core.ingestion.mineru_cloud import MineruCloudError, _validate_middle
        p = tmp_path / "m.json"
        p.write_text(json.dumps({"foo": 1}), encoding="utf-8")
        with pytest.raises(MineruCloudError, match="非同构产物"):
            _validate_middle(p)

    def test_cloud_guard_rejects_empty_pdf_info(self, tmp_path):
        from src.core.ingestion.mineru_cloud import MineruCloudError, _validate_middle
        p = tmp_path / "m.json"
        p.write_text(json.dumps({"pdf_info": []}), encoding="utf-8")
        with pytest.raises(MineruCloudError):
            _validate_middle(p)
