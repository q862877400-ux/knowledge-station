# -*- coding: utf-8 -*-
"""研究/调研报告导出（Phase D 第一步，2026-09-17）。

## 为什么需要它（这一段补的是什么）
到 §10.35 为止，"参考资料平面"已经能把材料**收进来、评审、按承重能力分组**，
但**产出物**这一侧还只有"问答依据清单"（`export_qa_citations_docx`）与"审查报告"——
都不包含"这一轮到底用了哪些参考资料、它们的两个轴是什么、还有哪些没批准"。
业主的原始要求是"经用户评审确认参考资料可用后再做**分析/产出**（报告、PPT）"，
所以本模块就是那份**产出物**：一份自包含的研究报告。

## 三条纪律
1. **分组不另写一份**：依据一节直接用 `materials.authority.assemble_evidence()` +
   `render_evidence()`（承重分组、两个轴、`[[m:i]]` 编号都只有一个所有者）。
   本模块只负责"排版成交付物"。
2. **引用要可核**：结论里的 `[[m:i]]` 会被**逐条校验**——指向不存在的材料、
   或指向**仅线索/不可用**的材料，都会进 `warnings`（**绝不静默放过**）。
   `[[c:i]]`（法条）在本次导出里**无法校验**（需要问答上下文的证据集），
   如实计成 `unchecked_law_refs`，并在报告里写明。
3. **不假装完整**：未批准材料**如实列出**；"没有命中"与"项目不存在"与"载入失败"
   是三种不同的说法（照 `assemble_evidence` 的 notes，不合并）。

## 依赖
**零新增依赖**：Markdown 与 HTML 都从**同一份结构化文档**渲染（不引 markdown 库、
不做 MD→HTML 转换），HTML 侧一律 `html.escape`。方案 §8 说 PPT 要单独立项、
退路是"先出 Markdown/HTML"——本模块就是那条退路，**能立刻交付**。
"""
from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.materials import authority
from src.core.materials import track_l as tl
from src.core.storage import material_repo as mr

#: 引用标记：`[[m:0]]` 是材料、`[[c:2]]` 是法条（与提示词里的两套编号一致）。
_RE_MATERIAL_REF = re.compile(r"\[\[m:\s*(-?\d+)\s*\]\]")
_RE_CLAUSE_REF = re.compile(r"\[\[c:\s*(-?\d+)\s*\]\]")

#: 报告中"只列前 N 条"的上限（避免一份报告把整库抄进去）。
LIST_CAP = 200


def _exports_dir() -> Path:
    from src.core.config import get_settings
    d = get_settings().data_dir / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name)[:60] or "report"


def _material_line(m: dict[str, Any]) -> str:
    """参考**材料**条目的一行说明（带两个轴——合成一个"可信度"必错）。"""
    role = m.get("task_role") or "未声明效力"
    role_label = {"criterion": "本任务准则", "reference": "仅作参考"}.get(role, role)
    bits = [f"{m.get('title') or '(无题)'}",
            f"[{m.get('source_tier') or '?'}·{m.get('tier_label') or ''} / {role_label}]",
            f"评审={m.get('review_status')}"]
    if m.get("url"):
        bits.append(str(m["url"]))
    if m.get("doc_id"):
        bits.append(f"法条={m['doc_id']}")
    return "，".join(bits)


def _check_citations(text: str, assembled: dict[str, Any]) -> dict[str, Any]:
    """校验结论里的引用标记（**本函数是唯一判据**）。

    `[[m:i]]` 的 `i` 由 `authority.assemble_evidence()` 按 `GROUP_ORDER` 分配，
    所以"这份材料在第几组"决定了它**能不能承重**：
    - 编号不存在 ⇒ `unknown`（引用了一个不在本次依据里的东西）；
    - 编号落在 `leads_only`/`excluded` ⇒ `not_load_bearing`（**引用了不该承重的东西**）。
    """
    index_to_group: dict[int, str] = {}
    for key, title in authority.GROUP_ORDER:
        for h in assembled.get(key, []):
            if isinstance(h.get("index"), int):
                index_to_group[int(h["index"])] = key
    unknown: list[int] = []
    not_load_bearing: list[dict[str, Any]] = []
    for raw in _RE_MATERIAL_REF.findall(text or ""):
        idx = int(raw)
        group = index_to_group.get(idx)
        if group is None:
            unknown.append(idx)
        elif group in ("leads_only", "excluded"):
            not_load_bearing.append({"index": idx, "group": group})
    return {
        "material_refs": sorted({int(x) for x in _RE_MATERIAL_REF.findall(text or "")}),
        "unknown": sorted(set(unknown)),
        "not_load_bearing": not_load_bearing,
        # ⚠ 法条引用**本次无法校验**（要问答上下文的证据集与页码）——如实计数，不假装查过
        "unchecked_law_refs": sorted({int(x) for x in _RE_CLAUSE_REF.findall(text or "")}),
    }


