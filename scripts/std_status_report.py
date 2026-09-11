# -*- coding: utf-8 -*-
"""国标体检结果汇总导出（2026-08-26）。

读 scripts/std_status_check.py 产出的 results.jsonl → 生成两份汇总（数据/代码分离：
结果文件默认位于国标目录同级"体检结果"，不在代码树内）：
- <体检结果>/国标状态汇总.csv  —— **GBK 编码**（Excel/WPS 双击打开中文不乱码）
- <体检结果>/国标状态汇总_utf8.csv —— UTF-8（程序/工具用）

列：标准号 | 状态(现行/已废止/被替代/即将实施/查无) | 官方状态原文 | 废止日期 | 代替/相关标准 | 官方证据链接 | 库内文件名(首个)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

STATUS_CN = {
    "effective": "现行", "withdrawn": "已废止", "superseded": "被替代",
    "upcoming": "即将实施", None: "查无/未标注",
}
STATUS_ORDER = {"已废止": 0, "被替代": 1, "即将实施": 2, "现行": 3, "查无/未标注": 4,
                "openstd未收录": 5, "查询失败": 6}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="国标体检结果汇总导出（GBK CSV）")
    ap.add_argument("--dir", help="国标文件目录（结果默认在 <同级>/体检结果）")
    ap.add_argument("--jsonl", default=None, help="results.jsonl 路径（优先于 --dir）")
    ap.add_argument("--out", default=None, help="输出 CSV 路径")
    args = ap.parse_args(argv)

    # 数据/代码分离：结果定位到国标目录同级"体检结果"（数据区）；不硬编码数据路径
    if args.jsonl:
        src = Path(args.jsonl)
    elif args.dir:
        src = Path(args.dir).parent / "体检结果" / "results.jsonl"
    else:
        print("需提供 --dir <国标目录> 或 --jsonl <results.jsonl>")
        return 1
    out = Path(args.out) if args.out else src.with_name("国标状态汇总.csv")
    if not src.exists():
        print(f"未找到结果文件: {src}（先跑 scripts/std_status_check.py）")
        return 1

    rows_by_std: dict[str, list] = {}
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        std = d.get("standard_no", "")
        if "error" in d:
            status = "查询失败"
            note = d.get("message", "")[:120]
            wd = rby = url = pub = eff = name = ccs = ics = ""
        else:
            st = d.get("legal_status")
            if st is None and d.get("channel") == "openstd":
                status = "openstd未收录"
            else:
                status = STATUS_CN.get(st, "查无/未标注")
            note = d.get("status_text") or ""
            wd = d.get("withdrawn_date") or ""
            rby = "、".join(d.get("replaced_by") or [])
            url = d.get("evidence_url") or ""
            pub = d.get("publish_date") or ""     # 发布日期
            eff = d.get("effective_date") or ""   # 实施日期（生效时间）
            name = d.get("standard_name") or ""
            # CCS 分类：名称（+代码 如 "C65"），无则留空
            ccs_name = d.get("ccs_name") or ""
            ccs_code = d.get("ccs_code") or ""
            ccs = f"{ccs_name}({ccs_code})" if (ccs_name and ccs_code) else (ccs_name or ccs_code)
            ics = d.get("ics") or ""
        # 多轮续查可能追加同一标准号的新行：保留最后一条（最新渠道结论）
        rows_by_std[std] = [std, name, status, ccs, pub, eff, wd, rby, url, note]
    rows = list(rows_by_std.values())

    # 排序：先废止/被替代，再现行，便于用户优先处理
    rows.sort(key=lambda r: STATUS_ORDER.get(r[2], 99))
    header = ["标准号", "标准名称", "状态", "CCS分类", "发布日期", "实施日期", "废止日期",
              "代替/相关标准", "官方证据链接", "官方状态原文"]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # GBK 版（Excel/WPS 友好）
    with out.open("w", encoding="gbk", newline="", errors="replace") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    # UTF-8 版（程序用）
    with out.with_name(out.stem + "_utf8.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    from collections import Counter
    cnt = Counter(r[1] for r in rows)
    print(f"汇总 {len(rows)} 条 → {out}（GBK）")
    for k in STATUS_ORDER:
        if cnt[k]:
            print(f"  {k}: {cnt[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
