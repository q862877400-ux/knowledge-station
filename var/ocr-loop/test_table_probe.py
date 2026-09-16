# -*- coding: utf-8 -*-
"""表格内容提取与判据的回归测试（2026-09-15 立）。

**为什么要有它**：用户指出"零命中是仪器口径、不是质量结论"——实测确认
判据原先只读 `content_text`，而表格在 `content_markdown`（全流程出现 0 次），
那份语料里 **19.9% 的字符量（表格）从未被任何判据检查**。补齐覆盖面后，
表格判据一连产生 **4 类误报/假象**，逐条修掉的过程必须**可回归**——否则
下一次改动又会把噪声带回来。

本测试覆盖（每条都对应一次真实踩坑）：
  1. `<eq>LaTeX</eq>` 必须转成可读文本（否则表格里出现 `\\mathrm { G a }` 假象）；
  2. `colspan` 必须算进"有效行宽"（否则合法的合并单元格被当成错并）；
  3. 跨列单元格的文本/图片提取正确；
  4. 纯点线占位格不判为目录行（`dot-leader` 的表格守卫）；
  5. `1 400 mm`（合法千分位）不判为 split-value、列名相邻不判为 unit-midspace；
  6. 真形态仍必须命中（反向对照）。

跑法：`& .\.venv\\Scripts\\python.exe -X utf8 var\\ocr-loop\\test_table_probe.py`
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import audit_text as A          # noqa: E402
import table_probe as TP        # noqa: E402

FAIL: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'OK ' if ok else 'FAIL'} {name}: {got!r}"
          f"{'' if ok else f'（期望 {want!r}）'}")
    if not ok:
        FAIL.append(name)


def _pat(cls: str):
    for k, v in A.CHECKS:
        if k == cls:
            return v
    raise KeyError(cls)


print("=== 1) <eq>LaTeX</eq> 必须转换（否则是提取器假象，不是入库缺陷）===")
_t = TP.parse_table('<table><tr><td><eq>\\mathrm { G a }</eq></td>'
                    '<td>普通文本</td></tr></table>')
check("LaTeX 已转可读", _t["rows"][0][0]["text"], "G a")
check("普通文本不受影响", _t["rows"][0][1]["text"], "普通文本")
check("不再残留 LaTeX 命令",
      bool(re.search(r"\\[a-zA-Z]{2,}", _t["rows"][0][0]["text"])), False)

print("\n=== 2) colspan 必须算进有效行宽（合并单元格是国标常态：47.1% 的表有 colspan）===")
_t = TP.parse_table('<table><tr><td colspan="2">标题</td><td>说明</td></tr>'
                    '<tr><td>a</td><td>b</td><td>c</td></tr></table>')
check("行宽按 Σspan 计", [sum(c["span"] for c in r) for r in _t["rows"]], [3, 3])
check("列数取众数行宽", _t["n_cols"], 3)
check("合法跨列不报 col-count（判据已删）",
      [d["kind"] for d in TP.table_defects(_t and '<table><tr><td colspan="2">t</td>'
                                                       '<td>x</td></tr></table>')], [])

print("\n=== 3) 跨列单元格的文本与图片提取 ===")
_t = TP.parse_table('<table><tr><td rowspan="2">序号</td><td>'
                    '<img src="a/abc.jpg"/></td><td colspan="2">含义A</td></tr></table>')
row = _t["rows"][0]
check("首格文本", row[0]["text"], "序号")
check("图片文件名提取", row[1]["images"], ["abc.jpg"])
check("跨列格文本", row[2]["text"], "含义A")
check("跨列格 span", row[2]["span"], 2)

print("\n=== 4) 表格里的纯点线占位格不判为目录行（dot-leader 的表格守卫口径）===")
# **注意两个同名的东西**（实测踩过）：
#   · `audit_text.dot-leader`      = 点线残留（`…{2,}\s*[（(]`/`…{3,}`/`\.{6,}`/`。{4,}`）
#   · `classify._RE_TOC_LINE`      = **目录行**（点线+页码），`table-text::dot-leader`
#     走的是**后者**（`evolve._evidence_patterns` 直引 `C._RE_TOC_LINE`）。
# evolve 里的守卫：命中片段必须含 ≥2 连续汉字或字母，才算真目录行。
import classify as C  # noqa: E402

_PLACEHOLDER = "名称 代码\n...... ......\n××市 ××××0 0 0 0"
_RE_SUBST = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{2,}")
check("占位格不判为目录行（判据本身不命中）",
      bool(C._RE_TOC_LINE.search(_PLACEHOLDER)), False)
check("真目录行判据命中", bool(C._RE_TOC_LINE.search("9.1 包装……13")), True)
check("占位格片段无实质内容 → 守卫判否",
      any(_RE_SUBST.search(m.group())
          for m in C._RE_TOC_LINE.finditer(_PLACEHOLDER)), False)
check("真目录行片段有实质内容 → 守卫判是",
      any(_RE_SUBST.search(m.group())
          for m in C._RE_TOC_LINE.finditer("9.1 包装……13")), True)

print("\n=== 5) 表格相邻列/千分位造成的误报必须不报 ===")
check("1 400 mm 是合法千分位",
      bool(_pat("split-value").search("1 400 mm")), False)
check("列名行 n c m M 不报 unit-midspace",
      bool(_pat("unit-midspace").search("n c m M")), False)
check("列名行 D E H K N Q R 不报 unit-midspace",
      bool(_pat("unit-midspace").search("D E H K N Q R")), False)

print("\n=== 6) 反向对照：真形态仍必须命中 ===")
check("真：kg 被拉开（≥2 空格）", bool(_pat("unit-midspace").search("k  g")), True)
check("真：min 被拉开", bool(_pat("unit-midspace").search("m  i  n")), True)
check("真：数值被拉开", bool(_pat("split-value").search("1  00 g")), True)

print("\n=== 7) 两树表格对照必须**文档级**（逐页判是错的，实测偏高一个量级）===")
# 现场教训（2026-09-16）：逐页 `max(0, pre−para)` 求和 = 26.6%、逐页"para=0 且
# preproc>0" = 476k 字符，两者都**把页序差异/重复副本当成丢失**。只有文档级总量
# 能回答"少读了多少"。用合成数据钉住"按文档求和"这一语义。
def _tbl(html: str) -> dict:
    """合成一个 table 块（含 table_body span，与 MinerU 产物同形）。"""
    return {"type": "table",
            "blocks": [{"type": "table_body",
                        "lines": [{"spans": [{"type": "table", "html": html}]}]}]}


def _page(para: list, preproc: list) -> dict:
    return {"para_blocks": para, "preproc_blocks": preproc}


# 同页只 1 个单元格：para 有 3 字、preproc 有 3 字 → 文档级差值 0
_mid_same = {"pdf_info": [_page([_tbl("<table><tr><td>abc</td></tr></table>")],
                               [_tbl("<table><tr><td>abc</td></tr></table>")])]}
check("两侧同内容 → para", TP.table_two_tree_chars(_mid_same)[0], 3)
check("两侧同内容 → preproc", TP.table_two_tree_chars(_mid_same)[1], 3)
check("两侧同内容 → 少读 0",
      TP.table_missing(*TP.table_two_tree_chars(_mid_same))["missing"], 0)
# **页序错位**：表在 preproc 的 p0、在 para 的 p1 → 逐页口径会判"丢 3 字"，
# 文档级口径必须判 **0**（同一张表只是挂在别页）。这是本组的核心断言。
_mid_shift = {"pdf_info": [
    _page([_tbl("<table><tr><td>abc</td></tr></table>")], []),
    _page([], [_tbl("<table><tr><td>abc</td></tr></table>")])]}
check("页序错位时文档级仍判不丢",
      TP.table_missing(*TP.table_two_tree_chars(_mid_shift))["missing"], 0)
# 真的少读：preproc 有 6 字、para 只有 3 字 → 少读 3
# 真的少读：preproc 侧 10×600 字、para 侧 10×90 字 → 少读 5,100
# （**数据必须过 `min_pre=500` 门槛**，否则按设计返回 unknown 而非比值——
#  这正是上面那条"preproc 太小 → unknown"钉住的语义）
_big = lambda n: "<table><tr><td>" + "字" * n + "</td></tr></table>"   # noqa: E731
_mid_loss = {"pdf_info": [_page([_tbl(_big(90)) for _ in range(10)],
                               [_tbl(_big(600)) for _ in range(10)])]}
check("真少读：10×600 − 10×90 = 5,100",
      TP.table_missing(*TP.table_two_tree_chars(_mid_loss))["missing"], 5100)
# 小样本（preproc < 500）→ unknown，比值不可用（**不是"无缺失"**）
check("preproc 太小 → unknown",
      TP.table_missing(3, 6)["unknown"], True)
check("preproc 够大 → 比值可用",
      TP.table_missing(0, 1000)["unknown"], False)
check("比值 = missing/pre",
      TP.table_missing(800, 1000)["ratio"], 0.2)

print("\n=== 8) `table-body-missing` 已删除，且**不许悄悄回来**（两个版本都被实测推翻）===")
# 现场教训（2026-09-16，加了两小时就被证据推翻）：
#   ① 按"条款页范围内有表、该条款 md 为空"判 → **3/3 全误报**（GB 30871-2022 报 30 处）
#      ——按页范围判测的是**表格绑定差异**，不是丢失；
#   ② 改文档级 `table_len < max(200, 0.2×preproc)` → 全量重跑 **215 部命中（8.5%）**，
#      实地抽样 20 部**全部 `preproc == para`、少读 0.0%**；根因是 `0.2×preproc`
#      对 <200 字符的表**恒成立**；反向核对真少读 >5% 的文档**一部未命中**；
#   ③ 代价：它 31 部假命中触发"达线类→停止推进"，把推进链停在第 6 批收批处。
# 结论：零真阳性 = 无判别信号 → 删除（同 `col-count-mismatch` / `empty-cell-run`）。
import evolve as E  # noqa: E402

_src = (HERE / "evolve.py").read_text(encoding="utf-8")
check("判据已从代码中移除（只剩说明注释）",
      'hits["table-body-missing"] += 1' in _src, False)
check("固定下限常量已移除", hasattr(E, "_TABLE_BODY_MIN"), False)
# 语义护栏：这类判据必须用**相对**口径，固定下限对"表格本来就小"的文档恒真。
# 用合成数字钉住这个陷阱本身，避免下一个接手者重犯。
_trap = lambda para, pre: para < max(200, 0.2 * pre)                     # noqa: E731
check("陷阱：小表且未丢（para==pre==32）会被固定下限误判",
      _trap(32, 32), True)
check("相对口径才是判别信号：真丢一半才判",
      (32 < 0.5 * 32), False)
check("相对口径：真丢一半（10 vs 32）才判",
      (10 < 0.5 * 32), True)

print()
if FAIL:
    print(f"{len(FAIL)} 项失败：{FAIL}")
    sys.exit(1)
print("全部通过")
