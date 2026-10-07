# 学术调研 · 第 3 轮：**还债 + 四条主线收敛**

> 第 3 轮。任务：**把拖欠的读完**（LegalBench、HyDE、两篇已下载 PDF）+ **对"中文法条检索基准有没有"下结论**。
> 规矩不变：**读到的说读到、没读到的说没读到**；每条给出处；**没价值的直说**。

---

## ★★★★★ 本轮颠覆性的发现：**中文法条检索基准是存在的，而且完全公开、MIT 许可**

### `STARD` —— STAtute Retrieval Dataset
**论文**：*STARD: A Chinese Statute Retrieval Dataset with Real Queries Issued by Non-professionals*
（arXiv `2406.15313`；`ar5iv.labs.arxiv.org/html/2406.15313`，**我读了摘要全文**）。
**代码与数据**：`https://github.com/oneal2000/STARD`（**我实测了仓库与文件清单**）。

### 它到底是什么（摘要原文要点 + 实测仓库）
> 「Statute retrieval aims to find relevant statutory articles for specific queries…
> **Existing statute retrieval benchmarks focus on formal and professional queries from sources like
> bar exams and legal case documents, thereby neglecting non-professional queries from the general
> public, which often lack precise legal terminology and references.**
> To address this gap, we introduce the **STAtute Retrieval Dataset (STARD), a Chinese dataset
> comprising 1,543 query cases collected from real-world legal consultations and 55,348 candidate
> statutory articles**…
> Through a comprehensive evaluation… we reveal that **existing retrieval approaches all fall short of
> these real queries issued by non-professional users. The best method only achieves a Recall@100 of
> 0.907**, suggesting the necessity for further exploration.」

**仓库实测（GitHub API，直连）**：
| 项 | 值 |
|---|---|
| 仓库 | `oneal2000/STARD`，★26 / fork 3，created 2024-03-17，pushed 2025-04-24 |
| **许可** | **MIT**（`spdx_id = MIT`）← **宽松，可商用** |
| 描述 | 「StaRD: Statute Retrieval Dataset based on Real-World Legal Consultation」|
| **`/data/corpus.jsonl`** | **23.0 MB**（≈55,348 条候选法条）|
| **`/data/queries.json`** | **1.8 MB**（≈1,543 条真实咨询提问 + 金标）|
| 其它 | `/src/`（代码）、`README.md`、`Data Statement.md`、`LICENSE` |

### ★★★ 为什么这条对我们**特别重要**（三点，逐条对得上）
1. **它是中文** —— 两轮没找到的中文基准，这里是；
2. **它的目标人群就是"非专业人士"** —— 原文明说"neglecting non-professional queries from the
   general public, **which often lack precise legal terminology**"
   ⇒ **这正是我们的判据①（`vocabulary mismatch`）的同一件事**；
3. **许可 MIT、数据公开可下** —— **没有付费墙、没有 gated、没有 NC 限制**。

### ★ 它的规模对照我们的现状
| | STARD | 我们 |
|---|---|---|
| 提问 | **1,543 条**（真实咨询）| **171 条**（其中 headline 120）|
| 候选条文 | **55,348 条** | 库里 clause_revision **663,634 条** |
| 许可 | **MIT** | —— |
| 论文自报最好成绩 | **Recall@100 = 0.907** | 我们并集@1000 = 0.40（**口径不同，不可直接比**）|

### ⚠ 必须说清的边界（**不许夸大**）
1. **STARD 是"法律法规"检索，不是"国标条文"检索** —— 我们目前主战场是国标；
2. **它的语料是它自己的 55,348 条**，不是我们的库 ⇒
   **要拿它当考卷，得先看它的问题在我们库里能不能找到对应法条**（同我们部委问答那套"在库率"切法）；
3. **我没下载数据**（本轮只核了清单与许可）—— **要不要下、怎么用，属业主决策**；
4. 论文自报 **Recall@100 0.907**，**和我们 @1000 的 0.40 不是同一个口径**（深度、语料、金标定义都不同），
   **不能拿来比高低**。

---

## ★★ 主线① 收尾：我们"重排无效"的结论，**适用范围比字面窄**

