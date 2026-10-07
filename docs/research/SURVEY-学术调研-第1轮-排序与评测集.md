# 学术调研 · 第 1 轮：**排序/重排**与**评测集**（对应我们的判据①②）

> **业主 2026-10-07**：「那你继续自己进行调研，**设置个目标自己搜自己找**」。
> 目标 `goal-29bd1eb5…`：**四条主线**（①排序/重排 ②公开评测集 ③LLM 查询改写 ④同类系统）。
> **本页是主线 ①② 的结论。** 规矩：**读到的说读到、没读到的说没读到**；
> 每条给**出处**；**没价值的直说**。

---

## ★★★ 主线① 最重要的一条：**有人做过和我们一模一样的诊断，并给出了解法**

### 文献
**Diagnosing and Mitigating Retrieval Bottlenecks in LLM-Based Cold-Start Recommendation**
（arXiv，`ar5iv.labs.arxiv.org/html/2606.29947`）。**我读到的是完整摘要**（正文未逐段读）。

### 它的摘要原文（关键段）
> 「Large language models (LLMs) are increasingly used as **rerankers** in recommender systems…
> We test this assumption with a five-domain benchmark **that explicitly separates reranking quality
> from retrieval coverage**. In a **positive-controlled regime where the gold item is guaranteed present**,
> calibrated **LLM rerankers fail to consistently outperform** strong collaborative and content baselines…
> In a **retrieval-realistic regime where the gold item is not injected**, the bottleneck is more severe:
> **standard single retrievers place the gold item in a 200-item pool only 4.6–22.9% of the time**…
> We introduce **LHF, a validation-trained learned hybrid fusion layer over a multi-retriever union pool**…
> **LHF is the only combiner we test that beats every single** …」

### ★ 它和我们做的事**几乎一一对应**（这是本轮最硬的对照）

| 他们 | 我们（已实测） |
|---|---|
| **明确把「重排质量」与「召回覆盖」分开** | 我们的分档 **L1（六路 1000 都没召回）/ L2（排不上）** |
| **"保证 gold 在池子里"的对照设定** | 我们 P2 实验 #1：把上限 20→100，**候选救回池子** |
| 该设定下**重排器跑不赢强基线** | `prod_caps.hit` **+9.17pt**，但 `fused@20` 只 **+1.67pt** |
| 单路检索 gold 进 **200 条池子只有 4.6–22.9%** | 我们 `union.prod_caps.hit` = **13.33%**（同在区间内）|
| **解法 = LHF：在多路并集池上训练的「学习式混合融合层」** | 我们的融合是**手写 RRF 权重 + 常数 60** |

**⇒ 三条结论：**
1. **我们的诊断方向被独立证实**（"候选在池子里但排不上去"是这类系统的通病，不是我们实现得差）；
2. **他们给出的解法是「学习式融合」**，而我们的计划明写「**不引入学习式排序（没有标注数据）**」；
3. **⚠ 那条禁令的根因是"没有标注数据"，不是"学习式排序没用"** ⇒
   **只要能拿到标注数据，这条禁令就失去了依据。**（这把主线①和主线②连起来了。）

**⚠ 诚实边界**：那是**推荐系统冷启动**场景，不是法条检索；我**只读了摘要**，没读它的实验细节。

---

## ★★ 主线② 的核心发现：**"给定问题→找出法条"的公开基准是存在的，但不是中文**

### （1）**ALQAC —— 法律问答竞赛（已办 5 届）**

**来源**：KSE 2025 会议论文集中"Flame Reavers@ALQAC 2025"一文（`kse2025.kse-conferences.org`）。

**它的子任务与指标**（我从 ViLegalLM 论文的图 1 读到，原文列出了 ALQAC 的全套任务）：

| 子任务 | 评测指标 |
|---|---|
| **ALQAC-IR**（信息检索 / **法条检索**）| **nDCG@10, MRR@10, MAP@100** |
| ALQAC-EQA（抽取式问答）| Exact Match, F1 |
| ALQAC-MCQ（多选）| Precision, Recall, F1（macro）|
| ALQAC-TF（判断）| Precision, Recall, F1（binary）|

**★ 对我们的两点直接含义：**
1. **`ALQAC-IR` 就是"给定问题 → 找出相关法条"**，**和我们判据②要量的是同一件事**；
2. **学界用 `nDCG@10 / MRR@10 / MAP@100`，我们用的是自创的"前五命中率"** ——
   **指标该换**（至少该同时报，否则没法与任何外部工作对齐）。

