# 等待期前台提示：现状盘点 + 外部借鉴（只分析，未改代码）

> 业主原话：「思考时间长没问题，就是前台人可能以为卡死了，看看现有的好不好加个提示」
> 任务性质：纯分析。本轮**没有**改任何前端代码（见文末 §7 诚实声明）。

## 一句话结论

**要补的只有一处**：知识库页的提问面板（`plugin/client/KsKnowledgePage.tsx`，`askPhase === 'running' ? '在问…'`）——它是全仓唯一一个「每题固定等 22–37 秒、却只显示三个静态字符、既无时间感也无法取消」的地方；其余等待面要么本来就短（毫秒级本地路由）、要么已经有真进度条/真数字/时长区间，加计时纯属多余。**引擎侧已经有流式能力，但前端一条都没接**（§5 单独标出）。

## 五条要点

1. **「完全没时间感」这个前提不成立**。宿主对话区（模型回答那个气泡）**已经有秒级计时**：`chat.deepDivingFor` = `"深度求索中，用时 {duration} ···"`，每 `LIVE_RUN_CLOCK_INTERVAL_MS = 1e3` 刷新一次。缺的是**我们自己渲染的面板**里没有，以及宿主那个计时只有一行小字、不解释在等什么。
2. **宿主的「停止生成」已经能取消 ks_answer**：宿主有 `"input.stop": "停止生成"`，而工具层把 `exec.signal` 一路传到 `apiPost({ signal })`。所以「不能取消」只对**我们自己的提问面板**成立。
3. **提问面板可取消的成本几乎为零**：`askKsAnswer()` 的签名里**已经有** `signal?: AbortSignal`，只是调用点没传（搜 `askKsAnswer(port, token, text, {`）。
4. **引擎有流式，但没用在取证链路上**：`POST /api/v1/chat/completions` 是真 SSE（`StreamingResponse(..., media_type="text/event-stream")`，事件骨架 `evidence → status → delta → verification → done`）；而提问面板打的是 `POST /api/v1/ks/answer`，那是一个**同步 `def` 端点**，一次性返回整个 JSON。更关键：**两条流式实现都只取 `delta.content`，全仓没有一处读 `reasoning_content`** ⇒ 即便接上 SSE，思考那 29 秒**仍然是零字节**，除非加心跳或转发思考流（§5）。
5. **不要造假进度条**。业界结论一致：百分比必须真（NN/g 明确"loop 动画不要用于 >10 秒的任务"、"百分比一旦卡住 99% 信任立刻归零"）；无分母的长任务正确做法是**已用时长 + 分档解释 + 可取消**，不是编一个百分比。

---

## 1. 现有等待反馈盘点（`plugin/client/` 全量）

判据：有没有**数字在动**、能不能**取消**、最长可能等多久。

### 1.1 知识库页 · 按范围提问面板（**唯一真正需要改的地方**）

- 文件：`plugin/client/KsKnowledgePage.tsx`
- 状态机：`const [askPhase, setAskPhase] = useState<'idle' | 'running' | 'done' | 'error'>('idle')`
- 等待时显示的字（照抄）：`{askPhase === 'running' ? '在问…' : '问一问'}`
- 时间感：**无**。按钮文案是常量字符串，`runAsk` 里除了 `setAskPhase('running')` 没有任何计时器。
- 取消：**无**。按钮 `disabled={askPhase === 'running' || askQ.trim() === ''}`，只能干等。
- 最长可能等多久：**10 分钟**。工具层 `timeoutMs: 300_000`（注释：「300s × 2 遍 = 10 分钟，正好是业主给的上限」，指工具超时 × 引擎空返回重试 `llm_empty_retries` 默认 1 即最多 2 遍）。实测常态 22.8s / 31.9s / 30s / 37.3s。
- 关键旁证（可搜索）：`await withSession((port, token) => askKsAnswer(port, token, text, {` —— **第三个参数对象里没有 `signal`**，而 `askKsAnswer` 的签名是 `opts: { kbFolderIds?; kbDocIds?; topK?; signal?: AbortSignal } = {}`。

### 1.2 「本轮」tab

- 文件：`plugin/client/KsTurnTab.tsx`
- 等待时显示的字（照抄）：`正在读取本轮…`
- 时间感：无。取消：无。
- 最长可能等多久：**毫秒级**。数据来自插件自己的本地只读口 `GET /ks/turn/last?session=…`（`plugin/src/turn.js`：「纯 host 内存暂存」），不走引擎。
- ⇒ **这一处加计时纯属多余**。

