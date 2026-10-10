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
    """轮询一个通道。**绝不抛异常** —— 任何错误都转成返回值（FR-021 故障隔离）。

    ## 增量算法（R1 的落地）

    政务列表**新内容在顶部** ⇒ 正确策略是：

        从第 1 页开始翻 → 每翻一批检查「这批是否全部已见过」
          ├─ 全部已见过 ⇒ **停**（水位已到最新）
          └─ 有新的     ⇒ 继续翻下一批

    这比「记页码」健壮 —— 列表会因新增内容整体后移，页码会漂。

    ## 为什么不用「一次取很多条 + 去重」

    那样**幂等性对、但没省下请求**，等于没做增量。
    真正省请求才是增量的完整价值（quickstart 场景 1.3 明确要求看 `pages_fetched`）。
    """
    key = channel.key
    t0 = time.time()
    result = {"key": key, "added": 0, "pages": 0, "batches": 0,
              "status": "ok", "error": None}

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

    fetch = _make_fetch()

    # ---- 迭代式增量抓取 -------------------------------------------------
    # ⚠ **关键机制**：adapter 每次调用都**从第 1 页开始**（它们不支持「从第 N 页开始」
    #   的入参），只认环境变量 `GOVQA_PAGE_FROM`。所以要推进页码，必须**每批改这个环境变量**。
    #   这是本轮实测发现的 —— 一开始没设它，循环每批都拿到同一页数据。
    BATCH = 400                         # 每批条数上限
    MAX_BATCHES = 50                    # 安全上限，防死循环
    PAGE_STEP = 20                      # 每批推进的页数（pageSize 多数是 20）
    all_new: list[dict] = []
    batches = 0
    pages = 0
    page_from = 1
    degraded_reason = None
    prev_env = os.environ.get("GOVQA_PAGE_FROM")

    try:
        while batches < MAX_BATCHES:
            batches += 1
            os.environ["GOVQA_PAGE_FROM"] = str(page_from)
            try:
                recs = adapter.harvest(fetch, limit=BATCH)
            except Exception as e:                                      # noqa: BLE001
                if batches == 1:
                    result["status"] = "failed"
                    result["error"] = f"{type(e).__name__}: {str(e)[:80]}"
                    store.mark_failure(key)
                    return result
                degraded_reason = f"第 {batches} 批失败：{type(e).__name__}（已收部分）"
                break

            if not isinstance(recs, list) or not recs:
                break

            got_pages = int(getattr(adapter, "last_pages_fetched", 0) or 0)
            pages += got_pages or PAGE_STEP

            new_this = []
            for r in recs:
                rid = str(r.get("id") or "")
                if not rid or rid in seen:
                    continue
                seen.add(rid)
                new_this.append(r)
            all_new.extend(new_this)

            # 停：本批没有新记录 ⇒ 已翻到水位（R1）
            if _should_stop(recs, new_this, need_full, wm):
                break

            # 推进页码继续翻（新内容都在顶部，越往后越旧）
            page_from += got_pages or PAGE_STEP
    finally:
        # 恢复环境变量 —— 不能污染调用方的环境
        if prev_env is None:
            os.environ.pop("GOVQA_PAGE_FROM", None)
        else:
            os.environ["GOVQA_PAGE_FROM"] = prev_env

    if degraded_reason:
        result["degraded"] = degraded_reason

    # ---- 落盘（边采边落盘，T016） --------------------------------------
    if not dry_run and all_new:
        out_path = data_path_for(key, site_name)
        for r in all_new:
            r.setdefault("extra", {})
            if isinstance(r["extra"], dict):
                r["extra"]["ingested_at"] = now_iso()
            atomic_append_jsonl(out_path, r)                            # 每条 fsync

    result["added"] = len(all_new)
    result["pages"] = pages
    result["batches"] = batches

    # **只在成功后前移水位**（FR-003）
    if not dry_run:
        store.mark_success(key, new_value=_next_value(wm, all_new, need_full),
                           batch_count=len(all_new))
    result["watermark"] = store.get(key).value if store.get(key) else None
    result["elapsed"] = round(time.time() - t0, 1)
    return result


def _should_stop(recs, new_this, need_full: bool, wm) -> bool:
    """判断是否可以停止翻页（R1 的「翻到已知位置就停」）。

    - **全量模式**（`need_full`）：不早停 —— 目的就是把存量全拿下来
    - **`page` / `since` 型**：本批**没有任何新记录** ⇒ 已翻到水位，停
      （列表按时间倒序，新的在顶部；翻到全旧的说明后面的更旧）
    - **`idset` 型**：同上（本批全新是旧的 ⇒ 后面的更旧）
    """
    if need_full:
        return False
    return len(new_this) == 0


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
            # ⚠ 走 `ascii_kv` 而不是 `print`（spec 005 T109）。
            #   旧写法直接 `print(f"CHANNEL=...")` 绕过了纯 ASCII 出口：
            #   当前 345 个 key 恰好全是 ASCII 所以没崩，但**通道名一旦含中文**
            #   就会在 GBK 控制台上 `UnicodeEncodeError` —— 而这条路径是**给闸门读的**。
            #   同时删掉一行死代码 `ascii_kv({}, stream=None) if False else None`。
            ascii_kv({"CHANNEL": r["key"], "ADDED": r["added"], "STATUS": r["status"]})
    else:
        human("")
        human(f"汇总：成功 {ok} / 失败 {failed} ｜ 新增 {added:,} 条 ｜ 用时 {elapsed}s")
        if args.timing:
            human(f"翻页总数 pages_fetched={sum(r.get('pages', 0) for r in results)}"
                  f"（**只看「新增 0 条」不能证明增量生效，要看这个**）")

    return EXIT_OK if failed == 0 else EXIT_PARTIAL


if __name__ == "__main__":
    sys.exit(main())
