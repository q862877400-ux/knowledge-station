# DSH 官方技能与门禁摘要（H）

源仓库根 `D:\AI\DSH\deepseek-harness`；下文所有 `file:line` 均相对该根。
读取范围：`.agents/skills/*/SKILL.md`（12 个全读）+ `dsh-doc/references/` 5 个参考 + `dsh-ci-test-reliability/references/ci-flake-diagnosis.md` + `dsh-trim-cot-leakage/references/recall-batteries.md`；门禁取自 `scripts/run-gates.ts`、`package.json`、`docs/development.md:129-137`、`AGENTS.md:81-115`。

## 官方技能索引

| 技能 | 什么时候用 | 关键步骤/判据 | 出处 file:line |
|---|---|---|---|
| dsh-archive-agent-notes | 新增/审计/裁剪/归档/还原 Agent Notes | 新增 note 时必须同 PR 做同主题 active note 的 supersession 审计；按"未来决策价值"分类（Implemented 可归档 / Proposed 永不归档 / Rejected 仅在仍能阻止诱人错误时留下）；归档 = 冻结 `foo.md`+`foo.zh.md`+`foo.i18n.yaml` 三件套移到 `archived/<kind>/`、只加 `Archived: YYYY-MM-DD`、不修文不修链 | `.agents/skills/dsh-archive-agent-notes/SKILL.md:16,22-26,56-60` |
| dsh-ci-test-reliability | 写/审/诊断可能在 CI 并发、共享主机资源、时钟、进程全局态、子进程、端口下不确定失败的测试 | 先建模执行拓扑；"Process isolation does not isolate host ports, predictable filesystem paths, external services, databases, sockets, or inherited child processes."；端口用 `listen(0)` 读实际地址、临时根用 `mkdtemp`；`process.env`/`cwd`/fake timers/globals 视为独占可变资源；同步等状态而非 sleep；cleanup 必须等到静默完成；拒绝 flake 掩盖式修法 | `.agents/skills/dsh-ci-test-reliability/SKILL.md:20-27,33-39,45,77-83,86-89,102-114` |
| dsh-code-review | 审 deepseek-harness 的 PR | 先 `pnpm --silent run change-scope --base <ref> --head <ref>` 再读 diff；7 条 blocking（新 prose 需语义审、docs 与代码同 diff 更新、core type docs、注册必须能清理、invariant companion 必须语义、必需证据、Client UI 文案 locale-owned）；其余为手工检查清单 | `.agents/skills/dsh-code-review/SKILL.md:8,21-29,31-48` |
| dsh-doc | 新建/重构/审/审计/迁移 DSH Markdown 文档、包 README、文档站 | 8 步工作流（分类→就近归属→YAML `kind` 选模板→双语同 pass 行对齐→运行每条被宣称的操作取证→`test:docs`/`doc-sync`/`lint`/`git diff --check`）；kind→模板一一映射；网站是"tested projection"不是第二份副本 | `.agents/skills/dsh-doc/SKILL.md:28-37,49-61,94-100,116-127` |
| dsh-find-simplifications | 找非显然的简化候选、删冗余注释/过重文档、写 proposed Agent Note 或 TODO/FIXME/XXX | 强候选需有生产消费者证据（rg 先查，再读调用点）；dual LLM adapters 与 JSONL 持久化默认视为有意设计；dependency 替换要称净删除量；每个候选要么证明要么拒绝；输出为 Agent Note 结构（Problem/Proposal/Why not keep/Acceptance/Risks） | `.agents/skills/dsh-find-simplifications/SKILL.md:17-31,15,64-73,75-90,110-124` |
| dsh-merging-stacked-prs | 落地 A←B←C 依赖 PR 栈、合并 base 为另一开启 PR 的 PR | 必须用 GitHub 官方 stack：先 `gh stack --version`，不可用就 hard-stop 不退回逐个 merge；用 `PullRequest.stack`/`stackEntry.position` 作栈成员权威；同作者链自动 `gh stack link`；落地 `gh stack merge <stack-number> --yes --merge`；等所有选中 PR 报 `MERGED`，删分支前要求 `gh pr list --state open --base <branch>` 长度为 0 | `.agents/skills/dsh-merging-stacked-prs/SKILL.md:12,20-46,50-66,83-99,101-117` |
| dsh-pre-push-checks | push/force-push/标 ready/宣称检查通过之前；`gh stack sync` 发布重写分支之后 | "There is no universal local baseline beyond the hooks."；先 `change-scope` 看范围，再按面选最小证据（包/脚本→owning vitest；docs→`doc-sync`；model/editor/CLI 可见输出→keyless snapshot；manifest/导出/构建→`build`+hygiene+built smoke）；覆盖率要显式 `--coverage.include` 指名源文件；重写推送只用 `--force-with-lease` | `.agents/skills/dsh-pre-push-checks/SKILL.md:8,19-25,29,33-41,52-73,81-94` |
| dsh-prose-standard | 写/审/恢复/裁剪/审计仓库 prose（Markdown、JSDoc、注释、prompt、诊断、CLI/UI 字符串） | 必须先有显式 `scope`，缺失就报缺并停；始终排除 `vendor/` 与 `.agents/notes/archived/`；"Remove adjectives, repetition, and narration only when every factual clause survives"；按 prose 位置规定必需覆盖（公共 JSDoc、内部注释、模块注释、测试、cookbook、README、Agent Note、postmortem、skill、示例配置、prompt/可见字符串、诊断） | `.agents/skills/dsh-prose-standard/SKILL.md:16,22-24,28-42,44-59` |
| dsh-speed-up-perf | 调研/优化性能、设计合成基准或 CI 性能门禁、剖析长 Session/Web 响应 | 先定端点/负载/资源/停止规则；实现前填 measurement card（操作、负载、入口、时钟、内存、判据、行为）；先量未优化版本再改一处因果；必须有 negative control；benchmark 不得依赖用户 home/私有数据 | `.agents/skills/dsh-speed-up-perf/SKILL.md:14,31-57,59-74,76-82` |
| dsh-translate-docs | 仅当用户显式调用 `dsh-translate-docs` | `disable-model-invocation: true`；"Never select or load it for ordinary documentation work"；更新走 briefing 驱动（`gen-translation-brief`，纯代码围栏变更可 `--apply`）、新对走整篇路径（先读 i18n 4 份真相源）；`verify-translation-pairing --write <pair>` 收尾 | `.agents/skills/dsh-translate-docs/SKILL.md:4-5,10-12,18-34,36-56,64-70` |
| dsh-trim-cot-leakage | 审计/修"像泄漏的推理过程"的 prose | 唯一判据："could a reader at HEAD, with no access to any session transcript, PR thread, or uncommitted draft, resolve every reference and verify every claim?"；8 类 taxonomy（死会话引用、PR 视角、变更叙述、review 编排、对评审者辩解、推导脚本、hedge、作者语言残留）；先只读跑 recall batteries 再语义判断 | `.agents/skills/dsh-trim-cot-leakage/SKILL.md:10-12,14-23,39-45`；`references/recall-batteries.md:6-13` |
| record-browser-gif | 任何改动产品用户可见 GUI 行为的 PR（MUST），或用户要录浏览器演示 GIF | "A pull request that changes product-user-visible GUI behavior MUST include a demonstration GIF"；录制与发布分开；必须真服务器+真 API key+真模型轮次，禁止 fixture/mock/合成事件；一次 storyboard 一次 evidence run 不得拼接；`encode_gif.py` 编码；发布用 `gh --attach`（≥v2.99.0、≤10MB），否则 orphan assets 分支 | `.agents/skills/record-browser-gif/SKILL.md:12-16,18-23,25-32,78-93,116-141,143-171` |

