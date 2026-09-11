# -*- coding: utf-8 -*-
"""公式区域定位（2026-08-29，语料级、零文档特判）。

背景：双层扫描 PDF 的文字层把二维公式（根号套分式、求和带上下限）压平成
线性串，全文只能给数学读序。原排版复刻 = 按公式编号定位原图区域 → 高清
clip 截图 → 前端注入（与 fig-embed 同款模式）。

定位策略（spans 主导）：
1. 编号锚：页面 spans 中，归一化 text 尾匹配 (N)/（N）且右缘 ≥75% 页宽
   （GB 公式编号恒右对齐页缘，正文引用 "(1)" 在行中部不会命中）
2. 公式 spans：编号左侧、同一 y 带（编号行向上 ≤2.3 行高覆盖分式分子）、
   CJK 占比 ≤0.5 或长度 ≤8（剔除混入 y 带的中文说明行）
3. bbox = 公式 spans 并集 + 6pt pad；无命中返回 None（宁缺勿滥）
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

import fitz

_NUM_TAIL = re.compile(r"[(（]\s*(\d{1,2})\s*[)）]\s*\.?\s*$")
_CJK = re.compile(r"[\u4e00-\u9fff]")


def _norm(s: str) -> str:
    """NFKC 折叠 + 去空白（全角/半角编号统一）。"""
    import unicodedata
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").replace("\u00a0", "")


def _number_anchor(page, target: str):
    """页面上右对齐编号锚 (target) 的 bbox（pt）；无命中 None。

    GB 公式编号恒右对齐页缘，正文引用 "(1)" 在行中部不会命中。
    """
    pw = page.rect.width
    anchors = []
    for blk in page.get_text("dict").get("blocks", []):
        for line in blk.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            joined = _norm("".join(sp.get("text", "") for sp in spans))
            m = _NUM_TAIL.search(joined)
            if not m or m.group(1) != target:
                continue
            lx1 = max(sp["bbox"][2] for sp in spans)
            lx0 = min(sp["bbox"][0] for sp in spans)
            ly0 = min(sp["bbox"][1] for sp in spans)
            ly1 = max(sp["bbox"][3] for sp in spans)
            if lx1 < pw * 0.75:      # 编号恒右对齐页缘
                continue
            if ly1 > page.rect.height * 0.96 or ly0 < page.rect.height * 0.02:
                continue            # 页眉页脚排除
            anchors.append((lx0, ly0, lx1, ly1))
    if not anchors:
        return None
    return max(anchors, key=lambda a: a[2])  # 最靠右缘者


def locate_formula(
    pdf_path: str,
    page_no: int,
    fno: str,
) -> Optional[Tuple[int, Tuple[float, float, float, float]]]:
    """在 page_no（1-based）页定位式(fno) 的 bbox。

    返回 (page_index0, (x0, y0, x1, y1))，pt 坐标；定位失败 None。
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None
    try:
        pno = int(page_no) - 1
        if pno < 0 or pno >= len(doc):
            return None
        page = doc[pno]
        pw = page.rect.width
        target = str(int(fno)) if str(fno).isdigit() else str(fno)

        d = page.get_text("dict")
        # 1) 编号锚：行级拼接匹配（编号常被拆成 （ ２ ） 三个独立 span）
        anchor = _number_anchor(page, target)
        if anchor is None:
            return None
        ax0, ay0, ax1, ay1 = anchor
        h = max(ay1 - ay0, 8.0)

        # 2) 公式 spans：按行收集（锚行 y 带 ±1.1/0.6 行高，覆盖分式与根号大字形），
        #    行 joined 含数学字符者为种子行；xmin = 种子行左缘 - 12（GB 标题/说明
        #    顶格 x≈60-84，公式块缩进 x≈230+，种子行左缘可剔除前者并保留 RMSEP 等变量）
        _MATH = ("=", "＝", "∑", "√", "槡", "－", "×", "÷", "＋", "／")
        cand_lines = []
        for blk in d.get("blocks", []):
            for line in blk.get("lines", []):
                rows = []
                joined = ""
                for sp in line.get("spans", []):
                    if sp["bbox"][0] > ax0 - 2:
                        continue        # 锚行残余（编号数字等）剪掉
                    txt = (sp.get("text") or "").strip()
                    if not txt or not re.sub(r"[\s\W]", "", txt, flags=re.UNICODE):
                        continue        # 纯标点/空白 span 不参与定界
                    joined += txt
                    rows.append(sp)
                if not rows:
                    continue
                lx0 = min(sp["bbox"][0] for sp in rows)
                cy = sum((sp["bbox"][1] + sp["bbox"][3]) / 2 for sp in rows) / len(rows)
                if not (ay0 - 1.1 * h <= cy <= ay1 + 0.6 * h):
                    continue
                cjk = len(_CJK.findall(joined))
                if len(joined) > 8 and cjk / max(len(joined), 1) > 0.5:
                    continue            # 中文说明行剔除
                cand_lines.append((lx0, rows, joined))
        seed_rows = [cl for cl in cand_lines if any(mk in cl[2] for mk in _MATH)]
        if not seed_rows:
            return None
        xmin = min(cl[0] for cl in seed_rows) - 12
        parts = [sp for cl in cand_lines if cl[0] >= xmin for sp in cl[1]]
        if not parts:
            return None
        bx0 = min(sp["bbox"][0] for sp in parts) - 6
        # y0 顶格：fitz 行框已含字形上伸部（∑上限、根号顶），再向上填充只会
        # 吃进上一行正文底部（实测 GB/T 34406 式(1) 被切进上一行 ~6pt=行高 18%）
        by0 = min(sp["bbox"][1] for sp in parts)
        bx1 = min(ax0 - 2, max(sp["bbox"][2] for sp in parts) + 6)
        # y1 只留 1pt 下伸余量（下标/分母行框下缘）；过多会碰下一行（下方文字
        # 由 x 范围兜底，但居右延续文字 x 会落入 rect）
        by1 = max(max(sp["bbox"][3] for sp in parts) + 1, ay1)
        rect = fitz.Rect(max(bx0, 0), max(by0, 0), min(bx1, pw), min(by1, page.rect.height))
        if rect.width < 20 or rect.height < 10:
            return None
        return pno, (rect.x0, rect.y0, rect.x1, rect.y1)
    except Exception:
        return None
    finally:
        try:
            doc.close()
        except Exception:
            pass


