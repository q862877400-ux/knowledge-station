"""Phase 9.2 Query Understanding Layer 测试（R9/R40/R41/R52/R53/R60）。"""
import json

import pytest


def test_intent_classification():
    from src.core.query.understanding import classify_intent
    assert classify_intent("查 5.2.1 条") == "clause_lookup"
    assert classify_intent("防火间距多少") == "data_query"
    assert classify_intent("收集人脸信息是否合法") == "compliance_review"
    assert classify_intent("单独同意什么意思") == "interpretation"
    assert classify_intent("两个标准的区别") == "compare"


def test_slot_extraction_and_declared():
    from src.core.query.understanding import extract_slots, parse_declared
    s = extract_slots("丙类厂房 耐火二级 24m 疏散宽度")
    assert s["building_type"] == "厂房" and s["fire_risk"] == "丙类"
    assert s["height"] == "24m"
    d, rest = parse_declared("[甲类/高层/耐火二级] 疏散宽度")
    assert d["fire_risk"] == "甲类" and d["fire_resistance"] == "耐火二级"
    assert rest == "疏散宽度"


def test_v1_slot_table_removed():
    """Task 13.1 死代码清除：v1 槽位表函数已删除（追问 v2 由 LLM 自判）。"""
    import src.core.query.understanding as u
    for dead in ("missing_core_slots", "build_clarify", "CORE_SLOTS", "THEME_CORE_SLOTS"):
        assert not hasattr(u, dead), f"{dead} 应已删除"


def test_clarify_event_when_missing(client):
    """R9 v2：不再用规则槽位表预先追问——统一先检索，由 LLM 单次自判（问还是答）。"""
    c, token = client
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": "防火间距多少", "query_mode": "default"},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        events = [l[7:] for l in r.iter_lines() if l.startswith("event: ")]
    assert events[0] == "evidence", "先检索（不预先规则追问）"
    assert events[-1] == "done"


def test_no_clarify_when_slots_full(client):
    """R9 免追问：带前置声明 [甲类/高层] → 直接出答案。"""
    c, token = client
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": "[甲类/高层民用] 防火间距多少", "query_mode": "default"},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        events = [l[7:] for l in r.iter_lines() if l.startswith("event: ")]
    assert "clarify" not in events
    assert events[0] == "evidence"
    # 参数标注应出现在回答尾部（delta 流中）
    c2 = c
    with c2.stream("POST", "/api/v1/chat/completions",
                   json={"query": "[甲类/高层民用] 防火间距多少", "query_mode": "default"},
                   headers={"Authorization": f"Bearer {token}"}) as r:
        deltas = [json.loads(l[6:])["content"] for l in r.iter_lines()
                  if l.startswith("data: ") and "\"content\"" in l]
    joined = "".join(deltas)
    assert "已识别参数" in joined


def test_condition_filter_and_rank():
    from src.core.query.understanding import apply_condition_filter, rank_with_hierarchy
    from src.core.domain.models import ClauseRevisionModel
    def mk(cid, text, h="GB", mandatory=False):
        return ClauseRevisionModel(
            clause_revision_id=cid, doc_id="d", clause_key=cid, standard_no="S",
            clause_number="1", content_text=text, knowledge_type="rule",
            modality="应", modality_strength=3, page_start=1, page_end=1,
            legal_hierarchy=h, is_mandatory=mandatory)
    civil = mk("a", "民用建筑要求")
    factory = mk("b", "工业厂房要求")
    law = mk("c", "法律层级条款", h="法律", mandatory=True)
    # R52：民用场景剔除厂房条款
    kept = apply_condition_filter([civil, factory], {"building_type": "民用建筑"})
    assert kept == [civil]
    # R40：法律/强标置顶
    ranked = rank_with_hierarchy([factory, law, civil])
    assert ranked[0].clause_revision_id == "c"


