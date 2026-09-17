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
1. **内容只从 `build_report_blocks` 来**（同一份块，三种形态）——**包括末页的"已知限制"**
   （2026-09-17 复核 b7 的 MEDIUM-3 之前，末页那 4 句是这里**手写**的第二份内容，
   实测与报告 §六 分叉：PPT 里多 3 句、报告里多 2 句 ⇒ 各自的诚实边界会各自漂移）。
2. **诚实**：**交付的 `.pptx` 总页数 ≤ `MAX_SLIDES`**（含末页——复核实测过旧实现
   落盘 31 页而常量写 30，属"过度声称"）；一页要点过多会**自动续页**（不超过
   `MAX_BULLETS_PER_SLIDE` 条，因为旧实现实测出现过**单页 120 条**，PPT 里必然溢出文本框）；
   截断要写在 slide 上；每条要点超长会截断并标 `…`（PPT 不是全文容器，全文在 Markdown 里）。
3. **不假装 pptx 可用**：缺依赖时抛**可操作**的错误（告诉你怎么装），不静默出一个空文件。
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.exports import research_report as rr

#: **交付物**（含末页）的幻灯片张数上限。
#: `build_slides` 最多产出 `MAX_SLIDES - 1` 张**内容页**，`write_slide_deck` 再加 1 张末页。
MAX_SLIDES = 30

#: **版式几何（默认 python-pptx 模板，实测值）**——`MAX_LINES_PER_SLIDE` 不是拍脑袋来的：
#:   · 幻灯片 10in × 7.5in = `9144000` × `6858000` EMU；
#:   · 正文框在 `write_slide_deck` 里是 `add_textbox(0, 1_000_000, slide_width,
#:     slide_height - 1_200_000)`（顶部留标题、底部留边）⇒ 高 `5658000` EMU = **445.5pt**；
#:   · 我们不设字号（`font.size = None`）⇒ 用版式默认 **18pt**；
#:   · 行高按 1.2 倍估 ⇒ 21.6pt/行 ⇒ 容量 `445.5 / 21.6 ≈ 20.6` 行。
#: ⚠ 这几个数字有**独立测试**从真实 `Presentation()` 重算并断言一致
#: （`test_slide_export.py::test_line_budget_matches_the_real_slide_geometry`），
#: 所以常量与版式**不会各自漂移**。⚠ 仍是**估算**（默认模板 + 默认字号 + 1.2 行高），
#: **没有**做渲染级测量 ⇒ 是"**减少溢出**"，不是"保证不溢出"。
SLIDE_WIDTH_EMU = 9_144_000
SLIDE_HEIGHT_EMU = 6_858_000
BODY_TOP_EMU = 1_000_000
BODY_HEIGHT_EMU = SLIDE_HEIGHT_EMU - 1_200_000          # 5658000 EMU
BODY_HEIGHT_PT = BODY_HEIGHT_EMU / 12_700               # 445.51pt
ASSUMED_FONT_PT = 18
LINE_HEIGHT_FACTOR = 1.2

#: 单张内容页的**行预算**（超了就续页，标题加"（续 N）"）。
#: 为什么是"行"而不是"条数"（2026-09-17 独立复核 b8 的 MEDIUM-3，实测打回）：
#: 上一版写的是"每页 ≤ 12 条"，而复核算过几何：12 条 × 40 字 ≈ 24 行 ≈ 7.20in **已经溢出**
#: （可用只有 6.19in ≈ 20.6 行）。也就是说那个常量**本身就不够**
#: （与 b7 的"30 页假上界"同型：看起来有上界，其实不是）。
#: 18 = 20.6 行的**约 88%**，留一行多的余量给项目符号间距与字体回退。
MAX_LINES_PER_SLIDE = 18

#: 每行容纳多少"**全角当量字符**"：正文框宽 10in = 720pt，18pt 的中文字宽 ≈ 18pt
#: ⇒ `720 / 18 = 40`。ASCII 按 0.5 全角计（见 `estimate_lines`），所以这个数是**全角当量**。
CHARS_PER_LINE = 40

#: 半角字符折算成"全角当量"的系数（估：ASCII 平均字宽 ≈ 0.5 em）。
NARROW_CHAR_WEIGHT = 0.5

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


