# -*- coding: utf-8 -*-
"""封面发布/实施日期提取测试（2026-08-29，通用修复）。

入库此前从不填 published_at/effective_from → 全库 UI 发布/生效恒"—"。
封面提取正则须覆盖：ISO 连排（GB 25596-2025 实测"2025-03-16发布⏎2027-03-16实施"）、
年月日排版（"2025年3月16日发布"）、带空格、容错分隔符。
2026-09-01（GB/T 24276 实测）补：扫描版 fitz 文本层为空 → middle.json 前 2 页
兜底提取；及 E8 闸门 3（折行行首"1.5m时，…"量值+单位非条款头）。
"""
from __future__ import annotations

import json

from src.core.ingestion.pipeline import (
    _COVER_EFF,
    _COVER_PUB,
    _middle_cover_blocks,
    _plausible_clause_head,
)


def test_iso_compact_cover():
    """GB 封面实测形态：ISO 连排 + 换行分隔。"""
    text = "中华人民共和国国家标准\nGB 25596-2025\n食品安全国家标准\n2025-03-16发布\n2027-03-16实施"
    m = _COVER_PUB.search(text)
    assert m and (m.group(1), m.group(2), m.group(3)) == ("2025", "03", "16")
    m2 = _COVER_EFF.search(text)
    assert m2 and (m2.group(1), m2.group(2), m2.group(3)) == ("2027", "03", "16")


def test_cjk_year_month_day():
    """行标常见"2025年3月16日发布"排版 → 归一化 2025-03-16。"""
    m = _COVER_PUB.search("2025年3月16日发布")
    assert m and f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" == "2025-03-16"


def test_spaced_and_slash_variants():
    """带空格 / 斜杠分隔 / 全角括注容忍。"""
    assert _COVER_PUB.search("2025 - 03 - 16 发布")
    assert _COVER_EFF.search("2027/3/16实施")
    assert _COVER_PUB.search("2025.03.16发布")


def test_body_mention_not_cover_only_scope():
    """正则只认"数字+发布/实施"连排；正文引用如"于2025-03-16发布"也命中
    （提取器仅扫前两页，正文页不会进入扫描范围——双层防护）。"""
    assert _COVER_PUB.search("本标准于2025-03-16发布")


def test_no_false_hit_on_clause_numbers():
    """条款号/标准号不误触发（"GB 25596-2025"无发布/实施词）。"""
    assert not _COVER_PUB.search("GB 25596-2025")
    assert not _COVER_EFF.search("3.1.2 应符合表4的规定 2025-03-16")


def test_missing_leaves_none():
    """无封面日期 → 诚实留空（不猜测）。"""
    assert not _COVER_PUB.search("封面残缺无日期")


def test_middle_cover_blocks_fallback(tmp_path):
    """扫描版兜底：fitz 文本层为空时，从 middle.json 前 2 页提取封面块。
    GB/T 24276 实测封面形态：'2017-11-01 发布' / '2018-05-01 实施'。"""
    mj = {
        "pdf_info": [
            {"page_idx": 0, "para_blocks": [
                {"type": "text", "lines": [{"spans": [
                    {"content": "中华人民共和国国家标准"}]}]},
                {"type": "image"},
                {"type": "text", "lines": [{"spans": [
                    {"content": "2017-11-01 发布"}]}]},
                {"type": "text", "lines": [{"spans": [
                    {"content": "2018-05-01 实施"}]}]},
            ]},
            {"page_idx": 1, "para_blocks": [
                {"type": "text", "blocks": [{"lines": [{"spans": [
                    {"content": "目  次"}]}]}]},
            ]},
        ]
    }
    p = tmp_path / "x_middle.json"
    p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")
    blocks = _middle_cover_blocks(p)
    assert [b["page_number"] for b in blocks] == [1, 1, 1, 2]
    pub = _COVER_PUB.search(_nfkc(blocks))
    eff = _COVER_EFF.search(_nfkc(blocks))
    assert pub and (pub.group(1), pub.group(2), pub.group(3)) == ("2017", "11", "01")
    assert eff and (eff.group(1), eff.group(2), eff.group(3)) == ("2018", "05", "01")


def _nfkc(blocks: list[dict]) -> str:
    import unicodedata
    return "\n".join(unicodedata.normalize("NFKC", b["text"]) for b in blocks)


def test_middle_cover_blocks_missing_file(tmp_path):
    """middle.json 缺失/坏件 → 空表（诚实留空）。"""
    assert _middle_cover_blocks(tmp_path / "nope_middle.json") == []


def test_gate3_value_unit_wrap_not_clause_head():
    """E8 闸门 3（2026-09-01）：正文折行后行首"1.5m时，为了计算…"是量值+单位
    续句，不是条款头——GB/T 24276 曾被切成假条款"1.5"。"""
    assert not _plausible_clause_head("1.5", "m时，为了计算将外壳划分为虚拟的柜架单元")
    assert not _plausible_clause_head("3.2", "mm厚的钢板应…")
    # 真条款头不受扰：中文标题 / 大写字母类目 / 后随拉丁的术语
    assert _plausible_clause_head("5.2.1", "通则")
    assert _plausible_clause_head("5.2", "A类评定")
    assert _plausible_clause_head("2.3", "pH值的测定")
    # 闸门 2（表格数值行）继续生效
    assert not _plausible_clause_head("4.2", "1 1.5 3.0")
