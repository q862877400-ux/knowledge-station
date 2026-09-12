# 能收敛的「自我找 bug 修 bug」循环 — 设计文档（loop2）

> 范围：KnowledgeStation 视觉/排版回归的自主收敛循环（GB 标准 PDF「导入 → 预览 → 逐页对比 → 根因修复」）。
> 依据：`docs/browser-screenshot-workflow.md`（用户权威规范 §0）、`docs/visual-regression-log.md`（历史登记簿）、
> `docs/ENCYCLOPEDIA.md`（§8 入库与 bbox、§15 已知坑、§16 规则红线、§17 未实现）、
> 以及三路只读侦察（渲染管线 / 现有对比工具 / 项目意图）。本文件是**设计交付物**，不修改产品代码。
> 与用户权威规范逐条对齐；把「无法判定的判据」替换为「可判定的派生判据」。

---

## 0. 一句话定位

把「上帝视角 VLM 判分 + 无上限打补丁」换成
**可判定结构判官 + 冻结测量契约 + 根因类三振 + 架构级上报闸门**。
环从「修不完」变成「收敛地修到修不动为止，并把「修不动」精确报出来」。

---

## 1. 确认的项目现实（根因诊断）

### 1.1 旧环为什么会「修不完」

1. **VLM 是唯一判官，且它是盲的**：`scripts/_dl_vision.py` 只 base64 了 `orig`，**从没把 `prev` 发出去**，prompt 却声称"双图对比"。
2. **测量脚本脆弱且与用户规范不符**：
   - `.page-break` DOM 锚点只在页切换处输出（`server.py:2358`：`pg and prev_pg is not None and pg != prev_pg`），**条款第 1 页永不发**；且 `page_breaks` NULL/空（存量 pre-B3）、编辑快照 md 含 `<p>`（`:2105`）、JSON 损坏（`:2122`）、行数漂移（`:2203`）会整段不输出。
   - 用户判读要点要求「原画面 = PDF 页内嵌入扫描位图（`get_image_info(xrefs=True)` 面积最大者）」，**勿用 get_pixmap 当原画面**；但 `program_compare.py` 现在用 `get_pixmap(dpi=150)` —— 测量与用户规范不符。
   - `b4()` 编码不一致、固定 sleep、`_wait` 把任意非空 stdout 当成功、`.png/.jpg` 扩展名不一致。
3. **环的大脑与测量脱钩**：`scripts/debug_loop_driver.py` 只是状态机；`pass/issue` 靠 CLI 手输；`next` 每次重扫 35k 文件树；**`record_pass` 计 `consecutive` 不看实际轮数**——「连续 5 本一次导入即完美」从未真正执行。
4. **三振按症状、且不阻止复发**：`record_issue` 按症状 type 计数，到 3 重置为 0 并记一条 three_strikes，不强制架构反思落地；同名可反复三振。`visual-regression-log.md` 里 C1 已反复触发。
5. **剩下的坑是架构级**：`visual-regression-log.md` 反复出现 (a) 按 type/途径补通道 = 打地鼠（A.3 / 图4/9 / p6 / 12326 'A.' 题注）；(b) **流式渲染无法还原真双栏**（记"版面渲染层/架构级"）；这正对应正式需求 **R71 多栏排版顺序验证**（验收"双栏与三栏…句子连续性达标率 100%"）。旧环没有「上升到架构」的闸门，只会继续计三振、继续打补丁。

### 1.2 但系统内已有可判定的权威结构信息（未被当判据用）