**数据可得性（实测）**：
· **HuggingFace `nguyenlab/ALQAC`**：文件结构为
  `ALQAC_2023|2024/{law.json, train.json, public_test.json, public_test_GOLD.json,
  private_test.json, private_test_GOLD.json, README.md}` ——
  **有 `law.json`（法条语料）+ `public_test_GOLD.json`（公开金标）**，形状正是我们要的；
· ⚠ **但它是 gated 的**：拉文件返回 **HTTP 401「Access … is restricted. You must have access
  to it and be authenticated」** ⇒ **需要 HuggingFace 账号并申请访问**（**我没登录、也没申请**）；
· 另有 **Kaggle `longvu2317/alqac-2025`**（同样需账号）；
· ⚠ **语言是越南语** ⇒ **不能直接当我们中文的考卷**，但**任务设计、金标组织方式、指标可以直接学**。

### （2）**ViLegalLM（ACL Findings 2026）—— 它怎么解决"数据稀缺"**

**出处**：Nguyen, Nguyen, Nguyen. **ViLegalLM: Language Models for Vietnamese Legal Text**.
Findings of ACL 2026, pp. 36136–36150. `https://aclanthology.org/2026.findings-acl.1801/`
（**我读到了全文抽取**，15 页 / 71,281 字）。

**摘要原话**：
> 「To mitigate **data scarcity**, we construct **three synthetic datasets using LLM-based generation
> and hard negative mining** for True/False QA, Multiple Choice QA, and Natural Language Inference.」

**它的仓库（`github.com/ntphuc149/ViLegalLM`，我读了 README）**：
· **许可：Apache 2.0**（宽松，可商用）；
· 语料：**16GB 越南法律文本**（HF `ntphuc149/ViLegalText`）；
· **`Datasets/` 下只有三个合成数据集**：`ViLegalTF/`、`ViLegalMCQ/`、`ViLegalNLI/`；
· **`Source codes/Fine-tuning/Information Retrieval/` 也在**（检索的微调代码公开）；
· ⚠ 仓库自己写着：「**These models are intended for research purposes only**」。

**★★ 它给出的模式很清楚，而且正好回答我们的问题：**
| 任务 | 它的数据从哪来 |
|---|---|
| **信息检索（IR）** | **用现成基准**（ALQAC-IR、ZALO-IR）——**不自己造** |
| True/False、多选、NLI | **没有现成基准 ⇒ 用 LLM 生成 + 难负例挖掘造合成数据** |

**⇒ 这就是我们该照抄的决策规则**：
**有现成基准就用现成的；没有的，用 LLM 生成 + 难负例挖掘自己造。**
而**中文的法条检索基准，我到目前为止没找到现成的** —— 所以对我们而言，
大概率是"**自己造**"这条路（或用王芳 2023 那套题集）。

### （3）其它检索/评测线索（**只读了标题或摘要，未读全文**）

| 文献 | 出处 | 我读到的 |
|---|---|---|
| **DRiLL@VLSP 2025: A Simple Two-Stage Retrieval Framework for Vietnamese Legal Document Retrieval** | `aclanthology.org/2025.vlsp-1.20.pdf` | **已下载 PDF（80KB）未细读**；标题即结论：**两阶段检索** |
| **EDM Team's Approach in DRiLL@VLSP 2025: A Multi-Stage End-to-End Architecture** | `aclanthology.org/2025.vlsp-1.19.pdf` | 未读；标题即**多阶段架构** |
| **Flame Reavers@ALQAC 2025: Integrating Learned Rankers and LLM Reasoning in a Dynamic Hybrid Architecture** | IEEE `11289384` | 未读全文；**据 KSE 论文集检索片段**：该队**两个子任务都排第一** |
| **Segment First, Retrieve Better: Realistic Legal Search via Rhetorical Role-Based Queries** | arXiv `2508.00679` | **已下载 PDF（403KB）未细读**；标题即思路：**按"修辞角色"先分段再检索** |
| **LegalBench**（前一轮发现）| arXiv | 法律推理基准，**未读** |

---

## 本轮产出的**可借鉴清单**（每条：出处 / 能怎么用 / 代价 / 我读到的是什么）

