# MemPalace 调研 + B站介绍视频评论区核查

> 调研时间：2026-09-30　　**所有数字都注明取得方式**；凡我未核的，明确写"未核"。
> 视频：`BV1ZUD7BgEiP`《生化危机女主开源有史以来得分最高的AI记忆系统，完全本地运行零成本》
> 仓库：`https://github.com/MemPalace/mempalace`（**注意大写**，原址是 `github.com/milla-jovovich/mempalace`）

---

## 一、先说结论（三句话）

1. **它的架构方向，恰好是我们对 Hindsight 最不满意的那一条的反面**——它**原文一字不动地存**，不摘要、不抽取、不改写。Hindsight 是把原文抽成事实、并且**故意抹平版本差异**。
2. **但它的跑分与成本数字有内部矛盾**，而且**没人验过**（评论区零条讨论跑分）。
3. 🔴 **仓库里有一份第三方对 `qwen3.8-27b`（你本机同款）的实测**：常规任务 90–100%，**高敏感压力测试只有 42.9%**。

---

## 二、项目事实（`gh api` 实取 + 官方文件）

| 项 | 值 |
|---|---|
| 星标 / fork / 关注 | **59,359** / 7,561 / 325 |
| 开放 issue | **760** ⚠ 数量很大 |
| 语言 / 许可 | Python / **MIT** |
| 创建 / 最后推送 | 2026-04-05 / 2026-09-29 |
| 最新版本 | **v3.10.0**（2026-09-16 发布） |
| 仓库体积 | 28,662 KB |

**自述**（README 首行）：
> "Local-first AI memory. **Verbatim storage**, pluggable backend, **96.6% R@5 raw on LongMemEval — zero API calls**."

**核心设计**（README 原文）：
> "MemPalace stores your conversation history as **verbatim text** and retrieves it with semantic search. **It does not summarize, extract, or paraphrase.**"

⚠ 这一句是**与 Hindsight 最本质的区别**，也是对我们最重要的地方（见第六节）。

### 2.1 结构（"记忆宫殿"）

| 概念 | 含义 |
|---|---|
| Palace | 包含所有知识的大房间 |
| **Wing** | 一个人 / 一个项目 = 独立空间 |
| **Room** | 一个具体主题（认证、计费、部署…） |
| **Hall** | 定义"这段记忆属于哪一类"（建议/偏好/决策） |
| **Drawer** | **原始记录，一字不动，完整封存** |
| **Closet** | 上述内容的**压缩摘要**，为 AI 快速读取准备 |
| **Tunnel** | 不同 Wing 出现相同 Room 时自动打通 |

**记忆堆栈**（按需加载）：L0+L1 常驻 ≈ **170 tokens**；L2 房间级召回；L3 全局深搜。

### 2.2 存储后端（可插拔，非默认均需显式开启）

| 后端 | 模式 | 命名空间 | 词法 |
|---|---|---|---|
| `chroma`（默认） | 本地嵌入式 | – | ✓ |
| `sqlite_exact` | 本地（NumPy 精确） | – | ✓ |
| `rust_exact` | 本地（原生向量） | – | ✓ |
| `milvus` | 本地 Lite / 服务端 | ✓ | ✓ |
| `qdrant` | 服务端 REST | ✓ | ✓ |
| `pgvector` | 服务端 Postgres | ✓ | ✓ |

### 2.3 嵌入模型 ⚠ **中文必须换**

`mempalace/embedding.py` 原文：

| 模型 | 维度 | 语言 |
|---|---|---|
| `minilm`（**默认**） | 384 | `all-MiniLM-L6-v2`，**English-only training** |
| `embeddinggemma` | 384（Matryoshka 截断） | `embeddinggemma-300m`，**multilingual（100+ 语言）** |

> "Cross-lingual cos **~0.88** on parallel translations vs MiniLM's **~0.35**. **Recommended**"

⇒ **默认那个是英文的**；中文要用得手动换成 `embeddinggemma`（约 300 MB）。

### 2.4 跑分（仓库自己给的表）