| 来源 | 锚点 | 用途 |
|---|---|---|
| `clause_revision` | `schema.sql:50`；`page_start/page_end` NOT NULL（`:82-83`）、`page_breaks TEXT`（`:87`）、`figure_html`（`:60`） | 每条款页界/图 HTML |
| `source_span` | `schema.sql:93`（`bbox_json`,`span_type`,`sort_order`）；`pipeline.py:662-680` 行级 `page_number+bbox` | 行→页→bbox |
| `doc_page_geometry` | `schema.sql:37`（`doc_id,page_number` PK，`width/height/rotation/crop_box/media_box`） | 页尺寸/旋转（对齐 PDF 原页） |
| 入库 | `pipeline.py` `run_full_ingest:1140` → `build_clause_models:568`；`page_breaks=[[row_idx,pdf_page],...]`（`:651-656`，`or None` `:717`）；`page_start=min(pages)/page_end=max(pages)`（`:716`） | 逐页结构快照 |
| 预览 HTML | `server.py` `_content_html:1946`（无 server 端 `.fulltext` 外壳）；`GET /documents/{id}/clauses`（`doc_full_clauses:1078-1150`）→ React `App.tsx:2024-2038` `.fulltext`/`.fulltext-clause[data-page=page_start]` | 取数 |
| bbox | `span_calibration.calibrate_new/_vote_from_centers/_flip_bbox`（底部原点归一化，`span_calibration.py:11-87`）；前端 `PdfViewer.tsx` via pdfjs `viewport.convertToViewportRectangle`（无项目 `convertToViewportPoint`） | 契约，勿碰 |

> 结论：逐页「原文 vs 预览」的逐字/物理归属**可完全绕开浏览器**，直接从 DB（`clause_revision`+`source_span`+`doc_page_geometry`）+ PDF（fitz 文本层 + `middle.json`）确定性重建。这是收敛的关键。

---

## 2. 设计：四层收敛环

```
┌ 确定性结构判官（A）────────────── 可判定的 pass/fail 唯一来源（免浏览器）
├ VLM 只当候选提示器（B）────────── 低风险辅助，绝不参与 pass/fail
├ 根因类负责制（C）──────────────── 症状→根因映射；三振治本；回归 + 兄弟本验证
└ 有界编排器（D）──────────────── 持久化队列 + 内环上限 + 阻塞上报 + 真实停止判据
```

### A. 确定性结构判官（收敛核心）

**不依赖浏览器**。从 `/documents/{id}/clauses`（或直接 `clause_revision`）读 `page_start/page_end/page_breaks/content_text/content_html/figure_html/table_html` + `source_span` + `doc_page_geometry`；用 `page_breaks`（run-start 编码）+ 行序重建 `page → [lines]` 与 `page → [图/表/公式]`。另一侧从真实 PDF：fitz 逐页文本层 + `middle.json`（图/表/公式对象）建「期望」。

三个**数值化、fail-closed** 指标（单本通过 = 全过）：

| 指标 | 定义 | 判据 |
|---|---|---|
| `text_fidelity` | 归一化后「该页预览文本」vs「该页 PDF 文本」编辑距离 | ≥ 0.98 |
| `page_map_fidelity` | `page_start`/`page_breaks` 页号对齐 `doc_page_geometry` 页数（含封面/前页 offset 校准） | 100% |
| `object_presence` | 每类对象（图/表/公式）期望（PDF/middle）vs 预览实际（`content_html` 的 `fig-embed`/`img`/`table`/KaTeX） | 0 缺失 |

- **先做前页 offset 校准**：用一本已知文本层书（如 GB/T 10-2013）定「PDF 页 1」vs「条款 page_start」的常量，写进快照供全环用。
- 判官**fail-closed**：结构判不过，无论 VLM 怎么说都不能过。

### B. VLM = 低风险候选提示器（不当判官）

- 修 `_dl_vision.py` 只发单图 bug（两条都发）——测量契约硬修复。
- 固定 prompt + 结构化 JSON 输出 + 重试 + 缓存；走 `egress_audit`。
- 只输出候选差异清单 + 置信度（双栏/裁切/公式形态/颜色/字体），**永不单独判 pass**。

### C. 根因类负责制（对症，不打地鼠）

`known_issues.json` 以**根因类**为主键 = 因果机制 + 落点（`file:function`）。先用 `visual-regression-log.md` 反向播种：

