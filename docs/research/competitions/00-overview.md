# 知识库/RAG 大规模竞赛与评测：历年头部技术路线总览

> **抓取日**：2026-11-05。本报告汇总四条分线调研，不重复全文细节。证据等级与“查不到就说查不到”的纪律沿用 research-protocol；每条关键数字在其源文件里有 URL 与抓取日。

## 1. 一句话结论

> **知识库/RAG 头部竞赛近年的共同赢法，不是“换更强更大的模型”或“候选池更大”，而是“把检索、证据、拒答做成可控模块”：RAG 头部靠 nugget/事实抽取与拒答重标，LiveRAG 头部靠假设答案/多样性重排与去噪，BioASQ 头部靠 snippet 先抽再重排，TREC ToT 头部靠 cue 清单 + 难负样本 + 受控 LLM 补位，TrustBit 头部靠分文档路由 + 父页回链 + 无据 N/A。**

---

## 2. 四条线与文件归属

| 线 | 覆盖 | 头部队伍/对象 | 正文 | 机器账本 |
|---|---|---|---|---|
| **A 线** | KDD Cup CRAG 2024、CRAG-MM 2025 | db3、APEX、md_dh、ElectricSheep、Dianping-Trust-Safety、Team_NVIDIA、cruise、y3h2 | [01-kddcup-crag.md](01-kddcup-crag.md) | [data/line-a.jsonl](data/line-a.jsonl) |
| **B 线** | TREC RAG 2024/2025、LiveRAG 2025、BioASQ 2024/2025、TREC ToT 2024/2025 | IITD-IRL、TREMA-UNH、WaterlooClarke、UTokyo、NITATREC、RMIT-ADMS、Magikarp、RAGtifier、UniTor、BSRC、SRCB、DS@GT | [02-trec-liverag-bioasq-tot.md](02-trec-liverag-bioasq-tot.md) | [data/line-b.jsonl](data/line-b.jsonl) |
| **C 线** | CCKS 2022–2025、CCIR Cup 2025、CCF BDCI、中文 RAG 评测集 | 中科院计算所（CCIR 第 3）、BDCI 特等奖队、BDCI 运营商亚军、RGB/CRUD-RAG/DuReader/C-MTEB | [03-china-ccks-ccir-bdci.md](03-china-ccks-ccir-bdci.md) | [data/line-c.jsonl](data/line-c.jsonl) |
| **D 线** | Amazon KDD Cup 2024、TrustBit ERC 2024/2025 | Team_NVIDIA、AML666、Ilya Ris、Emil Shagiev、Dmitry Buykin | [04-kddcup-other-industrial.md](04-kddcup-other-industrial.md) | [data/line-d.jsonl](data/line-d.jsonl) |

---

## 3. 头部技术路线归纳（跨赛道 8 条）

| # | 路线 | 证据 | 本仓可抄处 |
|---|---|---|---|
| 1 | **可答性/拒答是独立模块** | CRAG：MARAGS 重标把 CRAG 分 −0.204→+0.186；Dianping 课程学习 0.027→0.151。ToT 不属此列，但反证了纯重排不够。 | 无据拒答 + 指标/口径兼容性核对；不要只靠“要谨慎”提示词。 |
| 2 | **假设答案/HyDE 扩召回 + RRF** | LiveRAG RMIT（Hypothetical Answer + Boyer RRF k=60）；TREC 2025 UTokyo（HyDE + 四路 RRF） | 仅作召回补强；假设答案可能幻觉，需要与原 query 并联。 |
| 3 | **多子问题多样性重排** | Magikarp knowledge-aware diverse reranking；TREC 2025 sub-narrative coverage | 多跳/多问先拆子问，再对每子问候选交错合并，避免一个子问吃满名额。 |
| 4 | **Snippet/父页回链** | BioASQ UniTor（snippet 先行+重排锚点）；TrustBit Ilya（chunk→整页） | chunk 命中只作指针，证据回整页/整表；页码/条号回链是硬约束。 |
| 5 | **事实/nugget 抽取 + 跨文档验证** | TREC RAG TREMA-UNH；UIS GINGER；LiveRAG InstructRAG | 先抽 nuggets 再验证多文档互证，再生成；“先事实后回答”。 |
| 6 | **按类型/领域路由提示词** | TrustBit 四类题分提示；NVIDIA Amazon 按 task-type 提示；CRAG APEX 按 domain/dynamism routing | 条文/标准问答按“编号可定位/数值/多跳/拒答”分流，规则少而准。 |
| 7 | **模糊检索先抽 cue，不要先猜实体** | TREC ToT SRCB cue list + 删 cue/同义/误导增强 + 难负样本 1:3:3 | 大白话检索先抽线索清单，但最终排序仍靠候选池与 reranker。 |
| 8 | **后端工程：向量不是必需** | TrustBit 第二名不用向量仍 R=86.3；Dmitry 用 ontology + CBOW 投票；BioASQ 用 BM25 首检 | 强本体场景可用 ontology/精确召回/精确匹配替代或补充向量。 |

