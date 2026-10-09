# -*- coding: utf-8 -*-
"""exp-15 池深 × 融合方式尺子（`eval/recall-funnel/exp-15-pool-depth-fusion/run.py`）的单测。

**为什么必须测**（每条判据都对应一个"很容易踩回去"的坑）：

1. **`exact` / `modality` 在每一条臂里都必须不限量** —— 本批的**唯一变量**是 `fts`/`vec`
   的「池深」；若顺手把 exact/modality 也按 depth 截断，臂与臂之间就不止差一个变量了
   （这正是 exp-7 的口径复核抓过的"用错池口径"同类错误，那次静默测了一个不存在的东西）。
   判据见 `test_exact_and_modality_are_never_truncated`。
2. **`A0_prod` 必须逐字复刻生产的每路取数**（fts 20 / vec 20）—— 它是仪器对照臂，
   它一变，整批的 Δ 都失去参照。判据见 `test_a0_prod_replicates_production_caps`。
3. **`take_doc_diverse` 的语义**：每篇文档最多 N 条、总预算 B 条、**保序**、未知文档跳过。
   判据见 `test_take_doc_diverse_caps_per_doc_and_budget` / `test_take_doc_diverse_skips_unknown_docs`。
4. **`oracle_pool` 是"并集 + 截断"**：`fts[:d] ∪ vec[:d] ∪ exact ∪ modality`。
   写成"先并集再截断"或漏掉 exact/modality 都会**静默改**那条上界读数。
   判据见 `test_oracle_pool_is_union_then_truncate_per_channel`。
5. **命中阈值是闭区间（`r <= 20`）** —— 名次恰等于 20 算命中；写成 `<` 会让 `@20` 变成"前 19 名"。
   判据见 `test_hit_rate_is_inclusive_at_boundary`。
6. **`(翻进 b, 翻出 c)` 有方向、Δ 有符号**。判据见 `test_flip_and_delta_direction`。
7. **缺条不许静默补 0**（缺条会让 @20 的分母错而读数看不出来）。判据见 `test_missing_item_raises`。
8. **上报的副终点也要有牙**：`pool_median`（上中位定义）/ `fused_hit_n`（数非 None）/
   `by_subset_top20`（按 label 分组 + 闭区间）。判据见最后三条。
9. **静态契约锚**：本尺子的 `A0_prod` 复刻的是生产那两处硬编码上限
   （`ORDER BY rank LIMIT 20` 与 `AND k = 20`）—— 生产改了上限而这里没跟，仪器对照会红
   （那是**好事**），但更糟的是有人把上限改成读配置后**静默**漂移 ⇒ 钉住它们。
   另外 `exp7.fuse` / `exp7.order` 与臂名 `"A"` / `"Dp"` 也必须仍在；
   台账必须分别存 `rank20`/`rank100`/`rank1000`（**第 15 轮复核 P1-1** 的根因）。
   判据见 `test_production_caps_and_exp7_reuse_points_still_exist` / `test_ledger_stores_three_depths_separately`。
10. **★ 三个阈值不许退化成同一个**（**第 15 轮复核 P1-1**）：初版只存「top-20 名单里的名次」
   ⇒ `@100`/`@1000` **恒等于 `@20`**，而 `stop-loss.json` 明列 `fused@100` 为副终点 ⇒ **读数不真**。
   判据见 `test_top100_and_top1000_are_not_copies_of_top20`。
11. **★ 旧台账兼容 + 「没测的不许报 0%」**（P1-1 的修法）：本轮台账是**旧形状**
   （只有 `rank` 与 `hit@100`）⇒ `arm_rank()` 必须能读；`@1000` 无字段 ⇒ 必须上报 `null`。
   **不许**把没测的深度算成 `0.0%`（那是把"不知道"说成"零"）。
   判据见 `test_arm_rank_reads_both_ledger_shapes` / `test_legacy_ledger_reports_only_measured_depths`。
12. **★ `fused_hit_n` / `fused_median_rank` 定义在 @20 上**（与冻结版逐位一致）——
   修 P1-1 时**曾误把它们改到 `rank1000`**，那是**静默换定义**（A0_prod 会从 `10 / 3` 变成别的数）。
   判据见 `test_fused_hit_n_and_median_are_defined_on_top20`。

⚠ 本文件**不测** `_run()`（要真库 + 5 分钟 KNN），只测判据所依赖的**纯函数**与**静态锚点**。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "eval" / "recall-funnel" / "exp-15-pool-depth-fusion" / "run.py"
STOPLOSS = REPO / "eval" / "recall-funnel" / "exp-15-pool-depth-fusion" / "stop-loss.json"
EXP7 = REPO / "eval" / "recall-funnel" / "exp-7-rrm" / "run.py"
HYBRID = REPO / "src" / "core" / "retrieval" / "hybrid_engine.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


RULER = _load("ks_pool_depth_ruler", SCRIPT)
E7 = _load("ks_pool_depth_exp7", EXP7)


def _deep(n_fts=1000, n_vec=1000, exact=(), modality=()) -> dict:
    return {"exact": list(exact), "modality": list(modality),
            "fts": [f"f{k}" for k in range(n_fts)], "vec": [f"v{k}" for k in range(n_vec)]}


# ── 判据 1：唯一变量 ─────────────────────────────────────────────────────────

def test_exact_and_modality_are_never_truncated():
    """★ 每一条臂里 `exact`/`modality` 都必须**原样全量**（唯一变量只有 fts/vec 的池深）。"""
    d = _deep(exact=[f"e{k}" for k in range(50)], modality=[f"m{k}" for k in range(3000)])
    for arm in RULER.ARMS:
        rk = RULER.build_rankings(d, arm, {})
        assert rk["exact"] == d["exact"], f"{arm} 把 exact 截断了 —— 那就多了一个变量"
        assert rk["modality"] == d["modality"], f"{arm} 把 modality 截断了 —— 那就多了一个变量"


def test_a0_prod_replicates_production_caps():
    """★ A0_prod = 生产：fts/vec 各 20 条（它是仪器对照臂，不许漂）。"""
    d = _deep()
    rk = RULER.build_rankings(d, "A0_prod", {})
    assert len(rk["fts"]) == 20 and len(rk["vec"]) == 20
    assert rk["fts"] == d["fts"][:20] and rk["vec"] == d["vec"][:20], "必须是**前** 20 条、保序"


def test_pool_depth_arms_take_declared_depth():
    """★ 池深臂按各自声明取数（100 / 1000）。"""
    d = _deep()
    assert len(RULER.build_rankings(d, "P100_rrf60", {})["fts"]) == 100
    assert len(RULER.build_rankings(d, "P1000_rrf60", {})["vec"]) == 1000
    assert len(RULER.build_rankings(d, "P1000_rrm60", {})["vec"]) == 1000


# ── 判据 3：take_doc_diverse ────────────────────────────────────────────────

def test_take_doc_diverse_caps_per_doc_and_budget():
    """★ 每篇文档最多 `per_doc` 条、总数不超过 `budget`，且**保序**。"""
    lst = ["a1", "a2", "a3", "a4", "b1", "b2", "c1"]
    doc = {"a1": "A", "a2": "A", "a3": "A", "a4": "A", "b1": "B", "b2": "B", "c1": "C"}
    out = RULER.take_doc_diverse(lst, doc, 2, 10)
    assert out == ["a1", "a2", "b1", "b2", "c1"], "每篇最多 2 条 + 保序"
    out2 = RULER.take_doc_diverse(lst, doc, 3, 2)
    assert out2 == ["a1", "a2"], "预算优先：满 budget 就停"


def test_take_doc_diverse_skips_unknown_docs():
    """★ 查不到文档的 id 必须跳过（与生产 `fetch_full_clause` 取不到就跳过同向）。"""
    assert RULER.take_doc_diverse(["x1", "a1"], {"a1": "A"}, 3, 10) == ["a1"]


def test_doc3_arm_uses_doc_diverse_not_plain_truncation():
    """★ `P1000_doc3` 的 fts/vec 必须走**文档去重**（预算 20），不是简单取前 20。"""
    deep = {"exact": [], "modality": [],
            "fts": [f"d0_{k}" for k in range(30)] + [f"d1_{k}" for k in range(30)],
            "vec": [f"z{k}" for k in range(30)]}
    doc = {f"d0_{k}": "D0" for k in range(30)}
    doc.update({f"d1_{k}": "D1" for k in range(30)})
    doc.update({f"z{k}": "Z" for k in range(30)})
    rk = RULER.build_rankings(deep, "P1000_doc3", doc)
    assert rk["fts"][:3] == ["d0_0", "d0_1", "d0_2"]
    assert rk["fts"][3:6] == ["d1_0", "d1_1", "d1_2"], "同文档第 4 条必须被跳过"
    assert len(rk["fts"]) == 6 and len(rk["vec"]) == 3, "预算=20 但候选只有这些"


# ── 判据 4：oracle 池 ───────────────────────────────────────────────────────

def test_oracle_pool_is_union_then_truncate_per_channel():
    """★ oracle 池 = `exact ∪ modality ∪ fts[:d] ∪ vec[:d]`（**逐路截断**再并集）。"""
    d = _deep(n_fts=5, n_vec=5, exact=["e0"], modality=["m0"])
    assert RULER.oracle_pool(d, 2) == {"e0", "m0", "f0", "f1", "v0", "v1"}
    assert RULER.oracle_pool(d, 5) == {"e0", "m0", "f0", "f1", "f2", "f3", "f4",
                                       "v0", "v1", "v2", "v3", "v4"}


# ── 判据 5/6/7/8：聚合 ──────────────────────────────────────────────────────

def _mk_items(n: int) -> list[dict]:
    return [{"i": i, "query": f"q{i}", "v2": {"gold_cr_id": f"clrev_{i}", "bucket": "keep",
                                              "flags": [], "subset": {"label": "普通"}}}
            for i in range(n)]


def _mk_runs(items: list[dict], ranks: dict[str, list[int | None]],
             pools: dict[str, list[int]] | None = None,
             oracle: dict[str, bool] | None = None,
             identical: bool = True,
             ranks1000: dict[str, list[int | None]] | None = None) -> dict:
    """`ranks` = **rank20**（top-20 名单里的名次）；`ranks1000` 缺省时**与 rank20 相同**
    （只有"要区分 @20 与 @100/@1000"的用例才需要单独给）。

    ⚠ 三个深度必须分开存（第 15 轮复核 **P1-1**：初版只有一个 `rank`，导致 @100/@1000 是 @20 的复制）。
    """
    r1000 = ranks1000 or ranks
    out = {}
    for n, it in enumerate(items):
        arms = {}
        for arm in RULER.ARMS:
            r20 = ranks[arm][n]
            r1k = r1000[arm][n]
            # rank100 在测试里按"与 rank1000 同档、但不小于 rank20"取：只要能区分三个阈值即可
            r100 = r20 if r20 is not None else (r1k if (r1k is not None and r1k <= 100) else None)
            arms[arm] = {"pool": (pools or {}).get(arm, [40] * len(items))[n],
                         "rank20": r20, "rank100": r100, "rank1000": r1k, "ch_n": {}}
        out[it["i"]] = {
            "i": it["i"], "query": it["query"], "gold_cr_id": it["v2"]["gold_cr_id"],
            "modality_filter": None,
            "deep_n": {"fts": 1000, "vec": 1000},
            "gold_rank_in_deep": {"fts": None, "vec": None},
            "oracle": {f"@{d}": (oracle or {}).get(f"@{d}", False) for d in RULER.ORACLE_DEPTHS},
            "arms": arms,
            "check_identical": identical,
        }
    return out


def _ranks(items: list[dict], fill: int | None = None) -> dict[str, list[int | None]]:
    return {a: [fill] * len(items) for a in RULER.ARMS}


def _mk_legacy_runs(items: list[dict], ranks20: dict[str, list], hits100: dict[str, list]) -> dict:
    """造**旧形状**台账（第 15 轮初版）：`arms[臂]` 只有 `rank` + `hit@100`，**没有** `rank100/rank1000`。"""
    out = {}
    for n, it in enumerate(items):
        arms = {a: {"pool": 40, "rank": ranks20[a][n], "hit@100": hits100[a][n], "ch_n": {}}
                for a in RULER.ARMS}
        out[it["i"]] = {
            "i": it["i"], "query": it["query"], "gold_cr_id": it["v2"]["gold_cr_id"],
            "modality_filter": None,
            "deep_n": {"fts": 1000, "vec": 1000},
            "gold_rank_in_deep": {"fts": None, "vec": None},
            "oracle": {f"@{d}": False for d in RULER.ORACLE_DEPTHS},
            "arms": arms, "check_identical": True,
        }
    return out


def test_hit_rate_is_inclusive_at_boundary():
    """★ 名次恰等于 20 算命中；21 不算（闭区间）。"""
    items = _mk_items(2)
    ranks = _ranks(items)
    ranks["A0_prod"] = [20, 21]
    agg, _ = RULER.aggregate_runs(items, _mk_runs(items, ranks), E7)
    assert agg["arms"]["A0_prod"]["fused_top20"] == 50.0, "rank=20 必须算命中、rank=21 不算"


def test_flip_and_delta_direction():
    """★ 非对称样本上 `(翻进 b, 翻出 c)` 与 Δ 的方向：净改善必须读成正 Δ。"""
    items = _mk_items(4)
    ranks = _ranks(items)
    ranks["A0_prod"] = [1, None, None, 5]
    ranks["P1000_rrf60"] = [1, 5, 7, None]           # 2 进 / 1 出
    agg, _ = RULER.aggregate_runs(items, _mk_runs(items, ranks), E7)
    v = agg["arms"]["P1000_rrf60"]["vs_A0_top20"]
    assert (v["flip_in"], v["flip_out"]) == (2, 1), "方向对调会让 2 进 1 出 变成 1 进 2 出"
    assert v["delta_pt"] > 0, "净改善必须读成正 Δ"
    assert "vs_A0_top20" not in agg["arms"]["A0_prod"], "对照臂自己不许有 vs_A0"


def test_missing_item_raises():
    """★ 缺一条必须抛错，不许静默补 0（补 0 会让 @20 的分母错而读数看不出来）。"""
    items = _mk_items(2)
    runs = _mk_runs(items, _ranks(items))
    del runs[1]
    try:
        RULER.aggregate_runs(items, runs, E7)
    except KeyError:
        return
    raise AssertionError("缺条时必须 KeyError")


def test_oracle_aggregation_counts_booleans():
    """★ oracle 聚合必须数 `True` 的比例（写成数非空会让它恒 100%）。"""
    items = _mk_items(4)
    ranks = _ranks(items)
    agg, _ = RULER.aggregate_runs(
        items, _mk_runs(items, ranks, oracle={"@20": True, "@100": True, "@1000": False}), E7)
    assert agg["oracle"]["@20"] == 100.0 and agg["oracle"]["@1000"] == 0.0


def test_instrument_check_counts_identical():
    """★ 仪器对照读数必须数 `check_identical`（它不是装饰，是整批作废的开关）。"""
    items = _mk_items(3)
    runs = _mk_runs(items, _ranks(items))
    runs[1]["check_identical"] = False
    agg, _ = RULER.aggregate_runs(items, runs, E7)
    assert agg["instrument_check"]["compared"] == 3
    assert agg["instrument_check"]["identical_count"] == 2


def test_pool_median_definition_is_pinned():
    """★ `pool_median` 取**上中位** `sorted[n//2]`：排序后 [10,20,30,1000] ⇒ 30（≠ 下中位 20）。"""
    items = _mk_items(4)
    agg, _ = RULER.aggregate_runs(
        items, _mk_runs(items, _ranks(items), pools={"A0_prod": [10, 20, 30, 1000]}), E7)
    assert agg["arms"]["A0_prod"]["pool_median"] == 30, "必须是 sorted[n//2]"


def test_fused_hit_n_and_median_are_defined_on_top20():
    """★ `fused_hit_n` / `fused_median_rank` **定义在 @20 上**（与冻结版逐位一致）。

    第 15 轮修 P1-1 时曾把这两个改到 `rank1000` 上 ⇒ **静默换定义**
    （A0_prod 会从 `fused_hit_n=10 / median=3` 变成别的数）。这条判据钉住它：
    `rank1000` 口径更宽，若定义漂到 @1000 上，这两个读数会变大。
    """
    items = _mk_items(3)
    ranks = _ranks(items)
    ranks["A0_prod"] = [5, None, None]        # @20 只命中 1 条
    r1000 = _ranks(items)
    r1000["A0_prod"] = [5, 500, None]         # 池内召回 2 条（若按 @1000 定义就会数成 2）
    agg, _ = RULER.aggregate_runs(items, _mk_runs(items, ranks, ranks1000=r1000), E7)
    a = agg["arms"]["A0_prod"]
    assert a["fused_hit_n"] == 1, "hit_n 必须数 **@20 命中数**，不是池内召回数"
    assert a["fused_median_rank"] == 5, "median 也必须取 @20 命中条"
    assert a["fused_top20"] == round(100 * 1 / 3, 2)


def test_arm_rank_reads_both_ledger_shapes():
    """★ `arm_rank()` 必须同时吃**新台账**（`rank20/100/1000`）与**旧台账**（`rank` + `hit@100`）。"""
    new = {"rank20": 3, "rank100": 30, "rank1000": 300}
    assert (RULER.arm_rank(new, 20), RULER.arm_rank(new, 100), RULER.arm_rank(new, 1000)) == (3, 30, 300)
    old_hit = {"rank": 7, "hit@100": True}
    assert RULER.arm_rank(old_hit, 20) == 7, "旧台账 @20 读 rank"
    assert RULER.arm_rank(old_hit, 100) == 1, "旧台账 @100 只能还原「命中」（用 1 占位）"
    assert RULER.arm_rank(old_hit, 1000) is None, "旧台账没有 @1000 字段"
    old_miss = {"rank": None, "hit@100": False}
    assert RULER.arm_rank(old_miss, 20) is None and RULER.arm_rank(old_miss, 100) is None


def test_top100_and_top1000_are_not_copies_of_top20():
    """★ **第 15 轮复核 P1-1 的回归判据**：`@100`/`@1000` 必须用**对应深度的名次**算。

    初版三个阈值都套在「top-20 名单里的名次」上 ⇒ `rank ∈ {1..20, None}` ⇒
    `@100` 与 `@1000` **恒等于 `@20`**，而 `stop-loss.json` 明列 `fused@100` 为副终点 ⇒ **读数不真**。
    """
    items = _mk_items(3)
    ranks = _ranks(items)
    ranks["A0_prod"] = [None, None, None]          # 一条都不在 top-20
    r1000 = _ranks(items)
    r1000["A0_prod"] = [50, 900, None]             # 一条在 @100 内、一条只在 @1000 内、一条没召回
    agg, _ = RULER.aggregate_runs(items, _mk_runs(items, ranks, ranks1000=r1000), E7)
    a = agg["arms"]["A0_prod"]
    assert a["fused_top20"] == 0.0, "@20 必须还是 0（三条都不在前 20）"
    assert a["fused_top100"] == round(100 * 1 / 3, 2), "@100 不许等于 @20"
    assert a["fused_top1000"] == round(100 * 2 / 3, 2), "@1000 不许等于 @20/@100"


def test_legacy_ledger_reports_only_measured_depths():
    """★ **第 15 轮复核 P1-1 的修法判据**：旧台账（只有 `rank` + `hit@100`）下，
    `@100` 必须从 `hit@100` **还原**，`@1000` 必须上报 **`null`**（**不许报 0%**）。"""
    items = _mk_items(4)
    r20 = _ranks(items)
    r20["A0_prod"] = [None, None, None, None]
    h100 = _ranks(items, fill=False)
    h100["A0_prod"] = [True, False, True, False]
    agg, _ = RULER.aggregate_runs(items, _mk_legacy_runs(items, r20, h100), E7)
    a = agg["arms"]["A0_prod"]
    assert agg["ledger_depths"] == [20, 100], "旧台账没有 @1000 字段 ⇒ 只能上报 @20/@100"
    assert a["fused_top20"] == 0.0
    assert a["fused_top100"] == 50.0, "@100 必须从 hit@100 还原（不是 @20 的复制）"
    assert a["fused_top1000"] is None, "没测的深度必须 null —— 不许把「不知道」说成「零」"


def test_by_subset_top20_partitions_by_label():
    """★ `by_subset_top20` 按 label 分组 + 组内闭区间。"""
    items = _mk_items(3)
    items[0]["v2"]["subset"] = {"label": "A"}
    items[1]["v2"]["subset"] = {"label": "A"}
    items[2]["v2"]["subset"] = {"label": "B"}
    ranks = _ranks(items)
    ranks["A0_prod"] = [20, 21, 20]
    agg, _ = RULER.aggregate_runs(items, _mk_runs(items, ranks), E7)
    bs = agg["arms"]["A0_prod"]["by_subset_top20"]
    assert set(bs) == {"A", "B"}
    assert (bs["A"]["n"], bs["A"]["hit"]) == (2, 50.0)
    assert (bs["B"]["n"], bs["B"]["hit"]) == (1, 100.0)


# ── 判据 9：静态契约锚 ──────────────────────────────────────────────────────

def test_production_caps_and_exp7_reuse_points_still_exist():
    """★ 生产的两处硬编码上限（A0_prod 复刻的对象）+ exp-7 的复用点必须仍在。"""
    src = HYBRID.read_text(encoding="utf-8")
    assert "ORDER BY rank LIMIT 20" in src, "生产 FTS 通道上限变了 ⇒ A0_prod 的仪器对照会失去参照"
    assert "AND k = 20" in src, "生产向量通道上限变了 ⇒ A0_prod 的仪器对照会失去参照"
    e7 = EXP7.read_text(encoding="utf-8")
    assert "def fuse(" in e7 and "def order(" in e7, "exp-15 复用 exp-7 的 fuse/order，改名会让尺子断"
    assert '"A0_prod":       {"depth": 20,   "fusion": "A",  "k": 60}' in SCRIPT.read_text(encoding="utf-8"), \
        "A0_prod 必须仍是 depth=20 / 融合 A / k=60（生产现状）"


def test_ledger_stores_three_depths_separately():
    """★ 台账必须**分别存** `rank20`/`rank100`/`rank1000`（第 15 轮复核 P1-1 的根因锚点）。

    只存一个 `rank` ⇒ 三个阈值共用同一个名次 ⇒ `@100/@1000` 静默退化成 `@20` 的复制。
    """
    src = SCRIPT.read_text(encoding="utf-8")
    for key in ('"rank20"', '"rank100"', '"rank1000"'):
        assert key in src, f"台账缺 {key} ⇒ 阈值会退化成同一个名次的复制"
    assert "arm_r20" in src and "arm_r100" in src and "arm_r1000" in src, \
        "聚合必须按三个深度分开取数"


def test_stop_loss_preregistered_contract():
    """★ 预注册文件必须在，主终点 = `fused@20`，臂表与代码一致。"""
    data = json.loads(STOPLOSS.read_text(encoding="utf-8"))
    assert data["registered_before_run"] is True
    assert data["primary_endpoint"].startswith("fused@20")
    assert set(data["arms"]) == set(RULER.ARMS), "预注册的臂表必须与代码里的 ARMS 完全一致"
    for k in ("advance_ge_pt", "observe_ge_pt", "abandon_lt_pt"):
        assert k in data["thresholds"]
