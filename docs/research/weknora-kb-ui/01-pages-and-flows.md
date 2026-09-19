# WeKnora「知识库管理」界面与流程记录

**来源**：`D:\AI\WeKnora`（Git checkout），commit `b82fd6c0f9939e8497fa7474999dd1bde5d0d88d`
**前端栈**：Vue 3 + TDesign Vue Next + Pinia + vue-router（`frontend/src`）
**读法说明**：源码里界面文案全部走 i18n key（`$t('a.b.c')`）。本文档把 key 解析成 **`frontend/src/i18n/locales/zh-CN.ts` 里的中文原文**并照抄，同时给出 key。凡 `zh-CN.ts` 里找不到的 key，本文档明确标注为"缺失"，不代填。
**只读声明**：本次研究未修改 `D:\AI\WeKnora` 下任何文件（`git status --short` 仅显示研究前已存在的 `?? DEPLOY-NOTES.md`）。
**性质与归属**：本文件是**源码级界面/流程事实记录**（可抄的交互与数据结构依据），不是决策文档。
决策与影响评估在 [weknora-assessment.md](../weknora-assessment.md)（那里基于官方文档；本文件基于源码，两者互补）。
**许可证**：`D:\AI\WeKnora\LICENSE` 存在（161 682 字节），开头即 "Tencent is pleased to support the open source community…"，
并指向 `THIRD_PARTY_NOTICES.md` 与 `licenses/`；具体条款与署名义务见评估文档 §五第 0 条（**未在本文件重复核验**）。

---

## 一、页面 / 路由清单表

路由表唯一来源：`frontend/src/router/index.ts`。视图文件全部位于 `frontend/src/views/`。

| 路由路径 | 路由 name | 视图文件 | 这一页干什么 | 路由定义 |
|---|---|---|---|---|
| `/` | — | — | 重定向到 `/platform/knowledge-bases` | router/index.ts:49-52 |
| `/login` | `login` | `views/auth/Login.vue` | 登录（`?token=` 时同一组件切邀请注册模式） | router/index.ts:53-58 |
| `/register` | `registerByInvite` | `views/auth/Login.vue` | 邀请注册落地页（复用 Login） | router/index.ts:60-70 |
| `/onboarding/workspace` | `workspaceOnboarding` | `views/auth/WorkspaceOnboarding.vue` | 无租户时先建/加入空间 | router/index.ts:71-76 |
| `/join` | `joinOrganization` | — | 重定向到 `/platform/organizations` 并带 `invite_code` | router/index.ts:77-89 |
| **`/knowledgeBase`** | `home` | `views/knowledge/KnowledgeBase.vue` | **同一个详情组件的另一个挂载点**（无 `:kbId`，用于 Lite/默认入口场景） | router/index.ts:90-95 |
| `/platform` | `Platform` | `views/platform/index.vue` | 平台外壳：左侧 Menu + `<RouterView>` + 全局拖拽上传遮罩 + `UploadTasksPanel` 浮层 + 全局命令面板 | router/index.ts:96-102；platform/index.vue:1-22 |
| `/platform/settings` | `settings` | `views/settings/Settings.vue` | 全局设置（含解析引擎、模型、向量存储等；知识库设置不在这里） | router/index.ts:107-112 |
| **`/platform/knowledge-bases`** | `knowledgeBaseList` | `views/knowledge/KnowledgeBaseList.vue` | **知识库列表页**：卡片列表、分区折叠、置顶/收藏、新建/副本/设置/删除入口 | router/index.ts:113-118 |
| **`/platform/knowledge-bases/:kbId`** | `knowledgeBaseDetail` | `views/knowledge/KnowledgeBase.vue` | **知识库详情页**：文档/分块管理；FAQ 型知识库在同路由下渲染 `FAQEntryManager` | router/index.ts:119-124 |
| `/platform/knowledge-search` | — | — | 旧路径保留，重定向到 `/platform/knowledge-bases?cmdk=<q>`（打开全局命令面板） | router/index.ts:125-135 |
| `/platform/artifacts` | `artifactLibrary` | `views/artifacts/ArtifactLibrary.vue` | 产物库（需 `settings.sandbox` 能力） | router/index.ts:136-141 |
| `/platform/agents` | `agentList` | `views/agent/AgentList.vue` | 智能体列表 | router/index.ts:142-147 |
| `/platform/creatChat` | `globalCreatChat` | `views/creatChat/creatChat.vue` | 新建会话页（也挂 `KnowledgeBaseEditorModal`） | router/index.ts:165-170 |
| `/platform/knowledge-bases/:kbId/creatChat` | `kbCreatChat` | `views/creatChat/creatChat.vue` | 从某知识库发起新会话 | router/index.ts:171-176 |
| `/platform/chat/:chatid` | `chat` | `views/chat/index.vue` | 对话页（也挂 `KnowledgeBaseEditorModal`） | router/index.ts:177-182 |
| `/platform/organizations` | `organizationList` | `views/organization/OrganizationList.vue` | 共享空间列表 | router/index.ts:183-188 |
| `/platform/system/*` 等 | — | — | 全部重定向到 `/platform/settings?section=…` | router/index.ts:189-215 |

### 关键结论：知识库"设置"不是路由，是弹窗

`KnowledgeBaseEditorModal.vue`（即"知识库设置"）**没有任何路由**，它由 Pinia `uiStore` 驱动：

- 状态：`showKBEditorModal`、`kbEditorMode: 'create' | 'edit'`、`currentKBId`、`kbEditorType: 'document' | 'faq'`（`frontend/src/stores/ui.ts:6-9`）
- 打开创建：`uiStore.openCreateKB(type, initialSection)`（ui.ts:55-61）
- 打开编辑：`uiStore.openKBSettings(kbId, initialSection)`（ui.ts:43-49，内部把 mode 设为 `'edit'`）
- 挂载点共 4 处：`views/knowledge/KnowledgeBaseList.vue:630-632`、`views/knowledge/KnowledgeBase.vue:2565-2567`、`views/chat/index.vue:170`、`views/creatChat/creatChat.vue:53`
- 形态：`SettingsModalShell`（左侧分组导航 + 右侧内容 + 底部按钮），不是 `t-dialog`（KnowledgeBaseEditorModal.vue:2-5）

### 与知识库相关的其它视图文件（非路由页，均为组件/抽屉）

| 文件 | 作用 |
|---|---|
| `views/knowledge/components/UploadConfirmDialog.vue` | 上传确认大弹窗（2065 行；模板 1-570，脚本 572-1473） |
| `views/knowledge/components/KbUploadSourceDropdown.vue` | "添加文档"下拉：上传文档/文件夹/网页/在线编辑 |
| `views/knowledge/components/DocumentListView.vue` | 列表视图（780 行；脚本 1-256，模板 258-483） |
| `views/knowledge/components/DocumentCardView.vue` | 卡片视图（1152 行；脚本 1-315，模板 317-687） |
| `views/knowledge/components/DocumentActionMenu.vue` | 单条文档"…"菜单 |
| `views/knowledge/components/DocumentBatchBar.vue` | 底部浮动批量条 |
| `views/knowledge/components/FAQBatchBar.vue` | FAQ 专用批量条 |
| `views/knowledge/components/KnowledgeTagFilter.vue` | 标签筛选下拉（多选 chips） |
| `views/knowledge/components/TagEditDialog.vue` | 单条文档打标签对话框 |
| `views/knowledge/components/BatchTagDialog.vue` | 批量打标签对话框 |
| `views/knowledge/components/KbTagManageDrawer.vue` | 标签管理抽屉（建/改名/删） |
| `views/knowledge/components/KbFolderTree.vue` | 左侧目录树 |
| `views/knowledge/components/FolderPickerMenu.vue` | 目录选择器（含"新建子目录"） |
| `views/knowledge/components/FAQEntryManager.vue` | FAQ 型知识库的整页管理器（4721 行） |
| `components/upload-tasks/UploadTasksPanel.vue` | 全局上传进度浮层 |
| `components/upload-tasks/UploadTaskRow.vue` | 浮层内单文件行 |
| `components/upload-mask.vue` | 全局拖拽时的整页遮罩 |

---

## 二、五条流程逐条

### 流程 1：知识库怎么新建

#### 1.1 入口

| 位置 | 条件 | 证据 |
|---|---|---|
| 列表页 header 右侧的图标按钮（`folder-add`），tooltip = `knowledgeList.create`「新建知识库」 | `authStore.hasRole('contributor')` | KnowledgeBaseList.vue:11-15 |
| 「全部」空态里的主按钮，文案「新建知识库」 | 同上 | KnowledgeBaseList.vue:595-601 |
| 「我创建的」空态里的主按钮，文案「新建知识库」 | 同上 | KnowledgeBaseList.vue:614-620 |

三者都调 `handleCreateKnowledgeBase`：

```
// KnowledgeBaseList.vue:1499-1505
const handleCreateKnowledgeBase = () => {
  markContextualGuideDone('kbList')
  const initialSection = modelsReadyLoaded.value && !isReadyForDocumentKb.value ? 'models' : undefined
  uiStore.openCreateKB('document', initialSection)
}
```
即：模型未就绪时**仍然打开创建向导**，但会预先把左侧导航定位到「模型配置」。

#### 1.2 形态

- **不是路由，是弹窗**（`SettingsModalShell`）。
- 标题：create 模式 `knowledgeEditor.titleCreate` = **「新建知识库」**（KnowledgeBaseEditorModal.vue:3；zh-CN.ts:3945）；edit 模式 `knowledgeEditor.titleEdit` = 「知识库设置」（zh-CN.ts:3946）。
- 左侧导航按 5 个分组渲染（KnowledgeBaseEditorModal.vue:695-726）：
  - 基础 `knowledgeEditor.navGroups.basic`「基础」
  - 索引与解析 `…processing`「索引与解析」
  - 存储与数据 `…data`「存储与数据」
  - 集成 `…integration`（空组自动过滤）
  - 管理 `…management`（空组自动过滤）
  - （导航项自身文案：`knowledgeEditor.sidebar.*`「基本信息/模型配置/向量存储/分块设置/存储引擎/高级设置/FAQ 设置/知识图谱/图像处理/音频处理/数据源/共享管理/活动记录」，zh-CN.ts:4501-4515）

创建模式下实际出现的导航项（KnowledgeBaseEditorModal.vue:660-692 的 `navItems`）：

1. `basic`「基本信息」
2. `models`「模型配置」
3. `vectorStore`「向量存储」
4. 文档型：`parser`（label 取 `t('settings.parserEngine')`「解析引擎」）、`multimodal`「图像处理」、`asr`「音频处理」、`storage`「存储引擎」、`chunking`「分块设置」、`graph`「知识图谱」、`advanced`「高级设置」
   问答型：`faq`「FAQ 设置」
5. `datasource`「数据源」/`share`「共享管理」/`activity`「活动记录」**仅 edit 模式且已有 kbId 时才出现**（681-690）

#### 1.3 表单字段一览

