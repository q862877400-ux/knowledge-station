# Agent「技能 / 知识」三层结构 —— 四路调研参考材料

> **性质**：**参考材料**。业主 2026-09-28 明确「只做调研给我参考」⇒ 本文**不推方案、不劝采纳、不排优先级**。
> **触发**：业主提出「做一个介于 RAG 知识库与记忆之间的东西，让 agent 记忆扩到百万/千万条」，
> 并追问「这种把知识库和 skill 统一管理的结构我们现在没有，真的没有价值吗」。
> **范围**：`A` 开源仓库与许可 ｜ `B` 同族四篇横向 ｜ `C` 优化整个运行壳那条线 ｜ `D` 溯源边与规则治理（**待回**）。
> **纪律**：① 数字分「我一手核过」与「子代理核过」两级；② 论文与仓库的**自相矛盾处照实列出**；
> ③ **负结论标明检索边界**（"在我核过的 N 篇候选内没找到" ≠ "不存在"）；④ 长件只落 `var/tmp/`（gitignore），仓内只留这份摘要。

---

## §0 一页速查

| 业主的问题 | 答案 | 在哪节 |
|---|---|---|
| 这个结构长什么样？ | 三层：**不可变原始层 / 持续积累的知识层 / 可执行技能层**，知识与技能**分开但用一条溯源边连起来** | §2 |
| 我们有这个结构吗？ | **没有。** 但**症状已全部出现**，且规模比论文大一个量级（我们 55 份技能 / 论文 6.3–8.9 个知识页） | §1 |
| 真的没有价值吗？ | 我上一份评估**答偏了**（把流程问题当主答案、漏了架构那半），其中一条判断**过宽**，已更正 | §6 |
| 能抄吗？ | **多数不能。** 概念上唯一对得上的那篇**没有官方代码**；最值得抄的资产**许可禁止复制** | §3 |
| 有没有场景对得上的先例？ | **有一半。** 裂成两半：一半有我们的场景但无优化，一半有优化但无我们的场景 | §5 |
| "知识层长起来会失控"有人解决过吗？ | **四篇一篇都没有。** 共同根因：**没一篇跑到会显形的规模** | §2.3 |
| "不涨分的规矩怎么留"有人解决过吗？ | **族内有解**（EvoSkill 定容前沿），我上一份说"别指望抄到答案"**过宽** | §6.1 |
| 🔧 "什么该过期"是空白吗？ | **不是空白，我说过头了。** 已有命名的失效模式（Library Drift）、棘轮理论、硬阈值与生命周期八阶段。**真正的空白窄得多：LLM 技能之间的语义冲突检测** | §4.5 |
| 溯源边只有 `PURPOSE.md` 一种？ | **不是**，而且文献**一致往"运行时强制"走**；`PURPOSE.md` 是最左端的"纯文档字段"档，**已知会被洗掉** | §4.5 |

---

## §1 我们现在有什么、没有什么（**我一手盘点，可复核**）

### 1.1 技能层：55 份、散三处、无清单

| 位置 | `SKILL.md` 数量（我实测） |
|---|---|
| `~/.agents/skills/` | **8** |
| `~/.dsh/` | **10** |
| DSH 检出目录 | **37** |
| **合计** | **55** |

而每轮注入到会话里的技能清单只有约 20 条 ⇒ **另外 35 份在哪、归谁、是否过期，没有清单可查。**

### 1.2 技能的"身份证"里**没有"为什么存在"这一栏**

我逐个读了 `~/.agents/skills/` 下 8 个技能的 frontmatter 字段：

```
agent-reach / hindsight-memory / hindsight-coding-agent / scent-miner / systematic-debugging
    → name, description
browser4-cli / browser4-plugin / browser4-experience
    → name, title, description, tier
```

**全部只有"叫什么 + 干什么"。** 没有"它是哪次事故生成的""什么时候该被取代""谁有权改"。

⇒ **这正是 `PURPOSE.md` 那一栏。** 而它不是我臆想的抽象问题——**我们这套技能格式里就缺这一栏**，今天在跑的环境里。

### 1.3 已经有一处**活的、自相矛盾的内容**

