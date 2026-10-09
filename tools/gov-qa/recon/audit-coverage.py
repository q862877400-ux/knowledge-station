"""数据落盘核查 —— 对每个已登记适配器，核对它的数据文件里到底有多少条。

## 为什么需要它

本会话同一个失败模式出现了**三种形态**：
  1. 「适配器建好、抽验通过、已登记」但**从没启动采集**（worker-city 17 个市 / worker-national 3 个大源）
  2. 「采集任务已启动」但**被中断、没跑完**（四川第二批 10 个市只剩抽验的 3 条）
  3. 「文件存在」但里面是**抽验残留**，不是正式采集结果

⇒ 光看"任务已启动"、光看"文件存在"都不够。**唯一可信的判据是：数据文件里的行数。**

## 用法

```bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe

$P tools/gov-qa/recon/audit-coverage.py              # 全量核查（按省分组）
$P tools/gov-qa/recon/audit-coverage.py --empty      # 只看「零数据」的适配器
$P tools/gov-qa/recon/audit-coverage.py --thin 50    # 只看条数 < 50 的（疑似抽验残留）
$P tools/gov-qa/recon/audit-coverage.py --key js-    # 只看某前缀
```

**只读，不改任何文件。**
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent          # tools/gov-qa/recon
ROOT = HERE.parent                              # tools/gov-qa
sys.path.insert(0, str(ROOT))


def count_lines(path: str) -> int:
    """数有效行（跳过采集进行中的半行）。"""
    n = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip() and line.lstrip().startswith("{"):
                n += 1
    return n


def show_fields() -> int:
    """各字段非空率 —— 用来发现「整列全空」的静默数据缺陷。

    动机：四川内江/绵阳/阿坝三个源的 `answered_at` 全为 None，
    接口里 `replyContents[].replyTime` 一直存在、是适配器硬编码漏取。
    **光看条数发现不了这种缺陷** —— 数据看着有、字段是空的。
    """
    fields = ("question", "answer", "url", "dept", "channel", "asked_at", "answered_at")
    tot = 0
    nonempty = dict.fromkeys(fields, 0)
    extras: dict[str, int] = defaultdict(int)
    for p in glob.glob(str(ROOT / "data" / "*.jsonl")):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip() or not line.lstrip().startswith("{"):
                    continue
                try:
                    r = json.loads(line)
                except Exception:                                   # noqa: BLE001
                    continue
                tot += 1
                for k in fields:
                    v = r.get(k)
                    if v not in (None, "", [], {}):
                        nonempty[k] += 1
                ex = r.get("extra") or {}
                if isinstance(ex, dict):
                    for k, v in ex.items():
                        if v not in (None, "", [], {}):
                            extras[k] += 1
    if not tot:
        print("无数据")
        return 0
    print(f"总记录 {tot:,}")
    print("\n=== 主字段非空率（⚠ 某列接近 0% 就是静默缺陷）===")
    for k in fields:
        n = nonempty[k]
        flag = "   ← ⚠ 整列几乎全空！" if n / tot < 0.05 else ""
        print(f"  {k:14s} {n:8,d}  {n / tot * 100:6.1f}%{flag}")
    print("\n=== extra 子字段出现率 top20 ===")
    for k, n in sorted(extras.items(), key=lambda kv: -kv[1])[:20]:
        print(f"  {k:26s} {n:8,d}  {n / tot * 100:6.1f}%")
    return 0


def show_answers() -> int:
    """答复长度分布 —— 用来发现「答复被截断」这类静默缺陷。

    动机：四川巴中的答复正文含**嵌套 `<div>`**，非贪婪正则 `(.*?)</div>` 停在第一个内层标签
    ⇒ 548 条里 192 条答复只剩「尊敬的网友：您好！」（13 字）。**条数正常、字段非空，
    光看条数或字段覆盖率都发现不了。** 但**答复长度分布**一眼可见。

    ⚠ 判据：如果某来源出现大量 <30 字的答复，基本就是截断或占位符。
    """
    import statistics
    per_src: dict[str, list[int]] = defaultdict(list)
    for p in glob.glob(str(ROOT / "data" / "*.jsonl")):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip() or not line.lstrip().startswith("{"):
                    continue
                try:
                    r = json.loads(line)
                except Exception:                                   # noqa: BLE001
                    continue
                a = (r.get("answer") or "").strip()
                if a:
                    per_src[str(r.get("source") or "?")].append(len(a))

    tot = sum(len(v) for v in per_src.values())
    all_len = [n for v in per_src.values() for n in v]
    if not tot:
        print("无数据")
        return 0
    all_len.sort()

    def pct(xs, q):
        return xs[min(len(xs) - 1, int(len(xs) * q))]

    print(f"总记录 {tot:,}    答复长度：min={all_len[0]} "
          f"p10={pct(all_len, .1)} 中位={pct(all_len, .5)} p90={pct(all_len, .9)} max={all_len[-1]}")
    short_all = sum(1 for n in all_len if n < 30)
    print(f"⚠ 答复 <30 字的记录：{short_all:,}（{short_all / tot * 100:.2f}%）\n")

    rows = []
    for s, xs in per_src.items():
        xs_sorted = sorted(xs)
        short = sum(1 for n in xs if n < 30)
        rows.append((s, len(xs), short, short / len(xs), pct(xs_sorted, .5)))
    rows.sort(key=lambda r: -r[3])
    print("=== 按来源：短答复占比（只列占比 >5% 的）===")
    for s, n, short, ratio, med in rows:
        if ratio > 0.05:
            print(f"  {s:26s} 共 {n:6,d}  |  短(<30字) {short:5,d} ({ratio * 100:5.1f}%)  |  中位长度 {med}")
    if not [r for r in rows if r[3] > 0.05]:
        print("  （无）")

    # ★ 锋利的截断判据：**短答复是不是同来源里某条长答复的「前缀」**。
    #   巴中那 192 条截断后全是「尊敬的网友：您好！」—— 它正是同来源其它长答复的开头部分。
    #   而「感谢您对市长信箱工作的关注！」这类**固定套话**不是任何长答复的前缀 ⇒ 不会误报。
    print("\n=== ⚠ 疑似截断（短答复是同来源长答复的「前缀」）===")
    flagged = 0
    for p in glob.glob(str(ROOT / "data" / "*.jsonl")):
        by_src: dict[str, list[str]] = defaultdict(list)
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip() or not line.lstrip().startswith("{"):
                    continue
                try:
                    r = json.loads(line)
                except Exception:                                   # noqa: BLE001
                    continue
                a = (r.get("answer") or "").strip()
                if a:
                    by_src[str(r.get("source") or "?")].append(a)
        for s, ans in by_src.items():
            shorts = [a for a in ans if 0 < len(a) < 60]
            if len(shorts) < 5:
                continue
            longs = [a for a in ans if len(a) >= 80]
            if not longs:
                continue
            # 该来源里出现 ≥5 次的短答复，且是某条长答复的前缀
            hit = Counter()
            for t, n in Counter(shorts).items():
                if n < 5:
                    continue
                if any(lo.startswith(t) for lo in longs):
                    hit[t] = n
            if hit:
                flagged += 1
                t, n = hit.most_common(1)[0]
                print(f"  {s:26s} 「{t[:34]}」× {n}  ← 是长答复的前缀，疑似截断")
    if not flagged:
        print("  （无 —— 干净）")
    return 0


def show_dups() -> int:
    """重复 id 检测 —— 用来发现「并发写导致重复落盘」。

    动机：`harvest.py` 的去重是**开跑时一次性读文件**建 `done` 集合，
    之后只按该快照过滤。**两路进程并发采同一个站**时，双方读到同一初始状态
    ⇒ 各写一份、文件里出现重复 id。
    （2026-10-09 实测：浙江金华被两路并发写 ⇒ 6350 行 / 只有 3351 唯一 id，重复 2,999 条。）

    ⚠ 规则：**同一个站（同 source）只能有一路在采。**
    """
    rows = []
    for p in sorted(glob.glob(str(ROOT / "data" / "*.jsonl"))):
        per_src: dict[str, Counter] = defaultdict(Counter)
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip() or not line.lstrip().startswith("{"):
                    continue
                try:
                    r = json.loads(line)
                except Exception:                                   # noqa: BLE001
                    continue
                per_src[str(r.get("source") or "?")][str(r.get("id"))] += 1
        for s, c in per_src.items():
            total = sum(c.values())
            uniq = len(c)
            if total != uniq:
                rows.append((s, total, uniq, total - uniq, os.path.basename(p)))
    if not rows:
        print("重复 id 检测：**全部干净** ✓")
        return 0
    rows.sort(key=lambda r: -r[3])
    print(f"⚠ 发现 {len(rows)} 个来源存在重复 id：\n")
    print(f"  {'source':26s} {'总行数':>9s} {'唯一':>9s} {'重复':>8s}  文件")
    for s, total, uniq, dup, fn in rows:
        print(f"  {s:26s} {total:9,d} {uniq:9,d} {dup:8,d}  {fn[:40]}")
    print(f"\n  重复合计 {sum(r[3] for r in rows):,} 行")
    return 0


def show_targets() -> int:
    """对比「枚举/接口自报总量」vs「实际落盘量」—— 发现「采了但远未达目标」。

    动机：2026-10-09 实测山西/广西 IGI **正常结束**（日志写「完成」），
    但只采了 1,283 / 1,731 条，而枚举潜力是 84,381 / 34,938（不到 2%）。
    **`--empty` 查不出这种问题**（它不是零数据），也没有任何告警。
    ⇒ 必须把「潜力」显式登记下来做对比（`recon/targets.json`）。
    """
    tp = HERE / "targets.json"
    if not tp.exists():
        print(f"缺少 {tp}（登记各源的自报总量）")
        return 1
    targets = (json.loads(tp.read_text(encoding="utf-8")) or {}).get("targets") or {}

    # 现算各 key 的实际落盘量
    actual: dict[str, int] = defaultdict(int)
    for p in glob.glob(str(ROOT / "data" / "*.jsonl")):
        base = os.path.basename(p)
        n = count_lines(p)
        for k in targets:
            if base.startswith(f"{k}-"):
                actual[k] += n
                break

    rows = []
    for k, meta in targets.items():
        t = int(meta.get("total") or 0)
        cap = int(meta.get("cap") or 0)
        goal = min(t, cap) if cap else t        # 有效目标 = min(自报总量, 我方上限)
        a = actual.get(k, 0)
        rows.append((k, t, cap, goal, a, a / goal if goal else 0, meta.get("note", "")))
    rows.sort(key=lambda r: r[5])

    print(f"{'source':16s} {'自报总量':>10s} {'上限':>8s} {'有效目标':>10s} "
          f"{'已落盘':>9s} {'完成度':>7s}")
    warn = 0
    for k, t, cap, goal, a, ratio, note in rows:
        flag = ""
        if ratio < 0.5 and goal >= 1000:
            flag = "  ⚠ 远未达目标"
            warn += 1
        cap_s = f"{cap:,}" if cap else "-"
        print(f"{k:16s} {t:10,d} {cap_s:>8s} {goal:10,d} {a:9,d} {ratio * 100:6.1f}%{flag}")
        if flag:
            print(f"{'':16s} {'':10s} {'':8s} {'':10s} {'':9s}         {note}")
    print(f"\n⚠ 完成度 <50%（且有效目标 ≥1000 条）的源：{warn} 个")
    print("（cap = 我方主动设定的上限：单源 2 万、每市 3000/8000）")
    return 0


def show_gate() -> int:
    """给 `check.sh` 用的**纯 ASCII 机器可读输出**。

    为什么需要它：`check.sh` 原来用 `sed` 匹配**中文**（「数据总条数」「重复合计」）
    来解析判据。**sed 的中文匹配依赖 locale/编码**，在 hook 的执行环境里可能失配
    ⇒ 解析不到 ⇒ 误判「执行失败」⇒ 闸门永远红（2026-10-10 排查了很久）。

    ⇒ 改为输出纯 ASCII 的 `KEY=VALUE`，`check.sh` 用 `grep`+`cut` 解析，**不碰中文**。
    退出码：0 = 可解析（不代表通过，通过与否由 check.sh 判）。
    """
    # 数据总数
    tot = 0
    for p in glob.glob(str(ROOT / "data" / "*.jsonl")):
        tot += count_lines(p)

    # 零数据适配器数
    n_empty = 0
    n_keys = 0
    try:
        import adapters
        keys = list(adapters.ADAPTERS)
        n_keys = len(keys)
        all_files = [os.path.basename(p) for p in glob.glob(str(ROOT / "data" / "*.jsonl"))]
        key_prefixes = []
        for k in keys:
            try:
                key_prefixes.append((f"{adapters.load(k).SITE['key']}-", k))
            except Exception:                                           # noqa: BLE001
                key_prefixes.append((f"{k}-", k))
        key_prefixes.sort(key=lambda x: -len(x[0]))
        owned = {}
        for base in all_files:
            for pre, k in key_prefixes:
                if base.startswith(pre):
                    owned[base] = k
                    break
        have = set(owned.values())
        n_empty = sum(1 for k in keys if k not in have)
    except Exception as e:                                              # noqa: BLE001
        print(f"ADAPTERS_ERR={type(e).__name__}")

    # 重复 id 行数
    dups = 0
    for p in glob.glob(str(ROOT / "data" / "*.jsonl")):
        per_src: dict[str, Counter] = defaultdict(Counter)
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip() or not line.lstrip().startswith("{"):
                    continue
                try:
                    r = json.loads(line)
                except Exception:                                       # noqa: BLE001
                    continue
                per_src[str(r.get("source") or "?")][str(r.get("id"))] += 1
        for c in per_src.values():
            dups += sum(c.values()) - len(c)

    print(f"TOTAL={tot}")
    print(f"ADAPTERS={n_keys}")
    print(f"EMPTY={n_empty}")
    print(f"DUPS={dups}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="数据落盘核查")
    ap.add_argument("--empty", action="store_true", help="只看零数据的适配器")
    ap.add_argument("--thin", type=int, default=0, help="只看条数 < N 的适配器")
    ap.add_argument("--fields", action="store_true",
                    help="输出各字段非空率（发现「整列全空」的静默缺陷）")
    ap.add_argument("--answers", action="store_true",
                    help="输出答复长度分布（发现「答复被截断」的静默缺陷）")
    ap.add_argument("--dups", action="store_true",
                    help="检测重复 id（发现「并发写导致重复落盘」）")
    ap.add_argument("--targets", action="store_true",
                    help="对比「自报总量 vs 实际落盘」（发现「采了但远未达目标」）")
    ap.add_argument("--gate", action="store_true",
                    help="★ 纯 ASCII 机器可读输出（给 check.sh 用，避免 sed 中文匹配失配）")
    ap.add_argument("--key", default="", help="只看某前缀的 key")
    args = ap.parse_args()

    if args.gate:
        return show_gate()
    if args.fields:
        return show_fields()
    if args.answers:
        return show_answers()
    if args.dups:
        return show_dups()
    if args.targets:
        return show_targets()


    os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
    import adapters

    # 预先扫一遍 data/ 的条数（按文件名前缀聚合）
    counts: dict[str, int] = defaultdict(int)
    all_files: list[str] = []
    for p in glob.glob(str(ROOT / "data" / "*.jsonl")):
        base = os.path.basename(p)
        counts[base] = count_lines(p)
        all_files.append(base)

    keys = sorted(k for k in adapters.ADAPTERS if k.startswith(args.key))

    # ⚠ 每个文件只能归属**最长匹配**的那个 key，否则会重复计数：
    #   若同时登记了 `gx-igi` 和 `gx-igi-293`，文件 `gx-igi-293-….jsonl` 会同时匹配两个前缀，
    #   按「逐 key 累加」的写法会被算两次 ⇒ 总量虚高（2026-10-09 实测虚高约 8,800 条）。
    key_prefixes = []
    for k in keys:
        try:
            key_prefixes.append((f"{adapters.load(k).SITE['key']}-", k))
        except Exception:                                               # noqa: BLE001
            key_prefixes.append((f"{k}-", k))
    # 长前缀优先
    key_prefixes.sort(key=lambda x: -len(x[0]))

    owned: dict[str, str] = {}          # 文件名 -> 归属 key
    for base in all_files:
        for pre, k in key_prefixes:
            if base.startswith(pre):
                owned[base] = k
                break

    rows = []
    for k in keys:
        mod = adapters.load(k)
        site = mod.SITE
        prefix = f"{site['key']}-"
        total = 0
        nf = 0
        for base in all_files:
            if owned.get(base) == k and base.startswith(prefix):
                total += counts[base]
                nf += 1
        rows.append((k, site.get("name", ""), site.get("level", ""), total, nf))

    empty = [r for r in rows if r[3] == 0]
    thin = [r for r in rows if 0 < r[3] < (args.thin or 10**9)]

    print(f"已登记适配器 {len(rows)} 个；其中**零数据 {len(empty)} 个**、"
          f"薄（<{args.thin}）{len(thin) if args.thin else '-'} 个")
    print(f"数据总条数（按适配器聚合）：{sum(r[3] for r in rows):,}")
    print()

    if args.empty:
        print("=== 零数据（建好没采 / 采了没落盘）===")
        for k, name, lvl, tot, nf in empty:
            print(f"  {k:22s} {lvl:9s} {name}")
        return 0

    if args.thin:
        print(f"=== 薄数据（0 < 条数 < {args.thin}，疑似抽验残留）===")
        for k, name, lvl, tot, nf in thin:
            print(f"  {tot:6d}  {k:22s} {name}")
        return 0

    # 全量：按 level 分组
    for lvl in ("national", "province", "city", ""):
        grp = [r for r in rows if r[2] == lvl]
        if not grp:
            continue
        label = {"national": "国家级", "province": "省级", "city": "地市级", "": "其它"}[lvl]
        print(f"=== {label}（{len(grp)} 个，合计 {sum(r[3] for r in grp):,} 条）===")
        for k, name, _l, tot, nf in sorted(grp, key=lambda r: -r[3]):
            flag = "  ← 零数据" if tot == 0 else ("  ← 疑似抽验残留" if tot < 30 else "")
            print(f"  {tot:7d}  {k:24s} {name[:34]:36s}{flag}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
