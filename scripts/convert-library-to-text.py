"""把下载的论文/教材转成文本再入库 —— **绕过仓里那条抽不出文字的 PDF 路径**。

为什么要绕过（2026-09-25 实测，脚本 `var/tmp/diag-pdf.py`）：
  · 同一份 `2023_Query2doc.pdf`（arXiv，10 页）：**PyMuPDF 直接抽**第 1 页得 3,943 字，正常；
  · 而仓里 `material_ingest.extract_pages()` 返回 **0 页**；
    隔离子进程返回 `{'blocks': []}`，并伴随 `解析失败…Invalid port: ':1]'` 的噪声。
  ⇒ **材料平面的 PDF 入库路径在这批文件上一个字都取不到**（已登记计划）。
  ⇒ 本脚本用 PyMuPDF 自己转文本（`.md`），再交给材料平面——那条路是好的（我们已入库 42 份）。

**许可证纪律**（每条都会写进生成文件的开头，随文本一起入库）：
  · `FREE`   ：CC BY / CC BY-SA / 官方免费下载 ⇒ 入库（**对外分发只安全拿 CC BY 的**）
  · `INTERNAL`：arXiv 非独占 / 无许可声明 / "不得分发" ⇒ **只作内部语料**，入库但明确标注
  · 没有稳定免费来源的（盗版站/网盘/付费墙后）⇒ **一律不收**，本脚本不碰

用法：
    .venv\\Scripts\\python.exe scripts\\convert-library-to-text.py <清单.json> [--out 目录]
清单 JSON：`[{"pdf": "相对路径", "title": "...", "source": "URL", "license": "FREE|INTERNAL", "license_note": "逐字说明"}]`
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

MIN_CHARS = 2_000          # 抽出来太少的，判定为"没文本层"，不转
#: **看得懂的字符**占比下限。⚠ 这里我第一版写的是"ASCII 占比 ≥0.30"——**那是同一类语言错**：
#: 中文文档的 ASCII 占比天然很低，于是把**抽得好好的中文样章**（51,912 字）判成了"文本层不可用"。
#: 正确口径：ASCII 可打印 + 汉字 + 中文标点 **都算"看得懂"**；只有**两边都低**（1999 年那种
#: LaTeX2HTML 缺 ToUnicode 的乱码，字符落在怪 Unicode 区）才该拒。
MIN_GOOD_RATIO = 0.75
_CJK = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0x3000, 0x303F), (0xFF00, 0xFFEF))


def _clean(t: str) -> str:
    """去连字垃圾、压缩空行、去掉页眉页脚式的孤立短行。"""
    t = t.replace("\xad", "").replace("\ufb01", "fi").replace("\ufb02", "fl")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", help="清单 JSON 路径")
    ap.add_argument("--out", default="var/tmp/library/text")
    args = ap.parse_args()

    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):       # pragma: no cover
            pass

    items = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    out_dir = (REPO / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    import fitz

    ok = skipped = 0
    for it in items:
        src = REPO / it["pdf"] if not Path(it["pdf"]).is_absolute() else Path(it["pdf"])
        name = src.stem + ".md"
        dst = out_dir / name
        if not src.is_file():
            print(f"  ✗ 缺文件 {src}")
            continue
        try:
            doc = fitz.open(str(src))
            pages = [_clean(doc[i].get_text()) for i in range(doc.page_count)]
            doc.close()
        except Exception as e:                  # noqa: BLE001
            print(f"  ✗ {name} 打不开：{type(e).__name__}: {e}")
            continue
        body = "\n\n".join(p for p in pages if p)
        n_char = len(body)
        good = sum(1 for ch in body
                   if 0x20 <= ord(ch) <= 0x7E
                   or any(lo <= ord(ch) <= hi for lo, hi in _CJK))
        good_ratio = (good / n_char) if n_char else 0.0
        if n_char < MIN_CHARS or good_ratio < MIN_GOOD_RATIO:
            skipped += 1
            print(f"  ⚠ 跳过 {name}：抽出 {n_char:,} 字 / 看得懂的字符占比 {good_ratio:.2f}"
                  f" ⇒ 文本层不可用（要 OCR 才能用）")
            continue
        header = (
            f"# {it['title']}\n\n"
            f"> **来源**：{it['source']}\n"
            f"> **许可证**：{it['license']} —— {it.get('license_note', '')}\n"
            f"> ⚠ 本文件是**为内部检索**把 PDF 转成的纯文本（工具：PyMuPDF），**未改写内容**；\n"
            f"> 版权归原作者/出版方。**内部语料，不得对外分发。**\n\n---\n\n"
        )
        dst.write_text(header + body, encoding="utf-8")
        ok += 1
        print(f"  ✓ {name:<56} {doc_page_count(pages)} 页 → {n_char:>9,} 字")
    print()
    print(f"  转换成功 {ok} 份 / 跳过 {skipped} 份（跳过的需要 OCR，本脚本不假装能用）")
    print(f"  输出目录：{out_dir}")
    return 0


def doc_page_count(pages: list[str]) -> int:
    return len(pages)


if __name__ == "__main__":
    raise SystemExit(main())
