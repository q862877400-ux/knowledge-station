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

## 2026-10-09 追加：`--page-chunk N`（大站**站内**也能增量落盘）
原来的粒度是「一个 siteId 一个文件」，但**大站本身就能跑 2 小时** ——
实测 `sx-igi-24` 单站 5,998 条跑了 **8,133 s**，中途被中断 = **整站零产出**。
`--page-chunk 50` 把该站切成「每 50 页一窗口」，**每窗口落盘一次**
（配合 `_igi_common.harvest_igi(page_from=…)`）⇒ 中断只损失当前窗口。
不传 = 旧行为（整站翻完才落盘）。

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
    ap.add_argument("--page-chunk", type=int, default=0,
                    help=">0 时按**页窗口**切分（每窗口 N 页），逐窗口落盘；"
                         "0 = 旧行为（整站翻完才落盘）")
    ap.add_argument("--max-pages", type=int, default=0,
                    help="绝对页数上界（0 = 自动：有 --sites-json 的 total 就按它算，"
                         "否则 300）。`--only` 路径没有 total，**必须显式给**，"
                         "否则会空翻 300 个窗口")
    ap.add_argument("--pause", type=float, default=1.2, help="siteId 之间的间隔秒数")
    ap.add_argument("--retries", type=int, default=2, help="单个 siteId 失败后的重试次数")
    ap.add_argument("--cooldown", type=float, default=30.0, help="重试前的冷却秒数")
    ap.add_argument("--abort-after", type=int, default=8, help="连续多少个 siteId 失败即中止整轮")
    args = ap.parse_args()

    import httpx
    from adapters._igi_common import PAGE_SIZE, existing_ids, harvest_igi

    mod = __import__(f"adapters.{args.module}", fromlist=["SITE"])
    SITE = mod.SITE
    strip = getattr(mod, "postprocess", None) or getattr(mod, "strip_portal_geo", None)

    site_totals: dict[str, int] = {}
    if args.only:
        site_ids = [s.strip() for s in args.only.split(",") if s.strip()]
    elif args.sites_json:
        p = HERE / args.sites_json
        sites = json.loads(p.read_text(encoding="utf-8"))["sites"]
        site_totals = {str(k): int(v) for k, v in sites.items()}
        site_ids = [k for k, _ in sorted(sites.items(), key=lambda kv: -kv[1])]
    else:
        site_ids = list(mod.SITE_IDS)

    #: 除本适配器已落盘 id 外，还要并进来做去重的「兄弟源」（同门户另一入口，可能暴露同一批信件）。
    #: 模块用 `EXTRA_SEEN_KEYS = ("gz-portal",)` 声明。
    #: ⚠ 2026-10-09 修：原先**硬编码**了 `existing_ids("sx-szxx")` ⇒ 对宁夏/广西等模块
    #: 会把山西的 400 个 id 并进 `skip_ids`（**跨省 id 污染**，日志里那句
    #: 「已落盘 400 条」对宁夏来说其实一个都不是宁夏的）。现改为仅按模块声明并。
    seen = existing_ids(SITE["key"])
    for _k in getattr(mod, "EXTRA_SEEN_KEYS", ()):
        seen |= existing_ids(_k)
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
            t0 = time.perf_counter()
            site_new = 0
            failed = False

            # ★ 页窗口（--page-chunk N>0）：把大站切成「每窗口 N 页」，**逐窗口落盘**。
            #   动机见 `_igi_common.harvest_igi` 的 `page_from` 说明 —— `harvest_igi` 是
            #   「翻完页才返回」，所以一个 5,000 条的大站要跑约 2 小时，任何中断都
            #   **整站零产出**（逐 siteId 落盘救不了站内的部分）。
            #   2026-10-09 实测 `sx-igi-24` 单站 5,998 条跑了 8,133 s ⇒ 必须能切。
            abs_pages = args.max_pages or _abs_pages(site_totals, sid, PAGE_SIZE)
            for (pf, pt) in _page_windows(args.page_chunk, abs_pages):
                remain = (args.limit - grand_new) if args.limit else None
                if remain is not None and remain <= 0:
                    break
                rows = None
                for attempt in range(args.retries + 1):
                    try:
                        rows = harvest_igi(
                            fetcher, SITE=sub_site, base=mod.BASE, site_id=sid,
                            app_id=mod.APP_ID, group_id=mod.GROUP_ID, referer=mod.REFERER,
                            limit=remain, max_pages=pt, page_from=pf, skip_ids=seen)
                        break
                    except Exception as e:                               # noqa: BLE001
                        if attempt < args.retries:
                            print(f"  [{i}/{len(site_ids)}] siteId={sid} 页{pf}-{pt} "
                                  f"{type(e).__name__}，{args.cooldown:.0f}s 后重试 "
                                  f"{attempt + 1}/{args.retries}", flush=True)
                            time.sleep(args.cooldown)
                        else:
                            print(f"  [{i}/{len(site_ids)}] siteId={sid} 页{pf}-{pt} 失败 "
                                  f"{type(e).__name__}: {e}（已重试 {args.retries} 次，跳过）",
                                  flush=True)
                if rows is None:
                    failed = True
                    break

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
                site_new += len(fresh)
                print(f"  [{i}/{len(site_ids)}] siteId={sid} 页{pf}-{pt}: 新增 {len(fresh)}"
                      f"（本站 {site_new} / 全局 {grand_new}，{time.perf_counter() - t0:.0f}s）",
                      flush=True)
                if args.limit and grand_new >= args.limit:
                    break

            if failed:
                consec_fail += 1
                if consec_fail >= args.abort_after:
                    print(f"  ⚠ 连续 {consec_fail} 个 siteId 失败 ⇒ 中止本轮"
                          f"（疑似限流，稍后再跑可续采）", flush=True)
                    break
                continue
            consec_fail = 0
            print(f"  [{i}/{len(site_ids)}] siteId={sid}: 本站新增 {site_new}"
                  f"（{time.perf_counter() - t0:.0f}s）", flush=True)
            if i < len(site_ids):
                time.sleep(args.pause)

    print(f"[{SITE['key']}] 完成：新增合计 {grand_new} 条，用时 {time.perf_counter() - t_all:.0f}s",
          flush=True)
    return 0


def _abs_pages(site_totals: dict, sid: str, page_size: int) -> int:
    """该 siteId 的**绝对页数上界**。

    有枚举 `total` 就按 `ceil(total/page_size)` 算（`--sites-json` 路径）；
    否则退回 **300**（= 旧代码里的硬顶，`--only` 路径没有 total 可用）。
    """
    tot = site_totals.get(str(sid))
    if not tot:
        return 300
    return max(1, -(-int(tot) // page_size))


def _page_windows(chunk: int, abs_pages: int) -> list[tuple[int, int]]:
    """把 `1..abs_pages` 切成页窗口；`chunk<=0` ⇒ **单窗口 = 旧行为**。"""
    if chunk <= 0:
        return [(1, abs_pages)]
    out: list[tuple[int, int]] = []
    pf = 1
    while pf <= abs_pages:
        pt = min(pf + chunk - 1, abs_pages)
        out.append((pf, pt))
        pf = pt + 1
    return out


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
