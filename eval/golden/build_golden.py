"""Golden Set 构建器（Task 10.1）：从当前知识库抽取/合成问题-答案对，冻结落盘。

设计：数据集固定为 eval/golden/golden.json（提交），benchmark 读盘评测，
不随库演化漂移——门禁的可复现性依赖"答案冻结"。
覆盖：三型知识（data/rule/legal）、六通道优势场景、精确号、语义近义、
模态对抗样本（核验器）、合规三色判定（复用 16 条 ground truth）。

用法: .venv/Scripts/python eval/golden/build_golden.py [--force]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from src.core.storage.sqlite_db import get_db_connection

GOLDEN_PATH = Path(__file__).resolve().parent / "golden.json"


def _load_real_clauses() -> list[dict]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT cr.clause_revision_id, cr.clause_number, cr.content_text,"
        " cr.knowledge_type, cr.modality, cr.subject, dm.standard_no,"
        " dm.legal_status FROM clause_revision cr"
        " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
        " WHERE cr.content_type='normal' AND LENGTH(cr.content_text) > 10"
        " ORDER BY dm.standard_no, cr.rowid").fetchall()
    return [dict(r) for r in rows]


def build() -> list[dict]:
    items: list[dict] = []
    clauses = _load_real_clauses()

    # ① 精确条款号场景（exact 通道）
    for c in clauses[:24]:
        items.append({
            "type": "exact",
            "query": f"查 {c['standard_no']} 第{c['clause_number']}条",
            "answer": [c["clause_number"]],
            "knowledge_type": c["knowledge_type"],
            "standard_no": c["standard_no"],
        })

    # ② 口语/语义场景（fts+vec 通道）：取内容前 20 字关键词
    def _keywords(text: str) -> str:
        import re
        toks = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
        return " ".join(dict.fromkeys(toks[:4]))

    for c in clauses[:20]:
        kw = _keywords(c["content_text"])
        if len(kw) < 4:
            continue
        items.append({
            "type": "semantic",
            "query": f"关于{kw}有什么要求",
            "answer": [c["clause_number"]],
            "knowledge_type": c["knowledge_type"],
            "standard_no": c["standard_no"],
        })

    # ③ 模态/法要素/行为域通道样本：查询含具体主题 + 模态词（避免泛问）
    for c in clauses:
        import re as _re
        topic = _re.sub(r"[应应当不得禁止严禁必须可以有权]+", "", c["content_text"])[:14]
        if c["modality"] and c["modality"] in ("不得", "禁止", "严禁", "应当", "应"):
            items.append({
                "type": "modality",
                "query": f"{topic} {c['modality']}",
                "answer": [c["clause_number"]],
                "knowledge_type": c["knowledge_type"],
                "standard_no": c["standard_no"],
            })
        if c["subject"]:
            items.append({
                "type": "legal_element",
                "query": f"{c['subject']}的义务",
                "answer": [c["clause_number"]],
                "knowledge_type": c["knowledge_type"],
                "standard_no": c["standard_no"],
            })
        if len(items) >= 90:
            break

    # ④ 模态对抗样本（核验器拦截率，answer 无意义）
    items.append({"type": "modality_adversarial", "query": "动火作业监护强度",
                  "answer": [], "knowledge_type": "rule",
                  "llm_output": "动火作业宜设专人监护", "source_modality": "应"})
    items.append({"type": "modality_adversarial", "query": "可燃材料",
                  "answer": [], "knowledge_type": "rule",
                  "llm_output": "可以采用可燃材料作保温层", "source_modality": "严禁"})
    items.append({"type": "modality_adversarial", "query": "监护人离岗",
                  "answer": [], "knowledge_type": "rule",
                  "llm_output": "监护人宜坚守现场", "source_modality": "不应"})

    # ⑤ 合规三色判定样本（复用租赁合同 ground truth 特征）
    items.append({"type": "compliance", "query": "本协议最终解释权归甲方所有",
                  "answer": [], "expected_verdict": "red"})
    items.append({"type": "compliance", "query": "未住满12个月押金一律不退",
                  "answer": [], "expected_verdict": "red"})
    items.append({"type": "compliance", "query": "由甲方所在地人民法院管辖",
                  "answer": [], "expected_verdict": "yellow"})
    return items


def main() -> int:
    force = "--force" in sys.argv
    if GOLDEN_PATH.exists() and not force:
        print(f"golden.json 已存在（{GOLDEN_PATH}）；用 --force 重建")
        return 0
    data = build()
    GOLDEN_PATH.write_text(
        json.dumps({"meta": {"source": "knowledge.db @ build time", "count": len(data)},
                    "items": data}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已生成 {GOLDEN_PATH}: {len(data)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
