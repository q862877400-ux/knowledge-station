"""把 LawRefBook 的 8 MB 法规数据**解到 `D:\\AI\\work space\\标准\\法律法规`**，保持原目录结构。

业主 2026-10-07 指示："把这 8 MB 补进去，放在 D:\\AI\\work space\\标准\\法律法规，就保持人家原来的文件目录结构"。

## 为什么不能直接用 `zipfile.extractall`
zip 里的文件名是 **UTF-8 字节被 Python 按 CP437 解码**出来的乱码（如 `σ«¬µ│òτ¢╕σà│µ│ò` = `宪法相关法`）。
`extractall()` 会**照着乱码建目录**。所以本脚本：
 · 自己解 `cp437 → utf-8` 拿回真名；
 · 自己读写每个条目；
 · 解完**逐个复核**（文件数、总字节、抽样验 UTF-8 可读、目录树）。

## 安全
 · 目标不存在则新建；**已存在且非空时默认拒绝**（除非 `--force`），避免覆盖业主已有内容；
 · 只写目标目录；**不碰真库、不碰仓库**；
 · 在仓内留一份**提取清单**（计数 + 顶层结构 + 抽样），供日后核对。

用法：
  .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\18-extract-to-standards.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "lawrefbook-extracted-manifest.json"
ZIP = ROOT / "var" / "tmp" / "lawrefbook" / "laws.zip"
TARGET = Path("D:/AI/work space/标准/法律法规")


def fix(name: str) -> str:
    """zip 内文件名按 CP437 解的 ⇒ 还原（原编码 UTF-8）。"""
    try:
        raw = name.encode("cp437")
    except UnicodeEncodeError:
        return name
    for enc in ("utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return name


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="目标已存在且非空时也继续（会覆盖同名文件）")
    args = ap.parse_args()

    if not ZIP.exists():
        print(f"⛔ 原料不在：{ZIP}（先跑 15-fetch-zip-retry.py）")
        return 1

    if TARGET.exists() and any(TARGET.iterdir()) and not args.force:
        n = sum(1 for _ in TARGET.rglob("*"))
        print(f"⛔ 目标已存在且非空（{n} 项）：{TARGET}\n   如确认要覆盖，加 --force")
        return 1

    TARGET.mkdir(parents=True, exist_ok=True)
    src_sha = hashlib.sha256(ZIP.read_bytes()).hexdigest()
    print(f"[x] 原料 {ZIP.name}  {ZIP.stat().st_size/1e6:.2f} MB  sha256={src_sha[:16]}…")
    print(f"[x] 目标 {TARGET}")

    dirs, files, total = 0, 0, 0
    top: Counter = Counter()
    names_sample: list[str] = []
    with zipfile.ZipFile(ZIP) as z:
        for zi in z.infolist():
            real = fix(zi.filename)
            if not real or real.startswith("/") or ".." in Path(real).parts:
                print(f"[x] ⚠ 跳过可疑路径：{zi.filename!r}")
                continue
            dest = TARGET / real
            if zi.is_dir() or real.endswith("/"):
                dest.mkdir(parents=True, exist_ok=True)
                dirs += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = z.read(zi)
            dest.write_bytes(data)
            files += 1
            total += len(data)
            top[Path(real).parts[0]] += 1
            if len(names_sample) < 8:
                names_sample.append(real)

    print(f"[x] 解出：目录 {dirs} 个 / 文件 {files} 个 / 合计 {total/1e6:.2f} MB")

    # ---- 复核 ----
    on_disk = [p for p in TARGET.rglob("*") if p.is_file()]
    size_disk = sum(p.stat().st_size for p in on_disk)
    print(f"[verify] 磁盘上实际：{len(on_disk)} 个文件 / {size_disk/1e6:.2f} MB")
    ok_names = all("σ" not in str(p.relative_to(TARGET)) and "µ" not in str(p.relative_to(TARGET))
                   for p in on_disk)
    print(f"[verify] 目录/文件名无乱码：{'✅ 是' if ok_names else '⛔ 否'}")

    read_ok, sample_body = 0, None
    for p in sorted(on_disk)[:12]:
        try:
            t = p.read_text(encoding="utf-8")
            if t.strip():
                read_ok += 1
                if sample_body is None and len(t) > 200:
                    sample_body = {"file": str(p.relative_to(TARGET)), "chars": len(t),
                                   "head": t[:400]}
        except UnicodeDecodeError:
            pass
    print(f"[verify] 前 12 个文件里，UTF-8 可读且非空：{read_ok}/12")

    tree = {}
    for d in sorted(TARGET.iterdir()):
        if d.is_dir():
            tree[d.name] = sum(1 for _ in d.rglob("*") if _.is_file())
    print("[verify] 顶层结构：")
    for k, v in sorted(tree.items(), key=lambda kv: -kv[1]):
        print(f"      {k}/  {v} 个文件")
    for f in sorted(TARGET.glob("*")):
        if f.is_file():
            print(f"      {f.name}  {f.stat().st_size} 字节")

    manifest = {
        "why": "业主指示：把 LawRefBook 的 8MB 法规数据解到 D:\\AI\\work space\\标准\\法律法规，保持原目录结构",
        "source_zip": {"path": str(ZIP), "bytes": ZIP.stat().st_size, "sha256": src_sha},
        "target": str(TARGET),
        "extracted": {"dirs": dirs, "files": files, "bytes": total},
        "verified_on_disk": {"files": len(on_disk), "bytes": size_disk,
                             "no_mojibake_in_names": ok_names,
                             "utf8_readable_of_first12": read_ok},
        "top_level": dict(sorted(tree.items(), key=lambda kv: -kv[1])),
        "root_files": {f.name: f.stat().st_size for f in sorted(TARGET.glob("*")) if f.is_file()},
        "names_sample": names_sample,
        "sample_body": sample_body,
        "boundary": [
            "只写目标目录；未碰真库与仓库内数据。",
            "原 zip 的名录是 UTF-8 被按 CP437 解出的乱码 ⇒ 本脚本自行还原后写盘（用 extractall 会建乱码目录）。",
            "许可：LawRefBook 仓库 SPDX=NOASSERTION，README 主张依《著作权法》第五条属公有领域；引入前的合规判断由业主负责。",
        ],
    }
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[x] 抽样文件名：")
    for n in names_sample:
        print("      ", n)
    if sample_body:
        print(f"\n[x] 抽样正文（{sample_body['file']}，{sample_body['chars']} 字）：")
        print("      " + sample_body["head"][:260].replace("\n", "\n      "))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
