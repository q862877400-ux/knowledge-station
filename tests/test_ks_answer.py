# -*- coding: utf-8 -*-
"""P1a 取证答案 ks_answer 单测。

运行（仓库根，便于解析 src）：:
    cd D:\\AI\\work space\\zcode && .venv\\Scripts\\python.exe -m pytest ".p1rollout\\p1_ks_answer_130632\\test_ks_answer.py" -q

策略：
  * 临时库（KS_DATA_DIR 重定向）种子数据 + monkeypatch 假 LLM 流（零真实 LLM 消耗）；
  * 向量/rerank 引擎强制离线（monkeypatch embedder.is_available → False、reranker.is_available → False），
    走 R30 降级路径，快速且确定（与 tests/conftest.py 隔离约定一致）；
  * 断言证据全部 effective、非法条款不进 evidence、tier 三态、verification 字段形状、[[c:i]] 解析。
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"D:\AI\work space\zcode")

import pytest
from pydantic import BaseModel

from src.core.domain.models import ClauseRevisionModel
from src.core.retrieval import embedder as _emb
from src.core.retrieval import reranker as _rr

# 被测模块（仓库规范路径）
from src.core.llm import ks_answer
from src.core.llm.ks_answer import (
    answer, build_messages, parse_llm_answer,
    _decide_tier, _filter_effective, _dedupe, _cap, _is_effective,
    _is_substantive, _clause_to_evidence, EVIDENCE_CAP,
)


# ---------------------------------------------------------------------------
# 会话级临时库 + 强制离线引擎
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def _isolate_and_offline():
    """module 级私有临时库：只在本模块运行期间生效，结束后还原。

    不用 session 级——全局 KS_DATA_DIR 若在模块中途被替换会污染同会话其他模块
    （ENCYCLOPEDIA §13.3 共享库约定）。module 级 = 本模块内等效独立运行，
    跑完即还原，对其他模块零影响。
    """
    with tempfile.TemporaryDirectory(prefix="ksanswer_", ignore_cleanup_errors=True) as td:
        old = os.environ.get("KS_DATA_DIR")
        os.environ["KS_DATA_DIR"] = td
        from src.core import config
        config.reset_settings()
        # 默认连接缓存的 key 是固定 "conn_default"（不看路径）：前序模块可能已把
        # 该线程连接指向旧库（空文件/共享库）。清掉，让本模块在新数据目录上重连。
        from src.core.storage.sqlite_db import close_thread_connection
        close_thread_connection()
        yield Path(td)
        config.reset_settings()
        close_thread_connection()
        if old is None:
            os.environ.pop("KS_DATA_DIR", None)
        else:
            os.environ["KS_DATA_DIR"] = old


@pytest.fixture(autouse=True)
def _offline_engines(monkeypatch):
    monkeypatch.setattr(_emb, "is_available", lambda: False)
    monkeypatch.setattr(_rr, "is_available", lambda: False)
    yield


# ---------------------------------------------------------------------------
# 种子数据
# ---------------------------------------------------------------------------
DOC_A = dict(doc_id="docA", standard_no="GB 30871-2022", standard_name="危险化学品企业特殊作业安全规范",
             short_code="30871", current_revision_id="revA", legal_status="effective",
             legal_hierarchy="GB", standard_type="mandatory", doc_type="standard",
             quality_grade="A", domain_tags=["特殊作业"], effective_from="2022-10-01",
             file_path="/f/A.pdf", file_hash="hashA")
DOC_B = dict(doc_id="docB", standard_no="GB/T 50493-2019", standard_name="石油化工可燃气体和有毒气体检测报警设计标准",
             short_code="50493", current_revision_id="revB", legal_status="effective",
             legal_hierarchy="T", standard_type="recommended", doc_type="standard",
             quality_grade="A", domain_tags=["气体检测"], effective_from="2019-11-01",
             file_path="/f/B.pdf", file_hash="hashB")
DOC_C = dict(doc_id="docC", standard_no="GB 30871-2025", standard_name="危险化学品企业特殊作业安全规范（2025版）",
             short_code="30871", current_revision_id="revC", legal_status="upcoming",
             legal_hierarchy="GB", standard_type="mandatory", doc_type="standard",
             quality_grade="A", domain_tags=["特殊作业"], effective_from="2026-10-01",
             file_path="/f/C.pdf", file_hash="hashC")
DOC_D = dict(doc_id="docD", standard_no="GB 30871-2018", standard_name="化学品生产单位特殊作业安全规范",
             short_code="30871", current_revision_id="revD", legal_status="superseded",
             legal_hierarchy="GB", standard_type="mandatory", doc_type="standard",
             quality_grade="A", domain_tags=["特殊作业"], effective_from="2018-06-01",
             file_path="/f/D.pdf", file_hash="hashD")


def _clause(cid, doc_id, standard_no, no, content, title=None, modality=None,
            knowledge_type="rule", is_mandatory=False, page_start=1):
    return ClauseRevisionModel(
        clause_revision_id=cid, doc_id=doc_id,
        clause_key=f"{doc_id}:{no}", standard_no=standard_no, clause_number=no,
        title=title, content_text=content, knowledge_type=knowledge_type,
        modality=modality, is_mandatory=is_mandatory,
        content_type="normal", page_start=page_start, page_end=page_start,
    )


def _seed_db():
    """初始化临时库并插入四份文档的条款（clause_fts 由 insert_clauses 自动填充）。"""
    from src.core.storage.sqlite_db import init_schema, get_db_connection, close_thread_connection
    from src.core.storage import clause_repo
    from src.core.retrieval import embedder as emb
    # 种子阶段强制向量离线（避免 conf 缓存之外的模型下载；与 autouse fixture 一致）。
    # 2026-09-06 泄漏修复：直接 setattr 打在全局模块对象上且永不还原，会污染
    # 同进程后续所有检索测试（phase4 obligation 顺序敏感失败的根因）——
    # 首次 setattr 前保存原函数，由 _isolate_and_offline teardown 还原。
    if not hasattr(emb, "_ksanswer_forced_offline"):
        emb._ksanswer_orig_is_available = emb.is_available
        emb.is_available = lambda: False
        emb._ksanswer_forced_offline = True
    init_schema()
    conn = get_db_connection()
    from src.core.retrieval import embedder as emb
    # 保证向量通道离线（insert_clauses 内部 embedder.is_available 也被 monkeypatch）
    for doc in (DOC_A, DOC_B, DOC_C, DOC_D):
        clause_repo.insert_document(conn, doc)
    clauses = [
        _clause("clA51", "docA", "GB 30871-2022", "5.1", "特殊作业分级", title="特殊作业分级", knowledge_type="rule"),
        _clause("clA52", "docA", "GB 30871-2022", "5.2", "特殊作业基本要求", title="特殊作业基本要求", knowledge_type="rule"),
        _clause("clA521", "docA", "GB 30871-2022", "5.2.1",
                "动火作业应办理作业许可证。动火作业前应进行作业风险分析并确认现场安全条件，作业人员应佩戴相应的个体防护用品。",
                modality="应", is_mandatory=True, page_start=11),
        _clause("clA43", "docA", "GB 30871-2022", "4.3",
                "特殊作业现场应配备必要的应急救援器材与个体防护装备。作业人员应经过专项培训并持证上岗。",
                modality="应", is_mandatory=True, page_start=9),
        _clause("clB612", "docB", "GB/T 50493-2019", "6.1.2",
                "特殊作业现场气体检测报警仪应定期检定，检定周期应符合相关标准规定。检测探头安装位置应能有效覆盖作业区域。",
                modality="应", page_start=5),
        _clause("clC521", "docC", "GB 30871-2025", "5.2.1",
                "动火作业应办理作业许可证，并落实2025版新增的安全交底与监护人要求。作业前应进行风险分析。",
                modality="应", is_mandatory=True, page_start=1),
        _clause("clD521", "docD", "GB 30871-2018", "5.2.1",
                "动火作业应办理动火安全作业证。作业前应清理现场可燃物并落实防护措施。",
                modality="应", is_mandatory=True, page_start=1),
    ]
    clause_repo.insert_clauses(clauses)
    close_thread_connection()
    conn.close()


_SEEDED = False


@pytest.fixture(scope="module", autouse=True)
def _seeded(_isolate_and_offline):
    global _SEEDED
    if not _SEEDED:
        _seed_db()
        _SEEDED = True
    yield
    # 还原 _seed_db 打在全局 embedder 模块上的离线补丁（泄漏修复，见 _seed_db 注释）。
    from src.core.retrieval import embedder as emb
    orig = getattr(emb, "_ksanswer_orig_is_available", None)
    if orig is not None:
        emb.is_available = orig
        del emb._ksanswer_orig_is_available
    if getattr(emb, "_ksanswer_forced_offline", False):
        del emb._ksanswer_forced_offline


# ---------------------------------------------------------------------------
# 假 LLM 流
# ---------------------------------------------------------------------------

def _fake_stream(text: str):
    def g():
        for i in range(0, len(text), 7):
            yield text[i:i + 7]
    return g()


def _patch_llm(monkeypatch, text):
    monkeypatch.setattr(ks_answer, "_stream_llm",
                        lambda messages, **kw: _fake_stream(text))


# ---------------------------------------------------------------------------
# 纯函数单测（不依赖 LLM / 检索）
# ---------------------------------------------------------------------------

def _ev(status="_", cid="", standard_no="GB X-1", clause_number="a", content="X" * 90,
        doc_id="d", kt="rule", modality="应"):
    # 构造最小内部证据 dict（缺省 _full_text 长正文 → substantive）
    return {
        "clause_revision_id": cid or f"cid{abs(hash(standard_no + clause_number))}",
        "doc_id": doc_id, "standard_no": standard_no, "clause_number": clause_number,
        "title": None, "legal_status": status, "legal_hierarchy": "GB",
        "page_start": 1, "snippet": content[:800], "effective_from": None,
        "_clause_key": f"{doc_id}:{clause_number}", "_full_text": content,
        "_table_md": "", "_knowledge_type": kt, "_modality": modality,
        "_modality_strength": 3, "_exception": None, "_subject": None,
        "_is_suspicious": False, "_type_confidence": 1.0,
    }


def test_filter_effective_drops_non_effective_and_keeps_effective():
    evs = [_ev(status="effective"), _ev(status="superseded"), _ev(status="withdrawn"),
           _ev(status="upcoming", standard_no="GB X-2025"), _ev(status="effective")]
    kept = _filter_effective(evs)
    assert len(kept) == 2
    assert all(_is_effective(e) for e in kept)
    assert kept[0]["legal_status"] == "effective"
    assert all(e["clause_number"] == "a" for e in kept)  # 抽查字段保留


def test_dedupe_by_revision_id_and_on_pairs():
    a = _ev(cid="c1")
    b = _ev(cid="c2", standard_no="GB Y-1", clause_number="b")
    dup = _ev(cid="c1")                      # 同 revision_id 重复
    pair_dup = _ev(cid="c3", doc_id="d", clause_number="c", standard_no="GB Z-1")
    pair_dup["clause_revision_id"] = ""      # 空 id → 走 (doc,clause) 去重
    out = _dedupe([a, b, dup, pair_dup, dict(pair_dup)])
    assert len(out) == 3
    assert len([e for e in out if e["_clause_key"] == "d:c"]) == 1   # pair 去重（仅 1 条）
    assert {e["clause_revision_id"] for e in out} == {"c1", "c2", ""}  # 空 id 保留一条


def test_cap_enforces_upper_bound_8():
    evs = [_ev(cid=f"c{i}") for i in range(20)]
    assert len(_cap(evs)) == EVIDENCE_CAP == 8
    # max_evidence 大于 8 时也被钳制到 8
    assert len(_cap(evs, max_n=99)) == 8
    assert len(_cap(evs, max_n=3)) == 3


def test_tier_three_states():
    substantive = _ev()
    hollow = _ev(content="作业分级", kt="rule", modality=None)
    hollow["_full_text"] = "作业分级"
    assert _decide_tier([substantive], {}) == "direct"
    assert _decide_tier([substantive, _ev(standard_no="GB Y-1", clause_number="b")], {}) == "synthesis"
    assert _decide_tier([], {}) == "reference"
    assert _decide_tier([hollow], {}) == "reference"


def test_is_substantive():
    assert _is_substantive(_ev(content="X" * 90)) is True          # 长正文
    assert _is_substantive(_ev(content="短文", modality="应")) is True   # 短但有模态词
    assert _is_substantive(_ev(content="短文", modality=None)) is False  # 空标题（无模态/无表/短）
    assert _is_substantive({**_ev(content="短文", modality=None), "_table_md": "| a | b |"}) is True


def test_clause_public_evidence_has_spec_fields_and_no_underscore():
    clause = _clause("cid", "docA", "GB 30871-2022", "5.2.1", "X" * 100,
                     modality="应", page_start=11)
    ev = _clause_to_evidence(clause)
    # 对外 evidence 只暴露（去下划线后的）公共字段
    public = {k: v for k, v in ev.items() if not k.startswith("_")}
    for k in ("clause_revision_id", "doc_id", "standard_no", "clause_number",
              "title", "legal_status", "legal_hierarchy", "page_start", "snippet"):
        assert k in public
    assert all(not k.startswith("_") for k in public)
    assert len(public["snippet"]) <= 800
    assert ev["_full_text"] == "X" * 100            # 内部保留全量（核验用）
    assert public["legal_status"] == "effective"    # resolve_status 后现行


# ---------------------------------------------------------------------------
# LLM 输出解析
# ---------------------------------------------------------------------------

def test_parse_llm_answer_json_with_citation():
    text = '{"derivation":"根据[[c:0]]规定，动火作业应办理作业许可证。","conclusion":"应办理作业许可证。"}'
    parsed = parse_llm_answer(text, evidence_count=1)
    assert parsed["derivation"].startswith("根据[[c:0]]")
    assert parsed["conclusion"] == "应办理作业许可证。"
    assert "[[c:0]]" in parsed["derivation"]
    assert parsed["warnings"] == []


def test_parse_llm_answer_code_fence_and_bare_text_fallback():
    fenced = '```json\n{"derivation":"依据[[c:0]]","conclusion":"结论"}\n```'
    p = parse_llm_answer(fenced, evidence_count=1)
    assert p["derivation"] == "依据[[c:0]]"
    assert p["conclusion"] == "结论"
    # 纯正文（无 JSON）→ 全程作为 derivation，给出兜底 warning
    prose = "依据[[c:0]]，动火作业应办理作业许可证。"
    p2 = parse_llm_answer(prose, evidence_count=1)
    assert p2["derivation"] == prose
    assert any("llm_json_unparsed" in w for w in p2["warnings"])


def test_parse_llm_answer_out_of_range_index():
    text = '{"derivation":"引用[[c:5]]越界。","conclusion":"x"}'
    parsed = parse_llm_answer(text, evidence_count=2)
    assert any("citation_index_out_of_range" in w for w in parsed["warnings"])


# ---------------------------------------------------------------------------
# 集成：answer()（真实临时库检索 + monkeypatch 假 LLM）
# ---------------------------------------------------------------------------

def test_answer_direct_tier_returns_full_struct(monkeypatch):
    _patch_llm(monkeypatch,
               '{"derivation":"由[[c:0]]直接得出：动火作业应办理作业许可证。",'
               '"conclusion":"动火作业应办理作业许可证。"}')
    data = answer("第5.2.1条", query_mode="default")
    assert data["tier"] == "direct"
    # 结构字段齐全
    for k in ("tier", "evidence", "derivation", "conclusion", "verification", "notes"):
        assert k in data
    assert 0 < len(data["evidence"]) <= 8
    # 证据全部现行
    assert all(e["legal_status"] == "effective" for e in data["evidence"])
    # 核验字段形状
    v = data["verification"]
    for k in ("is_valid", "answer_confidence", "confidence_reasons",
              "unsupported_clauses", "unverified_numbers", "modality_violations",
              "legal_element_violations"):
        assert k in v
    assert isinstance(v["confidence_reasons"], list)
    assert isinstance(v["unsupported_clauses"], list)
    # 推导含引用标记
    assert "[[c:0]]" in data["derivation"]


def test_answer_effective_exclusive_and_upcoming_note(monkeypatch):
    """跨版本 5.2.1（现行2022/即将2025/已废止2018）→ 只保留现行，notes 说明即将生效。"""
    _patch_llm(monkeypatch,
               '{"derivation":"依据[[c:0]]现行条款。","conclusion":"现行口径结论。"}')
    data = answer("第5.2.1条 动火作业 应", query_mode="default")
    # 不含 superseded 与 upcoming 条款（只现行）
    assert data["evidence"], "应至少命中现行 GB 30871-2022 5.2.1"
    stds = {e["standard_no"] for e in data["evidence"]}
    assert "GB 30871-2025" not in stds        # upcoming 不进 evidence
    assert "GB 30871-2018" not in stds        # superseded 不进 evidence
    assert "GB 30871-2022" in stds
    # notes 说明即将生效版本
    assert any("即将生效" in n for n in data["notes"])


def test_answer_synthesis_tier(monkeypatch):
    _patch_llm(monkeypatch,
               '{"derivation":"综合[[c:0]]与[[c:1]]得出。","conclusion":"综合结论。"}')
    data = answer("特殊作业 分级 应", query_mode="default")
    assert data["tier"] == "synthesis"
    assert len(data["evidence"]) >= 2
    # 综合时可能含多条（GB 30871-2022 + GB/T 50493-2019）
    assert any(e["standard_no"] == "GB 30871-2022" for e in data["evidence"])


def test_answer_reference_tier_and_verification_marks(monkeypatch):
    _patch_llm(monkeypatch,
               '{"derivation":"依据不足，未能定位直接规定。","conclusion":"无直接规定，给出参考口径。"}')
    data = answer("太阳能电站 防火 布局 无此内容", query_mode="default")
    assert data["tier"] == "reference"
    assert data["evidence"] == []
    assert data["verification"]["answer_confidence"] == "low"
    assert any("参考口径" in r or "无有效现行证据" in r
               for r in data["verification"]["confidence_reasons"])


def test_answer_verification_flags_unsupported_clause(monkeypatch):
    # LLM 的推导引用了证据之外的条款号 → typed_verifier 应拦截
    _patch_llm(monkeypatch,
               '{"derivation":"依据[[c:0]]，并按第9.9.9条补充。","conclusion":"结论。"}')
    data = answer("GB 30871-2022 第5.2.1条", query_mode="default")
    assert data["verification"]["is_valid"] is False
    assert "9.9.9" in data["verification"]["unsupported_clauses"]


def test_answer_degrades_gracefully_when_llm_unavailable(monkeypatch):
    from src.core.exceptions import LLMError
    def _boom(messages, **kw):
        raise LLMError("DEEPSEEK_API_KEY 未配置")
    monkeypatch.setattr(ks_answer, "_stream_llm", _boom)
    data = answer("GB 30871-2022 第5.2.1条", query_mode="default")
    assert "大模型不可用" in data["derivation"]
    assert data["verification"]["answer_confidence"] in ("high", "mid", "low")
    assert data["verification"]["citation_index_warnings"] == ["llm_unavailable"]


def test_build_messages_includes_system_and_c_marks():
    ev = _ev()
    msgs = build_messages("测试问题", [ev], "default")
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert "[c:0]" in msgs[1]["content"]
    assert "三段式" in msgs[0]["content"]


def test_answer_rejects_empty_query():
    with pytest.raises(ValueError):
        answer("   ", query_mode="default")


# ---------------------------------------------------------------------------
# 收藏范围（bookmarks_only / bookmarked 三态）——2026-09-10 verifier 四轮
# ---------------------------------------------------------------------------

def _enable_bookmarks(monkeypatch, keys):
    """把 user_data.bookmarked_clause_keys 钉成给定集合（不碰真实收藏表）。"""
    from src.core.storage import user_data
    monkeypatch.setattr(user_data, "bookmarked_clause_keys", lambda: set(keys))


def _break_bookmarks(monkeypatch):
    from src.core.storage import user_data
    def _boom():
        raise RuntimeError("collection unavailable")
    monkeypatch.setattr(user_data, "bookmarked_clause_keys", _boom)


def test_answer_marks_every_evidence_item_with_bookmarked(monkeypatch):
    """逐条透出 bookmarked（宿主与提示词据此判断"范围过滤是否真的生效"）。"""
    _patch_llm(monkeypatch,
               '{"derivation":"依据[[c:0]]。","conclusion":"结论。"}')
    _enable_bookmarks(monkeypatch, ["docA:5.2.1"])
    data = answer("第5.2.1条 动火作业", query_mode="default")
    assert data["evidence"], "应命中现行条款"
    # 键一定存在且是布尔（不是恒 false，也不是 undefined）
    assert all(isinstance(e["bookmarked"], bool) for e in data["evidence"])
    marked = {e["clause_number"]: e["bookmarked"] for e in data["evidence"]}
    assert marked.get("5.2.1") is True           # 已收藏
    # 未开仅收藏 → 不做过滤，收藏集外的条目照常在证据里、且标记为 False
    assert any(v is False for v in marked.values()) or len(marked) == 1


def test_answer_bookmarks_only_filters_and_says_so(monkeypatch):
    """bookmarks_only=True 且收藏集可用 → 只返回收藏条款，并在 notes 如实说明。"""
    _patch_llm(monkeypatch,
               '{"derivation":"依据[[c:0]]。","conclusion":"结论。"}')
    _enable_bookmarks(monkeypatch, ["docA:5.2.1"])
    data = answer("特殊作业 分级 应", query_mode="default",
                  params={"bookmarks_only": True})
    assert data["evidence"], "收藏集内应有命中"
    assert all(e["bookmarked"] is True for e in data["evidence"])
    assert any("仅收藏" in n and "限定" in n for n in data["notes"])


def test_answer_bookmarks_only_with_empty_collection_returns_nothing(monkeypatch):
    _patch_llm(monkeypatch,
               '{"derivation":"未能定位。","conclusion":"无。"}')
    _enable_bookmarks(monkeypatch, [])
    data = answer("特殊作业 分级 应", query_mode="default",
                  params={"bookmarks_only": True})
    assert data["evidence"] == []
    # 空收藏集是**合法的空**，不是"查询失败"——notes 不得谎报（verifier 五轮 P1）
    assert not any("查询失败" in n for n in data["notes"])
    assert any("已限定在用户收藏" in n for n in data["notes"])


def test_answer_bookmarks_only_zero_hits_is_not_a_query_failure(monkeypatch):
    """收藏集查询成功、但**检索本身 0 命中** → 必须仍然声明"已限定"，绝不能输出
    "收藏集查询失败/未能限定"（那是对用户的事实性假陈述）。
    注意触发条件是"过滤前 evidence 就是空的"——若检索有命中、只是被过滤光了，
    `and evidence` 那种写法不会暴露问题（verifier 五轮 P1 的原始复现用的是空检索）。"""
    _patch_llm(monkeypatch,
               '{"derivation":"依据不足，未能定位直接规定。","conclusion":"无直接规定。"}')
    _enable_bookmarks(monkeypatch, ["docA:5.2.1"])  # 收藏集非空
    data = answer("太阳能电站 防火 布局 无此内容", query_mode="default",
                  params={"bookmarks_only": True})
    assert data["evidence"] == [], "该查询本就不该命中任何条款"
    assert not any("查询失败" in n or "未能" in n for n in data["notes"]), data["notes"]
    assert any("已限定在用户收藏" in n for n in data["notes"]), data["notes"]


def test_answer_marks_bookmarked_unknown_when_collection_returns_none(monkeypatch):
    """查询函数返回 None（而非抛错）同样表示"未知"，不得当成空收藏集。"""
    _patch_llm(monkeypatch,
               '{"derivation":"依据[[c:0]]。","conclusion":"结论。"}')
    from src.core.storage import user_data
    monkeypatch.setattr(user_data, "bookmarked_clause_keys", lambda: None)
    data = answer("特殊作业 分级 应", query_mode="default",
                  params={"bookmarks_only": True})
    assert all(e["bookmarked"] is None for e in data["evidence"])
    assert any("未能" in n for n in data["notes"])


def test_answer_bookmarks_only_filters_before_the_evidence_cap(monkeypatch):
    """上限**只在收藏集内**生效（verifier 六轮 P1）：先 `_cap` 再过滤时，收藏集条款
    只要排在 max_evidence 之外就被丢掉 → 「仅收藏」长期返回空。"""
    _patch_llm(monkeypatch,
               '{"derivation":"依据[[c:0]]。","conclusion":"结论。"}')
    _enable_bookmarks(monkeypatch, ["docA:5.1"])
    data = answer("特殊作业 分级 应", query_mode="default",
                  params={"bookmarks_only": True, "max_evidence": 1})
    assert data["evidence"], "收藏集内的条款必须能被取到（过滤发生在截断之前）"
    assert all(e["bookmarked"] is True for e in data["evidence"])
    nums = {e["clause_number"] for e in data["evidence"]}
    assert nums == {"5.1"}, nums


def test_answer_bookmarks_only_widens_the_candidate_pool(monkeypatch):
    """仅收藏时检索候选池被放大（默认 k=8 时收藏条款几乎进不了候选）。"""
    seen = {}
    from src.core.retrieval import hybrid_engine
    real = hybrid_engine.search_with_details

    def spy(query, **kw):
        seen["top_k"] = kw.get("top_k")
        return real(query, **kw)

    monkeypatch.setattr(ks_answer, "search_with_details", spy, raising=False)
    monkeypatch.setattr(hybrid_engine, "search_with_details", spy)
    _patch_llm(monkeypatch,
               '{"derivation":"依据[[c:0]]。","conclusion":"结论。"}')
    _enable_bookmarks(monkeypatch, ["docA:5.1"])
    answer("特殊作业 分级 应", query_mode="default", params={"bookmarks_only": True})
    assert seen.get("top_k") == ks_answer.BOOKMARKS_MIN_TOP_K, seen


def test_answer_bookmarks_only_zero_hits_note_does_not_blame_the_collection(monkeypatch):
    """空结果时的措辞：不得断言"收藏集里没有相关条款"（可能只是没被检索到）。"""
    _patch_llm(monkeypatch,
               '{"derivation":"依据不足。","conclusion":"无直接规定。"}')
    _enable_bookmarks(monkeypatch, ["docZ:9.9.9"])
    data = answer("太阳能电站 防火 布局 无此内容", query_mode="default",
                  params={"bookmarks_only": True})
    assert data["evidence"] == []
    joined = " ".join(data["notes"])
    assert "收藏集内没有命中相关条款" not in joined, joined
    assert "候选池" in joined and "可能仍有" in joined, joined
    assert "全库检索结果" not in joined, joined


def test_answer_marks_bookmarked_unknown_when_collection_query_fails(monkeypatch):
    """收藏集查询失败：**不得**把"查不到"当成 False（那会让模型误报"过滤未生效"），
    flag 必须是 None，且 notes 必须明说本轮未能限定收藏集（不再静默 fail-open）。"""
    _patch_llm(monkeypatch,
               '{"derivation":"依据[[c:0]]。","conclusion":"结论。"}')
    _break_bookmarks(monkeypatch)
    data = answer("特殊作业 分级 应", query_mode="default",
                  params={"bookmarks_only": True})
    assert data["evidence"], "查询失败时按 fail-open 返回全库结果"
    assert all(e["bookmarked"] is None for e in data["evidence"])
    assert any("未能" in n and "仅收藏" in n for n in data["notes"])


def test_answer_without_bookmarks_only_still_flags(monkeypatch):
    """未开仅收藏：仍透出真值（不写 notes 的范围声明）。"""
    _patch_llm(monkeypatch,
               '{"derivation":"依据[[c:0]]。","conclusion":"结论。"}')
    _enable_bookmarks(monkeypatch, ["docA:5.2.1"])
    data = answer("第5.2.1条 动火作业", query_mode="default")
    assert all(e["bookmarked"] is not None for e in data["evidence"])
    assert not any("限定在用户收藏" in n for n in data["notes"])
