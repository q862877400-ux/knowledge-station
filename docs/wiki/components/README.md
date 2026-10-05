# 组件契约索引

**每套组件一篇**，逐篇回答同一个问题：**这块负责什么、提供什么、依赖什么、明确不做什么。**
**读完一篇就能改它，不用先读代码。**

> 依据：本特征（`specs/001-project-consolidation`）的
> [`contracts/component-contract.md`](../../../specs/001-project-consolidation/contracts/component-contract.md) 模板。
> **「明确不做什么」是必填**——防的是接手者把别处的职责塞进来。

---

## 一、引擎子系统（`src/core/`）

| 篇 | 子系统 | 一句话 |
|---|---|---|
| [retrieval](retrieval.md) | 检索 | 把问句变成排好序的候选条款 |
| [api](api.md) | HTTP 端点 | 引擎对外的唯一入口（`server.py` 187.7 KB） |
| [storage](storage.md) | 存取与 schema | 一切数据进出的唯一通道，38 张表对象 |
| [ingestion](ingestion.md) | 解析与入库 | 原始文件 → 带坐标的条款（`pipeline.py` 141 KB） |
| [knowledge](knowledge.md) | 法规知识本体 | 目录、分类号 CCS、别名反查 |
| [update](update.md) | 渠道巡检与变更 | 盯 131 条渠道，把「还活着吗」变成可实测事实 |
| [materials](materials.md) | 材料平面 | 自有材料也能当依据，但要过权威性纪律 |

**待写（13 个）**：`llm`、`exports`、`quality`、`verification`、`compliance`、`domain`、
`vision`、`query`、`settings`、`law_source`、`update/channels` 等。

## 二、插件对外工具（`plugin/`）

| 工具 | 用途 | 篇 |
|---|---|---|
| `ks_ping` | 探活 | ⏳ |
| `ks_resolve_clause` | **条款定位**——按标准号/条款号取原文 | ⏳ |
| `ks_answer` | 问答（带检索结果） | ⏳ |
| `ks_materials` | 材料平面只读 | ⏳ |
| `ks_effect_report` | 效果上报 | ⏳ |

---

## 三、进度与规矩

**已写 7 / 目标约 20。** 覆盖率是 SC-006 的判据，**未满 100% 时会在这里如实标着**。

**写一篇的规矩**：
1. **事实来自读代码与既有文档**，不许凭印象。不确定的标「未核」。
2. **「明确不做什么」必填**，且每条要说清**该由谁做**。
3. **一个事实一个归属层**：这里只说本组件的接口与边界；检索算法的取舍、渠道的判据等在各自归属文档里。
4. **改了某个子系统的对外接口 ⇒ 同步改对应那篇**。
