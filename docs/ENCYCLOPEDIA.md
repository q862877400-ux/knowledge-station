# KnowledgeStation 技术百科全书（ENCYCLOPEDIA）

> **文档地图**：本文件 = 技术事实唯一权威（架构/契约/坑/规则）。并行文档仅四份——
> `README.md`（快速开始）、`docs/INTRODUCTION.md`（产品介绍）、`docs/REQUIREMENTS-v4.3.md`（需求 SSOT，历史基线）、`docs/DEVELOPMENT-HISTORY.md`（开发简史）。
> ⚠ 本仓库**不存在** `docs/_deprecated/` 或旧 phase 交接文档——历史只存在于 git 提交（`git log`）与 `docs/DEVELOPMENT-HISTORY.md`。

## 目录

- 第一篇 产品与形态：§1 定位与承诺 · §2 交互形态与产品决策 · §3 检索 · §4 LLM 层 · §5 核验层 · §6 合规引擎
- 第二篇 引擎与契约：§7 架构与进程 · §8 数据模型 · §9 入库管线与 bbox · §10 API 与 SSE · §11 测试体系
- 第三篇 运行与运维：§12 技术栈环境 · §13 运维 · §14 插件前端
- 第四篇 凭据与安全：§15 凭据体系
- 第五篇 规则与遗留：§16 规则红线宪法 · §17 未实现清单 · 附录 A 已退役系统 · 附录 B 已知坑全集

---

# 1. 项目概览与产品承诺

## 1.1 一句话定位

把国标/法规 PDF 变成**可检索、可溯源、可纠错、可落检查表**的本地知识库：回答每条结论都带"标准号-条款号"引用，点引用即可跳到 PDF 原文对应位置高亮核对；LLM 只接收"问题 + 本地检索的证据片段"；每次外发 payload 落库可审计。

## 1.2 目标用户与典型场景

- **用户**：企业安全/环保/合规/工程人员（危化、消防、施工、工贸等行业）。
- **典型问题**："动火作业怎么分级""气体探头装多高""消防疏散宽度多少"。

## 1.3 痛点

1. 国标/法规 PDF 动辄几十上百页，条文分散，人工翻阅慢且容易漏。
2. 同一主题多版本（强标/推标、废止/未生效/替代关系），用错版本是合规事故。
3. 通用 AI 常编造条款——合规场景不允许不可溯源的回答。
4. 光回答"应该做什么"不够，还要能落地：义务清单、检查表、差距分析。

## 1.4 产品形态（批 8 定稿）

**引擎 + DSH 插件一体**。DSH Web GUI 会话 = 左栏（结论/三段式/可点引用）；插件侧栏 tab = 右栏工作台（证据 PDF / 效力报告 / 收藏 / 入库预览 + 设置栏目）。引擎 Python 进程按需懒拉（随机端口 + 一次性 token）。

## 1.5 产品承诺（验收红线 v2）

1. **可溯源**：每条结论带标准号-条款号引用，可点回原文核对。
2. **数据可信**：OCR 可纠、可体检、可集中修；修订留痕可撤销；快照不可变且 SHA-256 可验证；补丁作用域绑定 `(standard_id, version_id, clause_key, revision_hash)`，解析不出的补丁拒绝落库。
3. **版本正确**：引用自动指向现行有效版本；已废止/未生效有提示；**只引现行版**（废止版不作依据，点名问旧版时说明状态与差异）；即将生效单独提示施行时间。
4. **外发可审计**（D1 废止"零外发"后的替代红线 D2；**D5（2026-09-17）补齐了 REQUIREMENTS §0.1 里残留的同名禁令**）：每次 LLM/rerank/云解析调用的完整 payload 落库，用户可在 UI 查看并可导出。**它不是禁止外发，是要求外发留痕。**
5. **额度克制**：云调用预算控制（历史截断、追问单轮封顶）。
6. **引用准确率门禁**：Golden Set 指标进 pytest（红线 6），检索/提示词任何改动掉指标即卡住。
7. **答案排序红线**：现行性 > 效力层级 > 内容匹配度；收藏/偏好权重不得越过前三条。

---

# 2. 交互形态与产品决策台账（DSH 转生定稿）

## 2.1 触发与模式

- **轻模式（默认）**：模型自动识别合规主题 → **静默检索** → 流水正文 + 内联蓝链。skill 规则 1：规范题禁止凭记忆作答。闲聊不触发。
- **取证模式**：斜杠命令 `/forensic`（会话级）→ 每问强制权威链路 + 三段式（依据区蓝链 → 推导区 [1][2] 引用 → 结论区）。
- **仅收藏**：`/bookmarks`（依附取证模式）→ 检索只从收藏集查。
- **追问**：问齐才答；缺参数绝不拒答 → 分情况作答（分支各自带结论+链）。
- **冲突处理**：跨源冲突（法规 vs 国标/新旧版/强制 vs 推荐/地方更严）→ 答案尾部 ⚠️ 冲突块全量列出 + 判断逻辑 + 用户选口径；选择存入画像并显式标注。

## 2.2 25 条决策台账（2026-09-05 逐项问答定稿，全部 ✅ 采纳）

| # | 决策 | # | 决策 |
|---|---|---|---|
| 1 | 单本入库永远先 Dry-Run 预览再确认落库 | 14 | 答案骨架三段式 + 强提示词 + 会话级开关 |
| 2 | 批量入库总账分桶 ✅/⚠️/❌；新语料源先抽样 3~5 本 | 15 | 轻模式（静默检索）vs 取证模式（强制三段式）双层 |
| 3 | 国标原 PDF；官方 docx 法规公文文本视图 + PDF 并存 | 16 | 仅收藏按钮依附取证模式 |
| 4 | 回答顺序：依据 → 推导 → 结论 | 17 | 收藏最简版：无同分优先权重 |
| 5 | 更新默默执行 + 轻通知 + 影响清单 | 18 | 冲突块全量列出 + 用户选口径入画像 |
| 6 | 上传自动分类：法规国标→主库；制度文稿→私有目录 | 19 | 巡检每日扫官网公告；引擎 headless 跑完即退；顺延补跑 |
| 7 | 关键词硬触发 + 主题自动识别 + 禁凭记忆答规范题 | 20 | 配置页密钥引擎侧 DPAPI 加密，不绑全局 |
| 8 | 自动更新只接官网公告源，不接公众号 | 21 | 效力报告：按文件目录分类体系组织（业主修订） |
| 9 | 查无外扩：官方下载 + 全网线索；非官方只给线索 | 22 | 引用只允许现行版；即将生效单独说明 |
| 10 | 手动上传生效校验：不阻塞 + 灰标未核验 + 巡检补核 | 23 | 引用蓝链点击直接跳 PDF 对应位置（悬停无动作） |
| 11 | 修订助手两段式：网络发现候选 → 挑选 → 本地引用/下载 → 成稿 | 24 | 批注作为上下文纳入推理，答案注明"含您的批注" |
| 12 | 修订复查：一次成稿 + 改动对照清单（采纳/回退/改表述） | 25 | 首次初始化引导卡 + 分级导入选项，库"建设中"不阻塞 |
| 13 | 溯源标记：加色/下划线 + 句尾上标引用 + 文末依据清单(docx) | | |

## 2.3 明确不做（Non-goal）

公众号抓取、PDF 页级自由批注（条款级即可）、引用悬停卡片、非官方渠道下载、多用户/权限、自建使用统计看板（用 dsh 生态 usage 插件）、引擎模型微调。

---

# 3. 检索链路

## 3.1 六通道混合检索（契约冻结）

通道枚举（**冻结**）：`exact | fts | vec | modality | legal_element | behavior_scope`。

| 通道 | 说明 |
|---|---|
| exact | 精确标准号-条款号查询 |
| fts | FTS5 + jieba 分词（容忍 OCR 错别字） |
| vec | fastembed 向量语义（bge-small-zh-v1.5，512 维） |
| modality | 义务模态词（应/宜/严禁…） |
| legal_element | 法理要素 |
| behavior_scope | 行为域 |

**RRF 融合**：`score = Σ w_i / (60 + rank_i)`；exact 权重 2.0，modality/legal_element 0.8，behavior_scope 1.2，其余 1.0。默认过滤 `legal_status='superseded'`（除非 `include_superseded=true`）。

关键实现点：
- `expand_query_with_history`：补充式回答（以 是/对/在/属于/设备/生产/密度 等开头）并入原始问题——"是硫化氢，生产装置区域"不再脱靶。
- `expand_evidence_chain`：主证据不足时沿 evidence_edge 补引用链条款。
- `_expand_title_clauses`：命中纯数字标题条款自动附带子条款，证据上限 8 条。
- `refine_search_query`：口语前缀清洗（我要搞个/咋看/请问），分级问法追加主题词。
- `apply_condition_filter`：声明条件（甲类/高层）过滤不适用条款；`rank_with_hierarchy`：效力层级高的排前面。
- 收藏加权 +0.15；别名反查（alias_store）；向量引擎离线自动降级（R30）。

## 3.2 Rerank 标准阶段

- 六通道 RRF → top-N（**N=24**）→ reranker 对 (query, content_text 截断 512 字) 打分 → top-K（**K=6，合规审查 K=8**）。
- 模型 BAAI/bge-reranker-base（fastembed/ONNX/CPU ~400MB；bge-reranker-v2-m3 不被 fastembed 0.8 支持）。
- **例外条款保护**：例外/引用边扩入的证据强制保留，不参与 rerank 淘汰（但书不可被挤掉，P1）。
- 降级：模型未下载/加载失败 → 跳过 rerank（响应标记 `rerank_offline: true`）。
- 门禁默认 `rerank=False`（锁基础检索质量），rerank 增量用 `--with-rerank` 专项评测。

## 3.3 通道消融结论（2026-08-23 实测，结论已固化）

- **exact 主力**：禁用后 -38pp。**fts 弱**（-1.1pp）但保留。
- vec / modality / legal_element / behavior_scope 当前问答场景贡献 ≈0，**但不删**：vec 未来必要、behavior_scope 审查场景主力。
- 消融必须分"问答场景/审查场景"两组数据分别判定。

## 3.4 Golden Set 门禁（红线 6）

- **数据集**：`eval/golden/`（96 条冻结 + 快照库 knowledge-snapshot.db）。**评测器**：`eval/run_benchmark.py`。**基线**：`eval/baseline.json`——exact_hit@1 **0.889** / recall@5 **0.978** / 核验拦截 1.0 / 合规 1.0。
- **门禁断言**：`tests/test_golden_gate.py`——任何指标回退 >2pp 即失败（含硬底线）。
- 指标：exact_hit@1、recall@5、recall@10、citation_precision、modality_intercept_rate、三色判定准确率、red_precision。