| 模式 | R@5 | 需要 LLM |
|---|---|---|
| Raw（语义搜索，无启发式、无 LLM） | **96.6%** | 无 |
| Hybrid v4，**held-out 450 题** | **98.4%** | 无 |
| Hybrid v4 + LLM rerank（全 500） | ≥99% | 任意可用模型 |

⚠ **官方自己承认的那一条**（README 原文）：
> "we do not headline a '100%' number because the last 0.6% was reached by **inspecting specific wrong answers**, which `benchmarks/BENCHMARKS.md` flags as **teaching to the test**."

**跑分文件是真的提交了**（我核了 `benchmarks/` 目录）：
`results_mempal_raw_session_*.jsonl`、`results_mempal_hybrid_v4_held_out_*.jsonl`、
`results_locomo_*`、`results_convomem_*`、`results_membench_*` —— **每题原始结果都在**。

---

## 三、🔴 我核查出的五处问题

### 3.1 README 声明"刻意不做并排对比"，但仓库自己做了

**README 原文**：
> "We **deliberately do not include a side-by-side comparison** against Mem0, Mastra, **Hindsight**, Supermemory, or Zep. Those projects publish different metrics on different splits, and **placing retrieval recall next to end-to-end QA accuracy is not an honest comparison**."

**但 `benchmarks/BENCHMARKS.md` 里有一张排名表**，这几个名字全在，而且**混了指标**（表里自己标了"QA accuracy, not R@5"）：

| # | 系统 | R@5 |
|---|---|---|
| 1 | MemPal（hybrid v4 + Haiku rerank） | **100%** |
| 2 | Supermemory ASMR | ~99%（*QA accuracy, not R@5*） |
| 3 | MemPal（hybrid v3 / palace + rerank） | 99.4% |
| 4 | Mastra | 94.87%（*QA accuracy, not R@5*） |
| 5 | **MemPal（raw, no LLM）** | **96.6%** |
| 7 | **Hindsight** | **91.4%**（*per their release, **metric unverified***） |
| 10 | BM25 | ~70% |

⇒ **它一边说"这么做不诚实"，一边这么做了。**

### 3.2 同一个文件里，对 Hindsight 91.4% 的出处自相矛盾

- 排名表：`Hindsight | 91.4% *(per their release, metric unverified)*`
- 另一张对照表：`Hindsight | Time-aware vector retrieval | 91.4% | LLM API | **Validated by Virginia Tech**`

⇒ **同一个数，一处"未经核实"，一处"已被弗吉尼亚理工验证"。**（⚠ 我**未核**"弗吉尼亚理工验证"这个说法本身是否属实。）

### 3.3 成本数字三处不一致

| 来源 | 说法 |
|---|---|
| 量子位（2026-04-09） | 6 个月对话 ≈ **1950 万 tokens**；传统摘要压缩到 65 万 tokens，**年成本约 507 美元**；MemPalace **年成本 10 美元** |
| B站视频标题 | "**一年 0.7 美元**" |
| 仓库 README | ⚠ **未找到这两个数字的原始出处** |

⇒ **507→10 与 0.7 对不上**，相差 14 倍。**这两个数我都未在仓库里核到。**

### 3.4 它自己的"轻量模式"反而更差（同款本地模型实测）

见第五节——`lightweight`（3 工具）90% / 30.68 秒，`legacy`（45 工具）**100% / 25.19 秒**。

⇒ **轻量模式又慢又差**，与"轻量=更快更省"的直觉相反。

### 3.5 自定义缩写语言 AAAK 的代价（量子位引作者自述）

| 模式 | LongMemEval 召回 |
|---|---|
| AAAK | **84.2%** |
| RAW | **96.6%** |

⇒ **差 12 个多点**（作者自己给的数）。想省 token 就用 AAAK，想保精度就用 RAW。

---

## 四、团队与"是不是她本人"

**媒体口径**（量子位 2026-04-09）：
> "Milla Jovovich，这位曾饰演爱丽丝的知名女星，最近和**程序员老友**及 Claude 一起，合造了一个 AI 记忆系统。"
> "**一个架构师 + 一个程序员 + Claude**"——架构师是 Milla，程序员是 **Ben Sigman**（相识 20 多年的老朋友）

