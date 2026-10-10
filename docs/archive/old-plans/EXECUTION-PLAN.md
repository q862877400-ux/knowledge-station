# 执行计划（自主执行台账）—— 业主 2026-09-19 全权授权

**怎么用这份文件**：每轮开工先读它 → 按序做 → 收工把该行状态改成「✅ 完成（提交号+快照）」
或「⏸ 待做（原因）」。**它是进度的唯一真源**，细节在各步的归属文档里，不在这里抄。

**纪律（每步都适用）**：小提交 + 快照 `snapshot-project.ps1` + 门禁 `run-gates.ps1 -Full` **退出码为准**（6/6 + 棘轮）
+ 独立复核（冻结 tag + 提取树）；复核打回**就地更正并留痕**；提案前先对 [NOT-DOING](../../NOT-DOING.md)。
**业主已全权授权**：所有决定自行做出（含重启脚本、UI 截图自检），**不得因无人拍板而停**；
唯一例外：真实世界花钱、对外发布、不可逆删除用户数据。

| 步 | 内容 | 验收（做到什么算完） | 状态 |
|---|---|---|---|
| 1 | **门禁棘轮 v3**：skip 判据的键从 `文件:行号` 换成 pytest **nodeid**（`--junitxml`）；白名单补全；解析不到**报错而非静默丢弃**；删死代码；无基线路径填 `$why` | `-Full` 退出码 0；**变异实测**：① 在 `tests/test_reranker.py` 顶部加一行注释 ⇒ **不再假红**；② 新增一条 skip 站点 ⇒ **报红**；③ junit 缺失/解析空 ⇒ **报错** | ✅ 完成（`2c059cc`）；⚠ 独立复核 v3 抓到**一处假绿**：整块棘轮被 `if ($null -ne $pytestPassed)` 罩住，pytest 输出里没有 `N passed` 时**三条判据一条都不跑**却报 ✅（反例：`PYTEST_ADDOPTS='-p allskip_plugin'` ⇒ 2175 条白名单外新 skip 未被判）⇒ 已修（拿不到数字即判红），见本轮修复提交 |
| 2 | **打包纯度检查**：`build-client.mjs` 不把 `@deepseek-ai/*` 整片 external，改成"基线模块 + 显式白名单"，其余 `onResolve` 抛错 | 冒烟：引一个不在白名单的包 ⇒ 构建**当场失败**；正常构建产物与现在**逐字节一致** | ✅ 完成（`f50aed9`，复核实测 blob `5dccd9de…` 逐字节一致）；⚠ 复核抓到 scope 判定**大小写敏感**的绕过（`@DeepSeek-AI/x` 判 bundle、onResolve filter 不触发）⇒ 已修（折小写 + 非全小写显式抛 + filter 加 `i` + 冒烟 4 条反例 1 条对照） |
| 3 | **三处小清理**：① `S6` 默认值双份（`DEFAULTS` vs schema）② `S1` 的 `sidebar.right.pane.tab.title` 从未注册但注释声称注册 ③ `S2` 该用未用的宿主原语 | 每处要么修好要么删掉错话；门禁全绿；冒烟钉住"注释与代码一致" | ✅ 完成（`f50aed9`）；⚠ 复核抓到 `UI-BASELINE.md` **两处失真**（`FoldToggle` 不在权威面里、原语实数 9 个含 `Switch`）⇒ 已就地更正留痕 |
| 4 | **撤掉 docx/pptx 导出通路**（业主已否决 Word/PPT 交付物）：研究/巡检报告的 `.docx` 落盘、`slide_export`、对应路由/UI/用例；**输入侧 Word 解析保留**、`office_roundtrip` 保留、`.md`/`.html`/`.xlsx` 保留 | 引擎与插件里不再产出 Word/PPT；只出 Markdown；棘轮基线按新总账重记；UI 不再出现下载 Word/PPT 的入口 | ✅ 完成（引擎侧 `c219176` + 插件/测试/文档侧 `2ab66b6`；⚠ 棘轮基线已按新总账重记，见本节末行） |
| 5 | **UI 照 WeKnora 知识库管理复刻**：先建**视觉基线**（参照清单 + 我们的映射表），再逐块落地（尺度系统 → 页面骨架/卡片/列表 → 上传进度 → 多选批量 → 标签 → 命令面板 → 设置形态） | 每一块都**截图自检**（⚠ **口径更正（复核 ui5 2026-09-20）**：**不是**"真机 GUI 截图"——宿主 GUI 对我们的浏览器自动化是 **401**（实测），实际走的是**离屏渲染成自包含 HTML → 无头浏览器截图 + 量几何**；正式步骤与工具表见 [UI 基线](../../UI-BASELINE.md) 第五节）并与参照对比，把截图路径记进文档；门禁含渲染级冒烟 | 🔄 **进行中（5a/5b/5c 完成，5d=本轮复核打回的行高对齐）**：5a = 尺度 token（`--ks-*`）+ 页面骨架（`9edfebd`）；5b = 据看图查出的行内溢出（「详情」被压成竖排）修掉（`0fbe6af`）；5c = 入库面板换宿主 token + 能力页/知识库页字面 `**` + 尺度棘轮 + 截图工具入库（`d5366bd`）；5d = `.ks-item` 加 `box-sizing:border-box`（实测行高 44 / 节距 52）。口径与各块记录见 [UI 基线](../../UI-BASELINE.md) 第六节。⚠ **截图口径已变**：宿主 GUI 对我们的浏览器自动化是 **401**（实测），改用**离屏渲染成自包含 HTML → 无头浏览器截图**（工具已入库到 `plugin/scripts/`）。`-Full` 在 `0fbe6af`/`ce2487f` 两次退出码 0。**5c 那批（当时列在"未做"里）现已全部落地**：入库面板换宿主 token（21 处硬编码 → 0）、能力页/知识库页字面 `**`（⚠ `ui-audit.mjs` B 段**仍会把注释里的解释性 `**` 计入**——那是该段的已知上界，非上屏文本）、KS_STYLES 离网格 spacing 17→0 与现场字号 13→0、kb@1300 死白归 8px（详见 [UI 基线](../../UI-BASELINE.md) 第六节 5c）。 |
| 6 | **插件侧借鉴 6 条**（取自 WeKnora 自带的 DSH 插件）：json-schema 三件套+"返回值满足自己声明 schema" 门禁、`output.schema`+`render` 配对、`isConcurrencySafe`、`AbortSignal.any`、fixture 回放、e2e 三段式 | 6 条各有冒烟/用例；e2e 在真宿主里断言"插件挂上 + 工具被 offer + 原文进上下文" | ⏳ |
| 7 | **渠道号段数据轮**：给台账填号段（那 10 条"今天到不了"的渠道接回链），给出"死号段"基线 | `chain-snapshot` 显示号段带来的变化（真库全量）；死号段清单进报告；用例覆盖 | 🔄 **量测完成·裁定不填（验收项①按证据作废，待业主追认）**（⚠ **状态降级（复核 r7 2026-09-20）**：这里原是 **✅**，属"**未经业主追认就把验收判为不该做**"——原 ✅ 会让状态列读成"第 7 步做完了"，而**验收三项里 1/3 未达成**：①"chain-snapshot 显示号段带来的**变化**"**未达成**（实测变化 **0**，`unreachable_no_segments` 仍 **10** ⇒ 原目标"接回链"没实现）；②"死号段清单进报告"只有**机制**、**清单为空**；③"用例覆盖"达成。裁定与依据见 [渠道覆盖方案](../../CHANNEL-COVERAGE-PLAN.md) 的 R7-数据轮）**：`chain-snapshot` 基线复测 = 真库 **6417** 号 / 台账 131 条 / **零号段声明 ⇒ 带来 0 个号** / 死号段 **0**；逐条量出"能填的（`cssn`/`mohurd`，覆盖 GB）**证据不足且与 **R6g** 定的"按类补探"（出自 **R6c-6**）结论冲突**、覆盖清楚的（6 条非国标 + `laws_db`）**库里一个号都没有 ⇒ 填了就是死号段**（⚠ `laws_db` 那条**已被 r7 复核证伪**：它是"活但语义荒谬"，见归属文档）"⇒ 一条都不填（**没填 ≠ 没做完**：验收的"填号段"按本轮证据**裁定为不该做**，已在文档里留依据与可复核判据）。用例 **+2**（`test_channel_repo.py` 种子契约 2 条：形状/大小写/适配器存在、**已声明号段不许是死号段**；`test_ledger_chain.py` 死号段**后果**断言是**改**不是加——pytest 收集函数 **34 → 36**）；**数据文件一字未改** |
| 8 | **其余 DSH 适配积压**：`defineTool`（拿回 `presentCall/presentResult`）、`Config` 校验口径、工具注册写法、文档结构拆分、git hook/CI | 逐条做完并留证据；`../research-process/DSH-ALIGNMENT-AUDIT.md` 积压表同步勾掉 | ⏳ |