---

# 4. LLM 层与追问机制

## 4.1 调用链与凭据（权威表述——批 2/4 定稿）

- 文件：`src/core/llm/deepseek_client.py`（SYSTEM_PROMPT / build_evidence_prompt / build_messages / stream_chat_completion）。
- 证据 prompt 截断 800 字符/条；历史最多 4 条、每条 300 字。
- **Key 读取链（唯一权威，本节是所有其他章节的指针目标）**：加密存储 `<data_dir>/secrets.json`（DPAPI）优先 → 环境变量 `KS_LLM_API_KEY` → 旧名 `DEEPSEEK_API_KEY` 只读回退。注册表 HKCU\Environment 只作只读覆盖，**引擎与脚本绝不写注册表**。详见 §15。
- 未配 Key 自动降级占位（离线可用）；外发审计见 §13.4。

## 4.2 SYSTEM_PROMPT 规则 1~9（用户实测调优产物，**只能增强不能回退**）

| 规则 | 内容 | 业务原因 |
|---|---|---|
| 1 | 必须依据证据作答，常识/假设可补充并标注 | 防编造 |
| 2 | 严禁提及证据外条款号；保留应/宜/严禁强度 | 条款与义务强度不可篡改 |
| 3 | 例外（但书/除外）必述 | 只看主文会误导 |
| 4 | 依据不足明说"依据不足" | 不硬编 |
| 5 | 罗马数字=阿拉伯数字等价 | 中文标准混用 Ⅰ/Ⅱ/Ⅲ 与 1/2/3 |
| 6 | 末尾一句话追问（句号结尾） | 缺条件时引导补充 |
| 7 | 常识可用（气体密度等），标注（常识） | 用户明确不满"硫化氢密度还要问" |
| 8 | 追问节制：已补充关键信息不再问次要细节 | 用户明确不满连环次要追问 |
| 9 | 问还是答一次定夺：JSON {"ask":[≤3]} 或直接答 | v2 追问机制 |

## 4.3 追问机制演进史（v1 → v2）

- **v1（规则槽位表）**：每类意图手维护"该问哪些参数"。问题：通用性差、追问没写进历史→连环追问、追问含次要参数。
- **v2（LLM 单次自判，现行）**：规则 9 约定缺关键信息 → 只输出 `{"ask":["问题1","问题2","问题3"]}`（≤3 个一次问完）；否则直接作答。硬上限 `user_turns < 2`。v1 槽位表代码 Phase 13.1 已删；`extract_slots` 保留（主题作用域槽位）。

## 4.4 查询理解层（understanding.py）

- 意图分类（7 类）；工程/法律双 Schema 槽位；四档追问（thorough/default/quick/guess）；免追问前置声明语法 `[丙类/高层民用/耐火二级] 问题`。
- R52 互斥条件过滤；R40 强标/层级置顶；R53 依据充分度提示；R60 否定维度纠错。
- 协议：首轮缺核心参数 → SSE `clarify` 事件（不检索不调 LLM，零成本追问）。

## 4.5 Few-shot 注入（R17 轻量版）

`fewshot.py`：feedback_log 负向聚类 → ≤5 条示例（每条 ≤100 字，R77 预算约束）；已接入 build_messages。不做模型微调。

---

# 5. 核验层

## 5.1 三通道核验（typed_verifier.py）

基于"证据 vs 回答"规则比对，**不改写回答**；聚合为置信度 high/mid/low。

| 通道 | 检查 |
|---|---|
| 数值一致性 | 回答数值 vs 证据数值 |
| 模态强度 | 义务词强度（严禁5 > 禁止5 > 不得4 > 应3 > 宜2 > 可以1 > 鼓励0） |
| 法理要素 | 条款要素 vs 回答要素 |

**模态强度字典（权威 MODALITY_STRENGTH）**：严禁5 禁止5｜不得4 不应4 不能4｜应当3 应3 必须3｜宜2 一般应2 原则上2｜可以1 有权1 可1｜鼓励0 提倡0 支持0。

## 5.2 核验报告

SSE `verification` 事件：`{is_valid, answer_confidence, confidence_reasons[], unsupported_clauses, unverified_numbers, modality_violations, legal_element_violations}`。不合格标红列出违规项；核验通过前复制按钮禁用。**核验用全量条款文本**（`_full_evidence` 不截断——修"25.0%→4.0%"误报的关键）。

## 5.3 核验哲学 + 两轮误报修复判据（2026-09-06）

- 规则式为主，**宁误报不漏报**；LLM advisory judge 已判定砍（指标达标）。
- **误报修复判据 1（PDF 宽容字距）**：`_canon_pairs` 剥数字间空格——"4. 3. 3"与"4.3.3"比对前归一。
- **误报修复判据 2（提及≠转述）**：`_MENTION_ONLY_RE` 对比语境豁免——证据若只是"提及"某数值（引用他条）而答案转述的是主条款数值，不算篡改。

---

# 6. 合规引擎与导出

## 6.1 合规审查（compliance/engine.py）

审查点逐句抽取 → 六路匹配（风险锚点增强）→ 三色判定（🔴 违法/🟡 风险/🟢 合规）。规则版为主（LLM 精判 use_llm 开关预留）；审查 SSE：point_verdict → report_ready → done。ground truth：16 条植入条款召回 16/16、标红精确 10/10。

## 6.2 义务清单与检查表（obligation.py）

输入业务描述 → 分组义务列表（应/必须型条款，含来源条款号）→ 转检查表问句 → 勾选持久化 → 导出 Word。

## 6.3 制度差距分析（gap_analysis.py）

粘贴内部制度 → 与法定义务三色差距 + 整改建议（R-L12/13）。

## 6.4 条款释义（interpretation.py）

五要素 JSON：法理要素/适用情形（落入+不落入）/实务要点/关联条款/立法本意。规则版为主；use_llm 增强（max_tokens=800 + 括号配对提取——早期 250 截断教训，保持）。

## 6.5 批量问答（batch_qa.py）

`POST /api/v1/batch/qa`：预算护栏 ≤50 问硬截断；无 Key 走占位答案；未通过核验的在报告中**标黄而非隐藏**（P1 不粉饰）。

## 6.6 双向溯源（backlinks.py）

`GET /api/v1/clauses/{id}/backlinks`：聚合 debug_dump / user_bookmark / project_list / obligation_list / review_point。

## 6.7 导出（exports/report_export.py）