### 1.3 PDF 证据 tab

- 文件：`plugin/client/KsEvidenceTab.tsx`
- 三处等待文案（照抄）：
  - `载入证据 PDF…（首次可能启动引擎，需要数秒）`
  - `加载中…`（目录树：`<div style={$tocHint}>加载中…</div>`）
  - 收藏按钮：`{docBusy ? '…' : docBookmarked ? '★ 已收藏本标准' : '☆ 收藏本标准'}`
- 时间感：无。取消：无（PDF 加载有 `retry` 重试按钮，但那是失败后）。
- 最长可能等多久：**首次冷启动约数秒到 20 秒**（引擎 `startupProbeTimeoutMs = 20_000`、`startupTimeoutMs = 60_000`）。文案里已经写了「需要数秒」。
- 关联：`plugin/client/KsDocTextView.tsx` 有 `载入正文条款…（首次可能启动引擎）`。

### 1.4 知识库导入面板（目录层「导入到这一层」）

- 文件：`plugin/client/KsKnowledgePage.tsx`
- 等待时显示的字：**有真数字**，而且分阶段：
  - `正在读取导入前的库快照…`
  - `批次 ${started.batch_id} 已建，正在快扫来源目录（建清单，还没开始解析）…`
  - `正在快扫：已看 ${st.scanned} / ${st.total} 个文件…`
  - `已解析 ${parsed} / ${last} 篇…`
  - 超时如实说：`快扫这一步等了 5 分钟还没结束（已看 ${String(last)} 个文件）——`
  - 按钮：`{upPhase === 'running' ? '导入中…' : '导入到这一层'}`
- 时间感：**有（真计数）**。取消：无（但每 1–2 秒刷新一次数字，不会像卡死）。
- ⇒ 这一处**已经是良好样板**，不要动。

### 1.5 入库预览面板（`KsIngestPanel`）

- 文件：`plugin/client/KsIngestPanel.tsx`
- 同步预览：`预览中…（解析 + 体检，扫描件可能要几秒）`；详情：`加载 {detailName} 的报告…`
- 异步全量预览：**全仓唯一有真进度条的地方** —— `role="progressbar"` + `aria-label="全量预览进度"` + 宽度按 `job.done / job.total` 算，并且**有中断按钮**：`<Button variant="ghost" size="sm" onClick={() => void abortFullJob()}>中断</Button>`，状态行写 `状态：{job.status} · 已体检 {job.done}/{job.total}`。
- ⇒ **这一处是「长任务等待反馈」的全仓样板**，其他地方照它抄即可，不要重新发明。

### 1.6 设置页 · 巡检 / 公告 / 待清清单

- 文件：`plugin/client/KsSettingsSection.tsx`
- 等待时显示的字：
  - `判断中（每条要过一遍语义判断，实测约 0.5 秒一条；这批有多长就要等多久，请稍候）…`
  - `{busy ? '启动中…' : isRunning ? '巡检中…' : …}`、`{scanning ? '启动中…' : isRunning ? '扫描中…' : '扫描公告源'}`
  - `{ingesting ? '入库中…（正在抓正文）' : '把新公告入库（每次 10 条）'}`
  - `加载中…`（两处）
- 时间感：**半有** —— 「判断中」那条**已经自带分档解释与速率**（0.5 秒/条），这是「超过 N 秒追加解释」的现成写法；巡检/扫描/入库只有状态词，无数字。
- 取消：无。
- 最长可能等多久：巡检「约 10–30 秒」（同仓 `KsChannelsPanel` 的 title 原文如此）；入库每次 10 条「可能要等十几秒」（同文件 title 原文）。

### 1.7 渠道采集面板（`KsChannelsPanel`）

- 文件：`plugin/client/KsChannelsPanel.tsx`
- 等待时显示的字（照抄）：
  - 常驻栏：`📢 读取最新动态…`
  - 刷新：`{busy ? '读取中…' : '⟳ 刷新'}`
  - 巡检：`{probeBusy ? '巡检中…（约 10–30 秒）' : '🩺 立即巡检'}`，title 里写得更细：`立即巡检：对配了检查口径的渠道各探一遍，实测今天能不能抓（约 10–30 秒）。`
  - 提交：`{mutating ? '提交中…' : '提交'}`
