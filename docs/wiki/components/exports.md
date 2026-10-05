# exports（交付物导出）

**位置**：`src/core/exports/`
**一句话**：把结论变成能交出去的文档——报告、草稿、可编辑的 Office。

## 职责

**交付形态层**：调研报告导出（`research_report.py` 29.6 KB）、效力报告聚合（`effect_report.py` 18.9 KB，按文件目录分类体系组织）、结论草稿（`research_draft.py`）、Office 往返编辑会话（`office_roundtrip.py` 14 KB）。

**它不负责**：不生成结论（`llm`）、不核验（`verification`）、不决定能不能外发（`compliance` + 审计）。

## 对外提供什么

| 调研报告导出 | `research_report.py` | 界面交付入口 |
| 效力报告聚合 | `effect_report.py` | 界面 |
| 结论草稿 | `research_draft.py` | 界面 |
| Office 往返编辑（打开→改→提交） | `office_roundtrip.py` | 界面 |

## 依赖什么

| `storage` | 上游模块 | 取数据 |
| Office / COM | 外部（可选） | Office 往返 |

## 明确不做什么

- **MUST NOT 让草稿冒充已批准结论**：`research_draft.py` 产出的是**草稿**，基于**已批准材料**起草，**未经用户批准**——这个状态必须一直可见。
- **不做** Word/PPT 的**通用排版引擎**：本仓已否决「产出 Word/PPT」作为产品目标（`NOT-DOING` #1）；这里做的是**已在范围内的**报告导出与往返编辑。
- **不核验内容**：导出不管内容对不对。

## 已知边界（诚实）

- **Office 往返依赖本机 Word（COM）**；无 Word 时该路径不可用。
- ⚠ **「附件区/草稿/批准」三态是纪律**：导出件必须带对状态，不许把草稿当成品发出去。
