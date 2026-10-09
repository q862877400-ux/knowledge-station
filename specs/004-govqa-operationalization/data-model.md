# Phase 1 数据模型：政务问答采集系统的可运维化

**Created**: 2026-10-10 ｜ **对应 spec**: [spec.md](./spec.md) ｜ **调研依据**: [research.md](./research.md)

> 只描述**结构与状态**，不写实现代码。字段名是契约，实现细节在 `tasks.md`。

---

## E1. Channel（通道）

一个可采集的数据来源。**对应现有 `adapters/` 里的一个模块。**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `key` | string | ✅ | 唯一标识（= `adapters.SITE["key"]`，如 `sd-yantai`） |
| `name` | string | ✅ | 中文名（如「烟台市·互动交流·网上民声」） |
| `level` | enum | ✅ | `national` / `province` / `city` / `other` |
| `region` | string | — | 所属行政区（用于覆盖销号表聚合） |
| `entry` | string | ✅ | 入口 URL |
| `watermark_type` | enum | ✅ | `page` / `since` / `idset`（见 R1） |
| `self_reported_total` | int | — | 源站自报总量（用于算完成度） |
| `cap` | int | — | 我方策略上限（超此不再采） |
| `status` | enum | ✅ | `ok` / `blocked` / `todo` / `dead` |

**状态机**：

```
todo ──首次采集成功──▶ ok ──连续失败 N 次──▶ blocked ──复验通过──▶ ok
                      │
                      └──实测确认为空壳──▶ dead（不再投入）
```

**验证规则**：
- `key` 必须与 adapter 模块里的 `SITE["key"]` 一致（不一致 ⇒ 采集结果无法归属）
- `watermark_type` 必须与 adapter 实际能提供的位置信息匹配
- `status=dead` 的通道**必须**在 GOAL.md §三 的判死清单里有对应条目（宪法 III 证据优于断言）

---

## E2. Watermark（水位）

某通道上次成功采集到的位置。**存 `state/watermarks.json`。**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `channel_key` | string | ✅ | 关联 E1 |
| `type` | enum | ✅ | 冗余自 E1，用于校验（不一致 ⇒ 报错） |
| `value` | any | ✅ | 位置值。`page`→int；`since`→ISO 时间串；`idset`→id 数组 |
| `updated_at` | string | ✅ | 水位更新时间（ISO 8601） |
| `last_batch_count` | int | ✅ | 上次该通道新增条数 |
| `last_success_at` | string | ✅ | 上次成功采集完成时间 |
| `consecutive_failures` | int | ✅ | 连续失败次数（用于状态机迁移） |

**关键规则**：
- **水位只在采集成功后前移**（FR-003）。失败时**不得**改动 `value`，只 `consecutive_failures += 1`。
- 水位**丢失/损坏**时，`value` 视为「无」，退化为全量采集（FR-006），
  并在 `health` 输出里标注「水位缺失，已退化全量」。
- `idset` 型 `value` **必须有上限**（建议 50,000），超限时按 LRU 淘汰 ——
  否则 JSON 会无限膨胀。

**状态机**：

```
（不存在）──首次采集成功──▶ 有水位
有水位 ──采集成功──▶ 前移 + consecutive_failures=0
有水位 ──采集失败──▶ value 不变 + consecutive_failures+1
有水位 ──文件损坏──▶ 视为不存在 + 标记「需全量」
```

---

## E3. Record（记录）

一条问答。**现有格式，本特性不改变其结构**，只新增两个派生字段。

| 字段 | 类型 | 必填 | 本特性是否改动 |
|---|---|---|---|
| `source` | string | ✅ | 否（= E1.key） |
| `id` | string | ✅ | 否 |
| `question` | string | ✅ | 否 |
| `answer` | string | ✅ | 否 |
| `asked_at` | string | — | 否 |
| `answered_at` | string | — | 否 |
| `dept` | string | — | 否 |
| `channel` | string | — | 否 |
| `url` | string | — | 否 |
| `extra.msg_type_norm` | string | — | 否（已有） |
| `extra.msg_type_source` | string | — | 否（已有） |
| **`extra.ingested_at`** | string | — | ★ **新增**：本条被采集入库的时间（用于增量诊断） |
| **`extra.scope_tag`** | string | — | ★ **新增**：口径标签（`law_std` / `other`），配合新口径 |

