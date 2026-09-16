# -*- coding: utf-8 -*-
"""P1a 同步「取证答案」能力 ks_answer（pure engine + plugin tool candidate）。

Product spec (docs/DSH_REINCARNATION.md §3.2/§14 + ENCYCLOPEDIA §6/§7/§11):
  取证模式强制「三段式」答案：依据区(evidence) → 推导区(derivation) → 结论区(conclusion)，
  只引用现行版 (legal_status==effective)，配套 typed_verifier 核验与置信度。

Hard rules enforced here:
  ① 只引用现行版：任何 resolve_status() 后非 effective 的条款一律不进 evidence
     （检索天然已排除 withdrawn/superseded，此处再兜底断言），即将生效(upcoming)单独进 notes。
  ② 涉「即将生效」新版 → notes 单独说明（何时施行、届时将如何改变），主答按现行口径。
  ③ tier 三态：direct(1 条实质直接命中) / synthesis(>=2 条多源综合) /
     reference(无支撑或证据置信不足 → verification 明示)。
  ④ evidence 去重、上限 8、每条约 800 字截断供 prompt，核验用全量条款文本。

Isolated-candidate discipline: 本文件不写入仓库、不改引擎、不调用真实 LLM（_stream_llm
为 monkeypatch-able seam，测试一律 mock）。合入时按 README 指引整文件放至
``src/core/llm/ks_answer.py`` 并在 ``src/core/api/server.py`` 加同步端点。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Iterator, List, Optional

from src.core.config import get_settings
from src.core.domain.models import ClauseRevisionModel
from src.core.exceptions import LLMError
from src.core.knowledge.legal_status import resolve_status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
EVIDENCE_SNIPPET_MAX = 800     # 供 prompt 的正文截断（ENCYCLOPEDIA §15.1 条 5）
EVIDENCE_TABLE_MAX = 300       # 附表格截断（对齐 build_evidence_prompt）
EVIDENCE_CAP = 8               # 证据上限（§5.1 硬规则④ / 过期影响面）

# 「仅收藏」时的最小检索候选池（verifier 六轮 P1）：检索是全库 top-k，而收藏集只是
# 其中的交集；k 太小时收藏的条款根本进不了候选。放大到 50（与 host 侧 params.top_k
# 白名单上限一致），最终证据仍由 max_evidence 封顶。
BOOKMARKS_MIN_TOP_K = 50
TITLE_CLAUSE_MAXLEN = 80       # 标题条款判定（<80 字且纯数字条款号 = 标题条款）

_TITLE_CLAUSE_NO = re.compile(r'^\d+(?:\.\d+)*$')

# 取证三段式输出的引用标记格式：[[c:i]] 指 evidence[i]
_CITE_MARK = re.compile(r'\[\[c:(\d+)\]\]')

# 取证模式 SYSTEM_PROMPT 精神对齐 ENCYCLOPEDIA §6.2 规则 1~5 + 取证三段式约束，
# 且取证模式不复用「追问」规则（规则 6/8/9 是轻模式双轨追问机制，取证答案不催问）。
FORENSIC_SYSTEM_PROMPT = (
    "你是国标与法律法规取证咨询助手，输出「三段式」取证答案。"
    "你必须仅依据下方给出的证据条款作答；常识性事实仅作定性补充并标注（常识）。\n"
    "1. 每条结论后紧跟引用标记，格式 [[c:i]]，i 为下方证据序号（从 0 开始）；\n"
    "2. 严禁提及证据之外的条款号；严禁改写数值、单位与义务模态词"
    "（应/宜/严禁/不得/必须等必须原样保留强度）；\n"
    "3. 证据含例外（但书/除外/另有规定）时必须在该处一并说明；\n"
    "4. 证据不足时明确回答\"依据不足\"，不得编造；\n"
    "5. 分级表述等价：罗马数字（Ⅰ/Ⅱ/Ⅲ/Ⅳ级）即阿拉伯数字（1/2/3/4级）；\n"
    "6. 只输出一个 JSON 对象，恰好两个字段："
    '{"derivation":"推导正文","conclusion":"一句话结论"}。'
    "derivation 内在引用证据处用 [[c:i]] 标记；不要输出 JSON 之外的任何内容（不要 markdown 代码块）。"
)

# ---------------------------------------------------------------------------
# 内部证据表示
# ---------------------------------------------------------------------------

def _clause_to_evidence(clause: ClauseRevisionModel) -> Dict[str, Any]:
    """把一个检索到的 ClauseRevisionModel 转成内部证据 dict。

    公共字段对齐 spec 的 evidence[]，另以 ``_`` 前缀携带核验/prompt 所需全量字段。
    legal_status 已用 resolve_status 惰性翻转（upcoming+实施日期已到 → effective）。
    """
    resolved = resolve_status(clause.legal_status, getattr(clause, "effective_from", None))
    full_text = clause.content_text or ""
    table_md = _html_to_text_compact(clause.content_markdown)
    return {
        # ---- 公共 evidence 字段（对外 JSON）----
        "clause_revision_id": clause.clause_revision_id,
        "doc_id": clause.doc_id,
        "standard_no": clause.standard_no,
        "clause_number": clause.clause_number,
        "title": clause.title,
        "legal_status": resolved,
        "legal_hierarchy": clause.legal_hierarchy or "GB",
        "page_start": clause.page_start,
        "snippet": full_text[:EVIDENCE_SNIPPET_MAX],
        "effective_from": getattr(clause, "effective_from", None),
        # ---- 内部字段（不进对外 evidence 序列化，供 filter/prompt/verify）----
        "_clause_key": getattr(clause, "clause_key", "") or "",
        "_full_text": full_text,
        "_table_md": table_md,
        "_knowledge_type": getattr(clause, "knowledge_type", "rule"),
        "_modality": getattr(clause, "modality", None),
        "_modality_strength": getattr(clause, "modality_strength", None),
        "_exception": getattr(clause, "exception", None),
        "_subject": getattr(clause, "subject", None),
        "_is_suspicious": bool(getattr(clause, "is_suspicious", False)),
        "_type_confidence": getattr(clause, "type_confidence", 1.0),
    }


def _html_to_text_compact(html: Optional[str], limit: int = EVIDENCE_TABLE_MAX) -> str:
    """表格 html → 紧凑纯文本（供 prompt 附表）。

    2026-09-11：改为委托 `src.core.quality.clause_health_html_to_text`（**唯一所有者**）——
    此前这里是第三份同构实现（另两份在 server.py / 质检模块）。行为等价：同一套
    实体解码 + `<eq>` 公式转换 + 空白压缩 + 行尾分隔符清理，仅默认截断长度不同。
    异常仍在此吞掉（表格解析失败不得阻塞取证答案）。
    """
    if not html:
        return ""
    try:
        from src.core.quality import clause_health_html_to_text
        t = clause_health_html_to_text(html, limit)
    except Exception:  # noqa: BLE001 - 表格解析失败不阻塞取证答案
        t = ""
    return t


def _is_effective(ev: Dict[str, Any]) -> bool:
    """硬规则①：只保留现行版。resolve_status 后仍 != 'effective' → 不得进 evidence。"""
    return ev.get("legal_status") == "effective"


def _filter_effective(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """兜底断言：剔除一切非 effective 条款（含检索漏网的 superseded/withdrawn/upcoming）。

    返回仅现行版。对剔除项打 warning 日志（保留在 dropped_counter 供验证）。
    """
    kept = []
    for ev in evidence:
        if _is_effective(ev):
            kept.append(ev)
        else:
            logger.warning(
                "ks_answer 兜底过滤: 非现行条款被移除 standard_no=%s clause=%s status=%s "
                "(resolved-by resolve_status)",
                ev.get("standard_no"), ev.get("clause_number"), ev.get("legal_status"))
    return kept


def _dedupe(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """证据去重：先按 clause_revision_id，若为空再按 (doc_id, clause_number) 兜底。"""
    out: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_keys: set[tuple[str, str]] = set()
    for ev in evidence:
        cid = ev.get("clause_revision_id")
        if cid:
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
        else:
            k = (ev.get("doc_id") or "", ev.get("clause_number") or "")
            if k in seen_keys:
                continue
            seen_keys.add(k)
        out.append(ev)
    return out


def _cap(evidence: List[Dict[str, Any]], max_n: int = EVIDENCE_CAP) -> List[Dict[str, Any]]:
    """证据上限（spec 硬规则④：上限 8）。max_n 不得 > 8。"""
    return evidence[: min(max_n, EVIDENCE_CAP)]


def _is_substantive(ev: Dict[str, Any]) -> bool:
    """判定一条证据是否为「实质」条款（区别于无实质规定的空标题条款）。

    实质 = 含义务模态词（应/宜/严禁…）或 表格/公式 或 法条型(legal) 或 例外说明，或正文较长。
    空标题（无模态词、无表格、很短、非法条）→ 视为非实质 → tier 退到 reference
    （无直接规定，给参考口径）。采用「模态词优先」而非纯长度，避免把短而实的
    「动火作业应办理作业许可证。」误判为非实质。
    """
    text = (ev.get("_full_text") or "").strip()
    if ev.get("_table_md"):
        return True
    if ev.get("_knowledge_type") == "legal":
        return True
    if ev.get("_exception"):
        return True
    if ev.get("_modality"):
        return True
    if len(text) >= TITLE_CLAUSE_MAXLEN:   # 长短正文才算实质
        return True
    return False


def _decide_tier(
    evidence: List[Dict[str, Any]],
    retrieval_meta: Dict[str, Any],
) -> str:
    """tier 三态判定（确定性启发式，取证口径）：

    - reference：无支撑（检索 0 结果 / 全被滤除）或唯一证据为空标题（置信不足无直接规定）
    - direct   ：恰 1 条实质证据直接命中
    - synthesis：>=2 条证据（多条款/多源综合）
    检索降级（rerank_offline / vector_offline 等）只影响 confidence_reasons，不改 tier 主体。
    """
    n = len(evidence)
    if n == 0:
        return "reference"
    if n == 1 and not _is_substantive(evidence[0]):
        return "reference"
    if n == 1:
        return "direct"
    return "synthesis"


# ---------------------------------------------------------------------------
# Prompt 构造（对齐 SYSTEM_PROMPT 1~5 精神 + 三段式输出约束）
# ---------------------------------------------------------------------------

def _build_evidence_prompt(query: str, evidence: List[Dict[str, Any]]) -> str:
    """组装用户侧证据 Prompt：每条约 800 字截断 + 附表 300 字，引用标记 [c:i]。"""
    lines = [f"用户问题：{query}", "", "证据条款："]
    for i, ev in enumerate(evidence):
        content = ev.get("snippet") or (ev.get("_full_text") or "")[:EVIDENCE_SNIPPET_MAX]
        table = ""
        if ev.get("_table_md"):
            table = "\n    （附表：" + ev["_table_md"][:EVIDENCE_TABLE_MAX] + "）"
        lines.append(
            f"[c:{i}] {ev.get('standard_no')} 第{ev.get('clause_number')}条"
            f"（第{ev.get('page_start')}页，效力={ev.get('legal_status')}）：{content}{table}")
    lines.append("")
    lines.append("请仅基于以上证据给出三段式取证答案（JSON），引用处用 [[c:i]] 标记。")
    return "\n".join(lines)


def build_messages(query: str, evidence: List[Dict[str, Any]],
                   query_mode: str = "default") -> List[Dict[str, str]]:
    """组装 messages。query_mode 仅影响提示措辞（guess 强制作答；这里取证档位不催问）。"""
    system = FORENSIC_SYSTEM_PROMPT
    if query_mode == "guess":
        system += "\n（用户档位 guess：信息疑缺也请先给最接近的结论，并标注（假设）。）"
    elif query_mode == "quick":
        system += "\n（用户档位 quick：除非证据完全缺失，否则直接作答。）"
    return [{"role": "system", "content": system},
            {"role": "user", "content": _build_evidence_prompt(query, evidence)}]


# ---------------------------------------------------------------------------
# LLM 流式 seam（monkeypatch-able；复用 deepseek_client 的客户端配置哲学）
# ---------------------------------------------------------------------------

def _stream_llm(messages: List[Dict[str, str]],
                max_tokens: int = 1200,
                temperature: float = 0.1) -> Iterator[str]:
    """流式生成文本片段。未配置 Key / 失败抛 LLMError（由 answer() 降级）。

    测试用 monkeypatch 本函数（或 deepseek_client.stream_chat_completion）为假生成器即可，
    零真实 LLM 消耗。
    """
    settings = get_settings()
    if not settings.llm_api_key:
        raise LLMError("DEEPSEEK_API_KEY 未配置")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.llm_api_key,
                        base_url=settings.llm_base_url)
        stream = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,  # type: ignore[arg-type]  # openai SDK messages TypedDict 形参窄于 list[dict]（运行时结构等价）
            max_tokens=max_tokens, temperature=temperature, stream=True)
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None  # type: ignore[union-attr]  # SDK 重载联合含 tuple，stream=True 恒 ChatCompletionChunk
            if delta and delta.content:
                yield delta.content
    except LLMError:
        raise
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"DeepSeek 取证调用失败: {e}") from e


def _collect_stream(gen: Iterator[str]) -> str:
    """把生成器拼成完整文本（同步端点用；容忍流式为空）。"""
    return "".join(gen) if gen else ""


# ---------------------------------------------------------------------------
# LLM 输出解析（容忍 JSON / 正文混合 / 代码块 / 三段落）
# ---------------------------------------------------------------------------

def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


def parse_llm_answer(text: str, evidence_count: int) -> Dict[str, Any]:
    """解析 LLM 输出为 {derivation, conclusion} + 校验 warnings。

    容错顺序：
      1) 剥代码围栏；
      2) 尝试整体 json.loads（严格两个字段证明）；
      3) 从文本中截取首个 '{'..末个 '}' 再 json.loads；
      4) 按 [推导]/[结论] 或 依据/推导/结论 标题切分；
      5) 兜底：全文作为 derivation，conclusion 置空。
    同时校验 [[c:i]] 标记序号是否越界（越界 → citation_warning）。
    """
    text = text or ""
    body = _strip_code_fences(text)
    derivation, conclusion = "", ""
    warnings: List[str] = []

    parsed_ok = False
    candidates = []
    try:
        candidates.append(json.loads(body))
    except Exception:
        pass
    # 截取 JSON 子串（容忍正文包裹 / markdown 前后缀）
    m = re.search(r"\{.*\}", body, re.S)
    if m:
        try:
            candidates.append(json.loads(m.group(0)))
        except Exception:
            pass
    for obj in candidates:
        if isinstance(obj, dict) and ("derivation" in obj or "conclusion" in obj):
            derivation = str(obj.get("derivation", "") or "").strip()
            conclusion = str(obj.get("conclusion", "") or "").strip()
            parsed_ok = True
            break

    if not parsed_ok:
        # 标题切分兜底：优先 [推导]/[结论] 中文方括号，其次 依据/推导/结论 标题
        sec = re.split(r"[\[\u3010]?(推导|结论|依据)[\]\u3011]?[:：\s]*", body, maxsplit=3)
        if len(sec) >= 3:
            derivation = (sec[1].strip() if sec[0].strip() == "" else body)
            # 简单处理：把剩余按 结论 划分
            parts = re.split(r"[\[\u3010]?结论[\]\u3011]?[:：\s]*", body, maxsplit=1)
            if len(parts) == 2:
                derivation = parts[0]
                conclusion = parts[1].strip()
            else:
                derivation = body
                conclusion = ""
        else:
            derivation = body
            conclusion = ""
        warnings.append("llm_json_unparsed: 按正文/标题兜底解析")

    # 越界引用校验
    idxs = sorted({int(x) for x in _CITE_MARK.findall(derivation or "")})
    for i in idxs:
        if i < 0 or i >= evidence_count:
            warnings.append(f"citation_index_out_of_range: [[c:{i}]] 越界 (evidence_count={evidence_count})")
    if parsed_ok and idxs and not _CITE_MARK.search(derivation or ""):
        warnings.append("llm_json_no_citation_marker: derivation 未出现 [[c:i]] 引用标记")

    return {"derivation": derivation, "conclusion": conclusion, "warnings": warnings}


# ---------------------------------------------------------------------------
# verifier 封装（核验用全量条款文本，§15.3）
# ---------------------------------------------------------------------------

def _full_evidence_for_verify(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """构造 typed_verifier 期望的 evidence_clauses（content_text 用全量，不截断）。"""
    return [{
        "clause_revision_id": ev.get("clause_revision_id"),
        "clause_number": ev.get("clause_number"),
        "standard_no": ev.get("standard_no"),
        "knowledge_type": ev.get("_knowledge_type") or "rule",
        "modality": ev.get("_modality"),
        "content_text": ev.get("_full_text") or "",
        "exception": ev.get("_exception"),
        "subject": ev.get("_subject"),
    } for ev in evidence]


def _answer_confidence(verification, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """R24 答案层置信度分级（high/mid/low），镜像 server._answer_confidence 语义。

    无有效现行证据（tier=reference）→ 一律 low，与「取证答案需明示置信不足」呼应；
    核验未通过 → low；证据含存疑/低可信 → mid；否则 high。
    """
    reasons: List[str] = []
    if not evidence:
        reasons.append("无有效现行证据支撑（tier=reference）")
        return {"level": "low", "reasons": reasons}
    if not verification.is_valid:
        reasons.append("核验拦截项未清零")
        return {"level": "low", "reasons": reasons}
    low_conf = [ev.get("clause_number") for ev in evidence
                if ev.get("_is_suspicious") or (ev.get("_type_confidence") or 1) < 0.85]
    if low_conf:
        reasons.append(f"证据存疑/低可信: {'、'.join(str(x) for x in low_conf[:4])}")
        return {"level": "mid", "reasons": reasons}
    reasons.append("核验通过且证据高可信")
    return {"level": "high", "reasons": reasons}


def _assemble_verification(derivation: str, conclusion: str,
                           evidence: List[Dict[str, Any]],
                           citation_warnings: List[str]) -> Dict[str, Any]:
    """跑 typed_verifier 并组装 verification 字段。core output = derivation+conclusion。"""
    from src.core.verification.typed_verifier import verify_llm_output
    full = _full_evidence_for_verify(evidence)
    combined = f"{derivation}\n{conclusion}"
    v = verify_llm_output(combined, full)
    conf = _answer_confidence(v, evidence)
    reasons = list(conf["reasons"])
    reasons.extend(citation_warnings)
    if not evidence:
        reasons.append("无有效现行证据支撑，以下为参考口径")
    return {
        "is_valid": v.is_valid,
        "answer_confidence": conf["level"],
        "confidence_reasons": reasons,
        "unsupported_clauses": list(v.unsupported_clauses),
        # 2026-09-16：每条"证据外条款号"的可操作说明（属于哪部标准/是检索未召回
        # 还是模型越界）。`unsupported_clauses` 保持原样以兼容既有消费方。
        "unsupported_context": list(v.unsupported_context),
        "unverified_numbers": v.unverified_numbers,
        "modality_violations": [x.model_dump() for x in v.modality_violations],
        "legal_element_violations": v.legal_element_violations,
        "citation_index_warnings": citation_warnings,
    }


# ---------------------------------------------------------------------------
# 即将生效版本提示（硬规则②）
# ---------------------------------------------------------------------------

def _upcoming_notes(evidence: List[Dict[str, Any]]) -> List[str]:
    """对 evidence 中各标准（取其基准确则无年份部分），查 doc_meta 是否存在即将生效(upcoming)
    的新版本 → notes 说明何时施行。只读查询，基于标准号基名（去年份后缀）比对。"""
    base_to_ev: Dict[str, List[Dict[str, Any]]] = {}
    for ev in evidence:
        no = ev.get("standard_no") or ""
        base = re.sub(r"\s*[-–—]\s*\d{4}$", "", no).strip()
        base_to_ev.setdefault(base, []).append(ev)
    if not base_to_ev:
        return []
    notes: List[str] = []
    try:
        from src.core.storage.sqlite_db import get_db_connection
        conn = get_db_connection()
        for base, evs in base_to_ev.items():
            rows = conn.execute(
                "SELECT standard_no, standard_name, effective_from, superseded_by"
                " FROM doc_meta WHERE legal_status='upcoming'").fetchall()
            for r in rows:
                r_no = r["standard_no"] or ""
                r_base = re.sub(r"\s*[-–—]\s*\d{4}$", "", r_no).strip()
                if r_base == base:
                    when = r["effective_from"] or "尚未公布"
                    notes.append(
                        f"【即将生效】{r_no}（{r['standard_name'] or ''}）将于 {when} 施行，"
                        f"届时将更新/取代现行 {evs[0]['standard_no']} 的相关要求；"
                        "本答案按现行版本口径给出。")
    except Exception as e:  # noqa: BLE001
        logger.warning("ks_answer 即将生效版本查询失败: %s", e)
    return notes


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def answer(query: str,
           params: Optional[Dict[str, Any]] = None,
           query_mode: Optional[str] = None) -> Dict[str, Any]:
    """同步取证答案主体。

    Args:
        query: 用户问题。
        params: 可选; 支持 top_k / channels / include_superseded / rerank / history /
              bookmarks_only / answer_scope / max_evidence / folder_id（夹内提问）。
        query_mode: thorough|default|quick|guess，缺省 'default'。

    Returns:
        三段式取证答案 dict（结构见模块 docstring）。LLM 不可用时降级为结构化占位，
        不抛业务异常（仅参数错误类异常上抛）。
    """
    if not query or not str(query).strip():
        raise ValueError("query 不能为空")
    query = str(query).strip()
    mode = query_mode or "default"
    params = params or {}

    top_k = int(params.get("top_k", 8))
    channels = params.get("channels")
    include_superseded = bool(params.get("include_superseded", False))
    rerank = bool(params.get("rerank", False))
    history = params.get("history") or []
    bookmarks_only = bool(params.get("bookmarks_only", False))
    folder_id = params.get("folder_id") or None
    max_evidence = int(params.get("max_evidence", EVIDENCE_CAP))
    # 范围过滤（仅收藏 / 收藏夹）候选池放大：默认 k=8 时范围内那几条几乎不可能进前 8 →
    # 范围提问会长期返回空（verifier 六轮 P1）。放大的是**候选**，最终证据仍受
    # max_evidence 约束。
    if bookmarks_only or folder_id is not None:
        top_k = max(top_k, BOOKMARKS_MIN_TOP_K)

    # ---- 查询理解（复用引擎现有函数）----
    from src.core.query import understanding as qu
    from src.core.knowledge.alias_extract import expand_with_alias
    from src.core.retrieval.hybrid_engine import (
        search_with_details, expand_query_with_history)

    declared_slots, clean_query = qu.parse_declared(query)
    theme0 = qu.detect_theme(clean_query)
    intent = qu.classify_intent(clean_query)
    search_query_raw = clean_query or query

    refined = qu.refine_search_query(search_query_raw, intent, theme0)
    try:
        # R48 别名 + R9 追问并入原问题；alias_store 为辅助增强表——缺失/异常不阻塞取证主链
        search_query = expand_with_alias(expand_query_with_history(refined, history))
    except Exception as e:  # noqa: BLE001
        logger.warning("ks_answer 别名扩展降级（不阻塞）: %s", e)
        search_query = expand_query_with_history(refined, history)

    out = search_with_details(search_query, top_k=top_k, channels=channels,
                              include_superseded=include_superseded, rerank=rerank)

    # 证据链扩展（R5a）→ 检索结果 + 扩展项合并
    raw: List[ClauseRevisionModel] = list(out.get("results") or [])
    seen_ids = {c.clause_revision_id for c in raw}
    for _ex in (out.get("expanded") or []):
        _cl = _ex.get("clause")
        if _cl is not None and _cl.clause_revision_id not in seen_ids:
            raw.append(_cl)
            seen_ids.add(_cl.clause_revision_id)

    # 条件过滤 + 效力置顶（检索语义，直接调引擎现有函数）
    filtered = qu.apply_condition_filter(raw,
                                         {**declared_slots, **qu.extract_slots(clean_query, theme=theme0)})
    ranked = qu.rank_with_hierarchy(filtered)

    # 标题条款聚合子条款（8.1 → 8.1.1~，P1 保证拿到内容条款）
    ranked = _expand_title_clauses(ranked)

    # ---- 组装证据：现行 + 去重 → **先按收藏集过滤** → 再截断 ----
    # 顺序很重要（verifier 六轮 P1）：若先 `_cap` 再过滤，上限会在**全库**候选上生效，
    # 收藏集里的条款只要排在 max_evidence 之外就被丢掉，于是「仅收藏」长期返回空、
    # 还把锅甩给用户的收藏集。正确顺序 = 上限只在收藏集内生效。
    evidence = [_clause_to_evidence(c) for c in ranked]
    evidence = _filter_effective(evidence)
    evidence = _dedupe(evidence)

    # 检索元数据（供 tier / confidence）
    retr_meta = {
        "result_count": len(out.get("results") or []),
        "expanded_count": len(out.get("expanded") or []),
        "vector_engine": (out.get("debug") or {}).get("vector_engine", "unknown"),
        "rerank": (out.get("debug") or {}).get("rerank", {}),
    }

    # 仅收藏过滤（bookmarks_only）+ 逐条收藏标记。
    # 收藏标记的语义（2026-09-10，verifier 四轮）：**宿主/模型用它判断"范围过滤是否真的
    # 生效"**，所以三种取值必须能被区分——True/False 是查到的真值，None 表示"收藏集查询
    # 失败、本项未知"，绝不能把"查不到"当成 False（那会让模型误报"过滤未生效"）。
    bm: Optional[set] = None
    try:
        from src.core.storage import user_data
        _keys = user_data.bookmarked_clause_keys()
        # 显式区分"返回 None"（未知）与"返回空集"（收藏集确实是空的）：前者是查询失败，
        # 后者是合法的空收藏集。
        bm = None if _keys is None else set(_keys)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ks_answer: 收藏集查询失败，bookmarked 标记为未知：%s", exc)
    # 过滤是否真的执行，真值只有一个：收藏集**查到了**（bm is not None）。
    # 注意不能用 `and evidence`——那会把"收藏集里没有这条（0 命中）"误判成"查询失败"，
    # 从而在 notes 里对用户谎报过滤失败（verifier 五轮 P1）。
    bookmarks_filter_applied = False
    candidate_count_before_filter = len(evidence)
    if bookmarks_only and bm is not None:
        evidence = [e for e in evidence if e.get("_clause_key", "") in bm]
        bookmarks_filter_applied = True
    # ---- 夹内提问过滤（folder_id）：与 bookmarks_only 同链同序 ----
    # 并集语义：夹内标准级收藏 → doc_ids（整本标准的条款都算）；
    # 夹内条款级收藏 → clause_keys（仅那几条）。证据按 (doc_id ∈ doc_ids) ∪
    # (clause_key ∈ clause_keys) 判定。folder_scope 查询失败/夹不存在 → 过滤**不执行**，
    # notes 如实降级（绝不静默放全库，绝不谎报已限定）。
    folder_scope_applied = False
    folder_name: Optional[str] = None
    folder_found = True
    if folder_id is not None:
        try:
            from src.core.storage import user_data as _ud
            _scope = _ud.folder_scope(folder_id)
            if _scope is None:
                # 收藏夹不存在（被删/会话残留 id）→ 如实标记，不得静默全库
                folder_found = False
                folder_scope_applied = False
            else:
                folder_name = _scope["folder_name"]
                _doc_ids = _scope["doc_ids"]
                _ckeys = _scope["clause_keys"]
                evidence = [e for e in evidence
                            if e.get("doc_id", "") in _doc_ids
                            or e.get("_clause_key", "") in _ckeys]
                folder_scope_applied = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("ks_answer: 收藏夹范围查询失败: %s", exc)
            folder_scope_applied = False
            folder_found = False  # 查询失败同样视为"未能限定"，不是合法空夹
    # 截断放在过滤之后（且只在范围内生效）
    evidence = _cap(evidence, max_evidence)
    for _ev in evidence:
        _ev["bookmarked"] = (_ev.get("_clause_key", "") in bm) if bm is not None else None

    tier = _decide_tier(evidence, retr_meta)

    # ---- prompt + LLM（monkeypatch-able）----
    messages = build_messages(query, evidence, mode)
    llm_error: Optional[str] = None
    raw_text = ""
    try:
        gen = _stream_llm(messages)
        raw_text = _collect_stream(gen)
    except LLMError as e:
        llm_error = str(e)
    except Exception as e:  # noqa: BLE001
        llm_error = f"LLM 调用异常: {e}"

    if raw_text.strip():
        parsed = parse_llm_answer(raw_text, len(evidence))
        derivation = parsed["derivation"]
        conclusion = parsed["conclusion"]
        cite_warnings = parsed["warnings"]
    else:
        # LLM 不可用：结构化降级（诚实，不假装推理）
        derivation = (
            f"大模型不可用（{llm_error or '无输出'}），无法生成推理正文。"
            + ("以下仅为证据列示，未形成三段式推理。" if not evidence else
               "以下依据检索到的现行条款列示证据，未形成三段式推理。")
        )
        conclusion = "取证推导因大模型不可用未生成，请仅参考证据区列示的现行条款。"
        cite_warnings = ["llm_unavailable"]

    # ---- 核验（全量条款文本）+ 置信度 ----
    verification = _assemble_verification(derivation, conclusion, evidence, cite_warnings)

    # tier==reference 时 verification 明示（spec 硬规则③）
    if tier == "reference":
        verification["confidence_reasons"].append(
            f"tier=reference: 无直接现行规定/证据置信不足（reason: {retr_meta.get('result_count')} 检索)")

    notes = _upcoming_notes(evidence)
    # 仅收藏：把"过滤到底有没有生效"如实写进 notes（fail-open 不再静默——verifier 四轮）
    if bookmarks_only:
        if bookmarks_filter_applied:
            # 措辞纪律（verifier 六轮 P1）：**绝不断言"收藏集里没有相关条款"**——我们只知道
            # "本轮候选池（过滤前 N 条）里没有收藏集条款"，收藏集内可能有排在候选池之外、
            # 相关性更低的条款。也不能说"返回的是全库检索结果"（本轮证据已限定在收藏集内）。
            notes.append(
                f"【仅收藏】本次检索已限定在用户收藏的条款内（收藏集 {len(bm or ())} 条）；"
                + (f"候选池（过滤前 {candidate_count_before_filter} 条）内没有收藏集里的条款，"
                   "收藏集内可能仍有相关条款（未被检索到）。" if not evidence else ""))
        else:
            notes.append(
                "【仅收藏】收藏集查询失败，本轮**未能**限定在收藏集内；"
                "结论不得声称已限定收藏集。")
    # 夹内提问：同样把"范围过滤到底有没有生效"如实写进 notes
    if folder_id is not None:
        if folder_scope_applied:
            notes.append(
                f"【收藏夹】本次检索已限定在收藏夹「{folder_name}」的内容内"
                "（夹内标准级收藏按整本标准计，条款级收藏按单条计）；"
                + (f"候选池（过滤前 {candidate_count_before_filter} 条）内没有该收藏夹的条款，"
                   "夹内可能仍有相关条款（未被检索到）。" if not evidence else ""))
        else:
            reason = "收藏夹不存在或已被删除" if not folder_found else "收藏夹范围查询失败"
            notes.append(
                f"【收藏夹】{reason}，本轮**未能**限定在收藏夹内；"
                "结论不得声称已限定收藏夹范围。")

    return {
        "tier": tier,
        "evidence": [
            {k: v for k, v in ev.items() if not k.startswith("_")}
            for ev in evidence
        ],
        "derivation": derivation,
        "conclusion": conclusion,
        "verification": verification,
        "notes": notes,
        # 内部调试/审计信息（供已接入的 debug_dump / 前端隐去）
        "_meta": {
            "query": query, "search_query": search_query,
            "intent": intent, "theme": theme0, "tier_rule": tier,
            "evidence_total": len(evidence), "retrieval": retr_meta,
            "llm_error": llm_error, "llm_raw_length": len(raw_text),
            "cite_warnings": cite_warnings,
        },
    }


# ---------------------------------------------------------------------------
# 标题条款子条款聚合（与 server._expand_title_clauses 同语义，但可直接被检索侧复用）
# ---------------------------------------------------------------------------

def _expand_title_clauses(evidences: list) -> list:
    """命中纯数字标题条款（内容 <80 字）自动附带其子条款（如 8.1 → 8.1.1~8.1.3），
    证据上限 8（ENCYCLOPEDIA §5.1）。"""
    import re as _re
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    out: list = []
    seen: set[str] = set()
    for e in evidences:
        if e.clause_revision_id in seen:
            continue
        seen.add(e.clause_revision_id)
        out.append(e)
        no = e.clause_number or ""
        # 2026-09-13 附录细分配套：门控放宽接纳附录字母章号（E.1/E.5.2）——
        # 此前 fullmatch 纯数字把附录子条款头挡在聚合外（附录细分红利白切）。
        is_title = bool(_re.fullmatch(r'[0-9A-Z]+(?:[.][0-9A-Z]+)*', no)) \
            and len(e.content_text or "") < TITLE_CLAUSE_MAXLEN
        if is_title:
            try:
                subs = conn.execute(
                    "SELECT clause_revision_id FROM clause_revision"
                    " WHERE doc_id=? AND clause_number LIKE ? ORDER BY rowid LIMIT 4",
                    (e.doc_id, no + ".%")).fetchall()
            except Exception:  # noqa: BLE001
                subs = []
            from src.core.storage.clause_repo import fetch_full_clause
            for s in subs:
                if s["clause_revision_id"] in seen:
                    continue
                seen.add(s["clause_revision_id"])
                sub = fetch_full_clause(conn, s["clause_revision_id"])
                if sub is not None:
                    out.append(sub)
    return out[:8]


# 便于被插件/其它模块 import 的统一入口
__all__ = [
    "answer", "build_messages", "parse_llm_answer", "_decide_tier",
    "_filter_effective", "_dedupe", "_cap", "_is_effective", "EVIDENCE_CAP",
]