**不做（已被业主否决，见 [NOT-DOING](../../NOT-DOING.md)）**：Word/PPT 交付物、真机录屏/GIF、bbox 高亮（正确做法是**红色定位箭头**）、
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
| 收尾 | 棘轮基线按**新总账**重记（删用例 ⇒ 总账下降是**预期**）| ✅ 已重记：总账 **2144**（passed 2141 / skipped 3）（⚠ **时点说明**：这是**第 4 步当时**的账；**今天**（HEAD `d49b1ac`）是 **2146（2143 passed / 3 skipped）**、`smoke` 全链 **29 套** —— 出处 `scripts/gates-baseline.json` 与 `plugin/scripts/smoke-all.mjs` 的 `SUITES` 实数；别再把这一行当"当前值"抄）。⚠ **口径限定（复核 2026-09-20 打回）**：应说"不再有 Word/PPT **交付物**通路"——`POST /clauses/{id}/office-edit` 仍会落 `.docx`（那是裁定**保留**的"用 Word 编辑条款再回传"编辑工具，`office_roundtrip.py` 属输入/编辑侧）。字面写"不再有 Word 产出通路"**不成立**。⚠ 另修两处，且**两处我先前都低报/错判**：① 插件侧误删 `registerResearchRoute` 的真实影响面是**死 2 条路由**（该函数缺失使 `registerDraftRoute` 也挂不上），不是 1 条；② `smoke-chatmode` 的偶发**不是**我先前指认的"裸写 ⇒ 读到半截 JSON ⇒ 拒写"（复核实测：把原子写改回裸写跑 60 次 **0 红**，而原样跑 100 次红 2 次，红的是 `merge keeps the other process's sessions`）⇒ 真机制是**不持锁的写者与 CAS 的 TOCTOU**（`chatmode.js` 落盘在锁内读基线 → CAS → rename；对端 rename 落在 CAS 读与我们的 rename 之间时，用旧基线合并覆盖掉对方会话，而回读校验只看 `touched`）。修法：模块侧回读校验补"基线里有、我们没打算删、回读却没了" ⇒ 判 `retry`；测试侧对端写者改用模块导出的 `__writeStateFileAsPeerForTests`（**同一条锁协议**，不复刻）。复测数字见 [开发史 §10.140](../../DEVELOPMENT-HISTORY.md)（⚠ **更正（复核 r2 2026-09-20 C11）**：这里原来引的是 **§10.139**，而那张复测表在 **§10.140**；`smoke-chatmode.mjs` 头注同错，已一并改对） |