| 字段 | 控件 | 必填 | 限制/默认 | 证据 |
|---|---|---|---|---|
| 知识库类型 | `t-radio-group`，值 `document`/`faq`；文案 `knowledgeEditor.basic.typeDocument`「文档」/`typeFAQ`「问答」 | **是**（`form-label required`） | **edit 模式 disabled**；提示 `basic.typeDescription`「FAQ 类型适合结构化问答数据；文档型支持文件解析与分块；Wiki 类型由 LLM 自动构建互链知识页面。」 | KnowledgeBaseEditorModal.vue:29-40；zh-CN.ts:4473-4476 |
| 索引策略 | 两个 `t-checkbox`：`indexing.searchTitle`「RAG 检索」、`indexing.wikiTitle`「Wiki 知识库」（带 NEW 徽标） | **是**（至少一种） | 文案 `indexing.description`「配置文档上传后的处理管道，可以独立开启或关闭每种索引方式」；`searchDesc`「对文档进行分块、向量化和关键词索引，支持混合检索」；`wikiDesc`「自动生成互相关联的 Wiki 知识页面，构建结构化知识体系」 | 43-81；zh-CN.ts:4431-4437 |
| ↳ 锁定提示 | 文本 | — | `isIndexingLocked = editorMode === 'edit' && hasFiles`（1080）；提示 `indexing.lockedTip`「知识库已有内容，索引策略暂不支持调整。如需变更，请先清空知识库。」 | 46,78-80,1080；zh-CN.ts:4442 |
| Wiki 提取粒度 | 3 个 radio：`focused`/`standard`/`exhaustive`（仅 wikiEnabled） | 否 | 文案见 `knowledgeEditor.wiki.granularity*` | 84-103 |
| Wiki 内容指令 / 抽取指令 | `t-textarea`，`maxlength=4000` | 否 | 仅 wikiEnabled | 105-125 |
| 知识库名称 | `t-input`，`maxlength=50` | **是** | placeholder「请输入知识库名称」 | 127-134；zh-CN.ts:4477-4478 |
| 知识库描述 | `t-textarea`，`maxlength=200` | 否 | placeholder「请输入知识库描述（可选）」 | 135-143；zh-CN.ts:4479-4480 |
| AI 生成描述 | 卡片 + 「生成 AI 描述」/「重新生成」/「用作知识库描述」按钮 | 否 | **仅 edit 模式、文档型** | 145-198；zh-CN.ts:4481-4495 |
| 模型配置（`KBModelConfig`） | 子组件 | **Embedding 条件必填、Summary 必填** | 见 1.5 校验 | 206-217 |
| 向量存储（`KBVectorStoreSettings`） | create 模式为下拉；edit 模式只读并提示不可改 | 否 | `mode` prop 传 `editorMode` | 219-231 |
| FAQ 索引方式 | radio `question_only`/`question_answer` | **是**（FAQ 型） | 文案「仅索引问题」/「标准问 + 答案」 | 234-250；zh-CN.ts:4215 |
| FAQ 问题索引方式 | radio `combined`/`separate` | **是**（FAQ 型） | 文案「合并索引」/「分别索引」 | 251-260；zh-CN.ts:4217 |
| 解析引擎（`KBParserSettings`） | 子组件 | 否 | 仅文档型 | 269-274 |
| 存储引擎（`KBStorageSettings`） | 子组件 | 否 | edit 且有文件时给 `has-files` | 277-285 |
| 分块设置（`KBChunkingSettings`） | 子组件 | 否 | 默认预设：`DEFAULT_CHUNKING_PRESET = { chunkSize: 512, chunkOverlap: 80, enableParentChild: true }`；仅 Wiki 预设 `{ 2048, 0, false }`，**只在创建模式且未手动改过时生效** | 288-294；639-653；634-635 |
| 多模态（VLLM） | `t-switch` + `ModelSelector model-type="VLLM"` | VLLM 模型在启用后必填 | `advanced.multimodal.*` | 297-368 |
| 音频处理（ASR） | `t-switch` + `ModelSelector model-type="ASR"` | ASR 模型在启用后必填 | `asr.*` | 370-412 |
| 知识图谱（`GraphSettings`） | 子组件 | 否 | 仅文档型 | 414-423 |
| 高级设置（`KBAdvancedSettings`） | 问题生成 / 自动关联标签 / 自动生成知识库描述 / 表格元数据要求 | 否 | 仅文档型 | 425-441 |

创建提交的 payload 结构（`buildSubmitData`，KnowledgeBaseEditorModal.vue:1292-1436）包含：`name`、`description`、`type`、`chunking_config{chunk_size,chunk_overlap,separators,enable_parent_child,parent_chunk_size,child_chunk_size,strategy,token_limit,languages,table_metadata_instructions[,parser_engine_rules]}`、`embedding_model_id`、`summary_model_id`、`vlm_config`、`asr_config`、`storage_backend_id`/`storage_provider_config`/`storage_config`、`question_generation_config`、`auto_tag_config`、`profile_config`、`faq_config`(FAQ)、`wiki_config`、`indexing_strategy{vector_enabled,keyword_enabled,wiki_enabled,graph_enabled}`、`extract_config`，以及按需的 `vector_store_id`（1326-1328）。

#### 1.4 逐步动作 → 界面反应

1. 点「新建知识库」→ `uiStore.openCreateKB('document', …)` → 弹窗打开，落在「基本信息」段。
2. 选「文档」/「问答」→ 左侧导航项**立即增减**（`navItems` 依赖 `formData.value?.type`，669-684）。
3. 勾/取消「RAG 检索」「Wiki 知识库」→ Wiki 相关字段块显隐（84/105/116 的 `v-if`）；索引策略还会联动默认分块预设（639-653）。
4. 点左侧导航跳到「模型配置」，选 Embedding / Summary 模型（`ModelSelector`，缺失时可在弹窗内 `openSettings('models', …)` 去添加）。
5. 点底部「创建知识库」（`knowledgeEditor.buttons.create`，zh-CN.ts:4248）→ 前端校验。

#### 1.5 校验与限制（`validateForm`，KnowledgeBaseEditorModal.vue:1241-1289）

按顺序短路返回，并把左侧导航**强制跳回**出错段：

| 条件 | 提示原文 | 跳回段 | 行 |
|---|---|---|---|
| 名称为空 | **「请输入知识库名称」** | basic | 1245-1249 |
| 文档型且四种索引全关 | **「至少需要开启一种索引策略」** | basic | 1252-1259 |
| 需 RAG 但无 Embedding 模型 | **「RAG 检索需要配置 Embedding 模型」** | models | 1262-1267 |
| 无 Summary 模型 | **「请选择 Summary 模型」** | models | 1269-1273 |
| 启用多模态但无 VLLM | **「多模态配置验证失败」** | multimodal | 1276-1280 |
| FAQ 型无索引方式 | **「请选择 FAQ 的索引方式」** | faq | 1282-1286 |

其它限制：
- 名称 `maxlength=50`、描述 `maxlength=200`（前端截断，非报错）。
- **没有"重名知识库"校验**：前端无任何同名检查，也没有对应错误文案（本文档未在 zh-CN 找到同名类提示）。
- 编辑模式下若已有文件且存储引擎被改：`DialogPlugin.confirm` 标题 `common.confirm`「确认」，正文 **「知识库中已有文件，更改存储引擎后旧文件可能无法正常访问。是否确认更改？」**（1445-1466；zh-CN.ts:4237）。
- 保存按钮 `:loading="saving" :disabled="loading"`（480-483）。

#### 1.6 提交与创建后的走向

```
// KnowledgeBaseEditorModal.vue:1479-1491
if (editorMode.value === 'create') {
  const result: any = await createKnowledgeBase(data)
  if (!result.success || !result.data?.id) throw new Error(result.message || t('knowledgeEditor.messages.createFailed'))
  const createdKbId = result.data.id as string
  savedKbId.value = createdKbId
  currentSection.value = 'basic'
  await loadKBData(createdKbId)
  MessagePlugin.success(t('knowledgeEditor.messages.createSuccess'))   // 「已创建知识库」
  markContextualGuideDone('kbCreate')
  emit('success', createdKbId)
}
```

- 接口：`createKnowledgeBase(data)` → **`POST /api/v1/knowledge-bases`**（`frontend/src/api/knowledge-base/index.ts:83-129`，实际 `post` 在 128 行）。
- 成功 toast：**「已创建知识库」**（zh-CN.ts:4231）。
- **注意：创建成功后弹窗不关，而是原地切成 edit 模式**（`editorMode` 由 `savedKbId` 决定，550；`isPostCreateSession` 552）。底部因此出现 `postCreateHint.footer` 说明（459-466）。
- **跳转发生在列表页回调里**，且是有条件的：

```
// KnowledgeBaseList.vue:1508-1524
const handleKBEditorSuccess = (kbId: string) => {
  const shouldOpenDetailForUploadGuide = !isContextualGuideDone('kbDetail')
  chatResources.invalidateKnowledgeBaseDetail(kbId)
  fetchList(true).then(() => {
    if (shouldOpenDetailForUploadGuide && kbId && !uiStore.showKBEditorModal) {
      goDetail(kbId)          // → router.push(`/platform/knowledge-bases/${id}`)
    }
    …
  })
}
```
即：**"知识库详情上传引导"未完成过 → 自动跳到详情页**；否则只刷新列表、留在列表页（`goDetail` 定义在 1489-1491）。

- 失败：`MessagePlugin.error(error?.message || '操作失败')`；特别地，向量存储错误码 `2200`/`2201` 会给出专用文案并跳回「向量存储」段（1614-1632；zh-CN.ts:4498-4499）。
- 编辑模式保存：`updateKnowledgeBase` **`PUT /api/v1/knowledge-bases/{id}`**（api:139-164）+ `updateKBConfig`，成功 **「配置已保存」**（1575；zh-CN.ts:4235）；若索引策略变化且已有文件，弹 `DialogPlugin.confirm`「重建索引」/「索引策略已变更，是否对已有的 {count} 篇文档重新处理？这可能需要一些时间。」（1587-1608；zh-CN.ts:4443-4444），确认后 `rebuildKBIndex` → **`POST /api/v1/knowledge-bases/{kbId}/rebuild-index`**（api:209-211）。

#### 1.7 状态

- **列表页空态**（`EmptyState`）：标题 `knowledgeList.empty.title`「暂无知识库」+ 描述 `knowledgeList.empty.description`「点击左侧快捷操作"新建知识库"按钮创建第一个知识库」（KnowledgeBaseList.vue:595-596；zh-CN.ts:4840-4841）。收藏空态/最近空态**刻意不放创建按钮**（604-611）。
- **未初始化横幅**：`hasUninitializedKbs` 时显示 `knowledgeList.uninitializedBanner`「部分知识库尚未初始化，需要先在设置中配置模型信息才能添加知识文档」（KnowledgeBaseList.vue:30-31；判据 `isInitialized` 1451-1459；zh-CN.ts:4786）。
- **加载态**：6 个 `kb-card-skeleton`（36-46）。
- **弹窗加载态**：`SettingsModalShell :loading`（4）；模型列表加载失败 `MessagePlugin.error('加载模型列表失败')`（879）。

---

### 流程 2：文件怎么上传

#### 2.1 三个入口

| 入口 | 位置 | 证据 |
|---|---|---|
| **详情页"添加文档"下拉**（图标按钮 `file-add`，tooltip = `knowledgeBase.addDocument`「添加文档」） | 筛选条最右侧，`data-guide="kb-detail-add-doc"` | KnowledgeBase.vue:2436-2442 |
| **全局拖拽**（拖到平台任意位置） | 平台外壳在 `document` 上以 capture 监听 dragenter/dragover/dragleave/drop | platform/index.vue:199-203 |
| **空知识库的拖放区提示** | 列表为空时渲染 `EmptyKnowledge` | KnowledgeBase.vue:2525-2533 → `components/empty-knowledge.vue:6-11` |

下拉菜单项（`KbUploadSourceDropdown.vue:104-130`）：

| 菜单文案 | value | 行为 |
|---|---|---|
| `upload.uploadDocument`「上传文档」 | `upload` | 触发 `<input type="file" multiple>`（:3-10） |
| `upload.uploadFolder`「上传文件夹」 | `uploadFolder` | 触发 `<input type="file" webkitdirectory multiple>`（:11-18） |
| `knowledgeBase.importURL`「导入网页」 | `importURL` | 打开小 `t-dialog`，标题 `knowledgeBase.importURLTitle`「导入网页」，字段 `urlLabel`「URL地址」，placeholder「请输入网页URL，例如：https://example.com」，提示「支持导入各类网页内容，系统会自动提取和解析网页中的文本内容」（:39-59；zh-CN.ts:6803-6813） |
| `upload.onlineEdit`「在线编辑」 | `manualCreate` | 仅在 `include-manual` 时出现（详情页传了，:2438）→ `uiStore.openManualEditor({mode:'create', status:'draft'})`（KnowledgeBase.vue:1726-1734） |

全局拖拽的实现细节：

```
// platform/index.vue:150,173-174,192-193
ismask.value = true                                  // dragover 时显示整页遮罩
const droppedFiles = await collectDroppedFiles(event)
if (droppedFiles.length === 0) { … }
window.dispatchEvent(new CustomEvent('weknora:knowledge-file-drop', {
  detail: { kbId: getCurrentKbId(), files: droppedFiles }
}))
```
`KnowledgeBase.vue:1211-1216` 收到后校验 kbId 匹配即走 `handleUploadSourceFiles(files)`——**与点按钮完全同一条路**（含标签与逐批处理设置）。

遮罩文案（`components/upload-mask.vue:8-10`）：
- `file.upload`「上传文件」（zh-CN.ts:5020）
- `knowledgeBase.pdfDocFormat`「pdf、doc 格式文件，不超过10M」
- `knowledgeBase.textMarkdownFormat`「text、markdown格式文件，不超过200K」

> 注：这三行是**静态营销文案**，与真实校验阈值不一致（真实阈值见 2.2）。

#### 2.2 校验与限制（前端）

`filterUploadFiles`（`views/knowledge/utils/uploadSources.ts:29-73`）在**打开确认弹窗前**过滤：

