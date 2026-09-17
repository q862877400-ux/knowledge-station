# -*- coding: utf-8 -*-
"""材料平面：权威性纪律（Phase B）。把"可信度"从**标签**变成**可执行规则**。

## 这个模块解决什么
业主的原话：**"要对材料可信度进行判别，而不是随便找个什么网络文章就当权威信源"**。
光给材料贴 T0~T4 标签不够——**必须有人按标签拒绝/降级**，否则标签只是装饰。
本模块就是那个"按标签办事"的地方：检索命中进来，按承重能力**分组**（不是排序），
并给出**为什么**被降级/排除的说明。

## 两个轴（业主 2026-09-17 裁定的"公司制度"例）
- **轴 A 来源可信度** `source_tier`(T0~T4) → 决定**能不能承重**（本模块的判据）；
- **轴 B 任务内效力** `task_role`(criterion/reference) → 决定**谁说话**（本模块单列 `criteria`）。
二者**正交**：公司制度的来源层级低于国标，但对"我们公司报销怎么走"它才是准绳。
⇒ **本模块不提供"按一个分数给材料排序"的函数**——那样必然把两个轴压成一个，错一个。

## 承重规则（写死在这里，别在别处再抄一份）
| 层 | 承重 |
|---|---|
| T0 法定/官方原文 | 可作依据 |
| T1 用户自有原始件 | 可作依据（对**其自身内容**是初级证据） |
| T2 权威第三方 | 可作依据 |
| T3 二手转述 | **只作线索**；**≥2 个独立来源互证**才可作辅证 |
| T4 不可回溯 | **禁止用于结论**（仍如实列出，标"已知不可用"——不假装它不存在） |

**可信度 ≠ 相关性**：本模块**不因"相关"而提级**，也不因为层级低就丢掉线索。
"""
from __future__ import annotations

from typing import Any

from src.core.storage import material_repo as mr

#: 轴的取值 → 承重行为。**规则只有一个所有者**（改这里即改全局判据）。
TIER_BEHAVIOUR: dict[str, str] = {
    "T0": "usable",
    "T1": "usable",
    "T2": "usable",
    "T3": "needs_corroboration",
    "T4": "excluded",
}

#: 承重行为的说明（给产出物/UI 用，避免各处各写一份措辞）
BEHAVIOUR_LABELS: dict[str, str] = {
    "usable": "可作依据",
    "needs_corroboration": "仅作线索（需 ≥2 个独立来源互证才可作辅证）",
    "corroborated": "已获多源互证，可作辅证",
    "excluded": "不可用于结论（来源不可回溯）",
}


def _source_identity(hit: dict[str, Any]) -> str:
    """判"独立来源"的口径：优先域名；没有域名则退到材料本身。

    为什么用域名而不是 URL：同一站点转载同一篇稿子**不是**互证（那是最常见的假互证）。
    同一域名的多篇也**只算一个来源**。
    """
    domain = (hit.get("domain") or "").strip().lower()
    if domain:
        return f"domain:{domain}"
    url = (hit.get("url") or "").strip()
    if url:
        return f"url:{url.split('?')[0]}"
    return f"material:{hit.get('material_id')}"


