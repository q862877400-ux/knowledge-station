# Implementation Plan: 「本轮依据」三处界面改动（spec 009）

**Feature**: `009-turn-evidence-ui` ｜ **Spec**: [spec.md](./spec.md) ｜ **取证**: [research.md](./research.md)

**Created**: 2026-10-10

---

## 一、技术上下文

| 项 | 值 |
|---|---|
| 引擎 | Python（`src/core/`），FastAPI，走本地 HTTP |
| 插件 | TypeScript + React 18（`plugin/client/`、`plugin/src/`） |
| 本轮数据通路 | `ks_answer` → `plugin/src/turn.js` 暂存 → `GET /ks/turn/last` → `KsTurnTab` 渲染 |
| bbox 现成能力 | 引擎端点 `/api/v1/clauses/{id}/spans`、宿主代理 `/ks/bbox`、前端 `fetchBbox(rev)`、证据 tab 自取兜底 |
| 判据通道 | jsdom 渲染冒烟（`smoke-turn-tab.mjs`）、pytest、`tsc` |

## 二、宪法检查（`.specify/memory/constitution.md`）

- **原则 VI「只做缝合不做发明」**：bbox 三环全部**复用现成能力**，不新写取数逻辑。
- **判据要有牙**：每条配变异。
- **诚实边界**：真宿主验不了箭头 ⇒ 如实写；引擎未运行 ⇒ 端到端未验。

## 三、阶段划分

### 阶段 1：问题 2（删 GB 字样）—— 最便宜，先做

**改法**：`KsTurnTab.tsx` 的 `KsTurnEvidenceRow` **不再渲染** `legal_hierarchy`。
⚠ 只删显示；`KsTurnEvidenceItem` 接口里**保留**该字段（数据仍到达前端，别的消费者可能要用）。

**判据**：`smoke-turn-tab.mjs` 加一条**负向**断言（渲染结果里不出现 `GB` / 层级值）。
**变异**：把它加回去 ⇒ 必红。

### 阶段 2：问题 1（同文件多条款归组）—— 结构性改动

**改法**：把 `KsTurnTab` 的渲染从"一条依据一张卡"改成：
1. 按 `doc_id` **分组**；
2. 组内按 `clause_number` **数值感知升序**（`5.2.3` < `5.10.1`）；
3. 每组渲染**一个文件标题**（标准号 + 文件名）+ 组内条款列表。

⚠ **排序的稳健性**（风险点）：`clause_number` 可能是 `第一条`、`8.1.1`、空。
排序键 = **先按"能切成数字段"的比数值，不能切的按原串比**，**不许抛错**。

**判据**：
- 同一 `doc_id` 的标题在渲染结果里**只出现一次**；
- 组内条款顺序正确（构造 `5.10.1` 与 `5.2.3` 反序输入 ⇒ 输出必须是 `5.2.3` 在前）；
- 每个条款仍各自有徽章 / 摘要 / 看原文入口。

**变异**：把分组拆开（不归组）⇒ 必红；把排序改成字典序 ⇒ 必红。

### 阶段 3：问题 3（红箭头）—— 三环全修

| 环 | 改法 | 文件 |
|---|---|---|
| ① 引擎不输出 bbox | 证据字段新增 `bbox`（4 个数）与 `bbox_page`；数据来自 `source_span` 的**首个 span**（`sort_order` 最小，且 `page_number == page_start` 优先） | `src/core/llm/ks_answer.py` |
| ② 前端不声明也不传 | `KsTurnEvidenceItem` 加 `bbox` / `bbox_page`；`turnEvidenceHref` 把它们放进 `KsEvidence` 目标 | `plugin/client/KsTurnTab.tsx` |
| ③ ★ URL 编码器丢掉它 | `evidenceUrlOf` **补编 `bbox` 参数**（`x0,y0,x1,y1`） | `plugin/client/ksEvidence.ts` |

⚠ **环①的实现约束**：
- **只读**（`SELECT`），零副作用；
- 取 bbox **失败不许阻塞回答**（与证据 tab 的兜底同口径：失败就留空、前端显示"取不到"）；
- 用**一次批量查询**（`IN (...)`），实测 0.2 ms；
- 取不到时字段**留空**（不编造、不用 0 兜底 —— 0 会画出左上角一个错箭头）。

**判据**：
- 引擎：pytest——证据 dict 里 `bbox` 存在且是 4 个数字、`bbox_page` 是 int；
  无 span 的条款 ⇒ 两者**都不存在**（不是 0、不是空数组）。
- 前端：`evidenceUrlOf` 对带 bbox 的目标 ⇒ URL **含 `bbox=`**；不带 ⇒ **不含**（不许编空参）。
- **变异**：三环各摘一次 ⇒ 对应判据各红。

### 阶段 4：收口

- `tsc` / pytest / 冒烟全跑；重建产物；小提交 + 快照；开发史登记。
- **派独立复核**（改了引擎证据契约 + 前端 URL 契约 ⇒ 属必验类别）。

## 四、交付物

| 产物 | 落点 |
|---|---|
| 引擎 | `src/core/llm/ks_answer.py`（bbox 进证据字段） |
| 前端 | `plugin/client/KsTurnTab.tsx`（分组 + 删 GB + 传 bbox）、`plugin/client/ksEvidence.ts`（编 bbox） |
| 判据 | `plugin/scripts/smoke-turn-tab.mjs`（改）、`tests/test_ks_answer*.py`（改/增） |
| 产物 | `plugin/client.js` |
| 留痕 | `docs/UI-BASELINE.md` §5ac、`docs/DEVELOPMENT-HISTORY.md` §10.235 |

## 五、风险与对策

| 风险 | 对策 |
|---|---|
| 改证据字段影响快照/契约测试 | 先跑相关测试看影响面；逐条按新行为更新，**不许**为了绿而放宽判据 |
| 分组改变既有渲染断言 | 逐条核 `smoke-turn-tab.mjs` 的既有断言，该更新的按新行为更新并**说明为什么** |
| 条款号排序抛错 | 排序键做成**永不抛错**的纯函数，单独测（含空值/中文/乱序） |
| 引擎未运行 ⇒ 端到端验不了 | 用 pytest 直调 `answer()` 的组装逻辑 + 真库只读查询验证；端到端如实标"未验" |
| 改了 `evidenceUrlOf` 影响别的调用方 | `grep` 全部调用点；补编 `bbox` 是**纯增量**（不传就不编，行为不变） |
