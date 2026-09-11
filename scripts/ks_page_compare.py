# -*- coding: utf-8 -*-
"""逐页「预览渲染 vs 原文扫描」成对截图 + VLM 对比核对脚本（用户验收方法论）。

原则（2026-09-02 用户要求）：每次修复 BUG 截图检查时——
1. 每一页**预览窗口**截图（渲染结果）
2. 每一页**原文窗口**截图（PDF 扫描图）
3. 成对作 **VLM 分析对比**——重点发现「最初 OCR 识别就错」的数据层问题
   （渲染正确但 OCR 把扫描图认错：公式/数字/汉字/图错），而非仅渲染错误。

产出：<TMP>/pagecmp/ 下每页 orig_pN.png（原文）与 prev_pN.png（预览），
并输出 JSON 清单（成对路径 + 页号 + 可选高亮）。VLM 逐页 read_image 对比。
"""
import subprocess
import os
import sys
import time
import json
import shutil
import base64
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

TMP = Path(os.environ.get("TEMP", r"C:\Users\Zegel\AppData\Local\Temp"))
OUT = TMP / "pagecmp"
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://127.0.0.1:5173"
import sys as _sys
DOC_ID = (_sys.argv[1] if len(_sys.argv) > 1
          else "doc_01M1FF6SDVG04BYZ8DS5KYCT3F")

_B4EXE = (shutil.which("browser4-cli")
          or r"C:\Users\Zegel\AppData\Roaming\npm\browser4-cli\bin\browser4-cli-win32-x64.exe")


def b4(*args):
    r = subprocess.run([_B4EXE, *args], capture_output=True,
                       text=True, timeout=120)
    return (r.stdout or r.stderr)


def ev(js):
    b = base64.b64encode(js.encode("utf-8")).decode()
    return b4("eval", "--base64", b, "--json")


def shot(name):
    p = OUT / f"{name}.png"
    # 只截预览文本窗格 .fulltext（用户要求：不要整窗口，左栏 QA/目录不截）
    b4("screenshot", ".fulltext", "-o", str(p))
    return p


def render_orig(pdf, n_pages):
    """原文逐页：直接提取 PDF 页**嵌入的原始扫描位图**（get_image_info → 
    extract_image），不经 get_pixmap 渲染、不经任何 OCR——与用户在 PDF 里
    看到的一致（对比基准必须是原画面，用户 2026-09-02 要求）。"""
    doc = fitz.open(str(pdf))
    for i in range(n_pages):
        page = doc[i]
        saved = False
        try:
            infos = page.get_image_info(xrefs=True)
            # 扫描页通常 1 张覆盖全页的图；取面积最大者（防子图优先）
            best = None
            best_area = 0.0
            for inf in infos:
                xref = inf.get("xref")
                if not xref:
                    continue
                bbox = inf.get("bbox", (0, 0, 0, 0))
                area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                if area > best_area:
                    best_area = area
                    best = (xref, inf.get("ext", "jpg"))
            if best:
                d = doc.extract_image(best[0])
                ext = d.get("ext", "jpg")
                (OUT / f"orig_p{i + 1}.{ext}").write_bytes(d["image"])
                saved = True
        except Exception:
            saved = False
        if not saved:
            # 兜底：无嵌入图（程序生成 PDF）则渲染页
            page.get_pixmap(dpi=150).save(str(OUT / f"orig_p{i + 1}.png"))
    doc.close()


def preview_open(standard_no: str):
    b4("open", "--headed", "--fresh", URL)
    time.sleep(6)
    ev('''() => { const b = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim()==='📚 文件目录'); if (b && !document.querySelector('.toc-drawer')) b.click(); return 'n'; }''')
    time.sleep(1)
    # 2026-09-02 修复：用目标文档标准号（非硬编码 24276）→ 目录搜索/打开随配置文档
    q = standard_no.replace(" ", "").replace("／", "/").replace("／", "/") \
        .split("—")[0] if standard_no else "24276"
    ev(f'''() => {{ const i = document.querySelector('.toc-drawer input'); const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(i,{q!r}); i.dispatchEvent(new Event('input',{{bubbles:true}})); return 'q'; }}''')
    time.sleep(1)
    ev(f'''() => {{ const d = document.querySelector('.toc-drawer'); const h = Array.from(d.querySelectorAll('*')).find(e => (e.textContent.trim()==={standard_no!r} || e.textContent.includes({q!r})) && e.children.length===0); if (h) h.click(); return 'opened'; }}''')
    time.sleep(10)


def preview_scroll_shot(n_pages):
    """预览逐页滚动到 [data-page=N] 页界并截图。"""
    for i in range(1, n_pages + 1):
        ev(f'''() => {{ const pv = document.querySelector('.fulltext'); const pb = Array.from(pv.querySelectorAll('.page-break')).find(x => x.dataset.page==='{i}'); if (pb) pb.scrollIntoView({{ block: 'start' }}); return 'p{i}'; }}''')
        time.sleep(0.6)
        shot(f"prev_p{i}")
        print(f"  prev_p{i} done")


def main():
    # 原文 PDF 路径（从引擎查库）
    import sqlite3
    db = r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db"
    con = sqlite3.connect(db)
    pdf = con.execute("SELECT file_path FROM doc_meta WHERE doc_id=?",
                      (DOC_ID,)).fetchone()[0]
    std = con.execute("SELECT standard_no FROM doc_meta WHERE doc_id=?",
                      (DOC_ID,)).fetchone()
    con.close()
    doc = fitz.open(str(pdf))
    n_pages = len(doc)
    doc.close()

    print(f"[orig] 渲染 {n_pages} 页原文")
    render_orig(pdf, n_pages)

    print(f"[prev] 打开预览 {std}")
    preview_open(std[0] if std else None)

    print("[prev] 逐页滚动截图")
    preview_scroll_shot(n_pages)

    manifest = [{"page": i, "orig": str(OUT / f"orig_p{i}.png"),
                 "prev": str(OUT / f"prev_p{i}.png")} for i in range(1, n_pages + 1)]
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[done] 成对截图清单: {OUT}")
    print("VLM 逐页对比：read_image 每页 orig_pN.png + prev_pN.png")


if __name__ == "__main__":
    main()