- 技能文件里硬写：「记忆库 `coding-agent::<项目名>`；**本工作区为 `coding-agent::DSH`**」
- 而本工作区实际是 `D:\AI\work space\zcode`，今天实测记忆库返回 **`coding-agent::zcode`**

⇒ **照字面执行的 agent 会去查错的库。** 这不是过期措辞，是**会改行为的错**。

### 1.4 对照：论文在同一位置上的规模

| | 论文（WikiSkill Table 4） | 我们 |
|---|---|---|
| 知识/技能条目数 | **6.3–8.9 个 pattern** | 技能 **55 份**（散三处）＋纪律 **42 条 / 188 行** |
| 有清理机制吗 | **没有，作者自认** | 没有 |
| 增长比例 | — | 纪律层 21 次改动**新增 197 行 / 删除 9 行**（≈21.9:1，我实测） |

**我们已经在论文"还没走到"的那个位置上，而且症状更全**（无主、无清单、无溯源边、已有矛盾）。

### 1.5 我们**已有**的、这一族没有的东西

| 我们的 | 这一族的情况 |
|---|---|
| 条款级引用（标准号 + 条款号 + 可点原文） | **全部 8 个仓命中 0**（路径级扫描） |
| 效力由发布机关决定（现行/废止/即将实施） | 四篇**均无此维** |
| 材料评审三态硬门（未批准不得进结论） | 只有 Parthenon Law 有等价物（§5） |
| 两个棘轮（计数只涨不跌 + golden 逐指标回退 ≤2pp） | 四篇**均无显著性检验**（§2.4） |

---

## §2 同族四篇：机制、持久层、裁剪、接受门（Track B，子代理核过 + 我复核了 WikiSkill 部分）

### 2.1 四篇的身份

| 简称 | arXiv | 机构 | 官方仓 / ★ / 许可 |
|---|---|---|---|
| **WikiSkill** | 2608.27454 v1 | Google Research + Virginia Tech | 🔴 **无官方仓**（只有 4 个第三方复现，MIT，★251/38/5/2） |
| Trace2Skill | 2603.25158 v5 | Qwen | `Qwen-Applications/Trace2Skill` 295 / 🔴 **无 LICENSE** |
| EvoSkill | 2603.02766 v1 | — | `sentient-agi/EvoSkill` 1,230 / Apache-2.0 |
| SkillOpt | 2605.23904 v2 | Microsoft | `microsoft/SkillOpt` **17,698** / **MIT** |

### 2.2 各自的持久层

| | 持久层是什么 | 裁剪机制 |
|---|---|---|
| WikiSkill | 轨迹 + `wiki/`（`patterns/*.md`、`index.md`、`logs.md`、`skill-impact.md`）+ `skills/`（每技能 `SKILL.md` + **`PURPOSE.md`**） | **无**（作者自曝；同段还有"每轮 pattern 数量无硬上限"） |
| SkillOpt | **只有一个 `best_skill.md` 单文件** | 无 wiki、无技能库 |
| EvoSkill | git 分支技能夹 + **定容前沿 K=3** + 累计反馈历史 H | **只淘汰候选程序池**（未入围分支删除，原文明写 `to prevent repository bloat`）；**真正线性增长的 H 无界** |
| Trace2Skill | 单个技能目录 `S=(SKILL.md, references/)` | **连承认都没有** |

**SkillOpt 的"每步编辑条数上限"（默认 4、余弦衰减到 2）是变化率不是总量**——每步都涨分就能一直长，
论文自报最终增长 **×2.5 到 ×53**。它的真实对策是**从设计上回避**，Limitations 逐字：
`intentionally optimizes a single portable skill rather than growing a large skill library`。

### 2.3 ✅ 确认：**四篇没有一篇解决"长起来会失控"**

**共同根因：没有一篇跑到会显形的规模。** 最长演化 = WikiSkill 8 轮 / EvoSkill 约 5–11 轮 /
SkillOpt 4 个 epoch / Trace2Skill 单趟；持久层最终都停在**个位数到十几条**。

**这是"没碰到"，不是"解决了"。**

### 2.4 接受判据分两派（这一条改变了我上一份的结论）