**唯一性**：`(source, id)` 全库唯一 —— 这是幂等的基础（R2）。

**验证规则**：
- `id` 不得为空
- **`question` 与 `answer` 不得同时为空**（SC-008）
- 生成 `id` 用内容指纹时，**指纹输入的所有字段都必须参与空值处理**
  （教训来源：`nat-mohurd` 因 `question` 为空导致 59 行碰撞）

---

## E4. CoverageUnit（覆盖单元）

一个行政区或机构。**覆盖销号表的行。**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | ✅ | 名称（如「云南省」「大理白族自治州」） |
| `level` | enum | ✅ | `province` / `city` / `ministry` / `npc` / `thirdparty` |
| `parent` | string | — | 上级（地级市 → 省） |
| `channels` | string[] | ✅ | 下属通道 key 列表 |
| `total_records` | int | ✅ | 落盘总量 |
| `threshold` | int | ✅ | 达标下限（省级默认 3000 / 地级默认 500，可调） |
| `gap` | int | ✅ | 缺口 = `max(0, threshold - total_records)` |
| `ratio_to_median` | float | ✅ | 相对全国同级的**中位数**比值 |
| `status` | enum | ✅ | `ok` / `thin` / `none` |
| `uncovered_channels` | string[] | ✅ | **尚未建立来源的渠道清单**（FR-010） |

**状态机**：

```
none（无来源）──建源并采集──▶ thin（有数据但 < threshold）──补采──▶ ok（≥ threshold）
```

**关键规则**：
- `uncovered_channels` **不能为空数组了事** —— 若某地区确实已无未覆盖渠道，
  必须显式写「已穷尽」，而不是留空（否则无法区分「没查」和「查完没有」）
- `ratio_to_median` 用**同级中位数**（省级比省级，地级比地级），不跨级比

---

## E5. HealthReport（体检报告）

一次自检的结果。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `checked_at` | string | ✅ | 检查时间 |
| `total_records` | int | ✅ | 全库条数 |
| `floor` | int | ✅ | 地板值（`.round-floor`） |
| `criteria` | object | ✅ | 4 项判据各自的状态与实测值 |
| `verdict` | enum | ✅ | `usable` / `not_usable` |
| `reason` | string | ✅ | 一句话原因（给人看的，可用中文） |
| `elapsed_seconds` | float | ✅ | 耗时（SC-010 要求 ≤60s） |

**`criteria` 结构**（**机器可读部分一律纯 ASCII**，R5）：

```
TOTAL=<n>
ADAPTERS=<n>
EMPTY=<n>
DUPS=<n>
COVERAGE=<pct>
```

**关键规则**：
- `verdict` 只有两态，**不允许「部分可用」这种模糊态** ——
  模糊态会让用户无法判断能不能开始分析
- `reason` 必须能回答「我能不能现在拿这份数据去做分析」

---

## 实体关系

```
CoverageUnit 1 ──< N Channel 1 ── 1 Watermark
                     │
                     └──< N Record
                     
HealthReport ── 聚合自 ──▶ Record / Channel / Watermark
```

---

## 本特性对现有数据的改动

| 改动 | 影响面 | 可回滚 |
|---|---|---|
| 新增 `extra.ingested_at` | 新写入的记录才有；旧记录留空 | ✅（纯新增字段） |
| 新增 `extra.scope_tag` | 同上 | ✅（纯新增字段） |
| 新增 `state/watermarks.json` | 全新文件 | ✅（删掉即回到无水位状态） |
| **不删任何现有记录** | — | — |

> ⚠ **明确未做**：本特性**不处理**「现有 35 万条里只有 2.20% 符合新口径」这个问题。
> 那是**口径问题**，属另一条线（见 GOAL.md 的「口径收窄」段）。
> 本特性只保证「按新口径采集时，系统能正确运营」。