### dsh-doc 的 12 个支撑文件（目录内共 13 个文件）

`references/`：`metadata-links-i18n.md`（frontmatter/kind 推导/描述质量/链接/行对齐/侧车）、`structure-hierarchy.md`（页序、段落递进、docs 树、小规则文件、Further Exploration、Dev Note 归属）、`style.md`（短 Summary、受控技术英语、`-----` 分隔、`<details>` 折叠、强调纪律）、`review.md`（newcomer test、证据审、包 README 审、参考样例、验证命令）、`website-sync.md`（manifest 字段、投影链接规则、预览与校验、部署分离）。
`templates/`：`package-group.md`、`package-reference.md`、`package-library.md`、`package-bundle.md`、`persistence-change.md`、`persistence-release.md`、`persistence-format.md`（各对应一个 kind，一一映射）。
已按需读取 `metadata-links-i18n.md`、`structure-hierarchy.md`、`style.md`、`review.md`、`website-sync.md`；7 个 template 未逐份读（其作用由 `SKILL.md:51-61` 与 `metadata-links-i18n.md:39-47` 的映射表确定）。

## 官方门禁清单

| 门禁命令 | 它保护什么（防止哪类漂移/静默失效） | 出处 |
|---|---|---|
| `pnpm run test:docs`（= `run-gates.ts doc-quick`） | 快速综合文档检查：pairing/wrap/links/README/budgets/skill metadata/Agent Note 门禁，无构建；只跑 `quick` 叶子 | `scripts/run-gates.ts:794-796`；`.agents/skills/dsh-doc/SKILL.md:127`；`package.json:118` |
| `pnpm run doc-sync`（= `doc-sync` 聚合） | 全量文档叶子：`doc-typecheck`、`docs:build`、`verify-doc-graphs` 及全部生成目录 `--check` 与 Agent Note/README/budget/链接门禁 | `scripts/run-gates.ts:723-787`；`package.json:180` |
| `pnpm run doc-typecheck` | 文档中可编译 fence 相对源码的漂移（与 `verify-type-equiv` 同衍生物规则，跳过两种 source-equivalence fence） | `docs/development.md:177`；`scripts/run-gates.ts:737` |
| `pnpm run verify-translation-pairing` | 双语对结构、精确行数、术语、链接 locale/语义目标、侧车 blob 哈希记录；缺对/失同步即红 | `.agents/skills/dsh-doc/references/metadata-links-i18n.md:67,73`；`references/review.md:57` |
| `pnpm run verify-type-equiv` | `ts type-equiv` / `ts public-api` 粘贴块与源码声明+JSDoc 漂移；1:1 block↔manifest 对应 | `docs/development.md:171-177`；`scripts/run-gates.ts:741` |
| `pnpm run verify-export-jsdoc` | 导出缺 JSDoc（function-like 缺 `@param`/`@returns`） | `AGENTS.md:163`；`scripts/run-gates.ts:750` |
| `pnpm run verify-md-links` / `verify-md-wrap` / `verify-doc-refs` / `verify-repository-references` / `verify-public-repository-links` | 仓库内链接可解析、换行纪律、文档引用与公开仓库链接漂移（缺失目标必须失败而非静默坏链） | `scripts/run-gates.ts:740,748,762,760,759` |
| `pnpm run verify-cordis-catalog` / `verify-cordis-inspect-catalog` | 从源码生成的 Cordis 目录与 Cordis Inspect 目录未随源码重生成 | `scripts/run-gates.ts:742-743` |
| `pnpm run verify-tool-catalog` / `verify-config-catalog` / `verify-client-catalog` | 工具目录、配置目录、client 目录由生成器 `--check` 锁定 | `scripts/run-gates.ts:751,752,749` |
| `pnpm run verify-skill-invocation-metadata` | skill 的调用元数据（如 `disable-model-invocation`/`user-invocable`） | `scripts/run-gates.ts:772`；`.agents/skills/dsh-doc/SKILL.md:125` |
| `pnpm run verify-archived-agent-notes` | 归档三件套封条 append-only：先证明既有封印仍匹配，再加新哈希 | `.agents/skills/dsh-archive-agent-notes/SKILL.md:60`；`scripts/run-gates.ts:771` |
| `pnpm run verify-agent-note-classification` / `verify-agent-note-format` | Agent Note 生命周期分类与格式 | `scripts/run-gates.ts:769-770` |
| `pnpm run verify-package-readme-summaries` | 英文包 README Summary ≤100 `wc -w` words | `.agents/skills/dsh-doc/SKILL.md:124`；`references/style.md:18` |
| `pnpm run verify-package-readme-model-experience` / `verify-package-readme-limitations` | 包 README 必须有 canonical `Model Experience` 与 `Known Limitations and Deferred Work` 作为最后两个 H2 | `references/structure-hierarchy.md:30`；`references/style.md:41`；`scripts/run-gates.ts:768,785` |
| `pnpm run verify-doc-budgets` | 常驻文档字数上限（`scripts/doc-budgets.manifest.json`）；红门禁走 relocate-condense-raise 政策 | `.agents/skills/dsh-doc/SKILL.md:96`；`scripts/run-gates.ts:774` |
| `pnpm run verify-client-ui-i18n` | 硬编码产品文案；要求 typed dictionary + `t`/本地化 props | `AGENTS.md:147`；`scripts/run-gates.ts:718` |
| `pnpm run verify-cordis-config` | raw/Web `cordis.yml` 的 bare plugin 必须出现在其 resolver manifest 的 `dependencies` | `AGENTS.md:124`；`scripts/run-gates.ts:306` |
| `pnpm run verify-package-invariants` / `verify-built-package-invariants` | `./invariant` 只在独立观测可分歧时发布；空 installer 与"检查 service 是否存在/插件元数据/固定示例"无效 | `AGENTS.md:126`；`scripts/run-gates.ts:708,674-679` |
| `pnpm run verify-runtime-closure` / `verify-default-product-isolation` / `verify-application-entrypoints` / `verify-package-dependencies` / `constraints` | 运行时依赖闭包、默认产品隔离、应用入口、包依赖方向、workspace 约束（含 split tsconfig 引用面） | `scripts/run-gates.ts:299-303`；`docs/development.md:70` |
| `pnpm run verify-optional-dependency-imports` / `verify-no-bare-dispatcher` | 可选依赖的 import 形态；proxy-aware dispatcher 要求 | `scripts/run-gates.ts:307,312` |
| `pnpm run typecheck` | Host lib 阶段（含生成的 Typert 契约）→ Client tsc；同时是 pre-push hook 的唯一内容 | `AGENTS.md:92`；`docs/development.md:121`；`scripts/run-gates.ts:322` |
| `pnpm run lint` / `pnpm run duplication` | oxlint（`lint:contracts-ready`）；jscpd 跨文件 TypeScript 克隆检测 | `scripts/run-gates.ts:580-589,324`；`package.json:51` |
| `pnpm run test:coverage` | CI 覆盖率门禁：`packages/*/*/src` 每文件 100%（`test` 不是覆盖率门禁） | `AGENTS.md:87,115`；`package.json:53` |
| `pnpm run test:snapshot` / `test:expected` | 无 key 录制会话回放覆盖 model/产品用户可见输出；owner-local 过程期望 | `AGENTS.md:90,148`；`scripts/run-gates.ts:658-672` |
| `pnpm run build` + `publint` + `verify-node-next-types` + built-bin-smoke | 构建产物入口、声明对 NodeNext 消费者的可用性、内置 bin 冒烟（源码面与产物面不得混用） | `AGENTS.md:139`；`scripts/run-gates.ts:336-343` |
| `pnpm run hygiene` | publint + workspace/package/dependency 检查 + NodeNext 消费者检查（无 built 产物时这些会缺证据） | `AGENTS.md:96`；`docs/development.md:98` |
| `pnpm run check:all` | 全面本地门禁集合；与 Git hooks 无关，且"is not an agent instruction" | `docs/development.md:127`；`scripts/run-gates.ts:263-283` |
| `gh pr checks` | 远端 CI 真值；pending 只能报 pending。无 checks 且 `total_count: 0` 时先查 `mergeable`/`mergeStateStatus`——`CONFLICTING` 时 GitHub 不创建 `pull_request` 工作流 | `.agents/skills/dsh-pre-push-checks/SKILL.md:123,128-134` |
| `git diff --check` / pre-commit | 空白错误、staged 配对记录、vendored `src` 变更必须带 `vendor/README.md` 清单更新；文件以恰好一个尾换行结束 | `docs/development.md:119`；`AGENTS.md:155` |

