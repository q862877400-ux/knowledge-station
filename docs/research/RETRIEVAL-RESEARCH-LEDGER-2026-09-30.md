# 调研台账（防失忆）—— 2026-09-30 会话

> **这份文件是干什么的**：业主指示「**你调研分析的过程要做笔记报告，以免上下文压缩导致失忆**」。
> **它记的是"过程与状态"，不是"结论"**——结论在各自的归属文档里（见 §2 的表）。
> **用法**：每次上下文被压缩、或换会话接手时，**先读本文**，再决定从哪接着做。
> **维护规矩**：本文只记**可核的状态**（读了哪几页、什么命令、什么报错）；
> **不重复结论**，结论一律指回归属文档 —— 一个事实一个归属层。

---

## 1. 一句话现状（2026-09-30 收尾时）

**本轮四件事都已落盘、都已提交，没有半途的东西。**
当前停在「文献调研第二轮读完，等着决定要不要读剩下的页，以及要不要把'路由信号'那条登记进总纲 P4」。

---

## 2. 本会话产出的全部文档（归属表）

| 文档 | 主题 | 提交 |
|---|---|---|
| `docs/research/HINDSIGHT-DOCS-READING-2026-09-28.md` | Hindsight 官方文档 42/42 通读（996 行，§0–§16） | `51fcdf7` 等 |
| `docs/research/HINDSIGHT-DEPLOYMENT-STATUS-2026-09-30.md` | Hindsight 本机部署现状交接说明（213 行） | `cc5ae20` |
| `docs/research/HINDSIGHT-FACTCHECK-2026-09-30.md` | 对一份外部 AI 报告的逐条核查（**另一个会话在写**，473 行） | **未提交**（不是我的） |
| `docs/research/MEMPALACE-REVIEW-2026-09-30.md` | MemPalace 调研，**五轮**（§1–§10，785 行） | `2b5c32f`/`ed3cf59`/`e6d7047`/`1c88451` |
| `docs/research/RETRIEVAL-LITERATURE-SCAN-2026-09-30.md` | 检索文献扫描，**两轮**（TREC ToT / 冠军做法 / UvA 警告） | `36418ca`/`4380e59` |
| `docs/research/papers/README.md` | 外部原件清单 + 取得命令 + 校验值 | 本次 |
| `docs/RETRIEVAL-LONG-RANGE-PLAN.md` | **施工总纲**（我加了三处登记 + 一处更正） | `3388fa2`/`363e3aa`/`f1ff6fc`/`981c7f2` |
| `docs/NEXT-DEV-PLAN-2026-09-28.md` | 现在该做什么（我加了 §7.2 登记） | `a374bd2` |
| `docs/NOT-DOING.md` | 台账（我加了 #21 解除、#22 三字滑窗否决） | `3388fa2` |
| `eval/lay-phrasing/` | 大白话语料入库（36 文件 / 0.69 MB，含 README） | `981c7f2` |

---

## 3. 文献调研：**逐份的读没读**（最重要的防失忆表）

### 3.1 已经拿到原件并读过的

| 来源 | 原件在哪 | 读到哪 | 未读的部分 |
|---|---|---|---|
| **TREC 2025 ToT 赛道总览**（arXiv 2601.20671） | 无本地件（网页读到全文） | **读完正文**（含结果表 Table 1） | 无（正文已读） |
| **DS@GT 那篇**（arXiv 2602.10321，"单轮改写+多阶段重排"） | `docs/research/papers/mst.html` / `mst.txt` | **读到第 649 行附近**（§1–§6，含 Table 6 与净增益段） | 参考文献之后 |
| **冠军 SRCB**（TREC 2025） | `docs/research/papers/SRCB.mllm.tot.pdf` | **第 1–5 页**（§1–§3.1.2 开头，含 Table 4 提示词图） | **§3.1.2 后半 + §3.2 + 结果表（第 5–8 页）** |
| **UvA "Simulation Gap"**（TREC 2025） | `docs/research/papers/UAmsterdam.tot.pdf` | **第 1–2 页**（摘要 + §1 引言 + §2 开头） | **§2.1 之后全部（第 2–9 页）**，含 RQ1/RQ2/RQ3 逐项结果 |

### 3.2 明确**没读**的

| 想读 | 状态 |
|---|---|
| `webis.tot.pdf`、`YaleNLP.tot.pdf`、`IISERK.tot.pdf`、`DSGT.tot.pdf` | **没试过下载**（命名规律同 SRCB，值得一试） |
| **BLUR 基准原文**（Wang et al.） | 只从别人转引看到数（人 98% vs 系统 ~56%），**未找原文** |
| **CLEF Social Book Search（2011–2016）** | 只从 UvA 参考文献看到名字（"Name that Book"），**未找** |
| **arXiv 2604.21284 的附录**（MemPalace 那篇，20 页 10 表） | 只读了摘要+§1–§8+§D 披露；**附录 A（代码统计）/B（基准复现）未读** |
| **有没有中文检索工作** | **完全没查** |

---

## 4. 已经用过的检索词（**别重复查**）

```
entity retrieval candidate generation disambiguation large candidate set arxiv
synonym aware dense retrieval query expansion lay user vocabulary arxiv
sparse dense hybrid retrieval fusion reranking candidate set size arxiv 2025
synthetic query generation retrieval doc2query InPars distribution mismatch
learned sparse retrieval SPLADE vs dense reranking arxiv
Chinese term retrieval entity linking lay language colloquial query
TREC Tip-of-the-Tongue track overview 2025 arxiv recall description vague
tip of the tongue retrieval benchmark identifying unknown item from description
SRCB TREC 2025 tip-of-the-tongue million LLMs approach method
simulation gap tip-of-the-tongue synthetic queries hedge removal query drift
```

