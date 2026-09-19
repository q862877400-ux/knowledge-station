# 执行计划（自主执行台账）—— 业主 2026-09-19 全权授权

**怎么用这份文件**：每轮开工先读它 → 按序做 → 收工把该行状态改成「✅ 完成（提交号+快照）」
或「⏸ 待做（原因）」。**它是进度的唯一真源**，细节在各步的归属文档里，不在这里抄。

**纪律（每步都适用）**：小提交 + 快照 `snapshot-project.ps1` + 门禁 `run-gates.ps1 -Full` **退出码为准**（6/6 + 棘轮）
+ 独立复核（冻结 tag + 提取树）；复核打回**就地更正并留痕**；提案前先对 [NOT-DOING](NOT-DOING.md)。
**业主已全权授权**：所有决定自行做出（含重启脚本、UI 截图自检），**不得因无人拍板而停**；
唯一例外：真实世界花钱、对外发布、不可逆删除用户数据。

| 步 | 内容 | 验收（做到什么算完） | 状态 |
|---|---|---|---|
| 1 | **门禁棘轮 v3**：skip 判据的键从 `文件:行号` 换成 pytest **nodeid**（`--junitxml`）；白名单补全；解析不到**报错而非静默丢弃**；删死代码；无基线路径填 `$why` | `-Full` 退出码 0；**变异实测**：① 在 `tests/test_reranker.py` 顶部加一行注释 ⇒ **不再假红**；② 新增一条 skip 站点 ⇒ **报红**；③ junit 缺失/解析空 ⇒ **报错** | ✅ 完成（`2c059cc`）；⚠ 独立复核 v3 抓到**一处假绿**：整块棘轮被 `if ($null -ne $pytestPassed)` 罩住，pytest 输出里没有 `N passed` 时**三条判据一条都不跑**却报 ✅（反例：`PYTEST_ADDOPTS='-p allskip_plugin'` ⇒ 2175 条白名单外新 skip 未被判）⇒ 已修（拿不到数字即判红），见本轮修复提交 |
| 2 | **打包纯度检查**：`build-client.mjs` 不把 `@deepseek-ai/*` 整片 external，改成"基线模块 + 显式白名单"，其余 `onResolve` 抛错 | 冒烟：引一个不在白名单的包 ⇒ 构建**当场失败**；正常构建产物与现在**逐字节一致** | ✅ 完成（`f50aed9`，复核实测 blob `5dccd9de…` 逐字节一致）；⚠ 复核抓到 scope 判定**大小写敏感**的绕过（`@DeepSeek-AI/x` 判 bundle、onResolve filter 不触发）⇒ 已修（折小写 + 非全小写显式抛 + filter 加 `i` + 冒烟 4 条反例 1 条对照） |
| 3 | **三处小清理**：① `S6` 默认值双份（`DEFAULTS` vs schema）② `S1` 的 `sidebar.right.pane.tab.title` 从未注册但注释声称注册 ③ `S2` 该用未用的宿主原语 | 每处要么修好要么删掉错话；门禁全绿；冒烟钉住"注释与代码一致" | ✅ 完成（`f50aed9`）；⚠ 复核抓到 `UI-BASELINE.md` **两处失真**（`FoldToggle` 不在权威面里、原语实数 9 个含 `Switch`）⇒ 已就地更正留痕 |
| 4 | **撤掉 docx/pptx 导出通路**（业主已否决 Word/PPT 交付物）：研究/巡检报告的 `.docx` 落盘、`slide_export`、对应路由/UI/用例；**输入侧 Word 解析保留**、`office_roundtrip` 保留、`.md`/`.html`/`.xlsx` 保留 | 引擎与插件里不再产出 Word/PPT；只出 Markdown；棘轮基线按新总账重记；UI 不再出现下载 Word/PPT 的入口 | ✅ 完成（引擎侧 `c219176` + 插件/测试/文档侧 `2ab66b6`；⚠ 棘轮基线已按新总账重记，见本节末行） |
| 5 | **UI 照 WeKnora 知识库管理复刻**：先建**视觉基线**（参照清单 + 我们的映射表），再逐块落地（尺度系统 → 页面骨架/卡片/列表 → 上传进度 → 多选批量 → 标签 → 命令面板 → 设置形态） | 每一块都**截图自检**（真机 GUI 截图与参照对比），并把截图路径记进文档；门禁含渲染级冒烟 | 🔄 **进行中（5a/5b 完成，5c 待做）**：5a = 尺度 token（`--ks-*`）+ 页面骨架（`9edfebd`）；5b = 据看图查出的行内溢出（「详情」被压成竖排）修掉（`0fbe6af`）；口径与 5c 待办见 [UI 基线](UI-BASELINE.md) 第六节。⚠ **截图口径已变**：宿主 GUI 对我们的浏览器自动化是 **401**（实测），改用**离屏渲染成自包含 HTML → 无头浏览器截图**（工具暂在 `var/tmp/`，**未入库**）。`-Full` 在 `0fbe6af`/`ce2487f` 两次退出码 0。**5c 未做的**：入库面板换成宿主 token（现 21 处硬编码色值）、能力页 4 处字面 `**` 与页标题 14px 不同级、KS_STYLES 17 处不在 4px 网格的 spacing + 2 处 11.5px 字号、kb@1300 空档与死白 |
| 6 | **插件侧借鉴 6 条**（取自 WeKnora 自带的 DSH 插件）：json-schema 三件套+"返回值满足自己声明 schema" 门禁、`output.schema`+`render` 配对、`isConcurrencySafe`、`AbortSignal.any`、fixture 回放、e2e 三段式 | 6 条各有冒烟/用例；e2e 在真宿主里断言"插件挂上 + 工具被 offer + 原文进上下文" | ⏳ |
| 7 | **渠道号段数据轮**：给台账填号段（那 10 条"今天到不了"的渠道接回链），给出"死号段"基线 | `chain-snapshot` 显示号段带来的变化（真库全量）；死号段清单进报告；用例覆盖 | ⏳ |
| 8 | **其余 DSH 适配积压**：`defineTool`（拿回 `presentCall/presentResult`）、`Config` 校验口径、工具注册写法、文档结构拆分、git hook/CI | 逐条做完并留证据；`docs/DSH-ALIGNMENT-AUDIT.md` 积压表同步勾掉 | ⏳ |

