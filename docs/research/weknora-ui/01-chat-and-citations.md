# WeKnora 前端「问答 / 对话」整块精读

- 源码：`D:\AI\WeKnora`（Vue 3 + TDesign Vue Next + Pinia + vue-router）
- 精读范围：会话与导航、提问区、回答渲染、引用与来源面板、文档预览、产物、消息级操作、状态反馈、接口
- 读法：只读。本文所有路径**相对 `D:\AI\WeKnora\frontend`**，即 `src/...`。文案照抄自 `src/i18n/locales/zh-CN.ts`（默认中文），行号即该文件行号。
- 未验证项集中放在末尾「我没查到/不确定」。

---

## 0. 页面 / 路由清单表

路由定义全部在 `src/router/index.ts`。与「问答」这块真正相关的只有下列几条：

| 路径 | name | 文件 | 干什么 |
|---|---|---|---|
| `/platform/creatChat` | `globalCreatChat` | `src/views/creatChat/creatChat.vue` | **全局新会话欢迎页**：大标题 + 推荐问题 + 输入框；发送后先 `POST /sessions` 建会话再跳 `chat/:id` (`src/router/index.ts:166-170`) |
| `/platform/knowledge-bases/:kbId/creatChat` | `kbCreatChat` | 同上（同一文件） | 知识库内的新会话页；靠 `route.params.kbId` 与 `isInKnowledgeBase` 判定上下文 (`src/router/index.ts:172-176`) |
| `/platform/chat/:chatid` | `chat` | `src/views/chat/index.vue` | **会话主界面**：消息流 + 输入栏 + 来源抽屉 + 沙箱面板 (`src/router/index.ts:178-182`) |
| `/platform/artifacts` | `artifactLibrary` | `src/views/artifacts/ArtifactLibrary.vue` | **产物库**：跨会话汇总智能体生成的文件，按类型/关键词筛选、日期分组、抽屉内预览、下载 (`src/router/index.ts:137-141`) |
| `/platform/knowledge-bases` | `knowledgeBaseList` | `src/views/knowledge/KnowledgeBaseList.vue` | 知识库列表（来源抽屉里「查看文档详情」的落地页之一） |
| `/platform/knowledge-bases/:kbId` | `knowledgeBaseDetail` | `src/views/knowledge/KnowledgeBase.vue` | 知识库详情（文档列表/分块）；引用抽屉的点跳转目标是这里 |
| `/platform/knowledge-search` | （重定向） | → `knowledgeBaseList` | 见 `src/router/index.ts:126-135` |
| `/platform/agents` | `agentList` | `src/views/agent/AgentList.vue` | 智能体列表/编辑器；决定「问答」用哪个 agent、可用工具、KB 范围、联网开关 |
| `/platform/settings` | `settings` | `src/views/settings/Settings.vue` | 设置（含对话历史设置 `chatHistorySettings`） |
| 嵌入渠道 | 无独立路由 | `src/views/embed/EmbedPage.vue` → `EmbedChatView.vue` → `EmbedChatCore.vue` | 对外嵌入的问答界面，复用 `botmsg`/`ChatReferencesDrawer`，但走 `embed_token` 与独立 API (`src/views/embed/EmbedChatCore.vue:112,130-138`) |

侧栏导航项（`src/components/menu.vue:444`）：`TOP_MENU_PATHS = {creatChat, knowledge-bases, artifacts, agents, organizations}`；对应文案 `src/i18n/locales/zh-CN.ts:7402-7429`（`menu.newChat` = `新对话`、`menu.knowledgeBase` = `知识库`、`menu.agents` = `智能体`、`menu.artifacts` = `产物`…）。

---

## 1. 会话与导航

### 1.1 会话列表在哪

- 左侧栏组件 `src/components/menu.vue`，宽度可折叠（`uiStore.sidebarCollapsed`，`src/components/menu.vue:2`），折叠按钮文案 `menu.collapseSidebar` = `收起侧边栏` / `menu.expandSidebar` = `展开侧边栏`（`src/i18n/locales/zh-CN.ts:7424-7425`）。
- 列表区是 `div.submenu`，仅在展开态渲染（`src/components/menu.vue:104`）。
- **不是抽屉**；引用来来源面板（右侧抽屉）是另一回事（见 §4）。

### 1.2 列表项长什么样

`src/components/SessionSidebarRow.vue`：

- 标题 `item.title`（hover 有 title 提示），置顶时前置 pin 图标，分叉会话前置 `git-branch` 图标且 tooltip **硬编码中文** `由其他会话分叉而来`（`src/components/SessionSidebarRow.vue:16-20`，注意这里没走 i18n）。
- API/渠道会话在标题旁渲染 owner 小徽标（`api_external_user:` / `api_tenant_key:` 前缀解析，`src/components/SessionSidebarRow.vue:122-130`）。
- 运行中会话显示转圈指示器，`aria-label`/`title` = `menu.sessionInProgress` = `会话进行中`（`src/components/SessionSidebarRow.vue:24-25`，文案 `zh-CN.ts:7403`）。
- 行尾 `…` 弹出菜单（`src/components/SessionSidebarRow.vue:26-63`）：置顶/取消置顶、修改标题、批量管理、删除；危险操作走**行内二次确认**（不是 Modal），标题/正文分别复用 `chatHeader.clearConfirmTitle|clearConfirmBody|deleteConfirmTitle|deleteConfirmBody`（`src/components/SessionSidebarRow.vue:45-60`）。
- 会话列表**不显示**时间/预览/来源图标在行内；时间只体现在**日期分组标题**上。

### 1.3 按时间分组

- 分组纯逻辑 `src/components/sessionGrouping.ts`（`groupSessionsByDate`）；标签在 `src/components/menu.vue:462-470` 装配：
  `pinned`=`已置顶`、`today`=`今天`、`yesterday`=`昨天`、`last7Days`=`近7天`、`last30Days`=`近30天`、`lastYear`=`近1年`、`earlier`=`更早`（`src/i18n/locales/zh-CN.ts:2660-2668`）。
- 默认分组模式是 `none`（`DEFAULT_SESSION_GROUP_MODE = 'none'`，`src/components/sessionGrouping.ts:6`），但侧栏实际渲染走的是 `groupSessionsByDate(...)`（`src/components/menu.vue:472-484`），`group.label` 为空时不渲染标题行（`src/components/menu.vue:137`）。

### 1.4 新建会话

- 「新对话」在 `TOP_MENU_PATHS` 里是 `creatChat`，点击 `router.push('/platform/creatChat')`（`src/components/menu.vue:1172-1179`）。
- 新会话是**懒创建**：先在欢迎页输入，`createNewSession` 才 `POST /api/v1/sessions`（`src/views/creatChat/creatChat.vue:213`），拿到 id 后写侧栏 + `router.push('/platform/chat/'+id)`（`src/views/creatChat/creatChat.vue:237-240`）。
- 失败提示原文：`createChat.messages.createFailed` = `创建会话失败`、`createChat.messages.createError` = `创建会话失败，请稍后重试`（`zh-CN.ts:4854-4855`）。
- 新会话占位标题 = `createChat.newSessionTitle` = `新会话`（`zh-CN.ts:4852`），`isNoTitle: true`（`src/views/creatChat/creatChat.vue:233`）。
- 会话标题由后端生成：`POST /api/v1/sessions/{id}/generate_title`（`src/api/chat/index.ts:25-27`）。

### 1.5 重命名 / 删除 / 置顶 / 批量

- 重命名：双击顶部标题进入行内编辑（`src/components/ChatHeader.vue:24`），或侧栏行菜单 `menu.renameSession` = `修改标题`（`zh-CN.ts:7414`）；占位符 `chatHeader.renamePlaceholder` = `输入对话标题`（`zh-CN.ts:7340`）；成功/失败 `menu.renameSessionSuccess`=`标题已更新` / `renameSessionFailed`=`修改标题失败，请稍后再试`（`zh-CN.ts:7415-7416`）。标题长度上限常量 `SESSION_TITLE_MAX_LENGTH`（`src/components/sessionTitleEdit.ts`）。
- 置顶/取消置顶：`menu.pin`=`置顶` / `menu.unpin`=`取消置顶`（`zh-CN.ts:7419-7420`）；成功 `chatHeader.pinSuccess`=`已置顶`、`chatHeader.unpinSuccess`=`已取消置顶`（`zh-CN.ts:4826-4827` 与 `7341`）；失败 `menu.pinFailed`=`置顶失败，请稍后再试`、`menu.unpinFailed`=`取消置顶失败，请稍后再试`（`zh-CN.ts:7421-7422`）。防重复点击靠 `pinningIds`（`src/components/menu.vue:459,696-703`）。
- 删除：单条 `removeSession`（`src/components/menu.vue:715`，失败 `chat.deleteSessionFailed`=`删除失败，请稍后再试！`，`zh-CN.ts:3927`）；批量 `batchMode` + 底部操作条「全选 / 取消 / 删除对话」(n)（`src/components/menu.vue:174-191`，文案 `batchManage.*`，`zh-CN.ts:7081-7089`）。批量确认正文：`确定要删除选中的 {count} 条对话吗？删除后无法恢复。` / `确定要删除所有对话吗？此操作无法恢复。`（`zh-CN.ts:7086-7087`）。
- 删除当前打开的会话会 `router.push('/platform/creatChat')` 回欢迎页（`src/components/menu.vue:1009-1011`）。

### 1.6 搜索历史

- **侧栏没有会话搜索框**。全仓 `menu.vue` 内无 `t-input`/关键字过滤（已核：`grep -n "t-input|filterSessions|keyword"` 无命中）。
- 搜索入口是**全局命令面板**：logo 行放大镜按钮或 `⌘/Ctrl + K`，`commandPaletteStore.openPalette('')`（`src/components/menu.vue:10-21`），tooltip 文案 `menu.search` = `搜索`（`zh-CN.ts:7423`）。
- 面板搜两类东西（`src/components/GlobalCommandPalette/useSearch.ts:244-278`）：
  - 知识片段：`POST /api/v1/knowledge-search`（按 `knowledge_base_ids` 收敛）；
  - **聊天历史**：`POST /api/v1/messages/search`，参数 `{query, mode:'hybrid', limit:30}`（`src/components/GlobalCommandPalette/useSearch.ts:271`）。
- 结果按 `session_id` 分组，组字段 `sessionId/sessionTitle/items`（`src/components/GlobalCommandPalette/useSearch.ts:312-327`），每条含 `query_content`/`answer_content`/`score`/`match_type`（`src/api/chat-history.ts:30-39`）。
- 静态快捷命令见 `src/components/GlobalCommandPalette/commands.ts:33-96`（第一个就是「新对话」→ `/platform/creatChat`）。

### 1.7 会话与知识库的关系（最关键的一条）

- **会话不绑定知识库**。代码里写着注释：`// Session 不再和知识库绑定，直接创建 Session`（`src/views/knowledge/KnowledgeBase.vue:2220`），`createSessions({})` 传空对象（同处 `:2221`）。
- 「限定在某个知识库内提问」是靠**发起请求时带上 `knowledge_base_ids`** 实现的：
  - 侧栏/@ 选中的 KB → `settings.selectedKnowledgeBases`；
  - `sendMsg` 里把它与 `@` 提及的 kb/file 合并成 `kbIds` / `knowledgeIds`（`src/views/chat/index.vue:1356-1374`），随 SSE 请求体发出（`src/views/chat/index.vue:1387-1409`）。
- 会话级「记忆」来自后端 `sessions.last_request_state`：重新打开旧会话时，用当时那次请求的 agent / model / KB / 联网 / MCP / skill 覆盖输入栏 store，离开会话再还原全局默认（`src/stores/settings.ts:516-597`，字段形状 `:603-617`）。**这是「点开旧会话能看到当时的检索范围」的实现方式**。
- 切换知识库**不会**新建或切换会话，只改输入栏选择。切换 KB/文件会以 300ms 防抖重取推荐问题（`src/views/chat/index.vue:614-633`）。

### 1.8 会话来源（source）枚举

- 侧栏按来源分桶：`SidebarBucketKind = 'web' | 'im' | 'embed' | 'api'`（`src/components/sessionSidebarBuckets.ts:8`），分页大小 `SIDEBAR_BUCKET_PAGE_SIZE = 30`（`:6`）。
- 分桶由 `buildBucketDefinitions(imPlatforms, embedChannels, labels, {includeAdminChannelBuckets})` 生成（`:75-125`）；IM/embed/api 三个桶是**管理员可见**，且先做一次 `page_size=1` 的 count 探测，为 0 就隐藏（`:49-60,799-822`）。
- 文案：`menu.myChats` = `我的对话`、`menu.apiChats` = `API 会话`（`zh-CN.ts:7427-7428`）；IM 平台名走 `agentEditor.im.<platform>`（`src/components/menu.vue:792`）。
- 来源筛选器 `src/components/SessionSourceFilter.vue`（inline 触发器 + Teleport 下拉）；空态 `menu.noSessions` = `暂无对话`（`src/components/menu.vue:133`，`zh-CN.ts:7429`）。

