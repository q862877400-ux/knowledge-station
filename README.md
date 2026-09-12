# KnowledgeStation — 通用国标与法律法规本地 AI 知识工作站

把国标/法规 PDF 变成**可检索、可溯源、可纠错、可落检查表**的本地知识库（Windows 11）：
回答每条结论带标准号-条款号引用，点引用即可跳到 PDF 原文对应位置核对；LLM 只接收
问题 + 本地证据片段，外发内容全程留痕可审计。框架按 v5 优先级重排，**phase 1~14 全部完成**。

> **桌面形态（批 8 起定稿）**：本项目**不再单独打包 EXE**——引擎 + DSH 插件（`plugin/`）一体，
> GUI 一律经 **DSH Web 宿主侧栏**呈现；桌面化由 DSH 整体打包承担。旧 Electron/Vite 独立
> 前端已于批 8（2026-09-12）整体退役删除。

## 📖 文档入口（唯一现行文档）

> **`docs/ENCYCLOPEDIA.md` —— 项目百科全书（18 章单入口）**：概览 / 技术栈 / 架构 / 数据模型 /
> 检索链路 / LLM 与追问 / 核验 / 入库与 bbox 契约 / 前端 / 合规引擎 / API 与 SSE / 运维 / 测试 /
> 阶段史 / 已知坑 / 规则红线 / 未实现清单 / 文档索引。接手、开发、排障一律从这里开始。

- 旧文档（框架 v5 / 路线图 / 契约 / 维护手册 / 阶段交接 / 测试套件等 30 份）已融合进百科全书，
  原件归档于 **`docs/_deprecated/`（⚠️ 已废弃，请勿使用，仅历史溯源）**。
- 需求 SSOT 仍为主计划 v4.3（`1-v4.3 (1).md`，仓库根工作副本；需求编号 R1~R79 + R-L1~L14 + T00~T13）。

## 接手必读（按顺序）

1. `docs/ENCYCLOPEDIA.md` —— **百科全书（先读，建立全局认知）**
2. `DSH_REINCARNATION.md` —— 秽土转生改造台账（整改批 0~8 + 业主裁决原话）
3. `docs/ENCYCLOPEDIA.md §18` —— 文档索引与接手指南（含各主题跳转）
4. 需要历史细节时 → `docs/_deprecated/onboarding/`（仅溯源，以百科全书为准）

## 当前状态

- **阶段**：phase 1~14 全部完成（v5 路线图 25 Task 闭环）；「更新」模块与万级批量导入已交付
  （pipeline/ 目录全流程文档）；**批 8（Electron 退役）后为引擎 + DSH 插件一体形态**。
- **测试**（2026-09-12 批 8 门禁实测，只涨不跌基线）：pytest **830 passed + 3 skipped**；
  插件 smoke **10 段全绿**；`npm run verify:commands` **15/15**；**新增 tsc 门禁**
  `npm run typecheck`（= `tsc --noEmit -p plugin/client`）**0 错误**。
- **服务**：引擎（随机端口 + 一次性 token，session 文件）由 DSH 插件按需拉起；GUI 为 DSH Web
  宿主侧栏 tab（`plugin/client`），不再有独立前端进程。

## 目录结构（核心）

```
docs/ENCYCLOPEDIA.md        # 项目百科全书（唯一现行文档）
docs/_deprecated/           # 旧文档归档（已废弃，仅溯源）
DSH_REINCARNATION.md        # 秽土转生整改台账（批 0~8）
plugin/                     # DSH 插件（批 8 起唯一 GUI/工具面）
  src/index.js              # 宿主桥：懒拉引擎 + ks_* 模型工具 + /ks/* 代理路由
  client/                   # 侧栏 tab（证据 PDF 查看器 / 报告 / 收藏 / 入库 / 设置）
  client.js                 # esbuild 产物（~1.1MB 单文件，DSH ModuleLoader 加载）
  scripts/                  # build:client + smoke 10 段 + verify:commands
src/core/
  main.py                   # 引擎入口：python -m src.core.main
  api/server.py             # FastAPI：全部 API + SSE；随机端口 + token + engine.session.json
  config.py                 # 配置中心（%APPDATA%/KnowledgeStation，可用 KS_DATA_DIR 重定向）
  domain/models.py          # Pydantic 域模型（冻结契约）
  storage/                  # sqlite_db / clause_repo（补丁机制）/ user_data / versioning / backup
  retrieval/                # hybrid_engine（六通道+RRF+rerank）/ embedder / reranker
  query/understanding.py    # 主题/意图/槽位；追问策略（v2：LLM 自判问还是答）
  llm/                      # deepseek_client / egress_audit / fewshot
  verification/typed_verifier.py  # 数值/模态/法理核验 → 答案置信度
  ingestion/                # pipeline / mineru_adapter / docx / watcher / auto_tag / vision
  compliance/               # 义务清单 / 合同审查 / 差距分析 / 释义 / 批量问答
  exports/                  # report_export / office_roundtrip / backlinks
scripts/                    # 凭据迁移/对账、入库回填、handoff 打包、DSH 宿主守护脚本
tests/                      # 测试文件（2026-09-12 批 8 门禁 830 passed + 3 skipped）
```

