# Hindsight 官方文档本地副本

> ## ⚠️ 版本口径（先读这一行）
> **这里的正文与接口说明，对应文档站 `llms-full.txt`（生成于 `2026-09-28T19:18:34Z`）与
> `openapi.json`（`info.version = 0.10.1`，77 路径 / 99 操作）。**
>
> ⚠ **本机实跑的 Hindsight 是 `0.10.0`、71 条路径 —— 比这里的文档旧一版。**
> 已实际踩到的差异：**归档导入端点路径不同**（文档写 `/transfer/import?mode=merge`，
> 实机只有 `/document-transfer?on_conflict=replace`）。⇒ **动手前先查实机的 `/openapi.json`，
> 别照这份文档猜参数。**

**这是什么**：Hindsight 官方文档站（`hindsight.vectorize.io`）整站正文的**本地逐字副本**，
外加接口说明（OpenAPI）。共 42 篇，见 [`referenced-files.txt`](referenced-files.txt)。

**为什么放在这里**：2026-09-28 起通读这份文档，为 KS 是否、以及如何用 Hindsight 做判断
（结论与逐条证据见 [`../HINDSIGHT-DOCS-READING-2026-09-28.md`](../HINDSIGHT-DOCS-READING-2026-09-28.md)）。
原先的副本放在 `%USERPROFILE%\AppData\Local\Temp\hs-docs2\` ——
**那是系统临时目录，会被清理**，一手件随时可能消失，故迁到此处。

**为什么不进版本库**：本目录约 1.5 MB，是**外部资料的本地副本**，不是本项目的产出，
进 git 会污染历史。正文可从 `https://hindsight.vectorize.io/llms-full.txt` 随时重下（本文档头部自带生成时间戳）。

---

## 目录内容

| 文件 | 说明 |
|---|---|
| `llms-full.txt` | 整站正文，938,683 字节，官方自述 "complete Hindsight documentation for LLM consumption" |
| `openapi.json` | 接口说明，603,960 字节，v0.10.1，77 路径 / 99 操作 |
| `referenced-files.txt` | 42 篇清单 |
| `split.py` | 把 `llms-full.txt` 按篇切成单文件的脚本 |

⚠ **切分结果（`split/`）不入库**，按需重建：

```powershell
python docs/research/hindsight-official/split.py
```

## 取件时踩过的坑（别重犯）

- 文档站是 SPA：`/docs/*` 各种路径**全部返回同一个 22,747 字节的 404 壳，HTTP 200 但不是正文**。
  ⇒ **只有 `llms-full.txt` 是真的。**
- `llms.txt` **同样是那个 22,747 字节的壳**，不是资料。本目录因此不收它。
- 下载来源：`https://hindsight.vectorize.io/llms-full.txt`、`https://hindsight.vectorize.io/openapi.json`。
  ⚠ 文档站若改版，`llms-full.txt` 里的 `## File: xxx` 分隔格式可能变，`split.py` 要跟着改。

## 与本项目的关系（一句话）

KS 是**中文法律/国标语料上的资料工作站**；Hindsight 是**给 AI 助手用的长期记忆**。
两者只在"记忆"这一层重叠。硬约束记在
[`../HINDSIGHT-DOCS-READING-2026-09-28.md`](../HINDSIGHT-DOCS-READING-2026-09-28.md) §10.2：
**Hindsight 装不下"效力档"**（`fact_type` 只有 `world` / `experience`），
而"作废 / 被代替 / 仅供参考必须原样并存"正是法规场景的核心。
