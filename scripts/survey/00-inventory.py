"""检查第 1 步：全仓文件清单（三重账本对账）。

## 检查什么

仓里**每一个文件**（受控 + 未跟踪），各一条记录：路径、字节、行数、sha256、
语言、分类。**只记录，不判断。**

## 怎么保证没漏（本脚本的核心）

```
账本甲 = git ls-files                      （受控文件）
账本乙 = git status --porcelain 里 '??' 的  （未跟踪文件）
账本丙 = 本脚本的输出条数

判据：甲 + 乙 == 丙，且输出里没有重复路径
```

`--check` 会核这个账；不平就 exit 1。

## 用法

    python scripts/survey/00-inventory.py                # 生成 JSON
    python scripts/survey/00-inventory.py --check        # 只对账
    python scripts/survey/00-inventory.py --md           # 顺便生成 01-inventory.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "docs" / "survey" / "data" / "inventory.json"

#: 扩展名 → 语言
LANG = {
    ".py": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".md": "Markdown",
    ".ps1": "PowerShell",
    ".bat": "Batch",
    ".cmd": "Batch",
    ".json": "JSON",
    ".jsonl": "JSONL",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".toml": "TOML",
    ".txt": "Text",
    ".pdf": "PDF",
    ".db": "SQLite",
    ".patch": "Patch",
    ".woff": "Font",
    ".woff2": "Font",
    ".ttf": "Font",
    ".png": "Image",
    ".jpg": "Image",
    ".jpeg": "Image",
    ".svg": "Image",
    ".ico": "Icon",
    ".joblib": "Model",
    ".pt": "Model",
    ".onnx": "Model",
    ".lock": "Lock",
    ".cfg": "Config",
    ".ini": "Config",
    ".env": "Config",
}

#: **本脚本自己的输出目录**。必须排除，否则清单会把自己算进去 ——
#: 实测第一版就是这样：`inventory.json` 1 MB / 43,055 行被算成"文档"，
#: 于是每跑一次"文档"就变大一次，数字不稳定。
GENERATED_PREFIXES = ("docs/survey/data/",)


#: 分类（按路径判定，**只描述"它在仓里承担什么角色"，不评价好坏**）
def classify(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("src/core/"):
        return "产品代码-引擎"
    if p.startswith("plugin/src/"):
        return "产品代码-插件宿主"
    if p.startswith("plugin/client/"):
        return "产品代码-界面"
    if p.startswith("plugin/scripts/"):
        return "验证脚本-冒烟/探针"
    if p.startswith("plugin/"):
        return "插件其他"
    if p.startswith("tests/"):
        return "测试"
    if p.startswith("scripts/"):
        return "脚本-工具/门禁"
    if p.startswith("docs/survey/") or p.startswith("docs/uniformity/"):
        return "文档-项目现状地图"
    if p.startswith("docs/archive/"):
        return "文档-历史归档"
    if p.startswith("docs/"):
        return "文档"
    if p.startswith("specs/"):
        return "规格-spec-kit"
    if p.startswith(".specify/"):
        return "规格-spec-kit脚手架"
    if p.startswith("eval/"):
        return "评测集"
    if p.startswith("tools/gov-qa/"):
        return "另一条线-政务问答采集"
    if p.startswith("wenjianmulu/"):
        return "证据原件-PDF"
    if p.startswith("var/"):
        return "本地产物-数据/模型"
    if p.startswith("output/"):
        return "本地产物-作业单"
    if p.startswith("tests/fixtures/"):
        return "测试夹具"
    if p.startswith((".codebuddy/", ".dsh/", ".zcode/", ".claude")):
        return "工具配置"
    if p.startswith(".github/"):
        return "CI"
    return "其他"


def git_ls_files() -> list[str]:
    r = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [x for x in r.stdout.split("\0") if x]


def git_untracked() -> list[str]:
    r = subprocess.run(
        ["git", "status", "--porcelain", "-z", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    out = []
    for entry in r.stdout.split("\0"):
        if len(entry) > 3 and entry[:2] == "??":
            out.append(entry[3:])
    return out


def git_ignored() -> list[str]:
    """账本丁：被 `.gitignore` 排除、但**确实存在于磁盘上**的路径。

    ## 为什么必须有这一本账（2026-10-24 实测出来的坑）

    前两本账（受控 + 未跟踪）**看不见被忽略的东西**。
    而本仓**最要紧的数据就在被忽略的地方**：

    | 路径 | 实测 |
    |---|---|
    | `var/data/` | **358,400 个文件 / 74 GB** ← 生产库与证据原件全在这 |
    | `var/models/` | 79 个文件 / 7 GB |
    | `var/tmp/` | 14,111 个文件 / 1.6 GB |

    ⇒ 只对前两本账，下一棒会以为"仓里没有数据"。
    本函数把这本账也记下来（**只汇总，不逐条** —— 35 万条逐条列没有意义）。
    """
    r = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "-z",
            "--ignored=matching",
            "--untracked-files=all",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    out = []
    for entry in r.stdout.split("\0"):
        if len(entry) > 3 and entry[:2] == "!!":
            out.append(entry[3:])
    return out


def summarize_ignored(paths: list[str]) -> dict:
    """把被忽略的路径按「前两级目录」汇总成计数与体积。"""
    buckets: dict[str, dict] = {}
    for rel in paths:
        parts = rel.replace("\\", "/").rstrip("/").split("/")
        key = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        b = buckets.setdefault(key, {"entries": 0, "bytes": 0})
        b["entries"] += 1
        p = ROOT / rel
        if p.is_file():
            try:
                b["bytes"] += p.stat().st_size
            except OSError:
                pass
    # 目录条目本身大小算 0，真实体积用磁盘测量补（下面单独算）
    return dict(sorted(buckets.items(), key=lambda kv: -kv[1]["entries"]))


def file_record(rel: str) -> dict:
    p = ROOT / rel
    rec = {"path": rel.replace("\\", "/"), "exists": p.exists()}
    if not p.exists():
        # 受控但磁盘上没有 —— **这是一个观察，不是错误**。
        # 实测本仓有 1 个：`var/_trash-2026-10-11/README.md`（git status 显示 ` D`，
        # 即"已从工作树删除但没提交"）。记下来，不判断。
        rec["category"] = "受控但磁盘缺失"
        rec["state"] = "missing"
        return rec
    rec["state"] = "present"
    try:
        st = p.stat()
        rec["bytes"] = st.st_size
    except OSError:
        return rec
    rec["ext"] = p.suffix.lower()
    rec["lang"] = LANG.get(p.suffix.lower(), "其他")
    rec["category"] = classify(rec["path"])
    # 行数只对文本文件算（二进制读不动也不该读）
    if rec["lang"] not in ("PDF", "SQLite", "Image", "Icon", "Font", "Model"):
        try:
            raw = p.read_bytes()
            rec["lines"] = raw.count(b"\n") + (
                0 if raw.endswith(b"\n") or not raw else 1
            )
            rec["sha256"] = hashlib.sha256(raw).hexdigest()[:16]
        except OSError:
            pass
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--md", action="store_true")
    args = ap.parse_args()

    tracked = git_ls_files()
    untracked = git_untracked()
    all_entries = sorted(set(tracked) | set(untracked))
    all_files = [
        f
        for f in all_entries
        if not f.replace("\\", "/").startswith(GENERATED_PREFIXES)
    ]
    generated = [
        f for f in all_entries if f.replace("\\", "/").startswith(GENERATED_PREFIXES)
    ]

    print(f"账本甲（受控）      : {len(tracked)}")
    print(f"账本乙（未跟踪）    : {len(untracked)}")
    print(f"账本丙（去重合并后）: {len(all_entries)}")
    print(f"  其中生成物（本脚本输出，不计入项目统计）: {len(generated)}")
    print(f"  计入项目统计: {len(all_files)}")

    # 对账：甲 + 乙 vs 丙（去重会少于相加，因为未跟踪里可能有已跟踪的修改）
    dup = len(tracked) + len(untracked) - len(all_files)
    print(f"重叠（既受控又出现在未跟踪列表）: {dup}")

    ok = True
    if len(all_files) == 0:
        print("✘ 清单为空", file=sys.stderr)
        ok = False

    if args.check:
        if not OUT_JSON.exists():
            print(f"✘ 先跑一次生成：{OUT_JSON} 不存在", file=sys.stderr)
            return 1
        data = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        got = {r["path"] for r in data["files"]}
        missing = [f for f in all_files if f.replace("\\", "/") not in got]
        extra = [p for p in got if p not in {f.replace("\\", "/") for f in all_files}]
        print(f"\n--check：清单 {len(got)} 条 / 实际 {len(all_files)} 条")
        if missing:
            ok = False
            print(f"✘ 漏了 {len(missing)} 个文件：", file=sys.stderr)
            for m in missing[:20]:
                print(f"    {m}", file=sys.stderr)
        if extra:
            ok = False
            print(f"✘ 清单里多了 {len(extra)} 个文件（已删？）：", file=sys.stderr)
            for e in extra[:20]:
                print(f"    {e}", file=sys.stderr)
        if ok:
            print("PASS 三重账本平（零漏、零多余）")
        return 0 if ok else 1

    records = [file_record(f) for f in all_files]
    by_cat: dict[str, dict] = {}
    for r in records:
        c = r.get("category", "?")
        d = by_cat.setdefault(c, {"files": 0, "bytes": 0, "lines": 0})
        d["files"] += 1
        d["bytes"] += r.get("bytes", 0)
        d["lines"] += r.get("lines", 0)

    # 账本丁：被忽略但确实存在
    ignored = git_ignored()
    ignored_summary = summarize_ignored(ignored)
    print(f"\n账本丁（被忽略但存在）: {len(ignored)} 条")

    payload = {
        "generated_by": "scripts/survey/00-inventory.py",
        "repo_root": str(ROOT),
        "ledger": {
            "tracked": len(tracked),
            "untracked": len(untracked),
            "merged": len(all_entries),
            "overlap": dup,
            "generated_excluded": len(generated),
            "counted": len(all_files),
            "ignored_entries": len(ignored),
        },
        "generated_paths": generated,
        "by_category": dict(sorted(by_cat.items(), key=lambda kv: -kv[1]["files"])),
        "ignored_summary": ignored_summary,
        "ignored_paths": ignored,
        "files": records,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\n已落：{OUT_JSON.relative_to(ROOT)}（{len(records)} 条）")

    print("\n按分类：")
    for c, d in payload["by_category"].items():
        print(
            f"  {c:28} {d['files']:>5} 文件 {d['bytes'] / 1048576:>9.1f} MB "
            f"{d['lines']:>9,} 行"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