def test_standard_type_is_a_real_sort_term_not_a_dead_one():
    """`standard_type` 那一项**曾经是死项**（2026-09-17 独立复核 b7 的 MEDIUM-4）。

    `rank_with_hierarchy` 写的是 `getattr(c, 'standard_type', 'mandatory')`，而
    `ClauseRevisionModel` **没有这个字段** ⇒ 恒取默认 `'mandatory'` ⇒ 对所有条款都算 0。
    也就是说"按强制性排前"这句话**从来没生效过**（复核实测 `std_term=0`），
    而它的写法让读者以为它在起作用——本用例把"它真的在起作用"钉住：

      · `standard_type='mandatory'` 排在 `None`（未登记/采集件）**之前**；
      · `None` 排在 `'recommended'` 之前或之后都行吗？——**不行**：只有 `'mandatory'` 优先，
        其余（含未知）一视同仁，所以这里只断言前一条（外加"未知不得被当作强制"）。
    """
    from src.core.domain.models import ClauseRevisionModel
    from src.core.query.understanding import rank_with_hierarchy

    def mk(cid, std_type):
        return ClauseRevisionModel(
            clause_revision_id=cid, doc_id="d", clause_key=cid, standard_no="S",
            clause_number="1", content_text="t", knowledge_type="rule",
            modality="应", modality_strength=3, page_start=1, page_end=1,
            legal_hierarchy="GB", is_mandatory=False, standard_type=std_type)

    unknown = mk("u", None)                 # 采集件：doc_meta.standard_type 是 NULL
    mandatory = mk("m", "mandatory")
    recommended = mk("r", "recommended")
    ranked = rank_with_hierarchy([unknown, recommended, mandatory])
    ids = [c.clause_revision_id for c in ranked]
    assert ids[0] == "m", ids                 # 强制性在前（这一项现在**真的**承重）
    assert ids[1:] == ["u", "r"], ids          # 未知与推荐同档（未知**不**被当强制）


def test_fetch_full_clause_fills_standard_type(db):
    """`fetch_full_clause` 必须把 `doc_meta.standard_type` 带出来（否则排序项又成死项）。

    ⚠ 条款表**没有** `standard_type` 列（它在 `doc_meta`）——所以这里走**真实入库路径**
    （`insert_clauses_in_txn`），而不是手拼 INSERT（第一版手拼了 `standard_no`，
    而 `clause_revision` 根本没这一列，当场红）。
    """
    from src.core.domain.models import ClauseRevisionModel
    from src.core.storage import clause_repo as cr
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    cr.insert_document(conn, {
        "doc_id": "doc_st_1", "standard_no": "GB 99999-2099", "standard_name": "排序测试",
        "short_code": "GB99999", "current_revision_id": "rev_st_1", "doc_type": "standard",
        "legal_status": "effective", "legal_hierarchy": "GB", "standard_type": "mandatory",
        "file_path": "/tmp/st.pdf", "file_hash": "h_st"})
    from src.core.storage.sqlite_db import write_transaction
    with write_transaction() as txn:
        cr.insert_clauses_in_txn(txn, [ClauseRevisionModel(
            clause_revision_id="clrev_st_1", doc_id="doc_st_1", clause_key="k1",
            standard_no="GB 99999-2099", clause_number="1", title="t", content_text="正文",
            knowledge_type="rule", page_start=1, page_end=1)])
    try:
        got = cr.fetch_full_clause(conn, "clrev_st_1")
        assert got is not None and got.standard_type == "mandatory", got
    finally:
        cr.delete_document("doc_st_1")


def test_sufficiency_note():
    from src.core.query.understanding import sufficiency_note
    assert sufficiency_note("data_query", 1) is not None
    assert sufficiency_note("data_query", 3) is None
    assert sufficiency_note("clause_lookup", 1) is None


def test_special_work_theme_no_clarify(client):
    """R9 追问合理性：高处作业分级是规则查询，不追问建筑参数，直接检索。"""
    c, token = client
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": "我要搞个高处作业，咋看多少级", "query_mode": "default"},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        events = [l[7:] for l in r.iter_lines() if l.startswith("event: ")]
    assert "clarify" not in events, "特殊作业分级问题不应追问建筑参数"
    assert events[0] == "evidence"


def test_theme_missing_slots():
    from src.core.query.understanding import detect_theme, extract_slots
    assert detect_theme("高处作业分几级") == "special_work"
    assert detect_theme("防火间距多少") == "building"
    assert detect_theme("收集人脸信息是否合法") == "privacy"
    # 主题检测与槽位作用域（v1 追问槽位表已删，此处仅验证 extract_slots 的主题作用域）
    assert extract_slots("收集人脸信息是否合法", theme="privacy").get("behavior") is not None