## 该复用而不是自造的流程

- 自造"push 前跑一遍全套"的清单 → `dsh-pre-push-checks`（没有普适本地基线，只按面选最小证据；不重复已通过的检查，尤其不要为推送再跑 typecheck） → `.agents/skills/dsh-pre-push-checks/SKILL.md:29,42,75-77`
- 自造插件的 README/文档结构 → `dsh-doc` 的 kind 系统 + `templates/package-reference.md`（kind 由 `package.json` 的 `dsh.bundle.patch` 与入口形状机械推导） → `.agents/skills/dsh-doc/SKILL.md:49-61`；`references/metadata-links-i18n.md:32-37,49`
- 自造"测试偶发失败"的处置（加重试、全部串行、加 sleep、放宽断言） → `dsh-ci-test-reliability` 明确把这几项列为 flake 掩盖而非根因修复 → `.agents/skills/dsh-ci-test-reliability/SKILL.md:102-114`
- 自造 CI flake 诊断流程 → `references/ci-flake-diagnosis.md`（冻结证据→按 8 类分类→最小拓扑阶梯复现→在 owner 处修） → `.agents/skills/dsh-ci-test-reliability/references/ci-flake-diagnosis.md:5-11,13-26,28-42,44-48`
- 自造 PR 评审清单 → `dsh-code-review`（先 `change-scope`，7 条 blocking + 手工检查；"a short review with one substantiated blocker is better than a list of nits"） → `.agents/skills/dsh-code-review/SKILL.md:8,21-29`
- 自造注释/文档措辞规则 → `dsh-prose-standard`（完整命题规则 + 按位置的必需覆盖）+ `dsh-trim-cot-leakage`（HEAD 可解析判据 + recall batteries） → `.agents/skills/dsh-prose-standard/SKILL.md:28-42,44-59`；`.agents/skills/dsh-trim-cot-leakage/SKILL.md:10-12,39-45`
- 自造"清理/简化/写 TODO"流程 → `dsh-find-simplifications`（候选质量标准、生产 vs 非生产消费者分类、Agent Note/内联 TODO 的分界）+ `dsh-archive-agent-notes`（归档机制） → `.agents/skills/dsh-find-simplifications/SKILL.md:17-31,75-90,126-132`；`.agents/skills/dsh-archive-agent-notes/SKILL.md:54-60`
- 自造性能基准与阈值 → `dsh-speed-up-perf`（先量后改、measurement card、negative control、不得为测量加生产导出） → `.agents/skills/dsh-speed-up-perf/SKILL.md:31-57,59-74`
- 自造栈式 PR 合并/retarget 脚本 → `dsh-merging-stacked-prs`（强制官方 `gh stack`，禁止 `gh pr merge` 逐个合并与手动 retarget） → `.agents/skills/dsh-merging-stacked-prs/SKILL.md:8,12,97-99`
- 自造翻译流程 → 只有显式调用才用 `dsh-translate-docs`；日常双语更新走 `docs/AGENTS.md` 的 one-shot、one-pass 与 `verify-translation-pairing --write <pair>` → `.agents/skills/dsh-translate-docs/SKILL.md:10-12`；`.agents/skills/dsh-doc/SKILL.md:47`
- 自造 GUI 演示截图/GIF 流程 → `record-browser-gif`（真服务器+真模型、一次 run 一个 storyboard、`gh --attach` 发布、绝不把二进制提交进 PR 分支） → `.agents/skills/record-browser-gif/SKILL.md:14-16,20-22,120-141`

