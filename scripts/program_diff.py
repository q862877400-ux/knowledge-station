# -*- coding: utf-8 -*-
"""自动对账工具：用 fitz 提取原 PDF 的 图/表题注 + 特殊符号，与库 content_text/content_html 对账，
自动输出「原文有、库里缺/错」的缺失清单。不依赖人工肉眼，解决逐屏对比看漏问题。

用法：python scripts/program_diff.py <pdf_path> <doc_id> [--no-db] [--std <no>]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fitz  # noqa: E402

# 图/表题注：图A.1 / 表B.2 / 图1 / 表5
_FIG = re.compile(r"图\s*([A-Za-z]?\s*\.?\s*\d+(?:\.\d+)*)")
_TAB = re.compile(r"表\s*([A-Za-z]?\s*\.?\s*\d+(?:\.\d+)*)")
# 特殊符号/上下标（会被 PUA 形近/全角/combining 表示，库常丢）
_SYM = re.compile(r"[ĈĈĉĉĈC̄C̄Ĉᵢᵢₜₐ±×÷≈≤≥⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉]|[\u0302\u0304\u0300\u0301\uFF3E\uFF3F^_-]")


def _norm(s: str) -> str:
    """形近/PUA/全角归一→拉丁（与钱库内容对齐）。"""
    from src.core.text_utils import normalize_pua_latin
    return normalize_pua_latin(s or "")


def collect_pdf(pdf: Path, normalize=True) -> dict:
    """fitz 逐页提取图/表题注、特殊符号。"""
    figs, tabs, syms = set(), set(), []
    with fitz.open(str(pdf)) as d:
        for i in range(len(d)):
            t = d[i].get_text()
            if normalize:
                t = _norm(t)
            for m in _FIG.finditer(t):
                figs.add(m.group(1))
            for m in _TAB.finditer(t):
                tabs.add(m.group(1))
            for ch in t:
                if _SYM.match(ch):
                    syms.append(ch)
    return {"figs": figs, "tabs": tabs, "syms": syms}


def collect_db(doc_id: str) -> dict:
    import sqlite3
    con = sqlite3.connect(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
    con.row_factory = sqlite3.Row
    # 收集全部条款的 content_text / content_markdown / figure_html
    rows = con.execute(
        "SELECT content_text, content_markdown, figure_html FROM clause_revision WHERE doc_id=?",
        (doc_id,)).fetchall()
    con.close()
    body = " ".join((r["content_text"] or "") + " " + (r["content_markdown"] or "") +
                    " " + (r["figure_html"] or "") for r in rows)
    return {"body": body}


def diff(pdf: Path, doc_id: str, normalize=True) -> dict:
    p = collect_pdf(pdf, normalize)
    b = collect_db(doc_id)
    body = b["body"]
    missing_figs = sorted(f for f in p["figs"] if f and f not in body)
    missing_tabs = sorted(t for t in p["tabs"] if t and t not in body)
    # 符号：PDF 有的特殊符号在库 body 缺失（含 combining 帽/上划线等）
    sym_counts = {c: p["syms"].count(c) for c in set(p["syms"])}
    missing_syms = [c for c, n in sym_counts.items() if c not in body and n > 0]
    return {"missing_figs": missing_figs, "missing_tabs": missing_tabs,
            "missing_syms": missing_syms, "fig_count": len(p["figs"]),
            "tab_count": len(p["tabs"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("doc_id")
    ap.add_argument("--raw", action="store_true", help="不做 PUA 归一(原样提取)")
    a = ap.parse_args()
    res = diff(Path(a.pdf), a.doc_id, normalize=not a.raw)
    print("图题注总数:", res["fig_count"], " 缺失题注:", res["missing_figs"])
    print("表题注总数:", res["tab_count"], " 缺失题注:", res["missing_tabs"])
    print("特殊符号缺失:", res["missing_syms"])


if __name__ == "__main__":
    main()