- 时间感：**半有**（「约 10–30 秒」是区间，不是实时数字）。取消：无。
- ⇒ 这一处**已经给了时长区间**，收益中等，优先级低于提问面板。

### 1.8 参考资料 / 材料面板（`KsMaterialsPanel`）

- 文件：`plugin/client/KsMaterialsPanel.tsx`
- 等待时显示的字：`加载中…`、`读取切片…`、按钮后缀 `{busy === n ? ' …' : ''}`
- 时间感：无。取消：无。最长等多久：**未确认**（该面板的 `busy` 覆盖多个动作，各自时长未逐个量）。
- 备注：这个文件里已经有一条明确的设计纪律注释：「失败**必须显示**（例如产物被清理 ⇒ 引擎 404）：否则按钮点了没反应，用户会以为是界面卡了。」——与本次业主诉求同源，可作为立论依据。

### 1.9 其它等待面（一并列出，均无长等待）

| 位置 | 文件 | 等待时显示的字（照抄） |
|---|---|---|
| 文件 tab | `KsFilesTab.tsx` | `加载中…（首次可能启动引擎，需要数秒）`、`⏳ 正在删除选中的 <b>{selDocs.size}</b> 部文档…` |
| 收藏 tab | `KsBookmarksTab.tsx` | `载入收藏目录…（首次可能启动引擎，需要数秒）` |
| 办事台 / 能力页 | `KsCapabilityPage.tsx` | `正在读取外发记录…`、`正在逐条比对法定义务…` |
| 目录树 / 批量动作 | `KsKnowledgePage.tsx` | `正在读取这一层…`、`正在读取…`、`正在读目录清单…`、`正在读这几个目录的真实影响（只读，还没动任何东西）…`、`正在数这个范围里有多少篇…` |
| 补全分类号 | `KsKnowledgePage.tsx` | `补全分类号：已跑 {ccsStatus.done} / {ccsStatus.total} 篇`（真数字）+ `role="status"` + `data-ccs-running` |
| 重来一次 | `KsKnowledgePage.tsx` | `重来一次进行中：${String(st.done)} / ${String(st.total)} 篇跑完…`（真数字，3 秒轮询） |

### 1.10 对话区（**宿主渲染，不归我们改**）

这一层必须写清边界，但也必须写清事实：

- 渲染方：DSH 宿主包 `@deepseek-ai/dsh-client-ui-chat`（对话流、运行指示器、工具卡片），以及 `@deepseek-ai/dsh-client-ui-tool`（工具行）。我们的插件只通过 `plugin/src/index.js` 的 `render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }]` 提供**文本回执**，没有卡片渲染权。
- **运行指示器已经有秒级计时**（可搜索）：`"chat.deepDivingFor": "深度求索中，用时 {duration} ···"`，`const LIVE_RUN_CLOCK_INTERVAL_MS = 1e3;`，`formatRunDuration` 支持 时/分/秒。
- **工具行只显示状态词，不显示时长**（可搜索）：`"row.running": "运行中"`、`"row.preparing": "正在准备调用"`，running 时用 `TextShimmer active` 做流光，但**没有**「已调用 N 秒」。
- **取消在宿主**（可搜索）：`"input.stop": "停止生成"`。
- 结论：**对话区不是「完全没有反馈」，是「有计时但不说在等什么、工具行不说等了多久」**。这一层改不了（不是我们的包），但可以用我们自己的面板补上解释性文案。

---

## 2. 「好不好加」逐处判断

判据三条：是否纯前端、是否碰宿主契约（`plugin/client/ksHostPrimitives.d.ts`）、有没有现成样式类（`plugin/client/ksGuideStyles.ts` 的 `KS_STYLES`）。

### 2.1 提问面板 —— **值得加，且最容易加**

