#!/usr/bin/env python
"""幂等验证器（spec 004 T028 / SC-002、SC-003）。

## 这个脚本回答一个问题

> **对真实通道，连续两次轮询，第二次会不会新增 0 条、且不产生重复？**

## 与测试的关系（别搞混）

`tests/test_poll.py` 里的 `test_idempotent_second_run_adds_zero` 用**假适配器**
（`FakeAdapter`）钉住了 `poll_one` 的幂等语义 —— 那证明**代码逻辑**对。

本脚本证明的是**真实通道**上对：它拿**已落盘的语料**当"上游返回"，
跑一遍真实的 `poll_one`，看是否 0 新增。这能抓到假适配器抓不到的东西
（真实 id 形态、真实水位线、真实文件命名）。

⇒ 两者**互补**，不是重复。

## 用法

    python tools/gov-qa/recon/verify-idempotent.py            # 全部通道
    python tools/gov-qa/recon/verify-idempotent.py --limit 20 # 只验前 20 个
    python tools/gov-qa/recon/verify-idempotent.py --quiet    # 机器可读
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import poll                                                             # noqa: E402
from channel import load_channels                                       # noqa: E402
from common import ascii_kv, safe_print                                 # noqa: E402
from poll import poll_one                                               # noqa: E402
from state import WatermarkStore                                        # noqa: E402

DATA = ROOT / "data"


class _Isolated:
    """把 `poll.DATA_DIR` 指到临时目录 —— **与 `tests/test_poll.py` 同法**。

    ⚠⚠ **不隔离就是灾难**：`poll_one` 写的是 `poll.DATA_DIR`（默认 = 真实
    `tools/gov-qa/data/`）。我第一版忘了隔离 ⇒ 验证器**往真实语料目录写数据**。
    本模块已有过一次同样的教训（"测试污染真实数据 —— 没隔离 `poll.DATA_DIR`，
    往真实目录写了 `fake-1-fake.jsonl`"）。
    ⇒ 这个上下文管理器是本脚本**唯一的**隔离手段，不得绕过。
    """

    def __init__(self, root: Path):
        self.root = root
        self.old = None

    def __enter__(self):
        (self.root / "data").mkdir(parents=True, exist_ok=True)
        self.old = poll.DATA_DIR
        poll.DATA_DIR = self.root / "data"
        return self

    def __exit__(self, *a):
        poll.DATA_DIR = self.old


class ReplayAdapter:
    """把**已落盘的记录**当"上游返回"重放。

    这样不需要联网就能验证：`poll_one` 对同一批上游数据跑两次，
    第二次是否 0 新增。**这是幂等性的直接判据。**

    ⚠ 接口必须是 `harvest(fetch, limit=)`（`poll_one` 就是这么调的）。
    我第一版写成了 `fetch()` ⇒ `poll_one` 拿不到记录、两次都 0 新增
    ⇒ **判据全绿但是假的**（"没跑"和"跑了通过"分不出来）。
    ⇒ 现在加断言：**第一次必须真的新增 > 0**，否则判"判据无效"。
    """

    def __init__(self, records: list[dict], key: str):
        self._records = records
        self.key = key

    def harvest(self, fetch, *, limit: int | None = None, **kw):
        recs = list(self._records)
        return recs[:limit] if limit else recs


def records_for(key: str, limit: int | None = None) -> list[dict]:
    """读某个通道已落盘的记录（按文件名前缀匹配）。"""
    out: list[dict] = []
    for p in sorted(DATA.glob(f"{key}-*.jsonl")):
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip() or not line.lstrip().startswith("{"):
                        continue
                    try:
                        out.append(json.loads(line))
                    except Exception:                                   # noqa: BLE001
                        continue
        except OSError:
            continue
        if limit and len(out) >= limit:
            break
    return out[:limit] if limit else out


def verify_one(ch, limit: int | None) -> dict:
    """验一个通道：跑两遍 `poll_one`，第二遍必须 0 新增。"""
    recs = records_for(ch.key, limit)
    if not recs:
        return {"key": ch.key, "skipped": "无落盘语料", "ok": None}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        store = WatermarkStore(td / "watermarks.json")
        with _Isolated(td):
            # 第一次：应全新增
            r1 = poll_one(ReplayAdapter(recs, ch.key), ch, store, dry_run=False,
                          force_full=True, site_name=ch.key)
            # 第二次：上游无变化 ⇒ 必须 0 新增
            r2 = poll_one(ReplayAdapter(recs, ch.key), ch, store, dry_run=False,
                          force_full=False, site_name=ch.key)
            added2 = int(r2.get("added", -1))
            # 落盘侧：不得有重复 id
            dup = _count_dups(td / "data")
        first = int(r1.get("added", -1))
        # ⚠ **判据有效性前置条件**：第一次必须真的写进去东西。
        #   否则"第二次 0 新增"是**因为压根没跑**，不是因为它幂等
        #   （我第一版就踩了这个：接口写错 ⇒ 两次都 0，全绿但是假的）。
        if first <= 0:
            return {"key": ch.key, "n": len(recs), "first_added": first,
                    "second_added": added2, "dups": dup, "ok": None,
                    "skipped": f"判据无效：首次新增 {first}（重放没接上）"}
        return {"key": ch.key, "n": len(recs), "first_added": first,
                "second_added": added2, "dups": dup,
                "ok": added2 == 0 and dup == 0}


def _count_dups(d: Path) -> int:
    """落盘文件里重复 (source, id) 的条数。"""
    seen: dict[tuple, int] = {}
    for p in d.glob("*.jsonl"):
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip().startswith("{"):
                        continue
                    try:
                        r = json.loads(line)
                    except Exception:                                   # noqa: BLE001
                        continue
                    k = (str(r.get("source") or "?"), str(r.get("id")))
                    seen[k] = seen.get(k, 0) + 1
        except OSError:
            continue
    return sum(n - 1 for n in seen.values() if n > 1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="幂等验证器（spec 004 T028 / SC-002）")
    ap.add_argument("--limit", type=int, default=50,
                    help="每个通道最多用多少条语料重放（默认 50，0=全部）")
    ap.add_argument("--only", default="", help="只验这些通道（逗号分隔）")
    ap.add_argument("--quiet", action="store_true", help="机器可读输出")
    args = ap.parse_args(argv)

    limit = args.limit or None
    channels = load_channels()
    if args.only:
        want = {x.strip() for x in args.only.split(",") if x.strip()}
        channels = [c for c in channels if c.key in want]

    results = []
    for ch in channels:
        try:
            results.append(verify_one(ch, limit))
        except Exception as e:                                          # noqa: BLE001
            results.append({"key": ch.key, "error": f"{type(e).__name__}: {e}",
                            "ok": False})

    tested = [r for r in results if r.get("ok") is not None]
    bad = [r for r in tested if not r["ok"]]
    skipped = [r for r in results if r.get("ok") is None]

    if args.quiet:
        ascii_kv({
            "CHECKED": len(tested),
            "PASSED": len(tested) - len(bad),
            "FAILED": len(bad),
            "SKIPPED": len(skipped),
        })
        for r in bad:
            safe_print(f"  FAIL {r['key']}: second_added={r.get('second_added')} "
                       f"dups={r.get('dups')}")
        return 1 if bad else 0

    safe_print(f"幂等验证：{len(tested)} 个通道有语料可重放，"
               f"{len(skipped)} 个无语料跳过")
    safe_print("")
    if bad:
        safe_print("=== 不幂等（SC-002 未达成）===")
        for r in bad:
            safe_print(f"  {r['key']}: 第二次新增 {r.get('second_added')} 条，"
                       f"重复 {r.get('dups')} 条")
    else:
        safe_print("=== 全部幂等（第二次 0 新增、0 重复）===")
    safe_print("")
    for r in tested[:10]:
        safe_print(f"  {r['key']:24s} 语料 {r['n']:5,d}  首次 +{r['first_added']:5,d}  "
                   f"二次 +{r['second_added']}  重复 {r['dups']}  "
                   f"{'OK' if r['ok'] else '**FAIL**'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