- 文件夹上传时，路径任一段以 `.` 开头 → 静默跳过（`hiddenFileCount`，51-57）
- 视频扩展名 → 跳过：`UPLOAD_VIDEO_EXTENSIONS = ['mp4','mov','avi','mkv','webm','wmv','flv']`（:3，:60-63）
- `kbFileTypeVerification(file, multiFile, dynamicTypes)`（:65）：
  - 类型白名单：**优先用后端解析引擎列表**（`supportedFileTypes`，来自 `editorResources`）；为空集时回退到内置默认白名单（`frontend/src/utils/fileTypeVerification.ts:1-24`）：`pdf, txt, md, docx, doc, pptx, ppt, epub, html, htm, mhtml, jpg, jpeg, png, csv, xlsx, xls, mp3, wav, m4a, flac, ogg`
  - 大小上限：`MAX_FILE_SIZE_BYTES`，默认 **50 MB**（`frontend/src/utils/index.ts:23-27`）；优先级 运行时 `window.__RUNTIME_CONFIG__.MAX_FILE_SIZE_MB` > `VITE_MAX_FILE_SIZE_MB` > 50
- 一次可加多个文件、也可以一次加整个文件夹；**前端未发现"文件数量上限"**（批量下载才有 200 项上限，见流程 5）。并发由队列限制为 3（见 2.4）。

提示文案（照抄）：

| 场景 | 文案 | 位置 |
|---|---|---|
| 全部因类型被跳过 | `knowledgeBase.allFilesSkippedNoEngine`「所选文件类型暂无可用解析引擎，已全部跳过」 | KbUploadSourceDropdown.vue:180；zh-CN.ts:7024 |
| 部分因无引擎被跳过 | `filesSkippedNoEngine`「{count} 个文件因无可用解析引擎被跳过」 | :164；zh-CN.ts:7025 |
| 视频被过滤 | `videosFilteredNoVLM`「已跳过 {count} 个视频文件（暂不支持视频上传）」 | :161；zh-CN.ts:6800 |
| 类型不支持（来自校验工具） | `error.unsupportedFileType`「不支持的文件类型！」 | utils/index.ts:83；zh-CN.ts:3009 |
| 超过大小 | `error.fileSizeExceeded`「文件大小不能超过 {size}M！」 | utils/index.ts:71；zh-CN.ts:3008 |
| URL 为空 / 非法 | 「请输入URL」/「请输入有效的URL」 | KbUploadSourceDropdown.vue:192,198；zh-CN.ts:6806-6807 |
| 详情页头部的类型预警（非拦截） | `unsupportedTypesHint`「部分文档类型（{types}）暂无可用解析引擎，上传后将无法解析」+「前往配置 →」 | KnowledgeBase.vue:2302-2309；zh-CN.ts:6801-6802 |

#### 2.3 上传确认弹窗（`UploadConfirmDialog.vue`）

- 形态：自定义全屏遮罩弹窗（不是 `t-dialog`），`overlay` + `modal`（1-5）。
- 标题：`uploadConfirm.title` = **「上传文档确认」**（:806；zh-CN.ts:6675）。（manual 模式「在线编辑发布确认」，reparse 模式「重新解析确认」，803-807）
- 布局三栏：
  1. **左：文件清单**（13-123）。显示每个 URL 行（标签 `uploadConfirm.urlItemLabel`「URL」）与每个文件行（图标 + 文件名 + 相对目录 + 大小 + 单条移除按钮 `common.remove`「移除」）。顶部有 `KbUploadSourceDropdown`（tooltip `uploadConfirm.continueAdd`「继续添加」，19-26）可继续加；空清单时显示 `uploadConfirm.noItems`「请至少添加一个文件或 URL」（121）。
  2. **中：配置导航**（125-157）。标题 `uploadConfirm.parseConfig`「解析配置」，`aria-label` = `configNav`「解析配置导航」。每个导航项右侧带状态角标，例：未选标签 → `summaryNoTags`「未设置」；已选 → `summaryTagsCount`「{count} 个标签」；解析引擎 → `navParserDefault`「默认」/`navParserCustomized`「已自定义」；分块 → `navChunkingSummary`「分块 {size}」+ `summaryParentChildShort`「父子分块」；多模态未开 → `statusOff`「未开启」，缺模型 → `statusNeedsSetup`「待配置」（error 态，并在 `multimodal` 段顶部插 `multimodalSetupHint`「含图片内容，请启用多模态并选择模型」）。逻辑在 918-1017+。
  3. **右：配置内容**（159-554）。分段（`v-show activeSection === …`）：
     - `tags`「文档标签」：说明 `tagsDescription`「为本批次导入的所有文档选择标签，可多选」，`t-select multiple filterable clearable`，placeholder `tagsPlaceholder`「请选择标签（可多选）」；空态 `tagsEmpty`「当前知识库暂无标签，可上传后在标签管理中创建」；加载失败 `tagsLoadFailed`「标签加载失败，可稍后在文档列表中设置」（161-192）
     - `parser`「解析引擎」（`KBParserSettings`）+ 若本批含 pdf 则出现 `pdfForceScanned.label`「按扫描件解析 PDF」（194-213）
     - `chunking`「分块设置」：策略 / 大小(100–4000) / 重叠(0–500)，「更多处理选项」折叠里有 分隔符(可创建) / token 上限(0–8192) / 语言(多选) / 父子分块开关 / 父块大小(512–8192) / 子块大小(64–2048)（215-352）
     - `multimodal`「图像处理」、`asr`「音频处理」
     - `summary`「文档摘要」：开关 `generateSummary`「生成文档摘要」，说明 `generateSummaryHint`「默认开启。关闭后跳过摘要生成，文档解析、索引及其他处理步骤仍按配置执行。」（483-501）
     - `question`（`advanced.questionGeneration.label`「AI 问题生成」，数量 1–10）
     - `graph`「知识图谱」：仅当系统图数据库已启用且本批开启（546-553；判据 882-889）
  - 顶部还有**「上传位置」**面包屑（30-63）：`destinationLabel`「上传位置」，点击弹 `FolderPickerMenu`（可换目录/新建），`destinationChange`「更改上传位置」。
- 底部：`uploadConfirm.cancel`「取消」/ `uploadConfirm.confirm` = **「确认上传并解析」**（556-563；zh-CN.ts:6691-6692）。`:disabled="!canConfirm"`。
- 隐藏的 `confirm` **不做文件校验**（`validateBeforeConfirm` 只检查 multimodal/asr 模型，1410-1414）；空清单时点确认走 `handleConfirm` → 提示 `uploadConfirm.noItems`（1444-1446）。
- 追加去重：`appendFiles` 用 `getUploadFileKey`（`webkitRelativePath + '\0' + size`，uploadSources.ts:11-14）判重 → 有新增则 `uploadConfirm.filesAdded`「已添加 {count} 个文件」，全重则 `filesAllDuplicate`「所选文件已在列表中」（1345-1366）；URL 重复 → `urlDuplicate`「该 URL 已在列表中」，成功 → `urlAdded`「已添加 URL」（1368-1375）。
- 文件夹批量提示键已定义但**本文档未在模板里找到使用点**：`folderUploadTitle`「文件夹「{name}」」、`folderUploadHint`「共 {count} 个文件，将保留本地目录结构」（zh-CN.ts:6713-6714）——标为不确定。

#### 2.4 进度显示

上传提交后由**全局队列 + 全局浮层**接管（页面切换不中断）：

```
// KnowledgeBase.vue:1602-1622（摘要）
const enqueueUploads = (files, options = {}) => {
  uploadTasksStore.enqueue({ kbId, kbName, targetFolder, tagIds, processConfig,
    uploads: files.map(file => ({ file, fileName: buildUploadFileName(file, targetFolder) })) })
}
```
- `buildUploadFileName`（`folderTree.ts:60-71`）把"目标目录 + webkitRelativePath 的父段"拼成 `fileName` 字段，后端据此拆出 `folder_path` + `file_name`；纯单文件传根目录时返回 `undefined`，保持与旧行为字节一致。
- Store：`stores/uploadTasks.ts:17-47`；行为：`stores/uploadTasksCore.ts`（`CONCURRENCY = 3`、`POLL_INTERVAL_MS = 3000`、`POLL_CHUNK_SIZE = 40`，:23-26）；队列：`stores/uploadQueue.ts`。
- 上传接口：`uploadKnowledgeFile(kbId, {file, fileName, tag_ids, process_config}, onProgress, {signal})` → **`POST /api/v1/knowledge-bases/{kbId}/knowledge/file`**（api:251-276）。进度来自 `postUpload` 的 `onProgress`（`event.progress` 或 `loaded/total`），见 uploadTasks.ts:29-31。
- 界面（`components/upload-tasks/UploadTasksPanel.vue`）：
  - 标题随阶段切换：`uploadTasks.titleUploading`「正在上传 {done}/{total}」→ `titleParsing`「正在解析 {done}/{total}」→ `titleDone`「全部完成」/`titleDoneWithIssues`「{ok} 个完成，{bad} 个未成功」/`titleCancelled`「上传已取消」（UploadTasksPanel.vue:100-107）
  - 副标题：`destination`「上传至「{name}」」或 `destinationMany`「上传至 {count} 个知识库」（91-94）
  - **四段堆叠进度条**（ready/active/failed/duplicate）+ 图例（`legend.ready`「可检索」/`active`「处理中」/`waiting`「等待中」/`failed`「失败」/`duplicate`「已存在」），以及 `remaining`「剩余约 {time}」（eta: 「{n} 秒/分钟/小时」）（283-300，144-148，81）
  - 阶段提示：`hintUploading`「上传完成前请不要关闭或刷新页面」/`hintParsing`「文件已全部上传，解析在后台继续，可以放心离开此页面」（153-154；zh-CN.ts:2626-2627）
  - 关闭时若仍在上传，`t-popconfirm`：`closeConfirm`「关闭后将取消剩余 {count} 个文件的上传」，确认按钮 `closeConfirmOk`「取消上传」，取消按钮 `closeConfirmKeep`「继续上传」（256-269）

#### 2.5 每行状态与失败/重试

单行文案由 `itemPhase` 决定（`components/upload-tasks/UploadTaskRow.vue:58-74`；状态机在 `stores/uploadTasksState.ts:47-75`）：

| 阶段 | 文案 | 备注 |
|---|---|---|
| `waiting` | `phaseWaiting`「等待上传」+ ` · ` + 文件大小 | |
| `uploading` | 进度百分比/大小 | |
| `saving` | `phaseSaving`「正在保存…」 | 字节已发完、等响应（服务端在算哈希/落盘） |
| `parsing` | `phasePending`「排队解析」或 `phaseParsing`「解析中」（按 `parse_status`） | |
| `ready` | `phaseFinalizing`「可检索，后台优化中」（finalizing）或 `phaseReady`「已完成」 | |
| `failed` | `phaseUploadFailed`「上传失败」或 `phaseParseFailed`「解析失败」 | |
| `duplicate` | `phaseDuplicate`「知识库中已有相同文件」 | |
| `cancelled` | `phaseCancelled`「已取消」或 `phaseDeleted`「已删除」 | |

- 单行动作：`uploadTasks.cancel`「取消」、`uploadTasks.retry`「重试」、`uploadTasks.open`「查看」（UploadTaskRow.vue:43-45）。
- 底部：`cancelAll`「全部取消」（仅在上传中时）；`retryFailed`「重试 {count} 个」（仅在 `summary.retryable > 0` 时）（UploadTasksPanel.vue:347-362）。
- 重试可行性：`retry()` 只对 `transfer` 为 `failed` 或 `cancelled` 且 payload 还在的行生效（uploadQueue.ts:220-227）；**已 `saving` 的行不允许取消**（198-214 有显式注释：整包已发完，abort 会隐藏一条仍会被创建的行）。
- 重复文件：服务端 409 + `code === 'duplicate_file'` → `classifyUploadResult` 归为 `duplicate`（uploadTasksState.ts:227-236），带上已存在的 `knowledgeId`。
- 失败提示：行内状态文字 + `store.retryItem/retryFailed`；错误信息取自 `result?.error?.message || result?.message`（uploadTasksState.ts:235）。**没有单独的 toast 错误横幅**。
- 轮询：`needsParsePolling` 只对 `transfer==='uploaded'` 且 `parseStatus ∈ {undefined,'pending','processing','finalizing'}` 的行开启（uploadTasksState.ts:78-82），每 3 s 一批（`POLL_CHUNK_SIZE=40`），走 `batchQueryKnowledge` → **`GET /api/v1/knowledge/batch?ids=…&kb_id=…`**（uploadTasks.ts:34-42；api:440-446）。连续 3 次查不到该 id 才判 `deleted`（`MISSING_POLLS_BEFORE_DELETED = 3`，uploadQueue.ts:81,279）。
- 列表刷新：队列结束一轮转账后 dispatch `window` 事件 `knowledgeFileUploaded`（uploadTasks.ts:43-45），详情页/列表页监听并刷新；节流 2 s、合并窗口 150 ms（uploadTasksCore.ts:27-30；createListRefreshThrottle 在 uploadQueue.ts:330-368）。详情页对"批中刷新"（`settled === false`）在 `page > 1` 时**跳过**，避免把列表打回第一页（KnowledgeBase.vue:1179-1193）。