引用块（R19 标准 Markdown 格式）；问答依据 Word；合规审查报告 Word；义务清单/检查表 Word。导出模板自定义：`%APPDATA%\KnowledgeStation\templates\` 下同名 docx 存在时作基础 Document。下载接口严格限定 exports 目录（路径穿越 403，有测试）。

---

# 7. 架构总览与进程模型

## 7.1 分层架构

```mermaid
flowchart LR
  FE[DSH Web GUI 宿主<br/>会话(结论) + 侧栏tab(证据PDF)] -->|同源代理 /ks/*| PLG[ks-dsh-plugin 宿主桥<br/>懒拉引擎 + 模型工具]
  PLG -->|SSE/REST Bearer| ENG[引擎 FastAPI 本地进程<br/>随机端口 + 一次性 token]
  ENG --> DB[(SQLite 34 表 WAL<br/>clause_revision 快照 + clause_patch 补丁)]
  ENG --> LLM[DeepSeek 云端<br/>仅问题 + 证据片段<br/>payload 落库可审计]
  ING[入库管线<br/>MinerU 2.x / PyMuPDF] --> DB
  RET[六通道检索 + RRF + rerank] --> ENG
  VER[核验三通道<br/>数值/模态/法理] --> ENG
```

- **引擎**：FastAPI 本地进程；query/understanding（主题/意图/槽位/追问 v2）；hybrid_engine（六通道+RRF+rerank+历史+证据链）；typed_verifier；deepseek_client（SYSTEM_PROMPT 1~9）；compliance；exports。
- **存储**：SQLite 单文件 WAL；clause_revision 不可变快照 + clause_patch 补丁叠加；clause_fts FTS5 + clause_vec vec0。
- **入库**：MinerU 2.x 版面分析（可降级）；pypdf 数字回填；三型分型/章节还原/证据边。

## 7.2 进程模型与连接链（批 8 后形态）

- **引擎** = 独立 Python 进程（FastAPI/uvicorn），随机空闲端口 + 一次性 token，写 `engine.session.json`。
- **插件宿主桥**（plugin/src/index.js）：按需懒拉引擎（复用存活的，死了才 spawn）→ 读 session → 工具调用与代理路由都经插件转发。
- **client 连接链**：DSH 侧栏 tab → 宿主同源代理 `/ks/session`（每次载入重取，引擎轮换对 tab 透明）→ `/ks/pdf`、`/ks/bbox`、`/ks/assets/*` 全部同源转发（token 不进页面不跨源）。
- **坑**：引擎重启后端口/token 必变 → tab 无需刷新（fetch 经 /ks/session 取新值）；host 侧状态镜像 stale 时如实标注。**不要杀 DSH 宿主进程**（§15.6 事故）。
- **引擎重启**：直接 Stop-Process 即可——下次 ks_ping 拉新引擎（新代码生效）；批量任务跑着时不要杀。

## 7.3 目录与模块地图（文件 → 职责）

```
src/core/
  main.py                        # 引擎入口：python -m src.core.main（含 figure-ocr-warmup 后台预热）
  api/server.py                  # FastAPI 全部 API + SSE；随机端口+token+session；认证/CORS
  config.py                      # %APPDATA%\KnowledgeStation（KS_DATA_DIR 可重定向）
  domain/models.py               # Pydantic 域模型（冻结契约）+ MODALITY_STRENGTH + SSE 事件枚举
  storage/
    sqlite_db.py                 # 连接管理（WAL/外键/busy_timeout）+ 单写者队列 + schema 权威 DDL
    schema.sql                   # 34 表（32 CREATE TABLE + clause_fts/clause_vec 虚拟表）+ 索引（冻结）
    clause_repo.py               # 条款读写 + 补丁机制（fetch_full_clause/PATCHABLE_FIELDS/migrate_patches/resolve_clause）
    user_data.py                 # 收藏/批注/项目清单/义务清单 CRUD
    versioning.py                # 版本链（R29/R42）
    impact.py                    # 影响面分析（R49）
    backup.py                    # 快照备份/恢复（VACUUM INTO + 校验和验证）
    update/data_package.py       # 数据包导出/导入（引用 scripts/restore_package.py 还原流程）
  retrieval/
    hybrid_engine.py             # 六通道混合检索+RRF+rerank+证据链扩展+历史扩展+收藏加权
    embedder.py                  # fastembed bge-small-zh-v1.5（本地缓存，离线可用）
    reranker.py                  # bge-reranker-base 重排（例外条款保护 + 离线降级）
  query/understanding.py        # 主题/意图/槽位；追问策略 v2
  knowledge/
    classifier.py                # 三型分型 + 模态抽取 + 法理要素 + 引用抽取
    alias_extract.py             # 术语别名抽取（R10/R48）
    auto_tag.py                  # 入库自动标签（规则层；红线：标签永不进正文）
    law_source/                  # 官方法规来源（flk/govcn client + convert + ingest + update）
  llm/
    deepseek_client.py           # SYSTEM_PROMPT 规则 1~9 + 证据 prompt + 流式
    egress_audit.py              # record_egress/query_egress/export_egress（D2 审计）
    fewshot.py                   # R17 轻量版 Few-shot 注入
    ks_answer.py                 # 取证答案链（三段式 + typed_verifier 核验）
  verification/typed_verifier.py # 数值/模态/法理三通道核验 → 答案置信度
  ingestion/
    pipeline.py                  # 主入库管线（run_full_ingest/analyze_preview/load_middle_items/split_items_into_clauses）
    mineru_adapter.py            # MinerU 2.x 深度版面分析（可降级；PUA 归一化）
    pypdf_backfill.py            # OCR 数字回填（自动打补丁）
    law_text.py                  # 章节式条款还原
    parser_worker.py             # spawn 子进程隔离解析
    docx_adapter.py / docx_ingest.py  # docx 一等公民入库（COM 转 PDF 优先 / 降级直解）
    bulk.py                      # 万级批量导入（三阶段：快扫建目录→异步解析→首检入列）
    span_calibration.py          # span 坐标顶部/底部原点自动校准（最近行投票）
    figure_redraw.py             # 流程图矢量重绘（内孔检测→RapidOCR→SVG；get_ocr）
    figure_locator.py            # 图题锚定位图区
    doc_delete.py                # 文档删除（清虚拟表）
  update/                        # 更新检查（channels cssn/openstd/… + change_repo + subscriptions + inspector 巡检）
  compliance/                    # engine.py / obligation.py / gap_analysis.py / interpretation.py / batch_qa.py
  exports/                       # report_export.py / office_roundtrip.py / backlinks.py
  vision/local_vision.py        # 图片 OCR → 检索定位（MinerU 本地，零外发）
  settings/                      # api_credentials.py（加密存储读写链）/ secret_store.py（DPAPI）
  supervisor.py                  # 引擎看门狗（历史模块，保留——职责主体已移交插件 host）
  figure_redraw 相关：RapidOCR 惰性单例
plugin/                          # DSH 插件（批 8 后唯一 GUI/工具面）
  src/index.js                   # 宿主桥：懒拉引擎 + ks_* 模型工具 + /ks/* 同源代理路由
  src/engine.js                  # 引擎 session 发现 + HTTP 客户端 + ensureLive 守护
  client/entry.ts                # tab 注册（证据 PDF/报告/收藏/入库 + 设置区）
  client/KsEvidenceTab.tsx       # 证据 PDF 查看器（跳页 + 红色定位箭头 + 标题目录）
  client/api.ts                  # 引擎 fetch 链（经宿主代理）
  client.js                      # esbuild 单文件产物（~1.1MB，DSH ModuleLoader 加载）
  scripts/build-client.mjs       # 构建；smoke.mjs 引擎冒烟；verify:commands-real.mjs 命令回归
scripts/                          # 见 §13.5 活脚本清单
eval/                            # Golden Set 门禁三件最小集（golden/ + run_benchmark.py + baseline.json）
tests/                           # 80 个测试文件（契约/检索/入库/API/多轮/运维/门禁）
wenjianmulu/                     # GB/T 39910-2021.pdf 等——⚠ 生产库 doc_meta.file_path 指向这里，禁止删除/移动
```

---

# 8. 数据模型与存储契约

## 8.1 存储全局约定

- **单文件库**：`%APPDATA%\KnowledgeStation\database\knowledge.db`。
- **PRAGMA**：`journal_mode=WAL`、`foreign_keys=ON`、`busy_timeout=5000`。
- **34 表 DDL 冻结于 `src/core/storage/schema.sql`**（**2026-09-16 实测**：32 个 `CREATE TABLE`
  + `clause_fts`/`clause_vec` 两个虚拟表；改动 = 契约变更，流程见 §10.4）。
  ⚠ 口径提示：生产库 `sqlite_master` 里 `type='table'` 有 **45** 条。**2026-09-16 实测对账**：
  `45 = 34`（schema.sql 冻结：32 实体 + 2 虚拟）`+ 1`（`law_catalog`，由
  `src/core/knowledge/law_source/catalog.py:70` 懒建，不在 schema.sql 内）
  `+ 5`（FTS5 影子：`clause_fts_data`/`_idx`/`_content`/`_docsize`/`_config`）
  `+ 4`（sqlite-vec 影子：`clause_vec_chunks`/`_info`/`_rowids`/`_vector_chunks00`）
  `+ 1`（`sqlite_sequence`）。**报"表数"必须说明口径**——历史上 31/32/33/34/45 五个数字并存
  就是口径未注明所致。另注：`content='clause_fts_content'` 之类的影子表**不是**业务表，
  迁移/审计时不要当资产盘点。
- 主键 ULID 前缀：`doc_`/`clrev_`/`span_`/`patch_`/`bm_`/`ann_`/`proj_`/`task_`/`pt_`/`obl_`/`edge_`/`list_`/`gap_`。
- JSON 字段存 TEXT；时间统一 `datetime('now')` UTC。
- **虚拟表不受外键级联**：删文档必须走 `clause_repo.delete_document()`（显式清 clause_vec/clause_fts）。
- **单写者队列**：所有写操作经 write_queue 表 + 后台串行消费者；启动时 processing→pending 恢复。
- **契约增量台账**：schema 每次变更记录于 `pipeline/03-contract-delta.md`（条目含 DDL/影响面/回滚 SQL；最后一条 2026-09-06 批 32 号表）。

## 8.2 核心知识表

### doc_meta（文档元数据）
`doc_id` PK(ULID)；`standard_no` UNIQUE（GB 30871-2022 / 个人信息保护法）；`standard_name`；`short_code`（归一化检索代码）；`current_revision_id`；`legal_status` CHECK（effective/upcoming/superseded/withdrawn）；`legal_hierarchy`（宪法/法律/行政法规/…/GB/JGJ/DB/T/企标）；`standard_type`（mandatory/recommended）；`doc_type`（standard/条文说明/立法释义/用户自定义/法律法规）；`quality_grade`（A/B/C）；`domain_tags` JSON；`effective_from`/`superseded_by`/`normative_refs`；`file_path`/`file_hash`（SHA-256 防重 R43）。

⚠ `file_path` 指向的文件是**证据 PDF 溯源载体**（证据 tab 预览/高亮打开它）——生产库现有两份指向仓库内部：`wenjianmulu/GBT+39910-2021.pdf` 与 `var/fixtures/测试法.pdf`，另有 21 份指向用户区 `D:\AI\work space\标准\` 与 DSH 附件目录。**删这些文件 = 该文档证据链断裂**。

### clause_revision（条款不可变快照，三型知识单元）
`clause_revision_id` PK；`doc_id`；`clause_key`（**sha256(doc_id+normalized_no)[:24]，跨版本平移凭它**）；`clause_number`（5.2.3 / 第四百九十六条 / 表N）；`title`/`content_text`/`content_markdown`/`table_summary`（table_md 由 content_markdown 派生）；`formula_number`/`image_text`；`hierarchy_path`。
三型字段：`knowledge_type`(data/rule/legal)、`type_confidence`、`modality`、`modality_strength`(0-5)、`behavior_scope`、`subject/object/behavior`、`applicability_condition`、`restriction`、`exception`、`legal_refs` JSON。
`is_mandatory`/`is_suspicious`/`ocr_confidence`；`content_type`（normal/前置说明/附则/附录）；`page_start`/`page_end`；`cross_refs`/`explanation_ref`；`content_hash`（Phase 10.4 幂等回填）；`patched_fields`。
**2026-09-01 排版还原新增列**：`page_breaks`（页界 run-start 编码 `[[行号,PDF页],...]`，行号=content_text 0-based 行索引，首条目恒 `[0,首行页]`；NULL=存量未采集渲染层跳过）；`figure_html`（插图独立列——**关键裁决：绝不进 content_markdown**，防 md 路径判定误翻转页界逻辑）。

### clause_patch（纠错补丁叠加层）
`patch_id` PK｜`clause_revision_id` FK｜`field_name`（**PATCHABLE_FIELDS**：content_text/title/table_summary/content_markdown/is_suspicious/user_confirmed）｜`patched_value`｜`patch_reason`｜UNIQUE(clause_revision_id, field_name)。读取时 fetch_full_clause 透明覆写；写 FTS/向量同事务重算。

### source_span（条款物理原页坐标，bbox 契约见 §9.3）
`span_id` PK｜`page_number`｜`bbox_json [x0,y0,x1,y1]`｜`span_type`(text/table/formula/title)｜`sort_order`。

### clause_fts（FTS5 虚拟表）
clause_revision_id/clause_number/standard_no/title/content_segmented(jieba)/modality/subject/behavior_scope_segmented——tokenize='ascii'，中文预分词写入。

### clause_vec（vec0 虚拟表）
clause_revision_id PK + embedding FLOAT[512]（**查询前必须 load_vec_extension(conn)**）。

### evidence_edge（证据依赖图）
edge_type（clause_relation/exception_relation/definition_relation/reference_relation/correction_relation）；source/target_clause_id；confidence；status。

## 8.3 用户资产表

- **user_bookmark**：条款收藏（检索加权 +0.15），绑定稳定 clause_key。
- **user_doc_bookmark**：标准级收藏（doc_id UNIQUE）。**并入巡检 tier0**（收藏的标准每日优先查官网更新）。
- **user_annotation**：批注（绑 clause_key，跨版本平移不丢；**批注参与 ks_answer 推理**，答案注明"含您的批注"）。
- **project_list** / **watch_list**（tier0 高频层）/ **feedback_log**（Few-shot 数据源）。

## 8.4 合规审查表

review_task / review_point（verdict red/yellow/green）/ obligation_list（items JSON）/ gap_analysis / legal_obligation / internal_policy。

## 8.5 运维与治理表

write_queue / event_log（统一事件模型）/ debug_dump（每次提问落库，容量 1000 自动清理；**同时是 D2 外发审计数据源**）/ operation_log / audit_log / app_config / snapshot_meta / remapping_queue（跨版本映射人工确认）/ alias_store / doc_page_geometry。
**更新模块四表（2026-08-24/09-06）**：update_check_batch / update_change_event / bulk_import_batch / announcement_observed（32 号表，公告发现，SSRF 默认禁内网）。

## 8.6 补丁跨修订平移（Phase 10.4）

- 根因：clause_key 掺 doc_id，跨版本天然不同 → 平移匹配改用 **(short_code, clause_number)**（migrate_patches）。
- 三分支：(a) 新条款原始值==补丁基准值 → 平移；(b) 原始值已变 → remapping_queue pending（人工确认）；(c) 新版无此条款 → 孤儿标记。
- content_text 补丁联动 is_suspicious（人工纠错=复核）；幂等。

---

# 9. 入库管线与 bbox 契约

## 9.1 分层降级入库

- **识别版（有文本层）**：PyMuPDF 快速路径（13 页实测秒级；force_deep 参数控制——原生数字版无需 MinerU，深度解析 900s 超时整单失败实测）。
- **扫描版（无文本层）**：MinerU 2.x 深度版面分析（OCR 自动判定）；`KS_MINERU_DEEP=0` 可跳过。
- **分层降级**：PyMuPDF → MinerU 深度 → 失败自动降级，不阻塞。
- 章节式条款还原（law_text.py）；三型分型（classifier.py）；pypdf 数字回填；OCR 换行清理（normalizeWraps）。
- **入库原子性**：先解析后单事务入库（R1）。
- **parser_worker**：spawn 子进程隔离；**必须先 result_queue.get(timeout) 再 proc.join**（大结果集先 join 死锁）。

## 9.2 docx 一等公民（Phase 11.1）

两档：本机有 Word/WPS → **COM 转 PDF**（SaveAs2 FileFormat=17）→ run_full_ingest（原生保真 + 有 bbox，优先）；无 Word → python-docx 直解（无 bbox，显示"原文为 Word 文档"禁用跳页）。ProgID 探测：Word.Application → Kwps.Application → wps.Application。R43 防重对 docx 同样生效。

## 9.3 bbox 契约（本仓库最隐蔽的跨端约定，已两次踩坑）

- **MinerU middle.json 的 bbox 是 PDF 底部原点（左下、y 向上，页顶文本 y≈页高）**。
- **pipeline 原样直存 source_span（不做翻转）；前端 pdfjs 用 `convertToViewportPoint(x, y)` 直接映射，禁止 H−y 翻转**。
- 历史事故（两次）：早期误判左上原点 → pipeline `_flip_bbox` 翻转 → 前端又 H−y → **双重翻转黄标垂直镜像**。`_flip_bbox` 已删。
- **存量校准**：span_calibration.py（最近行投票——每页构建文字行中心表，对每个 span 取"直读"与"H−y 换算"两种解释近者胜，文档级投票多数决归一为底部原点，幂等）。
- 验证：`scripts/verify_highlight.py`（离屏画 bbox，框内文本必须==条款文本）；回归 tests/test_pipeline.py。
- **行级 bbox（2026-09-01 B5）**：文本块证据 span 从块级×8 条封顶改为行级×全量（行框缺失回退块级——宁粗不高灭）；表格保留块级。

## 9.4 入库自动标签（Phase 11.3）

规则层：standard_no / 年代号 / "代替 GB XXXX-XXXX" / 施行日期正则 + 领域词表。**红线：标签只写 doc_meta，永不改写条款原文/不进引用路径**（有断言测试）。LLM 层增强留待接线；置信度 <0.8 进待确认。

## 9.5 Dry-Run 预览（Phase 11.5 / R27 红线落地 2026-09-11）

`pipeline.analyze_preview()`：快速文本层路径秒级预览（条款数/分型分布/可疑数/样本）——**不落库断言**（测试用全表行数差分 + sqlite_master 差分证明）+ **零外发断言**（egress:"none" 真机确证）。批量场景：异步预览 jobs（preview_jobs.py 引擎侧 + host 侧推进 + 📥 入库预览 tab 三半边）+ 批量分桶（✅/⚠️/❌ 总账）。

## 9.6 数据体检

5 类质量问题（正文换行残留/英文粘连/页脚下节标题泄漏/表格列数不一致/表格脏单元格），GET /api/v1/data/quality-issues；扫描只读零副作用；每条可一键纠错。

## 9.7 排版还原批次（2026-09-01 五件套，用户验收口径：「原文哪里换页我就哪里换页，哪里换行我就哪里换行，且不能强加回车」）

① B3 页界（page_breaks 列 + 渲染层 `<div class="page-break" data-page="N">`，不增删正文行——强加回车=证据卡文字断裂，用户红线）；② B5 行级 bbox；③ B4 表格身份（无题注表格 <4 字 guard 豁免 + title=「表(未识别题注，第N页)」）；④ C1 资产端点（`GET /documents/{doc_id}/assets/{fname}`，sha256 白名单防穿越）；⑤ C2 插图入库（figure_html 独立列 + `<p class="fig-strip">` + 图题/物理就近/独立"图"条款三段式绑定）。C3 兜底：figure_locator.locate_middle_figure。

## 9.8 官方法规来源管线（2026-08-24）

法规**只从两个官方源**获取，下载官方 Word → 转 PDF → 走 §9.1 标准管线（预览/高亮/目录与国标同构）。

- **来源白名单**（law_source/http.py 强制，非白名单域抛 ValueError）：`flk.npc.gov.cn`（含签名下载域 flkoss.obs-bj2.cucloud.cn）、`sousuo.www.gov.cn`、`www.gov.cn`、`gov.cn`。
- **flk**：POST /law-search/search/list 搜索（sxx=[3] 仅有效）、GET flfgDetails?bbbs= 详情（sxx 时效 3有效/2被修改/4未生效/1废止）、GET download/pc?format=docx（勿拼 ossFile 路径，实测返回 SPA 首页）。
- **gov.cn**：GET sousuo.www.gov.cn/search-gov/data（t=zhengcelibrary、childtype、文号/年份）；结果链接字段是 `url`（piclinksurl 常空）；公报页无下载 → 正文 HTML 生成 docx 兜底（content_origin:"web"）。
- **转换链**：LibreOffice headless 主选 → WPS/Word COM 回退。转换源头只能是官方 docx。
- **入库**：docx 落 `<data_dir>/law_source/<source>/<source_id>/`（meta.json 溯源）→ run_full_ingest(doc_type="法律法规")；doc_meta 溯源列（source/source_id/source_url/downloaded_at/source_status）幂等迁移。
- **更新检查**：detail.sxx 与入库 source_status 比对报时效变更。
- **CLI/API**：`scripts/fetch_law.py`；`/api/v1/laws/sources|search|ingest|check-updates`。
- 工程细节（端点参数/附 A 接口探测法/§7 合规边界）见 `docs/LAW_SOURCE_PLAN.md`（保留原文件）。
- 限速 ≥0.6s/请求；3 次退避重试。

## 9.9 标准状态巡检渠道（2026-08-27 实测定型）

渠道能力矩阵（保留原文件 `docs/STD_STATUS_CHANNELS.md`）：**cssn 单渠道覆盖国标 1~6 类**（openstd 盲区正是此前 270 条 miss/53% 的根因）；ndls 有验证码；全渠道探测实证见 `docs/CHANNEL_PROBE_REPORT.md`（含 ANOM-002 JA3/TLS 指纹拦截与 curl_cffi impersonate 决策）。铁律：**真实站点先于 mock**（ANOM-003 教训）；渠道适配器 RUN_LIVE 门控。


---

# 10. API 与 SSE 契约

## 10.1 通用

随机端口 + 一次性 Bearer token；所有请求带 `Authorization: Bearer <token>`；**仅 `/api/v1/health` 免 token**；CORS 预检 OPTIONS 放行（允许 localhost/127.0.0.1 任意端口——DSH web GUI 3080 跨源 fetch 引擎）。响应包裹 `{"code":200,"status":"success","data":...}`。

## 10.2 端点全表（要点；底数见下"枚举实测"）

> **枚举实测（2026-09-16，AST 全量重扫）**：`src/core/api/` 六个模块合计 **127 个端点**
> （method × path；**全部**在 `/api/v1/` 下），**113 个唯一路径**（14 条路径是一路径两方法，
> 如 `GET+POST /bookmarks`）。全部以 `app.<verb>()` 装饰器注册；五个 `routes_*.py` 均由
> `create_app()` 显式 `register(app, …)` 挂载，无遗漏。分模块：`server.py` 77 ·
> `routes_update.py` 30 · `routes_law.py` 7 · `routes_ingest_preview.py` 6 · `routes_report.py` 4 ·
> `routes_settings.py` 3。
>
> ⚠ **旧"消费面四分类"的口径没有留下，且底数已无法对账**：原文写"**120** 端点"并给
> LIVE-PRODUCT 47 / TEST-ONLY 54 / ZERO 19 / SCRIPT-ONLY 0，但 47+54+19=120 ≠ 今天实测的 127，
> 说明当时的分母与今天不同（或含未记录的排除）。**故该四分类只能当 2026-09-13 历史快照，
> 不可当现状引用。**
>
> ✅ **但它的 ZERO 标签经抽样复核站得住**（2026-09-16，抽查 8 条）：
> `POST /compare`、`POST /export/citations`、`POST /laws/check-updates`、
> `/clauses/office-edit/poll`、`/clauses/office-edit/commit`、`/documents/{id}/versions`、
> `/clauses/{id}/backlinks`、`/annotations` CRUD —— 逐条按路径字面 + host 别名两种形式
> 全仓（client/host/tests/scripts）搜索，**未发现反例**。
> ⚠ 这条抽检同时暴露一个反向陷阱：**用单词做匹配会造出假反例**——Python 的
> `from __future__ import annotations` 让 `/annotations` 看似"测试在用"，函数名
> `compare_clause_texts` 让 `/compare` 看似"测试在用"。**匹配必须是路径级，不是词级。**
>
> ⚠ **重做必须用"别名感知"匹配器**，否则会得出错误的 ZERO。host 把引擎路径重写成语义不同的
> 同源前缀（`/ks/doc-image/{doc}/figure/{no}` → `/api/v1/documents/{doc}/figure/{no}`），另有
> host 自有路由（`/ks/session`、`/ks/bbox`、`/ks/assets/*`）根本没有对应的引擎端点。
> **本会话实测该错法**：朴素字面匹配把 `/documents/{id}/file`、`/figure`、`/formula`、
> `/table-image` 四个**确实在用**的端点全判成 ZERO —— 机械结果不可照抄。
>
> **2026-09-13 端点接线**：图/公式/表图抽取 3 端点 ZERO→LIVE（`/figure/{fig_no}`｜`/formula/{fno}`｜`/table-image/{page}/{idx}`——host 代理 `plugin/src/docimage.js`（`/ks/doc-image/*` 前缀，Bearer 只在 host 侧，X-Frac-* 逐字透传，引擎 404 状态码透传+本地信封=占位隐藏契约）+ client 正文视图（KsEvidenceTab「📄 正文」模式：KsDocTextView 渲染 content_html，fig-embed/table-embed/katex-formula 占位经同源代理拉 PNG/SVG blob 接线；HTML 经结构白名单消毒——剥 script/on*/外链 src，过滤不变量=属性过滤只在节点被 pop 时做）。E2E 实测（GB/T 34406 语料）：figure 1 SVG 矢量重绘 2601B / A.1 PNG 44KB / formula 1@3.7 PNG 3007B 带 X-Frac 三头 / 无图 404。现网语料边界：fig-embed 92 处 · katex 510 处 · asset-embed 124 处（本批不接线，只显 alt）· table-embed 0 处（代码链路通、待语料）。