def build_research_report(project_id: str, *, title: str | None = None,
                          query: str | None = None,
                          conclusion_md: str | None = None,
                          limit: int = 8) -> dict[str, Any]:
    """组装研究报告（**不写文件**）。返回 `{title, markdown, html, citations, warnings, counts}`。

    Args:
        project_id: 参考资料项目（`prj_…`）。
        title: 报告标题；不给则用项目名。
        query: 本次研究的问题。给了就按它检索**已批准**材料并分组；不给就只列清单。
        conclusion_md: 结论正文（由调用方/模型给）。里面的 `[[m:i]]` 会被校验。
        limit: 检索命中上限（交给 `assemble_evidence`）。
    """
    project = mr.get_project(project_id)
    if project is None:
        raise ValueError(f"report: 项目不存在: {project_id}")
    name = (title or "").strip() or str(project.get("name") or project_id)

    approved = mr.list_materials(project_id, review_status="approved")
    pending = mr.list_materials(project_id, review_status="pending")
    rejected = mr.list_materials(project_id, review_status="rejected")

    assembled: dict[str, Any] | None = None
    if (query or "").strip():
        assembled = authority.assemble_evidence(project_id, str(query).strip(), limit=limit)

    warnings: list[str] = []
    citations: dict[str, Any] = {"material_refs": [], "unknown": [],
                                 "not_load_bearing": [], "unchecked_law_refs": []}
    conclusion = str(conclusion_md or "").strip()
    if conclusion and assembled is not None:
        citations = _check_citations(conclusion, assembled)
        if citations["unknown"]:
            warnings.append("结论引用了**本次依据里不存在**的材料编号："
                            + "、".join(f"[[m:{i}]]" for i in citations["unknown"]))
        for bad in citations["not_load_bearing"]:
            warnings.append(f"结论引用了[[m:{bad['index']}]]，但它在 **{bad['group']}** 组"
                            "（仅线索/不可用）——**不得**用它承重")
    elif conclusion:
        still = sorted({int(x) for x in _RE_MATERIAL_REF.findall(conclusion)})
        if still:
            citations["unchecked_law_refs"] = sorted(
                {int(x) for x in _RE_CLAUSE_REF.findall(conclusion)})
            warnings.append("这次没有给 `query`，所以**无法校验**结论里的 "
                            f"{len(still)} 个 `[[m:i]]` 引用（没有依据集可比对）")

    # ---- 组装成结构化文档（Markdown 与 HTML 从**同一份**渲染，不引 markdown 库）----
    doc: list[tuple[str, Any]] = []
    doc.append(("h1", name))
    doc.append(("p", f"生成时间：{datetime.now():%Y-%m-%d %H:%M}（本地生成，未外发）"))
    doc.append(("p", f"参考资料项目：{project.get('name') or ''}（`{project_id}`）；"
                     f"已批准 {len(approved)} 份 / 待评审 {len(pending)} 份 / "
                     f"已拒绝 {len(rejected)} 份"))
    if project.get("authority_policy"):
        doc.append(("p", f"项目权威策略：{project['authority_policy']}"))
    if (query or "").strip():
        doc.append(("h2", "一、研究问题"))
        doc.append(("p", str(query).strip()))
    if conclusion:
        doc.append(("h2", "二、结论"))
        doc.append(("p", conclusion))
    if assembled is not None:
        doc.append(("h2", "三、依据（按**承重能力**分组；每条的编号就是 `[[m:i]]`）"))
        rendered = authority.render_evidence(assembled)
        doc.append(("pre", rendered) if rendered.strip() else ("p", "（没有命中任何材料）"))
        if assembled.get("notes"):
            doc.append(("h3", "说明"))
            doc.append(("ul", [str(x) for x in assembled["notes"]]))
    doc.append(("h2", "四、已批准参考资料清单"))
    if approved:
        doc.append(("ul", [_material_line(m) for m in approved[:LIST_CAP]]))
        if len(approved) > LIST_CAP:
            doc.append(("p", f"（只列前 {LIST_CAP} 条，共 {len(approved)} 条）"))
    else:
        doc.append(("p", "（**没有已批准的材料**——本报告的结论不应引用任何材料）"))
    doc.append(("h2", "五、尚未批准的材料（**不会进入任何结论**）"))
    if pending:
        doc.append(("ul", [_material_line(m) for m in pending[:LIST_CAP]]))
        doc.append(("p", "这些材料尚未评审；批准与否由**用户**判断（硬门）。"))
    else:
        doc.append(("p", "（没有待评审材料）"))
    if rejected:
        doc.append(("h3", "已拒绝（留痕）"))
        doc.append(("ul", [_material_line(m) for m in rejected[:LIST_CAP]]))
    doc.append(("h2", "六、已知限制（这份报告**不**保证什么）"))
    limits = [
        "材料来自**用户上传或采集**，不是官方原件；效力判据以库内法条链为准。",
        "两个轴**分开看**：轴 A 来源可信度（T0~T4）决定能不能承重，轴 B 任务内效力决定它在本任务里说话的分量。",
        "**仅线索**（T3 未互证）与**不可用**（T4）的材料不得单独支撑结论。",
    ]
    if citations["unchecked_law_refs"] or citations["unknown"]:
        limits.append("本报告里的引用标记**未经引擎逐条核验**（见上面的警告）。")
    limits.append("报告只在**本机**生成与保存（不外发）。")
    doc.append(("ul", limits))

    return {
        "title": name,
        "query": (query or None),
        "markdown": _to_markdown(doc),
        "html": _to_html(doc, title=name),
        "citations": citations,
        "warnings": warnings,
        "counts": {"approved": len(approved), "pending": len(pending),
                   "rejected": len(rejected)},
    }