| | 判据 | 允不允许"不涨但接受" |
|---|---|---|
| WikiSkill | `R(T_val,k) > R_best`（比**历史最好**，平局拒） | ❌ |
| SkillOpt | `score_cand > score_cur`，超参原文 `strictly greater—ties are rejected` | ❌ |
| **EvoSkill** | `\|G\|<k or s̃ > min_{q∈G} SCORE(q)`（**比队尾最弱即可**） | ✅ **四篇中唯一** |
| Trace2Skill | **主流程没有接受门**，只有格式 guardrail | — |

⚠ EvoSkill 这么做之后**前沿的最优分可能下降**，论文没有讨论。

**拒绝留痕强弱**：WikiSkill（永久台账 + **unified diff** + 分数 + 判决）＞ EvoSkill（永久但**无 diff**）＞
SkillOpt（rejected-edit buffer **每 epoch 重置**，不是永久台账）＞ Trace2Skill（无）。

⚠ **四篇都没有在接受门上做显著性检验。** WikiSkill 的配对 bootstrap 只用于报表排名；
EvoSkill 自曝 `single run… Variance analysis left to future work`。

### 2.5 一条**反直觉**的发现（可能比上面所有结论都值钱）

Trace2Skill §C.2 是四篇中**唯一**给出"知识会变脏"实证的地方（测的是**补丁池**、不是知识层，只在选择性补丁实验里）：

- **323 条补丁里 4 个主题被反复引用**（55.1% / 54.8% / 42.7% / 16.4%），**贪心选十轮仍回到同几个主题**；
- 单步内 **57 个 fail-to-pass 对 21 个 pass-to-fail**。

它的结论与"脏了就删"**相反**：**全量整合 > 贪心选择**；低支持内容"**不丢弃，而是归入 13 个补充参考文件**"。

⚠ **四篇没有任何一篇报告过垃圾率 / 陈旧率 / 冲突率 / 失效条目比例。**

⇒ 与 [记忆系统调研](agent-memory-systems.md) §3.3 **互补**：那批文献**测了脏率**
（mem0 生产库 10,134 条里 97.8% 不可用、单条幻觉被复制 668 份），这批文献**测了涨分**。

🔧 **更正（2026-09-28，D 路回后）**：我在这里写过的 **"脏了之后该怎么办，两批文献合起来仍然没有答案"——这句过头了。**
§4.5 列出**已有的**答案：命名的失效模式（library drift）、闭式判据的棘轮、硬阈值、以及把
"repair or prune stale entries" 写进生命周期的八阶段综述。**真正剩下的空白要窄得多**（语义冲突检测）。

---

## §3 真实仓库与许可：**"抄"这件事多数情况下不成立**（Track A，子代理核过 + 我逐条复核）

### 3.1 8 个官方仓

| 仓 | ★ | 根 LICENSE 原文 | API 字段 |
|---|---|---|---|
| `microsoft/SkillOpt` | **17,698** | **MIT** | MIT ✅ |
| `benchflow-ai/skillsbench` | 1,818 | Apache-2.0 | Apache-2.0 ✅ |
| `stanford-iris-lab/meta-harness` | 1,621 | **MIT** | MIT ✅ |
| `sentient-agi/EvoSkill` | 1,230 | Apache-2.0 | Apache-2.0 ✅ |
| `Darwin-Agent/HarnessX` | 479 | **MIT** | MIT ✅ |
| `Qwen-Applications/Trace2Skill` | 295 | 🔴 **无 LICENSE 文件** | 空 |
| `shiqichen17/SkillCraft` | 106 | 🔴 **无 LICENSE 文件** | 空 |
| `ThakiCloud/SKILLRET` | 26 | 🔴 **无 LICENSE 文件** | 空 |

### 3.2 三条许可事实（**我逐条独立复核过**）

1. **🔴🔴 Trace2Skill 发布的 4 套最优技能资产不是自由资产。**
   `released_skills/*/LICENSE.txt` 原文（**我读出全文，1,466 字节**）：
   `© 2025 Anthropic, PBC. All rights reserved.`，且明文**禁止**提取/留存副本、**禁止复制**、
   **禁止制作衍生作品**、**禁止分发或转授权**、**禁止逆向**。
   ⇒ **论文最值得抄的那批结果，恰恰是最不能抄的。**