**我能核到的**：
- 仓库贡献者里**确有一个账号叫 `milla-jovovich`**（80 commits，排第 5）
- 它的 bio 写着 `Milla Jovovich-Creator/Architect of MemPalace`
- 它提交的是**真技术活**（带 issue 号的修复）：`fix(hallways): paginate drawer fetch to avoid SQLite variable overflow on large wings (#1619)`、`fix(ids): delimit hash inputs to prevent drawer_id collisions (#80)`
- **最多产的贡献者是 `igorls`（1046 commits）**，是 `milla-jovovich` 的 13 倍

⚠ **我无法核实这个 GitHub 账号是否就是那位演员本人。** 需要外部验证，本轮**未做**。
（该账号 `followers: 0` / `following: 0` / `public_repos: 2`，创建于 2025-09-14。）

---

## 五、🔴 与你本机直接相关：第三方对 `qwen3.8-27b` 的实测

仓库里有 `benchmarks/results_ninfer_qwen27b.json` + `test_ninfer_qwen27b.py`：

```json
{
  "model": "qwen3.8-27b-nvfp4",
  "endpoint": "http://x870e-9950x3d:8010/v1/chat/completions",
  "timestamp": "2026-09-01 12:18:09"
}
```

**常规测试（各 20 项）**：

| 模式 | 通过率 | 平均延迟 |
|---|---|---|
| `lightweight`（3 个工具） | **90.0%**（18/20） | **30.68 秒** |
| `legacy`（45 个工具） | **100.0%**（20/20） | 25.19 秒 |

**高敏感压力测试（7 项）**：

| 指标 | 值 |
|---|---|
| **通过率** | **42.86%（3/7）** |
| 平均推理分 | 66.7% |
| 平均延迟 | **35.82 秒** |

7 项各自延迟：25.07 – 42.04 秒。测的都是：时序用药、跨科过敏禁忌、大海捞针干扰项、**未存储事实的幻觉抵抗**、隐式症状检索、多约束查询、过敏更新。

⇒ ⚠ **"高敏感"这一档通过率只有 42.9%。** 而我们关心的法规条文场景，**正属于这一档**。
⇒ ⚠ 另外注意：**测的是 `nvfp4` 量化，你本机是"三值"量化**，两者不是同一档；**这个结果不能直接搬到你那台机器上**。

---

## 六、B站视频评论区（`BV1ZUD7BgEiP`）

### 6.1 视频本身（`bili video` 实取）

| 项 | 值 |
|---|---|
| 标题 | 《生化危机女主开源有史以来得分最高的AI记忆系统，完全本地运行零成本》 |
| UP 主 | 阿甘探AI |
| **时长** | **35 秒** ⚠ 极短视频 |
| 播放 / 赞 / 收藏 | 543,986 / 20,803 / 19,848 |
| **投币** | **820** ⚠ 币/赞 ≈ **3.9%** |
| 弹幕 | 88 |
| 字幕 | **无** |
| 简介 | **空** |

### 6.2 评论全貌：3 条顶层 + 41 条楼中楼

⚠ **顶层只有 3 条**（543,986 播放），说明热评集中、且**没有长尾讨论**。

**顶层三条**：

| 赞 | 内容 |
|---|---|
| **2524** | 「真是她吗？[笑哭]」 |
| **1845** | 「那这样游戏里面的npc会永远记住你。酒馆的老板会说老伙计又来了…」（20 条回复，**全是游戏幻想**） |
| 556 | 「我就说她肯定不会把红皇后就放哪不管」（红皇后 = 生化危机里的 AI） |

### 6.3 🔴 评论区的两个焦点，**都与技术无关**

**焦点一：是不是她本人**（对「真是她吗？」的 33 条回复）

