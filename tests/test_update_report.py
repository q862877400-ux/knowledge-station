"""批次4：更新检查结果 Excel 导出测试（F-05；pipeline/02 §1 report.py）。

覆盖：批次信息 / 四色汇总 / 变更类型细分 / tier 分组明细 / 月度趋势 30 天窗口、
空批次出报告、批次不存在 UPD-2003 零副作用、xlsx 可被 openpyxl 重开。
全部离线临时目录（conftest KS_DATA_DIR 会话隔离），唯一前缀防共享库串扰。

⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：原来的 REP-01/02/03 三条**Word（`.docx`）**
用例（`export_batch_report` + `python-docx` 重开 + 失败路径零副作用）**已随通路删除**
——业主否决 Word/PPT 交付物（`docs/NOT-DOING.md` 第 1 条），
"研究/巡检报告落 `.docx`"正是那条裁决点名的一类。Excel 版不受影响（裁决没碰 xlsx）；
原 REP-04 里与 Word 渲染有关的一半也改由 xlsx 承接（聚合与趋势断言一条没少）。
"""
from __future__ import annotations

import pytest

from src.core.exports.report_export import _exports_dir
from src.core.update import change_repo
from src.core.update.channels.base import UpdateError
from src.core.update.report import (
    CHANGE_COLOR,
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


# ================================================================ 数据聚合
def test_rep_04_tier_grouping_and_trend_window(db):
    """tier 分组取自 bulk_import_batch 锚行；趋势只计近 30 天事件。

    ⚠ 这条原来还顺带断言 Word 版渲染（tier0 标题 / 今日行），Word 通路 2026-09-19 拆掉后
    **只留数据层与 xlsx 层**的判据（tier 分组是两版共用的聚合，值得单独钉住）。
    """
    from src.core.update.report import collect_batch_report_data

    trend_before = monthly_trend()["totals"]
    batch = _mk_batch("rb", [
        ("GB/T RB 0001-2020", "superseded", "superseded", None),
        ("GB/T RB 0002-2020", "new_version", "upcoming", None),
        ("GB/T RB 0003-2020", "no_change", "effective", None),
    ])
    # 锚行标注 tier0（inspector 建批时的镜像语义；此处直插验证分组）
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

    # xlsx 侧承接原 Word 用例里"tier 分组 / 趋势按日分桶含今日行"那两条断言
    from openpyxl import load_workbook

    from src.core.update.report import export_batch_report_xlsx

    out = export_batch_report_xlsx(batch["batch_id"])
    wb = load_workbook(str(out), data_only=True)
    wd = wb["变更明细"]
    assert [wd.cell(row=r, column=7).value for r in range(2, 5)] == ["tier0"] * 3
    wt = wb["月度趋势"]
    today = db.execute("SELECT substr(datetime('now'),1,10)").fetchone()[0]
    assert any(wt.cell(row=r, column=1).value == today
               for r in range(3, wt.max_row + 1)), "趋势按日分桶含今日行（UTC 口径与库内一致）"


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