| 项 | 结论 |
|---|---|
| 改哪个文件 | `plugin/client/KsKnowledgePage.tsx`（单文件；可选再加 1 条样式到 `plugin/client/ksGuideStyles.ts`） |
| 纯前端？ | **是**。`askPhase`、`runAsk`、按钮渲染都在同一文件内；引擎与工具层一个字不用改 |
| 碰宿主契约？ | **不碰**。只用到已在 `ksHostPrimitives.d.ts` 里声明的 `Button` / `IconClockOutlineRegular` / `IconRefreshOutlineRegular` / `IconEllipsisOutlineRegular` |
| 现成样式类 | 有：`.ks-ask-hint`（`font-size:var(--ks-fs-sm);line-height:1.5;color:var(--dsw-alias-label-tertiary)`）、`.ks-ask-msg`、`.ks-ask-row`、`.ks-ask-go`。**不需要新 CSS 也能做**（一行提示文字直接用 `.ks-ask-hint`） |
| 取消的现成钩子 | **已有**：`askKsAnswer(..., { signal })` 的 `signal` 参数已在 `api.ts` 声明，只是调用点没传 |

### 2.2 其余各处的性价比判断

| 位置 | 该不该加 | 理由（一句） |
|---|---|---|
| 「本轮」tab | **不该** | 数据来自本地内存只读口，毫秒级；加计时是纯噪音 |
| 入库预览（`KsIngestPanel`） | **不该** | 已经有真进度条 + 真数字 + 中断按钮，是全仓样板 |
| 导入到这一层（`upMsg`） | **不该** | 已经有真计数、分阶段、超时如实说 |
| 设置页「判断中」 | **不该** | 已经自带「0.5 秒/条，这批有多长就要等多久」的分档解释 |
| 补全分类号 / 重来一次 | **不该** | 已经有 done/total 真数字 + `role="status"` |
| 渠道巡检（`巡检中…（约 10–30 秒）`） | **可选（低优先）** | 已有区间；改成实时秒数收益中等，但每次只有 10–30 秒，误判卡死的风险小 |
| PDF 证据 / 文件 / 收藏 tab 的「首次可能启动引擎，需要数秒」 | **可选（低优先）** | 一次性冷启动，文案已交代；且这几个面用户会自己切走 |
| 材料面板 `加载中…` | **不该（先量再说）** | 各动作时长未确认，先确认再谈 |
| 对话区 | **改不了** | 宿主包渲染，不在本仓 |

**一句话：全仓 10 处等待面里，只有 1 处（提问面板）符合「固定 20 秒以上 + 零数字 + 零取消」这三个条件同时成立。**

---

## 3. 外部借鉴（业界做法，不是我们的证据）

### 3.1 已用时长 vs 假进度条：为什么假进度条有害

- **NN/g《Progress Indicators Make a Slow System Less Insufferable》**：loop 动画（转圈）只该用于 **2–10 秒**；**超过 10 秒不要用 loop 动画**，因为「用户很快就不耐烦，而且转圈如果无限旋转，用户无法判断系统还在工作还是已经停了」；百分比指示器一旦「先跑很快、最后卡在最后一个百分点」，好处会**被抵消**。
  <https://www.nngroup.com/articles/progress-indicators/>
- **NN/g《Response Times: The 3 Important Limits》**：**10 秒**是「用户把注意力留在对话上的上限」；超过 10 秒要给「进度指示」**以及明确的打断方式**；无分母时可退一步「用绝对工作量做反馈」，再不行才用转圈。
  <https://www.nngroup.com/articles/response-times-3-important-limits/>
- **UX Tigers《Progress Indicators Ease the Wait》**：把假百分比称为 "progress theater"——「每一个被打破的承诺，都在教用户不信任下一个指示器」；并直接点名 **AI agent 场景的「分母问题」**：开放式知识工作**没有已知总量**，编百分比就是加料的进度剧场。它给出的替代是五件事：**计划式步骤清单 / 用用户语言叙述在做什么 / 中间产物 / 已用时长（永远显示）/ 完成通知**——其中「**已用时长，永远显示；剩余时间，只在诚实的时候显示**」正是我们要的。
  <https://www.uxtigers.com/post/progress-indicators>
- **「劳动幻觉」有学术依据**：Buell & Norton（Harvard Business School / *Management Science* 2011）——把正在做的事展示出来，用户**更愿意等、评价更高**，甚至「看得到过程但要等」比「立刻给结果」更受偏好。
  <https://pubsonline.informs.org/doi/10.1287/mnsc.1110.1376>
  <https://www.hbs.edu/faculty/Publication%20Files/think%20customers%20hate%20waiting_20d66186-ad13-4af6-93d7-c712dd409bd9.pdf>