def test_theme_scoped_slots():
    """通用主题作用域：特殊作业不提取建筑高度槽位（不做死标签）；
    建筑主题才提取 height。「间距几米/探头安装高度几米」等数字
    LLM 从问题原文直接可见，无需槽位语义。"""
    from src.core.query.understanding import extract_slots, detect_theme
    q = "4米高处作业是几级"
    assert detect_theme(q) == "special_work"
    slots = extract_slots(q, theme=detect_theme(q))
    assert "height" not in slots, "特殊作业主题不应提取建筑高度"
    assert "work_height" not in slots, "不应有硬编码作业高度标签"
    # 建筑主题：高度槽位保留（R9 追问/场景注入用）
    slots2 = extract_slots("丙类厂房建筑高度80米", theme="building")
    assert "height" in slots2 and slots2["height"].startswith("80")
    # 默认（general）行为不变：仍提取高度
    slots3 = extract_slots("高度80米", theme="general")
    assert "height" in slots3


def test_grade_question_is_rule_query():
    from src.core.query.understanding import classify_intent
    assert classify_intent("高处作业分几级") == "rule_query"
    assert classify_intent("高处作业多少级") == "rule_query"
    assert classify_intent("防火间距多少米") == "data_query"


def test_refine_search_query():
    from src.core.query.understanding import refine_search_query
    assert "分级" in refine_search_query("高处作业咋看多少级", "rule_query", "special_work")
    assert "特殊作业" in refine_search_query("动火作业要求", "rule_query", "special_work")
    assert refine_search_query("防火间距多少米", "data_query", "building").startswith("防火间距多少米")


def test_title_clause_expansion(_isolate_data_dir):
    """命中标题条款（8.1 作业分级）应附带子条款（8.1.1 分级内容）。"""
    from src.core.storage.sqlite_db import init_schema, get_db_connection, write_transaction
    from src.core.storage import clause_repo
    from src.core.domain.models import ClauseRevisionModel
    init_schema()
    conn = get_db_connection()
    if conn.execute("SELECT 1 FROM doc_meta WHERE doc_id='t8'").fetchone():
        clause_repo.delete_document("t8")
    with write_transaction() as c:
        clause_repo.insert_document(c, dict(
            doc_id="t8", standard_no="GB T8-2022", standard_name="t", short_code="t8",
            current_revision_id="r", domain_tags=[], file_path="t.pdf", file_hash="ht8"))
    clause_repo.insert_clauses([
        ClauseRevisionModel(clause_revision_id="t8a", doc_id="t8", clause_key="t8a",
                            standard_no="GB T8-2022", clause_number="8.1",
                            content_text="8.1 作业分级", knowledge_type="rule",
                            page_start=10, page_end=10),
        ClauseRevisionModel(clause_revision_id="t8b", doc_id="t8", clause_key="t8b",
                            standard_no="GB T8-2022", clause_number="8.1.1",
                            content_text="8.1.1 作业高度 h 分为四个区段：2m至5m；5m至15m；15m至30m；大于30m。",
                            knowledge_type="data", page_start=10, page_end=10),
        ClauseRevisionModel(clause_revision_id="t8c", doc_id="t8", clause_key="t8c",
                            standard_no="GB T8-2022", clause_number="8.2",
                            content_text="8.2 作业要求：应正确佩戴安全带。", knowledge_type="rule",
                            modality="应", modality_strength=3, page_start=11, page_end=11),
    ])
    from src.core.api.server import create_app
    from fastapi.testclient import TestClient
    with TestClient(create_app("t")) as c:
        with c.stream("POST", "/api/v1/chat/completions",
                      json={"query": "高处作业咋看多少级", "query_mode": "guess", "top_k": 3},
                      headers={"Authorization": "Bearer t"}) as r:
            evs = None
            for line in r.iter_lines():
                if line.startswith("data: ") and "evidences" in line:
                    evs = json.loads(line[6:])["evidences"]
                    break
    nums = [e["clause_number"] for e in (evs or [])]
    assert "8.1" in nums, f"应命中标题条款: {nums}"
    assert "8.1.1" in nums, f"标题条款应附带子条款 8.1.1: {nums}"


def test_correction_detection():
    from src.core.query.understanding import detect_correction
    c = detect_correction("不对，我问的是日照间距，不是防火间距")
    assert c is not None and (c.get("right") == "日照间距" or c.get("wrong") == "防火间距")
    assert detect_correction("正常问题") is None