| 分组 | 端点 |
|---|---|
| 健康 | `GET /api/v1/health`（status/uptime/db_status/vector_engine/parser_worker） |
| 入库预览（全 LIVE） | `POST /ingest/preview`｜`/preview/batch`｜`GET /preview/inbox`｜`POST /preview/jobs`｜`GET /preview/jobs/{id}`｜`POST /preview/jobs/{id}/abort`（Dry-Run + 异步预览 jobs） |
| 批量入库（TEST-ONLY 3 + ZERO 1） | `POST /ingest/bulk`（万级三阶段）｜`GET /ingest/bulk/{id}`｜`POST /ingest/bulk/{id}/resume`｜`/abort`（ZERO） |
| 检索问答 | `POST /chat/completions`（SSE；history/query_mode/answer_scope/免追问语法）｜`POST /ks/answer`（取证答案）｜`POST /batch/qa`｜`POST /compare`（R42，ZERO）｜`POST /aliases/extract` |
| 文档 | `GET /documents`｜`/categories`｜`POST /documents/batch-delete`｜`GET /documents/{id}/file`｜`/tree`｜`/clauses`｜`/clauses-by-prefix`｜`/versions`（ZERO）｜`/figure/{fig_no}`（LIVE 2026-09-13，截图/矢量重绘+C3 兜底）｜`/formula/{fno}`（LIVE）｜`/table-image/{page}/{idx}`（LIVE）｜`/assets/{fname}`（sha256 白名单）｜`POST /documents/{id}/impact`（R49）｜`/migrate-patches` |
| 条款 | `GET /clauses/resolve?standard_no&clause_number`（年份宽容+表回退）｜`GET /clauses/{id}/meta`｜`/backlinks`｜`/spans`｜office-edit start/poll(ZERO)/commit(ZERO)/cancel；`POST/GET /clauses/patches` |
| 收藏/批注 | `/bookmarks`｜`/doc-bookmarks` CRUD（LIVE）｜`/annotations` CRUD（ZERO ×3）｜`/projects(+clauses)`（ZERO ×4） |
| 合规 | `POST /compliance/review`｜`/review/{task_id}/execute`（普通 JSON，非 SSE）｜`/compliance/obligations` 全族 6 条（ZERO ×5 + export 1）｜`/gap-analysis`｜`/compliance/policies` |
| 更新/发现/法规 | `/update/*` 37 条（check/batch/changes/announce×8/subscriptions/report×2）｜`/discover/*` 4 条｜`/laws/sources|search|ingest|catalog|verify`（TEST）｜`/laws/check-updates`（ZERO）｜`/data/package/export|import` |
| 导出 | `POST /export/review/{task_id}`｜`/export/obligations/{id}`｜`/export/citations`（ZERO）｜`GET /export/download?name=`（限 exports 目录） |
| 视觉 | `POST /vision/locate`（贴图→条款定位，本地 MinerU OCR，零外发） |
| 效力报告（全 LIVE） | `GET /report/effect`｜`/docs`｜`/color`｜`POST /report/effect/export`（host 侧裁剪——绝不回传全量分类树） |
| 审计/运维 | `GET /egress/audit(+export)`｜`/health-board`｜`/operation-log`｜`/debug-dumps`｜`/data/quality-issues`｜`/snapshots` |
| 设置（全 LIVE） | `GET/PUT /settings/api-config`｜`POST /settings/api-config/test` |