def assemble_evidence(project_id: str, question: str, *, limit: int = 8) -> dict[str, Any]:
    """在**已批准**材料里检索并**按承重能力分组**。

    返回结构（每个命中都带两个轴的标注，供下游如实呈现）：
      - `criteria`        : 轴 B 判为 `criterion` 的命中（**本任务准则**，永远单列在最前）
      - `usable`          : T0/T1/T2 命中（可作依据）
      - `corroborated`    : T3 命中，且同一主张有 **≥2 个独立来源**（可作**辅证**）
      - `leads_only`      : T3 命中但只有单一来源（**仅线索**，不得单独支撑结论）
      - `excluded`        : T4 命中（**禁用于结论**，如实列出）
      - `notes`           : 人话说明"哪些被降级/排除、为什么"（可见性硬需求）
      - `counts`          : 各组的条数

    检索本身走 `material_repo.search_materials()` ⇒ **评审硬门在那一层已经保证**
    （未批准材料根本不会出现在这里的输入里）。
    """
    hits = mr.search_materials(project_id, question, limit=limit)
    criteria: list[dict] = []
    usable: list[dict] = []
    leads: list[dict] = []
    excluded: list[dict] = []

    for h in hits:
        h = dict(h)
        h["behaviour"] = TIER_BEHAVIOUR.get(h.get("source_tier") or "", "excluded")
        h["behaviour_label"] = BEHAVIOUR_LABELS.get(h["behaviour"], "")
        if h.get("task_role") == "criterion":
            criteria.append(h)                     # 准则单列（轴 B），与层级无关
        elif h["behaviour"] == "excluded":
            excluded.append(h)
        elif h["behaviour"] == "needs_corroboration":
            leads.append(h)
        else:
            usable.append(h)

    # T3 的互证判定：按"该主张"分组——这里用**检索命中的共性**近似：
    # 只要出现 ≥2 个**独立来源**的 T3 命中，就认为这批线索获得多源互证。
    # ⚠ 这是**批级**判定，不是逐主张级（逐主张需要语义聚类，属后续；
    #   当下宁可保守——批级互证只把线索升到"辅证"，不会升到"可作依据"）。
    domains = {_source_identity(h) for h in leads}
    corroborated: list[dict] = []
    if len(domains) >= 2:
        corroborated = leads
        leads = []
        for h in corroborated:
            h["behaviour"] = "corroborated"
            h["behaviour_label"] = BEHAVIOUR_LABELS["corroborated"]

    notes: list[str] = []
    if criteria:
        notes.append(f"本任务准则材料 {len(criteria)} 条（轴 B：以它为准绳，不按来源层级降级）。")
    if corroborated:
        notes.append(f"二手转述 {len(corroborated)} 条获 **{len(domains)} 个独立来源**互证，"
                     f"可作辅证（来源：{'、'.join(sorted(domains))}）。")
    if leads:
        notes.append(f"二手转述 {len(leads)} 条**仅单一来源**，只能当线索，**未用于支撑结论**。")
    if excluded:
        notes.append(f"不可回溯来源 {len(excluded)} 条已排除在结论之外（仍如实列出以便你判断）。")
    if not hits:
        notes.append("本项目已批准材料中没有命中；结论不得建立在材料之上。")

    return {
        "question": question,
        "criteria": criteria,
        "usable": usable,
        "corroborated": corroborated,
        "leads_only": leads,
        "excluded": excluded,
        "notes": notes,
        "counts": {"criteria": len(criteria), "usable": len(usable),
                   "corroborated": len(corroborated), "leads_only": len(leads),
                   "excluded": len(excluded), "total": len(hits)},
    }


def render_evidence(assembled: dict[str, Any]) -> str:
    """把分组结果渲染成**给提示词/产出物用的文本**（每条都带两个轴的标注与可点回的位置）。

    为什么渲染时要带 `材料#id@起-止`：产出物里的引用要能**点回原文位置**，
    那就必须把材料 id 与字符区间一起带出去（与法条侧"标准号-条款号可点回"同精神）。
    """
    def line(h: dict[str, Any]) -> str:
        loc = f"{h.get('title')}#{h.get('material_id')}@{h.get('char_start')}-{h.get('char_end')}"
        if h.get("page"):
            loc += f"(第{h['page']}页)"
        return (f"- [{h.get('tier_label')}·{h.get('role_label')}] {loc}\n"
                f"  {h.get('text', '').strip()}")

    parts: list[str] = []
    sec = [("本任务准则（轴 B：以它为准绳）", assembled["criteria"]),
           ("可作依据的材料", assembled["usable"]),
           ("已获多源互证的辅证", assembled["corroborated"]),
           ("仅供参考的线索（单一来源，未用于支撑结论）", assembled["leads_only"]),
           ("已知不可用（不可用于结论）", assembled["excluded"])]
    for title, group in sec:
        if group:
            parts.append(f"### {title}")
            parts.extend(line(h) for h in group)
    if assembled["notes"]:
        parts.append("### 说明")
        parts.extend(f"- {n}" for n in assembled["notes"])
    return "\n".join(parts)


def usable_hits(assembled: dict[str, Any]) -> list[dict[str, Any]]:
    """**只取能承重的**命中（准则 + 可作依据 + 多源互证的辅证）。

    给"要产出结论"的调用方用的安全入口：`leads_only` 与 `excluded` 都**不**在里面。
    要展示线索/被排除项请用 `assemble_evidence()` 的完整结构——**别用本函数**，
    否则会把"只能当线索"的东西漏掉在可见性之外。
    """
    return assembled["criteria"] + assembled["usable"] + assembled["corroborated"]
