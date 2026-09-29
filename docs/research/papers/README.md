# 外部原件存放处（检索文献调研）

> **为什么在这里**：这些原件是从外部下载的（`trec.nist.gov` / arXiv），
> 而**下载过程容易断**（`r.jina.ai` 已被 401 限流、`web_fetch` 不支持 PDF）。
> 所以：**原件落在本目录（不入库）**，**取得方式与校验值记在这里（入库）**。
> ⚠ 与本仓 `docs/research/dsh-official/` 的约定一致：**原始外部资料不入库，入库的是索引与清单**。

## 一、这里有什么

| 文件 | 字节 | SHA256 前 16 | 是什么 | 状态 |
|---|---|---|---|---|
| `SRCB.mllm.tot.pdf` | 118,267 | `8946BE8909B60E27` | **TREC 2025 ToT 冠军方案**（NDCG@1000 = 0.6824） | **已读第 1–5 页**（共 8 页） |
| `UAmsterdam.tot.pdf` | 256,212 | `ABCD82610C8E79C3` | 阿姆斯特丹大学：合成语料 vs 真人语料（"Simulation Gap"） | **已读第 1–2 页**（共 9 页） |
| `mst.html` | 219,422 | `902E964F14950D72` | arXiv 2602.10321 的 ar5iv HTML（DS@GT 那篇：单轮改写 + 多阶段混合重排） | 已读（正文已提取） |
| `mst.txt` | 85,836 | `98421849B76A7605` | 上一行的**纯文本提取**（84,478 字符，脚本去标签所得，非手抄） | ✅ 完整 |

## 二、怎么重新取得（可复现）

⚠ **三条路里只有第三条通：**
* ❌ `web_fetch` → **不支持 PDF**（报 `unsupported content type`）
* ❌ `https://r.jina.ai/<url>` → **401**（`AuthenticationRequiredError`，IP 信誉被限）
* ✅ **`curl` 带浏览器 UA 直连**（下面的命令）

```powershell
$UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
# 冠军方案（8 页）
curl.exe -sL --max-time 90 -A $UA -e "https://trec.nist.gov/pubs/trec34/" `
  "https://trec.nist.gov/pubs/trec34/papers/SRCB.mllm.tot.pdf" -o SRCB.mllm.tot.pdf
# 合成语料那篇（9 页）
curl.exe -sL --max-time 90 -A $UA -e "https://trec.nist.gov/pubs/trec34/" `
  "https://trec.nist.gov/pubs/trec34/papers/UAmsterdam.tot.pdf" -o UAmsterdam.tot.pdf
# DS@GT 那篇的 HTML（ar5iv 通，arXiv 的 /abs 页只有摘要）
curl.exe -sL --max-time 120 "https://ar5iv.labs.arxiv.org/html/2602.10321" -o mst.html
```

**下完必须验头**：真实的 PDF 以 `%PDF` 四个字节开头。
⚠ 我第一轮就是把 `DSGT.tot.pdf` 猜错成 276 字节的 404 页而没察觉。

```powershell
$b = [System.IO.File]::ReadAllBytes("SRCB.mllm.tot.pdf")[0..3]
($b[0] -eq 0x25 -and $b[1] -eq 0x50 -and $b[2] -eq 0x44 -and $b[3] -eq 0x46)  # True = 是 PDF
```

**读的入口**：本机 `read_pdf` 工具（`focus:"toc"` 看目录、`pages` 指定页、返回的 `cursor` 续读）。

## 三、还没拿到的

| 想拿 | 卡在哪 |
|---|---|
| **DS@GT 的 PDF** | 文件名没猜对（`DSGT.tot.pdf` 是 404）。⚠ 但它的**正文已从 ar5iv 拿到**（`mst.html`/`mst.txt`） |
| `webis.tot.pdf`、`YaleNLP.tot.pdf`、`IISERK.tot.pdf` | **没试过**（命名规律同 SRCB，值得一试） |
| **BLUR 基准原文**（Wang et al.） | 只从别人转引里看到数，**未找** |
| **CLEF Social Book Search（2011–2016）** | 只从 UvA 那篇的参考文献里看到名字，**未找** |
| **有没有中文工作** | **未查** |