## 10.3 SSE 事件顺序（chat/completions，**冻结不得增删 reorder**）

1. `evidence` — `{evidences[], expanded_evidences[], time_warnings[]}`（证据对象含 clause_revision_id/doc_id/clause_key/knowledge_type/is_suspicious/bookmarked/annotations/patched_fields）。
2. `status` — `{phase:"streaming_with_verification_pending"}`。
3. `delta` — `{content}`（0..n 次）。
4. `verification` — `{is_valid, answer_confidence, confidence_reasons[], unsupported_clauses, unverified_numbers, modality_violations, legal_element_violations}`。
5. `done` — `{}`。

另有 `clarify` 事件（首轮缺核心参数时替代检索+LLM）。请求体扩展：`history`（最近 4 条×300 字）；`query_mode: thorough|default|quick|guess`；`answer_scope: concise|full`。

## 10.4 契约变更流程（红线）

凡动 `schema.sql` / 通道枚举与 RRF 权重 / SSE 事件顺序 / 安全条款 → **必须先改 `pipeline/03-contract-delta.md`（契约增量台账）+ `tests/test_contract.py`，再改实现**，评审通过后方可合入。（原 docs/onboarding/contract.md 已不存在——见附录 A。）

---

# 11. 测试体系

## 11.1 门禁五件套（当前基线，2026-09-13 扩容）

- **pytest**：`.venv/Scripts/python -m pytest tests -q` → **1214 passed + 3 skipped + 0 failed + 1 xfailed**（**2026-09-17 实测**；那 1 条 xfail 钉住"`pipeline._STD_CODE_FRAG` 家具剥离是「页码+标准号」判据的**第二个所有者**、尚未接上下文"这一已量化未修项，见 DEVELOPMENT-HISTORY §八.3。演进链 24→…→792→828→1145→1166→1180→**1214**，全程只涨不跌）。
  ⚠ **2026-09-16 起门禁自我豁免已关闭**：`test_golden_gate` 旧实现在基线缺失时
  `write_text` 重建 + skip —— **删掉 `eval/baseline.json` 即可让红线 6 失效**（全项目
  唯一"一步可破坏"的防线）。现改为：基线缺失=**失败**且不自动重建，首建走显式开关
  `KS_BASELINE_BOOTSTRAP=1`；并新增"基线键集必须覆盖 KEYS"断言（防裁剪指标式规避）。
- **插件 smoke**：`cd plugin && npm run smoke` → **11 段**全 PASS（2026-09-16 移除 `smoke-bs-contract`——它只服务已下线的第三方 `dsh-better-sidebar`）。11 段依次为 pdf-fit / pdf-panel / settings / settings-guard / effect-tool / chatmode / ingest / engine-guard / client-entry / **smoke-docimage（2026-09-13 端点接线新增，24 断言：路径解析/栅栏/字节与 X-Frac 透传/404 状态码透传+本地信封/401×2/dpi 钳制）** / **smoke-sanitize（同日消毒器回归，13 断言：剥壳上移节点必被过滤/占位 class 必存活/src 直剥/文本保全）**。
- **命令回归**：`cd plugin && npm run verify:commands` → 15/15。
- **类型门禁（TS）**：`npm run typecheck` = `tsc --noEmit -p plugin/client` → 0 错误（批 8 新增，plugin/client 纳入检查）。
- **类型门禁（Python，2026-09-13 新建）**：`npm run typecheck:py` = `.venv\Scripts\python -m mypy` → **120 文件 0 错误**（基线演进 126→95→82→47→10→0）。非 strict 保守口径：`[tool.mypy]` 开 check_untyped_defs/no_implicit_optional/warn_redundant_casts；第三方无 stub 包 ignore_missing_imports；每处 `# type: ignore[code]` 带行内中文理由（fcntl/curl_cffi/openai-SDK/pypdf 回退等环境限制，运行时有守卫）。mypy>=1.10 已回 pyproject dev extras。修复附带捕获真实缺陷：announce.py `Path` 未导入（Excel 导出必崩 P1）、server.py 三处 `_p` int→str 变量复用、effect_report 循环变量遮蔽、write_queue `int(None)`、office_roundtrip 条款并发删除 None 崩溃。

## 11.2 测试文件清单（tests/ 80 个 test_*.py + conftest）

契约与门禁：test_contract / test_contract_eval / test_golden_gate / test_golden_set。
检索与理解：test_retrieval / test_reranker / test_r5a / test_understanding / test_t06 / test_layout_fidelity。
入库：test_pipeline / test_docx_ingest / test_dryrun / test_auto_tag / test_phase4~8 / test_mineru_channel / test_table_binding / test_quality_rules。
合规：test_compliance / test_effect_report / test_law_*（law_source 系列）。
凭据与安全：test_credentials_namespace（34 用例双向断言）/ test_batch7_security_hardening / test_egress。
更新与巡检：test_update_*（api/inspector/…）/ test_effect_report。
插件协作：test_ks_answer / test_loop2_{oracle,driver,vlm}。
运维：test_api / test_backup / test_storage / test_supervisor / test_phase10/12/13_blindspots / test_selfcheck_fixes / test_vision / test_fewshot / test_patches / test_patch_migration / test_update_package。

## 11.3 测试隔离约定（三次踩坑总结）

1. **共享会话级库**：conftest 用会话级 KS_DATA_DIR 临时目录（ignore_cleanup_errors=True——Windows 文件锁）。
2. **测试 id 必须完整 ULID**：前 6/8 hex 是时间戳，同毫秒碰撞。
3. **禁止绝对计数断言**：共享库下用相对断言（any(...) / 限定 doc_id）。
4. **清库禁用 DELETE FROM sqlite_master** → 逐表 DROP + load_vec_extension。
5. 连接没关干净时 TemporaryDirectory 清理报 PermissionError → 注意 close_thread_connection()。

## 11.4 Golden Set 门禁测试

