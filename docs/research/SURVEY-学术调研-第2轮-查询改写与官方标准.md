# 学术调研 · 第 2 轮：**LLM 查询改写**与**同类系统/官方评测标准**

> 接第 1 轮（主线①②：排序/重排、公开评测集）。**本页是主线 ③④ 的结论。**
> 规矩不变：**读到的说读到、没读到的说没读到**；每条给出处；**没价值的直说**。

---

## ★★★ 主线③ 最重要的一条：`GuRE` —— **"法条检索的生成式查询改写器"，和我们判据①是同一件事**

### 文献
**GuRE: Generative Query Rewriter for Legal Passage Retrieval**. Findings of the **NLLP 2025**
（Natural Legal Language Processing workshop），`https://aclanthology.org/2025.nllp-1.31/`。
代码：`github.com/daehuikim/GuRE`。**我下载了 PDF 并抽了全文**（已读摘要、引言、第 5 节分析）。

### 它的摘要原文（关键句）
> 「**Legal Passage Retrieval (LPR) systems are crucial** as they help practitioners save time when
> drafting legal arguments. However, it remains an underexplored avenue. **One primary reason is the
> significant vocabulary mismatch between the query and the target passage.**
> To address this, we propose a simple yet effective method, the **Generative query REwriter (GuRE)**.
> We leverage the generative capabilities of LLMs by **training the LLM for query rewriting**.
> "Rewritten queries" help retrievers to retrieve target passages by **mitigating vocabulary mismatch**.
> Experimental results show that GuRE **significantly improves performance in a retriever-agnostic
> manner, outperforming all baseline methods**. Further analysis reveals that **different training
> objectives lead to distinct retrieval behaviors, making GuRE more suitable than direct retriever
> fine-tuning for real-world applications.**」

### ★ 术语对齐（**这一条本身就有用**）
**我们叫「换词可对 / 53% 一个字都对不上」，学界叫 `vocabulary mismatch`（词汇不匹配）。**
GuRE 的题目就是"法条检索"，**和我们是同一件事**。

### ★★★ 它的 Table 2 把"词汇不匹配"量化了（**这张表我们该记住**）
比较"生成物"与**目标条文**的相似度（10K 测试集）：

| 方法 | BLEU | ROUGE-L | BertScore-F | 字数 |
|---|---|---|---|---|
| **目标条文本身** | — | — | — | 50.21 |
| **原始提问（Query）** | **5.75** | **18.98** | 75.61 | **123.99** |
| Q2D（HyDE 式**伪文档**）| 8.56 | 19.19 | 78.6 | 88.19 |
| Q2D-CoT | 11.86 | 27.28 | 80.1 | **36.28** |
| **GuRE（改写后的查询）** | **59.43** | **67.62** | **90.92** | 50.90 |

**三条判读（都对我们的判据①有直接含义）：**
1. **原始提问与目标条文的 BLEU 只有 5.75、ROUGE-L 18.98** —— **"词汇不匹配"的直接量化**。
   我们的"53% 一个字都对不上"是同一现象的另一种量法（我们用"零重合率"，它用 BLEU/ROUGE）；
2. **"生成伪文档"（HyDE 那条路）在法条检索上不行**（Q2D BLEU 8.56，几乎没改善），
   **"把提问改写成条文体"才行**（GuRE 59.43，**约 10 倍**）；
3. **改写把 124 字的长提问压到 51 字** —— 与目标条文长度（50.21）几乎一致
   ⇒ **改写不只是换词，还在"把提问写成答案会长的样子"**。

### ★★ 它的数据需求：**10K 就够**，而且**有专门一节讲数据受限**
**§5.2 Generalizability under Data Constraints 原文**：
> 「Results show that **GuRE trained on only 10K cases already outperforms retriever fine-tuning
> across all retrieval pool settings**. When trained on 100K cases… performance further improves.
> These findings demonstrate that **GuRE remains robust under limited-resource conditions**.」

**§5.3 还给了一个机理解释**（对我们理解"为什么别直接微调检索器"有用）：
法条引用是**长尾分布**；**微调检索器用的"批内负例"会把高频条文当负样本**，
所以**它越训越差，而 GuRE 相反**。