## 快速开始

```bash
# 0) 安装依赖（根：tsc 门禁/类型工具链；插件：esbuild + smoke）
npm install
cd plugin && npm install && cd ..

# 1) 启动 DSH Web 宿主（业主操作：桌面「DSH复活币X1」），
#    插件自动注册：ks_ping/ks_resolve_clause/ks_answer 工具 + 侧栏四个 tab
#    + 「法规标准知识库」设置区；引擎由插件按需懒拉（无需手动启动）。

# 2) 引擎单独调试时
.venv/Scripts/python -m src.core.main   # stdout + %APPDATA%/KnowledgeStation/engine.session.json

# 3) 测试与门禁（批 8 四道门禁）
.venv/Scripts/python -m pytest tests -q         # 830 passed + 3 skipped
cd plugin && npm run smoke                      # 10 段全 PASS
cd plugin && npm run verify:commands            # 15/15
npm run typecheck                               # plugin/client 0 错误

# 4) 重建插件前端产物（改 client 后必跑）
cd plugin && npm run build:client               # -> client.js (~1.1MB)

# 5) 入库（详见 ENCYCLOPEDIA §8）
.venv/Scripts/python -m src.core.ingestion.smoke_ingest <pdf> --standard-no "GB 30871-2022" --name "化学品生产单位特殊作业安全规范"
```

> 引擎端口/令牌每次启动轮换，DSH 侧栏自动经 `/ks/session` 取新值；证据 PDF 在 DSH Web GUI
> 内经宿主同源代理（`/ks/assets/*`、`/ks/pdf`、`/ks/bbox`）加载，无跨源凭据泄漏
> （详见 ENCYCLOPEDIA §12）。

## 已实现能力（概览）

- **可信问答**：六通道混合检索（精确/FTS+jieba/向量/模态/法要素/行为域）+ RRF + rerank + 证据链 + LLM 仅依据证据作答 + 数值/模态/法理核验分级。
- **溯源核对**：回答引用可点击 → DSH 侧栏证据 tab 跳页 + 红色定位箭头（bbox 底部原点契约）；
  证据卡片含置信度徽章/修订记录/收藏批注（`docs/onboarding/evidence-card-contract.md`）。
- **纠错闭环**：快速修改（补丁文字/表格）+ 完整编辑（Word/WPS 往返）双轨 → 补丁落库（快照不可变）→ 修订记录可撤销。
- **数据体检**：自动扫描 OCR/切分质量问题（5 类），集中纠错。
- **追问机制 v2**：LLM 单次自判"问还是答"，最多 3 问一次问完，常识/默认场景直接作答。
- **合规落地**：义务清单/检查表、合同审查、制度差距分析、条款释义、批量问答、双向溯源。
- **入库便利**：PDF（识别版/扫描版）/ Word(docx) / 监听文件夹（已闭环：入队→消费→入库）/ 自动标签 / Dry-Run 预览 / 入库 span 坐标体检（异常当日告警）。
- **数据可信**：快照不可变 + 补丁平移 + SHA-256 校验 + 定时滚动备份/回滚。
- **外发可审计**：每次云调用 payload 落库（debug_dump），UI 可查可导出（D2 红线）。
- **版本与运维**：版本链/跨版本对照、时效提醒、审计日志、Debug Trace、健康看板、DSH 宿主一键拉起。

## 安全约束

- API Key 只存于**引擎加密存储** `<data_dir>/secrets.json`（Windows DPAPI 加密，权威存储；
  环境变量/注册表仅作**只读覆盖**，引擎**绝不写**注册表——2026-09-11/12 迁移整改后定稿）。
  旧全局名 `DEEPSEEK_API_KEY`/`KS_MINERU_CLOUD_API_KEY`/`SCNET_OCR_API_KEY` 已全部搬入加密存储
  并从注册表删除（搬迁与核对工具：`scripts/ks-credentials-migrate.py` / `scripts/ks-credential-reconcile.py`）。
  改名原因：写裸全局名会遮蔽 DSH 等同类工具的凭据层（继承环境变量优先级最高且只读），
  详见 `src/core/settings/api_credentials.py` 模块说明。
- **清理旧全局名后必须重启 DSH 宿主进程**：DSH 在启动时冻结环境快照，删掉
  `DEEPSEEK_API_KEY` 后只有重启宿主（桌面「DSH复活币X1」）才会重新读环境、其模型设置页的
  密钥输入框才恢复可写；引擎侧不需要重启。工具与顺序见 `scripts/ks-credentials-migrate.py`。
- 外发可审计：发往 LLM 的 Prompt 仅含问题与最小必要证据片段，且完整 payload 落库可追责。
- 引擎绑定 127.0.0.1 随机端口 + 一次性 token 鉴权（/health 除外）；DSH 侧栏经宿主同源代理访问，token 不进页面。

## 未实现 / 待办

见 `docs/ENCYCLOPEDIA.md §17`（未实现 / 挂起 / 条件触发清单）与 §13.5（测试盲区）。
