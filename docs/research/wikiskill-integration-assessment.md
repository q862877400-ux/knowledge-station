# WikiSkill（arXiv 2608.27454）融合评估

> **评估对象**：Google Research + Virginia Tech 的 *WikiSkill: Compiling Agent Experience into
> Persistent Knowledge for Skill Evolution*（arXiv:2608.27454，v1 2026-08-27）。
> **评估问题**：这篇论文里哪些东西值得我们这个仓借鉴、哪些不能借鉴、要花多少、风险在哪。
> **评估人**：DSH 会话（`coding-agent::zcode`），2026-09-26。
> **性质**：本文是**评估**，不是方案；不动代码、不改判据。
>
> **纪律**：① 论文是二手（微信公众号转述），**所有数字回一手 PDF 逐字核过**；② 每条结论标证据层级
> （`一手论文` / `论文自报` / `本文推断`）；③ 没核到的逐条列出；④ **没有代码可抄**（见 §8），
> 所以本文不涉"抄许可证"问题。

---

## §0 一页结论

**一句话**：它给的是**结构**（不可变原始层 + 一个有名字的中间整理者 + 每条判据指回它生成的那次事故），
**不是算法**；而且它**自己承认缺少最关键的那一步——清理**。

| 问 | 答 |
|---|---|
| 值不值得投入？ | **值得投入"很小的一件事"**（给解析判据补一条指回事故的边），**不值得**照搬整套三层 |
| 最大的价值 | 它的 `PURPOSE.md` 正好补我们**已经付过学费但没留下结构**的那个缺口 |
| 最大的陷阱 | **它的 Wiki 层没有自动清理机制**（论文 Limitations 第三条自认）⇒ 照搬结构会复现"越记越脏" |
| 最反直觉的一条 | **WikiSkill 式的接受门会杀掉我们最好的规矩**（§7） |
| 建议动作 | 只做 §6 的 G1（一条边，先只覆盖乱码判定），其余**只登记不做** |

---

## §1 一手核验记录（不转述那篇公众号文章）

### 1.1 抓取链（含踩到的坑）

| 步骤 | 结果 |
|---|---|
| 业主给的链接 | `https://mp.weixin.qq.com/s/rmS1mtEBMdb_png2Nvddvg` |
| 微信公众号文章标题 | **谷歌重磅发布WikiSkill，技能可以自己进化了！**（栏目：Datawhale干货） |
| ① Jina Reader（`r.jina.ai`） | ❌ **失败**：返回 311 字节，内容是「**环境异常**／完成验证后即可继续访问」⇒ 微信验证码 |
| ② 直连 + 浏览器 UA | ✅ 成功，**3,726,966 字节**，`<title>` 为空但 `id="js_content"` 正文容器存在（微信惯例：标题由 JS 填） |
| ③ 抽正文 | 自写脚本（`var/tmp/study/wx-extract.py`）**2322 字** |
| ④ 文章给的论文链接 | `https://arxiv.org/abs/2608.27454` |
| ⑤ arXiv 官方 API 逐字标题 | **WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution** |
| ⑥ PDF | **1,177,706 字节**，magic `%PDF-`，**28 页**，pymupdf 抽出 **87,441 字符**（存 `var/tmp/study/memory/raw/papers/wikiskill.txt`） |
| ⑦ SHA-256 前 16 位 | `65AFC6E12F6F7074` |

⚠ **这一节本身就是"HTTP 200 ≠ 抓对了"的实例**：Jina Reader 那次返回 HTTP 200、正文长度看着正常，
内容却是验证码页。**判据是逐字核标题 + 核正文容器，不是看状态码。**

### 1.2 那篇文章转述得准不准

**逐条核过，结论：忠实。** 文章给的九个数字**全部**能在论文正文逐字命中：

