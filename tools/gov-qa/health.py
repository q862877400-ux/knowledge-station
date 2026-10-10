"""健康结论 —— spec 004 的 US4（FR-017 ~ FR-021 / SC-009 ~ SC-011）。

## 它回答一个问题

> **「我现在能不能拿这份数据去做分析？」**

输出**首行即结论**（宪法 I「说人话」），不用内部术语。

## 与 check.sh 的关系

| | `check.sh` | `health.py` |
|---|---|---|
| 给谁用 | **Stop hook**（机器） | **人** |
| 回答 | 「能不能停」 | 「能不能用」 |
| 输出 | 过/不过 + 简因 | 可用/不可用 + 完整实测值 + 一句话解释 |
| 速度要求 | **极快**（hook 有 300s 超时，已因超时踩过坑） | 可以慢一些、详细一些 |

⇒ **不要合并**。判据一致，用途不同。

## 用法

```bash
$P tools/gov-qa/health.py              # 一句话结论（主用法）
$P tools/gov-qa/health.py --detail     # 展开每项实测值
$P tools/gov-qa/health.py --quiet      # 纯 ASCII（给脚本用）
$P tools/gov-qa/health.py --trace f    # 追加执行轨迹
```

## 退出码

`0` 可用 ｜ `1` 不可用 ｜ `2` 体检本身失败
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common import ascii_kv, has_label, human                     # noqa: E402

DATA = HERE / "data"
FLOOR_FILE = HERE.parent.parent / ".round-floor"
COVERAGE_GATE = 90.0

VERDICT_OK = "usable"
VERDICT_BAD = "not_usable"


def _count_lines(p: str) -> int:
    n = 0
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for _ in fh:
                n += 1
    except OSError:
        pass
    return n


def count_empty_adapters(files: "list[str]") -> int:
    """数「零数据适配器」。

    ⚠ **抽成独立函数是为了可测** —— 测试用临时数据目录时，
    331 个 adapter 会全部被判「零数据」（它们的数据文件不在临时目录里），
    这**是正确行为**但让测试无法构造「健康」场景。
    ⇒ 测试里 mock 这个函数即可。
    """
    try:
        import adapters
    except Exception:                                                   # noqa: BLE001
        return 0
    keys = list(adapters.ADAPTERS)
    bases = [Path(p).name for p in files]
    prefixes = []
    for k in keys:
        try:
            prefixes.append((f"{adapters.load(k).SITE['key']}-", k))
        except Exception:                                               # noqa: BLE001
            prefixes.append((f"{k}-", k))
    prefixes.sort(key=lambda x: -len(x[0]))
    have = set()
    for b in bases:
        for pre, k in prefixes:
            if b.startswith(pre):
                have.add(k)
                break
    return sum(1 for k in keys if k not in have)


def count_adapters() -> int:
    try:
        import adapters
        return len(adapters.ADAPTERS)
    except Exception:                                                   # noqa: BLE001
        return 0


def collect() -> dict:
    """一次遍历收集全部判据（**一次运行检出全部故障**，SC-009）。"""
    files = sorted(glob.glob(str(DATA / "*.jsonl")))
    total = 0
    labeled = 0
    dups = 0
    for p in files:
        per_src: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip() or not line.lstrip().startswith("{"):
                        continue
                    try:
                        r = json.loads(line)
                    except Exception:                                   # noqa: BLE001
                        continue
                    total += 1
                    # ⚠ 口径唯一出处 = `common.has_label(strict=True)`（spec 005 T105）。
                    #   此前这里是内联的 `ex.get("msg_type_norm")`，与 `label-coverage.py`
                    #   各算各的（那边回落到脏 `msg_type`）⇒ 同一指标两个数字。
                    if has_label(r, strict=True):
                        labeled += 1
                    per_src[str(r.get("source") or "?")][str(r.get("id"))] += 1
        except OSError:
            continue
        for c in per_src.values():
            dups += sum(c.values()) - len(c)

    n_empty = count_empty_adapters(files)
    n_keys = count_adapters()

    floor = 0
    try:
        floor = int("".join(ch for ch in FLOOR_FILE.read_text(encoding="utf-8")
                            if ch.isdigit()) or "0")
    except OSError:
        pass

    coverage = (labeled / total * 100) if total else 0.0
    return {"total": total, "floor": floor, "empty": n_empty, "dups": dups,
            "coverage": round(coverage, 1), "adapters": n_keys}


def build_checks(s: dict) -> list:
    """把实测值判成 `(名称, 是否通过, 详情)` 列表。

    ⚠⚠ **抽成独立函数是有原因的**（spec 005 T112，2026-10-10）：
    原来这四行**内联在 `main()` 里**，独立复核发现"把任意一项改成恒真，
    测试全绿；四项同时改才变红" —— 也就是**每项判据没有被各自钉住**，
    `test_health_detects_all_three_faults` 只验证了输出格式。
    ⇒ 抽出来后，测试可以对**单项**造故障并断言**该项**失败
    （见 `tests/test_health_checks.py`）。
    """
    return [
        ("数据总数 ≥ 地板", s["total"] >= s["floor"],
         f"{s['total']:,} ≥ {s['floor']:,}"),
        ("无零数据适配器", s["empty"] == 0, f"{s['empty']} 个"),
        ("无重复 id", s["dups"] == 0, f"{s['dups']} 行"),
        (f"标签覆盖率 ≥ {COVERAGE_GATE:.0f}%",
         s["coverage"] >= COVERAGE_GATE, f"{s['coverage']}%"),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="健康结论（spec 004 US4）")
    ap.add_argument("--detail", action="store_true", help="展开每项实测值")
    ap.add_argument("--quiet", action="store_true", help="纯 ASCII")
    ap.add_argument("--trace", default="", help="追加执行轨迹到该文件")
    args = ap.parse_args()

    t0 = time.time()
    try:
        s = collect()
    except Exception as e:                                              # noqa: BLE001
        human(f"❌ 体检本身失败：{type(e).__name__}: {e}")
        return 2
    elapsed = round(time.time() - t0, 1)

    # ---- 逐项判定（构造抽到 `build_checks`，便于单测）------------------
    checks = build_checks(s)

    failed = [(n, d) for n, ok, d in checks if not ok]
    verdict = VERDICT_OK if not failed else VERDICT_BAD

    # ---- 输出 ----------------------------------------------------------
    if args.quiet:
        kv = {"VERDICT": verdict, "TOTAL": s["total"], "FLOOR": s["floor"],
              "EMPTY": s["empty"], "DUPS": s["dups"],
              "COVERAGE": s["coverage"], "COVERAGE_GATE": COVERAGE_GATE,
              "ELAPSED": elapsed, "ADAPTERS": s["adapters"]}
        ascii_kv(kv)
    else:
        # **首行即结论**（宪法 I）
        if verdict == VERDICT_OK:
            human(f"✅ 当前可用：{s['total']:,} 条 / {s['empty']} 空通道 / "
                  f"{s['dups']} 重复 / 标签覆盖 {s['coverage']}%")
        else:
            why = "；".join(f"{n}（{d}）" for n, d in failed)
            human(f"❌ 当前不可用：{why}")
        human("")
        for n, ok, d in checks:
            mark = "✅" if ok else "❌"
            human(f"  {mark} {n:22s} {d}")
        human(f"  ⏱️  用时 {elapsed}s" + ("" if elapsed <= 60 else "  ⚠️ 超 60s"))

    if args.trace:
        try:
            with open(args.trace, "a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%F %T')} verdict={verdict} "
                         f"total={s['total']} empty={s['empty']} "
                         f"dups={s['dups']} cov={s['coverage']} "
                         f"elapsed={elapsed}\n")
        except OSError:
            pass

    return 0 if verdict == VERDICT_OK else 1


if __name__ == "__main__":
    sys.exit(main())
