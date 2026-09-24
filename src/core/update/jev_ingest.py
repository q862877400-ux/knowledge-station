"""公告入库的"Jev 管清"那一层（2026-09-24，B2）。

## 为什么它只管"清"，不管"留"

同一天的两组真机实测（18 条有标准答案的样本，`tests/test_jev_guard.py` 同源方法）：

| | 规则（关键词） | Jev |
|---|---|---|
| 判"该清" | 2/10（**会漏**：弄虚作假典型案例通报、防汛责任人通报它都留了） | **9/9 零误清** |
| 判"该留" | **10/10 零漏**（令/办法/目录/征求意见稿一条不漏） | 5/9（3 条落 review 档） |

⇒ 两边**各管一头、零重叠**：**规则管"留"（漏的代价是"该入库的没进"），Jev 管"清"
（清的代价是"库里多了噪声"，可忍）**。这是 B2 的全部理由——不是"Jev 更好"，是**分工**。

## 三档 + 为什么中间档要留着

Jev 的 `confidence`（Choice 题才有，Noul 没有）是本层的门：
- **clear**（该清）：`confidence ≥ 0.90` 且判 admin ⇒ 确证是行政事务；
- **review**（灰区）：`0.70 ≤ confidence < 0.90` ⇒ 模型自己没把握，**交人看，不动**；
- **keep**：其余（含判 normative、判 change_signal、或 confidence <0.70 的 admin）⇒ 留着。

`confidence < 0.70` 却判 admin 的，按 Jev 官方分类范式
（`classification_using_confidence`）**报更粗的标签而不是丢掉**——这里粗标签就是"留着"。

## 判据与"是否已被规则留"的关系

本层**只处理规则已经判"待清"的那批**（`classify_scope != normative`），不碰规则放行的
——所以**规则永远是第一道**，Jev 只能在规则说"不收"的里面**再捞回**（review/keep），
绝不会因为 Jev 说了什么就**自动删库**。删除动作仍由调用方决定。
"""
from __future__ import annotations

import logging
from typing import Any

from src.core.llm import jev_client

logger = logging.getLogger(__name__)

CLEAR = "clear"          # 确证行政事务，可清
REVIEW = "review"        # 灰区：交人看
KEEP = "keep"            # 留着

#: 两道门（可改：见 config.Settings 的 jev_* 字段；此处是默认值常量）
CLEAR_CONFIDENCE = 0.90
REVIEW_CONFIDENCE = 0.70

_CHOICE = {
    "type": "choice",
    "instructions": "这份中国政府公文的标题，应该收进企业用的法规标准资料库吗？",
    "criteria": {
        "normative": (
            "收进去。文件本身规定了别人必须遵守的要求：法律、行政法规、部门规章、"
            "国家标准/行业标准，或发布、修订、修改、废止一份上述文件的公告、通知。"
        ),
        "change_signal": (
            "收进去，但只当参考。文件本身不是规范，只是某个法规或标准"
            "发布、修订、修改、废止了的线索。"
        ),
        "admin": (
            "不收。只是行政事务：表彰奖励、任免、开会、办竞赛、检查通报、"
            "征集选聘、招标采购、年度决算/预算/报表、普法宣传。没人需要照着它做事。"
        ),
    },
}
#: 变更信号单独一题（Noul）：上一题的 admin/normative 判据里不含"只是提到某法规变了"，
#: 而这一类**恰恰是业主第一目的**（实时获取发布/更新/修改/废止）——混在大题里会被稀释。
_CHANGE_NOUL = {
    "type": "noul",
    "instructions": "这份文件的标题里，是否提到了某个法规或标准被发布、修订、修改或废止？",
    "criteria": {
        "true": "标题里出现“废止”“新修订”“修改”“替代”“纳入目录”等说法，指出某个法规或标准变了。",
        "false": "标题只是在讲别的事情，没有说哪个法规或标准变了。",
    },
}


def judge_one(title: str) -> dict[str, Any] | None:
    """判**一条**公告标题该不该清。Jev 不可用 ⇒ `None`（调用方按规则原样处理）。

    一次调用问两题（官方 `parallel_questions`：打包比逐个问更便宜更快，答案不变）。
    """
    t = (title or "").strip()
    if not t:
        return None
    try:
        body = jev_client.system_one(t, {"kind": dict(_CHOICE), "change": dict(_CHANGE_NOUL)},
                                    service="jev-ingest")
    except jev_client.JevUnavailable as exc:
        logger.info("jev 入库判据不可用，按规则原样处理：%s", exc)
        return None
    answers = body.get("answers") or {}
    kind = (answers.get("kind") or {}).get("choice")
    conf = (answers.get("kind") or {}).get("confidence")
    change = (answers.get("change") or {}).get("noul")
    if kind not in ("normative", "change_signal", "admin"):
        return None
    if not isinstance(conf, (int, float)) or not isinstance(change, (int, float)):
        return None
    conf = float(conf)
    change = float(change)
    if change >= REVIEW_CONFIDENCE:
        verdict = KEEP                      # 变更线索永远留（它是"那条变了"的证据）
    elif kind != "admin":
        verdict = KEEP
    elif conf >= CLEAR_CONFIDENCE:
        verdict = CLEAR
    elif conf >= REVIEW_CONFIDENCE:
        verdict = REVIEW
    else:
        verdict = KEEP                      # 不够确信 ⇒ 按官方范式报粗标签（"留着"）
    return {"verdict": verdict, "choice": kind, "confidence": conf, "change": change}


def judge_many(titles: list[str]) -> dict[str, dict[str, Any] | None]:
    """批量判（逐条独立；某条失败不拖累其它条）。"""
    return {t: judge_one(t) for t in titles}
