"""数据质量闸门 —— **四项静默缺陷判据的唯一数字源**（spec 005 / T102）。

## 为什么需要它

现有的闸门（`gate/check.sh`）只查四件事：总数、零数据适配器、重复 id、标签覆盖率。
2026-10-10 的独立诊断证明，**这四项都不覆盖"字段非空但内容是垃圾"**：

| 缺陷 | 实测 | 旧闸门为何看不见 |
|---|---|---|
| 答复为空 | `xz-lasa` 全源 1,030 条（100%） | 只看条数，条数正常 |
| 内容重复 | 8,462 条（5,642 组，id 各不相同） | 只比 `id`，不比内容 |
| 时间倒置 | `ln-8890` 7,807 条（答复早于提问） | 无任何字段语义判据 |
| 标签口径分裂 | `health.py` 报 99.2 / `label-coverage.py` 报 100.0 | 两个出处，闸门用宽的那个 |

⇒ 本脚本把这四项做成**以退出码说话**的判据。**只读，不写任何数据。**

## 用法

```powershell
$P = .venv\\Scripts\\python.exe
& $P tools/gov-qa/recon/gate-quality.py            # 给人看（中文）
& $P tools/gov-qa/recon/gate-quality.py --quiet    # 给闸门看（纯 ASCII KEY=VALUE）
& $P tools/gov-qa/recon/gate-quality.py --detail   # 展开到源
& $P tools/gov-qa/recon/gate-quality.py --update-baseline   # 修好后重记棘轮基线
```

**退出码**：0 = 全部达标 / 1 = 有超阈值项 / 2 = 执行失败。

## 判据有两层（**都要过**）

1. **绝对阈值**（`MAX_*` 常量）—— 缺陷必须清零。**`--strict` 才判。**
2. **棘轮**（`quality-baseline.json`）—— **只许变好，不许变坏**。**默认就判。**

### ⚠ 为什么默认只判棘轮（这是过渡态，不是放宽）

本模块的缺陷是**分批还的**（Phase 2）。在还清之前：

- 若默认判绝对阈值 ⇒ 门禁**从一开始就红** ⇒ 按本仓纪律"门禁红了不许推进"，
  等于自己把自己堵死；
- 若默认什么都不判 ⇒ 缺陷**会继续恶化**（实测：`time_inverted` 在诊断后
  由 7,807 涨到 20,131，因为并行采集还在加数据）。

⇒ 默认判**棘轮**：门禁绿，但**任何指标变坏当场报红**。
`--strict` 判绝对阈值，**Phase 2 把缺陷清零后由门禁改用 `--strict`**。

**过渡期可见性**：非 `--strict` 时，绝对阈值的失败项仍**照常打印**（打 `[!!]`），
只是不进退出码 —— 不允许"悄悄藏起来"。

## 用法

```powershell
$P = .venv\\Scripts\\python.exe
& $P tools/gov-qa/recon/gate-quality.py            # 给人看（中文）
& $P tools/gov-qa/recon/gate-quality.py --quiet    # 给闸门看（纯 ASCII KEY=VALUE）
& $P tools/gov-qa/recon/gate-quality.py --detail   # 展开到源
& $P tools/gov-qa/recon/gate-quality.py --strict   # 绝对阈值也判（Phase 2 后启用）
& $P tools/gov-qa/recon/gate-quality.py --update-baseline   # 修好后重记棘轮基线
```
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent          # tools/gov-qa/recon
ROOT = HERE.parent                              # tools/gov-qa
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"

#: 棘轮基线文件（只许变好）。与 `scripts/gates-baseline.json` 同一套办法。
BASELINE = HERE / "quality-baseline.json"

# ---- 阈值（可调，集中在这里，不散落在代码里） --------------------------------
#: 全库答复为空率的容忍上限（比例）。实测 `xz-lasa` 单源 100% 为空。
MAX_EMPTY_ANSWER_RATE = 0.005
#: 单个源的答复为空率上限 —— 超过就指名道姓（不能只报全库平均，会被大源稀释）。
MAX_SOURCE_EMPTY_RATE = 0.10
#: 内容重复（同 question+answer 但 id 不同）的容忍条数。
MAX_CONTENT_DUPS = 0
#: 时间倒置（answered_at < asked_at）的容忍条数。
MAX_TIME_INVERTED = 0

#: 棘轮容差：每十万条的缺陷率允许的抖动（浮点/采样）。
_RATCHET_EPS = 0.05

#: 时间倒置的容忍秒数。
#:
#: ⚠⚠ **必须解析后比较，不能直接比字符串**（2026-10-10 实测踩到）。
#: 第一版用 `str(answered) < str(asked)` 裸比字符串，报出 20,131 条"倒置"，
#: 逐条看下来**大半是假阳性**，三种形态：
#:   1. `Thu Oct 19 10:57:25 CST 2023` vs `Fri Oct 20 …` —— 字母序 `Fri` < `Thu`，
#:      但 10-20 明明晚于 10-19（`nat-tax` 5,720 条全是这个）
#:   2. `2021-09-22 15:02:00` vs `2021-09-22 15:02` —— 同一分钟，短串排前面
#:   3. `2026年09月7日` vs `2026年09月09日` —— `"7" > "0"`，但 9-7 早于 9-9
#: ⇒ 现在**先解析成 datetime 再比**，并容忍同一分钟内的截断差异（60 秒）。
_TIME_TOLERANCE_SEC = 60

#: 标签只认这个键 —— 与 `health.py` 同口径。
#: ⚠ 旧闸门用的是 `label-coverage.py` 的**宽口径**（回落到原始脏 `msg_type`），
#:   两者实测差 3,025 条 / 0.8pt（100.0 vs 99.2）。**本脚本以窄口径为准。**
LABEL_KEY = "msg_type_norm"


def _p(s: str) -> str:
    """把字符串转成当前控制台能打印的形式（**绝不抛异常**）。

    本机控制台是 GBK；`✅` / `⚠` 这类符号直接 `print` 会 `UnicodeEncodeError`
    把整个脚本带崩（实测）。打印非 ASCII 一律走这里 —— 与 `harvest.py::_safe()` 同法。
    """
    enc = sys.stdout.encoding or "utf-8"
    try:
        return s.encode(enc, "replace").decode(enc, "replace")
    except Exception:                                                   # noqa: BLE001
        return s.encode("ascii", "replace").decode("ascii")


def _norm(s) -> str:
    """归一化文本用于内容比较：去掉所有空白。"""
    return "".join(str(s or "").split())


# ---- 时间解析（判据 3 用）----------------------------------------------------

_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?")
_CN = re.compile(r"^(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})?:?(\d{1,2})?:?(\d{1,2})?")
_JAVA = re.compile(r"^\w{3} (\w{3}) (\d{1,2}) (\d{2}):(\d{2}):(\d{2}) \w+ (\d{4})$")
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def parse_time(s):
    """把各站各式的日期串解析成 `datetime`；**解析不了返回 None**。

    语料里实测至少三种格式（见 `_TIME_TOLERANCE_SEC` 的注释）：
    ISO（`2026-09-30 02:37:41`）/ 中文（`2026年09月7日`）/
    Java `Date.toString()`（`Thu Oct 19 10:57:25 CST 2023`）。
    """
    if not s:
        return None
    s = str(s).strip()
    m = _ISO.match(s)
    if m:
        y, mo, d, hh, mm, ss = m.groups()
        try:
            return datetime(int(y), int(mo), int(d),
                            int(hh or 0), int(mm or 0), int(ss or 0))
        except ValueError:
            return None
    m = _CN.match(s)
    if m:
        y, mo, d, hh, mm, ss = m.groups()
        try:
            return datetime(int(y), int(mo), int(d),
                            int(hh or 0), int(mm or 0), int(ss or 0))
        except ValueError:
            return None
    m = _JAVA.match(s)
    if m:
        mon, d, hh, mm, ss, y = m.groups()
        try:
            return datetime(int(y), _MONTHS.get(mon, 1), int(d),
                            int(hh), int(mm), int(ss))
        except ValueError:
            return None
    return None


def _iter_all():
    """流式读全部数据文件，yield `(path, rec)`。"""
    for p in sorted(glob.glob(str(DATA / "*.jsonl"))):
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip() or not line.lstrip().startswith("{"):
                        continue
                    try:
                        yield p, json.loads(line)
                    except Exception:                                   # noqa: BLE001
                        continue
        except OSError:
            continue


def collect() -> dict:
    """一次遍历算出四项判据（**一次运行检出全部**，不给闸门加多次全表扫描）。"""
    total = 0
    answer_empty = 0
    per_source_total: Counter = Counter()
    per_source_empty: Counter = Counter()

    # 内容重复：按 (question, answer) 归一化后分组，看有几组、冗余几条
    content_groups: dict = defaultdict(int)
    content_dups = 0
    dup_examples: list = []

    inverted = 0
    inv_sources: Counter = Counter()
    unparsed_time = 0
    unparsed_sources: Counter = Counter()

    labeled = 0
    label_sources: Counter = Counter()

    for _p, r in _iter_all():
        total += 1
        src = str(r.get("source") or "?")
        per_source_total[src] += 1

        # ---- 判据 1：答复为空 ----
        ans = str(r.get("answer") or "").strip()
        if not ans:
            answer_empty += 1
            per_source_empty[src] += 1

        # ---- 判据 2：内容重复 ----
        q, a = _norm(r.get("question")), _norm(ans)
        if q or a:
            key = (q, a)
            content_groups[key] += 1

        # ---- 判据 3：时间倒置（**必须解析后比，不能裸比字符串**）----
        pa, pb = parse_time(r.get("asked_at")), parse_time(r.get("answered_at"))
        if pa is not None and pb is not None:
            if (pa - pb).total_seconds() > _TIME_TOLERANCE_SEC:
                inverted += 1
                inv_sources[src] += 1
        elif r.get("asked_at") and r.get("answered_at"):
            # 两个字段都有值、但至少一个解析不了 ⇒ 无法判定，单独计数
            # （不许当成"没问题"悄悄放过，也不许当成"倒置"冤枉它）
            unparsed_time += 1
            unparsed_sources[src] += 1

        # ---- 判据 4：标签覆盖（只认窄口径） ----
        ex = r.get("extra")
        if isinstance(ex, dict):
            if ex.get(LABEL_KEY):
                labeled += 1
            label_sources[str(ex.get("msg_type_source") or "?")] += 1

    for key, n in content_groups.items():
        if n > 1:
            content_dups += n - 1
            if len(dup_examples) < 5:
                dup_examples.append((n, key[0][:60]))

    return {
        "total": total,
        "answer_empty": answer_empty,
        "empty_rate": (answer_empty / total) if total else 0.0,
        "per_source_total": per_source_total,
        "per_source_empty": per_source_empty,
        "content_dups": content_dups,
        "content_dup_groups": sum(1 for n in content_groups.values() if n > 1),
        "dup_examples": dup_examples,
        "inverted": inverted,
        "inv_sources": inv_sources,
        "unparsed_time": unparsed_time,
        "unparsed_sources": unparsed_sources,
        "labeled": labeled,
        "coverage": (labeled / total * 100) if total else 0.0,
        "label_sources": label_sources,
    }


def verdicts(s: dict) -> list:
    """把实测值判成 `(名称, 是否通过, 详情)` —— **闸门只读这个**。"""
    bad_sources = [
        (src, n, n / s["per_source_total"][src])
        for src, n in s["per_source_empty"].items()
        if s["per_source_total"][src] and n / s["per_source_total"][src] > MAX_SOURCE_EMPTY_RATE
    ]
    bad_sources.sort(key=lambda x: -x[2])
    return [
        ("答复非空率", s["empty_rate"] <= MAX_EMPTY_ANSWER_RATE,
         f"空 {s['answer_empty']} / {s['total']} = {s['empty_rate'] * 100:.3f}%"),
        ("无单源答复大面积为空", not bad_sources,
         f"超 {MAX_SOURCE_EMPTY_RATE:.0%} 的源 {len(bad_sources)} 个"),
        ("内容无重复", s["content_dups"] <= MAX_CONTENT_DUPS,
         f"冗余 {s['content_dups']} 条 / {s['content_dup_groups']} 组"),
        ("时间序正确", s["inverted"] <= MAX_TIME_INVERTED,
         f"倒置 {s['inverted']} 条（另有 {s['unparsed_time']} 条时间格式无法解析，未计入）"),
    ]


def ratchet(s: dict) -> list:
    """棘轮判据：与基线比，**缺陷率只许变好不许变坏**。返回 `(名称, 是否通过, 详情)`。

    ## 为什么比的是**率**而不是**绝对条数**（2026-10-10 实测教训）

    第一版比绝对条数，接进闸门后**立刻报红**：`content_dups` 8470 → 8475。
    查下来**不是回归** —— 是本目录**有另一个 Agent 的采集进程在持续加数据**
    （`igi-chunked.py`，实测仍在写 `gx-igi-*.jsonl`）。
    语料变大，缺陷的**绝对条数**自然变大。

    ⇒ 不变量应该是「**每十万条的缺陷数不上升**」，而不是「缺陷条数不上升」。
    绝对条数在输出里照常打印，只是不单独作为判据。

    容差 `_RATCHET_EPS`：允许极小的浮点/采样抖动，避免同一份数据两跑判出不同结论。
    """
    b = _load_baseline()
    if not b:
        return []
    out = []
    for skey, bkey, name in (("answer_empty", "answer_empty", "答复为空"),
                             ("content_dups", "content_dups", "内容重复"),
                             ("inverted", "time_inverted", "时间倒置")):
        cur_n, cur_t = int(s[skey]), int(s["total"])
        old_n, old_t = int(b.get(bkey, cur_n)), int(b.get("total", cur_t))
        cur_rate = (cur_n / cur_t * 100000) if cur_t else 0.0
        old_rate = (old_n / old_t * 100000) if old_t else 0.0
        ok = cur_rate <= old_rate + _RATCHET_EPS
        out.append((f"棘轮·{name}率不恶化", ok,
                    f"{cur_rate:.1f}/10万 ≤ 基线 {old_rate:.1f}/10万"
                    f"（{cur_n:,} 条 / 共 {cur_t:,}）"))
    return out


def _load_baseline() -> dict:
    try:
        return json.loads(BASELINE.read_text(encoding="utf-8"))
    except Exception:                                                   # noqa: BLE001
        return {}


def _save_baseline(s: dict) -> int:
    """记基线。**只在缺陷率确实变好（或首次）时允许写** —— 变坏时报错拒绝。

    ⚠ 比的是**率**不是绝对条数（理由见 `ratchet()` 的文档：并行采集会持续加数据）。
    """
    old = _load_baseline()
    cur = {"answer_empty": s["answer_empty"], "content_dups": s["content_dups"],
           "time_inverted": s["inverted"], "total": s["total"],
           "recorded_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S")}
    if old:
        worse = []
        # ⚠ 键名对照：`cur` 里叫 `time_inverted`，而 `s` 里叫 `inverted`
        #   （基线的键名更自解释，给读文件的人看）。这里显式写映射，不用猜。
        for skey, ckey, bkey in (("answer_empty", "answer_empty", "answer_empty"),
                                 ("content_dups", "content_dups", "content_dups"),
                                 ("inverted", "time_inverted", "time_inverted")):
            cur_rate = cur[ckey] / cur["total"] * 100000 if cur["total"] else 0.0
            old_rate = (old.get(bkey, 0) / old.get("total", 1) * 100000) if old.get("total") else 0.0
            if cur_rate > old_rate + _RATCHET_EPS:
                worse.append(f"{bkey}({old_rate:.1f}->{cur_rate:.1f}/10万)")
        if worse:
            print(f"拒绝记基线：这些缺陷率变坏了 {worse}（棘轮只许变好）")
            return 1
    BASELINE.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已记基线：{cur}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="数据质量闸门（spec 005 T102）")
    ap.add_argument("--quiet", action="store_true", help="纯 ASCII KEY=VALUE（给闸门用）")
    ap.add_argument("--detail", action="store_true", help="展开到源")
    ap.add_argument("--update-baseline", action="store_true",
                    help="重记棘轮基线（只在确实变好时允许）")
    ap.add_argument("--strict", action="store_true",
                    help="绝对阈值也进退出码（Phase 2 缺陷清零后启用）")
    args = ap.parse_args()

    try:
        s = collect()
    except Exception as e:                                              # noqa: BLE001
        print(f"ERROR={type(e).__name__}", file=sys.stdout)
        return 2

    if args.update_baseline:
        return _save_baseline(s)

    abs_checks = verdicts(s)
    rat_checks = ratchet(s)
    # 棘轮**永远**进退出码；绝对阈值只有 --strict 才进（过渡态，见模块文档）。
    checks = abs_checks + rat_checks
    failing = [c for c in (abs_checks if args.strict else []) + rat_checks if not c[1]]

    if args.quiet:
        from common import ascii_kv
        ascii_kv({
            "TOTAL": s["total"],
            "ANSWER_EMPTY": s["answer_empty"],
            "ANSWER_EMPTY_RATE": f"{s['empty_rate'] * 100:.3f}",
            "CONTENT_DUPS": s["content_dups"],
            "CONTENT_DUP_GROUPS": s["content_dup_groups"],
            "TIME_INVERTED": s["inverted"],
            "LABELED": s["labeled"],
            "LABEL_COVERAGE": f"{s['coverage']:.2f}",
            "ABS_CHECKS_FAILED": len([c for c in abs_checks if not c[1]]),
            "RATCHET_CHECKS_FAILED": len([c for c in rat_checks if not c[1]]),
            "MODE": "strict" if args.strict else "ratchet",
            "RATCHET": "on" if _load_baseline() else "none",
        })
        return 1 if failing else 0

    # 给人看
    # ⚠ 本机控制台是 GBK，`✅` 这类符号会直接 UnicodeEncodeError 把脚本带崩
    #   （我自己第一版就踩了）。人看的输出一律走 `_p()`。
    print(f"总记录 {s['total']:,}    模式={_p('绝对阈值+棘轮' if args.strict else '仅棘轮（过渡态）')}")
    print("\n=== 判据 ===")
    for name, ok, detail in checks:
        mark = "[OK]" if ok else "[!!]"
        # 过渡态下，绝对阈值失败**照常显示**但标注"不计退出码"—— 不许悄悄藏起来
        tag = ""
        if not args.strict and (name, ok, detail) in abs_checks and not ok:
            tag = "   （过渡态：不计退出码，Phase 2 还清）"
        print(f"  {_p(mark)} {name:26s} {detail}{tag}")

    if args.detail:
        print("\n=== 单源答复为空率 top15 ===")
        rows = [(src, s["per_source_empty"].get(src, 0), n)
                for src, n in s["per_source_total"].items()]
        rows = [r for r in rows if r[1] > 0]
        rows.sort(key=lambda r: -(r[1] / r[2] if r[2] else 0))
        for src, e, n in rows[:15]:
            print(f"  {src:30s} {e:6,d} / {n:6,d} = {e / n * 100:6.1f}%")

        print("\n=== 时间倒置 top10 源 ===")
        for src, n in s["inv_sources"].most_common(10):
            print(f"  {src:30s} {n:6,d}")

        print("\n=== 标签来源 ===")
        for k, n in s["label_sources"].most_common():
            print(f"  {k:20s} {n:8,d}")

    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
