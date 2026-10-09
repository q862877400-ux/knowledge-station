# Implementation Plan: 政务问答采集系统的可运维化

**Branch**: `004-govqa-operationalization` | **Date**: 2026-10-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-govqa-operationalization/spec.md`

## Summary

把现有「一次性扒全量」的采集脚本群，改造成**可长期运营的数据服务**。核心是补齐
**增量轮询**能力（当前完全缺失），并把覆盖完整性、数据可用性、自愈可观测三条线补到可验收水平。

**技术路径**：在现有 `tools/gov-qa/` 上**增量扩展**，不重写。
新增一个「水位存储 + 增量调度」层，复用已有的 331 个 adapter
（它们已经能采全量，只需让它们支持「采到某个位置就停」）。

## Technical Context

**Language/Version**: Python 3.13（项目 venv 已就绪）

**Primary Dependencies**: 已有 `httpx` / `beautifulsoup4` / `scikit-learn` / `jieba` / `joblib`。
**不新增依赖** —— 增量水位用 JSON 文件即可，不需要数据库。

**Storage**: 本地文件（`tools/gov-qa/data/*.jsonl` 为权威存储）。
水位另存 `tools/gov-qa/state/watermarks.json`。**不引入数据库** —— 36 万条规模用文件足够，
引数据库只会增加运维负担（宪法原则 VI「够用即止」）。

**Testing**: 沿用现有 `recon/*.py` 体检脚本群 + 新增端到端验收脚本。
验收靠**退出码**（与现有 `check.sh` 一致）。

**Target Platform**: Windows + Git Bash（当前环境）；脚本须兼容 POSIX shell。

**Project Type**: 单项目（CLI 工具 + 数据产物），非服务端。

**Performance Goals**:
- 全通道增量轮询 ≤ 10 分钟（SC-001）
- 体检 ≤ 60 秒（SC-010）

**Constraints**:
- **必须对并发安全** —— 本目录有并行 agent 在跑（GOAL.md 硬约束 1）
- **必须幂等** —— 重复轮询不得产生重复记录（SC-002）
- **必须可断点续跑** —— 中断不丢数据（SC-003）
- **机器可读输出一律纯 ASCII**（本次闸门排查 4 层 bug 换来的教训）

**Scale/Scope**: 331 个 adapter / 681 个来源 / 36 万条记录 / 32 个省级 + 333 个地级行政区。

### NEEDS CLARIFICATION

无。所有技术未知点都已在 spec 的 Assumptions 里用合理默认解决。
唯一需用户确认的是**达标下限**（省级 ≥3,000 / 地级 ≥500），已标注为假设。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 本特性如何满足 | 判定 |
|---|---|---|
| **I. 说人话** | 面向用户的输出（体检报告、销号表、轮询摘要）用「能做什么/会看到什么/代价是什么」表述。spec 与 plan 的交付描述面向数据使用者而非开发者。 | ✅ |
| **II. 从事实出发，不迎合** | 立项的直接原因就是**承认现状不足**（增量轮询从未验证、14 省深度不足、标签准确率是自评）。**不把「331 个适配器」当成绩**，而指出它是「未验证的死资产」。 | ✅ |
| **III. 证据优于断言** | 每条 Success Criteria 都要求**可外部观察的验证**：SC-002 要求「0 条新增且 0 条重复」实测；SC-007 要求**人工抽检 200 条**算真实准确率（非模型自评）；SC-009 要求**人为制造故障**验证检出。**未做的写「明确未做」**。 | ✅ |
| **IV. 一个事实一个归属层** | 事实归属：spec → `spec.md`；技术决策 → `plan.md`+`research.md`；数据结构 → `data-model.md`；接口契约 → `contracts/`；运行验证 → `quickstart.md`。**不重复写全文**。 | ✅ |
| **V. 留痕不许悄悄删** | 闸门排查的 4 层 bug（中文 sed 失配 / 自愈打满超时 / pickle 失败 / 编码异常）**全部保留在 `check-trace.log` 与记忆文件里**，含我自己写错的那两条。**不删错话**。 | ✅ |
| **VI. 先查有没有现成的** | **已查**：增量采集的成熟方案（Scrapy `JOBDIR`、RSS `Last-Modified`/`ETag`）都读过。**结论：不引入框架** —— 现有 adapter 是「翻页 HTML 抓取」，框架帮不上，且会破坏 331 个 adapter 的兼容性。⇒ 自写薄水位层（~200 行）。 | ✅ |
| **VII. 提案前先对已否决台账** | ⚠ 本仓库**无** `docs/NOT-DOING.md`（该文件属 KnowledgeStation 主仓）。gov-qa 的「判死清单」记在 `GOAL.md §三`。**本特性不涉及任何已判死通道**（判死的是采集目标，不是可运维化）。 | ✅（附注） |

**结论：七条原则全部通过，无违规需辩护。**

## Project Structure

### Documentation (this feature)

```text
specs/004-govqa-operationalization/
├── spec.md              # 需求规范（已完成，checklist 全项通过）
├── plan.md              # 本文件
├── research.md          # Phase 0：技术选型与调研结论
├── data-model.md        # Phase 1：水位/通道/覆盖单元的数据结构
├── quickstart.md        # Phase 1：端到端验证指南
├── checklists/
│   └── requirements.md  # 规范质量清单（已完成）
└── contracts/           # Phase 1：CLI 命令契约
    ├── poll.md          # 增量轮询命令契约
    ├── coverage.md      # 覆盖销号表命令契约
    └── health.md        # 体检命令契约
```

### Source Code (repository root)

```text
tools/gov-qa/
├── harvest.py               # 现有：全量采集入口（不改对外行为）
├── adapters/                # 现有：331 个 adapter
├── data/*.jsonl             # 现有：权威数据存储
├── state/                   # ★ 新增：运行态
│   └── watermarks.json      #   各通道水位
├── poll.py                  # ★ 新增：增量轮询调度器
├── coverage-report.py       # ★ 新增：覆盖销号表生成
├── health.py                # ★ 新增：一句话健康结论
└── recon/                   # 现有：体检脚本群（扩展，不重写）
    ├── audit-coverage.py    #   已有 --gate 纯 ASCII 模式
    ├── label-coverage.py    #   已有 --quiet 纯 ASCII 模式
    └── ...
```

**Structure Decision**: 在现有 `tools/gov-qa/` 下**增量新增**三个顶层脚本
（`poll.py` / `coverage-report.py` / `health.py`）+ 一个 `state/` 目录。
**不重写 `harvest.py`、不动 `adapters/`** —— 那 331 个 adapter 是项目最贵的资产，
改造风险远大于收益。增量能力通过**在 adapter 层之上加调度层**实现。

## Phase 0: 关键调研（详见 research.md）

三个必须解决的未知点：

1. **水位用什么做？** 政务站没有增量 API，只能靠「页码 / 时间戳 / 已知 id」。
   不同 adapter 的「可比较位置」不同 ⇒ 需要**每通道可声明自己的水位类型**。
2. **如何保证幂等？** 现有 adapter 用 `(source, id)` 做唯一键，但部分源 id 是内容指纹。
   ⇒ 幂等靠**落盘前按 id 去重**（已有 `dedup-data.py` 的能力，需前置到写入路径）。
3. **如何做到断点续跑？** 现有 `harvest.py` **跑完才落盘**（GOAL.md 硬约束 3），
   这是「中断丢整轮」的根因。⇒ 增量模式必须**边采边落盘**。

## Phase 1: 设计产物

- `data-model.md` —— 水位、通道、覆盖单元、体检报告的字段与状态机
- `contracts/*.md` —— 三个 CLI 命令的输入/输出/退出码契约
- `quickstart.md` —— 端到端验证步骤（含「人为制造故障验证检出」）

## 复杂度与取舍

| 决策 | 取舍 |
|---|---|
| 不引入数据库 | 水位用 JSON 文件。**代价**：并发写需加锁。**收益**：零运维负担（宪法 VI） |
| 不重写 adapter | 在调度层实现增量。**代价**：需 adapter 暴露「可比较位置」。**收益**：331 个资产零风险 |
| 不引入爬虫框架 | 自写 ~200 行水位层。**代价**：没有现成重试/去重基建。**收益**：不破坏现有兼容性 |
| 机器接口纯 ASCII | 人类输出仍用中文。**代价**：两份格式化代码。**收益**：不再有跨环境编码 bug（已踩 4 次） |

## 风险

| 风险 | 缓解 |
|---|---|
| 部分 adapter 无法提供「可比较位置」 | 该通道退化为「全量重采 + 按 id 去重」，**仍保证不重复**，只是慢 |
| 并行 agent 同时写同一文件 | 水位文件加锁；数据写入前按 id 去重 |
| 水位文件损坏 | 安全退化为全量重采（FR-006），**宁可慢不可漏** |
| 新口径（只采国家级公告）改变分母 | 覆盖销号表支持**按口径过滤**，两种口径都能出表 |

## 附：本轮实际进度（2026-10-10）

- [x] Phase 0 调研 → `research.md`
- [x] Phase 1 设计 → `data-model.md` + `contracts/` + `quickstart.md`
- [ ] Phase 2 任务拆解 → `tasks.md`（下一步 `/speckit-tasks`）