| 文章说法 | 论文原文（`一手论文`） |
|---|---|
| Qwen 4B/9B/27B 分别 +12.3 / +17.5 / +23.9 | "Within the Qwen family, WikiSkill improves average performance by 12.3%, 17.5%, and 23.9% for 4B, 9B, and 27B models, respectively" |
| 9B 加技能 47.4% > 27B 无技能 39.4% | "Qwen-3.5-9B with WikiSkill outperforms Qwen-3.6-27B without skills (47.4% vs. 39.4%)" |
| 跨家族迁移 70.2% vs 自进化 63.4% | "Qwen-3.5-9B reaches 70.2% with a Qwen-3.6-27B-evolved skill, compared with 63.4% using its own skill" |
| 去掉 wiki 从 63.7% 掉到 48.7% | "providing the Skill Proposer with access to the persistent wiki increases average benchmark performance from 48.7% to 63.7% (+15.0%)" |
| 三层命名（Raw/Wiki/Skills） | 与 §3.1 逐字一致 |
| 每技能两个文件 `SKILL.md` + `PURPOSE.md` | 与 §3.1 逐字一致 |
| wiki 含 `patterns/` + `logs.md` + `skill-impact.md` | 与 §3.1 逐字一致 |
| "训练时不能访问 Wiki" | 与 §3.2 逐字一致，且**论文说得更重**（见 §3.4） |

⚠ 但文章**漏了一条**对我们最要命的：**论文 Limitations 明说它没有 wiki 清理机制**。文章末尾只说
"让知识持续积累"，没提这件事。⇒ **转述可以核数字，但结构性的"作者自认缺陷"最容易被转述抹掉。**

### 1.3 论文元数据

| 项 | 值 |
|---|---|
| 作者 | Liyan Tang、Cyrus Rashtchian、Chun-Sung Ferng、Andrew Tomkins、Da-Cheng Juan、Tu Vu |
| 机构 | Google Research、Virginia Tech |
| v1 | 2026-08-27 |
| feed 里的 updated | 2026-09-28 ⚠ 与本机时钟不一致，**未究**（可能是我这边时钟偏差） |
| arXiv license 字段 | **feed 未给**（`arxiv:license` 缺失） |
| 代码 | **全文无仓库链接**（只有一个参考文献里的 Karpathy gist）⇒ **没有代码可抄** |
| AI 披露 | 原文："Large language models and coding agents are used to aid with and polish writing and generate some tables and plots." |

---

## §2 论文的三层架构（逐条，带原文）

| 层 | 存什么 | 原文关键句 |
|---|---|---|
| **Raw Layer**（`raw/`） | 每轮的执行轨迹：完整推理、工具调用、输出 | "these traces capture the agent's complete step-by-step interactions... **To preserve the raw history, this layer is immutable**" |
| **Wiki Layer**（`wiki/`） | `patterns/`（**一个模式一个 md**，记具体失败模式或成功策略 + 可操作的绕法）、`logs.md`（进化日志）、`skill-impact.md`（接受历史） | "allow... (1) **observe the complete skill acceptance history so that rejected interventions are not proposed again**, (2) track what was proposed... and whether those proposals succeeded, and (3) identify which errors recur" |
| **Skills Layer**（`skills/`） | `SKILL.md`（技能正文）+ **`PURPOSE.md`**（把技能**映射回促成它的 wiki patterns**） | "`PURPOSE.md`, which **maps the skill back to the motivating Wiki patterns** that inspired its creation or modification" |

**两处关键设计**（`一手论文`）：

1. **Wiki 永不回滚**："the wiki **is never rolled back** regardless of the acceptance decision; accumulated
   patterns and logs persist across all iterations"。
2. **知识与技能分离**：wiki 回答"我们知道什么"，skill 回答"我们该怎么做"。

---

## §3 循环与机制（可借的零件在这一节）

### 3.1 四步循环

1. **Inference Agent**：用当前技能集合跑 rollout，产出轨迹到 `raw/`。
2. **Wiki Maintainer**：对失败轨迹做根因分析、从成功轨迹抽有效策略，**增量补丁式**改 `patterns/`，
   同步改 `index.md` 目录，追加 `logs.md`。
3. **Skill Proposer**：ReAct 多轮，起手只给 `index.md` + `skill-impact.md` + 一份通过/失败摘要，
   **按需 `read_file` 打开具体 pattern 页和轨迹**；每轮只提**一个原子提案**（新建或改一个技能）。
4. **Gating & Rollback**：验证集打分，按判据接受或回滚。

### 3.2 接受判据（**跑一个历史最大值**）

```
S_k ← S'_k  if R(T_val,k) > R_best
      S_{k-1}  otherwise
```

