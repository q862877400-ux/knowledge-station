"""把「转换好的文献纯文本」入「参考资料」平面（**绕过那条抽不出文字的 PDF 路径**）。

背景（2026-09-25）：仓里的材料 PDF 路径在**非中文 PDF** 上返回 0 字——根因是
`mineru_adapter.py:187-191` 的判据四把"没有汉字"判成 PUA 乱码（已登记计划 P0.11）。
本脚本导入的是 `scripts/convert-library-to-text.py` 用 PyMuPDF 转好的 `.md`
（每个文件开头带**来源 URL + 许可证 + "内部语料不得对外"**）。

⚠ 许可证纪律：只导入"能从官方入口免费拿到"的材料；每份的许可证写在文件头，
随文本一起入库 ⇒ 将来谁导出都能看见限制。
⚠ 不导入无明示许可/ACM 版权的那几篇（MMR/RRF/docTTTTTquery）——它们只做**链接索引**，不进正文。
   **该规则由下面 `NO_TEXT_LICENSE` 在代码里强制**（拦住会打印，不静默跳过）。

用法：
    .venv\\Scripts\\python.exe scripts\\ingest-library-text.py [--project 名称] [--dir 目录] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.core.ingestion.material_ingest import ingest_material_file  # noqa: E402
from src.core.storage import material_repo as mr  # noqa: E402

PROJECT_NAME = "权威文献（检索/RAG）"
PROJECT_NOTE = ("权威教材与论文（信息检索 / RAG）。文本由 PDF 经 PyMuPDF 转换为 .md，"
                "每份开头带来源 URL 与许可证。"
                "⚠ 多数为**内部语料**（arXiv 非独占 / 版权方保留权利）⇒ 不得对外分发；"
                "明确可再分发的只有 CC BY 4.0 的几份（见各文件头）。")

#: 🔴 **只做链接索引、不进正文**的几篇（无明示许可 / ACM 版权）。
#: 依据：这几份的 PDF 里扫不到**任何**许可证文本（`var/tmp/library/_pdf_license_scan.json`
#: 实测 `license_lines: []`），与 `docs/research/` 里记的下载决定一致。
#:
#: ⚠ **2026-09-25 实测发现的窟窿**：本文件原先只在 docstring 里写了这条规矩，
#: **代码里没有任何强制**（旧版第 59/67 行把目录里的 `*.md` 照单全收）。
#: 批次 1 之所以没违规，只是因为那三份**恰好没被列进转换清单**——是运气，不是机制。
#: 一个机械的"把整个目录导进去"就会违规。⇒ 现在把"说的"变成"做的"。
NO_TEXT_LICENSE = frozenset({
    "1998_MMR_Carbonell_Goldstein",     # ACM 版权，无开放许可
    "2009_RRF_Cormack",                 # 无许可声明
    "2019_docTTTTTquery",               # 无许可声明
})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=PROJECT_NAME)
    ap.add_argument("--dir", default="var/tmp/library/text")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):       # pragma: no cover
            pass

    pid = next((p["project_id"] for p in mr.list_projects() if p.get("name") == args.project), None)
    if not pid:
        if args.dry_run:
            print(f"[dry-run] 会新建项目：{args.project}")
            pid = "prj_DRYRUN"
        else:
            pid = str(mr.create_project(args.project, note=PROJECT_NOTE)["project_id"])
            print(f"已新建项目：{pid}")
    else:
        print(f"已有项目：{pid}")

    d = REPO / args.dir
    all_md = sorted(p for p in d.glob("*.md") if p.is_file())
    blocked = [p for p in all_md if p.stem in NO_TEXT_LICENSE]
    files = [p for p in all_md if p.stem not in NO_TEXT_LICENSE]
    print(f"待导入 {len(files)} 份（来自 {d}）")
    for p in blocked:
        print(f"  ⛔ 拦住 {p.name:<56} 无明示许可 ⇒ 只做链接索引，不进正文")
    if args.dry_run:
        for p in files:
            print(f"  [dry-run] {p.name:<58} {p.stat().st_size:>10,} B")
        return 0

    ok = total = 0
    for p in files:
        try:
            r = ingest_material_file(pid, p, origin="user")
        except Exception as e:                  # noqa: BLE001
            print(f"  ✗ {p.name:<58} {type(e).__name__}: {e}")
            continue
        n = len(mr.material_chunks(r["material_id"]))
        ok += 1
        total += n
        print(f"  {'重复' if r.get('duplicate') else '新入':<6}{p.name:<58} 切片 {n:>5}")
    print()
    print(f"  ⇒ 成功 {ok}/{len(files)} 份，合计 {total} 片")
    print("  ⚠ 这批多数是**内部语料**（见每份文件头）⇒ 不得对外分发。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
