# AGENTS.md — KnowledgeStation 的站立指令

本文件只放**每个会话都需要在上下文里的规矩**，每条 1–3 行并指向它的归属文档。
它**不是**史书也不是方案：做过什么、为什么那么做，去各自的归属层（见下"事实的归属"）。

## 动手之前

- **提案前先对一遍[已否决/已作废台账](docs/NOT-DOING.md)**（2026-09-19 立）：我连续两次把业主
  **早就否掉**的东西重新端上来当待办（Word/PPT 交付物、bbox 高亮——实际早改成**红色定位箭头**）。
  ⇒ 任何新待办/计划/设计，先在台账里搜一遍；命中就**不许再提**。业主每给一次否决，**当场登记一行**。
- **先查有没有现成的，再决定要不要自己写**（业主 2026-09-19 裁定：**通用层「纯借鉴」，不造轮子**）：
  有现成项目/现成思路 ⇒ **读它、抄它**（鼓励）；只能从零设计并长期维护 ⇒ **不做**（够用即止）。
  抄之前先核许可证并留出处（WeKnora 是 MIT，需随附版权声明）。判据与出处见
  [WeKnora 影响评估](docs/research/weknora-assessment.md) §五第 0 条。
- **先查 DSH 有没有现成的**：写 UI/插件代码前，先看 [DSH 官方文档精读索引](docs/research/dsh-official/README.md)
  与 [升级手册](docs/research/dsh-official/REALIGN.md)。已因"自己造轮子"返工过两次（HTML 仿真界面、手搓徽章）。
- **外置插件的硬约束与已作废的说法**都在 [ERRATA-alpha.2](docs/research/dsh-official/ERRATA-alpha.2.md)：
  插件改动**是热重载的**（不必重启宿主）、**不必**补 `peerDependencies`、`priority` 是 band 字面量。
- **本仓库是仓外 bundle 插件**（官方不收外部 PR）⇒ `packages/` 里的门禁**扫不到我们**，
  所以护栏必须自建；"没被扫到"不等于合规。

## 门禁

- **一条命令、以退出码为准**：`pwsh -File scripts/run-gates.ps1 -Quick`（改动面）或 `-Full`（全量）。
  **不许**靠"我记得跑过哪几条"；测试基线只涨不跌。
- **门禁一次只跑一个**（这条**照旧**）：脚本用锁文件把"并发"变成**当场报错**，而不是靠人记得；
  ⚠ 锁也盖住冒烟本身（`plugin/scripts/smoke-all.mjs`）——复核子代理**绕过 `run-gates.ps1`
  直接跑冒烟**正是上次假红的来源；拿到退出码 3 就是"有人在跑"，**不是**失败。
  ⚠ **更正（复核 2026-09-20 打回）**：这里原写"并发跑会给自己制造假红（`smoke-chatmode` 实测两次
  172/173 都发生在与全量 pytest 并发时）"——**那个因果没有证据，且被本仓自己的记录否证**：
  `plugin/scripts/smoke-chatmode.mjs` 里那条注释自己写着"在**串行链**里偶发过一次变红，
  **单独跑 / 在高负载下并发跑都复现不出来**"。能站住的只有：① 该次失败是 `persisted=false`
  （**写盘失败**，不是复活逻辑错）；② 一次跑一个**仍然**是纪律（省得把"偶发"和"并发"混成一锅）。
  ⚠ 复核还抓到：我引的那句注释**行号写错了**（`AGENTS.md` 里曾写 `:527`，而 `:527` 恰是复核实测
  变红的那条断言；注释本体在别处）⇒ **引用漂移的行号是坏习惯**，此后一律引"文件 + 可搜的原文"。
- **只为被触碰的面跑最小证据**（官方 `dsh-pre-push-checks` 口径）；全量留给 `-Full` 与收工前。

## 复核

- **每个特性/修复派独立 verifier**，并给它的任务书**冻结区间**：先 `git tag verify-freeze-<批次>`，
  再用 `git rev-list --count <base>..<frozen>` **数出**提交条数写进任务书（不凭印象）。
- verifier **必须在冻结提交的提取树上验**（`git worktree add`/`git archive`），并在报告首尾各记一次
  `git rev-parse HEAD` + `git status --short`。**"边改边验"是双向污染。**