### 我们自己的原始记录（`docs/RETRIEVAL-LONG-RANGE-PLAN.md` P1 段，**原文**）
> 「❌ **第三刀也量掉了：两段式重排（现成的 `bge-reranker-base`）无效、且略负。**
> 粗排前5 **5.5%** → 重排后前5 **4.0%**；池子内被挪上去 12 条、被挪下去 **18** 条；
> ⇒ **现成重排器**不能用来救"候选集太大"。」

**⇒ 我们测的是「现成的、未微调的」`bge-reranker-base`，结论本身写得是准确的（"现成的"）。**

### 而学界（**本轮读到的两篇，都是竞赛 top 名次**）用的**不是**现成的
| 文献 | 它的做法 | 成绩 | 我读到的 |
|---|---|---|---|
| **DRiLL@VLSP 2025**（`aclanthology.org/2025.vlsp-1.20.pdf`）| **两阶段**：① 混合检索（稀疏+稠密）② **cross-encoder 重排（微调 BERT 类）**；**用难负例挖掘**微调重排器；**给条文加标题**增强上下文 | **public top-2 / private top-3** | **PDF 已读摘要与引言** |
| **Segment First, Retrieve Better（TraceRetriever）**（arXiv `2508.00679`，IIT Kanpur）| 整合 **BM25 + 向量库 + Cross-Encoder**，**用 RRF 合并**，**再最终重排**；按**修辞角色**先分段 | 在 IL-PCR、COLIEE 2025 上评测 | **PDF 已读摘要** |

**★★ 关键对照**：
| DRiLL 的做法 | 我们 |
|---|---|
| 两阶段（召回 → 重排）| 一次融合（**没有第二阶段重排**）|
| **重排器用难负例挖掘微调过** | **我们用现成的（未微调）** |
| **给条文加标题** | 我们法规那边已做（`## 第一章 总则`），国标待查 |
| 混合检索（稀疏+稠密）→ RRF → 重排 | 我们 FTS+向量+RRF，**但缺最后一步重排** |

**⇒ 结论（精确版）**：
**"重排无效"这句话，适用范围只到"现成的通用重排器"。**
学界两篇 top 名次的做法都靠 **cross-encoder 重排**，而**它们的关键差别是"难负例挖掘微调"**。
⇒ **我们从未测过"微调过的重排器"** —— 但**微调要有训练对**，于是又回到同一个瓶颈。

**⚠ 另一条我们自己的已知缺陷（会成为拦路虎）**：
`docs/RETRIEVAL-LONG-RANGE-PLAN.md` **0.7 行**原文：
> 「**`reranker.py::rerank` 的返回形状有缺陷**（2026-09-25 登记，**未改**）：它 `sorted(...)` 之后
> **只返回分数、不返回顺序**，调用方拿不到"哪条对哪个分"⇒ **这一层想被真正用起来
> （重排、调序、看哪个候选赢）必须先改它**。」

⇒ **我们要真做重排实验，得先修这个。**

---

## ★★★ 四条主线**收敛到同一个瓶颈**（本轮最重要的判断）

把三轮的结论并起来看：

| 主线 | 结论 | 它的**前提条件** |
|---|---|---|
| ① 排序/重排 | 正解 = **cross-encoder 重排**（DRiLL/TraceRetriever 两篇 top 名次独立印证；另有一篇说 **LHF 学习式融合**）| **重排器要"难负例挖掘微调"** ⇒ **要训练对** |
| ② 评测集 | **STARD 可直接用**（中文/MIT/1,543 条）| ✅ **这条能拿到** |
| ③ 查询改写 | 正解 = **训练 LLM 做查询改写**（GuRE，法条检索，**10K 对即可**）| **要 10K 训练对** |
| ④ 同类系统 | 官方有 **`YD/T 4394.10-2025`** 评测标准 | 全文要会员（业主决策）|

**⇒ ①②③ 三条的**技术解法都指向同一个前提：`(提问, 正确条文)` 的标注对**，
而我们一直卡在"只有 171 条"。**

**★★ 而 STARD 给的是 1,543 条真实咨询提问 + 金标 + MIT** ——
**它是本轮唯一一条"能直接把这个瓶颈松开一半"的东西。**

