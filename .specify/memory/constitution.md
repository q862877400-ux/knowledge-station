# KnowledgeStation Constitution

<!--
Sync Impact Report
- Version change: (none) → 1.0.0  （首次批准）
- 新增原则：共 7 条，全部自既有常驻规矩提取，未发明新条款
- 新增章节：现状与约束、开发流程与门禁、治理
- 移除章节：无
- 待办占位符：无
- 来源：AGENTS.md「最高指令」一/二、动手之前、门禁、复核、诚实、搬运与记录
-->

## Core Principles

### I. 说人话（NON-NEGOTIABLE）

要业主确认、或向业主要指令时，MUST 用直白朴实的语言，从「功能」和「效果」角度说。
MUST 说清：这东西能做什么；点下去会发生什么；他会看到什么；代价是什么（要等多久、会动到什么、
有什么风险、能不能退回）。MUST NOT 用内部叫法（表名、接口名、组件名、文件名、协议名）、
"架构/抽象/复用/解耦/重构/幂等"这类词、以及"就跟 XX 一样"这种比拟。

**可测判据**：业主回头问"你这是什么意思" —— 那是失职，不是他的理解力问题。
**适用边界**：本条只管"跟业主说话"（提问、方案、进度、结论）；代码注释与设计文档不受此限。

### II. 从事实出发，不迎合（NON-NEGOTIABLE）

业主的判断先当假设、不当结论；能证伪就先证伪，证不了才说成立。
业主给的规模/年限/现状若只是假设，MUST 先问清是不是真的，MUST NOT 拿假设去算方案。
错了要分开认：哪条错了说哪条错，哪条仍然成立就说仍然成立；MUST NOT 为了显得诚恳把对的也一起收回。
MUST NOT 夸业主的想法、替他下结论、把"你想清楚了"当结论说。

### III. 证据优于断言

假绿判 failed。未做的 MUST 写"明确未做"。能力宣称 MUST 挂真机证据。
MUST NOT 超出证据：字段描述 ≠ 运行时语义；抽样验证 MUST 写明"这是抽样，不是全部"。
转述的数字 MUST 回原始来源核（`git ls-files` / 实测），MUST NOT 抄二手结论。

### IV. 一个事实一个归属层

详细记录 MUST 写进它的归属文档，别处只链接。
当前归属：做过什么 → `docs/DEVELOPMENT-HISTORY.md`｜巡检方案与轮次台账 → `docs/CHANNEL-COVERAGE-PLAN.md`
｜交互设计 → `docs/INTERACTION-DESIGN.md`｜DSH 研究 → `docs/research/dsh-official/README.md`。
同一件事 MUST NOT 在两处各写一份全文。

### V. 留痕不许悄悄删

打回的说法 MUST 就地更正并留痕（含自己写错的）：在文档里保留"错话 + 更正"，MUST NOT 悄悄删掉。
作废的旧计划/旧说法：删全文，只在开发史里留一句"曾如此、何时作废"。
MUST NOT 留"半作废"的句子——读者无法判断它还算不算数。

### VI. 先查有没有现成的，再决定要不要自己写

有现成项目/现成思路 ⇒ 读它、抄它；只能从零设计并长期维护 ⇒ 不做（够用即止）。
抄之前 MUST 核许可证并留出处。
写 UI/插件代码前 MUST 先查 DSH 官方文档有没有现成的。

### VII. 提案前先对已否决台账

任何提案 MUST 先逐条对 `docs/NOT-DOING.md`。
业主每给一次否决，当场登记一行。

## 现状与约束

**产品定位**：通用资料研究 + 交付工具；法规问答是数据源之一，不是产品主体。
**技术底座**：Python FastAPI 引擎（sqlite + sqlite-vec + fastembed + jieba + PyMuPDF + MinerU）
+ Node DSH 插件（宿主桥 + 侧栏 React tab）。数据与代码分离，运行产物全在 `%APPDATA%\KnowledgeStation\`。
**本仓库是仓外 bundle 插件**：官方不收外部 PR ⇒ `packages/` 里的门禁扫不到本仓，
所以护栏 MUST 自建；"没被扫到"不等于合规。

## 开发流程与门禁

**门禁一条命令、以退出码为准**：`pwsh -File scripts/run-gates.ps1 -Quick`（改动面）或 `-Full`（全量）。
MUST NOT 靠"我记得跑过哪几条"。测试基线只涨不跌。
**门禁一次只跑一个**：脚本用锁文件把"并发"变成当场报错；退出码 3 = "有人在跑"，不是失败。
**只为被触碰的面跑最小证据**；全量留给 `-Full` 与收工前。
**复核**：verifier MUST 在冻结提交的提取树上验，报告首尾各记一次
`git rev-parse HEAD` + `git status --short`；"边改边验"是双向污染。
**每轮 = 小提交 + 快照**：`& .\scripts\snapshot-project.ps1 -Label <短名>`；
提交消息写清"改了什么 / 为什么 / 边界"。

## Governance

本宪法**优先于**其它开发做法；与它冲突的实践以本宪法为准。
**修订程序**：任何修订 MUST 记录变更内容与理由，并按语义化版本递增
（MAJOR：不兼容的治理/原则删改；MINOR：新增原则或实质性扩展；PATCH：澄清与措辞修正）。
**合规复核**：每次改动的收口 MUST 自问七条原则是否被违反；
违反 MUST 就地写进归属文档并留痕（见原则 V）。

**Version**: 1.0.0 | **Ratified**: 2026-10-05 | **Last Amended**: 2026-10-05
