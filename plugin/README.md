# ks-dsh-plugin（KnowledgeStation × DSH 桥 + 侧栏工作台）

把「法规国标强关联 RAG」Python 引擎（KnowledgeStation）桥接进 DeepSeek Harness：
插件在首次调用时**懒启动**本地引擎（随机端口 + 一次性 token），提供 **4 个模型工具** +
**5 个侧栏 tab/视图** + **设置栏目** + **同源代理路由**。引擎侧取证问答的答案**只引现行版**、
依据全部带链、点链即到原 PDF 红箭头高亮。

- 插件名：`ks-dsh-plugin`（P0/P1a/P1b/P1c/P2 各阶段已全部闭环）
- 引擎仓库根：`D:\AI\work space\zcode`（只读，不改引擎代码/数据）
- 引擎入口：`.venv\Scripts\python.exe -m src.core.main`（cwd=仓库根）
- 会话文件：`%APPDATA%\KnowledgeStation\engine.session.json` = `{port, token, pid, started_at}`
- 鉴权：除 `GET /api/v1/health` 外所有 `/api/v1/*` 需要 `Authorization: Bearer <token>`

## 模型工具（4 个）

| 工具 | 职责 | 超时 |
|---|---|---|
| `ks_ping` | 引擎健康探测（status/uptime/db_status/vector_engine/parser_worker） | 毫秒级 |
| `ks_resolve_clause` | 条款快查（standard_no + clause_number → 机器证据 + PDF 锚链接） | 毫秒级 |
| `ks_answer` | **取证答案**：引擎侧检索 + DeepSeek 推理 + typed_verifier 核验 → 裁剪三段式（依据区 → 推导区 → 结论区） | **120s 契约下限**（引擎自带推理实测可达 120s 量级；低于此值长推理被杀） |
| `ks_effect_report` | 效力报告（库内标准/法规现行快照总览，host 侧裁剪——只回统计+红黄清单 top-N，绝不回传全量分类树） | 秒级 |

成本纪律：能 `ks_resolve_clause` 快查的不调 `ks_answer`。

## 侧栏 UI（官方 right sidebar + settings.section + 输入框 dock）

2026-09-16 迁移后**只注册三个座位**（均在 `client/entry.ts` 可见）：

| 座位 | 内容 |
|---|---|
| `sidebar.right.pane.tab`（📖 证据 PDF） | 单 tab 承载多个视图：pdfjs 单页渲染 + 跳页 + 红色定位箭头（bbox 底部原点契约）· 标题目录（纯悬浮 overlay）· 文件目录（4 级分类树/搜索/多选批删）· ⭐收藏视图（`KsBookmarksView`，条款收藏列表 + 逐条删除 + 点击跳证据 PDF）· 📄正文/📑PDF 视图切换 · 最近证据互跳 |
| `settings.section`「法规标准知识库」 | 顶层 nav，**六个类目全折叠**（2026-11）：证据查看器（红箭头开关）· 效力报告（四色分组 🟢🔴🟡⚪ + 时间窗 + 导出，内嵌面板）· 入库预览（Dry-Run + 异步批量 jobs ✅/⚠️/❌，内嵌面板）· 每日巡检 · 公告发现 · API 配置（LLM/云 OCR Key，引擎侧 DPAPI 加密存储）。收起零请求，展开才拉数据 |
| `conversation.input.dock` | `KsScopeChip`——查法规模式作用域提示条 |

> 注：收藏/文件目录**不再是独立 tab**，而是证据 tab 内的视图（`KsBookmarksView` / `KsFilesTab` 被 `KsEvidenceTab` 引用）。

斜杠命令（会话输入框）：`/forensic` 查法规模式（强制三段式）+ `/bookmarks` 仅收藏。

## 目录

```
plugin/
  package.json        # npm 清单（dsh.client 声明 + 14 个脚本）
  cordis.patch.yml    # bundle patch：insert 一行 ks-engine -> ks-dsh-plugin
  src/index.js        # 宿主桥：4 工具注册 + /ks/* 同源代理路由 + 引擎守护(ensureLive) + 异步 jobs 路由
  src/engine.js       # EngineManager：单实例判定 + 懒 spawn + 健康轮询 + idle 30min 优雅关停
  client/entry.ts     # tab 注册（证据 PDF + 收藏）+ settings.section（含内嵌效力报告/入库预览）+ 证据锚点接管
  client/KsEvidenceTab.tsx / KsBookmarksTab.tsx / KsFilesTab.tsx / KsReportPanel.tsx / KsIngestPanel.tsx / KsSettingsSection.tsx / ApiConfigPanel.tsx
  client/api.ts       # 引擎 fetch 链（经宿主代理）
  client/ksSidebar.ts # 官方右侧栏契约（tabs/slots 两段式注册 + 证据 tab 定义，2026-09-16 迁移）
  client/KsEvidenceHost.tsx # 官方注入（useTabInfo/openEvidence）→ KsEvidenceProps 映射
  client/ksPrefs.ts   # 侧栏偏好存储（localStorage，取代旧第三方 store）
  client.js           # esbuild 单文件产物（~1.1MB，DSH ModuleLoader 加载；git 跟踪）
  scripts/build-client.mjs  # 构建（改 client 后必跑）
  scripts/smoke.mjs         # 独立 host 侧冒烟（真拉引擎打 /health + /documents）
  scripts/smoke-*.mjs       # smoke 11 段（pdf-fit/pdf-panel/settings/settings-guard/effect-tool/chatmode/ingest/engine-guard/client-entry/docimage/sanitize）
  scripts/verify-commands-real.mjs  # 命令回归 15 项
```