### 1.9 会话运行态

- `src/stores/sessionActivity.ts` + `sessionActivityState.ts`；侧栏每 5s 轮询刷新（`src/components/menu.vue:1016`），行内用 spinner 表达「会话进行中」。

---

## 2. 提问区

主组件 `src/components/Input-field.vue`（4080 行）。

### 2.1 输入框形态

- 就是 TDesign `t-textarea`，`autosize` 开（自动增高，未设 maxRows），`name="description"`（`src/components/Input-field.vue:2704-2706`）。
- placeholder **按状态计算**（`src/components/Input-field.vue:723-750`）：
  | 状态 | key | 原文 |
  |---|---|---|
  | 自定义智能体有描述 | — | 直接用 `agent.description` |
  | 自定义智能体无描述 | `input.placeholderAgent` | `向 {name} 提问` |
  | 有 KB + 有联网 | `input.placeholderKbAndWeb` | `输入问题，将基于知识库和网络搜索回答` |
  | 只有 KB | `input.placeholderWithContext` | `输入问题，将基于上方选中的知识库/文件回答` |
  | 只有联网 | `input.placeholderWebOnly` | `输入问题，将结合网络搜索回答` |
  | 都没有 | `input.placeholder` | `直接向模型提问` |
  （文案 `zh-CN.ts:4860-4864`）
- 输入框上方按文档流堆叠：图片预览条（`:2668-2673`）、`AttachmentUpload` 附件区（`:2676-2679`）、已选 KB/文件/tag/MCP/skill 的 chip 行（`:2682-2701`），chip 末尾有 `×` 可删（`:2698-2699`）。

### 2.2 快捷键发送（精确规则）

`src/utils/chatSubmitShortcut.ts:6-10` 是唯一真源：

- 组合输入中 / `keyCode===229` / 非 Enter → 不处理；
- `Shift` 或 `Ctrl` + Enter → 不处理（留给换行）；
- `Meta`(⌘) + Enter → `'inject'`（补充当前正在跑的任务）；
- `Alt` + Enter → 可 steer 时 `'inject'`，否则不处理；
- 裸 Enter → 可 steer 时 `'after'`（排队到当前回答结束后发），否则 `'inject'`（等价于普通发送）。
- 队列里第一条 `after` 消息的「立即发送」按钮 tooltip 会带上快捷键标签：Mac 显示 `⌘ Enter`，其他平台 `Alt+Enter`（`src/components/Input-field.vue:2325,2653`）。
- Enter 的 6 个分派分支在 `src/components/Input-field.vue:2375-2380`；IME 守卫在 `:2335`（`isComposing` / `keyCode===229` 直接 return）。
- @ 菜单打开时键盘被菜单接管：↑/↓ 移动、Enter 确认、Esc 关闭或退出分组（`src/components/Input-field.vue:2336-2359`）。
- 输入框为空时按 Backspace 会删掉最后一个已选 chip（`src/components/Input-field.vue:2362-2373`）。

### 2.3 发送 / 停止

- 右侧按钮**同位置二态**：`isReplying && (!canSteer || 输入为空)` → 停止按钮（icon `stop`，tooltip = `input.stopGeneration` = `停止生成`，`src/components/Input-field.vue:2913-2917`）；否则发送按钮（icon `arrow-up`，`disabled = !query.trim()`，tooltip 模板 `${发送/完成后发送} · Enter`，`src/components/Input-field.vue:2918-2924`）。
- 停止会调 `POST /api/v1/sessions/{id}/stop`，body `{message_id}`（`src/api/chat/index.ts:83-85`，调用点 `src/components/Input-field.vue:2602`）；toast `input.messages.stopSuccess`=`已停止生成`、`stopFailed`=`停止失败，请重试`（`zh-CN.ts:4916-4917`）。
- 前端**同时**立刻清 loading：`handleStopGeneration()` 里 `stopStream()` + 清 `loading/isReplying` + 标记进行中的 assistant 为已停止（`src/views/chat/index.vue:924-932`）。
- **没有「重新生成上一条回答」按钮**（已核：`regenerate` 只用于推荐问题，见 §7）。

### 2.4 附件与图片

- 附件选择器 `src/components/AttachmentUpload.vue`，`max-files=5`（`src/components/Input-field.vue:2676`；组件默认 `props.maxFiles || 5`，`src/components/AttachmentUpload.vue:76`）。
- 支持后缀白名单（静态基线 + 后端解析引擎发现的类型合并，`src/components/AttachmentUpload.vue:49-74`）：
  `.pdf .doc .docx .xls .xlsx .ppt .pptx .epub .mhtml .txt .md .csv .json .xml .html .markdown .yaml .yml .log .jpg .jpeg .png .gif .bmp .tiff .webp .mp3 .wav .m4a .flac .ogg .aac`
- 大小上限 `MAX_FILE_SIZE_MB`，**默认 50MB**，可被 `window.__RUNTIME_CONFIG__.MAX_FILE_SIZE_MB` 覆盖（`src/utils/index.ts:21-26`）。
- 图片是独立一路：`accept="image/jpeg,image/png,image/gif,image/webp" multiple`（`src/components/Input-field.vue:2639`），只允许 4 种 MIME、单张 ≤10MB、最多 5 张（`src/components/Input-field.vue:128-147`）；支持**粘贴**与**拖拽**（`onPaste` `:2383-2397`、`@drop` `:2637,2399-2404`）。
- 图片和附件**合计上限 5**：`MAX_TOTAL_ATTACHMENTS = 5`（`src/components/Input-field.vue:2037-2044`），超限提示 `chat.attachmentTotalTooMany` = `图片和附件合计最多 {max} 个`（`zh-CN.ts:3934`）。
- 图片在 Web 端不再走 inline base64，而是**当临时文档上传**：`uploadTemporaryAttachment(...)` → `POST /api/v1/sessions/{id}/attachments`（`src/views/chat/index.vue:1262-1271`，API `src/api/chat/temporary-attachments.ts:25-45`）；只有 embed 公共路径保留 base64 `images`（`src/views/chat/index.vue:1258-1261`）。
- 发送时请求体字段：`attachment_ids`（已上传文档 id）、可选 `images`（base64 兜底）、可选 `attachment_uploads`（embed 兼容）（`src/views/chat/index.vue:1401-1403`）。
- 附件解析状态枚举 `TemporaryAttachmentStatus = 'uploaded' | 'processing' | 'ready' | 'failed'`（`src/api/chat/temporary-attachments.ts:3`），前端另加 `'local' | 'uploading'`（`src/components/AttachmentUpload.vue:24`）。
- 相关文案（`zh-CN.ts:3928-3942`）：`最多上传5张图片` / `仅支持 JPG/PNG/GIF/WEBP 格式，单张不超过 10MB` / `上传图片（支持粘贴/拖拽）` / `上传附件（文档、音频等）` / `已上传 {count} 个附件` / `最多上传 {max} 个附件` / `文件 {name} 超过 {max}MB 限制` / `不支持的文件类型：{name}` / `上传中 {progress}%` / `正在解析` / `解析完成` / `附件上传失败` / `附件解析失败` / `附件 {name} 仍在解析，请稍候`。
- 未上传完就发送会被拦：`chat.attachmentStillProcessing`（`src/components/Input-field.vue:2012-2018`）；**steer（追加）路径不允许带附件**：`input.messages.steerAttachmentPending` = `附件尚未上传完成，请稍后再追加`、`steerHasAttachments` = `进行中的回答无法附带附件，请先移除附件或等当前回答结束后再发送`（`src/components/Input-field.vue:1986-1993`，文案 `zh-CN.ts:4900-4901`）。
- 附件预览抽屉：点开用户消息里的附件卡片 → `ChatAttachmentPreviewDrawer`（`src/views/chat/components/usermsg.vue:21-42,76`，抽屉体 `src/components/ChatAttachmentPreviewDrawer.vue:138`，数据走 `previewTemporaryAttachment` = `GET /api/v1/sessions/{sid}/attachments/{aid}/preview`）。

### 2.5 @ 提及

- 触发符就是 `@`：`textBeforeCursor.endsWith('@')` 打开菜单（`src/components/Input-field.vue:1595-1605`）；也可用控制栏的 @ 按钮 `triggerMention()` 直接开菜单（不插入 `@`）（`:1665-1685,2840`）。
- 可 @ 的类型只有 5 种：`MentionItemType = 'kb' | 'file' | 'tag' | 'mcp' | 'skill'`（`src/types/mention.ts:1`）。**没有 @Agent**；Agent 是左侧下拉选的。
- 每类图标：kb → `folder`（FAQ 型 `chat-bubble-help`）、file → `file`、tag → `tag`、mcp → `tools`、skill → `system-code`（`SKILL_ICON`，`src/types/mention.ts:4`；`src/views/chat/components/botmsg.vue:163-173`）。
- 选中后**不插入文本标记**，而是变成输入框上方的 chip（`removeSelectedItem` / `allSelectedItems`，`src/components/Input-field.vue:2682-2701`），并随请求以 `mentioned_items` 数组发出（`src/components/Input-field.vue:1994-2004`）。
- 请求侧派生：`kb`/`file` 合并进 `knowledge_base_ids`/`knowledge_ids`；`tag`→`tag_ids`；`mcp`→`mcp_service_ids`；`skill`→`skill_names`（`src/views/chat/index.vue:1365-1377`）。
- 菜单本身 `src/components/MentionSelector.vue`（支持分页 `loadMore`、分组计数、空提示）。
- KB 选择另有 `KnowledgeBaseSelector` 弹层（`src/components/Input-field.vue:2936-2939`）。

### 2.6 模式 / 选项区

从左到右（都是**按文档流换行**的普通按钮，不是工具条覆盖层，`src/components/Input-field.vue:2708-2926`）：

1. **Agent 模式按钮**：显示 `selectedAgent.name || (isAgentEnabled ? input.agentMode : input.normalMode)`，即 `智能推理` / `快速问答`（`src/components/Input-field.vue:2713-2725`；文案 `zh-CN.ts:4865-4866`，描述 `normalModeDesc`=`基于知识库的 RAG 问答`、`agentModeDesc`=`多步思考，深度分析`）。下拉 `AgentSelector`（`:2728-2730`）。
2. **本地浏览器来源按钮**（仅 Agent 模式，`:2732-2753`）。
3. **联网搜索开关**：`input.webSearch.toggleOn`=`开启网络搜索` / `toggleOff`=`关闭网络搜索` / `notConfigured`=`未配置网络搜索引擎`（`zh-CN.ts:4919-4922`）；开关后的 toast `网络搜索已开启` / `网络搜索已关闭`（`zh-CN.ts:4912-4913`）。
4. **上传图片按钮**：`chat.imageUploadTooltip` = `上传图片（支持粘贴/拖拽）`（`zh-CN.ts:3930`）。
5. **上传附件按钮**：`chat.attachmentUploadTooltip` = `上传附件（文档、音频等）`（`zh-CN.ts:3931`）。
6. **@ 按钮**（知识库/文件/tag/MCP/skill）（`:2824-2840`）。
7. **模型选择**：下拉列表 + 每项右侧显示 context window；底部 `input.addModel` = `添加模型`；空列表 `input.noModel` = `暂无可用模型`（`src/components/Input-field.vue:2856-2908`；文案 `zh-CN.ts:4859,4881`）。

智能体约束会**禁用/锁定**相应控件，文案（`zh-CN.ts:4891-4896`）：`当前智能体已禁用网络搜索` / `当前智能体已锁定知识库配置` / `当前智能体已禁用知识库功能` / `当前智能体已锁定模型配置` / `当前智能体未启用图片上传` / 按钮 `去设置智能体`（`input.goToAgentSettings`）。智能体未就绪时：`input.agentNotReadyDetail` = `智能体「{agentName}」未就绪，需要配置以下内容：{reasons}`；共享智能体 `sharedAgentNotReadyDetail` = `共享智能体「{agentName}」尚未就绪（缺少：{reasons}），请联系分享方管理员完成配置。`（`zh-CN.ts:4875-4876`）；缺失项名称 `允许的工具`/`对话模型`/`重排模型`（`zh-CN.ts:4869-4872`）+ 跳转链接 `前往配置 →`（`zh-CN.ts:4874`）。

### 2.7 发送流程

