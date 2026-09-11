"""更新检查报告导出（阶段六·批次4）：F-05《更新检查报告》Word 版。

职责（pipeline/02 §1 report.py；§3 ``POST /api/v1/update/report/{batch_id}``；
FRB F-05「一键导出《更新检查报告》（界面版 + Word 版），含月度趋势」）：
- ``collect_batch_report_data(batch_id)``：聚合 ``update_check_batch`` +
  ``update_change_event``（LEFT JOIN ``bulk_import_batch`` 取 tier），产出
  界面 JSON 与 Word 共用的确定性数据；批次不存在抛 UPD-2003。
- ``monthly_trend(days=30)``：近 N 天全库变更的四色计数（按日分桶）。
- ``export_batch_report(batch_id) -> Path``：**纯 python-docx、无模板依赖**
  （区别于 exports/report_export 的模板机制），生成四段式报告：
  头部批次信息（触发方式/时间/总数）→ 三色汇总表 → tier 分组明细表
  （标准号/变更类型/证据链接）→ 月度趋势小节；空批次同样出报告。
- ``export_batch_report_xlsx(batch_id) -> Path``：同聚合的 Excel 版
  （openpyxl，三 sheet：巡检汇总/变更明细全量/月度趋势），供「导出巡查结果」。
  落盘复用 report_export 的 exports 目录与命名约定。

三色口径与 inspector.judge_result 逐位一致（批次2指令）：
superseded|withdrawn→红；new_version→黄；no_change→绿；not_found→灰。

副作用边界：只读聚合 + 单文件输出——除导出的 docx 外零库写入
（审计仅打点日志，不写 event_log）。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import RGBColor

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.core.exports.report_export import _exports_dir, _safe_name
from src.core.storage.sqlite_db import get_db_connection
from src.core.update.channels.base import (
    UPD_BATCH_NOT_FOUND,
    UpdateError,
    upd_log,
)

# ---------------------------------------------------------------- 口径常量
#: change_type → 三色桶（与 inspector.judge_result 映射逐位一致，批次2指令）
CHANGE_COLOR: dict[str, str] = {
    "superseded": "red", "withdrawn": "red",
    "new_version": "yellow",
    "no_change": "green",
    "not_found": "gray",
}
#: 四色中文标签（F-04 徽章口径）
COLOR_LABELS: dict[str, str] = {
    "red": "🔴 在用已废止", "yellow": "🟡 有新版",
    "green": "🟢 现行有效", "gray": "⚪ 查无此号",
}
COLOR_MEANINGS: dict[str, str] = {
    "red": "在用已废止 / 被代替", "yellow": "有新版（含即将实施）",
    "green": "现行有效", "gray": "官方渠道查无此号",
}
COLOR_RGB: dict[str, RGBColor] = {
    "red": RGBColor(0xB9, 0x1C, 0x1C), "yellow": RGBColor(0xB4, 0x53, 0x09),
    "green": RGBColor(0x15, 0x80, 0x3D), "gray": RGBColor(0x6B, 0x72, 0x80),
}
CHANGE_TYPE_LABELS: dict[str, str] = {
    "new_version": "有新版", "superseded": "被代替", "withdrawn": "已废止",
    "not_found": "查无此号", "no_change": "无变化",
}
TRIGGER_LABELS: dict[str, str] = {"manual": "手动一键", "scheduled": "定时自动"}
_TIER_ORDER: dict[str, int] = {"tier0": 0, "tier1": 1}
_TIER_LABELS: dict[str, str] = {
    "tier0": "tier0 高频层（特别关注 ∪ 未首检）",
    "tier1": "tier1 全库滚动层",
}

_TREND_SQL = """
SELECT substr(detected_at, 1, 10) AS day,
       SUM(CASE WHEN change_type IN ('superseded','withdrawn') THEN 1 ELSE 0 END) AS red,
       SUM(CASE WHEN change_type = 'new_version' THEN 1 ELSE 0 END) AS yellow,
       SUM(CASE WHEN change_type = 'no_change'   THEN 1 ELSE 0 END) AS green,
       SUM(CASE WHEN change_type = 'not_found'   THEN 1 ELSE 0 END) AS gray
FROM update_change_event
WHERE detected_at >= datetime('now', ?)
GROUP BY day ORDER BY day
"""

_EVENTS_SQL = """
SELECT e.*, COALESCE(b.tier, '未分层') AS tier
FROM update_change_event e
LEFT JOIN bulk_import_batch b
       ON b.batch_id = e.batch_id AND b.batch_kind = 'inspect'