⇒ 对我们的含义：**别编百分比**（这道题没有分母：检索 + LLM 思考 + 核验，各段耗时随题变化），显示**已用秒数 + 分档解释**才是诚实且有效的。

### 3.2 超过 N 秒后追加一句解释（progressive disclosure）

- **《Designing "Thinking" Experiences》**：把「通用转圈」换成「分步说明在做什么」（例：`Analyzing sentiment… Matching response tone…`），作者称其客户案例里「与『它没在工作！』相关的支持工单下降 38%」（**这是对方自述数字，非独立研究，按业界做法引用**）。
  <https://jensen.technology/en/post/designing-thinking-experiences-how-to-turn-ai-load-times-into-trust-building-moments>
- **《Long-Running AI Tasks in UIs》**：给出**区间**而非精确值——「AI 负载耗时随输入复杂度变化大时，考虑显示区间：`Typically completes in 30-60 seconds`；这种对不确定性的诚实承认，比一致的假精确表现更好」；并且**按阶段换文案**能「重置用户的耐心计时」。
  <https://particula.tech/blog/long-running-ai-tasks-user-interface-patterns>

⇒ 对我们的含义：0–5 秒说「正在检索条款」，5–15 秒说「正在思考，这类问题通常要 20–40 秒」，>15 秒说「已等 N 秒，可以继续等或取消」。这句话里的 20–40 秒有本仓实测支撑（22.8/31.9/30/37.3 秒）。

### 3.3 可取消（cancel）

- **CodeGym《Flow UX: progress, partial results, canceling long-running operations》**：取消要分两层——**前端取消**（abort fetch / 关掉 SSE，省流量但不停后端）与**真任务取消**（`POST /jobs/{id}/cancel`）；UI 上建议「一个够显眼但别是屏幕中央大红块的主按钮 + 一句小字『随时可以重来』」，并明确告诉用户取消的是**当前这次分析**、不是整个应用。
  <https://codegym.cc/quests/lectures/en.codegym.chatgptapp.next.lecture.level13.lecture03>
- NN/g 同上：「对稍慢的操作，给用户停止的选项，否则你的设计等于劫持了系统控制权，让用户无力」。

⇒ 对我们的含义：提问面板的「取消」是**前端取消**（abort 掉 `fetch`），要如实说清「停的是等待，引擎那边可能还在跑」——本仓引擎 `/api/v1/ks/answer` 是同步 `def` 端点，客户端断开**不会**中断已在线程里跑的 Python 调用（机制上如此，**未实测**）。

### 3.4 流式输出是根本解

- **《What Is Streaming in LLM Inference?》**：「流式与非流式的差别，就是一个聊天产品**感觉秒回**还是**感觉坏了**」；真正决定感知延迟的是 **time-to-first-token**，不是端到端时间。
  <https://futureagi.com/glossary/streaming/>
- **《Streaming》pattern（aiverse.design）**：渐进披露「相比延迟整体揭示，可把感知等待降低最多 40%」（**对方引用数字，非我们的证据**）；并强调「能中途停」是流式的一半价值。
  <https://www.aiverse.design/patterns/v1/output-streaming>
- **applied-ai-engineer-learning · streaming & cancellation**：后端流的三个健康属性——**背压感知**、**断连感知**（每个 yield 边界查 `req.is_disconnected()`）、**错误放在流内**（上游中途失败要发 `error` 事件，不能默默关掉让前端转圈）。
  <https://github.com/ai-engineering-curriculum/applied-ai-engineer-learning/blob/7cdc2123ed4c6d4255b350fc1db3020b1fe89bf2/lessons/mod-102-production-prompting-and-structured-outputs/03-streaming-and-cancellation.md>

---

## 4. 现状对照：我们离「已用时长 + 分档解释 + 取消」还差什么

| 能力位 | 宿主对话区 | 我们的提问面板 | 差距 |
|---|---|---|---|
| 已用时长 | **有**（`chat.deepDivingFor` + 1s tick） | **无**（`在问…` 常量） | 面板侧要自己起一个 tick |
| 分档解释 | 无（只有「深度求索中」） | 无 | 两边都没有 |
| 可取消 | **有**（`input.stop` = 停止生成） | **无** | 面板侧要加，且 `signal` 钩子已存在 |
| 真进度/真数字 | 无（不适用） | 无（不适用，此题无分母） | 不该有 |
| 流式正文 | 有（宿主按 SSE 渲染助手输出） | **未接**（打的是同步端点） | §5 |

