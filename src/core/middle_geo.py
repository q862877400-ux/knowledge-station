# -*- coding: utf-8 -*-
"""MinerU middle.json 几何缓存（2026-09-02，表格/图片/独立公式 bbox 页级索引）。

背景：双层扫描 PDF 的深度解析产物 middle.json
（parse_out/<doc_id>/mineru/*/auto/*_middle.json）的 para_blocks 带版面坐标
（bbox，MinerU 内部像素坐标，页顶原点 y 向下），page_size 提供归一化基准。
文字层把二维对象（公式/图/带图表格）压平成线性串，原排版只存在于版面坐标
——本模块按页收集三类几何，供展示层与端点「按原版排布」：

- tables: type=table —— 带图表格 = 同页 table bbox 与 image bbox 有交集，
  按用户契约（2026-09-02）整个表格当图片处理（table-embed 截图）；
- images: type=image —— 图区 bbox（/figure 端点 middle 兜底的比例基准）；
- eqs:    type=interline_equation —— 独立公式块 bbox，比 formula_locator
  文字层启发式更精确的原排版截图锚点（/formula 端点优先取用）。

坐标一律以「页宽/页高比例」归一化输出（frac_x0/frac_w/frac_h），消费端
（server 端点）再乘回 fitz 页 pt 尺寸 → clip 渲染，与 PDF 同源永远不脏。

进程内缓存：parse_root + mtime 键控，同一文档重复渲染零重读；文件被重导
覆盖后 mtime 变化自动失效。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

#: 进程内缓存：{parse_root_str: (mtime_ns, Cache)}
_cache: Dict[str, Tuple[int, "MiddleGeo"]] = {}


class MiddleGeo:
    """页级几何索引。page_no 1-based。"""

    def __init__(self, pages: Dict[int, Dict[str, Any]], sizes: Dict[int, Tuple[float, float]]):
        self.pages = pages          # {page_no: {"tables": [bbox], "images": [bbox], "eqs": [bbox]}}
        self.sizes = sizes          # {page_no: (w_px, h_px)}

    def page(self, page_no: int) -> Optional[Dict[str, Any]]:
        return self.pages.get(int(page_no))

    def size(self, page_no: int) -> Optional[Tuple[float, float]]:
        return self.sizes.get(int(page_no))

    def tables(self, page_no: int) -> List[List[float]]:
        pg = self.page(page_no)
        return (pg or {}).get("tables", [])

    def images(self, page_no: int) -> List[List[float]]:
        pg = self.page(page_no)
        return (pg or {}).get("images", [])

    def eqs(self, page_no: int) -> List[List[float]]:
        pg = self.page(page_no)
        return [e[0] for e in (pg or {}).get("eqs", [])]

    def eq_blocks(self, page_no: int) -> List[Tuple[List[float], str]]:
        """独立公式块（interline_equation）：bbox px + LaTeX 行（含 \tag 编号）。"""
        pg = self.page(page_no)
        return (pg or {}).get("eqs", [])

    def text_blocks(self, page_no: int) -> List[Tuple[List[float], str]]:
        """OCR 文本块（type=text，bbox px + 行拼接文本）——纯扫描 PDF 的
        文字层替代源（编号锚/图题锚定用，2026-09-02）。"""
        pg = self.page(page_no)
        return (pg or {}).get("texts", [])

    def charts(self, page_no: int) -> List[Tuple[List[float], str]]:
        """曲线/图表（type=chart）：bbox px + 题注文本（图1-8、图A.2/A.5）。
        2026-09-02 修复：此前只处理 image → 曲线图全部缺失。"""
        pg = self.page(page_no)
        return (pg or {}).get("charts", [])

    def chart_by_caption(self, fig_no: str):
        """按题注图号（如 '1'、'A.2'）在全部页找 chart，返回 (page_no,
        bbox, caption) 或 None——/figure 端点优先定位（curve 图缺 image 块）。
        用 search（含正文混入的题注，如 '•排气口…图 5 带通风口'），防扫描件
        题注被 OCR 合并进正文。"""
        import re as _re
        pat = _re.compile(r"图\s*" + _re.escape(fig_no) + r"(?![0-9A-Za-z.])")
        for pno, pg in self.pages.items():
            for bbox, cap in pg.get("charts", []):
                if pat.search(cap):
                    return pno, bbox, cap
        return None

    def chart_by_no(self, fig_no: str):
        """数字图号兜底（2026-09-02 图4/6/8）：部分曲线图题注被 OCR 合并进
        正文（p13/15/17 的 chart cap 无图号），但正文数字图（图1-8）页序 =
        图号序（p9,10,12..17 依次 = 图1..图8，恰好 8 个数字 chart）。本方法按
        页序遍历数字 chart（跳过附录图 图A./图B.）计数定位第 N 个；附录图
        号（A.x）回退 chart_by_caption。"""
        import re as _re
        if not _re.match(r"^\d+$", fig_no or ""):
            return self.chart_by_caption(fig_no)
        target = int(fig_no)
        seq = 0
        for pno in sorted(self.pages):
            for bbox, cap in self.pages[pno].get("charts", []):
                if _re.match(r"\s*图\s*[AB]\.", cap.strip()):
                    continue   # 附录图不占数字图序
                seq += 1
                if seq == target:
                    return pno, bbox, cap
        return None

    def figures(self) -> List[dict]:
        """统一图对象（2026-09-02 C1 架构根治）：合并 image + chart 版面图，
        各带 (页, bbox, 题注, 图号, kind)。**题注权威 = 版面模型**（image_caption
        / chart caption）——渲染/注入统一消费，取代 content_text 正则猜题注/
        引用（后者把"图4 的系数c取决于…"引用句误当题注注入 → 错位）。
        图号：题注提取；题注被 OCR 合并（无图号）则用**数字图全局页序计数**
        兜底（图 4/6/8 = 第 4/6/8 个数字 chart）——跨条款一致，供渲染统一注入。"""
        import re as _re
        out: List[dict] = []
        num_seq = 0
        for pno, pg in self.pages.items():
            for bbox, cap in pg.get("img_caps", []):
                fm = _re.search(r"图\s*([0-9A-Z.]+)\s*[^0-9A-Za-z.]", cap or "")
                if fm:
                    out.append({"page": pno, "bbox": bbox, "caption": cap,
                                "no": fm.group(1), "kind": "image"})
            for bbox, cap in pg.get("charts", []):
                if _re.match(r"\s*图\s*[AB]\.", cap.strip()):
                    fm = _re.search(r"图\s*([0-9A-Z.]+)\s*[^0-9A-Za-z.]", cap or "")
                    if fm:
                        out.append({"page": pno, "bbox": bbox, "caption": cap,
                                    "no": fm.group(1), "kind": "chart"})
                    continue   # 附录图不占数字图序（另按题注）
                num_seq += 1
                fm = _re.search(r"图\s*([0-9A-Z.]+)\s*[^0-9A-Za-z.]", cap or "")
                out.append({"page": pno, "bbox": bbox, "caption": cap,
                            "no": (fm.group(1) if fm else str(num_seq)),
                            "kind": "chart"})
        return out

    def assets(self) -> List[dict]:
        """全部 image asset（页 + bbox + 文件名），供渲染统一注入。
        C1 收尾：无题注的孤儿 image（split 未绑条款 → figure_html 丢，如
        30871 p6 图）在 render 层按物理页补插，不再依赖 C2 绑定成功。"""
        out: List[dict] = []
        for pno, pg in self.pages.items():
            for bbox, ipath in pg.get("img_paths", []):
                out.append({"page": pno, "bbox": bbox, "path": ipath})
        return out

    def image_bbox_by_path(self, fname: str):
        """按裁剪文件名（images/<sha256>.jpg 的裸名）反查 image bbox。

        返回 (page_no, bbox_px) 或 None——/assets 端点按 fname 定位原图
        在原页的位置/尺寸（2026-09-02 需求2：截图与原版同尺寸同位）。
        """
        for pno, pg in self.pages.items():
            for bbox, ip in pg.get("img_paths", []):
                if ip == fname or ip.endswith("/" + fname):
                    return pno, bbox
        return None

    def image_hit_tables(self, page_no: int) -> List[int]:
        """该页「带图表格」序号（tables 列表内索引，升序）。交集面积 >0 即算。"""
        tabs = self.tables(page_no)
        if not tabs:
            return []
        imgs = self.images(page_no)
        if not imgs:
            return []
        hit: List[int] = []
        for i, t in enumerate(tabs):
            for im in imgs:
                if _inter_area(t, im) > 0:
                    hit.append(i)
                    break
        return hit

    def frac(self, page_no: int, bbox: List[float]) -> Optional[Tuple[float, float, float]]:
        """bbox 像素 → (frac_x0, frac_w, frac_h)（页宽/页高比例）。"""
        sz = self.size(page_no)
        if not sz or len(bbox) != 4:
            return None
        w, h = sz
        if w <= 0 or h <= 0:
            return None
        return (bbox[0] / w, (bbox[2] - bbox[0]) / w, (bbox[3] - bbox[1]) / h)


def _inter_area(a: List[float], b: List[float]) -> float:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _find_middle_jsons(parse_root: Path) -> List[Path]:
    """定位全部 middle.json（任意深度，防穿越）。一个 parse_root 下可能有
    多次深度解析的子任务产物（pre_ 残留），全部合并——页级 bbox 无冲突。"""
    root = parse_root.resolve()
    if not root.is_dir():
        return []
    out: List[Path] = []
    for mj in sorted(root.rglob("*_middle.json")):
        try:
            mj.resolve().relative_to(root)
            out.append(mj)
        except ValueError:
            continue
    return out


def load(parse_root: str | Path) -> Optional[MiddleGeo]:
    """读取并缓存 parse_root 的几何索引；无深度产物返回 None。"""
    root = Path(parse_root)
    key = str(root.resolve())
    try:
        mtime = root.stat().st_mtime_ns if root.exists() else -1
    except OSError:
        mtime = -1
    hit = _cache.get(key)
    if hit and hit[0] == mtime:
        return hit[1]
    mj_paths = _find_middle_jsons(root)
    if not mj_paths:
        _cache[key] = (mtime, None)  # type: ignore[arg-type]
        return None
    pages: Dict[int, Dict[str, Any]] = {}
    sizes: Dict[int, Tuple[float, float]] = {}
    any_ok = False
    for mj_path in mj_paths:
        try:
            mj = json.loads(mj_path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 - 坏产物不阻塞，视为无深度几何
            logger.warning("middle.json 读取失败 %s: %s", mj_path, e)
            continue
        for page in mj.get("pdf_info") or []:
            try:
                pno = int(page.get("page_idx", 0)) + 1
            except (TypeError, ValueError):
                continue
            sz = page.get("page_size") or [0, 0]
            try:
                sizes[pno] = (float(sz[0]), float(sz[1]))
            except (TypeError, ValueError, IndexError):
                sizes[pno] = (0.0, 0.0)
            entry = pages.setdefault(
                pno, {"tables": [], "images": [], "eqs": [], "texts": [], "charts": []})
            for blk in page.get("para_blocks") or []:
                bb = blk.get("bbox")
                if not isinstance(bb, list) or len(bb) != 4:
                    continue
                t = blk.get("type")
                bbox = [float(x) for x in bb]
                if t == "table":
                    entry["tables"].append(bbox)
                elif t == "image":
                    entry["images"].append(bbox)
                    # image 题注（image_caption 子块文本）——figure() 统一图对象
                    # 用它作为题注权威（取代 content_text 正则猜题注/引用）
                    icap = ""
                    for sub in blk.get("blocks") or []:
                        if sub.get("type") == "image_caption":
                            for ln in sub.get("lines") or []:
                                for sp in ln.get("spans") or []:
                                    icap += sp.get("content") or ""
                    entry.setdefault("img_caps", []).append((bbox, icap))
                    # image_path（MinerU 裁剪 jpg 文件名）——/assets 端点按
                    # fname 反查 bbox 以还原原版比例（2026-09-02 需求2）
                    ipath = ""
                    for sub in blk.get("blocks") or []:
                        if sub.get("type") != "image_body":
                            continue
                        for ln in sub.get("lines") or []:
                            for sp in ln.get("spans") or []:
                                if sp.get("image_path"):
                                    ipath = sp["image_path"]
                                    break
                            if ipath:
                                break
                        if ipath:
                            break
                    if ipath:
                        entry.setdefault("img_paths", []).append(
                            (bbox, ipath))
                elif t == "interline_equation":
                    latex = ""
                    for ln in blk.get("lines") or []:
                        for sp in ln.get("spans") or []:
                            latex += sp.get("content") or ""
                    entry["eqs"].append((bbox, latex))
                elif t == "chart":
                    # 2026-09-02 曲线/图表（图1-8、图A.2/A.5 等）：MinerU 用
                    # chart 类型标记（非 image）——题注在 **blocks 子级**的
                    # lines spans（chart 无顶层 lines，与 text 不同）。修复：
                    # 收集 chart（bbox + 题注），/figure 端点按其截图。
                    cap = ""
                    for sub in blk.get("blocks") or []:
                        for ln in sub.get("lines") or []:
                            for sp in ln.get("spans") or []:
                                cap += sp.get("content") or ""
                    entry["charts"].append((bbox, cap))
                elif t == "text":
                    txt = ""
                    for ln in blk.get("lines") or []:
                        for sp in ln.get("spans") or []:
                            txt += sp.get("content") or ""
                    if txt.strip():
                        entry["texts"].append((bbox, txt))
            any_ok = True
    if not any_ok:
        _cache[key] = (mtime, None)  # type: ignore[arg-type]
        return None
    geo = MiddleGeo(pages, sizes)
    _cache[key] = (mtime, geo)
    return geo