---

## 收尾状态（2026-09-20，自主执行轮次的交接说明）

**门禁**：`pwsh -File scripts/run-gates.ps1 -Full` ⇒ **退出码 0**，6/6 步通过（tsc 0 / mypy 0 / verify:commands 0 /
smoke 全链 0 / pytest `passed=2143 skipped=3`（总账 **2146**）/ 引擎门禁 0，棘轮 ✅）。
快照：`step-189-step6-fixtures` 及之后的 `step-190`；冻结 tag 见下。

| 步 | 状态 | 说明（证据指向） |
|---|---|---|
| 1 棘轮 v3 | ✅ | 键改 pytest **nodeid**；复核抓到"没跑出 `N passed` 却报绿"的假绿 ⇒ 已改成判红；绿灯也留证（`%TEMP%\ks-gates-last.txt`） |
| 2 打包纯度 | 🔄 | 只允许"基线模块 + 显式白名单"；复核三轮各抓到一个绕过（**大小写** → **分隔符/`..`** → **相对/绝对路径指向宿主单例**）⇒ 逐轮修掉，冒烟 35 → 45 → 59 → **81/81**（含真 esbuild 两向断言）。⚠ **第四轮的"已修"被第五轮复核证伪（只修了冒烟里那两条写法）** ⇒ 第五轮**从根上改**：不再看文本，改成 `build.resolve()` 让 esbuild 自己解析、按**真实落点 + realpath** 判（8 条变体：多级上跳 / 8.3 短名 / 尾随点 / junction / 相对+绝对 react 全部被拦），并补**变异测试**证明断言有牙（去掉接线 ⇒ 80/81 FAIL）。⚠ 仍**盖不到**：把宿主单例**拷进源码树**做第二份实现；"源码里写错包名"的静态扫描（两条都写在 lib 的"盖不到的地方"段） |
| 3 三处清理 | ✅ | 默认值双份 / 从未注册的 tab.title / 该用未用的原语（含 `UI-BASELINE` 两处失真更正） |
| 4 撤 Word/PPT 产出通路 | ✅ | 引擎 + 插件 + 测试 + 文档；口径限定为"**交付物**通路"（`office-edit` 仍落 .docx，是保留的编辑工具）；误删的 `registerResearchRoute` 已恢复（**实际死 2 条路由**） |
| 5 UI 照 WeKnora 复刻 | 🔄 | 5a 尺度 token + 页面骨架；5b 行内溢出；5c 入库面板换宿主 token（21 处硬编码 → 0）+ 能力页 4 处字面 `**` + 尺度棘轮冒烟；5d 行高 `box-sizing` 修正（实测 44/52，浅色深色、520/1300 四组一致）。**未做**：Materials/Evidence/Channels/Settings 四个老面板里约 50 处同类字面 `**`、命令面板、上传进度浮层、多选/标签抽屉、设置形态。**截图口径**：宿主 GUI 对未授权浏览器 **401** ⇒ 走离屏渲染 + 无头截图（工具已入库 `plugin/scripts/ui-render-shot.mjs` 等） |
| 6 插件侧借鉴 6 条 | 🔄（A/B 批完成） | 施工单 `docs/research/STEP6-WORKORDER.md` 把六条**重新裁定**：①该做但**弃抄** WK 校验器（DSH 宿主机已自动校验）、②半条不该做（配对已存在）、③`isConcurrencySafe` 已做（5 个只读工具声明 true，`ks_collect` 故意不声明）、④**"照抄 `AbortSignal.any`"不该做**（DSH 同位点刻意避免）但同节两个真缺陷已修（监听泄漏、取消/超时不可分辨）、⑤**wire fixture 回放已做**（9 条 calls / 8 场景 / 14 断言，10 个变异全红）、⑥e2e 三段式**未做**（最贵，且必须用临时 profile —— 线上 `web` profile 装的是 `link:C:/Users/Zegel/dsh-ks-src/ks-dsh-plugin`，不是本仓） |
| 6 附 | ⏳ | ⚠ **第 6 步 B 批的 `ks_answer` 声明可并行是唯一有争议的判定**（引擎单进程时是"慢"不是"错"，但同轮两条会让第二条在排队中消耗自己的 120s 预算）——复核若不同意，删那一行即可 |
| 7 号段数据轮 | 🔄 **待业主追认** | 量测裁定"**十条一条都不填**"（库内 6417 个号只有国标号；非国标号段必然是死号段）⇒ 验收三项里 **①"chain-snapshot 显示号段带来的变化"未达成（实测变化 0、`unreachable_no_segments` 仍 10）**、②死号段清单为空、③用例覆盖达成。**这是把业主的验收项按证据判为不该做 ⇒ 必须由业主追认**。另：复核**证伪**了"`laws_db` 任何前缀都会造死号段"（`["中华"]` 命中 1 个 ⇒ "**活但语义荒谬**"），⇒ 已登记待办"号段命中量与覆盖声明量级不符要告警"（**只登记、未实现**） |
| 8 其余 DSH 适配积压 | ⏳ 未开始 | `defineTool`（拿回 `presentCall/presentResult`）、`Config` 校验口径、文档结构拆分、git hook/CI |

