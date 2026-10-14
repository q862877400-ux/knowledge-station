# Implementation Plan: 红箭头画不出的五个根因

**Branch**: `012-arrow-bbox-root-causes` | **Date**: 2026-10-12（归档 2026-10-14）

**Input**: Feature specification from `/specs/012-arrow-bbox-root-causes/spec.md`

## Summary

五件事，**三件是"修根因"、两件是"业主新要求"**：

1. **R1**：`middle_schema._convert_40_to_34` 补**单位换算**（MinerU 4.0 的比例 → 点）。
2. **R2**：回填 756 篇存量坏值（复用盘上的 MinerU 产物重算）。
3. **R3**：宿主侧 `evidenceAnchor` 与客户端 `evidenceUrlOf` **同口径**编 bbox。
4. **R4**：同轮其他条款画**半透明**红箭头。
5. **R5**：正文自带条款号时**不单出**那一行。

## Technical Context

**Language/Version**: Python 3.12（引擎）+ TypeScript/TSX（客户端）

**Primary Dependencies**: 无新增（全部复用）

**Storage**: SQLite（`source_span.bbox_json`）

**Testing**: pytest + 既有 smoke（`smoke-turn-tab.mjs` / `smoke-effect-tool.mjs`）

**Constraints**:
- **判据只有一个所有者**：CCS 在 `ccs_fetcher`、下载校验在 `archive_pdf`、占位字节数在 `_MINIMAL_PDF`
- 回填**写前必须备份**、**单事务**、**幂等**
- **不新增依赖**

## Constitution Check

| 原则 | 怎么满足 |
|---|---|
| **I 说人话** | 汇报说"坐标的单位搞错了""从网上入的现在也能进目录了""要下载前会问你要不要"；不说字段/常量 |
| **II 从事实出发** | ⚠ **本 spec 推翻了我自己三处说法**：① 我说"框太小画不出" —— 实际是**坐标单位错**；② 我说"要放宽白名单" —— 错；③ 我用 `附录A` 当"不带编号"的反例 —— 错（真库附录正文首行就是「附 录 A」）。**每处都就地更正、留痕** |
| **III 证据优于断言** | 每个数字挂复算命令；SC-008 要求变异自验 |
| **IV 一个事实一个归属层** | 根因报告落 `docs/research/ARROW-ROOT-CAUSES-2026-10-12.md`；实现写本 spec |
| **V 假绿判 failed** | 变异自验：R1 **5/5**、R4 **6/6** |
| **VI 门禁为准** | `-Full` N/N · exit=0 |
| **VII 不撞车** | 只动 `src/core/ingestion/` + `src/core/llm/` + `plugin/client/` + `plugin/src/index.js` + `scripts/` + `tests/` |

## Project Structure

```text
src/core/ingestion/middle_schema.py   # R1 修（单位换算）
plugin/src/index.js                   # R3 修（宿主侧编 bbox）
plugin/client/ksEvidence.ts           # R3+R4（also= 编/解）
plugin/client/KsArrowOverlay.tsx      # R4（半透明箭头 + 共享转换）
plugin/client/KsEvidenceTab.tsx       # R4（兄弟箭头几何 + 两模式渲染）
plugin/client/KsTurnTab.tsx           # R5 + R4（snippetCarriesClauseNo / siblingEvidenceOf）
scripts/backfill-bbox-units.py        # R2（新）
tests/test_middle_bbox_units.py       # R1 判据（9 条）
tests/test_channel_system_wiring.py   # spec 011 的（本批加了占位识别 3 条）
plugin/scripts/smoke-turn-tab.mjs     # R5 + R4 判据
plugin/scripts/smoke-effect-tool.mjs  # R3 判据
docs/research/ARROW-ROOT-CAUSES-2026-10-12.md
```

## 判据设计（先定判据，再写实现）

### R1（单位换算）

| # | 断言 | 牙在哪 |
|---|---|---|
| A1 | 比例 bbox ⇒ 输出是点（`0.116*2456=284.9`） | 不换算 ⇒ 红 |
| A2 | 换算后**通过退化闸门**（宽≥5 / 高≥3） | 这是**用户可见的效果** |
| A3 | 坐标落在页尺寸内 | 越界 ⇒ 红 |
| A4 | 不同页尺寸算出不同结果（防写死 595/841） | 写死 ⇒ 红 |
| A5 | **已是点的 bbox 原样返回**（>1 不缩） | 重复缩放 ⇒ 红 |
| A6 | 混合值（有 >1）整条原样返回 | 部分缩 ⇒ 红 |
| A7 | 行级 bbox 也换算 | 行级才是箭头用的 |
| A8 | 3.4 产物**原样返回**（同一对象） | 误伤 6,417 篇正常文档 |

### R2（回填）

| # | 断言 | 牙在哪 |
|---|---|---|
| B1 | 坏值数大幅下降 | 不回填 ⇒ 红 |
| B2 | **独立**（重解析）比对一致 | 自证不算 |
| B3 | 匹配不上**不硬写** | 硬写 ⇒ 错位置 |

### R3（同口径）

| # | 断言 | 牙在哪 |
|---|---|---|
| C1 | 宿主侧 URL 含 `bbox=` / `bboxPage=` | 不编 ⇒ 红 |
| C2 | 无 bbox ⇒ **不编空参** | 编空串 ⇒ 红 |
| C3 | bbox 只有 3 个数 / 含 NaN ⇒ 不编 | 编错参 ⇒ 红 |

### R4（兄弟箭头）

| # | 断言 | 牙在哪 |
|---|---|---|
| D1 | 只收同文档、不是我、有坐标的 | 缺任一 ⇒ 红 |
| D2 | 跨文档**不收** | 收 ⇒ 红 |
| D3 | **去重**（同条款命中两次只画一个） | 不去重 ⇒ 叠画成假象 |
| D4 | URL 含 `also=`；无兄弟时**不编空参** | — |
| D5 | 与主箭头**同一图形**（只差 opacity） | 换色 ⇒ 红 |
| D6 | 透明度在 0.15~0.6 | — |

### R5（去重复行）

| # | 断言 | 牙在哪 |
|---|---|---|
| E1 | 正文自带条款号 ⇒ 行里只出现 1 次 | 不隐藏 ⇒ 出现 2 次 |
| E2 | 正文不含（`前置1`）⇒ **仍显示** | 一律隐藏 ⇒ 丢信息 |
| E3 | 无条款号 ⇒ 显示占位（既有行为不变） | — |

### 变异自验

| 变异 | 必须变红 |
|---|---|
| R1：去掉换算 / 只乘宽 / 去掉 >1 闸门 / 行级不换算 / 写死页尺寸 | A1–A4, A7 |
| R4：不排自己 / 不校验文档 / 去掉去重 / 不编 also / 换颜色 / 编空参 | D1–D5 |

## 实施顺序（按业主令「①②③顺序」）

R1（根因）→ R5（改动小）→ R3（消两个家）→ R4（新功能）→ R2（回填最重）

## 风险与回退

| 风险 | 缓解 |
|---|---|
| 单位换算误伤 3.4 产物 | A8 判据钉"原样返回" |
| 回填写错位置 | **x 当锚**（存 3 位小数）+ y 只消歧；匹配不上**不硬写**；写前备份；独立验证 |
| 兄弟箭头叠画成"更重要"假象 | 去重 |
| 半透明箭头在关开关时仍画 | 与主箭头**同开关** |

## Complexity Tracking

无违规项。