| # | 可借鉴 | 出处 | 我们能用它做什么 | 代价 / 前提 | 证据等级 |
|---|---|---|---|---|---|
| **1** | **把"重排质量"与"召回覆盖"分开评测** | Retrieval Bottlenecks 论文 | 我们已经在做（L1/L2 分档）—— **可引用它作为方法论依据** | 无 | **摘要** |
| **2** | **学习式混合融合层（LHF）** | 同上 | **替掉手写 RRF 权重** —— 直接针对我们判据② | ⚠ **要有验证集标注数据**；我们现在没有 | **摘要** |
| **3** | **ALQAC-IR 的任务定义与指标（nDCG@10/MRR@10/MAP@100）** | ALQAC / ViLegalLM 图1 | **把我们"前五命中率"升级成标准 IR 指标**，才能与外部工作对齐 | 无（纯改指标） | **图 1 原文** |
| **4** | **ALQAC 数据集结构（law.json + public_test + public_test_GOLD）** | HuggingFace `nguyenlab/ALQAC` | 学它的**考卷组织方式**（语料/题/金标分文件） | ⚠ **gated 要 HF 账号申请**；**越南语** | **实测文件清单 + 401 响应** |
| **5** | **"有现成基准用现成的，没有就用 LLM 生成 + 难负例挖掘造"** | ViLegalLM（ACL Findings 2026，**Apache 2.0**） | **我们考卷做不大的正解**：中文没有现成基准 ⇒ **自己造** | 要写生成 + 难负例挖掘的流水线 | **全文抽取** |
| **6** | **两阶段 / 多阶段检索架构** | DRiLL、EDM（VLSP 2025） | 对照我们"六路并行 + 一次融合"的架构 | 未读全文，**先不采信** | **仅标题** |
| **7** | **按"修辞角色"先分段再检索** | arXiv 2508.00679 | 法条天然有"章/条/款"结构，思路相近 | 未读全文 | **仅标题** |

---

## 对判据①②的**实验提案**（本轮目标要求）

### 提案 A（对应判据②）：**用标准 IR 指标重报我们的结果**
· **做什么**：把我们的评测从"前五命中率"改成**同时报 `nDCG@10 / MRR@10 / MAP@100`**（我们的逐条结果里**已经有名次**，是纯计算，**不用重跑检索**）；
· **为什么**：现在**没法与任何外部工作对齐**；ALQAC 用这三个，我们换了就能对上话；
· **代价**：**近零**（改 `summarize.py` 的输出，不改检索）；
· **止损线**：这是**加指标不是改算法**，不需要止损线；但**必须保留旧口径**（不许换掉，否则历史数字断档）。

### 提案 B（对应判据②）：**融合层实验 —— 但先确认"没有标注数据"这条禁令还算不算数**
· **现状**：`docs/RETRIEVAL-LONG-RANGE-PLAN.md` §P2 明写「**不引入学习式排序（没有标注数据）**」；
· **本轮发现**：那篇论文的解法（LHF）**正是学习式融合**，而它成立的前提是**有验证集**；
· ⚠ **所以我不擅自开这个实验** —— **这是计划里的一条明确边界**，要动它得**先拿到标注数据**，
  或者**由业主裁定"用 LLM 生成的弱标注也能算数"**（那是结构性变化，按仓规要留痕）；
· **若要走**：止损线口径同 E1/E3b（**±6pt**），且**必须先冻结·先写止损线**。

### 提案 C（对应"考卷做不大"）：**照 ViLegalLM 的模式造我们自己的题**
· **做什么**：**不做"从零编题"，而是照王芳 2023 的三条同义规则 + 四类错字规则**，
  把现有 171 条**纯文本改造**成"同义版 / 错字版"（**不需要新数据源**）；
· **为什么**：这是**本轮唯一一条不依赖外部数据、今天就能动手**的路；
· **代价**：纯文本改造，**不需要模型、不需要标注**；
· **止损线**：这不是检索实验，不需要止损线；但**改造规则要先冻结**（不然"改多难"会随手调）。

---

## 本轮**没做完 / 没读到**的（如实登记，不许假装）

| 项 | 状态 |
|---|---|
| `DRiLL@VLSP 2025` 全文 | **PDF 已下载，未读** |
| `Segment First, Retrieve Better`（arXiv 2508.00679）| **PDF 已下载，未读** |
| `Flame Reavers@ALQAC 2025`（IEEE）| **未读全文**（IEEE 可能付费；只读到检索片段）|
| ALQAC 数据集本体 | **未下载**（HF 需登录；**我没登录、没申请**）|
| LegalBench | **未读** |
| 中文法条检索基准 | **本轮没找到**（下面的主线③④继续找）|
| 主线③（LLM 查询改写）、主线④（同类系统） | **本轮未开始** |