---

## 5. ★ 关键发现：引擎**已经有流式能力**，但取证链路一处都没用上

这是本次最重要的发现，分三层说，别混成一句。

### 5.1 引擎确实有 SSE 端点（现成的）

`src/core/api/server.py`：

- 文件头第一行就写着：`"""FastAPI 服务组装（全量路由）：随机端口 + token 鉴权 + /health + SSE 流式 + 证据/补丁/更新 API。"""`
- `from fastapi.responses import FileResponse, StreamingResponse`
- `@app.post("/api/v1/chat/completions")` 的 docstring：`"""SSE 骨架：evidence → status → delta → verification → done。`
- 事件确实按这个顺序发：`yield _sse("evidence", {...})` → `yield _sse("status", {"phase": "streaming_with_verification_pending", "message": "核验中..."})` → 逐片 `yield _sse("delta", {"content": part})` → `yield _sse("verification", {...})` → `yield _sse("done", {})`
- 返回：`return StreamingResponse(event_stream(), media_type="text/event-stream")`
- `def _sse(event: str, data: dict) -> str: return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"`

`src/core/llm/deepseek_client.py` 有 `stream_chat_completion(...)`，内部 `stream=True` 后 `for chunk in stream: ... yield delta.content`。

### 5.2 但取证答案走的不是这条路

- 提问面板打的是 `POST /api/v1/ks/answer`（`plugin/client/api.ts` 的 `askKsAnswer`），**不是** `/chat/completions`。
- `/api/v1/ks/answer` 是**同步 `def` 端点**：`@app.post("/api/v1/ks/answer")` / `def ks_answer_endpoint(body: dict | None = None):`，内部 `data = ks_answer.answer(query, params=params, query_mode=query_mode)`，最后 `return {"code": 200, "status": "success", "data": data}`。docstring 自己写明：`与 /api/v1/chat/completions（SSE）并存；SSE 事件顺序契约不动。`
- 更微妙的一层：`src/core/llm/ks_answer.py` **内部本来就是流式调用的** —— `gen = _stream_llm(messages)` 然后 `raw_text = _collect_stream(gen)`。`_collect_stream` 的 docstring：`"""把生成器拼成完整文本（同步端点用；容忍流式为空）。"""`
  ⇒ **tokens 是流式产出的，但在引擎内部被拼成整串、丢掉时间信息、最后一次性返回。** 这是「已经付了流式的成本，却没拿到流式的好处」。
- 另一层缺口：`/api/v1/chat/completions` 的入参只有 `query / history / top_k / channels / include_superseded / dump / query_mode / answer_scope`，**没有** `kb_folder_ids` / `kb_doc_ids`。也就是说，那条现成 SSE **接不了「按知识库目录范围提问」**（这是第 6 步的核心语义）。

### 5.3 最关键的一句：**即使接上 SSE，思考那 29 秒仍然是零字节**

- `src/core/llm/ks_answer.py` 的 `_stream_llm`：`if delta and delta.content: yield delta.content`
- `src/core/llm/deepseek_client.py` 的 `stream_chat_completion`：`if delta and delta.content: yield delta.content`
- 全仓 grep `reasoning_content`：**只有 1 处命中，而且是 `src/core/config.py` 里的一段注释**（记载免费 router 车道「会先输出 `reasoning_content`，10 个真实取证问题实测思考部分占 688–12751 字符」），**没有任何代码读它**。

⇒ 所以「正文前空转 29 秒」在流式下依然存在：SSE 会在 1 秒内把 `evidence` + `status` 发出来（比现在好），然后**29 秒静默**，直到第一个 `content` token。要真正填掉这段空白，只有三条路：

1. **心跳**：思考期每 1–2 秒发一次 `event: status`（`{"phase":"thinking","elapsed_s":N}`），前端拿它驱动计时与分档文案。**不动 LLM 侧，最省。**
2. **转发 `reasoning_content`**：把思考流也发出去（SDK 的 delta 上有这个字段）。能彻底填满，但会把「思考过程」暴露到前台，有被误读成结论的风险，业主也没要求看思考。
3. **前端纯计时**（不碰引擎）：面板自己 tick，文案分档。零引擎改动，但仍是「我不知道它在干什么」。