#### 2.6 上传后走到哪一步

- 上传成功即把 `parseStatus = data.parse_status || 'pending'` 写入队列行（uploadQueue.ts:158-164），随后进入 3 s 轮询直到 `completed`/`finalizing`。
- 界面上体现为：浮层行文案 `排队解析`/`解析中` → `可检索，后台优化中` → `已完成`；同一条文档在详情页列表中同步显示对应状态标签（见流程 3 状态机）。
- 若知识库启用了 Wiki/图谱等，还会探测 Wiki 索引状态：`fetchWikiStatusOnce`（页面上有 5 s `setInterval`，KnowledgeBase.vue:144），并 `scheduleWikiStatusProbes()` 打几次延时探测（155-160）。
- **URL 导入不在上传队列里**：`executeUrlImport` 直接 `createKnowledgeFromURL` → **`POST /api/v1/knowledge-bases/{kbId}/knowledge/url`**（api:280-285），成功 `knowledgeBase.urlImportSuccess`「已导入 URL」、失败「URL导入失败！」、`duplicate_url` → 「该URL已存在」（KnowledgeBase.vue:1624-1667）。

#### 2.7 上传前的就绪门槛

`ensureDocumentKbReady()` 在打开上传前检查（被 `handleUploadSourceFiles`/Url/Manual 调用，KnowledgeBase.vue:1716/1722/1727）。相关文案（zh-CN.ts:6900-6905）：
- `notInitialized`「该知识库尚未完成初始化配置，请先前往设置页面配置模型信息后再上传文件」
- `missingStorageEngine`「该知识库尚未选择存储引擎，请先前往设置页面配置存储引擎后再上传内容。」
- `missingStorageEngineUpload`「请先配置存储引擎后再上传内容」
- `getInfoFailed`「获取知识库信息失败，无法上传文件」
- `missingId`「缺少知识库ID」

---

### 流程 3：内容怎么管理

#### 3.1 页面骨架（`KnowledgeBase.vue` 模板 2234-2593）

```
知识库（面包屑）› [KB 切换下拉] › 文档            ← 文档/（wiki 时）Wiki/知识图谱 三个 breadcrumb tab
  副标题：knowledgeEditor.document.subtitle「支持点击或拖拽上传，多格式文档自动解析并智能分块，快速构建可检索的知识库」
  ┌ KbFolderTree 左侧目录树（仅 showFolderTree = !isFAQ && hasFolders）
  └ 右侧：
      目录面包屑（根目录 › …）+ 筛选时显示「（含子目录）」
      筛选条：搜索框 | 标签筛选 | 文件类型 | 解析状态 | 来源 | 日期范围    ‖ 批量管理/取消选择 | 视图切换 | 添加文档
      列表区（卡片 or 列表，无限滚动；空态/骨架屏）
      底部浮动批量条（batchMode 或已选 > 0 时显示）
  DocContent 抽屉（详情/分块）
```
- 面包屑与 KB 切换：KnowledgeBase.vue:2240-2264（`menu.knowledgeBase`「知识库」、`knowledgeEditor.document.title`「文档」，zh-CN.ts:4221）
- Wiki 型知识库额外有 `Wiki`/`knowledgeEditor.wikiBrowser.tabGraph` 两个 breadcrumb tab，并在索引时显示 loading 指示（2266-2287）
- 右上两个按钮：`KBInfoPopover`（「查看知识库信息」）+ 设置（`knowledgeBase.settings`「设置」）（2290-2299）
- 视图切换：`knowledgeBase.viewModeGrid`「卡片视图」/`viewModeList`「列表视图」，`aria-label` = `viewModeToggle`「切换视图」（2422-2435）。**默认 `grid`**，选择持久化在 `localStorage['weknora.kb.docs.viewMode']`（425-436）。
- FAQ 型知识库**整个页面换成** `FAQEntryManager`（2558-2562）。

#### 3.2 列表列与卡片字段

**列表视图列**（`DocumentListView.vue:262-272`，顺序即渲染顺序）：

| 列 | 表头文案 | 内容 |
|---|---|---|
| 勾选 | —（`aria-label`/`title` = `knowledgeBase.selectAll`「全选」） | 表头 checkbox，支持 indeterminate |
| 文件名 | `columnName`「文件名」 | 文件图标 + 名称（去扩展名，见 `useKnowledgeBase.ts:70-78`）+ 可选目录链接 + 描述 |
| 标签 | `columnTag`「标签」 | 标签 chips（超出折叠为 `+N`）；无标签时显示 `+ 标签`（349-351） |
| 来源 | `columnSource`「来源」 | 图标 + 文案（`channel*`/`typeFile` 等，`getSourceInfo` 108-128） |
| 大小 | `columnSize`「大小」 | `formatFileSize`，空显示 `--` |
| 状态 | `columnStatus`「状态」 | 状态标签（见 3.6） |
| 更新时间 | `columnUpdatedAt`「更新时间」 | `YY-MM-DD HH:mm` |
| 操作 | `columnActions`「操作」 | `…` 弹出菜单（`v-if="canEdit"`） |

- 目录行会插在文档行之前，显示 `folderTree.folderCardCount`「{count} 个文档」（277-303）。
- **没有排序列**：所有表头都是纯文本 `role="columnheader"`，无点击排序；排序参数在 `listKnowledgeFiles` 里也不存在（api:302-340）。

**卡片视图**（`DocumentCardView.vue:317-687`）：标题 + `…` 菜单 + 状态区 + 底部标签/来源/时间等；同样支持目录卡片（321-337）。

#### 3.3 搜索 / 筛选 / 分页

| 能力 | 控件 | 文案 | 行为 / 参数 | 证据 |
|---|---|---|---|---|
| 搜索 | `t-input` | placeholder `docSearchPlaceholder`「搜索文档名称...」 | **300 ms 防抖**后 `resetPage()+loadKnowledgeFiles()`；回车/清空也触发；传 `keyword` | KnowledgeBase.vue:2364-2370；1135-1146；726 |
| 标签筛选 | `KnowledgeTagFilter`（popup + chips 多选） | 触发按钮 `tagFilterTitle`「按标签筛选」；未选(cleared) 显示 `allTags`「全部标签」；选了 1 个显示标签名；多个显示 `tagFilterMulti`「{count} 个标签」；面板内搜索 placeholder `tagSearchPlaceholder`「输入标签名称关键字」；无结果显示 `tagEmptyResult`「未找到匹配的标签」；底部 `tagManageLink`「管理标签…」 | 传 `tag_ids`（**逗号拼接**） | KnowledgeBase.vue:2372-2376；724；KnowledgeTagFilter.vue:28-52,55-147 |
| 文件类型 | `t-select clearable` | `fileTypeFilter`「文件类型」；首项 `allFileTypes`「全部类型」 | 选项：`pdf/docx/doc/pptx/ppt/epub/mhtml/txt/md/url/manual/mp3/wav/m4a/flac/ogg` | 612-630；2377-2385 |
| 解析状态 | `t-select clearable` | `parseStatusFilter`「解析状态」；首项 `allParseStatuses`「全部状态」 | 选项见 3.6 | 632-641 |
| 来源 | `t-select clearable` | `sourceFilter`「来源」；首项 `allSources`「全部来源」 | 选项：`web`(本地上传)/`url`/`manual`/`api`/`browser_extension` + 各 IM 渠道（飞书/飞书云盘/Notion/语雀/Confluence/GitLab/腾讯IMA/微信/企业微信/钉钉/Slack/IM） | 645-664 |
| 时间范围 | `t-date-range-picker` | placeholder `[updatedTimeFrom, updatedTimeTo]` =「起始时间」「结束时间」；禁止选未来 | 传 `start_time`/`end_time` | 2404-2413；666-668 |
| 排序 | — | — | **无** | — |
| 分页 | 无限滚动 | — | `page`/`pageSize`（`pageSize = Math.max(35, 视口高/148*5)`）；滚动到底 `scrollTop + clientHeight >= scrollHeight - 10` 且 `cardList.length < total` 时加载下一页 | 409-412,759-765,1857-1879 |

**筛选的隐藏语义**：任一筛选生效即 `isFiltering = true`（`folderTree.ts:186-202` 的 `isFilteringDocuments`），此时：
- 传 `folder_recursive = true`（搜索整个子树，KnowledgeBase.vue:734）
- 面包屑追加 `folderTree.searchingSubtree`「（含子目录）」（2359-2361）
- 子目录行被丢弃（列表变平，712-716）
- 每行在文件名下显示所属目录路径（`showDocumentFolderPath`，718；DocumentListView.vue:319-323）

#### 3.4 单条文档操作

菜单组件 `DocumentActionMenu.vue`。**每个动作的可见条件与文案（照抄）**：

| 动作 | 文案 | 可见条件 | 二次确认正文 | 行 |
|---|---|---|---|---|
| 下载 | `common.download`「下载」 | `canDownload && (type==='file' \|\| type==='manual')` | 无 | 47-54 |
| 编辑文档 | `knowledgeBase.editDocument`「编辑文档」 | `type === 'manual'` | 无（打开在线编辑器） | 57-60 |
| 查看处理过程 | `knowledgeStages.viewTrace`「查看处理过程」 | `traceVisible` | 无 | 63-66 |
| 重建知识 | `knowledgeBase.rebuildDocument`「重建知识」 | 总有；解析中则无 popconfirm 直接触发 | `rebuildConfirm`「确认重建文档"{fileName}"？该操作会清理现有分块并重新解析。」 | 68-84 |
| 停止解析 | `knowledgeBase.cancelParse`「停止解析」 | `parse_status ∈ {pending, processing, finalizing}`（36-40） | `cancelParseConfirmBody`「确认停止解析"{title}"？已写入的分块会保留，可稍后通过"重建"重新触发；优化阶段（摘要 / 问答 / 知识图谱）的待执行任务会被立即丢弃。」 | 86-96 |
| 移动到目录 | `moveToFolder.action`「移动到目录」 | `canMutateKnowledge` | 无（同菜单内切目录选择器） | 98-102 |
| 移动到…（其他知识库） | `moveDocument`「移动到...」 | `canMutateKnowledge` | 三级子菜单：目标 KB 列表 → `moveConfirmTitle`「确认移动设置」+ 模式二选一 + `moveConfirm`「确认移动」 | 104-108；DocumentListView.vue:420-476 |
| 批量管理 | `menu.batchManage`「批量管理」 | `canMutateKnowledge \|\| canDownload` | 无（进入多选模式） | 110-114 |
| 删除文档 | `deleteDocument`「删除文档」 | 总有 | `confirmDeleteDocument`「确认删除文档"{fileName}"，删除后将无法恢复」；确认按钮 `confirmDelete`「删除」 | 116-126 |

调用的接口：

| 动作 | api 函数 | HTTP |
|---|---|---|
| 下载 | `downKnowledgeDetails(id)` | `GET /api/v1/knowledge/{id}/download`（api:422-424） |
| 删除单条 | `delKnowledgeDetails(id)` | `DELETE /api/v1/knowledge/{id}`（api:413-415）——实际走 `deleteKnowledgeDocuments` + `waitForKnowledgeDeletion` 轮询确认 |
| 重建 | `reparseKnowledge(id, {process_config})` | `POST /api/v1/knowledge/{id}/reparse`（api:400-402） |
| 停止解析 | `cancelKnowledgeParse(id)` | `POST /api/v1/knowledge/{id}/cancel-parse`（api:404-406） |
| 移动到目录 | `moveKnowledgeToFolder(kbId, ids, folderPath)` | `POST /api/v1/knowledge/folder`（api:372-378） |
| 移动到其他 KB | `listMoveTargets(sourceKbId)` + `moveKnowledge({...mode})` + `getKnowledgeMoveProgress(taskId)` | `GET /api/v1/knowledge-bases/{id}/move-targets`、`POST /api/v1/knowledge/move`、`GET /api/v1/knowledge/move/progress/{taskId}`（api:226-243） |
| 单条打标签 | `updateKnowledgeTagBatch({updates:{[knowledgeId]: tagIds}})` | `PUT /api/v1/knowledge/tags`（api:536-538） |

