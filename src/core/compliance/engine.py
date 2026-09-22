"""T06a 合规审查引擎（R-L4~L7）：审查点抽取 → 法条匹配 → 三色判定 → 报告。

判定策略（阶段3，省 API 预算）：
- 规则优先：模态比对 + 关键词重合度给出确定性判定；
- LLM 可选：use_llm=True 时对"风险(黄)"档做一次小窗精判（业主余额有限，默认关闭）。
"""
from __future__ import annotations

import json
import re

from ulid import ULID

from src.core.config import get_settings
from src.core.retrieval.hybrid_engine import perform_hybrid_search
from src.core.storage.sqlite_db import get_db_connection, write_transaction

# 审查点类型关键词表（R-L4 合同关键条款）
_POINT_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("格式条款", ("最终解释权", "解释权归", "格式条款", "概不退换", "单方变更")),
    ("违约金条款", ("违约金", "赔偿金", "定金")),
    ("管辖条款", ("管辖", "仲裁", "法院", "诉讼")),
    ("保密条款", ("保密", "商业秘密")),
    ("知识产权条款", ("知识产权", "著作权", "专利")),
    ("付款条件", ("付款", "价款", "支付方式")),
    ("解除条款", ("解除", "终止合同")),
    ("数据收集行为", ("收集", "个人信息", "人脸", "生物识别")),
    ("数据使用行为", ("使用", "共享", "传输", "委托处理")),
    ("费用条款", ("押金", "退还", "物业管理费", "水电费", "维修费", "单价", "缴纳")),
]

_FORBIDDEN_PATTERNS = re.compile(
    r"最终解释权|放弃.{0,8}权利|概不退换|单方(?:变更|解除|终止|定价)|不承担.{0,8}责任|"
    r"未取得.{0,12}同意|未经同意|强制同意|一揽子同意|"
    r"(?:押金|费用|租金).{0,12}(?:一律不退|不予退还|不退\b)|(?:此|概不)不退|"
    r"三倍赔偿|视为违约|不得以任何理由异议|不得.{0,10}异议|"
    r"不得在[^，。]{2,12}(?:怀孕|生产|坐月子|留宿)|"
    r"按月租金的\s*10\s*%|逾期.{0,10}违约金")
# 风险模式 → 检索锚点（合规系统的规则锚点层：口语风险描述映射到法条术语）
_ANCHOR_TERMS: list[tuple[str, str]] = [
    (r"最终解释权", "格式条款 解释 不利于提供方"),
    (r"(?:押金|费用|租金).{0,12}(?:一律不退|不予退还|不退\b)|此费用不退", "格式条款 排除 主要权利 无效 加重对方责任"),
    (r"三倍赔偿", "损失赔偿额 相当于 因违约所造成的损失"),
    (r"不承担.{0,8}责任", "格式条款 不合理地免除 减轻其责任 无效"),
    (r"视为违约|不得以任何理由异议|不得.{0,10}异议", "格式条款 限制 对方主要权利 无效"),
    (r"按月租金的\s*10\s*%|违约金", "违约金 过分高于造成的损失 适当减少"),
    (r"(?:单方|重新确定).{0,8}(?:解除|租金|定价)|有权提前解除", "格式条款 排除 对方主要权利 加重对方责任"),
    (r"管辖", "合同纠纷 被告住所地 合同履行地 管辖"),
    (r"(?:怀孕|坐月子|月嫂)", "公序良俗 无效 违背"),
    (r"维修.{0,20}(?:由乙方|不承担|自行承担)", "出租人 维修义务 租赁物"),
    (r"电费|水费", "电费 加收其他费用 禁止"),
]
_OBLIGATION_MARKERS = re.compile(r"应当|必须|须|应")
_CLAUSE_SPLIT = re.compile(r"(?=第[一二三四五六七八九十百千]+条)")


def _anchor_terms(text: str) -> str | None:
    """风险模式 → 法条检索锚点。"""
    for pat, terms in _ANCHOR_TERMS:
        if re.search(pat, text):
            return terms
    return None


def extract_review_points(object_content: str, review_type: str = "contract"
                          ) -> list[dict[str, str]]:
    """R-L4 审查点抽取（规则版）：合同按条文切分并归类；行为描述整体为一点。"""
    points: list[dict[str, str]] = []
    if review_type == "behavior":
        points.append({"point_type": "行为描述", "point_content": object_content.strip()[:2000]})
        return points
    chunks = _CLAUSE_SPLIT.split(object_content)
    for chunk in chunks:
        chunk = chunk.strip()
        if len(chunk) < 6:
            continue
        ptype = "一般条款"
        for name, kws in _POINT_KEYWORDS:
            if any(k in chunk for k in kws):
                ptype = name
                break
        # 逐句扫描：每个风险句独立成审查点（同一合同条内多个植入问题分别捕获）
        added = 0
        for sent in re.split(r"[。；\n]", chunk):
            sent = sent.strip()
            if len(sent) < 8:
                continue
            if _FORBIDDEN_PATTERNS.search(sent) or any(
                    k in sent for _, kws in _POINT_KEYWORDS for k in kws):
                points.append({"point_type": ptype, "point_content": sent[:500]})
                added += 1
        if added == 0:
            points.append({"point_type": ptype, "point_content": chunk[:500]})
    return points[:40]


