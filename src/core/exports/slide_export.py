# -*- coding: utf-8 -*-
"""研究报告 → **PPT** 导出（Phase D 第二步，2026-09-17，业主原始要求里的"PPT"）。

## 立项论证（方案 §8 要求"先论证值不值"——这一节就是那份论证）
1. **内容模型已经有了**：§10.36 的 `research_report.build_report_blocks()` 产出结构化内容块，
   本模块只做"块 → 幻灯片"的映射（**不重新组织内容**，所以不会出现"报告写的和 PPT 不一样"）。
   ⇒ 边际成本 = 一个薄映射 + 一次落盘，**不是**一条新管线。
2. **依赖几乎不新增**：`python-pptx` 是纯 Python 包，它的依赖（`lxml`、`Pillow`）在本仓
   已经因为 `python-docx` 等直接/传递存在（实测：`lxml 6.1.2`、`PIL 12.3.0` 均可用）。
   ⚠ 本仓纪律是"**0 import 就删依赖**"，所以本模块**真的用**它，并在 `pyproject.toml`
   **显式声明**（不再像 `requests/bs4` 那样靠传递依赖偶然满足——那条教训写在 pyproject 里）。
3. **业主明确要过**（原始要求："报告、PPT"），而 §10.36 交付的是 Markdown/HTML（"自行转"）。

## 三条纪律
1. **内容只从 `build_report_blocks` 来**（同一份块，三种形态）。
2. **诚实**：单张幻灯片最多 `MAX_SLIDES` 张，**截断要写在 slide 上**；
   每条要点超长会截断并标 `…`（PPT 不是全文容器，全文在 Markdown 报告里）；
   每份 PPT 末尾一页写清"本机生成、未外发、两个轴不得合并看"。
3. **不假装 pptx 可用**：缺依赖时抛**可操作**的错误（告诉你怎么装），不静默出一个空文件。
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.exports import research_report as rr

#: 幻灯片张数上限（超出就停，并在末页写明"后续见报告"——不假装全放得下）。
MAX_SLIDES = 30

#: 单条要点的字符上限（超长截断 + `…`；全文在 Markdown 报告里）。
MAX_BULLET_CHARS = 300

_RE_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")


def _plain(text: str) -> str:
    """把报告里的轻量 Markdown（`**粗体**`、反引号）转成**纯文本**（PPT 不做富文本解析）。"""
    s = _RE_MD_BOLD.sub(r"\1", str(text or ""))
    return s.replace("`", "")


def _clip(text: str, cap: int = MAX_BULLET_CHARS) -> str:
    s = _plain(text).strip().replace("\n", " ")
    return s if len(s) <= cap else s[:cap].rstrip() + "…"


def build_slides(blocks: list[tuple[str, Any]], *, title: str) -> list[dict[str, Any]]:
    """内容块 → 幻灯片模型（**纯函数，可离线测**）。

    映射规则（简单到不需要解释，也不需要"智能摘要"）：
      · `h1` → 首页标题；`h2` → **新开一页**（标题用 h2 的文字）；
      · `h3` → 当页的一级要点（加 `【】` 前缀）；
      · `ul` → 要点列表；`p` → 一段要点；`pre`（依据区）→ 逐行要点。
    """
    slides: list[dict[str, Any]] = [{"title": _clip(title, 120), "bullets": []}]
    for kind, payload in blocks:
        if kind == "h1":
            slides[0]["title"] = _clip(str(payload), 120)
        elif kind == "h2":
            slides.append({"title": _clip(str(payload), 120), "bullets": []})
        elif kind == "h3":
            slides[-1]["bullets"].append(f"【{_clip(str(payload), 80)}】")
        elif kind == "p":
            slides[-1]["bullets"].append(_clip(str(payload)))
        elif kind == "ul":
            slides[-1]["bullets"].extend(_clip(str(x)) for x in payload)
        elif kind == "pre":
            for line in str(payload).splitlines():
                if line.strip():
                    slides[-1]["bullets"].append(_clip(line))
    # 去掉空页（只有标题没内容的页在 PPT 里是噪声），但首页永远保留
    out = [slides[0]] + [s for s in slides[1:] if s["bullets"]]
    if len(out) > MAX_SLIDES:
        kept = out[:MAX_SLIDES - 1]
        kept.append({"title": "（内容较多，后续请见 Markdown 报告）",
                     "bullets": [f"完整报告共 {len(out)} 页内容，本 PPT 只放了前 "
                                 f"{MAX_SLIDES - 1} 页。"]})
        return kept
    return out


def _presentation() -> Any:
    """新建 Presentation（**缺依赖时给可操作的错误**，不是空文件）。"""
    try:
        from pptx import Presentation
    except ImportError as exc:  # pragma: no cover - 已声明依赖，正常环境不会走到
        raise RuntimeError(
            "导出 PPT 需要 python-pptx（已在 pyproject.toml 声明）："
            "pip install 'python-pptx>=1.0'") from exc
    return Presentation()


def write_slide_deck(project_id: str, *, title: str | None = None,
                     query: str | None = None, conclusion_md: str | None = None,
                     limit: int = 8) -> dict[str, Any]:
    """组装并落盘 `<exports>/研究报告-<安全名>-<时间戳>.pptx`。返回 `{path, name, slides, warnings, counts}`。"""
    model = rr.build_report_blocks(project_id, title=title, query=query,
                                  conclusion_md=conclusion_md, limit=limit)
    name = str(model["title"])
    slides = build_slides(model["blocks"], title=name)

    prs = _presentation()
    blank = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
    for idx, item in enumerate(slides):
        slide = prs.slides.add_slide(blank)
        top = slide.shapes.add_textbox(0, 0, prs.slide_width, 900_000)
        tf = top.text_frame
        tf.text = item["title"]
        tf.paragraphs[0].font.size = None if idx else None      # 用版式默认值，不硬编码字号
        body = slide.shapes.add_textbox(0, 1_000_000, prs.slide_width,
                                        prs.slide_height - 1_200_000)
        bf = body.text_frame
        bf.word_wrap = True
        first = True
        for bullet in item["bullets"]:
            p = bf.paragraphs[0] if first else bf.add_paragraph()
            first = False
            p.text = f"· {bullet}"
    # 末页：把"这份 PPT 不保证什么"写进去（诚实边界要跟上产出物，不能只写在文档里）
    tail = prs.slides.add_slide(blank)
    tf = tail.shapes.add_textbox(0, 0, prs.slide_width, 900_000).text_frame
    tf.text = "说明"
    bf = tail.shapes.add_textbox(0, 1_000_000, prs.slide_width,
                                 prs.slide_height - 1_200_000).text_frame
    bf.word_wrap = True
    notes = [
        f"生成时间：{datetime.now():%Y-%m-%d %H:%M}（本机生成，未外发）",
        "两个轴分开看：轴 A 来源可信度（T0~T4）决定能不能承重；轴 B 任务内效力决定它在"
        "本任务里说话的分量。",
        "仅线索（T3 未互证）与不可用（T4）的材料不得单独支撑结论。",
        "待评审材料不会进入任何结论（评审是用户的判断）。",
    ]
    for i, line in enumerate(notes):
        p = bf.paragraphs[0] if i == 0 else bf.add_paragraph()
        p.text = f"· {line}"

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    d = rr._exports_dir()
    path = d / f"研究报告-{rr._safe_name(name)}-{stamp}.pptx"
    prs.save(str(path))
    return {**{k: v for k, v in model.items() if k != "blocks"},
            "path": str(path), "name": Path(path).name,
            "slide_count": len(prs.slides._sldIdLst)}  # noqa: SLF001 — pptx 没给公开计数
