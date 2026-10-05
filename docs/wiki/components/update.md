# update（渠道巡检与变更）

**位置**：`src/core/update/`
**一句话**：盯着 131 条官方渠道，把「这个渠道今天还活着吗」「有什么变了」变成可实测、可落库的事实。

## 职责

**覆盖率的执行层**。这是产品三件护城河之一（可核验的覆盖率）的实现：渠道健康探针（`channel_probe.py`）、公告发现（`announce.py`）、发现编排（`discover.py`）、网页入库（`web_ingest.py`）、变更仓储（`change_repo.py`）、巡检（`inspector.py` 51.5 KB）。

**规模**：`inspector.py` 51.5 KB、`announce.py` 39.7 KB、`discover.py` 29.9 KB。

**它不负责**：不做解析（`ingestion`）、不做条款检索（`retrieval`）、不管渠道台账的**人工维护界面**（那在 `api` + 插件）。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 渠道健康探针 | `channel_probe.py` | 巡检与台账面板 |
| 公告发现 | `announce.py` | 法规/标准变更 |
| 发现编排 | `discover.py` | 巡检主流程 |
| 网页入库 | `web_ingest.py` | `ingestion` |
| 变更仓储 | `change_repo.py`（`update_check_batch` / `update_change_event`） | 变更事件 |
| 渠道能力表 | `channel_answers.py`（五类能力） | 台账面板 |
| 巡检 | `inspector.py` | 运维 |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| `storage`（`channel_repo`） | 上游模块 | 台账持久化 |
| `proxy_rotate` | 仓内 | 换出口 |
| 各渠道 HTTP 端点 | 外部 | 抓取 |

## 明确不做什么

- **不做判定「这条渠道死了」**：429 限流改判 `suspicious/rate_limited`——**限流是「稍后再来」，不是死**。
- **不把「HTTP 200」当判据**：本领域 200 经常意味着 JS 壳或空列表（实测：应急部标准页 465 bytes、bzw 列表页「共 0 条」）。
- **不做工具类渠道的链接可达性**：那类**不是采集通路**，判据不同、不并进探针表（见 `docs/CHANNEL-COVERAGE-PLAN.md` §7 的 D-a）。

## 已知边界（诚实）

- **台账 131 条**，其中含 github 字样 19 条。
- **探针表答的是「采集通路今天能不能抓到东西」**——别把仓库链接算成渠道能力。
- ⚠ 2026-09-30 业主给 `tool` 类补了新用途：**GitHub 上的教学/文档要采集并持续更新**（按采集通路设计，**新开一组**，不改现有 24 条归类）。
