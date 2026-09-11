# 开源生态融合调研（GitHub）——KnowledgeStation 可吞并项目总表

> 2026-08-25 四队并行调研（法律法规语料 / 国标生态 / 法律 RAG 与知识库 / 合规审查能力），
> 全部候选经 GitHub API 实测星数/许可证/最近推送；按「对本站模块补强 × 吸收成本」评估。
> 结论状态：调研完成，待用户拍板优先级后实施。

## 一、跨方向总 Top 10（去重后）

| # | 项目 | ★ | 许可证 | 融入什么 | 成本 |
|---|---|---|---|---|---|
| 1 | [lawtext/laws + law-flk-vol1/vol2](https://github.com/lawtext/laws) | 88+24+13 | 无（官方文本可自由用） | **2000+ 部法规语料**（docx 原件直通 MinerU；含地方法规+已废止；定期自动更新） | 低 |
| 2 | [LawRefBook/Laws](https://github.com/LawRefBook/Laws) | 1844 | 无（同上，代码勿抄） | **最大 markdown 法规库**（独家司法解释/部门规章/案例分类） | 低 |
| 3 | [ImCa0/just-laws](https://github.com/ImCa0/just-laws) | 770 | **MIT** ✅ | **311 部现行有效法律 100% 基线**——与 flk 抓取交叉对账（修订/废止核验） | 低 |
| 4 | [ZongziForu/cn-law-hub](https://github.com/ZongziForu/cn-law-hub) | 62 | ❌ 非开源（借源清单） | **10 官方源状态核验**（现行/废止/已修改）→ 三色报告升级为法律效力核验；含税务/党内法规等未覆盖源路线图 | 低-中 |
| 5 | [SocialSisterYi/OpenSTD_Spider](https://github.com/SocialSisterYi/OpenSTD_Spider) | 91 | GPL-3.0（子进程隔离，不并码） | **openstd 三合一**：搜索/元数据（CCS/日期/中英标题）/PDF 全文 → 增强 official_gb 巡检渠道 | 低 |
| 6 | [metanorma/cnccs + cn-ccs-codes + iso-ics](https://github.com/metanorma/cn-ccs-codes) | — | BSD-2-Clause | **CCS 全层级中英对照底表 + ICS 分类** → 喂现有 CCS 分类模块做规范化/层级树 | 低 |
| 7 | [open-compass/LawBench](https://github.com/open-compass/LawBench) | 448 | Apache-2.0 ✅ | **20 任务×500 例中文法律评测基线**（法条背诵/知识问答+弃权率）→ P1 准确性回归门禁 | 低 |
| 8 | [FudanDISC/DISC-LawLLM](https://github.com/FudanDISC/DISC-LawLLM) | 948 | Apache-2.0（HF 数据需确认） | **Triplet-QA「问题+法条+回答」**与证据链问答同构 → 评测 gold 集 + QA 构造范式 | 低-中 |
| 9 | [CSlawyer1985/contract-review-pro](https://github.com/CSlawyer1985/contract-review-pro) | 235 | MIT（徽标，需确认 LICENSE 实文） | **中文审查方法论包**：16 审查门禁+15 风险标签+8 维评分+义务四问 → 合规审查规则包 | 低 |
| 10 | [jherrodthomas/compliance-checker-algo](https://github.com/jherrodthomas/compliance-checker-algo) | 58 | Apache-2.0 | **标准无关比对引擎**（任意标准↔任意文档，纯标准库）→ 合规审查第二引擎交叉验证+缺口分析 | 中 |

## 二、schema/思路借鉴（不引码/少量引）

- [vickywu97/verified-chinese-law-kb](https://github.com/vickywu97/verified-chinese-law-kb)（MIT）：**律师具名核验记录 + 版本轴 + 失效标注 schema** —— 正对 V2.0「可信增强·敢引用能核验」，字段设计可抄进条款表
- [relaton-gb](https://github.com/relaton/relaton-gb)（BSD-2）：GB 标准号语法解析（唯一活跃实现）→ 移植为 Python 解析器（引用抽取/去重/替代关系地基）
- [metanorma/gb-agencies](https://github.com/metanorma/gb-agencies)（BSD-2）：GB 发布/归口机构代号↔全称映射
- [legal-tech-chat](https://github.com/tomasonjo-labs/legal-tech-chat)（MIT）：法规↔国标关联升级图谱的节点/边 schema 参考
- [xiaodingfeng/contract-review](https://github.com/xiaodingfeng/contract-review)（MIT）：审查点配置化模型 → 场景化审查模板
- [billvsme/law_ai](https://github.com/billvsme/law_ai)（无 LICENSE 只读）：MarkdownHeader→Recursive 分块 + MultiQuery 改写参考
- [ChatLaw](https://github.com/PKU-YuanGroup/ChatLaw)（AGPL 只借思想）：关键词+向量混合检索互证、SOP 报告结构
- [LexNLP](https://github.com/LexPredict/lexpredict-lexnlp)（AGPL 只借 schema）：义务四元组（主体/行为/时限/条件）抽取模式
- [cn-law-hub SKILL.md 的 10 源清单]：税务法规库/党内法规库/部委规章 = 抓取扩展路线图

## 三、明确规避

- **AGPL 传染**：ChatLaw、LexNLP、ViVi141/gd-law-crawler、MNR-Law-Crawler —— 只借思想/schema，绝不引码
- **GPL 外挂**：OpenSTD_Spider —— 独立子进程使用，产出 PDF 走自家 MinerU，代码不并入
- **溯源断裂**：chinese-law-mcp（上游 404，npm 包无法验证源码）—— 只作交叉校验源
- **无 LICENSE 代码**：lawtext/LawRefBook/contract-review-pro —— 官方文本数据可吞（著作权法第5条），**代码不复制**
- **GB 全文著作权**：本地个人使用合规，不可再分发（本项目纯本地，OK）

## 四、优先级路线（建议，待拍板）

### P0 语料吞并（低成本高收益，直接补齐法规覆盖）
1. lawtext/law-flk-vol1/vol2 docx 原件 → 批量喂 MinerU 入库（零改造）
2. LawRefBook markdown 解析器 → 补司法解释/部门规章分类
3. just-laws 导入为「现行有效基线」→ 与 flk 抓取交叉对账

### P1 权威性升级
4. cn-law-hub 10 源状态核验 → 三色报告升级为法律效力核验
5. OpenSTD_Spider 子进程外挂 → 国标元数据补齐 + 全文获取通道
6. cnccs/ICS 底表导入 → CCS 分类规范化 + 双语 + ICS 维度

### P2 可量化与规则包
7. LawBench 评测接入 pytest → P1 准确性回归门禁（弃权率指标）
8. contract-review-pro 规则包 → 合规审查审查点 schema 化
9. DISC-LawLLM Triplet-QA → 检索评测 gold 集

### P3 可选远期
10. compliance-checker-algo 第二引擎；relaton-gb 标准号解析移植；cncases 类案（320G）；verified-kb 核验 schema 进 V2.0

## 五、验收口径（每项吞并后）
- 语料类：入库条数/去重率/与 flk 在线版抽样对账一致
- 核验类：三色报告新增「法定效力核验」字段与证据链接
- 评测类：基线数字落盘 eval/，回归不回退
- 许可证：每项记录来源与许可，AGPL/GPL 零代码并入