1. `createSession(val, delivery, options)` 先做一串前置校验（空内容 `请先输入内容!`、回复中且不能 steer `正在回复中，请稍后再试!`、附件未上传完、附件失败、合计超 5）（`src/components/Input-field.vue:1966-2044`；文案 `zh-CN.ts:4898-4899`）。
2. 发出 `send-msg` 事件（签名见 `src/components/Input-field.vue:1951-1962`）。
3. `chat/index.vue` 的 `sendMsg`：`stopStream()` → `prepareForNewOutgoingMessage()` → 置 `isReplying/loading` → 处理图片/附件上传 → **乐观插入用户消息**（`messagesList.push({role:'user', ...})`，`src/views/chat/index.vue:1344`）→ 滚到底。
4. 端点二选一：`agentEnabled ? '/api/v1/agent-chat' : '/api/v1/knowledge-chat'`（`src/views/chat/index.vue:1379`）。
5. `startStream({...})`：`POST {base}{url}/{session_id}`，SSE（`@microsoft/fetch-event-source`）（`src/api/chat/streame.ts:83-86,166`）。请求体字段见 §9。

### 2.8 空态 / 欢迎页

- `src/views/creatChat/creatChat.vue`：大标题 `createChat.title` = `Hi，我是 WeKnora，让你的知识触手可及`（`zh-CN.ts:4851`）。
- 下面是推荐问题卡片（最多 6 张骨架→卡片），标题 `chat.suggestedQuestions` = `你可以这样问我`，刷新按钮 title/aria = `chat.refreshSuggestedQuestions` = `换一批`（`src/views/creatChat/creatChat.vue:8-45`；文案 `zh-CN.ts:3758,3761`）；FAQ 来源的卡片带 `FAQ` 角标（`:40`）。
- 会话内无消息时（`messagesList.length===0`）同样渲染推荐问题块（`src/views/chat/index.vue:47-91`），并配有 6 行骨架（`:52-63`）。

---

## 3. 回答渲染

### 3.1 非 Agent（快速问答）路径

`src/views/chat/components/botmsg.vue`：

- 结构（`:1-113`）：@提及 chips → `RagPipelineProgress`（检索时间线）→ `docInfo`（参考来源折叠块）→ markdown 正文 → `deepThink` → 底部 `answer-toolbar`。
- Markdown **一次性整段渲染**（不是 token 逐段），原因写在注释里：修 KaTeX 公式在流式中闪烁（`src/views/chat/components/botmsg.vue:359-370`）；用自定义指令 `v-stable-html` 写入（`:48`）。
- **打字机效果**在 Markdown 之前：`useTypewriter(getTarget, getComplete)` 把 SSE 全文平滑成自适应节奏的展示串（`src/views/chat/components/botmsg.vue:335-342`）。
  - 参数默认 `minCps=72`、`drainSeconds=0.42`、`maxCps=240`、`maxFrameSeconds=0.05`（`src/composables/useTypewriter.ts:89-92`）。
  - 分帧用 `requestAnimationFrame`；CJK 按 2–4 字成组，拉丁文等到词边界再吐（`src/composables/useTypewriter.ts:44-75`）。
  - `prefers-reduced-motion: reduce` 时**直接全文显示**（`:102-105,160-167`）。
- 「回答已完成」判定要等打字机追上：`answerFullyRendered = is_completed && typedAnswer.length >= answerText.length`（`src/views/chat/components/botmsg.vue:347-349`）——所以工具条不会紧贴还在滚动的文字出现。

### 3.2 Agent 路径

`src/views/chat/components/AgentStreamDisplay.vue`（约 4000 行）：把 `session.agentEventStream` 渲染成时间线（思考/工具调用/检索/沙箱/审批卡…），answer 事件也在时间线里。工具栏与 `botmsg` 基本同构（`:386-427`）。

### 3.3 Markdown 渲染范围

渲染器 `src/utils/chatMarkdownRenderer.ts`：

- 基于 `marked` + `marked-katex-extension`（`throwOnError:false, nonStandard:true`），即支持 **KaTeX 公式**（`src/utils/chatMarkdownRenderer.ts:2,52`）。
- **代码块**走可插拔 `codeRenderer`；聊天里注入的是 `createMermaidCodeRenderer('mermaid-botmsg')`，即 ` ```mermaid ` 会渲染成图（`src/views/chat/components/botmsg.vue:306-307`）；代码高亮用 highlight.js，主题在 `src/components/css/chat-hljs.less` / `chat-hljs-dark.less`。
- **表格**包一层 `.chat-markdown-table` 容器便于横向滚动（`src/utils/chatMarkdownRenderer.ts:414-421`）。
- **图片**经 `imageRenderer` → `createSafeImage`，非法 URL 替换为 `error.invalidImageLink` = `无效的图片链接`（`src/views/chat/components/botmsg.vue:308-326`，文案 `zh-CN.ts:3011`）。
- 流式稳定性做得很细：未完成的 `<kb`/`<web` 标签先隐藏（`stripIncompleteCitationTag`，`src/utils/citationMarkdown.ts:18-32`）、未闭合图片换成骨架（`chatMarkdownRenderer.ts:19`）、流式中悬空的 `---`/`**`/列表符先不渲染（`chatMarkdownRenderer.ts:189-360`）。
- 表格/强调/标题/列表都由 marked 原生支持；`sanitizeMarkdownHTML` 兜底（`src/utils/security.ts`）。
- 独立 Markdown 测试页：`/platform/dev/markdown`（`src/router/index.ts:220-222`），说明这块是有专门回归的。

### 3.4 引用角标怎么呈现

- 模型输出里的 `<kb doc="…" chunk_id="…" kb_id="…"/>`、`<web url="…" title="…"/>`、`[[wiki/slug|显示名]]` 三种标签，被改写成 HTML 角标（`src/utils/citationMarkdown.ts:146-199`）：
  - kb：`<span class="citation citation-kb" data-kb-id data-chunk-id data-doc role="button" tabindex="0">` + 图标 + **文档名（中间截断到 13 字符，超出显示 `abc...xyz`）** + 一段 `<span class="citation-tip">`（初始只有 `…`）（`:63-70,183-184`）。
  - web：`<a class="citation citation-web" data-url href target="_blank">` + 域名（取 hostname 末两段）+ tooltip 标题/URL（`:153-171`）。
  - wiki：`<a class="wiki-content-link citation-wiki" data-slug>`（`:186-198`）。
- 角标为**行内 pill**，样式集中在 `src/components/css/chat-citations.less`（`chat-citation-pills()` mixin）。
- **编号一致性靠"位置→真实 chunk UUID"解析**：模型给的是 `1`/`FAQ-2`/`DOC-3` 这种上下文序号，前端用 `resolveCitationChunkId(raw, {doc,kbId}, refs)` 按文档标题匹配 → FAQ 序数 → DOC 序数 → 数组下标 → `chunk_index` 依次回查真实 UUID（`src/utils/citationMarkdown.ts:84-143`）。**没有全局统一编号重新排版**，编号就是模型写的原文。
- 流式中角标会被"贴回上一行"并合并独立段落，避免 marked 把只有角标的 `<p>` 拆成空段（`src/utils/citationMarkdown.ts:235-301`）。

### 3.5 悬浮卡片 `ChatCitationFloat`

- 组件本体只有 36 行：`<Teleport to="body">` + 绝对定位 div，两种形态 `web` / `kb`（`src/components/ChatCitationFloat.vue:1-18`）。
- 触发：**hover 80ms（kb）/ 40ms（web）** 后打开（`src/composables/useCitationPopover.ts:152-164`）；关闭延迟 120ms，且鼠标移进浮层或角标不关（`:136-143`）。
- kb 卡片内容**按需拉取**：`GET /api/v1/chunks/by-id/{chunkId}`（`src/api/knowledge-base/index.ts:488-490`，注入点 `src/composables/useChatCitationPopover.ts:28-32`），并带进程内缓存 `citationChunkCache`（key = `scope::chunkId`，scope 默认 session id 或 `embed:<channel>:<token>`）（`src/utils/citationChunkCache.ts:5-7`，`src/composables/useChatCitationPopover.ts:23-27`）。
- 失败文案：`agentStream.citation.notFound` = `未找到内容`、`loadFailed` = `加载失败`（`src/composables/useChatCitationPopover.ts:33-34`，文案 `zh-CN.ts:1595-1596`）。
- **没有相似度分数**，卡片只显示标题（`data-doc`）+ 片段正文。

### 3.6 点击角标发生什么

`src/composables/useCitationPopover.ts:183-208`（点击是 capture 阶段委托绑定在消息根节点上）：

- 点 `.citation-web`：先尝试 `openDrawerForCitation({url})`；成功就打开右侧来源抽屉并高亮该条，否则退回打开浮层。
- 点 `.citation-kb`：先尝试 `openDrawerForCitation({chunkId})`（解析出真实 chunk id）；**成功则只开抽屉 + 高亮对应卡片**，不跳转。
- Agent 路径另有自己的委托（`src/views/chat/components/AgentStreamDisplay.vue:2366-2421`）：web 优先级为 `handleCitationActivate`；kb 打不开抽屉时**降级为新标签打开 `/platform/knowledge-bases/{kbId}`**；wiki 链接打开 KB 的 Wiki 抽屉，KB 识别不出来时提示 `agentStream.citation.noKbForWiki` = `无法识别关联的知识库，无法打开 Wiki`（`zh-CN.ts:1597`）。

> ⚠️ 结论（对方最关心的一条）：**WeKnora 的引用点击不会跳到 PDF 的具体页/具体段落**。引用粒度是 chunk（`chunk_index`），落地只有「右侧来源抽屉里高亮那张卡」，再往外只有一个「查看文档详情」链接跳到知识库详情页。引用数据自身**不带页码、不带相似度分数**（字段全集见 `src/utils/referenceSources.ts:3-14`）。

---

## 4. 引用与来源面板

### 4.1 面板壳 `src/components/ChatReferencesDrawer.vue`（604 行）

- 打开即**固定右侧面板**（`position: fixed; top/right/bottom: 0`），宽度 `min(420px, 100vw)`，`z-index: 1201`（`:337-353`）。
- 窄屏（`window.innerWidth < 960`，可通过 `overlayBreakpoint` 覆盖）或 `embeddedMode` 时切成**遮罩式浮层**并有半透明 backdrop（`:128-134,168-172,330-335`）。
- 头部：标题 + ` · {totalCount}` + 关闭按钮（`aria-label` = `common.close`）（`:11-25`）。
- 标题按内容动态选（`panelTitle`，`:181-198`）：
  `chat.referencesDrawerTitleTools`=`工具结果` / `referencesDrawerTitleMixed`=`参考来源` / `referencesDrawerTitleWeb`=`网页来源` / `referencesDrawerTitleDocs`=`文档来源` / `referencesDrawerTitle`=`参考来源`（`zh-CN.ts:3779-3783`）。
- 分节标题（`sections.length > 1` 才显示）：`referencesDrawerWebSection`=`网页` / `referencesDrawerDocsSection`=`知识库文档` / `referencesDrawerToolsSection`=`工具`（`:200-204`，文案 `zh-CN.ts:3784-3786`）。
- 空态：`chat.referencesDrawerEmpty` = `暂无参考来源`（`:28-30`，文案 `zh-CN.ts:3787`）。

### 4.2 数据装配 `src/utils/referenceSources.ts`

- 输入类型 `KnowledgeReferenceLike`（字段全集，`:3-14`）：
  `id, chunk_ids[], knowledge_id, knowledge_title, knowledge_filename, knowledge_base_id, chunk_index, chunk_type, content, metadata{}`。
  **没有 score / page / position 字段。**
- 分三路（`:262-308`）：
  - `chunk_type === 'web_search'` → web 节；
  - `chunk_type === 'tool_result'` → tools 节；
  - 其余 → documents 节。
- 文档按 `knowledge_id`（退回 `kb_id+title`）**合并**，同名文档只出一张卡；合并时 `chunk_ids` 去重并集，`content` 只取前 3 段用 `\n\n` 连接（`mergeDocumentReferences`，`:206-246`）。
- web 按规范化 URL 去重（`:248-260`）。
- 列表项字段 `ReferenceListItem`（`:16-30`）：`key, kind('web'|'document'|'tool'), index, title, url?, domain?, faviconUrl?, snippet?, chunkId?, chunkIds?, knowledgeId?, knowledgeBaseId?, content?`。
- `snippet` = `formatReferenceSnippet(content)` 压空白 + 去 Markdown 标记，**截断 220 字**（`:79-97,145,177,190`）。
- favicon 走 Google S2：`https://www.google.com/s2/favicons?domain=…&sz=32`（`:71-77`）。

### 4.3 列表项渲染

