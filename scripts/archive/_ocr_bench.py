# -*- coding: utf-8 -*-
"""OCR/解析途径基准测试（2026-08-27）：找最优分流。

对比：
- 有文本层 PDF：PyMuPDF 直接提取（预期秒级）
- 无文本层 PDF：scnet per-page（API key） vs MinerU 整本深度分析（本地）
输出各途径耗时/字符数，供"哪种文件走哪条路"决策。
"""
import sys, time, json
from pathlib import Path
sys.path.insert(0, r"D:\AI\work space\zcode")
from src.core.ingestion.mineru_adapter import _extract_text_blocks, _ocr_pdf_with_scnet

def bench(label, fn, *args):
    t0 = time.time()
    try:
        out = fn(*args)
        dt = time.time() - t0
        n = len(out) if isinstance(out, (list, str)) else 0
        print(f"[{label}] {dt:.1f}s items={n}", flush=True)
        return out, dt
    except Exception as e:
        print(f"[{label}] 失败 {type(e).__name__}: {str(e)[:120]}", flush=True)
        return None, time.time() - t0

text_pdf = Path(r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)")  # 占位
import fitz

def find_pdf(root, needle):
    root = Path(root)
    for p in root.rglob("*.pdf"):
        if needle.lower() in p.name.lower():
            return p
    return None

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="国标目录")
    ap.add_argument("--text", required=True, help="有文本层 PDF 文件名子串")
    ap.add_argument("--nolayer", required=True, help="无文本层 PDF 文件名子串")
    args = ap.parse_args()

    tp = find_pdf(args.dir, args.text)
    np_ = find_pdf(args.dir, args.nolayer)
    print(f"有文本层: {tp}") if tp else print(f"未找到 {args.text}")
    print(f"无文本层: {np_}") if np_ else print(f"未找到 {args.nolayer}")

    if tp:
        doc = fitz.open(str(tp)); pages = len(doc); doc.close()
        print(f"--- 有文本层 {tp.name} ({pages}页) ---", flush=True)
        bench("PyMuPDF 提取", _extract_text_blocks, tp)
    if np_:
        doc = fitz.open(str(np_)); pages = len(doc); doc.close()
        print(f"--- 无文本层 {np_.name} ({pages}页) ---", flush=True)
        bench("scnet per-page", _ocr_pdf_with_scnet, np_)
