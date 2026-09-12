# KnowledgeStation —— 法规标准智能工作站

> 让每一句合规结论，都有法可依。国标/法规 PDF → 本地知识库 → AI 答案带可点击证据链（点引用跳 PDF 原文高亮）。
> 产品介绍：`docs/INTRODUCTION.md` ｜ 技术百科（架构/契约/坑）：`docs/ENCYCLOPEDIA.md`

## 快速开始

```text
1. 启动 DSH 宿主（平时入口）→ 插件自动注册（侧栏「法规标准知识库」+ 4 个模型工具）
2. 会话里直接问："/forensic 动火作业怎么分级" → 三段式取证答案
3. 点答案里的引用蓝链 → 侧栏 PDF 证据 tab 跳页 + 红色定位箭头高亮原文
4. 引擎按需懒拉（随机端口 + 一次性 token，无需手动启动）
```

## 形态（2026-09-12 批 8 定稿）

**引擎 + DSH 插件一体，无独立 EXE**。Python FastAPI 引擎（`src/core/`，入口 `python -m src.core.main`）+ Node DSH 插件（`plugin/`）。旧 Electron/Vite/双栏 SPA 已整体退役（git `0dcb67f`）。

## 四道门禁（改代码后必跑）

```text
.venv/Scripts/python -m pytest tests -q     # pytest：828 passed + 3 skipped（只涨不跌）
cd plugin && npm run smoke                  # 插件冒烟：10 段
cd plugin && npm run verify:commands         # 命令回归：15/15
npm run typecheck                           # tsc --noEmit -p plugin/client：0 错误
```

## 目录结构

```text
src/core/       # 引擎本体（api/storage/retrieval/ingestion/compliance/llm/update/…）
plugin/         # DSH 插件：宿主桥(src/index.js) + 侧栏 client(React) + 4 个模型工具
scripts/        # 运维脚本（凭据迁移/交接打包/巡检/法规抓取/loop2 收敛环）
tests/          # 80 个测试文件（契约/检索/入库/API/合规/凭据/门禁）
eval/           # Golden Set 门禁三件最小集（golden/ + run_benchmark.py + baseline.json）⚠ 勿删
docs/           # ENCYCLOPEDIA(技术百科) / INTRODUCTION(产品) / REQUIREMENTS-v4.3(需求SSOT)
                # / DEVELOPMENT-HISTORY(开发简史) / LAW_SOURCE_PLAN + STD_STATUS_CHANNELS(工程参考)
                # / CHANNEL_PROBE_REPORT(渠道实证) / pipeline/03-contract-delta.md(契约增量台账)
wenjianmulu/    # ⚠ 生产库 doc_meta.file_path 指向这里的 PDF（活数据，勿删）
var/            # gitignore 工作区（engine.log / mineru_cli_out 测试依赖 / fixtures 活数据）
```

## 文档地图（接手必读）

1. **`docs/ENCYCLOPEDIA.md`**——技术百科全书（架构/数据契约/检索/入库/坑全集/红线宪法），先读。
2. `docs/INTRODUCTION.md`——产品介绍（是什么/为什么可信/能力清单）。
3. `docs/REQUIREMENTS-v4.3.md`——需求 SSOT（R1~R79 + R-L1~L14 + T00~T13；抬头注记列明已被后续裁决覆盖的条目）。
4. `docs/DEVELOPMENT-HISTORY.md`——开发历程简史（2026-08 引擎从零 → 2026-09 DSH 转生 → 批 0~10 → 冗余清剿）。
5. 改 schema/API/SSE 前 → ENCYCLOPEDIA §8/§10 + `pipeline/03-contract-delta.md`。
6. 改插件 client 前 → `plugin/client/bsContract.ts` + `plugin/client/dsh-better-sidebar.d.ts`（smoke-bs-contract 对真包校验）。

## 安全约束

- API Key 只存引擎加密存储 `<data_dir>/secrets.json`（DPAPI）；环境变量只读覆盖；引擎绝不写注册表（凭据链权威表述见 ENCYCLOPEDIA §15）。
- 每次云调用完整 payload 落库可审计（外发审计面板可查可导出）；OCR 出网带 went_on_the_wire 标记。
- 数据/代码分离：运行产物全在 `%APPDATA%\KnowledgeStation\`（`KS_DATA_DIR` 可重定向）。

## 已知红线（改代码前必读，全表见 ENCYCLOPEDIA §16）

- SSE 事件顺序冻结不得增删 reorder；bbox 底部原点契约不要碰。
- SYSTEM_PROMPT 规则 1~9 只能增强不能回退；写操作必须走单写者队列。
- Golden Set 门禁（eval/ 三件套）任何指标回退 >2pp 即失败。
- 生产库 doc_meta.file_path 指向的文件禁止删除/移动。

## 历史

2026-08 从零建成引擎（phase 1~14）→ 2026-09-05 DSH 秽土转生（旧前端退役）→ 2026-09-12 批 0~10 整改 + Electron 退役 + 冗余清剿收官。详见 `docs/DEVELOPMENT-HISTORY.md`；原始记录在 git 历史（`git log`）。
