"""xlsx 导出的共用样式与工具（唯一所有者）。

## 为什么有这个文件（2026-10-23 统一化第一批）

`_xlsx_header_style` 同一段实现原来在**三个文件里逐字存在**：

- `exports/effect_report.py`
- `update/announce.py`
- `update/report.py`

三处都是：`PatternFill("solid", fgColor="DDEBF7")` + 加粗 + 垂直居中，
一个字符都不差。统一化尺子（`scripts/check-repo-uniformity.py` 的指标 ⑤，
跨文件同函数体 α-等价）把它抓成一组 3 处。

## 为什么放在 `exports/` 而不是别处

`update` 本来就 import `exports`（依赖方向已存在，见包级依赖矩阵），
放这里**不引入新的依赖环**。反过来放 `update/` 会让 `exports` 反向依赖 `update`。

## 为什么值得合（不是纯风格）

这类样式一旦分叉，表现是**三个导出文件的表头颜色/粗细不一致** ——
用户看不出来是哪里的问题，只会觉得"这个系统的导出有点乱"。
而且颜色值是**业主定的口径**（`DDEBF7` 浅蓝），改的时候必须只改一处。

## 判据

合并后必须满足：
1. 三个导出函数的输出**逐字节不变**（`tests/test_xlsx_exports.py` 比对）；
2. 尺子 ⑤ 从 13 组降到 12 组；
3. 三处 import 里不再需要 `Alignment` / `PatternFill`（只剩 `Font` 等自用的）。
"""
from __future__ import annotations

from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

#: 表头底色（浅蓝）。**业主定过的口径，改这里改全部三个导出**。
HEADER_FILL_COLOR = "DDEBF7"


def xlsx_header_style(ws: Worksheet, row: int, cols: int) -> None:
    """给第 `row` 行的前 `cols` 列加表头样式：**加粗 + 浅蓝底 + 垂直居中**。

    只在**表头行**加样式，明细行不加 ——
    几万行的明细表逐格设样式会明显拖慢导出
    （`update/report.py` 的原注释：「明细大表仅头行有样式，行内不加——几万行免样式提速」）。

    Args:
        ws: 目标工作表。
        row: 表头所在行号（1 起）。
        cols: 要套样式的列数（从第 1 列开始连续 `cols` 列）。
    """
    fill = PatternFill("solid", fgColor=HEADER_FILL_COLOR)
    for c in range(1, cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(bold=True)
        cell.fill = fill
        cell.alignment = Alignment(vertical="center")