def _token_overlap(a: str, b: str) -> int:
    import jieba
    ta = {w for w in jieba.cut(a) if len(w) >= 2}
    tb = {w for w in jieba.cut(b) if len(w) >= 2}
    return len(ta & tb)


def _behavior_scope_of(point: dict) -> str | None:
    text = point["point_content"]
    kws = [kw for name, kws_t in _POINT_KEYWORDS
           if name.startswith("数据") for kw in kws_t if kw in text]
    return " ".join(kws) if kws else None


def judge_point_rule(point: dict, matched: list) -> dict:
    """R-L6 三色判定（规则版）。

    red: 审查点命中禁止性表述，且命中法条含 不得/禁止/严禁 且主题重合
    yellow: 命中"应当"型义务但审查点无履行迹象，或落入但书条件
    green: 命中"可以/有权"赋权条款且无禁止命中
    """
    text = point["point_content"]
    has_forbidden_pattern = bool(_FORBIDDEN_PATTERNS.search(text))
    has_obligation_signal = bool(_OBLIGATION_MARKERS.search(text))

    best_red, best_yellow, best_green = None, None, None
    for c in matched:
        overlap = _token_overlap(text, c.content_text)
        if overlap == 0 and not has_forbidden_pattern:
            continue
        # 禁止性法条：显式 不得/禁止/严禁 模态，或"格式条款无效"类无效条款（如民法典497）
        prohibitive = (c.modality in ("不得", "禁止", "严禁")
                       or ("无效" in (c.content_text or "") and "格式条款" in (c.content_text or "")))
        entry = {"clause": c, "overlap": overlap}
        if prohibitive:
            if best_red is None or overlap > best_red["overlap"]:
                best_red = entry
        elif c.modality in ("应当", "应", "必须"):
            if best_yellow is None or overlap > best_yellow["overlap"]:
                best_yellow = entry
        elif c.modality in ("可以", "有权", "可"):
            if best_green is None or overlap > best_green["overlap"]:
                best_green = entry

    if best_red and (has_forbidden_pattern or best_red["overlap"] >= 2):
        c = best_red["clause"]
        return {"verdict": "red",
                "reason": f"审查点落入禁止性规定（{c.standard_no} {c.clause_number}："
                          f"{(c.content_text or '')[:80]}），且表述含限制权利/未经同意特征。",
                "matched": best_red}
    if best_yellow and not has_obligation_signal:
        c = best_yellow["clause"]
        return {"verdict": "yellow",
                "reason": f"涉及「应当」型义务（{c.standard_no} {c.clause_number}），"
                          f"审查点未见履行表述，需人工确认落实情况。",
                "matched": best_yellow}
    if best_green:
        c = best_green["clause"]
        return {"verdict": "green",
                "reason": f"属赋权性规定允许的范围（{c.standard_no} {c.clause_number}）。",
                "matched": best_green}
    if best_yellow:
        c = best_yellow["clause"]
        return {"verdict": "yellow",
                "reason": f"涉及义务条款（{c.standard_no} {c.clause_number}），建议对照落实。",
                "matched": best_yellow}
    return {"verdict": "yellow", "reason": "未命中明确法条，需人工复核。",
            "matched": None}


def judge_point(point: dict, matched: list, use_llm: bool = False) -> dict:
    """判定入口：规则版为主；use_llm 且配置了 Key 时对黄档做一次小窗 LLM 精判。"""
    result = judge_point_rule(point, matched)
    if use_llm and result["verdict"] == "yellow" and matched and get_settings().llm_api_key:
        try:
            result = _judge_point_llm(point, matched) or result
        except Exception:
            pass
    return result


def _judge_point_llm(point: dict, matched: list) -> dict | None:
    from src.core.llm.deepseek_client import stream_chat_completion
    ev = [{"clause_revision_id": c.clause_revision_id, "clause_number": c.clause_number,
           "standard_no": c.standard_no, "knowledge_type": c.knowledge_type,
           "modality": c.modality, "content_text": (c.content_text or "")[:300],
           "exception": c.exception, "subject": c.subject, "page_start": c.page_start}
          for c in matched[:4]]
    prompt = (f"审查点[{point['point_type']}]：{point['point_content']}\n"
              f"请仅依据上述法条判断该审查点合规性，"
              f'输出 JSON：{{"verdict":"red|yellow|green","reason":"..."}}')
    answer = "".join(stream_chat_completion(prompt, ev, max_tokens=150, temperature=0.0))
    m = re.search(r'\{[^{}]*"verdict"[^{}]*\}', answer)
    if not m:
        return None
    try:
        data = json.loads(m.group(0).replace("'", '"'))
        if data.get("verdict") in ("red", "yellow", "green"):
            return {"verdict": data["verdict"], "reason": str(data.get("reason", ""))[:300],
                    "matched": {"clause": matched[0], "overlap": 0} if matched else None}
    except Exception:
        return None
    return None


