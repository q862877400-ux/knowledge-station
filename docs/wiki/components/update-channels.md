# update-channels（渠道适配器）

**位置**：`src/core/update/channels/`
**一句话**：每条官方渠道一个适配器，把「能不能抓、抓到了什么」说清楚。

## 职责

**渠道覆盖率的执行实体**。每个来源一个适配器类（实测 **14 个适配器**），外加公共基类与台账链：`base.py` 22.6 KB（适配器基类）、`ledger_chain.py` 20.9 KB（台账链）、`ndls.py` / `ttzb.py` 等具体来源、`question_router.py`（把五类问题路由到能回答它的渠道）。

**它不负责**：不做探针调度（`update/channel_probe.py`）、不做公告发现（`update/announce.py`）、不做台账界面（`api` + 插件）。

## 对外提供什么

| 各来源适配器 | `ndls.py` / `ttzb.py` / …（共 14 个） | `update` 的巡检 |
| 适配器基类 | `base.py` | 全部适配器 |
| 台账链 | `ledger_chain.py` | 台账 |
| 问题路由 | `question_router.py` | 五类能力表 |

## 依赖什么

| `proxy_rotate` | 仓内 | 换出口 |
| 各来源 HTTP 端点 | 外部 | 抓取 |

## 明确不做什么

- **不许吞异常当「没数据」**：抓不到要如实说抓不到（本领域「HTTP 200 但内容为空」很常见）。
- **不做判死**：限流（429）不是死，见 `update` 契约。
- **MUST NOT 绕过白名单域**。

## 已知边界（诚实）

- ⚠ **`ADAPTER_CLASSES` 的键与适配器名必须一致**：本仓出过一次接线名不一致导致渠道「在链上但实际不工作」（台账里的 G23）。
- **新增适配器 MUST 同时登记台账**，否则它不在覆盖率里。
