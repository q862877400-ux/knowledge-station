"""效力报告聚合（决策 21 · 用户修订版，2026-09）：按文件目录分类体系组织的
库内效力现状——与查号巡检（inspector，变更事件流）是两条独立流程，本模块是
**库内现行快照**的只读聚合。

设计（verify_rollout 三路择优 0.516 + 用户拍板"不混排，按文件目录分类"）：
- 状态真值 = doc_meta.legal_status 经 ``resolve_status`` 惰性翻转（与决策 22
  "只引现行版"同口径；绝不直读 raw——真机回归 F1：categories 叶节点未翻转的
  教训，本模块自行 resolve，不消费 categories 输出）。
- 效力分色（2026-09-24 起**五档**，此前四档）：effective→green（现行有效，可引用）/
  upcoming→yellow（即将实施，当前不可引用）/ superseded|withdrawn→red（在用已废止·被代替）/
  reference→**自己一档**（🔵 参考资料·仅参考：征求意见稿/草案等未生效文本，可查不可作依据）/
  NULL→gray（**状态未知/未登记**——与巡检"官方查无此号"语义不同，UI/Excel
  文案必须区分，不得照抄巡检口径）。
- 分类 = ``classify_document`` 两棵树（std：L2 CCS 大类→L3 区间→L4 类目；
  law：L2 效力等级→L3 法律部门→L4 领域）——报告主体与文件目录同构，永不混排。
- 两级接口（payload 量化定案：全量明细万级 ≈2.5-6MB 超红线被否）：骨架+统计
  秒回（30-300KB），节点明细按需（limit 封顶 1000）。
- 时间窗四档：all / upcoming90 / recent90 / retired90（分桶前过滤；任意日期
  范围是导出 Excel 的活，UI 不做——YAGNI）。
- 纯聚合红线：单 SELECT doc_meta + 内存分组，零 N+1、零 DDL、零 write_queue、
  零 LLM；空库同样出报告/出 Excel（镜像"空批次同样出报告"先例）。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.core.knowledge.doc_catalog import classify_document
from src.core.knowledge.legal_status import resolve_status
from src.core.storage.sqlite_db import get_db_connection
from src.core.exports.report_export import _exports_dir, _safe_name

# ---------------------------------------------------------------- 口径常量
#: resolved status → 效力分色（色系对齐 report.py 巡检报告；gray 文案区分见模块头）
#: ⚠ 2026-09-24 加成**五档**：`reference` = 征求意见稿/草案等"**仅参考**"的入库件
#:   （业主：征求意见稿也要入库，"在有效性里作为单独的一个类别，当成仅做参考的有效性来用"）。
#:   它**绝不能**并进 `gray`——gray 的含义是"库内未登记效力状态，建议补全元数据"，
#:   而 `reference` 是**登记得明明白白**的一种状态（就是"未生效、不得作为依据"），
#:   并进去等于对业主说"这个要补元数据"，是假话。
STATUS_COLOR: dict[str | None, str] = {
    "effective": "green",
    "upcoming": "yellow",
    "superseded": "red",
    "withdrawn": "red",
    "reference": "reference",
    None: "gray",
}
#: 展示/遍历顺序。`reference` **追加在末尾**：前四色的序号（报告、Excel、per_color 请求序、
#: 面板四色灯）一字不变，纯加一档，不动既有约定。
COLOR_ORDER = ("red", "yellow", "green", "gray", "reference")
COLOR_LABELS: dict[str, str] = {
    "red": "🔴 在用已废止/被代替",
    "yellow": "🟡 即将实施",
    "green": "🟢 现行有效",
    "gray": "⚪ 状态未知/未登记",
    "reference": "🔵 参考资料（仅参考）",
}
COLOR_MEANINGS: dict[str, str] = {
    "red": "已被替代或废止（当前引用违规）",
    "yellow": "已发布未实施（到点自动翻现行）",
    "green": "现行有效（可引用）",
    "gray": "库内未登记效力状态，建议补全元数据",
    "reference": "征求意见稿/草案等未生效文本：可检索、可查阅，但不得作为现行依据",
}
#: E2 明细行的排序权重（报告第一职责是把问题顶上去）。
#: `reference` 排在 `gray` 之后、`green` 之前：它比"现行"更该被注意到（不能当依据），
#: 但不像 `gray` 那样是"缺元数据"要人去补。
_COLOR_RANK = {"red": 0, "yellow": 1, "gray": 2, "reference": 3, "green": 4}

_WINDOWS = ("all", "upcoming90", "recent90", "retired90")
#: E2 瘦身行（9 字段——全量行 15 字段含 domain_tags 原串，万级超 payload 红线）
_DOC_FIELDS = ("doc_id", "standard_no", "standard_name", "effective_from",
               "published_at", "superseded_by", "withdrawn_date")

_DATE_STRICT_LEN = 10


def _empty_colors() -> dict[str, int]:
    return {c: 0 for c in COLOR_ORDER}


def _shift_days(today: str, days: int) -> str:
    return (datetime.strptime(today, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")


def _in_range(value: str | None, lo: str, hi: str) -> bool:
    """严格 YYYY-MM-DD 才参与窗口（非法/缺省 → False，诚实不猜）。"""
    s = (value or "").strip()
    if len(s) != _DATE_STRICT_LEN:
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return False
    return lo <= s <= hi


def _window_pred(window: str):
    """窗口谓词工厂（分桶前作用于文档集）。非法 window → ValueError→422。"""
    if window not in _WINDOWS:
        raise ValueError("invalid_window")
    if window == "all":
        return lambda d: True
    today = datetime.now().strftime("%Y-%m-%d")
    if window == "upcoming90":
        lo, hi = today, _shift_days(today, 90)
        return lambda d: (d["status"] == "upcoming"
                          and _in_range(d.get("effective_from"), lo, hi))
    if window == "recent90":
        lo, hi = _shift_days(today, -90), today
        return lambda d: (d["status"] == "effective"
                          and _in_range(d.get("effective_from"), lo, hi))
    # retired90：superseded 无"被代替日期"字段（superseded_by 只存替代号），
    # 不入此窗——诚实限制，全量 Excel 仍可见。
    lo, hi = _shift_days(today, -90), today
    return lambda d: (d["status"] == "withdrawn"
                      and _in_range(d.get("withdrawn_date"), lo, hi))


def _normalize_colors(color) -> set[str] | None:
    """color CSV/list → 子集聚合；None/空 = 全部。非法 → ValueError→422。"""
    if color is None or color == "":
        return None
    if isinstance(color, str):
        parts = [c.strip() for c in color.split(",") if c.strip()]
    elif isinstance(color, (list, tuple)):
        parts = [str(c).strip() for c in color if str(c).strip()]
    else:
        raise ValueError("invalid_color")
    if not parts:
        return None
    bad = [c for c in parts if c not in COLOR_ORDER]
    if bad:
        raise ValueError("invalid_color")
    return set(parts)


# ---------------------------------------------------------------- 单次聚合（三端点共用）
def _load_docs() -> list[dict]:
    """单 SELECT 全量可见文档 → resolve + classify（内存纯函数，零 N+1）。"""
    rows = get_db_connection().execute(
        "SELECT doc_id, standard_no, standard_name, legal_status, legal_hierarchy,"
        " effective_from, published_at, ccs_code, ccs_name, ics,"
        " superseded_by, withdrawn_date, quality_grade, doc_type, domain_tags"
        " FROM doc_meta WHERE catalog_hidden = 0 ORDER BY standard_no").fetchall()
    out: list[dict] = []
    for r in rows:
        d = dict(r)
        d["status"] = resolve_status(d.get("legal_status"), d.get("effective_from"))
        d["color"] = STATUS_COLOR.get(d["status"], "gray")
        try:
            tags = json.loads(d.get("domain_tags") or "[]")
        except (TypeError, ValueError):
            tags = []
        d["domain_tags"] = tags if isinstance(tags, list) else []
        d["_cls"] = classify_document(d)
        out.append(d)
    return out


def _collect(window: str, colors: set[str] | None):
    """统一聚合：窗口+色过滤 → (docs, colors_total)。一次遍历产出骨架/明细/导出。"""
    pred = _window_pred(window)
    docs = []
    for d in _load_docs():
        if not pred(d):
            continue
        if colors is not None and d["color"] not in colors:
            continue
        docs.append(d)
    return docs


def _colors_of(docs: list[dict]) -> dict[str, int]:
    out = _empty_colors()
    for d in docs:
        out[d["color"]] += 1
    return out


def _doc_slim(d: dict) -> dict:
    """E2 瘦身行（9 字段）。"""
    out = {"status": d["status"], "color": d["color"]}
    for f in _DOC_FIELDS:
        out[f] = d.get(f)
    return out


# ---------------------------------------------------------------- E1 骨架+统计
def collect_effect_report(window: str = "all", color=None) -> dict:
    """骨架 + 效力分色统计（tree 到 L4 计数，无文档行——payload 红线见模块头）。"""
    colors_set = _normalize_colors(color)
    docs = _collect(window, colors_set)
    colors_total = _colors_of(docs)

    def node(colors: dict[str, int], **kw) -> dict:
        return {"colors": colors, **kw}

    # 两棵树统一四层骨架：top → L2 → L3 → L4（计数，不带文档行）
    tree_map: dict[str, dict] = {}
    for d in docs:
        cl = d["_cls"]
        t = tree_map.setdefault(cl["top"], node(_empty_colors(), name=cl["top_name"],
                                                order=cl["order"], items={}))
        t["colors"][d["color"]] += 1
        l2 = t["items"].setdefault(cl["level2"], node(_empty_colors(), items={}))
        l2["colors"][d["color"]] += 1
        l3 = l2["items"].setdefault(cl["level3"], node(_empty_colors(), items={}))
        l3["colors"][d["color"]] += 1
        l4 = l3["items"].setdefault(cl["level4"], node(_empty_colors(), count=0))
        l4["colors"][d["color"]] += 1
        l4["count"] += 1

    def to_list(m: dict) -> list:
        """递归转列表：有 items 的中间层继续下钻，带 count 的 L4 叶子收口。"""
        out = []
        for name, v in sorted(m.items()):
            if "items" in v:
                out.append(node(v["colors"], name=name, items=to_list(v["items"])))
            else:
                out.append(node(v["colors"], name=name, count=v["count"]))
        return out

    tree = []
    for top_key in sorted(tree_map, key=lambda k: tree_map[k]["order"]):
        t = tree_map[top_key]
        tree.append(node(t["colors"], top=top_key, name=t["name"],
                         items=to_list(t["items"])))

    def colors_with_total(ds: list[dict]) -> dict:
        c = _colors_of(ds)
        return {"total": sum(c.values()), "colors": c}

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "window": window,
        "colors": colors_total,
        "total": sum(colors_total.values()),
        "std": colors_with_total([d for d in docs if d["_cls"]["top"] == "std"]),
        "law": colors_with_total([d for d in docs if d["_cls"]["top"] == "law"]),
        "tree": tree,
    }


# ---------------------------------------------------------------- E2 节点明细
def collect_effect_docs(top: str, l2: str, l3: str | None = None,
                        l4: str | None = None, window: str = "all", color=None,
                        limit: int = 1000, offset: int = 0) -> dict:
    """节点明细（瘦身行）：red→yellow→gray→**reference**→green → 标准号升序——问题顶上去。"""
    if top not in ("std", "law"):
        raise ValueError("invalid_top")
    if not (l2 or "").strip():
        raise ValueError("invalid_l2")
    # verifier F12：显式判 None，避免 limit=0 被兜成 1000
    n = max(1, min(int(limit) if limit is not None else 1000, 2000))
    off = max(0, int(offset or 0))
    colors_set = _normalize_colors(color)
    docs = _collect(window, colors_set)
    sel = []
    for d in docs:
        cl = d["_cls"]
        if cl["top"] != top or cl["level2"] != l2:
            continue
        if l3 is not None and cl["level3"] != l3:
            continue
        if l4 is not None and cl["level4"] != l4:
            continue
        sel.append(d)
    sel.sort(key=lambda d: (_COLOR_RANK.get(d["color"], 9),
                            (d.get("standard_no") or "")))
    return {
        "colors": _colors_of(sel),
        "count": len(sel),
        "offset": off,
        "docs": [_doc_slim(d) for d in sel[off:off + n]],
    }


# ---------------------------------------------------------------- E4 按色 top-N（模型工具用）
def collect_effect_by_color(color: str, window: str = "all", limit: int = 20,
                            per_color: bool = False) -> dict:
    """全库按色取 top-N 瘦身行（`ks_effect_report` 模型工具的红/黄清单数据源）。

    E2 需 top+l2 才能查（防两树 L2 同名），而模型工具要的是"全库红色清单"，
    故单列此端点：复用同一聚合与排序（色内按标准号），limit ≤100 防滥用。

    ``per_color=True``（verifier F4，2026-09-08）：多色请求时**每色各取 n 条**
    而非全局 top-n——否则红色条目多时黄色清单会被整段挤空，且 host 需发
    2 次请求。docs 顺序 = COLOR_ORDER 请求序。
    """
    colors_set = _normalize_colors(color)
    if colors_set is None:
        raise ValueError("invalid_color")
    # verifier F12：`limit or 20` 会把 0 兜成 20（与 max(1,…) 意图矛盾）→ 显式判 None
    n = max(1, min(int(limit) if limit is not None else 20, 100))
    docs = _collect(window, colors_set)
    docs.sort(key=lambda d: (_COLOR_RANK.get(d["color"], 9), d.get("standard_no") or ""))
    if per_color and len(colors_set) > 1:
        picked: list[dict] = []
        for c in COLOR_ORDER:
            if c in colors_set:
                picked.extend([d for d in docs if d["color"] == c][:n])
        return {"colors": _colors_of(docs), "count": len(docs), "per_color": True,
                "docs": [_doc_slim(d) for d in picked]}
    return {"colors": _colors_of(docs), "count": len(docs),
            "docs": [_doc_slim(d) for d in docs[:n]]}


# ---------------------------------------------------------------- E3 Excel 导出
_XLSX_HEADERS = ["文献类型", "大类/效力等级", "区间/法律部门", "类目/领域",
                 "标准号", "名称", "效力状态", "效力色", "实施日期", "发布日期",
                 "被代替为", "废止日期", "doc_id"]
_STATUS_CN = {"effective": "现行有效", "upcoming": "即将实施",
              "superseded": "被代替", "withdrawn": "已废止",
              "reference": "参考资料（仅参考）", None: "状态未知"}
_COLOR_CN = {"red": "🔴 红", "yellow": "🟡 黄", "green": "🟢 绿", "gray": "⚪ 灰",
             "reference": "🔵 蓝"}


def _xlsx_header_style(ws, row: int, cols: int) -> None:
    fill = PatternFill("solid", fgColor="DDEBF7")
    for c in range(1, cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(bold=True)
        cell.fill = fill
        cell.alignment = Alignment(vertical="center")


def export_effect_report_xlsx(window: str = "all", color=None) -> Path:
    """《效力报告》Excel（两 sheet：总览/分类明细全量）到 exports 目录。
    空库同样出文件（明细仅表头 + 汇总全 0）；全程零库写入。"""
    colors_set = _normalize_colors(color)
    docs = _collect(window, colors_set)
    colors_total = _colors_of(docs)
    wb = Workbook()

    # ---- Sheet1 效力报告总览 ----
    ws = wb.active
    ws.title = "效力报告总览"
    ws.cell(row=1, column=1, value="效力报告（按文件目录分类体系）").font = Font(size=14, bold=True)
    meta_rows = [
        ("生成时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("时间窗", window),
        ("库内文档", f"{sum(colors_total.values())} 部（标准 {sum(1 for d in docs if d['_cls']['top'] == 'std')}"
                     f" · 法规 {sum(1 for d in docs if d['_cls']['top'] == 'law')}）"),
    ]
    for i, (k, v) in enumerate(meta_rows):
        ws.cell(row=3 + i, column=1, value=k).font = Font(bold=True)
        ws.cell(row=3 + i, column=2, value=v)
    r0 = 7
    ws.cell(row=r0, column=1, value="效力分色统计").font = Font(bold=True)
    _xlsx_header_style(ws, r0 + 1, 3)
    for c, h in enumerate(["色别", "含义", "数量"], start=1):
        ws.cell(row=r0 + 1, column=c, value=h)
    for i, color_key in enumerate(COLOR_ORDER):
        ws.cell(row=r0 + 2 + i, column=1, value=COLOR_LABELS[color_key])
        ws.cell(row=r0 + 2 + i, column=2, value=COLOR_MEANINGS[color_key])
        ws.cell(row=r0 + 2 + i, column=3, value=colors_total[color_key])
    ws.cell(row=r0 + 2 + len(COLOR_ORDER), column=1, value="合计").font = Font(bold=True)
    ws.cell(row=r0 + 2 + len(COLOR_ORDER), column=2, value="各色合计 = 库内可见文档总数")
    ws.cell(row=r0 + 2 + len(COLOR_ORDER), column=3,
            value=sum(colors_total.values())).font = Font(bold=True)
    ws.cell(row=r0 + 4 + len(COLOR_ORDER), column=1,
            value="口径注脚：状态以读取时惰性翻转（resolve_status）为准；"
                  "⚪=库内未登记效力状态（与巡检「官方查无此号」语义不同）；"
                  "🔵=征求意见稿/草案等未生效文本（仅参考，不得作为现行依据）。")
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 44

    # ---- Sheet2 分类明细（全量平铺，13 列，冻结+筛选；大表仅头行样式） ----
    wd = wb.create_sheet("分类明细")
    wd.append(_XLSX_HEADERS)
    for d in docs:
        cl = d["_cls"]
        wd.append([
            "标准" if cl["top"] == "std" else "法规",
            cl["level2"], cl["level3"], cl["level4"],
            d.get("standard_no"), d.get("standard_name"),
            _STATUS_CN.get(d["status"], d["status"] or "状态未知"),
            _COLOR_CN.get(d["color"], d["color"]),
            d.get("effective_from"), d.get("published_at"),
            d.get("superseded_by"), d.get("withdrawn_date"), d.get("doc_id"),
        ])
    if wd.max_row > 1:
        _xlsx_header_style(wd, 1, len(_XLSX_HEADERS))
        wd.freeze_panes = "A2"
        wd.auto_filter.ref = f"A1:{get_column_letter(len(_XLSX_HEADERS))}{wd.max_row}"
    widths = [8, 26, 22, 22, 22, 40, 10, 8, 12, 12, 20, 12, 30]
    for i, w in enumerate(widths, start=1):
        wd.column_dimensions[get_column_letter(i)].width = w

    out = (_exports_dir() /
           f"效力报告_{_safe_name(window)}_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
    wb.save(str(out))
    return out
