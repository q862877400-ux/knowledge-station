# Implementation Plan: 检索路径必须尊重 `catalog_hidden`

**Branch**: `013-catalog-hidden-retrieval-guard` | **Date**: 2026-10-14

**Input**: Feature specification from `/specs/013-catalog-hidden-retrieval-guard/spec.md`

## Summary

给六条检索通道**统一加**"目录可见性"判据（`catalog_hidden=0`），
让检索路径与浏览路径**用同一个可见性口径**。

## Technical Context

**Language**: Python 3.12
**Storage**: SQLite（`doc_meta.catalog_hidden` —— **增量列**，不在 `schema.sql`）
**Testing**: pytest
**Constraints**: 判据**唯一所有者**（不许六条 SQL 各写一份）；列可能不存在 ⇒ 自适应

## Constitution Check

| 原则 | 怎么满足 |
|---|---|
| **I 说人话** | 汇报说"测试用的假法规不再出现在答案里了"；不说表名/列名 |
| **II 从事实出发** | ⚠ **推翻我自己 2026-10-12 的说法**："修检索会误伤 6 篇真标准" —— **错**（它们 `n_normal=0`，本来就该挡）。**就地更正** |
| **III 证据优于断言** | 修前/修后都跑了真实检索（2 条 → 0 条；真法规召回 17 → 17） |
| **V 假绿判 failed** | ⚠ **第一版判据有缺口**（变异 M4/M5 存活）⇒ 补结构判据后才全咬住，**留痕** |
| **VI 门禁为准** | `-Full` N/N |

## Project Structure

```text
src/core/retrieval/hybrid_engine.py   # 改：两个片段函数 + 六通道接线
tests/test_catalog_hidden_retrieval.py # 新：11 条判据
specs/013-catalog-hidden-retrieval-guard/{spec,plan,tasks}.md
```

## 判据设计

| 组 | 断言 | 牙在哪 |
|---|---|---|
| 片段函数 | 隐藏被排除 | 恒空 ⇒ 红 |
| | **两处同口径** | 只改一处 ⇒ 红 |
| | **列不在时不加条件** | 列不在也拼 ⇒ 老库 `no such column` |
| | **没有隐藏文档时仍生成片段** | 写成"没有就不拼" ⇒ 第一篇隐藏后失效 |
| 那 6 篇 | `n_normal==0` ⇒ **本来就该挡** | 防下一个人把"别挡它们"当需求 |
| 接线 | `+ vis_doc` ≥3、`+ vis_clause` ≥2 | 通道 A 不拼 ⇒ 红（M5） |
| | 向量通道在 Python 里筛 | 改成 SQL 拼法 ⇒ 红（逼他先验证） |
| | **隐藏集合被算出来** | 用 `if False` 关掉 ⇒ 红（M4） |
| 端到端 | 真库上假样本不进结果 | 回到缺陷 ⇒ 红 |

## 变异自验（5 条）

| 变异 | 必须变红 |
|---|---|
| M1 片段恒空 | 隐藏被排除 / 两处同口径 |
| M2 只改一处 | 两处同口径 |
| M3 列不在也拼 | 列不在时不加条件 |
| M4 隐藏集合不算 | 隐藏集合被算出来 |
| M5 通道 A 不拼片段 | `+ vis_doc` ≥3 |

## 风险与回退

| 风险 | 缓解 |
|---|---|
| 列不存在时拼片段 ⇒ 老库全红 | 自适应（列在才拼）；判据钉住 |
| 只改一处 ⇒ 两条路口径分叉 | "两处同口径"判据 |
| vec0 下推写错 ⇒ 整路返回空 | 通道 C **不拼 SQL**，Python 里筛 |
| 误伤 `catalog_hidden=0` 的文档 | 端到端判"真法规召回没减少" |

## Complexity Tracking

无违规项。
