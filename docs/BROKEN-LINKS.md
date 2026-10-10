# 已知断链台账（**不许静默忽略**）

> **为什么要这一页**：`scripts/docs/check-links.py` 是**独立于门禁**的全仓断链检查
> （门禁扫不到全部文档）。它红了就是红了 —— 但**有些断链的修复面在别的写入方手里**，
> 当场改会与并行自动化撞车。**这一页就是那类断链的登记处**：
> 让"当前有 N 处断链"变成一个**有归属、有理由、有复查判据**的事实，而不是一句"应该没事"。
>
> ⚠ **纪律**：本页只登记**改不了的**。能当场改的一律**当场改掉**（那才是收口）。
> 每次收工前跑一遍检查命令，把读数与本页对账。

**检查命令**（唯一真源，不许手抄计数）：

```bash
.venv/Scripts/python.exe scripts/docs/check-links.py
```

---

## 一、当前在读（2026-10-10 14:0x）

| # | 位置 | 目标 | 真错在哪 | 为什么不当场改 | 归谁 |
|---|---|---|---|---|---|
| 1 | `tools/gov-qa/recon/ROUND-2026-10-08-js.md:3` | `SITE-REGISTRY.md` | 文件在 **`tools/gov-qa/`**（上一级），不在 `recon/` ⇒ 应为 `../SITE-REGISTRY.md` | **该目录由并行自动化高频写入**（实测 2026-10-10 14:0x 它仍在写 `tools/gov-qa/**`、且有 2 个采集进程在跑）⇒ 当场改会与它撞车 | **并行自动化**（`specs/005-govqa-conformance`） |
| 2 | `tools/gov-qa/recon/ROUND-2026-10-08-night.md:3` | `SITE-REGISTRY.md` | 同上（同一处错，两个文件各一次） | 同上 | **并行自动化** |

**性质**：这两条**不是**「路径写错方向」那种低级错 —— 它们是**索引页指向上一级的台账**，
写法上少了 `../`。修法是一行的事，**唯一的障碍是写入面归属**。

**复查判据**：`check-links.py` 报 **0 处断链** ⇒ 本页第一节清空。
**触发时机**：并行自动化收工后（判据：`tools/gov-qa/**` 连续 ≥30 分钟无写入、
`git log` 无新提交、无采集进程）**立刻改掉**。

---

## 二、已修（留痕，供查"当时怎么错的"）

| 日期 | 位置 | 错在哪 | 修法 | 提交 |
|---|---|---|---|---|
| 2026-10-10 | `specs/007-ui-polish/tasks.md:110` | 写 `verify-briefs/VERIFY-REPORT-spec007-ui-polish.md`（**相对本文件**）⇒ 解析成 `specs/007-ui-polish/verify-briefs/…`，**该目录不存在** | 改成 `../../docs/verify-briefs/…`（报告实际在 `docs/verify-briefs/`）；并就地写明"原文错在哪、本仓惯例是什么" | `025739ee` |
| 2026-10-10 | `specs/003-vec-scope-pushdown/data-model.md:35` | 写 `[research.md](../research.md)` ⇒ 解析成 `specs/research.md`，**不存在**（兄弟文档一律写同目录 `research.md`） | 去掉 `../` | `ee56cd0` |

---

## 三、历史上"以为是断链、其实不是"的（防误报）

| 现象 | 真相 |
|---|---|
| `docs/research/dsh-official/ERRATA-alpha.2.md` 里指向 `../architecture/2026-09-14-*.md` | 那是 **DSH 官方仓**的路径，**不是本仓的** ⇒ 检查脚本已按"疑似示例/外部路径"跳过 |
| `docs/research/dsh-official/dshdocs-F.md` 里的 `foo.md` / `foo.zh.md` | **示例文本**，非真引用 ⇒ 脚本按"占位符"跳过 |

（本节只记**已定性的误报**；新增误报先查清再登记，不许直接把检查结果当噪声。）
