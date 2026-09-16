"""T05 完整入库管线：MinerU 深度解析 → middle.json 结构化 → E1-E7 切分
→ 三型分型 → 证据图抽取 → 单事务原子入库（R1）。

用法:
    python -m src.core.ingestion.pipeline <pdf> --standard-no "GB 30871-2022" \
        --name "..." [--doc-type standard|法律法规] [--domain-tags 安全,消防]

坐标契约（2026-09-16 更正）:
    本节的旧文本写的是「左上原点（y 向下）…勿用底部原点翻转」——**那是错的**，
    它与**同一个文件下方** :658-661 的废弃说明互相矛盾，也与前端
    `plugin/client/KsEvidenceTab.tsx:477-479` 的契约注释相反（先读到的恰是错误版本）。

    正确契约：MinerU middle.json 的 bbox 为 **PDF 底部原点（左下、y 向上）**；
    `source_span` **原样直存**（不做任何翻转）；前端用 pdfjs
    `convertToViewportPoint(x, y)` **直接映射**，**禁止再做 H−y 翻转**。
    历史事故（两次）：曾误判为"左上原点"并加 `_flip_bbox` 翻转 → 前端又 H−y
    → **双重翻转黄标垂直镜像**。`_flip_bbox` 已删除。
    权威表述见 `ENCYCLOPEDIA` §9.3；`span_calibration.py` 负责把存量 span
    归一为底部原点（最近文字行投票，幂等）。
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
_CLAUSE_GB = re.compile(r"^(\d+(?:\.\d+){1,7})\s*(.*)$", re.S)
_CLAUSE_LAW = re.compile(r"^(第[一二三四五六七八九十百千]+条)\s*(.*)$", re.S)
_TABLE_CAPTION = re.compile(r"^表\s*([A-Za-z]?\s*\.?\s*\d+(?:\.\d+)*)\s*(.*)$")
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
# 2026-09-13 附录细分：附录内子条款头 "A.1"/"E.5.2"/"B.2.1"——字母章号+点分段。
# _CLAUSE_GB 只认 \d 开头（3654 条 normal 条款的口径，不动）；附录内全部文本
# 因此并入附录头单块（实测 21 条 >800ch 大块全由此机制产生，2 条恰好 4000 字
# 被 [:4000] 截断丢内容）。老前端 escDupNo 的字间空白容忍思想（"表A. 1"）在此
# 落地为点后 \s*。词边界 (?![\d.]) 防 "A.1" 误配 "A.10"（dupNoMatches 同款）。
_CLAUSE_APPENDIX = re.compile(r"^([A-Z]\.\s*\d+(?:\.\s*\d+){0,5})\s*(.*)$", re.S)
# 2026-09-02 目录条目排除（GB/T 1000-2016 实测）：文件目录页写
# "附录A (规范性附录) 绝缘子螺套…"，与真附录头"附 录 A"同形，误设 in_appendix →
# 后续正文章级条款(1/2/3/4)被 `m_chap and not in_appendix` 跳过而全丢。
# 目录条目特征：附录号后紧跟 " (规范性/资料性/推荐性/引导性附录)" 说明。
_DIR_ENTRY_RE = re.compile(
    r"附\s*录\s*[A-Z一二三四五六七八九十]?\s*[（(]\s*(规范性|资料性|推荐性|引导性)\s*附录")
_CHAPTER_HEAD = re.compile(r"^(\d+)\s*[\u4e00-\u9fff]")  # \s*：容忍 _span_norm 压掉章头数字与标题间空格（"1 范围"→"1范围"），否则章级条款被丢
_TOC_HEAD = re.compile(r"^目\s*次")

#: 文末「索引」小节标题（2026-09-15 批次3 实测缺陷）。
#: **缺陷证据**：`GB/T 5845.2-2008 城市公共交通标志 第2部分` 的**中文索引**
#:   `中文名称 …… 序号\nIC 卡充值站 …… 27\n…`（点线 + **序号列**，页码位置被
#:   序号冒充）既带点线页码形、又不是条款，于是被 `_is_toc_entry` 认作目录条目
#:   ——但此时**不在目录态**（`in_toc` 只在文首「目次」置位），故这些行全被
#:   **并进前一条款**：正文 5.5 只有一行内容，却吃下 126 行（索引两页）。
#: 判据：整块恰为「索引」类词——前缀取**白名单**（`中文索引`/`英文索引`/`术语索引`/
#:   `汉语拼音索引`），并容许字间空格（`索 引`/`索  引`）。
#:   **必须整块**：不能是"见索引"/"索引号"这类正文词，否则会把正文块误判成索引起始。
#:   ⚠ 白名单而非 `[\u4e00-\u9fff]{1,4}`：后者会把 `见索引` 也收进来
#:     （自测当场抓到）。索引标题的前缀是**有限枚举**，不该用任意汉字。
#:   （2026-09-16 扩宽，实测 GB/T 13964-2008：该标准文末为 `中文索引` … `英文索引`，
#:    而旧判据只认整块 `索引` → 索引态从不置位 → 「英文索引」之后的整段英文索引
#:    被当正文吞入。用 pipeline 自己的 item 加载器实测该部 item #1464=`中文索引`、
#:    #1489=`英文索引`，均在旧判据下不置位。）
#:   误报风险实测：40 部语料中，旧判据命中块 0 个、扩宽后仅多命中这批索引标题，
#:   未见任何正文块被误判（见 `var/ocr-loop/probe_index_head.py`）。
_INDEX_HEAD = re.compile(
    r"^\s*(?:中文|英文|术语|汉语拼音|拼音|拉丁文|西文)?\s*索\s*引\s*$")

# ---------------------------------------------------------------------------
# 目录条目判据（2026-09-15 新语料头部类 toc-ingested-as-clauses 8 部）
# ---------------------------------------------------------------------------
# **缺陷证据**：目录页正文被判成条款摄入，且打乱号序——实测
#   GB/T 17889.5-2025 号序 ['前置1','7.1','1','2',…]（'7.1' 行含 40 行目录）
#   GB/T 24842-2018 ['前置1','10.5','1',…]、GB/T 25483-2010 ['前置1','5.3.2','1',…]
#   GB/T 28853-2012 更碎：'9.1 包装……13'/'9.2 运输……14' 被切成 5 个独立条款
#
# **根因**：`in_toc` 的退出判据写的是"出现第一个章/条款头即退出"，而**目录条目
# 本身长得就像条款头**——'7.1 一般要求 …… 16' 匹配 `_CLAUSE_GB`，于是进入目录
# 态后第一行就退出，其后的目录行全部被当正文条款摄入。
#
# **修法**：目录条目有确定签名——**点线引导 + 页码**（'……16'）。故在目录态内
# 只要该块是目录条目就继续吃；退出改由"遇到不是目录条目的块"触发
# （正文条款不带页码尾）。
# 判据与 `audit_text.dot-leader` 同源口径（`…{2,}` = '……'），保持单一判据。
_TOC_ENTRY = re.compile(r"(?:…{2,}|[.．]{3,})\s*\d{1,3}\s*$", re.M)

#: 目录条目的**第二签名**（2026-09-15 批次2 实测 GB/T 29798-2013 缺陷）：
#: 目录被压成单行时**点线会被吞掉**，只余"条款号 + 页码"：
#:   '10.2.3 重连接 80\n10.2.4 订阅响应 SubscribeResponse 80\n…'（无点线）
#: 该块 `_is_toc_entry` 判 False → 目录态当行退出，**其后的点线目录块
#: （'14.5 出错信息的扩展性 …… 108' 起 10 行）也一并倒进正文**，
#: 产出条款号序列断裂：['前置1','10.2.3','14.5','1','2','3',…]
#: ——'14.5' 抢占正文 14.5 的座位（正文 14.5 内容实为目录尾部）。
#: 判据：**≥2 行**形如「条款号 + 标题 + 1–3 位数字（页码）」。两条约束缺一不可：
#:   - 数字尾是目录行与正文行的分水岭：正文块行尾**不会**带裸页码；
#:     少了它会把普通多行正文块吃进目录态（'3.1 原则\n3.2 方法' 即误判）。
#:   - ≥2 行是防单行误判：正文里一句"见 4.2 条 5"也可能单行成立。
_RE_TOC_CL_NO_DOTS = re.compile(r"^\s*\d+(?:\.\d+)*\s+\S.*?\s\d{1,3}\s*$", re.M)

#: **索引条目的签名**（2026-09-16 实测 GB/T 13964-2008 缺陷）。
#: 形态：`词条 + 点线 + 页码`，但页码是**小数**（索引指向"条款号"而非"页号"）：
#:   '白平衡 …… 2.78\n半峰值时间 …… 6.37\n包容角 …… 2.40\n饱和度 …… 10.49'
#:   '压片板……9.7'（点线与数字之间**可以没有空格**）
#: 为什么前两条签名都够不着：`_TOC_ENTRY` 要求点线后是 `\d{1,3}\s*$`（无小数点），
#: `_RE_TOC_CL_NO_DOTS` 要求行首是**条款号** + 整数页码尾——索引条目行首是**词条**。
#: 现状靠 `_INDEX_HEAD` 置索引起止态侥幸绕过（实测该部 416 条正文、索引未倒灌），
#: 但**若某文档的索引没有标题块**，这些条目就会倒进正文——这是本次要堵的洞。
#: 判据收紧点：① 必须有**点线**（正文里几乎没有连续的 `……`）；
#:   ② 页码必须是 `数字.数字`（小数）；③ ≥2 行（单行可能是正文里的"见 3.2 …… 4.5"）。
_RE_INDEX_ENTRY = re.compile(r"(?:…{2,}|[.．]{3,})\s*\d{1,3}\.\d{1,3}\s*$", re.M)


def _is_index_entry(text: str) -> bool:
    """该块是否像**索引条目**（≥2 行「词条 + 点线 + 小数页码」）。

    与 `_is_toc_entry` 并列的独立签名，用于"索引没有标题块"时仍能识别并跳过。
    ≥2 行约束见 `_RE_INDEX_ENTRY` 注释——单行在正文里可能是合法引用。
    """
    return len(_RE_INDEX_ENTRY.findall(text or "")) >= 2


def _is_toc_entry(text: str) -> bool:
    """该块是否为目录条目（点线 + 页码尾，或 ≥2 行「条款号 + 页码尾」）。

    逐行判定而非整块匹配：MinerU 常把多个条目并进一个块
    （实测 '国家标准化管理委员会\\n11 数据共享要求……7\\n12 数据删除要求……8'），
    整块 `$` 锚定会漏判。任一行是目录条目即认——**要求点线**是关键，
    没有点线的普通条款（'3.1 驾驶自动化分级原则'）不会被误吃。
    无点线形态另由 `_RE_TOC_CL_NO_DOTS` 兜底（≥2 行条款号+页码尾），
    见其注释中的实测缺陷证据与反向对照。
    """
    for ln in (text or "").split("\n"):
        s = ln.strip()
        if s and _TOC_ENTRY.search(s):
            return True
    return len(_RE_TOC_CL_NO_DOTS.findall(text or "")) >= 2

# E8 表格数值防误判（2026-08-28 生产实测）：化学分析类标准的大表被 MinerU 切成
# 文本行后，行首单元格值（"0.10 0.030 0.002"）满足 _CLAUSE_GB 的 len≥3/含点门槛
# → 每行被切成 0.x 假条款（审计：41% 新产出文档中招，单文档最多数百假条款）。
# 闸门 1：真实 GB 标准章号首段 ∈ 1..60（GB 50xxx 的 "4.0.1" 首段也是 4，
#         从无 0 开头的章；"1103.11" 这类千位数值全是表格数据）。
# 闸门 2：真实条款头号码后极少紧跟 ≥2 个独立数字（表格行特征："4.2 1.5 3.0"）。
_CHAPTER_MAX = 60
_TABULAR_REST = re.compile(r"^\s*\d+(?:\.\d+)?(?:\s+\d+(?:\.\d+)?)")


#: 闸门 5 的单位词表（**多字符单位 + 小写单字母单位**）。
#: 大写单字母（A/V/W/N/J/L）故意不收：`A类评定`/`A 型结构` 这类"型号标签"
#: 标题会被误拒（实测反向对照，见 tests/test_head_unit_fragment_gate.py）。
_RE_HEAD_UNIT = (
    r"mm|cm|dm|km|nm|µm|μm|kg|mg|µg|μg|mL|µL|μL|dL|ms|ns|min|"
    r"mol|mmol|ppm|kPa|MPa|GHz|kHz|kN|mA|mV|kV|kW|kJ|Pa|Hz|"
    r"m|g|t|s|h|d|l"
)
#: 闸门 5：条款头后面跟的是**「数值 + 单位」的句子片段**（而非标题）。
#: 判据两条同时成立：
#:   ① rest 以单位 token 起头；
#:   ② 该单位后面**不是另一个拉丁词**（`\s*[A-Za-z]` 为否）——"ppm parts per
#:      million" 是合法术语条（英文缩写作标题），必须放行；而 "mmol/L氯化镁"、
#:      "mL，用40%"、"m/s<v≤2.0"、"kg/m³。"、"m×全幅"、"mm 模数直齿轮" 都是
#:      数值片段的后续（斜杠/乘号/中文标点/中文），即假条款头。
_RE_HEAD_UNIT_FRAG = re.compile(
    rf"^\s*(?:{_RE_HEAD_UNIT})(?!\s*[A-Za-z])")


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
    # 闸门 4（2026-09-15，GB/T 12706.4-2020 收敛循环首轮实测）：标题折行后行首是
    # **「量值 + 单位」的收尾**——原文封面/标题 "( Uₘ = 40.5 kV )挤包绝缘电力电缆…"
    # 折行成 "40.5kV)挤包绝缘电力电缆及附件 第4部分…"，被 _CLAUSE_GB 当条款号
    # 40.5（实测产出伪条款 40.5、553 字，且是后续序性判据毒化的引信）。
    # 闸门 3 只认**纯小写**拉丁（"kV" 的 V 是大写 → 漏），故补一条独立形态：
    # 短拉丁（1~4 字母，含大小写）+ 紧跟右括号 = 数值括号的收尾，非条款头。
    # 反例保护：真条款头 "4.1 pH的测定"（拉丁后跟中文、无括号）不受影响。
    if rest and re.match(r"\s*[A-Za-z]{1,4}\s*[\)）\]】]", rest):
        return False
    # 闸门 5（2026-09-15 收敛循环第 9 轮，spurious-clause-number 18 部实测）：
    # 「数值 + 单位」的**句子片段**被当条款头——原闸门 3 只认"单位紧跟中文"
    # （`1.5m时`），漏掉单位后跟斜杠/乘号/中文标点/空格的全部形态：
    #   '1.5cm/m。' '1.293 kg/m³。' '1.00mL，用40%乙醇…' '2.0mmol/L氯化镁…'
    #   '1.0m/s<v≤2.0 m/s时…' '1.5m×全幅' '1.0 mm 模数直齿轮的…'
    # 反向保护：rest 以单位起头但**后面还跟拉丁词**的放行（'3.4 ppm parts per
    # million' 是合法术语条，英文缩写作标题）——见 _RE_HEAD_UNIT_FRAG 注释。
    if rest and _RE_HEAD_UNIT_FRAG.match(rest):
        return False
    return not _TABULAR_REST.match(rest or "")


#: 续行/交叉引用起头特征（2026-09-15，OCR 循环「重复条款号」根因修复）：
#: OCR 折行把一句话切断，续行行首恰好是被引用条款号 → 被当新条款头，
#: 造成同号重复条款（全库 216 组 (doc, clause_number) 重复、17 部文档受影响）。
#: 实测形态：'3.18)，在距离全开位置10mm以内处关闭推拉构件。'（右括号起头）、
#: '5.1.1~5.1.19的试验结果记入表 A.2。'（波浪号）、'12.9。如未规定频率…'
#: （句号）、'11.6.2 或11.6.3得出的值大。'（连接词）、'8.3.1.2.3.1 概述'
#: 旧正则深度不足时的 '.1 概述'（点起头）。
#:
#: **2026-09-15 修正（GB/T 12706.4-2020 '7.8 如果在较低U₀值电缆…' 被误拒）**：
#: 初版连接词分支只认词本身（或/见/按/如…）→ **合法条款标题以「如」起头也被拒**
#: （"7.8 如果…" 整条并进上一条）。真续行的连接词后面**必然紧跟一个引用对象**
#: （条款号或标准号），故连接词分支补这个必要条件：后面接数字或标准号前缀。
_RE_CONT_REST = re.compile(
    r"^[\s\)）\]】》~～。，、；：,.;:·—–\-]+"
    r"|^\s*(?:或|和|及|与|即|则|其中|式中|以及|见|按|如)\s*"
    r"(?:\d|[A-Z]{2,6}\s*[/\s]?\s*[A-Z]?\s*\d)"
    r"|^\s*[\d.]"
)


def _num_segments(num: str) -> tuple[int, ...] | None:
    """号 → 可比较段元组；不可比较（前置N 等）返回 None。

    2026-09-15：附录字母号（C.7）也参与序性比较——字母折算为 1000+ord，
    保证 A.1 < A.2 < B.1；数字号与附录号同处一序（正文 5.1 < 附录 A.1）。
    实测残留：GB/T 1094.6 的 'C.7'/'E.1' 重复需此扩展清除。
    """
    n = (num or "").strip()
    m = re.fullmatch(r"([A-Z])(?:\.(\d+))+", n)
    if m:
        segs = [1000 + ord(m.group(1))]
        segs += [int(x) for x in re.findall(r"\.(\d+)", n)]
        return tuple(segs)
    if not re.fullmatch(r"\d+(?:\.\d+)*", n):
        return None
    return tuple(int(p) for p in n.split("."))


def _is_continuation_head(num: str, rest: str | None, clauses: list) -> bool:
    """判断匹配到的号是否是「续行/交叉引用」而非真条款头（2026-09-15）。

    两道独立判据（任一命中即拒）：
      ① 形态：rest 以续行标点（)/）/~ 。，、；: 等）、连接词（或/和/及/与…）
         或数字/点起头——真条款头的标题不会这样起头；
      ② 序性：**重复号**或**同父回退**（见下）。
    失效方向：页序错乱的文档可能把真头并进上一条（内容保留、少切一条），
    比「伪造同号条款污染 clause_key」安全。

    **2026-09-15 二次修正（收敛循环首轮实测，GB/T 12706.4-2020）**：
    初版序性判据是「号 ≤ 最近已产出号即拒」——**顺序依赖且不可恢复**：
    标题折行把行首电压值 "40.5kV)…" 当成条款号 40.5 后，其后所有真头
    （4.1/5.2/附录 A.1…）都不大于 40.5 → 被全数拒绝，27 页文档从 53 条
    塌成 3 条、正文 6489→4886 字。**一个假头毒死全文**，而且这一层没有
    任何机制能自愈。改为两条**局部充分**判据：
      ① 重复：该号已在本文档产出过（交叉引用/续行重号的真特征）；
      ② 同父回退：与最近已产出号**同长且同父**（前缀相同）而更小——
         同一父下真条款号严格递增，回退只可能是引用前面兄弟的续行。
    跨父的大幅"回退"（40.5 → 4.1）不再拒：那是新章开始，且不受假头污染。
    """
    if _RE_CONT_REST.match((rest or "")):
        return True
    cur = _num_segments(num)
    if cur is None:
        return False
    produced: list[tuple[int, ...]] = []
    for cl in clauses:
        seg = _num_segments(getattr(cl, "number", "") or "")
        if seg is not None:
            produced.append(seg)
    if not produced:
        return False
    if cur in produced:            # ① 重复号
        return True
    last = produced[-1]            # ② 同父回退
    return (len(cur) == len(last) and cur[:-1] == last[:-1]
            and cur[-1] < last[-1])


_RE_LEADER_RUN = re.compile(r"^[0.·\u2024\s]{6,}$")


def _is_leader_run(text: str) -> bool:
    """纯引点填充块判定（索引行特有）。

    2026-09-15：GB/T 1008-2008 索引页（中文索引 p17-24）每行是「裸号 + 引点
    + 词条」，引点被 OCR 成 000000000000000 —— '编号独行块前瞻' 分支把
    「裸号 + 引点块」当条款头，154 个索引号全部变成伪条款（重复号 154 组，
    全库最大单点）。引点块本身（纯 0/点/间隔号 ≥6 位）是索引行的强特征。
    """
    return bool(_RE_LEADER_RUN.match((text or "").strip()))


def _plausible_appendix_head(num: str, rest: str | None) -> bool:
    """2026-09-13 附录版 E8 闸门：字母章号 "A.1" 的三道防误切护栏。

    背景：附录是表格最密处（GB/T 1028 附录B 表格 HTML 达 241KB），而主
    _plausible_clause_head 的闸门 1（首段数字 ∈ 1..60）对字母号全部失效——
    防护失效方向与风险最高方向重合。本闸门对附录编号形态重设防线：
      ① 号 = 单个大写字母 + 1..4 段数字（防 "AB.1" 乱码/多字母缩写误入）；
      ② rest 必须有标题文字（孤立编号 = 表格数据行，与主闸门闸门 2 同理）；
      ③ rest 不得是表格数值行特征（_TABULAR_REST，与主闸门共用）；
      ④ 排除图表题注与引用句开头——"表E.4给出了…"/"图A.1所示…"/"(见表E.2)"
         是正文引用而非子条款头（红队 D 实证 4 条假正例：附录E 第 47 行
         "表E.4给出了每个Uₘ值…" 若切，真 E.4 头在第 37 行的正文被拦腰截断）。
    """
    num = re.sub(r"\s+", "", num)  # 点后排版空格（"A. 4"→"A.4"）先归一
    if not re.fullmatch(r"[A-Z](?:\.\d+){1,4}", num):
        return False
    r = (rest or "").strip()
    if not r:
        return False
    if re.match(r"[图表]\s*[A-Z]", r):
        return False
    if re.match(r"[（(]?\s*[见如按]", r):
        return False
    # 号形态末检：归一后必须仍是 单字母+点分段（防空白归一掩盖 "A .1" 之类乱形）
    return (not _TABULAR_REST.match(r)
            and re.fullmatch(r"[A-Z](?:\.\d+){1,4}", num) is not None)


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
    # 2026-09-14（执行计划 v3 阶段 2a）：OCR span 真实置信度聚合（min，
    # 最弱环节原则——评审裁决）。深度通道 middle.json 的 span 自带
    # score（PP-OCR rec 置信度），文本层路径无此信号 → None（不参与
    # 质量分推导，启发式口径保持）。表/图条目为 None。
    min_span_score: float | None = None


def _spans_rows(node: dict) -> list[tuple[str, list[float] | None]]:
    """行级提取底座（2026-09-01 B5）：[(行文本, 行bbox|None), ...]。

    行界 = block.lines[]（真折行边界）；行 bbox = line.bbox 直取（同 bbox
    契约）。行内 span（text|inline_equation）无缝原位拼回（假行界修复同
    _spans_text：MinerU 把行内数字/字母抽成 LaTeX 公式 span，丢弃 → 正文
    缺内容；逐 span '\\n' join → 一行内正文+公式被强行拆行）。公式 LaTeX
    转可读 Unicode 文本。空行（全 span 空内容）不产出。
    """
    return [r for r in _spans_rows_scored(node) if r[0]]


def _spans_rows_scored(node: dict) -> list[tuple[str, list[float] | None]]:
    """_spans_rows 的带分底座：额外收集行内 span score 的 min（2026-09-14
    阶段 2a，识别层真实置信度）。公式 span（MFR 产物）无 score，不参与；
    文本层文档 span 无 score 字段 → 整块 None。空行不产出。"""
    from src.core.text_utils import latex_to_text
    rows: list[tuple[str, list[float] | None]] = []
    for line in node.get("lines") or []:
        parts: list[str] = []
        scores: list[float] = []
        for span in line.get("spans") or []:
            st = span.get("type")
            content = span.get("content") or ""
            if not content:
                continue
            if st == "text":
                parts.append(content)
                sc = span.get("score")
                if isinstance(sc, (int, float)):
                    try:
                        scores.append(float(sc))
                    except (TypeError, ValueError):
                        pass
            elif st in ("inline_equation", "interline_equation"):
                # 2026-09-01 interline_equation（独立公式行）与 inline 同族：
                # 此前只认 inline_equation，独立公式块（MinerU 抽成整块
                # interline_equation，span type 也是 interline_equation）在
                # 此处 parts 落空 → 整条公式从条目流蒸发（GB/T 24276 实测
                # 24 条公式全部丢失，"公式没识别出来"根因）。同走
                # latex_to_text → 可读 Unicode 文本行，作为独立行入库。
                # score：MFR 公式置信度语义与文本 rec 不同，且公式质量已有
                # 独立泄漏归一管线 → 不进 min 聚合。
                parts.append(latex_to_text(content))
        if parts:
            _g = node.setdefault("_ks_min_score", None)
            if scores:
                m = min(scores)
                node["_ks_min_score"] = m if _g is None else min(_g, m)
            # 2026-09-14（OCR 循环轮次 4/7/12 同类 3 次达线）：OCR 通道逐字符
            # 拉开的单位/数字（"± 2 0 0 r / * m i n"）原样入库 → 行出口统一
            # 保守粘合（数字/字母分段、不跨型、含小数点；详见 text_utils
            # glue_ocr_spaced_units）。文本层路径的 glue 在 fitz 侧另有调用点。
            from src.core.text_utils import glue_ocr_spaced_units
            rows.append((glue_ocr_spaced_units(
                "".join(parts).strip()),
                list(line["bbox"]) if line.get("bbox") else None))
    return rows


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


_RE_LEGEND_HEAD = re.compile(
    r"^标.{0,3}序.{0,4}[：:]?\s*$"          # 原形态：短尾（标引序号说明：）
    r"|^标.{0,3}序.{0,12}[：:]\s*$"        # 放宽仅限**带冒号**（标引序号(符号)说明：）
    r"|^标.{0,3}序.{0,4}说?明?[：:]"
    r"|^标.{0,3}序.{0,12}说?明?[：:]")     # 同上：冒号是必要条件
#: 图注行（图例段的结束边界）：'图 B.4' / '图 12' / '图A.1'
_RE_FIG_CAPTION_LINE = re.compile(r"^\s*图\s*[A-Z]?\.?\s*\d")
# 图例清单项：'N——标签'（同一行可多项：'1——托架：5——辐射锥：9——控制盒：'）。
# 前界用「非数字/字母」负向环视而非 \s ——实测多项同行时分隔符是 '：'/'；'，
# 初版 (?:^|\s) 只匹配到第一项、整块漏判。
_RE_LEGEND_ITEM = re.compile(r"(?<![\dA-Za-z])\d{1,2}\s*[—\-–~]{1,3}\s*[^\d\s]")


def _is_figure_legend(text: str) -> bool:
    """图例块（标引序号说明 + 'N——标签' 编号清单）判定（2026-09-15 立）。

    背景（OCR 循环自治循环 figure-neighborhood 类跨 3 文档达线，实测
    GB/T 10671 / 11345）：图内标引序号说明被 OCR 成低分文本块，被当作
    条款正文并入 → ①条款正文混入图例垃圾（'标可序影视听：/ 1 供：…下光衡：'）
    ②条款 ocr_confidence 被图内文字拖低（虚假告警）。
    判据：① 首行是「标引序号说明」头（含 OCR 乱码变体 '标可序影视听：'，
    用 标.*序.*[：:] 松匹配）；② 块内 'N——标签' 编号项 ≥2（**按项计数而非
    按行**：实测图例常压成一行多项，初版逐行 match 只数到 1 而漏判）。
    """
    lines = [ln for ln in (text or "").split("\n") if ln.strip()]
    if not lines:
        return False
    if _RE_LEGEND_HEAD.match(lines[0].strip()):
        return True
    return len(_RE_LEGEND_ITEM.findall(text)) >= 2


def _legend_follows_image(bb: list[float] | None, img_bb: list[float] | None,
                          gap_max: float = 60.0) -> bool:
    """几何判据：图例块紧邻图（上下任一方向），且横向有交叠。

    2026-09-15 修：初版按「图下沿 = img_bb[1]」写死 y 方向假设 → 实测
    （10671 图 bbox y 166..421、图例 y 446..459）最近边是 img[3]/bb[1]，
    写死方向把距离算成 293 直接否掉、图例全部漏判。改为取两框**最近边距**
    （方向无关），只要求相邻且横向不远离（图例可略宽出图，实测左伸 ~20px）。
    """
    if not bb or not img_bb or len(bb) != 4 or len(img_bb) != 4:
        return False
    vgap = min(abs(bb[3] - img_bb[1]), abs(bb[1] - img_bb[3]))
    if vgap > gap_max:
        return False
    x_overlap = min(bb[2], img_bb[2]) - max(bb[0], img_bb[0])
    return x_overlap > -40.0


def load_middle_items(middle_path: Path) -> tuple[list[MidItem], dict[int, tuple[float, float]]]:
    """解析 middle.json → 阅读顺序条目 + 每页尺寸。

    discarded_blocks（页眉/页脚/页码）直接跳过 —— R65 边角过滤 + E4 跨页杂音消除。
    """
    mj = json.loads(middle_path.read_text(encoding="utf-8"))
    items: list[MidItem] = []
    page_sizes: dict[int, tuple[float, float]] = {}
    last_img: tuple[int, list[float], MidItem] | None = None   # (page_idx, bbox, item)
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
                    img_item = MidItem(kind="image", text=cap_text.strip(),
                                       caption=cap_text.strip() or None,
                                       image_path=img_rel, page_idx=pidx,
                                       bbox=list(block.get("bbox", [])))
                    items.append(img_item)
                    last_img = (pidx, list(block.get("bbox", [])), img_item)
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
                        blk_bb = list(block.get("bbox", []))
                        # 2026-09-15 图例归图：紧贴图下方的「标引序号说明 +
                        # N——标签」清单是图内容而非条款正文——并入图条目
                        # caption（内容不丢、随图渲染），不再进条款正文
                        # （否则正文混入图例乱码且 ocr_confidence 被图内文字拖低）。
                        if (last_img and last_img[0] == pidx
                                and _is_figure_legend(text)
                                and _legend_follows_image(blk_bb, last_img[1])):
                            it_img = last_img[2]
                            merged = "\n".join(
                                x for x in ((it_img.caption or ""), text) if x)
                            it_img.text = merged
                            it_img.caption = merged
                            continue
                        # 2026-09-14 阶段 2a：_spans_rows 内部已把 span score
                        # min 写进 block["_ks_min_score"]（见 _spans_rows_scored）
                        items.append(MidItem(
                            kind="title" if btype == "title" else "text",
                            text=text, page_idx=pidx,
                            bbox=blk_bb,
                            line_boxes=[b for _, b in text_rows],
                            min_span_score=block.get("_ks_min_score")))
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
    in_index = False
    in_appendix = False
    current: SplitClause | None = None
    chapter: str | None = None   # 最近章号（还原 MinerU 吞点的条款号 "41"→"4.1"）
    skip_idxs: set[int] = set()  # 编号独行块前瞻已并入消费的标题块

    for idx, it in enumerate(items):
        if idx in skip_idxs:
            continue
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
        # 文末「索引」小节：标题与**其后全部内容**都不属于任何条款
        # （见 `_INDEX_HEAD` 注释的实测缺陷：索引两页被并进正文 5.5）。
        # 与目录态的区别：目录态里只有"目录条目形"的块被吃，这里索引**整段**
        # 都不是条款——故置位后所有块都跳过（索引标题、条目、续页皆然）。
        # 用 `continue` 而非 `break`：其后可能还有别的内容块，交给后续分支判断；
        # 索引态一旦置位就不再复位（索引是文末小节，其后无正文条款）。
        if _INDEX_HEAD.match(text):
            in_index = True
            continue
        if in_index:
            continue
        # **索引条目在"非目录态"也要收掉**（2026-09-16 实测 GB/T 13964-2008）：
        # 索引条目形如 `白平衡 …… 2.78`（**小数页码**），`_is_toc_entry` 两条签名
        # 都够不着 → 若该文档**没有「目次」标题**（`in_toc` 从未置位），
        # 这些条目就会直接倒进正文。上面的 `in_toc` 分支只在目录态内生效，
        # 故此处必须独立判一次。
        # 判据收紧到"≥2 行「词条 + 点线 + 小数页码」"（见 `_RE_INDEX_ENTRY`），
        # 正文里几乎不会连续出现这种形态；一旦命中即认为进入文末索引小节，
        # 置位后其后内容都不入条款（与 `_INDEX_HEAD` 同语义）。
        if _is_index_entry(text):
            in_index = True
            continue
        if in_toc:
            # 目次结束判定（2026-09-15 修订）：**只要是目录条目就继续吃**。
            # 旧判据"出现第一个章/条款头即退出"是缺陷根源——目录条目本身
            # 就匹配 `_CLAUSE_GB`（'7.1 一般要求 …… 16'），进入目录态后第一行
            # 立刻退出，其后目录行全被当条款摄入（实测 8 部，号序错乱）。
            # 目录条目的确定签名是**点线 + 页码尾**，据此判定；
            # 遇到不带页码尾的块才是正文开始。
            if _is_toc_entry(text):
                continue
            # **索引条目也在此收掉**（2026-09-16 实测 GB/T 13964-2008）：
            # 该标准目录之后是 `中文索引`/`英文索引`，条目形如
            # '白平衡 …… 2.78'（**小数页码**）——`_is_toc_entry` 两条签名都够不着，
            # 于是目录态在此退出，索引条目开始倒向正文。
            # 加这条后：无论索引**有没有标题块**，条目都不会进正文。
            if _is_index_entry(text):
                in_index = True      # 索引是文末小节，置位后不再复位（同 `_INDEX_HEAD`）
                continue
            # 兼容：真正的章/条款头（无点线页码尾）出现 → 退出目录态
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
        # 2026-09-13 编号独行块前瞻（GB/T 1032-2023 重导实测）：MinerU 常把
        # 术语条目的编号与标题拆成两个单行块（"3.1"\n"异步电机asynchronous
        # machine"）。编号独行块本身 rest 为空 → _plausible_clause_head 闸门 2
        # 拒绝 → 编号并入上一条款、标题也并入 → 整章术语条目坍缩成章巨条款
        # （1032 章3 实测 1136 字吞了 3.1~3.14 十四条）。前瞻修法：块级编号
        # 匹配且 rest 为空时，看**下一个非空块**——若它以编号开头（下一个条
        # 目）则是表格数值块（拒绝，行为不变）；若它是纯标题/正文（不带编号），
        # 则本块是真条款头，开新条款并把下一块作为其首段。护栏：编号段必须
        # 带点（章号 "3" 独行不是条款头——那是章标题块，_CHAPTER_CLAUSE 管）。
        if (m_gb and not m_gb.group(2).strip()
                and "." in m_gb.group(1)
                and 1 <= int(m_gb.group(1).split(".")[0]) <= _CHAPTER_MAX):
            nxt_txt = ""
            for j in range(idx + 1, len(items)):
                nt = (items[j].text or "").strip()
                if nt:
                    nxt_txt = nt
                    break
            # 2026-09-15 索引页护栏（GB/T 1008 154 组重复号根因）：索引行是
            # 「裸号 + 引点 + 词条」，前瞻分支会把它当条款头。两道拒：
            # ① 下一块是纯引点填充（索引行强特征）；② 序性——索引号必然 ≤
            # 正文已产出号（索引在正文之后，按正文号排序引用）。真条款的
            # 独行编号块（1032 术语条目）号递增，不受影响。
            if _is_leader_run(nxt_txt) or _is_continuation_head(
                    m_gb.group(1), "", clauses):
                nxt_txt = ""
            if nxt_txt and not _CLAUSE_GB.match(nxt_txt.split("\n")[0]):
                current = SplitClause(
                    number=normalize_clause_number(m_gb.group(1)),
                    texts=[text, nxt_txt], items=[it, items[j]],
                    content_type="附录" if in_appendix else "normal",
                    rows=_rows_of(text, it)
                    + _rows_of(nxt_txt, items[j]))
                clauses.append(current)
                # 下一块已被消费，跳过它
                skip_idxs.add(j)
                continue
        # 2026-09-13 附录细分：in_appendix 时字母编号优先于 _CLAUSE_GB 判定。
        # 命中即建独立子条款（content_type=附录，随父块同型），保持附录头
        # 巨块继续存在（父条款保留——附录A 只有 82 字正文时切子块只会造空壳，
        # test_table_binding.py:66-77 还断言表 A.1 挂附录A）。多行块（MinerU
        # 常把子条款+正文+下一子条款并成一块）不在此 continue——落入下方行级
        # 循环逐行切，块内后续 "B.2 …" 才不会被首行 B.1 吞掉。
        m_ann = _CLAUSE_APPENDIX.match(text) if in_appendix else None
        ann_head = bool(m_ann) and _plausible_appendix_head(
            m_ann.group(1), m_ann.group(2)) \
            and not _is_continuation_head(
                re.sub(r"\s+", "", m_ann.group(1)),
                m_ann.group(2), clauses) if m_ann else False
        if ann_head and m_ann is not None and "\n" not in text:
            current = SplitClause(
                number=normalize_clause_number(
                    re.sub(r"\s+", "", m_ann.group(1))),
                texts=[text], items=[it], content_type="附录",
                rows=_rows_of(text, it))
            clauses.append(current)
            continue
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
                and not _is_continuation_head(m_gb.group(1), m_gb.group(2), clauses)
                and (in_appendix or len(m_gb.group(1)) >= 3
                     or m_gb.group(1).count(".") >= 1)):
            number = normalize_clause_number(m_gb.group(1))
            current = SplitClause(number=number, texts=[text], items=[it],
                                  content_type="附录" if in_appendix else "normal",
                                  rows=_rows_of(text, it))
            clauses.append(current)
        elif m_chap and is_chapter and _plausible_clause_head(
                m_chap.group(1), m_chap.group(2)) \
                and not _is_continuation_head(
                    m_chap.group(1), m_chap.group(2), clauses):
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
                    # 2026-09-13 附录细分行级：附录内多行块的行首 "A.1 …" 同样
                    # 切独立子条款（与块级 _CLAUSE_APPENDIX 分支同款闸门）。
                    m_ln_ann = _CLAUSE_APPENDIX.match(ln) if in_appendix else None
                    if m_ln_ann and _plausible_appendix_head(
                            m_ln_ann.group(1), m_ln_ann.group(2)) \
                            and not _is_continuation_head(
                                re.sub(r"\s+", "", m_ln_ann.group(1)),
                                m_ln_ann.group(2), clauses):
                        cur = SplitClause(
                            number=normalize_clause_number(
                                re.sub(r"\s+", "", m_ln_ann.group(1))),
                            texts=[ln], items=[it], content_type="附录",
                            rows=[(ln, it.page_idx, boxes[i])])
                        clauses.append(cur)
                        i += 1
                        while i < len(lines):
                            nxt = lines[i].strip()
                            m2a = _CLAUSE_APPENDIX.match(nxt)
                            if (m2a and _plausible_appendix_head(
                                    m2a.group(1), m2a.group(2))):
                                break
                            cur.texts.append(nxt)
                            cur.rows.append((nxt, it.page_idx, boxes[i]))
                            i += 1
                        continue
                    mm = _CLAUSE_GB.match(ln)
                    num = mm.group(1) if mm else ""
                    is_head = (bool(mm) and (len(num) >= 3 or num.count(".") >= 1)
                               and _plausible_clause_head(num, mm.group(2) if mm else "")
                               and not _is_continuation_head(
                                   num, mm.group(2) if mm else "", clauses))
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
                                    and _plausible_clause_head(n2, m2.group(2))
                                    and not _is_continuation_head(
                                        n2, m2.group(2), clauses)):
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


_RE_LEGEND_HEAD_ANY = re.compile(
    r"标.{0,3}序.{0,12}[：:]"          # 标引序号说明：/ 标引序号(符号)说明：
    r"|说\s*明\s*[：:]"                # 说明：（GB/T 10238-2015 实测）
    r"|图\s*中\s*[：:]")               # 图中：（GB/T 16422.3-2014 实测）
#: 图例条目（放宽到**任意符号/编号 + ——**）：'1——径向综合总公差'、'X ——温度 t'、
#: '4——接触销'。原先只认数字型 `\d{1,2}[—\-–~]{1,3}`，符号型条目（X/Y/H/dₙ₁）数不到。
_RE_LEGEND_ITEM_ANY = re.compile(
    r"(?<![\w])(?:[0-9A-Za-zΑ-Ωα-ω₀-₉ᵢₙₜₑ]{1,4})\s*[—–]{2,}\s*\S")


def strip_figure_legend_segment(text: str) -> str:
    r"""切掉条款文本里的**图例段**（「标引序号说明」及其条目）。

    2026-09-15 收敛循环第 6 轮立；第 17 轮（VLM 通道）按真实产物实测扩容。
    MinerU 常把**条款正文 + 图例 + 图注压进同一个文本块**，实测形态：

        B.2.1.2 异径接头 …见表 B.5。
        标引序号说明：
        dₙ₁ 、 dₙ₂ ——与异径长接头连接管材的公称外径；

    **第 17 轮扩的三处覆盖缺口**（VLM 通道实测，4 部全部漏判）：
      ① 条目与头**同行**：'标引序号说明：X ——温度 t，单位为℃；Y ——…'
         （GB/T 10002.1-2023）——原实现只看头的**后续行**，seg 为空 → 不切；
      ② 头**不在行首**：'…的径向综合公差标引序号说明：'（GB/T 10095.2-2023）
         ——原实现用 `^` 锚定，行中头匹配不到；
      ③ 头是**别的说法**：'说明：\n4——接触销；…'（GB/T 10238-2015）、
         '图中：1 ——CIE 85…'（GB/T 16422.3-2014）。

    保守护栏：段内必须有 **≥2 个 `符号——名称` 条目**才切（`说明：`/`图中：` 在正文里
    很常见，没有条目就不能切）；不满足则跳过该头继续找下一个头。

    **2026-09-15 新语料批次2 补第四种形态：图例条目在**图题行内/紧随其后且无头**
    （GB/T 23496-2009 实测）：
        '…不得超过算术平均值的 10%。\\n____\\n1——碱性橙 21;2——碱性橙 2;3——碱性橙 22。\\n图 A.1 …色谱图(波长:449'
        '图 A.2 碱性橙标准色谱图(波长:485 nm)1——碱性橙 21；2——碱性橙 2;3——碱性橙 22。'
    旧实现只认"有头"（`标引序号说明：`/`说明：`/`图中：`）→ 这类**全部漏切**。
    处置：见下方"无头图例"分支——**图题行内**的条目直接剥掉；**紧随图题其后**
    的条目行（≤2 行）整行删。护栏同上：起行须含 ≥2 个条目。
    """
    if not text or "—" not in text:
        return text
    for _ in range(10):
        lines = text.split("\n")
        cut = None
        for i, ln in enumerate(lines):
            for m in _RE_LEGEND_HEAD_ANY.finditer(ln):
                # 段 = 头行剩余 + 后续行（至图注行或结束）
                seg_head = ln[m.start():]
                rest = lines[i + 1:]
                end_rel = len(rest)
                for j, s in enumerate(rest):
                    if _RE_FIG_CAPTION_LINE.match(s):
                        end_rel = j
                        break
                seg = [seg_head] + rest[:end_rel]
                n_items = len(_RE_LEGEND_ITEM_ANY.findall("\n".join(seg)))
                # 强头（"标引序号…"）本身就是图例充分信号，1 个条目即切；
                # 弱头（"说明："/"图中："）正文里很常见，须 ≥2 条目才切。
                strong = bool(re.match(r"^\s*标.{0,3}序", seg_head))
                if (n_items < 2 and not (strong and n_items >= 1)):
                    continue        # 不是图例 → 找下一个头
                keep_before = lines[:i] + ([ln[:m.start()]] if ln[:m.start()].strip() else [])
                cut = "\n".join(keep_before + rest[end_rel:]).strip("\n")
                break
            if cut is not None:
                break
        if cut is None or cut == text:
            break
        text = cut
    # **先有头、后无头**（顺序关键，2026-09-15 实测）：无头分支若先跑，会把条目删掉
    # 而留下 '标引序号说明：' 头 —— 随后有头分支因"条目数 <2"不再匹配 → 头残留，
    # 回归测试 test_caption_terminates_segment 当场变红。故无头分支只作为**兜底**，
    # 处理"本来就没有头"的那一族（GB/T 23496-2009 图题 + 无头条目）。
    return _strip_headerless_legend(text)


def _strip_headerless_legend(text: str) -> str:
    r"""切掉**无头图例**：条目贴在图题上或紧随图题，没有 `标引序号说明：` 之类的头。

    实测形态（GB/T 23496-2009，新语料批次2）：
        '…不得超过算术平均值的 10%。\n____\n1——碱性橙 21;2——碱性橙 2;3——碱性橙 22。\n图 A.1 …色谱图'
        '图 A.2 碱性橙标准色谱图(波长:485 nm)1——碱性橙 21；2——碱性橙 2;3——碱性橙 22。'

    三条护栏（**图例必属某张图**）：
      ① 只在**图题邻域**动手（图题行内 / 图题前 1~4 行 / 图题后 1~2 行）；
      ② 判定用**窗口内累计条目数 ≥2**（单行 1 条可能是续行，如
         '3——阀座；7——螺栓。\n4——活塞；'）；
      ③ 回看可跨越装饰行（分隔线）与单字母类型标注（'b) B型'）——
         **不能一见空行就停**，否则永远够不到更前的真图例（实测图题紧邻前一行
         恰是 'b) B型'；此前写成 break 就是"护栏变断路"）。
    反向对照：`'—— 额定关合电流 5.12'` 这类标准引用列表**不含** `序号——名称`，
    不满足条目判据，不会被切（实测 GB/T 25307-2010 B.1 未误切）。
    """
    if not text or "—" not in text:
        return text
    _lines = text.split("\n")
    _drop: set[int] = set()
    _inline: dict[int, int] = {}
    for i, ln in enumerate(_lines):
        cap = _RE_FIG_CAPTION_LINE.match(ln)
        if not cap:
            continue
        start = cap.end()
        if len(_RE_LEGEND_ITEM_ANY.findall(ln[start:])) >= 2:
            _inline[i] = start
        for k in (i + 1, i + 2):
            if k < len(_lines) and _RE_LEGEND_ITEM_ANY.findall(_lines[k]):
                if len(_RE_LEGEND_ITEM_ANY.findall(_lines[k])) >= 2:
                    _drop.add(k)
                else:
                    break
            else:
                break
        _cand: list[int] = []
        _total = 0
        _skipped = 0
        for depth in range(1, 5):
            k = i - depth
            if k < 0:
                break
            ln_k = _lines[k]
            hits = _RE_LEGEND_ITEM_ANY.findall(ln_k)
            _st = ln_k.strip()
            _crossable = (not _st or set(_st) <= set("_-—–~ ")
                          or bool(re.match(r"^[a-zA-Z]\)\s*[A-Za-z]?\s*型?$", _st)))
            if hits:
                _cand.append(k)
                _total += len(hits)
                continue
            if _crossable and _skipped < 2:
                _skipped += 1
                continue
            break
        if _total >= 2:
            _drop.update(_cand)
    if not (_drop or _inline):
        return text
    _kept: list[str] = []
    for i, ln in enumerate(_lines):
        if i in _drop:
            continue
        if i in _inline:
            ln = ln[: _inline[i]]
        _kept.append(ln)
    return "\n".join(_kept)


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
        # 2026-09-15 追加 PUA 分隔符还原（U+E011/U+E788 → '-'/' '）+ 公式编号
        # 引导点线清洗（'……………( 1' → ' (1)'）+ 图例段切除（条款块内混入的
        # 「标引序号说明」条目）——三者都是全库审计达线类。
        #
        # **2026-09-15 抽为单一所有者** `text_utils.clean_clause_text`：次序原先
        # 只写在这一处，而自进化循环的评估器（`evolve.evaluate_doc`）对 VLM
        # 产物**原文**跑判据、从不经过本链 → 清洗器修好的类判据照旧报、留出集
        # 永远判不通过（结构性缺陷，实测）。抽出去后入库与评估同次序同结果。
        from src.core.text_utils import (clean_clause_text as _clean_text,
                                         normalize_pua_separators as _pua_sep,
                                         pua_bond_dash_html as _pua_dash)
        content = _pua_dash(content)
        content = _clean_text(content, legend_stripper=strip_figure_legend_segment,
                              own_standard_no=standard_no)
        tc = classify_clause(content, doc_type=doc_type)
        # 2026-09-14（执行计划 v3 阶段 2a）：识别层真实置信度首次接入
        # clause_revision.ocr_confidence（此前恒 1.0 无生产者——quality/
        # recognition.py 模块注释记录的假绿问题）。聚合 = min（最弱环节
        # 原则，评审裁决）：条款内任一文本 span 的 PP-OCR rec score 取最小。
        # 文本层文档 span 无 score（min_span_score=None）→ 保持 1.0 不变
        # （启发式预览口径不受扰，dry_run 路径行为不变）。
        span_scores = [it.min_span_score for it in cl.items
                       if it.min_span_score is not None]
        ocr_conf = (round(min(span_scores), 4) if span_scores else 1.0)
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
            ocr_confidence=ocr_conf,
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
                  number_to_id: dict[str, str],
                  unresolved_out: list[dict[str, Any]] | None = None
                  ) -> list[tuple[str, str, str, float, str]]:
    """把 raw_edges 解析成可落库的证据边元组（`(edge_type, src_id, dst_id, conf, status)`）。

    ⚠ 2026-09-16（iteration-6 自查 §8.2，代码级核实）：旧实现里**未解析成功的引用被
    静默丢弃** —— `if src and dst and src != dst:` 没有 else 分支、无日志、无计数。
    而"引用目标解析不到"（指向外部标准 / 指向本库未收录的条款号）**本身就是合规风险**：
    条款写着"应符合 GB XXXX 的 5.2.3"，而本库没有那一条，用户与检查者都无从知晓 ——
    这恰好打在 KS「可溯源」的价值主张上。

    参照 eyecite（BSD-2）对同族问题的纪律：**"歧义即不解析，但失败项必须留痕"**
    （`resolve.py:288-293` + 各 resolver 的 `len(matches)==1` 唯一命中判据）。

    修法保持**非破坏性**：返回值与既有调用方零改动；新增可选 `unresolved_out` ——
    传入时把每条未解析的边连同**未解析的是哪一端**与原因追加进去，由调用方落
    `event_log`（`run_full_ingest` 内已在同一写事务里这么做）。
    """
    out = []
    for e in raw_edges:
        if e["edge_type"] == "clause_relation":
            continue  # 表绑定已落在同一条款内部，不建自环边
        src, dst = number_to_id.get(e["src"]), number_to_id.get(e["dst"])
        if src and dst and src != dst:
            out.append((e["edge_type"], src, dst, e["conf"], e["status"]))
        elif unresolved_out is not None:
            if not src or not dst:
                reason = "unresolved_reference"
                missing = [p for p, v in (("src", src), ("dst", dst)) if not v]
            else:
                reason = "self_loop"      # src == dst：两端解析到了同一条款
                missing = []
            unresolved_out.append({
                "edge_type": e["edge_type"], "src": e["src"], "dst": e["dst"],
                "missing": missing, "conf": e.get("conf"), "reason": reason,
            })
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
        kt = str(p["knowledge_type"])
        type_dist[kt] = type_dist.get(kt, 0) + 1
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


def _cached_parse_result(parse_dir: Path, pdf_path: Path) -> dict[str, Any] | None:
    """从既有解析产物重建 run_parser_isolated 的等价 result（**零 OCR**）。

    2026-09-15（收敛循环 v2 立）：修复只发生在**后处理层**（条款头闸门 / 粘合 /
    LaTeX 空格 / 引导点线 / 图例 / PUA …）时，重导整库**不需要重新 OCR**——
    产物已缓存在 `parse_out/<doc_id>/`。本函数把缓存还原成解析器返回值形态，
    使 `run_full_ingest(reuse_parse=True)` 跳过 `run_parser_isolated`，全库重扫
    从「小时级云额度」降到「秒级零外发」。

    两种缓存形态（与 middle_locator / 文本层路径一致）：
    - `blocks.json` 非空 → 文本层路径（blocks + 几何自 PDF 重建）
    - `mineru/**/*_layout.json|*_middle.json` → 深度路径（deep_output 由
      run_full_ingest 用 middle_locator 再定位，故只需给 parse_dir）
    两者皆无 → None（调用方回退真解析）。
    """
    if not parse_dir.is_dir():
        return None
    blocks: list = []
    bp = parse_dir / "blocks.json"
    if bp.exists():
        try:
            raw = json.loads(bp.read_text(encoding="utf-8"))
            blocks = [b for b in raw if isinstance(b, dict) and b.get("text")]
        except Exception:  # noqa: BLE001 —— 缓存坏了就当没有，回退真解析
            blocks = []
    if blocks:
        geos: dict[int, dict] = {}
        try:
            import fitz
            with fitz.open(pdf_path) as d:
                for i, pg in enumerate(d, 1):
                    rect = pg.rect
                    geos[i] = {"width": rect.width, "height": rect.height,
                               "rotation": pg.rotation, "crop_box": [], "media_box": []}
        except Exception:
            logger.warning("复用产物：几何重建失败 %s", pdf_path.name, exc_info=True)
        logger.info("复用解析产物（文本层 blocks）：%d 块 (%s)", len(blocks), pdf_path.name)
        return {"blocks": blocks, "is_ocr": False, "geometries": geos,
                "deep_output": None, "text_layer_state": "ok",
                "deep_fallback_skipped": False, "parse_reused": "blocks"}
    from src.core.ingestion.middle_locator import find_middle_files
    if find_middle_files(parse_dir):
        logger.info("复用解析产物（深度）：%s", pdf_path.name)
        return {"blocks": [], "geometries": {}, "deep_output": str(parse_dir),
                "text_layer_state": "ok", "deep_fallback_skipped": False,
                "parse_reused": "deep"}
    return None


def run_full_ingest(pdf_path: Path, standard_no: str, standard_name: str,
                    short_code: str | None = None, doc_type: str = "standard",
                    domain_tags: list[str] | None = None,
                    legal_hierarchy: str = "GB",
                    reingest: bool = False,
                    force_deep: bool = True,
                    reuse_parse: bool = False,
                    product_dir: Path | None = None) -> dict:
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
    result = None
    if reuse_parse:
        # 2026-09-15（收敛循环 v2）：先尝试复用**既有文档**的解析产物（零 OCR）。
        # 既有文档 = 同 file_hash（dup）或同 standard_no（same_no）；新文档无缓存 → 回退真解析。
        for cand in (dup[0] if dup else None, same_no["doc_id"] if same_no else None):
            if not cand:
                continue
            result = _cached_parse_result(settings.data_dir / "parse_out" / cand, pdf_path)
            if result is not None:
                break
    # **复用"已有 OCR 产物目录"（2026-09-16 新增，OCR 循环配套通道）**：
    # 背景（实测确认，pipeline.py:1884）：不给这个入口时，入库一律走
    # `run_parser_isolated(pdf, parse_out/<doc_id>)` —— 即**重新解析**。
    # 而 OCR 循环因语料文档无 doc_id，产物落在 `parse_out/<_land_key(std_no)>`，
    # 与入库默认的 `parse_out/<doc_id>` 是**两套命名、互不相认**。
    # 于是"把循环产出的 8,484 部产物入库"会退化成**对同一批 PDF 重新 OCR 一遍**，
    # 把已有 VLM 产物整批废掉。
    #
    # 给了 `product_dir` 即**零重解析**：直接把该目录当作深度产物目录，
    # 下游经 `middle_locator.find_middle_files`（单一所有者）找到 `*_middle.json`
    # 后走既有 `load_middle_items` 通道。
    # `blocks` 显式置**空列表**（不是 None）：使 `_has_text_layer_ok` 为假，从而走
    # "深度产物"分支（这条分支本就为"无文本层 → 用 OCR 产物"设计，正是本场景）。
    # ⚠ 不能置 None：pipeline.py:2021 的封面块提取会**无条件**遍历
    # `result["blocks"]`，None 会抛 `TypeError: 'NoneType' object is not iterable`（实测踩过）。
    #
    # `geometries` 必须存在且为 **dict[int, dict]**（pipeline.py:2037
    # `insert_page_geometries` 逐个取 `g["width"]/g["height"]`，2096 还取 `len()`）。
    # 2026-09-16：**从源 PDF 取真实页尺寸**（fitz），而不是给空 dict——
    # 空 dict 会让 `doc_page_geometry` 无行、`pages_parsed` 记 0，
    # 进而**按页定位证据（原文跳页/高亮）对这批文档不可用**。
    # 实测：空 dict 时 3 部测试文档 页几何=0；用 fitz 填真实尺寸后应为真实页数。
    if product_dir is not None:
        pd = Path(product_dir)
        if not pd.is_dir():
            return {"status": "error", "message": f"产物目录不存在: {pd}"}
        geos: dict[int, dict] = {}
        try:
            import fitz  # noqa: PLC0415
            with fitz.open(str(pdf_path)) as _doc:
                for _i, _p in enumerate(_doc, 1):
                    _r = _p.rect
                    geos[_i] = {"width": _r.width, "height": _r.height,
                                "rotation": int(getattr(_p, "rotation", 0) or 0)}
        except Exception:  # noqa: BLE001
            geos = {}          # 取不到就退回空 dict（不阻断入库），但会记 0
        result = {"deep_output": str(pd), "blocks": [], "geometries": geos}
    if result is None:
        result = run_parser_isolated(pdf_path, settings.data_dir / "parse_out" / doc_id,
                                     force_deep=force_deep)
    deep_output = result.get("deep_output")
    # 2026-09-02 治本（正常入库识别流程丢字修复）：文本层完好（blocks 非空 = 非 OCR、
    # 非 PUA 错位归一化后可用）→ 正文用 fitz 文本层保真（MinerU 深度模型对文本层
    # 重识别丢数字/字母/标准号：GB/T 1000-2016 实测 10kV→空、GB/T 197→/）。
    # 仅真正无文本层（blocks 空）才用 MinerU 深度全文（OCR 通道）。
    _has_text_layer_ok = bool(result.get("blocks"))
    if deep_output and not _has_text_layer_ok:
        # 2026-09-14（OCR 循环轮次 1）：云产物改名 layout.json 后此处硬编码
        # rglob("*_middle.json") 不认 → 云通道成功产物被误判「未找到」。
        # 模式契约统一走 middle_locator（单一所有者）。
        from src.core.ingestion.middle_locator import find_middle_files
        middle_files = find_middle_files(Path(deep_output))
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
    # 未解析引用留痕（iteration-6 自查 §8.2）：旧实现静默丢弃 → 引用断链不可观测。
    unresolved_refs: list[dict[str, Any]] = []
    edges = resolve_edges(raw_edges, number_to_id, unresolved_refs)

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
        # 未解析引用落 event_log（**同一写事务**，守单写者纪律 §16.4 铁律 3）——
        # 让"引用断链"从不可观测变成可查询（iteration-6 自查 §8.2）。
        # items 截断 50 条：本表是审计/回溯用途，不是全量转储。
        if unresolved_refs:
            txn.execute(
                "INSERT INTO event_log (event_id, event_type, actor, target_type,"
                " target_id, metadata) VALUES (?,?,?,?,?,?)",
                (f"evt_{ULID()}", "ingest_unresolved_refs", "pipeline", "doc", doc_id,
                 json.dumps({"count": len(unresolved_refs),
                             "items": unresolved_refs[:50]}, ensure_ascii=False)))
            logger.warning(
                "入库存在未解析引用 %d 条（已落 event_log）: %s",
                len(unresolved_refs),
                [f"{u['src']}->{u['dst']}" for u in unresolved_refs[:5]])
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
                         "edges": len(edges),
                         "unresolved_refs": len(unresolved_refs)}, ensure_ascii=False)))

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
            "unresolved_refs": len(unresolved_refs),
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
