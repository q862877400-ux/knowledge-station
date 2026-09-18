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

§10.92 又落了**第三种形态 Word（`.docx`）**，用的还是 `exports/report_export` 里
既有那条 `python-docx` 通路（效力报告/审查报告/问答依据三条导出早就在用）
⇒ 依旧**零新增依赖**；三种形态都是 `build_report_blocks` 的同一份内容块渲染的。
"""
from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.exceptions import KnowledgeStationError
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


def _docx_template_path() -> Path:
    """Word 模板路径（与 `report_export._open_document` 同一约定，§10.92）。

    单独抽出来只有**一个**用途：`_to_docx` 失败时能在错误信息里**指名道姓**地
    把"是不是这个模板的问题"说清楚——否则调用方只能看到一句裸的 `KeyError`。
    """
    from src.core.exports.report_export import _templates_dir
    return _templates_dir() / "research-report.docx"


def _status_marks() -> dict[str, str]:
    """`locator.STATUS_MARKS` 的**惰性**取用（延迟 import：本模块在材料层之上，
    顶层 import 容易绕成环）。措辞的唯一所有者仍是 `locator.py`。"""
    from src.core.materials.locator import STATUS_MARKS
    return STATUS_MARKS


def _material_line(m: dict[str, Any]) -> str:
    """参考**材料**条目的一行说明（带两个轴——合成一个"可信度"必错）。

    ⚠ 还带**引用锚点健康度**（方案 §12 未决第 5 条）：`char_start/char_end/page` 是
    解析结果的坐标，换解析器就可能失效 ⇒ 报告里必须**看得见**这件事，否则"引用看起来
    正常"本身就是误导。只在**有问题**时加标记（`ok` 不加噪声）：
      · `stale` ⇒ ⚠锚点需复算；`unknown` ⇒ ⚠锚点未验证（含"入库时没记指纹"）；
      · `health_error` ⇒ ⚠锚点健康度算不出来（**我们的**判据跑挂了，不是材料的问题）。
    """
    role = m.get("task_role") or "未声明效力"
    role_label = {"criterion": "本任务准则", "reference": "仅作参考"}.get(role, role)
    bits = [f"{m.get('title') or '(无题)'}",
            f"[{m.get('source_tier') or '?'}·{m.get('tier_label') or ''} / {role_label}]",
            f"评审={m.get('review_status')}"]
    anchor = m.get("_locator_status")
    # ⚠ 短标记的措辞**从 `locator.STATUS_MARKS` 取**（唯一所有者）：证据行
    # （`authority.render_evidence`）用的是同一份，免得两处各写一份慢慢漂开（b11 的 INFO-4）。
    _marks = _status_marks()
    if anchor in _marks:
        bits.append(_marks[anchor])
    if m.get("url"):
        bits.append(str(m["url"]))
    if m.get("doc_id"):
        bits.append(f"法条={m['doc_id']}")
    return "，".join(bits)


def _attach_locator_status(materials: list[dict[str, Any]]) -> None:
    """给材料行挂上 `_locator_status`（判据本身不重解析，但**会读一次源文件**；判不了就是 `unknown`）。

    ⚠ **这里要改准一句旧话**（复核 b11 的 INFO-4，2026-09-18）：旧版写"报告要能**引用前校验**"，
    但实际标出来的位置是**材料清单行**（`_material_line`），而**真正的引用在「三、依据」节**
    ——那一节由 `authority.render_evidence()` 渲染，**这一层不碰它**（它是另一个所有者）。
    ⇒ 准确说法是：**本函数只保证"材料清单里看得见"，不保证"引用点上看得见"**。
    要把标记放到引用点上，得让 `render_evidence` 认识锚点状态（**跨所有者改动**），
    已作为**新立项**登记在方案 §12（不在这一步夹带）。

    为什么粒度放在这里：`reverify` 太贵（子进程解析），不能进报告路径 ⇒
    只用 `locator.locator_health()`（比指纹 + 比源文件字节），并把结论**如实**标出来
    （`stale`/`unknown`/`health_error` 都有标记，`ok`/`no_locators` 不加噪声）。
    ⚠ `unknown` **不**等于有问题，只等于"判据下不了结论"——措辞见 `locator.py`。

    ⚠ `health_error` **不是**健康状态，是"**我们的判据跑挂了**"（复核 b9 的 INFO-3）：
    旧写法把异常吞成 `unknown` ⇒ 报告上会出现"⚠锚点**未验证**（不等于有问题）"，
    等于把**我们自己的**异常算到材料头上（"这份材料没验证过" vs "我们没算出来"）。
    现在单独取值 + 单独警告（**并把原因也说出来**，复核 b11 的 LOW-1），界面/报告都不许把它混进 `unknown`。
    （取值域仍以 `locator.HEALTH_STATUSES` 为准：那个词表是 `locator_health` 的**结论**，
      `health_error` 是"结论没拿到"，与 `unavailable` 之于 `reverify` 同理。）
    """
    from src.core.materials import locator as lo
    for m in materials:
        try:
            out = lo.locator_health(m)
            m["_locator_status"] = out["status"]
            m["_locator_why"] = out.get("why") or ""
        except Exception as exc:  # noqa: BLE001 — 健康度算不出来不该让报告失败
            m["_locator_status"] = "health_error"
            m["_locator_why"] = f"锚点健康度计算失败：{type(exc).__name__}: {exc}"


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


def clause_refs(text: str | None) -> list[int]:
    """文本里出现的**法条**引用编号（`[[c:i]]`）——判据的**唯一所有者**（§10.98）。

    为什么要单开一个公开函数：结论草稿（`research_draft`）需要它判断"草稿里有没有出现法条编号"
    （本次起草**没喂**法条证据 ⇒ 那些编号无从核验）。正则只有一个，别在第二个文件里再写一遍。
    """
    return sorted({int(x) for x in _RE_CLAUSE_REF.findall(text or "")})


def assemble_evidence_or_raise(project_id: str, query: str, *, limit: int = 8,
                               ) -> dict[str, Any]:
    """装配依据集；**失败翻成可操作的错误码**（§10.98，复核 b25 的 MEDIUM-1）。

    为什么必须有它：`authority.assemble_evidence()` 里要调 `search_materials()`（SQL + FTS），
    库损坏 / 被锁死 / 磁盘读失败都会抛。原先**两处**调用点（报告 `build_report_blocks` 与
    草稿 `research_draft`）**都没接** ⇒ 异常穿过路由层那两个 `except`
    （只接 `ValueError` / `KnowledgeStationError`）变成**裸 500**：用户只看到
    "Internal Server Error"，真原因只在日志里。对照 `ks_answer.py` 的材料装载（它有 except
    + "不许静默降级"的注释）——同一类活，两处口径不一致本身就是缺陷。

    ⚠ 这里**只翻类型、不改语义**：`ValueError`（项目不存在那类）**照原样放行**，
    由路由层翻成 404；其余异常一律变成 `materials_load_failed`。
    """
    try:
        return authority.assemble_evidence(project_id, query, limit=limit)
    except (ValueError, KnowledgeStationError):
        raise
    except Exception as e:  # noqa: BLE001 —— 见 docstring：翻成可操作错误码，不吞
        raise KnowledgeStationError(
            f"载入参考资料失败（{type(e).__name__}: {e}）——依据集取不到时**不会**给出一份"
            "看着正常、其实没用上项目材料的产物；请检查数据库/磁盘后重试",
            code="materials_load_failed") from e


def check_conclusion_citations(conclusion_md: str | None,
                               assembled: dict[str, Any] | None,
                               ) -> tuple[dict[str, Any], list[str]]:
    """校验结论文本里的 `[[m:i]]` 并产出**同一套**警告文案（**判据与措辞的唯一所有者**）。

    返回 `(citations, warnings)`：
      - `citations`：`{material_refs, unknown, not_load_bearing, unchecked_law_refs}`；
      - `warnings`：人话警告（"引用了不存在的编号" / "引用了仅线索或不可用的材料" /
        "这次没有依据集，无法校验"）。

    ## 为什么抽成函数（§10.96）
    现在有**两个**调用方：报告（`build_report_blocks`）与**结论草稿**
    （`exports/research_draft.py` / `POST /report/research/draft`）。
    抽出来之前这段逻辑内联在报告里，草稿要么复刻一份（⇒ 同一段文字在两个地方给出不同警告，
    最难查的一种分叉），要么不校验（⇒ 草稿的引用没人管）。**判据本体**仍然是
    `_check_citations()`——本函数只负责"把结果翻译成同一套人话"。
    """
    citations: dict[str, Any] = {"material_refs": [], "unknown": [],
                                 "not_load_bearing": [], "unchecked_law_refs": []}
    warnings: list[str] = []
    conclusion = str(conclusion_md or "").strip()
    if not conclusion:
        return citations, warnings
    if assembled is not None:
        citations = _check_citations(conclusion, assembled)
        if citations["unknown"]:
            warnings.append("结论引用了**本次依据里不存在**的材料编号："
                            + "、".join(f"[[m:{i}]]" for i in citations["unknown"]))
        for bad in citations["not_load_bearing"]:
            warnings.append(f"结论引用了[[m:{bad['index']}]]，但它在 **{bad['group']}** 组"
                            "（仅线索/不可用）——**不得**用它承重")
    else:
        still = sorted({int(x) for x in _RE_MATERIAL_REF.findall(conclusion)})
        if still:
            # ⚠ **结构化字段也要如实**（2026-09-17 复核 b7 的 LOW-3）：原来只往 warning 文案里
            # 写了"有 N 个引用无法校验"，而 `citations["material_refs"]` 仍是空列表 ——
            # 读结构化字段的消费者会得出"结论里没有材料引用"这个**相反的结论**。
            citations["material_refs"] = still
            citations["unchecked_law_refs"] = clause_refs(conclusion)
            warnings.append("这次没有给 `query`，所以**无法校验**结论里的 "
                            f"{len(still)} 个 `[[m:i]]` 引用（没有依据集可比对）")
    return citations, warnings


def build_report_blocks(project_id: str, *, title: str | None = None,
                        query: str | None = None,
                        conclusion_md: str | None = None,
                        limit: int = 8) -> dict[str, Any]:
    """组装报告的**内容块**（`[(kind, payload)]`）——**唯一的内容来源**。

    Markdown / HTML（本模块）与 PPT（`exports.slide_export`）都从这里渲染：
    三种形态**同一份内容**，不会出现"报告里写的和 PPT 里写的不一样"。

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
    # 引用锚点的**便宜**健康度（方案 §12 未决第 5 条）：只比指纹，不重解析（报告不能慢成
    # 解析器）。⚠ 这里**不**下"引用有效"的结论，只把 stale/unknown **标出来**给人看。
    _attach_locator_status(approved + pending + rejected)

    assembled: dict[str, Any] | None = None
    if (query or "").strip():
        # §10.98：走**会翻错误码**的入口（复核 b25 的 MEDIUM-1：原先这里不接异常 ⇒ 裸 500）
        assembled = assemble_evidence_or_raise(project_id, str(query).strip(), limit=limit)

    warnings: list[str] = []
    # 锚点问题要**在 warnings 里也出现一次**：清单里的 ⚠ 标记只有逐条读才看得到，
    # 而"引用位置可能失效"属于该被一眼看到的事（措辞严格区分"需复算"与"未验证"）。
    _stale = [m for m in approved + pending + rejected if m.get("_locator_status") == "stale"]
    _unknown = [m for m in approved if m.get("_locator_status") == "unknown"]
    _health_error = [m for m in approved + pending + rejected
                     if m.get("_locator_status") == "health_error"]
    if _stale:
        # ⚠ **不写死成因**（2026-09-18，复核 b9 的 MEDIUM-1 带来第二个成因）：`stale` 既可能是
        # "解析器身份变了"，也可能是"**源文件字节变了**"（后者是**确定**失效，不是"可能"）。
        # 这里只报"状态 + 该怎么办"，具体成因逐条在 `locator_health(...)['why']` 里（唯一所有者）。
        warnings.append(f"⚠ {len(_stale)} 份材料的**引用锚点需要复算**"
                        "（成因逐条见各条的便宜判据：解析器身份变了，或**源文件字节已变**）"
                        "——**不代表已经坏了**，但已存区间与当前解析器/文件不一定对得上："
                        "要不要重建请先跑重解析比对（见清单里的「⚠锚点需复算」）")
    if _unknown:
        warnings.append(f"⚠ {len(_unknown)} 份**已批准**材料的引用锚点**未经验证**"
                        "（入库时没记解析器指纹、源文件不在磁盘上，或 PDF 的便宜判据下不了"
                        "结论）——**不等于**有问题，但报告里的引用位置**未经确认**")
    if _health_error:
        # ⚠ 这条**不是**材料的问题，是**我们**的判据跑挂了（复核 b9 的 INFO-3）。
        # 旧写法把它并进 `unknown` ⇒ 报告说"未经验证"，读者会去怀疑材料。
        # ⚠ **把原因也说出来**（复核 b11 的 LOW-1）：`_locator_why` 原先只写不读（2 写 0 读）
        # ⇒ 面板会把异常说出来、报告却不说，两个通道不对称。去重后最多列 3 条。
        _reasons: list[str] = []
        for _m in _health_error:
            _r = str(_m.get("_locator_why") or "").strip()
            if _r and _r not in _reasons:
                _reasons.append(_r)
        _detail = ""
        if _reasons:
            _detail = "；原因：" + "；".join(_reasons[:3]) + ("…" if len(_reasons) > 3 else "")
        warnings.append(f"⚠ {len(_health_error)} 份材料的**锚点健康度算不出来**"
                        "（判据抛异常——这是**工具缺陷**，不是这些材料有问题；"
                        "报告仍照原样列出，请把这几份当'引用位置未知'看；"
                        # ⚠ 作用域**故意**与上面那条 `_unknown` 不同（复核 b11 的 LOW-2）：
                        # `unknown` 只扫**已批准**（只有已批准承重；待评审的未经验证不影响结论），
                        # 而"判据崩溃"是**我们自己的**失败，无论评审状态都该被看见，
                        # 所以这里把待评审/已拒绝的也算进来——**明写出来**，别让读者猜。
                        "含待评审/已拒绝的在内）" + _detail)
    # §10.96：引用判据与措辞抽成**唯一所有者** `check_conclusion_citations()`
    # （结论草稿 `research_draft` 用同一份——两处对同一段文字必须给出同样的警告）。
    citations, _cite_warnings = check_conclusion_citations(conclusion_md, assembled)
    warnings.extend(_cite_warnings)
    conclusion = str(conclusion_md or "").strip()      # 文档块仍用它判"有没有结论一节"

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
        # ⚠ **把锚点状态传进证据渲染**（复核 b11 的 INFO-4）：标记要出现在**引用行**上，
        # 也就是引用**真正出现的地方**——此前它只在下面的"已批准参考资料清单"里，
        # 而那句"报告要能引用前校验"的理由说的正是这里。
        # ⚠ 只有**报告**这一处传 map；答案链（`ks_answer`）不传 ⇒ **提示词逐字节不变**
        # （B-5 的保证不受影响）。见 `authority.render_evidence` 的 docstring。
        _status_map = {str(m.get("material_id")): str(m.get("_locator_status"))
                       for m in approved + pending + rejected
                       if m.get("_locator_status")}
        rendered = authority.render_evidence(assembled, _status_map)
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
        # 2026-09-17：这条从 PPT 末页的**手写**文案搬过来（复核 b7 的 MEDIUM-3）——
        # 两份交付物原来各说各的；现在"已知限制"只有**这一份**，PPT 末页从这些块渲染。
        "**待评审**材料不会进入任何结论（批准与否是**用户**的判断，本系统不能代批）。",
    ]
    if citations["unchecked_law_refs"] or citations["unknown"]:
        limits.append("本报告里的引用标记**未经引擎逐条核验**（见上面的警告）。")
    limits.append("报告只在**本机**生成与保存（不外发）。")
    doc.append(("ul", limits))

    return {
        "title": name,
        "query": (query or None),
        "blocks": doc,
        "citations": citations,
        "warnings": warnings,
        "counts": {"approved": len(approved), "pending": len(pending),
                   "rejected": len(rejected)},
    }