2. **🔴 徽章不构成授权。** Trace2Skill 与 SKILLRET 的 README 都挂 Apache-2.0 徽章，
   **而根目录没有 LICENSE 文件**；SKILLRET 的徽章还相对链接到一个 **404 的 LICENSE**。法律上等同"保留所有权利"。
3. **API 字段两个方向都会骗人。** 反例：`Tencent/SkillHone` API 报 `NOASSERTION`，
   而 LICENSE 原文逐字是 MIT（1,429 字节，非标准抬头导致识别失败）。
   ⚠ 易混：SKILLRET 的 **GitHub 仓无许可**，但其 **HuggingFace 数据集与 embedding/reranker 权重是 apache-2.0**
   ——**三者法律状态不同，不能混说**。

### 3.3 🔴 对「文档知识库 + 技能」的直接支持：**基本为零**

路径级扫描：Trace2Skill / EvoSkill / meta-harness 命中 **0**；
README 里搜 knowledge base / 知识库 **0 次实质命中**；所有 `rag` 命中都是子串误配
（`Ave-rag-e`、`del-e-rag-e`、`Supe-rag-enticAI`）。
HarnessX 的 `memory_retrieval.py` 最接近，但那是**agent 对话记忆，不是文档库**。

⇒ **概念上唯一对得上的就是 WikiSkill，而它没有官方代码。**

### 3.4 有真许可、能看的资产（**是零件，不是那个结构**）

| 仓 | 里面有什么 |
|---|---|
| `microsoft/SkillOpt` | 训练循环、`best_skill.md` 产物、`skillopt_sleep/`（夜间自进化）、六种 harness 接入壳，**已上 PyPI** |
| `benchflow-ai/skillsbench` | **「任务 + 技能 + 确定性验证器」三件套结构**，731 个 md |
| `stanford-iris-lab/meta-harness` | `ONBOARDING.md` 引导流程 + 参考样例 |
| `sentient-agi/EvoSkill` | CLI + 六种 agent 适配层 |
| `Darwin-Agent/HarnessX` | 九维 processor 流水线 + `memory_retrieval.py` |

---

## §4 另一条线：优化整个运行壳（Track C）

### 4.1 两条路线优化的东西**不重叠**

| | 优化对象 | 动作空间 | 证据支持什么 |
|---|---|---|---|
| **Meta-Harness**（2603.28052，Stanford/MIT，★1,621） | **整段 harness 代码**（单个 100–1000 行 Python 程序，可整文件重写） | 无结构 | "检索程序可被搜出来" |
| **HarnessX**（2606.14249v3，★479） | **类型化配置对象 C=(P,S)**（8 个生命周期钩子上的处理器列表 + 5 个单例槽位） | 有边界（类型系统/单例组互斥约束） | "在可组合壳上反复改提示/工具能涨分，**记忆检索槽位没被真正搜过**" |

### 4.2 记忆/检索在里面的角色——**这是最大差别**

- **Meta-Harness：检索是一等实验对象。** 整节（§4.2）在优化检索，原文
  `allow the retrieval behavior itself to emerge from search`。发现物是**一个四路 BM25 路由器，
  路由谓词、重排项、去重阈值、每路条数全部由外循环在 40 轮里选出**；跨 5 个留出模型 **+4.7 分**。
  ⚠ **但检索栈本身是固定的**（还是 BM25，语料固定 535,356 题）——**它搜的是"怎么用 BM25"**。
- **HarnessX：记忆管理是九个维度之一，且实践中最弱。** 真正 ship 的只有 prompt/tools/config/processor 四桶；
  "检索"表现为"**加一个工具**"（GAIA 第 10 轮加了个 MediaWiki API 工具绕开浏览器，单轮 +4.9pp）。
  ⇒ **没有一个结果来自"记忆/检索策略被优化"。**

### 4.3 顺带回答"省上下文 ≠ 变聪明"

Meta-Harness 有干净的**同预算对照**：

| | 上下文 | 成绩 |
|---|---|---|
| Few-Shot（全给） | 12.3K | 40.8 |
| Meta-Harness | 11.4K | **48.6** |
| Meta-Harness 最低上下文端点 | **5.4K** | 40.1（**打不过对照基线的 40.9**） |