## 与"第三方插件作者"最相关的 5 条

1. **`dsh-pre-push-checks` 决定"我该跑什么"** —— 插件作者最容易自造一套"全跑"或"只跑 lint"的直觉；该技能给出唯一官方选择规则（按面匹配证据、覆盖率必须指名源文件范围、`change-scope` 只看自己的 diff），并明确 pre-push hook 只做增量 typecheck。`.agents/skills/dsh-pre-push-checks/SKILL.md:8,29,33-41,52-62`
2. **`dsh-doc` 的 `kind` 系统决定插件 README 的形状** —— 插件是 `apply` 导出/default service 导出 → `package-reference`；`dsh.bundle.patch` → `package-bundle`；纯模块 API → `package-library`（且**不得**写 profile 安装指引）。README 还要满足 Summary ≤100 words、最后两个 H2 必须是 Model Experience 与 Known Limitations。`.agents/skills/dsh-doc/SKILL.md:51-61`；`references/metadata-links-i18n.md:32-37,49`；`references/structure-hierarchy.md:30`
3. **注册/贡献必须可清理 + invariant 必须语义** —— 这是插件作者最常踩的硬门禁："every contribution goes through `ctx.effect()` / `ctx.on()`; a registry's `register()` returns the disposer"，且 `./invariant` 只应在独立观测可分歧时发布，空 installer 与"检查 service 存在"的检查无效。`.agents/skills/dsh-code-review/SKILL.md:26-27`；`AGENTS.md:125-126`；门禁 `verify-package-invariants`/`verify-built-package-invariants` `scripts/run-gates.ts:708,674-679`
4. **`dsh-ci-test-reliability` 保护插件自带的 fixture** —— 插件测试常绑端口、临时目录、`process.env`、子进程；该技能给出原子分配、全局态还原、静默 teardown 与"必须证明目标回归"的判据，并明确进程隔离不隔离端口/可预测路径/外部服务。`.agents/skills/dsh-ci-test-reliability/SKILL.md:27,33-39,45,86-89,92-100`
5. **改 GUI 就 MUST 交 GIF，且必须真跑** —— 任何产品用户可见 GUI 行为的 PR 必须附真实服务器+真实模型轮次录制的 GIF，并声明精确 SHA、来源、模式开关与是否真跑了模型；录制与发布分离，二进制不得进 PR 分支。`.agents/skills/record-browser-gif/SKILL.md:12-16,20-22,120-141`