删除的异步语义（KnowledgeBase.vue:2000-2063）：
- 提交后 `MessagePlugin.info` `deleteSubmitted`「删除任务已提交，正在等待完成。」
- 轮询 `batchQueryKnowledge` 确认；`completed` → `batchDeleteSuccess`「成功删除 {count} 个文档」/`deleteSuccess`「已删除知识」；`failed` → `deleteTaskFailed`「删除任务失败，请查看文档错误详情后重试。」；超时未决 → `deletePending`「删除尚未完成，请稍后刷新查看结果。」
- 提交后异常 → `deleteStatusUnavailable`「暂时无法确认删除结果，请稍后刷新查看文档状态。」
- 提交前异常 → `batchDeleteFailed`「批量删除失败」或 `deleteFailed`「删除失败，请稍后再试！」

#### 3.5 详情 / 预览怎么打开

- 点卡片或列表行 → `openKnowledgeItem(item)`（KnowledgeBase.vue:1980-1990）：
  - 若为**手动创建的草稿**（`type==='manual' && parse_status==='draft'`）且 `canEdit` → 直接进在线编辑器 `handleManualEdit`
  - 否则 → `openCardDetails(item)` → `<DocContent :visible="isCardDetails" :details="details" …>`（2552-2555；`components/doc-content.vue`，2979 行）
- 详情数据：`getCardDetails` → `getKnowledgeDetails(id)` → **`GET /api/v1/knowledge/{id}`**（`hooks/useKnowledgeBase.ts:103-146`；api:385-391）
- **分块列表**：`getfDetails(id, page)` → `getKnowledgeDetailsCon` → **`GET /api/v1/chunks/{id}?page&page_size=25`**，页大小常量 `KNOWLEDGE_CHUNK_PAGE_SIZE = 25`（api:448-452；hooks/useKnowledgeBase.ts:148-177）
- 分块可编辑且有版本历史：`updateDocumentChunk` `PUT /api/v1/chunks/{knowledgeId}/{chunkId}`、`listChunkRevisions` `GET …/revisions`、`revertDocumentChunk` `POST …/revert`（api:460-473）
- 文档元数据/摘要：`updateKnowledgeMetadata` `PUT /api/v1/knowledge/{id}`（`custom_metadata`）、`updateKnowledgeSummary`（`description`）、`regenerateKnowledgeSummary` `POST /api/v1/knowledge/{id}/regenerate-summary`（api:475-485）
- 相关文案：`customMetadata`「自定义元数据」、`metadataCapabilityHint`「用于文档总结，并在文档被召回后作为文档级上下文辅助回答；不会参与索引或影响召回排序」、`noCustomMetadata`「暂无自定义元数据」、`addMetadataField`「添加元数据字段」、`regenerateSummary`「重新生成摘要」/`generateSummary`「生成摘要」、`noDocumentSummary`「暂无文档摘要」、`chunkHistory`「分块编辑历史」、`currentVersion`「当前版本」、`noChunkHistory「暂无编辑历史」、`revertRevision`「回滚版本」（zh-CN.ts:6856-6888）
- 也有"只开处理过程抽屉、不开详情"的路径 `handleViewTrace`（1781-1792）。
- **深链**：`?knowledge_id=xxx` 会自动打开对应文档详情，并先 `getKnowledgeDetails` 解出它所在目录再切目录（`tryAutoOpenDocument`，1230-1259）；也监听 `weknora:open-knowledge` window 事件（1274-1280）。

#### 3.6 状态机与枚举（详见第四节）

界面渲染逻辑在 `DocumentListView.vue:136-174`（`computeStatus`）与 `DocumentCardView.vue`（`inFlightCardStatusText`）。同一 `parse_status` 在**列表里叫一套名字、筛选下拉里叫另一套名字**，这是本项目的真实情况，照抄如下：

| `parse_status` | 列表状态标签（+ theme/图标） | 筛选下拉选项文案 |
|---|---|---|
| `pending` | `statusProcessing`「解析中」（primary + 旋转 loading） | `parseStatusPending`「等待中」 |
| `processing` | `statusProcessing`「解析中」（同上） | `parseStatusProcessing`「处理中」 |
| `finalizing` | 若 `summary_status ∈ {pending,processing}` → `generatingSummary`「生成摘要中...」；否则 `statusFinalizing`「优化中」（均 primary + 旋转） | `parseStatusFinalizing`「整理优化中」 |
| `completed` | `statusCompleted`「已完成」（success） | `parseStatusCompleted`「已完成」 |
| `failed` | `statusFailed`「失败」（danger + close-circle） | `parseStatusFailed`「失败」 |
| `cancelled` | `statusCancelled`「已取消」（warning + close-circle） | `parseStatusCancelled`「已取消」 |
| `draft` | `statusDraft`「草稿」（warning） | `parseStatusDraft`「草稿」 |
| `completed` + `summary_status ∈ {pending,processing}` | `generatingSummary`「生成摘要中...」（遗留兜底路径） | — |
| 其它/空 | 纯文本 `--` | — |

（zh-CN.ts:6936-6938, 6986-6991, 7004-7010；DocumentListView.vue:136-174）

#### 3.7 空态 / 加载态 / 错误态

| 场景 | 显示 | 证据 |
|---|---|---|
| 知识库完全没有文档 | `EmptyKnowledge`：`emptyKnowledgeDragDrop`「知识为空，拖放上传」+ `pdfDocFormat`「pdf、doc 格式文件，不超过10M」+ `textMarkdownFormat`「text、markdown格式文件，不超过200K」 | KnowledgeBase.vue:2525-2533；empty-knowledge.vue:6-11；zh-CN.ts:6993-6995 |
| 在某个目录里但目录为空 | `folderTree.emptyFolder`「这个文件夹里还没有文档」 | 2527-2531；zh-CN.ts:6747 |
| 有筛选但无结果 | `folderTree.emptySearch`「没有匹配的文档」 | 2528-2530；zh-CN.ts:6748 |
| 首屏加载中 | 8 个 `knowledge-card-skeleton`（`t-skeleton animation="gradient"`） | 2454-2469 |
| 目录树加载中 | 5 行 skeleton | KbFolderTree.vue:30-34 |
| 标签下拉加载中 | 8 个 chip skeleton | KnowledgeTagFilter.vue:75-82 |
| 分块加载失败 | `chunkLoadFailed`「分块加载失败」 | hooks/useKnowledgeBase.ts:160,165；zh-CN.ts:7027 |
| 知识库列表加载失败 | `loadingFailed`「加载知识库失败」 | zh-CN.ts:7022（列表页） |
| 类型不支持的操作 | `operationNotSupportedForType`「当前知识库类型不支持该操作」 | zh-CN.ts:7023 |
| 拖动非文件内容 | `dragFileNotText`「请拖拽文件而不是文本或链接」 | zh-CN.ts:6996 |

**页面上的状态轮询**：`updateStatus(analyzeList)` 对 `pending/processing/finalizing` 或"completed 但 summary 未落"的行**每 1500 ms** 调一次 `GET /api/v1/knowledge/batch?ids=…`，直到不再需要（KnowledgeBase.vue:1348-1416；判据 `needsStatusPolling` → `wikiStatusRefresh.ts:10-14`）。

---

### 流程 4：怎么打标签

#### 4.1 标签的层级：**知识库级**

- 所有增删改都带 `kbId`：`listKnowledgeTags(kbId)` `GET /api/v1/knowledge-bases/{kbId}/tags`、`createKnowledgeBaseTag(kbId, {name})` `POST …/tags`、`updateKnowledgeBaseTag(kbId, tagId, {name})` `PUT …/tags/{tagId}`、`deleteKnowledgeBaseTag(kbId, seqId, {force})` `DELETE …/tags/{seqId}`（api:508-534）
- 标签**归属知识库**，不能跨知识库复用（URL 结构即证明）。
- 文档与标签是**多对多**，绑定关系由 `PUT /api/v1/knowledge/tags` body `{updates: {knowledgeId: tagIds[]}}` 建立/替换（api:536-538）。

#### 4.2 在哪里创建 / 编辑

三个入口都能打开标签对话框或管理抽屉：

| 入口 | 位置 | 证据 |
|---|---|---|
| 标签筛选面板底部「管理标签…」（`tagManageLink`） | 详情页筛选条内的 `KnowledgeTagFilter` | KnowledgeBase.vue:2376（`@manage="openTagManageDrawer"`）；KnowledgeTagFilter.vue:109-113 |
| 单条文档的标签单元格（点击 chips 或 `+ 标签`） | 列表视图标签列 | DocumentListView.vue:333,342,349 → `@tag-edit` → KnowledgeBase.vue:2518 → `openTagEditDialog` |
| 批量条「批量打标签」→ 对话框里的「管理标签…」 | 见 4.4 | BatchTagDialog.vue:34-43 |

- **单条打标签**：`TagEditDialog`（`t-dialog`，`width="400px"`，`footer=false`）。标题 `tagEditDialogHeading`「编辑标签」，副标题是文档名。分两段：`tagEditSelectedSection`「已选标签」/`tagEditAvailableSection`「可选标签」；各自有 `tagClearAction`「清空已选」、搜索框 placeholder `tagEditSearch`「搜索标签...」、空态 `tagEditNoSelected`「暂未选择」/`tagEmptyResult`「未找到匹配的标签」/`noTags`「暂无标签」。底部计数 `tagSelectedCount`「已选 {count} 个标签」+「取消」/「确认」（TagEditDialog.vue:1-87；zh-CN.ts:6736-6799）
- **新建标签**：对话框底部有一个输入框，placeholder `tagNewPlaceholder`「输入新标签名称，回车添加」，`maxlength=40`，回车提交；搜索无结果时还会出现按钮「新建标签 "{query}"」（TagEditDialog.vue:59-69）。通过共享 composable `useKnowledgeTagSelection`（`@/composables/useKnowledgeTagSelection`）调 `createKnowledgeBaseTag`。
- **管理抽屉**：`KbTagManageDrawer`（`SettingDrawer`，`width="480px"`，可缩放）。标题 `tagManageTitle`「管理标签」，描述 `tagManageDescription`「新建、重命名或删除知识库标签」。列表段标题 `tagManageListSection`「标签列表」；搜索 placeholder `tagSearchPlaceholder`「输入标签名称关键字」；每行显示标签名 + 计数（文档型 `tagManageDocCount`「{count} 个文档」，FAQ 型 `tagManageFaqCount`「{count} 个 FAQ」）+ 改名按钮（title `tagEditAction`「重命名」）+ 删除按钮（title `tagDeleteAction`「删除」）。空态 `tagEmptyResult`「未找到匹配的标签」。分页 50/页 + 「加载更多」（`TAG_PAGE_SIZE = 50`，KbTagManageDrawer.vue:230；`tenant.loadMore`「加载更多」）
- 名称必填校验：`MessagePlugin.warning` `tagNameRequired`「请先输入标签名称」（KbTagManageDrawer.vue:365,401）
- 成功提示：创建 `tagCreateSuccess`「已创建标签」；改名 `tagEditSuccess`「标签已更新」；删除 `tagDeleteSuccess`「标签已删除」

#### 4.3 颜色与分组：**界面没有**

- `createKnowledgeBaseTag` / `updateKnowledgeBaseTag` 的 API 类型**接受 `color?: string` 与 `sort_order?: number`**（api:516-529），但：
  - `KbTagManageDrawer` 创建时只传 `{ name }`（KbTagManageDrawer.vue:370），改名只传 `{ name }`（:411）
  - `TagEditDialog` / `BatchTagDialog` 都只用共享 composable 的 tag 选择逻辑，均无颜色控件
  - 对全部 `*Tag*.vue` 文件 grep `color`，命中的**全是 CSS 变量**，没有一个取色器/色板组件
- 结论：**颜色字段存在但 UI 未暴露**；`sort_order` 同样无 UI（排序靠列表返回顺序）。**没有任何标签分组/层级/父子概念。**

#### 4.4 给文档打标签 & 批量打标签

- **单条**：点标签单元格 → `TagEditDialog` → 「确认」→ `handleKnowledgeTagChange`：
```
// KnowledgeBase.vue:998-1008
await updateKnowledgeTagBatch({ updates: { [knowledgeId]: tagIds } })
MessagePlugin.success(t('knowledgeBase.tagUpdateSuccess'))   // 「标签已更新」
```
- **批量**：批量条上的「批量打标签」（`knowledgeBase.batchTag`，icon `discount`）→ `handleBatchTag` → `BatchTagDialog`：
  - 标题 `batchTagDialogHeading`「批量打标签」
  - 副标题 `batchTagSubtitle` = **「为选中的 {count} 个文档统一设置标签（将替换文档原有标签）」** ← **语义是"替换"，不是"追加"**
  - 结构同 `TagEditDialog`（已选/可选两段 + 搜索 + 新建输入框 + 管理标签链接），底部 `tagSelectedCount`「已选 {count} 个标签」+ 取消/确认
  - 预选值 = 选中项标签的**交集**（`batchTagPreSelectedIds`，KnowledgeBase.vue:507-522）
  - 确认 → `onBatchTagConfirm` → 对每个 id 都写同一份 tagIds 数组 → `updateKnowledgeTagBatch`（2076-2098）
  - 成功 `batchTagSuccess`「已为 {count} 个文档成功设置标签」；失败 `batchTagFailed`「批量打标签失败」
  - FAQ 型走 `knowledgeBase.batchTag` 对应的 FAQ 批量条（见流程 5），最终调 `updateFAQEntryTagBatch(kbId, {updates:{entryId: tagId|null}})` → `PUT /api/v1/knowledge-bases/{kbId}/faq/entries/tags`（api:540-542）

#### 4.5 按标签筛选

- 组件 `KnowledgeTagFilter`：`t-popup` + chips（按钮列），**多选**，点击切换；面板顶部显示 `tagFilterTitle`「按标签筛选」+ 总数 `(total || tags.length)`；每个 chip 右上角显示计数（文档型取 `knowledge_count`，FAQ 型取 `chunk_count`，`countOf` at :37）
- 已选表达式：触发按钮上标签名以「、」连接；hover 出现 `common.clear`「清空」图标（`clear()` 置 `cleared=true` 并传空数组）
- 传给列表：`filterParams.tag_ids = selectedTagIds.join(',')`（KnowledgeBase.vue:724）→ `GET /api/v1/knowledge-bases/{kbId}/knowledge?…&tag_ids=a,b,c`
  - **多个标签之间是 AND 还是 OR：前端只是逗号拼接，语义由后端决定；本文档未查后端，故不确定。**
- 切换标签即时重载列表（`watch(selectedTagIds, …, {deep:true})`，1115-1120），并清空当前多选（2168-2173）
- 标签被删除后：若删的正是当前筛选项 → 清空筛选并重载；否则延时 800 ms 再刷新（`onTagManageChanged`，974-996）

#### 4.6 删除标签

- 抽屉里删除按钮外包 `t-popconfirm`，正文 `getDeleteConfirmContent`：
  - 文档型：`tagDeleteDescDoc` = **「确定删除标签"{name}"？该标签下的所有文档将被一并删除」**
  - FAQ 型：`tagDeleteDesc`——**该 key 在 zh-CN.ts / en-US.ts / ja-JP.ts / ko-KR.ts / ru-RU.ts 中均不存在**（grep 全 locales 只命中 `tagDeleteDescDoc`）。FAQ 型知识库的这条确认文案会退化成显示原始 key。
- 确认按钮 `common.delete`「删除」/ 取消 `common.cancel`「取消」
- **实现上永远 force**：`deleteKnowledgeBaseTag(props.kbId, tag.seq_id, { force: true })`（KbTagManageDrawer.vue:428）→ `DELETE /api/v1/knowledge-bases/{kbId}/tags/{tagSeqId}?force=true`。也就是说**没有"标签下有文档时先拦截"的分支**，确认文案里的"所有文档将被一并删除"是真的会执行。
- 注意删除用的是 `tag.seq_id`（数字）而不是 `tag.id`（字符串）：`deleteTag` 传 `tag.seq_id`（428），本地状态里 `id` 被 `String()` 化（322-325）。

#### 4.7 标签 vs「分类目录」：两套并存的独立体系

| | 标签（tag） | 目录（folder_path） |
|---|---|---|
| 层级 | 知识库级标签库 + 文档多对多 | 单一字符串路径（`a/b/c`），文档属于**一个**目录 |
| 存储 | 独立 tags 表 + 关联表 | 文档行的 `folder_path` 列；注释明确「folder_path is display-only，两种操作都只是列更新，不重新解析/分块/嵌入」（KnowledgeBase.vue:825-827） |
| API | `…/knowledge-bases/{kbId}/tags`、`PUT /knowledge/tags` | `GET …/knowledge/folders`、`POST /knowledge/folder`、`PUT …/knowledge/folders` |
| 界面位置 | 筛选条里的标签下拉；列表标签列；批量条"批量打标签" | 左侧 `KbFolderTree`；列表目录行/面包屑；批量条"移动到目录" |
| 能否共存 | **可以**：同一个文档既有 `tags` 也有 `folder_path`（`KnowledgeItem` 接口同时声明两者，DocumentListView.vue:15-30） |
| 目录不存在的处理 | — | 目录由 `folder_path` 派生，"不存在的路径会被这次调用创建"（api:367-371 注释） |
| 目录限制 | — | `MAX_FOLDER_DEPTH = 16`、`MAX_FOLDER_SEGMENT_LENGTH = 128`、`MAX_FOLDER_PATH_LENGTH = 1024`（folderTree.ts:14-18，注释说与服务端 `types.MaxKnowledge*` 保持同步） |

---

### 流程 5：多选与批量操作

#### 5.1 怎么进入多选

四条途径：

1. **列表视图：每行常驻勾选框**（不需先进"批量模式"）
   - 表头：`t-checkbox :checked="allSelected" :indeterminate="someSelected" :disabled="!items.length"`，`title` = `selectAll`「全选」（DocumentListView.vue:262-265）
   - 行内：`t-checkbox :checked="selectedIds.has(item.id)"`（:308-311）
   - 渲染条件：`v-if="canEdit || canDownload"`（263, 309）
   - `allSelected`/`someSelected` 定义在 182-187（`someSelected = 有选中但非全选`）
2. **卡片视图：勾选框只在"批量模式"下出现**
   - `v-if="(canEdit || canDownload) && batchMode"`（DocumentCardView.vue:351）
   - 进入方式：筛选条右侧按钮，文案随状态切换 `menu.batchManage`「批量管理」↔ `knowledgeBase.clearSelection`「取消选择」（KnowledgeBase.vue:2416-2421，`toggleBatchMode` 1936-1939）
   - 也可从单条卡片的 `…` 菜单点「批量管理」→ `handleEnterBatchFromCard`：**清空当前选择**然后开 `batchMode=true`（1954-1959；注释说这是对齐会话列表的 UX）
   - 从列表视图切到卡片视图时，若已有选中会自动开 `batchMode`，否则勾选态不可见（1945-1951）
3. **Shift 范围选**：`toggleSelectRow(id, checked, shiftKey)`——`shiftKey` 为真且存在 `lastSelectedIndex` 时，把 `[min,max]` 闭区间整体 add/delete（1896-1912）。事件链：`t-checkbox @change="(c, ctx) => onRowCheckboxChange(item, c, ctx)"` → 取 `ctx.e.shiftKey`（DocumentListView.vue:193-196, 309-310）
4. **框选（marquee）**：拖动容器空白处拉出选择框
   - `useMarqueeSelect({ containerRef: knowledgeScroll, itemSelector: '.knowledge-card[data-select-id], .doc-list-row[data-select-id]', selectedIds, getItemId: el => el.dataset.selectId, enabled: (canEdit||canDownload) && !isFAQ && cardList.length>0, onSelectionStart: () => { batchMode = true } })`（KnowledgeBase.vue:1960-1975）
   - 有 add / subtract 两种模式（模板 2451-2453 的 `is-add` / `is-subtract` class）
   - 框选结束后抑制本次 click，避免误开详情（`shouldSuppressDocClick`，1981）

**选中集合的存法与生命周期**：
- `const selectedIds = ref<Set<string>>(new Set())`（KnowledgeBase.vue:440，注释说明依赖 Vue 3.5 对 Set 的响应式追踪）
- **能跨页保留**（滚动加载更多不会清空），但列表刷新后会**剔除已不可见的 id**：
```
// KnowledgeBase.vue:2185-2189
if (selectedIds.value.size === 0) return
const visible = new Set(items.map(i => i.id))
for (const id of selectedIds.value) if (!visible.has(id)) selectedIds.value.delete(id)
```
- **任一筛选/搜索/知识库切换都会清空选择**（避免对隐藏项动手）：
```
// KnowledgeBase.vue:2168-2173
watch([selectedTagIds, docSearchKeyword, selectedFileType, selectedParseStatus, selectedSource, updatedTimeRange, kbId],
  () => { clearSelection() })