⇒ **同等上下文下 +7.8，增益主体不是"少给东西"；但一味压到最低反而输。**
⚠ HarnessX 这题**无法回答**——主表没有 token 列，且 ALFWorld 那档 +44% 恰恰是在上下文**增加 60%** 时拿到的。

### 4.4 Karpathy 那个 gist 里的 `Lint`

`gist.github.com/karpathy/442a6bf5…`（文件名 `llm-wiki.md`）。三层：
**raw sources**（不可变，事实源）/ **wiki**（模型全权维护，`You read it; the LLM writes it`）/
**schema**（AGENTS.md 或 CLAUDE.md 那种文件，**你与模型共同演化**）。三个操作：
**Ingest**（一份源可能触及 10–15 个页面）/ **Query**（先读 `index.md` 再钻取，好答案回填成新页）/
**Lint** ← **查页面之间的矛盾、"被新源取代的过时声明"、孤儿页、缺失的交叉引用**。

**`Lint` 正好是"什么该过期"那个所有人都在绕的问题的一个具体答案**——而 §2 的四篇没有一篇报告过脏率。

⚠ **但它有一道最硬的墙**（原文逐字）：
`This works surprisingly well at moderate scale (~100 sources, ~hundreds of pages) and avoids the need for embedding-based RAG infrastructure.`
**比我们低三个数量级。** 且它的硬约束一条都没覆盖：可点原文出处、效力状态、审批门（**全文零处**）、规模。

**关系上有个值得注意的点**：**只有 WikiSkill 引用它**，Meta-Harness 与 HarnessX 都没引。
而 Meta-Harness 附录 D 自认"**改技能文本比改迭代次数或种群规模对检索质量的影响更大**"——
gist 把那个文件抽出来当整个方案的核心。**方向相反**：gist 往 wiki 里写，论文把 harness 本身改掉。

---

## §4.5 溯源边与"什么该过期"（Track D）

### 4.5.1 溯源边不是只有 `PURPOSE.md` 一种，**而且文献一致往"运行时强制"走**

`PURPOSE.md` 是**最左端的"纯文档字段"那一档**。往右是逐步强化的形态：

| 形态 | 出处 | 关键原文/要点 |
|---|---|---|
| 每条记忆必带 origin/timestamp/evidence pointer + **citation lock**（只许引真读过的证据） | 2608.29606 Agent Zero Memory | 运行时锁 |
| typed 执行图（agents/sources/memories/claims/actions） | 2608.10509 MAP-Graph | **"provenance 是运行时控制信号，不只是事后审计元数据"** |
| 🔴 **边会被"洗掉"** | **2607.29167 Memory Provenance Laundering** | **不强制就会在记忆整合时失效**——对"只在文档里写个字段"这条路线是最重要的警告 |
| 扩展 **W3C PROV + MCP**（唯一走国际标准的） | 2508.02866 PROV-AGENT | 标准件 |
| 技能的三条 trace（Expression / Implementation / Operational SOG） | 2608.05204 SkillTrace | 最贴近 `PURPOSE.md` 的工业化版 |
| **"把证据与治理规则分开、并把规则当作有生命周期的治理对象"** | 2607.16130 | **与业主"三条寿命"的判断同构**（逐字） |

其余命中：2608.09153 TRACE、2607.25637 F(AI)2R（aiprov 两条不变式）、2606.22142 RoboLineage、2606.31272 部件级指纹。

### 4.5.2 知识库与技能"统一管理"的分类（业主要的那个答案）

| 类别 | 代表 | 说明 |
|---|---|---|
| **(a) 统一存储 / 统一 API** | 2606.02304 UCE（Memory+Strategy+Workflow+Skill 同一 library 同一管线）、**2609.25991 Knowledge-as-Skill**（知识文件进 `SKILL.md` 结构，frontmatter = topic/type/**provenance**/**lifecycle**）、2604.16911 Skilldex、2609.16669（记忆即 Skill，L0/L1/L2） | 少数派 |
| **(b) 分开 + 交叉引用** | WikiSkill 本体、2605.10114 SkillRAE、2608.09153 TRACE（四源分开 + 跨层归因）、2609.14631 IntentCap、**2605.29250 OmniRetrieval**（逐字 `not homogenization but an overarching layer`）、2608.25091 Auto-Policy、2605.22634 Contractual Skills | **多数派** |
| **(c) 完全分开、互不引用** | **无显式先例** | 负结论：**这是默认状态，不是被辩护的立场** |