**不做（已被业主否决，见 [NOT-DOING](NOT-DOING.md)）**：Word/PPT 交付物、真机录屏/GIF、bbox 高亮（正确做法是**红色定位箭头**）、
通用层自己手搓、客户端多语言（缓办）。

**待业主拍板（唯一保留项）**：无 —— 批量打标签按"**追加 + 单独移除**"做（业主未反对即视为同意）。

---

## 第 4 步施工单（撤掉 Word/PPT 导出；**已执行完毕，2026-09-19**）

**范围裁定（我自己拍的，理由写在这里）**：撤掉 **Word（`.docx`）与 PPT（`.pptx`）的产出通路**；
**保留** `.md`（交付物本体）与 `.html`（界面预览用的渲染形态，不是交付物）；
**保留** `office_roundtrip`（那是"用 Word 编辑条款再回传"的**编辑工具**，不是"交付 Word 文件"——
与"只出 Markdown"不冲突，撤它属于超范围删除）；**保留** 输入侧的 Word 解析
（`docx_adapter` / `docx_ingest`）⇒ `python-docx` **留在依赖里**（施工单原稿写"删 `python-docx`"
是**错的**，执行时已按本节裁定改正）；**`.xlsx` 不在裁决范围内**（裁决说的是 Word/PPT）。

