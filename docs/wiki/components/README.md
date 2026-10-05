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
| [llm](llm.md) | 模型调用与作答 | 把证据交给模型，拿回只依据证据的答案 |
| [exports](exports.md) | 交付物导出 | 报告 / 草稿 / Office 往返编辑 |
| [quality](quality.md) | 质量分级与体检 | 打分定级挑毛病，**阈值与规则的唯一所有者** |
| [verification](verification.md) | 分型核验 | 检查答案里「按规定该是什么」的东西对不对 |
| [compliance](compliance.md) | 合规触发与差距分析 | 制度 vs 法规的逐条缺口 |
| [domain](domain.md) | 域模型契约 | 全项目共用的数据形状（T00 冻结） |
| [vision](vision.md) | 本地视觉 | 无云端视觉 API 也能看图 |
| [query](query.md) | 查询理解 | 检索之前先把问句读懂 |
| [settings](settings.md) | 设置与凭据 | 存密钥——而且**不碰系统层** |
| [law-source](law-source.md) | 官方法规来源管线 | 抓官方法规原文，与标准件同构入库 |
| [update-channels](update-channels.md) | 渠道适配器 | 每条官方渠道一个适配器（实测 14 个） |

## 二、插件侧（`plugin/`）

| 篇 | 覆盖 | 一句话 |
|---|---|---|
| [plugin-tools](plugin-tools.md) | 5 个模型可见工具 + 错误码常量 + 侧栏 | 本产品对 agent 的「手」 |

---

## 三、进度与规矩

**✅ 覆盖率 100%**：`src/core/` 的 **18 个子系统**逐篇 + 插件侧 1 篇 = **19 篇**（SC-006 达成）。

**若日后新增子系统**：**必须补一篇**，否则覆盖率不再是 100%——那时要在这里如实改回"未满"。

**写一篇的规矩**：
1. **事实来自读代码与既有文档**，不许凭印象。不确定的标「未核」。
2. **「明确不做什么」必填**，且每条要说清**该由谁做**。
3. **一个事实一个归属层**：这里只说本组件的接口与边界；检索算法的取舍、渠道的判据等在各自归属文档里。
4. **改了某个子系统的对外接口 ⇒ 同步改对应那篇**。