### ★ 另一条硬结论
> 「**mitigating vocabulary mismatch is significantly more effective than training the retrievers**」
（缓解词汇不匹配，比训练检索器有效得多。）

### ⚠ 对我们的现实差距（**不许含糊**）
· GuRE **是"训练"出来的改写器**，需要 **(提问, 目标条文) 训练对**，它的量级是 **10K**；
· **我们只有 171 条**（headline 120）；
· ⇒ **要照它做，先得把训练对做到千级/万级**。而我们**手里已经有**：
  ① 171 条带金标条款的题；② **`eval/lay-phrasing/gen-V2.jsonl` 的 1,832 条外行说法**
  （500 术语 × 4 口吻）；③ 王芳 2023 的三条同义改写规则 + 四类错字规则。
  ⇒ **这三样合起来，是"把 171 扩到千级"最现实的原料**（**纯文本改造 + 现有语料，不需要新数据源**）。

---

## ★★★ 主线④ 最重要的一条：**中国有一份现行的行业标准，专门讲"知识问答系统怎么评估、验收"**

### 标准信息（**我从标准平台读到完整元数据**）
| 项 | 值 |
|---|---|
| **标准号** | **`YD/T 4394.10-2025`** |
| **名称** | **自然语言处理技术及产品评估方法 第10部分：知识问答系统** |
| **适用范围（原文）** | **「本文件适用于指导对知识问答系统的评估、验收等工作」** |
| 状态 | **现行**（发布 2025-08-19，**实施 2025-12-01**）|
| ICS / 中标分类 | 35.240 / L67 |
| **起草单位** | **北京大学、中国信息通信研究院、南京新一代人工智能研究院有限公司、北京邮电大学、电子科技大学、中国科学院自动化研究所、哈尔滨工业大学、苏州大学** |
| 起草人 | 邓志鸿、李子恒、刘一廷、夏惟、董晓飞、吴思奇、张学强、张丹、陶玥、双锴、王玉龙、张忠宝、刘峤、蓝天、周玉、翟飞飞、亢晓勉、赵阳、赵妍妍、王中卿 |
| 归口 / 发布 | 中国通信标准化协会（CCSA）/ **工业和信息化部** |
| 出处 | `spc.org.cn/online/10857c719a8636169e5de7b316d2f5f4.html`；`std.samr.gov.cn`（全国标准信息公共服务平台）|

**同系列另外两条**（同一批发布）：
· **`YD/T 6522-2025` 面向应用场景的自然语言处理模型评估方法**；
· **`YD/T 6521-2025` 基于深度神经网络的音频结构化框架**。

### ★ 对我们的三条含义
1. **这是官方评测依据** —— 我们的产品若要"评估、验收"，**应当按它来**；
   它比学术论文**更权威、更新（2025-12 实施）**，而且**是"知识问答系统"专门的标准**；
2. **它很可能规定了评测指标与测试集构造方法** —— **那正是我们"尺子"问题的官方答案**，
   可能**比王芳 2023（学术）更该优先看**；
3. ⚠ **全文要会员**（平台写明"开通会员免费在线看10万余条国内标准"）
   ⇒ **我没读全文，如实登记**。买不买、怎么拿，**属业主决策**。

### ⚠ 顺带查出的一个**真实的库缺口**
**我们库里 `YD`（通信行业标准）总数 = 0**；`%4394%`、`%自然语言处理%`、`%知识问答%` **全部 0 条**。
⇒ **这类"AI/信息化"行业标准，我们一条都没有** —— 若产品要谈"符合 YD/T 4394.10"，
**得先把这份标准本身入进库**。

---

## ★ 主线④ 其它同类系统（**只读到标题/摘要，未读全文**）

