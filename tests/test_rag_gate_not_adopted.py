"""**检索闸（Jev 对 top-5 逐段判相关/有答案/与前提矛盾）为什么暂不接进链路**（2026-09-24 量测结论）。

这份文件是**决策留痕 + 回归数据**，不是"待办"。业主 2026-09-24 的原话是
「做出来确实很好用而且性能要求低的话再打包进我们的项目」⇒ 先量，量不过就不做。

## 量法（`var/tmp/measure-rag-gate.py`，可复算）
真库 6797 篇 / 522021 条款；6 个真实提问各跑 `perform_hybrid_search(top_k=5)`，
再对每段问 Jev 四个 Noul（相关 / 有可用答案 / 与提问前提矛盾 / 有提示注入）。

## 量到的结果（28.2 秒 / 6 查询）

| 提问 | top-5 里 Jev「相关」分范围 | 现有链路命中的法规 | 判读 |
|---|---|---|---|
| 特种作业人员操作证复审周期 | 0.06 – 0.21 | 特种作业人员安全技术培训考核管理规定 5/5（对） | ⚠ **全被闸拦掉** |
| 危险化学品仓库的储存禁忌 | 0.07 – 0.28 | 危化品安全管理条例 4/5 + GB 45673-2025 1/5（都对） | ⚠ **全被闸拦掉** |
| 动火作业的分级标准 | 0.11 – 0.94 | GB 30871-2022（对） | 5.4/5.3.1 真条款被低分拦掉 |
| 生产经营单位安全生产主体责任 | 0.26 – 0.91 | 安全生产法（对） | 可用 |
| 应急预案演练的频次要求 | 0.19 – 0.98 | GB 42301-2022（对） | 可用 |
| 有限空间作业的通风要求 | 0.20 – 0.97 | 有限空间作业安全规定 / GB 30871（对） | 可用 |

**结论：低分 ≠ 不相关。** 前两组里 bge 的 top-5 **全部来自正确法规**（4/5 或 5/5；
危化品那组第 5 条是 GB 45673-2025，同属危化品标准、也不是跑题），
只是 Jev 在**被截断的 800 字**上给分低——「复审周期」这类答案散在多条里，单段本就不完整。
拿 0.7 阈值去拦，会**把真答案当噪声扔掉**（这正是业主最不能接受的方向：漏依据）。

性能也不达标"低"的口径：**4.7 秒/查询**（top-5 × 4 题，串行）。要压到可接受得并发，
又是一层复杂度，而收益尚未证明。

## 因此（决策）

- **不接进取证链路**（`hybrid_engine` / `ks_answer` 一行都不动）。
- **保留可复算的量测脚本**与本文件；将来若重议，先改**输入**（给整条法规的上下文，而不是
  截断的 800 字）并**重新量**，再决定阈值——不是拿这批低分直接调阈值。
- ⚠ 与本项目已有的重排器（`bge-reranker-base`，本机实测可用）**不冲突、不替换**：
  重排器做的是"同义相关度"，Jev 闸做的是"这段答不答这个问题"，两者不可互相证明。

## 回归数据（供下次对照）

`var/tmp/rag-gate-measure.json`：6 查询 × 5 段 × 4 维的逐条分数。
"""
from __future__ import annotations

import json
from pathlib import Path

MEASURE = Path(r"D:\AI\work space\zcode\var\tmp\rag-gate-measure.json")

#: 量测时的"应该被拦下"条数与"实际会被闸拦下"条数——**故意让它们不相等**：
#: 这就是"低分≠不相关"的证据本身（若哪天有人想接进链路，这三个数会不一致）。
EXPECTED_BOX = [
    ("特种作业人员操作证复审周期是多久", 5, 5),
    ("危险化学品仓库的储存禁忌有哪些", 5, 5),
    ("动火作业的分级标准", 2, 1),
    ("生产经营单位安全生产主体责任包括什么", 2, 1),
    ("应急预案演练的频次要求", 4, 1),
    ("有限空间作业的通风要求", 3, 0),
]


def test_measure_file_exists_and_has_all_queries():
    assert MEASURE.exists(), f"量测结果不在：{MEASURE}（重新跑 var/tmp/measure-rag-gate.py）"
    data = json.loads(MEASURE.read_text(encoding="utf-8"))
    got = [q["q"] for q in data["queries"]]
    for q, _would, _actual in EXPECTED_BOX:
        assert q in got, f"量测少了这一问：{q}"
    for q in data["queries"]:
        assert len(q["hits"]) == 5, (q["q"], len(q["hits"]))
        for h in q["hits"]:
            assert "relevant" in h, f"缺「相关」分：{h}"


def test_low_score_does_not_mean_irrelevant_documented():
    """**决策钉死**：前两组 top-5 的「相关」分全低，但它们**命中的法规是对的**。

    这条不是测现在的实现（现在没接闸），是**把量测结论钉住**：
    将来谁拿这批低分去接链路当"噪声过滤"，会先把真答案扔掉——正是业主最不能接受的方向。
    """
    if not MEASURE.exists():
        return
    data = json.loads(MEASURE.read_text(encoding="utf-8"))
    low_but_right = ("特种作业人员操作证复审周期是多久", "危险化学品仓库的储存禁忌有哪些")
    for q in data["queries"]:
        if q["q"] not in low_but_right:
            continue
        scores = [h["relevant"] for h in q["hits"]]
        assert scores and max(scores) < 0.30, (q["q"], scores)
        # 多数命中的是**该问题所属的那部法规/同族标准**（不是跑题）
        # ⚠ 真数据：危化品那组 5 条里 **4 条**是条例、第 5 条是 GB 45673-2025（同是危化品标准），
        #   所以判据是"≥4/5 命中相关法规"，不是"全部"——我第一版写"全部"时**自己判据红了**，
        #   查真数据发现叙述不准，按事实改（不为了判据绿而改叙述）。
        right_doc = ("特种作业人员安全技术培训考核管理规定"
                     if "特种作业" in q["q"] else "危化品安全管理条例")
        same_family = "GB 45673-2025"   # 同属危化品标准，非跑题
        n_right = sum(1 for h in q["hits"]
                      if right_doc in h["clause"] or same_family in h["clause"])
        assert n_right >= 4, f"{q['q']}：只有 {n_right}/5 命中相关法规 ⇒ '低分≠不相关' 的前提不成立"
