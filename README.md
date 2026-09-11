# KnowledgeStation — 通用国标与法律法规本地 AI 知识工作站

把国标/法规 PDF 变成**可检索、可溯源、可纠错、可落检查表**的本地知识库（Windows 11）：
回答每条结论带标准号-条款号引用，点引用即可跳到 PDF 原文对应位置黄框高亮核对；LLM 只接收
问题 + 本地证据片段，外发内容全程留痕可审计。框架按 v5 优先级重排，**phase 1~14 全部完成**。

## 📖 文档入口（唯一现行文档）

> **`docs/ENCYCLOPEDIA.md` —— 项目百科全书（18 章单入口）**：概览 / 技术栈 / 架构 / 数据模型 /
> 检索链路 / LLM 与追问 / 核验 / 入库与 bbox 契约 / 前端 / 合规引擎 / API 与 SSE / 运维 / 测试 /
> 阶段史 / 已知坑 / 规则红线 / 未实现清单 / 文档索引。接手、开发、排障一律从这里开始。

- 旧文档（框架 v5 / 路线图 / 契约 / 维护手册 / 阶段交接 / 测试套件等 30 份）已融合进百科全书，
  原件归档于 **`docs/_deprecated/`（⚠️ 已废弃，请勿使用，仅历史溯源）**。
- 需求 SSOT 仍为主计划 v4.3（`1-v4.3 (1).md`，仓库根工作副本；需求编号 R1~R79 + R-L1~L14 + T00~T13）。

## 接手必读（按顺序）

1. `docs/ENCYCLOPEDIA.md` —— **百科全书（先读，建立全局认知）**
2. `docs/ENCYCLOPEDIA.md §18` —— 文档索引与接手指南（含各主题跳转）
3. 需要历史细节时 → `docs/_deprecated/onboarding/`（仅溯源，以百科全书为准）

## 当前状态

- **阶段**：phase 1~14 全部完成（v5 路线图 25 Task 闭环）；「更新」模块与万级批量导入已交付（pipeline/ 目录全流程文档）。
- **测试**：pytest **404 passed + 3 skipped**；`npx tsc --noEmit` 0 错误；Golden Set 门禁全绿。
- **服务**：引擎（随机端口 + 一次性 token，session 文件）+ 前端 http://127.0.0.1:5173/ 常驻。

## 目录结构（核心）

```
docs/ENCYCLOPEDIA.md        # 项目百科全书（唯一现行文档）
docs/_deprecated/           # 旧文档归档（已废弃，仅溯源）
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
scripts/                    # dev_launcher（一键启动）/ restart_dev / verify_highlight / verify_linkify
tests/                      # 33 个测试文件（基线 165 passed + 2 skipped）
src/renderer/               # React 双栏 UI：左问答右原文（App.tsx / PdfViewer / TipTap / tableText）
```

## 快速开始

```bash
# 一键启动（推荐）：拉起引擎 → 读 session → 拉起 vite → 打开浏览器
.venv/Scripts/python scripts/dev_launcher.py

# 或手动两步
.venv/Scripts/python -m src.core.main          # 引擎：stdout + %APPDATA%/KnowledgeStation/engine.session.json
VITE_ENGINE_PORT=<port> VITE_ENGINE_TOKEN=<token> npm run dev:vite -- --host 127.0.0.1   # 前端（必须 --host 127.0.0.1）

# 测试与类型检查
.venv/Scripts/python -m pytest -q              # 基线 398 passed + 3 skipped
npx tsc --noEmit -p tsconfig.json

# 入库（详见 ENCYCLOPEDIA §8）
.venv/Scripts/python -m src.core.ingestion.smoke_ingest <pdf> --standard-no "GB 30871-2022" --name "化学品生产单位特殊作业安全规范"
```

> 前端自动发现引擎的顺序：Electron preload → localStorage(`engine.port`/`engine.token`) → vite env。
> 重启引擎后端口/令牌会变：重启 vite 注入新 env，或浏览器刷新后由探测链接管（详见 ENCYCLOPEDIA §12.2）。

## 已实现能力（概览）

- **可信问答**：六通道混合检索（精确/FTS+jieba/向量/模态/法要素/行为域）+ RRF + rerank + 证据链 + LLM 仅依据证据作答 + 数值/模态/法理核验分级。
- **溯源核对**：回答引用可点击 → PDF 跳页 + 黄框高亮（bbox 底部原点契约）；证据卡片含置信度徽章/修订记录/收藏批注。
- **纠错闭环**：快速修改（TipTap 文字/表格）+ 完整编辑（Word/WPS 往返）双轨 → 补丁落库（快照不可变）→ 修订记录可撤销。
- **数据体检**：自动扫描 OCR/切分质量问题（5 类），集中纠错。
- **追问机制 v2**：LLM 单次自判"问还是答"，最多 3 问一次问完，常识/默认场景直接作答。
- **合规落地**：义务清单/检查表、合同审查、制度差距分析、条款释义、批量问答、双向溯源。
- **入库便利**：PDF（识别版/扫描版）/ Word(docx) / 监听文件夹（已闭环：入队→消费→入库）/ 自动标签 / Dry-Run 预览 / 入库 span 坐标体检（异常当日告警）。
- **数据可信**：快照不可变 + 补丁平移 + SHA-256 校验 + 定时滚动备份/回滚。
- **外发可审计**：每次云调用 payload 落库（debug_dump），UI 可查可导出（D2 红线）。
- **版本与运维**：版本链/跨版本对照、时效提醒、审计日志、Debug Trace、健康看板、一键启动。

## 安全约束

- DeepSeek API Key 仅存于用户环境变量 `KS_LLM_API_KEY`（Windows 用户变量，支持注册表回退；
  旧名 `DEEPSEEK_API_KEY` 自 2026-09-11 起仅作**只读回退**），代码库无明文密钥。
  改名原因：写裸全局名会遮蔽 DSH 等同类工具的凭据层（继承环境变量优先级最高且只读），
  详见 `src/core/settings/api_credentials.py` 模块说明。
- **清理旧全局名后必须重启 DSH 宿主进程**：DSH 在启动时冻结环境快照，删掉
  `DEEPSEEK_API_KEY` 后只有重启宿主（桌面「DSH复活币X1」）才会重新读环境、其模型设置页的
  密钥输入框才恢复可写；引擎侧不需要重启。工具与顺序见 `scripts/ks-credentials-migrate.py`。
- 外发可审计：发往 LLM 的 Prompt 仅含问题与最小必要证据片段，且完整 payload 落库可追责。
- 引擎绑定 127.0.0.1 随机端口 + 一次性 token 鉴权（/health 除外）。

## 未实现 / 待办

见 `docs/ENCYCLOPEDIA.md §17`（未实现 / 挂起 / 条件触发清单）与 §13.5（测试盲区）。
