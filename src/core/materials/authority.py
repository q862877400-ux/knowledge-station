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
| T3 二手转述 | **只作线索**；**≥2 个来源身份已知且互异**（按域名）才可作辅证 |
| T4 不可回溯 | **禁止用于结论**（仍如实列出，标"已知不可用"——不假装它不存在） |

**两条不可被其他轴覆盖的绝对规则**（2026-09-17 独立复核后写死，别再改回顺序）：
1. **T4 优先于轴 B**：即使某条材料被声明为 `task_role='criterion'`，只要它是 T4，
   就**不按准则承重**（列在"已知不可用"，并在行内标出"你声明它为准绳但来源不可回溯"）。
   否则一篇匿名内容农场的帖子会因为"用户把它定为准绳"而压过国标——T4 的禁令是绝对的。
2. **身份未知不能互证**：没有域名/URL 的 T3 **不参与互证**（见 `_source_identity` 的
   `None` 语义）。宁可保守为"仅线索"，也不要报一个**不可证伪**的"多源互证"。

**可信度 ≠ 相关性**：本模块**不因"相关"而提级**，也不因为层级低就丢掉线索。
"""
from __future__ import annotations

from typing import Any

from src.core.materials import dedup
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

#: 分组顺序的**唯一所有者**：既决定渲染次序，也决定 `[[m:i]]` 的编号。
#:
#: ⚠ 为什么必须固定：`[[m:i]]` 是给模型的引用标记，编号一漂移，产出物里的引用就全指错。
#: 故编号按**本元组顺序**分配，且**包含 leads_only / excluded**——这两组也可能被引用
#: （线索要带"单一来源"声明，排除项只能在"已知不可用"的意义上提及），
#: 若不给它们编号，模型就只能靠文字指代，引用就不可核验了。
GROUP_ORDER: tuple[tuple[str, str], ...] = (
    ("criteria", "本任务准则（轴 B：以它为准绳）"),
    ("usable", "可作依据的材料"),
    ("corroborated", "已获多源互证的辅证"),
    ("leads_only", "仅供参考的线索（单一来源，未用于支撑结论）"),
    ("excluded", "已知不可用（不可用于结论）"),
)


def _domain_of(url: str) -> str:
    """从 URL 里取**来源域名**（小写、去 scheme/userinfo/端口/路径、去前导 `www.`）。

    ⚠ 这不是 eTLD+1（那要公共后缀表，未引入）：`news.a.com` 与 `blog.a.com` 仍算
    两个域名。**如实记这条局限**——但比"原文比较"强得多：
    独立复核 2026-09-17 实测旧口径把 `A.COM` 与 `a.com` 算两个，`www.a.com` 与
    `a.com` 也算两个（都是假"独立来源"）。
    """
    s = url.strip().lower()
    if "://" in s:
        s = s.split("://", 1)[1]
    s = s.split("/", 1)[0]           # 去路径
    s = s.split("@")[-1]             # 去 userinfo
    s = s.split(":", 1)[0]           # 去端口
    if s.startswith("www."):
        s = s[4:]
    return s


def _source_identity(hit: dict[str, Any]) -> str | None:
    """判"独立来源"的口径：优先 `domain`，其次从 `url` 取域名；**都没有 → None**。

    为什么用域名而不是 URL：同一站点转载同一篇稿子**不是**互证（那是最常见的假互证）。

    ⚠ **`None` 的语义（2026-09-17 独立复核后改，很关键）**：身份未知的来源**不能参与互证**。
    原先身份未知时退到 `material:<id>`，而**生产代码从不设置 domain/url**
    （`ingest_material_file` 两个都不传）⇒ 那份兜底等于"任意两份材料都算两个独立来源"，
    把"≥2 个独立来源"这条核心纪律变成了**不可证伪**的装饰：实测同一篇文章的两份副本
    被报成「二手转述 2 条获 **2 个独立来源**互证」。
    现在宁可保守：**身份未知 ⇒ 只作线索**（准确性优先于"看起来有互证"）。
    """
    domain = (hit.get("domain") or "").strip().lower()
    if domain:
        # ⚠ **一律**过 `_domain_of`，别写"含 :// 才归一"的分支——那样 `www.a.com`
        # （无 scheme 无路径）会被原样返回，于是 `A.COM` / `www.a.com` / `http://a.com`
        # 被算成**三个**来源（本文件第一版就这么错了，被自己的测试当场抓住）。
        return _domain_of(domain) or None
    url = (hit.get("url") or "").strip()
    if url:
        return _domain_of(url) or None
    return None


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
    # 项目不存在 vs 项目里没命中——**是两件不同的事**，不能都报成"没有命中"
    # （那会让调用方以为"这个项目确实没有可用材料"）。故先确证项目存在。
    project_found = mr.get_project(project_id) is not None
    hits = mr.search_materials(project_id, question, limit=limit) if project_found else []
    criteria: list[dict] = []
    usable: list[dict] = []
    leads: list[dict] = []
    excluded: list[dict] = []
    for h in hits:
        h = dict(h)
        h["behaviour"] = TIER_BEHAVIOUR.get(h.get("source_tier") or "", "excluded")
        h["behaviour_label"] = BEHAVIOUR_LABELS.get(h["behaviour"], "")
        h["source_identity"] = _source_identity(h)
        declared_criterion = h.get("task_role") == "criterion"
        # ⚠ **T4 优先于轴 B**（2026-09-17 独立复核报的 MEDIUM）：T4 = 来源不可回溯，
        # "禁用于结论"是**绝对规则**，不能被"用户把它声明为准绳"重置。旧实现先判
        # `task_role=='criterion'`，于是 T4+准则会落进 `criteria`、进 `usable_hits()`，
        # 而提示词里"本任务准则**优先于法条**"——等于让一篇匿名内容农场的帖子压过国标。
        # 现在 T4 一律进 `excluded`，**但保留用户声明的痕迹**（`criterion_blocked_by_tier`），
        # 并在渲染与 notes 里显式说明"你声明它为准绳，但它来源不可回溯、未按准则承重"
        # —— 不是悄悄推翻用户的声明，而是**不承重 + 说清楚**。
        if declared_criterion and h["behaviour"] == "excluded":
            h["criterion_blocked_by_tier"] = True
        if h["behaviour"] == "excluded":
            excluded.append(h)
        elif declared_criterion:
            criteria.append(h)          # 准则单列（轴 B），与层级无关（T4 除外，见上）
        elif h["behaviour"] == "needs_corroboration":
            leads.append(h)
        else:
            usable.append(h)

    # T3 的互证判定：按"该主张"分组——这里用**检索命中的共性**近似：
    # 只要出现 ≥2 个**内容各自独立**的来源，就认为这批线索获得多源互证。
    # ⚠ 这是**批级**判定，不是逐主张级（逐主张需要语义聚类，属后续；
    #   当下宁可保守——批级互证只把线索升到"辅证"，不会升到"可作依据"）。
    # ⚠ **身份未知（无域名/URL）的 T3 不参与互证**（见 `_source_identity` 的 None 语义）。
    # ⚠ **内容近似的域名要合并**（`dedup.independent_source_count`）：独立复核实测，
    #   只按域名判会把"**同一篇通稿被两个站点转载**"算成两个独立来源 ⇒ 假互证。
    #   现在"独立"要求**域名不同且不是同一篇稿子**。
    identities = {h["source_identity"] for h in leads}
    identities.discard(None)
    source_count, merged_domains = dedup.independent_source_count(
        [h["source_identity"] for h in leads],
        [str(h.get("text") or "") for h in leads])
    corroborated: list[dict] = []
    if source_count >= 2:
        # ⚠ **逐条**判定，不是整批一起升：身份未知的那条**没有**被互证
        # （它无法与任何来源配对）。整批一起升会让"无出处的帖子"搭上别人的互证
        # ——本文件第一版就是这么错的，被 test_unknown_identity_does_not_drag_down… 抓住。
        corroborated = [h for h in leads if h["source_identity"] is not None]
        leads = [h for h in leads if h["source_identity"] is None]
        for h in corroborated:
            h["behaviour"] = "corroborated"
            h["behaviour_label"] = BEHAVIOUR_LABELS["corroborated"]

    notes: list[str] = []
    if criteria:
        notes.append(f"本任务准则材料 {len(criteria)} 条（轴 B：以它为准绳，不按来源层级降级）。")
    blocked = [h for h in excluded if h.get("criterion_blocked_by_tier")]
    if blocked:
        notes.append(f"⚠ {len(blocked)} 条材料被声明为「本任务准则」，但来源**不可回溯（T4）**，"
                     "故**未按准则承重**（T4 禁用于结论是绝对规则）——它们列在"
                     "「已知不可用」一节，请自行判断是否需要换用可回溯的来源。")
    merged_groups = [g for g in merged_domains if len(g) > 1]
    merged_note = ("；".join(f"{'、'.join(g)} 承载**内容近似**的转述" for g in merged_groups)
                   if merged_groups else "")
    if corroborated:
        notes.append(f"二手转述 {len(corroborated)} 条获 **{source_count} 个独立来源**互证，"
                     f"可作辅证（来源：{'、'.join(sorted(identities))}）。")
        # 被合并的域名要说出来：用户才知道"为什么两个域名只算一个来源"
        if merged_note:
            notes.append(f"其中 {merged_note}，已按**同一来源**计（疑似同稿转载）"
                         "——一稿多发**不是**多源互证。")
    elif source_count == 1 and merged_groups:
        # **合并挡住了互证**时更要说明**为什么**（这正是最需要解释的情形：
        # 用户看到两个域名，会以为已经有互证了）。旧写法只在互证成立时说明，
        # 于是"为什么不算两个来源"在最该解释的时候没有解释——被测试抓到。
        notes.append(f"有 {merged_note}，已按**同一来源**计（疑似同稿转载）"
                     f"⇒ 实际只有 **1 个**独立来源，**不构成互证**，只能当线索。")
    if leads:
        unknown = [h for h in leads if h["source_identity"] is None]
        notes.append(f"二手转述 {len(leads)} 条**仅单一来源**，只能当线索，**未用于支撑结论**。")
        if unknown:
            notes.append(f"其中 {len(unknown)} 条**没有可回溯的来源标识（无域名/URL）**，"
                         "身份未知者**不能互证**——请勿把它们当成多个独立来源。")
    if excluded:
        notes.append(f"不可回溯来源 {len(excluded)} 条已排除在结论之外（仍如实列出以便你判断）。")
    if not project_found:
        notes.append(f"项目 {project_id} 不存在——本轮**没有**可用的参考资料"
                     "（不是「项目里没有命中」，两者不同）。")
    elif not hits:
        notes.append("本项目已批准材料中没有命中；结论不得建立在材料之上。")

    assembled: dict[str, Any] = {
        "question": question,
        "project_id": project_id,
        "project_found": project_found,
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
    # `[[m:i]]` 编号：按 GROUP_ORDER 顺序**全局**递增（跨组连续，模型好数）。
    idx = 0
    for key, _title in GROUP_ORDER:
        for h in assembled[key]:
            h["index"] = idx
            idx += 1
    return assembled


def render_evidence(assembled: dict[str, Any],
                    locator_status: dict[str, str] | None = None) -> str:
    """把分组结果渲染成**给提示词/产出物用的文本**（每条都带两个轴的标注、`[[m:i]]` 与位置）。

    为什么渲染时要带 `材料#id@起-止`：产出物里的引用要能**点回原文位置**，
    那就必须把材料 id 与字符区间一起带出去（与法条侧"标准号-条款号可点回"同精神）。
    `[[m:i]]` 的 `i` 就是 `hit["index"]`（由 `assemble_evidence()` 按 GROUP_ORDER 分配）。

    ## `locator_status`（可选，**默认 None**）——2026-09-18 加，收复核 b11 的 INFO-4
    材料 id → 锚点状态（`locator.HEALTH_STATUSES` 或 `health_error`）。**只有报告传它**
    （`research_report` 里那一处调用）——这样「⚠锚点…」标记才会出现在**引用行**上，
    也就是引用**真正出现的地方**；此前它只出现在"已批准参考资料清单"里，
    而 b11 指出：那正是"报告要能引用前校验"这句理由与实际不符之处。

    ⚠ **为什么是可选参数（这一条比功能本身重要）**：本函数的输出**同时喂给答案链的提示词**
    （`ks_answer` 那一处调用）。答案链**不传**这个参数 ⇒ 提示词**逐字节不变**，
    B-5 那条"不给 `params.material_project_id` 时提示词逐字不变"的保证**不受影响**。
    原先我把"标记放到引用点"与"改提示词"当成一件事（所以登记为需要立项），
    其实**解耦就行**：**谁要标记谁传 map**。`tests/...::TestEvidenceAnchorMarks` 把这条钉住了。
    """
    def line(h: dict[str, Any]) -> str:
        loc = f"{h.get('title')}#{h.get('material_id')}@{h.get('char_start')}-{h.get('char_end')}"
        if h.get("page"):
            loc += f"(第{h['page']}页)"
        # 被层级挡下的"准则"必须**在行内**就能看出来，不能只靠 notes 或所在小节：
        # 否则模型读到 role_label「本任务准则」+ 提示词规则 8（准则优先于法条）就会照办。
        mark = " ⛔你声明它为准绳，但来源不可回溯（T4），**未按准则承重**" \
            if h.get("criterion_blocked_by_tier") else ""
        # 锚点状态（**只有传了 map 才会出现**，见 docstring）：短标记的措辞所有者是
        # `locator.STATUS_MARKS`（与材料清单行用的是同一份，免得两处漂开）。
        if locator_status:
            from src.core.materials.locator import STATUS_MARKS
            st = locator_status.get(str(h.get("material_id") or ""))
            if st in STATUS_MARKS:
                mark += f" {STATUS_MARKS[st]}"
        return (f"- [[m:{h.get('index')}]] [{h.get('tier_label')}·{h.get('role_label')}] {loc}{mark}\n"
                f"  {h.get('text', '').strip()}")

    parts: list[str] = []
    for key, title in GROUP_ORDER:
        group = assembled[key]
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
