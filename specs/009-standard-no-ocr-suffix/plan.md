# Implementation Plan: 标准号「(OCR采集)」显示污染清理

**Branch**: `009-standard-no-ocr-suffix` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-standard-no-ocr-suffix/spec.md`

## Summary

把 1,430 篇 LawRefBook 第三方法规的**来源标记**从 `doc_meta.standard_no` 的尾部后缀
搬到 `doc_meta.source` 字段，并同步 `clause_fts` 里的那份副本。

**技术路径**：一次性回填脚本（`scripts/fix-standard-no-ocr-suffix.py`），
照本仓既有先例 `scripts/fix_standard_name_suffix.py` 的形状写
（默认 dry-run / `--apply` 先快照 / 单事务 / 每行 `operation_log` / 写后复验 / 幂等）。

**为什么不是"改派生逻辑"**：后缀**不是代码拼出来的**（实测全仓搜不到拼接点），
它来自 2026-10-07 那次 LawRefBook 导入的**数据本身**（`file_path` 是 `lawrefbook://`）。
⇒ 修派生没地方修，只能回填。

## Technical Context

**Language/Version**: Python 3.12（本仓 `.venv`）

**Primary Dependencies**: `src/core/storage/sqlite_db.py`（`get_db_connection` / `write_transaction`）、
`src/core/storage/backup.py`（`create_snapshot`）

**Storage**: SQLite（生产库 `%APPDATA%\KnowledgeStation\database\knowledge.db`，2.88 GB / 62 表）

**Testing**: pytest（根 `tests/`，`testpaths` 已含 `tools/gov-qa/tests`）

**Target Platform**: Windows（本机）；脚本本身跨平台

**Project Type**: 单仓（引擎 `src/` + 插件 `plugin/`）

**Constraints**:
- 写生产库**必须先快照**（手动快照永不被自动清理）
- `clause_fts` 是 FTS5 **虚拟表**，`UPDATE` 直接写内容列（本仓已有先例：`pypdf_backfill.py`）
- **一次只跑一个门禁**（锁文件）

**Scale/Scope**: 1,430 行 `doc_meta` + 58,536 行 `clause_fts`；脚本单次 < 1 分钟

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 本特性怎么满足 |
|---|---|
| **I 说人话** | 跟业主汇报时说"证据卡片上的标准号不再带『(OCR采集)』"、"这批法规的来路记在来源字段里"；不说表名/字段名 |
| **II 从事实出发** | ⚠ **本特性推翻了原方案 §九 的一个隐含前提**：原方案说"建议在造尺子之前先修它"（当成纯显示问题）。实测发现**后缀是唯一的非官方标记**（这 1,430 篇全是 `quality_grade='A'` / `legal_status='effective'`）⇒ 只删后缀 = 删来路信息。**已改设计**：搬标记而不是删标记 |
| **III 证据优于断言** | 每个数字挂实测命令；SC-008 要求变异自验（塞回一条必须变红） |
| **IV 一个事实一个归属层** | 本特性的完整记录写进 `specs/009-*/`；`docs/PLAN-REAL-QUESTION-RULER.md` §九 就地更正并链过来 |
| **V 假绿判 failed** | 写后复验（同一判据再跑应为 0）；幂等断言（第二次 0 行） |
| **VI 门禁为准** | `-Full` N/N · exit=0 才算完 |
| **VII 不撞车** | 只动 `src/`（不碰 `tools/gov-qa/**`）；写前确认采集进程为 0 |

**结论**：无违规。本特性**加强**了原则 II（发现并纠正了一个隐含前提）。

## Project Structure

### Documentation (this feature)

```text
specs/009-standard-no-ocr-suffix/
├── spec.md              # 已完成
├── plan.md              # 本文件
└── tasks.md             # 下一步
```

### Source Code (repository root)

