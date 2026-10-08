"""政务问答语料 · 筛选/导出工具。

## 用法

```bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe

# ① 看能筛什么（维度清单 + 取值分布）
$P tools/gov-qa/query.py --stats

# ② 按省筛
$P tools/gov-qa/query.py --province 广东 --limit 20

# ③ 按类型筛（咨询/投诉/建议/表扬/求助…）
$P tools/gov-qa/query.py --type 投诉

# ④ 组合筛：广东省 + 住建类部门 + 关键词「物业」
$P tools/gov-qa/query.py --province 广东 --dept 住建 --kw 物业

# ⑤ 导出成文件（jsonl / csv）
$P tools/gov-qa/query.py --province 重庆 --out cq.jsonl
$P tools/gov-qa/query.py --type 建议 --out jianyi.csv --csv
```

## 可用筛选维度（依据实际字段覆盖率）

| 维度 | 参数 | 覆盖率 | 说明 |
|---|---|---|---|
| **地区（省）** | `--province` | **100%** | 由 `source` 前缀映射（复用 `recon/coverage-matrix.py` 的表），31 个省级单位全覆盖 |
| 来源站 | `--source` | 100% | 如 `gd-amr`、`cq-igi-180`；支持前缀匹配 |
| 答复部门 | `--dept` | 97.6% | 子串匹配；部门名常自带市/区/县，可当二级地区筛 |
| **问题类型** | `--type` | 20.3% | `extra.msg_type`：咨询/投诉/建议/表扬/求助/我要留言… |
| 时间窗 | `--since` `--until` | 99.0% | 按 `asked_at` 日期（`YYYY-MM-DD` 前缀比较） |
| 关键词 | `--kw` | — | 在 question+answer 里子串搜（可多次传，全部命中） |
| 有答复 | `--has-answer` | 100% | 只保留 answer 非空 |

⚠ **地区不是「字段」而是「映射」**：库里没有统一的 `province` 列，
   而是靠 `source` 前缀（`gd-`→广东、`cq-`→重庆…）归类。
   `extra.province/city/area`（约 14-17%）只在 IGI 系来源里有，可作为**更细一级**的补充。
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent          # tools/gov-qa
DATA = HERE / "data"

# —— 复用 coverage-matrix.py 的省份映射表，避免两份逻辑分叉 ——
# （该文件用连字符命名，不能常规 import，用 importlib 按路径加载）
_spec = importlib.util.spec_from_file_location("_covmatrix", HERE / "recon" / "coverage-matrix.py")
_cm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cm)


def province_of(rec: dict, src: str = "") -> str:
    """判省 —— **直接复用 `recon/coverage-matrix.py` 的 `province_of(rec)`**，别自己重写。

    它的口径比「source 前缀」更全，依次回退：
      ① `extra.pForumNames[0]`（人民网留言板自带 省→市→县 归属）
      ② `extra.fid_label[:3]`（fid 版块标签）
      ③ `source` 前缀表（`gd-`→广东、`cq-`→重庆…）
      ④ `NATIONAL`（mee/mem/people-liuyan → 国家级（部委））
    ⚠ 我一开始只写了 ③，导致 1,492 条（2.1%）被误判成「未归属」。
    """
    return _cm.province_of(rec)


def iter_records():
    """遍历全部 jsonl；跳过解析失败的行（采集进行中的半行）。"""
    for f in sorted(DATA.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except Exception:                                       # noqa: BLE001
                continue


def show_stats() -> int:
    n = 0
    prov = Counter()
    src = Counter()
    typ = Counter()
    dept_top = Counter()
    for r in iter_records():
        n += 1
        s = str(r.get("source") or "")
        src[s] += 1
        prov[province_of(r, s)] += 1
        t = (r.get("extra") or {}).get("msg_type")
        if t:
            typ[str(t)] += 1
        d = (r.get("dept") or "").strip()
        if d:
            dept_top[d] += 1
    print(f"总记录：{n}")
    print(f"来源站：{len(src)}    省级单位：{len([p for p in prov if not p.startswith('（')])}")
    print("\n=== 按省（可 --province 筛）===")
    for k, v in prov.most_common():
        print(f"  {k:16s} {v:7d}")
    print(f"\n=== 按类型（可 --type 筛；仅 {sum(typ.values())} 条有该字段）===")
    for k, v in typ.most_common(20):
        print(f"  {k:16s} {v:7d}")
    print("\n=== 答复部门 top20（可 --dept 子串筛）===")
    for k, v in dept_top.most_common(20):
        print(f"  {k[:38]:40s} {v:6d}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="政务问答语料筛选/导出")
    ap.add_argument("--stats", action="store_true", help="打印维度清单与取值分布")
    ap.add_argument("--province", default="", help="省名（子串匹配，如 广东）")
    ap.add_argument("--source", default="", help="来源 key（前缀匹配，如 gd-）")
    ap.add_argument("--type", default="", help="问题类型（子串匹配，如 投诉）")
    ap.add_argument("--dept", default="", help="答复部门（子串匹配，如 住建）")
    ap.add_argument("--kw", action="append", default=[], help="关键词（可多次；须全部命中）")
    ap.add_argument("--since", default="", help="起始日期 YYYY-MM-DD（按 asked_at）")
    ap.add_argument("--until", default="", help="截止日期 YYYY-MM-DD")
    ap.add_argument("--has-answer", action="store_true", help="只要 answer 非空")
    ap.add_argument("--limit", type=int, default=0, help="最多输出多少条（0=不限）")
    ap.add_argument("--out", default="", help="输出文件（默认只打印统计，不输出正文）")
    ap.add_argument("--csv", action="store_true", help="输出为 CSV（默认 jsonl）")
    ap.add_argument("--preview", type=int, default=3, help="打印前 N 条预览")
    args = ap.parse_args()

    if args.stats:
        return show_stats()

    hits: list[dict] = []
    scanned = 0
    prov_cnt: Counter = Counter()
    for r in iter_records():
        scanned += 1
        s = str(r.get("source") or "")
        if args.source and not s.startswith(args.source):
            continue
        p = province_of(r, s)
        if args.province and args.province not in p:
            continue
        if args.type and args.type not in str((r.get("extra") or {}).get("msg_type") or ""):
            continue
        if args.dept and args.dept not in str(r.get("dept") or ""):
            continue
        if args.has_answer and not (r.get("answer") or "").strip():
            continue
        d = str(r.get("asked_at") or "")
        if args.since and d[:10] < args.since:
            continue
        if args.until and d[:10] > args.until:
            continue
        if args.kw:
            blob = f"{r.get('question') or ''}\n{r.get('answer') or ''}"
            if not all(k in blob for k in args.kw):
                continue
        hits.append(r)
        prov_cnt[p] += 1

    print(f"扫描 {scanned} 条 → 命中 {len(hits)} 条")
    if prov_cnt:
        print("  命中分布：" + "、".join(f"{k} {v}" for k, v in prov_cnt.most_common(8)))

    if args.out and hits:
        out = Path(args.out)
        if args.csv:
            with out.open("w", encoding="utf-8-sig", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["province", "source", "id", "asked_at", "answered_at",
                            "dept", "type", "question", "answer", "url"])
                for r in hits:
                    w.writerow([province_of(r, str(r.get("source") or "")),
                                r.get("source"), r.get("id"), r.get("asked_at"),
                                r.get("answered_at"), r.get("dept"),
                                (r.get("extra") or {}).get("msg_type"),
                                r.get("question"), r.get("answer"), r.get("url")])
        else:
            with out.open("w", encoding="utf-8") as fh:
                for r in hits:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"已写出 {len(hits)} 条 → {out}")

    for r in hits[: args.preview]:
        s = str(r.get("source") or "")
        print(f"\n[{province_of(r, s)}] {s} | {r.get('dept') or '-'} | "
              f"{(r.get('extra') or {}).get('msg_type') or '-'} | {r.get('asked_at') or '-'}")
        print("  Q: " + (r.get("question") or "").replace("\n", " ")[:90])
        print("  A: " + (r.get("answer") or "").replace("\n", " ")[:90])
    return 0


if __name__ == "__main__":
    sys.exit(main())
