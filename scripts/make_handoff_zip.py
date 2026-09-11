"""生成交接包：源码+文档+测试+数据库快照，排除可重建的重型目录。

用法: .venv/Scripts/python scripts/make_handoff_zip.py [输出zip路径]
默认输出到桌面 KnowledgeStation-handoff-<日期>.zip
"""
import os
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {".venv", "node_modules", "var", "dist", "dist-electron",
                "__pycache__", ".pytest_cache", ".mimosa", ".zcode", ".git",
                "models", "database", "parse_out", "exports"}
EXCLUDE_FILES = {".DS_Store"}

APPDATA_KS = Path(os.environ.get("APPDATA", "")) / "KnowledgeStation"


def add_tree(zf: zipfile.ZipFile, base: Path, arc_base: str) -> int:
    n = 0
    for p in sorted(base.rglob("*")):
        if any(part in EXCLUDE_DIRS for part in p.relative_to(base).parts):
            continue
        if p.name in EXCLUDE_FILES or p.suffix in {".pyc", ".log"}:
            continue
        if p.is_file():
            zf.write(p, f"{arc_base}/{p.relative_to(base).as_posix()}")
            n += 1
    return n


def main() -> None:
    out = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop" / \
        f"KnowledgeStation-handoff-{datetime.now():%Y%m%d}.zip"
    if out.exists():
        out.unlink()
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        n += add_tree(zf, ROOT, "KnowledgeStation")
        # 数据库快照（真实数据：3 部文档 167 条款）
        db = APPDATA_KS / "database" / "knowledge.db"
        if db.exists():
            zf.write(db, "KnowledgeStation/handoff-data/knowledge.db")
            n += 1
        for cfg_name in ("mineru.json", "magic-pdf.json"):
            cfg = Path.home() / cfg_name
            if cfg.exists():
                zf.write(cfg, f"KnowledgeStation/handoff-data/{cfg_name}.sample")
                n += 1
        # 交接说明
        zf.writestr("KnowledgeStation/handoff-data/还原说明.txt", """本包内容与还原步骤
========================

包含：全部源码/测试/文档/前端工程 + handoff-data/（数据库快照与配置样例）。
不含（需在目标机重建）：
  1. .venv        -> uv venv --python 3.12 .venv 后按 pyproject.toml + README 装依赖
  2. node_modules -> npm install（需代理见 phase1-handover）
  3. MinerU 模型  -> mineru-models-download -s modelscope -m pipeline（约2GB）
  4. fastembed 模型 -> 首次运行自动下载（约100MB）
  5. KS_LLM_API_KEY / KS_MINERU_CLOUD_API_KEY -> 用户环境变量（HKCU\Environment），
     切勿写入任何文件；旧的 DEEPSEEK_API_KEY 仍作只读回退（2026-09-11 命名空间化）

数据库还原：把 handoff-data/knowledge.db 复制到
  %APPDATA%\\KnowledgeStation\\database\\knowledge.db

必读文档（按序）：README.md -> docs/onboarding/phase1-handover.md -> docs/onboarding/phase1-selfcheck.md
  -> docs/onboarding/phase2-handover.md -> docs/onboarding/phase2.1-review-response.md
  -> docs/onboarding/phase3-handover.md -> docs/onboarding/phase4-handover.md -> docs/onboarding/contract.md

验证环境完好：.venv\\Scripts\\python -m pytest tests/ -q  应 72 passed
""")
        n += 1
    print(f"{out}")
    print(f"files: {n}, size: {out.stat().st_size / 1048576:.1f} MB")


if __name__ == "__main__":
    main()
