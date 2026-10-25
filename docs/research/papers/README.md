# 外部原件存放处（调研克隆物，按主题分类）

> **为什么在这里**：这些原件是从外部下载的（`trec.nist.gov` / `ar5iv` / arXiv），而**下载过程容易断**。
> 所以：**原件落在本目录（不入库）**，**取得方式与校验值记在这里（入库）**。
> ⚠ 与本仓 `docs/research/dsh-official/` 的约定一致：**原始外部资料不入库，入库的是索引与清单**。

## 一、目录结构（2026-10-25 分类整理）

```
docs/research/papers/
├─ README.md                      ← 本文件（索引 + 复现命令 + 校验值）
├─ trec-tot-2023-2025/            ← TREC Tip-of-the-Tongue 赛道原件（9 份）
└─ dsgt-2025/                     ← DS@GT 参赛队论文（HTML + 纯文本提取）
```

按**调研主题**分类，不按文件格式分类：同一主题的官方总览、冠军方案、参赛论文放在一起，读的时候不用来回跳。

## 二、`trec-tot-2023-2025/` —— TREC ToT 赛道（9 份）

| 文件 | 字节 | SHA256 前 16 | 是什么 |
|---|---:|---|---|
| `Overview_tot_trec32.pdf` | 613,768 | `1DCA7365434C1258` | **2023（TREC 32）官方总览**：23.16 万维基页、11 队 33 run，冠军 CMU-LTI 0.5554 |
| `Overview_tot_trec33.pdf` | 385,422 | `3F3C34B73BC86184` | **2024（TREC 33）官方总览**：318.5 万维基页、6 队 18 run，冠军 h2oloo 0.8159 |
| `Overview_tot_trec34.pdf` | 708,301 | `28C26F388A2C92EF` | **2025（TREC 34）官方总览**：640.8 万维基页、9 队 32 run，冠军 SRCB 0.6824 |
| `SRCB.mllm.tot.pdf` | 118,267 | `8946BE8909B60E27` | **2025 冠军方案全文**（8 页）：cue list 改写 → 稠密检索 → 三级重排 → RRF |
| `YaleNLP.tot.pdf` | 268,871 | `7A9AB79C60EAE6C5` | 2024 参赛（第 4）：pointwise + listwise round-robin，`+0.0625` NDCG@1000 |
| `IISER-K.tot.pdf` | 526,513 | `67649A54079FCF2A` | 2024 参赛：纯 BM25 + 四阶段 LLM 改写，0.4239（最便宜的可比基线） |
| `webis.biogen.rag.tot.pdf` | 554,185 | `E46F25D79B5B2BB4` | 2024 参赛（Webis）：BM25-F + LLM 查询缩减变体 + monoT5 两级重排 |
| `webis.tot.pdf` | 369,323 | `DF29FCF40FA4A05B` | 2025 参赛（Webis）：同上路线，闭源 GPT 换开源模型 |
| `UAmsterdam.tot.pdf` | 256,212 | `ABCD82610C8E79C3` | **2025 负面结果（最值得读）**：合成语料 +25.4% vs 真人 +2.7% 不显著；RM3 三个划分全变差 |

**缺口**：2023 冠军 CMU-LTI 与 2024 冠军 h2oloo **都没交参赛论文**（只有总览叙述与官方提交表单那一栏）；2022 年**没有这个赛道**（TREC 31 议程页无该总览）。

## 三、`dsgt-2025/` —— DS@GT 参赛队论文（2 份）

| 文件 | 字节 | SHA256 前 16 | 是什么 |
|---|---:|---|---|
| `mst.html` | 219,422 | `902E964F14950D72` | arXiv 2602.10321 的 **ar5iv HTML**（单轮改写 + 多阶段混合重排） |
| `mst.txt` | 85,836 | `98421849B76A7605` | 上一行的**纯文本提取**（84,478 字符，脚本去标签所得，非手抄） |

## 四、怎么重新取得（可复现，2026-10-25 实测）

⚠ **三条路里只有第三条通：**
* ❌ `web_fetch` → **不支持 PDF**（报 `unsupported content type`）
* ❌ `https://r.jina.ai/<url>` → **401**（`AuthenticationRequiredError`，IP 信誉被限）
* ✅ **`curl` 带浏览器 UA 直连**（下面的命令）

```powershell
$UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
# 三份官方总览（按年份目录区分，文件名都叫 Overview_tot.pdf）
curl.exe -sL --max-time 90 -A $UA "https://trec.nist.gov/pubs/trec32/papers/Overview_tot.pdf" -o Overview_tot_trec32.pdf
curl.exe -sL --max-time 90 -A $UA "https://trec.nist.gov/pubs/trec33/papers/Overview_tot.pdf" -o Overview_tot_trec33.pdf
curl.exe -sL --max-time 90 -A $UA "https://trec.nist.gov/pubs/trec34/papers/Overview_tot.pdf" -o Overview_tot_trec34.pdf
# 参赛队论文（同一目录下按文件名取）
curl.exe -sL --max-time 90 -A $UA -e "https://trec.nist.gov/pubs/trec34/" "https://trec.nist.gov/pubs/trec34/papers/SRCB.mllm.tot.pdf" -o SRCB.mllm.tot.pdf
# DS@GT 那篇的 HTML（ar5iv 通；arXiv 的 /abs 页只有摘要）
curl.exe -sL --max-time 120 "https://ar5iv.labs.arxiv.org/html/2602.10321" -o mst.html
```

**下完必须验头**：真实的 PDF 以 `%PDF` 四个字节开头。

```powershell
$b = [System.IO.File]::ReadAllBytes("SRCB.mllm.tot.pdf")[0..3]
($b[0] -eq 0x25 -and $b[1] -eq 0x50 -and $b[2] -eq 0x44 -and $b[3] -eq 0x46)  # True = 是 PDF
```

⚠ 第一轮曾把 `DSGT.tot.pdf` 猜错成 276 字节的 404 页而没察觉——**文件大小异常就是信号**。

**读的入口**：`read_pdf` 工具（`focus:"toc"` 看目录、`pages` 指定页、返回的 `cursor` 续读）；本机 2026-10-25 实测 `read_pdf` 依赖的 MinerU 服务曾不可用，退化为 PyMuPDF 抽正文读，页码记 PDF 物理页。

## 五、还没拿到的（如实登记）

| 想拿 | 卡在哪 |
|---|---|
| **2023 冠军 CMU-LTI / 2024 冠军 h2oloo 的方法论文** | 两届**都没交论文**，只能读总览叙述与提交表单 |
| `TOMT-KIS` 原文（128 万条英文电影查询） | 未下；只在总览与 DS@GT 综述里读到规模 |
| **BLUR 基准原文**（Wang et al.） | 只从别人转引里看到数，**未找** |
| **CLEF Social Book Search（2011–2016）** | 只从 UvA 那篇参考文献看到名字，**未找** |
| **中文条款级检索的公开竞赛原件** | 确认**不存在**（见 `../kb-at-scale/70-competitions.md` §五） |