---

## 4. 业主两条前提的核查结论

### 4.1 KDD Cup CRAG 是否“最权威、规模最大”

- **CRAG 是目前国际上最完整、把幻觉罚分显性化的 RAG 赛道**（KDD Cup 2024：384 队 / 6,323 提交；2025 CRAG-MM：256 队 / 4,927 提交）。
- **“规模最大”需要口径**：按**总加总**，CCKS 2024 是 11 条赛道合计 2,400+ 队；按**单赛道**，CCKS 人物 KG 问答 223 队 **小于** CRAG 384 队。两条线结论一致，不是单条赛道碾压。
- Amazon KDD Cup 2024 有 **508 队**，单届队伍数超过 CRAG；但它是**多任务购物 LLM 能力赛**，不是知识库/RAG 赛。
- **建议表述**：CRAG 是“RAG 赛道里任务最完整、罚分设计最显性的 KDD Cup 赛道”，不要写成笼统“规模最大竞赛”。

### 4.2 ToT 的定位

- ToT（TREC Tip-of-the-Tongue）是 **known-item retrieval**：“根据模糊记忆找目标”，官方摘要原话。2025 只有 **9 组 / 32 runs**，NDCG@1000 官方指标。
- 它**不是 RAG/知识库竞赛**，但它是本仓“大白话提问、关键词对不上”的同构问题；其 cue→dense→rerank→LLM rerank 管线可借，不可与 CRAG 并列解释 RAG 赛道。

---

## 5. 反证（四线合计）

**搜过的词**（各线在源文件里逐条记录）：
- `RAG 竞赛 被高估 质疑 benchmark 刷分 CRAG leaderboard criticism`
- `KDD Cup CRAG 比赛 方案 过拟合 leaderboard 不可复现`
- `TREC RAG benchmark 被高估 质疑 复现失败 limitations`
- `LiveRAG challenge 争议 LLM-as-a-judge 偏差`
- `BioASQ challenge winner 刷榜 overfitting`
- `Tip of the Tongue TREC 局限 争议 benchmark 质疑`
- `CCKS 评测 含金量 质疑 水赛 / 榜单 刷分 作弊 取消资格`
- `Enterprise RAG Challenge 被高估 质疑 争议 / Amazon KDD Cup 2024 刷榜 overfitting 不可复现`

**命中要点**：
1. **CRAG 官方自承刷榜与提示词攻击**：公开榜曾被刷到 100% accuracy；有人攻击 auto-eval prompt；最终靠私有集 + 人工评测定胜负。
2. **TREC support 评测**：GPT-4o 与人工完全一致仅 56%（post-editing 72%），run-level Kendall >0.79；自动 judge 分数不可当真值。
3. **LiveRAG 自承**：LLM-as-a-judge 高分不必然等于用户满意度。
4. **CCKS 2020**：组织者承认曾有前三名被取消资格（case-by-case / 塞测试答案）；且只审前三名。
5. **TrustBit 榜单含赛后补交**，自承非正式。

