"""IGI 多 siteId **分片增量**采集驱动（2026-10-09 新增，为山西 `sx-igi` 写）。

## 与 `recon/igi-chunked-harvest.py` 的两点差别（都是硬需求）
1. **每个 siteId 一个文件**：`data/<key>-<sid>-<name>.jsonl`（与 `hb-hdjl` 同约定）。
   旧的 chunked 驱动把全部 siteId 写进**同一个文件** ⇒ `existing_ids('<key>-<sid>')`
   永远为空、`skip_ids` 传不进去 ⇒ **重跑要逐条重取明细**。
   山西全量约 4.8 万条，重取一遍 = 十几小时白跑。
2. **把已落盘 id 作为 `skip_ids` 传回 `harvest_igi`** ⇒ 重跑只取新增，天然续采。

## 为什么必须有它（而不是直接用 harvest.py）
`harvest.py` **只在跑完时落盘**（先收全量 rows 再写文件）⇒ 4.8 万条跑到一半被中断 = 零产出。
本驱动**逐 siteId 采完即落盘**，中断只损失当前那一个 siteId。

## 用法
  .venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked.py sx_igi
  .venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked.py sx_igi --only 32,41 --limit 500
  .venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked.py sx_igi --sites-json igi-siteid-shanxi.json

只写 `data/`，不改任何共享代码。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent          # tools/gov-qa/recon
ROOT = HERE.parent                              # tools/gov-qa
sys.path.insert(0, str(ROOT))

# ⚠ 同 harvest.py：NO_PROXY 里的 [::1] 会让 httpx 连 Client() 都构造不出来
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
DATA = ROOT / "data"


class _Fetcher:
    """与 harvest.py 的 _Fetcher 同协议（可调用 = GET，另有 .post）。"""

    def __init__(self, client):
        self._c = client

    def __call__(self, url, **kw):
        return self._c.get(url, **kw)

    def post(self, url, **kw):
        return self._c.post(url, **kw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("module", help="adapters/ 下的模块名，如 sx_igi")
    ap.add_argument("--only", default="", help="只跑指定 siteId，逗号分隔（默认用模块 SITE_IDS）")
    ap.add_argument("--sites-json", default="", help="用枚举结果 json 里的 sites 键（按 total 降序）")
    ap.add_argument("--limit", type=int, default=0, help="本轮新增总量上限（0 = 不限）")
    ap.add_argument("--pause", type=float, default=1.2, help="siteId 之间的间隔秒数")
    ap.add_argument("--retries", type=int, default=2, help="单个 siteId 失败后的重试次数")
    ap.add_argument("--cooldown", type=float, default=30.0, help="重试前的冷却秒数")
    ap.add_argument("--abort-after", type=int, default=8, help="连续多少个 siteId 失败即中止整轮")
    args = ap.parse_args()

    import httpx
    from adapters._igi_common import existing_ids, harvest_igi

    mod = __import__(f"adapters.{args.module}", fromlist=["SITE"])
    SITE = mod.SITE
    strip = getattr(mod, "postprocess", None) or getattr(mod, "strip_portal_geo", None)

    if args.only:
        site_ids = [s.strip() for s in args.only.split(",") if s.strip()]
    elif args.sites_json:
        p = HERE / args.sites_json
        sites = json.loads(p.read_text(encoding="utf-8"))["sites"]
        site_ids = [k for k, _ in sorted(sites.items(), key=lambda kv: -kv[1])]
    else:
        site_ids = list(mod.SITE_IDS)

    seen = existing_ids(SITE["key"]) | existing_ids("sx-szxx")
    print(f"[{SITE['key']}] 已落盘 {len(seen)} 条；待跑 {len(site_ids)} 个 siteId："
          f"{','.join(site_ids)}", flush=True)

    grand_new = 0
    consec_fail = 0
    t_all = time.perf_counter()
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False, verify=False) as cli:
        fetcher = _Fetcher(cli)
        for i, sid in enumerate(site_ids, 1):
            if args.limit and grand_new >= args.limit:
                break
            sub_site = dict(SITE)
            sub_site["key"] = f"{SITE['key']}-{sid}"
            sub_name = f"{SITE['name']}·siteId={sid}"
            out_path = DATA / f"{SITE['key']}-{sid}-{sub_name}.jsonl"
            done = _load_done(out_path)
            remain = (args.limit - grand_new) if args.limit else None
            t0 = time.perf_counter()

            rows = None
            for attempt in range(args.retries + 1):
                try:
                    rows = harvest_igi(
                        fetcher, SITE=sub_site, base=mod.BASE, site_id=sid,
                        app_id=mod.APP_ID, group_id=mod.GROUP_ID, referer=mod.REFERER,
                        limit=remain, max_pages=300, skip_ids=seen)
                    break
                except Exception as e:                                   # noqa: BLE001
                    if attempt < args.retries:
                        print(f"  [{i}/{len(site_ids)}] siteId={sid} {type(e).__name__}，"
                              f"{args.cooldown:.0f}s 后重试 {attempt + 1}/{args.retries}",
                              flush=True)
                        time.sleep(args.cooldown)
                    else:
                        print(f"  [{i}/{len(site_ids)}] siteId={sid} 失败 "
                              f"{type(e).__name__}: {e}（已重试 {args.retries} 次，跳过）",
                              flush=True)
            if rows is None:
                consec_fail += 1
                if consec_fail >= args.abort_after:
                    print(f"  ⚠ 连续 {consec_fail} 个 siteId 失败 ⇒ 中止本轮"
                          f"（疑似限流，稍后再跑可续采）", flush=True)
                    break
                continue
            consec_fail = 0

            if strip:
                rows = strip(rows)
            fresh = [r for r in rows if (r["source"], str(r["id"])) not in done]
            for r in fresh:
                done.add((r["source"], str(r["id"])))
                seen.add(str(r["id"]))
            if fresh:
                with out_path.open("a", encoding="utf-8") as fh:
                    for r in fresh:
                        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            grand_new += len(fresh)
            print(f"  [{i}/{len(site_ids)}] siteId={sid}: 取 {len(rows)} / 新增 {len(fresh)}"
                  f"（{time.perf_counter() - t0:.0f}s，累计 {grand_new}）", flush=True)
            if i < len(site_ids):
                time.sleep(args.pause)

    print(f"[{SITE['key']}] 完成：新增合计 {grand_new} 条，用时 {time.perf_counter() - t_all:.0f}s",
          flush=True)
    return 0


def _load_done(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    done = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            done.add((r.get("source", ""), str(r.get("id", ""))))
    return done


if __name__ == "__main__":
    sys.exit(main())
