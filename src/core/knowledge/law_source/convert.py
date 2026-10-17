"""docx → PDF 转换链（方案 §3）：LibreOffice headless 主选 → WPS/Word COM 回退。

转换源头只允许官方 docx；本模块不做任何"网页文字版重排版"路径。
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def find_libreoffice() -> Path | None:
    """探测 soffice 可执行。

    ## 取值顺序（2026-10-18 加第 1 级）

      1. **`$KS_SOFFICE`** —— 部署方显式指定（与 `KS_PYTHON`/`KS_DATA_DIR` 同一套约定）。
         便携包场景要的就是这一级：LibreOffice 可以放在包里任意位置，
         **不必**是系统安装目录。
      2. 两个**标准安装位置**（`C:\\Program Files[ (x86)]\\LibreOffice\\program`，
         另加 `D:` 盘那份 —— 本机实测装在 D:）
      3. `PATH` 上的 `soffice`

    ## 为什么这里可以有"写死盘符"（与 `docs/PORTABILITY.md` 的纪律不矛盾）

    那三条写的是**"这个程序通常装在哪"**，不是**"我的数据在哪"**：
    换了机器、装了 LibreOffice，它就在那儿；没装，`None` ⇒ 走 COM 回退。
    ⚠ 它**不是硬依赖**：`convert_docx_to_pdf` 有完整降级链
    （LibreOffice → 完整性校验 → WPS/Word COM → 校验 → 空串），
    没有 LibreOffice 只是"这条通道不可用"，**不是"KS 跑不起来"**。
    ⇒ 按 `docs/PORTABILITY.md` §二 的判据（「没有它，KS 是坏了，还是只是空着？」）
      它属于**后者** ⇒ 保留探测，但必须**可显式覆盖**（就是第 1 级）。
    """
    import os
    override = os.environ.get("KS_SOFFICE")
    if override:
        p = Path(override)
        if p.exists():
            return p
    candidates = [
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
        Path(r"D:\Program Files\LibreOffice\program\soffice.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c
    which = shutil.which("soffice")
    if which:
        return Path(which)
    return None


def docx_to_pdf_libreoffice(docx_path: Path, out_pdf: Path, timeout: int = 180) -> bool:
    """LibreOffice headless 转换。产物名 = 输入 stem，转换后 rename 到 out_pdf。"""
    soffice = find_libreoffice()
    if soffice is None:
        return False
    out_dir = out_pdf.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [str(soffice), "--headless", "--convert-to", "pdf:writer_pdf_Export",
             "--outdir", str(out_dir), str(docx_path.resolve())],
            capture_output=True, timeout=timeout, check=False)
        if proc.returncode != 0:
            return False
        produced = out_dir / f"{docx_path.stem}.pdf"
        if not produced.exists():
            # 文件名被清理等情况：取目录内最新 pdf 兜底
            pdfs = sorted(out_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not pdfs:
                return False
            produced = pdfs[0]
        if produced.resolve() != out_pdf.resolve():
            produced.replace(out_pdf)
        return out_pdf.exists() and out_pdf.stat().st_size > 0
    except Exception:
        return False


def docx_to_pdf_com(docx_path: Path, out_pdf: Path) -> bool:
    """WPS/Word COM 回退（复用 Task 11.1 docx_adapter）。需 pywin32。"""
    try:
        from src.core.ingestion.docx_adapter import docx_to_pdf_via_com
        return docx_to_pdf_via_com(docx_path, out_pdf)
    except Exception:
        return False


def pdf_completeness(docx_path: Path, pdf_path: Path) -> bool:
    """转换完整性检测：docx 文本量 vs PDF 提取文本量。

    LibreOffice 对部分官方 docx（flk 法规 Word）只渲染文档前部（实测
    建设工程条例 71 条只出前 24 条/7 页）。docx 明显多于 PDF 文本 → 判截断，
    由调用方换转换器重转。无法校验（异常/空 docx）时放行，不阻塞。
    """
    try:
        from docx import Document
        docx_chars = sum(len(p.text) for p in Document(str(docx_path)).paragraphs)
        if docx_chars < 300:
            return True  # 短文档不做完整性判断
        import fitz
        d = fitz.open(str(pdf_path))
        pdf_chars = sum(len(d[i].get_text()) for i in range(d.page_count))
        d.close()
        return pdf_chars >= docx_chars * 0.55
    except Exception:
        return True


def convert_docx_to_pdf(docx_path: Path, out_pdf: Path,
                        prefer: str = "libreoffice") -> str:
    """转换链：LibreOffice →（完整性校验）→ WPS/Word COM →（校验）→ 空串。

    任一转换器产出被判定截断时删除产物并切换下一个；都失败返回 ""。
    prefer="com"（web 兜底 docx 用）时先走 WPS COM——LibreOffice 对
    无样式纯文本 docx 产出的 PDF 文本层可能乱序（实测公报正文逐字乱排）。
    """
    order = ("com", "libreoffice") if prefer == "com" else ("libreoffice", "com")
    for mode in order:
        ok = (docx_to_pdf_com(docx_path, out_pdf) if mode == "com"
              else docx_to_pdf_libreoffice(docx_path, out_pdf))
        if ok and pdf_completeness(docx_path, out_pdf):
            return mode
        out_pdf.unlink(missing_ok=True)  # 截断/不合格产物弃用
    return ""