def write_research_report(project_id: str, *, title: str | None = None,
                          query: str | None = None,
                          conclusion_md: str | None = None,
                          limit: int = 8) -> dict[str, Any]:
    """组装并**落盘**（`<exports>/研究报告-<安全名>-<时间戳>.md` + `.html`）。"""
    out = build_research_report(project_id, title=title, query=query,
                               conclusion_md=conclusion_md, limit=limit)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"研究报告-{_safe_name(out['title'])}-{stamp}"
    d = _exports_dir()
    md_path = d / f"{base}.md"
    html_path = d / f"{base}.html"
    md_path.write_text(out["markdown"], encoding="utf-8")
    html_path.write_text(out["html"], encoding="utf-8")
    return {**out, "files": [str(md_path), str(html_path)],
            "names": [md_path.name, html_path.name]}


# ---------------------------------------------------------------- 渲染（两种形态同一份源）
def _to_markdown(doc: list[tuple[str, Any]]) -> str:
    lines: list[str] = []
    for kind, payload in doc:
        if kind == "h1":
            lines.append(f"# {payload}")
        elif kind == "h2":
            lines.append(f"\n## {payload}")
        elif kind == "h3":
            lines.append(f"\n### {payload}")
        elif kind == "p":
            lines.append(str(payload))
        elif kind == "pre":
            lines.append("")
            lines.append("```")
            lines.append(str(payload))
            lines.append("```")
        elif kind == "ul":
            lines.extend(f"- {x}" for x in payload)
    return "\n".join(lines).strip() + "\n"


def _to_html(doc: list[tuple[str, Any]], *, title: str) -> str:
    """极简 HTML（**全部转义**，不解析输入里的 HTML——报告是可交付文件，不是网页）。"""
    esc = lambda s: html.escape(str(s), quote=True)  # noqa: E731
    parts = ["<!doctype html>", '<html lang="zh-CN"><head><meta charset="utf-8">',
             f"<title>{esc(title)}</title>",
             "<style>body{font-family:system-ui,'Microsoft YaHei',sans-serif;"
             "max-width:52em;margin:2em auto;line-height:1.6}"
             "pre{white-space:pre-wrap;background:#f6f6f6;padding:.6em;border-radius:4px}"
             "h1,h2,h3{line-height:1.3}</style></head><body>"]
    for kind, payload in doc:
        if kind == "h1":
            parts.append(f"<h1>{esc(payload)}</h1>")
        elif kind == "h2":
            parts.append(f"<h2>{esc(payload)}</h2>")
        elif kind == "h3":
            parts.append(f"<h3>{esc(payload)}</h3>")
        elif kind == "p":
            parts.append(f"<p>{esc(payload)}</p>")
        elif kind == "pre":
            parts.append(f"<pre>{esc(payload)}</pre>")
        elif kind == "ul":
            parts.append("<ul>" + "".join(f"<li>{esc(x)}</li>" for x in payload) + "</ul>")
    parts.append("</body></html>")
    return "\n".join(parts)


def track_l_status(project_id: str) -> list[dict[str, Any]]:
    """项目内材料的 Track L 状态（给报告/界面看"哪几条已进法条库"）。

    只读：`plan_import` 不写任何东西（它的 docstring 就是这么承诺的）。
    """
    out: list[dict[str, Any]] = []
    for m in mr.list_materials(project_id):
        intent = tl.track_l_intent(m)
        if intent is None:
            continue
        plan = tl.plan_import(str(m["material_id"]))
        out.append({"material_id": m["material_id"], "title": m.get("title"),
                    "review_status": m.get("review_status"), "doc_id": m.get("doc_id"),
                    "doc_kind": intent.get("doc_kind"), "action": plan.get("action"),
                    "why": plan.get("why")})
    return out