⚠ 两处自我标注：2609.16669 自陈其信号是"存在性信号"而非确证率；
2605.29250 的对象是**异构知识源**，与我们"条款库"只是**类比**。

### 4.5.3 🔧 更正：**"什么该过期"不是空白**（我说过头了）

D 路给了完整检索词与命中数，可复核：
`abs:"skill" AND abs:"stale"`=13 ｜ `AND abs:"outdated"`=13 ｜ `all:"skill" AND all:"retire"`=12 ｜
`AND abs:"lifecycle"`=97 ｜ `AND abs:"pruning"`=83 ｜ `AND abs:"audit"`=211 ｜ `AND abs:"conflict"`=134

**已有的答案**：

| 贡献 | 出处 |
|---|---|
| 八阶段生命周期**明文含** `repair or prune stale entries` 与 `provenance and rollback`（TMLR 2026，审计 124 篇） | 2607.10113 |
| **给这个失效模式命了名：library drift**；台账 = append-only evidence log + per-skill contribution scores + attribution verdicts | 2605.19576 |
| **闭式判据的棘轮**：judge 把失败判过 ≥(1−τ)/2，则**任何样本量都裁不掉** | 2605.22148 Ratchet |
| **false-pass 率 0.45 是硬阈值**，越过则**静默关掉治理，任何汇总指标都看不到** | 2607.07436 Blind Curator |
| **57 个真实仓库 / 105 次 release transition，每次都让部分技能失效**，前沿 agent 仅 29.9–69.7% F1 | 2608.21964 Repo2Skill-Evo |

⇒ **真正的空白要窄得多：LLM 技能之间的语义冲突检测**——
那 134 条 `conflict` 命中**全部**是机器人 / IoT / SDN / 自动驾驶 / 传统 rule-based，**没有一条是 LLM 技能之间**。

### 4.5.4 反面证据：ClawHavoc 核实通过，**数字能追到一手**

- "nearly 1,200" 的实际出处：**Antiy CERT 2026-02-06 逐字 `at least 1,184 malicious Skills`**（12 个作者 ID 分解合计正好 1184）。
- **独立交叉验证更硬**：arXiv **2603.00195 v2 的更正逐字**写着
  `ClawHavoc counts are 341, later 824, and 1,184 by source and date, not "over 1,200"`
  ——**一篇正式论文专门把这个流传说法订正掉**。
- 三类资产（API key / 钱包 / 浏览器凭据）均由 Antiy + PolySwarm 独立确认。
- ⚠ **别混三个数**：**1184** = 恶意包数 ｜ **1467** = 含任一缺陷的技能数（Snyk）｜ **76** = Snyk 人工确认的恶意载荷数。

**同类与最硬的教训**：

| 原文/结论 | 出处 |
|---|---|
| **"skill writing without validation is no better than using no skills"** | 2605.29668 GRASP |
| **"post-hoc rollback recovers only a small fraction"**（污染不可逆） | 2608.05810 |
| 三条独立谱系：**能力全部↑ 的同时未授权变更也全部↑** | 2608.17684 |
| 三个扫描器在 61,990 个共有技能上，对 23,702 个结论不一致 | 2609.17274 |
| 技能级联 / 后门 / 隐蔽策略操纵 / SkillBloat | 2609.30383 / 2608.09577 / 2609.02564 / 2608.21929 |

---

## §5 与我们场景的交叉点：谁对得上、**差在哪**

### 5.1 有一篇横跨了一半

**Parthenon Law（arXiv 2606.04602v3）** —— 法律 matter 语料，带 `citation_scan` 工具 + **authority whitelist** +
**rubric-blind 反泄漏门**（≈ 我们的"未批准材料不得进结论"）+ Skills 版本化 + **best-so-far 门**。
Codex gated accuracy **45.3% → 55.8%**，**两个不同底模收敛到 0.4pp 以内**。

**但不满足我们**（决定性）：
- **规模差 2–3 个数量级**：1,251 matter × 中位 7 份文件 ≈ **8,700 份** vs 我们几万到几十万条款；
- 语料是**单案交易文件**，不是可跨案检索的条款库；
- **没有"版本 / 效力状态"这一维**；
- 没有"每条结论挂可点原文锚"的产品形态；
- Table 4 主结果是**手工搭的对照**，优化只在 10 道题上跑了 10 步。

