"""条款级体检规则（数据体检 6 标签）——**唯一所有者**。

## 为什么有这个模块
这 6 个标签原先内联在 `src/core/api/server.py` 的 `data_quality_issues` handler 里，
只服务于那一个 HTTP 端点；而 R27 入库预览（Dry-Run）需要在**尚未落库**的解析结果上跑
同一套判据。若在预览里重写一遍，就会长出第二套质量规则（反熵违规：同一条规则两个所有者，
阈值一改就不同步）。

所以抽出本模块：**纯函数、零 IO、零 DB、零 parser 依赖**，两个调用方共用同一实现。

## 覆盖面（6 标签，顺序即契约）
1. 正文含内嵌表格文本   2. 表格列数不一致   3. 表格脏单元格
4. 英文粘连             5. 页脚/下节标题泄漏 6. 正文换行残留

## 与旧实现的等价性
`clause_health()` 的判据表达式与阈值逐字符照抄自 `server.py` 内联版（含 `table_md` 先按
400 字截断再判表格类标签这一既有语义）。差异由 `tests/test_quality_rules.py` 的
差分测试（对冻结的旧实现副本）锁定；任何"顺手改进"都必须先改那个测试。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["ClauseHealth", "clause_health", "clause_health_html_to_text"]

#: 表格 html → 文本的截断长度（旧实现硬编码 400；判表格类标签时也用这个长度，
#: 这会让超长表格漏检——**已知缺陷，本期刻意不修**（修它会改变既有端点输出），
#: 见 docs/DSH_REINCARNATION.md 的入库预览台账条目。
TABLE_MD_LIMIT = 400


@dataclass(frozen=True)
class ClauseHealth:
    """一条条款的体检结论。`tags` 为空 = 未发现已知问题。"""

    tags: list[str] = field(default_factory=list)
    #: 表格正文（已按 TABLE_MD_LIMIT 截断）；调用方若还要给用户看，需自行 [:200]
    table_md: str = ""


def clause_health_html_to_text(html: str | None, limit: int = TABLE_MD_LIMIT) -> str:
    """表格 html → 紧凑纯文本（证据 prompt / table_md 用）。解码 HTML 实体 + <eq> 公式转可读。

    逐字符等价于 `server.py` 的原 `_html_to_text`。
    """
    if not html:
        return ""
    from src.core.text_utils import clean_eq_tags, html_unescape
    t = clean_eq_tags(html)
    t = re.sub(r"</t[dh]>", " | ", t)
    t = re.sub(r"</tr>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html_unescape(t)
    t = re.sub(r"[ \t\u3000]+", " ", t)
    t = re.sub(r"(?m) \| +$", "", t)  # 去掉行尾多余分隔符（避免表格多出空列）
    return re.sub(r"\n{2,}", "\n", t).strip()[:limit]


def clause_health(content_text: str, content_markdown: str | None) -> ClauseHealth:
    """对单条条款跑 6 标签判据（纯函数）。

    :param content_text: 条款正文纯文本（`clause_revision.content_text`）
    :param content_markdown: 条款表格 html（`clause_revision.content_markdown`），可为空
    """
    ct = content_text or ""
    table_md = (clause_health_html_to_text(content_markdown)
                if content_markdown else "")
    tags: list[str] = []
    if table_md:
        tokens = {c.strip() for ln in table_md.split("\n")
                  for c in ln.split("|") if c.strip()}
        lines = {re.sub(r"\s+", " ", ln.strip()) for ln in ct.split("\n") if ln.strip()}
        if tokens & lines:
            tags.append("正文含内嵌表格文本")
        counts = [len([c for c in r.split("|") if c.strip()])
                  for r in table_md.split("\n") if "|" in r]
        # 跳过首行（常为标题/合并表头），仅比较数据行列数
        data_counts = counts[1:] if len(counts) > 1 else counts
        if data_counts and max(data_counts) - min(data_counts) >= 2:
            tags.append("表格列数不一致")
        if (re.search(r"\|\s*\d{3,}\s*\|", table_md)
                or re.search(r"\|\s*(IN|NV|IVI|VI)\s*\|", table_md)):
            tags.append("表格脏单元格")
    if re.search(r"[a-z]{16,}", ct):
        tags.append("英文粘连")
    if (re.search(r"\d+\s+GB\s+[0-9—–-]+\s*$", ct)
            or re.search(r"\n\s*\d{1,2}\s+[\u4e00-\u9fa5]{4,}\s*$", ct)):
        tags.append("页脚/下节标题泄漏")
    if re.search(r"[\u4e00-\u9fa5A-Za-z0-9]\n[\u4e00-\u9fa5A-Za-z0-9]", ct):
        tags.append("正文换行残留")
    return ClauseHealth(tags=tags, table_md=table_md)