- 文档项：`file` 图标 + 标题（最多 2 行省略）+ snippet（2 行钳制）；标题右侧 hover 才出现的 `jump` 跳转图标，`aria-label` = `chat.navigateToDocument` = `查看文档详情`，href = `/platform/knowledge-bases/{kbId}?knowledge_id={docId}`（`src/components/ChatReferencesDrawer.vue:67-92,262-270`，文案 `zh-CN.ts:3842`）。
- **逐条展开**：`hasMoreContent()` 判断正文比 snippet 长时，整卡可点（`role="button"` + Enter/Space），展开后显示完整 `content`，容器 `max-height: 360px; overflow-y: auto`（`:56-65,88-90,223-231,563-572`）。展开态在关面板时清空（`:320-326`）。点击时会**忽略用户在选文本**的情况（`:233-260`）。
- web 项：favicon + 域名 + 标题（标题等于域名时不重复显示）+ snippet；整卡是 `<a target="_blank">`；favicon 加载失败就 `display:none`（`:94-119,218-221,272-277`）。
- 工具项：`tools` 图标 + 来源名 + 全文内容（不折叠）（`:106-118`）。
- **排序**：不重排，就是 `knowledge_references` 原始顺序经合并后的顺序（web / documents / tools 三节固定顺序）。**没有相似度排序、没有超出"按节/按关键词"的筛选**。

### 4.4 高亮与滚动（点击角标后的落点）

- 高亮 key 由 `resolveReferenceHighlightKey(refs, target)` 解析（`src/utils/referenceSources.ts:324-371`）：先 `target.key`，再按 URL 规范化匹配，再按 chunkId / chunkIds / `doc:{raw}`，最后用「文档标题 + kbId」兜底（注释说明这是给历史/流式不全的 Agent 消息兜底的，`:353-368`）。
- 面板里对应卡片加 `is-highlighted` 类（`src/components/ChatReferencesDrawer.vue:50,449-451`），并 `scrollTo` 到该卡（在面板容器内滚动，留 8px 边距；注释特意说不能用原生滚动以免整页跳）（`:279-318`）。
- 每次 `highlight` 对象变化都会重放滚动（同一张卡再点一次也能滚回去）（`:313-318`）。

### 4.5 入口都是谁

- 非 Agent 回答：`docInfo.vue` 的「参考了 N 个相关内容」折叠头 —— **点标题头不再展开本地列表，而是改开右侧抽屉**（`src/views/chat/components/docInfo.vue:100-107`）。
- `docInfo` 折叠头文案（`headerText`，`:144-158`）：
  `chat.referencesDocCount`=`引用了{count}篇文档` / `referencesWebCount`=`参考了{count}条网页` / `referencesDocAndWebCount`=`引用了{docCount}篇文档和{webCount}条网页` / 兜底 `referencesTitle`=`参考了{count}个相关内容`（`zh-CN.ts:3775-3778`）。
- `docInfo` 里每篇文档再分组展开到 chunk 级：组头 `文件名` + `chat.referenceChunkCount`=`{count}个片段`（`zh-CN.ts:3829`），每条 chunk 前缀 `chat.chunkLabel`=`片段{index}:`（`zh-CN.ts:3841`），点 chunk 弹 `t-popup`（宽 400，最大高 400）显示带 HTML 的片段内容（`src/views/chat/components/docInfo.vue:23-57`）。
- 检索时间线 `RagPipelineProgress` 的检索步骤也能开抽屉（`src/views/chat/components/RagPipelineProgress.vue:263,287`）。
- Agent 时间线里的工具卡（`canOpenToolReferences`）同样开抽屉（`src/views/chat/components/AgentStreamDisplay.vue:1462-1467`）。

---

## 5. 文档预览

组件 `src/components/document-preview.vue`（1244 行）+ 依赖 `src/utils/filePreview.ts`。

### 5.1 它是什么形态

- **不是抽屉**，是一个普通容器 div（`.document-preview`，`min-height: 200px`），由**宿主**决定放在抽屉里还是页面里：`.chat-references-panel` 那种右侧抽屉里由 `ChatArtifactsDrawer` / `ChatArtifactPanel` / `ArtifactLibrary` / `ChatAttachmentPreviewDrawer` 承载。
- **全屏**：优先用原生 Fullscreen API `root.requestFullscreen()`（多屏/iframe 里的 Escape 也能处理），失败则退回"body overflow hidden + `is-fullscreen` 类"（`src/components/document-preview.vue:123-181`）。工具栏按钮文案 `preview.fullscreen`=`全屏预览` / `preview.exitFullscreen`=`退出全屏`（`:508-513`，文案 `zh-CN.ts:1851-1852`）。
- **没有宽度拖拽**（未见 resizer）；宽度由宿主给（产物抽屉用 `min(880px, 92vw)`，`src/views/artifacts/ArtifactLibrary.vue:132`）。
- 工具栏可被 `toolbarTarget` **Teleport 到宿主头部**，和宿主的下载按钮排在一起（`:495-516`；用法见 `src/views/artifacts/ArtifactLibrary.vue:149,178`）。
- 有一份专门的焦点契约测试 `src/components/document-preview.focus.test.mjs`：打开预览要把焦点给到真正的滚动元素且 `preventScroll: true`，且**绝不抢输入框/工具栏焦点**；每个可滚动目标都要可 tab（`:47-143`）。

### 5.2 props（全部在 `src/components/document-preview.vue:35-48`）

| prop | 类型 | 含义 |
|---|---|---|
| `sourceBlob` | `Blob?` | 直接给字节（受保护资源预览用） |
| `knowledgeId` | `string?` | 知识库文档 id |
| `sessionId` | `string?` | 会话 id（附件/产物用） |
| `attachmentId` | `string?` | 临时附件 id |
| `messageId` | `string?` | 产物所属 assistant 消息 id |
| `artifactIndex` | `number?` | 产物在该消息里的序号 |
| `fileType` | `string` | 扩展名/MIME |
| `fileName` | `string` | 文件名（同时是 aria-label） |
| `active` | `boolean` | 是否可见；**只有 true 才加载**，false 会退出全屏 |
| `fillHeight` | `boolean?` | 撑满宿主高度 |
| `toolbarTarget` | `HTMLElement?` | 工具栏 Teleport 目标 |

**没有 emit**（无 `defineEmits`）；对外沟通全靠 props 与宿主的 ref。

调用方举例：`src/components/doc-content.vue:2136`（KB 文档详情，`:knowledgeId`）、`src/views/artifacts/ArtifactLibrary.vue:176-186`（`:sessionId/:messageId/:artifactIndex/:toolbarTarget`）、`src/views/chat/components/ChatArtifactsPanel.vue:37-46`、`src/components/ChatAttachmentPreviewDrawer.vue:138`、`src/components/ProtectedResourcePreview.vue:26`（`:sourceBlob`）。

### 5.3 支持哪些类型、各怎么渲染

`loadPreview()` 按 `resolvePreviewKind(ext)` 分派；扩展名未知时**读前 16KB 做魔数/内容嗅探**再决定（`src/components/document-preview.vue:379-447`，`FILE_PREVIEW_SNIFF_BYTES = 16384`，`src/utils/filePreview.ts:231,367-408`）。

| kind | 渲染方式 | 依据 |
|---|---|---|
| `pdf` | `URL.createObjectURL(blob)` + **`<iframe src>`**（浏览器原生 PDF 阅读器） | `document-preview.vue:405-411,541-543` |
| `image` | `<img>` + 显示 `宽 × 高 px` | `:562-569` |
| `docx` | `await import('docx-preview')` → `renderAsync(blob, container, …)`，参数含 `breakPages:true`、`useBase64URL:true` | `:211-228,572-574` |
| `pptx` | `@vue-office/pptx`（异步组件），先 `preparePptxPreview` 再喂 `ArrayBuffer`，渲染不完整会报错 | `:31,436-442,577-579`，`src/utils/pptxPreview.ts` |
| `excel` | `await import('xlsx')` → `sheet_to_html` 逐 sheet 输出（多 sheet 加 sheet 名标题）；CSV/TSV 先解码（BOM→UTF-8→GBK 兜底） | `:230-269,581-584` |
| `markdown` | `renderDocumentPreviewMarkdown(text)` → `v-html` | `:289-299,587-589`，`src/utils/documentPreviewMarkdown.ts` |
| `text`/代码 | `highlight.js`（先按扩展名指定语言，失败再 `highlightAuto`），JSON 类先 `prettyPrintJson` | `:271-287,592-594` |
| `html` | **分两种**：产物（`artifact:` 源）用 `sandbox="allow-scripts"` 的 iframe 渲染，可切「渲染预览 / 查看源码」；知识库文件与会话附件当作不可信上传，只显示源码 | `:324-329,377,412-419,500-507,546-559` |
| `mermaid` | `renderMermaidToSvg` → v-html，点击可开全屏图查看器 `openMermaidFullscreen` | `:350-367,596-599` |
| `audio` / `video` | 原生 `<audio controls>` / `<video controls playsinline>` | `:601-617` |
| `unsupported` | 图标 + `preview.unsupported`=`该文件类型暂不支持在线预览` + `preview.unsupportedHint`=`请下载文件后使用本地应用查看` | `:533-538`，文案 `zh-CN.ts:1849-1850` |

扩展名→kind 的完整登记表在 `src/utils/filePreview.ts:38-79`（注意 `.doc`/`.ppt` **故意不登记**，因为 docx-preview/pptx 解析不了 OLE2，会退化为"不支持"状态，注释见 `:39-42`）。

### 5.4 页码跳转 / 缩放 / 页内查找 / 「定位到命中段」

- **页码跳转：没有。** PDF 只是一个 `<iframe>` 指向 blob URL，没有页码参数、没有 pdf.js。
- **缩放：没有。** 只有图片显示原始像素尺寸（`:565-567`）。
- **页内查找：没有。**
- **「定位到命中段」：没有。** `document-preview.vue` 里**不存在** `focus(chunk)` / `scrollIntoView`（对命中段的定位）/ `highlight` 命中高亮的任何实现——它唯一的 `focus` 逻辑是**键盘可达性**（把焦点给滚动容器，见 5.1）。这一点可用两份测试反证：`document-preview.focus.test.mjs` 全篇只断言焦点行为，`document-preview.fullscreen.test.mjs` 只断言全屏行为，都没有"命中高亮/跳转"的字样。
- 所以整条链是：**角标点击 → 右侧来源抽屉高亮该 chunk 卡（§4.4）→（可选）「查看文档详情」跳到知识库详情页 → 在详情页手动切到「预览」tab 看原文**，没有任何一步能把页面滚到、或高亮到命中的那一段。

### 5.5 字节从哪来（三种源，都带鉴权）

`fetchPreviewBlob()`（`src/components/document-preview.vue:331-348`）：

| 源 | 接口 |
|---|---|
| `sourceBlob` | 调用方自己取（受保护资源） |
| `knowledgeId` | `previewKnowledgeFile(id)` = `GET /api/v1/knowledge/{id}/preview`（`src/api/knowledge-base/index.ts:435-437`） |
| `sessionId`+`attachmentId` | `previewTemporaryAttachment` = `GET /api/v1/sessions/{sid}/attachments/{aid}/preview`（`src/api/chat/temporary-attachments.ts:51-53`） |
| `sessionId`+`messageId`+`artifactIndex` | `downloadArtifact` = `GET /api/v1/sessions/{sid}/messages/{mid}/artifacts/{index}/download`，返回 Blob（`src/api/chat/index.ts:136-144`） |

- 注释明确说明：**不能用 `<a href>` 直接下载**，因为要带 Bearer token，所以统一走 axios 拿 Blob 再转 object URL（`src/api/chat/index.ts:131-135`）。
- 缓存键 `getPreviewSourceKey()` 由这些 props 拼成（`src/components/document-preview.vue:307-322`），同一 key 不重复加载；`cleanup()` 里 `URL.revokeObjectURL`（`:456-475`）。
- 加载/错误态文案：`preview.loading` = `正在加载文档预览...`、`preview.loadFailed` = `加载文档预览失败`、`preview.retry` = `重试`（`:519-531`，文案 `zh-CN.ts:1846-1848`）。

### 5.6 预览里的命中片段与引用列表是否同一份数据

- **不是。** 预览只认 `knowledgeId`/`attachmentId`/`artifactIndex`，**不认识 chunk**；引用列表（§4）的数据是 SSE `references` 事件落到 `message.knowledge_references` 的那份。
- `doc-content.vue` 里能看到双轨：`viewMode: 'chunks' | 'merged' | 'preview'`（`src/components/doc-content.vue:546`），`chunks` 视图显示 chunk 列表（带启用开关、编辑、版本历史 diff），`preview` 视图才挂 `DocumentPreview`；三个视图**互不联动**，切到 preview 不会带上当前 chunk。

### 5.7 知识库详情页里的预览 UI

