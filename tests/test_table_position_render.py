# -*- coding: utf-8 -*-
"""2026-09-01 表格归位渲染（"表格到处跑"修复）。

根因：_content_html 旧实现把条款全部表格 html 一次性追加在正文末尾
（body += md）——跨页条款里第 10 页的表渲染在第 17 页文本之后，阅读序
与页界叙事错位。修复：按表格 span 页号把每张表插回原文页位（其页最后
一行之后、下一页页界标记之前）；无 span/页界/数量不对齐 → 旧末尾追加
（存量文档零行为变化）。
"""
import pytest

from src.core.storage import clause_repo


_TBL_MD = ("<table><tr><td>表甲</td></tr></table>"
           "<table><tr><td>表乙</td></tr></table>")
_TXT = "6 设计评估\n应当确定成套设备内的设备。\n如果不能，重新计算。\n验证完毕。"


def _seed(client, span_pages):
    """conftest 库为 session 级共享 → 每次先删旧档再种（幂等）。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    if conn.execute("SELECT 1 FROM doc_meta WHERE doc_id='doc_tblpos'").fetchone():
        clause_repo.delete_document("doc_tblpos")
    conn.execute(
        "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES ('doc_tblpos','GB TBLPOS-2025','表格归位','TBLPOS','r1','[]',"
        "'/x.pdf','h_tblpos')")
    conn.execute(
        "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
        " clause_key, clause_number, content_text, content_markdown, page_start,"
        " page_end, page_breaks)"
        " VALUES ('cr_tblpos','r1','doc_tblpos','k_tblpos','6',?,"
        " ?, 10, 12, '[[0,10],[2,12]]')", (_TXT, _TBL_MD))
    for so, pg in enumerate(span_pages):
        conn.execute(
            "INSERT INTO source_span (span_id, clause_revision_id,"
            " page_number, bbox_json, span_type, sort_order)"
            " VALUES (?,?,?,?,?,?)",
            (f"sp_tblpos_{so}", "cr_tblpos", pg, "[1,2,3,4]", "table", so))
    conn.commit()
    r = c.get("/api/v1/documents/doc_tblpos/clauses", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["data"]["clauses"][0]["content_html"]


def test_tables_interleaved_back_to_source_pages(client):
    """表甲（第10页）插在第10页两行之后、12页页界之前；表乙（第12页=末行
    页）缀尾；归位后每张表只出现一次（不再整体追加）。"""
    html = _seed(client, span_pages=[10, 12])
    assert html.count("<table>") == 2
    assert html.index("应当确定") < html.index("表甲") < \
        html.index('data-page="12"') < html.index("如果不能"), \
        "第10页的表必须落回第10页阅读流（页界标记之前）"
    assert html.index("验证完毕") < html.index("表乙"), \
        "末行页的表缀尾（其后无更晚页的行）"


def test_tables_tail_append_without_spans(client):
    """无表格 span（存量文档）→ 旧末尾追加行为，零变化。"""
    html = _seed(client, span_pages=[])
    assert html.index("验证完毕") < html.index("表甲") < html.index("表乙")


def test_tables_tail_append_on_span_count_mismatch(client):
    """span 数与 <table> 数不对齐（旧库部分 span 丢失）→ 宁可缀尾不可错位。"""
    html = _seed(client, span_pages=[10])
    assert html.index("验证完毕") < html.index("表甲"), \
        "数量不对齐 → 回退末尾追加（不可把第2张表错插到第10页）"