`R_best` 初始为**空技能集**的基线分，接受后更新为当前分 ⇒ **只升不降**；
`R_best = 1.0` 时**提前终止**。拒绝则丢弃候选、回退到上一个成功配置，**但 wiki 不受影响**。

### 3.3 `skill-impact.md` 记什么（每次验证后由外层 harness 程序化追加）

提案元数据、目标技能名、**unified diff**、验证分 `R(T_val,k)`、最终结论 `Accepted` / `Rejected`。
⇒ **一次改动无论被不被接受，都留下一条"带 diff 的判决"。**

### 3.4 训练期不许看 wiki（论文自述，且做了消融）

> "During the training rollouts, the Inference Agent **is restricted from accessing the Wiki Layer**, as our
> ablation study (§5.1) shows that **allowing wiki access during training negatively affects skill development**."

论文给的解释：推理时同时能看技能和 wiki，"some task-solving knowledge may be obtained directly from the
wiki rather than the skills, which can make the resulting trajectories **less informative** for skill development"。

### 3.5 两个可直接借的**具体参数**

| 参数 | 值 | 出处 |
|---|---|---|
| Wiki Maintainer 每轮采样轨迹数 | **≤8 条**（≤5 失败做根因 + ≤3 成功抽策略、防回归） | 附录 C |
| 单条执行日志注入上限 | **15,000 字符** | 附录 C |

---

## §4 实验与数字（全部 `一手论文`，我逐字核过）

| 项 | 值 |
|---|---|
| 基准 | 5 个：LiveMath（数学推理）、SealQA（网络检索）、SpreadsheetBench、OfficeQA（长上下文文档问答）、ALFWorld（具身交互） |
| 模型 | Gemini-3.5-Flash（闭源）、Qwen-3.5-4B/9B-Instruct、Qwen-3.6-27B、Gemma-4-31B-It（vLLM 部署） |
| 对比方法 | Trace2Skill、EvoSkill、SkillOpt（三个技能进化基线）+ 无技能基线。**故意不与通用提示词优化器（如 GEPA）比** |
| 统计口径 | **每个方法独立跑 3 轮取均值**；配对 bootstrap **1000 次**、**p<0.05**；分不出显著差异时并列"统计平局"，**不宣布唯一最优** |
| 相对最强基线 | +3.3 / +5.1 / +10.0 / +5.8 / +12.0 分（4B/9B/27B/Gemma/Gemini） |
| 消融（论文自己的措辞） | 给 Proposer 开 wiki：48.7% → **63.7%（+15.0）**；在此基础上再给推理方开 wiki：63.7% → **60.9%**（**LiveMath** 72.6 → 64.8） |
| 技能长度 | Qwen 系 118.9–128.6 行；Gemma-4-31B **45.1** 行；Gemini-3.5-Flash **81.2** 行 |
| **wiki pattern 数量** | **6.3–8.9 个**（各模型平均） |
| 边界情况（作者自报） | Gemini-3.5-Flash 在 ALFWorld 上进化前验证集已 100% ⇒ 所有方法都等于无技能基线 85.9%，标 `−` 不参与迁移 |

---

## §5 与我们的映射（三层各对应什么）

| 论文层 | 我们这一侧的对应物 | 状态 |
|---|---|---|
| Raw Layer（不可变原始轨迹） | **MinerU 解析产物 + 库里的条款原文与坐标** | 🟢 **已有且成熟**（详见 `docs/ENCYCLOPEDIA.md` 解析段） |
| Raw Layer 的"不可变"要求 | 我们的**锚点纪律**：「锚点会失效：材料区间是解析结果的坐标 ⇒ 换解析器或源文件被替换都可能让它失效」 | 🟢 **已有，但是当成 bug 逐个修的，没有升成原则** |
| Wiki Layer（模式页 + 进化日志 + 接受台账） | `docs/NOT-DOING.md`（已否决台账）+ `docs/TEST-FLAKES.md`（已知竞态）+ `docs/DEVELOPMENT-HISTORY.md`（取证）+ `AGENTS.md` 里的纪律条目 | 🟡 **有，但散在四处、没有统一入口、没有"一个模式一页"的粒度** |
| Skills Layer + `PURPOSE.md` | 我们没有 `PURPOSE.md` 形态的东西 | 🔴 **缺**（这就是 §6 的 G1） |
| 接受门（跑历史最大值） | `scripts/gates-baseline.json`（计数只涨不跌）+ `eval/baseline.json`（golden 逐指标回退 ≤2pp） | 🟡 **有两个棘轮，但都不是"跑最大值 + 显著性检验"**（§6 的 G3） |
| 训练期不许看 wiki | 我们的 `eval/golden/golden.json`（96 题）在仓内可读 | 🟡 **风险存在，但我没有证据表明已经污染**（§6 的 G4） |