- 视图切换按钮：`preview.tab`=`预览` / `knowledgeBase.viewMerged`（全文）/ `knowledgeBase.viewChunks`（分块）（`src/components/doc-content.vue:1821-1837`）。
- 文件类型默认视图：file 类型默认 `preview`，音频类型用 `merged` + 播放器（`src/components/doc-content.vue:751-765`）。
- `doc-content.vue` 是 `t-drawer` 里的一个内容块，props 为 `["visible","details","knowledgeType","sourceInfo","canEditKB","canDownloadKB","parse_status","kbId"]`，emit 为 `["closeDoc","getDoc","questionDeleted","summaryStateChange"]`（`src/components/doc-content.vue:244-245`）。

---

## 6. 产物（artifacts）

### 6.1 产物库页 `src/views/artifacts/ArtifactLibrary.vue`

- 头部：`artifactLibrary.title` = `产物`，副标题 `artifactLibrary.subtitle` = `智能体在各个会话中生成的文件，都会汇总在这里`（`:5-6`，文案 `zh-CN.ts:7362-7363`）。
- 类型筛选 tab（`role="tablist"`，`aria-label`=`按类型筛选`）：全部 / 文档 / 表格 / 演示文稿 / 图片 / 网页 / 数据（`:11-22`，文案 `zh-CN.ts:7364,7366-7374`）。分类到扩展名映射见 `src/utils/artifactLibrary.ts:17-24`（如 document = `.pdf .doc .docx .md .txt .rtf .odt`）。
- 搜索框 placeholder `artifactLibrary.searchPlaceholder` = `搜索文件名`，300ms 防抖（`:23-31,213`）。
- 列表：**按日期分组**（今天 / 昨天 / 最近 7 天 / 最近 30 天 / 更早，`artifactLibrary.groups.*`，文案 `zh-CN.ts:7375-7381`；纯函数 `artifactDateGroup`，`src/utils/artifactLibrary.ts:38-51`）。
- 每行：文件类型图标 + 文件名 + `大小 · 时间`（>1 版本时追加 `{count} 个版本`）+ 「打开所在会话」按钮（icon `chat` + 会话标题，空则 `未命名会话`）+ 下载按钮（`:70-115`，文案 `zh-CN.ts:7382-7388`）。
- 分页：`PAGE_SIZE = 30`（`:212`），滚动 sentinel 自动加载 + 兜底「加载更多」按钮（`:119-124`，文案 `加载更多`）。
- **预览**：点行 → 右侧 `t-drawer`（`size="min(880px, 92vw)"`）内嵌 `DocumentPreview`，`:toolbar-target` 指向抽屉头部（`:128-188`）。
- 空态 / 错误态（`EmptyState` 组件）：
  - 加载失败：`artifactLibrary.loadFailed` = `产物加载失败` + 按钮 `重试`（`:42-48`）；
  - 有筛选但无结果：`没有匹配的文件` / `换个关键词或文件类型试试` + `清除筛选`（`:50-57`）；
  - 完全没有：`还没有产物` / `在对话中让智能体生成报告、表格或演示文稿，文件会出现在这里`（`:59-64`）；
  - 骨架 6 行（`:35-40`）。
- 下载失败 `artifactLibrary.downloadFailed` = `下载失败，请稍后重试`（`zh-CN.ts:7386`）。
- 数据源：`listArtifactLibrary(params)` = `GET /api/v1/artifacts?keyword=&file_types=&page=&page_size=`（`src/api/artifacts.ts:41-48`）。

### 6.2 会话内产物面板 / 抽屉

- 消息工具栏上的产物按钮**按需出现**：只有该 assistant 消息真的记录了 artifacts 才渲染，进行中显示 loading 图标（`src/views/chat/components/botmsg.vue:66-81`）。tooltip 文案 `agent.artifactDrawer.buttonTitle`=`查看本次生成的文件` / `collecting`=`正在保存生成的文件…`（`zh-CN.ts:6312,6317`）；按钮上还有数量角标（`botmsg.vue:80`）。
- 桌面端打开的是沙箱侧板的「产物」tab，embed 端才用 `ChatArtifactsDrawer`（`src/views/chat/components/botmsg.vue:266-281`）。
- 面板 `src/views/chat/components/ChatArtifactsPanel.vue`：
  - 作用域切换「本轮 / 全部」= `chat.sandbox.artifactsCurrent`/`artifactsAll`（`:58-73`）；
  - 搜索 `chat.sandbox.artifactsSearch` = `搜索文件名`（`:74-83`）；
  - 空态 `chat.sandbox.artifactsEmpty` = `本会话尚未生成可下载的文件`、无匹配 `artifactsNoMatches` = `没有匹配的文件`（`:49-56,88-91`；文案 `zh-CN.ts:3793,3798`）；
  - 点条目进 `DocumentPreview`，头部「返回列表」`agent.artifactDrawer.previewBack`=`返回列表`（`:3-16`）。
- 沙箱侧板标题 `chat.sandbox.panelTitle` = `沙箱可视化`，三个 tab `产物 / 终端 / 桌面`（`zh-CN.ts:3789-3791`）。
- 产物在 Markdown 正文里也能内联出现：`resource://` 形式的图片若命中该消息的 artifacts，会渲染成「点击预览」卡片；`agent.artifactDrawer.inlinePreviewHint`=`点击预览` / `inlineMissing`=`文件不可用`（`src/views/chat/components/botmsg.vue:308-321,289-292`，文案 `zh-CN.ts:6320-6321`）。
- 产物到达有入场动画（`useArtifactArriveMotion`，`botmsg.vue:255`）。

---

## 7. 消息级操作

### 7.1 用户消息（`src/views/chat/components/usermsg.vue`）

- 展示：@提及 chips、上传的图片缩略图（可点开大图）、附件卡片（可点开预览抽屉）、正文、时间戳（`:1-62`）。
- 操作只有两个（`:46-62`）：**复制**（tooltip `agent.copy` = `复制`，`zh-CN.ts:6309`）与 **分叉 fork**（`git-branch`，tooltip 是**硬编码中文 `从这里分叉出新会话`**，`src/views/chat/components/usermsg.vue:146`）。
  > 更正（我自己写错过）：初稿写"usermsg 与 botmsg 用同一 forkTooltip"——**是错的**。两处文案不同：用户消息侧 = `从这里分叉出新会话`（`usermsg.vue:146`），助手回答侧 = `从这条回答继续分叉`（`src/views/chat/components/botmsg.vue:224`）。且两处都没走 i18n。
- steer 失败时行内出现失败条：文案 `正在回复中，请稍后再试!` 那一族的 `input.messages.steerFailed` = `追加失败，请重试`，带「重试发送」`input.steerRetry`=`重试发送` 与删除按钮（`src/views/chat/components/usermsg.vue:63-67`，文案 `zh-CN.ts:4902,4887`）。
- **没有「编辑重问」**：想改问题只能靠 fork 后在前端 prefill（见 7.3）。

### 7.2 助手消息（`src/views/chat/components/botmsg.vue:52-96`，Agent 同理 `AgentStreamDisplay.vue:386-427`）

出现条件是 `answerFullyRendered`（打字机追平且后端 complete）：

1. **分叉**（可 fork 时）`git-branch`，tooltip `从这条回答继续分叉`（`botmsg.vue:53-57,224`）；
2. **复制回答** `copy`，tooltip `agent.copy`=`复制`；空内容时 toast 用 `chat.emptyContentWarning`（`botmsg.vue:58-61,384-392`）；
3. **添加到知识库** `bookmark-add`，tooltip `agent.addToKnowledgeBase`=`添加到知识库`（`:62-65`）；行为是**打开手工编辑器**（`uiStore.openManualEditor`，mode `create`，标题来自问题、正文由 `buildManualMarkdown` 拼），toast `chat.editorOpened`（`:395-414`，文案 `zh-CN.ts:6310`）；
4. **产物下载**（条件显示，见 §6.2）；
5. **fallback 提示图标**：`session.is_fallback` 时显示 info 图标，tooltip `chat.fallbackHint` = `未从知识库中检索到相关内容，以上为模型直接回答`（`:82-87`，文案 `zh-CN.ts:3830`）；
6. **请求信息**按钮 `ChatRequestInfoButton`（可看 Request ID / 消息 ID / 会话 ID / 请求 URL / 发起时间，文案 `chat.requestInfo*`，`zh-CN.ts:3831-3837`）；
7. **追问加载中**提示（灯泡 + `chat.followUpQuestionsLoading` = `加载推荐问题`，`botmsg.vue:89-95`，文案 `zh-CN.ts:3760`）。

**没有点赞/点踩/评分/反馈**（全仓 grep `thumbs|feedback|like-|dislike|rating` 无相关命中）。

### 7.3 分叉（fork）

- `POST /api/v1/sessions/{sid}/fork`，body `{message_id, title?}`，前端超时给到 180s（`src/api/chat/index.ts:33-38`）。
- 新会话标题 = `{原标题}（分支）`（`src/views/chat/index.vue:387-397`），侧栏新行有入场动画（`src/components/menu.vue:486-523`）。
- 问题文本通过 `sessionStorage`（key `weknora:fork-prefill`）带到新会话并 **prefill 但不自动发送**（注释说明了原因：让用户落在分支上改问题）（`src/views/chat/index.vue:321-364`，`src/components/Input-field.vue:2630-2632`）。
- 失败兜底：409 时 `请等本轮回答结束后再分叉`；其他 `分叉失败，请重试`（`src/views/chat/index.vue:400-408`）。

### 7.4 会话级操作（`src/components/ChatHeader.vue` 顶部 `…` 菜单）

`chatHeader.*`（文案 `zh-CN.ts:7333-7359`）：

| 菜单项 | key | 原文 | 实现 |
|---|---|---|---|
| 更多对话操作（按钮 aria） | `moreActions` | `更多对话操作` | `:44` |
| 置顶/取消置顶 | `menu.pin/unpin` | `置顶`/`取消置顶` | `:53-56` |
| 修改标题 | `menu.renameSession` | `修改标题` | `:57-60` |
| 复制会话 ID | `copySessionId` | `复制会话 ID` | `:62-65`，成功 `会话 ID 已复制` |
| 复制对话链接 | `copyLink` | `复制对话链接` | `:66-69`，成功 `对话链接已复制` |
| 复制为 Markdown | `copyMarkdown` | `复制为 Markdown` | `:70-73`，**导出整段对话为 Markdown 并写剪贴板**，成功 `完整对话已复制为 Markdown`、失败 `复制 Markdown 失败，请稍后重试` |
| 在新窗口中打开 | `openNewWindow` | `在新窗口中打开` | `:74-77` |
| 清空消息 | `menu.clearMessages` | `清空消息` | `:79-82` |
| 删除对话 | `chatHeader.deleteSession` | `删除对话` | `:83-86` |

- 清空确认：标题 `清空对话消息`，正文 `确认清空当前对话的全部消息？对话本身会保留，此操作无法恢复。`（`zh-CN.ts:7347-7348`）；成功 `menu.clearMessagesSuccess`=`消息已清空`，失败 `清空消息失败，请稍后再试`（`zh-CN.ts:7412-7413`）。
- 删除确认：标题 `删除对话`，正文 `确认删除当前对话？删除后将无法恢复。`（`zh-CN.ts:7349-7350`）；成功 `对话已删除`。
- 复制链接会剥掉 query 与 hash（`src/components/ChatHeader.vue:187-192`）。剪贴板失败统一 `chatHeader.copyFailed` = `复制失败，请检查浏览器剪贴板权限`（`zh-CN.ts:7344`）。
- Markdown 导出的字段标签：`会话 ID` / `导出时间` / `用户` / `助手` / `附件` / `引用`（`zh-CN.ts:7352-7359`），实现 `src/utils/sessionMarkdown.ts`（`collectAllSessionMessages` 会**翻页拉全部历史**再拼，`src/components/ChatHeader.vue:274-297`）。
- 「清空上下文」= 上面的「清空消息」，接口 `DELETE /api/v1/sessions/{sid}/messages`（`src/api/chat/index.ts:87-89`）；前端还会 `messagesList.splice(0)` 并重取推荐问题（`src/views/chat/index.vue:1508-1515`）。

### 7.5 追问建议（Follow-up）

- 组件 `src/components/chat/FollowUpSuggestions.vue`：标题 `chat.followUpQuestions` = `继续问`，刷新按钮 `chat.refreshSuggestedQuestions` = `换一批`，每条按钮带 `arrow-up-right` 图标（`:3-25`，文案 `zh-CN.ts:3759,3761`）。
- 数据：`ensureMessageSuggestions`/`getMessageSuggestions`（`GET|POST /api/v1/sessions/{sid}/messages/{mid}/suggestions`），前端对 `status === 'generating'` **每秒轮询最多 120 次**（`src/views/chat/index.vue:565-588`）；状态枚举 `'generating' | 'ready' | 'suppressed' | 'failed'`（`src/api/message-suggestion.ts:15`）。
- 埋点：`impression` / `click` / `dismiss` → `POST /api/v1/sessions/{sid}/suggestion-events`（`src/api/message-suggestion.ts:35-45`，调用 `src/views/chat/index.vue:590-612`）。

