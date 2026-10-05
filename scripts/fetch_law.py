"""官方法规抓取 CLI（docs/LAW-SOURCE-PLAN.md P1/P3）。

用法：
  # 搜索候选（不落库）
  python scripts/fetch_law.py flk search "消防法" --effective
  python scripts/fetch_law.py govcn search "安全生产" --childtype 国务院文件

  # 按 bbbs / URL 入库（下载官方 docx → 转 PDF → run_full_ingest）
  python scripts/fetch_law.py flk ingest <bbbs> [--name 名称] [--tags 消防,法律] [--reingest]
  python scripts/fetch_law.py govcn ingest <详情页URL> [--name ...] [--tags ...] [--reingest]

  # 按关键词精确匹配后入库（自动取 sxx=3 有效版第一条）
  python scripts/fetch_law.py flk match "中华人民共和国消防法" --tags 消防,法律
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from src.core.knowledge.law_source import flk_client as flk
from src.core.knowledge.law_source import govcn_client as govcn
from src.core.knowledge.law_source.ingest import (
    ingest_law_from_flk, ingest_law_from_govcn,
)


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=1), flush=True)


def cmd_flk_search(args) -> int:
    sxx = [3] if args.effective else None
    data = flk.search(args.query, search_range=args.field, sxx=sxx,
                      page=1, page_size=args.size)
    rows = flk.parse_rows(data)
    for i, r in enumerate(rows, 1):
        print(f"{i}. [{r['flxz']}] {r['title']}  (bbbs={r['bbbs']}, "
              f"公布{r['gbrq']}, sxx={r['sxx']})")
    print(f"\n共 {data.get('total', 0)} 条，显示前 {len(rows)} 条")
    return 0


def cmd_flk_match(args) -> int:
    """标题精确匹配（searchType=1）→ 取 sxx=3 有效版第一条入库。"""
    data = flk.search(args.query, search_range=1, search_type=1, sxx=[3],
                      page=1, page_size=10)
    rows = flk.parse_rows(data)
    if not rows:
        print(f"未匹配到有效版: {args.query}")
        return 1
    r = rows[0]
    print(f"命中: {r['title']} ({r['bbbs']})")
    out = ingest_law_from_flk(r["bbbs"], domain_tags=_tags(args),
                              reingest=args.reingest)
    _print(out)
    return 0 if out.get("status") == "ok" else 1


def cmd_flk_ingest(args) -> int:
    out = ingest_law_from_flk(args.bbbs, standard_name=args.name,
                              domain_tags=_tags(args), reingest=args.reingest)
    _print(out)
    return 0 if out.get("status") == "ok" else 1


def cmd_govcn_search(args) -> int:
    data = govcn.search(args.query, field=args.field, page=0, size=args.size,
                        childtype=args.childtype, year=args.year,
                        department=args.department)
    rows = govcn.parse_rows(data)
    for i, r in enumerate(rows, 1):
        print(f"{i}. [{r['category']}] {r['title']}")
        print(f"   文号:{r['pcode']} 机关:{r['source']} 时间:{r['pubtime']}")
        print(f"   {r['url']}")
    print(f"\n共 {len(rows)} 条")
    return 0


def cmd_govcn_ingest(args) -> int:
    out = ingest_law_from_govcn(args.url, standard_name=args.name,
                                domain_tags=_tags(args), reingest=args.reingest)
    _print(out)
    return 0 if out.get("status") == "ok" else 1


def cmd_updates(args) -> int:
    """法规更新检查（只读）：库内官方源文档 vs 官方源现状。"""
    from src.core.knowledge.law_source.update import check_law_updates
    out = check_law_updates()
    print(f"检查 {out['checked']} 部官方来源文档")
    for c in out["status_changes"]:
        print(f"  ⚠ 时效变更: {c['standard_no']} {c.get('old_status')} → {c.get('new_status')} ({c.get('title')})")
    for nv in out["new_versions"]:
        print(f"  🔄 新版本: {nv['standard_no']} 已有 {nv.get('new_gbrq')} 版 ({nv.get('new_title')}, bbbs={nv.get('new_bbbs')})")
    if not out["status_changes"] and not out["new_versions"]:
        print("  无时效变更、无新版本")
    return 0


def _tags(args) -> list[str]:
    return [t.strip() for t in (args.tags or "").split(",") if t.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="官方法规抓取 CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("flk", help="国家法律法规数据库")
    fs = p.add_subparsers(dest="action", required=True)
    s = fs.add_parser("search", help="搜索候选")
    s.add_argument("query"); s.add_argument("--size", type=int, default=20)
    s.add_argument("--field", type=int, choices=[1, 2], default=1, help="1=标题 2=正文")
    s.add_argument("--effective", action="store_true", help="仅 sxx=3 有效")
    s.set_defaults(fn=cmd_flk_search)
    m = fs.add_parser("match", help="标题精确匹配并入库（取有效版）")
    m.add_argument("query"); m.add_argument("--tags", default="")
    m.add_argument("--reingest", action="store_true")
    m.set_defaults(fn=cmd_flk_match)
    i = fs.add_parser("ingest", help="按 bbbs 入库")
    i.add_argument("bbbs"); i.add_argument("--name", default="")
    i.add_argument("--tags", default=""); i.add_argument("--reingest", action="store_true")
    i.set_defaults(fn=cmd_flk_ingest)

    p2 = sub.add_parser("govcn", help="国务院政策文件库")
    gs = p2.add_subparsers(dest="action", required=True)
    s2 = gs.add_parser("search", help="搜索候选")
    s2.add_argument("query"); s2.add_argument("--size", type=int, default=20)
    s2.add_argument("--field", choices=["title", "content"], default="title")
    s2.add_argument("--childtype", choices=["国务院文件", "部门文件", "解读"], default="")
    s2.add_argument("--year", default=""); s2.add_argument("--department", default="")
    s2.set_defaults(fn=cmd_govcn_search)
    i2 = gs.add_parser("ingest", help="按详情页 URL 入库")
    i2.add_argument("url"); i2.add_argument("--name", default="")
    i2.add_argument("--tags", default=""); i2.add_argument("--reingest", action="store_true")
    i2.set_defaults(fn=cmd_govcn_ingest)

    u = sub.add_parser("updates", help="法规更新检查（只读）")
    u.set_defaults(fn=cmd_updates)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