### 5.4 一个附带确认

- 工具层超时与内层同值：`timeoutMs: 300_000`，注释明写 `⚠ **这一层才是真上限**：它比下面 apiPost 的 timeoutMs 先到期时，内层还没跑完就被杀` ⇒ 最坏等待 **5 分钟 × 2 遍（空返回重试）= 10 分钟**。
- 引擎侧 HTTP 客户端（openai SDK）默认超时是 **600 秒**（`.venv/Lib/site-packages/openai/_constants.py`：`DEFAULT_TIMEOUT = httpx.Timeout(timeout=600, connect=5.0)`），`DEFAULT_MAX_RETRIES = 2` ⇒ **引擎内部最坏还可能再放大**。这条未逐题实测，标「机制如此，未实测」。

---

## 6. 方案排序（只给方案，未实施）

排序依据：改动小 + 收益大。每个方案写清改哪、用户看到什么、工作量、风险、可回退性。

### 方案 A（首选）：提问面板加「已用秒数 + 分档解释 + 取消」

- **改哪**：`plugin/client/KsKnowledgePage.tsx` 单文件（可选：`plugin/client/ksGuideStyles.ts` 加 1 条 `.ks-ask-wait` 样式，也可以完全复用现成的 `.ks-ask-hint`，不新增 CSS）。引擎、工具层、宿主契约一个字不动。
- **怎么做**（描述形状，不含代码）：
  1. `runAsk` 里记下起始时间戳（与 `askPhase` 并列的一个 state）；
  2. `askPhase === 'running'` 时起一个 1 秒 `setInterval` 更新「已等秒数」，`done`/`error`/卸载时清掉；
  3. 在 `.ks-ask-row` 下方渲染一行 `.ks-ask-hint`，按秒数换文案：`0–5s`「正在检索条款…」/ `5–15s`「正在思考，这类问题通常要 20–40 秒」/ `>15s`「已等 N 秒，可以继续等，也可以取消」；
  4. 按钮旁加一个「取消」，`onClick` 调 `abortRef.current.abort()`；`runAsk` 里新建 `AbortController`，把 `signal` 传进 `askKsAnswer(..., { signal })`（该参数**已存在**）；取消后 `askPhase` 回 `idle`，并显示一句「已取消（引擎那边可能还在跑）」。
- **用户看到什么**：点「问一问」后，按钮变「在问…」的同时下面多一行会自己走秒的说明；超过 15 秒出现「取消」；点取消立刻回到可再问状态。
- **工作量**：小。一个文件、约 40–60 行、无新依赖。
- **风险**：
  - 低。纯展示 + 一个 `AbortController`；不动引擎、不动数据流。
  - **已知风险点**：取消只停前端等待，引擎里那次 `ks_answer.answer()` 是同步 `def` 跑在线程里，**不会**被中断（机制如此，未实测）。所以文案必须写「停的是等待」，不能写「已终止分析」。
  - **纪律风险**：上一轮就是在这一处被误改（加计时器 24 行）后 `git checkout` 还原。本轮**不实施**；真要实施必须走必验流程。
- **可回退性**：`git checkout -- plugin/client/KsKnowledgePage.tsx`，一行命令。

### 方案 B（次选）：引擎加「思考期心跳」，前端另接一条 SSE

- **改哪**：
  - `src/core/api/server.py`：新增一个 `POST /api/v1/ks/answer/stream`（或给现有端点加 `?stream=1` 分支），复用 `_sse()` 与 `StreamingResponse`，事件顺序对齐现有 SSE 契约（`evidence → status(thinking, 每秒一次) → delta → verification → done`）；
  - `src/core/llm/ks_answer.py`：`answer()` 需要能在生成过程中回报进度（心跳线程 / 队列，或把 `_stream_llm` 的每个 chunk 先发出去）；
  - `plugin/client/api.ts`：加一个 SSE 客户端（`fetch` + `ReadableStream` 解析，或 `EventSource`）；
  - `plugin/client/KsKnowledgePage.tsx`：`runAsk` 改走这条流。
