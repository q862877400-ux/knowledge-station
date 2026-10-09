# -*- coding: utf-8 -*-
"""exp-13 查询侧改写尺子（`eval/recall-funnel/exp-13-query-rewrite/run.py`）的单测。

**为什么必须测**（不是形式主义）：这把尺子上每条判据都有一条**很容易踩回去**的坑：

1. **"没扩到词"必须与基线逐字相同** —— 若 `arm_queries` 在扩展词为空时也追加一个空格/空串，
   那么"这次没扩到词"会被当成"一次改写"，读数会凭空多出一臂。
   判据见 `test_d1_without_terms_equals_baseline`。
2. **`df` 是"文档频率"、不是"词频"** —— 同一个词在一篇里出现 5 次只算 1 次；
   否则高频重复的词会被误当成"在伪相关集里很普遍"而扩进来。
   判据见 `test_prf_df_is_document_frequency_not_term_frequency`。
3. **名次 = 严格更优的条数 + 1** —— 并列**不算**更优（与 exp-8 的 `d < d[gi]` 同口径）。
   判据见 `test_rank_of_counts_strictly_better_only`。
4. **未召回（None）算不中** —— 不能把它从分母里摘掉（那会把命中率抬高）。
   判据见 `test_hit_rate_counts_none_as_miss`。
5. **契约锚**：本尺子必须仍在用**生产**的向量入口与**生产**的模型名 ——
   若有人把生产模型换了，这把尺子的"生产口径"就不再成立。
   判据见 `test_still_uses_production_embedder_and_model`。

⚠ 本文件**不测** `main()`（要真库 + 全库矩阵，十几分钟），只测判据所依赖的**纯函数**。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "eval" / "recall-funnel" / "exp-13-query-rewrite" / "run.py"
STOPLOSS = REPO / "eval" / "recall-funnel" / "exp-13-query-rewrite" / "stop-loss.json"
EMBEDDER = REPO / "src" / "core" / "retrieval" / "embedder.py"


def _load():
    spec = importlib.util.spec_from_file_location("ks_query_rewrite_ruler", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


RULER = _load()


def _stub_tokenize(text: str) -> list[str]:
    """替身分词器：按空白切（测试要脱离 jieba）。"""
    return [t for t in text.split() if t]


def test_d1_without_terms_equals_baseline():
    """★ 没扩到词 ⇒ D1 与 A0 **逐字相同**（空扩展不是一次改写）。"""
    q = "车间墙角那个测细菌的小盒子是干什么用的"
    arms = RULER.arm_queries(q)
    assert arms["D1_prf_expand"] == arms["A0_raw"] == q
    # 有扩展词 ⇒ 真的追加了
    arms2 = RULER.arm_queries(q, ["微生物采样器", "采样"])
    assert arms2["D1_prf_expand"] == q + " " + "微生物采样器 采样"
    assert arms2["A0_raw"] == q, "A0 不许被扩展词污染"


def test_prefix_arms_are_exact():
    """B1/C1 的前缀必须与常量逐字一致（否则测的不是那一条前缀）。"""
    q = "测试提问"
    assert RULER.arm_queries(q)["B1_bge_instruction"] == RULER.BGE_QUERY_INSTRUCTION + q
    assert RULER.arm_queries(q)["C1_domain_prefix"] == RULER.DOMAIN_PREFIX + q
    assert RULER.BGE_QUERY_INSTRUCTION.startswith("为这个句子生成表示")
    assert RULER.DOMAIN_PREFIX != RULER.BGE_QUERY_INSTRUCTION


def test_prf_df_is_document_frequency_not_term_frequency():
    """★ df 是文档频率：同一篇里重复 5 次只算 1 次 ⇒ 达不到 min_df=3。"""
    q = "提问"
    one_doc_repeated = "甲甲 乙乙 乙乙 乙乙 乙乙 乙乙 丙丙"
    docs = [one_doc_repeated, one_doc_repeated, one_doc_repeated]  # 3 篇都含"乙乙"，但每篇只算 1 次
    terms = RULER.pick_prf_terms(q, docs, tokenize=_stub_tokenize, top_m=8, min_df=3)
    assert "乙乙" in terms, "3 篇各出现一次 ⇒ df=3 ⇒ 应当入选"
    # 只出现在 1 篇里（哪怕重复 5 次）⇒ df=1 < 3 ⇒ 不入选
    docs2 = ["乙乙 乙乙 乙乙 乙乙 乙乙 丙丙", "丙丙", "丙丙"]
    assert "乙乙" not in RULER.pick_prf_terms(q, docs2, tokenize=_stub_tokenize, top_m=8, min_df=3)


def test_prf_excludes_query_terms_and_non_cjk_and_short():
    """提问里已有的词、非中文串、单字都不许被扩进来。"""
    q = "仓库 编码"
    docs = ["仓库 编码 分类 分类 分类 A1 A1 A1 甲 甲 甲", "仓库 编码 分类 A1 甲", "分类 A1 甲"]
    terms = RULER.pick_prf_terms(q, docs, tokenize=_stub_tokenize, top_m=8, min_df=2)
    assert "分类" in terms
    assert "仓库" not in terms and "编码" not in terms, "提问里已有的词不许扩"
    assert "A1" not in terms, "纯英文/数字串不许扩"
    assert "甲" not in terms, "单字不许扩（长度 < 2）"


def test_prf_ordering_is_deterministic_by_df_then_length_then_lex():
    """排序：df 降序 → 词长降序 → 字典序（确定性，重跑逐字节相同）。"""
    q = "提问"
    docs = ["甲甲 乙乙乙 丙丙丙", "甲甲 乙乙乙 丙丙丙", "甲甲 丙丙丙"]  # 甲甲 df3 / 丙丙丙 df3 / 乙乙乙 df2
    terms = RULER.pick_prf_terms(q, docs, tokenize=_stub_tokenize, top_m=8, min_df=2)
    assert terms[0] == "丙丙丙", "df 相同时词长的排前"
    assert terms[1] == "甲甲"
    assert terms[2] == "乙乙乙"
    # 重跑确定性
    assert RULER.pick_prf_terms(q, docs, tokenize=_stub_tokenize, top_m=8, min_df=2) == terms


def test_prf_respects_top_m():
    q = "提问"
    docs = ["一甲 一乙 一丙 一丁", "一甲 一乙 一丙 一丁"]
    terms = RULER.pick_prf_terms(q, docs, tokenize=_stub_tokenize, top_m=2, min_df=2)
    assert len(terms) == 2


def test_rank_of_counts_strictly_better_only():
    """★ 名次 = 严格更优的条数 + 1；并列不算更优。"""
    import numpy as np
    s = np.array([0.9, 0.5, 0.5, 0.1], dtype=np.float32)
    assert RULER.rank_of(s, 0) == 1          # 最好
    assert RULER.rank_of(s, 1) == 2          # 只有 1 个严格更优
    assert RULER.rank_of(s, 2) == 2          # 并列的 0.5 不算更优
    assert RULER.rank_of(s, 3) == 4


def test_top_k_indices_is_descending_and_bounded():
    import numpy as np
    s = np.array([0.1, 0.9, 0.5, 0.7], dtype=np.float32)
    assert RULER.top_k_indices(s, 2) == [1, 3]
    assert len(RULER.top_k_indices(s, 99)) == 4


def test_hit_rate_counts_none_as_miss():
    """★ 未召回（None）算不中，不许从分母里摘掉。"""
    assert RULER.hit_rate([1, 5, None, None], 1000) == 50.0
    assert RULER.hit_rate([1, 5], 1000) == 100.0
    assert RULER.hit_rate([1001, 2000], 1000) == 0.0
    assert RULER.hit_rate([], 1000) == 0.0


def test_median_rank_ignores_none_and_is_deterministic():
    assert RULER.median_rank([1, 5, 2000, None]) == 5
    assert RULER.median_rank([None, None]) is None


def test_mcnemar_exact_matches_known_values():
    """★ McNemar 双侧精确二项：b=2,c=0 ⇒ 0.5；b=0,c=0 ⇒ 1.0；对称。"""
    assert RULER.mcnemar_exact(2, 0) == 0.5
    assert RULER.mcnemar_exact(0, 2) == 0.5
    assert RULER.mcnemar_exact(0, 0) == 1.0
    assert RULER.mcnemar_exact(5, 0) == RULER.mcnemar_exact(0, 5)
    assert RULER.mcnemar_exact(5, 0) < 0.1


def test_flip_counts():
    base = [True, False, False, True]
    arm = [True, True, False, False]
    assert RULER.flip_counts(base, arm) == (1, 1)
    assert RULER.flip_counts(base, base) == (0, 0)


def test_frozen_constants_are_pinned():
    """口径常量被钉住（改了要显式改测试，不许静默漂移）。"""
    assert RULER.PRF_TOP_DOCS == 20
    assert RULER.PRF_TOP_TERMS == 8
    assert RULER.PRF_MIN_DF == 3
    assert RULER.PRF_MIN_LEN == 2
    assert RULER.THRESHOLDS_PT == (20, 100, 1000)
    assert RULER.ARMS == ("A0_raw", "B1_bge_instruction", "C1_domain_prefix", "D1_prf_expand")


def test_stoploss_registered_with_expected_endpoint_and_thresholds():
    """契约锚：预注册止损线在盘上，且主终点/阈值与代码口径一致。"""
    cfg = json.loads(STOPLOSS.read_text(encoding="utf-8"))
    assert "Vector@1000" in cfg["primary_endpoint"]
    assert "8.18" in cfg["thresholds"]["推广"]
    assert cfg["arms"]["D1_prf_expand"].startswith("语料内 PRF")
    assert "A0" in cfg["instrument_check"]


def test_still_uses_production_embedder_and_model():
    """★ 契约锚：本尺子用的必须是**生产**的向量入口与**生产**的模型名。

    若有人换了生产模型（或把 `embed_query` 改成先加前缀），这把尺子的"生产口径"就不成立 ⇒ 要变红提醒。
    """
    src = EMBEDDER.read_text(encoding="utf-8")
    assert "BAAI/bge-small-zh-v1.5" in src
    assert "def embed_query" in src
    runner = SCRIPT.read_text(encoding="utf-8")
    assert "embedder.embed_query" in runner, "尺子必须走生产的 embed_query"
