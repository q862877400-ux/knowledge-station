"""政务问答 · 把采集到的问答切成**两类资产**（考卷 / 补料清单）。

## 为什么要有这一步
一条"真问题 + 官方答复"**不等于**一条能用的考卷。要当考卷，答复里必须**点名一份可核的依据**
（《某文件》或 GB 号），否则没有对错标准。

于是按「答复点名的文件**在不在我们库里**」一刀切成两类：

| 类 | 判据 | 用途 |
|---|---|---|
| **A 可当考卷** | 点名的文件**在我们库里** | 测检索准不准（有 gold 可依） |
| **B 补料清单** | 点名的文件**不在我们库里** | 直接回答"还该补哪几类、补多少" |
| C 无依据 | 答复里没点名任何文件 | 两样都不是，单列 |

**两类都有用，B 不是噪声** —— 这条是 2026-10-07 定的口径（业主更正：产品面向广大人民群众，
**"提问者是企业还是个人"不是剔除条件**）。

## 用法
```powershell
.venv\\Scripts\\python.exe tools\\gov-qa\\measure-locate-rate.py
.venv\\Scripts\\python.exe tools\\gov-qa\\measure-locate-rate.py --db "<某个库>" --out x.json
```

⚠ 默认只读**生产库**（不写）。要对着别的库量就把 `--db` 指过去。

## ⚠⚠ 本脚本会**写文件**，而且不止 `--out` 那一个

它会为**每个来源**写一个 `assets-<源名>.json`（实测 **592 个**），
默认写在**本脚本所在目录**（`tools/gov-qa/`）—— 其中 **160 个受版本控制**
⇒ 在干净的工作区里跑一次，`git status` 会多出几百行改动。

**`--out` 只控制那份汇总报告，不控制 `assets-*.json`** —— 这是本脚本最容易踩的坑
（2026-10-11 实测：有人以为给了 `--out` 就不会动仓库，结果改了 592 个文件）。

三条正确用法：

| 你想干什么 | 怎么跑 |
|---|---|
| **只想看数字、不碰仓库** | 加 `--assets-dir` 指向临时目录：`--assets-dir "$env:TEMP\\ks-assets"` |
| **就是要刷新仓库里的验收产物** | 直接跑（默认写回 `tools/gov-qa/`），然后 `git status` 看差异 |
| **先知道会写多少** | 脚本启动时会打印「将写 N 个 assets-*.json 到 <目录>」 |
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "locate-rate.json"

#: 答复里"点名文件"的两种写法
DOC_RE = re.compile(r"《([^》]{3,60})》")
STD_RE = re.compile(r"(GB(?:/T|/Z)?\s?\d{3,5}(?:\.\d+)?\s?[—\-]\s?\d{2,4})")
CLAUSE_RE = re.compile(r"第[一二三四五六七八九十百零\d]{1,4}条")
#: 点名了这些词的，多半不是"可核依据"（是程序性公文），标 weak 但不剔除
WEAK = ("征求意见", "通知", "公告", "公示", "解读", "函")


def norm(s: str) -> str:
    return re.sub(r"[\s（）()《》]", "", s or "")


def load_lib(db: Path) -> dict[str, str]:
    c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    out = {}
    for no, nm in c.execute("SELECT standard_no, standard_name FROM doc_meta"):
        if nm:
            out[norm(nm)] = no
    c.close()
    return out


def find_std(lib: dict[str, str], name: str) -> str | None:
    k = norm(name)
    if k in lib:
        return lib[k]
    for nm, no in lib.items():                 # 宽松兜底：≥8 字才允许包含匹配
        if len(k) >= 8 and (k in nm or nm in k):
            return no
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None, help="要对照的库（默认生产库，只读）")
    ap.add_argument("--out", default=str(OUT),
                    help="汇总报告写到哪（**不影响 assets-*.json**）")
    ap.add_argument("--assets-dir", default=str(HERE),
                    help="每个来源的 assets-*.json 写到哪。默认写回本目录"
                         "（⚠ 那里有 160 个受版本控制的 assets 文件，会被覆盖）；"
                         "**只想看数字就指到临时目录**")
    args = ap.parse_args()

    db = Path(args.db) if args.db else (
        Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db")
    if not db.exists():
        print(f"⛔ 库不在：{db}")
        return 1
    lib = load_lib(db)
    print(f"[m] 对照库 = {db}（{len(lib)} 个标准名）")

    files = sorted(DATA.glob("*.jsonl"))
    if not files:
        print(f"⛔ {DATA} 下没有采集结果；先跑 harvest.py")
        return 1

    # ⚠ 先说清"会写什么、写到哪" —— 免得跑完才发现动了仓库（2026-10-11 的教训）
    assets_dir = Path(args.assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)
    n_existing = len(list(assets_dir.glob("assets-*.json")))
    print(f"[m] ⚠ 将写 {len(files)} 个 assets-*.json 到 {assets_dir}"
          f"（该目录现有 {n_existing} 个 assets-*.json，**会被覆盖**）")
    print(f"[m]    汇总报告另写到 {args.out}")
    if assets_dir.resolve() == HERE.resolve() and n_existing:
        print("[m]    ⇒ 你正在写回仓库目录；只想看数字请加 "
              "--assets-dir <临时目录>")

    report = {"db": str(db), "n_lib_names": len(lib), "sources": {}}
    skipped = 0
    for f in files:
        # 2026-10-09 第 9 轮加容错（**影响另一个对话**）：两个对话共写 data/，
        # 对方采集进程正在追加时本文件会读到**半行** ⇒ 原实现直接 JSONDecodeError
        # 崩在第一个撞上的文件，整份验收产物（含 assets-*.json）刷不出来。
        # 口径与 coverage-matrix.py 对齐：跳过并计数；下次重跑即补上。
        rows = []
        for l in f.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            try:
                rows.append(json.loads(l))
            except Exception:                                               # noqa: BLE001
                skipped += 1
        a, b, c = [], [], []          # 考卷 / 补料 / 无依据
        cited_all = cited_in = 0
        for r in rows:
            ans = r.get("answer") or ""
            docs = DOC_RE.findall(ans)
            stds = STD_RE.findall(ans)
            hits, misses = [], []
            for name in docs + stds:
                no = find_std(lib, name)
                cited_all += 1
                if no:
                    cited_in += 1
                    hits.append({"name": name, "lib_no": no,
                                 "weak": any(w in name for w in WEAK)})
                else:
                    misses.append(name)
            rec = {"source": r.get("source"), "id": r.get("id"), "url": r.get("url"),
                   "question": (r.get("question") or "")[:120],
                   "cited_hits": hits, "cited_missing": misses,
                   "has_clause_no": bool(CLAUSE_RE.search(ans))}
            if hits:
                a.append(rec)
            elif misses:
                b.append(rec)
            else:
                c.append(rec)
        n = max(1, len(rows))
        report["sources"][f.stem] = {
            "n_items": len(rows),
            "可当考卷(A_点名且在我们库)": len(a),
            "补料清单(B_点名但不在库)": len(b),
            "无依据(C_没点名)": len(c),
            "可定位率(点过名的条目占比)": f"{len(a)+len(b)}/{n}",
            "在库率(点名文件命中占比)": f"{cited_in}/{cited_all}" if cited_all else "0/0",
        }
        print(f"\n[{f.stem}] {len(rows)} 条")
        print(f"    A 可当考卷 = {len(a)}   B 补料清单 = {len(b)}   C 无依据 = {len(c)}")
        print(f"    可定位率 = {len(a)+len(b)}/{n} ； 在库率 = {cited_in}/{cited_all}")
        (assets_dir / f"assets-{f.stem}.json").write_text(
            json.dumps({"A_考卷": a, "B_补料": b, "C_无依据": c},
                       ensure_ascii=False, indent=1), encoding="utf-8")

    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    tot_a = sum(v["可当考卷(A_点名且在我们库)"] for v in report["sources"].values())
    print(f"\n[m] **可用考卷合计 = {tot_a} 条**（目标 >=100，见 README「瓶颈在库不在采集」一节）")
    if skipped:
        print(f"[m] 跳过 {skipped} 行（解析失败，多为另一个对话采集进行中的半行）")
    print(f"[m] 已写 {args.out} 与 {len(files)} 个 assets-*.json（写到 {assets_dir}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