### 7.6 中断与追加（steer）

- 生成中可以在同一输入框继续打字，Enter（或发送按钮）会**追加到当前 turn**：`delivery='after'` 排队 / `'inject'` 立刻注入（见 §2.2）。
- 接口：`POST /api/v1/sessions/{sid}/steer`（body 含 `query, expected_assistant_message_id, steer_id, mentioned_items, channel:'web', delivery`），`POST …/steer/{id}/inject` 提前注入，`GET …/steer` 读队列，`DELETE …/steer/{id}` 丢弃（`src/api/chat/steer.ts:29-60`）。
- 队列 UI 紧贴输入框上方：`time` 图标 + 内容 + 「立即发送」（tooltip `当前回答结束后发送` 之类）+ 删除；失败显示重试（`src/components/Input-field.vue:2642-2664`，文案 `zh-CN.ts:4884-4890`）。
- `delivery` 枚举真源：`export type SteerDelivery = 'inject' | 'after'`（`src/api/chat/steer.ts:3`）。

---

## 8. 状态与反馈（文案原文）

### 8.1 空态

| 场景 | 文案 | 位置 |
|---|---|---|
| 侧栏该来源下无会话 | `暂无对话` | `src/components/menu.vue:133` / `zh-CN.ts:7429` |
| 新会话欢迎页标题 | `Hi，我是 WeKnora，让你的知识触手可及` | `src/views/creatChat/creatChat.vue:5` / `zh-CN.ts:4851` |
| 推荐问题标题 | `你可以这样问我` | `zh-CN.ts:3758` |
| 来源抽屉无来源 | `暂无参考来源` | `zh-CN.ts:3787` |
| 产物库无产物 | `还没有产物` / `在对话中让智能体生成报告、表格或演示文稿，文件会出现在这里` | `zh-CN.ts:7394-7395` |
| 本会话无产物 | `本会话尚未生成可下载的文件` | `zh-CN.ts:3793` |
| 无可用模型 | `暂无可用模型` | `zh-CN.ts:4881` |

### 8.2 加载 / 检索中

- 历史消息骨架屏：4 块（2 个用户条 + 2 段回答条），`t-skeleton animation="gradient"`（`src/views/chat/index.vue:29-46`）。
- 推荐问题骨架：标题 120×14 + 6 张卡（`src/views/chat/index.vue:52-63`）。
- 侧栏会话骨架 4 行（`src/components/menu.vue:113-131`）。
- 检索/流水线时间线 `RagPipelineProgress`，关键文案（`zh-CN.ts:1546-1553`）：
  - `正在检索知识库...` / `正在检索知识库：「{query}」`
  - `正在检索网络...` / `正在检索网络：「{query}」`
  - `正在检索知识库和网络...` / `正在检索知识库和网络：「{query}」`
  - `检索完成`
- 检索后的等待行（`chat.*`）：
  - `chat.preparingAnswer` = `正在准备回答…`
  - `chat.connectingModelAndGeneratingAnswer` = `正在连接模型并生成回答…`
  - `chat.modelStillResponding` = `模型响应较慢，仍在等待…`（**60 秒无输出才切这句**）
  - 实现：`RAG_WAIT_REVEAL_DELAY_MS = 250`（快速回答不闪）、`RAG_WAIT_STALL_DELAY_MS = 60_000`（`src/utils/rag-pipeline-state.ts:2,9`；文案 `src/views/chat/components/RagPipelineProgress.vue:416-421`）
- 「思考中」：`chat.thinking` = `思考中...`、`chat.thinkingAlt` = `正在思考`、完成后 `chat.deepThoughtCompleted` = `已深度思考`、`chat.deepThoughtAlt` = `深度思考完成`（`src/views/chat/components/deepThink.vue:10,14`，文案 `zh-CN.ts:3762-3763,3773-3774`）。
- 全局等待指示器（有 loading 但还没有 assistant 行时）：一个 spinner，`role="status"`，`aria-label` = `正在思考`（`src/views/chat/index.vue:141-144`；判定 `shouldShowGlobalTypingIndicator`，`src/composables/useChatStreamHandler.ts:274-284`）。
- 工具/步骤运行文案在 `agentStream.toolStatus.*`（如 `正在调用 {name}...`、`检索知识库`、`检索知识库失败`、`网络搜索失败`、`正在解析附件...`，`zh-CN.ts:1517-1544`）。
- 工具结果状态枚举（MCP）：`not_loaded / loading / ready / needs_auth / error / disabled / unavailable` → `未加载/加载中/可用/需要授权/连接失败/已禁用/不可用`（`zh-CN.ts:1507-1515`）。

### 8.3 出错

- 流式连接失败：`error.streamFailed` = `流式连接失败`，包在 `Error` 里（`src/api/chat/streame.ts:211`）。
- 未登录/令牌问题：`error.tokenNotFound` = `未找到登录令牌，请重新登录`（`src/api/chat/streame.ts:58`）；`error.pleaseRelogin` = `请重新登录`、`error.tokenRefreshFailed` = `Token刷新失败`（`src/api/chat/streame.ts:226-230`）。
- 通用错误：`error.networkError` = `网络错误，请检查您的网络连接`、`error.requestTimeout` = `请求超时，文件较大或网络较慢时请稍后重试`（`zh-CN.ts:3003-3004`）。
- 后端 `response_type === 'error'` 且不带工具名 → 把 `data.content`（空则 `chat.processError` = `处理出错`）写进消息正文并 toast（`src/composables/useChatStreamHandler.ts:871-891`，文案 `zh-CN.ts:3923`）。
- 历史加载失败只 `console.error`，不弹 toast（`src/views/chat/index.vue:908-912`）。
- IM 会话挂不上流时静默轮询恢复：2.5s × 最多 48 次（≈2 分钟），期间显示"生成中"（`src/views/chat/index.vue:1417-1424`）。
- 停止失败会回滚成"仍在回复"（`handleStopFailed`，`src/views/chat/index.vue:939-942`）。
- 模型/智能体不可用**不是运行时 toast**，而是发送前就禁用/提示：见 §2.6 的 `agentNotReadyDetail` / `已锁定` / `未启用` 系列文案（`zh-CN.ts:4869-4896`）。
- 附件相关失败文案见 §2.4。

### 8.4 引用悬浮失败

`未找到内容`（`agentStream.citation.notFound`）/ `加载失败`（`agentStream.citation.loadFailed`）（`zh-CN.ts:1595-1596`）。

---

## 9. 接口清单（方法 + 路径 + 用途，逐条从 api 层核出）

### 9.1 会话 / 消息（`src/api/chat/index.ts`）

| 方法 | 路径 | 用途 | 行 |
|---|---|---|---|
| POST | `/api/v1/sessions` | 新建会话（body 可为 `agent_config`） | `:5-7` |
| GET | `/api/v1/sessions?page&page_size&source` | 会话列表（按来源分页） | `:9-15` |
| GET | `/api/v1/sessions/{id}` | 会话详情（含 `last_request_state`） | `:79-81` |
| PUT | `/api/v1/sessions/{id}` | 改标题/描述 | `:29-31` |
| DEL | `/api/v1/sessions/{id}` | 删单条 | `:67-69` |
| DEL | `/api/v1/sessions/batch` | 批量删除（`{ids}` 或 `{delete_all:true}`） | `:71-77` |
| POST | `/api/v1/sessions/{id}/pin` / DEL 同路径 | 置顶 / 取消置顶 | `:17-23` |
| POST | `/api/v1/sessions/{id}/generate_title` | 生成标题 | `:25-27` |
| POST | `/api/v1/sessions/{id}/fork` | 从某条消息分叉（180s 超时） | `:33-38` |
| POST | `/api/v1/sessions/{id}/stop` | 停止生成（`{message_id}`） | `:83-85` |
| DEL | `/api/v1/sessions/{id}/messages` | 清空消息 | `:87-89` |
| GET | `/api/v1/messages/{sid}/load?before_time&limit` | 历史消息（向上翻页游标 = 最早一条 `created_at`） | `:59-65` |
| POST | `/api/v1/knowledge-chat/{sid}` | 快速问答（非流式封装的 postChat；实际聊天走 SSE） | `:40-42` |
| POST | `/api/v1/agent-chat/{sid}` | Agent 问答 | `:45-57` |

### 9.2 聊天 SSE（`src/api/chat/streame.ts`）

- 真正发消息走 `fetchEventSource`，URL = `${apiBase}${params.url}/${session_id}`，请求头含 `Authorization: Bearer …`（或 `Embed …`）、`Accept-Language`、`X-Request-ID`、可选 `X-Tenant-ID` / `X-Embed-Session` / `X-Embed-Visitor`（`:83-86,166-176`）。
- `method: 'POST'` 用于 `agent-chat`/`knowledge-chat`；`method: 'GET'` 且 `query=assistantMessageId` 用于 **恢复在跑的流**：`/api/v1/sessions/continue-stream`（`src/views/chat/index.vue:837-842`）。
- 请求体字段全集（`:91-153`）：`query, agent_enabled, knowledge_base_ids, knowledge_ids, agent_id, agent_source_tenant_id, web_search_enabled, local_browser_enabled, summary_model_id, mcp_service_ids, skill_names, tag_ids, mentioned_items, images, attachment_uploads, attachment_ids, suggestion_attribution, question_origin, channel('web'|'embed')`。
- 401 可恢复：刷新 token 后**重放一次**（`:184-190,219-231`）。

### 9.3 引用 / 检索

| 方法 | 路径 | 用途 | 出处 |
|---|---|---|---|
| GET | `/api/v1/chunks/by-id/{chunkId}` | 悬浮卡片/来源定位拉 chunk 正文 | `src/api/knowledge-base/index.ts:488-490` |
| POST | `/api/v1/knowledge-search` | 命令面板语义检索知识片段 | `src/api/knowledge-base/index.ts:688-693` |
| POST | `/api/v1/messages/search` | 命令面板搜历史问答（keyword/vector/hybrid） | `src/api/chat-history.ts:62-65` |
| GET | `/api/v1/messages/chat-history-stats` | 对话历史 KB 统计 | `src/api/chat-history.ts:57-60` |
| GET/PUT | `/api/v1/tenants/kv/chat-history-config` | 对话历史索引配置 | `src/api/chat-history.ts:47-55` |

### 9.4 附件 / 预览 / 产物

| 方法 | 路径 | 用途 | 出处 |
|---|---|---|---|
| POST | `/api/v1/sessions/{sid}/attachments` | 上传临时附件（图片也走这里） | `src/api/chat/temporary-attachments.ts:25-45` |
| GET | `/api/v1/sessions/{sid}/attachments/{aid}` | 查询附件状态 | `:47-49` |
| GET | `/api/v1/sessions/{sid}/attachments/{aid}/preview` | 附件字节（预览） | `:51-53` |
| DEL | `/api/v1/sessions/{sid}/attachments/{aid}` | 删附件 | `:55-57` |
| GET | `/api/v1/knowledge/{id}/preview` | 知识库文档字节（预览） | `src/api/knowledge-base/index.ts:435-437` |
| GET | `/api/v1/artifacts?keyword&file_types&page&page_size` | 产物库列表 | `src/api/artifacts.ts:41-48` |
| GET | `/api/v1/sessions/{sid}/messages/{mid}/artifacts` | 单条消息的产物 | `src/api/chat/index.ts:118-122` |
| GET | `/api/v1/sessions/{sid}/artifacts` | 整个会话的产物 | `src/api/chat/index.ts:127-129` |
| GET | `/api/v1/sessions/{sid}/messages/{mid}/artifacts/{index}/download` | 产物下载（Blob） | `src/api/chat/index.ts:136-144` |

### 9.5 追问建议 / 追加 / 其他

| 方法 | 路径 | 用途 | 出处 |
|---|---|---|---|
| POST/GET | `/api/v1/sessions/{sid}/messages/{mid}/suggestions` | 生成 / 读取追问建议 | `src/api/message-suggestion.ts:22-33` |
| POST | `/api/v1/sessions/{sid}/suggestion-events` | 建议埋点（impression/click/dismiss） | `src/api/message-suggestion.ts:35-45` |
| POST | `/api/v1/sessions/{sid}/steer` | 追加消息到运行中的 turn | `src/api/chat/steer.ts:29-45` |
| POST | `/api/v1/sessions/{sid}/steer/{steer_id}/inject` | 把排队项改成立即注入 | `src/api/chat/steer.ts:47-50` |
| GET | `/api/v1/sessions/{sid}/steer` | 读队列（含 `assistant_message_id`） | `src/api/chat/steer.ts:52-55` |
| DEL | `/api/v1/sessions/{sid}/steer/{steer_id}` | 丢弃排队项 | `src/api/chat/steer.ts:57-59` |
| GET | `/api/v1/agents/{id}/suggested-questions`（经 `getSuggestedQuestions(agentId, params)`） | 推荐问题 | `src/api/agent/index.ts`（调用点 `src/views/creatChat/creatChat.vue:143`） |