| 赞 | 内容 |
|---|---|
| **1603** | 「是她，ins上发了」 |
| **948** | 「**她和她的工程师朋友搞的，至于具体贡献就不知道了**」 |
| 367 | 「查一下再下定论不难吧，就是她和朋友搞得」 |
| 198 | 「**也有说她只是站台背书的，目前还不确定**」 |
| 148 | 「应该是提了些需求上的痛点」 |
| 42 | 「**虽然只是挂名**，但东欧女的确是很聪明的」 |
| 6 | 「**一眼炒作，背书而已**」 |
| 3 | 「技术贡献大家不知道，**宣传贡献也很重要**」 |

⇒ **评论区的倾向性结论：她大概率是"背书/挂名"，实际工程是她的工程师朋友做的。** 但这只是网友判断，**不是证据**。

**焦点二：游戏 NPC 幻想**（对 1845 赞那条的 20 条回复）——全部在聊"以后游戏 NPC 能记住玩家"，**没有一条**聊记忆系统的技术实现。其中两条**真实用户反馈**值得记：

- 「我也很喜欢玩这种酒馆类的ai，但是**现在这个记忆能力实在是太难蚌了，基本上一百多轮就开始胡言乱语**」
  ⇒ 这是他们真正遇到的痛点：**约 100 轮后记忆崩坏**
- 「说真的不太可能，一是AI输出的内容不确定，二是这样很费钱，玩家自己的钱」
- 「这玩意儿也就在18内容上有点竞争力，更何况花的钱可不少，**你要真去玩模型一年花个三四千还是得有的**」

### 6.4 🔴 评论区最重要的事实：**零条讨论跑分**

**没有一条评论提到 96.6% / LongMemEval / 98.4% / 记忆宫殿结构。**
543,986 次播放、41 条楼中楼，**技术主张一条都没被验证或质疑过**。

⇒ 这个视频是**人设驱动**的传播（"明星跨界"），**不是技术驱动的**。
⇒ 评论区对它的"有用性"**没有提供任何证据**，只提供了一条真实痛点（100 轮后崩坏）。

---

## 七、对我们（KnowledgeStation / 法规语料）的意义

### 7.1 ✅ 架构方向对上了我们最疼的那一条

| | Hindsight | **MemPalace** |
|---|---|---|
| 存什么 | 抽成结构化**事实** | **原文一字不动**（Drawer） |
| 版本差异 | 官方设计**故意抹平**（"页面就说 Y，而不是两版都留"） | 原文都在，**不抹** |
| 对我们 | 🔴 与我们"作废/被代替必须并存"**正面冲突** | ✅ 方向一致 |

⇒ **这是本轮调研里对我们最有价值的一条**：**"原文不动 + 语义检索"这条路线，是存在的、有人在做的、而且拿了 59K 星。**

### 7.2 ⚠ 但有四处要打折

1. **中文要手动换嵌入模型**（默认为英文 `minilm`）
2. **成本数字三处不一致**（507→10 vs 0.7），**均未在仓库核到**
3. **README 与 BENCHMARKS.md 自相矛盾**（声明不做对比 / 实际做了）
4. **没人在评论区验过它的跑分**，而媒体口径（"满分 AI / 反杀大厂"）**比仓库自己的说法激进得多**
   （仓库：不宣传 100%，因为最后 0.6% 是"对着错题调出来的"）

### 7.3 🔴 本地模型这一档，数字不好看

第三方对 `qwen3.8-27b` 的实测：**高敏感压力测试通过率 42.9%**、延迟 35.8 秒。
⚠ 且那是 `nvfp4`，与你的三值量化不同档，**不能直接搬**。

### 7.4 未核清单（别当结论）

- `milla-jovovich` 账号**是否真是那位演员** —— 未核
- **507→10 与 0.7 美元**两个成本数字 —— **未在仓库核到**
- "**Validated by Virginia Tech**" 这个说法 —— 未核
- 59,359 星里**有多少是"明星效应"带来的** —— 未核（4/9 当天 3.3k→17.4k，与量子位报道同期）
- 它对**中文法规语料**的实际表现 —— **未测**（它自己没有中文跑分）

---

## 八、第二轮：对批评意见的代码级核查（2026-09-30 追加）

