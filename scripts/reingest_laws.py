"""P3 存量 7 部 law-text 重建脚本：官方源匹配 → 下载 → 转 PDF → reingest（删旧 law-text）。

映射：旧 standard_no → (source, 查询方式)。--dry-run 只显示匹配不落库。
用法：
  python scripts/reingest_laws.py --dry-run            # 显示全部匹配候选
  python scripts/reingest_laws.py --only 消防法        # 只重建一部
  python scripts/reingest_laws.py                      # 全量重建（每部确认式跑）
"""
from __future__ import annotations

import argparse
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.core.knowledge.law_source import flk_client as flk
from src.core.knowledge.law_source import govcn_client as govcn
from src.core.knowledge.law_source.ingest import (
    ingest_law_from_flk, ingest_law_from_govcn,
)

# 旧 law-text standard_no → 官方源定位
# 每项: {old_no, source, query(标题), tags, govcn_url?}
REBUILD_PLAN = [
    {"old_no": "消防法(2021修正全本)", "source": "flk", "query": "中华人民共和国消防法",
     "tags": ["消防", "法律"]},
    {"old_no": "安全生产法(2021修正)", "source": "flk", "query": "中华人民共和国安全生产法",
     "tags": ["安全", "法律"]},
    {"old_no": "危化品安全管理条例(2011修订)", "source": "flk",
     "query": "危险化学品安全管理条例", "tags": ["安全", "危险化学品"]},
    {"old_no": "建设工程安全生产管理条例(2004)", "source": "flk",
     "query": "建设工程安全生产管理条例", "tags": ["安全", "建设"]},
    {"old_no": "工贸企业有限空间作业安全规定(2024)", "source": "govcn",
     "query": "工贸企业有限空间作业安全规定",
     "govcn_url": "https://www.gov.cn/gongbao/2024/issue_11166/202402/content_6931872.html",
     "tags": ["安全", "有限空间"]},
    {"old_no": "民法典(节选)", "source": "flk", "query": "中华人民共和国民法典",
     "tags": ["合同", "租赁"], "full_text": True},
]


def _flk_effective(query: str) -> dict | None:
    """标题精确搜索 → 取 sxx=3 有效版第一条（法律/行政法规优先于地方法规）。"""
    data = flk.search(query, search_range=1, search_type=1, sxx=[3],
                      page=1, page_size=20)
    rows = flk.parse_rows(data)
    if not rows:
        data2 = flk.search(query, search_range=1, search_type=2, sxx=[3],
                           page=1, page_size=20)
        rows = flk.parse_rows(data2)
    for r in rows:
        if r["flxz"] in ("法律", "行政法规", "宪法"):
            return r
    return rows[0] if rows else None


def resolve(plan: dict) -> dict:
    """定位官方源目标。返回 {plan, matched: dict|None, source}。"""
    if plan["source"] == "flk":
        hit = _flk_effective(plan["query"])
        return {"plan": plan, "matched": hit, "source": "flk"}
    return {"plan": plan, "matched": {"url": plan.get("govcn_url")}, "source": "govcn"}


def dry_run() -> int:
    for p in REBUILD_PLAN:
        r = resolve(p)
        m = r["matched"]
        print(f"\n[{p['old_no']}] → {p['source']}:{p['query']}")
        if not m:
            print("  ✗ 未匹配")
            continue
        if r["source"] == "flk":
            print(f"  ✓ {m['title']} (flxz={m['flxz']}, sxx={m['sxx']}, bbbs={m['bbbs']})")
        else:
            print(f"  ✓ {m['url']}")
    return 0


def rebuild(plan: dict) -> dict:
    r = resolve(plan)
    m = r["matched"]
    if not m:
        return {"old_no": plan["old_no"], "status": "error",
                "message": f"官方源未匹配: {plan['query']}"}
    if r["source"] == "flk":
        return ingest_law_from_flk(m["bbbs"], standard_no=plan["old_no"],
                                   domain_tags=plan.get("tags", []), reingest=True)
    return ingest_law_from_govcn(m["url"], standard_no=plan["old_no"],
                                 domain_tags=plan.get("tags", []), reingest=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="存量法规官方源重建")
    ap.add_argument("--dry-run", action="store_true", help="只显示匹配候选不落库")
    ap.add_argument("--only", default="", help="只重建包含此子串的 old_no")
    args = ap.parse_args(argv)

    if args.dry_run:
        return dry_run()

    targets = [p for p in REBUILD_PLAN
               if not args.only or args.only in p["old_no"]]
    results = []
    for p in targets:
        print(f"\n>>> 重建 {p['old_no']} …", flush=True)
        out = rebuild(p)
        results.append(out)
        print(json.dumps({k: out.get(k) for k in
                          ("old_no", "status", "doc_id", "total_clauses",
                           "pages_parsed", "converter", "message")},
                         ensure_ascii=False, indent=1), flush=True)
    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f"\n完成 {ok}/{len(targets)}")
    return 0 if ok == len(targets) else 1


if __name__ == "__main__":
    sys.exit(main())