- **用户看到什么**：点下去 1 秒内就出现「已收到证据（N 条），正在思考」；思考期秒数在走；正文开始出字后逐字显示；最后核验结果照旧。
- **工作量**：中到大。要动引擎 + 工具层（`plugin/src/index.js` 的模型侧仍是同步返回，两条路要并存）+ 前端三处。
- **风险**：
  - **中高**。`server.py` 里有明确的「重活闸门」纪律：`HEAVY_PREFIXES` 里 `/api/v1/ks/answer` 是「引擎侧推理，120s 契约」，且注释写着「开流之前就 release，**流式（SSE）重活因此完全不受闸门约束**」——新开一条流式取证端点会**绕过 4 个令牌的重活闸门**，并发时可能把线程池打满。这必须在方案里显式处理（照 `HEAVY_SKIP` 的反面：要么让它吃令牌，要么证明它不吃线程）。
  - SSE 中途失败必须发 `error` 事件，不能默默关流（业界共识，见 §3.4）。
  - 前端要处理「流到一半断开」的三态：仍在流 / 正常结束 / 中途出错。
- **可回退性**：新端点独立、前端可 feature-flag 切回同步端点 ⇒ 回退成本低；但引擎改动本身要过本仓门禁。

### 方案 C（可选，最小引擎改动）：只加心跳，不改正文流

- **改哪**：只给 `/api/v1/ks/answer` 加一个**旁路**进度口（例如 `GET /api/v1/ks/answer/progress?token=…` 返回当前是否在思考、已用秒数），前端在 `running` 期轮询它。
- **优点**：不动正文链路，不动 SSE 契约，闸门问题小（廉价 GET）。
- **缺点**：多一次轮询；且「已用秒数」前端自己就能算，**这条轮询的边际收益接近于零**——除非要报告「引擎真的在动（而不是我们前端在数秒）」。⇒ **除非业主要求「证明后台真的在干活」，否则不必做。**

### 方案 D（不建议）：转发 `reasoning_content` 给前台

- **理由不做**：技术上可行（SDK delta 上有该字段），但把「思考过程」暴露给前台，容易被当成结论读；业主的诉求是「知道还活着」，不是「看它怎么想」。方案 A 的秒数 + 分档解释已经满足这个诉求。

### 明确不做的事

- **不给提问面板加假进度条**：这道题没有分母（检索 + 思考 + 核验三段耗时随题变化），编百分比正是 §3.1 里被点名的 "progress theater"。
- **不动 `KsIngestPanel` 的异步进度条**：它是全仓唯一正确的样板，改了只有坏处。
- **不动「本轮」tab**：毫秒级本地读取，加计时是噪音。

---

## 7. 诚实声明

1. **本轮没有改任何前端代码。** 全程只做 `grep` / `read` / 文件系统只读检查 + `web_search`。
2. **上一轮误改已还原，可核**：`git status --short -- plugin/client/KsKnowledgePage.tsx` 输出为空；`git diff --stat -- plugin/client/KsKnowledgePage.tsx` 输出为空 ⇒ 该文件在 git 眼里是**干净的**。
3. **`plugin/client/api.ts` 的 `M` 状态与本轮无关**，是接手前就有的既有改动（同批还有 `src/core/api/routes_update.py`、`src/core/llm/ks_answer.py` 也是 `M`）。
4. **未跑任何会写盘的门禁**（`scripts/run-gates.ps1` 等一律未执行）。
5. **外部资料均为「业界做法」，不是「我们的证据」**：所有 URL 只用来支撑「业界怎么处理这类等待」，不用来支撑「我们代码是什么样」。我们代码的每条结论都附了文件路径 + 可搜索原文片段。
6. **标「未确认」的三处**：
   - 取消后引擎侧是否真的继续跑完（机制推断为「继续跑」，**未实测**）；
   - 材料面板各动作的真实耗时（**未逐个量**）；
   - 引擎内 openai SDK 的 600s 默认超时与 `DEFAULT_MAX_RETRIES = 2` 在真实取证题上会不会叠加出比 300s 更长的等待（**机制上可能，未实测**）。
7. **一处对前提的更正**（按「不许迎合、从事实出发」）：业主/任务书说「界面上等待期的提示极弱」——**对提问面板成立，对宿主对话区不成立**。宿主对话区已经有秒级计时（`chat.deepDivingFor` + 1 秒 tick）和「停止生成」。所以问题不是「完全没有反馈」，而是「**反馈分散在两个不同的面**：宿主那边有秒数但不说在等什么，我们这边说在问但不说等了多久」。
