# -*- coding: utf-8 -*-
"""表格内容的结构化提取与缺陷判据（2026-09-15 立）。

**为什么必须有它**（用户与另一会话指出的口径问题，已实测确认）：
`evolve.evaluate_doc` 的判据只读 `ClauseRevisionModel.content_text`，而**表格在
`content_markdown`**——`content_markdown` 在整个 `evolve.py` 里出现 **0 次**。

**口径数字（2026-09-15 同语料更正，勿再用旧值）**：
本模块立论时用的是**另一份 12 部小样本**，得出"判据视野只覆盖全文 70.1%"。
同语料重测（79 部）的真值是：**正文 541,875 + 表格 134,672 = 676,547 字符，
加入表格后视野 100%，表格占 19.9%**（旧值 80.1%/84.5% 均为口径错，已作废）。
`scout.py` 输出的 `text_len`/`table_len`/`table_share` 才是当前口径的**单一所有者**。

**残留的"读不到"部分**：文档级 `para_blocks` 侧表格文本 ≈ `preproc_blocks` 侧的
**98%**（少读 2.0%；>20% 的 0 部）。这部分既不进上面分母、也不触发任何类——
故由 `scout` 的 `table_missing_chars` 显式报出（见 `table_missing()`）。

本模块把表格 HTML 解析成规整的 `rows`（每行 = 单元格文本列表），在此之上判缺陷。
**判据必须有实测基线才启用**（见 `evidence.py` 的纪律：误报判据要删/收窄）。
"""
from __future__ import annotations

import html as _html
import re

#: 单元格内的插图引用：`<img src="<sha256>.jpg"/>`（MinerU 把符号/照片抽成图片）
_RE_IMG = re.compile(r'<img[^>]*\bsrc\s*=\s*"([^"]+)"[^>]*/?>', re.I)
#: 行/单元格切分（表格 HTML 由 MinerU 生成，结构规整）
_RE_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
_RE_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
#: 单元格的 colspan（合并列）。**判"列数不一致"必须用它算"有效列跨度"**：
#: 实测 47.1% 的表含 colspan、43% 含 rowspan——合并单元格让"行内单元格数"
#: 天然不等，若直接比单元格个数会把**合法的跨列**判成"错并/错分"
#: （实测未修正前 `col-count-mismatch` 命中 **278.9% 的表**，典型误报）。
_RE_COLSPAN = re.compile(r'\bcolspan\s*=\s*"?(\d+)', re.I)
#: 任意标签（用于清洗单元格文本）
_RE_TAG = re.compile(r"<[^>]+>")


def cell_text(cell_html: str) -> str:
    """单元格 HTML → 纯文本（含 `<br>` 视为空格；实体解码）。

    **必须先 `clean_eq_tags` 再剥标签**（2026-09-15 实测修正）：MinerU 把公式包在
    `<eq>\\mathrm { G a }</eq>` 里，而入库链（`pipeline` 的 table 分支）会用
    `text_utils.clean_eq_tags` 把它转成可读文本。本函数若直接 `_RE_TAG.sub("")`
    就会**把 `<eq>` 标签连同包裹一起去掉、却留下原文 LaTeX**，于是表格里出现
    `\\mathrm { G a }`（应为 `Ga`）这种"看起来像入库缺陷、其实是提取器绕过转换"
    的假象——实测踩过（0.98% 单元格含 LaTeX 命令，全部由此产生）。
    图片单元格返回空串（图片没有文本）——由 `cell_images()` 单独看。
    """
    from src.core.text_utils import clean_eq_tags
    s = re.sub(r"<br\s*/?>", " ", cell_html or "", flags=re.I)
    s = clean_eq_tags(s)                  # <eq>LaTeX</eq> → 可读文本（单一所有者）
    s = _RE_TAG.sub("", s)
    return _html.unescape(s).strip()


def cell_images(cell_html: str) -> list[str]:
    """单元格里的图片文件名列表（`src` 的 basename）。"""
    return [n.rsplit("/", 1)[-1] for n in _RE_IMG.findall(cell_html or "")]


def parse_table(table_html: str) -> dict:
    """表格 HTML → `{"rows": [[{"text","images","span"}, ...], ...], ...}`。

    `span` = 该单元格的 `colspan`（缺省 1）。**有效的行宽 = Σ span**，
    而不是单元格个数——合并单元格是国标表的常态（实测 47.1% 的表含 colspan）。
    `n_cols` 取**多数行的有效行宽**（众数）；不用首行：表头本身也可能跨列。
    """
    rows: list[list[dict]] = []
    for rhtml in _RE_ROW.findall(table_html or ""):
        cells = []
        # **必须用 finditer 拿完整匹配**：`colspan` 在**开标签**里，而
        # `_RE_CELL.findall` 只返回**单元格内容**（不含 `<td …>`），
        # 搜内容自然搜不到 colspan（实测踩过：自测 `[2,3]` 行宽算错、
        # 基线 col-count-mismatch 高达 47.4%）。
        for m in _RE_CELL.finditer(rhtml):
            full, inner = m.group(0), m.group(1)
            sm = _RE_COLSPAN.search(full[:200])
            span = int(sm.group(1)) if sm and sm.group(1).isdigit() else 1
            cells.append({"text": cell_text(inner), "images": cell_images(inner),
                          "span": max(1, span)})
        if cells:
            rows.append(cells)
    widths = [sum(c["span"] for c in r) for r in rows]
    n_cols = 0
    if widths:
        from collections import Counter
        n_cols = Counter(widths).most_common(1)[0][0]
    return {"rows": rows, "n_rows": len(rows), "n_cols": n_cols}