> 注（2026-09-16）：`dsh.client.inject` 现列 `@deepseek-ai/dsh-client-ui-sidebar-right`
> 等官方包，运行时由宿主提供。旧的第三方 `dsh-better-sidebar` 已下线，
> `bsContract.ts` / `dsh-better-sidebar.d.ts` / `smoke-bs-contract.mjs` 三件同批删除。

## 安装（实测坑：路径含空格）

`dsh plugin add` 按空格拆参数——仓库路径 `D:\AI\work space\zcode\plugin` 含空格，加引号也会被拆。
**必须用无空格路径**。本机做法（junction staging，改仓库代码即生效）：

```powershell
cmd /c mklink /J "C:\Users\Zegel\dsh-ks-src\ks-dsh-plugin" "D:\AI\work space\zcode\plugin"
dsh plugin --profile web add "C:\Users\Zegel\dsh-ks-src\ks-dsh-plugin"
```

重启 `dsh web`（host 行不热更）装载。client 半改动只需 `npm run build:client` + 浏览器硬刷新（不需 dsh 重启）；src 半改动需 dsh 宿主重启。
回滚：`dsh plugin --profile web remove ks-dsh-plugin`。

## 常用命令

```text
cd plugin
npm run build:client      # esbuild 构建 client.js（改 client/ 后必跑）
npm run smoke             # 10 段冒烟（含 engine-guard 离线逻辑 + bs-contract 对真包校验）
npm run verify:commands   # 15 项命令回归
（根目录）npm run typecheck  # tsc --noEmit -p plugin/client（类型门禁）
```

## 关键运行契约

- **引擎守护**：ensureLive 懒拉起（复用存活实例）+ stale 会话改名留档 + 看门狗；idle 30 分钟优雅关停（`idleTimeoutMs` 可配）；查法规模式 keepalive；并发 ensureLive 合并（防幽灵引擎）。
- **同源代理**（信任栅栏覆盖全部 18 条 `/ks` 路由，verifier 审计过）：`/ks/session`（每次载入重取，引擎轮换对 tab 透明）、`/ks/pdf`、`/ks/bbox`（底部原点原样透传零转换）、`/ks/assets/*`。token 不进页面不跨源。
- **host 状态镜像**：`ks-{inspection,announce,chatmode,ingest}.json`——浏览器关掉后 host 权威推进任务；引擎不可达时镜像兜底并**如实标注 stale**，不假装在跑。
- **每日巡检**：插件内置定时器 → 每日固定时刻 spawn 引擎 headless 巡检（扫公告→更新→写效力报告→退出，零常驻）；当天 dsh 没开则错过顺延、下次启动补跑。
- **超时预算自洽 80s deadline**（批 8 审计）：请求链路各段超时总和 ≤ 上层预算，杜绝"下级比上级活得久"。
- **dsh lossless 校验**：host 侧返回 `data ?? null` 规避（曾因 undefined 字段挂 DSH 校验）。

## 安装与验证状态

- ✅ 已安装（staging junction 路径）并真实 host 加载；引擎懒加载符合预期；4 工具 + 3 座位（1 侧栏 tab / settings.section / input.dock）**迁移前**真机全通。
- ✅ 真机已验证（迁移前的旧桥接）：蓝链点击 → PDF 跳页红箭头高亮（用户实测）、收藏互跳、效力报告（设置栏目内嵌面板）、入库预览 egress:"none" 确证、斜杠命令。
- ⚠ **2026-09-16 官方侧栏迁移后尚未做真机复核**——运行中的 host 由 tsx 从更新前源码启动，需重启 `dsh web` 才装载新注册路径；重启前看不到 tab 不代表代码错。见 `docs/DEVELOPMENT-HISTORY.md` §八.4。
- ✅ 离线门禁基线：pytest 1208+3（0 failed / 0 xfailed）/ smoke 11 段 / verify:commands 15 项 / tsc 0 错 / mypy 0 错。

---

## 附：历史验证记录（保留原文件 2026-09-05~09-08 的关键结论）

- **install 坑**（09-05）：`dsh plugin add` 空格拆参——见上文安装节。
- **既有环境坏点**（09-05 发现）：`dsh-plugin-llm-verifier` 零依赖声明却 import `@deepseek-ai/*`，任何新 boot 都挂；已用 junction 补进其 node_modules（重装会丢需重补）。同 profile 双实例被 `web-ui-task-board` 进程独占 ledger 挡住。
- **单例 tab path 陷阱**（09-05）：better-sidebar `openTab` 对 single tab 只 FOCUS 不更新 path——修复：document 级 capture click 接管 + `updateTab` 强制覆写 + `meta:{ksClick:++n}` 单调 nonce 触发重载。
- **convertToViewportPoint**（09-05 根因修复，verifier 三路定案）：箭头曾永不显示 = pdfjs 无 `convertToViewPoint` 方法（真实名 convertToViewportPoint）；esbuild 不查类型故构建期拦不住——**client 改动必须过 tsc 门禁**（批 8 起 typecheck 已含 plugin/client）。
- **hidden tab ≠ 设置栏目**（09-06）：better-sidebar 的 hidden tab 契约上无法成为设置栏目，正解是 `settings.section` 顶层 nav。
- **深度解析通道语义**（09-08 业主裁决）：已配置云 Key → 云优先、本地兜底；未配置 → 直接本地通道。
- **批 3 改动需重启宿主才 live**：keepalive / idle 30min / 异步 jobs 路由等 src 侧改动在 dsh 重启后生效。