### 5.2 这一片文献**裂成了两半**

| 有我们的场景、但**没有**优化 | 有优化、但**没有**我们的场景 |
|---|---|
| **2609.18769** — 约 **73,000 份规范文件**、版本现行有效、管辖/日期范围、每条声明可溯源（**场景几乎逐条对上**，但版本与范围是"生成前显式规则"**手写**） | 2607.25415 — bandit 优化运行壳，奖励含 policy compliance + unsupported-claim 惩罚，**但语料是 HotpotQA** |
| 2607.24791 — OPG 监管合规生产系统（**领域完全对，但手搭流水线复盘，不是优化**） | 2607.25408 — 把"取多少上下文"当受控变量，**无合规语料** |
| 2607.08028 — 企业可审计运行壳，有 source boundaries 与版本化产物，**但无自动优化循环** | Meta-Harness / HarnessX（见 §4） |

⇒ **没有一篇同时满足「可溯源条款库 + 版本/效力 + 审批硬门 + 几万到几十万条款」并做端到端自动化。**
**Parthenon Law 是唯一横跨的，只横跨了一半规模。**

---

## §6 这轮调研**推翻/加强/修正**了我们自己哪些说法

| # | 原说法 | 这次的结果 |
|---|---|---|
| 1 | 「WikiSkill 式接受门会杀掉我们最值钱的中性规矩 ⇒ **别指望从它那儿抄到答案**」 | 🔧 **后半句过宽。** 同族四篇分两派，**EvoSkill 的定容前沿 + 只比最弱**在族内给了机制（代价：前沿最优分可能下降，论文未讨论）。**对 WikiSkill 单篇仍成立** |
| 2 | 「只做研究、别动代码」 | ✅ 遵守。四路全程只写 `var/tmp/study/skill-evo/`（gitignore），**未动任何被跟踪文件** |
| 3 | 「记忆侧最贵的那条通道实测贡献≈0」 | ➕ **被加强但被限定**：Meta-Harness 独立得到同类现象（同等上下文下 +7.8，压到最低反而输）；但它搜的是"**怎么用** BM25"，**没有替代我们的向量路线** |
| 4 | 「我们的原始层/知识层已有」 | ⚠ **修正为更坏**：技能层 **55 份散三处、无清单、无溯源边、已有一处会导致查错库的矛盾** |
| 5 | 「WikiSkill 值得借鉴」 | ⚠ **大幅收窄**：它**没有官方代码**；而四篇**都没有**裁剪机制、都没跑到会显形的规模 |
| 6 | 「**脏了之后该怎么办，两批文献合起来仍然没有答案**」 | 🔧 **过头了。** 已有 library drift（命名）、Ratchet（闭式判据）、Blind Curator（0.45 硬阈值）、八阶段生命周期含 `repair or prune stale entries`（TMLR 2026，124 篇审计）。**剩下的真空白窄得多：LLM 技能间的语义冲突检测** |
| 7 | 「G1 = 给判据补一条 `PURPOSE.md` 式的边」 | ⚠ **被限定**：2607.29167 证明**只写在文件里的边会在记忆整合时被洗掉**；2608.10509 明说 provenance 应是**运行时控制信号**而非事后元数据。⇒ **纯文档字段是最左端、最弱的一档** |

---

## §7 四路的证据边界（照实列，含子代理自报的失效）

1. **子代理 C 的 arXiv API 中途 429 限流，三组关键检索失败且未重跑成功**
   （harness×provenance/citation、harness×policy-compliance/audit-trail、regulatory×harness）
   ⇒ **"没找到"严格说是"在我核过的约 40 篇候选内没找到"，不等于全库不存在。**
2. **Meta-Harness 全文没有 Limitations 节**（检索 `limitation` 只在讲别人），且**零显著性检验**；
   TerminalBench-2 的搜索与终评**用同一批 89 题**（自认）。
3. **HarnessX 的 +14.5% / +44% 没有留出集**——其 §7.7 Limitations 第一条自认
   `No held-out evaluation… 报的是峰值且在用于进化的那批题上测的`。