> ⚠️ 上面最后一行的**具体路径**我只读到调用签名 `getSuggestedQuestions(agentId, settingsStore.getSuggestedQuestionsParams())`（`src/views/creatChat/creatChat.vue:143`、`src/views/chat/index.vue:533`），没有逐行核到 `src/api/agent/index.ts` 里的字符串，列入「不确定」。

---

## 10. 关键状态枚举（从代码常量/mapping 里找）

| 枚举 | 取值 | 出处 |
|---|---|---|
| SSE `response_type`（Agent 事件类型） | `agent_query, thinking, answer, tool_call, tool_result, command_output, reflection, error, complete, stop, references, memory_recalled, artifacts_pending, context_compacted, tool_approval_required, tool_approval_resolved, mcp_oauth_required, mcp_oauth_resolved, user_message_injected` | `src/composables/useChatStreamHandler.ts:603-1050,1130-1138,1159-1168` |
| 消息完成态 | `is_completed`（bool）；`is_fallback`；`showThink`/`thinking`；`superseded`（被新 answer 取代的旧 answer 事件）；`isAgentMode`/`isRagMode` | `useChatStreamHandler.ts:743-747,919-922,1220-1236`；渲染裁剪 `:258-272` |
| Agent 时间线事件 `type` | `thinking, answer, tool_call, context_compacted, tool_approval_required, mcp_oauth_required, stop, agent_complete` | `useChatStreamHandler.ts:621,657,675,707,799,907,1026,1038` |
| steer 投递方式 | `'inject' \| 'after'` | `src/api/chat/steer.ts:3`；键盘映射 `src/utils/chatSubmitShortcut.ts:8-10` |
| 临时附件状态 | `'uploaded' \| 'processing' \| 'ready' \| 'failed'`（前端并集再加 `'local' \| 'uploading'`） | `src/api/chat/temporary-attachments.ts:3`；`src/components/AttachmentUpload.vue:24` |
| 追问建议集状态 | `'generating' \| 'ready' \| 'suppressed' \| 'failed'` | `src/api/message-suggestion.ts:15` |
| 追问建议类别/来源 | `category: 'clarify' \| 'deepen' \| 'action'`；`source: 'model' \| 'faq' \| 'document' \| 'wiki' \| string` | `src/api/message-suggestion.ts:6-7` |
| 引用分节 | `'web' \| 'documents' \| 'tools'`；项类型 `'web' \| 'document' \| 'tool'` | `src/utils/referenceSources.ts:1,32-35` |
| 引用 chunk 类型 | `web_search`（网页）/ `tool_result`（工具）/ `faq`（FAQ）/ 其余按文档 | `src/utils/referenceSources.ts:99-105,279-288`；`citationMarkdown.ts:107-119` |
| 会话来源桶 | `'web' \| 'im' \| 'embed' \| 'api'` | `src/components/sessionSidebarBuckets.ts:8` |
| 会话日期分组 | `pinned, today, yesterday, last7Days, last30Days, lastYear, earlier` | `src/components/menu.vue:462-470` |
| 预览等待态 | `RagWaitKind = 'none' \| 'preparing' \| 'model'`（+ `stalled`） | `src/utils/rag-pipeline-state.ts:11,36-39` |
| 文件预览 kind | `pdf, docx, pptx, image, excel, text, markdown, html, audio, video, mermaid, unsupported` | `src/utils/filePreview.ts:11-23` |
| 产物分类 | `all, document, spreadsheet, presentation, image, web, data` | `src/utils/artifactLibrary.ts:5` |
| 产物日期分组 | `today, yesterday, last7Days, last30Days, earlier` | `src/utils/artifactLibrary.ts:38` |
| 文档详情视图 | `'chunks' \| 'merged' \| 'preview'` | `src/components/doc-content.vue:546` |
| 抽屉/菜单模式 | `MenuMode = 'menu' \| 'clear' \| 'delete'` | `src/components/ChatHeader.vue:139`；`SessionSidebarRow.vue:80` |
| MCP 工具状态 | `not_loaded, loading, ready, needs_auth, error, disabled, unavailable` | `zh-CN.ts:1507-1515`（i18n mapping 即枚举证据） |

---

## 11. 组件清单（名称 / 文件:行 / 职责 / 关键 props 与事件）

| 组件 | 文件 | 职责 | props / emits |
|---|---|---|---|
| `chat/index.vue` | `src/views/chat/index.vue:1` | 会话主界面：消息流、SSE 接入、滚动、分叉、steer 编排、两个抽屉的 provide | props `session_id, agentId, kbIds, embeddedMode`（`:237-242`）；provide `ChatReferencesDrawer` / `ChatAttachmentPreviewDrawer` / `ChatSandboxPanel`（`:232-234`） |
| `botmsg` | `src/views/chat/components/botmsg.vue:1` | 非 Agent 回答渲染 + 消息工具栏 | props `content, session, userQuery, isFirstEnter, embeddedMode, sessionId, followUpLoading, canFork`（`:186-221`）；emits `scroll-bottom, render-complete-change, fork`（`:175`） |
| `usermsg` | `src/views/chat/components/usermsg.vue:1` | 用户消息（提及/图片/附件/复制/分叉/steer 失败条） | emits `retry-steer, remove-steer, fork`（`:81`） |
| `docInfo` | `src/views/chat/components/docInfo.vue:1` | 「引用了 N 篇文档」折叠块；点头部即开右侧来源抽屉；文档分组→chunk 列表 + popup 看片段 | props `content, session, embeddedMode, timelineMode, contentOnly`（`:74-95`） |
| `RagPipelineProgress` | `src/views/chat/components/RagPipelineProgress.vue:1` | 检索/工具步骤时间线 + 等待行 + 记忆行 | props `session, embeddedMode, memoryOnly`；内部用 `useChatReferencesDrawer` 开抽屉（`:263,287`） |
| `AgentStreamDisplay` | `src/views/chat/components/AgentStreamDisplay.vue:1` | Agent 时间线（思考/工具/沙箱/审批/OAuth/答案）+ 工具栏 + 引用委托点击 | props 含 `session, sessionId, userQuery, ragMode, followUpLoading, embeddedMode, canFork`；emits `fork, render-complete-change` |
| `deepThink` | `src/views/chat/components/deepThink.vue:1` | `<think>` 折叠块（思考中 / 已深度思考） | props `deepSession`（`:33-39`） |
| `ChatHeader` | `src/components/ChatHeader.vue:1` | 会话标题（双击改名）+ `…` 菜单（置顶/改名/复制 ID/复制链接/导出 Markdown/新窗口/清空/删除）+ 行内二次确认 | props `session, hasReferencesPanel`（`:141-144`），无 emit（靠事件总线 + router） |
| `Input-field` | `src/components/Input-field.vue:1` | 提问区全部：textarea、快捷键、附件/图片、@提及、模式与模型选择、发送/停止、steer 队列 | props 含 `isReplying, sessionId, assistantMessageId, embeddedMode, queuedSteers, canSteer, autoFocus`；emits `send-msg, stop-generation, stop-confirmed, stop-failed, steer-msg, promote-steer, remove-steer, retry-steer`（`:1951-1962`）；expose `focusInput, triggerSend, prefill`（`:2618-2633`） |
| `AttachmentUpload` | `src/components/AttachmentUpload.vue:1` | 附件选择/上传/轮询解析状态；后缀白名单 + 大小/数量校验 | props `maxFiles, maxSize, disabled, sessionId, agentId, agentSourceTenantId`；emits `update:files, remove`（`:38-41`） |
| `ChatAttachmentPreviewDrawer` | `src/components/ChatAttachmentPreviewDrawer.vue:1` | 附件预览抽屉（内嵌 `DocumentPreview`） | 由 `useChatAttachmentPreviewDrawer` 上下文驱动，无 props |
| `MentionSelector` | `src/components/MentionSelector.vue:1` | @ 菜单（分组、分页、键盘） | props `visible, style, items, hasMore, loading, emptyHint, query, groupCounts`，`v-model:activeIndex`；emits `select, loadMore`（`src/components/Input-field.vue:2931-2933`） |
| `AgentSelector` | `src/components/AgentSelector.vue:1` | 智能体下拉（能力矩阵、未就绪提示） | props `visible, anchorEl, currentAgentId, agents, allModels`；emits `close, select, not-ready`（`src/components/Input-field.vue:2728-2730`） |
| `ModelSelector` | `src/components/ModelSelector.vue:1` | 模型选择 | 见 `src/components/Input-field.vue:2856-2908` 的内联实现 |
| `KnowledgeBaseSelector` | `src/components/KnowledgeBaseSelector.vue:1` | 知识库多选弹层 | `v-model:visible` + `anchorEl`（`src/components/Input-field.vue:2938`） |
| `ChatReferencesDrawer` | `src/components/ChatReferencesDrawer.vue:1` | **来源面板**（右侧固定 420px / 窄屏遮罩）；三节列表；高亮 + 面板内滚动定位；文档项可展开全文 | props `embeddedMode, overlayBreakpoint`（`:149-152`），无 emit；上下文 `useChatReferencesDrawer` |
| `ChatCitationFloat` | `src/components/ChatCitationFloat.vue:1` | 引用的 hover 浮层（web / kb 两形态） | props `float: CitationFloatState, onEnter, onLeave`（`:24-28`） |
| `useChatCitationPopover` | `src/composables/useChatCitationPopover.ts:18` | 把 `useCitationPopover` 绑到聊天场景（chunk 拉取 + 缓存 scope + 错误文案） | options `getKnowledgeReferences, embedChannelId, embedToken, sessionId` |
| `useCitationPopover` | `src/composables/useCitationPopover.ts:31` | 浮层生命周期 + capture 事件委托（mouseover/mouseout/click）+ 点击优先开抽屉 | 返回 `{float, rebind, cancelClose, scheduleClose}` |
| `useChatReferencesDrawer` | `src/composables/useChatReferencesDrawer.ts:27,90` | 抽屉的 provide/inject 上下文 | `open/toggle/close/setHighlight` + `sourceKey` 去重 |
| `useChatStreamHandler` | `src/composables/useChatStreamHandler.ts:1` | SSE 事件 → 消息模型（全部 response_type 分派）、引用/记忆落库、渲染裁剪 | 返回 `findLastMessage, shouldRenderAssistantMessage, shouldShowGlobalTypingIndicator, handleMsgList, processStreamChunk, prepareForNewOutgoingMessage, markInFlightAssistantStopped`（`:1254-1262`） |
| `useStream` | `src/api/chat/streame.ts:28` | SSE 客户端（fetch-event-source + 401 重放 + TTFB 埋点） | 返回 `output, isStreaming, isLoading, error, lastStreamRequest, onChunk, startStream, stopStream` |
| `useTypewriter` | `src/composables/useTypewriter.ts:84` | 流式文本平滑（自适应 cps、CJK 分组、reduced-motion 直出） | `(getTarget, getComplete, options)` → `{displayed}` |
| `document-preview` | `src/components/document-preview.vue:35` | 多格式文件预览（PDF/Office/图片/文本/HTML/Mermaid）+ 全屏 + 焦点契约 | 见 §5.2；无 emit |
| `doc-content` | `src/components/doc-content.vue:244` | KB 文档详情抽屉：全文 / 分块 / 预览三视图，分块可编辑、可切启用、有版本 diff | props `visible, details, knowledgeType, sourceInfo, canEditKB, canDownloadKB, parse_status, kbId`；emits `closeDoc, getDoc, questionDeleted, summaryStateChange`；expose `openTimeline`（`:513`） |
| `ArtifactLibrary` | `src/views/artifacts/ArtifactLibrary.vue:1` | 产物库页（筛选/搜索/日期分组/预览抽屉/下载/打开会话） | 无 props；读 `route.query.type|q` |
| `ChatArtifactsPanel` | `src/views/chat/components/ChatArtifactsPanel.vue:1` | 沙箱侧板的产物 tab（作用域切换 + 搜索 + 预览） | 无公开 props（由侧板组合） |
| `ChatArtifactsDrawer` | `src/views/chat/components/ChatArtifactsDrawer.vue:91,184` | embed 模式的产物抽屉（内嵌 `DocumentPreview`） | `v-model:visible, session-id, message-id, artifacts, preview-index`（`src/views/chat/components/botmsg.vue:105-112`） |
| `FollowUpSuggestions` | `src/components/chat/FollowUpSuggestions.vue:35-45` | 回答下方的追问卡片 | props `suggestionSet, loading, allowRegenerate`；emits `select, regenerate, impression, dismiss` |
| `ChatQuestionMinimap` | `src/components/chat/ChatQuestionMinimap.vue:74-80` | 右侧「提问目录」轨：hover 出山形刻度 + 问答预览，点击跳转 | props `scrollContainer, messages`；emits `jump(messageId)`；文案 `chat.questionMinimapTitle`=`问答`、`questionMinimapAriaLabel`=`提问目录`（`zh-CN.ts:3826-3827`） |
| `MessageTimestamp` | `src/components/chat/MessageTimestamp.vue:10-14` | 会话内时间分隔（今天/昨天/…） | props `{value}`；文案 `chat.conversationTime.*`（`zh-CN.ts:3764-3769`） |
| `SessionSidebarRow` | `src/components/SessionSidebarRow.vue:82-100` | 侧栏单行（标题/置顶/分叉/运行中/owner 徽标/行菜单/行内改名） | props `item, batchMode, activePath, selectedIds, menuOptions, running, nested`；emits `navigate, toggle-select, menu-click, rename-submit, hover-in, hover-out` |
| `SessionSourceFilter` | `src/components/SessionSourceFilter.vue:51-62` | 来源筛选下拉（inline 触发器） | props `sources, current, inline, emphasized`；emits `select` |
| `menu` | `src/components/menu.vue:1` | 左侧栏整体（logo/搜索/导航/会话列表/批量条/用户菜单） | 无 props |
| `ChatRequestInfoButton` | `src/components/ChatRequestInfoButton.vue:1` | 展示 Request ID / 消息 ID / 会话 ID / 请求 URL / 发起时间 | props `session, session-id`（`src/views/chat/components/botmsg.vue:88`） |

