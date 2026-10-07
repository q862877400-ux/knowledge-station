"""政务问答采集 · 统一入口。

## 用法
```powershell
# 看有哪些站、各自什么状态
.venv\\Scripts\\python.exe tools\\gov-qa\\harvest.py --list

# 采一个站（结果落到 data/<key>-<中文名>.jsonl，**按 id 去重、可反复跑**）
.venv\\Scripts\\python.exe tools\\gov-qa\\harvest.py --site mee

# 全采
.venv\\Scripts\\python.exe tools\\gov-qa\\harvest.py --site all

# 只试跑（不写盘）
.venv\\Scripts\\python.exe tools\\gov-qa\\harvest.py --site mee --limit 20 --dry-run
```

## 设计（给接手的人）
 · **采集与解析分家**：HTTP 与重试在这里；"怎么从一个站取出问答"在各站的
   `adapters/*.py` 里。**加站点不用改本文件**（在 `adapters/__init__.py` 的 `ADAPTERS` 登记即可）。
 · **去重靠 `(source, id)`**：重跑只追加新条目，不会重复。
 · **只写 `data/`**，不碰数据库、不碰生产件。

## 礼貌抓取的硬约束
 · 每站之间 `--pause`（默认 2 秒）；单站内部由适配器自己控制；
 · `--limit` 便于试跑；
 · **不许**把它当成镜像工具的入口 —— 目标是取"问答文本"当语料，不是复制网站。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))          # 让 `import adapters` 生效

# ⚠ 本仓 G27：`NO_PROXY` 里含 `[::1]` ⇒ httpx 0.28.1 **连 Client() 都构造不出来**
#   （`InvalidURL: Invalid port: ':1]'`）。就地修成 `::1`。
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
DATA = HERE / "data"


def _load_done(path: Path) -> set[tuple[str, str]]:
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
    ap.add_argument("--site", default="all", help="站点 key（见 --list），或 all")
    ap.add_argument("--limit", type=int, default=0, help="每站最多取多少条（试跑用）")
    ap.add_argument("--pause", type=float, default=2.0, help="站与站之间的间隔秒数")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写盘")
    ap.add_argument("--list", action="store_true", help="列出已登记的站点")
    args = ap.parse_args()

    import adapters

    if args.list:
        print(f"{'key':8s} {'站点':16s} {'取法':8s} {'层级':10s} 状态    说明")
        for k in sorted(adapters.ADAPTERS):
            m = adapters.load(k)
            s = m.SITE
            print(f"{s['key']:8s} {s['name']:16s} {s['kind']:8s} {s.get('level',''):10s} "
                  f"{s.get('status',''):7s} {s.get('note','')[:60]}")
        return 0

    keys = sorted(adapters.ADAPTERS) if args.site == "all" else [args.site]
    import httpx

    DATA.mkdir(parents=True, exist_ok=True)
    grand_new = 0

    class _Fetcher:
        """注入给适配器的 HTTP 函数：可调用（=GET，兼容旧适配器）+ .post。

        人民网留言板等站点的列表/详情接口是 POST —— 旧约定只有 `cli.get`，
        这里包一层让适配器按需取用；旧适配器把 fetch 当函数调，行为不变。
        """

        def __init__(self, client):
            self._c = client

        def __call__(self, url, **kw):
            return self._c.get(url, **kw)

        def post(self, url, **kw):
            return self._c.post(url, **kw)

    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        fetcher = _Fetcher(cli)
        for k in keys:
            mod = adapters.load(k)
            site = mod.SITE
            out_path = DATA / f"{site['key']}-{site['name']}.jsonl"
            done = _load_done(out_path)
            print(f"\n[{site['key']}] {site['name']} → {out_path.name}"
                  f"（已有 {len(done)} 条）", flush=True)
            t0 = time.perf_counter()
            try:
                rows = mod.harvest(fetcher, limit=args.limit or None)
            except Exception as e:                                          # noqa: BLE001
                # ⚠ Windows 控制台常是 GBK：错误消息里别用非 GBK 字符，否则
                # 这一行自己会 UnicodeEncodeError，把真正的错误吞掉（踩过）
                print(f"    [采集失败] {type(e).__name__}: {e}")
                continue
            fresh = [r for r in rows if (r["source"], str(r["id"])) not in done]
            print(f"    取到 {len(rows)} 条，其中**新增 {len(fresh)} 条**"
                  f"（用时 {time.perf_counter()-t0:.0f}s）", flush=True)
            if args.dry_run:
                for r in fresh[:3]:
                    print(f"      · {(r['question'] or '')[:60]}")
                    print(f"        {(r['answer'] or '')[:80]}")
            else:
                if fresh:                     # 0 新增时不建空文件（403 空跑会留垃圾）
                    with out_path.open("a", encoding="utf-8") as fh:
                        for r in fresh:
                            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                    print(f"    已追加到 {out_path}")
            grand_new += len(fresh)
            time.sleep(args.pause)

    print(f"\n[harvest] 全部完成，新增合计 {grand_new} 条。")
    print("[harvest] 下一步：跑 `measure-locate-rate.py` 看这些条目能不能当考卷。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