**0 命中**：未搜到对 CRAG / LiveRAG / BioASQ 头部方法的独立复现失败报告；未搜到针对 Ilya 方案的复现失败。

---

## 6. 两面账

### 账一：覆盖

| 线 | 登记记录（jsonl） | depth 分布 |
|---|---:|---|
| A 线 | **11** | fulltext 7 / source 1 / readme 2 / metadata 1 / tested 0 |
| B 线 | **22** | fulltext 16 / source 4 / readme 1 / metadata 1 / tested 0 |
| C 线 | **25** | fulltext 5 / source 6 / readme 6 / metadata 8 / tested 0 |
| D 线 | **8** | fulltext 2 / source 4 / readme 1 / metadata 1 / tested 0 |
| **合计** | **66** | fulltext 30 / source 15 / readme 10 / metadata 11 / tested **0** |

> 本仓对任何系统都没有本机复跑；所有 `tested` 均为 0。

### 账二：复核（抽查 ≥10%）

- **A 线**：抽查 14 条，错误 1 条（CCKS 口径写错），错误率 **7.1%**；查不到来源 0 条。
- **B 线**：本线写完后抽查 **12 条**关键数（TREC RAG 93/53、2025 51/25、LiveRAG 70/25、BioASQ 37/700、13b 49/160、ToT 2025 9/32、SRCB 0.6824、BM25 0.1700、dense 0.0514、UFMG 0.2771），全部回原文核对，**错误 0 条**；UDInfo 方法、Amazon/KDD 细节与 TrustBit 正式名次 **无法核实**。
- **C 线**：25 条记录经脚本校验，0 字段错误；冠军身份缺失 4 条属“无法核实”而非错误。
- **D 线**：抽查 **8 条**（Amazon 508 队/20,000 题；TrustBit 7,496 份/46GB 与 100 题；R/G 计分公式；Ilya 49 分钟 123.7；Emil R 86.3；Dmitry 117.5），全部回官方页/仓库核对，**错误 0 条**；TrustBit 正式名次与 AML 细粒度方法 **无法核实**。

**合计错误率**：A 线 1 条 / 全线抽查约 **46 条** ≈ **2.2%**；未核实项已在各线未查证清单具名。

---

## 7. 已知遗漏（明确没做到的）

| 线 | 未查证项 |
|---|---|
| A 线 | vslyu-team（Task 3 第三）方法、dRAGonRAnGers 报告全文、cruise 全文、AcroYAMALEX/BlackPearl/otonadake/gogoogo/NEC_AI_ROCKETS 等分项冠军方法、CRAG-MM 逐队人工明细 |
| B 线 | UDInfo 方法、TREC RAG 2024 retrieval 精确 top-scoring run 与分数、BioASQ Task 13b 官方名次表细节、BioASQ 工业 ROI、ToT 2024 完整榜单 |
| C 线 | CCKS 多赛道冠军身份（2024 CKBQA/人物 KG/知识编辑/零样本抽取、2025 多数任务）、DuReader-RAG 是否存在、CCIR 往届知识库问答赛道 |
| D 线 | TrustBit ERC 2025 正式名次与官方提交数、ERC 2024 正式榜单、Amazon 第二名细粒度方法、Amazon “submissions” 总数、TrustBit 两个奖金类的技术细节 |

---

## 8. 边界声明

- **分数不可跨赛道、跨年份比较**：语料、指标、硬件、评分口径每年都变；只在同赛道同年内可比。
- **所有结论均据论文/README/榜单原文**；`depth=metadata/readme` 的记录未被当作“借鉴”依据。
- **本报告不做归因**：例如 CCKS 逐年收缩只陈述数字，不猜原因。
- **A 线与 C 线口径对齐**：CCKS “2,400+ 队”为 11 条赛道加总（C 线 §1.4），单赛道 223～1,237 队；A 线 §2 的“CCKS 大 6 倍”只在加总口径下成立。
