# Implementation Plan: 项目整理与接手文档体系

**Branch**: `001-project-consolidation` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-project-consolidation/spec.md`

## Summary

把 KnowledgeStation 仓库从"文档是代码的两倍、113 份文档里 37 份只被引用一次、13 份零引用、
全仓无总索引"的状态，整理成：**名字统一 → 结构归位 → 一张大 map + 每子系统契约**。

技术路径极简：**只用 git + 文件系统 + 仓内 markdown**，不引入任何新工具、不新增依赖。
分类与改名由脚本机械执行（可重跑、可复核），索引由脚本生成（已建 `scripts/docs/gen-doc-index.py`）。
所有"删除"先移动到归档区或回收区，**保持可恢复路径**。

## Technical Context

**Language/Version**: 不新增语言。改名会触及 Python 3.12 与 Node（插件）里的**路径字符串字面量**。

**Primary Dependencies**: `git`（唯一的"撤销"手段）、PowerShell 7（既有门禁脚本）、
Python 3.12（既有 `.venv`，用于机械改名/索引脚本）。**不新增任何依赖。**

**Storage**: 文件系统 + git。归档区受版本控制；`var/` 不受版本控制（**唯一没有安全网的地方**）。

**Testing**: 既有门禁 `pwsh -File scripts/run-gates.ps1 -Quick|-Full`；
另加**独立的全仓断链检查**（门禁扫不到全部文档，不能只凭门禁绿断言 SC-001）。

**Target Platform**: 本机 Windows；首要读者是**接手的 coding agent**，其次是业主。

**Project Type**: 仓库重构 + 文档体系（非库、非服务、非应用）。

**Performance Goals**: 不适用。机械脚本须在本机单次运行内完成（改名/索引/断链检查各自亚分钟级）。

**Constraints**:
- MUST NOT 触碰其它会话的未提交改动（清单见 §边界）。
- MUST NOT 改 `AGENTS.md`（归业主专门的维护对话）。
- 不可逆删除前 MUST 留可恢复路径；`var/` 下的东西**只移动不删除**。
- 改名 MUST 同步改正全部 3 类引用：文档间链接（实测 207 处）、代码引用（实测 28 处）、门禁断言。

**Scale/Scope**（开工前实测）:
- 文档 **113 份 / 5,268 KB**；代码 `src/` **152 个 py / 2,244 KB**、`plugin/src/` 19 个 js / 456 KB、`tests/` 158 个 py。
- 最大单文档 `docs/DEVELOPMENT-HISTORY.md` **1,053 KB / 11,888 行**（占根文档体积 61%）。
- 零引用孤儿 **13 份**；只被引用 1 次的 **37 份**。
- `var/` 下 **9 个子目录**。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 本特征如何满足 | 判定 |
|---|---|---|
| I 说人话 | 交付物（大 map、组件契约）的首要用途就是让人与 agent 读懂；汇报用直白语言 | ✅ |
| II 从事实出发 | 对应表每行给理由；分类依据是实测（引用数、体积、最后改动），不是印象 | ✅ |
| III 证据优于断言 | 断链检查独立于门禁（见 Technical Context）；SC-001 用独立检查验证，不用"门禁绿了"顶替 | ✅ |
| IV 一个事实一个归属层 | 规格 FR-017 直接要求"同一主题只有一处说全文"；本特征本身就是这条的大规模执行 | ✅ |
| V 留痕不许悄悄删 | **归档 ≠ 删除**；错话+更正就地保留的既有纪律不变；作废全文删除前先移动 | ✅ |
| VI 先查现成的 | 不引入新工具（用 git + md）；wiki 先**改造既有总览**（`ENCYCLOPEDIA.md` / `INTRODUCTION.md` / `VISION-TREE.md` / `README.md`），不另起第四套 | ✅ |
| VII 对已否决台账 | 本特征不新增产品功能，不做通用层自研（NOT-DOING #6 不触发）；仍需在 Phase 0 逐条对一遍 | ✅（Phase 0 执行） |

**Gate 结果：通过，无违反项，无需 Complexity Tracking。**

## Project Structure

### Documentation (this feature)

```text
specs/001-project-consolidation/
├── plan.md              # 本文件
├── research.md          # Phase 0：命名规范 / 归档体系 / wiki 结构 / 去重策略 的决策与理由
├── data-model.md        # Phase 1：本特征产出的六类实体
├── quickstart.md        # Phase 1：如何验证本特征已达成（可跑的场景）
├── contracts/           # Phase 1：三份契约
│   ├── naming-convention.md      # 命名与分类规范（人读 + 脚本可判）
│   └── component-contract.md     # 单个子系统契约的**必填项模板**
├── checklists/
│   └── requirements.md  # 规格质量检查单（已建）
└── tasks.md             # Phase 2 产出（/speckit-tasks 生成，非本命令产出）
```

### Source Code (repository root) — 目标结构（本特征要达成的形状）

```text
# 仓库根：只留"当前真源"与工程配置；别的一律有明确归属
AGENTS.md              # 项目规矩（本特征不动它）
README.md              # 项目入口（改造为 wiki 入口）
pyproject.toml         # 工程配置
package.json           # 插件工程配置
.gitignore

docs/
├── README.md          # ← 新建：docs 的入口与大 map（各类文件怎么归档、什么功能）
├── INDEX.md           # ← 已有：113 份文档的机械索引（脚本生成）
├── wiki/              # ← 新建：分级接手文档
│   ├── map.md         #     一张大 map：仓库每一类文件在哪、干什么
│   ├── architecture.md#     项目目标与现状（一页读懂的入口）
│   └── components/    #     每套组件一篇（职责/接口/依赖/明确的非目标）
├── archive/           # ← 新建：历史与备份的分类归档区
│   ├── README.md      #     归档索引：哪类历史在哪、怎么查
│   └── <分类>/        #     按类分目录（旧计划 / 调研过程 / 旧基线 / 过程记录）
└── ...（当前真源类文档留原处）

specs/                 # Spec Kit 的工作区（本特征引入，边界写进命名规范）
src/  plugin/  tests/  scripts/  eval/   # 代码与工程，结构不变
var/                   # 本地目录（不进版本控制）：整理为有用途说明的分类
```

**Structure Decision**: **保持既有顶层结构不动**（`src/` `plugin/` `tests/` `scripts/` `eval/` 已是清楚的），
只在 `docs/` 内新增三个受控目录：`wiki/`（分级接手文档）、`archive/`（历史归档）、以及 `docs/README.md`（入口）。
理由：本特征的目标是**让归属变清楚**，不是重新发明目录布局；动既有顶层结构会把 207 处链接的改动面
从"文档内部"扩大到"全仓所有引用"，风险与收益不成比例。

## Complexity Tracking

> 无违反项，本节不填。