## 未解答

- `docs/development.md` 没有逐门禁说明表，只指向 `scripts/run-gates.ts` 与工作流文件（`docs/development.md:131`）；因此上表"保护什么"里凡是我未读脚本实现的行，均只由 gate 名 + 命名/注释/其他文档的交叉引用得出，未逐个验证实现语义。未读实现的叶子包括：`verify-workflow-guest`、`verify-mermaid`、`verify-scoped-events`、`verify-concrete-terms`、`verify-doc-graphs`、`verify-subsystem-pages`、`verify-package-paths`、`verify-tsconfig-paths`、`verify-config-source-ownership`、`verify-persistence-catalog`、`verify-persistence-changes`、`verify-persistence-releases`、`verify-persistence-formats`、`verify-session-format-catalog`、`verify-translation-prompt`、`doc-standard-tests`、`docs-site-projection`（`scripts/run-gates.ts:739-786`）。
- `.github/workflows/ci.yml` 的 job 与 lane 划分、`ci-windows-*` 三档与 `scripts/wine-windows-gates.sh` 未读；`ci-windows-observational` 的 `allowFailure` 边界未确认（`scripts/run-gates.ts:520-575`）。
- `dsh-doc` 的 7 个 template 未逐份读；"13 supporting files"若指目录内文件总数则含 `SKILL.md` 本身，本摘要按"12 个支撑文件 + SKILL.md"处理。
- `packages/AGENTS.md`（包作者规则，被 `dsh-code-review` 引用）与 `docs/AGENTS.md`（写作规则/字数政策）未读，因此 `verify-package-invariants`、`verify-doc-budgets` 的精确判据只有二级引用。
- `verify-cordis-config`、`verify-tool-catalog`、`verify-config-catalog` 的实现未读：能确认"bare plugin 必须在 resolver manifest dependencies"（`AGENTS.md:124`），但不能确认三者对插件 `cordis.yml` 行的具体校验项。
- 未确认第三方（仓库外）插件包是否同样受这些门禁覆盖；技能与门禁均以本仓库路径（`packages/*`、`.agents/skills`、`docs/`）为范围，仓库外适用性需要另行确认。