**明确未修 / 未验（不许当成已解决）**
1. **不持锁的写者仍可能整批会话被静默覆盖**（`plugin/src/chatmode.js` 的落盘协议）：复核已用确定性手法复现（把 CAS→rename 窗口拉宽 400ms + 一个不持锁的对端写入 ⇒ `persisted:true` 但对端会话消失）。`lostPeer` 判据**盖不到**它（对端写在我们基线读之后）。修法候选（锁文件作为唯一写入口 + 版本令牌）**未实施**。
2. 第 6 步 §4 的 `isConcurrencySafe` 与取消语义**未在真宿主里端到端验过**（属第 6 条 e2e）。
3. `test_deep_server` 那条偶发的**根因仍未定**（"自旋饿死 daemon"的假说已被实测否证）。
4. 棘轮对 `passed → skipped` 翻转**本来就不判**（脚本自认；实测出现过 `2140/4` 仍判 ✅）。
5. 最后一批（`be87f68`..`7c6d9df`，5 个提交：纯度相对路径空洞、`chain-snapshot --json` 的 segments、§10.141 与 B1–B5 文档更正）**门禁绿但尚未派独立复核**（上一批的复核报告 `corr3` 已逐条落地）。

**需要业主拍板的（只有两件）**
- 第 7 步的**验收项①**按证据作废是否追认（不追认则要真机 A/B：`cssn`/`mohurd` 能否答出 `official_gb`+`ndls` 答不出的东西，需联网）。
- `--ks-fs-2xs:10px`（受限字号表唯一例外）与 `.ks-guide-main` 从"逐字抄宿主 14px"改成 12px 这两处**取舍**是否接受。
