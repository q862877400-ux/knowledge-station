"""图例归图契约测试（2026-09-15，figure-neighborhood 类跨 3 文档达线根因修复）。

问题：图内「标引序号说明 + N——标签」清单被 OCR 成低分文本块并当作条款正文
并入 → ①正文混入图例乱码（GB/T 10671 实测 '标可序影视听：/ 1 供：…下光衡：'）
②条款 ocr_confidence 被图内文字拖低（虚假告警）。
修复：条目层识别图例块 → 并入紧邻图条目的 caption（内容不丢、随图渲染）。
"""
import json

from src.core.ingestion.pipeline import (
    _is_figure_legend, _legend_follows_image, load_middle_items,
    split_items_into_clauses,
)


class TestLegendDetect:
    def test_header_standard(self):
        assert _is_figure_legend("标引序号说明：\n1——试样：")

    def test_header_garbled_ocr(self):
        # 10671 实测乱码变体（'说明' → '视听'）
        assert _is_figure_legend("标可序影视听：")

    def test_single_line_multi_items(self):
        # 实测图例常压成一行多项（初版逐行 match 只数到 1 而漏判）
        assert _is_figure_legend("1——托架：5——辐射锥：9——控制盒：")

    def test_two_item_lines(self):
        assert _is_figure_legend("1——试样：\n2——铝箔：")

    def test_normal_clause_not_legend(self):
        assert not _is_figure_legend("7.4.4 试样盒上的小槽内应铺有铝箔。")
        assert not _is_figure_legend("5.1 试验样机\n试验样机应符合要求。")

    def test_mention_without_items_not_legend(self):
        assert not _is_figure_legend("标引序号说明见附录。")

    def test_empty(self):
        assert not _is_figure_legend("")
        assert not _is_figure_legend(None)


class TestLegendGeometry:
    def test_adjacent_below_top_origin(self):
        # 实测 10671 p4：图 bbox y 166..421，图例 y 446..459（相邻边距 25）
        assert _legend_follows_image([86, 446, 150, 459], [107, 166, 294, 421])

    def test_adjacent_above_image_accepted(self):
        # 方向无关：图例在图**上方**同样接受（取两框最近边距，不写死 y 方向）
        assert _legend_follows_image([86, 100, 150, 113], [107, 166, 294, 421])

    def test_far_block_rejected(self):
        assert not _legend_follows_image([86, 700, 150, 713], [107, 166, 294, 421])

    def test_x_far_rejected(self):
        assert not _legend_follows_image([400, 446, 500, 459], [107, 166, 294, 421])

    def test_missing_bbox(self):
        assert not _legend_follows_image(None, [1, 2, 3, 4])
        assert not _legend_follows_image([1, 2, 3], [1, 2, 3, 4])


def _mj_with_image_and_legend(legend_bbox, img_bbox, legend_text) -> dict:
    return {"pdf_info": [{"page_idx": 0, "page_size": [595.0, 841.0], "para_blocks": [
        {"type": "text", "bbox": [60, 100, 530, 130], "lines": [
            {"bbox": [60, 100, 530, 120],
             "spans": [{"type": "text", "content": "7.4.4 试样盒上的小槽内应铺有铝箔。"}]}]},
        {"type": "image", "bbox": img_bbox, "blocks": [
            {"type": "image_body", "lines": [{"bbox": img_bbox, "spans": [
                {"type": "image", "image_path": "images/abc.jpg"}]}]}]},
        {"type": "text", "bbox": legend_bbox, "lines": [
            {"bbox": legend_bbox, "spans": [{"type": "text", "content": t}]}
            for t in legend_text]},
    ]}]}


class TestIntegration:
    def test_legend_attached_to_figure_not_clause(self, tmp_path):
        mj = _mj_with_image_and_legend(
            [86, 446, 300, 480], [107, 166, 294, 421],
            ["标引序号说明：", "1——试样：", "2——铝箔："])
        p = tmp_path / "legend.json"
        p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")
        items, _ = load_middle_items(p)
        img = [i for i in items if i.kind == "image"]
        assert img and "标引序号" in (img[0].text or ""), "图例应并入图条目"
        clauses = split_items_into_clauses(items)
        body = "\n".join(t for c in clauses for t in c.texts)
        assert "标引序号说明" not in body, "图例不得混入条款正文"
        assert "1——试样" not in body

    def test_far_legend_stays_text(self, tmp_path):
        # 反向控制：离图很远 → 保守不动（宁可不归，不可误删正文）
        mj = _mj_with_image_and_legend(
            [86, 700, 300, 760], [107, 166, 294, 421],
            ["标引序号说明：", "1——试样："])
        p = tmp_path / "far.json"
        p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")
        items, _ = load_middle_items(p)
        assert any(i.kind == "text" and "标引序号" in (i.text or "") for i in items)

    def test_clause_text_kept(self, tmp_path):
        mj = _mj_with_image_and_legend(
            [86, 446, 300, 480], [107, 166, 294, 421], ["标引序号说明：", "1——试样："])
        p = tmp_path / "keep.json"
        p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")
        items, _ = load_middle_items(p)
        clauses = split_items_into_clauses(items)
        body = "\n".join(t for c in clauses for t in c.texts)
        assert "应铺有铝箔" in body, "真条款正文不得受影响"