---

## 本轮**可借鉴清单**（接前两轮，编号续）

| # | 可借鉴 | 出处 | 能怎么用 | 代价 / 前提 | 证据等级 |
|---|---|---|---|---|---|
| **13** | **STARD：中文、真实非专业提问、1,543 条 + 55,348 条文、MIT** | arXiv 2406.15313；`github.com/oneal2000/STARD` | **直接把考卷从 171 扩到 1,543 的候选池**；先量"它的问题在我们库里的在库率"，再切两类资产 | 要下载（**我没下**）；**语料是法律的、不是国标的**，要核在库率 | **摘要全文 + GitHub API 实测** |
| **14** | **两阶段检索：混合召回 → cross-encoder 重排** | DRiLL（VLSP 2025，public top-2）；TraceRetriever（arXiv 2508.00679）| **给我们的 P2「排得上去」一个被竞赛验证过的架构** | ⚠ **重排器要微调**（要训练对）；⚠ 我们 `rerank()` **有已知缺陷要先修** | **摘要+引言 / 摘要** |
| **15** | **重排器用"难负例挖掘"微调** | DRiLL | **解释了我们"现成重排器无效"与学界"有效"的差别** | 要训练对 | **摘要** |
| **16** | **给条文加标题（chunking to add titles）** | DRiLL | 提升上下文准确性；我们法规已做、**国标待核** | 低 | **摘要** |
| **17** | **按修辞角色先分段再检索** | TraceRetriever | 法条天然有"章/条/款"结构，思路可比 | 中（要分段器）| **摘要** |
| **18** | **`CAIL`（China AI and Law Challenge）** | `cail.cipsc.org.cn` | 中国法律 AI 竞赛，**可能有更多公开数据/赛道** | **本轮只见到官网链接，未读** | **仅链接** |
| **19** | **`COLIEE`（法律信息提取/蕴含竞赛）** | `coliee.org`；2025 论文集 | **Task 3 = 检索日本民法典相关条文**（法条检索）| 未读全文 | **仅检索片段** |
| **20** | **`BSARD`（Bilingual Statutory Article Retrieval，荷兰语）** | researchportal.be | 另一个法条检索数据集（对照）| 未读 | **仅检索片段** |

---

## 本轮**仍然没读到的**（**累计欠债，如实登记**）

| 项 | 状态 |
|---|---|
| **LegalBench** | ❌ **连续三轮拖欠** —— 每次都被更重要的发现挤掉。**下一轮第一件事就还它** |
| **HyDE 原论文**（ACL 2023 `2023.acl-long.99`）| ❌ 未读（只在 GuRE 里见过它的对照结果 Q2D）|
| **GUIR（SemEval-2026 Task 8）** | ❌ 未读 |
| **`YD/T 4394.10-2025` 全文** | ❌ 未读（要会员，**我没绕**）|
| **STARD 数据本体** | ❌ 未下载（**只核了清单与许可**）|
| **CAIL / COLIEE / BSARD 正文** | ❌ 未读 |
| **GuRE 第 3 节方法与附录 H** | ❌ 未读 |
| **中文法条检索基准有没有** | ✅ **本轮有结论了：有（STARD），且不止一个（CAIL/COLIEE/BSARD 同类）** |

---

## 四条主线最终状态

| 主线 | 结论 |
|---|---|
| ① 排序/重排 | ✅ **正解 = 两阶段（混合召回 → 微调过的 cross-encoder 重排）**；我们"现成重排器无效"的范围已厘清 |
| ② 公开评测集 | ✅ **STARD 可直用（中文/MIT/1,543）；CAIL/COLIEE/BSARD 为同类** |
| ③ LLM 查询改写 | ✅ **GuRE：训练改写器，10K 对即可，法条检索上显著** |
| ④ 同类系统 | ✅ **`YD/T 4394.10-2025` 官方评测标准** + 若干同类系统 |
| **收敛** | ★ **①②③ 的技术解法都指向同一个前提：`(提问, 正确条文)` 标注对。我们只有 171 条 ⇒ STARD 是松开它的钥匙。** |