tests/test_golden_gate.py：对 eval/golden/knowledge-snapshot.db 跑指标，与 eval/baseline.json 比对，任何指标回退 >2pp 即失败。**任何检索/提示词改动必须过此门禁**（红线 6）。⚠ eval/ 目录是门禁三件最小集（golden/ + run_benchmark.py + baseline.json），**不得删除**——删 baseline.json 会让门禁"重建基线"自我豁免。

---

# 12. 技术栈与环境

## 12.1 技术栈总表

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | Python 3.12.14（uv 安装） | ⚠ 勿用系统 3.14（pydantic-core/fasttext 无 wheel） |
| Web | FastAPI + uvicorn | 随机端口 + 一次性 Bearer token |
| 数据 | SQLite 单文件（WAL） | %APPDATA%\KnowledgeStation\database\knowledge.db |
| 向量 | sqlite-vec（vec0，512 维） | bge-small-zh-v1.5；查询前 load_vec_extension |
| 全文 | FTS5 + jieba 预分词 | tokenize='ascii'；_fts_query() 过滤+引号 |
| Embedding | fastembed | 本地缓存 %APPDATA%\KnowledgeStation\models，离线可用 |
| Rerank | BAAI/bge-reranker-base | CPU/ONNX ~400MB；离线降级 |
| LLM | DeepSeek（OpenAI 兼容） | 凭据链见 §15 |
| OCR | MinerU 2.x + RapidOCR（流程图重绘） | 通道语义见 §15.4 |
| 前端 | DSH 插件 client（React 18 + esbuild 单文件 bundle ~1.1MB） | 批 8 起 GUI = DSH Web 宿主侧栏 tab |
| PDF | pdfjs-dist 5.7.284（插件） | 单页渲染+红色定位箭头；worker/wasm 经宿主 /ks/assets/* |
| 桌面壳 | **无** | 业主裁决：「把 DSH 整个打包成 EXE，本项目不单独打包」 |

## 12.2 环境事实（换机器/重置环境前必读）

| 项 | 值 |
|---|---|
| 工作目录 | `D:\AI\work space\zcode`（git 仓库，本地身份 zegel@local 绝不 --global；tag baseline-792） |
| venv | `.venv/`（3.12）——重建 `uv venv --python 3.12 .venv` + `uv pip install -e ".[parser,vision,proc,wincom,dev]"`（2026-09-13 修复 pyproject 后；**无 uv.lock**——重装会解析最新版本，pymupdf 实装 1.24.14 是验证过的组合） |
| MinerU 模型 | `C:\Users\Zegel\.cache\modelscope\models\OpenDataLab--PDF-Extract-Kit-1.0\snapshots\master`（~2GB）；mineru-models-download -s modelscope -m pipeline |
| MinerU 配置 | `~/mineru.json`（新版）+ `~/magic-pdf.json`（兼容版），两份都在别删 |
| 数据目录 | `%APPDATA%\KnowledgeStation\`（KS_DATA_DIR 可重定向） |
| 会话文件 | `%APPDATA%\KnowledgeStation\engine.session.json`（{port,token,pid,started_at}，引擎重启必变） |
| 插件状态 | `ks-{inspection,announce,chatmode,ingest}.json`；ks-chatmode.json 可 KS_CHATMODE_DIR 单独重定向（多 dsh 实例必须取值一致） |
| 引擎日志 | `var/engine.log`（spawn 时写 PORT/TOKEN 两行） |
| Node | v26.7.0 / npm 11.19.0；根 node_modules（react/react-dom SSR + typescript + esbuild）+ plugin/node_modules（pdfjs-dist + esbuild） |
| 备份 | 引擎 VACUUM INTO 快照滚动 7 份 + 手动；KS_BACKUP_DIR 可指向独立物理盘 |

## 12.3 常用命令（仓库根）

```text
只起引擎      .venv/Scripts/python -m src.core.main
全量测试      .venv/Scripts/python -m pytest tests -q
类型门禁      npm run typecheck
插件冒烟      cd plugin && npm run smoke
命令回归      cd plugin && npm run verify:commands
前端构建      cd plugin && npm run build:client      # -> plugin/client.js
高亮回归      .venv/Scripts/python scripts/verify_highlight.py
```

---

# 13. 运维

## 13.0 数据/代码边界（项目原则）

| 层 | 位置 | 原则 |
|---|---|---|
| 代码（可复用） | 仓库 `D:\AI\work space\zcode\` | 脚本不硬编码数据路径，参数化或从配置读 |
| 主数据（可维护） | `%APPDATA%\KnowledgeStation\`（KS_DATA_DIR 可重定向） | 备份=拷数据区；升级=换代码区 |
| 国标原始文件 | `D:\AI\work space\标准\`（35,243 PDF，141G） | 只读源；不进代码树 |
| 运行产物 | KS 数据目录 / 国标目录同级 | 一律不进 var/ 代码树；GBK CSV 供 Excel |

## 13.1 启动与重启

- **正常启动**：业主从平时入口启动 DSH → 插件自动注册（ks_ping/ks_resolve_clause/ks_answer/ks_effect_report 工具 + 侧栏 tab + 设置区）；引擎按需懒拉。
- **引擎单独调试**：`python -m src.core.main`。
- **引擎重启**：直接 Stop-Process，下次 ks_ping 拉新引擎。批量任务跑着时不要杀。
- **DSH 宿主重启**：业主操作；插件 src 改动要宿主重启才 live。**绝不主动杀宿主**。⚠ 桌面「DSH复活币X1」是 dsh-fuhuobi 插件的**回滚恢复键**（恢复 profile 配置 + node_modules）——只在 DSH 崩了/黑屏/插件装崩时用，**不是重启入口**。

## 13.2 引擎连接与坑

client 连接链：侧栏 tab → 宿主同源代理 `/ks/session`（每次载入重取）→ `/ks/pdf`/`/ks/bbox`/`/ks/assets/*` 同源转发。host 侧状态镜像（ks-*.json）：浏览器关掉后 host 权威推进任务；引擎不可达时镜像兜底并**如实标注 stale**。

## 13.3 supervisor 与健康看板

`supervisor.py`（引擎看门狗——崩溃重启+熔断；历史模块保留，**职责主体已移交插件 host 的 ensureLive 守护**）。`GET /api/v1/health-board`：六引擎状态 + 知识库统计。Debug Trace：每次提问全量落库 debug_dump。

## 13.4 外发审计（D2 红线落地）

- 数据源：debug_dump（trigger_type='user_export'）+ 非 chat 云调用 record_egress()（trigger_type='egress'，返回 dump_id 即 Trace ID）。
- API：`GET /api/v1/egress/audit?limit&offset`（token 保护，默认脱敏摘要）、`/egress/audit/export`（完整 payload 仅用户主动导出时提供）。
- **OCR 出网门控**（批 7）：probe_token 真实出网必带 `went_on_the_wire` 审计标记。

## 13.5 快照备份与恢复

backup.py：VACUUM INTO 在线备份到 `%APPDATA%\KnowledgeStation\backups\`；自动快照滚动 7 份、手动永不清理；恢复前校验和验证（db_checksum 不匹配拒绝）；实际 db 替换由上层执行（restore 返回路径+说明；`scripts/restore_package.py` 承担还原流程，被 data_package.py 引用）。

## 13.6 日志与调试

引擎日志 `var/engine.log`。API 调试带 Bearer token。**中文 JSON 走 httpx/requests，禁止 Git Bash curl 带中文**（GBK 编码写坏数据）。

## 13.7 活脚本清单（scripts/，冗余清剿后）

| 脚本 | 职责 |
|---|---|
| ks-credential-{migrate,reconcile,readers-scan}.py | 凭据迁移/对账/读者排查（批 1/2 工具，active） |
| make_handoff_zip.py | 交接打包 |
| dsh-host-restart.ps1 / dsh-host-watchdog.ps1 | DSH 宿主重启辅助/看门狗 |
| dsh-gui-e2e-ingest.ps1 | GUI 端到端入库冒烟 |
| dsh-session-dump.mjs | DSH 会话转储 |
| fetch_law.py | 法规抓取 CLI（flk/govcn） |
| verify_highlight.py | 离屏 bbox 验证 |
| restore_package.py | 数据包还原（data_package 引用） |
| _stdparse.py | 标准号解析（loop2/driver_v2 import——**勿删**，批 10 归档事故前科） |
| loop2/ | 四层收敛环（driver_v2/oracle/vlm；3 个 test_loop2_* 依赖） |
| std_bulk_import.py / std_status_check.py / std_status_import.py / std_status_report.py | 国标批量导入/状态巡检链 |
| make_law_pdf.py（tests/fixtures/） | 测试 PDF 生成器（**注意：默认输出 var/fixtures/测试法.pdf 是生产库活数据**） |

**已删除**（2026-09-12 冗余清剿，git 可溯）：scripts/archive/（48 个一次性调试）、backfill_* / repair_span_origin / reingest_* / eval_contract / program_diff / debug_loop_driver / campaign_driver / make_repair_queue 等一次性脚本。历史：批 10 曾把 46 个调试脚本归档 scripts/archive/，本次连归档一并删除（零引用）。


---

# 14. 插件前端（plugin/client，批 8 后唯一 GUI）

## 14.1 结构

- `entry.ts`：tab 注册（📖 证据 PDF / 📊 效力报告 / ⭐ 收藏 / 📥 入库预览）+ 设置栏目（法规标准知识库 / API 配置）。
- `KsEvidenceTab.tsx`：证据 PDF 查看器——跳页、红色定位箭头（bbox 底部原点 + pdfFit/pdfPanel 两条几何规则）、标题目录（纯悬浮 overlay，四轮推翻后定案）、缩放、打开外部。
- `api.ts`：引擎 fetch 链（经宿主代理，Bearer 由 host 注入）。
- ~~`bsContract.ts` + `dsh-better-sidebar.d.ts`~~ **已于 2026-09-16 删除**（第三方
  `dsh-better-sidebar` 被官方 `@deepseek-ai/dsh-client-ui-sidebar-right` 取代）。
  现行契约面：`ksSidebar.ts`（官方两段式注册 + 新旧映射表）/ `ks-evidence-props.ts`
  （证据组件自有 props）/ `KsEvidenceHost.tsx`（官方座位注入 → 组件 props 的适配层）/ `ksPrefs.ts`（偏好存储）。
- `client.js`：esbuild 单文件产物（~1.1MB），DSH ModuleLoader 加载；**git 跟踪**（dsh plugin add 直接消费）。
- package.json `dsh.client.inject` 列官方 `@deepseek-ai/dsh-client-ui-sidebar-right`（信息性声明）；
  `entry.ts` 仍**只用 `inject: ['slots']`**——右侧栏两面经 `ctx.get()` 运行时探测，
  因为硬 inject 会让官方列一改名/未挂载就停住整个 client half。

## 14.2 宿主桥（plugin/src/index.js）

- 模型工具 4 个：ks_ping（健康探测）/ ks_resolve_clause（条款快查，毫秒级）/ ks_answer（取证答案，120s 超时**契约下限**）/ ks_effect_report（效力报告，host 裁剪）。
- `/ks/*` 同源代理路由：session/pdf/bbox/assets（信任栅栏覆盖全部 18 条路由，verifier 审计过）。
- 引擎守护：ensureLive + stale 重拉 + 看门狗；idle 30 分钟优雅关停（批 3：15→30 + 查法规模式 keepalive + 并发 ensureLive 合并防幽灵引擎）。
- host 侧状态镜像 ks-{inspection,announce,chatmode,ingest}.json（浏览器关闭后 host 权威推进）。
- 异步 jobs 路由（批量预览三半边之一）。

## 14.3 斜杠命令（业主定稿）

`/forensic`（查法规模式，会话级）+ `/bookmarks`（仅收藏，依附前者）。历史：曾为输入框按钮组，业主反馈「输入框顶上多了几个按钮还是太丑了，删了，做成用/符号调用」。

---

# 15. 凭据体系（独立成篇——未来接手者最可能重犯的错）

## 15.1 权威读链（批 2/4 定稿，全项目唯一权威表述）

**加密存储 `<data_dir>/secrets.json`（Windows DPAPI）优先 → 环境变量（KS_LLM_API_KEY 等 KS_ 前缀名）→ 旧名 DEEPSEEK_API_KEY 只读回退**。注册表 HKCU\Environment 只作只读覆盖。**引擎与脚本绝不写注册表**。HKCU\Environment 本项目三键（DEEPSEEK_API_KEY / KS_MINERU_CLOUD_API_KEY / SCNET_OCR_API_KEY）已全部迁移删除（后者以 KS_SCNET_OCR_API_KEY 名入加密存储）。

## 15.2 2026-09-11 遮蔽事故（根因链，照录防重犯）

原实现把 LLM Key 写进裸全局名 `DEEPSEEK_API_KEY`——而 **DSH 宿主继承的进程环境变量优先级最高且只读、启动时冻结快照** → 裸名遮蔽了 DSH 自己的凭据层 → DSH 模型设置页密钥输入框被置灰（业主问责）。修复：命名空间化为 `KS_LLM_API_KEY`（旧名降级只读回退）。verifier 三路审计还抓出修复自己引入的 P1（adopt_legacy 无条件覆盖会永久清掉用户新 Key）。**业主裁决（照录）：「不要动系统层」**——不写注册表、不改全局环境变量、不用 --global git 配置，这条纪律适用于本项目一切代码。

## 15.3 凭据工具链

- `scripts/ks-credentials-migrate.py --apply --delete-legacy`：注册表 → 加密存储迁移；**删旧名后必须重启 DSH 宿主**（进程环境快照冻结）才生效；脚本不回显 Key。
- `scripts/ks-credential-reconcile.py`：引擎↔DSH 名字配对 + 指纹比对。
- `scripts/ks-credential-readers-scan.py`：谁在读旧名（只记存在性/长度/pid，绝不记值）。
- `tests/test_credentials_namespace.py`（34 用例）：LEGACY_ALLOWED_FILES 白名单 + **双向硬断言**（条目指向已删文件会红=幽灵条目检查；批 8 曾靠它抓回 Electron 残留）。
- secrets.json 崩溃注入测试 3 条（批 7）。

## 15.4 OCR 分发通道语义（2026-09-08 业主裁决修订）

**已配置云 Key → 云优先、本地兜底；未配置 → 直接本地通道（纯本地不外发）**——不再有"本地优先"分支。`KS_MINERU_CLOUD=0` 显式禁云 / `KS_MINERU_LOCAL=0` 跳本地 / `KS_MINERU_DEEP=0` 整体跳过。云 Key 用户自配（设置面板「API配置」，加密存储），保存即生效。动机：第三方免费 OCR 配额随时失效（实测轻度使用即封号）。OCR 出网必带 went_on_the_wire 审计（批 7）。

---

# 16. 规则、红线与优先级宪法

## 16.1 文档规则（2026-09-12 修订）

1. **事实源文档 = 本文件 + README.md + docs/INTRODUCTION.md + docs/REQUIREMENTS-v4.3.md + docs/DEVELOPMENT-HISTORY.md**（直接修订保持最新，不搞无限追加附录）。⚠ 旧规则引用的 MAINTAINER-GUIDE / contract.md / coverage-matrix / PHASE-INDEX / FRAMEWORK-v5 / ROADMAP-v5 均已散佚（见附录 A），其有效内容已固化进本文件。
2. 施工日志照常逐阶段写；失去参考价值的旧日志可压缩合并。
3. 删除前置条件：内容已失效或已被更高层文档吸收；冗余清剿删除走 git（历史可溯）。
4. **本仓库是 git 仓库**（2026-09-12 批 0 起，tag baseline-792）——删除 tracked 文件可从 git 恢复；var/ 等 gitignore 区**删除即真删**，拿不准的先备份再删。
5. 历史 phase 日志残留的旧规则表述，以本节为准。

## 16.2 框架决策（v5 决策，仍有效）

| # | 决策 |
|---|---|
| D1 | 删除"零外发"验收红线（2026-08-23 业主裁决） |
| D2 | **外发可审计**成为替代性信任承诺（所有外发 payload 落库、可见、可导出） |
| D3 | 复杂编辑走 MS Word / WPS 往返通道；快速小改走补丁双轨 |
| D4 | 保留 LLM/embedding/reranker 的 backend 抽象 seam（OpenAI 兼容） |
| D5 | **撤销残留的"原始文档零外发"禁令**（2026-09-17 业主裁决）。D1 当时只删了**验收红线**，`REQUIREMENTS-v4.3.md` §0.1 第 2 条的 `[MUST NOT] 原始文档零外发` 与代码里的**结构性锁**（`dry_run.py` 不接受 `deep_fallback`、`preview_jobs.py`、`routes_ingest_preview.py:49`）一直留到 2026-09-17，**持续压制深度解析通道**。业主裁定："不能外发的红线不要……我也不知道为啥之前要这样限制自己"。⇒ 该红线改写为 `[MUST NOT] 无留痕外发`（= D2 外发可审计），**是否把原始文档送云端由用户决定，系统不再代为禁止，但必须留痕**。 |

## 16.3 优先级宪法（冲突裁决）

**P1 准确性 > P2 入库便利性 > P3 体验顺滑 > P4 代码简洁 > P5 性能需求**。

裁决示例：
- reranker +200ms 延迟（P5 vs P1）→ 上，P5 让步。
- 通道代码绕但消融证明有贡献（P4 vs P1）→ 保留。
- 自动标签偶发误标（P2 副作用）→ 可接受——标签永不进引用与原文。
- Word 往返解析不出干净补丁（P3 vs P1）→ 拒绝落库，不写脏补丁。
- 为优雅重做存储抽象（P4）→ 否决。

## 16.4 工程铁律

1. 测试基线只涨不跌（数字见 §11.1，本条不重复维护——历史上这里写死过 828，随门禁扩容即失真）。
2. 契约变更流程：schema / 通道枚举与 RRF / SSE 顺序 / 安全条款 → 先改 pipeline/03-contract-delta.md + tests/test_contract.py。
3. 写操作走单写者队列（write_queue），不得绕过。
4. bbox 底部原点契约不要碰。
5. SYSTEM_PROMPT 规则 1~9 只能增强不能回退成纯证据主义。
6. API Key 只从加密存储/环境变量读取（链见 §15.1）；代码库严禁明文密钥与本机绝对路径。
7. 中文 JSON 用 httpx/requests，禁止 Git Bash curl 带中文。
8. 云调用必走 egress_audit；标签永不改写条款原文。
9. 生产库 doc_meta.file_path 指向的文件（wenjianmulu/、var/fixtures/、用户区标准目录）**禁止删除/移动**——删=证据链断裂。

---

# 17. 未实现 / 挂起 / 条件触发清单

> 需求状态以 docs/REQUIREMENTS-v4.3.md + 本表为准（原 coverage-matrix 94 项已散佚）。

| 项 | 状态 | 卡点/建议 |
|---|---|---|
| 纯扫描页方向自动检测 | 未实现 | 需 OCR OSD；库内文档抽检全部正立 |
| R15/R70 公式可检索 | 未实现 | 公式以 MinerU <eq> 保存；先做"公式编号→条款"索引 |
| R38 使用统计看板 | 未实现 | 用 dsh 生态 usage 插件（Non-goal 自建） |
| R44 离线模式 | 降级为可选 | backend seam 已有 |
| 剩余测试盲区 | 部分 | R61/R72/R73/R76/R-L3 等 |
| bge-m3 升维 | 不触发 | recall@5 97.8% >> 85% 验收线 |
| LLM advisory judge | 判定砍 | 指标已达标，省额度 |
| 端点消费面四分类（2026-09-13 精确化，替换旧"约 55"粗估） | ⚠ **底数对不上，标签仍可信** | 旧快照：LIVE-PRODUCT 47 · TEST-ONLY 54 · ZERO 19 · SCRIPT-ONLY 0（合计 120）。**2026-09-16 AST 实测底数为 127 个端点 / 113 条唯一路径**，120 与 127 对不上 → 四分类占比不可当现状引用。**但抽查 8 条 ZERO 标签全部站得住**（见 §10.2），故分类结论可用、分母须重算。图/公式/表图 3 端点 2026-09-13 已接线 ZERO→LIVE 这一条仍然有效。重算需别名感知 + 路径级匹配（词级匹配会造假反例） |
| exceptions.py 4 个未 raise 的异常类 | 现状 | 契约预定义，保留 |
| office-edit poll/commit 端点 | 已实现 | 前端入口在 DSH 侧「数据体检」tab |
| 知识库多用户/权限 | Non-goal | v5 §6 |
| Electron 打包 | **已退役** | 批 8 业主拍板；桌面化由 DSH 整体打包承担 |
| 万级语料战役 | 等业主拍板 | 批 9 种子样本不适合正式入库（一本重复、一本无国标结构） |

---

# 附录 A. 已退役系统索引（防考古迷路）

| 系统 | 何时退役 | 去哪找 |
|---|---|---|
| Electron 壳 + Vite + 双栏 React SPA（App.tsx/证据卡/TipTap 阅读面/PdfViewer 面板） | 2026-09-12 批 8（业主拍板「把 DSH 整个打包成 EXE，本项目不单独打包」；删 618+ 文件、卸 644 npm 包） | git 提交 `0dcb67f`（633 files changed）与术前备份 `D:\AI\zcode-backups\20260912-pre-batch8\` |
| dev_launcher.py / restart_dev.py 一键启动 | 批 8 | git 历史 |
| TipTap 原位纠错界面 | 批 8（纠错收敛到「数据体检」tab + Office 往返） | git 历史 |
| Univer 编辑器 / OnlyOffice | 2026-08 phase 13.1（画布空白不渲染，弃用） | git 历史 |
| v1 追问槽位表（THEME_SLOT_KEYS/CORE_SLOTS） | phase 13.1 | git 历史 |
| `_flip_bbox` 双重翻转 | 2026-08-23 bbox 根修 | git 历史 |
| scripts/archive/ 48 个归档调试脚本 | 2026-09-12 冗余清剿（零引用） | git 历史（提交 8f02c5b） |
| docs/_deprecated/ 30 份旧文档 | **从未存在**——README/旧百科的 12 处宣称是文档谎言；30 份原件在 git 之前散佚，不可恢复 | 本文件 + DEVELOPMENT-HISTORY.md 承载其有效结论 |
| pipeline/00~13 流水线文档（除 03） | 2026-09-12 冗余清剿（结论并入本文件；03 契约台账保留） | git 历史 |
| DSH_REINCARNATION.md 转生台账（154KB） | 2026-09-12 压缩为 DEVELOPMENT-HISTORY.md + 本文件 §2（决策台账 25 条全文迁入 §2.2） | git 历史 + 术前备份 |
| eval/ 消融产物（ablation-*.json/report） | 2026-09-12（结论固化于 §3.3） | git 历史 |
| loop2 设计文档（docs/loop2-design.md） | 2026-09-12（四层收敛环方法论要点并入 §9；scripts/loop2/ 代码保留） | git 历史 |
| var/univer-upstream（154MB）/ browser4-runtime（258MB）/ wheels_local（2.42GB） | 2026-09-12 物理删除 | 不可恢复（gitignore 区）；wheels 重下：pip download torch --index-url https://download.pytorch.org/whl/cu126 |

# 附录 B. 已知坑与历史事故全集

## B.1 检索与 LLM

1. 补充式回答不并入原问题 → 检索脱靶（expand_query_with_history 已修）。
2. fastembed 返回 numpy float32 → embedder 统一 float(x)。
3. FTS5 分词含 `.` `-` 会 syntax error → _fts_query() 引号包裹。
4. fastembed 首次联网下模型（~100MB）→ 缓存数据区。
5. 证据截断 800 字/条、历史 4×300 字；核验用全量文本。
6. rerank 例外条款保护（但书不可被挤掉，P1）。

## B.2 存储与并发

1. **multiprocessing.Queue 死锁**（最重要）：大结果集先 join 后取队列 = 死锁超时；parser_worker 已修——先 result_queue.get(timeout) 再 proc.join，别改回。
2. write_queue handler 必须提交事务（裸 db.execute 不 commit → database is locked）。
3. vec0 扩展按连接加载（新连接必须 load_vec_extension）。
4. begin transaction 嵌套 → write_transaction 开头自动 commit 兜底。
5. 测试共享会话级库 → 完整 ULID + 相对断言。
6. 清库禁用 DELETE FROM sqlite_master。

## B.3 运行契约（超时与冷启动——批 10 固化）

1. **ks_answer 工具超时 120s 下限**：引擎自带 DeepSeek 推理全流程实测可达 120s 量级；DSH 侧 timeoutMs=120_000 是**契约下限**，任何宿主/会话配置不得低于此值（低于=长推理被杀，表现为 HTTP 0 断连）。快查用 ks_resolve_clause（毫秒级）。
2. **fastembed 冷启动** ~2.6s（热缓存后常驻）；空闲回收后再来请求=冷启动+模型重载——idle 30min + 查法规 keepalive 的根因。
3. deep_server 解析 daemon 常驻只加载一次；一次只起一个 daemon。

## B.4 核验误报（用户实测暴露）

- "25.0%→4.0%" 判数值篡改 → 修复：核验用全量条款文本。
- 模态波动偶发（已知 2 例弱项，良性——宁误报不漏报）。
- 2026-09-06 两轮误报修复判据见 §5.3。

## B.5 入库与渲染坑（语料级，GB/T 34406/25596/24276 实测沉淀）

1. **PUA 错位字体文本层**：GBT 双层扫描 PDF 文本层是"形近 CJK 替代"hack（'GB/T'→'犌犅／犜'、数字整体平移 0x21-0x2A）→ normalize_pua_latin 映射归一化（犬部 52 字映射 + +15 还原数字 + NFKC），归一化后复验 mangled，干净则复用文本层（秒级入库）。
2. **附录内容缺失三层根因**：切分层（旧代码只出 normal 条款）+ API 层（三端点硬过滤 content_type）+ 重导通道（force_deep 参数 + spawn 子进程可能静默死亡 → 单文档重导用同步直调绕开）。语料级影响：历史入库文档附录均缺，重导即愈。
3. **条款编号重复显示**（正文开头编号与识别徽章重复）：仅当精确一致（词边界防 3.1 误匹 3.10）才包 display:none span，DOM 原样保留绝不硬删；判定正则字符间容排版空白（"附 录 A"→`附\s*录\s*A`）。
4. **水印/页码/点线清洗**：盗版站页眉 URL 独立文本块（行级清洗，行中 URL 不动防误伤 gb688.cn）；页码 NFKC 后 fullmatch + 页眉/页脚区双条件；公式引导点线 `\.{7,}`（NFKC 后 2 字省略号=6 点必须存活，阈值定稿 7）。
5. **根号套分式行序重排**：PDF 文本层把「√ 覆盖分式」压成"分子行→分母行→根号行"→ reflow_sqrt_formulas 重排为 'R=√(分子/分母)'；触发保守（√ 独立成行+前紧邻公式行+含 = 等式行）。
6. **表格斜铺水印碎片**：45° 斜铺水印与表格 bbox 重叠 → 字符级截断出碎片 → span 级过滤（line dir 偏离水平 `|dir[1]|>0.01` 是最强判据——中文国标正文绝无斜排）；fitz redact 不可用（按矩形删会整表删掉）。
7. **图形内嵌两阶段**：以题注为锚定位图区（图题"图"字收尾是最强形态锚）→ 流程图矢量重绘（**v2 内孔法**：空心闭合框在二值化+close 后必围白区，箭头不闭合无孔、散点图 U 形轴无孔——结构判别力极强；v1 外轮廓法全灭的教训：箭头连线把框连成一个连通体）→ RapidOCR → SVG；任一环不达标回退 PNG 截图。OCR 惰性单例首载 ~2s（main.py daemon 预热——曾因 import 笔误 `_get_ocr` 静默失效，2026-09-12 修复为 get_ocr）。
8. **PS 管道改写中文文件必坏编码**：Get-Content | Set-Content 一轮确定性损坏 → 文件内容读写一律 write/edit 工具或 Python open(encoding='utf-8')。
9. **附录子条款不切分（2026-09-13 修复，四路 verifier 评估定案）**：`_CLAUSE_GB` 只认 `\d` 开头（3654 条 normal 条款的口径，**永不修改**），附录内 `A.1/E.5.2` 字母章号全部落空 → 并入附录头单块（21 条 >800ch 附录大块全由此而来，2 条恰好 4000 字被 `[:4000]` 截断丢内容）。修复 = `_CLAUSE_APPENDIX`（字母+点分段，点后空白容忍）+ `_plausible_appendix_head` 字母版 E8 闸门（四护栏：`[A-Z]` 单字母+1..4 段数字 / rest 非空 / 排除 `表[E.4]给出了…` 图表题注与引用句 / `_TABULAR_REST` 数值行），主循环块级+行级双分支接入（多行块必须落行级循环——块级 `continue` 会吞块内后续 `B.2` 行）。配套五处：`_TABLE_CAPTION` 扩字母点号（`表A.1` 归一出 bind_no）；`build_hierarchy_path` 支持字母首段（`A.5.2 → 'A > A.5'`）；`_expand_title_clauses` 门控（两处，server.py+ks_answer.py）接纳字母号；检索 exact 通道 `_CLAUSE_NO_APPENDIX_RE`（`E.5.2` 先被 `_CLAUSE_NO_RE` 截成 `5.2` 返回**错标准**条款——比查不到更危险；边界用 `(?<![A-Za-z0-9])` 显式断言，Python `\b` 不认中文，`表E.4` 的 E 与中文之间无 `\b`）。重导 10 文档试点断言全绿：数字条款口径零变化、附录大块 1294→清零（子条款吸走）、最长 761 字。红队 D 铁律：图/表题注**不是**切分锚（47 个行首图表候选仅 ~1 真题注，`表E.4给出了…` 引用句会拦腰截断真条款）。

## B.6 运维与进程

1. （历史）vite 绑 [::1]：Windows 默认 → dev 必须 --host 127.0.0.1（vite 已退役，坑留档）。
2. 全局 taskkill /IM python.exe 误杀 mineru 子进程 → psutil 按 cmdline 精确匹配。
3. setx 不注入已存在进程环境 → config.py 回退链。
4. Windows 测试临时目录清理 PermissionError → conftest ignore_cleanup_errors。
5. **git 仓库**（2026-09-12 起）：tracked 文件删除可从 git 恢复；var/ 等 gitignore 区删除即真删。
6. PowerShell 管道读写中文必坏编码（UTF-16LE/GBK 陷阱）——规则见 B.5-8。
7. **宿主停摆事故 3.5 小时**（2026-09-11）：看门狗裸拉起 12 次全部数秒退出——"已经有自动恢复"是自我感觉；修复路径见批 3。
8. **引擎在跑批量任务时不要杀引擎**。

---

*本文件 2026-09-12 推倒重构（5-verifier 文档审计 + 交叉核实）：修正 12 处死链（docs/_deprecated 谎言、contract.md、coverage-matrix、5173 测试页、33 表、81→80 测试文件数）、统一 API Key 语义四处为 §15.1 单一权威、删除 §9 旧前端 9.1-9.7 历史章节（改附录 A）、合并 §14 阶段史与 §18.3 台账（归 DEVELOPMENT-HISTORY.md）、并入 DSH_REINCARNATION 25 条决策台账、消融结论、渠道实证、loop2 方法论要点。旧版全文见 git 历史（提交 72ed44f 之前）。*