---

## §6 缺口清单（每条含"缺的那条边"具体在哪）

| # | 缺口 | 证据 | 代价 |
|---|---|---|---|
| **G1** | **每条解析判据没有指回"它是哪次事故生成的"这条边** | P0.11（判据四把非中文文档判成乱码）是目前**唯一一条证据链完整**的解析判据事故：根因、修法、复核结论都在长周期计划里，但**全在计划文档里，`mineru_adapter.py` 的判据旁边什么都没有** | 小：只给判据加一行指针 + 一个模式页文件 |
| **G2** | **没有任何清理机制** | 论文 Limitations 第三条自认："WikiSkill currently **lacks an automated mechanism to prune the wiki**. Such pruning may become necessary as knowledge accumulates"；它能不做清理是因为 pattern 只有 **6.3–8.9 个**，而我们纪律条目已 **42 条 / 188 行**（`本文实测`） | 中：需要先定"什么算过期" |
| **G3** | **结果棘轮没有显著性检验** | 论文用 1000 次配对 bootstrap、p<0.05、分不出显著差异就并列；我们的 golden 门是**绝对阈值 2pp**，分不出 2pp 是噪声还是退化 | 大：要重做基线统计，属于必验五类之 ① |
| **G4** | **"我在这个尺子上调过参"的风险没有被任何机制挡住** | 论文明确禁止推理期看 wiki（且有消融证明有害）；我们的 `eval/golden/golden.json` 96 题在仓内、任何会话都能读 | 小：加一条纪律（调参前不看 golden），但**需要人自觉，无机械强制** |

---

## §7 一条反直觉但重要的结论

**WikiSkill 式的接受门会杀掉我们最好的规矩。**

论文 Limitations 第二条自认：接受判据要求"**每个被接受的提案必须提升验证分**"，这
"**excludes neutral proposals that preserve immediate performance but could enable gains in subsequent
iterations**"（排除了"当下不涨、但为后续铺路"的提案）。

**而我们纪律里最值钱的那几条，绝大多数正是 neutral 的**：

- 「引用漂移的行号是坏习惯」——不改变任何分数，只在**没人见过的场景**里防错；
- 「SKIP 不等于通过」——不改变分数，只在**门禁被绕过时**生效；
- 「先证明命令真的走到了被测路径」（空闸门）——只在**测试有 bug 时**才产生差别。

**它们的价值全部落在"没有分数"的地方。** 任何"必须有结果提升才准进"的门，都会把它们判成无用而删掉。

⇒ 这条既说明**不能照搬它的门**，也说明**我们缺的不是门，是"怎么给 neutral 的东西判账"的办法**。
论文没解决这个（它自己承认了），所以**别指望从它那儿抄到答案**。

---

## §8 能借的 / 不能借的

### ✅ 能借（结构，不是算法）

| # | 借什么 | 落到我们哪 | 引用出处 |
|---|---|---|---|
| B1 | **`PURPOSE.md` 形态的"指回边"**：每条判据旁边写清它是哪次事故生成的 | 解析判据（先只做乱码判定那一条） | §3.1 原文 |
| B2 | **一次改动无论接受与否都留"带 diff 的判决"** | 我们只有提交消息，没有台账 | §3.3 原文 |
| B3 | **整理者每轮的输入预算**（≤8 条轨迹、单条 ≤15k 字符） | 任何"读一批原始记录做归因"的步骤都该有上限 | 附录 C |
| B4 | **"不可变原始层"升成原则** | 换解析器/换源文件 ⇒ 引用坐标全变，应当有**主动巡检**而不是等用户发现 | §2 原文 + 我们锚点纪律 |

### ❌ 不能借