def estimate_lines(bullet: str) -> int:
    """一条要点**估算**占几行（至少 1 行）。

    按"**全角当量**"折算：中文/全角标点算 1，ASCII 算 `NARROW_CHAR_WEIGHT`（0.5），
    再除以每行容量 `CHARS_PER_LINE`。为什么不做"一律按字符数"：一份英文清单会被
    **高估**行数（拆得更碎，安全但浪费页），而一份中英混排的会被**低估**（危险方向）。
    单独抽出来是为了**可断言**（复核 b8 建议的钉法：断言"每页估算行数 ≤ 行预算"）。
    """
    text = bullet or ""
    wide = sum(1 for ch in text if ord(ch) > 0x2E7F)       # 全角/宽字符（含中文、全角标点）
    narrow = len(text) - wide
    ems = wide + narrow * NARROW_CHAR_WEIGHT
    return max(1, int(-(-ems // CHARS_PER_LINE)))          # 向上取整，至少 1 行


def _paginate(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按**行预算**把一页拆成多页（标题加"（续 N）"）。

    为什么在**模型层**做而不是在写 pptx 时做：页数是**可断言的交付物属性**
    （`slide_count` 与 `len(prs.slides)`），测试要能在不装 python-pptx 的路径上验它。
    """
    out: list[dict[str, Any]] = []
    for s in slides:
        bullets = s["bullets"]
        if sum(estimate_lines(b) for b in bullets) <= MAX_LINES_PER_SLIDE:
            out.append(s)
            continue
        chunk: list[str] = []
        used = 0
        part = 1
        for b in bullets:
            need = estimate_lines(b)
            if chunk and used + need > MAX_LINES_PER_SLIDE:
                title = s["title"] if part == 1 else f"{s['title']}（续 {part}）"
                out.append({"title": title, "bullets": chunk})
                part += 1
                chunk, used = [], 0
            chunk.append(b)
            used += need
        if chunk:
            title = s["title"] if part == 1 else f"{s['title']}（续 {part}）"
            out.append({"title": title, "bullets": chunk})
    return out


def build_slides(blocks: list[tuple[str, Any]], *, title: str) -> list[dict[str, Any]]:
    """内容块 → 幻灯片模型（**纯函数，可离线测**）。

    映射规则（简单到不需要解释，也不需要"智能摘要"）：
      · `h1` → 首页标题；`h2` → **新开一页**（标题用 h2 的文字）；
      · `h3` → 当页的一级要点（加 `【】` 前缀）；
      · `ul` → 要点列表；`p` → 一段要点；`pre`（依据区）→ 逐行要点。
    ⚠ 返回的是**内容页**（≤ `MAX_SLIDES - 1` 张）；末页由 `write_slide_deck` 加，
    这样**交付物总页数 ≤ `MAX_SLIDES`**（复核 b7 的 MEDIUM-2）。
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
    out = _paginate(out)
    cap = MAX_SLIDES - 1          # 留 1 张给末页（交付物总数因此 ≤ MAX_SLIDES）
    if len(out) > cap:
        kept = out[:cap - 1]
        # ⚠ **丢了多少条要点必须写在页上**（2026-09-17 独立复核 b8 的 MEDIUM-2）：
        # 页数上限一旦触发，超出的内容就**真的没了**——复核实测"三份清单各 200 条"
        # 这个**在报告自己的设计范围内**的输入会丢掉 47% 的要点，而上一版的措辞是
        # "条数守恒（续页不丢内容）"，只说了续页那一半。现在把丢的条数算出来写清。
        total_bullets = sum(len(s["bullets"]) for s in out)
        kept_bullets = sum(len(s["bullets"]) for s in kept)
        dropped = total_bullets - kept_bullets
        kept.append({"title": "（内容较多，后续请见 Markdown 报告）",
                     "bullets": [f"完整报告共 {len(out)} 页内容，本 PPT 只放了前 "
                                 f"{cap - 1} 页。",
                                 f"**另有 {dropped} 条要点未放入本 PPT**"
                                 f"（共 {total_bullets} 条，这里放了 {kept_bullets} 条）"
                                 "——完整清单见同名 Markdown 报告。"]})
        return kept
    return out


def limits_from_blocks(blocks: list[tuple[str, Any]]) -> list[str]:
    """从报告块里取**"已知限制"那一节**（`## 六、已知限制` 之后的第一个 `ul`）。

    ⚠ 这是"内容只有一个所有者"的落点（复核 b7 的 MEDIUM-3）：末页那几句以前是**手写**的，
    于是 PPT 与报告各说各的。现在从**同一份块**取——报告改了什么，PPT 跟着变。

    取不到时**不编造**：返回一条说明"报告里没有这一节"（那是异常状态，要看得见）。
    """
    hit = False
    for kind, payload in blocks:
        if kind == "h2":
            hit = "已知限制" in str(payload)
            continue
        if hit and kind == "ul":
            return [_plain(str(x)) for x in payload]
    return ["（报告里没有『已知限制』一节——这本身是异常，请核对报告）"]


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
    # 末页：把"这份 PPT 不保证什么"写进去（诚实边界要跟上产出物，不能只写在文档里）。
    # ⚠ 内容**从报告块里取**（`limits_from_blocks`），不是在这里手写第二份
    #   ——复核 b7 的 MEDIUM-3：手写的那 4 句与报告 §六 分叉（PPT 多 3 句、报告多 2 句）。
    tail = prs.slides.add_slide(blank)
    tf = tail.shapes.add_textbox(0, 0, prs.slide_width, 900_000).text_frame
    tf.text = "说明"
    bf = tail.shapes.add_textbox(0, 1_000_000, prs.slide_width,
                                 prs.slide_height - 1_200_000).text_frame
    bf.word_wrap = True
    notes = [f"生成时间：{datetime.now():%Y-%m-%d %H:%M}（本机生成，未外发）"]
    notes.extend(limits_from_blocks(model["blocks"]))
    notes.append("本 PPT 与同名 Markdown 报告**同一份内容**（同一份内容块渲染）。")
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
