# update-channels（渠道适配器）

**位置**：`src/core/update/channels/`
**一句话**：每条官方渠道一个适配器，回答「这一号，这个渠道怎么说」。

## 职责

**覆盖率的执行实体**：`base.py` 22.6 KB 定死单渠道探测的结论对象与基类，各来源各写一个适配器，`__init__.py` 的 `ADAPTER_CLASSES` 登记 **13 个渠道**（`official_gb` / `web` / `govcn` / `laws_db` / `mem_gov` / `std_samr_hb` / `hbba` / `dbba` / `ndls` / `mohurd` / `ttzb` / `mee` / `cssn`）。

配套：`routing.py`（按标准号特征选链）、`ledger_chain.py` 20.9 KB（台账驱动的降级链，**只算不改**）、`question_router.py`（把五类问题路由到能答它的渠道）、`class_outcomes.py`（把一次探测翻译成五类各自答成什么样）、`proxy_rotate.py`（换出口 IP）。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 结论对象 | `base.ChannelResult`（11 字段） | 全部适配器与巡检 |
| 适配器基类与默认传输 | `base.ChannelAdapter` / `default_transport()` / `CurlCffiTransport` / `HttpxTransport` | 全部适配器、`materials/harvest.py`、`knowledge/ccs_fetcher.py` |
| 渠道登记表 | `__init__.ADAPTER_CLASSES` | `update/inspector.py`、`ingestion/bulk.py`、`api/routes_update.py` |
| 归一与映射工具 | `base.norm_no()` / `query_no()` / `map_state_text()` / `derive_change_type()` / `looks_like_captcha()` / `recordable()` / `upd_log()` | `update/*`、`knowledge/ccs_fetcher.py` |
| 按号选链 | `routing.fallback_chain()` / `select_chain()` / `segment_matches()` | `update/inspector.py` |
| 台账链与问题路由 | `ledger_chain.chain_for_number()` / `question_router.channels_for()` | 巡检与能力表 |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| 各来源 HTTP 端点 | 外部服务 | 抓取 |
| curl_cffi / httpx | 外部库 | 传输；curl_cffi 优先（模拟浏览器 TLS 指纹），不可导入时回退 httpx 并打 WARN |
| `proxy_rotate`（仓内同包） | 仓内 | 被限流时换出口 |

## 明确不做什么

- **不做编排与巡检**：降级链由 `update/inspector.py` 编排；`routing` 只给字面量链，`ledger_chain` 只算不改；本包保证的是**单渠道 `probe` 的确定性**。
- **不落库**：`probe` 只返回 `ChannelResult`；写库在 `update/change_repo.py`。
- **不把验证码当失败**：命中验证码特征只标 `captcha=True`，**不写库、不计 gray/failed**，批次转 paused 等人工过点。
- **不猜未知状态码**：未知 state 串 → `legal_status=None` 并告警，不许猜。
- **不改 schema**：新增渠道不许顺手改 `update_change_event` 的 CHECK 约束。
- **不做「这条渠道死了」的判定**：限流不是死，见 [update](update.md)。

## 关键数据

`ChannelResult` 的 11 个字段（接口冻结）：`channel` / `found` / `captcha` / `change_type` / `legal_status` / `latest_version` / `effective_date` / `published_date` / `withdrawn_date` / `evidence_url` / `raw`。

## 改了它会影响谁

- **`update/inspector.py`**：巡检主流程与台账链
- **`knowledge/ccs_fetcher.py`**：直接 import `cssn` 适配器与 `looks_like_captcha` / `query_no`
- **`materials/harvest.py`**、**`ingestion/bulk.py`**、**`api/routes_update.py`**：直接用基类与登记表

## 已知边界（诚实）

- ⚠ **`ADAPTER_CLASSES` 用 `_safe_import` 容错注册**：子代理在实现的渠道导入失败（改名、语法错）只记一条 WARN，**渠道会静默从表里消失**。改渠道名后必须实测它还在表里。
- **13 个渠道里 9 个走 `_safe_import`**，只有 `official_gb` / `web` / `govcn` / `laws_db` 是硬 import。
- **注释里写的降级链是 `official_gb → ndls → govcn` 字面量**，与台账（`update_channel`）里的 `enabled` / `wiring` / `state` **不是同一份真值**；台账驱动的那版还在 `ledger_chain` 里「只算不改」。
