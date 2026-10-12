"""MinerU middle 产物的**结构归一**与未知形状的**大声报错**（2026-10-07 立）。

## 为什么要有这个模块（实测背景）
MinerU **4.0** 把 middle 产物的顶层结构换了：
 · **3.4**：``{"pdf_info": [{"page_idx", "page_size", "para_blocks": [...]}, ...]}``
 · **4.0**：``{"schema": "docvortex.middle", "schema_version": "2.0",
   "pages": [{"page_idx", "blocks": [...]}, ...],
   "extensions": {"docvortex_layout": {"pages": [{"width_pt", "height_pt"}]}}}``

而 ``pipeline.load_middle_items`` 读的是 ``mj.get("pdf_info", [])`` —— 键不在就给空列表 ⇒
**静默返回 0 条、不报错**。业主 2026-10-07 用它 OCR 的 933 本国标实测：
**933/933 本 items=0**，表面"入库成功"，实际一条都没进来。

云通道（``mineru_cloud._validate_middle``）**本来就有**"缺 pdf_info 就拒绝消费"的守卫，
但**本地通道没有** —— 本模块把这个判据收成**单一所有者**，两条通道共用。

## 归一后的形状 = 3.4（``load_middle_items`` 消费的最小充分结构）
``_convert_40_to_34`` 的映射（逐条经 933 本实测验证）：
 · ``pages`` → ``pdf_info``
 · ``pages[i].blocks`` → ``pdf_info[i].para_blocks``
 · 页尺寸 ← ``extensions.docvortex_layout.pages[i].width_pt/height_pt``
 · ``block["content"]``（列表）→ ``block["blocks"]``
 · ``content[].type=text`` → ``lines[].spans[].type=text``；
   ``equation_inline`` → ``inline_equation``（切分层的 ``_spans_rows_scored`` 认它）
 · ``paragraph_title`` / ``doc_title`` → 3.4 的 ``title``（切分层据此判 ``kind='title'``）
 · ``table`` → 子块 ``table_caption`` + ``table_body``；**4.0 的 ``table_body.content`` 直接就是 HTML**
   （3.4 是 ``lines[].spans[].type='table'`` + ``html``，所以这里补包一层）
 · ``image`` → 子块 ``image_caption`` + ``image_body``（span 带 ``image_path``）
 · ``chart`` → 3.4 chart 块（子块文本作题注）
 · ``equation``（独立公式块）→ 文本块内放一个 ``interline_equation`` span
 · ``header`` / ``footer`` / ``page_number`` / ``page_footnote`` → ``discarded_blocks``
   （3.4 里这些本就在 ``discarded_blocks``，``load_middle_items`` 不读 ⇒ 等效跳过）

## 未知形状
既不认 ``pdf_info`` 也不认 ``pages`` ⇒ 抛 :class:`MiddleSchemaError`，**绝不静默返回空**。
测试：``tests/test_middle_schema.py``。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: 3.4 顶层键
SCHEMA_34 = "mineru-3.4"
#: 4.0 顶层键（`schema: docvortex.middle`）
SCHEMA_40 = "mineru-4.0"

#: 4.0 里属于"丢弃块"的类型（3.4 放在 discarded_blocks，load_middle_items 不读）
_DISCARD_40 = frozenset({"header", "footer", "page_number", "page_footnote"})
#: 4.0 里应映射成 3.4 `title` 的类型
_TITLE_40 = frozenset({"paragraph_title", "doc_title", "title"})


class MiddleSchemaError(ValueError):
    """middle 产物结构无法识别（既不是 3.4 也不是 4.0），或读盘/解析失败。

    调用方**不应**吞掉它：静默继续会让"入库成功但一条没有"这种症状离原因更远。
    """


def _as_text(c: Any) -> str:
    """4.0 的 ``content`` 有时候是字符串、有时候是对象列表、还可能**嵌套**。

    实测 GB 39800.8-2024 触发 ``TypeError: sequence item 0: expected str, list found``
    （``"".join(parts)`` 收到 list）——所以这里必须递归展平。
    """
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(x for x in (_as_text(i) for i in c) if x)
    if isinstance(c, dict):
        return _as_text(c.get("content"))
    return ""


def detect_schema(mj: Any) -> str:
    """识别 middle 产物的结构版本。

    Returns:
        :data:`SCHEMA_34` 或 :data:`SCHEMA_40`。

    Raises:
        MiddleSchemaError: 不是 JSON 对象，或两个顶层键都没有。
    """
    if not isinstance(mj, dict):
        raise MiddleSchemaError(
            f"middle 产物顶层不是 JSON 对象（实际 {type(mj).__name__}），无法消费")
    if "pdf_info" in mj:
        return SCHEMA_34
    if "pages" in mj:
        return SCHEMA_40
    raise MiddleSchemaError(
        "middle 产物结构无法识别：既没有 pdf_info（MinerU 3.4）也没有 pages（MinerU 4.0）；"
        f"实际顶层键 = {sorted(mj.keys())[:12]}")


def _spans_of(items: Any) -> list[dict]:
    """4.0 的 ``content`` 列表 → 3.4 的 ``lines[].spans[]``。"""
    if isinstance(items, str):
        items = [{"type": "text", "content": items}]
    spans: list[dict] = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        t = it.get("type")
        c = _as_text(it.get("content"))
        if t in ("text", None) and c:
            spans.append({"type": "text", "content": c})
        elif t in ("equation_inline", "interline_equation") and c:
            spans.append({"type": "inline_equation", "content": c})
    return spans


def _convert_40_to_34(mj: dict) -> dict:
    """MinerU 4.0 结构 → 3.4 结构（``load_middle_items`` 直接可消费）。

    ## ⚠⚠ bbox 单位换算（2026-10-12 修，真缺陷）

    **4.0 的 ``bbox`` 是归一化比例（0~1），3.4 的是绝对点** —— 两者单位不同，
    而本函数原来只做**结构映射**、不做**单位换算**，于是把比例当点直接往下传。

    后果链（实测，`GB 1094.1-2013`）：
      原始 ``[0.116, 0.138, 0.937, 0.176]``（比例）
      → 本函数原样传 → ``calibrate_new`` 按"顶部原点"做 ``y' = H − y``
      → 库里的值 ``[0.116, 3455.82, 0.937, 3455.86]``
      ⇒ **同一行里 x 是比例、y 是"H 减比例"**，前端画出来的"箭头"只有一个点大，
        被退化框闸门拒收 ⇒ **红箭头永远不出现**。

    实测判据（`GB 1094.1-2013` 第 1 页，**7/7 命中**）：
      · 库里的 x 值命中原始 x 集合（**x 未被缩放**）
      · 库里的 y 值命中 ``{H − 原始y}``（**y 只翻转、没乘页高**）

    影响面：**756 篇 / 253,222 条条款（13.7%）**，全部是 `2026-10-07`
    MinerU 4.0 那批标准。

    ⇒ 修法：**在这里**按页尺寸把 bbox 还原成点（``x*W`` / ``y*H``）。
    选这里当修复点的理由（规范所有者）：本模块的职责就是"MinerU 4.0 → 3.4 形状归一"，
    而"4.0 是比例、3.4 是点"正是**两个版本之间的差异**；
    下游（`calibrate_new` 的翻转、`pipeline` 的坐标契约）都按"点"消费，
    不该各自去猜上游是比例还是点（那会让每个消费者都要带一份换算）。

    ⚠ 换算后是**顶部原点**（原始 ``y=0.034`` 是页眉，在页顶）——
    顶部原点 → 底部原点的翻转由既有的 `calibrate_new` 投票负责，**本函数不做翻转**
    （保持"只归一形状与单位、不判原点方向"的单一职责）。
    """
    layout = (((mj.get("extensions") or {}).get("docvortex_layout") or {}).get("pages")) or []
    size_by_idx: dict[Any, list[float]] = {}
    for k, p in enumerate(layout):
        if not isinstance(p, dict):
            continue
        size_by_idx[p.get("page_idx", k)] = [
            float(p.get("width_pt") or 595.0), float(p.get("height_pt") or 841.0)]

    def _to_points(bbox: Any, size: list[float]) -> list[float]:
        """4.0 的**归一化比例** bbox → 3.4 的**绝对点** bbox。

        ⚠ 只在"确实像比例"时才换算：4 个有限数、且**全部落在 [0,1]**。
        若某个坐标 >1，说明这份产物本来就是点（或形状异常）⇒ **原样返回**，
        不猜、不缩 —— 误缩一次会让整份文档的箭头全画错位置，比不画更糟。
        """
        if not (isinstance(bbox, list) and len(bbox) == 4):
            return bbox
        try:
            nums = [float(v) for v in bbox]
        except (TypeError, ValueError):
            return bbox
        if not all(0.0 <= v <= 1.0 for v in nums):
            return bbox
        w, h = float(size[0]), float(size[1])
        return [nums[0] * w, nums[1] * h, nums[2] * w, nums[3] * h]

    pdf_info: list[dict] = []
    for k, pg in enumerate(mj.get("pages") or []):
        if not isinstance(pg, dict):
            continue
        pidx = pg.get("page_idx", k)
        size = size_by_idx.get(pidx, [595.0, 841.0])
        para: list[dict] = []
        discarded: list[dict] = []
        for b in pg.get("blocks") or []:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            bbox = _to_points(b.get("bbox") or [], size)
            if t in _DISCARD_40:
                discarded.append({"type": t, "bbox": bbox})
                continue
            if t == "table":
                cap, html = "", None
                for it in b.get("content") or []:
                    if not isinstance(it, dict):
                        continue
                    if it.get("type") == "table_caption":
                        cap = _as_text(it.get("content"))
                    elif it.get("type") == "table_body":
                        c = it.get("content")
                        if isinstance(c, str) and c.strip().startswith("<"):
                            html = c
                subs: list[dict] = []
                if cap:
                    subs.append({"type": "table_caption",
                                 "lines": [{"spans": [{"type": "text", "content": cap}]}]})
                if html:
                    subs.append({"type": "table_body",
                                 "lines": [{"spans": [{"type": "table", "html": html}]}]})
                para.append({"type": "table", "bbox": bbox, "blocks": subs})
            elif t == "image":
                cap, rel = "", None
                for it in b.get("content") or []:
                    if not isinstance(it, dict):
                        continue
                    if it.get("type") == "image_caption":
                        cap += _as_text(it.get("content"))
                    elif it.get("type") == "image_body":
                        rel = it.get("image_path") or _as_text(it.get("content"))
                subs = []
                if cap:
                    subs.append({"type": "image_caption",
                                 "lines": [{"spans": [{"type": "text", "content": cap}]}]})
                if rel:
                    subs.append({"type": "image_body",
                                 "lines": [{"spans": [{"image_path": rel}]}]})
                para.append({"type": "image", "bbox": bbox, "blocks": subs})
            elif t == "chart":
                txt = " ".join(
                    _as_text(it.get("content")) for it in (b.get("content") or [])
                    if isinstance(it, dict)
                    and it.get("type") in ("chart_caption", "chart_footnote"))
                subs = []
                if txt.strip():
                    subs.append({"type": "chart_caption",
                                 "lines": [{"spans": [{"type": "text", "content": txt}]}]})
                para.append({"type": "chart", "bbox": bbox, "blocks": subs})
            elif t == "equation":
                para.append({"type": "text", "bbox": bbox,
                             "lines": [{"spans": [{"type": "interline_equation",
                                                   "content": _as_text(b.get("content"))}]}]})
            else:
                spans = _spans_of(b.get("content"))
                if spans:
                    para.append({"type": "title" if t in _TITLE_40 else "text",
                                 "bbox": bbox,
                                 "lines": [{"bbox": bbox, "spans": spans}]})
        pdf_info.append({"page_idx": pidx,
                         "page_size": size_by_idx.get(pidx, [595.0, 841.0]),
                         "para_blocks": para,
                         "discarded_blocks": discarded})
    return {"pdf_info": pdf_info}


def normalize_middle(mj: Any, *, source: str = "<memory>") -> dict:
    """把 middle 产物归一成 3.4 形状（``pdf_info`` 顶层键）。

    3.4 产物**原样返回**（不复制、不改写），既有调用方行为一字不变。

    Raises:
        MiddleSchemaError: 结构无法识别。
    """
    schema = detect_schema(mj)
    if schema == SCHEMA_34:
        return mj
    return _convert_40_to_34(mj)


def load_middle_json(path: Path) -> dict:
    """读 middle 产物文件并归一成 3.4 形状。

    Raises:
        MiddleSchemaError: 读盘/解析失败，或结构无法识别（含文件不存在）。
    """
    p = Path(path)
    try:
        mj = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 —— 统一翻成一句人话，别让调用方各自 try
        raise MiddleSchemaError(f"middle 产物读取/解析失败（{p.name}）: {e}") from e
    return normalize_middle(mj, source=str(p))