**下一步可试的检索词**（未用过）：`ColBERT late interaction Chinese`、
`国标 术语 检索`、`legal term retrieval Chinese BM25`、`BEIR Chinese benchmark`、
`query performance prediction TOT`、`known-item search social book search CLEF`。

---

## 5. 🔴 已经踩过的坑（**别重踩**）

| # | 坑 | 正确做法 |
|---|---|---|
| 1 | `web_fetch` 取 PDF → `unsupported content type` | **下到本机，用 `read_pdf`** |
| 2 | `https://r.jina.ai/<url>` → **401** `AuthenticationRequiredError`（IP 信誉被限） | 用 **`curl` 带浏览器 UA 直连**（`trec.nist.gov` 可直连） |
| 3 | **猜 PDF 文件名，下到 276 字节的 404 页却没察觉**（`DSGT.tot.pdf`） | **下完必须验 `%PDF` 文件头**；命令在 `papers/README.md` |
| 4 | MemPalace 源码**先读了 `main` 分支**，而默认分支是 `develop`（两分支内容不同） | 先 `gh api repos/X --jq .default_branch` |
| 5 | 差点提议「**按领域缩窄候选术语**」——**本纲已实测失败**（真术语所在文档前 1 只 9.1%） | **提案前先读总纲 P1 段**；已在台账/总纲登记为不许再提 |
| 6 | 差点把「**$var/tmp 里的难问题语料**」当成"建议入库"（实际是**必须**：生成脚本不在，不可再生） | 报"建议"前先查**能不能再生** |
| 7 | 差点把**总纲已知的事**（金标跑在 19 篇快照库上）当新发现端上来 | 登记前先 `grep` 总纲与 NEXT-DEV-PLAN |
| 8 | 编辑时**吞掉过 `## 4. 依赖关系` 标题**（旧串只替换标题行） | 替换的 `old_string` **别只含标题**；改完 `Select-String '^## '` 复核章节结构 |

---

## 6. 未决 / 下一步（**接手时从这里挑**）

### 6.1 文献线（本轮停在这里）

1. **读完 UvA 的 §3–§5** ← 最该做。那 10.6%（"难题上提升、词面重叠强反而变差"）的**条件细节**在里面，
   而它是**唯一一条能直接支持本纲 P4 路由信号**的证据。
2. **读完 SRCB 的第 5–8 页**（§3.1.2 后半 + §3.2 提交 + 结果表）——负采样细节与它自己报的分项。
3. **试下 `webis/YaleNLP/IISERK` 三个 PDF**（命名规律同 SRCB，一条 curl 的事）。
4. **查有没有中文工作**（未开始的空白）。
5. **BLUR 原文**（人 98% vs 系统 56% 这个数我只从转引看到，**没核过**）。

### 6.2 待业主拍板（**5 件，一件都没动**，全在总纲 §6）

| # | 事 |
|---|---|
| 1 | P4 的调用预算（每次提问最多问 Jev 几次） |
| 2 | 要不要给金标补"答案片段"字段 |
| 3 | `个人信息保护法(测试)` 假样本怎么处置 |
| 4 | 总纲 P0 表 0.4b 那组数**已就地更正**（本次办的）；**仍未定的是 `ORDER BY` 两键要不要改成产品决策** |
| 5 | §2 要不要加第四条总判据「答得对」——**我建议排在"难问题进尺子"之后** |

### 6.3 撞车申报（**要求翻案，等业主明说**）

**本纲 §7「学习式排序/学习式稀疏（没有标注数据）」** vs **我本轮入库的 `gen-V2.jsonl`（1,832 条"外行说法→术语"配对）**：
* 对 **P1 的术语选择**这一步，**那已经是标注数据**；
* 对**条款级排序**，**确实仍没有**（标签是术语不是条文）；
* 且 SRCB 的三种数据增强（删线索/换同义/换误导）是"没有标注也能造"的配方。
⇒ **不说就维持 §7 现状；要说请业主明说。**

### 6.4 明确**登记了但没开工**的两件

* 那批难问题语料的**原件**（`var/tmp/`）要不要清（我已复制入库，原件没删）。
* 8 份「未判死活」的计划文件要不要逐份定性（表在总纲 §6.1）。

---

## 7. 环境与产物位置（防找不到）

| 东西 | 在哪 |
|---|---|
| 本轮下的外部原件 | `docs/research/papers/`（**不入库**，见该目录 README） |
| 大白话语料（已入库） | `eval/lay-phrasing/`（36 文件 / 0.69 MB） |
| 语料原件（未删） | `var/tmp/gen-V2.jsonl` 等 |
| 本会话的临时提取 | `%TEMP%\rag\`（**会被清，不要依赖**） |
| 真库 | `C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db`（2,272.7 MB） |
| 评测快照库 | `eval/golden/knowledge-snapshot.db`（10.4 MB，**19 篇**，金标就在它上面跑） |

---

## 8. ⚠ 本台账自身的一条边界

**本文记录的是"我做过什么、读到哪、卡在哪"，不是结论，也不是证据。**
凡涉及数字与判断的，**一律以 §2 表里的归属文档为准**；
凡本文与归属文档冲突的，**以归属文档为准**，并**就地把本文改掉**（不许两说并存）。
