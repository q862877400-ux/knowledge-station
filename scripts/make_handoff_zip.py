"""生成交接包：源码+文档+测试+数据库快照，排除可重建的重型目录。

用法: .venv/Scripts/python scripts/make_handoff_zip.py [输出zip路径]
默认输出到桌面 KnowledgeStation-handoff-<日期>.zip

批 8 同步（2026-09-12，Electron 退役）：旧前端（src/renderer、electron/、
vite.config.ts、public/pagecmp、dist*）已整体删除，排除表里对应目录已不存在
（保留无害，防同名目录复活）；还原说明改为 DSH 插件形态；pytest 基线刷新为
830 passed + 3 skipped；必读文档列表同步 docs/onboarding 实际存留状态
（仅 evidence-card-contract.md 在库，phase 系列交接文档早已散佚）。
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

包含：引擎源码/测试/文档 + DSH 插件（plugin/：host 桥 + client tab）
+ handoff-data/（数据库快照与配置样例）。
（批 8 起不再含独立前端工程：Electron/Vite 壳已退役，GUI 一律经 DSH
Web 宿主侧栏呈现；桌面化由 DSH 整体打包承担，本项目不单独出 EXE。）
不含（需在目标机重建）：
  1. .venv        -> uv venv --python 3.12 .venv 后按 pyproject.toml + README 装依赖
  2. node_modules -> 根：npm install（tsc 门禁/类型债工具链）；plugin/：cd plugin && npm install
  3. MinerU 模型  -> mineru-models-download -s modelscope -m pipeline（约2GB）
  4. fastembed 模型 -> 首次运行自动下载（约100MB）
  5. KS_LLM_API_KEY / KS_MINERU_CLOUD_API_KEY -> 引擎加密存储（<data_dir>/secrets.json，
     Windows DPAPI；2026-09-12 迁移整改后注册表仅作只读覆盖、引擎绝不写），
     切勿写入任何文件；旧名 DEEPSEEK_API_KEY 等已全部搬迁删除
     （工具 scripts/ks-credentials-migrate.py）

数据库还原：把 handoff-data/knowledge.db 复制到
  %APPDATA%\\KnowledgeStation\\database\\knowledge.db

必读文档（按序）：README.md -> ENCYCLOPEDIA.md -> DSH_REINCARNATION.md
  -> docs/onboarding/evidence-card-contract.md
  （注：历史上引用过的 docs/onboarding/phase1-handover.md 等 phase 系列交接
   文档已不在库中；phase1~4 的关键结论沉淀于 ENCYCLOPEDIA.md 的阶段史与
   DSH_REINCARNATION.md 的整改台账，交接以这三份为准。）

验证环境完好：
  .venv\\Scripts\\python -m pytest tests/ -q        应 830 passed + 3 skipped
  cd plugin && npm run smoke                         应 10 段全 PASS
  cd plugin && npm run verify:commands               应 15/15
  npm run typecheck                                  应 0 错误（plugin/client 门禁）
""")
        n += 1
    print(f"{out}")
    print(f"files: {n}, size: {out.stat().st_size / 1048576:.1f} MB")


if __name__ == "__main__":
    main()
