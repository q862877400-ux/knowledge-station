"""批次4：更新检查报告 Word 导出测试（F-05；pipeline/02 §1 report.py）。

覆盖：头部批次信息 / 三色汇总表 / tier 分组明细 / 月度趋势 30 天窗口、
空批次出报告、批次不存在 UPD-2003 零副作用、docx 可被 python-docx 重开。
全部离线临时目录（conftest KS_DATA_DIR 会话隔离），唯一前缀防共享库串扰。
"""
from __future__ import annotations

import pytest
from docx import Document

from src.core.exports.report_export import _exports_dir
from src.core.update import change_repo
from src.core.update.channels.base import UpdateError
from src.core.update.report import (
    CHANGE_COLOR,
    collect_batch_report_data,
    export_batch_report,
    monthly_trend,
)


# ---------------------------------------------------------------- 夹具工具
def _mk_batch(prefix: str, specs: list[tuple[str, str, str | None, str | None]]):
    """建批 + 走 change_repo 公共写路径逐事件落库并同步四色计数。

    specs 元组：(standard_no, change_type, current_legal_status, evidence_url)。
    """
    batch = change_repo.create_batch(trigger="manual", total=len(specs))
    for i, (no, ctype, status, url) in enumerate(specs):
        change_repo.append_change({
            "batch_id": batch["batch_id"], "standard_no": no,
            "standard_name": f"标准{prefix}_{i}", "change_type": ctype,
            "current_legal_status": status, "source_channel": "official_gb",
            "evidence_url": url})
        change_repo.update_progress(batch["batch_id"], checked=1,
                                    **{CHANGE_COLOR[ctype]: 1})
    return change_repo.get_batch(batch["batch_id"])


def _tables_text(doc) -> str:
    return "\n".join(c.text for t in doc.tables for r in t.rows for c in r.cells)


def _paras_text(doc) -> str:
    return "\n".join(p.text for p in doc.paragraphs)


# ================================================================ REP-导出
def test_rep_01_export_docx_reopenable_with_key_content(db):
    """/F-05 报告落盘 exports 目录、可被 python-docx 重开且含关键字样与数字。"""
    batch = _mk_batch("ra", [
        ("GB/T RA 0001-2020", "superseded", "superseded",
         "https://evidence.example/ra1"),
        ("GB/T RA 0002-2020", "new_version", "upcoming",
         "https://evidence.example/ra2"),
        ("GB/T RA 0003-2020", "no_change", "effective", None),
        ("GB/T RA 0004-2020", "not_found", None, None),
    ])
    out = export_batch_report(batch["batch_id"])
    assert out.exists() and out.suffix == ".docx"
    assert out.parent == _exports_dir(), "复用 report_export 的 exports 目录约定"
    assert batch["batch_id"] in out.name, "命名约定含安全化的批次号"

    doc = Document(str(out))  # 可被 python-docx 重新打开
    paras = _paras_text(doc)
    tables = _tables_text(doc)
    for key in ("更新检查报告", batch["batch_id"], "手动一键", "月度趋势"):
        assert key in paras, f"缺关键字样: {key}"
    # 明细表：标准号 / 变更类型 / 证据链接
    assert "GB/T RA 0001-2020" in tables and "GB/T RA 0004-2020" in tables
    assert "https://evidence.example/ra1" in tables, "证据链接列"
    assert "被代替" in tables and "有新版" in tables and "查无此号" in tables
    # 三色汇总表数字与批次四色计数一致 + 合计行恒等式
    grid = [[c.text for c in r.cells] for r in doc.tables[0].rows]

    def num(marker: str) -> int:
        return next(int(row[2]) for row in grid if marker in row[0])

    assert (num("在用已废止"), num("有新版"), num("现行有效"),
            num("查无此号")) == (1, 1, 1, 1)
    assert num("合计") == 4


def test_rep_02_empty_batch_still_exports(db):
    """/F-05 空批次（total=0、零事件）也能出报告，三色全 0。"""
    batch = change_repo.create_batch(trigger="scheduled", total=0)
    out = export_batch_report(batch["batch_id"])
    doc = Document(str(out))
    paras = _paras_text(doc)
    assert "更新检查报告" in paras and "定时自动" in paras
    assert "本批次暂无变更明细" in paras
    grid = [[c.text for c in r.cells] for r in doc.tables[0].rows]
    nums = [int(row[2]) for row in grid
            if row[0].startswith(("🔴", "🟡", "🟢", "⚪"))]
    assert nums == [0, 0, 0, 0]


def test_rep_03_missing_batch_upd2003_zero_side_effect(db):
    """/UPD-2003 批次不存在：拒绝且不在 exports 目录产生任何新文件。"""
    before = set(_exports_dir().glob("*.docx"))
    with pytest.raises(UpdateError) as ei:
        export_batch_report("upd_missing_rep03")
    assert ei.value.code == "UPD-2003"
    assert set(_exports_dir().glob("*.docx")) == before, "失败路径零副作用"