| 面 | 具体位置 | 执行结果 |
|---|---|---|
| 引擎产出 | `src/core/exports/research_report.py`（`.docx` 那一形态 + `_docx_template_path`）、`src/core/exports/slide_export.py`（整个模块删除）、`src/core/exports/report_export.py`（`export_qa_citations_docx` / `export_review_report_docx` / `_open_document` / `_templates_dir`） | ✅ 全部删除；另**超施工单**拆了 `src/core/update/report.py` 的 `export_batch_report`（更新检查报告 Word 版）与 `server.py` 的义务清单 Word 导出——两处都是 docx **产出通路**，按上面的"范围裁定"属该撤之列 |
| 引擎路由 | `src/core/api/routes_report.py`（`/report/research/slides`）、`routes_update.py`（`/update/report/{batch_id}`）、`server.py`（`/export/review/{task_id}`、`/export/obligations/{list_id}`、`/export/citations` 的 docx 落盘） | ✅ 全部删除；`/export/citations` **保留**但只回 `citation_text`（纯文本引用块从来不是 Word 交付物） |
| 依赖 | `pyproject.toml` 的 `python-pptx>=1.0`；⚠ `python-docx>=1.0` **保留**（输入侧 + `office_roundtrip`）；Word COM 的 `pywin32` 保留 | ✅ 只删 `python-pptx` |
| 宿主插件 | `plugin/src/report.js`：`KS_REPORT_SLIDES_PATH` / `registerSlidesRoute` / `ENGINE_SLIDES_PATH` | ✅ 全删（路由 6 → 5） |
| 客户端 | `plugin/client/api.ts`：`KsSlideDeck` / `exportResearchSlides`；调用点 `KsMaterialsPanel.tsx`（`onExportSlides` / 「生成 PPT」按钮 / slides 展示块 / `Deliverables` 里的 Word·PPT 措辞） | ✅ 全删；`client.js` 已按 `build-client.mjs` **重新构建**（它是被跟踪的构建产物，`smoke-client-entry` 要求"与现构建整份一致"） |
| 用例 | `tests/test_slide_export.py`（整个文件）、`test_research_report.py` 的 docx 三条、`test_update_report.py` 的 docx 三条、`test_phase4.py`/`test_phase7.py` 的 Word 断言、`test_material_api.py` 的慢端点表 | ✅ 该删的删；`test_update_report.py` 的 REP-04 与 `test_phase7.py` 的 citations 契约**改成测留存的路径**（没连坐删）；`test_layout_fidelity.py` **实际不含** docx/pptx 断言（施工单点名它与事实不符） |
| 冒烟 | `plugin/scripts/smoke-report-*.mjs` 的 pptx 断言、`smoke-client-entry.mjs`、`smoke-catalog-ui.mjs` | ✅ pptx 断言全删；另加负向断言挡"PPT 接线被写回来" |
| 收尾 | 棘轮基线按**新总账**重记（删用例 ⇒ 总账下降是**预期**）| ✅ 已重记：总账 **2144**（passed 2141 / skipped 3）。⚠ **口径限定（复核 2026-09-20 打回）**：应说"不再有 Word/PPT **交付物**通路"——`POST /clauses/{id}/office-edit` 仍会落 `.docx`（那是裁定**保留**的"用 Word 编辑条款再回传"编辑工具，`office_roundtrip.py` 属输入/编辑侧）。字面写"不再有 Word 产出通路"**不成立**。⚠ 另修两处，且**两处我先前都低报/错判**：① 插件侧误删 `registerResearchRoute` 的真实影响面是**死 2 条路由**（该函数缺失使 `registerDraftRoute` 也挂不上），不是 1 条；② `smoke-chatmode` 的偶发**不是**我先前指认的"裸写 ⇒ 读到半截 JSON ⇒ 拒写"（复核实测：把原子写改回裸写跑 60 次 **0 红**，而原样跑 100 次红 2 次，红的是 `merge keeps the other process's sessions`）⇒ 真机制是**不持锁的写者与 CAS 的 TOCTOU**（`chatmode.js` 落盘在锁内读基线 → CAS → rename；对端 rename 落在 CAS 读与我们的 rename 之间时，用旧基线合并覆盖掉对方会话，而回读校验只看 `touched`）。修法：模块侧回读校验补"基线里有、我们没打算删、回读却没了" ⇒ 判 `retry`；测试侧对端写者改用模块导出的 `__writeStateFileAsPeerForTests`（**同一条锁协议**，不复刻）。复测数字见 [开发史 §10.139](DEVELOPMENT-HISTORY.md) |
