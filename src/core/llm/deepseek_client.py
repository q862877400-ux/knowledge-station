"""DeepSeek 官方 API 流式客户端（openai SDK 协议）。

零外发红线：Prompt 仅含用户问题 + 检索出的最小必要证据片段。
Key 仅从环境变量/Settings 读取；未配置时抛 LLMError，由上层降级为占位答案。
"""
from __future__ import annotations

import logging
from typing import Iterator, List

from src.core.config import get_settings
from src.core.exceptions import LLMError
from src.core.text_utils import weave_meaning_marks

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是国标与法律法规咨询助手。你必须依据给出的证据条款作答，常识性事实与常规场景假设可作补充并标注（常识）/（假设）：\n"
    "1. 每条结论后紧跟引用角标，格式 [引用:标准号-条款号]；\n"
    "2. 严禁提及证据之外的条款号；严禁改写数值、单位与义务模态词"
    "（应/宜/严禁/不得等必须原样保留强度）；\n"
    "3. 证据含例外（但书/除外）时必须一并说明；\n"
    "4. 证据不足时明确回答\"依据不足\"，不得编造。\n"
    "5. 分级表述等价：罗马数字（Ⅰ/Ⅱ/Ⅲ/Ⅳ级）即阿拉伯数字（1/2/3/4级），"
    "用户说\"2级\"就是\"Ⅱ级\"，回答时直接对应。\n"
    "6. 末尾追问：如果答案依赖用户未提供的条件（如分级A/B类法、建筑类型、火灾危险性、作业高度等），"
    "回答末尾必须用一句话以问句形式（句号结尾）引导用户补充，例如\"请补充说明是否存在客观危险因素。\"，"
    "不要用卡片或列表罗列问题。\n"
    "7. 常识可用：常见理化常识（如常见气体相对密度：硫化氢≈1.19 重于空气、氨≈0.59 轻于空气、"
    "一氧化碳与空气相近、氢气/甲烷比空气轻等）允许直接使用，标注\"（常识）\"；"
    "常识只用于定性判断方向，具体数值与安装高度以证据条款为准。\n"
    "8. 追问节制：用户已补充关键信息（如气体种类、作业场所）后不得再追问次要细节"
    "（如通风死角、局部空间等）——按常见工程场景直接作答并注明假设前提；"
    "同一轮回答末尾最多一句话追问。\n"
    "9. 问还是答（一次定夺，不要连环追问）：如果缺少会实质改变结论的关键信息，且该信息无法"
    "用常识或常见场景推断，则先只输出一行 JSON，格式为 {\"ask\":[\"问题1\",\"问题2\",\"问题3\"]}"
    "（最多 3 个问题、每个一句话、只问最关键点、一次问完）；"
    "否则必须直接作答——常见理化常识（如硫化氢≈1.19 重于空气）与常规场景假设可直接使用并注明"
    "（常识）/（假设），不得提问。输出 JSON 时不要输出任何其它内容；"
    "历史中已有追问且用户已补充信息时，不得再次追问相同或次要问题。"


)


def build_evidence_prompt(query: str, evidences: List[dict]) -> str:
    """构造最小必要证据 Prompt（R2 红线：不传全文，正文截断 800 字符，R77）。"""
    lines = [f"用户问题：{query}", "", "证据条款："]
    for i, e in enumerate(evidences, 1):
        # 2026-08-29 平均值 bar 织入：'Ci———样品i的平均值' → 'C̄i———…'（见
        # text_utils.weave_meaning_marks——画线 bar 文字层无字符，LLM 证据线
        # 不织则标准值/平均值同形不可分）
        content = weave_meaning_marks(e.get("content_text") or "")[:800]
        table = ""
        if e.get("table_md"):
            table = "\n    （附表：" + e["table_md"][:300] + "）"
        lines.append(
            f"[{i}] {e.get('standard_no')} 第{e.get('clause_number')}条"
            f"（第{e.get('page_start')}页）：{content}{table}")
    lines.append("")
    lines.append("请仅基于以上证据回答，遵守引用与模态保留规则。")
    return "\n".join(lines)


# R60 多轮对话：历史截断参数（防 Prompt 膨胀与重复计费）
HISTORY_MAX_TURNS = 4          # 最多携带最近 4 条（2 问 2 答）
HISTORY_CONTENT_MAX = 300      # 单条历史文本截断长度


def build_messages(query: str, evidences: List[dict],
                   history: List[dict] | None = None,
                   allow_clarify: bool = True) -> List[dict]:
    """组装 messages：system（含 R17 Few-shot + 追问禁令）+ 历史文本(截断) + 当前轮。

    R60 要点：history 只回传对话文本，**不重传旧证据**；
    每条截断 + 最多 4 条，控制 token 增长（省额度）。
    Task 13.4：system prompt 注入 feedback 高频纠错 Few-shot（无反馈时原样）。
    Task v5 追问死循环修复：user_turns ≥ 2 时 allow_clarify=False，
    在 system 中强制"禁止追问、基于现有信息直接作答"（硬上限，不再依赖 LLM 自觉）。
    """
    from src.core.llm.fewshot import inject_fewshot
    system = inject_fewshot(SYSTEM_PROMPT)
    if not allow_clarify:
        system += (
            "\n\n【本轮硬约束】这是多轮对话的后续轮次：禁止再向用户追问任何信息。"
            "请基于现有证据与已知信息直接给出结论；信息不足时明确说明'依据现有信息无法确定'"
            "并给出最接近的条款依据，而不是索要更多参数。")
    msgs = [{"role": "system", "content": system}]
    for turn in (history or [])[-HISTORY_MAX_TURNS:]:
        role = "user" if turn.get("role") == "user" else "assistant"
        content = (turn.get("content") or "")[:HISTORY_CONTENT_MAX]
        msgs.append({"role": role, "content": content})
    msgs.append({"role": "user",
                 "content": build_evidence_prompt(query, evidences)})
    return msgs


def stream_chat_completion(query: str, evidences: List[dict],
                           history: List[dict] | None = None,
                           max_tokens: int = 1024,
                           temperature: float = 0.1,
                           allow_clarify: bool = True) -> Iterator[str]:
    """流式生成回答片段（支持 R60 多轮历史）。未配置 Key 或调用失败时抛 LLMError。"""
    settings = get_settings()
    if not settings.llm_api_key:
        raise LLMError("DEEPSEEK_API_KEY 未配置")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.llm_api_key,
                        base_url=settings.llm_base_url)
        stream = client.chat.completions.create(
            model=settings.llm_model,
            messages=build_messages(query, evidences, history, allow_clarify),
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
    except LLMError:
        raise
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"DeepSeek 调用失败: {e}") from e


def chat_complete(system: str, user: str, max_tokens: int = 256,
                  temperature: float = 0.0) -> str:
    """通用非流式补全（结构化调用：找标 LLM 分类/释义等）。

    返回完整文本；未配 Key 或调用失败抛 LLMError，由调用方降级。
    """
    settings = get_settings()
    if not settings.llm_api_key:
        raise LLMError("DEEPSEEK_API_KEY 未配置")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.llm_api_key,
                        base_url=settings.llm_base_url)
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""
    except LLMError:
        raise
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"DeepSeek 调用失败: {e}") from e
