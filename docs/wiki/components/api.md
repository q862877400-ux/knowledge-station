# api（HTTP 端点）

**位置**：`src/core/api/`
**一句话**：引擎对外的唯一入口——所有能力都从这里以 HTTP 端点暴露。

## 职责

**把引擎的能力变成可被调用的 HTTP 端点**，并对调用方守住契约（鉴权、请求校验、响应结构）。
插件、外部系统、`ks_*` 工具最终都打到这里。

**它不负责**：业务逻辑（在各子系统里）、界面（在 `plugin/`）、检索算法（在 `retrieval`）。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 应用装配 | `server.py`（`create_app`） | 引擎启动 |
| 知识库目录端点 | `routes_kb_folders.py` | 插件侧栏 |
| 渠道台账端点 | `routes_channels.py` | 巡检界面 |
| 材料平面端点 | `routes_materials.py` | 材料界面 |
| 更新/巡检端点 | `routes_update.py` | 巡检界面 |
| 入库预览端点（**只读**） | `routes_ingest_preview.py` | 入库界面 |
| 交付物端点 | `routes_report.py` | 交付界面 |
| 法规来源端点 | `routes_law.py` | 法规抓取 |
| 设置端点 | `routes_settings.py` | 设置界面 |

**规模**：`server.py` **187.7 KB**（最大单文件），其余 9 个路由文件 3.7–37.2 KB。
**端点总数**：几十个（实测 `/api/v1/...` 前缀）。

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| `storage` | 上游模块 | 所有数据读写 |
| `retrieval` | 上游模块 | 问答端点的候选 |
| `compliance` / `llm` / `ingestion` / `update` / `materials` | 上游模块 | 各自领域的端点 |
| 鉴权（Bearer token） | 机制 | 引擎侧校验 |

## 明确不做什么

- **不做业务规则**：端点是"搬运工"，判断在子系统里。**MUST NOT 在路由里写业务判定**
  （已有先例：路由从 `server.py` 的闭包里抽出来，正是为了让职责清楚）。
- **不做界面**：返回数据，不管怎么显示。界面在 `plugin/client/`。
- **不做鉴权策略的决定**：只执行；策略在引擎配置。
- **不做检索**：调用 `retrieval`，不自己实现。

## 关键数据

不直接持有数据；经 `storage` 的仓储访问（`clause_repo` / `channel_repo` / `material_repo` / `user_data`）。

## 改了它会影响谁

- **`plugin/` 全部界面**：界面全靠这些端点
- **`ks_*` 模型工具**（`ks_ping` / `ks_resolve_clause` / `ks_answer` / `ks_materials` / `ks_effect_report`）
- **外部调用方**（若有）

## 已知边界（诚实）

- ⚠ **`server.py` 187.7 KB 是单文件**，是本仓最大的单文件。
  路由已抽出 9 个，但主体仍大。**是否继续拆是未决问题**（登记，不擅自动）。
- **改 schema/API/SSE 前** MUST 先读 `docs/ENCYCLOPEDIA.md` §8/§10 与 `pipeline/03-contract-delta.md`
  （契约增量台账，每次 schema 变更记 DDL/影响面/回滚 SQL）。
