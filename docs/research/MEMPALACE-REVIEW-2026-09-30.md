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