def _number_anchor_middle(geo, page_no: int, target: str):
    """middle.json OCR 产物里的右对齐编号锚 (target) bbox（px，MinerU 坐标）。

    纯扫描 PDF（无文字层）的 fitz 锚定失效——OCR 文本块（type=text）带 bbox，
    编号 (N) 恒右对齐页缘（x1 > 75% 页宽），正文引用在行中部不会命中。
    返回 (x0, y0, x1, y1) px 或 None。
    """
    sz = geo.size(page_no)
    if not sz or sz[0] <= 0:
        return None
    for bbox, txt in geo.text_blocks(page_no):
        x0, y0, x1, y1 = bbox
        if x1 < sz[0] * 0.75:
            continue
        m = _NUM_TAIL.search(_norm(txt))
        if m and m.group(1) == target:
            return (x0, y0, x1, y1)
    return None


def locate_eq_by_number(pdf_path: str, page_no: int, fno: str,
                        parse_root) -> Optional[Tuple[int, Tuple[float, float, float, float]]]:
    """MinerU 深度解析的独立公式块定位（2026-09-02 全局序策略）。

    背景：24276 实测（纯扫描 PDF，fitz 文字层全空）——MinerU 版面模型把每个
    公式识别为 interline_equation block（bbox + LaTeX，页码序 = 阅读序），
    全文公式数（24）与编号 (1)..(24) 一一对应（GB 公式编号全局递增）。
    而文字层编号锚在纯扫描件不可用（OCR 文本块里编号常并入公式行/缺失）。

    策略：fno 视为**全局公式序号** → middle.json 全页累计第 fno 个公式块的
    (page, idx) → bbox。tag 校验：该块 LaTeX 含 `\tag{…(fno)}`（附录公式
    编号形态）时确认命中；无 tag（正文公式）按阅读序 = 编号序，仍可靠。
    无深度产物/公式数不足 → None（调用方回退文字层 spans 启发）。

    返回 (page_index0, (x0, y0, x1, y1)) pt 坐标。
    """
    from src.core.middle_geo import load as load_middle_geo
    import fitz

    target = str(int(fno)) if str(fno).isdigit() else str(fno)
    try:
        idx = int(target) - 1
    except (TypeError, ValueError):
        return None
    if idx < 0:
        return None
    geo = load_middle_geo(parse_root)
    if geo is None:
        return None
    # 全页累计（pdf_info 序 = PDF 页序，阅读序）
    acc = 0
    hit_page = hit_blk = None
    for pno in sorted(geo.pages):
        eqs = geo.eq_blocks(pno)
        if not eqs:
            continue
        if acc + len(eqs) > idx:
            hit_page, hit_blk = pno, eqs[idx - acc]
            break
        acc += len(eqs)
    if hit_page is None or hit_blk is None:
        return None
    bbox, latex = hit_blk
    # tag 校验：块 LaTeX 含编号时须与目标一致（防漏检公式造成全局序漂移）；
    # 实际形态 '\\tag{………………(A.3}'（点线引导、编号后即 }，无右括号）
    tag_m = re.search(r"\\tag\{[^}]*?[（(]\s*([0-9A-Za-z.]+)", latex or "")
    if tag_m and tag_m.group(1) != target:
        return None
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None
    try:
        pno = int(hit_page) - 1
        if pno < 0 or pno >= len(doc):
            return None
        page = doc[pno]
        sz = geo.size(hit_page)
        if not sz or sz[0] <= 0 or sz[1] <= 0:
            return None
        sx = page.rect.width / sz[0]
        sy = page.rect.height / sz[1]
        rect = fitz.Rect(bbox[0] * sx, bbox[1] * sy, bbox[2] * sx, bbox[3] * sy)
        pw, ph = page.rect.width, page.rect.height
        rect = fitz.Rect(max(rect.x0, 0), max(rect.y0, 0),
                         min(rect.x1, pw), min(rect.y1, ph))
        if rect.width < 8 or rect.height < 6:
            return None
        return pno, (rect.x0, rect.y0, rect.x1, rect.y1)
    except Exception:
        return None
    finally:
        try:
            doc.close()
        except Exception:
            pass