| # | 为什么不能 | 依据 |
|---|---|---|
| N1 | **它的 Wiki 没有清理机制**，照搬会复现"越记越脏" | Limitations 第三条自认（§6 G2） |
| N2 | **它的接受门会杀掉 neutral 规矩** | Limitations 第二条自认（§7） |
| N3 | **它完全没测"技能怎么被找到"**——技能全量注入提示词，作者明说这是为了**排除触发/检索的干扰**，因此"不评估技能检索与触发，而这在技能变多时变得重要" | Limitations 第一条自认 |
| N4 | **收益幅度对我们不成立**：+15.0pp 是**有自动打分器的任务基准**上量的；我们的解析层**没有自动打分器** | `本文推断`：无度量即无预期 |

---

## §9 一个必须说清的规模事实

**别把这篇论文当"知识层无限增长"的解药。**

| | 论文的 wiki | 我们的纪律层 |
|---|---|---|
| 条目数 | **6.3–8.9 个 pattern**（论文 Table 4） | **42 条顶层条目 / 188 行**（本文实测） |
| 有清理机制吗 | **没有，作者自认** | 没有 |
| 增长比例 | — | 21 次改动累计 **新增 197 行 / 删除 9 行**（≈21.9:1，本文实测） |

**论文从来没有走到"长到需要清理"的位置。** 所以它能证明的是"结构有用"，
**证明不了"结构能撑住长期增长"**。这两件事差得很远。

---

## §10 我没核到的（如实）

1. §1.2 Introduction 与 §5.3 案例**未逐字读完**（只读了方法、实验设置、主结果表、消融、Limitations、统计附录）。
2. **附录 A 的算法伪码未逐行核**。
3. 五个基准各自的**数据量**（题目数、会话数）未核。
4. arXiv feed 的 `updated: 2026-09-28` 与本机时钟不一致，**未究**。
5. 那篇公众号文章我**只核了它转述的数字与结构描述**，有没有别的遗漏未穷尽。
6. 论文的复现性未评估（**没有代码**；是否有第三方复现未查）。
7. `eval/golden/golden.json` 是否**真的**在历史上被用于调参 ⇒ **未核**，我只核了它在仓内可读。

---

## §11 出处

| 项 | 位置 |
|---|---|
| 论文 PDF（一手） | `var/tmp/study/memory/raw/papers/wikiskill.2608.27454.pdf`（1,177,706 B，SHA-256 前 16 位 `65AFC6E12F6F7074`） |
| 抽取文本 | `var/tmp/study/memory/raw/papers/wikiskill.txt`（87,441 字符 / 28 页） |
| arXiv 元数据 | `var/tmp/study/memory/raw/arxiv-2608.27454.xml`（官方 API 逐字标题与作者） |
| 公众号原文抓取件 | `%TEMP%/wx-article.html`（3,726,966 B，**未入库**） |
| 正文抽取脚本 | `var/tmp/study/wx-extract.py` |
| arXiv 页面 | https://arxiv.org/abs/2608.27454 |
| 本仓相关归属层 | 解析管线 → `docs/ENCYCLOPEDIA.md`；已否决 → `docs/NOT-DOING.md`；棘轮与门禁 → `scripts/gates-baseline.json` / `eval/baseline.json` / `tests/test_golden_gate.py`；长周期计划 → `docs/RETRIEVAL-LONG-RANGE-PLAN.md` |

---

## §12 2026-09-28 增补：把同族四篇与真实仓库一起核进来之后

> 本节是**同族横向核验**的结果，证据在 `var/tmp/study/skill-evo/A-repos.md` 与 `B-siblings.md`
> （gitignore 目录，原始件在同目录 `raw/`）。**本节只增补与更正，不推翻上文；上文若有与本节冲突处，以本节为准。**

### 12.1 🔧 更正：§7 那个"别指望从它那儿抄到答案"——**对 WikiSkill 成立，对整个族不成立**

§7 我写的是：论文自认排除 neutral 提案 ⇒ **"我们缺的不是门，是怎么给 neutral 的东西判账的办法；论文没解决，所以别指望从它那儿抄到答案"**。

**这句话的后半句过宽了。** 同族四篇在接受判据上分成两派：