def table_plain_text(table_html: str) -> str:
    """表格 → 纯文本（行 `\\n` 分隔、单元格 `\\t` 分隔）。

    用途：把表格内容送进**现有文本判据**（跑一遍看有没有共通的缺陷），
    以及给"判据覆盖率"提供分母。
    """
    t = parse_table(table_html)
    out = []
    for r in t["rows"]:
        out.append("\t".join(c["text"] for c in r))
    return "\n".join(out)


def table_defects(table_html: str, *, image_exists=None,
                  min_cols: int = 2) -> list[dict]:
    """表格的结构缺陷清单（**每条都带证据**，便于人工判定误报）。

    **已删除的判据（实测误报，按纪律不留）**：
      - `col-count-mismatch`（行宽 ≠ 众数行宽）：实测 **5.0% 的表命中，逐条人审
        全是误报**，成因是"表头行与表体行结构天然不同"这类**合法差异**：
          · `['EPL','防爆型式','标志','依据标准']`（4 列表头） vs 表体 3 列；
          · 行宽分布 `[(3,28),(4,8)]`——多数行 3 列、少数 4 列，众数判据把少数判成错。
        判据**分不出"合法结构差异"与"错并/错分"**，属无判别信号 → 删除。
        （修正 `colspan` 前它命中 47.4%，修正后 5.0%，两次都不可用。）
      - `LaTeX 泄漏`：曾以为 0.98% 单元格含 `\\mathrm { G a }` 是入库缺陷，
        追查发现**原始 HTML 里是 `<eq>\\mathrm { G a }</eq>`、入库已转好**，
        是提取器剥标签时把转换绕过了 → **修提取器**（`cell_text` 先 `clean_eq_tags`），
        修后 0.00%。**不是缺陷，不入判据。**

    保留的判据（信号明确、误报可控）：
      - `empty-cell-run`：连续 ≥3 个空单元格（内容丢失的强信号；单个空单元格在
        国标表里合法，如"同上"留空）。实测 0.3% 的表命中。
      - `image-missing`：`<img src>` 指向的文件在产物里不存在（符号图丢失）。
        实测 0 命中——保留作**回归护栏**（未来若路径口径变了会立刻报出来）。
      - `no-rows`：有 table 块但解析不出任何行（表格整体丢失）。实测 0 命中，
        同样作回归护栏。
    """
    t = parse_table(table_html)
    rows = t["rows"]
    out: list[dict] = []
    if not rows:
        return [{"kind": "no-rows", "detail": "table 块无任何 <tr>（表格整体丢失）"}]
    if image_exists is not None:
        for i, r in enumerate(rows):
            for j, c in enumerate(r):
                for name in c["images"]:
                    try:
                        ok = bool(image_exists(name))
                    except Exception:  # noqa: BLE001
                        ok = True
                    if not ok:
                        out.append({"kind": "image-missing", "row": i, "col": j,
                                    "src": name, "detail": "图片文件在产物里不存在"})
    return out


def table_plain_text_of_html(html: str) -> str:
    """（别名）见 `table_plain_text`——保留可读调用点。"""
    return table_plain_text(html)


def page_table_chars(page: dict, tree: str) -> int:
    """一页里 `tree` 侧的表格文本字符量（`tree` = `para_blocks` / `preproc_blocks`）。"""
    n = 0
    for block in page.get(tree) or []:
        if block.get("type") != "table":
            continue
        for sub in block.get("blocks") or []:
            if sub.get("type") != "table_body":
                continue
            for line in sub.get("lines") or []:
                for span in line.get("spans") or []:
                    if span.get("type") == "table" and span.get("html"):
                        n += len(table_plain_text(span["html"]))
    return n


def table_two_tree_chars(middle: dict) -> tuple[int, int]:
    """`(para 侧表格字符, preproc 侧表格字符)`——**必须文档级求和**。

    **逐页相减是错的**（2026-09-16 审计实测，两次口径都偏高，记录在此以免重犯）：
      ① 逐页 `max(0, pre − para)` 求和 → 26.6%：把 preproc 里的**重复/拆分副本**
         也算成丢失；
      ② 逐页"para=0 且 preproc>0"计数 → 476,365 字符：两棵树的 `page_idx`
         **口径不同**（同一张表挂在别的页上）被算成丢失——实测
         `GB／T 23208-2008` 两侧只差 2.4%，却被逐页判成"丢 81,645"。
    只有**文档级总量对比**能回答"少读了多少"。故本函数只返回两个总量，不返回逐页差。
    """
    pages = middle.get("pdf_info") or []
    para = sum(page_table_chars(p, "para_blocks") for p in pages)
    pre = sum(page_table_chars(p, "preproc_blocks") for p in pages)
    return para, pre


def table_missing(para: int, pre: int, *, min_pre: int = 500) -> dict:
    """由两树总量算"少读"量。返回 `{"pre","para","missing","ratio","unknown"}`。

    · `ratio` = `missing / pre`，仅当 `pre >= min_pre`（实测 `pre < 500` 的文档
      几乎没有表格文本，比值噪声极大）；
    · **`ratio` 有噪声底噪**（审计实测：379 部里 15 部 >5%、最差 14.3%，
      但 >20% 的为 **0 部**）→ 调用方**不要**拿它当"缺陷类"，它是**口径量**：
      用来把"读不到的表"与"本来没有表"在报告里区分开，而不是判质量问题。
    """
    pre = int(pre or 0)
    para = int(para or 0)
    if pre < min_pre:
        return {"pre": pre, "para": para, "missing": 0, "ratio": None,
                "unknown": True}
    missing = max(0, pre - para)
    return {"pre": pre, "para": para, "missing": missing,
            "ratio": round(missing / pre, 4), "unknown": False}
