# -*- coding: utf-8 -*-
"""侦察 / 留出集 / 留出集验证（吸收《夜间全自主运行指南》，2026-09-15）。

对应 `evolve/PLAN_V2.md` 的落地顺序 2–4：

- `holdout`：可复现的 **30 本留出集**（固定种子、分层、按**稳定键哈希**排序），
  写入后加只读锁（`locked:true`），**永不参与修复决策**——没有它，所有"修复
  是否有效"的判断都是自欺（在训练集上降了可能是过拟合）。
- `scout`：**分层侦察**（4 层 × 标准号区间）+ 前三类占比 + 灾难性文档 +
  层特异类，产出 `decide` 分支。
- `verify`：留出集判定——**命中下降 ≥30% 才算通过**，基线直接取**上一轮**的
  逐文档记录（轮次结果 append-only，天然有 before/after，无需额外记账）。

判据一律复用 `evolve.evaluate_doc`（单一所有者），本模块只做编排与统计。
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import artifact_index as AI   # noqa: E402
import evolve as E             # noqa: E402

EVOLVE = HERE / "evolve"
HOLDOUT = EVOLVE / "holdout.json"
SCOUT = EVOLVE / "scout.json"
SEED = "ks-evolve-2026"        # 固定种子：抽样必须可复现
HOLDOUT_N = 30
#: 四层：标准号区间（指南原文口径）。第四层额外含"2020 年后发布"的最新版式。
STRATA = [(0, 10000), (10000, 20000), (20000, 30000), (30000, 10 ** 9)]
CATASTROPHIC_CLASSES = 20      # 单本命中 >20 类 → 灾难性文档，排除统计


def std_num(std_no: str) -> int | None:
    """'GB/T 10002.1-2023' → 10002（首个数字段）。取不到返回 None。"""
    import re
    m = re.search(r"(\d{1,6})", std_no or "")
    return int(m.group(1)) if m else None


def stable_key(d: dict) -> str:
    """稳定键 = 源 PDF 文件名（归一）+ 固定种子 → 哈希。

    用文件名而非 doc_id：入库会重发 ULID（实测按 doc_id 直配只有 32.8% 对得上，
    按源文件名 96.5%）。加种子保证"同一语料、同一抽样"。
    """
    stem = AI.norm_stem(Path(d.get("file_path") or "").stem) or d.get("std_no", "")
    return hashlib.sha256(f"{SEED}|{stem}".encode()).hexdigest()


def stratum_of(std_no: str) -> int:
    n = std_num(std_no)
    if n is None:
        return -1
    for i, (lo, hi) in enumerate(STRATA):
        if lo <= n < hi:
            return i
    return -1


def _eval_doc(d: dict, idx: dict, scratch: Path, ambiguous: set) -> dict:
    return E.evaluate_doc(d, idx, scratch, ambiguous)


# ------------------------------------------------------------------ holdout
def cmd_holdout(args: list[str]) -> int:
    if HOLDOUT.exists() and "--force" not in args:
        h = json.loads(HOLDOUT.read_text(encoding="utf-8"))
        print(f"留出集已存在（{len(h['std_nos'])} 本，locked={h.get('locked')}）"
              f"——不覆盖。要重建请显式 --force")
        return 0
    docs = E.doc_list()
    buckets: dict[int, list[dict]] = defaultdict(list)
    for d in docs:
        buckets[stratum_of(d["std_no"])].append(d)
    picked: list[dict] = []
    per = max(1, HOLDOUT_N // len(STRATA))
    for i in range(len(STRATA)):
        s = sorted(buckets.get(i, []), key=stable_key)
        picked += s[:per]
    # 不足则按其余层哈希序补齐
    if len(picked) < HOLDOUT_N:
        rest = sorted([d for d in docs if d not in picked], key=stable_key)
        picked += rest[:HOLDOUT_N - len(picked)]
    picked = sorted(picked, key=lambda d: d["std_no"])
    obj = {"built_at": time.strftime("%Y-%m-%d %H:%M:%S"), "seed": SEED,
           "n": len(picked), "locked": True,
           "rule": "分层 4 层 × 各层按源 PDF 名哈希取前 7~8 本，固定种子",
           "strata": {str(k): len([d for d in picked if stratum_of(d["std_no"]) == k])
                      for k in sorted(set(stratum_of(d["std_no"]) for d in picked))},
           "std_nos": [d["std_no"] for d in picked]}
    E.atomic_write(HOLDOUT, obj)
    print(f"留出集已建：{obj['n']} 本 · 分层分布 {obj['strata']}")
    print(f"  → {HOLDOUT}（locked=true，只读，永不参与修复决策）")
    return 0


def _docs(corpus: bool) -> list[dict]:
    """文档清单来源：`corpus=True` → 新语料工作集（未入库），否则库内。

    2026-09-15（用户指令）：换全新语料防过拟合——原 260 部已被反复审计，
    其判据数字不再可信。新文档未入库，必须走 `corpus_docs`。
    """
    if not corpus:
        return E.doc_list()
    import corpus_docs  # noqa: PLC0415
    return corpus_docs.work_docs()


def load_holdout() -> set[str]:
    if not HOLDOUT.exists():
        print("⚠ 尚无留出集，先跑：scout.py holdout")
        return set()
    return set(json.loads(HOLDOUT.read_text(encoding="utf-8"))["std_nos"])


def holdout_paths() -> dict[str, str]:
    """留出集标准号 → 源 PDF 路径（新语料留出集带 `paths`，旧集没有）。"""
    if not HOLDOUT.exists():
        return {}
    h = json.loads(HOLDOUT.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for p in h.get("paths") or []:
        out[Path(p).stem] = p
    return out


# ------------------------------------------------------------------ scout
def cmd_scout(args: list[str]) -> int:
    hold = load_holdout()
    only_vlm = "--vlm-only" in args
    corpus = "--corpus" in args
    products_only = "--products-only" in args
    docs = [d for d in _docs(corpus) if d["std_no"] not in hold]
    idx = AI.load()
    scratch = EVOLVE / "scratch"
    ambiguous = AI.ambiguous_stems(docs)
    print(f"=== 侦察（分层，排除留出集 {len(hold)} 本）· 目标 {len(docs)} 部 "
          f"· 语料={'全新工作集' if corpus else '库内'} · VLM-only={only_vlm}"
          f"{' · 只算有产物' if products_only else ''} ===")
    cls_docs: dict[str, set] = defaultdict(set)
    cls_strata: dict[str, set] = defaultdict(set)
    per_doc_cls: dict[str, int] = {}
    catastrophic: list[dict] = []
    cov_body = cov_table = 0      # 判据可见正文 / 表格字符量（覆盖率口径）
    miss_chars = 0                # preproc 侧有、para 侧没有的表格字符（"读不到"量）
    miss_pre = 0                  # 对应的 preproc 侧总量（**比值分母**，只含可算比值的部）
    miss_docs = 0                 # 其中有可算比值的文档数（unknown 的不计入）
    pre_all = 0                   # **全部**文档的 preproc 侧表格字符（与 cov_table 可比）
    skipped = 0
    # **样本来源构成**（2026-09-15 实测教训）：语料面未铺满时，评估到的文档其实
    # 混了三种来源——① VLM 产物（真正目标）② 文本层重提（fitz，非 OCR）
    # ③ GAP（无产物）。不把它显式记下来，就会把"评估了 N 部"误读成"N 部 VLM
    # 产物"，进而高估语料面（实测：231 部里 VLM 产物 144、文本层 43、GAP 44）。
    kinds: Counter = Counter()
    for i, d in enumerate(docs, 1):
        rec = _eval_doc(d, idx, scratch, ambiguous)
        a = rec.get("artifact", {})
        pb = a.get("parse_backend", "unknown")
        kinds[(str(a.get("kind")), str(pb))] += 1
        if rec.get("verdict") == "GAP":
            skipped += 1
            continue
        if only_vlm and pb not in ("hybrid", "vlm", "vlm-engine", "textlayer"):
            skipped += 1
            continue
        # `--products-only`：只统计**真有产物**的文档，排除文本层重提——
        # 用户口径是 VLM 独占，文本层重提虽保真但属另一个通道，
        # 混入会稀释"VLM 产物上的缺陷分布"（新语料实测 43 部属此类）。
        if products_only and a.get("kind") == "blocks":
            skipped += 1
            continue
        n_cls = len(rec.get("classes") or {})
        per_doc_cls[d["std_no"]] = n_cls
        if n_cls > CATASTROPHIC_CLASSES:
            catastrophic.append({"std_no": d["std_no"], "classes": n_cls,
                                 "verdict": rec.get("verdict")})
            continue                       # 灾难性文档排除统计（单独记录）
        # **判据覆盖率**（2026-09-15 口径修正，用户指出）：判据原先只看
        # `content_text`，表格在 `content_markdown` 从未被检查——实测视野仅 70.1%，
        # 而表格占约 1/3 字符量。现表格也过判据，但仍要**把两个量分开报**，
        # 否则"零命中"会被误读成"全文没问题"。
        # **累加必须在"灾难性排除"之后**（实测踩过）：放在之前会把被排除文档的
        # 字符量也算进来，与逐部口径不一致（79 部实测 80.1% vs 84.5%）。
        cov_body += int(rec.get("len") or 0)
        cov_table += int(rec.get("table_len") or 0)
        # **"读不到的表"必须进报告**（2026-09-16 审计提出）：文档级仍有一小部分表格
        # 文本在 `preproc_blocks`、不在 `para_blocks`。这部分此前**既不进分母、
        # 也不触发任何类**，于是"读不到的表"与"本来没有表"在报告里同形，
        # 外部无法证伪。此处累加**只作口径量**（不是缺陷类，实测比值有噪声底噪）。
        pre_all += int(rec.get("table_preproc_chars") or 0)
        if not rec.get("table_missing_unknown"):
            miss_chars += int(rec.get("table_missing_chars") or 0)
            miss_pre += int(rec.get("table_preproc_chars") or 0)
            miss_docs += 1
        for c in (rec.get("classes") or {}):
            cls_docs[c].add(d["std_no"])
            cls_strata[c].add(stratum_of(d["std_no"]))
        if i % 50 == 0:
            print(f"  …{i}/{len(docs)}", flush=True)
    total_hits = sum(len(v) for v in cls_docs.values())
    ranked = sorted(cls_docs.items(), key=lambda kv: -len(kv[1]))
    top3 = ranked[:3]
    top3_share = (sum(len(v) for _, v in top3) / total_hits) if total_hits else 0.0
    # 层特异类：只在第 0 层（老标准）出现
    layer0_only = [c for c, s in cls_strata.items() if s == {0}]
    obj = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
           "docs_evaluated": len(per_doc_cls), "skipped_pipeline": skipped,
           "source_kinds": {f"{k[0]}|{k[1]}": v for k, v in sorted(kinds.items())},
           "holdout_n": len(hold), "total_hits": total_hits,
           "top3_share": round(top3_share, 3),
           "classes": {c: {"docs": len(v), "share": round(len(v) / max(total_hits, 1), 3),
                           "strata": sorted(cls_strata[c])} for c, v in ranked},
           "top3": [c for c, _ in top3],
           # **不再输出单一的 `coverage` 比值**（2026-09-15）：它会被读成
           # "还有 20% 没覆盖"，而事实是**表格现已进判据视野**、只是字符量占比大。
           # 改为输出三个可直接核对的量 + 表格占比。
           "text_len": cov_body, "table_len": cov_table,
           "table_share": (round(cov_table / (cov_body + cov_table), 4)
                           if (cov_body + cov_table) else 0.0),
           # **"读不到的表"**（2026-09-16 审计提出）：文档级 `preproc` 侧有、而
           # `para` 侧没有的表格字符量 + 可算比值的文档数。**不是缺陷类**——
           # 它的作用是让"读不到"与"本来没有"在报告里可区分（此前同形）。
           "table_missing_chars": miss_chars, "table_missing_docs": miss_docs,
           # ⚠ **两个 preproc 分量口径不同，别混用**（2026-09-16 自查修正）：
           #   · `table_preproc_chars` = miss_pre：**只含可算比值的部**，用作 `table_missing_chars`
           #     的比值分母（口径自洽：分子分母同一批文档）；
           #   · `table_preproc_chars_all` = pre_all：**全部已评估部**，与 `table_len`（para 侧、
           #     全部部）可比。此前只输出前者，导致 `table_len 852,689` 与 `preproc 851,265`
           #     看似只差 0.2%、却与 `missing 18,195` 自相矛盾——**是分母不同，不是数据错**。
           "table_preproc_chars": miss_pre,
           "table_preproc_chars_all": pre_all,
           "catastrophic": catastrophic, "layer0_only": layer0_only,
           "over_line": [c for c, v in ranked if len(v) >= E.FIX_LINE]}
    E.atomic_write(SCOUT, obj)
    # **陈旧死变量已删**（2026-09-16 审计指出）：`cov` 在改成三块量输出后已无人使用，
    # 留着只会让下个接手者以为"覆盖率"仍是单一比值，进而重算错。
    # **报告必须带批次分母**（2026-09-16 审计指出）：原先只印"评估 N 部"，
    # 而批次 6 清单是 543 部——同一句话进历史后会被读成"全批零缺陷"。
    # 现印 `评估 N/总数（未计入 M 部）`。`total` 由 `--corpus-list` 的清单长度给出。
    total_n = len(docs)
    print(f"\n命中总计 {total_hits} · 评估 {len(per_doc_cls)}/{total_n} 部"
          f"（未计入 {total_n - len(per_doc_cls)} 部）")
    # **报告口径要说清"覆盖了什么"而不是只给一个百分比**（2026-09-15 用户指出）：
    # 判据原先只看 `content_text`，表格在 `content_markdown` 里从未被检查——
    # 实测那份语料有 **19.9% 的字符量（表格）从未进过任何判据**。
    # 现在表格也过判据（`table-text::` 与 `table-` 两类），故视野是 100%；
    # 但仍把三块量分开列出来，避免"0 命中"被读成"全文没问题"。
    print(f"判据视野：正文 {cov_body:,} + 表格 {cov_table:,} 字符"
          f"（合计 {cov_body + cov_table:,}）· 表格占比 "
          f"{(cov_table / (cov_body + cov_table) if (cov_body + cov_table) else 0):.1%}")
    # **把"读不到的表"显式报出来（哪怕为 0）**（2026-09-16 审计提出）：
    # 上式分母只含"我读到的正文+表格"，文档级仍有一小部分表格文本在
    # `preproc_blocks`、不在 `para_blocks`。不报出来，它就是**不可证伪的空白**。
    _mp = miss_chars / miss_pre if miss_pre else 0.0
    print(f"  └ 其中**读不到**（preproc 有、para 无）：{miss_chars:,} 字符"
          f"（占 preproc 侧表格 {_mp:.2%}，{miss_docs} 部可算比值）"
          f"· 口径见 `table_probe.table_missing`（**不是缺陷类**，是口径量）")
    # **两栏必须同分母才可比**（2026-09-16 自查）：`table_len` 是 para 侧、覆盖**全部**
    # 已评估部；故这里用 `pre_all`（同样全部部）对照。用 `miss_pre`（只含可算比值的部）
    # 对照会得出"preproc 与 para 几乎相等、却又少读 1.8 万"的自相矛盾读数。
    if pre_all:
        print(f"  └ 两树对照（全部已评估部）：para 侧 {cov_table:,} · "
              f"preproc 侧 {pre_all:,} · 差 {pre_all - cov_table:,} "
              f"= {(pre_all - cov_table) / pre_all:.2%}（**文档级口径**）")
    vlm_n = sum(v for k, v in kinds.items() if k[1] in ("hybrid", "vlm", "vlm-engine"))
    tl_n = sum(v for k, v in kinds.items() if k[1] == "textlayer")
    gap_n = sum(v for k, v in kinds.items() if k[1] in ("unknown", "?"))
    print(f"样本来源：VLM 产物 {vlm_n} · 文本层重提 {tl_n} · 无产物(GAP) {gap_n}"
          f"  ← **VLM 产物才是本轮语料面**")
    for c, v in ranked[:10]:
        print(f"  {c:<28} {len(v):>4} 部  占比 {len(v)/max(total_hits,1):>5.1%}"
              f"  层 {sorted(cls_strata[c])}")
    print(f"\n前三类占比 {top3_share:.1%} → {decision(top3_share)}")
    if catastrophic:
        print(f"⚠ 灾难性文档 {len(catastrophic)} 部（命中>{CATASTROPHIC_CLASSES} 类，"
              f"已排除统计）：{[c['std_no'] for c in catastrophic][:5]}")
    if layer0_only:
        print(f"⚠ 仅老标准层出现的类 {len(layer0_only)} 个（不参与全局修复决策）："
              f"{layer0_only[:6]}")
    print(f"→ {SCOUT}")
    return 0


def decision(top3_share: float) -> str:
    """指南第三章阶段二的三条占比规则（原样吸收）。"""
    if top3_share >= 0.60:
        return "错误集中 → 修头部（阶段三）"
    if top3_share >= 0.30:
        return "中等集中 → 修头部 + 后台扩样本（阶段三 + 阶段五）"
    return "错误弥散 → 不修，先扩样本（阶段五）"


def cmd_decide(_args: list[str]) -> int:
    if not SCOUT.exists():
        print("无侦察结果，先跑：scout.py scout")
        return 2
    s = json.loads(SCOUT.read_text(encoding="utf-8"))
    print(f"侦察：{s['docs_evaluated']} 部 · 命中 {s['total_hits']} · "
          f"前三类占比 {s['top3_share']:.1%}")
    print(f"前三类：{s['top3']}")
    print(f"分支：{decision(s['top3_share'])}")
    print(f"达线类：{s['over_line'] or '（无）'}")
    return 0


# ------------------------------------------------------------------ verify
def holdout_hits(cls: str, round_no: int | None = None,
                 corpus: bool = False) -> tuple[int, list[str]]:
    """留出集上某类的命中：`round_no=None` → 用**当前代码**现算；
    给轮次号 → 读该轮已写的逐文档记录（append-only，即修复前的基线）。

    `corpus=True`：留出集文档未入库，须从 `holdout.json` 的 `paths` 现造记录
    （`corpus_docs`），再按当前代码评估。
    """
    hold = load_holdout()
    if not hold:
        return 0, []
    if round_no is not None:
        rd = E.round_dir(round_no) / "docs"
        hits = []
        for f in rd.glob("*.json"):
            r = json.loads(f.read_text(encoding="utf-8"))
            if r.get("std_no") in hold and cls in (r.get("classes") or {}):
                hits.append(r["std_no"])
        return len(hits), sorted(hits)
    idx = AI.load()
    scratch = EVOLVE / "scratch"
    if corpus:
        import corpus_docs  # noqa: PLC0415
        docs = corpus_docs.holdout_docs()
    else:
        docs = [d for d in E.doc_list() if d["std_no"] in hold]
    ambiguous = AI.ambiguous_stems(docs)
    hits = []
    for d in docs:
        rec = _eval_doc(d, idx, scratch, ambiguous)
        if cls in (rec.get("classes") or {}):
            hits.append(d["std_no"])
    return len(hits), sorted(hits)


def cmd_verify(args: list[str]) -> int:
    cls = args[args.index("--class") + 1] if "--class" in args else ""
    base_round = int(args[args.index("--baseline-round") + 1]) \
        if "--baseline-round" in args else None
    corpus = "--corpus" in args
    if not cls:
        print("用法：scout.py verify --class <类> [--baseline-round N] [--corpus]")
        return 2
    after, after_docs = holdout_hits(cls, corpus=corpus)
    if base_round is None:
        # 自动取"最近一个已写文档记录的轮次"作基线（即修复前的状态）
        rounds = sorted((E.ROUNDS.glob("round-*")
                         if hasattr(E, "ROUNDS") else []), key=lambda p: p.name)
        cand = [int(p.name.split("-")[1]) for p in rounds
                if (p / "docs").is_dir() and any((p / "docs").glob("*.json"))]
        base_round = max(cand) if cand else None
    if base_round is None:
        print(f"⚠ 无基线轮次，只能报当前值：{cls} 在留出集命中 {after} 部")
        return 0
    before, before_docs = holdout_hits(cls, base_round)
    drop = (before - after) / before if before else 0.0
    passed = (before > 0 and after <= 0.7 * before)
    print(f"=== 留出集验证 · 类 {cls} ===")
    print(f"基线（轮 #{base_round}）：{before} 部  {before_docs}")
    print(f"当前（本轮代码）：   {after} 部  {after_docs}")
    print(f"下降 {drop:.1%}（判据 ≥30%）→ {'✅ 通过' if passed else '❌ 未通过'}")
    if before == 0:
        print("⚠ 基线为 0：留出集上本无该类命中，本判据无从判定（需另立样本或改判据）")
    return 0 if passed else 1


def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else "decide"
    table = {"holdout": cmd_holdout, "scout": cmd_scout, "decide": cmd_decide,
             "verify": cmd_verify}
    if cmd not in table:
        print(__doc__)
        sys.exit(2)
    sys.exit(table[cmd](args))


if __name__ == "__main__":
    main()