WHERE e.batch_id = ?
ORDER BY e.detected_at, e.standard_no, e.change_id
"""

_COLOR_ORDER = ("red", "yellow", "green", "gray")


# ================================================================ 数据聚合
def monthly_trend(days: int = 30) -> dict:
    """近 N 天（默认 30）全库变更四色计数，按日分桶。

    返回 ``{"window_days": N, "days": [{day, red, yellow, green, gray}],
    "totals": {red, yellow, green, gray}}``；窗口内无记录时 days 为空表。
    """
    n = int(days)
    if n < 1:
        raise ValueError(f"趋势窗口必须 ≥1 天: {days}")
    conn = get_db_connection()
    rows = conn.execute(_TREND_SQL, (f"-{n} days",)).fetchall()
    out_days: list[dict] = []
    totals = {c: 0 for c in _COLOR_ORDER}
    for r in rows:
        day = {"day": r["day"], **{c: int(r[c] or 0) for c in _COLOR_ORDER}}
        out_days.append(day)
        for c in _COLOR_ORDER:
            totals[c] += day[c]
    return {"window_days": n, "days": out_days, "totals": totals}


def collect_batch_report_data(batch_id: str) -> dict:
    """聚合单批次报告数据（界面 JSON 与 Word 共用）；批次不存在抛 UPD-2003。"""
    conn = get_db_connection()
    brow = conn.execute("SELECT * FROM update_check_batch WHERE batch_id=?",
                        (batch_id,)).fetchone()
    if brow is None:
        raise UpdateError(f"批次不存在: {batch_id}", code=UPD_BATCH_NOT_FOUND)
    batch = dict(brow)
    events = [dict(r) for r in conn.execute(_EVENTS_SQL, (batch_id,)).fetchall()]
    groups: dict[str, list[dict]] = {}
    for e in events:
        groups.setdefault(e["tier"], []).append(e)
    ordered = sorted(groups, key=lambda t: (_TIER_ORDER.get(t, 9), t))
    return {
        "batch": batch,
        "summary": {c: int(batch.get(f"{c}_count") or 0) for c in _COLOR_ORDER},
        "event_total": len(events),
        "groups": [{"tier": t, "label": _TIER_LABELS.get(t, t),
                    "events": groups[t]} for t in ordered],
        "trend": monthly_trend(),
    }


# ================================================================ Word 导出
def export_batch_report(batch_id: str) -> Path:
    """生成《更新检查报告》docx 到 exports 目录，返回文件路径。

    空批次同样出报告（明细节显示占位说明）；纯 python-docx 新建文档，
    不读任何模板。命名沿用 report_export 约定：``更新检查报告_<安全批次号>_
    <yyyymmdd_hhmmss>.docx``。
    """
    data = collect_batch_report_data(batch_id)
    b = data["batch"]
    doc = Document()

    # —— 头部批次信息 ——
    doc.add_heading("更新检查报告", level=1)
    trig = TRIGGER_LABELS.get(b.get("trigger_type") or "", "-")
    doc.add_paragraph(f"批次编号：{b['batch_id']}")
    doc.add_paragraph(f"触发方式：{trig}｜批次状态：{b.get('status') or '-'}")
    doc.add_paragraph(f"创建：{b.get('created_at') or '-'}｜"
                      f"开始：{b.get('started_at') or '-'}｜"
                      f"完成：{b.get('finished_at') or '-'}")
    doc.add_paragraph(f"巡检总数：{int(b.get('total') or 0)}｜"
                      f"已检：{int(b.get('checked') or 0)}｜"
                      f"变更事件：{data['event_total']} 项")

    # —— 一、三色汇总 ——
    doc.add_heading("一、三色汇总", level=2)
    s = data["summary"]
    rows = [[COLOR_LABELS[c], COLOR_MEANINGS[c], str(s[c])] for c in _COLOR_ORDER]
    rows.append(["合计", "四色恒等式 = 已检数", str(sum(s.values()))])
    tbl = _add_table(doc, ["色别", "含义", "数量"], rows)
    for i, c in enumerate(_COLOR_ORDER):
        for run in tbl.rows[i + 1].cells[0].paragraphs[0].runs:
            run.font.color.rgb = COLOR_RGB[c]

    # —— 二、变更明细（按 tier 分组） ——
    doc.add_heading("二、变更明细（按 tier 分组）", level=2)
    if not data["groups"]:
        doc.add_paragraph("本批次暂无变更明细。")
    for g in data["groups"]:
        doc.add_heading(f"{g['label']}（{len(g['events'])} 项）", level=3)
        rows = []
        for e in g["events"]:
            evidence = e.get("evidence_url") or e.get("archived_pdf_path") or "-"
            ctype = e.get("change_type") or "-"
            rows.append([e.get("standard_no") or "-",
                         e.get("standard_name") or "-",
                         CHANGE_TYPE_LABELS.get(ctype, ctype), evidence])
        _add_table(doc, ["标准号", "标准名称", "变更类型", "证据链接"], rows)

    # —— 三、月度趋势（近 30 天各色计数，跨批全库口径） ——
    doc.add_heading("三、月度趋势（近 30 天各色计数）", level=2)
    tot = data["trend"]["totals"]
    if sum(tot.values()) == 0:
        doc.add_paragraph("近 30 天无变更记录。")
    else:
        doc.add_paragraph(
            f"近 30 天共检出变更 {sum(tot.values())} 项："
            f"红 {tot['red']}／黄 {tot['yellow']}／绿 {tot['green']}／灰 {tot['gray']}。")
        rows = [[d["day"], str(d["red"]), str(d["yellow"]),
                 str(d["green"]), str(d["gray"])] for d in data["trend"]["days"]]
        _add_table(doc, ["日期", "🔴 废止", "🟡 新版", "🟢 现行", "⚪ 查无"], rows)

    doc.add_paragraph("—— 本报告由本地引擎生成（纯本地 python-docx，未外发），"
                      "判定口径与巡检引擎一致，仅供参考。")

    out = (_exports_dir() /
           f"更新检查报告_{_safe_name(batch_id)}_{datetime.now():%Y%m%d_%H%M%S}.docx")
    doc.save(str(out))
    upd_log(batch_id, "report", "INFO", "report_exported",
            path=str(out), events=data["event_total"])
    return out


def _add_table(doc, headers: list[str], rows: list[list[str]]):
    """追加带表头的表格（默认模板缺 Table Grid 样式时静默降级）。"""
    table = doc.add_table(rows=1, cols=len(headers))
    try:
        table.style = "Table Grid"
    except KeyError:
        pass
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = str(h)
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = "" if v is None else str(v)
    return table


# ================================================================ Excel 导出
#: Excel「变更明细」sheet 列头（与 docx 明细口径一致，多 tier 列）
_XLSX_DETAIL_HEADERS = ["标准号", "标准名称", "变更类型", "当前法律状态",
                        "证据链接", "检出时间", "巡检分层"]
#: 事件行证据展示优先级：官方证据 URL → 本地存档 PDF → 占位
_CHANGE_TYPE_ORDER = ("new_version", "superseded", "withdrawn",
                      "not_found", "no_change")


def _xlsx_header_style(ws, row: int, cols: int) -> None:
    """表头行加粗 + 浅底（明细大表仅头行有样式，行内不加——几万行免样式提速）。"""
    fill = PatternFill("solid", fgColor="DDEBF7")
    for c in range(1, cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(bold=True)
        cell.fill = fill
        cell.alignment = Alignment(vertical="center")


def export_batch_report_xlsx(batch_id: str) -> Path:
    """生成《更新检查结果》Excel（.xlsx）到 exports 目录，返回文件路径。

    与 docx 版共用 ``collect_batch_report_data`` 聚合（同批次不存在抛 UPD-2003）。
    三 sheet：巡检汇总（批次头 + 四色统计 + 变更类型细分）→ 变更明细
    （全量逐条，含 tier 分层列，冻结首行 + 自动筛选）→ 月度趋势（近 30 天）。
    空批次同样出文件（明细空表头 + 汇总全 0）。纯本地 openpyxl，零外发。
    """
    data = collect_batch_report_data(batch_id)
    b = data["batch"]
    wb = Workbook()

    # ---- Sheet 1 巡检汇总 ----
    ws = wb.active
    ws.title = "巡检汇总"
    ws.cell(row=1, column=1, value="更新检查结果（巡检批次）").font = Font(size=14, bold=True)
    trig = TRIGGER_LABELS.get(b.get("trigger_type") or "", "-")
    meta_rows = [
        ("批次编号", b.get("batch_id") or "-"),
        ("触发方式", f"{trig}｜状态：{b.get('status') or '-'}"),
        ("创建", f"{b.get('created_at') or '-'}｜开始：{b.get('started_at') or '-'}"
                 f"｜完成：{b.get('finished_at') or '-'}"),
        ("规模", f"巡检总数：{int(b.get('total') or 0)}｜已检：{int(b.get('checked') or 0)}"
                f"｜变更事件：{data['event_total']} 项"),
    ]
    for i, (k, v) in enumerate(meta_rows):
        ws.cell(row=3 + i, column=1, value=k).font = Font(bold=True)
        ws.cell(row=3 + i, column=2, value=v)

    s = data["summary"]
    r0 = 8
    ws.cell(row=r0, column=1, value="一、四色统计").font = Font(bold=True)
    _xlsx_header_style(ws, r0 + 1, 3)
    for c, h in enumerate(["色别", "含义", "数量"], start=1):
        ws.cell(row=r0 + 1, column=c, value=h)
    for i, color in enumerate(_COLOR_ORDER):
        ws.cell(row=r0 + 2 + i, column=1, value=COLOR_LABELS[color])
        ws.cell(row=r0 + 2 + i, column=2, value=COLOR_MEANINGS[color])
        ws.cell(row=r0 + 2 + i, column=3, value=s[color])
    ws.cell(row=r0 + 2 + len(_COLOR_ORDER), column=1, value="合计")
    ws.cell(row=r0 + 2 + len(_COLOR_ORDER), column=2, value="四色恒等式 = 已检数")
    ws.cell(row=r0 + 2 + len(_COLOR_ORDER), column=3,
            value=sum(s[c] for c in _COLOR_ORDER)).font = Font(bold=True)

    # 二、变更类型细分（同一事件按 change_type 五类拆数）
    by_type = {t: 0 for t in _CHANGE_TYPE_ORDER}
    for g in data["groups"]:
        for e in g["events"]:
            ct = e.get("change_type")
            if ct in by_type:
                by_type[ct] += 1
    r1 = r0 + 6 + len(_COLOR_ORDER)
    ws.cell(row=r1, column=1, value="二、变更类型细分").font = Font(bold=True)
    _xlsx_header_style(ws, r1 + 1, 3)
    for c, h in enumerate(["变更类型", "含义", "数量"], start=1):
        ws.cell(row=r1 + 1, column=c, value=h)
    for i, ct in enumerate(_CHANGE_TYPE_ORDER):
        ws.cell(row=r1 + 2 + i, column=1, value=CHANGE_TYPE_LABELS.get(ct, ct))
        ws.cell(row=r1 + 2 + i, column=2,
                value=COLOR_MEANINGS[CHANGE_COLOR[ct]])
        ws.cell(row=r1 + 2 + i, column=3, value=by_type[ct])
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 46

    # ---- Sheet 2 变更明细（全量逐条；平铺 tier 分组，保留顺序） ----
    wd = wb.create_sheet("变更明细")
    wd.append(_XLSX_DETAIL_HEADERS)
    for g in data["groups"]:
        tier = g["tier"]
        for e in g["events"]:
            ctype = e.get("change_type") or "-"
            evidence = (e.get("evidence_url") or e.get("archived_pdf_path")) or ""
            wd.append([
                e.get("standard_no") or "-",
                e.get("standard_name") or "-",
                CHANGE_TYPE_LABELS.get(ctype, ctype),
                e.get("current_legal_status") or "",
                evidence,
                e.get("detected_at") or "",
                tier,
            ])
    if wd.max_row > 1:
        _xlsx_header_style(wd, 1, len(_XLSX_DETAIL_HEADERS))
        wd.freeze_panes = "A2"
        wd.auto_filter.ref = f"A1:{get_column_letter(len(_XLSX_DETAIL_HEADERS))}{wd.max_row}"
    widths = [22, 34, 12, 16, 46, 20, 12]
    for i, w in enumerate(widths, start=1):
        wd.column_dimensions[get_column_letter(i)].width = w

    # ---- Sheet 3 月度趋势（近 30 天，跨批全库口径） ----
    wt = wb.create_sheet("月度趋势")
    wt.cell(row=1, column=1,
            value=f"近 {data['trend']['window_days']} 天变更趋势（跨批次全库口径）"
                  ).font = Font(bold=True)
    tot = data["trend"]["totals"]
    if sum(tot.values()) == 0:
        wt.cell(row=2, column=1, value="近 30 天无变更记录。")
    else:
        _xlsx_header_style(wt, 2, 5)
        for c, h in enumerate(["日期", "🔴 废止", "🟡 新版", "🟢 现行", "⚪ 查无"],
                              start=1):
            wt.cell(row=2, column=c, value=h)
        for i, d in enumerate(data["trend"]["days"]):
            wt.cell(row=3 + i, column=1, value=d["day"])
            for j, color in enumerate(_COLOR_ORDER):
                wt.cell(row=3 + i, column=2 + j, value=d[color])
        wt.column_dimensions["A"].width = 12

    out = (_exports_dir() /
           f"更新检查结果_{_safe_name(batch_id)}_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
    wb.save(str(out))
    upd_log(batch_id, "report", "INFO", "report_xlsx_exported",
            path=str(out), events=data["event_total"])
    return out
