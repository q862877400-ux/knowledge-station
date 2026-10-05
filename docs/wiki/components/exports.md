# exports（产出物组装与导出）

**位置**：`src/core/exports/`
**一句话**：把库内数据组装成用户能拿走的东西——效力报告、研究报告、引用块、Excel。

## 职责

**产出物那一侧**：效力报告只读聚合（`effect_report.py` 18.9 KB）、研究报告（`research_report.py` 29.6 KB）、结论草稿（`research_draft.py`）、Office 往返编辑（`office_roundtrip.py`）、条款反查（`backlinks.py`）、落盘目录与引用块约定（`report_export.py`）。

接手的是**库内已成形的数据**（条款、材料、效力状态），交付的是 Markdown / Excel / 供用户编辑的临时 docx。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 效力报告聚合 | `effect_report.collect_effect_report()` / `collect_effect_docs()` / `collect_effect_by_color()` | `api/routes_report.py`、`ks_effect_report` 工具 |
| 效力报告 Excel | `effect_report.export_effect_report_xlsx()` | 用户下载 |
| 效力分色常量 | `effect_report.STATUS_COLOR` / `COLOR_ORDER` | `knowledge/folder_store.py`（分类树着色） |
| 研究报告 | `research_report.build_research_report()` / `write_research_report()` | `api/routes_report.py` |
| 结论引用检查 | `research_report.check_conclusion_citations()` / `assemble_evidence_or_raise()` | 报告生成 |
| 结论草稿 | `research_draft.draft_conclusion()` | `api/routes_report.py`（回 `unapproved_draft` 标记） |
| Office 往返编辑会话 | `office_roundtrip.create/poll/commit/cancel_edit_session()` | `api/server.py` |
| 双向溯源「条款 → 谁引用」 | `backlinks.query_backlinks()` | `api/server.py` |
| 落盘目录与命名约定 | `report_export._exports_dir()` / `_safe_name()` | `update/announce.py`、`update/report.py`、`effect_report` |
| 引用纯文本块 | `report_export.build_citation_block()` | `api/server.py` |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| `storage`（`clause_repo` / `material_repo`） | 上游模块 | 取条款与材料 |
| `materials/authority` | 同仓 | 材料承重分组与 `[[m:i]]` 编号（只有这一份） |
| `knowledge/folder_store` | 上游模块 | 文件目录分类树 |
| python-docx / openpyxl | 外部库 | docx 往返解析与 xlsx 写出 |
| 本机 Word / WPS | 外部程序 | 往返编辑（`os.startfile` 拉起） |

## 明确不做什么

- **不出 Word / PPT 交付物**：业主已否决，产出物只出 Markdown（[NOT-DOING](../../NOT-DOING.md) 第 1 条）；整条 Word 导出通路已拆，只剩 docx 往返编辑（编辑后回库，不是交付）。
- **不判定效力状态**：真值是 `doc_meta.legal_status` 经 `knowledge/legal_status.resolve_status` 惰性翻转；本模块只聚合，不改状态。
- **不自己给材料分组**：承重分组、两个轴、`[[m:i]]` 编号归 `materials/authority`。
- **不自动采用结论草稿**：`draft_conclusion` 只返回文本，是否采用由**用户**逐次显式决定。
- **不越界落库**：Office 往返遇到图片 / 样式 / 公式对象 / 文本框一律拒绝并明示用户改用快速小改。

## 关键数据

不新建表：读 `doc_meta`、`clause_revision`、`material*`。导出文件落在 `_exports_dir()` 指定的目录——**该目录与命名规则是全仓单一所有者**，别的模块要落文件也走它。

## 改了它会影响谁

- **`ks_effect_report` 工具与「效力总览」页**：该工具的 `colors` 块是 required 五键，加档位必须同步工具 schema
- **`update` 的两个 xlsx**（公告发现、更新检查结果）：复用 `_exports_dir` / `_safe_name`
- **分类树着色**：`folder_store` 直接 import 本模块的分色常量

## 已知边界（诚实）

- **效力分色自 2026-09-24 起是五档**（新增 🔵 参考资料·仅参考 = 征求意见稿 / 草案等未生效文本）。别处写「四档」的以 `effect_report.py` 为准。
- **`report_export.py` 只剩两件东西**（引用纯文本块 + 落盘目录约定），不是残留，是被多处复用的约定所有者。
- **Office 往返只在本机有 Word / WPS 时可用**（`os.startfile` + 窗口前台化）。