| | 判据（原文/伪码） | 允不允许"不涨但接受" |
|---|---|---|
| WikiSkill | `R(T_val,k) > R_best`（比**历史最好**，平局拒） | ❌ |
| SkillOpt | `score_cand > score_cur`，超参原文 "strictly greater—ties are rejected" | ❌ |
| **EvoSkill** | `\|G\|<k or s̃ > min_{q∈G} SCORE(q)`（**比队尾最弱即可**） | ✅ **四篇中唯一** |
| Trace2Skill | **主流程没有接受门**，只有格式 guardrail | — |

⇒ **"怎么给不涨分的东西判账"，EvoSkill 用「定容前沿 + 只比最弱」在同族内给了机制**。
**代价也要写清**：这样收下之后**前沿的最优分可能下降**，论文没有讨论这一点。

**更正范围**：§7 的判断**对 WikiSkill 单篇仍然成立**（它确实自认排除 neutral）；被更正的是"这个族没有答案"这半句。

### 12.2 四篇的持久层与裁剪：严格说**一篇都没解决**

| | 持久层 | 裁剪机制 |
|---|---|---|
| WikiSkill | 轨迹 + `wiki/`（patterns / index / logs / skill-impact）+ `skills/` | **无**（作者自曝；同段还有"每轮 pattern 数量无硬上限"） |
| SkillOpt | **只有一个 `best_skill.md`** | 无 wiki、无技能库 |
| EvoSkill | git 分支技能夹 + **定容前沿 K=3** + 累计反馈历史 H | **只淘汰候选池**（未入围分支删除，原文明写 "to prevent repository bloat"）；**真正线性增长的 H 无界** |
| Trace2Skill | 单个技能目录 `S=(SKILL.md, references/)` | **连承认都没有** |

**SkillOpt 的"每步编辑条数上限"（默认 4、余弦衰减到 2）是变化率不是总量**——每步都涨分就能一直长，
论文自报最终增长 **×2.5 到 ×53**；它的真实对策是**从设计上回避**，Limitations 逐字
"intentionally optimizes a single portable skill rather than growing a large skill library"。

**共同根因（四篇一致）**：**没有一篇跑到会显形的规模。** 最长演化 = WikiSkill 8 轮 / EvoSkill 约 5–11 轮 /
SkillOpt 4 个 epoch / Trace2Skill 单趟；持久层最终都停在**个位数到十几条**。
**这是"没碰到"，不是"解决了"。** ⇒ §9 那个对比（论文 6.3–8.9 vs 我们 42 条）由此**加强而非削弱**。

### 12.3 拒绝留痕的强弱（这是 §6 G2 的现成参照）

**WikiSkill 最强**（`skill-impact.md` 永久累积，含 **unified diff + 验证分 + Accepted/Rejected**）
＞ EvoSkill（H 永久但无界，有分数与判决、**无 diff**）
＞ SkillOpt（rejected-edit buffer **每 epoch 重置**，不是永久台账）
＞ Trace2Skill（无）。

⚠ **四篇都没有在接受门上做显著性检验。** WikiSkill 的配对 bootstrap 只用于报表排名；
EvoSkill 自曝 "single run… Variance analysis left to future work"。
⇒ 对照本仓：`tests/test_golden_gate.py` 的 ≤2pp 是**绝对阈值**，同样**无显著性检验**（§6 G3 成立）。

### 12.4 一条反直觉的发现（可能比上面所有结论都值钱）

Trace2Skill §C.2 是四篇中**唯一**给出"知识会变脏"实证的地方（且测的是**补丁池**、不是知识层，
只在选择性补丁实验里）：**323 条补丁里 4 个主题被反复引用（55.1% / 54.8% / 42.7% / 16.4%），贪心选十轮仍回到同几个主题**；
单步内 **57 个 fail-to-pass 对 21 个 pass-to-fail**。

它的结论与"脏了就删"**相反**：**全量整合 > 贪心选择**；低支持内容"**不丢弃，而是归入 13 个补充参考文件**"。

⚠ **四篇没有任何一篇报告过垃圾率 / 陈旧率 / 冲突率 / 失效条目比例。**
⇒ 与 [记忆系统调研](agent-memory-systems.md) §3.3 互补：那批文献**测了脏率**（mem0 生产库 10,134 条里 97.8% 不可用），
这批文献**测了涨分**。**"脏了之后该怎么办"这个问题，两批文献合起来仍然没有答案。**

