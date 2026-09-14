# -*- coding: utf-8 -*-
"""图形区域定位（2026-08-29，GB/T 34406 图1/图A.1/图A.2 实测，语料级通用）。

用户诉求：「流程图、X轴Y轴点状图没识别出来……数学图形的可以直接截图」——
扫描双层 PDF 的图形（流程图/散点图）是整页扫描图的一部分，无独立图像对象
可抠；GB 图题格式固定（'图1 定性分析判定程序图'/'图A.1 判别分析相关图'，
居中、紧贴图形下方），以题注为锚、按「题注上方最近正文行的下缘」圈定图区，
fitz 渲染 PNG 截图（与 PDF 同源，永远不脏）。

规则（全语料级，无文档特判）：
- 题注：行文本（PUA 归一化后）匹配 `^图\\s*[0-9A-Z]+(?:\\.[0-9A-Z]+)?\\s*\\S`，
  且行宽 < 60% 页宽（居中短行——正文行很少以'图N'开头且行首；编号引用如
  '参见图A.2' 不会 ^图 起头）。
- 上界：同页题注上方最近的「正文行」下缘 + 6pt——正文行 = 水平行之外的
  水平行（斜排 dir≠0 是水印、页眉区 y1≤0.12*ph 是书眉、题注自身除外）。
  上方无正文行（题注贴页首）→ 0.10*ph。
- 下界：题注 y0 - 4pt。
- 横向：该页正文行 x 并集收窄（无正文 → 页宽 8% ~ 92%）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_RE_FIG_CAPTION = re.compile(r"^图\s*[0-9A-Z]+(?:\.[0-9A-Z]+)?\s*\S")


def _page_lines(page, normalize):
    """行级文本收集：[(y0, y1, x0, x1, dir_y, text)]，PUA 归一化后。"""
    out = []
    d = page.get_text("dict")
    ph = page.rect.height
    for blk in d.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for ln in blk.get("lines", []):
            t = "".join((sp.get("text") or "") for sp in ln.get("spans", [])).strip()
            if not t:
                continue
            if normalize:
                t = normalize(t)
            bb = ln["bbox"]
            dir_y = (ln.get("dir") or (1.0, 0.0))[1]
            out.append((bb[1], bb[3], bb[0], bb[2], dir_y, t, ph))
    return out


def locate_figure(pdf_path: str | Path, fig_no: str, normalize=None):
    """定位图区。返回 (page_no0, (x0, y0, x1, y1)) 或 None。

    fig_no：图号（'1'、'A.1'、'B.2'…）；题注正则按整号锚定，'图1' 不会
    误中 '图A.1'（图后字符不同）。多页同号取首个命中。
    """
    import fitz

    doc = fitz.open(str(pdf_path))
    try:
        pat = re.compile(r"^图\s*" + re.escape(fig_no) + r"(?![0-9A-Za-z.])\s*\S")
        for pno in range(len(doc)):
            page = doc[pno]
            ph, pw = page.rect.height, page.rect.width
            lines = _page_lines(page, normalize)
            cap = None
            for (y0, y1, x0, x1, dir_y, t, _ph) in lines:
                if abs(dir_y) > 0.01:  # 斜排=水印
                    continue
                if pat.match(t) and (x1 - x0) < pw * 0.6:
                    cap = (y0, y1, x0, x1)
                    break
            if cap is None:
                continue
            cap_y0, cap_y1 = cap[0], cap[1]
            # 上界：题注上方最近正文行（排除书眉/斜排水印/其他题注）
            body_bottom = ph * 0.10
            for (y0, y1, x0, x1, dir_y, t, _ph) in lines:
                if y1 >= cap_y0 - 2:  # 题注及其下方
                    continue
                if abs(dir_y) > 0.01 or y1 <= ph * 0.12:
                    continue
                if _RE_FIG_CAPTION.match(t):
                    continue  # 更靠上的其他图题（同页多图时上界取两题注之间）
                if y1 > body_bottom:
                    body_bottom = y1
            # 横向固定正文区：图A.1 形态（题注上方无正文行）行级收窄会把散点图
            # 裁到仅 caption 宽（实测 125pt 丢坐标系）——多留白边无害，裁轴致命。
            # 余量 2pt：34406 图1 正文行下缘距流程图顶框仅 ~4pt，6pt 会裁掉框顶
            # （实测顶部框连通域 y=0 贴边）；文字行 y1 即墨迹下缘，2pt 不吞正文。
            rect = fitz.Rect(pw * 0.08, body_bottom + 2, pw * 0.92,
                             max(body_bottom + 12, cap_y0 - 4))
            if rect.height < 24:  # 图区过矮=定位异常，宁缺勿滥
                continue
            return pno, (rect.x0, rect.y0, rect.x1, rect.y1)
    finally:
        doc.close()
    return None


def locate_middle_figure(parse_root: str | Path, fig_no: str) -> Path | None:
    """middle.json 兜底（2026-09-01 排版还原 C3）：文字层题注锚定失败时，
    从 MinerU 深度解析产物取预裁剪插图。

    MinerU 把每个图形区裁成 images/<sha256>.jpg（image_body 内 image_path
    相对引用），题注在 image_caption 子块——与 PDF 同源（深度解析的裁剪
    边界即模型认定的图形区），比 fitz 估算裁剪更准。返回图片文件路径或
    None。parse_root = parse_out/<doc_id>；防穿越：命中文件 resolve 后必须
    仍落在 parse_root 内。
    """
    hit = locate_middle_figure_full(parse_root, fig_no)
    return hit[0] if hit is not None else None


def locate_middle_figure_full(
    parse_root: str | Path, fig_no: str,
) -> tuple[Path, int, list[float], list[float]] | None:
    """middle.json 兜底（含几何）：返回 (图片路径, page_no(1-based),
    bbox_px, page_size_px)；未命中 None。bbox/page_size 供端点按原版
    比例还原尺寸/位置（2026-09-02 用户契约：截图尺寸与原件一致）。
    """
    root = Path(parse_root)
    if not root.is_dir():
        return None
    root = root.resolve()
    pat = re.compile(r"^图\s*" + re.escape(fig_no) + r"(?![0-9A-Za-z.])")
    # 2026-09-14（OCR 循环轮次 1）：middle 产物定位统一 middle_locator
    # （云产物改名 layout.json，旧硬编码不认）。
    from src.core.ingestion.middle_locator import iter_middle_files
    for mj_path in iter_middle_files(root):
        try:
            mj = json.loads(mj_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for page in mj.get("pdf_info", []):
            bbox_px = None
            cap_text, img_rel = "", None
            for block in page.get("para_blocks") or []:
                if block.get("type") != "image":
                    continue
                for sub in block.get("blocks") or []:
                    st = sub.get("type")
                    if st == "image_caption":
                        for ln in sub.get("lines") or []:
                            for sp in ln.get("spans") or []:
                                cap_text += sp.get("content") or ""
                    elif st == "image_body":
                        for ln in sub.get("lines") or []:
                            for sp in ln.get("spans") or []:
                                if sp.get("image_path"):
                                    img_rel = sp["image_path"]
                cap_text = cap_text.strip()
                if not img_rel or not pat.match(cap_text):
                    cap_text, img_rel = "", None
                    continue
                bbox_px = block.get("bbox")
                if isinstance(bbox_px, list) and len(bbox_px) == 4:
                    bbox_px = [float(x) for x in bbox_px]
                else:
                    bbox_px = None
                # MinerU 落盘约定：middle.json 同级 images/<sha256>.jpg；旧产物
                # image_path 可能自带 images/ 前缀 → 双形态都试（GB/T 24276
                # 实测：image_path 裸文件名，物理文件在 images/ 子目录）。
                img = (mj_path.parent / img_rel).resolve()
                if not img.is_file():
                    img = (mj_path.parent / "images" / img_rel).resolve()
                if (root in img.parents
                        and img.suffix.lower() in (".jpg", ".jpeg", ".png")
                        and img.is_file()):
                    sz = page.get("page_size") or [0, 0]
                    try:
                        page_size = [float(sz[0]), float(sz[1])]
                    except (TypeError, ValueError, IndexError):
                        page_size = [0.0, 0.0]
                    pno = int(page.get("page_idx", 0)) + 1
                    return img, pno, bbox_px or [], page_size
                # 2026-09-02 修复：匹配 block 的图片无效（越界/不存在）时
                # **不得 break**——同页可能多图同号，须继续扫描取首个有效者
                # （此前 break 使 ../../ 越界图提前终止 → 合法图永远找不到）
                cap_text, img_rel = "", None
            if img_rel is None:
                continue
    return None


def locate_middle_caption(parse_root: str | Path, fig_no: str):
    """OCR 题注锚定（2026-09-02 C1 统一图对象层第三途径）：题注在 middle.json
    OCR 文本块（text_blocks）但**无版面图对象**（无 image/chart 块，MinerU 漏
    识别，如 24276 图 A.3）时，以题注行为锚，按「题注上方最近正文块下缘」圈定
    图区（GB 图题在图下方）→ 返回 (page_no1, (x0,y0,x1,y1)) 或 None。

    bbox 为 middle.json 原系（顶原点，与 /figure 端点 clip 一致）。
    """
    from src.core.middle_geo import load as _load_middle_geo
    import re as _re
    geo = _load_middle_geo(Path(parse_root))
    if geo is None:
        return None
    pat = _re.compile(r"^图\s*" + _re.escape(fig_no) + r"(?![0-9A-Za-z.])")
    for pno in sorted(geo.pages):
        prev_bottom: float | None = None
        for bbox, text in geo.text_blocks(pno):
            if any(pat.match(ln.strip()) for ln in text.split("\n")):
                # 题注块：图区 = 题注上方（正文块下缘）到题注顶。
                # 2026-09-02 改进：图内/近题注文字块（y1 距 cap_top <60）会当
                # 正文 → 图区过矮<24px（A.3 实测 404）→ 用**题注上方 y1 <
                # cap_top-60 的最近正文块下缘**；无 → 固定 cap_top-260 高。
                cap_top = float(bbox[1])
                bottom = None
                for (b2, _t2) in geo.text_blocks(pno):
                    y1 = float(b2[3])
                    if y1 < cap_top - 60.0:
                        if bottom is None or y1 > bottom:
                            bottom = y1
                if bottom is None:
                    bottom = cap_top - 260.0
                if cap_top - bottom < 24:
                    continue   # 图区过矮=定位异常
                return pno, (float(bbox[0]) - 8.0, bottom,
                             float(bbox[2]) + 8.0, cap_top)
            b = float(bbox[3])
            if prev_bottom is None or b > prev_bottom:
                prev_bottom = b
    return None