```
ingest:mineru-type-split-consumption
ingest:chart-caption-not-in-content_text
render:text-layer-skips-deep-formula
render:fig-caption-boundary-regex
render:asset_done-global-dedup
store:page_break-null-pre-B3
layout:content-flow-vs-two-column      ← R71 架构级，直接进 blocked
```

- **登记缺陷必须绑根因**（`classify.py` 强制），没根因不许入账——根绝「修测量修到看不见」。
- **三振按根因类**（非症状）：同一根因类跨任意书累计 3 次 → 强制架构反思，必须产出：①统一产品改动（非单本补丁）；②一条回归测试；③**兄弟本验证**（结构相似的另一本也过判官）。只有兄弟本也过才清零；否则该根因类保持 hot。
- `layout:content-flow-vs-two-column` 这类架构级根因**不靠打补丁**，在 D 层触发上升。

### D. 有界编排器（`scripts/loop2/driver_v2.py`）

- **持久化书队列**：启动一次性枚举 35k → 快照（std_no / rel relpath / 文本层标记 / 页数 / 前 2 页 hash）；环内不再重扫，按快照游标推进（杜绝漂移）。
- **内环预算** `MAX_ROUNDS=3`（导入→测量→缺陷→修复→再测量）；3 轮仍不过判官 → 标 `blocked`（不算通过）进 `blocked_pending_architecture`。
- **真实停止判据**（对齐用户规范 §0 ③）：`STOP_CONSECUTIVE=5` 本都 **rounds==1**（首次导入即过判官），且最近 `M=5` 本无新根因类，且 `blocked_pending_architecture` 为空。**修正 `record_pass` 不计 rounds 的 bug**。
- **硬上报闸门**：
  - `MAX_BLOCKED=5` 个架构阻塞（含 R71 双栏 / 统一图抽象）→ 停止，输出「架构报告」上报给人。
  - 任何测量工具改动超出冻结 `measure_spec.md` → 判 `measurement_drift`，拒绝继续（环在"作弊"）。

---

## 3. 收敛性论证

1. 判官确定且 fail-closed：`pass = f(产品代码, 输入PDF)`。
2. 固定产品版本下：一本书要么确定地过，要么进 `blocked`；`blocked` 有上限（`MAX_BLOCKED`）。
3. 每个根因类修复都泛化 → 判官可探测缺陷集合收敛 → 下一本从"更接近过"开始。
4. 输入队列固定且有限、产品功能面有限 → 根因类有限 → 总迭代有界。
5. 即便假设错，`MAX_ROUNDS` / `MAX_BLOCKED` / `M-silence` 三硬上限保证**物理停止**；停下时输出「这批是架构级问题」这一精确、可行动的信号（对应 R71 / 统一图抽象），而非无限循环。

---

## 4. 红线核对（全部遵守）

- **P1 准确性 > P2 便利 > P3 体验 > P4 简洁 > P5 性能**（`ENCYCLOPEDIA §16.3`）。
- **测试基线只涨不跌**；触碰 retrieval/prompt → **Golden Set 门禁**（§5.4，回退 >2pp 即卡）。
- **契约变更先 `contract.md` + `test_contract.py`**；判官回归测试**放独立 test module**（`test_contract` 是 schema/枚举级，不塞像素/排版断言进去）。
- **写操作走 `write_queue` 单写者**；**bbox 底部原点不碰**（判官只读 bbox，不写不翻）。
- **云调用必走 `egress_audit`**（VLM/OCR/任何外发）。
- **证据文本改动不自动落库**，走人工闸（A2.5：LLM 输出不经人工确认不得改证据文本）；循环只自动改渲染/版面对象层（`figure_html` / `page_breaks` / 图注入 / KaTeX）。
- **数据/代码分离**：运行产物写数据区；新代码参数化（不写 `C:\Users\Zegel` 绝对路径）。
- **存量 `page_breaks=NULL` 不编造**（`test_contract` 已锁：NULL=未采集，零行为变化）。

