# spec 009 取证（三处改动，全部实测）

> 时点：2026-10-10 ｜ 全部为**代码级 + 真库级**取证；引擎当时**未运行**（见下"诚实边界"）

## 问题 2：`GB` 字样从哪来

### 数据事实（真库 `%APPDATA%\KnowledgeStation\database\knowledge.db`）

`doc_meta.legal_hierarchy` 取值分布（共 8983 行）：

| 值 | 篇数 |
|---|---|
| `GB/T` | 6130 |
| `法律` | 1430 |
| **`GB`** | **1043** |
| `规范性文件` | 261 |
| `其他` | 84 |
| `部门规章` | 19 |
| `征求意见稿` | 16 |

**交叉核（标准号前缀 × 层级）**：

| 交叉 | 条数 |
|---|---|
| `GB/T…` × `GB/T` | 6129 |
| `GB…` × `GB` | **1024** |
| `其它` × `GB` | **19** |
| `其它` × `GB/T` | 1 |

⇒ **`GB` 绝大多数是真实的"强制性国标"分类**（1024 篇标准号确实是 GB 开头）；
**另有 19 篇**是法律/条例被**默认值兜成 GB**
（`src/core/domain/models.py:102` 与 `:124` 的 `legal_hierarchy: str = "GB"`）。

### 渲染事实

- 引擎：`src/core/llm/ks_answer.py:113` → `"legal_hierarchy": clause.legal_hierarchy or "GB"`
  （**空值硬编码回退 "GB"**）。
- 前端：`plugin/client/KsTurnTab.tsx:185-189` 渲染它（字号 11、tertiary 色）。

### 业主诉求与我的判定

业主说「现行有效后面的 GB 字样删除」⇒ 嫌的是**显示冗余**：
徽章已说"现行有效/已被替代"，再挂 `GB` 对用户**没有增量信息**。
⇒ **改显示层**（不显示该字段），**数据保留**。

⚠ **另登记不本批修**：那 19 篇兜底错标是**数据层**问题（改它要动生产库 ⇒ 属"要业主点头"的类）。

## 问题 3：红箭头不出现的**完整根因链**（三环，全部确证）

| 环 | 位置 | 事实 | 复算 |
|---|---|---|---|
| **① 引擎不输出 bbox** | `src/core/llm/ks_answer.py:96-128` | 公共字段有 `page_start`，**没有 `bbox`** | `var/tmp/prove-arrow-chain.py` |
| **② 前端不声明也不传** | `KsTurnTab.tsx:47-58` 接口无 `bbox`；`:74-84` `turnEvidenceHref` 只传 `doc/page/rev` | 同上 | 同上 |
| **③ ★ URL 编码器丢掉它** | `ksEvidence.ts:123-137` `evidenceUrlOf` | **只 `params.set` 了 `doc` / `page` / `rev` —— 没有 `bbox`** | 同上 |

⇒ **环③ 是决定性的**：即使①②都修好，`bbox` 也会在编码这一步被丢掉。
（`parseEvidence` 能**解析** `bbox`（`parseBbox` 已实现），但**没有任何地方编它** —— 只进不出。）

### bbox 数据在哪（真库实测）

| 表 | 关联列 | 几何列 | 行数 |
|---|---|---|---|
| `source_span` | `clause_revision_id` | `bbox_json` + `page_number` | **1,842,493** |

- `bbox_json` 真实样例：`[76.0, 643.43, 117.0, 655.43]` = `[x0,y0,x1,y1]`、**左下原点**
  ⇒ 与 `ksEvidence.ts` 的坐标契约**逐字一致**（不许再做 H−y 翻转）。
- 索引：`idx_span_clause ON source_span(clause_revision_id, page_number)` 存在。
- **性能实测**：50 个 rev 逐个点查 **0.3 ms**（单次 0.01 ms）；一次 `IN` 批量查询 **0.2 ms**
  ⇒ 取 bbox **不是性能问题**。

### 已有现成能力（不该重复造）

| 能力 | 位置 | 说明 |
|---|---|---|
| 只读端点 | `src/core/api/server.py:2324` `GET /api/v1/clauses/{id}/spans` | 返回该条款全部 span（含 bbox），已处理"无 span → 空数组" |
| 宿主代理 | `plugin/src/index.js:137` `KS_BBOX_PATH = '/ks/bbox'` | 同源 GET，token 不出宿主 |
| 前端取数 | `plugin/client/api.ts:407` `fetchBbox(rev)` | 已实现、已做形状校验 |
| **证据 tab 的兜底** | `KsEvidenceTab.tsx:683` | `if (ev.rev !== undefined && ev.bbox === undefined)` ⇒ **自己去取 bbox** |

⇒ **所以"能跳转但没箭头"只剩两种可能**（本批都要覆盖）：
- **(a)** 兜底跑了，但 `/ks/bbox` 返回**空**（该条款确实没有 `source_span`，
  例如 docx 直解的文档 —— `docx_ingest.py:60` 明写"无原页，source_spans 空"）；
- **(b)** 兜底**没跑**（`rev` 缺失），或跑了但**箭头被后续重绘清掉**。

⚠ **本批的处置**：把 **①②③ 三环全修**（让 bbox 能一路传到），
并在**取不到时给出可见提示**（既有 `setAnchorWarn` 已实现，措辞已说"只跳页、不画箭头"）。
这样 (a) 类会**明确告诉用户"取不到"**，而不是静默无箭头。

## 诚实边界

1. **引擎当时未运行**（`http://127.0.0.1:7594/api/v1/health` 连接被拒）
   ⇒ 我**没能**做端到端的真机验证；上面全部是**代码级 + 真库级**取证。
2. **真宿主里验不了箭头是否真画出来**：本机 GUI 的会话树渲染不出会话节点
   （见 `UI-BASELINE` §五）。能验到的是"bbox 一路传到了证据 URL"；
   **箭头最终画不画归渲染层**（`KsEvidenceTab` 的 renderPage），那部分有既有判据。
3. `source_span` 的覆盖率**没有全库统计**（只抽样确认有数据、有索引、点查极快）。
   ⇒ "多少条款有 bbox"这个数**未量**，登记为未验。