> 触发：业主转来一段评论（**来源未确认，格式像知乎**——带时间戳/回复/赞数，
> 用户名 `雪影-Snow`、`PeterMa11111`、`yanzcc003`、`冰冻君`）。
> ⚠ **该段不属于 B站那个视频**：已实测该视频 44 条评论的 34 个用户名，**无一条吻合**。
> 核查方式：**不采信业主、也不采信批评者**，全部回到 `develop` 分支源码逐条验。

### 8.0 一条方法学更正（我自己先踩了）

⚠ 首次核查我用的是 **`main` 分支**。`gh api` 显示**默认分支是 `develop`**。
两分支内容有差异（如 `hallways.py`：`develop` 40,133 字节 vs `main` 17,924 字节）。
**下文全部数字取自 `develop`**（= 默认分支 = 安装时拿到的）。

### 8.1 那段评论的七条指控，逐条判定

| # | 指控 | 判定 | 代码依据（`develop`） |
|---|---|---|---|
| 1 | `wing`/`hall` 只是命名空间分层，靠 **metadata 过滤**实现的伪层级 | **成立** | `hallways.py` 用 `.get(where={"wing": ...}, limit=…, offset=…)` ⇒ 是**扁表加过滤**，非树/递归 |
| 2 | 预加载取 **top15 importance**，但 **importance 没设置** | **成立** | `layers.py` `MAX_DRAWERS = 15`；`importance = 3.0`（硬编码）；注释自认见 8.2 |
| 3 | 预加载**截断 200 字符**，质量极低 | **成立** | `layers.py` L255–256 `if len(snippet) > 200: snippet = snippet[:197] + "..."` |
| 4 | "hall 没看到"（没写完） | **不成立** | `hallways.py` 在 `develop` 有 40,133 字节，且实现**实体对**走廊：`_hallway_id(wing, entity_a, entity_b)`、`compute_hallways_for_wing` |
| 5 | `tunnel` 在 graph 里定义了但**搜索没用** | **未定论** | `tunnels_tool.py` 确实存在（12,396 字节，有 `tunnel_endpoints`/`_link_key`/`contains`/`add`）。是否接入检索路径**本轮未验完** |
| 6 | raw 96 本质是 **chromaDB 裸分**，"20 行代码就能实现" | **未核** | 未实测复现，**不当结论** |
| 7 | 100 的 hybrid 版**按 raw 的错题做了针对性改动**，泛化性难说 | **成立（项目自认）** | README 原文："the last 0.6% was reached by **inspecting specific wrong answers** … **teaching to the test**" |

### 8.2 最有分量的一处：`layers.py` 的注释是开发组自己写的认罪书

`mempalace/layers.py` 注释原文：

> "NOTE: the ingest pipeline (miner, convo_miner, diary, add_drawer) records provenance
> metadata — wing/room/source/chunk/filed_at — but **never an evaluative importance/weight field**.
> So `importance` is **absent on virtually every drawer** and ties at the default, which used
> to collapse the sort to insertion order (oldest first). `filed_at` is present on every drawer,
> so it is the ***effective* ordering signal: newest first**. This keeps importance as the primary
> key **for the day a scoring pass populates it**…"

⇒ **批评者说的"importance 没设置"，是代码自己写着的。**
⚠ **但要说公道**：开发组后来修了**一半**——候选窗口从"后端随便给的 2000 条"改成"最近归档的 2000 条"（注释里引 #1630）。**"importance 不存在"这一半至今没修**，排序实际只按时间新旧。

### 8.3 另一份批评：Penfield Labs《MemPalace Benchmark Fraud Analysis》

来源：`lhl/agentic-memory` 仓库收录的 `penfield-mempalace-analysis.md`（原发 Substack，2026-04-07）。
四条核心指控，**我逐条核了**：