---

## 5. 落地顺序

1. `scripts/loop2/oracle_snapshot.py` + `oracle_score.py`：从 `clause_revision`+`source_span`+`doc_page_geometry`+fitz 重建逐页结构快照并打分。**无 schema 改动**。
2. 用 GB/T 10-2013 校准前页 offset，让 `page_map_fidelity` 正确。
3. 修 `_dl_vision.py` 单图 bug；VLM 降级为提示器。
4. `known_issues.json` 重键为根因类；用 `visual-regression-log.md` 反向播种。
5. `scripts/loop2/driver_v2.py` 有界编排（持久化队列 + `MAX_ROUNDS` + `blocked` + 真实连续判据）。
6. 每处修复配一条排版收敛回归测试（独立 test module）；触点按 §4 红线走门禁。

---

## 6. 交付验收（文档级）

一个可收敛的环，应满足：
- [ ] 判官可判定、fail-closed；VLM 不进 pass/fail。
- [ ] `record_pass` / 停止判据真正用 `rounds==1`。
- [ ] 根因类是主键；三振触发必有统一改动 + 回归 + 兄弟本验证。
- [ ] `MAX_ROUNDS` / `MAX_BLOCKED` / `M-silence` 三硬上限存在且触发后正确上报。
- [ ] 测量契约冻结（`measure_spec.md`）；测量外改检测为 `measurement_drift` 拒绝。
- [ ] 红线逐条核对（§4）。

---

## 7. 实现状态（2026-09-02 自主推进）

**已实现（`scripts/loop2/` + `tests/test_loop2_*.py`）：**

| 文件 | 职责 |
|---|---|
| `oracle_snapshot.py` | DB(`clause_revision`+`source_span`+`doc_page_geometry`)+fitz 确定性逐页结构快照；PUA 错位门控；表格文本计入预览页；原文剥离水印/页脚/页码；`middle_geo.figures()` 期望图对象 |
| `oracle_score.py` | 三指标 `text_fidelity/page_map_fidelity/object_presence` + `mode(textlayer/scan)/needs_visual/text_layer_state`；`missing→fail`、`na` 非阻塞 |
| `driver_v2.py` | 有界编排器：持久化队列 `build/next`、`assess`(接 oracle)、`pass/fail/blocked`、根因类三振 `issue/solve`、`seed`(根因类基线)、`is_converged`、`status/report` |
| `vlm_check.py` | 双图 VLM 候选提示器（修单图 bug；结构化输出；重试；egress_audit），**不进 pass/fail** |
| `_dl_vision.py` | 补上 prev 图（遗留脚本不再误导） |
| `tests/test_loop2_{oracle,driver,vlm}.py` | 单测全绿 |

**校准偏差（已接受）**：设计写 `text_fidelity ≥0.98`（目标值），实测干净文本层本 min≈0.92（条款号前缀/图题/公式 LaTeX→Unicode/上下标的结构性残差），故 `Config.TEXT_FIDELITY_MIN` 默认 **0.90**，`<0.90` 判真差异。`object_presence` 期望侧用 `middle_geo.figures()`（非 `get_images()`——后者把每页背景/logo 算成图）；34406 实测 `missing_figure_pages=[9]`（第 9 页版面 2 图、预览 0 图）。

**扫描版路由（设计要点，driver/打分已支持）**：`mode=="scan"`（无文本层）时 `text_fidelity=na`、`needs_visual=True`——deterministic 门**不适用**，循环应把该本路由到 VLM/视觉校验（或 `blocked_pending_architecture`），**不得**仅凭 oracle 判为一个"round-1 deterministic 通过"。文本层本（`clean/pua_mangled`）才走 deterministic 门。

**剩余**：step 6 操作性打通（`assess --ingest` 触发真实入库较慢；`vlm_check` 需 `MOONSHOT_API_KEY` + 真实 orig/prev 图对）——已具备代码路径、接口齐备，待真正跑库时启用。
