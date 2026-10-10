# -*- coding: utf-8 -*-
"""生产库卫生检查：**测试夹具不许以「可见文档」身份留在库里**。

## 为什么要有这个脚本

2026-10-10 实测（只读真库）发现：本仓的测试夹具
`standard_no='个人信息保护法(测试)'`（`file_path` 指向 `var/fixtures/测试法.pdf`，
由 `tests/fixtures/make_law_pdf.py` 生成）被登记成
`legal_status='effective'` / `legal_hierarchy='GB'` / `standard_type='mandatory'` /
`catalog_hidden=0` ⇒ **检索「个人信息保护法」会命中它自己的 13 条条款**，
而它的条款内容还是**拼接的假条文**。⇒ 已处置为 `catalog_hidden=1`。

**判据是可核的机械特征**：生产库的文档来源是标准目录或官方渠道 URL，
**不可能**落在本仓（`D:\\AI\\work space\\zcode\\`）里面。
⚠ 第一版判据把 `lawrefbook://` 也算夹具特征 ⇒ 匹配 **1,430 篇真实法规**（正常来源）
⇒ 判据过宽、结论无效，已收窄。

## 用法

    python scripts/check-fixture-leak.py            # 只报告，退出码 0/1
    python scripts/check-fixture-leak.py --json     # 机器可读

退出码：**0 = 干净；1 = 有夹具可见**（可直接进闸门）。
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

# 本仓路径前缀（Windows 与 POSIX 两种写法都算）
PREFIXES = (
    str(REPO) + os.sep,
    REPO.as_posix() + "/",
)

# 「文件放在本仓内」**不足以**判定它是夹具 —— 本仓也可能是**开发期暂存真标准**的地方
# （实测：`wenjianmulu/GBT+39910-2021.pdf` 是**真的** GB/T 39910-2021，
#  12 页、64 条条款、正文完整，只是 `standard_name` 被 OCR 成 `'ICS01.140.20 A14 0 1 2'`）。
# ⇒ 真正的夹具特征要**再加一条**：标准号/标准名里带**加工标记**（`(测试)` 这类）。
#   两条都满足才算夹具；只满足"路径在本仓"的，报成**待核对**（不算失败）。
FIXTURE_MARKERS = ("(测试)", "（测试）", "(TEST)", "(test)", "测试节选")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="测试夹具泄漏检查（只读）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--db", default=str(DB), help="库路径（默认生产库）")
    args = ap.parse_args(argv)

    db = Path(args.db)
    if not db.exists():
        print(f"库不存在：{db}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        where = " OR ".join("file_path LIKE ?" for _ in PREFIXES)
        rows = conn.execute(
            f"SELECT doc_id, standard_no, standard_name, catalog_hidden, file_path"
            f" FROM doc_meta WHERE {where}",
            tuple(p + "%" for p in PREFIXES)).fetchall()
    finally:
        conn.close()

    all_internal = [dict(r) for r in rows]

    def is_fixture(r: dict) -> bool:
        """夹具判据：**路径在本仓内** 且 **名字带加工标记**（两条都要）。"""
        blob = f"{r.get('standard_no') or ''} {r.get('standard_name') or ''}"
        return any(m in blob for m in FIXTURE_MARKERS)

    leaked = [r for r in all_internal if is_fixture(r) and not r["catalog_hidden"]]
    review = [r for r in all_internal if not is_fixture(r)]

    if args.json:
        print(json.dumps({
            "internal_total": len(all_internal),
            "fixtures": [r for r in all_internal if is_fixture(r)],
            "leaked": leaked,
            "review": review,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"本仓内的文档：{len(all_internal)} 篇")
        for r in all_internal:
            kind = "夹具" if is_fixture(r) else "待核对"
            mark = "✅ 已隐藏" if r["catalog_hidden"] else (
                "❌ 可见" if is_fixture(r) else "⚠ 可见（非夹具）")
            print(f"  [{kind}] {mark}  {r['standard_no']!r}")
            print(f"          file_path={r['file_path']!r}")
        print()
        if leaked:
            print(f"❌ **{len(leaked)} 篇夹具以「可见」状态留在库里**（会被用户检索到）：")
            for r in leaked:
                print(f"    {r['standard_no']!r}  file_path={r['file_path']!r}")
            print()
            print("  ⇒ 处置：`UPDATE doc_meta SET catalog_hidden=1 WHERE doc_id=…`")
            print("    （**不删**：该字段可逆，`bulk.py` 注释写明它是"
                  "「那两篇被隐藏文档唯一走得通的回头路」）")
        else:
            print("✅ 无夹具泄漏")
        if review:
            print()
            print(f"⚠ {len(review)} 篇「文件在本仓、但不像夹具」（**不算失败，供人判**）：")
            for r in review:
                print(f"    {r['standard_no']!r}  standard_name={r['standard_name']!r}")

    return 1 if leaked else 0


if __name__ == "__main__":
    raise SystemExit(main())
