# 执行计划（自主执行台账）—— 业主 2026-09-19 全权授权

**怎么用这份文件**：每轮开工先读它 → 按序做 → 收工把该行状态改成「✅ 完成（提交号+快照）」
或「⏸ 待做（原因）」。**它是进度的唯一真源**，细节在各步的归属文档里，不在这里抄。

**纪律（每步都适用）**：小提交 + 快照 `snapshot-project.ps1` + 门禁 `run-gates.ps1 -Full` **退出码为准**（6/6 + 棘轮）
+ 独立复核（冻结 tag + 提取树）；复核打回**就地更正并留痕**；提案前先对 [NOT-DOING](NOT-DOING.md)。
**业主已全权授权**：所有决定自行做出（含重启脚本、UI 截图自检），**不得因无人拍板而停**；
唯一例外：真实世界花钱、对外发布、不可逆删除用户数据。

| 步 | 内容 | 验收（做到什么算完） | 状态 |
|---|---|---|---|
| 1 | **门禁棘轮 v3**：skip 判据的键从 `文件:行号` 换成 pytest **nodeid**（`--junitxml`）；白名单补全；解析不到**报错而非静默丢弃**；删死代码；无基线路径填 `$why` | `-Full` 退出码 0；**变异实测**：① 在 `tests/test_reranker.py` 顶部加一行注释 ⇒ **不再假红**；② 新增一条 skip 站点 ⇒ **报红**；③ junit 缺失/解析空 ⇒ **报错** | ⏳ |
| 2 | **打包纯度检查**：`build-client.mjs` 不把 `@deepseek-ai/*` 整片 external，改成"基线模块 + 显式白名单"，其余 `onResolve` 抛错 | 冒烟：引一个不在白名单的包 ⇒ 构建**当场失败**；正常构建产物与现在**逐字节一致** | ⏳ |
| 3 | **三处小清理**：① `S6` 默认值双份（`DEFAULTS` vs schema）② `S1` 的 `sidebar.right.pane.tab.title` 从未注册但注释声称注册 ③ `S2` 该用未用的宿主原语 | 每处要么修好要么删掉错话；门禁全绿；冒烟钉住"注释与代码一致" | ⏳ |
| 4 | **撤掉 docx/pptx 导出通路**（业主已否决 Word/PPT 交付物）：研究/巡检报告的 `.docx` 落盘、`slide_export`、`office_roundtrip`、对应路由/UI/用例/依赖；**输入侧 Word 解析保留** | 引擎与插件里不再产出 Word/PPT；只出 Markdown；棘轮基线按新总账重记；UI 不再出现下载 Word/PPT 的入口 | ⏳ |
| 5 | **UI 照 WeKnora 知识库管理复刻**：先建**视觉基线**（参照清单 + 我们的映射表），再逐块落地（尺度系统 → 页面骨架/卡片/列表 → 上传进度 → 多选批量 → 标签 → 命令面板 → 设置形态） | 每一块都**截图自检**（真机 GUI 截图与参照对比），并把截图路径记进文档；门禁含渲染级冒烟 | ⏳ |
| 6 | **插件侧借鉴 6 条**（取自 WeKnora 自带的 DSH 插件）：json-schema 三件套+"返回值满足自己声明 schema" 门禁、`output.schema`+`render` 配对、`isConcurrencySafe`、`AbortSignal.any`、fixture 回放、e2e 三段式 | 6 条各有冒烟/用例；e2e 在真宿主里断言"插件挂上 + 工具被 offer + 原文进上下文" | ⏳ |
| 7 | **渠道号段数据轮**：给台账填号段（那 10 条"今天到不了"的渠道接回链），给出"死号段"基线 | `chain-snapshot` 显示号段带来的变化（真库全量）；死号段清单进报告；用例覆盖 | ⏳ |
| 8 | **其余 DSH 适配积压**：`defineTool`（拿回 `presentCall/presentResult`）、`Config` 校验口径、工具注册写法、文档结构拆分、git hook/CI | 逐条做完并留证据；`docs/DSH-ALIGNMENT-AUDIT.md` 积压表同步勾掉 | ⏳ |

**不做（已被业主否决，见 [NOT-DOING](NOT-DOING.md)）**：Word/PPT 交付物、真机录屏/GIF、bbox 高亮（正确做法是**红色定位箭头**）、
通用层自己手搓、客户端多语言（缓办）。

**待业主拍板（唯一保留项）**：无 —— 批量打标签按"**追加 + 单独移除**"做（业主未反对即视为同意）。

---

## 第 4 步施工单（撤掉 Word/PPT 导出；**已完成的侦察**）

**范围裁定（我自己拍的，理由写在这里）**：撤掉 **Word（`.docx`）与 PPT（`.pptx`）的产出通路**；
**保留** `.md`（交付物本体）与 `.html`（界面预览用的渲染形态，不是交付物）；
**保留** `office_roundtrip`（那是"用 Word 编辑条款再回传"的**编辑工具**，不是"交付 Word 文件"——
与"只出 Markdown"不冲突，撤它属于超范围删除）；**输入侧**的 Word 解析（`docx_adapter`/`docx_ingest`）当然保留。

| 面 | 具体位置 |
|---|---|
| 引擎产出 | `src/core/exports/research_report.py`（`.docx` 那一形态 + `_docx_template_path`）、`src/core/exports/slide_export.py`（整个模块删除）、`src/core/exports/report_export.py`（`export_qa_citations_docx` / `export_review_report_docx` / `_open_document`） |
| 引擎路由 | `src/core/api/routes_report.py`、`src/core/api/routes_update.py`、`src/core/api/server.py` 里对应端点（`/report/research/slides`、docx 导出） |
| 依赖 | `pyproject.toml` 的 `python-docx>=1.0`、`python-pptx>=1.0`（⚠ Word COM 的 `pywin32` 属输入侧，保留） |
| 宿主插件 | `plugin/src/report.js`：`KS_REPORT_SLIDES_PATH` / `registerSlidesRoute` / `ENGINE_SLIDES_PATH`；既有 docx 形态的注释与错峰 |
| 客户端 | `plugin/client/api.ts`：`KsSlideDeck` / `exportResearchSlides` / `.docx` 相关类型与注释；调用点（下一步先 grep 出全部调用点） |
| 用例 | `tests/test_research_report.py`（docx 部分）、`tests/test_slide_export.py`（整文件）、`tests/test_update_report.py`、`tests/test_layout_fidelity.py` 里 docx/pptx 断言；`plugin/scripts/smoke-report-*.mjs` 里的 pptx 断言 |
| 收尾 | 棘轮基线按**新总账**重记（删用例 ⇒ 总账下降是**预期**，`-UpdateBaseline` 一次并说明原因）；`docs/NOT-DOING.md` 第 1 条的"待撤"改成"已撤（提交号）" |
