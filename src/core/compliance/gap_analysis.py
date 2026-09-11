"""R-L11~13 合规差距分析（Phase 7）。

流程：内部制度文本导入（internal_policy）→ 法定义务清单构建（legal_obligation，来自库内
应当/必须型条款）→ 逐义务 vs 制度章节关键词比对 → 三色判定（red 缺失 / yellow 不完善 /
green 已覆盖）→ gap_analysis 落库（挂 review_task）→ 整改建议 + 汇总报告。

判定规则（可解释性优先，非 LLM）：
- 义务关键词命中率 >= 0.5 或 绝对命中 >= 3 → green
- 命中 >= 1 → yellow（部分覆盖）
- 命中 0 → red（完全缺失）
"""
from __future__ import annotations

import json
import re
from typing import Any

from ulid import ULID

from src.core.storage.sqlite_db import get_db_connection, write_transaction

_SECTION_SPLIT = re.compile(r"(?=第[一二三四五六七八九十百千]+[章节编])")
_SECTION_HEAD = re.compile(r"^第[一二三四五六七八九十百千]+[章节编]\s*")
_STOP = {"应当", "必须", "不得", "应", "可以", "有权", "进行", "通过", "以及", "或者",
         "相关", "有关", "规定", "要求", "人员", "情况", "下列", "上述", "本文件",
         "本标准", "本法", "本规范", "企业", "单位"}

# 三色判定阈值（GREEN：命中关键词语义占比或绝对命中数任一达标）
GREEN_RATIO = 0.5
GREEN_ABS_HIT = 3


def import_internal_policy(policy_name: str, policy_text: str) -> dict:
    """内部制度文本导入（章节结构切分存入 sections）。"""
    sections: dict[str, str] = {}
    parts = _SECTION_SPLIT.split(policy_text)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = _SECTION_HEAD.match(p)
        if m:
            sections[m.group(0).strip()] = p[len(m.group(0)):].strip()
        elif sections:
            sections[list(sections.keys())[-1]] += "\n" + p
        else:
            sections["全文"] = p
    pid = f"pol_{ULID()}"
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO internal_policy (policy_id, policy_name, file_path, sections)"
            " VALUES (?,?,?,?)",
            (pid, policy_name, "policy-text://inline",
             json.dumps(sections, ensure_ascii=False)))
    return {"policy_id": pid, "sections": list(sections.keys())}


def build_obligations(refresh: bool = False) -> int:
    """从库内条款构建法定义务清单（legal_obligation），按 clause 去重。"""
    conn = get_db_connection()
    if refresh:
        with write_transaction() as c:
            c.execute("DELETE FROM legal_obligation")
    rows = conn.execute(
        "SELECT cr.clause_revision_id, cr.content_text, cr.clause_number,"
        " dm.standard_no, dm.domain_tags FROM clause_revision cr"
        " JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
        " WHERE cr.modality IN ('应当','应','必须') AND cr.modality_strength = 3"
        " AND cr.content_type='normal' ORDER BY dm.standard_no").fetchall()
    n = 0
    with write_transaction() as conn2:
        for r in rows:
            if conn2.execute(
                    "SELECT 1 FROM legal_obligation WHERE clause_revision_id=?",
                    (r["clause_revision_id"],)).fetchone():
                continue
            tags = json.loads(r["domain_tags"] or "[]")
            conn2.execute(
                "INSERT INTO legal_obligation (obligation_id, clause_revision_id,"
                " obligation_text, domain_tag) VALUES (?,?,?,?)",
                (f"ob_{ULID()}", r["clause_revision_id"],
                 f"{r['standard_no']} {r['clause_number']}：{(r['content_text'] or '')[:300]}",
                 tags[0] if tags else None))
            n += 1
    return n


def _keywords(text: str) -> list[str]:
    import jieba
    return [w for w in jieba.cut(text)
            if len(w) >= 2 and w not in _STOP and not w.isdigit()]


