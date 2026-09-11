"""R17 轻量版（Task 13.4）：负向反馈聚类 → SYSTEM_PROMPT Few-shot 注入。

不做模型微调（零外发下不可行）；把 feedback_log 高频错误模式转为
≤5 条提示示例注入系统提示词（受 R77 预算约束），降低同类错误复发率。
"""
from __future__ import annotations

import json
from collections import Counter

from src.core.storage.sqlite_db import get_db_connection

MAX_EXAMPLES = 5
MAX_CHARS = 100


def collect_feedback_patterns(limit: int = 50) -> list[dict]:
    """读取负向反馈（rating<0），按 feedback_type 聚类取高频内容片段。

    库表缺失/异常时静默返回空（Few-shot 是增强项，失败不得阻塞 build_messages）。
    """
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT feedback_type, feedback_content, clause_revision_ids FROM feedback_log"
            " WHERE rating < 0 ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    except Exception:
        return []
    by_type: dict[str, list[str]] = {}
    for r in rows:
        content = (r["feedback_content"] or "").strip()
        if len(content) < 6:
            continue
        by_type.setdefault(r["feedback_type"] or "unknown", []).append(content)

    patterns: list[dict] = []
    for ftype, contents in by_type.items():
        # 简单聚类：同类型反馈取最长代表样本（去重前 N 字）
        seen = set()
        for c in contents:
            key = c[:20]
            if key in seen:
                continue
            seen.add(key)
            patterns.append({"type": ftype, "example": c[:MAX_CHARS]})
            if len(patterns) >= MAX_EXAMPLES:
                break
    return patterns


def build_fewshot_block(patterns: list[dict]) -> str:
    if not patterns:
        return ""
    lines = ["用户历史纠错提示（务必避免重犯）："]
    for p in patterns:
        lines.append(f"- [{p['type']}] 用户反馈：{p['example']}")
    return "\n".join(lines)


def inject_fewshot(system_prompt: str) -> str:
    """在系统提示词尾部追加 Few-shot 块（无反馈时原样返回）。"""
    patterns = collect_feedback_patterns()
    block = build_fewshot_block(patterns)
    if not block:
        return system_prompt
    return f"{system_prompt}\n\n{block}"
