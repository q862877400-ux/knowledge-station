"""「全部导入」：把学习材料（教程原文 + 我们自己的笔记）一次性入「参考资料」平面。

业主 2026-09-25 指示："全部导入"。

导入什么：
  1. `var/tmp/tutorial/**/*.md` —— 教程**原文**（子代理抓下来落盘的课本；来源与许可证见该目录 SOURCE.md）
  2. 我们自己的 5 份学习笔记（`docs/research/rag-encyclopedia-study.md` + `var/tmp/study/*.md`）

落到哪：项目 **「RAG 学习资料」**（不存在就建）。
  ⚠ 理由：原先那 5 份笔记落在业主的**测试项目**（「测试-给材料按钮或者删除」）里，
  以后回头找不会去点它 ⇒ 本脚本把**全部材料收进一个正经项目**，
  并在**确认新家已就位之后**，把旧项目里**我们自己那 5 份**删掉（只删标题能对上的，
  不碰任何别人的材料）。删除是**可逆的**：文件仍在磁盘上，重跑本脚本会重新入库。

许可证（**必须记住**，见 `var/tmp/tutorial/SOURCE.md`）：
  · 教程仓库 **CC BY-NC-SA 4.0** ⇒ **禁止商业性使用**、相同方式共享 ⇒ **只作内部语料，不得对外发布**；
  · 菜鸟教程页为站点版权，同理。

用法：
    .venv\\Scripts\\python.exe scripts\\ingest-rag-study-materials.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.core.ingestion.material_ingest import ingest_material_file  # noqa: E402
from src.core.storage import material_repo as mr  # noqa: E402

PROJECT_NAME = "RAG 学习资料"
PROJECT_NOTE = ("RAG 学习材料（教程原文 + 我们的笔记）。"
                "⚠ 教程原文是 CC BY-NC-SA 4.0：禁止商业性使用、相同方式共享 ⇒ 仅内部语料，不得对外发布。")
TUTORIAL_DIR = REPO / "var" / "tmp" / "tutorial"

#: 我们自己的笔记（与 `scripts/measure-material-recall.py` 的 NOTES 同一批）
OWN_NOTES: tuple[Path, ...] = (
    REPO / "docs" / "research" / "rag-encyclopedia-study.md",
    REPO / "var" / "tmp" / "study" / "chunking.md",
    REPO / "var" / "tmp" / "study" / "query.md",
    REPO / "var" / "tmp" / "study" / "eval-routing.md",
    REPO / "var" / "tmp" / "study" / "literature.md",
)

#: 原先放笔记的那个**测试项目**（只从中删掉我们自己那 5 份，别的一律不碰）
OLD_PROJECT_ID = "prj_01M2S04BJN7E5R4SKY6917A22Q"


def _find_or_create_project(dry: bool) -> str:
    for p in mr.list_projects():
        if p.get("name") == PROJECT_NAME:
            print(f"   已有项目：{p['project_id']}")
            return str(p["project_id"])
    if dry:
        print(f"   [dry-run] 会新建项目：{PROJECT_NAME}")
        return "prj_DRYRUN"
    proj = mr.create_project(PROJECT_NAME, note=PROJECT_NOTE)
    print(f"   已新建项目：{proj['project_id']}")
    return str(proj["project_id"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只看会导哪些文件，不写库")
    args = ap.parse_args()

    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):       # pragma: no cover
            pass

    print("① 目标项目")
    pid = _find_or_create_project(args.dry_run)

    tutorial = sorted(TUTORIAL_DIR.rglob("*.md")) if TUTORIAL_DIR.is_dir() else []
    files: list[Path] = list(tutorial) + [p for p in OWN_NOTES if p.is_file()]
    print()
    print(f"② 待导入 {len(files)} 份（教程原文 {len(tutorial)} + 我们的笔记 "
          f"{sum(1 for p in OWN_NOTES if p.is_file())}）")
    if not tutorial:
        print(f"   ⚠ 教程目录还没有内容：{TUTORIAL_DIR}（先让下载那一步跑完再执行本脚本）")

    if args.dry_run:
        for p in files:
            print(f"   [dry-run] {p.relative_to(REPO)}  {p.stat().st_size:>8,} B")
        return 0

    print()
    print("③ 导入")
    ok = 0
    chunks_total = 0
    for p in files:
        try:
            r = ingest_material_file(pid, p, origin="user")
        except Exception as e:                  # noqa: BLE001 —— 单份失败不中断整批
            print(f"   ✗ {p.name:<44} 失败：{type(e).__name__}: {e}")
            continue
        n = len(mr.material_chunks(r["material_id"]))
        ok += 1
        chunks_total += n
        flag = "重复" if r.get("duplicate") else "新入"
        if n == 0:
            flag += "／⚠无文本"
        print(f"   {flag:<10}{p.name:<44} 切片 {n:>4}")
    print(f"   ⇒ 成功 {ok}/{len(files)} 份，合计 {chunks_total} 片")

    # ── ⑤ 旧测试项目里我们自己那 5 份：确认新家已就位后删掉 ─────────────────
    print()
    print("④ 清理旧位置（只删我们自己那 5 份，且必须在新家已就位之后）")
    new_titles = {m["title"] for m in mr.list_materials(pid)}
    removed = 0
    for m in mr.list_materials(OLD_PROJECT_ID):
        if m["project_id"] == pid or m["title"] not in new_titles:
            continue
        if m["title"] not in {p.stem for p in OWN_NOTES}:
            continue                             # 只认我们自己那 5 个标题
        if mr.delete_material(m["material_id"]):
            removed += 1
            print(f"   已删旧副本：{m['title']}")
    print(f"   ⇒ 旧项目里删掉 {removed} 份（其余材料一律未碰）")
    print()
    print("   提示：删除**可逆** —— 文件仍在磁盘上，重跑本脚本会重新入库。")
    print("   ⚠ 许可证再提醒一次：教程原文是 CC BY-NC-SA 4.0 ⇒ **仅内部语料，不得对外发布**。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