def build_research_report(project_id: str, *, title: str | None = None,
                          query: str | None = None,
                          conclusion_md: str | None = None,
                          limit: int = 8) -> dict[str, Any]:
    """**内容块 → 两种可交付形态**（Markdown / HTML）。

    内容块的组装只有一处（`build_report_blocks`）；本函数与
    `exports.slide_export.write_slide_deck()` 都从**同一份块**渲染
    ——避免"报告一套内容、PPT 又一套内容"这种必然分叉。
    """
    model = build_report_blocks(project_id, title=title, query=query,
                               conclusion_md=conclusion_md, limit=limit)
    blocks = model["blocks"]
    return {**{k: v for k, v in model.items() if k != "blocks"},
            "markdown": _to_markdown(blocks),
            "html": _to_html(blocks, title=str(model["title"]))}


def write_research_report(project_id: str, *, title: str | None = None,
                          query: str | None = None,
                          conclusion_md: str | None = None,
                          limit: int = 8) -> dict[str, Any]:
    """组装并**落盘**（`.md` + `.html` + **`.docx`**）。

    §10.92：加上 **Word**（方案 §8 明写"报告：`python-docx`（Word）… 扩展现有 `exports/` 即可"）。
    ⚠ 三种形态**同一份内容块**（`build_report_blocks` 是唯一内容来源）——不会出现
    "Markdown 里写的和 Word 里写的不一样"。⚠ `.docx` **只在落盘路径产生**：`dry_run` 预览
    仍旧只回 markdown/html（docx 是二进制，塞进 JSON 响应没有意义）。

    两条落盘纪律（§10.92）：
    1. **先渲染、后落盘**：`.docx` 是三步里**唯一**会因外部原因（业主自备的
       `templates/research-report.docx` 缺内置样式）而失败的一步。先把字节渲染出来，
       再写三个文件 ⇒ 失败时**盘上一个文件都不留**，而不是回 500 却留下两个孤儿
       `.md`/`.html`（那种"接口说失败、盘上却有半份产物"最难查）。
    2. 失败**转成可操作的错误码**（`docx_render_failed`，信息里带模板路径与所需样式名），
       而不是让 FastAPI 回一句裸的 500。
    """
    model = build_report_blocks(project_id, title=title, query=query,
                                conclusion_md=conclusion_md, limit=limit)
    blocks = model["blocks"]
    out = {**{k: v for k, v in model.items() if k != "blocks"},
           "markdown": _to_markdown(blocks),
           "html": _to_html(blocks, title=str(model["title"]))}
    try:
        docx_bytes = _to_docx(blocks, title=str(model["title"]))
    except Exception as e:  # noqa: BLE001 —— 见 docstring：转成**可操作**的错误码
        raise KnowledgeStationError(
            f"Word 版渲染失败（{type(e).__name__}: {e}）。若 `{_docx_template_path()}` 存在，"
            "它必须保留内置样式 `Heading 1/2/3`、`List Bullet`（本报告只用这几种）；"
            "删掉该模板即回落到默认模板。Markdown/HTML 未落盘（先渲染后落盘）",
            code="docx_render_failed") from e
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"研究报告-{_safe_name(out['title'])}-{stamp}"
    d = _exports_dir()
    md_path = d / f"{base}.md"
    html_path = d / f"{base}.html"
    docx_path = d / f"{base}.docx"
    md_path.write_text(out["markdown"], encoding="utf-8")
    html_path.write_text(out["html"], encoding="utf-8")
    docx_path.write_bytes(docx_bytes)
    return {**out, "files": [str(md_path), str(html_path), str(docx_path)],
            "names": [md_path.name, html_path.name, docx_path.name]}