```
- 因此**不存在"跨页全选所有筛选结果"**；最接近的是批量条上的「全选已加载」

#### 5.2 批量条（`DocumentBatchBar.vue`）

- 出现条件：`v-if="visible || count > 0"`，父组件传 `:visible="batchMode || selectedIds.size > 0"`，外层再 `v-show="batchMode || selectedIds.size > 0"`（DocumentBatchBar.vue:39；KnowledgeBase.vue:2536-2541）
- 位置：列表滚动容器下方的 `doc-batch-bar-anchor`（吸底浮动），`role="region"`，`aria-label` = `selectedCount`
- **左侧**：计数 + 两个文字按钮
  - `knowledgeBase.selectedCount` = **「已选 {count} 项」**（:43；zh-CN.ts:6954）
  - `knowledgeBase.selectLoaded` = **「全选已加载」**（:44-47；zh-CN.ts:6965）→ 对应事件 `select-loaded` → 父组件 `toggleSelectAll(true)`（KnowledgeBase.vue:2543）
  - `knowledgeBase.clearSelection` = **「取消选择」**（:48-51；zh-CN.ts:6955）→ `@cancel="handleBatchCancel"` → `clearSelection(); batchMode=false`（KnowledgeBase.vue:1941-1944）
- **右侧动作**（全部在 `t-tooltip`/`t-popconfirm` 里，禁用条件统一为 `count === 0 || deleteLoading || reparseLoading || tagLoading || downloadLoading`）：

| 动作 | 文案 | 可见条件 | 二次确认 | 事件 |
|---|---|---|---|---|
| 批量下载 | `batchDownload`「批量下载」；loading 时换成 `batchDownloading`「正在打包下载…」 | `canDownload`；tooltip `batchDownloadHint` | 无 | `download` |
| 重建知识 | `rebuildDocument`「重建知识」 | `canMutate` | `confirmBatchReparseDocument`「确认重建选中的 {count} 个文档？现有内容将被清除并重新解析。」，确认按钮 `confirmBatchReparse`「确认并重新解析」 | `reparse` |
| 批量打标签 | `batchTag`「批量打标签」 | `canMutate` | 无（打开对话框） | `batchTag` |
| 移动到目录 | `moveToFolder.action`「移动到目录」 | `canMutate && showMoveToFolder`（详情页传 `:show-move-to-folder="canEdit"`） | 无（popup 内 `FolderPickerMenu`） | `moveToFolder(path)` |
| 批量删除 | `batchDelete`「批量删除」 | `canMutate` | `confirmBatchDeleteDocument`「确认删除选中的 {count} 个文档？删除后将无法恢复。」，确认按钮 `confirmDelete`「删除」 | `delete` |

`batchDownloadHint` 全文（zh-CN.ts:6959）：
> 「下载所选文件为 ZIP，每批最多 200 项、原始文件合计 512 MiB。全选仅包含已加载的文档；没有原始文件的网页条目会自动跳过。ZIP 会保留知识库文件夹。」

#### 5.3 每个批量动作的落地

**批量下载**（KnowledgeBase.vue:448-505）
- 常量：`MAX_BATCH_DOWNLOAD_FILES = 200`、`MAX_BATCH_DOWNLOAD_BYTES = 512 * 1024 * 1024`（448-449）
- 过滤掉没有原始文件的行（`isBatchDownloadableKnowledge`）；全不可下载 → `batchDownloadNoFiles`「所选文档没有可下载的原始文件」
- 有跳过 → `batchDownloadSkipped`「已跳过 {count} 个没有原始文件的文档」
- 超量 → 复用 `batchDownloadHint`；超体积 → `batchDownloadTooLarge`「所选文件合计超过 512 MiB，请减少选择后分批下载」
- api：`batchDownloadKnowledge(kbId, ids, signal)` → **`POST /api/v1/knowledge-bases/{kbId}/knowledge/batch-download`**，`responseType:'blob'`，`timeout: 300000`，`signal`（api:427-433）
- 成功：前端把 blob 存成本地文件，文件名 **`knowledge-files-${Date.now()}.zip`**（硬编码，:486）；toast `batchDownloadStarted`「已开始保存 ZIP，解压后即可按文件夹批量上传文件」
- 失败：`batchDownloadFailed`「批量下载失败，请稍后重试」；切换 KB 或组件卸载会 `abort()`（504-505）
- 单文件下载文件名走 `resolveKnowledgeDownloadFileName`（`views/knowledge/knowledgeDownloadFileName.ts`，19 行）

**移动到目录**（`moveKnowledgeIntoFolder`，KnowledgeBase.vue:842-855）
- api：`moveKnowledgeToFolder(kbId, ids, folderPath)` → **`POST /api/v1/knowledge/folder`** body `{kb_id, knowledge_ids, folder_path}`
- 成功 `moveToFolder.success`「已移动 {count} 个文档」；失败 `moveToFolder.failed`「移动失败」
- 之后：`clearSelection()` + `batchMode=false` + `resetPage()` + 重载列表 + 重载目录树
- 目录选择器 `FolderPickerMenu`：第一行固定是 `folderTree.rootRow`「根目录」（:124-131）；每个目录行右侧有 `folder-add` 按钮新建子目录（`newFolderAddRoot`「在根目录下新建子目录」/`newFolderAddUnder`「在「{folder}」下新建子目录」）；新建输入框 placeholder `newFolderPlaceholder`「输入新目录名称」，回车提交，Esc 取消；重名 → `moveToFolder.duplicate`「该目录已存在」；新建成功 emit `create` 让调用方立即移动（:218-235）
- 目录**重命名**在左侧树的行内菜单里（`folderTree.rename`「重命名」，placeholder `renamePlaceholder`「输入文件夹名称」）；成功 `renameSuccess`「文件夹已重命名"、失败 `renameFailed`「文件夹重命名失败」、非法（把目录移进自己的子目录）`renameInvalid`「不能把文件夹移动到它自己的子目录下」（KnowledgeBase.vue:857-884；KbFolderTree.vue:88-114）

**批量打标签** → 见流程 4.4。

**批量重建**（`confirmBatchReparse`，KnowledgeBase.vue:561-…）
- 先剔除正在解析中的行（`isParseInFlight`）；全被剔除 → `MessagePlugin.info` `rebuildInProgress`「当前文档正在解析中，请稍后重试」；有剔除 → `batchReparseSkippedInFlight`「已跳过 {count} 个正在解析中的文档」
- api：`batchReparseKnowledge(kbId, ids)` → **`POST /api/v1/knowledge/batch-reparse`** body `{kb_id, ids, process_config?}`（api:696-702）
- 乐观更新：命中行本地置 `parse_status='pending'` 并清空摘要/描述，随后 `awaitBatchReparseReflection` 最多轮询 30 次 × 400 ms 让服务端状态落地（524-559）
- 成功 `batchReparseSuccess`「已提交 {count} 个重建任务」；失败 `batchReparseFailed`「批量重建失败」

**批量删除**（`confirmBatchDelete` → `deleteKnowledgeDocuments(..., batch=true)`，KnowledgeBase.vue:2000-2069）
- api：`batchDeleteKnowledge(kbId, ids)` → **`POST /api/v1/knowledge/batch-delete`** body `{kb_id, ids}`（api:418-420）
- 提交后：`clearSelection()` + `batchMode=false`，然后轮询确认（文案见表，见流程 3.4 的删除语义）

**"批量移动到其他知识库"不在批量条上**——只在单条菜单里（`moveDocument`「移动到...」）。

#### 5.4 批量条的禁用/权限条件

- 下载按钮额外硬限制：`:disabled="count === 0 || count > 200 || …"`（DocumentBatchBar.vue:57）
- 动作可见性由两个 prop 控制：`can-download="canDownloadKnowledge"`、`can-mutate="canMutateKnowledge"`（KnowledgeBase.vue:2539）
- 整个批量条只有当 `(canDownloadKnowledge || canMutateKnowledge) && cardList.length` 时才可能显示"批量管理"入口按钮（KnowledgeBase.vue:2416）
- 勾选框本身的渲染条件是 `canEdit || canDownload`（DocumentListView.vue:263,309；DocumentCardView.vue:351）

#### 5.5 目录树（`KbFolderTree.vue`）

- 只有知识库**真的有目录**时才渲染：`showFolderTree = !isFAQ && hasFolders`（KnowledgeBase.vue:696；注释：全是单文件上传的知识库看起来不变）
- 节点：
  - **根节点**固定第一行，标签 `folderTree.rootRow`「根目录」，`title` = `rootRowTip`「知识库根目录，未归入子文件夹的文档在此」（KbFolderTree.vue:47；folderTree.ts:132-153）
  - 子目录行：展开/收起箭头 + 目录图标 + 名称 + **后代文档计数徽章** `totalCount`（:83-87）
  - 每行可重命名（仅 `canEdit && kind === 'folder'`，:88-114）
- **没有"全部文件"这类伪节点**——注释明确：「根就是树的一个真实节点……所以没有单独的 'all documents' 伪行」（folderTree.ts:3-10）
- 折叠状态持久化在 `localStorage['weknora.kbFolderTreeCollapsed']`（KnowledgeBase.vue:671）
- 目录行也会作为"卡片/列表行"出现在文档列表顶部（当侧栏折叠时），显示 `folderCardCount`「{count} 个文档」（DocumentListView.vue:277-303；DocumentCardView.vue:321-337）
- **删除目录的 UI 不存在**：只有重命名（rename）与"新建子目录"（新建靠移动时创建）

#### 5.6 FAQ 的批量（`FAQBatchBar.vue`）

- 渲染条件：`count > 0 && (canEdit || canManage)`（:35）
- 左侧：`selectedCount`「已选 {count} 项」+ `clearSelection`「取消选择」
- 右侧动作（与文档批量条**不同**）：

| 动作 | 文案 | 条件 | 确认 |
|---|---|---|---|
| 批量改标签 | `knowledgeEditor.faq.batchUpdateTag` | `canEdit` | 无 |
| 批量启用 | `knowledgeEditor.faq.batchEnable` | `canEdit && disabledCount > 0` | 无 |
| 批量停用 | `knowledgeEditor.faq.batchDisable` | `canEdit && enabledCount > 0` | 无 |
| 批量删除 | `knowledgeEditor.faq.batchDelete` | `canManage` | `knowledgeEditor.faq.confirmBatchDelete`「{count}」 |

与文档批量条的区别：**多了启用/停用、少了下载/重建/移动到目录**（FAQ 条目的 state 是 `is_enabled`/`is_recommended`，不是 `parse_status`）。FAQ 的字段批量接口是 `updateFAQEntryFieldsBatch` → `PUT /api/v1/knowledge-bases/{kbId}/faq/entries/fields`（api:598-600），支持 `by_id`/`by_tag`/`exclude_ids` 三种寻址；FAQ 还有独立的导出（`exportFAQEntries` → `GET …/faq/entries/export?format=csv|json`，api:618-622）。

---

## 三、状态机 / 枚举

### 3.1 前端上传队列的两级状态

**`TransferStatus`**（客户端 HTTP 上传生命周期，`stores/uploadTasksState.ts:9`）：
`'queued' | 'uploading' | 'uploaded' | 'failed' | 'duplicate' | 'cancelled'`

**`ItemPhase`**（每行真正显示的那一个状态，合并传输与解析两段，`uploadTasksState.ts:35-43`）：
`'waiting' | 'uploading' | 'saving' | 'parsing' | 'ready' | 'failed' | 'duplicate' | 'cancelled'`

折叠规则（`itemPhase`，47-75）：
```
transfer queued                → waiting
transfer uploading, 未发完      → uploading
transfer uploading, 已发完      → saving      （等待服务端哈希/落盘响应）
transfer failed/duplicate/cancelled → 同名 phase
transfer uploaded + parseStatus:
  finalizing | completed       → ready
  failed                       → failed
  cancelled | deleting | deleted → cancelled
  其它（含 undefined）          → parsing
