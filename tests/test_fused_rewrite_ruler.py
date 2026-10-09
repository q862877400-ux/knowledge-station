# -*- coding: utf-8 -*-
"""exp-14 融合侧改写尺子（`eval/recall-funnel/exp-14-fused-rewrite/run.py`）的单测。

**为什么必须测**（每条判据都对应一个"很容易踩回去"的坑）：

1. **通道映射必须按通道分别施加** —— `B1/C1` 是**指令前缀**，只该改**向量通道**的嵌入输入；
   若把它们也喂给 FTS（或反过来：`D1` 只改向量、不改 FTS），测出来的就不是"生产会怎么用"。
   判据见 `test_b1_c1_only_touch_vector_channel` / `test_d1_touches_vector_and_fts`。
2. **`A0` 必须一个字不动** —— 基线被污染，后面所有 Δ 都不成立。
   判据见 `test_a0_touches_nothing`。
3. **headline 必须真的剔掉 `gold_multi_def`/`gold_dup_text`** —— 否则分母从 120 变成 143，
   与 `exp-8`/`exp-13` 的口径就不是同一张考卷了。
   判据见 `test_headline_excludes_multi_def_and_dup`。
4. **命中阈值是闭区间（`r <= 20`）** —— 名次恰等于 20 算命中；写成 `<` 会让 `@20` 变成"前 19 名"。
   判据见 `test_fused_top20_is_inclusive_at_boundary`。
5. **`(翻进 b, 翻出 c)` 有方向、Δ 有符号** —— 对调会让"净改善"读成"净变差"。
   判据见 `test_flip_and_delta_direction_on_asymmetric_sample`。
6. **缺格不许静默补 0** —— 缺一格会让 @20 的分母错、Δ 错，而读数看不出来。
   判据见 `test_missing_cell_raises_instead_of_silently_filling`。
7. **契约锚（静态）**：本尺子靠 `hybrid_engine._conn` 注入只读连接、靠
   `embedder.embed_query` + `hybrid_engine._fts_query` 两个**调用点**做改写 ——
   这三处任一被改名/移除，尺子会**静默**退化成"用真库默认连接 + 完全不改写"。
   判据见 `test_production_hook_points_still_exist`。

⚠ 本文件**不测** `_run()`（要真库 + 10 分钟 KNN），只测判据所依赖的**纯函数**与**静态锚点**。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "eval" / "recall-funnel" / "exp-14-fused-rewrite" / "run.py"
STOPLOSS = REPO / "eval" / "recall-funnel" / "exp-14-fused-rewrite" / "stop-loss.json"
HYBRID = REPO / "src" / "core" / "retrieval" / "hybrid_engine.py"
BENCH = REPO / "eval" / "recall-funnel" / "benchmark-v2.jsonl"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


RULER = _load("ks_fused_rewrite_ruler", SCRIPT)
E13 = RULER._load_e13()

RAW = "车间墙角那个测细菌的小盒子是干什么用的"
D1Q = RAW + " 微生物 采样 培养"


# ── 判据 1/2/3：通道映射 ─────────────────────────────────────────────────────

def test_b1_c1_only_touch_vector_channel():
    """★ B1/C1 是**指令前缀**：只改向量通道的嵌入输入，FTS 必须保持原样。"""
    b_vec = RULER.arm_vec_query(RAW, "B1_bge_instruction", D1Q, E13)
    c_vec = RULER.arm_vec_query(RAW, "C1_domain_prefix", D1Q, E13)
    assert b_vec.startswith(E13.BGE_QUERY_INSTRUCTION) and b_vec.endswith(RAW)
    assert c_vec.startswith(E13.DOMAIN_PREFIX) and c_vec.endswith(RAW)
    assert b_vec != c_vec, "两条前缀必须不同，否则不是两个臂"
    for arm in ("B1_bge_instruction", "C1_domain_prefix"):
        assert RULER.arm_fts_query(RAW, arm, D1Q) == RAW, f"{arm} 不许污染 FTS"


def test_d1_touches_vector_and_fts():
    """★ D1 是**内容扩展**：向量与 FTS 都该用扩展串（精确/模态通道不走这两个钩子）。"""
    assert RULER.arm_vec_query(RAW, "D1_prf_expand", D1Q, E13) == D1Q
    assert RULER.arm_fts_query(RAW, "D1_prf_expand", D1Q) == D1Q


def test_a0_touches_nothing():
    """★ A0 = 生产口径：两个通道都用原样提问。"""
    assert RULER.arm_vec_query(RAW, "A0_raw", D1Q, E13) == RAW
    assert RULER.arm_fts_query(RAW, "A0_raw", D1Q) == RAW


# ── 判据 4：headline 口径 ────────────────────────────────────────────────────

def test_headline_excludes_multi_def_and_dup():
    """★ headline 必须真的剔掉 `gold_multi_def`/`gold_dup_text`（否则与 exp-8/exp-13 不同卷）。"""
    allrows = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
    head = RULER._headline(allrows)
    assert head, "headline 不该为空"
    assert len(head) < len(allrows), "剔完必须比全量少（否则这条判据没在做事）"
    for r in head:
        v = r.get("v2") or {}
        assert v.get("bucket") == "keep"
        assert not ({"gold_multi_def", "gold_dup_text"} & set(v.get("flags") or []))
    # 反向：确实有被剔掉的（保证过滤器不是恒真）
    dropped = [r for r in allrows if r not in head]
    assert dropped, "应当存在被剔掉的条目"


# ── 判据 5/6：聚合的边界、方向、缺格 ────────────────────────────────────────

def _mk_items(n: int) -> list[dict]:
    return [{"i": i, "query": f"q{i}", "v2": {"gold_cr_id": f"clrev_{i}", "bucket": "keep",
                                              "flags": [], "subset": {"label": "普通"}}}
            for i in range(n)]


def _mk_runs(items: list[dict], ranks: dict[str, list[int | None]]) -> dict:
    out = {}
    for n, it in enumerate(items):
        for arm in RULER.ARMS:
            out[(it["i"], arm)] = {"i": it["i"], "arm": arm, "fused_rank": ranks[arm][n],
                                   "fused_n": 40, "vec_query": "v", "fts_query": "f"}
    return out


def test_fused_top20_is_inclusive_at_boundary():
    """★ 名次恰等于 20 算命中；21 不算（闭区间）。"""
    items = _mk_items(2)
    ranks = {a: [None, None] for a in RULER.ARMS}
    ranks["A0_raw"] = [20, 21]
    agg, _ = RULER.aggregate_runs(items, {0: "d0", 1: "d1"}, _mk_runs(items, ranks), E13)
    assert agg["arms"]["A0_raw"]["fused_top20"] == 50.0, "rank=20 必须算命中、rank=21 不算"


def test_flip_side_treats_boundary_20_as_hit():
    """★ 翻转统计那一侧也必须把**名次恰等于 20** 当命中 ——
    写成 `< 20` 会让"基线在边界上命中、改写臂丢了它"这件事**读不出来**（翻出 1 → 0）。"""
    items = _mk_items(1)
    ranks = {a: [None] for a in RULER.ARMS}
    ranks["A0_raw"] = [20]                  # 边界上命中
    ranks["B1_bge_instruction"] = [None]    # 改写后丢了
    agg, _ = RULER.aggregate_runs(items, {0: "d0"}, _mk_runs(items, ranks), E13)
    v = agg["arms"]["B1_bge_instruction"]["vs_A0_top20"]
    assert (v["flip_in"], v["flip_out"]) == (0, 1), "边界命中必须被算进基线，否则翻出读不出来"


def test_flip_and_delta_direction_on_asymmetric_sample():
    """★ 非对称样本上 `(翻进 b, 翻出 c)` 与 Δ 的**方向**：净改善必须读成正 Δ。"""
    items = _mk_items(4)
    ranks = {a: [None, None, None, None] for a in RULER.ARMS}
    ranks["A0_raw"] = [1, None, None, 5]
    ranks["B1_bge_instruction"] = [1, 5, 7, None]     # 2 进 / 1 出
    agg, _ = RULER.aggregate_runs(items, {i: f"d{i}" for i in range(4)},
                                 _mk_runs(items, ranks), E13)
    v = agg["arms"]["B1_bge_instruction"]["vs_A0_top20"]
    assert (v["flip_in"], v["flip_out"]) == (2, 1), "方向对调会让 2 进 1 出 变成 1 进 2 出"
    assert v["delta_pt"] > 0, "净改善必须读成正 Δ"


def test_missing_cell_raises_instead_of_silently_filling():
    """★ 缺一格必须抛错，不许静默补 0（补 0 会让 @20 的分母错而读数看不出来）。"""
    items = _mk_items(1)
    runs = _mk_runs(items, {a: [1] for a in RULER.ARMS})
    del runs[(0, "D1_prf_expand")]
    try:
        RULER.aggregate_runs(items, {0: "d0"}, runs, E13)
    except KeyError:
        return
    raise AssertionError("缺格时必须 KeyError")


# ── 判据 7：静态契约锚 ───────────────────────────────────────────────────────

def test_production_hook_points_still_exist():
    """★ 三个钩子（只读连接注入 + 两个改写调用点）必须仍在生产代码里。"""
    src = HYBRID.read_text(encoding="utf-8")
    assert "def _conn(" in src, "hybrid_engine._conn 是只读连接注入点，改名会让尺子静默读真库"
    assert "_conn()" in src, "_conn() 必须被真实调用（否则注入无效）"
    assert "embedder.embed_query(" in src, "向量通道改写钩子（embedder.embed_query）不见了"
    assert "_fts_query(" in src, "FTS 通道改写钩子（_fts_query）不见了"


def test_stop_loss_preregistered_contract():
    """★ 预注册文件必须在，且主终点是 `fused@20`（不是向量路）。"""
    data = json.loads(STOPLOSS.read_text(encoding="utf-8"))
    assert data["registered_before_run"] is True
    assert data["main_endpoint"] == "fused@20"
    assert set(data["arm_query_mapping"]) == set(RULER.ARMS)
    for k in ("promote", "observe", "abandon"):
        assert k in data["thresholds"]