# ---------------------------------------------------------------- 渲染（三种形态同一份源）

def _to_docx(doc_blocks: list[tuple[str, Any]], *, title: str) -> bytes:
    """把**同一份内容块**渲染成 Word（`.docx` 字节）。

    §10.92（方案 §8：报告 = `python-docx`）。设计取舍：
      · 只用**内容块六种类型**（h1/h2/h3/p/pre/ul）——标题走 `add_heading(level=…)`，
        列表走内置 `List Bullet` 样式，代码块走等宽字体段落；**不**引入表格/图片/页眉
        （内容模型里本来就没有，硬加等于再造一套内容）；
      · 复用 `report_export._open_document("research-report")` 的**模板机制**：
        `%APPDATA%/KnowledgeStation/templates/research-report.docx` 存在就用它当底
        ⇒ 业主将来能用自己的版式（与"审查报告/问答依据"两条既有导出同一个约定）。
        ⚠ **模板契约**：它必须保留内置样式 `Heading 1/2/3`、`List Bullet`
        （`add_heading`/`add_paragraph(style=…)` 是按**样式名**查的，查不到就抛
        `KeyError`）——缺样式会**大声失败**成 `docx_render_failed`，**不**静默降级成
        没有小标题/没有项目符号的段落（降级出来的文件看着"成功"，实际丢了结构）；
      · **不**手工设中文字体（与 `export_review_report_docx` 一致：交给 Word 的字体回退 +
        模板；硬设字体名在没装该字体的机器上会静默换字，比不设更难查）；
      · 返回**字节**而不是路径：落盘由调用方决定（测试里可以直接解析字节，不用碰磁盘）。
    """
    import io

    from src.core.exports.report_export import _open_document
    d = _open_document("research-report")
    _ = title          # 标题本身是内容块里的第一个 h1；参数留着是为了将来做页眉/属性
    for kind, payload in doc_blocks:
        if kind == "h1":
            d.add_heading(str(payload), level=1)
        elif kind == "h2":
            d.add_heading(str(payload), level=2)
        elif kind == "h3":
            d.add_heading(str(payload), level=3)
        elif kind == "p":
            d.add_paragraph(str(payload))
        elif kind == "pre":
            para = d.add_paragraph(str(payload))
            for run in para.runs:
                run.font.name = "Consolas"
        elif kind == "ul":
            for item in payload:
                d.add_paragraph(str(item), style="List Bullet")
    bio = io.BytesIO()
    d.save(bio)
    return bio.getvalue()


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