def test_rep_04_tier_grouping_and_trend_window(db):
    """tier 分组取自 bulk_import_batch 锚行；趋势只计近 30 天事件。"""
    trend_before = monthly_trend()["totals"]
    batch = _mk_batch("rb", [
        ("GB/T RB 0001-2020", "superseded", "superseded", None),
        ("GB/T RB 0002-2020", "new_version", "upcoming", None),
        ("GB/T RB 0003-2020", "no_change", "effective", None),
    ])
    # 锚行标注 tier0（inspector 建批时的镜像语义；此处直插验证分组渲染）
    db.execute("INSERT INTO bulk_import_batch (batch_id, batch_kind, trigger_type,"
               " status, total, tier) VALUES (?, 'inspect', 'manual', 'done', 3,"
               " 'tier0')", (batch["batch_id"],))
    # 「被代替」事件回拨 40 天 → 落在 30 天趋势窗口之外
    db.execute("UPDATE update_change_event SET detected_at=datetime('now','-40 days')"
               " WHERE standard_no='GB/T RB 0001-2020'")
    db.commit()

    data = collect_batch_report_data(batch["batch_id"])
    assert [g["tier"] for g in data["groups"]] == ["tier0"]
    assert len(data["groups"][0]["events"]) == 3

    totals = monthly_trend()["totals"]
    assert totals["yellow"] - trend_before["yellow"] == 1, "窗口内新版 +1"
    assert totals["green"] - trend_before["green"] == 1, "窗口内现行 +1"
    assert totals["red"] == trend_before["red"], "回拨 40 天的红事件不计入近 30 天"

    out = export_batch_report(batch["batch_id"])
    doc = Document(str(out))
    paras = _paras_text(doc)
    tables = _tables_text(doc)
    assert "tier0" in paras and "高频层" in paras, "tier 分组标题渲染"
    today = db.execute("SELECT substr(datetime('now'),1,10)").fetchone()[0]
    assert today in tables, "趋势按日分桶含今日行（UTC 口径与库内一致）"


# ================================================================ REP-xlsx
def test_rep_05_xlsx_export_reopenable_with_key_content(db):
    """Excel 版落盘 exports、openpyxl 可重开；三 sheet + 汇总/细分/明细数字正确。"""
    from openpyxl import load_workbook

    from src.core.update.report import export_batch_report_xlsx

    batch = _mk_batch("xa", [
        ("GB/T XA 0001-2020", "superseded", "superseded",
         "https://evidence.example/xa1"),
        ("GB/T XA 0002-2020", "new_version", "upcoming", None),
        ("GB/T XA 0003-2020", "no_change", "effective", None),
        ("GB/T XA 0004-2020", "not_found", None, None),
        ("GB/T XA 0005-2020", "withdrawn", "withdrawn", None),
    ])
    out = export_batch_report_xlsx(batch["batch_id"])
    assert out.exists() and out.suffix == ".xlsx"
    assert out.parent == _exports_dir(), "复用 exports 目录约定"
    assert batch["batch_id"] in out.name, "命名含安全化批次号"

    wb = load_workbook(str(out), data_only=True)  # openpyxl 可重开
    assert wb.sheetnames == ["巡检汇总", "变更明细", "月度趋势"]
    ws = wb["巡检汇总"]
    assert ws["A1"].value == "更新检查结果（巡检批次）"
    # 四色统计（固定布局：表头行 9，数据行 10-13 按 red/yellow/green/gray）
    assert (ws.cell(row=10, column=3).value, ws.cell(row=11, column=3).value,
            ws.cell(row=12, column=3).value, ws.cell(row=13, column=3).value) \
        == (2, 1, 1, 1), "red=superseded+withdrawn 合并、黄/绿/灰各 1"
    # 变更类型细分（表头行 19，数据行 20-24）
    detail_counts = [ws.cell(row=row, column=3).value for row in range(20, 25)]
    assert detail_counts == [1, 1, 1, 1, 1], "new_version/superseded/withdrawn/not_found/no_change 各 1"

    wd = wb["变更明细"]
    assert wd.max_row == 1 + 5, "表头 + 5 条事件"
    rows = [[c.value for c in r] for r in wd.iter_rows(min_row=2)]
    nos = [r[0] for r in rows]
    assert "GB/T XA 0001-2020" in nos and "GB/T XA 0005-2020" in nos
    labels = {r[0]: r[2] for r in rows}
    assert labels["GB/T XA 0001-2020"] == "被代替"
    assert labels["GB/T XA 0005-2020"] == "已废止"
    assert any("https://evidence.example/xa1" in (r[4] or "") for r in rows), "证据链接列"
    assert all(r[6] for r in rows), "明细每行带 tier 分层列"

    wt = wb["月度趋势"]
    assert wt["A1"].value and "近 30 天" in str(wt["A1"].value), "趋势标题渲染"


def test_rep_06_xlsx_empty_batch_still_exports(db):
    """空批次（total=0、零事件）也能出 xlsx：汇总全 0、明细仅表头。"""
    from openpyxl import load_workbook

    from src.core.update.report import export_batch_report_xlsx

    batch = change_repo.create_batch(trigger="scheduled", total=0)
    out = export_batch_report_xlsx(batch["batch_id"])
    wb = load_workbook(str(out), data_only=True)
    ws = wb["巡检汇总"]
    four = [ws.cell(row=row, column=3).value for row in range(10, 14)]
    assert four == [0, 0, 0, 0], "空批次四色全 0"
    assert wb["变更明细"].max_row == 1, "明细只有表头行"
    # 头部 meta 行自第 3 行起：批次编号(3)/触发方式(4)/创建(5)/规模(6)
    assert ws.cell(row=4, column=2).value and "定时自动" in str(ws.cell(row=4, column=2).value)


def test_rep_07_xlsx_missing_batch_upd2003_zero_side_effect(db):
    """批次不存在：抛 UPD-2003 且不在 exports 目录产生任何 .xlsx。"""
    from src.core.update.report import export_batch_report_xlsx

    before = set(_exports_dir().glob("*.xlsx"))
    with pytest.raises(UpdateError) as ei:
        export_batch_report_xlsx("upd_missing_rep07")
    assert ei.value.code == "UPD-2003"
    assert set(_exports_dir().glob("*.xlsx")) == before, "失败路径零副作用"
