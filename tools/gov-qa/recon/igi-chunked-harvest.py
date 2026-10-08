"""按 siteId 分片、逐片落盘的 IGI 采集驱动。

## 为什么需要它

`harvest.py` **只在跑完时落盘**（第 127 行先收全量 `rows`，第 144 行才写文件）。
对 `cq-igi` 这种 **75 site / 3.2 万条 / 约 14 小时** 的长任务，
中途一旦中断（超时、网络、手动重启）就是**零产出** —— 全部白跑。

本驱动**逐个 siteId 采完即追加落盘** ⇒ 中断只损失「当前那一个 siteId」，
已完成的部分留在文件里；重跑时按 (source, id) 去重，天然续采。

## 用法

```bash
cd "D:/AI/work space/zcode"
.venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked-harvest.py cq_igi
.venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked-harvest.py cq_igi --only 251,254,266
.venv/Scripts/python.exe tools/gov-qa/recon/igi-chunked-harvest.py gs_zhangye
```

第 1 个参数是 `adapters/` 下的模块名（需含 `SITE` / `SITE_IDS` / `BASE` / `REFERER` /
`APP_ID` / `GROUP_ID`）。可选 `--only <sid,sid>` 只跑指定 siteId、`--limit N` 总量上限。

**只写 `data/`，不改任何代码。**
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


def load_done(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    done = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            done.add((r.get("source", ""), str(r.get("id", ""))))
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("module", help="adapters/ 下的模块名，如 cq_igi")
    ap.add_argument("--only", default="", help="只跑指定 siteId，逗号分隔")
    ap.add_argument("--limit", type=int, default=0, help="总量上限（0 = 不限）")
    ap.add_argument("--pause", type=float, default=1.2, help="siteId 之间的间隔秒数")
    args = ap.parse_args()

    import httpx
    from adapters._igi_common import harvest_igi

    mod = __import__(f"adapters.{args.module}", fromlist=["SITE"])
    SITE = mod.SITE
    site_ids = [s.strip() for s in args.only.split(",") if s.strip()] or list(mod.SITE_IDS)

    DATA.mkdir(parents=True, exist_ok=True)
    out_path = DATA / f"{SITE['key']}-{SITE['name']}.jsonl"
    done = load_done(out_path)
    print(f"[{SITE['key']}] → {out_path.name}（已有 {len(done)} 条）", flush=True)
    print(f"[{SITE['key']}] 待跑 {len(site_ids)} 个 siteId：{','.join(site_ids)}", flush=True)

    grand_new = 0
    t_all = time.perf_counter()
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        fetcher = _Fetcher(cli)
        for i, sid in enumerate(site_ids, 1):
            if args.limit and grand_new >= args.limit:
                break
            sub_site = dict(SITE)
            sub_site["key"] = f"{SITE['key']}-{sid}"
            remain = (args.limit - grand_new) if args.limit else None
            t0 = time.perf_counter()
            try:
                rows = harvest_igi(
                    fetcher, SITE=sub_site, base=mod.BASE, site_id=sid,
                    app_id=mod.APP_ID, group_id=mod.GROUP_ID, referer=mod.REFERER,
                    limit=remain, max_pages=300)
            except Exception as e:                                  # noqa: BLE001
                print(f"  [{i}/{len(site_ids)}] siteId={sid} 失败 "
                      f"{type(e).__name__}: {e}（跳过，继续）", flush=True)
                continue
            fresh = [r for r in rows if (r["source"], str(r["id"])) not in done]
            for r in fresh:
                done.add((r["source"], str(r["id"])))
            if fresh:
                with out_path.open("a", encoding="utf-8") as fh:
                    for r in fresh:
                        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            grand_new += len(fresh)
            print(f"  [{i}/{len(site_ids)}] siteId={sid}: 取 {len(rows)} / "
                  f"新增 {len(fresh)}（{time.perf_counter() - t0:.0f}s，"
                  f"累计新增 {grand_new}）", flush=True)
            if i < len(site_ids):
                time.sleep(args.pause)

    print(f"[{SITE['key']}] 完成：新增合计 {grand_new} 条，"
          f"用时 {time.perf_counter() - t_all:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
