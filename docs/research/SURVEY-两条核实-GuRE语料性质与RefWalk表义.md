# 两条待核实的**核查结果**（GuRE 的语料性质 / RefWalk 的表义）

> **业主 2026-10-07**：「把两条还没核实的补上」。
> 两条 = ① GuRE 的语料到底是"判例段落"还是"法条"；② RefWalk 的 Table 3 列义。
>
> **结论：两条都核出来了，而且①的结果要求我下调对 GuRE 的采信。**

---

## 一、★ GuRE 的语料 = **美国联邦判例的段落**，**不是法条** —— 我的采信要下调

### 1.1 任务定义（论文 §3.1，**原文**）
> 「**LPR involves retrieving the most relevant passage `p_q` based on an ongoing context `q`**,
> where `q` serves as the query for the retriever. Given a set of candidate passages
> P_collection = {p1, …, pn}, our goal is to **identify `p_q` ∈ P_collection that can support `q`
> during the legal document drafting.**」

**⇒ 它的 query 是「律师起草文书时正在写的**专业论述上下文**」，目标是「**能支持该论述的判例段落**」。**
**⇒ 不是"普通人问一句话 → 找适用法条"。**

### 1.2 语料（论文 §5.3，**原文**）
> 「**Citations in U.S. federal precedents** follow a long-tailed distribution, with the **top 1% of
> passages** accounting for 18% of all citations, while 64% receive only one citation」
> ⇒ 「Thus, GuRE may be more suitable for LPR, where **frequently cited passages are repeatedly
> referenced**.」

**⇒ 语料 = 美国联邦判例（U.S. federal precedents），单位 = 判例段落（passage）。**

### 1.3 ★★ 还有一条我必须补上的（**论文 §3.2 原文**）
> 「**Due to the absence of prior research on LPR**, we compare GuRE with strong baselines as follows.」

**⇒ 论文自己承认：这个任务此前没有研究。** ⇒ **"超过所有基线"的含金量要打折**
（基线是作者自己挑的，不是社区公认的强基线）。

### 1.4 ★★★ 它的主表（**我这次把绝对数字全核了**，Table 1）
（每行 9 个数 = 3 个指标 × 3 种 target 数量；下表取第一个指标 `nDCG@10`）

| 方法 | nDCG@10 |
|---|---|
| **ModernBert（现成，未微调）** | **7.11** |
| ModernBert + Q2D（HyDE 式伪文档）| 6.67 |
| ModernBert + Q2D-CoT | 7.47 |
| **ModernBert-FT（微调过的检索器）** | **14.12** |
| **ModernBert + GuRE** | **33.14** |
| **BM25 + GuRE** | **34.88** |
| **DPR（稠密）** | **1.99**（nDCG@10 = 3.92）|
| DPR + Q2D | 1.92 |

**⇒ 三条读数：**
1. **它的稠密基线 `DPR` 差到几乎随机**（nDCG@10 ≈ 3.92）
   ⇒ **"大幅提升"的分母是一个几乎失效的检索器**；
2. **"改查询 > 训检索器"这条仍然成立**（33.14 vs 14.12）；
3. **"改写 > 生成伪文档"也成立**（33.14 vs 6.67）。

### 1.5 ★★ 下调后的采信（**这是本节要交付的结论**）
| 我上一轮的说法 | 修正后 |
|---|---|
| 「GuRE 是**法条检索**的查询改写」 | ❌ **不准确**。它是**判例段落检索**（US federal precedents）|
| 「它证明了这条路在**我们的场景**有效」 | ⚠ **不能这么说**。它的 query 是**律师的专业论述**，我们的是**老百姓的大白话** |
| 「vocabulary mismatch 的诊断」 | ✅ **仍然成立**（诊断是通用的）|
| 「改查询优于训检索器」 | ✅ **仍然成立**（33.14 vs 14.12）|
| 「改写优于生成伪文档（HyDE）」 | ✅ **仍然成立**（33.14 vs 6.67）|
| 「+32.96 nDCG@10」 | ⚠ **要带两个限定**：① 判例段落不是法条；② 分母是 nDCG@10 只有 3.92 的 DPR |

**⇒ 一句话：GuRE 的"路线判断"可借鉴，"效果量"不能搬到我们身上。**

---

## 二、★ RefWalk 的 Table 3 列义 = `R / FullCov / nDCG`（都 @10）+ HIPAA 的 `R`

### 2.1 表头（**原文**）
> 「**Table 3: Retrieval performance on RegOps-Bench and HIPAA-derived QA (Top-10).**」