def create_review_task(review_type: str, object_name: str, object_content: str,
                       project_id: str | None = None) -> dict:
    """R-L4：创建审查任务并抽取审查点（待用户确认后执行）。"""
    task_id = f"task_{ULID()}"
    points = extract_review_points(object_content, review_type)
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO review_task (task_id, project_id, review_type, object_name,"
            " object_content, status, total_points) VALUES (?,?,?,?,?,?,?)",
            (task_id, project_id, review_type, object_name,
             object_content[:10000], "pending", len(points)))
        for p in points:
            conn.execute(
                "INSERT INTO review_point (point_id, task_id, point_type, point_content)"
                " VALUES (?,?,?,?)",
                (f"pt_{ULID()}", task_id, p["point_type"], p["point_content"]))
    return {"task_id": task_id, "status": "pending",
            "extracted_points": [
                {"point_id": r["point_id"], "point_type": r["point_type"],
                 "point_content": r["point_content"]}
                for r in get_db_connection().execute(
                    "SELECT point_id, point_type, point_content FROM review_point"
                    " WHERE task_id=? ORDER BY created_at", (task_id,)).fetchall()]}


def execute_review(task_id: str, confirmed_point_ids: list[str] | None = None):
    """R-L5~L7：逐点匹配 → 判定 → 落库。生成器逐点 yield 结果（供 SSE）。"""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT point_id, point_type, point_content FROM review_point"
        " WHERE task_id=? ORDER BY created_at", (task_id,)).fetchall()
    if confirmed_point_ids:
        rows = [r for r in rows if r["point_id"] in confirmed_point_ids]
    conn.execute("UPDATE review_task SET status='analyzing' WHERE task_id=?", (task_id,))
    conn.commit()

    counts = {"red": 0, "yellow": 0, "green": 0}
    results = []
    for r in rows:
        point = {"point_type": r["point_type"], "point_content": r["point_content"]}
        # R-L5: 六路召回（合规场景启用 D/E/F）+ 风险锚点增强查询
        anchor = _anchor_terms(r["point_content"])
        query = f"{r['point_content']} {anchor}" if anchor else r["point_content"]
        matched = perform_hybrid_search(
            query=query, top_k=5, rerank_k=8,  # 合规场景 top-K=8（ROADMAP 10.2）
            behavior_scope_filter=_behavior_scope_of(point))
        # 强制性规定优先（R-L5.2）
        matched.sort(key=lambda c: 0 if (c.modality in ("严禁", "禁止", "不得", "应当", "应"))
                     else 1)
        verdict = judge_point(point, matched)
        counts[verdict["verdict"]] += 1
        matched_ids = [c.clause_revision_id for c in matched[:3]]
        top = verdict.get("matched")
        reason = verdict["reason"]
        with write_transaction() as txn:
            txn.execute(
                "UPDATE review_point SET matched_clause_ids=?, verdict=?, verdict_reason=?"
                " WHERE point_id=?",
                (json.dumps(matched_ids), verdict["verdict"], reason, r["point_id"]))
        item = {
            "point_id": r["point_id"], "point_type": r["point_type"],
            "point_content": r["point_content"][:200],
            "verdict": verdict["verdict"], "reason": reason,
            "matched_clauses": [
                {"clause_revision_id": c.clause_revision_id, "standard_no": c.standard_no,
                 "clause_number": c.clause_number, "modality": c.modality,
                 "page_start": c.page_start,
                 # S2-b1（2026-09-22，**只加不改**）：补 doc_id —— 界面「看原文」要拿它拼证据锚点
                 # （跳 PDF 那一页 + 红箭头）；没有它时客户端拿 rev 当 doc 兜底 = 假链接
                 # （真机点开找不到文件）。getattr 兜底 None ⇒ 旧形状语义不变。
                 "doc_id": getattr(c, "doc_id", None)} for c in matched[:3]],
        }
        results.append(item)
        yield item

    with write_transaction() as txn:
        txn.execute(
            "UPDATE review_task SET status='completed', red_count=?, yellow_count=?,"
            " green_count=?, completed_at=datetime('now'), report_data=? WHERE task_id=?",
            (counts["red"], counts["yellow"], counts["green"],
             json.dumps({"results": results, "counts": counts}, ensure_ascii=False),
             task_id))
