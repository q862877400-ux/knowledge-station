# Tasks: 检索路径必须尊重 `catalog_hidden`

**Input**: Design documents from `/specs/013-catalog-hidden-retrieval-guard/`

**Prerequisites**: plan.md, spec.md

## Format: `[ID] [P?] Description`

## 硬约束

1. **判据唯一所有者** —— 不许六条 SQL 各写一份。
2. **列可能不存在**（增量列）⇒ 自适应。
3. **不删文档**（不可逆）；`catalog_hidden` 是**可逆**的。
4. **不动那 6 篇真标准的隐藏状态**（它们本来就该挡）。

---

## Phase ①: 取证

- [x] **T001** 确认缺陷：真实检索（`top_k=20`）里假样本排**第 3、16 名**。
- [x] **T002** 查清那 6 篇真标准**为什么**被隐藏：`normal` 条款 = **0**
      ⇒ `pipeline` 的规则是 **`n_normal == 0`** ⇒ **它们本来就该挡**。
- [x] **T003** ⚠ **就地更正我 2026-10-12 说错的话**（"修检索会误伤这 6 篇"）——
      写在 spec.md 开头，原话与更正并列。

## Phase ②: 修法

- [x] **T004** `_catalog_visible_fragment()`（给 JOIN 了 `doc_meta` 的通道 A/D/E）。
- [x] **T005** `_catalog_visible_by_clause()`（给没 JOIN 的通道 B/F）。
      两条都**自适应列是否存在**（列不在 ⇒ 返回空串）。
- [x] **T006** 六通道接线：A/D/E 拼 `vis_doc`；B/F 拼 `vis_clause`；
      **C 在 Python 里筛**（vec0 的 `NOT IN` 下推没验证过，不许拼 SQL）。

## Phase ③: 判据

- [x] **T007** `tests/test_catalog_hidden_retrieval.py`（**11 条**）。
- [x] **T008** 端到端：真库上假样本 **2 → 0**；真法规召回 **17 → 17**（没减少）。
- [x] **T009** 变异自验 **5/5 被咬住**。
- [x] **T010** ⚠ **第一版判据有缺口**（M4/M5 存活、7 passed 假绿）⇒
      补两组**结构判据**（"拼进各通道 SQL" / "隐藏集合被算出来"）后才全咬住。**留痕**。

## Phase ④: 收口

- [x] **T011** 门禁 `-Full`（读数见提交）。

---

## 明确未做

- [ ] **不删任何文档**（不可逆）。
- [ ] **不改那 6 篇的隐藏状态**。
- [ ] **不改 `catalog_hidden` 的写入规则**。