| 文献 | 出处 | 我读到的 |
|---|---|---|
| **Evaluating LLM Accuracy in Referencing Danish Building Regulations** | Springer（Cooperative Design, Visualization, and Engineering），`dl.acm.org/doi/abs/10.1007/978-3-032-06952-8_3` | 未读（疑付费）；**标题即结论**：评测 LLM **引用建筑法规**的准确性 —— **正对我们"修厂房"那条答不好的题** |
| **Generative knowledge-guided review system for construction disclosure documents** | ScienceDirect `S1474034625005117` | 未读；施工披露文档的生成式审查 |
| **Implementasi Sistem Asisten Kepatuhan ISO/IEC 27001 Berbasis RAG** | ITS repository `141648` | 未读；ISO 27001 合规助手（RAG），印尼语 |
| **OsteoRAG: RAG for evidence-based osteoporosis knowledge management** | SAGE `10.1177/00368504261489884` | 未读；**有一条**：他们用 **50 个开放式问题 + 3 位骨科医生盲评** 做评测 —— **"专家盲评"这个做法可参考** |
| **（幻觉分类）** | IEEE `11631821` | 未读；**据检索片段**：把幻觉分成 OH（其它幻觉）/ NH（无幻觉）等类 |

---

## 本轮产出的**可借鉴清单（③④）**

| # | 可借鉴 | 出处 | 能怎么用 | 代价 / 前提 | 证据等级 |
|---|---|---|---|---|---|
| **8** | **`vocabulary mismatch` 这个术语 + 它的量化方式（BLEU/ROUGE 比"提问"与"目标条文"）** | GuRE（NLLP 2025）| **把我们"零重合率 53%"换成/补上 BLEU·ROUGE 口径**，才能和外部对齐 | 无（纯计算） | **全文抽取** |
| **9** | **"把提问改写成条文体"优于"生成伪文档（HyDE）"** | GuRE Table 2 | **给我们判据① 的路线选择提供了实证**：不要走 HyDE，走"改写" | 无 | **全文抽取（表）** |
| **10** | **训练改写器只需 10K 对，且显著优于微调检索器** | GuRE §5.2/§5.3 | **给我们判据① 的可行性背书** —— 也从机理上解释了我们**没有**直接微调检索器是对的 | 要造到 10K 对 | **全文抽取** |
| **11** | **`YD/T 4394.10-2025`（知识问答系统评估、验收）** | 工信部 / CCSA，2025-12-01 实施 | **官方评测依据** —— 我们的"尺子"该优先按它，而不是只按学术论文 | ⚠ **全文要会员**；另要**把标准本身入进我们库** | **标准平台元数据（原文）** |
| **12** | **专家盲评（3 位领域专家评 50 个开放问题）** | OsteoRAG（SAGE）| 我们的 AI 复核若要与"人评"对标，这是可引用的做法 | 要找到专家 | **仅检索片段** |

---

## 本轮**没做到 / 没读到**的（如实登记）

| 项 | 状态 |
|---|---|
| **`YD/T 4394.10-2025` 全文** | ⚠ **未读**（平台要会员；**我没绕**）|
| **GuRE 的训练细节（第 3 节方法、附录）** | 我读了**摘要/引言/第 5 节分析**，**第 3 节方法只掠过**；**§5.3 之后的附录 H（损失函数分析）未读** |
| **HyDE 原论文**（ACL 2023 `2023.acl-long.99`）| **未读**（只在 GuRE 里看到它的对照结果 Q2D）|
| **GUIR（SemEval-2026 Task 8，免训练多查询融合）** | **未读** |
| **LegalBench** | **仍未读**（连续两轮拖欠）|
| 主线②的"中文法条检索基准" | **两轮都没找到** —— 下一轮继续找，或以"确实没有"结案 |
| 上一轮下载未读的两篇 PDF（DRiLL、Segment First）| **仍未读** |

---

## 至此，四条主线的进度

| 主线 | 状态 |
|---|---|
| ① 排序/重排 | ✅ **有明确结论**（Retrieval Bottlenecks + LHF；ALQAC-IR 指标）|
| ② 公开评测集 | ✅ **有明确结论**（ALQAC 存在但越南语且 gated；ViLegalLM 的造数据模式）**，但中文基准两轮未找到** |
| ③ LLM 查询改写 | ✅ **有明确结论**（GuRE —— 法条检索 + vocabulary mismatch + 10K 即可）|
| ④ 同类系统 | ✅ **有明确结论**（**`YD/T 4394.10-2025` 官方标准** + 几个同类系统）|