| # | 指控 | 判定 | 依据 |
|---|---|---|---|
| 1 | **LoCoMo 取巧**：`top_k` 超过会话总数，embedding 检索被完全绕过 | **成立（项目自认）** | `BENCHMARKS.md` L127 原文：`Hybrid v5 + Sonnet rerank (top-50) ｜ 100% ｜ … ｜ **Structurally guaranteed (top-k > sessions)**` |
| 2 | **LongMemEval 指标类别错误**：榜单测端到端问答，它只做检索（`recall_any@5`） | **成立（项目自认）** | `BENCHMARKS.md` L48–51 原文："Retrieval recall and QA accuracy **are not comparable**" |
| 3 | 宣称的"**矛盾检测**"在代码里不存在 | **成立** | `knowledge_graph.py`（**988 行**）里 `contradict` 命中 **0 次** |
| 4 | AAAK 宣称"**30x 无损压缩**"，实际 55 字符截断 | **成立，且比指控更狠** | `dialect.py` L12：`NOTE: AAAK is **NOT lossless compression**. The original text cannot be reconstructed`；L531–532 截断至 55；**L1092 命令行自己打印** `(lossy summary, not lossless compression)` |

**Penfield 的一句总评值得原样记下：**
> "BENCHMARKS.md is 5,000+ words of careful self-critique that **directly contradicts the launch tweet**.
> Internal documentation acknowledged every flaw. **Marketing stripped every caveat.**"

⇒ 这与 §3.1 那条**内部矛盾**（README 声明"刻意不做并排对比"、`BENCHMARKS.md` 里却有该对比表）**是同一个模式**。

### 8.4 ⭐ 连批评者都承认的那一条（对我们最重要）

Penfield 在同一份分析里写：

> "**What's Genuinely Interesting** — Raw verbatim text with default embeddings
> **outperforms LLM-extraction approaches for session retrieval** — suggesting the field
> **over-engineers memory extraction**. A legitimate finding that didn't require inflated numbers."

⇒ **这独立印证了 §7.1 的判断**：**"原文不动 + 语义检索"这条路线本身是有价值的**——
**连花力气拆它的人，也承认这一点**。问题不在架构，在**它的营销把保留意见全删了**。

### 8.5 本轮新发现的四个外部批评源（此前完全不知道）

| 类型 | 出处 |
|---|---|
| **学术论文** | 《Spatial Metaphors for LLM Memory: A Critical Analysis of the MemPalace Architecture》（Dey & Viradecha，arXiv 2604.21284） |
| **GitHub Issue** | `MemPalace/mempalace` **#875**：《README 与官网仍含**虚假基准声明**》 |
| **GitHub Issue** | **#27**（Leonard Lin 提交，宣称的矛盾检测不在代码里） |
| **GitHub Discussion** | **#849**：简体中文用户看过来 |

⚠ `#875` 这个号**在它自己的 `BENCHMARKS.md` 里被我见过**（"…For a fair head-to-head, run the same metric on the same split."）
⇒ 项目**知道**这个指控，并在基准文档里回应过。**上述论文/issue 本轮均未展开细读，只登记。**

### 8.6 视频评论区：要"多找技术发言"——结论是**找不到**

| 项 | 实测 |
|---|---|
| 总评论数 | **553**（`cursor.all_count`） |
| **不登录能取到的顶层评论** | **仅 3 条**（B站翻页被限制） |
| 楼中楼 | 41 条（该接口未被限制） |
| **这 44 条里的技术发言** | **0 条**——全是「是不是她本人」和「游戏 NPC 幻想」 |
| `bili-cli` | **无评论命令** |
| `opencli bilibili comments` | **有**，但需 Chrome + OpenCLI 扩展（实测 `BROWSER_CONNECT: extension not connected`） |

⇒ **那个视频的评论区挖不出技术内容。** 你贴的那段（质量高得多）**不是它**——
技术讨论在**知乎 / GitHub issues / arXiv**，不在这个 35 秒短视频下面。

### 8.7 本轮未核清单（不得当结论）

- 那段评论的**真实出处**（只推定"像知乎"，**未找到原文页**）
- `tunnel` 是否接入检索路径
- 「raw 96 是 chromaDB 裸分、20 行可复现」—— **未复现**
- arXiv 2604.21284 全文、issue #875 / #27、discussion #849 的**正文** —— **只登记，未细读**
- 那四条 Penfield 指控我验的是**"项目是否自认/代码是否存在"**，
  **不是我独立重跑了它的基准** —— 所以"取巧成立"的依据是**它的自认**，不是我的复现