### 2.2 完整表（**原文数字，我逐个抄的**）
| Method | **RegOps R** | **FullCov** | **nDCG** | HIPAA R |
|---|---|---|---|---|
| **BM25** | 33.8 | 23.6 | 26.4 | 94.0 |
| **Dense** | 54.4 | 35.6 | 45.3 | 90.0 |
| **Dense+Rerank** | 57.0 | **36.4** | 53.5 | 94.0 |
| **LightRAG** | 43.9 | 30.4 | 31.0 | 100.0 |
| **HippoRAG-2** | 41.7 | 27.6 | 25.9 | 97.0 |
| **Query Decomp** | 50.1 | 31.2 | 42.7 | 92.0 |
| **PIKE-RAG** | 54.8 | 35.6 | 52.1 | 97.0 |
| **★ Ours（RefWalk）** | **63.8** | **44.4** | **57.4** | 95.0 |
| w/o multi-view | 59.9 | 41.2 | 54.5 | 94.0 |
| w/o OKG | 60.3 | 41.2 | 54.8 | 98.0 |
| w/o anchor | 60.4 | 41.6 | 55.4 | 94.0 |

### 2.3 ★★★ 四条对我们直接有用的读法
1. **重排能改 nDCG，但救不了"找齐"**：
   `Dense → Dense+Rerank`：R **+2.6**、nDCG **+8.2**，但 **`FullCov` 只 +0.8**
   ⇒ **多跳要的正是 FullCov，所以重排救不了多跳。**
2. **"BM25 还是稠密好"取决于任务**：
   · **STARD**：零样本下 **BM25 > 稠密**；
   · **RefWalk（本表）**：**Dense 54.4 ≫ BM25 33.8**。
   ⇒ **与我们自己文档 §六 的记法一致：「谁赢取决于任务，不是"向量一定好/一定差"」。**
3. **图方法在法规任务上不行（第三次印证）**：
   `LightRAG` 43.9、`HippoRAG-2` 41.7，**都低于朴素 `Dense` 54.4**。
4. **简单方法已经很强**：`PIKE-RAG`（54.8/35.6/52.1）**≈ `Dense+Rerank`（57.0/36.4/53.5）**。

### 2.4 ★ RefWalk 的消融：**没有哪个组件是决定性的**
| 去掉 | R | FullCov | nDCG |
|---|---|---|---|
| （完整）| 63.8 | 44.4 | 57.4 |
| **w/o multi-view** | 59.9（**−3.9**）| 41.2（−3.2）| 54.5（−2.9）|
| **w/o OKG** | 60.3（−3.5）| 41.2（−3.2）| 54.8（−2.6）|
| **w/o anchor** | 60.4（−3.4）| 41.6（−2.8）| 55.4（−2.0）|

**⇒ 三个组件的贡献都在 −2.0 ~ −3.9 之间，彼此接近，没有一个是"决定性"的。**
**⇒ 也就是说：把它拆开，每一块单独去掉，效果只掉一点。这是"三个小改进叠加"的形状，不是"找到一个关键机制"。**

---

## 三、★ 两条核实**合起来改变了我上一轮的哪三处**

| # | 我上一轮说 | 核实后 |
|---|---|---|
| 1 | 「GuRE 是**法条检索**的查询改写，证明这条路在我们场景有效」 | ❌ **它是判例段落检索**；query 是**律师专业论述**，不是老百姓大白话 ⇒ **效果量不能搬** |
| 2 | 「RefWalk 的 Table 3 `Ours` 那行 6 个数字列义未对齐」 | ✅ **已对齐**：Table 3 是 **4 列**（RegOps R/FullCov/nDCG + HIPAA R）；我上一轮看到的"6 个数字"是**另一张表**（我仍未确认它属于哪一节）|
| 3 | 「**多跳指标该用 FullCov**」 | ✅ **成立，而且更强**：`Dense+Rerank` 的 FullCov 只 +0.8，**说明重排这条我们本来最看好的路，对 FullCov 几乎无用** |

---

## 四、⚠ 本轮**仍然没核到**的（继续如实登记）

| 项 | 状态 |
|---|---|
| **RefWalk 里那张"6 个数字"的表** | ❌ **仍未确认属于哪一节**（我核到了 Table 3 是 4 列，但那张表还没定位）|
| **Table 3 里 `Query Decomp` / `PIKE-RAG` 是什么** | ❌ 只见过名字，**没读它们的原文** |
| **HIPAA 那一列为什么所有方法都 90–100** | ⚠ 论文说"扁平结构规则上饱和"，**我没读它那节的正文** |
| **LightRAG / HippoRAG-2 原文** | ❌ 未读 |
| **GuRE 的 query 具体长度/形态** | ⚠ §5.1 那张表给了字数（Target 50.21 / Query 123.99），**但我没核它的 query 是不是"律师写的"**（从任务描述推断的，**未经直接证据**）|
| **COLIEE 2026 那篇正文** | ❌ 未读 |