- ⚠ **提取树里装依赖必须"真拷贝"，别用 junction/符号链接**（复核实测两次，2026-09-20 定成协议）：
  esbuild 会把**经 junction 解析**的依赖打成**绝对路径**写进产物（`D:/.../plugin/node_modules/...`，
  而交付件里是 `node_modules/...`）⇒ `smoke-client-entry` 的"交付产物 ↔ 从源码现构建**整份一致**"
  断言**假红**，看上去像"忘了 `build:client`"（实测恰好差 30 字符）。真拷贝 `plugin/node_modules`（~88MB）
  后全绿。**这条假红会指向一个不存在的罪**，所以写进协议。
  ⚠ **补（复核 `verify-freeze-5j`，2026-09-20）：要真拷贝的是两份 —— `plugin/node_modules` 与
  **仓库根那份 `node_modules`****。只拷前者时 `smoke-build-purity` 的 R7/R8 会红在
  `Could not resolve ...\node_modules\react`；复核在**父提交**上跑同一脚本红得一模一样 ⇒ 那是**提取树
  环境假红**，不是被验批次的罪。协议原文只写了 `plugin/node_modules`，漏了根那份。
- ⚠ **变异"还原了没有"用 `git status --short` 判，别用文件哈希**（5j-补，2026-09-20 实测）：
  本机 `core.autocrlf=true`，`git checkout` 把源码物化成 CRLF 而工作区原来是 LF（git 两边都报"干净"）
  ⇒ **同内容的两种行尾哈希不同**，拿哈希比对会把"已还原"误读成"没还原"，或反过来。
  同理 `plugin/client.js` 的"磁盘字节数"会在 CRLF（1,535,332）与 LF（1,497,400 = 提交 blob）间变，
  那不是产物差异（`smoke-client-entry` 的整份一致断言两种形态都过）。
- ⚠ **门禁链从 5j-补（2026-09-20）起需要本机有 Chromium/Edge**：`smoke-all.mjs` 名单里现在有两套
  要真浏览器的脚本（`smoke-kb-pad-pixels`、`smoke-kb-cols`），没浏览器就是**红、不是跳过**。
  提取树里跑门禁前先确认 `msedge.exe`/`chrome.exe` 在（本机命中的是 Edge）。
- **复核自己造的变异必须在跑门禁前还原**：变异（例如往 `package.json` 的 `dsh.client.inject` 加一个
  假模块）与门禁并发时，同样会让上面那条整份一致断言红（复核第一遍 `-Full` 的 smoke 红就是这么来的，
  第二遍同代码全绿）。
- **复核打回的说法必须就地更正并留痕**（含我自己写错的）：在文档里保留"错话 + 更正"，
  **不许悄悄删掉**。本仓已发生多次（默认导出、peer、热重载、reflect 500 根因）。

## 诚实

- **假绿判 failed；未做的写"明确未做"；能力宣称挂真机证据。**
- **不许超出证据**：字段描述 ≠ 运行时语义（reflect 那次就是照 OpenAPI 的描述当根因，被复核推翻）；
  抽样验证要写明"这是抽样，不是全部"。
- **转述的数字要回原始来源核**（`git ls-files` / 实测），别抄二手结论。

## 搬运与记录

- **长文档一律字节级搬运**（脚本 + HTTP API），**不许手抄**：手抄实测 77 行错 2 处（2.6% 失真）。
- **一个事实一个归属层**：详细记录写进它的归属文档，别处只链接。当前归属：
  做过什么 → [开发史](docs/DEVELOPMENT-HISTORY.md)｜巡检方案与轮次台账 → [渠道覆盖方案](docs/CHANNEL-COVERAGE-PLAN.md)｜
  交互设计 → [交互设计](docs/INTERACTION-DESIGN.md)｜DSH 研究 → [dsh-official](docs/research/dsh-official/README.md)。
- **每轮 = 小提交 + 快照**：`& .\scripts\snapshot-project.ps1 -Label <短名>`；提交消息写清
  "改了什么 / 为什么 / 边界"。跨轮次的额外发现**只登记**，不在当轮顺手实施。

## 环境

- **绝不动系统层**：不写注册表、不改全局环境变量、不用 `--global` git 配置。
- **数据与代码分离**：运行产物写数据区（`%APPDATA%`），代码树零运行产物。
- **上下文预算**：唯一真源 + 一份文件一个主题 + 子代理写盘而父代理只读 ≤30 行摘要 +
  机器可读中间产物（读 JSON，不读散文）。
