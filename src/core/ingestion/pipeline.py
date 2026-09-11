"""T05 完整入库管线：MinerU 深度解析 → middle.json 结构化 → E1-E7 切分
→ 三型分型 → 证据图抽取 → 单事务原子入库（R1）。

用法:
    python -m src.core.ingestion.pipeline <pdf> --standard-no "GB 30871-2022" \
        --name "..." [--doc-type standard|法律法规] [--domain-tags 安全,消防]

坐标契约: middle.json bbox 为 PDF 点、左上原点（y 向下）；source_span 直接存左上原点坐标，
前端 PdfViewer 按「顶部原点→视口」映射高亮（勿用 convertToViewportRectangle 的底部原点翻转）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ulid import ULID

from src.core.config import get_settings
from src.core.domain.models import ClauseRevisionModel, SourceSpanModel
from src.core.ingestion.parser_worker import run_parser_isolated
from src.core.knowledge.classifier import (
    build_hierarchy_path, classify_clause, normalize_clause_number, strip_revision_marks,
)
from src.core.storage import clause_repo
from src.core.storage.sqlite_db import get_db_connection, init_schema, write_transaction

logger = logging.getLogger(__name__)

# 条款号开头（E3）：GB 风格 5.2.1 / 法律风格 第四百九十六条
_CLAUSE_GB = re.compile(r"^(\d+(?:\.\d+){1,4})\s*(.*)$", re.S)
_CLAUSE_LAW = re.compile(r"^(第[一二三四五六七八九十百千]+条)\s*(.*)$", re.S)
_TABLE_CAPTION = re.compile(r"^表\s*([A-Za-z]?\d+(?:\.\d+)*)\s*(.*)$")
# 2026-08-28 续表标记（通用）：国标跨页续表的题注/页眉通行写法"表x…(续)"/"续表x"
_TABLE_CONT = re.compile(r"[(（]\s*续\s*[)）]|^续\s*表")
# 2026-08-28 页眉家具片段（通用）：页码+标准编号。标准编号族模式 = 1-4 个大写
# 字母（GB/HG/YY/QB/NY…）+ 可选 /T + 位数 + 可选小数段 + 年份（—/–/-），
# 适用于全部国标与行标；前面必须紧跟 1-3 位页码才算家具（"4 GB25596—2025表5…"）。
# 长正文里的"按 GB/T 5009.5—2010 测定"无页码前缀 → 不受影响。
# 章级条款头（通用）："1 范围"/"2 术语和定义"——单段号+纯中文短标题。
# _CLAUSE_GB 的 (?:\.\d+){1,4} 要求至少一个点分段，章头永远匹配不上，
# 必须单独识别（25596 人工测试暴露："1 范围"整章在库里消失）。
# 空格可选：文本层 PDF 章头常为 "1范围" 连排（fitz 单行块实测）。
_CHAPTER_CLAUSE = re.compile(r"^(\d{1,2})\s*([\u4e00-\u9fff（）()]{1,14})\s*$")
# 2026-09-01 C2：插图文件名白名单（与 /assets 端点同款——图名不合规不渲染，
# 双闸一致防注入）。
_ASSET_FNAME_RE = re.compile(r"[0-9a-f]{64}\.(?:jpg|jpeg|png)")
_STD_CODE_FRAG = re.compile(
    r"\s*\d{1,3}\s+[A-Z]{1,4}(?:\s?/\s?T)?\s*\d{1,6}(?:\.\d+)*\s*[—–-]\s*\d{4}\s*")
# 整行恰好是标准编号（页眉独立块/封面行）：GB25596—2025、GB/T 223.32—1994 等
_STD_CODE_LINE = re.compile(
    r"^\s*[A-Z]{1,4}(?:\s?/\s?T)?\s*\d{1,6}(?:\.\d+)*\s*[—–-]\s*\d{4}\s*$")
# 2026-08-29 封面日期提取（通用）：GB/GB/T/行标封面通行"YYYY-MM-DD发布 /
# YYYY-MM-DD实施"（ISO 连排或"YYYY年M月D日发布/实施"两种排版；分隔符容错
# -/.）。此前入库从不填 published_at/effective_from → 全库 UI 发布/生效恒"—"。
# 2026-08-29 二补（GB/T 34406 实测）：双层扫描封面日期行是全角数字（２０１７）
# + PUA 连字符（\ue011——原"-"被嵌入字体映射进私用区）→ 匹配前 NFKC 归一 +
# 分隔符字符类纳入 PUA 区间；两种排版（含年/月汉字）统一覆盖。
_COVER_SEP = r"[-/.年\ue000-\uf8ff]"
_COVER_PUB = re.compile(
    rf"(\d{{4}})\s*{_COVER_SEP}\s*(\d{{1,2}})\s*[-/.月\ue000-\uf8ff]\s*(\d{{1,2}})\s*日?\s*发\s*布")
_COVER_EFF = re.compile(
    rf"(\d{{4}})\s*{_COVER_SEP}\s*(\d{{1,2}})\s*[-/.月\ue000-\uf8ff]\s*(\d{{1,2}})\s*日?\s*实\s*施")


def _middle_cover_blocks(mj_path: Path) -> list[dict]:
    """2026-09-01（GB/T 24276 实测）扫描版封面日期兜底：扫描 PDF 的 fitz
    文本层整页为空（文字全靠深度解析产生），_cover_date 只扫 fitz blocks
    → 封面"2017-11-01 发布"永远够不着，发布/生效日期恒空。从 middle.json
    前 2 页提取文本块（与 fitz blocks 同构：{page_number, text}）供同组
    正则复用。找不到/解析失败返回空表（诚实留空，不猜）。"""
    blocks: list[dict] = []
    try:
        mj = json.loads(mj_path.read_text(encoding="utf-8"))
    except Exception:
        return blocks
    for pi, pg in enumerate((mj.get("pdf_info") or [])[:2]):
        for blk in pg.get("para_blocks") or []:
            if blk.get("type") == "image":
                continue
            lines: list[dict] = []
            for sub in blk.get("blocks") or []:
                lines.extend(sub.get("lines") or [])
            lines.extend(blk.get("lines") or [])
            txt = "".join(
                s.get("content", "") for ln in lines for s in ln.get("spans") or [])
            if txt.strip():
                blocks.append({"page_number": pi + 1, "text": txt})
    return blocks
_APPENDIX_HEAD = re.compile(r"^(附\s*录\s*[A-Z一二三四五六七八九十]?|附\s*则)")
# 2026-09-02 目录条目排除（GB/T 1000-2016 实测）：文件目录页写
# "附录A (规范性附录) 绝缘子螺套…"，与真附录头"附 录 A"同形，误设 in_appendix →
# 后续正文章级条款(1/2/3/4)被 `m_chap and not in_appendix` 跳过而全丢。
# 目录条目特征：附录号后紧跟 " (规范性/资料性/推荐性/引导性附录)" 说明。
_DIR_ENTRY_RE = re.compile(
    r"附\s*录\s*[A-Z一二三四五六七八九十]?\s*[（(]\s*(规范性|资料性|推荐性|引导性)\s*附录")
_CHAPTER_HEAD = re.compile(r"^(\d+)\s*[\u4e00-\u9fff]")  # \s*：容忍 _span_norm 压掉章头数字与标题间空格（"1 范围"→"1范围"），否则章级条款被丢
_TOC_HEAD = re.compile(r"^目\s*次")

# E8 表格数值防误判（2026-08-28 生产实测）：化学分析类标准的大表被 MinerU 切成
# 文本行后，行首单元格值（"0.10 0.030 0.002"）满足 _CLAUSE_GB 的 len≥3/含点门槛
# → 每行被切成 0.x 假条款（审计：41% 新产出文档中招，单文档最多数百假条款）。
# 闸门 1：真实 GB 标准章号首段 ∈ 1..60（GB 50xxx 的 "4.0.1" 首段也是 4，
#         从无 0 开头的章；"1103.11" 这类千位数值全是表格数据）。
# 闸门 2：真实条款头号码后极少紧跟 ≥2 个独立数字（表格行特征："4.2 1.5 3.0"）。
_CHAPTER_MAX = 60
_TABULAR_REST = re.compile(r"^\s*\d+(?:\.\d+)?(?:\s+\d+(?:\.\d+)?)")


def _plausible_clause_head(num: str, rest: str | None) -> bool:
    """E8：判断匹配到的条款号是否是真实条款头（而非表格数值行）。"""
    first = num.split(".", 1)[0]
    if not first.isdigit() or not (1 <= int(first) <= _CHAPTER_MAX):
        return False
    # 2026-09-02 修复表格数值误切(GB/T 1031-2009 实测：表值 12.5/6.3/1.6/3.2 被 _CLAUSE_GB 当条款号)：
    # 条款必带标题文字(rest)，孤立数值(rest 空/纯表值)非真条款头。
    if not (rest or "").strip():
        return False
    # 闸门 3（2026-09-01，GB/T 24276 实测）：正文行宽折行后，第二行行首
    # "1.5m时，为了计算…"（量值+单位）恰好匹配编号 → 句子被拦腰切成假条款
    # "1.5"。量值单位是小写拉丁直接粘中文，真条款头不会这样起头（"A类评定"
    # 大写、"pH的测定"后随拉丁，均不受扰）；1~3 个小写拉丁后紧跟中文即拒绝。
    if rest and re.match(r"[a-z]{1,3}[\u4e00-\u9fff]", rest):
        return False
    return not _TABULAR_REST.match(rest or "")


def _std_type(legal_hierarchy: str | None) -> str:
    """2026-08-29 入库推断 standard_type：此前从不传 → 全库默认 'mandatory'，
    GB/T（推荐性）/GB/Z（指导性）全被标成强制。规则（语料级，按层级代号）：
    GB/Z → guiding；含 /T → recommended；其余（GB 城乡强制）→ mandatory。"""
    h = (legal_hierarchy or "").upper().replace("／", "/")
    if "/Z" in h:
        return "guiding"
    if "/T" in h:
        return "recommended"
    return "mandatory"


def _hier_from_no(standard_no: str, fallback: str = "GB") -> str:
    """2026-08-29 从标准号推导效力层级：此前调用方从不传 → 全库默认 'GB'，
    GB/T（推荐性）/GB/Z（指导性）与 GB（强制）在 UI 上不可分。全角／与空格
    容错；无法识别时保留调用方 fallback（法规等非国标路径不受影响）。"""
    n = (standard_no or "").upper().replace("／", "/").replace(" ", "")
    if n.startswith("GB/Z"):
        return "GB/Z"
    if n.startswith("GB/T"):
        return "GB/T"
    if n.startswith("DB"):
        return "DB"
    return fallback


@dataclass
class MidItem:
    """middle.json 归一化条目（阅读顺序）。"""
    kind: str                 # text | table | title | image
    text: str = ""
    html: str | None = None   # table_body html
    caption: str | None = None
    page_idx: int = 0         # 0-based
    bbox: list[float] = field(default_factory=list)  # PDF 点，左上原点
    # 2026-09-01 B5 行级 bbox：与 text 的行序列（\n 分隔）一一对齐的行框
    # （block.lines[].bbox 直取，坐标契约同 bbox：前端 convertToViewportPoint
    # 直消费）；表格条目为空（表格高亮走块级 bbox）。None = 该行框缺失。
    line_boxes: list[list[float] | None] = field(default_factory=list)
    # 2026-09-01 C2 插图：MinerU image_body 的 image_path 相对引用
    # （images/<sha256>.jpg，与 middle.json 同层）。
    image_path: str | None = None


def _spans_rows(node: dict) -> list[tuple[str, list[float] | None]]:
    """行级提取底座（2026-09-01 B5）：[(行文本, 行bbox|None), ...]。

    行界 = block.lines[]（真折行边界）；行 bbox = line.bbox 直取（同 bbox
    契约）。行内 span（text|inline_equation）无缝原位拼回（假行界修复同
    _spans_text：MinerU 把行内数字/字母抽成 LaTeX 公式 span，丢弃 → 正文
    缺内容；逐 span '\\n' join → 一行内正文+公式被强行拆行）。公式 LaTeX
    转可读 Unicode 文本。空行（全 span 空内容）不产出。
    """
    from src.core.text_utils import latex_to_text
    rows: list[tuple[str, list[float] | None]] = []
    for line in node.get("lines") or []:
        parts: list[str] = []
        for span in line.get("spans") or []:
            st = span.get("type")
            content = span.get("content") or ""
            if not content:
                continue
            if st == "text":
                parts.append(content)
            elif st in ("inline_equation", "interline_equation"):
                # 2026-09-01 interline_equation（独立公式行）与 inline 同族：
                # 此前只认 inline_equation，独立公式块（MinerU 抽成整块
                # interline_equation，span type 也是 interline_equation）在
                # 此处 parts 落空 → 整条公式从条目流蒸发（GB/T 24276 实测
                # 24 条公式全部丢失，"公式没识别出来"根因）。同走
                # latex_to_text → 可读 Unicode 文本行，作为独立行入库。
                parts.append(latex_to_text(content))
        if parts:
            rows.append(("".join(parts).strip(),
                         list(line["bbox"]) if line.get("bbox") else None))
    return [(t, b) for t, b in rows if t]


def _spans_text(node: dict) -> str:
    """提取文本块内容（2026-09-01 修假行界 bug：行界=line，行内 span 无缝拼接）。

    **必须包含 inline_equation span**（行内公式）：MinerU 把 "按表4.2规定的
    A类法分级" 里的数字/字母抽成 LaTeX 公式 span，若丢弃 → 正文变成
    "按表 规定的 类法分级"（缺内容），卡片/PDF高亮/WPS 三块错位。
    2026-09-01 扩：独立公式行 span（interline_equation）同族必收——此前
    丢弃导致整条公式蒸发（24276"公式没识别出来"根因）。
    原实现逐 span 用 '\\n' join → 一行内的 正文span+公式span 被强行拆成
    多行（"按表\\n4.2\\n规定的"），卡片文字断裂、证据不连贯。真行界 =
    block.lines[]（MinerU 流式折行边界）；行内 span（text|inline_equation）
    无缝原位拼回。公式 LaTeX 转可读 Unicode 文本。
    """
    return "\n".join(t for t, _ in _spans_rows(node))


def load_middle_items(middle_path: Path) -> tuple[list[MidItem], dict[int, tuple[float, float]]]:
    """解析 middle.json → 阅读顺序条目 + 每页尺寸。

    discarded_blocks（页眉/页脚/页码）直接跳过 —— R65 边角过滤 + E4 跨页杂音消除。
    """
    mj = json.loads(middle_path.read_text(encoding="utf-8"))
    items: list[MidItem] = []
    page_sizes: dict[int, tuple[float, float]] = {}
    for page in mj.get("pdf_info", []):
        pidx = page.get("page_idx", len(page_sizes))
        w, h = page.get("page_size", [595.0, 841.0])
        page_sizes[pidx] = (float(w), float(h))
        for block in page.get("para_blocks") or []:
            btype = block.get("type")
            if btype == "table":
                caption, html = None, None
                for sub in block.get("blocks") or []:
                    st = sub.get("type")
                    if st == "table_caption":
                        caption = _spans_text(sub)
                    elif st == "table_body":
                        for line in sub.get("lines") or []:
                            for span in line.get("spans") or []:
                                if span.get("type") == "table" and span.get("html"):
                                    html = span["html"]
                # 表格 html 里的 <eq> LaTeX 同样入库即转可读（卡片/WPS/编辑器全一致）
                if html:
                    from src.core.text_utils import clean_eq_tags
                    html = clean_eq_tags(html)
                items.append(MidItem(kind="table", text=caption or "", html=html,
                                     caption=caption, page_idx=pidx,
                                     bbox=list(block.get("bbox", []))))
            elif btype == "image":
                # 2026-09-01 C2 插图入库：image_body 的 image_path（相对引用
                # images/<sha256>.jpg）+ image_caption 题注。此前 image 块被
                # 整体跳过，深度解析文档的插图在全文视图消失。
                cap_text, img_rel = "", None
                for sub in block.get("blocks") or []:
                    st = sub.get("type")
                    if st == "image_caption":
                        cap_text = _spans_text(sub)
                    elif st == "image_body":
                        for line in sub.get("lines") or []:
                            for span in line.get("spans") or []:
                                if span.get("image_path"):
                                    img_rel = span["image_path"]
                if img_rel:
                    items.append(MidItem(kind="image", text=cap_text.strip(),
                                         caption=cap_text.strip() or None,
                                         image_path=img_rel, page_idx=pidx,
                                         bbox=list(block.get("bbox", []))))
            else:
                # 2026-09-02 chart（曲线/图表）治本：题注在 blocks 子级 lines
                # （chart 无顶层 lines）——用 _spans_text(sub) 提取题注入正文，
                # 否则图 1-8/A.2/A.5 题注缺失，渲染层只能靠 chart_queue 启发式
                # 兜底（治标）。题注进 content_text 后 _inject_figs 正常注入。
                if btype == "chart":
                    cap = ""
                    for sub in block.get("blocks") or []:
                        cap += _spans_text(sub)
                    if cap:
                        items.append(MidItem(kind="text", text=cap, page_idx=pidx,
                                             bbox=list(block.get("bbox", []))))
                else:
                    text_rows = _spans_rows(block)
                    text = "\n".join(t for t, _ in text_rows)
                    if text:
                        items.append(MidItem(kind="title" if btype == "title" else "text",
                                             text=text, page_idx=pidx,
                                             bbox=list(block.get("bbox", [])),
                                             line_boxes=[b for _, b in text_rows]))
    return items, page_sizes


# 废弃说明（v5 实测修复 2026-08-23）：MinerU middle.json 的 bbox 为 PDF 底部原点（左下 y 向上），
# pipeline 原样直存 source_span，前端 convertToViewportPoint 直接消费。
# 曾误判为"左上原点"并加 _flip_bbox 翻转 → 前端再 H−y 翻转 → 双重翻转黄标镜像。
# 此函数已删除；改坐标契约必须先读 MAINTAINER-GUIDE §4.2 更新版。


@dataclass
class SplitClause:
    number: str
    texts: list[str]
    items: list[MidItem]
    content_type: str = "normal"      # normal | 前置说明 | 附录
    table_html: str | None = None
    table_summary: str | None = None
    bind_table_number: str | None = None
    # 2026-09-01 B3/B5 行级管线：与 texts 行序列（平铺后）对齐的
    # (行文本, 0-based 页号, 行bbox|None)。texts 块与行不严格 1:1（块内多
    # 条款按行拆分 / 编号 "4.\n1" 合并），rows 才是页界与行级高亮的权威
    # 来源；家具剥离、[:4000] 截断在 build 阶段于 rows 上重排，保证
    # content_text 行号 ↔ 页号/行框始终对齐。
    rows: list[tuple[str, int, list[float] | None]] = field(default_factory=list)


def _rows_of(txt: str, it: MidItem) -> list[tuple[str, int, list[float] | None]]:
    """文本块 → (行, 页号, 行bbox) 行级序列（B3 页界 / B5 行级高亮数据源）。

    行 bbox 与 it.line_boxes 按行号对齐；条数失配（编号合并 "4.\\n1"→"4.1"、
    家具剥离改行）时防御回退全 None——宁缺行框不可错位（错位 = 高亮打歪）。
    """
    lns = txt.split("\n")
    boxes = it.line_boxes if len(it.line_boxes) == len(lns) else [None] * len(lns)
    return [(ln, it.page_idx, b) for ln, b in zip(lns, boxes)]


def split_items_into_clauses(items: list[MidItem]) -> list[SplitClause]:
    """E1-E7 切分主逻辑。

    E1 结构恢复: 依赖 MinerU 阅读顺序块（已做多栏正确排序）
    E2 附录隔离: 附录头之后 → content_type=附录
    E3 变长层级: 编号归一 + hierarchy_path（classify 阶段）
    E4 跨页拼接: 非条款开头的条目并入当前条款（页眉页脚已被 MinerU 丢弃）
    E5 表格绑定: 表 x 关联母条款，html 入 content_markdown
    E6 编号归一 / E7 修订剥离: normalize_clause_number / strip_revision_marks
    """
    clauses: list[SplitClause] = []
    in_toc = False
    in_appendix = False
    current: SplitClause | None = None
    chapter: str | None = None   # 最近章号（还原 MinerU 吞点的条款号 "41"→"4.1"）

    for idx, it in enumerate(items):
        text = strip_revision_marks(it.text or "").strip()
        if not text and it.kind not in ("table", "image"):
            # 2026-08-28：表格条目 text 为空（内容在 html），不能在此跳过，
            # 否则走不到下方表格绑定分支（框线重建表格 0 绑定真凶）。
            # 2026-09-01 C2：无题注插图同理（内容在 image_path，物理就近绑定）。
            continue
        # MinerU 常把条款号拆成 "4.\n1"（数字点换行数字）→ 合并为 4.1
        text = re.sub(r"(\d)\.\s*\n\s*(?=\d)", r"\1.", text)

        # 2026-08-28 通用页眉家具剥离（Fix B）：页眉里的"页码+标准号"随正文块
        # 落进条款文本（"4 GB25596—2025表5其他指标"→"表5其他指标"）。仅对含
        # 标准号片段的 ≤80 字短块生效；全剥空则整块丢弃（纯页眉块）。
        if len(text) <= 80 and _STD_CODE_FRAG.search(text):
            stripped = _STD_CODE_FRAG.sub(" ", text).strip()
            if not stripped:
                continue
            text = stripped

        if _TOC_HEAD.match(text):
            in_toc = True
            continue
        if in_toc:
            # 目次结束判定：出现第一个正文章节头或条款号
            if _CHAPTER_HEAD.match(text) or _CLAUSE_GB.match(text):
                in_toc = False
            else:
                continue

        if _APPENDIX_HEAD.match(text) and not _DIR_ENTRY_RE.match(text):
            in_appendix = True
            current = SplitClause(number=normalize_clause_number(text[:24]),
                                  texts=[text], items=[it], content_type="附录",
                                  rows=_rows_of(text, it))
            clauses.append(current)
            continue

        if it.kind == "table":
            cap = (it.caption or "").strip()
            # 2026-08-28 题注同样过页眉家具剥离（"表5其他指标"前的页码+标准号）
            if len(cap) <= 80 and _STD_CODE_FRAG.search(cap):
                cap = _STD_CODE_FRAG.sub(" ", cap).strip()
            m = _TABLE_CAPTION.match(cap)
            bind_no = normalize_clause_number(m.group(1)) if m else None
            summary = (m.group(2).strip() if m and m.group(2) else cap)[:120]
            is_cont = bool(_TABLE_CONT.search(cap))
            target = None
            # 2026-08-29 引用优先绑定（通用）：表x 的母条款 = 最近一个文内
            # 引用"表x"的条款（"应符合表x的规定"是国标通行句式）。旧逻辑按
            # 条款号裸匹配（bind_no==条款号即挂），章级条款修复后 "表1/表2/表3"
            # 的题注号撞上新章节点 1/2/3，正文必需成分表被抢挂到"1 范围"
            # "2 术语和定义"（25596 人工测试暴露）。引用判定带词边界
            # （"表1"不误配"表1.1/表12"）；无引用 → (续) 表走续表规则；
            # 再无 → 物理就近（current），号码裸匹配彻底废弃。
            pat_tab = (re.compile(rf"表\s*{re.escape(bind_no)}(?![\d.])")
                       if bind_no else None)
            # 2026-09-02 治本：表归属**物理就近优先**——表物理在哪页就归哪个
            # 条款（表 1 在 6 章 p10 归 6 章）。引用优先曾因"表1/表2/表3 题注
            # 号撞上新章节点 1/2/3"而引入，但把表 1（物理 6 章）误绑到引用它
            # 的 5.2.4 → 表显示在 5.2.4 而非物理 6 章 = 表位置错（24276 实测）。
            # 顺序：物理就近(current) → 引用（仅当物理无且非续表）→ 续表。
            target = current
            if target is None and pat_tab is not None:
                for c in reversed(clauses):
                    if any(pat_tab.search(t or "") for t in c.texts):
                        target = c
                        break
            if target is None and is_cont:
                target = next((c for c in reversed(clauses) if c.table_html), None)
            if target is not None:
                # 2026-08-28 追加而非覆盖（通用）：同一条款可对应多张表
                # （表x 正表+续表、附录表跨 3-4 页），旧逻辑"覆盖/先到优先"
                # 都会把后续表整段丢掉（25596 实测 15 张表只入库 9 张）。
                # 2026-09-02 防 None：it.html/原 table_html 可能为空（表 html
                # 缺失）→ str+None 报错（1032 实测），统一 or "" 兜底。
                target.table_html = (target.table_html or "") + (it.html or "")
                if summary and not target.table_summary:
                    target.table_summary = summary
                target.items.append(it)
                continue
            clauses.append(SplitClause(number=f"表{bind_no or ULID().hex[:4]}",
                                       texts=[cap], items=[it],
                                       rows=[(cap, it.page_idx, None)],
                                       table_html=it.html, table_summary=summary or None))
            continue

        if it.kind == "image":
            # 2026-09-01 C2 插图绑定：图N 题注引用优先（"如图N所示"通行句式，
            # 词边界防 图1 误中 图1.1/图12），无引用 → 物理就近（current）——
            # 插图在阅读序上紧跟所属条款。全失配 → 独立"图"条款。
            cap = (it.caption or "").strip()
            m_fig = re.match(r"^图\s*([0-9A-Za-z.]+)", cap)
            target = None
            if m_fig:
                pat_fig = re.compile(rf"图\s*{re.escape(m_fig.group(1))}(?![\d.])")
                for c in reversed(clauses):
                    if any(pat_fig.search(t or "") for t in c.texts):
                        target = c
                        break
            if target is None:
                target = current
            if target is not None:
                target.items.append(it)
                continue
            clauses.append(SplitClause(
                number=f"图{m_fig.group(1) if m_fig else ULID().hex[:4]}",
                texts=[cap] if cap else [], items=[it],
                rows=[(cap, it.page_idx, None)] if cap else []))
            continue

        # 还原 MinerU 吞点条款号：章号紧跟的 "41 xxx" → "4.1 xxx"
        if not _CLAUSE_GB.match(text) and chapter:
            m41 = re.match(r"^(\d)(\d{1,2})\s", text)
            if m41 and m41.group(1) == chapter:
                text = m41.group(1) + "." + m41.group(2) + text[len(m41.group(0)) - 1:]
        # 章号跟踪（"4 高处作业分级" 样式）
        mch = _CHAPTER_HEAD.match(text)
        if mch:
            chapter = mch.group(1)

        m_gb = _CLAUSE_GB.match(text)
        m_law = _CLAUSE_LAW.match(text)
        # 2026-08-29 章级条款（通用）：单段章号也是真实条款——"1 范围"
        # "2 术语和定义" "3 技术要求" "4 其他"。旧闸门只认带点号（len>=3 或
        # 含"."），章标题整段被吞进上一条款，"1 范围"在库里消失（25596 人工
        # 测试暴露；全语料国标同构）。放宽 + 三重护栏防误伤：
        #   ① 号 = 1-2 位纯数字，标题 = 纯中文/括号 ≤14 字（目录行带点线
        #      引导符"1 范围……1"天然过不了）；
        #   ② 下一项不是同级连排号（"1 加入试剂"+"2 称取样品"式正文列举）
        #      也不是孤立页码——真章头后跟正文句或子条款号；
        #   ③ 原有 _plausible_clause_head 数值行排除继续生效。
        is_chapter = False
        m_chap = None if m_gb else _CHAPTER_CLAUSE.match(text)
        if m_chap and not in_appendix:
            nxt = (items[idx + 1].text or "").strip() if idx + 1 < len(items) else ""
            prv = (items[idx - 1].text or "").strip() if idx else ""
            # 护栏：下一项是同级连排号（"1 加入试剂"+"2 称取样品"式正文列举，
            # 目次行 "1 范围"/"2 术语和定义" 连排同样命中）或孤立页码 → 不是章头；
            # 目录行点线引导符过不了纯中文标题闸门；列表末项（下一项为空且上一项
            # 同级连排）同样拒绝——真章头后必有正文句或子条款号。
            # 同级判定 = 单段号后紧跟中文（\s* 兼容无空格连排；"2.1"带点不命中）。
            _sib = re.compile(r"^\d{1,2}\s*[\u4e00-\u9fff（）(]")
            is_chapter = not (
                _sib.match(nxt) or nxt.isdigit()
                or (not nxt and _sib.match(prv)))
        if (m_gb and _plausible_clause_head(m_gb.group(1), m_gb.group(2))
                and (in_appendix or len(m_gb.group(1)) >= 3
                     or m_gb.group(1).count(".") >= 1)):
            number = normalize_clause_number(m_gb.group(1))
            current = SplitClause(number=number, texts=[text], items=[it],
                                  content_type="附录" if in_appendix else "normal",
                                  rows=_rows_of(text, it))
            clauses.append(current)
        elif m_chap and is_chapter and _plausible_clause_head(
                m_chap.group(1), m_chap.group(2)):
            current = SplitClause(number=m_chap.group(1), texts=[text],
                                  items=[it], rows=_rows_of(text, it))
            clauses.append(current)
        elif m_law:
            current = SplitClause(number=m_law.group(1), texts=[text], items=[it],
                                  rows=_rows_of(text, it))
            clauses.append(current)
        else:
            # 块内可能含多个条款（章标题+条款同块）：按行拆分
            lines = text.split("\n")
            if len(lines) > 1:
                # 行框与行号对齐（编号合并/家具剥离改行致失配 → 全 None 防错位）
                boxes = (it.line_boxes if len(it.line_boxes) == len(lines)
                         else [None] * len(lines))
                i = 0
                while i < len(lines):
                    ln = lines[i].strip()
                    if not ln:
                        i += 1
                        continue
                    mm = _CLAUSE_GB.match(ln)
                    num = mm.group(1) if mm else ""
                    is_head = (bool(mm) and (len(num) >= 3 or num.count(".") >= 1)
                               and _plausible_clause_head(num, mm.group(2)))
                    if is_head:
                        cur = SplitClause(number=normalize_clause_number(num),
                                          texts=[ln], items=[it], content_type="normal",
                                          rows=[(ln, it.page_idx, boxes[i])])
                        clauses.append(cur)
                        i += 1
                        while i < len(lines):
                            nxt = lines[i].strip()
                            m2 = _CLAUSE_GB.match(nxt)
                            n2 = m2.group(1) if m2 else ""
                            if (m2 and (len(n2) >= 3 or n2.count(".") >= 1)
                                    and _plausible_clause_head(n2, m2.group(2))):
                                break
                            cur.texts.append(nxt)
                            cur.rows.append((nxt, it.page_idx, boxes[i]))
                            i += 1
                        continue
                    if current is not None:
                        current.texts.append(ln)
                        current.items.append(it)
                        current.rows.append((ln, it.page_idx, boxes[i]))
                    i += 1
            elif current is not None:
                current.texts.append(text)
                current.items.append(it)
                current.rows.extend(_rows_of(text, it))
            else:
                # 正文前内容（封面/前言/引言）→ 前置说明（R65）
                current = SplitClause(number=f"前置{len(clauses) + 1}", texts=[text],
                                      items=[it], content_type="前置说明",
                                      rows=_rows_of(text, it))
                clauses.append(current)
    return clauses


def build_clause_models(doc_id: str, standard_no: str, doc_type: str,
                        clauses: list[SplitClause],
                        page_sizes: dict[int, tuple[float, float]],
                        ) -> tuple[list[ClauseRevisionModel], list[dict[str, Any]]]:
    """切分结果 → Pydantic 模型 + 证据图边（raw，source/target 用条款号表示）。"""
    models: list[ClauseRevisionModel] = []
    raw_edges: list[dict[str, Any]] = []
    number_to_id: dict[str, str] = {}

    for cl in clauses:
        # 2026-09-01 B3/B5 行级管线：rows = (行, 0-based 页号, 行bbox) 是页界
        # 与行级高亮的唯一权威来源；[:4000] 截断、家具剥离、页界采集全部在
        # rows 上做，保证 content_text 行号 ↔ 页号/行框始终对齐。
        rows = list(cl.rows)
        content = "\n".join(r[0] for r in rows)[:4000]
        # 2026-09-01 C2 插图占位（build 组装）：MinerU 预裁剪插图 → 无 src
        # img（/assets 受 Bearer 保护，前端 apiFetch 拉 blob 填 src，C1 资产
        # 端点回源 parse_out）。图名白名单与端点同款正则（双闸一致），不合规
        # 图名不渲染；alt 文本去尖括号防注入。
        fig_html = ""
        for it in cl.items:
            if it.kind != "image" or not it.image_path:
                continue
            fname = it.image_path.replace("\\", "/").rsplit("/", 1)[-1]
            if not _ASSET_FNAME_RE.fullmatch(fname):
                continue
            alt = ((it.caption or "插图").replace('"', "'")
                   .replace("<", "（").replace(">", "）"))
            fig_html += (f'<p class="fig-strip"><img class="asset-embed" '
                         f'data-asset="{fname}" alt="{alt}" loading="lazy"/></p>')
        # 2026-08-29 章头豁免（通用）：<4 守卫会把"4其他"这类 3 字章级标题
        # 当碎片丢弃（2术语和定义/3技术要求因字数≥4 幸存，纯看字数不公平）。
        # 首段是章头形态（与 split 同一正则判定）→ 保留，这是真实章节点。
        # 2026-09-01 B4 表格身份豁免：无题注表格条款 content_text 为空（正文
        # 只有表体 html，走 content_markdown），<4 守卫会把整张表丢掉
        # （GB/T 24276 B.1 表头图实测）——表格/插图条款跳过字数守卫。
        if (len(content.strip()) < 4 and not cl.table_html and not fig_html
                and not (cl.texts and _CHAPTER_CLAUSE.match(cl.texts[0].strip()))):
            continue
        # 2026-08-28 兜底逐行家具剥离（通用）：MinerU 路径的页眉可能与正文
        # 预合并成一行（'4 GB25596—2025表5其他指标'），块层剔除够不着；此处对
        # 残留合并形态按行再剥一次，整行标准号直接丢弃。模式本身即护栏
        # （须"数字+空格+标准号-年"连排），长正文引用不受影响。
        # （2026-09-01 B3：在 rows 上剥离，整行丢弃时同步剔除其页号/行框，
        # 行号与页界编码不漂移。）
        stripped_rows: list[tuple[str, int, list[float] | None]] = []
        for ln, pidx, lbox in rows:
            if _STD_CODE_LINE.match(ln):
                continue
            if _STD_CODE_FRAG.search(ln):
                s2 = _STD_CODE_FRAG.sub(" ", ln).strip()
                if not s2 or (len(s2) <= 3 and s2.isdigit()):
                    continue  # 整行即页码+标准号对，剥完只剩页码 → 丢
                ln = s2
            stripped_rows.append((ln, pidx, lbox))
        # [:4000] 截断（rows 语义：整行入账，末行可截半；+1 = join 换行符）
        final_rows: list[tuple[str, int, list[float] | None]] = []
        budget = 4000
        for ln, pidx, lbox in stripped_rows:
            if budget <= 0:
                break
            take = ln if len(ln) <= budget else ln[:budget]
            budget -= len(take) + 1
            final_rows.append((take, pidx, lbox))
        content = "\n".join(r[0] for r in final_rows)
        # 2026-08-30 国标排版还原三件套·入库路（与 _content_html 出口重放同
        # 规则、形态收敛）：PUA 键横线→—（等长）、单位负指数→Unicode 上标
        # （cm⁻¹，与 latex_to_text 纪律一致）、段首编号补空格。仅作用于新
        # 入库快照（入库清洗属快照内容，非篡改）；存量不动（快照不可变），
        # 展示由出口重放兜底——渲染同形，纯文本面（AI 引用/WPS/FTS）新档
        # 即干净。（三件套全部行内改写、不改行数 → 行号稳定，页界编码不受扰。）
        from src.core.text_utils import (
            pua_bond_dash_html as _pua_dash, space_clause_numbers_text,
            sup_unit_exponents_text)
        content = space_clause_numbers_text(
            sup_unit_exponents_text(_pua_dash(content)))
        tc = classify_clause(content, doc_type=doc_type)
        cid = f"clrev_{ULID()}"
        number_to_id[cl.number] = cid
        pages = [it.page_idx + 1 for it in cl.items]
        # 2026-09-01 B3 页界入库：run-start 编码 [[行号, PDF页码], ...]（行号 =
        # content_text 0-based 行索引，首个条目恒为 [0, 首行所在页]）。渲染层
        # 按行号在段间插页界分隔（「原文哪里换页就哪里换页」）。
        page_breaks: list[list[int]] = []
        last_pg: int | None = None
        for i, (_ln, pidx, _b) in enumerate(final_rows):
            if last_pg is None or pidx != last_pg:
                page_breaks.append([i, pidx + 1])
                last_pg = pidx
        # 2026-09-01 B5 行级 bbox 全量入库：取消 [:8] 封顶（第 9 块起证据高亮
        # 全灭的真 bug）；文本块降为行级 span（bbox 精确到折行行），表格保留
        # 块级。行框整体缺失（旧 json 无 line.bbox / 编号合并失配）→ 回退块级
        # span（宁粗不高灭），不是双轨并存。坐标契约同 bbox：前端
        # convertToViewportPoint 直消费。
        line_spans = [SourceSpanModel(
            span_id=f"span_{ULID()}", page_number=pidx + 1, bbox=list(lbox),
            span_type="text", sort_order=i)
            for i, (_ln, pidx, lbox) in enumerate(final_rows) if lbox]
        table_spans = [SourceSpanModel(
            span_id=f"span_{ULID()}", page_number=it.page_idx + 1,
            bbox=list(it.bbox), span_type="table")
            for it in cl.items if it.kind == "table"]
        if line_spans:
            spans = line_spans + table_spans
        else:
            # 行框不可用（无 line.bbox / 编号合并失配）→ 块级兜底（含表格）；
            # 空 bbox 条目跳过（bbox 空的 span 过不了模型校验，宁缺不高灭）；
            # 插图不是文本证据，不产 span（高亮/跳页只对文本与表格）。
            spans = [SourceSpanModel(
                span_id=f"span_{ULID()}", page_number=it.page_idx + 1,
                bbox=list(it.bbox),
                span_type="table" if it.kind == "table" else "text")
                for it in cl.items if it.bbox and it.kind != "image"]
        for i, s in enumerate(spans):
            s.sort_order = i
        # 2026-09-01 B4 表格身份：无题注表格条款（引用/续表/就近绑定全部失配
        # 落单、cap 为空）此前只有 "表"+ULID 片段的随机号且整表被守卫丢弃，
        # 证据卡/目录无法辨识 → 给可读身份「表(未识别题注，第N页)」。
        # 有题注的表格 table_summary 原语义不动。
        # C2 同理：无题注插图独立落单 → 「图(未识别题注，第N页)」。
        title = None
        if cl.table_html and cl.number.startswith("表") and not cl.table_summary:
            title = f"表(未识别题注，第{min(pages)}页)"
        elif (cl.number.startswith("图") and not any(
                it.caption for it in cl.items if it.kind == "image")):
            title = f"图(未识别题注，第{min(pages)}页)"
        models.append(ClauseRevisionModel(
            clause_revision_id=cid,
            doc_id=doc_id,
            clause_key=clause_repo.make_clause_key(doc_id, cl.number),
            standard_no=standard_no,
            clause_number=cl.number,
            title=title,
            content_text=content,
            content_markdown=cl.table_html,
            table_summary=cl.table_summary,
            hierarchy_path=build_hierarchy_path(cl.number) or None,
            knowledge_type=tc.knowledge_type,
            type_confidence=tc.type_confidence,
            modality=tc.modality,
            modality_strength=tc.modality_strength,
            modality_confidence=tc.modality_confidence,
            subject=tc.subject,
            exception=tc.exception,
            legal_refs=tc.external_refs,
            cross_refs=tc.cross_refs,
            is_mandatory=tc.is_mandatory,
            is_suspicious=tc.is_suspicious,
            page_start=min(pages), page_end=max(pages),
            page_breaks=page_breaks or None,
            figure_html=fig_html or None,
            source_spans=spans,
        ))

    # 证据图：reference_relation（内部引用）+ clause_relation（表绑定）
    for m in models:
        for ref in m.cross_refs:
            raw_edges.append({"edge_type": "reference_relation",
                              "src": m.clause_number, "dst": ref,
                              "conf": 0.9, "status": "active"})
        if m.table_summary:
            raw_edges.append({"edge_type": "clause_relation",
                              "src": m.clause_number, "dst": m.clause_number,
                              "conf": 1.0, "status": "active"})
    # exception_relation: 含但书条款 → 同号"注"条款（若存在）
    for m in models:
        if m.exception:
            note_no = f"{m.clause_number}注"
            if note_no in number_to_id:
                raw_edges.append({"edge_type": "exception_relation",
                                  "src": m.clause_number, "dst": note_no,
                                  "conf": 0.85, "status": "active"})
    return models, raw_edges


def resolve_edges(raw_edges: list[dict[str, Any]],
                  number_to_id: dict[str, str]) -> list[tuple[str, str, str, float, str]]:
    out = []
    for e in raw_edges:
        if e["edge_type"] == "clause_relation":
            continue  # 表绑定已落在同一条款内部，不建自环边
        src, dst = number_to_id.get(e["src"]), number_to_id.get(e["dst"])
        if src and dst and src != dst:
            out.append((e["edge_type"], src, dst, e["conf"], e["status"]))
    return out


def analyze_preview(pdf_path: Path) -> dict:
    """R27 入库预览 Dry-Run（Task 11.5）：解析但不落库，输出切分/分型/质量预览。

    走快速文本层路径（force_deep=False，不调 MinerU 深度模型），秒级返回；
    供入库前人工确认（拦截乱码/严重倾斜文档）。
    """
    from src.core.ingestion.parser_worker import run_parser_isolated
    from src.core.knowledge.classifier import classify_clause
    if not pdf_path.exists():
        return {"status": "error", "message": f"文件不存在: {pdf_path}"}
    result = run_parser_isolated(pdf_path, get_settings().data_dir / "preview_tmp",
                                 force_deep=False)
    items, _ = load_middle_items_from_blocks(result["blocks"])
    clauses = split_items_into_clauses(items)
    previews = []
    for cl in clauses:
        content = "\n".join(cl.texts)
        if len(content.strip()) < 4:
            continue
        tc = classify_clause(content)
        previews.append({"number": cl.number, "text_len": len(content),
                         "knowledge_type": tc.knowledge_type,
                         "modality": tc.modality, "suspicious": tc.is_suspicious})
    type_dist: dict[str, int] = {}
    for p in previews:
        type_dist[p["knowledge_type"]] = type_dist.get(p["knowledge_type"], 0) + 1
    n_susp = sum(1 for p in previews if p["suspicious"])
    return {"status": "ok", "total_clauses": len(previews),
            "knowledge_type_distribution": type_dist,
            "suspicious_count": n_susp,
            "sample": previews[:10],
            "pages": len(result["geometries"])}


def load_middle_items_from_blocks(blocks: list[dict]) -> tuple[list[MidItem], dict]:
    """blocks（PyMuPDF 文本块）→ MidItem（供 split_items_into_clauses）。

    文本块按行拆为独立条目（一条条款可能占块内多行，行首条款号需单独识别）。
    2026-08-28：先做块级吞点合并——fitz 常把条款号拆行（'3.'\\n'1 试剂'），
    与 split_items_into_clauses L156 同一正则；必须在拆行**前**合并，否则
    '3.' 与 '1 试剂' 成为独立行，条款号永远拼不回来（5009.124 实测 138→2 条）。
    2026-08-28 页眉家具对剔除（通用）：正文层 PDF 的页眉是两个独立块
    [页码][标准号]（'5'+'GB25596—2025'，GB/HG/YY/QB 全适用），若不剔，
    normalize_wraps 会把这两块与相邻正文拼成 '5 GB25596—2025表7脲酶活性指标'
    家具行。规则：整块即标准号 → 剔；1-3 位纯数字块且紧邻标准号块 → 剔。
    正文里的标准引用（'本标准代替GB25596—2010'）非整行形态，不受影响。
    块内 '4\\n其他' 式拆行章题拼回 '4 其他'（纯数字行+中文行），章号跟踪才不丢。
    """
    n = len(blocks)
    code_flags = [bool(_STD_CODE_LINE.match((b.get("text") or "").strip()))
                  for b in blocks]
    kept: list[dict] = []
    for i, b in enumerate(blocks):
        t = (b.get("text") or "").strip()
        if code_flags[i]:
            continue
        if (t.isdigit() and len(t) <= 3
                and ((i > 0 and code_flags[i - 1])
                     or (i + 1 < n and code_flags[i + 1]))):
            continue
        kept.append(b)
    blocks = kept

    items = []
    _span_norm = re.compile(r"\s*([.\d])\s*")
    _num_merge = re.compile(r"(\d)\.\s*\n\s*(?=\d)")
    _bare_digit_line = re.compile(r"^\d{1,2}$")
    for b in blocks:
        page_idx = int(b.get("page_number", 1)) - 1
        merged = _num_merge.sub(r"\1.", b.get("text", "") or "")
        # 块内拆行章题拼合：'4\n其他' → '4 其他'（仅纯数字行 + 中文起始行）
        lines = [ln for ln in merged.splitlines()]
        joined: list[str] = []
        for ln in lines:
            if (joined and _bare_digit_line.match(joined[-1].strip())
                    and re.match(r"^[\u4e00-\u9fff]", ln.strip())):
                joined[-1] = joined[-1].rstrip() + " " + ln.strip()
            else:
                joined.append(ln)
        for line in joined:
            line = _span_norm.sub(r"\1", line.strip())  # fitz 逐字 span：'5 . 2 . 1'→'5.2.1'
            if line:
                items.append(MidItem(kind="text", text=line, page_idx=page_idx,
                                     bbox=list(b.get("bbox", []))))
    return items, {}


def _cell_html(page, rect, fallback: str, pua: bool = False) -> str:
    """单元格 HTML：按字形渲染——同视觉行 span 按基线聚类（PDF 常把 '0.43'
    拆成 '0.'+'43' 两个独立文本对象，必须聚回一行），小字号 span 按基线
    相对位置判 <sup>/<sub>（脚注字母 a-d、公式下标 A1 的 1:1 关键）；
    字形提取失败退回 extract 纯文本。
    pua=True（2026-08-29，GB/T 34406 实测）：单元格文本直接来自 PDF 原始
    文本层，PUA 错位字体/全角数字需归一化（与 blocks 同口径），否则表格
    md 里残留 '９５．８５' 全角与水印 token。
    """
    import html as _html
    import unicodedata

    import fitz

    from src.core.text_utils import glue_spaced_formulas, normalize_pua_latin

    ph = page.rect.height if hasattr(page, "rect") else 0.0

    def _noise_span(sp: dict, direction=None) -> bool:
        """水印/页边页码 span 判定（2026-08-29，GB/T 34406 实测，语料级）。

        ① 斜排文本：line dir 偏离水平 → 水印。该 PDF 的 'www.bzfxw.com' 是
        45° 斜铺大字（size 72、dir=(0.707,-0.707)），clip 相交时 fitz 对斜排
        span 做**字符级截断**——各 cell 拿到 'om'/'co'/'w.c' 碎片，fullmatch
        URL 抓不到；而国标正文（中文排版）绝无斜排，dir 是最强语料级判据。
        ② URL 水印：span 文本（NFKC 后）整体即 URL token（水平独立网址
        对象）；正文行内 URL 与中文同 span，fullmatch 不命中。
        ③ 页码：纯数字/罗马短 span，仅限页眉 ≤12% 页高或页脚 ≥90% 页高——
        表格数字格 '96' 同形态，不锁位置会删光数据。
        """
        t = (sp.get("text") or "").strip()
        if not t:
            return True
        if direction and abs(float(direction[1])) > 0.01:
            return True
        tn = unicodedata.normalize("NFKC", t)
        if _RE_WM_SPAN_URL.fullmatch(tn):
            return True
        bb = sp.get("bbox") or []
        if ph and len(bb) == 4 and (bb[3] <= ph * 0.12 or bb[1] >= ph * 0.9) \
                and _RE_WM_SPAN_PAGENO.fullmatch(tn):
            return True
        return False

    def _n(s: str) -> str:
        return normalize_pua_latin(s) if pua else s

    try:
        d = page.get_text("dict", clip=fitz.Rect(rect))
        raw = []
        for blk in d.get("blocks", []):
            if blk.get("type") != 0:
                continue
            for ln in blk.get("lines", []):
                direction = ln.get("dir")
                for sp in ln.get("spans", []):
                    if "origin" not in sp or _noise_span(sp, direction):
                        continue
                    raw.append(sp)
    except Exception:
        raw = []
    if not raw:
        txt = _n((fallback or "").replace("\n", " "))
        # fallback（extract 网格切分文本）整段即 URL token → 空格；行中不动
        if _RE_WM_SPAN_URL.fullmatch(unicodedata.normalize("NFKC", txt.strip())):
            txt = ""
        txt = glue_spaced_formulas(txt).strip()
        return _html.escape(txt)
    dom = max(sp.get("size", 0.0) for sp in raw)
    tol = max(4.5, dom * 0.55)  # 行聚类容差：上下标偏移 ~3pt 应并入本行
    raw.sort(key=lambda s: (s["origin"][1], s["origin"][0]))
    clusters: list[list] = []
    for sp in raw:
        y = sp["origin"][1]
        if clusters and abs(y - clusters[-1][0]) <= tol:
            clusters[-1][1].append(sp)
            continue
        # 2026-08-28 通用小数续接（Fix C）：部分标准 PDF 把小数点后的数字
        # 排低半行（"5.0"→'5.'+低半行的'0'、"GB5009.3"→'GB5009.'+'3'），
        # 超出常规聚类容差被拆成两行 → 数值碎裂。规则：前簇末 span 以 '.'
        # 结尾、本 span 为 ≤3 位纯数字、落差 ≤2 倍字高 → 并回本行。
        # "12/2" 这类真实两行数值（12 不以 '.' 结尾）不受影响。
        if clusters:
            prev = sorted(clusters[-1][1], key=lambda s: s["origin"][0])[-1]
            pt = (prev.get("text") or "").strip()
            st = (sp.get("text") or "").strip()
            dy = y - prev["origin"][1]
            if (pt.endswith(".") and st.isdigit() and len(st) <= 3
                    and 0 < dy <= max(4.0, dom * 2.0)):
                clusters[-1][1].append(sp)
                continue
        clusters.append([y, [sp]])

    def _render(cluster: list) -> str:
        spans = sorted(cluster[1], key=lambda s: s["origin"][0])
        dom_ys = sorted(s["origin"][1] for s in spans
                        if s.get("size", 0.0) >= dom * 0.8)
        base_y = dom_ys[len(dom_ys) // 2] if dom_ys else cluster[0]
        segs = []
        for sp in spans:
            txt = _html.escape(glue_spaced_formulas(_n(sp.get("text", ""))))
            txt = re.sub(r"\s+", " ", txt).strip()
            if not txt:
                continue
            if dom and sp.get("size", dom) < dom * 0.8 and len(txt) <= 3:
                oy = sp["origin"][1]
                if oy < base_y - 0.5:
                    txt = f"<sup>{txt}</sup>"
                elif oy > base_y + 0.5:
                    txt = f"<sub>{txt}</sub>"
            segs.append(txt)
        return "".join(segs).strip()

    parts = [_render(c) for c in clusters]
    parts = [p for p in parts if p]
    return "<br>".join(parts) if parts else _html.escape(_n(fallback or ""))


#: 水印 URL / 页边页码形态（_cell_html 抽取侧 span 过滤用）。
#: 注意不能用 fitz redact 做「抽取前页面清理」：apply_redactions 按矩形区域
#: 删文本，斜铺大字水印（GB/T 34406 实测 bbox y219-619 横穿页面中央）的
#: 矩形覆盖表 A.1，cells 正文会整格陪葬——表格整个丢失、数据泄漏成
#: '36.92' 假条款。span 级过滤精确到文本对象，零陪葬。
_RE_WM_SPAN_URL = re.compile(r"www\.[A-Za-z0-9\-]+\.(?:com|cn|net|org)", re.I)
_RE_WM_SPAN_PAGENO = re.compile(r"[IVXivx\dⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]{1,4}")


def _grid_html(table, page, pua: bool = False) -> str:
    """find_tables 表 → 带 rowspan/colspan 的 1:1 HTML 网格。

    结构真源 = fitz cell 矩形：矩形跨几条行界就是 rowspan、跨几条列界就是
    colspan（GB 25596 表1 实测：'指标' colspan=4、'营养素' rowspan=3、
    '脂肪' rowspan=4、脚注行 colspan=6）。文字 = extract() 网格与
    rows[i].cells[j] 逐位对位；对位失败宁可放弃不出错表。
    pua：透传 _cell_html——单元格文本来自 PDF 原始文本层（绕过 blocks
    归一化），PUA 文档必须同口径归一化（2026-08-29，GB/T 34406 表A.1
    全角数字 '９５．８５' 实测）。
    """
    import html as _html

    try:
        grid = table.extract()
        row_cells = [r.cells for r in table.rows]
    except Exception:
        return ""
    if len(grid) != len(row_cells) or any(
            len(g) != len(rc) for g, rc in zip(grid, row_cells)):
        return ""
    ys: list[float] = []
    xs: list[float] = []
    for rc in row_cells:
        for c in rc:
            if c is None:
                continue
            for v in (c[1], c[3]):
                if not any(abs(v - w) < 0.5 for w in ys):
                    ys.append(v)
            for v in (c[0], c[2]):
                if not any(abs(v - w) < 0.5 for w in xs):
                    xs.append(v)
    ys.sort()
    xs.sort()

    def _idx(bounds: list[float], v: float) -> int:
        for i, b in enumerate(bounds):
            if abs(v - b) < 0.5:
                return i
        return 0

    rows_html = []
    for g_row, rc in zip(grid, row_cells):
        tds = []
        for rect, _txt in zip(rc, g_row):
            if rect is None:
                continue  # 被合并覆盖的格子：由 rowspan/colspan 表达
            rs = _idx(ys, rect[3]) - _idx(ys, rect[1])
            cs = _idx(xs, rect[2]) - _idx(xs, rect[0])
            attrs = (f' rowspan="{rs}"' if rs > 1 else "") + \
                    (f' colspan="{cs}"' if cs > 1 else "")
            tds.append(f"<td{attrs}>{_cell_html(page, rect, _txt, pua)}</td>")
        rows_html.append("<tr>" + "".join(tds) + "</tr>")
    return "<table>" + "".join(rows_html) + "</table>"


def _extract_vector_table_items(pdf_path: Path, o_blocks: list[dict],
                                is_ocr: bool = False,
                                ) -> tuple[list[MidItem], set[int]]:
    """文本层快路径的表格网格重建（2026-08-28 用户实证驱动）。

    快路径此前完全跳过表格识别 → 国标里无处不在的框线表格退化成散文本
    （GB 25466-2010 实测 0 网格）。而 PDF 的矢量框线一直都在：fitz
    find_tables 约 80ms/页即可按框线重建行列（GB 25466-2010 12 页检出
    11 张，合并表头正确）。仅对文本层页有效；扫描/OCR 页无矢量线自然空转
    （is_ocr=True 时直接跳过省时）。

    返回 (table MidItem 列表, 应剔除的文本块下标集)——块中心落在表格 bbox
    内即单元格文本，内容已入 HTML，不再进正文流（防重复 + 顺带消灭 E8
    表格数值假条款）。
    """
    if is_ocr:
        return [], set()
    import fitz

    from src.core.ingestion.mineru_adapter import text_layer_pua_mangled

    items: list[MidItem] = []
    drop: set[int] = set()
    try:
        doc = fitz.open(str(pdf_path))
    except Exception:
        logger.warning("框线表格重建打开 PDF 失败: %s", pdf_path.name, exc_info=True)
        return items, drop
    # 2026-08-29（GB/T 34406 表A.1 全角数字实测）：find_tables/_cell_html 直接
    # 从 PDF 原始文本层抽单元格，绕过 blocks 的 PUA 归一化——文档级判真后
    # 单元格文本同口径归一化，否则表格 md 残留 '９５．８５' 全角。
    pua = False
    if len(doc):
        pua = text_layer_pua_mangled([{"text": doc[0].get_text()[:4000]}])
    with doc:
        for pno in range(len(doc)):
            page = doc[pno]
            try:
                tables = page.find_tables().tables
            except Exception:
                continue
            ph = page.rect.height
            for t in tables:
                if t.row_count < 2 or t.col_count < 2:
                    continue
                try:
                    data = t.extract()
                except Exception:
                    continue
                if sum(1 for row in data for c in row if (c or "").strip()) < 2:
                    continue
                # find_tables=顶部原点 → 转底部原点，与文本块同系（v5 坐标契约）
                x0, y0, x1, y1 = t.bbox
                tb = [float(x0), float(ph - y1), float(x1), float(ph - y0)]
                for i, b in enumerate(o_blocks):
                    if i in drop or int(b.get("page_number", 1)) - 1 != pno:
                        continue
                    bb = b.get("bbox") or []
                    if len(bb) != 4:
                        continue
                    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
                    if tb[0] <= cx <= tb[2] and tb[1] <= cy <= tb[3]:
                        drop.add(i)
                # 2026-08-28 通用题注还原：取同页表格正上方最近、且文本呈题注
                # 样式（表x…/带(续)）的文本块作 caption——(续) 续表判定与
                # table_summary 都依赖它；非题注样式的邻近段落一律不认。
                cap = None
                best: tuple[float, int] | None = None
                for i, b in enumerate(o_blocks):
                    if i in drop or int(b.get("page_number", 1)) - 1 != pno:
                        continue
                    bb = b.get("bbox") or []
                    if len(bb) != 4:
                        continue
                    bx = (bb[0] + bb[2]) / 2
                    if not (tb[0] - 36 <= bx <= tb[2] + 36):
                        continue
                    gap = bb[3] - tb[3]   # 底部原点系：块底 − 表顶
                    if gap < -6 or gap > 90:
                        continue
                    txt = (b.get("text") or "").strip()
                    if not (_TABLE_CAPTION.match(txt) or _TABLE_CONT.search(txt)):
                        continue
                    if best is None or gap < best[0]:
                        best = (gap, i)
                if best is not None:
                    cap = (o_blocks[best[1]].get("text") or "").strip()
                items.append(MidItem(kind="table", text=cap or "", html=_grid_html(t, page, pua),
                                     caption=cap, page_idx=pno, bbox=tb))
    return items, drop


def _merge_table_items(items: list[MidItem],
                       tbl_items: list[MidItem]) -> list[MidItem]:
    """表格 MidItem 按阅读顺序落位：仅对含表格的页做位置排序
    （底部原点系内 y 越大越靠上 → 降序），无表格页保持原有顺序零改动。"""
    if not tbl_items:
        return items
    by_page: dict[int, list[MidItem]] = {}
    for it in items:
        by_page.setdefault(it.page_idx, []).append(it)
    tpages = {it.page_idx for it in tbl_items}
    for it in tbl_items:
        by_page.setdefault(it.page_idx, []).append(it)
    out: list[MidItem] = []
    for pno in sorted(by_page):
        page_items = by_page[pno]
        if pno in tpages:
            page_items.sort(
                key=lambda it: -(it.bbox[3] if len(it.bbox) == 4 else 0))
        out.extend(page_items)
    return out


def run_full_ingest(pdf_path: Path, standard_no: str, standard_name: str,
                    short_code: str | None = None, doc_type: str = "standard",
                    domain_tags: list[str] | None = None,
                    legal_hierarchy: str = "GB",
                    reingest: bool = False,
                    force_deep: bool = True) -> dict:
    settings = get_settings()
    if not pdf_path.exists():
        return {"status": "error", "message": f"文件不存在: {pdf_path}"}
    init_schema()
    file_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    conn = get_db_connection()

    dup = conn.execute("SELECT doc_id FROM doc_meta WHERE file_hash=?", (file_hash,)).fetchone()
    if dup and not reingest:
        return {"status": "duplicate", "doc_id": dup[0]}
    same_no = conn.execute(
        "SELECT doc_id, file_hash FROM doc_meta WHERE standard_no=?", (standard_no,)).fetchone()
    if same_no and same_no["file_hash"] != file_hash and not reingest:
        return {"status": "standard_exists", "existing_doc_id": same_no["doc_id"],
                "message": f"标准号 {standard_no} 已存在（hash 不同），如需覆盖请先废弃旧文档"}
    # reingest 模式：解析成功后删除同 standard_no 的旧文档（用户资产按 clause_key 迁移）

    doc_id = f"doc_{ULID()}"
    # 效力层级标准化（2026-08-29）：从标准号推导（GB/T→GB/T、GB/Z→GB/Z），
    # 调用方传值仅作无法识别时的 fallback——此前全库默认 'GB'，推荐性被埋没
    legal_hierarchy = _hier_from_no(standard_no, legal_hierarchy)
    # 2026-08-29 force_deep 参数化（附录缺失重导暴露）：文本层完好的原生数字版
    # 国标（GB 25596 实测）无需 MinerU 深度模型——fitz 文本层秒出 blocks，框线
    # 表格重建（_extract_vector_table_items）已能逐页恢复全部表格（15 张含跨页
    # 续表/附录表），且深度解析 900s 超时会整单失败。默认 True 保持原行为；
    # 单文档重导传 False 走快路径。
    result = run_parser_isolated(pdf_path, settings.data_dir / "parse_out" / doc_id,
                                 force_deep=force_deep)
    deep_output = result.get("deep_output")
    # 2026-09-02 治本（正常入库识别流程丢字修复）：文本层完好（blocks 非空 = 非 OCR、
    # 非 PUA 错位归一化后可用）→ 正文用 fitz 文本层保真（MinerU 深度模型对文本层
    # 重识别丢数字/字母/标准号：GB/T 1000-2016 实测 10kV→空、GB/T 197→/）。
    # 仅真正无文本层（blocks 空）才用 MinerU 深度全文（OCR 通道）。
    _has_text_layer_ok = bool(result.get("blocks"))
    if deep_output and not _has_text_layer_ok:
        middle_files = list(Path(deep_output).rglob("*_middle.json"))
        if not middle_files:
            return {"status": "error", "message": f"未找到 middle.json: {deep_output}"}
        items, page_sizes = load_middle_items(middle_files[0])
    elif result.get("blocks"):
        # 文本层直入（2026-08-27 修复：原先只认 is_ocr，导致
        # 有文本层的原生数字版 PDF 全部落入 else 误报"解析不可用"——B/C 区
        # 秒败真凶）。文本层 blocks 与深度解析产物同构消费，均不占 GPU。
        # （2026-09-01：旧云 blocks 通道退役，无文本层统一走 MinerU 深度
        # 分析——本地 GPU 优先 → 云解析兜底，deep_output 路径消费。）
        o_blocks = [b for b in result["blocks"] if b.get("text")]
        # 2026-08-28 框线表格重建：快路径此前跳过表格识别 → 框线表格退化散文本。
        # 矢量框线一直在，find_tables 逐页重建；单元格文本从正文流剔除防重复。
        tbl_items, drop_idx = _extract_vector_table_items(
            pdf_path, o_blocks, is_ocr=bool(result.get("is_ocr")))
        if drop_idx:
            o_blocks = [b for i, b in enumerate(o_blocks) if i not in drop_idx]
        # 2026-08-28 修复（1 条款假 ok 真凶）：blocks 必须经
        # load_middle_items_from_blocks 按行拆条 + '5 . 2 . 1' 归一——
        # 云 OCR 一页一大块 / fitz 段落大块直接进切分器，item 级正则只看
        # 块首，行首条款号全部漏识别 → 整文档坍缩成 1 条前置说明。
        items, _ = load_middle_items_from_blocks(o_blocks)
        if tbl_items:
            items = _merge_table_items(items, tbl_items)
            logger.info("框线表格重建：%d 张 / 剔除文本块 %d (%s)",
                        len(tbl_items), len(drop_idx), pdf_path.name)
        geos = result.get("geometries") or {}
        page_sizes = {int(k) - 1: (float(v["width"]), float(v["height"]))
                      for k, v in geos.items()}
        logger.info("blocks 直接入库：%d 块 / %d 行 (%s)",
                    len(o_blocks), len(items), pdf_path.name)
    else:
        return {"status": "error",
                "message": "解析不可用：深度解析失败且无文本层"
                           "（本地未装/跑不动时可在设置中配置云解析 API Key）"}

    clauses = split_items_into_clauses(items)
    models, raw_edges = build_clause_models(doc_id, standard_no, doc_type, clauses, page_sizes)

    # R-B span 坐标系自动校准（pipeline/13-round3.md）：MinerU middle 同源页高，
    # 写库前对全部 span 文档级投票并归一为底部原点（已正确则全 bottom 零改动，幂等）。
    # 仅 MinerU 深度路径接入（blocks/预览路径不落库）；失败降级保留原始坐标不阻塞入库。
    try:
        from src.core.ingestion.span_calibration import calibrate_new
        calibrate_new(
            pdf_path,
            [s for m in models for s in m.source_spans],
            # 条款分组 → 方向判别（同页多 span 的 y 单调性）可用；缺省按对象身份退化
            groups=[list(m.source_spans) for m in models],
        )
    except Exception:
        logger.warning("span 坐标校准失败，保留原始坐标入库", exc_info=True)

    number_to_id = {m.clause_number: m.clause_revision_id for m in models}
    edges = resolve_edges(raw_edges, number_to_id)

    type_dist: dict[str, int] = {}
    for m in models:
        type_dist[m.knowledge_type] = type_dist.get(m.knowledge_type, 0) + 1

    # reingest：入库前先删同 standard_no 的旧文档（否则唯一约束冲突）。
    # 收藏/批注绑 clause_key（= sha256(doc_id+no)，doc_id 变则 key 变——
    # 但旧文档删除时用户资产按 clause_key 留存，重解析后条款号一致即可在检索中重新关联）
    if reingest and same_no and same_no["doc_id"] != doc_id:
        from src.core.storage import clause_repo as _cr
        _cr.delete_document(same_no["doc_id"])

    # R1: 整个入库单事务（doc + 几何 + 条款 + FTS + 向量 + 边），任一步失败全回滚
    preface = [m for m in models if m.clause_number.startswith("前置")]
    appendix = [m for m in models if m.clause_number.startswith("附录")]
    normal = [m for m in models
              if not m.clause_number.startswith(("前置", "附录"))]
    # 入库自动查 CCS（官方渠道 cssn；失败静默降级本地表/无，不阻塞入库）
    tags = list(domain_tags or [])
    if doc_type == "standard":
        try:
            from src.core.knowledge.ccs_fetcher import fetch_ccs, ccs_to_tag
            ccs = fetch_ccs(standard_no, standard_name)
            tag = ccs_to_tag(ccs, standard_no)
            if tag and tag not in tags:
                tags.append(tag)
        except Exception:
            pass  # 网络/解析失败：无 CCS 标签，分类面板走兜底
    # 2026-08-29 封面日期提取（通用）：扫描前两页块文本（封面页），发布/实施
    # 日期归一化 YYYY-MM-DD → doc_meta.published_at / effective_from。离线权威
    # 来源（封面即官方日期），无网络依赖；找不到诚实留空。
    def _cover_date(pattern: re.Pattern[str], blocks: list[dict]) -> str | None:
        for b in blocks:
            if (b.get("page_number") or 1) > 2:
                break
            # NFKC 归一：全角数字（２０１７）→半角，全角标点随之折叠（见上方
            # 正则注释——PUA 连字符由字符类覆盖）
            m = pattern.search(unicodedata.normalize("NFKC", b.get("text") or ""))
            if m:
                return unicodedata.normalize(
                    "NFKC",
                    f"{m.group(1)}-{int(m.group(2)):02d}"
                    f"-{int(m.group(3)):02d}")
        return None

    # 封面日期候选源：fitz 文本层 blocks + 深度路径 middle.json 前 2 页
    # （扫描版 fitz 层为空，只有 middle 里才有"YYYY-MM-DD 发布/实施"）。
    cover_blocks = [b for b in result["blocks"] if b.get("text")]
    if deep_output:
        cover_blocks += _middle_cover_blocks(middle_files[0])
    pub_date = _cover_date(_COVER_PUB, cover_blocks)
    eff_date = _cover_date(_COVER_EFF, cover_blocks)
    with write_transaction() as txn:
        clause_repo.insert_document(txn, {
            "doc_id": doc_id, "standard_no": standard_no, "standard_name": standard_name,
            "short_code": short_code or standard_no.replace(" ", "").replace("-", ""),
            "current_revision_id": f"rev_{ULID()}",
            "doc_type": doc_type, "legal_hierarchy": legal_hierarchy,
            "standard_type": _std_type(legal_hierarchy),
            "domain_tags": tags,
            "published_at": pub_date, "effective_from": eff_date,
            "file_path": str(pdf_path.resolve()), "file_hash": file_hash,
        })
        clause_repo.insert_page_geometries(txn, doc_id, result["geometries"])
        n_normal = clause_repo.insert_clauses_in_txn(txn, normal)
        n_pre = clause_repo.insert_clauses_in_txn(txn, preface, content_type="前置说明")
        clause_repo.insert_clauses_in_txn(txn, appendix, content_type="附录")
        clause_repo.insert_edges_in_txn(txn, edges)
        # 目录卫生（2026-08-28 用户口径）：标准正文条款为零 = 坍缩/乱码吞没，
        # 不进目录。修复重导入产生真实条款 → 新行 DEFAULT 0 自动回归目录。
        if doc_type == "standard" and n_normal == 0:
            txn.execute(
                "UPDATE doc_meta SET catalog_hidden=1 WHERE doc_id=?", (doc_id,))

    # R8 运维日志：入库成功写 operation_log
    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO operation_log (operation, target_type, target_id, detail)"
            " VALUES (?,?,?,?)",
            ("ingest", "doc", doc_id,
             json.dumps({"standard_no": standard_no, "clauses": len(models),
                         "edges": len(edges)}, ensure_ascii=False)))

    # OCR 数字回填（R58 补丁机制）：MinerU 文本层数字缺失时用 pypdf 还原打补丁
    backfilled = 0
    try:
        from src.core.ingestion.pypdf_backfill import backfill_document
        backfilled = backfill_document(doc_id, str(pdf_path))
    except Exception:
        backfilled = 0

    # reingest 的旧文档删除已在入库事务前完成（见上方 reingest 块）

    # span 入库体检（2026-08-26，P1-③）：坐标异常入库当天告警，不静默
    span_warning = None
    try:
        from src.core.ingestion.span_verify import verify_doc
        fp_row = conn.execute(
            "SELECT file_path FROM doc_meta WHERE doc_id=?", (doc_id,)).fetchone()
        if fp_row and fp_row[0]:
            v = verify_doc(doc_id, fp_row[0])
            if v.get("verdict") == "top_suspect":
                span_warning = (
                    f"span 坐标体检告警：疑似顶部原点（top_only={v.get('top_only')}, "
                    f"bottom_hit={v.get('bottom_hit_rate')}）→ 高亮可能错位；"
                    f"请运行 python -m src.core.ingestion.span_verify 复查")
                logger.warning(span_warning)
            elif (v.get("verifiable_rate", 0) > 0.3
                    and v.get("bottom_hit_rate", 1) < 0.3):
                span_warning = (
                    f"span 坐标体检告警：底部原点命中率异常低"
                    f"（bottom_hit={v.get('bottom_hit_rate')}, 可验证率="
                    f"{v.get('verifiable_rate')}）→ 建议复查坐标系")
                logger.warning(span_warning)
    except Exception:
        logger.warning("span 体检失败（不阻塞入库）", exc_info=True)

    return {"status": "ok", "doc_id": doc_id,
            "reingested": bool(reingest and same_no),
            "pypdf_backfilled": backfilled,
            "total_clauses": n_normal - n_pre, "preface_clauses": n_pre,
            "evidence_edges": len(edges),
            "pages_parsed": len(result["geometries"]),
            "knowledge_type_distribution": type_dist,
            "span_warning": span_warning}


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_path", type=Path)
    ap.add_argument("--standard-no", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--short-code", default=None)
    ap.add_argument("--doc-type", default="standard", choices=["standard", "法律法规"])
    ap.add_argument("--domain-tags", default="")
    ap.add_argument("--legal-hierarchy", default="GB")
    args = ap.parse_args(argv)
    out = run_full_ingest(
        args.pdf_path, args.standard_no, args.name or args.standard_no,
        args.short_code, args.doc_type,
        [t for t in args.domain_tags.split(",") if t], args.legal_hierarchy)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
    # CLI 场景直接硬退出，避免解释器收尾被残留线程拖挂（worker 已自清理）
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if out.get("status") in ("ok", "duplicate", "standard_exists") else 1)


if __name__ == "__main__":
    sys.exit(main())