4. **四篇所有数字都是 `论文自报`，一份实验都没跑**，只核了内部算术一致性。
5. WikiSkill 的 **8 轮演化是推断**（据附录 Table 5 分组反推），**正文没有直写**。
6. **SkillOpt 正文那句 `±2.7 points` 与它自己 Table 3 的实际差值（1.6 / 4.6 / 2.4）对不上**，口径不明 ⇒ 引用应引表。
7. **EvoSkill 全文零次出现 `limitation`**，没有 Limitations 章节 ⇒ 四篇里自省最少。
8. 各仓的 **CI/测试是否真跑未核**（只读文件树，**未 clone、未执行**）；国内可访问性、issue 与弃坑情况**未核**。
9. 子代理均自报：`git status` 中 `plugin/src/compliance-sentry.js`、`plugin/src/tool-details.js` 的改动
   **在它们开工前就存在，非它们所为**（我也没碰）。

---

## §8 四路已齐，剩下的空白与已知失效

**四路全部完成**（A 仓库 / B 同族 / C 运行壳 / D 溯源边与治理）。完整报告与 64 个原始件在
`var/tmp/study/skill-evo/`（**gitignore**）：`A-repos.md`（23 KB）、`B-siblings.md`（54 KB）、
`C-harness.md`（43 KB）、`D-provenance.md`（**481 行**）。

**文献层面的真空白（收敛后）**：
1. **LLM 技能之间的语义冲突检测** —— 唯一确认的空白（134 条 `conflict` 命中全是机器人/IoT/SDN/自动驾驶/传统 rule-based）。
2. **可溯源条款库 + 版本/效力 + 审批硬门 + 几万到几十万条款** 的端到端自动化（§5）。
3. **"带 diff 的拒绝台账 + 显著性检验的接受门"** —— 四篇里最强的 WikiSkill 也没做显著性检验（§2.4）。

**方法层面的已知失效（子代理自报，照实列）**：
- 🔴 **D 路：arXiv 官方 API 全程对本机 IP 持续 429/406，5 轮退避无效。** 改用 `arxiv.org` 官方 abs 页
  的 citation meta 标签取逐字标题/摘要 + 官方 advanced search 取检索 —— **仍是 arXiv 一手来源**，
  但**只有"最新优先"无 relevance 排序、单次最多 50 条** ⇒ D 路所有"未找到"都受此口径限制。
- **C 路：arXiv API 429 导致三组关键检索失败且未重跑成功** ⇒ "没找到"只覆盖约 40 篇候选。
- 除 WikiSkill 外**未读 PDF 全文**；**论文自报的数字一个都没复现**（只核了内部算术一致性）。
- **未做 GitHub 仓库实证**（社区里是否真有人在用 `PURPOSE.md` 式做法）；**未查 Anthropic/OpenAI 官方 skill 规范原文**。
- ClawHavoc **无受害者侧取证**，Koi 原报告未直接读到。
- ⚠ **该领域每月新增数十篇**，2026-09-28 的索引下结论可能很快需要更新。

---

## §9 出处

| 层 | 位置 |
|---|---|
| 完整报告（四份） | `var/tmp/study/skill-evo/A-repos.md`（23 KB）、`B-siblings.md`（54 KB）、`C-harness.md`（43 KB）、`D-provenance.md`（481 行） |
| 原始件 | 同目录 `raw/`（64 个文件）＋ `var/tmp/study/memory/raw/papers/wikiskill.2608.27454.pdf` |
| WikiSkill 单篇评估（含 §12 同族增补与更正） | [wikiskill-integration-assessment.md](wikiskill-integration-assessment.md) |
| 记忆系统侧调研 | [agent-memory-systems.md](agent-memory-systems.md) |
| 本仓相关归属层 | 解析管线 → `docs/ENCYCLOPEDIA.md`；已否决 → `docs/NOT-DOING.md`；棘轮与门禁 → `scripts/gates-baseline.json` / `eval/baseline.json` / `tests/test_golden_gate.py`；长周期计划 → `docs/RETRIEVAL-LONG-RANGE-PLAN.md` |

> 本文**只登记，不改任何代码或判据**，也不含实施建议。§1.1–§1.3 的数字为我一手实测、可复核。