```text
scripts/
└── fix-standard-no-ocr-suffix.py     # 新增：一次性回填（dry-run 默认）

src/core/text_utils.py                # 新增 strip_ocr_source_suffix()（判据唯一所有者）
                                      # ⚠ 必须与既有 strip_duplicate_suffix 并列，不混用

src/core/storage/clause_repo.py       # 不动（本特性是回填，不改写入路径）

tests/
└── test_standard_no_ocr_suffix.py    # 新增：回归判据（含变异自验）

docs/
└── PLAN-REAL-QUESTION-RULER.md       # §九 就地更正（留痕，不删原话）
```

**Structure Decision**：单仓结构。回填脚本放 `scripts/`（与 `fix_standard_name_suffix.py` 同级，
那是本仓"一次性维护脚本"的既有位置）；判据函数放 `src/core/text_utils.py`
（本仓"标准号形态判据"的唯一所有者，`canon_standard_no` / `store_standard_no` /
`strip_duplicate_suffix` 都在那里）。

## 判据设计（**先定判据，再写实现**）

### 剥离判据：`strip_ocr_source_suffix`

**只剥离尾部**的 `(OCR采集)`，其余一字不动：

```python
_RE_OCR_SUFFIX = re.compile(r"\s*\(OCR采集\)\s*$")

def strip_ocr_source_suffix(s: str | None) -> str:
    """剥掉标准号尾部的「(OCR采集)」来源后缀（**只此一种**）。"""
    return _RE_OCR_SUFFIX.sub("", (s or "")).strip()
```

**⚠ 为什么不能用既有的 `strip_duplicate_suffix`**：那个函数剥的是尾部 `(数字)`
（副本后缀 `(1)`），判据不同。混用会把 `聚丙烯(PP)树脂` 这类**合法括号名**误伤。
本仓规矩：**一个判据一个所有者**，所以新开一个函数，不复用。

### 三条断言（各自有牙）

| # | 断言 | 牙在哪 |
|---|---|---|
| **A1** | `strip_ocr_source_suffix("刑法(OCR采集)") == "刑法"` | 不剥离 ⇒ 红 |
| **A2** | `strip_ocr_source_suffix("聚丙烯(PP)树脂") == "聚丙烯(PP)树脂"` | 判据写宽（剥任意括号）⇒ 红 |
| **A3** | `strip_ocr_source_suffix("GB 5009.12-2023食品安全国家标准") == 原值` | 把"尾部带中文"也剥 ⇒ 红 |

### 变异自验（SC-008）

把回归判据的判据函数**故意换成"剥任意尾部括号"**，回归测试必须变红。
若不红，说明判据没牙 ⇒ 按宪法 V 判 failed。

## 实施顺序

1. **T001**：`src/core/text_utils.py` 加 `strip_ocr_source_suffix` + docstring 写明"为什么不复用 `strip_duplicate_suffix`"
2. **T002**：核实"`lawrefbook` 作 `source` 取值安全"（源码级，不改代码）
3. **T003**：写回归测试（A1/A2/A3）—— **先跑，确认通过**
4. **T004**：写回填脚本（dry-run 默认）
5. **T005**：dry-run 跑一次，读数与 spec 的 1,430 / 58,536 对账
6. **T006**：`--apply` 执行（自动快照）
7. **T007**：写后复验（SC-001/002/003/005/006）
8. **T008**：变异自验（SC-008）
9. **T009**：门禁 `-Full`
10. **T010**：`docs/PLAN-REAL-QUESTION-RULER.md` §九 就地更正 + 小提交 + 快照

## Complexity Tracking

无违规项。

## 风险与回退

| 风险 | 缓解 |
|---|---|
| 剥错（动了合法括号名） | 判据只认 `(OCR采集)` 字面；A2 断言挡住；dry-run 先看样例 |
| 撞号 | 已实测：去后缀后重复 0 个；脚本写前**再测一次**，有撞号就中止 |
| FTS 与 doc_meta 分叉 | FR-004 强制同事务同步；SC-002 + US3 的断言 2 挡 |
| 误改别人的 `source` | 脚本**只**改 `standard_no LIKE '%(OCR采集)%'` 的那 1,430 行；SC-004 逐项对账 |
| 写坏库 | `--apply` 先 `create_snapshot("manual")`（手动快照永不被清理） |
