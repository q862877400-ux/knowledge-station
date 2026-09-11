"""纠错补丁防乱检测（patch guard，2026-08-23 新增）。

目的：防止用户"乱纠正"——误粘贴大段无关内容、贴代码/日志、清空重写等
污染知识库的行为。P1 准确性红线的入口守卫（宁可拒绝，不写脏补丁）。

三级响应：
  ok      —— 正常纠错，直接落库
  warning —— 可疑（长度/语言突变），落库但返回警告，前端二次确认
  reject  —— 明显异常（与原文几乎无关/大量不可打印字符），拒绝落库

判定维度（全部规则式，零 LLM 消耗）：
  1. 相似度：difflib.SequenceMatcher(原文, 新文).ratio()
     - OCR 纠错通常是局部改动 → ratio 高；整段替换/无关粘贴 → ratio 极低
  2. 长度突变：新文长度 / 原文长度
  3. 语言构成：中文字符占比突变（贴英文代码/日志的特征）
  4. 不可打印字符：乱码/二进制粘贴特征
"""
from __future__ import annotations

import difflib
import re

# 阈值（可按线上误报情况微调）
REJECT_SIMILARITY = 0.15       # 相似度低于此 → 拒绝（与原文几乎无关）
WARN_LENGTH_GROW = 3.0         # 新文长度超原文 3 倍 → 警告
WARN_LENGTH_SHRINK = 1 / 3     # 新文长度不足原文 1/3 → 警告
WARN_CJK_DROP = 0.30           # 中文占比下降超 30 个百分点 → 警告
REJECT_NONPRINT = 0.30         # 不可打印字符占比 > 30% → 拒绝（乱码）

_MIN_LEN_FOR_CHECK = 12        # 原文太短（<12字）跳过相似度检查（标题类小改）

_CTRL_RE = re.compile(r"[^\S\n]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _ratio_cjk(s: str) -> float:
    if not s:
        return 0.0
    return len(_CJK_RE.findall(s)) / max(len(s), 1)


def _nonprintable_ratio(s: str) -> float:
    if not s:
        return 0.0
    bad = sum(1 for ch in s if ord(ch) < 32 and ch not in "\n\r\t")
    return bad / max(len(s), 1)


#: 公开别名（2026-09-11）：R27 入库预览 / 数据体检复用同一「不可打印字符率」口径（反熵）。
nonprintable_ratio = _nonprintable_ratio


def check_patch(original: str, patched: str, field_name: str = "content_text") -> dict:
    """补丁合理性检测。

    返回 {verdict: ok|warning|reject, reasons: [...], similarity: float}
    仅对 content_text / content_markdown 做内容级检测；布尔/短字段直接放行。
    """
    if field_name not in ("content_text", "content_markdown"):
        return {"verdict": "ok", "reasons": [], "similarity": 1.0}

    orig = (original or "").strip()
    new = (patched or "").strip()

    # 1) 不可打印字符（乱码/二进制粘贴）→ 直接拒绝
    np_ratio = _nonprintable_ratio(new)
    if np_ratio > REJECT_NONPRINT:
        return {"verdict": "reject",
                "reasons": [f"内容含大量不可打印/乱码字符（{np_ratio:.0%}），疑似误粘贴二进制或编码错误的内容"],
                "similarity": 0.0}

    # 2) 相似度（原文足够长才有意义）
    sim = difflib.SequenceMatcher(None, orig[:4000], new[:4000]).ratio() \
        if len(orig) >= _MIN_LEN_FOR_CHECK else 1.0
    reasons: list[str] = []

    if sim < REJECT_SIMILARITY:
        return {"verdict": "reject",
                "reasons": [f"修正内容与原文几乎无关（相似度 {sim:.0%}）——"
                            f"疑似复制粘贴错了内容。纠错应基于原条款文字做局部修改"],
                "similarity": sim}

    # 3) 长度突变
    if orig:
        ratio = len(new) / max(len(orig), 1)
        if ratio > WARN_LENGTH_GROW:
            reasons.append(f"新文本长度是原文的 {ratio:.1f} 倍——疑似粘贴了多余内容")
        elif ratio < WARN_LENGTH_SHRINK:
            reasons.append(f"新文本长度只剩原文的 {ratio:.0%}——疑似误删了大段内容")

    # 4) 语言构成突变（中文占比骤降：贴英文代码/日志的特征）
    if len(orig) >= _MIN_LEN_FOR_CHECK:
        drop = _ratio_cjk(orig) - _ratio_cjk(new)
        if drop > WARN_CJK_DROP:
            reasons.append(f"中文字符占比下降 {drop:.0%}——疑似粘贴了英文代码/日志等无关内容")

    if reasons:
        return {"verdict": "warning", "reasons": reasons, "similarity": sim}
    return {"verdict": "ok", "reasons": [], "similarity": sim}