---

## 12. 值得抄的（对我们有用的）

面向「法规/标准取证工作台：IDE 侧栏里提问 → 答案带可点击条款依据（点开鉴权 PDF 跳页）」。

> 许可核实（抄之前必看）：`D:\AI\WeKnora\LICENSE:8` 原文——"This project is licensed under the MIT License except for the third-party components listed below, which is licensed under different terms."；同文件 `:26-241` 起是随附的第三方清单（Apache-2.0 / BSD / MPL 等），`THIRD_PARTY_NOTICES.md` 与 `licenses/` 是补充。**结论：项目本体 MIT，可抄，需随附 MIT 版权声明；若直接搬第三方组件则要另核各自许可。**

1. **引用角标点击 → 打开右侧来源面板并高亮命中卡**（`useCitationPopover.ts:195-203` + `ChatReferencesDrawer.vue:279-318`）：这是「答案→证据」最短路径，且高亮定位是面板内滚动（不整页跳），实现干净、可直接复用。
2. **hover 悬浮卡片按需拉 chunk 正文 + 进程内缓存**（`ChatCitationFloat.vue` + `useCitationPopover.ts:96-134` + `citationChunkCache.ts`）：不预载全文就能"悬停即见原文片段"，缓存 scope 按 session/embed 隔离、防串联——对我们的条款预览同样适用（我们的"点开引擎鉴权 PDF"可以先用它做悬浮预览层）。
3. **"序号 → 真实 chunk UUID"的解析层**（`citationMarkdown.ts:84-143`）：模型只会写 `1`/`DOC-3`，它按「文档标题匹配 → FAQ 序数 → DOC 序数 → 数组下标 → chunk_index」多级回退。我们的引擎若也只回条款号/序号，这一层能避免"引用点了跳错处"。
4. **流式期的角标/公式/表格稳定化**（`citationMarkdown.ts:18-32,235-301` + `chatMarkdownRenderer.ts:189-360`）：隐藏半个标签、把角标贴回上一行、合并只含角标的 `<p>`、悬空 `**`/`---`/列表符先不渲染。这类"半截 markdown 抖动"我们一定会遇到，是现成的坑位清单。
5. **打字机 + 「渲染追平才出工具栏」**（`useTypewriter.ts:84-207` + `botmsg.vue:347-349`）：`answerFullyRendered = is_completed && typed >= text.length`，保证操作按钮不会紧贴还在滚动的文字；`prefers-reduced-motion` 直出。用来做「答案逐条带依据」的稳定呈现很值。
6. **会话级输入态恢复**（`stores/settings.ts:516-597`，数据来自 `session.last_request_state`）：打开旧会话恢复当时的 agent/模型/KB 范围/联网/MCP，离开还原全局默认，且**故意不写 localStorage**。对"同一问题在不同法规库范围内复现"很有用。
7. **来源面板的数据装配层**（`referenceSources.ts:206-308`）：按文档合并、`chunk_ids` 去重并集、`content` 只取前 3 段、snippet 压空白去 Markdown 后截 220 字、web 按规范化 URL 去重。我们的"证据链呈现"可以直接照这个形状做文档级聚合卡。
8. **预览的"分源信任策略"**（`document-preview.vue:324-329`）：只有自生成产物允许 `sandbox="allow-scripts"` iframe 渲染，知识库上传文件与会话附件一律只显示源码。做鉴权 PDF/材料预览时必须抄这条安全边界。
9. **全屏 + 键盘可达性契约**（`document-preview.vue:74-198` + `document-preview.focus.test.mjs`）：原生 Fullscreen 优先、失败降级、焦点给滚动容器且 `preventScroll`、绝不抢输入框焦点、可 tab、iframe load 后保持焦点。这是一份现成的"预览面板无障碍清单"。
10. **等待反馈的两级计时**（`rag-pipeline-state.ts:2,9`）：250ms 内不显示等待行（避免闪），60s 无进展切「模型响应较慢，仍在等待…」。我们调用引擎动辄几十秒，这套阈值现成可用。
11. **steer（追加到运行中的 turn）与队列 UI**（`steer.ts` + `Input-field.vue:2642-2664`）：`inject`/`after` 两档 + 队列可提升/删除/重试，服务端为准 `GET …/steer` 回灌。做长任务巡检时"边跑边补要求"可直接借用。

## 13. 建议不抄 / 抄不动

1. **引用点击不跳原文页**：WeKnora 的引用只到 chunk 粒度，点击只开抽屉高亮卡片；引用数据里**根本没有页码**（字段全集见 `referenceSources.ts:3-14`），预览组件也没有 `focus(pos)` 能力。我们的核心诉求（跳 PDF 对应页）必须自建，不能照抄这条链。
2. **预览组件无定位/缩放/页内查找**：PDF 就是一个 `<iframe>`（`document-preview.vue:541-543`），没有 pdf.js、没有页码参数、没有 zoom、没有命中高亮。要"跳到第 N 页并高亮"只能换渲染器（pdf.js / 引擎侧 PDF 锚点），**改造代价 > 复用收益**。
3. **引用列表没有相似度分数、没有排序/筛选**：抽屉只按 web/documents/tools 三节固定顺序展示，分数不在数据里（`referenceSources.ts:16-30`）。若我们要"按证据强度排序"，得在引擎侧补字段。
4. **来源面板与文档预览是断开的两个系统**：抽屉只给一个「查看文档详情」外链（`ChatReferencesDrawer.vue:262-270`），跳到 KB 详情页后还得手动切到「预览」tab，两个视图之间没有任何 chunk 参数传递（`doc-content.vue:546,2135-2138`）。这条 UX 是断的，别学。
5. **抽屉/预览的宽度与"位置"都写死在宿主**：`min(420px,100vw)` 固定不可拖（`ChatReferencesDrawer.vue:342`），窄屏 960px 阈值写死（`:171`）。IDE 侧栏宽度本来就窄，这套固定宽度会让窄栏里直接退化遮罩层，需要重做断点。
6. **引用角标是"文档名"而不是"条款号"**：kb 角标显示的是截断到 13 字符的**文档标题**（`citationMarkdown.ts:63-70,183-184`），法规场景我们要的是 `GB 30871-2022 5.2.3` 这类**标准号+条款号**，标签语义要重做（但解析层思路可留）。
7. **大而全的 Agent 时间线**：`AgentStreamDisplay.vue` 近 4000 行、连同工具结果渲染器一大票（`components/tool-results/*` 20+ 个文件）。我们不做多工具 agent 编排，抄进来是纯负担。
8. **沙箱/终端/桌面/浏览器预览整块**（`SandboxSidePanel`、`SandboxTerminal`、`SandboxDesktop`、`BrowserTaskPreview`、`chat.sandbox.*` 40+ 条文案）：与我们场景无关。
9. **六套 locale 的字面量维护量**：`zh-CN.ts` 7431 行、`ru-RU.ts` 554KB，`src/i18n/embed.ts` 还有一份独立拷贝。我们只需中文（+可选英文），别复制这套多语言基座；顺带说，本项目自己就漏了 key：`botmsg.vue:387,398,413` 引用 `chat.emptyContentWarning` / `chat.editorOpened`，但 `chat` 命名空间（`zh-CN.ts:3752-3943`）里**没有这两个键**（只有 `agentStream.saveToKb.editorOpened` 在 `:1483`）。
10. **fork 用 sessionStorage 传递 prefill**（`chat/index.vue:321-364`）：能用，但跨窗口/刷新即失效、且只带文本不带提及项。我们要做"复制到新会话再改问"的话，用 store/router state 更稳。
11. **同一动作两处文案不一致 + 硬编码中文**：分叉 tooltip 在用户消息侧是 `从这里分叉出新会话`（`usermsg.vue:146`）、在回答侧是 `从这条回答继续分叉`（`botmsg.vue:224`），且都绕过了 i18n；侧栏分叉图标 tooltip 同样硬编码 `由其他会话分叉而来`（`SessionSidebarRow.vue:17`）。机制可抄，但这批字面量会带进不一致。

---

## 14. 我没查到 / 不确定

1. **`getSuggestedQuestions` 的确切 HTTP 路径**：只读到调用签名与参数构造函数（`src/views/creatChat/creatChat.vue:143`、`src/views/chat/index.vue:533`、`stores/settings.ts` 的 `getSuggestedQuestionsParams`），**没有逐行核 `src/api/agent/index.ts` 里的字符串**。
2. **`chat.emptyContentWarning` / `chat.editorOpened` 是不是真的会渲染成裸 key**：我确认了 `zh-CN.ts` 的 `chat` 段（3752–3943）没有这两个键，也确认了 `src/i18n/embed.ts` 里有 `emptyContentWarning`（独立命名空间）。但**没有跑起来验证** vue-i18n 在缺键时的实际渲染（可能回退到别的 locale，也可能打印 warn + 显示 key）。属于「读到的事实 + 未运行时验证」。
3. **agent-chat 的 SSE 事件名与 response_type 的完整后端契约**：我只从前端分派分支反推出枚举（§10 第一行），**没有读后端 Go 代码**逐一对照。
4. **`references` 事件里是否可能带分数**：前端类型没有 score 字段，但后端是否发了而被前端丢弃，我没核后端（`useChatStreamHandler.ts:156-164` 只取 `knowledge_references`/`references`/`knowledge_references`）。
5. **`document-preview.vue` 里 PDF iframe 的具体浏览器行为**（是否有内置页码 UI、能否 `#page=N` 定位）：代码只创建 object URL，没拼 `#page=`。这一点是**读代码所得**，未在浏览器实跑确认。
6. **会话列表是否真的会按 `sessionGrouping` 的 `mode` 开关切换 none/date**：我读到 `DEFAULT_SESSION_GROUP_MODE='none'` 与 `buildGroupModeOptions`，但侧栏渲染路径只看 `filteredGroupedSessions`（`menu.vue:472-484`），**没找到读该 localStorage 开关并影响渲染的调用点**，因此 §1.3 只描述实际渲染行为，不对该开关是否生效下结论。
7. **`views/embed` 那套的完整交互**（`EmbedChatCore.vue` 19158 字节、`api/embed/index.ts` 28KB）只做了架构层面的确认（复用 `botmsg`/`ChatReferencesDrawer` + `embed_token` 鉴权），**没有逐条核 embed 的接口与文案**。
8. **`views/agent`（AgentList / AgentEditorModal 254KB）的内部结构**未展开；只确认了它与提问区的关系（决定可用工具/KB 范围/联网/模型，`src/utils/agent-readiness.ts` 是"未就绪"判定的真源）。
9. **「文档预览」是否有宽度拖拽**：我在 `document-preview.vue` 里没找到 resizer，但**没有穷举宿主**（`ChatArtifactsDrawer.vue` 668 行起的样式里可能另有布局逻辑），故只说"未见"。
10. **各场景文案的英文/其他语言版本**：本文所有原文均取自 `zh-CN.ts`；`en-US.ts` 等未逐条对照（引用抽屉那组我在 `src/i18n/embedLocale.test.ts:112-113` 见过英文断言，可作旁证）。