def _judge(obligation_text: str, policy_text: str,
           sections: dict[str, str]) -> dict[str, Any]:
    kws = _keywords(obligation_text)
    if not kws:
        return {"verdict": "yellow", "reason": "义务文本过短，无法自动比对", "hit": []}
    hit = [w for w in kws if w in policy_text]
    ratio = len(hit) / len(kws)
    if ratio >= GREEN_RATIO or len(hit) >= GREEN_ABS_HIT:
        verdict = "green"
    elif hit:
        verdict = "yellow"
    else:
        verdict = "red"
    hit_sections = [s for s, body in sections.items() if any(w in body for w in hit[:8])]
    return {"verdict": verdict, "hit": hit[:12], "ratio": round(ratio, 2),
            "sections": hit_sections[:5]}


def _suggestion(obligation_text: str, verdict: str, hit: list[str],
                sections: list[str]) -> str:
    short = obligation_text[:100]
    if verdict == "red":
        return (f"建议在制度中新增对应条款，明确落实：{short}。"
                f"（当前制度未覆盖该义务关键词）")
    if verdict == "yellow":
        return (f"建议完善相关章节（{'、'.join(sections) or '全文'}），"
                f"补充以下关键词覆盖：{'、'.join(hit[:8]) or '细化具体要求'}。")
    return "已覆盖，无需整改。"


def run_gap_analysis(policy_id: str) -> dict:
    """执行差距分析：建 review_task(review_type=gap_analysis) → gap_analysis 落库 → 报告。"""
    conn = get_db_connection()
    pol = conn.execute("SELECT * FROM internal_policy WHERE policy_id=?",
                       (policy_id,)).fetchone()
    if pol is None:
        from src.core.exceptions import KnowledgeStationError
        raise KnowledgeStationError(f"制度不存在: {policy_id}", code="policy_not_found")
    sections = json.loads(pol["sections"] or "{}")
    policy_text = "\n".join(sections.values())

    obligations = conn.execute("SELECT * FROM legal_obligation").fetchall()
    if not obligations:
        build_obligations()
        obligations = conn.execute("SELECT * FROM legal_obligation").fetchall()

    task_id = f"task_{ULID()}"
    results: list[dict] = []
    counts = {"red": 0, "yellow": 0, "green": 0}
    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO review_task (task_id, review_type, object_name, object_content,"
            " status, total_points, completed_at) VALUES (?,?,?,?,?,?,datetime('now'))",
            (task_id, "gap_analysis", pol["policy_name"], policy_text[:1000],
             "completed", len(obligations)))
        for ob in obligations:
            j = _judge(ob["obligation_text"], policy_text, sections)
            counts[j["verdict"]] += 1
            suggestion = _suggestion(ob["obligation_text"], j["verdict"],
                                     j["hit"], j["sections"])
            txn.execute(
                "INSERT INTO gap_analysis (gap_id, task_id, legal_obligation_id,"
                " legal_obligation_text, internal_policy_section, verdict, gap_description,"
                " remediation_suggestion) VALUES (?,?,?,?,?,?,?,?)",
                (f"gap_{ULID()}", task_id, ob["obligation_id"],
                 ob["obligation_text"],
                 json.dumps(j["sections"], ensure_ascii=False) if j["sections"] else None,
                 j["verdict"],
                 f"关键词命中率 {j['ratio']}，命中 {len(j['hit'])} 个："
                 f"{'、'.join(j['hit'][:10]) or '无'}",
                 suggestion))
            results.append({
                "obligation": ob["obligation_text"][:120],
                "verdict": j["verdict"], "hit": j["hit"][:10],
                "ratio": j["ratio"], "suggestion": suggestion,
                "domain": ob["domain_tag"]})
        txn.execute(
            "UPDATE review_task SET red_count=?, yellow_count=?, green_count=?,"
            " report_data=? WHERE task_id=?",
            (counts["red"], counts["yellow"], counts["green"],
             json.dumps({"results": results, "counts": counts}, ensure_ascii=False),
             task_id))
    return {"task_id": task_id, "counts": counts, "results": results,
            "policy_name": pol["policy_name"]}
