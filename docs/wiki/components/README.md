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
| [llm](llm.md) | 模型调用与作答 | 把「问题 + 证据」送进模型，装配成可核验的答案 |
| [exports](exports.md) | 产出物组装与导出 | 效力报告 / 研究报告 / 引用块 / Excel / Office 往返 |
| [quality](quality.md) | 质量判定 | 判定解析结果坏没坏，**阈值与规则的唯一所有者** |
| [verification](verification.md) | 核验与纠错守卫 | 检查「模型说的」有没有证据、「用户改的」有没有改坏 |
| [compliance](compliance.md) | 合规差距分析 | 制度逐条对回法规义务，指出缺在哪 |
| [domain](domain.md) | 域模型契约 | 全项目共用的对象定义与模态强度（T00 冻结） |
| [vision](vision.md) | 本地视觉反查 | 截图 → 文字 → 条款，全程本机 |
| [query](query.md) | 查询理解 | 检索之前，先把问句拆成意图、主题与槽位 |
| [settings](settings.md) | 设置与凭据 | 密钥只存引擎自己这里——**不碰系统层** |
| [law-source](law-source.md) | 官方法规来源管线 | 从官方站抓法规原文，与标准件同构入库（`knowledge/` 子目录） |
| [update-channels](update-channels.md) | 渠道适配器 | 每条官方渠道一个适配器（实测登记 13 个，`update/` 子目录） |

## 二、插件侧（`plugin/`）

| 篇 | 覆盖 | 一句话 |
|---|---|---|
| [plugin-tools](plugin-tools.md) | **6 个**模型可见工具（逐工具给用途 / 参数 / 返回 / 边界） | 引擎能力对 agent 的入口 |

---

## 三、进度与规矩

**✅ 覆盖率 100%**：`src/core/` 的 **18 个组件**（16 个一级目录 + `knowledge/law_source`、`update/channels` 两个子目录）逐篇 + 插件侧 1 篇 = **19 篇**（SC-006 达成）。

**若日后新增子系统**：**必须补一篇**，否则覆盖率不再是 100%——那时要在这里如实改回"未满"。

**写一篇的规矩**：
1. **事实来自读代码与既有文档**，不许凭印象。不确定的标「未核」。
2. **「明确不做什么」必填**，且每条要说清**该由谁做**。
3. **一个事实一个归属层**：这里只说本组件的接口与边界；检索算法的取舍、渠道的判据等在各自归属文档里。
4. **改了某个子系统的对外接口 ⇒ 同步改对应那篇**。