```

**`UploadStage`**（浮层整体阶段，45）：`'uploading' | 'parsing' | 'done'`（`waiting+uploading>0 → uploading`；否则 `parsing>0 → parsing`；否则 `done`，170-171）

**需要继续轮询解析状态的条件**（78-82）：`transfer === 'uploaded' && knowledgeId && parseStatus ∈ {undefined,'pending','processing','finalizing'}`

**上传结果分类**（`classifyUploadResult`，227-236）：`code === 'duplicate_file'` → `duplicate`；`success === true` → `uploaded`；否则 `failed`。

**并发与节流常量**（`stores/uploadTasksCore.ts:23-30`）：`CONCURRENCY = 3`、`POLL_INTERVAL_MS = 3000`、`POLL_CHUNK_SIZE = 40`、`LIST_REFRESH_INTERVAL_MS = 2000`、`LIST_REFRESH_COALESCE_MS = 150`；另 `MISSING_POLLS_BEFORE_DELETED = 3`（uploadQueue.ts:81）。

### 3.2 文档 `parse_status` 枚举与显示

| 取值 | 来源证据 | 列表状态标签 | 筛选下拉文案 | 其它 |
|---|---|---|---|---|
| `pending` | KnowledgeBase.vue:634；uploadQueue.ts:162（默认） | 「解析中」（primary/loading 旋转） | 「等待中」 | 可"停止解析" |
| `processing` | :635 | 「解析中」（同上） | 「处理中」 | 可"停止解析" |
| `finalizing` | :639；uploadTasksState.ts:63 | `summary_status ∈ {pending,processing}` 时「生成摘要中...」否则「优化中」 | 「整理优化中」 | 可"停止解析"；登录后仍继续轮询 |
| `completed` | :636 | 「已完成」（success） | 「已完成」 | 若 summary 未落则显示「生成摘要中...」并继续轮询 |
| `failed` | :637 | 「失败」（danger + close-circle） | 「失败」 | 图标 close-circle |
| `cancelled` | :638 | 「已取消」（warning + close-circle） | 「已取消」 | `cancelKnowledgeParse` 的结果 |
| `draft` | :640 | 「草稿」（warning） | 「草稿」 | 仅 `type='manual'`；`draftTip`「暂存内容，未参与检索」 |
| `deleting` | uploadTasksState.ts:69 | 浮层按 `cancelled` 处理 | — | 未出现在筛选下拉 |
| `deleted` | uploadTasksState.ts:70；uploadQueue.ts:279 | 浮层 `phaseDeleted`「已删除」 | — | 连续 3 次轮询查不到才置 |
| 空 / 其它 | DocumentListView.vue:173 | 纯文本 `--` | — | |

配套字段：`summary_status`（`pending`/`processing`/…，KnowledgeBase.vue:1327-1328；DocumentListView.vue:24）、`error_message`（hooks/useKnowledgeBase.ts:32）、`description`。

### 3.3 `source` / `channel`（来源）枚举

- `source` 筛选值：`web`(本地上传) / `url` / `manual` / `api` / `browser_extension` + 各 IM 渠道（KnowledgeBase.vue:645-664）
- `channel` 值与显示文案映射在 `getSourceInfo`（DocumentListView.vue:108-128）：`feishu`「飞书」、`feishu_drive`「飞书云盘」、`lark_drive`「Lark 云盘」、`notion`、`yuque`、`confluence`、`gitlab`、`ima`「腾讯 IMA」、`wechat`「微信」、`wecom`「企业微信」、`dingtalk`「钉钉」、`slack`、`im`「IM 渠道」；`type==='url'` → 「网页」；`type==='manual'` → 「手动创建」；缺省 → 「上传」（`channelUpload`）
- `type` 文档类型枚举：`'file' | 'manual' | 'url'`（由 `DocumentActionMenu.vue:48,57` 与 `handleManualEdit` 的分支推断）+ FAQ 知识库整体类型 `type: 'document' | 'faq'`

### 3.4 知识库（KB）相关枚举

| 枚举 | 取值 | 证据 |
|---|---|---|
| KB 类型 | `'document' \| 'faq'` | api:86；ui.ts:9 |
| KB 编辑器模式 | `'create' \| 'edit'` | ui.ts:7 |
| 索引策略 | `indexing_strategy{vector_enabled, keyword_enabled, wiki_enabled, graph_enabled}` | api:121-126；KnowledgeBaseEditorModal.vue:1414-1419 |
| 向量存储来源 | `'env' \| 'user' \| 'shared' \| 'unavailable'` | api:72 |
| 向量存储可用性 | `'available' \| 'unavailable'` | api:73 |
| KB 是否"已初始化" | 推导式：`summary_model_id` 必须有；`vector_enabled||keyword_enabled` 时 `embedding_model_id` 必须有 | KnowledgeBaseList.vue:1451-1459 |
| AI 描述状态 | `'ready' \| 'empty' \| 'failed' \| string` | api:198 |
| 创建者筛选 | `'all' \| 'mine' \| 'others'` | api:41 |
| 列表分区 key | `pinned`/`mine`/`tenantOthers`/`tenantReadonly`/`sharedByMe`/`sharedEditable`/`sharedReadonly`（文案「置顶/我创建的/本空间 · 其他成员/本空间 · 仅查看/我共享的/共享给我 · 可编辑/共享给我 · 仅查看」） | KnowledgeBaseList.vue 模板 54-147；zh-CN.ts:4814-4821 |
| 卡片能力徽章 | `features.knowledgeGraph`「知识图谱」/`multimodal`「多模态」/`questionGeneration`「问题生成」/`wiki`「Wiki」 | KnowledgeBaseList.vue:214-251；zh-CN.ts:4787-4792 |

### 3.5 其它相关状态

| 枚举 | 取值 | 证据 |
|---|---|---|
| FAQ 导入进度状态 | `'pending' \| 'processing' \| 'completed' \| 'failed'` | api:643 |
| 数据源同步日志状态 | `running`「同步中」/`success`「成功」/`partial`「部分成功」/`failed`「失败」/`canceled`「已取消」 | zh-CN.ts:1015-1021 |
| 数据源连接状态 | `active`「已连接」/`paused`「已暂停」/`error`「异常」 | zh-CN.ts:1032-1036 |
| 同步冲突策略 | `overwrite`「覆盖更新」/`skip`「跳过已存在」 | zh-CN.ts:1028-1031 |
| 审计结果 | `failed`/`pending`/`completed`/`partial` | auditActionLocaleDefaults.ts:81-96 |
| 分块编辑载荷 | `ChunkEditPayload{content?, is_enabled?, expected_revision?}` | api:454-458 |

---

## 四、与我方产品的对应（只做映射，不设计）

我方现状（前提，来自任务书）：DSH 侧栏一个「知识库」页（React）；现有能力 = 目录树（两个内置树 + 自建夹）、标签、行勾选 + 全选 + 浮动批量条（已选 X 项 / 取消选择 / 批量打标签 / 移动到目录 / 批量删除）、详情页显示发布/生效/废止日期、搜索语法 `安全+半导体-冶金`。

> **一条来自源码的旁证（可直接引用）**：评估文档 §三 的表里写着 WeKnora「无标准/法规现行性、废止、被替代、施行日期」这一维——那是**基于官方文档**的判断。
> 本次读源码**从界面侧独立确认了同一结论**：文档列表的列只有 文件名/标签/来源/大小/状态/更新时间/操作（`DocumentListView.vue:266-272`），
> 状态列只渲染 `parse_status`（`computeStatus`，:136-174），**在 `frontend/src/views/knowledge` 全目录 grep `废止|生效日期|发布日期|effective_date|publish_date|repeal|abolish|expiry` 零命中**，
> 且在 `zh-CN.ts` 全文件 grep `废止|发布日期` 零命中（`生效` 的 56 处命中全部与本主题无关：如记忆条目「生效中」、共享链接「生效中」、设置「修改后立即生效」）；
> 筛选下拉也只有 文件类型/解析状态/来源/时间范围（`KnowledgeBase.vue:612-668`）。
> 即：**它的"时间"只有"上传/更新时间"，没有"效力时间"**——这从"文档里没写"升级为"源码里没有"。

| 流程 | 我们对应在哪 | 缺什么 |
|---|---|---|
| **1 新建知识库** | 侧栏「知识库」页 → 新建；WeKnora 走的是 `uiStore.openCreateKB` 驱动的**非路由弹窗**，我们也应是弹层而非整页路由——这一点我们**已有对应**（入口 + 弹层形态都对得上） | 缺 WeKnora 的**多段左侧导航 + 分段表单**（基本信息/模型配置/向量存储/解析引擎/分块/多模态/ASR/图谱/高级共 9-10 段）；缺**"校验失败自动跳回出错段"**这一交互（`validateForm` + `currentSection = …`）；缺**"创建成功后原地切 edit 模式继续配置"**（`savedKbId`/`isPostCreateSession`）；缺**模型未就绪时把导航预定位到「模型配置」**；缺 `document/faq` **库类型概念** |
| **2 文件上传** | 详情页的"添加/上传"入口；`UploadTasksPanel` 那种**全局上传队列浮层**正是我们"已选 X 项浮动条"同一类 chrome | 缺**确认前置弹窗**（标签 + 解析配置 + 上传位置三栏，`UploadConfirmDialog`）——我们现在是选完即传；缺**四段堆叠进度条 + 图例（可检索/处理中/等待中/失败/已存在）**；缺**逐文件"重试/取消/查看"**与"重试 {count} 个"；缺**重复文件识别**（`duplicate_file` → 「知识库中已有相同文件」）；缺**文件夹上传 + 目录结构保留**（`webkitdirectory` + `buildUploadFileName`）；缺**上传位置可选目录**；缺**解析阶段与"离开页面也不中断"的队列分离**（我们把队列放在 store 里而不是页面里） |
| **3 内容管理** | 知识库详情页的文档列表；我们的"详情页显示发布/生效/废止日期"对应 WeKnora 文档详情抽屉里的元数据区 | 缺**两种视图（卡片/列表）切换 + localStorage 记忆**；缺**目录树 + 目录面包屑 + "（含子目录）"语义**（筛选时自动递归整个子树）；缺**多条件筛选条**（文件类型/解析状态/来源/时间范围，我们现在只有搜索语法）；缺 **`parse_status` 7 值状态机与其两套文案**（列表名 ≠ 筛选名）；缺**无限滚动**（我们未知是否分页）；缺**单条动作菜单**（下载/编辑/重建知识/停止解析/移动到目录/移动到其他库/批量管理/删除，且"解析中"时"重建"跳过二次确认直接执行）；缺**删除是异步任务 + 前端轮询确认**（`deleteSubmitted`/`deletePending`/`deleteTaskFailed`/`deleteStatusUnavailable` 四种结果文案）；缺**状态自动轮询**（1.5 s 一批 batch 查询） |
| **4 打标签** | 我们**已有**标签 + 批量打标签，且 WeKnora 的标签也是**知识库级**——层级判断与我们一致 | 缺**语义确认**：WeKnora 的批量打标签是**替换**（`batchTagSubtitle`「将替换文档原有标签」）且预选值是选中项的**交集**，我们需要明确自己是替换还是追加；缺**多选标签筛选面板**（chips + 每个标签的文档计数 + 面板内搜索 + "管理标签…"）；缺**标签管理抽屉**（改名/删除 + 每标签计数 + 重建/删除后延时 800 ms 二次刷新）；缺**删除标签的破坏性语义**（WeKnora 恒 `force=true`，确认文案直说"该标签下的所有文档将被一并删除"）——我们是拦截还是同样连带删？这点必须定；无颜色/无分组这点**双方都没做**（WeKnora 有 `color` 字段但 UI 未暴露） |
| **5 多选与批量** | 我们**已有**行勾选 + 全选 + 浮动批量条（已选 X 项 / 取消选择 / 批量打标签 / 移动到目录 / 批量删除）——与 WeKnora 的 `DocumentBatchBar` 几乎一一对应 | 缺**半选（indeterminate）表头状态**；缺 **Shift 范围选**（`lastSelectedIndex` 闭区间）；缺 **框选 marquee**（add/subtract 两种模式 + 抑制误点）；缺**「全选已加载」**这个折中语义（WeKnora 明确不做"跨页全选所有筛选结果"）；缺**筛选变化即清空选择**这条安全规则；缺**批量下载 ZIP 的硬限制与文案**（≤200 项、≤512 MiB、跳过无原始文件的网页条目、保留目录结构）；缺**批量重建 + 乐观置 pending + 最多 30×400 ms 轮询落地**；缺**批量删除的分阶段反馈文案**；缺**"权限决定批量条动作可见性"**（`canDownload`/`canMutate`/`canEdit` 三个开关分别控制不同按钮）；**FAQ 型知识库的独立批量条**（启用/停用/删除，而非下载/重建）我们大概率没有对应物 |

---

## 五、我没查到 / 不确定

以下为诚实边界，均**未做推断填补**：

1. **`knowledgeBase.moreOptions` 这个 key 不存在**。`KbFolderTree.vue:101` 用它做目录行 `…` 按钮的 `aria-label`（`t('knowledgeBase.moreOptions')`），但 `zh-CN.ts` 的 `knowledgeBase` 块（6729-7061）内没有 `moreOptions`；全 locales grep `moreOptions` 只命中 `uploadConfirm.moreOptions`（zh-CN.ts:6680）。运行时该处会退化成显示原始 key。
2. **`knowledgeBase.tagDeleteDesc` 这个 key 不存在**。`KbTagManageDrawer.vue:278` 在 `isFaq` 时用它做删除确认正文，但 zh-CN/en-US/ja-JP/ko-KR/ru-RU **五个 locale 都没有**（只有 `tagDeleteDescDoc`）。FAQ 型知识库删除标签的确认文案会退化成原始 key。
3. **`uploadConfirm.folderUploadTitle` / `folderUploadHint` 两个 key 已定义但未找到使用点**（zh-CN.ts:6713-6714）。可能在我没读到的 `UploadConfirmDialog` 脚本段或别处使用，但我未定位到渲染位置，故不确定其触发时机。
4. **标签筛选的多选语义（AND / OR）不确定**。前端只做 `selectedTagIds.join(',')` 传给 `tag_ids`（KnowledgeBase.vue:724），语义在后端；我未读后端代码。
5. **后端字段语义未核**。`parse_status` 的每个取值到底对应后端生命周期的哪一步，我是从**前端映射与注释**推断的（如 `finalizing` = 主解析完成但摘要/问答/图谱等后处理仍在跑，见 `uploadTasksState.ts:61-62` 与 `KnowledgeBase.vue:1342-1347` 的注释），不是从服务端代码核实。
6. **`knowledgeBase.tagFilterMulti` 与其它带 `{count}` 的文案**我只核到 key 与中文原文，未实测复数/占位符在各种语言下的渲染结果。
7. **未读完整的两个巨型文件**：`FAQEntryManager.vue`（4721 行）与 `components/doc-content.vue`（2979 行）。本文档只覆盖了它们与知识库页面的**接线点**（`KnowledgeBase.vue:2560`、`:2552-2555`）；FAQ 条目的编辑/导入/导出细节、以及文档详情抽屉内部的分块编辑 UI，**未逐行读**。
8. **Wiki 相关界面未纳入范围**。`views/knowledge/wiki/WikiBrowser.vue`（5969 行）、`WikiRevisionDrawer.vue`、`WikiFolderActions.vue` 我只做了 grep 级确认（存在拖拽移动、目录 drop target 等），未读其流程——任务书的五件事不涉及 Wiki 页面。
9. **`settings/` 下 15 个知识库设置子组件未读**（`KBChunkingSettings`、`KBParserSettings`、`KBModelConfig`、`GraphSettings`、`KBAdvancedSettings`、`KBVectorStoreSettings`、`KBStorageSettings`、`KBShareSettings`、`DataSource*`、`KnowledgeBaseActivitySettings` 等）。我只记录了「哪个导航项挂哪个组件」，组件内部的字段清单、校验与接口调用未核。
10. **"重名知识库/重名标签"的处理**：知识库新建**确认无前端同名校验**；标签重名我**没有找到**显式前端校验（只看到标签名称必填 `tagNameRequired`），但未读后端，**不能断言后端不拦**。
11. **`t-upload` 组件未被使用**：`KnowledgeBase.vue` 与相关组件里上传走的是原生 `<input type="file">` + 全局 drop 事件，而不是 TDesign 的 `t-upload`。如果任务方预期看到 `t-upload`，那是不存在的。
12. **"文件数量上限"未找到**。前端只对**批量下载**限 200 项；单次上传的文件数、队列长度上限我未在前端找到常量，也未查后端。
13. **`views/knowledge/KnowledgeBaseReferenceNavigation.test.ts`** 这个测试文件的存在说明有「文档引用跳转」的额外行为（我看到了 `?knowledge_id=` 深链与 `weknora:open-knowledge` 事件两条路径），但该测试文件本身我未读。
14. **列表"操作"列在卡片/列表两个视图里的按钮数量不完全一致**（列表视图 `handleListAction` 对 `reparse` 不区分 in-flight，卡片视图 `handleCardAction` 会区分，见 KnowledgeBase.vue:2140-2142 vs 2159）。这是代码差异，**是否为有意设计我无法判断**。
15. **`doc-marquee` 的具体命中判定（相交面积阈值等）未读**——实现在 composable `useMarqueeSelect` 内，我反查了它的调用与暴露值（KnowledgeBase.vue:1960-1975）但未定位该 composable 的文件路径与实现。