### 12.5 🔴 真实仓库与许可：**"抄"这件事在多数情况下不成立**

8 个官方仓（代码用 `git/trees` 逐个点算，非看 README 长度；数值核到 2026-09-28）：

| 仓 | ★ | 根 LICENSE 原文 | API 字段 |
|---|---|---|---|
| `microsoft/SkillOpt` | 17,698 | **MIT** | MIT ✅ |
| `benchflow-ai/skillsbench` | 1,818 | Apache-2.0 | Apache-2.0 ✅ |
| `stanford-iris-lab/meta-harness` | 1,621 | **MIT** | MIT ✅ |
| `sentient-agi/EvoSkill` | 1,230 | Apache-2.0 | Apache-2.0 ✅ |
| `Darwin-Agent/HarnessX` | 479 | **MIT** | MIT ✅ |
| `Qwen-Applications/Trace2Skill` | 295 | 🔴 **无 LICENSE 文件** | 空 |
| `shiqichen17/SkillCraft` | 106 | 🔴 **无 LICENSE 文件** | 空 |
| `ThakiCloud/SKILLRET` | 26 | 🔴 **无 LICENSE 文件** | 空 |

**三条许可事实（我逐条独立复核过）**：

1. **🔴🔴 Trace2Skill 发布的 4 套最优技能资产不是自由资产。** `released_skills/*/LICENSE.txt` 原文（我读出全文，1466 字节）：
   `© 2025 Anthropic, PBC. All rights reserved.`，且明文 **禁止** 提取/留存副本、**禁止复制**、
   **禁止制作衍生作品**、**禁止分发或转授权**、**禁止逆向**。
   ⇒ **论文最值得抄的那批结果，恰恰是最不能抄的。**
2. **🔴 徽章不构成授权。** Trace2Skill 与 SKILLRET 的 README 都挂 Apache-2.0 徽章，
   **而根目录没有 LICENSE 文件**；SKILLRET 的徽章还相对链接到一个 **404 的 LICENSE**。法律上等同"保留所有权利"。
3. **API 字段两个方向都会骗人。** 反例：`Tencent/SkillHone` API 报 `NOASSERTION`，
   而 LICENSE 原文逐字是 MIT（1,429 字节，非标准抬头导致识别失败）。
   ⚠ 另一处易混：SKILLRET 的 **GitHub 仓无许可**，但其 **HuggingFace 数据集与 embedding/reranker 权重是 apache-2.0**
   ——**三者法律状态不同，不能混说**。

**另外两条**：
- **WikiSkill（2608.27454）没有官方仓库** —— `google-research` 组织下一个都没有，搜到的全是第三方复现
  （4 个 MIT，star 251 / 38 / 5 / 2）。**论文开源了，代码没开源。**
- **8 个仓对"文档知识库 + 技能"的直接支持 = 基本为零。** 路径级扫描：Trace2Skill / EvoSkill / meta-harness 命中 **0**；
  README 里搜 knowledge base / 知识库 **0 次实质命中**；所有 "rag" 命中都是子串误配（`Ave-rag-e`、`del-e-rag-e`）。
  HarnessX 的 `memory_retrieval.py` 最接近，但那是**agent 对话记忆，不是文档库**。
  **概念上唯一对得上的就是 WikiSkill，而它没开源。**

### 12.6 本节自身的证据边界

- WikiSkill 的 **8 轮演化**是**推断**（据附录 Table 5 把接受更新分成 0–1 / 2–4 / 5–7 三组），**正文没有直写**。
- **SkillOpt 正文那句 "±2.7 points" 与它自己 Table 3 的实际差值（1.6 / 4.6 / 2.4）对不上**，口径不明 ⇒ 引用应直接引表里的数。
- **EvoSkill 全文零次出现 "limitation"**，没有 Limitations 章节 ⇒ 四篇里自省最少。
- 各仓的 CI/测试**是否真跑未核**（只读文件树，**未 clone、未执行**）；国内可访问性、issue 与弃坑情况**未核**。

> 本文**只登记，不改任何代码或判据**。§6 的四条缺口**均未实施**；是否实施由业主决定。
> 同族与仓库层面的完整证据见 `var/tmp/study/skill-evo/A-repos.md`、`B-siblings.md`（gitignore 目录）。
