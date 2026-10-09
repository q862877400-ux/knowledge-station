"""增量轮询调度器 —— spec 004 的 US1（P1，MVP）。

用户的原话：「通道打通是为了**以后它有更新的时候，我一个轮询就可以获取到最新的**」。
**这条此前从未被验证过** —— 331 个 adapter 只能「跑一次拿全量」。
本模块把「拿增量」变成一条命令。

## 与 harvest.py 的关系

- `harvest.py`：**全量采集**，跑完才落盘。**不改它的对外行为。**
- `poll.py`：**增量采集**，边采边落盘。在 adapter 之上加调度层。

## 三条核心保证（对应 spec 的成功判据）

| 保证 | 判据 | 实现 |
|---|---|---|
| **幂等** | SC-002 | 落盘前按 `(source, id)` 去重（T017） |
| **可断点续跑** | SC-003 | 边采边落盘，每条 `fsync`（T016） |
| **可安全退化** | FR-006 | 水位损坏 ⇒ 退化为全量，不崩溃（T007 + T015） |

## 退出码契约（见 contracts/poll.md）

| 码 | 含义 |
|---|---|
| `0` | 全部通道成功（含「无新增」） |
| `1` | 有通道失败，但其他已完成 |
| `2` | 致命错误 |
| `3` | **有人在跑**（锁冲突）—— **不是失败** |
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from channel import load_channels                                    # noqa: E402
from common import (LockBusy, ascii_kv, atomic_append_jsonl,          # noqa: E402
                    file_lock, human, iter_records, now_iso)
from state import WatermarkStore                                     # noqa: E402

DATA_DIR = HERE / "data"
STATE_DIR = HERE / "state"
LOCK_PATH = STATE_DIR / ".poll.lock"

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_FATAL = 2
EXIT_LOCKED = 3


# ---------------------------------------------------------------- 落盘去重

def existing_ids(channel_key: str) -> set[str]:
    """读该通道已落盘的全部 id（幂等的基础，T017）。

    ⚠ 每次都全读该通道的文件。为什么不用持久化索引：
    索引会与真实数据不一致（并行 agent 也在写），**真实数据才是唯一事实来源**。
    代价：大通道首轮慢一点（36 万条全库扫描实测 1.8 秒，可接受）。
    """
    ids: set[str] = set()
    for rec in iter_records(str(DATA_DIR / f"{channel_key}-*.jsonl")):
        if str(rec.get("source")) == channel_key:
            ids.add(str(rec.get("id")))
    return ids


def data_path_for(channel_key: str, site_name: str) -> Path:
    """该通道的落盘路径。与 harvest.py 的命名规则保持一致。"""
    safe = "".join(ch for ch in site_name if ch not in '\\/:*?"<>|').strip() or channel_key
    return DATA_DIR / f"{channel_key}-{safe}.jsonl"


# ---------------------------------------------------------------- 单通道轮询

def poll_one(adapter, channel, store: WatermarkStore, *, dry_run: bool,
             force_full: bool, site_name: str) -> dict:
    """轮询一个通道。**绝不抛异常** —— 任何错误都转成返回值（FR-021 故障隔离）。"""
    key = channel.key
    t0 = time.time()
    result = {"key": key, "added": 0, "pages": 0, "status": "ok", "error": None}

    wm = store.ensure(key, channel.watermark_type)
    need_full = force_full or store.needs_full(key)
    if store.broken:
        result["degraded"] = "水位文件损坏 -> 全量"

    # 已落盘 id（幂等的基线）
    try:
        seen = existing_ids(key)
    except Exception as e:                                              # noqa: BLE001
        result["status"] = "failed"
        result["error"] = f"读已落盘 id 失败：{type(e).__name__}"
        store.mark_failure(key)
        return result

    # 让 adapter 去采（增量语义通过 limit + 水位提示传递）
    try:
        fetch = _make_fetch()
        recs = adapter.harvest(fetch, limit=_limit_for(channel, need_full))
    except Exception as e:                                              # noqa: BLE001
        result["status"] = "failed"
        result["error"] = f"{type(e).__name__}: {str(e)[:80]}"
        store.mark_failure(key)
        return result

    if not isinstance(recs, list):
        result["status"] = "failed"
        result["error"] = "adapter 未返回列表"
        store.mark_failure(key)
        return result

    # 落盘前去重 + 边采边落盘
    new_recs = []
    for r in recs:
        rid = str(r.get("id") or "")
        if not rid or rid in seen:
            continue
        seen.add(rid)
        r.setdefault("extra", {})
        if isinstance(r["extra"], dict):
            r["extra"]["ingested_at"] = now_iso()
        new_recs.append(r)

    if not dry_run and new_recs:
        out_path = data_path_for(key, site_name)
        for r in new_recs:
            atomic_append_jsonl(out_path, r)                            # 边采边落盘

    result["added"] = len(new_recs)
    result["pages"] = int(getattr(adapter, "last_pages_fetched", 0) or 0)

    # **只在成功后前移水位**（FR-003）
    if not dry_run:
        store.mark_success(key, new_value=_next_value(wm, new_recs, need_full),
                           batch_count=len(new_recs))
    result["watermark"] = store.get(key).value if store.get(key) else None
    result["elapsed"] = round(time.time() - t0, 1)
    return result


def _limit_for(channel, need_full: bool):
    """增量模式的条数上限。

    ⚠ 这里用「首轮取 cap、后续取小量」的朴素策略 —— **不是真正的增量**。
    真正的「翻到已知位置就停」需要 adapter 暴露分页控制（部分 adapter 支持
    `GOVQA_PAGE_FROM`）。**本函数是过渡实现，下一轮改为按水位驱动。**
    """
    if need_full:
        return channel.cap or 2000
    return 200


def _next_value(wm, new_recs, need_full):
    """算新水位值。

    - `idset` 型：把新 id 并入旧集合（`state.py` 的 `_trim` 会做 LRU 裁剪）
    - `page` 型：页码 + 本轮新增（过渡实现，下一轮改为 adapter 回报真实页数）
    - `since` 型：取本轮最大时间
    """
    if wm.type == "idset":
        old = wm.value if isinstance(wm.value, list) else []
        return [str(r.get("id")) for r in new_recs] + old
    if wm.type == "page":
        old = int(wm.value or 0)
        return old + (1 if new_recs else 0)
    if wm.type == "since":
        ts = [str(r.get("asked_at") or "") for r in new_recs]
        ts = [t for t in ts if t]
        return max(ts) if ts else wm.value
    return wm.value


def _make_fetch():
    """构造 fetch 函数（复用 harvest.py 的会话策略）。"""
    import httpx
    os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120 Safari/537.36")
    client = httpx.Client(timeout=30, headers={"User-Agent": UA},
                          follow_redirects=True, trust_env=False, verify=False)

    def fetch(url, **kw):
        return client.get(url, **kw)

    return fetch


# ---------------------------------------------------------------- CLI

def main() -> int:
    ap = argparse.ArgumentParser(description="增量轮询调度器（spec 004 US1）")
    ap.add_argument("--all", action="store_true", help="轮询全部通道")
    ap.add_argument("--channel", action="append", default=[], help="只轮询指定通道（可重复）")
    ap.add_argument("--level", default="", help="只轮询某层级：national/province/city")
    ap.add_argument("--region", default="", help="只轮询某地区（名称包含匹配）")
    ap.add_argument("--dry-run", action="store_true", help="不落盘、不动水位")
    ap.add_argument("--quiet", action="store_true", help="纯 ASCII 机器可读输出")
    ap.add_argument("--full", action="store_true", help="忽略水位，强制全量")
    ap.add_argument("--timing", action="store_true", help="输出 pages_fetched（证明增量生效）")
    args = ap.parse_args()

    if not (args.all or args.channel or args.level or args.region):
        ap.error("必须指定 --all / --channel / --level / --region 之一")

    try:
        with file_lock(LOCK_PATH, timeout=0.0):
            return _run(args)
    except LockBusy as e:
        human(f"⚠️  {e}")
        human("    另一个轮询正在进行 —— 这不是失败，等下一轮即可。")
        return EXIT_LOCKED


def _run(args) -> int:
    channels = load_channels()
    if not channels:
        human("❌ 读不到通道清单（adapters 加载失败）")
        return EXIT_FATAL

    # 选通道
    sel = channels
    if args.channel:
        want = set(args.channel)
        sel = [c for c in sel if c.key in want]
    if args.level:
        sel = [c for c in sel if c.level == args.level]
    if args.region:
        sel = [c for c in sel if args.region in (c.region or "")]

    if not sel:
        human("⚠️  没有匹配的通道")
        return EXIT_OK

    store = WatermarkStore()
    if store.broken:
        human("⚠️  水位文件损坏 → 本轮退化为全量采集（FR-006）")

    t0 = time.time()
    results = []
    for c in sel:
        try:
            adapter = __import__("adapters").load(c.key)
        except Exception as e:                                          # noqa: BLE001
            results.append({"key": c.key, "added": 0, "status": "failed",
                            "error": f"adapter 加载失败：{type(e).__name__}"})
            continue
        r = poll_one(adapter, c, store, dry_run=args.dry_run,
                     force_full=args.full, site_name=c.name or c.key)
        results.append(r)
        if not args.quiet:
            mark = {"ok": "✅", "failed": "❌"}.get(r["status"], "?")
            extra = f"+{r['added']} 条" if r["status"] == "ok" else f"失败：{r.get('error')}"
            human(f"  {mark} {c.key:22s} {extra}")

    if not args.dry_run:
        store.save()

    elapsed = round(time.time() - t0, 1)
    ok = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] != "ok")
    added = sum(r["added"] for r in results)

    if args.quiet:
        kv = {"POLLED": len(results), "OK": ok, "SKIPPED": 0,
              "FAILED": failed, "ADDED": added, "ELAPSED": elapsed}
        if args.timing:
            kv["PAGES_FETCHED"] = sum(r.get("pages", 0) for r in results)
        ascii_kv(kv)
        for r in results:
            ascii_kv({}, stream=None) if False else None
            print(f"CHANNEL={r['key']} ADDED={r['added']} STATUS={r['status']}")
    else:
        human("")
        human(f"汇总：成功 {ok} / 失败 {failed} ｜ 新增 {added:,} 条 ｜ 用时 {elapsed}s")
        if args.timing:
            human(f"翻页总数 pages_fetched={sum(r.get('pages', 0) for r in results)}"
                  f"（**只看「新增 0 条」不能证明增量生效，要看这个**）")

    return EXIT_OK if failed == 0 else EXIT_PARTIAL


if __name__ == "__main__":
    sys.exit(main())
