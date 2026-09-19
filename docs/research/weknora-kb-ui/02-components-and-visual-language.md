# WeKnora 知识库管理界面 —— 组件构成与视觉语言

- **调研对象**：`D:\AI\WeKnora`（Vue 3.5.34 + TDesign Vue Next `^1.19.2` + Pinia 3，`frontend/package.json:37-47`）
- **被读版本（可复现锚点）**：`VERSION` = `0.8.0`（`D:\AI\WeKnora\VERSION`）；`git rev-parse HEAD` = `b82fd6c0f9939e8497fa7474999dd1bde5d0d88d`（实测时间：本次会话）
- **范围**：只覆盖"知识库管理"这一块 —— 知识库列表页、知识库详情页（文档/分块）、及其用到的对话框/抽屉/卡片/空态/上传组件。其它页面（chat / agent / settings / integrations / wiki 正文）**不在本文范围**。
- **纪律：全程只读**。`git status --short` 在 `D:\AI\WeKnora` 的输出只有一行 `?? DEPLOY-NOTES.md`（**未跟踪、且在我开始前就已存在**，非我创建），**没有任何 `M` / `A` / `D` 行** ⇒ 未修改任何已跟踪文件。每条结论都带 `文件:行`。
- **许可证（若要借鉴，先看这一条）**：`D:\AI\WeKnora\LICENSE` 第 8 行原文 —— "This project is licensed under the MIT License except for the third-party components listed below, which is licensed under different terms."；第 6 行 `Copyright (C) 2025 Tencent. All rights reserved.`；MIT 正文起于第 11 行（`Terms of the MIT License:`），第 15 行是 Permission 段。第三方组件清单另见仓根 `THIRD_PARTY_NOTICES.md` 与 `licenses/` 目录。⇒ **可借鉴（MIT），但需随附版权与许可声明；且 TDesign 组件与其图标包是另一层许可，不能只署 WeKnora。** 本文只记录"它长什么样"，**不含任何搬运的源码片段**。
- **关于行号的一个陷阱**：`frontend/src/assets/theme/theme.css` 的**浅色主题整块被压在第 1 行**（一个 4KB 的单行），深色块在第 2–98 行。凡引用浅色块的变量，只能给到 `theme.css:1` + 变量名；深色块可以给精确行号。下文已逐条注明。

---

## 1. 组件清单

### 1.1 视图层（`frontend/src/views/knowledge/`）

| 组件 | 文件:行 | 职责 | 关键 props / 事件 |
|---|---|---|---|
| `KnowledgeBaseList.vue` | `views/knowledge/KnowledgeBaseList.vue:1`（模板 1–708，脚本 710–1558，样式 1560–2444） | **知识库列表页**：空间/收藏/最近侧栏 + 卡片网格 + 空态 + 新建/编辑弹窗 + 共享详情抽屉 | 本页无 props；含 `ListSpaceSidebar`、`EmptyState`、`KnowledgeBaseEditorModal`、`ShareKnowledgeBaseDialog`、`ContextualGuide` |
| `KnowledgeBase.vue` | `views/knowledge/KnowledgeBase.vue:1`（脚本 1–2232，模板 2234–2593，样式 2594–3398） | **知识库详情页**：面包屑 + 目录树 + 筛选条 + 卡片/列表双视图 + 详情抽屉 + 批量条；FAQ 类型走 `FAQEntryManager` | 无 props；`isFAQ` 分流（`KnowledgeBase.vue:2235` vs `2558`）；`viewMode: 'grid' \| 'list'`（`:2424`/`:2430`） |
| `KnowledgeBaseEditorModal.vue` | `views/knowledge/KnowledgeBaseEditorModal.vue:2`（模板 1–490） | **新建 / 编辑知识库**同一组件（全屏设置壳 + 左侧分区导航） | `visible` / `mode: 'create'\|'edit'` / `kb-id` / `initial-type`；事件 `update:visible`、`success`（调用点 `KnowledgeBaseList.vue:630-632`、`KnowledgeBase.vue:2565-2567`） |
| `FAQEntryManager.vue` | `views/knowledge/components/FAQEntryManager.vue`（161 KB） | FAQ 型知识库的问答条目管理（本文只在分流处登记，不展开） | `kb-id`（`KnowledgeBase.vue:2560`） |
| `WikiBrowser.vue` | `views/knowledge/wiki/WikiBrowser.vue:1` | Wiki / Graph 标签页容器（仅登记，不在"知识库管理"主路径） | `knowledge-base-id` / `view: 'graph'\|'browser'` / `can-edit`（`KnowledgeBase.vue:2320-2322`） |

### 1.2 列表与卡片

| 组件 | 文件:行 | 职责 | 关键 props / 事件 |
|---|---|---|---|
| `DocumentCardView.vue` | `views/knowledge/components/DocumentCardView.vue:317`（props/emits 40–80） | 文档**卡片网格**视图（含文件夹卡片、卡片内联打标签、悬停信息浮层） | props：`items`、`selectedIds:Set<string>`、`batchMode`、`canEdit`、`canDownload`、`canMutateKnowledge`、`tagList`、`folders`、`folderOptions`、`traceAvailableById`、`showFolderPath`、`moveMenuMode`/`moveTargetKbs`/`moveMode`/`moveSubmitting`；emits：`open`、`toggle-checkbox`、`action`、`tag-edit`、`open-folder`、`move-to-folder`、`move-select-target`、`move-back`、`move-confirm`、`update:moveMode` |
| `DocumentListView.vue` | `views/knowledge/components/DocumentListView.vue:258`（props/emits 32–75） | 文档**列表（表格式 grid）**视图，8 列，含吸顶表头、文件夹行、行内打标签、行级"更多"菜单 | 与卡片版同套 props，另加 `loading`、`traceVisibleIds`、`showFolderPath`；emits：`open`、`toggle-row`、`toggle-all`、`action`、`probe-trace`、`tag-edit`、`open-folder`、`reset-move-state` |
| `DocumentActionMenu.vue` | `views/knowledge/components/DocumentActionMenu.vue:45` | 文档"更多"菜单内的动作清单（下载/编辑/查看处理过程/重建/停止解析/移动到目录/移动到知识库/批量管理/删除） | props：`item`、`canDownload`、`canMutateKnowledge`、`traceVisible`、`fileName`；emits：`download`、`edit`、`view-trace`、`reparse`、`cancel-parse`、`move`、`move-folder`、`batch-manage`、`delete` |
| `FolderPickerMenu.vue` | `views/knowledge/components/FolderPickerMenu.vue:1` | 目录选择器（可内联新建子目录、可返回上一层） | props：`options`、`currentPath`、`showBack`、`allowReselect`；emits：`back`、`confirm(path)`、`create` |
| `ResourceOriginBadge.vue` | `components/ResourceOriginBadge.vue:1`（脚本 8–125） | 卡片右下角"来源"徽标（我创建 / 本空间 / 共享空间 / 外部共享） | props：`variant`、`creatorName`；文案取自 `i18n` `resourceOrigin.*`（`zh-CN.ts:7062-7073`） |
| `KbWikiBadge.vue` | `views/knowledge/components/KbWikiBadge.vue:1` | 卡片标题前的 Wiki 徽标（Lucide `book-open-text` 内联 SVG，15×15px） | 无 props；tooltip = `knowledgeList.features.wiki`（`:2`） |
| `KBSwitcherDropdown.vue` | `components/KBSwitcherDropdown.vue:1` | 详情页面包屑里的知识库切换下拉 | props：`kbList`、`currentKbId`；emits：`select(id)` |

### 1.3 筛选与批量

| 组件 | 文件:行 | 职责 | 关键 props / 事件 |
|---|---|---|---|
| `KnowledgeTagFilter.vue` | `views/knowledge/components/KnowledgeTagFilter.vue:55`（脚本 1–53） | 标签筛选**浮层**（触发器是个伪 input 按钮；面板内搜索 + chip 多选 + 加载更多 + "管理标签…"入口） | props：`search`(v-model)、`cleared`(v-model)、`tags`、`selectedIds`、`total`、`loading`、`loadingMore`、`hasMore`、`canManage`、`variant:'documents'`；emits：`change`、`load-more`、`manage` |
| `KbFolderTree.vue` | `views/knowledge/components/KbFolderTree.vue:1`（样式 240–473） | 详情页左侧**目录树**（可折叠、可重命名、显示每级文档数） | props：`tree`、`selectedPath`、`loading`、`canEdit`、`collapsed`；emits：`select`、`update:collapsed`、`rename` |
| `DocumentBatchBar.vue` | `views/knowledge/components/DocumentBatchBar.vue:37`（props/emits 6–30） | **批量操作条**（已选 N 项、全选已加载、取消选择、批量下载、批量重建、批量打标签、移动到目录、批量删除） | props：`count`、`deleteLoading`、`reparseLoading`、`tagLoading`、`downloadLoading`、`canDownload`、`canMutate`、`visible`、`showMoveToFolder`、`folderOptions`；emits：`cancel`、`delete`、`reparse`、`batchTag`、`download`、`selectLoaded`、`moveToFolder(path)` |
| `KbUploadSourceDropdown.vue` | `views/knowledge/components/KbUploadSourceDropdown.vue:1`（脚本 63–217） | **上传入口下拉 + 隐藏 file input + URL 导入对话框**（上传文档 / 上传文件夹 / 导入网页 / 在线编辑） | props：`acceptFileTypes`、`supportedFileTypes`、`includeManual`、`triggerIcon`、`triggerClass`、`tooltip`、`placement`；emits：`files(File[])`、`url(string)`、`manual()`；`defineExpose({ openUrlDialog })`（`:216`） |

### 1.4 对话框 / 抽屉

| 组件 | 文件:行 | 职责 | 关键 props / 事件 |
|---|---|---|---|
| `SettingsModalShell.vue` | `components/SettingsModalShell.vue:2`（样式 122–413） | 全屏"设置类"弹窗壳：遮罩 + 1080×780 面板 + 左侧分组导航 + 右侧内容 + 底栏。KB 编辑器和上传确认对话框都用它 | props：`visible`、`title`、`modelValue`(v-model)、`navGroups`、`loading`、`zIndex`(=1100 默认)、`overlayClass`、`navGuide`、`navItemGuidePrefix`；emits：`update:modelValue`、`close`；插槽：默认 / `nav` / `nav-icon` / `sidebar-header-extra` / `footer` / `footer-note` |
| `UploadConfirmDialog.vue` | `views/knowledge/components/UploadConfirmDialog.vue:1`（模板 1–570，样式 1475–2268） | **上传确认（"确认上传并解析"）三栏对话框**：左=待上传文件/URL 清单 + 上传位置面包屑，中=解析配置分区导航（含"待配置"红点），右=分区内容 + 底部取消/确认。一个组件覆盖 `file`/`manual`/`reparse` 三种 mode | 由 `useUploadConfirmStore` 驱动（`KnowledgeBase.vue:59`）；`dialogVisible`/`mode`/`localFiles`/`localUrls`/`destination`/`activeSection`；确认按钮文案随 mode 变（`confirmButtonText`，模板 `:561`） |
| `TagEditDialog.vue` | `views/knowledge/components/TagEditDialog.vue:2` | **单个文档**打标签对话框（`t-dialog` width 400px） | props：`visible`、`knowledgeName`、`kbId`、`tagList`、`selectedTags`、`canManage`；emits：`update:visible`、`confirm(tagIds)`、`tag-created`、`open-manage`（调用点 `KnowledgeBase.vue:2572-2576`） |
| `BatchTagDialog.vue` | `views/knowledge/components/BatchTagDialog.vue:2` | **批量**打标签对话框（`t-dialog` width 420px，`:footer="false"` 自绘页脚） | props：`visible`、`count`、`kbId`、`tagList`、`preSelectedTagIds`、`canManage`、`confirmLoading`；emits：`update:visible`、`confirm`、`tag-created`、`open-manage`（调用点 `KnowledgeBase.vue:2579-2584`） |
| `KbTagManageDrawer.vue` | `views/knowledge/components/KbTagManageDrawer.vue:2` | 标签管理**右侧抽屉**（列表增删改 + 搜索 + 加载更多 + 空态） | props：`visible`(v-model)、`kbId`、`isFaq`；emits：`changed`；基于 `SettingDrawer`，`width="480px"` / `min-width 420` / `max-width 640` / `resizable` / `hide-footer`（`:7-12`） |
| `SettingDrawer.vue` | `components/settings/SettingDrawer.vue:10` | 右侧抽屉**壳**（可拖拽改宽、自定义头部带图标徽标与副标题、body/footer 插槽） | props：`visible`、`title`、`description`、`icon`、`width`、`minWidth`、`maxWidth`、`resizable`、`storageKey`、`hideFooter`、`zIndex`；emits：`confirm`、`cancel`（`common.cancel`/`common.save` 默认页脚，`:55-60`） |
| `ShareKnowledgeBaseDialog.vue` | `components/ShareKnowledgeBaseDialog.vue` | 共享知识库给空间 | `v-model:visible`、`knowledge-base-id`、`knowledge-base-name`；事件 `shared`（`KnowledgeBaseList.vue:635-636`） |
| 共享详情**抽屉**（内联，非独立组件） | `KnowledgeBaseList.vue:639-704`（样式 `2291-2427`） | 共享知识库详情：`Teleport to="body"` + `Transition name="shared-detail-drawer"`，自绘右侧滑出面板（宽 360px） | 行项由 `knowledgeList.detail.*` 文案驱动（`zh-CN.ts:4793-4807`） |

### 1.5 空态 / 加载 / 进度

| 组件 | 文件:行 | 职责 | 关键 props / 事件 |
|---|---|---|---|
| `EmptyState.vue` | `components/EmptyState.vue:1`（props 24–33，样式 36–97） | 统一空态：圆形图标徽标 + 标题 + 描述 + 操作区 | props：`title`(必填)、`description`、`icon`(TDesign 图标名)、`image`(插图) 、`compact`；插槽：`icon`/`description`/默认(操作) |
| `empty-knowledge.vue` | `components/empty-knowledge.vue:5` | 详情页**知识库为空**的插图空态（`upload.svg` 162×162 + 两行格式提示） | 无 props；文案 `knowledgeBase.emptyKnowledgeDragDrop` / `pdfDocFormat` / `textMarkdownFormat`（`:8-10`） |
| `upload-mask.vue` | `components/upload-mask.vue:5` | 全局拖拽文件时的**全屏遮罩**内容（`upload-mask.svg` + "上传文件" + 两行格式提示） | 无 props；由 `views/platform/index.vue:7-9` 以 `v-show="ismask"` 控制 |
| `UploadTasksPanel.vue` | `components/upload-tasks/UploadTasksPanel.vue:226` | **上传/解析进度浮层**（右下角固定，可折叠；分段进度条 + 图例 + 每文件一行 + 全部取消/重试失败） | props：`visible`、`items`；内部用 `ProgressRing`（`:238`、`:108`） |
| `UploadTaskRow.vue` | `components/upload-tasks/UploadTaskRow.vue:90` | 浮层内单文件行：图标 + 文件名 + 阶段文案 + 状态图标/进度环 + 取消/重试按钮 | props：`item`；emits：`cancel`、`retry`、`open`（`:340-342`） |
| `ProgressRing.vue` | `components/upload-tasks/ProgressRing.vue:19` | 纯 SVG 环形进度（两圆 + `stroke-dashoffset`） | props：`value`(0..1)、`size`(默认 20)、`stroke`(默认 2.5) |
| `KBInfoPopover.vue` | `components/KBInfoPopover.vue:1`（脚本 167–371） | 详情页标题右侧"信息"圆按钮 → 知识库信息卡（基础/访问/存储绑定/能力/统计） | props：`kbInfo`、`supportedFileTypes` |
| `KnowledgeProcessingTimeline` | `components/knowledge-processing-timeline.vue`（109 KB） | 文档解析处理时间线（卡片悬停浮层内嵌 compact 版；二级抽屉里是完整 waterfall） | props：`knowledge-id`、`parse-status`、`compact`、`auto-poll`、`grace-poll`、`doc-title`、`show-close`；emits：`update:has-spans`、`update:summary`、`close`（`DocumentCardView.vue:632-637`、`doc-content.vue:1614-1634`） |
| `DocContent`（`doc-content.vue`） | `components/doc-content.vue:1573`（脚本 1–1572，样式 2145–3333） | **文档详情抽屉（含分块视图）**：元信息 + 自定义元数据编辑 + 摘要 + 内容（预览/合并/分块三视图）+ 分块内联编辑/历史/回滚 + 分页 + 二级处理时间线抽屉 | props：`visible`、`details`、`canEditKB`、`canDownloadKB`、`kbId`；emits：`closeDoc`、`getDoc`、`summaryStateChange`（调用点 `KnowledgeBase.vue:2552-2555`） |
| `useConfirmDelete()` | `components/settings/useConfirmDelete.ts:17` | 全局统一的删除确认（基于 `DialogPlugin.confirm`，danger 主题 + 红色确认键） | 参数：`title`、`body`、`confirmText`、`cancelText`、`onConfirm` |
| `useModalShell()` | `composables/useModalShell.ts:51` | 全屏设置弹窗的 Esc / 遮罩关闭 + 未保存二次确认 | 参数：`visible()`、`close()`、`snapshot?()`、`ignoreEscape?()` |
| `useMarqueeSelect()` | `hooks/useMarqueeSelect.ts`（`useMarqueeSelect` 导出） | 网格/列表**框选**（iOS Photos 语义：起点落在已选项 → 本次全程取消选中，否则追加） | 参数：`containerRef`、`itemSelector`、`selectedIds`、`getItemId`、`enabled`、`onSelectionStart`、`minDragDistance`(默认 6px) |
| `ListSpaceSidebar.vue` | `components/ListSpaceSidebar.vue:1`（脚本 153–293，样式 295–550） | 列表页**左侧空间侧栏**（折叠态 56px 图标条 / 展开态 208px 完整导航；可拖拽宽度、按 120px 阈值吸附） | props：`mode`、`modelValue`(v-model)、`collapsedKey`、`countAll`、`countMine`、`countByOrg`、`countFavorites`、`countRecents`、`showFavorites`、`showRecents`、`hideAll`、`countCreated`、`countJoined`；emits：`update:modelValue` |
| `ContextualGuide.vue` | `components/ContextualGuide.vue` | 分步新手引导浮层（`tour="kbList"` / `"kbDetail"`） | props：`tour`、`when`（`KnowledgeBaseList.vue:706`、`KnowledgeBase.vue:2569`） |

### 1.6 用到的 TDesign 组件（按功能归类，均为 `tdesign-vue-next` 具名组件）

| TDesign 组件 | 出现处（示例 `文件:行`） | 在本块的角色 |
|---|---|---|
| `t-button` | `KnowledgeBaseList.vue:12`、`KnowledgeBase.vue:2416`、`DocumentBatchBar.vue:44` | 所有动作按钮；`variant="text"` 用于无边框图标/文字按钮 |
| `t-icon` | `KnowledgeBaseList.vue:14`、`KnowledgeBase.vue:2244` | 全部图标（TDesign Icons 0.4.4，`package.json:39`） |
| `t-popup` | `KnowledgeBaseList.vue:172`、`DocumentCardView.vue:361`、`KnowledgeTagFilter.vue:56` | 卡片"更多"菜单、标签筛选浮层、知识库切换 |
| `t-tooltip` | `KnowledgeBaseList.vue:11`、`KnowledgeBase.vue:2294` | 悬停提示（`placement` 多为 `top`） |
| `t-skeleton` | `KnowledgeBaseList.vue:39-47`、`KnowledgeBase.vue:2459-2466`、`KbFolderTree.vue:32` | 骨架屏（`animation="gradient"`） |
| `t-loading` | `KnowledgeBase.vue:2474`(面包屑)、`:498`、`KbTagManageDrawer.vue:45` | 转圈加载 |
| `t-tag` | `DocumentListView.vue:334`、`DocumentCardView.vue:563`、`KbTagManageDrawer.vue` | 标签 chip、状态 chip（`variant="light-outline"`） |
| `t-checkbox` | `DocumentListView.vue:263`/`:309`、`DocumentCardView.vue:352`、`KnowledgeBaseEditorModal.vue:53` | 多选 |
| `t-input` | `KnowledgeBase.vue:2364`、`BatchTagDialog.vue:46` | 搜索/新建标签输入 |
| `t-textarea` | `KnowledgeBaseEditorModal.vue:108`/`:119`/`:137` | 长文本（`autosize`） |
| `t-select` | `KnowledgeBase.vue:2378`/`:2387`/`:2396`、`UploadConfirmDialog.vue:173` | 文件类型/解析状态/来源/标签多选 |
| `t-date-range-picker` | `KnowledgeBase.vue:2405` | 更新时间区间（`allow-input`、`disable-date`） |
| `t-input-number` | `UploadConfirmDialog.vue:242`/`:258`/`:302` | 分块参数（chunk size / overlap / token limit） |
| `t-switch` | `UploadConfirmDialog.vue:208`/`:331`/`:371`/`:445`/`:496`/`:525` | 各类开关 |
| `t-radio-group` + `t-radio-button` | `KnowledgeBaseEditorModal.vue:31-38`、`:87-101` | 类型/粒度单选（全局 outline 选中态被改成绿色实底，`theme.css:120-141`） |
| `t-radio` | `DocumentListView.vue:454`/`:462`、`DocumentCardView.vue:451`/`:462` | "移动模式"二选一 |
| `t-popconfirm` | `DocumentBatchBar.vue:65`/`:97`、`DocumentActionMenu.vue:75`/`:87`/`:117` | 行内二次确认（重建/删除/停止解析） |
| `t-dialog` | `BatchTagDialog.vue:2`、`TagEditDialog.vue:2`、`KbUploadSourceDropdown.vue:39` | 三个小对话框（URL 导入 500px / 单文档标签 400px / 批量标签 420px） |
| `t-drawer` | `doc-content.vue:1581`/`:1628`、`SettingDrawer.vue:10` | 文档详情抽屉、二级时间线抽屉、设置抽屉 |
| `t-form` / `t-form-item` | 仅在 `KnowledgeBaseList.vue:2431` 的样式覆盖里被引用（`.create-kb-dialog .t-form-item__label`）；KB 编辑器实际是**自绘 label + input**（`KnowledgeBaseEditorModal.vue:16`/`:30`/`:128`） | 表单排版 |
| `t-loading` / `t-empty` / `t-pagination` | `t-empty`：`KbTagManageDrawer.vue:47`；`t-pagination`：`doc-content.vue:2130` | 标签抽屉空态、分块分页 |
| `t-dropdown` | `KbUploadSourceDropdown.vue:21` | 上传来源菜单 |
| `t-tooltip` / `t-popup`（overlay 皮肤） | `tdesign-overrides.less:5-22`（`overlayClassName="wk-popover"`） | 统一悬浮面板外观 |

**明确没有用到**：`t-row` / `t-col`（栅格）、`t-table`、`t-list`、`t-transfer`、`t-tree`（目录树是自绘 `div` 列表，`KbFolderTree.vue:36-117`）。知识库列表/文档列表的分栏**全部用 CSS Grid 手写**，见第 2 节。

---

## 2. 布局骨架

### 2.1 一屏分区（列表页）

```
┌─ views/platform/index.vue（.main，flex 横排）────────────────────────────────────┐
│                                                                                  │
│ ┌─ menu.vue ────┐ ┌─ .platform-route-outlet（flex:1, min-width:0）──────────────┐ │
│ │ 全局左侧菜单    │ │                                                          │ │
│ │ 展开 260px     │ │  ┌─ KnowledgeBaseList.vue ───────────────────────────────┐ │ │
│ │ 折叠 60px      │ │  │ .kb-list-container（flex 横排）                       │ │ │
│ │ (menu.vue:1227│ │  │                                                     │ │ │
│ │  -1228/1251)  │ │  │ ┌ ListSpaceSidebar ┐ ┌ .kb-list-content ────────────┐ │ │ │
│ │               │ │  │ │ 56px 折叠        │ │ padding 20px 0 0 28px        │ │ │ │
│ │               │ │  │ │ 208px 展开       │ │  ┌ .header ───────────────┐  │ │ │ │
│ │               │ │  │ │ 可拖拽 56↔228    │ │  │ h2 24px/600            │  │ │ │ │
│ │               │ │  │ │ (…:296-307)      │ │  │ + 小圆形"新建"按钮      │  │ │ │ │
│ │               │ │  │ │                  │ │  │ p 14px 次要色（副标题） │  │ │ │ │
│ │               │ │  │ │ 全部/收藏/最近    │ │  │ mb 16px, pr 28px       │  │ │ │ │
│ │               │ │  │ │ /本空间/各空间    │ │  └────────────────────────┘  │ │ │ │
│ │               │ │  │ └──────────────────┘ │  ┌ .kb-list-main（纵向滚动）──┐ │ │ │
│ │               │ │  │                      │  │ 未初始化黄色 banner（条件） │ │ │ │
│ │               │ │  │                      │  │ ┌ .kb-card-wrap（Grid）──┐ │ │ │ │
│ │               │ │  │                      │  │ │ 分组标题（sticky）      │ │ │ │ │
│ │               │ │  │                      │  │ │ [卡片][卡片][卡片]      │ │ │ │ │
│ │               │ │  │                      │  │ │ [卡片][卡片][卡片]      │ │ │ │ │
│ │               │ │  │                      │  │ └───────────────────────┘ │ │ │ │
│ │               │ │  │                      │  │ 或 EmptyState（居中）      │ │ │ │
│ │               │ │  │                      │  └────────────────────────────┘ │ │ │
│ │               │ │  │                                                     │ │ │
│ │               │ │  │  Teleport→body: 共享详情抽屉（右侧 360px 滑出）        │ │ │
│ │               │ │  └─────────────────────────────────────────────────────┘ │ │
│ │               │ └──────────────────────────────────────────────────────────┘ │
│ └───────────────┘                                                              │
│  固定浮层（全站共存）：UploadTasksPanel 右下角 380px（upload-tasks/…:369-391）    │
│  全局拖拽遮罩：.upload-mask（fixed inset，z-index 999）（platform/index.vue:271-280）│
└──────────────────────────────────────────────────────────────────────────────────┘
```

- 容器：`.kb-list-container` 横向 flex、`flex:1`（`KnowledgeBaseList.vue:1563-1571`）；`.kb-list-content` 纵向 flex、`padding: 20px 0 0 28px`（`:1573-1579`）。
- 滚动：只有 `.kb-list-main` 纵向滚动（`:1611-1621`）——顶部**特意不留 padding**，好让分组标题 `position: sticky; top: 0` 贴到容器最顶（注释 `:1616-1617`）。
- 侧栏：`ListSpaceSidebar` 折叠 56px / 展开 208px，常量 `COLLAPSED_WIDTH = 56` / `EXPANDED_WIDTH = 208` / `SNAP_THRESHOLD = 120`（`ListSpaceSidebar.vue:160-162`）。

### 2.2 一屏分区（详情页 · 文档）

```
┌─ KnowledgeBase.vue .knowledge-layout ───────────────────────────────────────────┐
│ flex 纵向; margin: 0 16px 0 4px; gap: 20px; padding: 24px 32px 0; width:100%     │
│ (KnowledgeBase.vue:2625-2636)                                                   │
│ ┌ .document-header ────────────────────────────────────────────────────────────┐ │
│ │ 面包屑 h2 20px/600：知识库 › [KBSwitcherDropdown ▾] › 文档                    │ │
│ │   + .kb-title-actions：[ⓘ KBInfoPopover] [⚙ 30px 圆按钮]  (…:2291-2299)       │ │
│ │ 副标题 14px 次要色："支持点击或拖拽上传…"                                      │ │
│ │ 条件黄色提示：parser-hint / storage-engine-warning（可点跳设置）               │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
│ ┌ .knowledge-main（flex 横排）──────────────────────────────────────────────────┐ │
│ │ ┌ KbFolderTree ─┐ ┌ .tag-content ──────────────────────────────────────────┐ │ │
│ │ │ 268px          │ │ .doc-card-area（position: relative，容器查询上下文）    │ │ │
│ │ │ border-right   │ │  ┌ .doc-folder-path 面包屑（含"（含子目录）"提示）────┐  │ │ │
│ │ │ 1px            │ │  ┌ .doc-filter-bar（Grid 2 行）─────────────────────┐ │  │ │
│ │ │ 可折叠（收起→  │ │  │ [搜索 input 1fr]           [trailing: 批量管理｜   │ │  │ │
│ │ │  只剩 24px 按钮）│ │  │                            视图切换｜＋上传]    │ │  │ │
│ │ │ (…:241-258)    │ │  │ [filters: 标签｜类型｜状态｜来源｜时间区间]        │ │  │ │
│ │ └────────────────┘ │  └───────────────────────────────────────────────────┘ │ │ │
│ │                    │  ┌ .doc-scroll-container（唯一滚动区）─────────────────┐ │ │ │
│ │                    │  │ grid 视图：DocumentCardView（卡片网格）            │ │ │ │
│ │                    │  │ list 视图：DocumentListView（8 列 grid 表）        │ │ │ │
│ │                    │  │ 空：empty-knowledge 插图 / 文件夹空态文案           │ │ │ │
│ │                    │  │ 框选：.doc-marquee-box（绝对定位）                 │ │ │ │
│ │                    │  └───────────────────────────────────────────────────┘ │ │ │
│ │                    │  ┌ .doc-batch-bar-anchor（absolute, bottom:12px）─────┐ │ │ │
│ │                    │  │ DocumentBatchBar（max-width 920px 居中）           │ │ │ │
│ │                    │  └───────────────────────────────────────────────────┘ │ │ │
│ │                    └────────────────────────────────────────────────────────┘ │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
│  DocContent 主抽屉（默认 654px，可拖 480px 起，上限 min(1600, 95vw)）              │
│  └ 二级时间线抽屉（默认 820px）                                                    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

- `.knowledge-main` 无背景无边框（`KnowledgeBase.vue:2683-2689`），左侧目录树是唯一分隔（`KbFolderTree.vue:246-250`）。
- 详情页不再用独立 tab 条：Wiki 型知识库的「文档 / Wiki / 图谱」是**面包屑里的 tab 文字**（`KnowledgeBase.vue:2266-2287`），选中态 = 品牌绿 + 600（`:2652-2655`）。

### 2.3 栅格 / 断点 / 尺寸（列表用 Grid，不是 `t-row/t-col`）

| 位置 | 规则 | 出处 |
|---|---|---|
| 知识库列表卡片网格（基础） | `display:grid; gap:12px; grid-template-columns:1fr` | `components/css/resource-card.less:11-16`（`.resource-card-grid()`，由 `.kb-card-wrap` 消费：`KnowledgeBaseList.vue:1888-1890`） |
| ≥900px | `repeat(2, 1fr)` | `KnowledgeBaseList.vue:2225-2229` |
| ≥1250px | `repeat(3, 1fr)` | `:2231-2235` |
| ≥1600px | `repeat(4, 1fr)` | `:2237-2241` |
| ≥1900px | `repeat(5, 1fr)` | `:2243-2247` |
| ≥2200px | `repeat(6, 1fr)` | `:2249-2253` |
| 文档卡片网格 | `repeat(auto-fill, minmax(240px, 1fr))`，`gap:12px` | `KnowledgeBase.vue:3293-3305`；组件内同值 `DocumentCardView.vue:699-705` |
| 文档列表 8 列 | `44px / minmax(260px,2.6fr) / minmax(100px,.9fr) / minmax(96px,.8fr) / 96px / minmax(96px,.7fr) / 140px / 48px`（勾选/文件名/标签/来源/大小/状态/更新时间/操作） | `DocumentListView.vue:511-526` |
| 筛选条布局 | 默认 Grid：`1fr auto`，areas `search trailing` / `filters filters`，`gap:8px 12px` | `KnowledgeBase.vue:2789-2798` |
| 筛选条 → 单行 | 容器查询 `@container doc-card-area (min-width: 1240px)` 时切成一行 flex | `:2841-2851` |
| 筛选控件宽度 | `.doc-filter-field` 140px；`--wide` 280px | `:2853-2863`；`KnowledgeTagFilter.vue:167-170` 同 140px |
| 搜索框 | ≥1280px 时 `flex:1 1 220px; min-width:220px` | `:2866-2871` |
| KB 编辑器弹窗 | `max-width:1080px; height:780px; max-height:calc(100vh - 40px)`；左导航 `208px` | `SettingsModalShell.vue:141-143`、`:193` |
| 上传确认对话框 | `width:92vw; max-width:1160px; height:85vh; max-height:750px`；左文件栏 `220px`；中导航栏 `216px` | `UploadConfirmDialog.vue:1491-1494`、`:1533`、`:1813` |
| 标签管理抽屉 | `width 480px / min 420 / max 640`，可拖拽 | `KbTagManageDrawer.vue:7-11` |
| 文档详情主抽屉 | 默认 654px，最小 480px，上限 `min(1600, floor(innerWidth*0.95))` | `doc-content.vue:417-418`、`:427` |
| 二级时间线抽屉 | 默认 820px | `doc-content.vue:345` |
| 批量条 | `max-width:920px; margin:0 auto`；锚点 `position:absolute; left:0; right:0; bottom:12px` | `DocumentBatchBar.vue:113-121`；`KnowledgeBase.vue:3011-3019` |
| 上传浮层 | `position:fixed; right/bottom:24px; width:380px; max-height:calc(100vh - 80px)` | `upload-tasks/UploadTasksPanel.vue:369-390` |
| 目录树 | `width:268px; padding-right:12px; margin-right:12px; border-right:1px`；缩进变量 `--kb-folder-indent:10px` | `KbFolderTree.vue:241-258`、`:242` |
| 卡片高度 | 知识库卡 **136px**（`height:136px; min-height:136px`）；文档卡 **136px**；列表行 **min-height:60px**；表头 **40px** | `resource-card.less:23-24`；`DocumentCardView.vue:785`；`DocumentListView.vue:566`、`:540` |

---

## 3. 视觉语言

### 3.1 主题变量定义在哪 / 明暗怎么切

| 项 | 值 / 机制 | 出处 |
|---|---|---|
| 全局入口 | `main.ts` 依序引入 `tdesign-vue-next/dist/tdesign.css` → `@/assets/theme/theme.css` → `@/assets/theme/tdesign-overrides.less` → `@/assets/dropdown-menu.less` | `frontend/src/main.ts:7-15` |
| 浅色主题 | `:root:root, :root:root[theme-mode="light"]{ … }` —— **整块压在第 1 行**（单行 minified，含品牌/警告/错误/成功/灰阶/背景/文字/字体/圆角/阴影全部 Light token） | `theme.css:1` |
| 深色主题 | `:root:root[theme-mode="dark"]{ … }` | `theme.css:2-98` |
| 明暗切换机制 | `document.documentElement.setAttribute('theme-mode', effective)` —— 即**用 `theme-mode` 属性选择器切整套 CSS 变量**，不是加 class | `composables/useTheme.ts:67` |
| 三态 | `ThemeMode = 'light' \| 'dark' \| 'system'`；默认 `'light'`；`system` 时读 `prefers-color-scheme` 并监听其 change | `useTheme.ts:8`、`:12-16`、`:23-25`、`:88-93` |
| 持久化 | `savePreference('theme', mode)`（用户级偏好），登录/登出后 `reloadThemeFromStorage()` 重读 | `useTheme.ts:75`、`:97-101` |
| 桌面壳联动 | Wails 下同时设 `WindowSetDarkTheme/LightTheme` 与窗口底色 `#242424` / `#eeeeee` | `useTheme.ts:28-61` |
| 字体族 | `--app-font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif`；等宽 `--app-font-family-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, …` | `theme.css:1`（浅色块）；由 `--td-font-family: var(--app-font-family)` 顶掉 TDesign 默认（同行） |
| TDesign 意图覆盖层 | 只做一处：`.wk-popover .t-popup__content` 的 padding/圆角/描边/阴影/毛玻璃；深色下换背景与描边 | `assets/theme/tdesign-overrides.less:5-22` |

### 3.2 `--td-*` 覆盖了什么（**改了** vs **保持 TDesign 默认**）

**被改写**（浅色值在 `theme.css:1`，深色值在 `theme.css:2-98`）：

| Token | 浅色 | 深色 | 出处 |
|---|---|---|---|
| `--td-brand-color` | `var(--td-brand-color-4)` = **#07c05f** | `var(--td-brand-color-6)` = **#06b04d** | `theme.css:1`；深色 `:8`（值在 `:15`） |
| `--td-brand-color-1 … -10` | #e9f8ec, #09f479, #08dd6e, **#07c05f**, #06b04d, #049b38, #038626, #027218, #015e0d, #004b05 | #06b04d20, #015e0d, #027218, #038626, #049b38, **#06b04d**, #07c05f, #08dd6e, #09f479, #a6fccf | `theme.css:1`；深色 `:10-19` |
| `--td-brand-color-hover / active` | `-3` / `-5` | `-5` / `-7` | `theme.css:1`；深色 `:7`、`:9` |
| `--td-brand-color-disabled` | `#8ce0af` | `#1a6b3b` | `theme.css:1`；深色 `:6` |
| `--td-brand-color-focus` | `color-mix(in srgb, var(--td-brand-color) 20%, transparent)` | 28% | `theme.css:1`；深色 `:5` |
| `--td-warning-color` | `var(--td-warning-color-5)` = **#ed7b2f** | `#dc7633`（深色 `:25`） | `theme.css:1`；深色 `:20-29` |
| `--td-error-color` | `var(--td-error-color-6)` = **#e34d59** | `#c64751`（深色 `:34`） | `theme.css:1`；深色 `:29-38` |
| `--td-success-color` | `var(--td-success-color-5)` = **#00a870** | `#059465`（深色 `:42`） | `theme.css:1`；深色 `:38-47` |
| `--td-gray-color-1 … -14` | #f3f3f3, #eee, #e7e7e7, #dcdcdc, #c5c5c5, #a6a6a6, #8b8b8b, #777, #5e5e5e, #4b4b4b, #383838, #2c2c2c, #242424, #181818 | 同值（两套共用一套灰阶） | `theme.css:1`；深色 `:47-60` |
| `--td-bg-color-page` | `var(--td-gray-color-2)` = **#eee** | `--td-gray-color-14` = **#181818** | `theme.css:1`；深色 `:61` |
| `--td-bg-color-container` | **#fff** | `--td-gray-color-13` = **#242424** | `theme.css:1`；深色 `:64` |
| `--td-bg-color-container-hover / active / select` | `--td-gray-color-1`(#f3f3f3) / `-3`(#e7e7e7) / #fff | `-12`(#2c2c2c) / `-10`(#4b4b4b) / `-9`(#5e5e5e) | `theme.css:1`；深色 `:65-67` |
| `--td-bg-color-secondarycontainer` | `--td-gray-color-1` = **#f3f3f3** | `--td-gray-color-12` = **#2c2c2c** | `theme.css:1`；深色 `:68` |
| `--td-bg-color-sidebar` | **#f9f9f9** | **#181818** | `theme.css:1`；深色 `:62` |
| `--td-bg-color-settings-modal` | **#f9f9f9** | **#181818** | `theme.css:1`；深色 `:63` |
| `--td-component-stroke`（分隔线） | `--td-gray-color-3` = **#e7e7e7** | `--td-gray-color-11` = **#383838** | `theme.css:1`；深色 `:75` |
| `--td-component-border`（控件描边） | `--td-gray-color-4` = **#dcdcdc** | `--td-gray-color-9` = **#5e5e5e** | `theme.css:1`；深色 `:76` |
| 正文/次要/占位/禁用文字 | `--td-font-gray-1` rgba(0,0,0,.9) / `-2` .6 / `-3` .4 / `-4` .26 → `--td-text-color-primary/secondary/placeholder/disabled` | `--td-font-white-1` rgba(255,255,255,.9) / `-2` .55 / `-3` .35 / `-4` .22 | `theme.css:1`；深色 `:76-90` |
| 字号阶梯 `--td-font-size-*` | link 12/14/16；mark 12/14；body **12 / 14 / 16**；title **14 / 16 / 20**；headline 24/28/36；display 48/64 | 同左 | `theme.css:1`；深色 `:92` |
| 行高 `--td-line-height-common` | **8px**（所有 line-height = 字号 + 8px，如 body-medium = 14+8 = 22px） | 同左 | `theme.css:1`；深色 `:92` |
| 圆角 `--td-radius-*` | small **2px** / default **3px** / medium **6px** / large **9px** / extraLarge **12px** / round **999px** / circle **50%** | 同左 | `theme.css:1`；深色 `:94` |
| 阴影 `--td-shadow-1/2/3` | 三档，见下 3.5 | 同左 | `theme.css:1`；深色 `:96` |
| 深色滚动条 | thumb `#4b4b4b`、hover `#5e5e5e`、track transparent（均 `!important`） | — | `theme.css:100-109` |
| 深色下 `img` 图标反色 | `:root[theme-mode="dark"] .more-icon { filter: invert(1); opacity:.55 }`，hover 变 .9 | — | `theme.css:111-118` |
| 全局输入聚焦 | 保留 1px 品牌色描边、**去掉 TDesign 的外发光环**（`box-shadow:none`） | — | `theme.css:195-202` |
| 全局 radio-button 选中态 | 绿色实底 + 反白字（覆盖 TDesign 默认的浅色描边态） | — | `theme.css:120-141` |
| 自动填充背景 | 用 `-webkit-box-shadow: 0 0 0 1000px var(--td-bg-color-container) inset` 盖掉 Chrome 黄/蓝底 | — | `theme.css:182-193` |

**自建的应用级 token（不是 `--td-*`）** —— 这一块是"他们自己的 CSS 变量"，KB 界面几乎全在用：

| 组 | 变量与值 | 出处 |
|---|---|---|
| 品牌别名 | `--brand-main: var(--td-brand-color-4)`（深色 = `-6`） | `theme.css:1`；深色 `:3` |
| 强调色 | `--app-accent-purple: #7c4dff`（浅）/ `#9d7cff`（深）；用于"知识图谱"徽标 | `theme.css:205-210`；消费处 `KnowledgeBaseList.vue:2135` |
| 圆角 | `--app-radius-xs:4px` / `sm:6px` / `md:8px` / `lg:10px` / `xl:12px` / `pill:999px` | `theme.css:227-232` |
| 字号 | `--app-text-2xs:10px` / `xs:11px` / **`sm:12px`** / **`md:13px`** / **`base:14px`** / **`lg:15px`** / `xl:16px` / `2xl:18px` / `3xl:20px` / `4xl:24px` | `theme.css:235-244` |
| 间距（4px 网格） | `--app-space-1:4` / `2:8` / `3:12` / `4:16` / `5:20` / `6:24` / `8:32` / `10:40` | `theme.css:247-254` |
| 动效时长 | `--app-motion-instant:120ms` / `fast:150ms` / `base:200ms` / `slow:300ms` | `theme.css:257-260` |
| 层级 | `--z-sticky:10` / `--z-dropdown:1000` / `--z-modal:1100` / `--z-drawer:2500` / `--z-popover:3000` / `--z-toast:5000` | `theme.css:263-268` |
| 旋转动画 | `@keyframes wk-spin { to { transform: rotate(360deg) } }`，spinner/刷新统一 `animation: wk-spin 0.8s linear infinite` | `theme.css:212-217`；KB 卡片处理中用 1s/0.9s（`KnowledgeBaseList.vue:2109`、`DocumentListView.vue:839`） |

### 3.3 字号阶梯（本块实际用到的 + 出处）

| 语义 | 字号 | 行高 | 字重 | 颜色 | 出处 |
|---|---|---|---|---|---|
| 列表页 / 详情页主标题 `h2` | `--app-text-4xl` = **24px** | 32px | 600 | `--td-text-color-primary` | `KnowledgeBaseList.vue:1600-1607`；`KnowledgeBase.vue:3117-3124` |
| 详情页面包屑 `h2` | `--app-text-3xl` = **20px** | — | 600 | primary | `KnowledgeBase.vue:3057-3065` |
| 页副标题 | `--app-text-base` = **14px** | 20px | 400 | `--td-text-color-placeholder` | `KnowledgeBaseList.vue:1643-1650`；`KnowledgeBase.vue:3126-3133` |
| 抽屉/弹窗标题 | `--app-text-2xl` = **18px**（共享详情）/ `--app-text-xl` = **16px**（设置壳侧栏） | — | 600 | primary | `KnowledgeBaseList.vue:2323-2328`；`SettingsModalShell.vue:208-213` |
| 卡片标题 | `--app-text-lg` = **15px** | 22px | 600 + `letter-spacing:.01em` | primary | `resource-card.less:87-101` |
| 卡片描述 | `--app-text-sm` = **12px** | 17px，`-webkit-line-clamp:2` | 400 | secondary | `resource-card.less:172-182` |
| 分组标题（sticky） | `--app-text-md` = **13px** | 20px | 600 | secondary（hover→primary） | `KnowledgeBaseList.vue:1917-1921`、`:1926-1928` |
| 分组计数徽标 | `--app-text-xs` = **11px** | 16px | 500 | secondary，底 `--td-bg-color-secondarycontainer` | `KnowledgeBaseList.vue:1958-1967` |
| 列表表头 | `--app-text-sm` = **12px** | 40px 行高容器 | 500 | secondary | `DocumentListView.vue:540-544` |
| 列表行正文 | `--app-text-md` = **13px** | 行 min-height 60px | — | primary | `DocumentListView.vue:566-568` |
| 空态标题 | `--app-text-lg` = **15px** | 22px | 600 | primary | `EmptyState.vue:76-81` |
| 空态描述 | `--app-text-md` = **13px** | 20px，`max-width:360px` | — | secondary | `EmptyState.vue:83-89` |
| 空态图标 | `font-size:30px`（compact 22px），装在内径 **64px 圆**（compact 48px） | — | — | placeholder | `EmptyState.vue:51-74` |
| 抽屉 section 标题 | `--app-text-md` = **13px** | — | 600 | primary | `SettingDrawer.vue:425-433` |
| 标签 chip | `--app-text-xs` = **11px**（计数用 `--app-text-2xs` = 10px） | 24px 高 | — | secondary / 选中 brand | `KnowledgeTagFilter.vue:294-324` |
| 卡片底部小徽标 | `--app-text-xs` = **11px**，高 **22px**、`min-width:22px`、`padding:0 5px`、`border-radius:5px` | — | 500 | 随语义色 | `resource-card.less:207-231` |
| 空知识库插图文案 | `--app-text-xl` = **16px** | 26px | 600 | placeholder | `empty-knowledge.vue:22-29` |
| 上传遮罩大标题 | `--app-text-4xl` = **24px** | 26px | 600 | `--td-brand-color` | `upload-mask.vue:20-27` |

### 3.4 间距（内边距 / 卡片间距 / 表单行距）

| 位置 | 值 | 出处 |
|---|---|---|
| 列表页内容区 | `padding: 20px 0 0 28px`（容器）；滚动区 `padding: 0 28px 8px 0` | `KnowledgeBaseList.vue:1578`、`:1618` |
| 列表页 header | `margin-bottom:16px`、`padding-right:28px` | `:1585-1586` |
| 标题行内 gap | `title-row gap:8px`；`header-title gap:4px` | `:1594-1597`、`:1588-1591` |
| 详情页外层 | `padding: 24px 32px 0`，`gap:20px`，`margin: 0 16px 0 4px` | `KnowledgeBase.vue:2628-2634` |
| 筛选条 | `padding: 0 0 12px 0`，`gap: 8px 12px`，`__filters gap:12px`，`__trailing gap:8px` | `:2790-2798`、`:2806-2810`、`:2828-2833` |
| 卡片内边距（KB 卡） | `padding: 12px 14px` | `resource-card.less:25` |
| 卡片内边距（文档卡） | 内容区 `padding: 10px 14px 8px`；底部条 `height:32px; padding:0 14px` | `DocumentCardView.vue:826`、`:943-945` |
| 卡片内纵向间距 | `.card-header margin-bottom:6px`；`.card-content gap:6px; margin-bottom:6px`；`.card-bottom padding-top:6px` | `resource-card.less:68`、`:162-170`、`:189` |
| 卡片网格间距 | **12px**（滚动列表 `gap:12px`） | `resource-card.less:13`；`KnowledgeBase.vue:3298` |
| 卡片底部徽标间距 | `gap:4px`；`.bottom-left gap:8px`；`.bottom-right gap:8px` | `resource-card.less:199-203`；`KnowledgeBaseList.vue:2069-2087` |
| 列表行 | `padding: 0 16px`，单元格 `padding: 0 8px`（首/末列 0） | `DocumentListView.vue:525`、`:589-602` |
| 更多菜单项 | `padding: 8px 12px`，`gap:10px`，行高 20px | `DocumentActionMenu.vue:130-140` |
| 批量条 | 内层 `padding: 8px 12px`，`gap:12px`；左组 `gap:4px`；动作组 `gap:8px` | `DocumentBatchBar.vue:123-134`、`:136-171` |
| 上传确认对话框 | 左文件栏 `width:220px`；中导航 `216px`；分区 section `padding:12px 0 16px`；`gap:14px` | `UploadConfirmDialog.vue:1533`、`:1813`；`SettingDrawer.vue:386-391` |
| 设置壳侧栏 | `sidebar-header padding: 16px 14px 12px`；`settings-nav padding: 8px 8px 12px`；`nav-item padding: 6px 12px; margin-bottom:2px`；`settings-footer padding: 12px 40px; gap:16px` | `SettingsModalShell.vue:203`、`:217`、`:254-255`、`:354-359` |
| 共享详情抽屉 | header `padding:20px 24px`；body `padding:24px; gap:20px`；row `gap:6px`；footer `padding:16px 24px; gap:12px` | `KnowledgeBaseList.vue:2318`、`:2352-2355`、`:2358-2362`、`:2395-2399` |
| 标签筛选面板 | `width:320px`，`max-height:min(70vh,480px)`，`padding:12px 14px`；chip `gap:6px`、`height:24px`、`padding:0 8px` | `KnowledgeTagFilter.vue:242-306` |

### 3.5 圆角、阴影、边框

**圆角**

| 用途 | 值 | 出处 |
|---|---|---|
| 应用级阶梯 | xs 4 / sm 6 / md 8 / lg 10 / xl 12 / pill 999 px | `theme.css:227-232` |
| 知识库卡片 / 文档卡片 / 文件夹卡片 | `--app-radius-md` = **8px** | `resource-card.less:27`；`DocumentCardView.vue:786`、`:719` |
| 批量条 / 标签筛选面板 / 悬浮信息浮层 | `--app-radius-md` = **8px** | `DocumentBatchBar.vue:132`；`KnowledgeTagFilter.vue:157`；`DocumentCardView.vue:1129` |
| 知识库卡右上角装饰扇形 | `border-radius: 0 12px 0 100%`（60×60px 渐变块） | `KnowledgeBaseList.vue:1991-1999` |
| 文档列表容器 | **9px** | `DocumentListView.vue:504` |
| 列表表头 | `8px 8px 0 0`，吸顶时变 `0` | `DocumentListView.vue:547`、`:551-553` |
| 设置弹窗 / 上传确认弹窗 / 上传浮层 | `--app-radius-xl` = **12px** | `SettingsModalShell.vue:145`；`UploadConfirmDialog.vue:1496`；`upload-tasks/UploadTasksPanel.vue:382` |
| 悬浮面板（`.wk-popover`） | `--app-radius-xl` = 12px | `tdesign-overrides.less:7` |
| 小圆按钮 / chip 组 | `--app-radius-sm` = 6px | `KnowledgeBaseList.vue:1662`；`KnowledgeBase.vue:2894` |
| 圆形按钮（设置 / 关闭 / 空态图标 / 上传徽标） | `50%`（30px、32px、64px、36px） | `KnowledgeBase.vue:3207`；`SettingsModalShell.vue:170`；`EmptyState.vue:58`；`upload-tasks/UploadTasksPanel.vue:420` |
| 标签 chip（列表/卡片内） | `--app-radius-pill` = 999px，高 18px | `DocumentCardView.vue:1051`、`:1101` |
| 卡片底徽标 | **5px**（比 sm 更小，写死） | `resource-card.less:216` |
| section 标题前导竖条 | `3px × 14px`，`border-radius:2px`，品牌色 | `SettingDrawer.vue:438-443` |

**阴影（实际用了几档）**

| 档 | 值 | 出处 / 用途 |
|---|---|---|
| TDesign 三档（被保留） | `--td-shadow-1` / `--td-shadow-2` / `--td-shadow-3`（各 3 层叠加，见 `theme.css:1`）；深色同值 `theme.css:96` | `--td-shadow-3` 用于设置弹窗（`SettingsModalShell.vue:146`）；`--td-shadow-2` 用于上传浮层（`upload-tasks/UploadTasksPanel.vue:384`） |
| 卡片静置（KB 卡） | `0 1px 3px rgba(0,0,0,.04)` | `resource-card.less:29` |
| 卡片 hover（KB 卡） | `0 4px 12px color-mix(in srgb, var(--td-brand-color) 12%, transparent)` | `resource-card.less:36` |
| 卡片静置（文档卡 / 文件夹卡） | `0 1px 2px rgba(0,0,0,.06)` | `DocumentCardView.vue:789`、`:722` |
| 卡片 hover（文档卡） | `0 4px 14px rgba(0,0,0,.07)` | `DocumentCardView.vue:797` |
| 列表容器 / 表头 | `0 1px 3px rgba(0,0,0,.04)` / `0 2px 8px rgba(0,0,0,.04)`；吸顶后 `0 4px 10px rgba(0,0,0,.08)` | `DocumentListView.vue:507`、`:548`、`:553` |
| 悬浮面板（自绘） | `0 0 0 .5px rgba(0,0,0,.03), 0 2px 4px rgba(0,0,0,.04), 0 8px 24px rgba(0,0,0,.1)` | `tdesign-overrides.less:11-13`；`KnowledgeTagFilter.vue:160-163` 同值 |
| 批量条 | `0 6px 16px rgba(0,0,0,.08)` | `DocumentBatchBar.vue:133` |
| 卡片悬停信息浮层 | `0 4px 16px rgba(0,0,0,.12)` | `DocumentCardView.vue:1130` |
| 上传确认弹窗 | `0 8px 32px rgba(0,0,0,.12)` | `UploadConfirmDialog.vue:1498` |
| 共享详情抽屉 | `-4px 0 24px rgba(0,0,0,.12)` | `KnowledgeBaseList.vue:2308` |
| 列表视图切换选中块 | `0 1px 2px rgba(0,0,0,.06)` | `KnowledgeBase.vue:2917` |
| 卡片内陷高光（新建按钮） | `inset 0 1px 0 color-mix(in srgb, var(--td-bg-color-container) 72%, transparent)` | `KnowledgeBaseList.vue:1665` |

**边框**

| 用途 | 值 | 出处 |
|---|---|---|
| 卡片描边 | `1px solid var(--td-component-stroke)`（KB 卡）/ `--td-component-border`（文档卡、文件夹卡） | `resource-card.less:26`；`DocumentCardView.vue:784`、`:718` |
| 卡片底部与内容的分隔 | **0.5px** solid `--td-component-stroke` | `resource-card.less:190` |
| 列表行分隔 | `1px solid --td-component-stroke`（最后一行去掉） | `DocumentListView.vue:569-575` |
| 悬浮面板描边 | **0.5px** solid（`.wk-popover`、标签筛选面板） | `tdesign-overrides.less:9`；`KnowledgeTagFilter.vue:159` |
| 侧栏 / 抽屉分区竖线 | `1px solid --td-component-stroke` | `SettingsModalShell.vue:195`；`KbFolderTree.vue:250` |
| 目录树切换按钮（收起态） | `1px solid --td-component-border`，24×24px | `KnowledgeBase.vue:2735` |
| 暗色下 `.wk-popover` | 描边换 `rgba(255,255,255,.08)`，底 `rgba(36,36,36,.92)` | `tdesign-overrides.less:19-22` |

**背景层级（从外到内）**

1. 页面底：`--td-bg-color-page`（#eee / #181818）—— `theme.css:1`、深色 `:61`
2. 内容容器 / 卡片：`--td-bg-color-container`（#fff / #242424）—— `theme.css:1`、深色 `:64`
3. 次级容器（表头、筛选控件底、chip 底、批量条取消按钮）：`--td-bg-color-secondarycontainer`（#f3f3f3 / #2c2c2c）—— `theme.css:1`、深色 `:68`；用例 `DocumentListView.vue:545`、`KnowledgeBase.vue:2939`
4. 设置/抽屉侧栏：`--td-bg-color-settings-modal`（#f9f9f9 / #181818）—— `theme.css:1`、深色 `:63`
5. 遮罩：`rgba(0,0,0,.5)` + `backdrop-filter: blur(4px)`（设置弹窗、上传确认对话框）；共享详情抽屉用 `rgba(0,0,0,.4)`；全局拖拽遮罩是**浅色** `rgba(255,255,255,.8)` —— `SettingsModalShell.vue:126-131`；`UploadConfirmDialog.vue:1483-1484`；`KnowledgeBaseList.vue:2297`；`platform/index.vue:272`
6. 语义浅底（自绘）：徽标用 `color-mix(in srgb, var(--td-brand-color) 8%, transparent)`，hover 12%；来源标签用 6%；"未初始化"提示用 `--td-warning-color-light` —— `KnowledgeBaseList.vue:2093`、`:1748`、`:1863`

---

## 4. 状态与反馈

### 4.1 空态（文案原文 + 插画/按钮）

| 场景 | 文案（zh-CN 原文） | 图标 / 插画 | 动作 | 出处 |
|---|---|---|---|---|
| 列表页「全部」无知识库 | 标题 `暂无知识库`；描述 `点击左侧快捷操作"新建知识库"按钮创建第一个知识库` | 无插画，TDesign 图标 `folder-open` 装在 64px 圆里 | **有**按钮「新建知识库」（primary，`folder-add` 图标，仅 `contributor` 角色） | 文案 `zh-CN.ts:4840-4841`；组件 `KnowledgeBaseList.vue:595-602` |
| 「我创建的」无知识库 | 同「全部」 | 同上 | 同上（`KnowledgeBaseList.vue:614-621`） | — |
| 「收藏」空 | 标题 `暂无收藏`；描述 `在知识库卡片右上角点击星标即可收藏` | 图标 `star` | **无按钮**（注释明确说明："没有收藏 ≠ 没有知识库"，`KnowledgeBaseList.vue:604-605`） | `zh-CN.ts:4844-4845`；`KnowledgeBaseList.vue:606-607` |
| 「最近」空 | 标题 `暂无最近访问`；描述 `最近打开过的知识库会出现在这里` | 图标 `history` | 无按钮 | `zh-CN.ts:4846-4847`；`KnowledgeBaseList.vue:610-611` |
| 某空间下无共享知识库 | 标题 `暂无共享知识库`；描述 `您可以加入共享空间或请求他人共享知识库给您` | 图标 `folder-open` | 无按钮 | `zh-CN.ts:4842-4843`；`KnowledgeBaseList.vue:624-625` |
| 详情页知识库为空 | `知识为空，拖放上传` + 两行限制 `pdf、doc 格式文件，不超过10M` / `text、markdown格式文件，不超过200K` | **有插画** `@/assets/img/upload.svg`，162×162px | 无按钮（上传入口在右上工具栏） | `empty-knowledge.vue:7-10`（文案 `zh-CN.ts:6993-6995`）；消费 `KnowledgeBase.vue:2532` |
| 文件夹为空 | `这个文件夹里还没有文档` | 无（纯文字） | 无 | `zh-CN.ts:6747`；`KnowledgeBase.vue:2527-2531` |
| 筛选后无匹配 | `没有匹配的文档` | 无 | 无 | `zh-CN.ts:6748`；`KnowledgeBase.vue:2528-2530` |
| 标签筛选面板无结果 | `未找到匹配的标签` | 无（居中 11px 灰字） | 无 | `zh-CN.ts:6796`；`KnowledgeTagFilter.vue:98-100` |
| 标签管理抽屉无标签 | `未找到匹配的标签` | `t-empty` 默认插画 | 无（有顶部「+」新建按钮） | `KbTagManageDrawer.vue:46-48` |
| 批量打标签对话框"已选"为空 | `暂未选择` | 无 | 无 | `zh-CN.ts:6978`；`BatchTagDialog.vue:28` |
| 移动到知识库无目标 | `没有兼容的目标知识库（需要相同类型和 Embedding 模型）` | 无 | 无 | `zh-CN.ts:6925`；`DocumentListView.vue:428-430`、`DocumentCardView.vue:418-420` |
| 上传确认对话框无待上传项 | `请至少添加一个文件或 URL` | 无 | 无 | `zh-CN.ts:6698`；`UploadConfirmDialog.vue:121` |
| 移动端菜单切换下拉空 | `暂无数据`（`common.noData`） | 无 | 无 | `zh-CN.ts:5055`；`KBSwitcherDropdown.vue:32-34` |

### 4.2 加载中

| 形态 | 具体做法 | 出处 |
|---|---|---|
| 列表页骨架屏 | 加载中且列表为空 → 渲染 **6 张** 136px 骨架卡；每张用 `t-skeleton animation="gradient"` 三段：header 60%×20px、content 100%×14px + 80%×14px、bottom 两个 28×28 rect | `KnowledgeBaseList.vue:36-50` |
| 详情页文档骨架屏 | 加载中且列表+子目录都空 → 渲染 **8 张**；每张：标题 70%×18px、两行 100%/60%×14px、底部 80px×14px + 40px×18px rect | `KnowledgeBase.vue:2454-2469` |
| 目录树骨架 | 5 行 100%×16px | `KbFolderTree.vue:30-34` |
| 标签筛选浮层骨架 | 8 个 56×24 rect 的 chip 占位 | `KnowledgeTagFilter.vue:75-82` |
| 标签抽屉骨架 | 4 个 `100%×44px rect` 的 tile | `KbTagManageDrawer.vue:51-55` |
| 详情页面包屑加载 | 知识库名位置放 `t-skeleton` 120×20px | `KnowledgeBase.vue:2249`、`:2259` |
| 空间知识库切换加载 | `t-loading size="medium"` 居中，容器 `min-height:200px` | `KnowledgeBaseList.vue:497-499`；样式 `:1623-1630` |
| 弹窗初始化 | 设置壳内整块 `t-loading size="medium" :text="加载中..."`（`common.loading`）覆盖面板 | `SettingsModalShell.vue:7-9` |
| 移动/分页切换 | `t-loading size="small"` + `common.loading` 文案 | `doc-content.vue:1853-1856`、`:1865-1868` |
| 上传确认"标签加载" | `t-select :loading`；失败给 `标签加载失败，可稍后在文档列表中设置`，空给 `当前知识库暂无标签，可上传后在标签管理中创建` | `UploadConfirmDialog.vue:173-187`（文案 `zh-CN.ts:6696-6697`） |
| 无限滚动 | 无 `t-pagination`：`handleScroll` 监听滚动容器，触底 `scrollTop + clientHeight >= scrollHeight - 10` 时 `page++`；`pageSize = max(35, floor(viewportH/148)*5)` | `KnowledgeBase.vue:1857-1879`、`:759-764` |
| 分块分页（详情抽屉） | `t-pagination`，`page-size = KNOWLEDGE_CHUNK_PAGE_SIZE = 25`，仅当 `details.total > 25` 才显示 | `doc-content.vue:2130`、`:2128`；常量 `api/knowledge-base/index.ts:448` |
| 标签列表分页 | `TAG_PAGE_SIZE = 50`，滚到底"加载更多"（文案 `加载更多`＝`tenant.loadMore`） | `KnowledgeBase.vue:603`；`KnowledgeTagFilter.vue:101-106`；`KbTagManageDrawer.vue:198-202`、`:230` |

### 4.3 错误态 / 进行中 / 成功失败提示（Toast）

**进行中（进度与百分比）**

| 形态 | 显示内容 | 出处 |
|---|---|---|
| 上传/解析浮层标题 | `正在上传 {done}/{total}` / `正在解析 {done}/{total}` / `全部完成` / `{ok} 个完成，{bad} 个未成功` / `上传已取消` | `zh-CN.ts:2613-2617`；组件 `upload-tasks/UploadTasksPanel.vue:242` |
| 副标题 | `上传至「{name}」` 或 `上传至 {count} 个知识库`；剩余时间 `剩余约 {time}`（秒/分钟/小时） | `zh-CN.ts:2618-2625` |
| 分段进度条 | 4 段拼宽：`is-ready`（可检索）/ `is-active`（处理中）/ `is-failed`（失败）/ `is-duplicate`（已存在），宽度按 `summary.bar.*` 百分比；`role="progressbar"` + `aria-valuenow=overallPercent` | `upload-tasks/UploadTasksPanel.vue:283-301` |
| 图例 | `可检索 / 处理中 / 等待中 / 失败 / 已存在` + 计数 | `zh-CN.ts:2628-2634`；`:296-300` |
| 单文件环形进度 | 上传中显示 `ProgressRing`（`size=20, stroke=2.5`，`stroke-dashoffset` 由 `value` 驱动，`transition: stroke-dashoffset 300ms ease`） | `upload-tasks/UploadTaskRow.vue:108`；`ProgressRing.vue:34-43`、`:62-66` |
| 单文件阶段文案 | `等待上传` / `正在保存…` / `排队解析` / `解析中` / `可检索，后台优化中` / `已完成` / `上传失败` / `解析失败` / `知识库中已有相同文件` / `已取消` / `已删除` | `zh-CN.ts:2637-2647` |
| 阶段提示语 | 上传中：`上传完成前请不要关闭或刷新页面`；解析中：`文件已全部上传，解析在后台继续，可以放心离开此页面` | `zh-CN.ts:2626-2627` |
| 卡片上的解析中 | 图标 `loading` + `animation: wk-spin 1s linear infinite`（标签计数右侧）；文案 `解析中...` | `KnowledgeBaseList.vue:2108-2110`；`zh-CN.ts:6937` |
| 卡片上的"生成摘要中" | `生成摘要中...`（`--app-text-xs`，品牌色，左侧转圈图标，块高 52px） | `DocumentCardView.vue:529-535`；样式 `:829-848` |
| 列表行状态 chip | `已完成`(success) / `解析中`(primary+loading) / `优化中`(primary+loading) / `生成摘要中`(primary+loading) / `失败`(danger + `close-circle`) / `已取消`(warning + `close-circle`) / `草稿`(warning)；无状态显示 `--` | `DocumentListView.vue:136-174`；文案 `zh-CN.ts:6986-6991`、`:6938` |
| 卡片失败态 | `解析失败` + `chart-bar` 图标按钮（点击打开处理时间线） | `DocumentCardView.vue:504-524`；`zh-CN.ts:6936` |
| 卡片草稿态 | `t-tag theme="warning"` 文案 `草稿` + `暂存内容，未参与检索` | `DocumentCardView.vue:525-528`；`zh-CN.ts:6919-6920` |
| 上传位置面包屑 | `上传位置` + 当前路径 + caret；可点开目录选择器改到根目录（`改到根目录`） | `UploadConfirmDialog.vue:40-50`；`zh-CN.ts:6710-6712` |
| 上传确认导航"待配置"红点 | `.nav-status--warning/error/muted` 文案 `待配置`；`已开启` / `未开启` / `未设置`；含图/音频时提示 `含图片内容，请启用多模态并选择模型` / `含音频内容，请启用语音识别并选择模型` | `UploadConfirmDialog.vue:144-154`；`zh-CN.ts:6702-6708`、`:6686-6689` |

**错误态提示（MessagePlugin，文案原文）**

| 触发 | 级别 | 文案 | 出处 |
|---|---|---|---|
| 拖入的是文本/链接而非文件 | warning | `请拖拽文件而不是文本或链接` | `platform/index.vue:175`；`zh-CN.ts:6996` |
| 知识库未初始化 | warning | `该知识库尚未完成初始化配置，请先前往设置页面配置模型信息后再上传文件` | `platform/index.vue:100`/`:107`；`zh-CN.ts:6900` |
| 取知识库信息失败 | error | `获取知识库信息失败，无法上传文件` | `platform/index.vue:111`；`zh-CN.ts:6904` |
| 缺 KB ID | error | `缺少知识库ID` | `platform/index.vue:91`；`zh-CN.ts:6905` |
| 文件类型无解析引擎 | warning | `所选文件类型暂无可用解析引擎，已全部跳过` / `{count} 个文件因无可用解析引擎被跳过` | `KbUploadSourceDropdown.vue:156`/`:164`；`zh-CN.ts:7024-7025` |
| 视频被过滤 | warning | `已跳过 {count} 个视频文件（暂不支持视频上传）` | `KbUploadSourceDropdown.vue:161`；`zh-CN.ts:6800` |
| URL 为空 / 非法 | warning | `请输入URL` / `请输入有效的URL` | `KbUploadSourceDropdown.vue:192`/`:198`；`zh-CN.ts:6806-6807` |
| 未选存储引擎 | warning | `请先配置存储引擎后再上传内容` | `KnowledgeBase.vue:1586`；`zh-CN.ts:6902` |
| 类型不支持该操作 | warning | `当前知识库类型不支持该操作` | `KnowledgeBase.vue:1567`；`zh-CN.ts:7023` |
| 单文档重建失败 | error | `重建失败，请稍后再试` | `KnowledgeBase.vue:1853`；`zh-CN.ts:6913` |
| 批量重建全部失败 | error | `批量重建失败` | `KnowledgeBase.vue:587`/`:590`；`zh-CN.ts:6984` |
| 停止解析失败 | error | `停止失败，请稍后再试` | `KnowledgeBase.vue:2107`；`zh-CN.ts:6918` |
| 批量删除失败 | error | `批量删除失败` | `KnowledgeBase.vue:2015`/`:2048`；`zh-CN.ts:6972` |
| 批量打标签失败 | error | `批量打标签失败` | `KnowledgeBase.vue:2094`；`zh-CN.ts:6980` |
| 标签更新失败 | error | `操作失败`（`common.operationFailed`） | `KnowledgeBase.vue:1006` |
| 移动失败 | error | `移动失败` | `KnowledgeBase.vue:1508`/`:1535`；`zh-CN.ts:6933` |
| 目录重命名非法/失败 | warning | `不能把文件夹移动到它自己的子目录下` / `文件夹重命名失败` | `KnowledgeBase.vue:860`/`:867`；`zh-CN.ts:6757`、`:6756` |
| 批量下载失败 | error | `批量下载失败，请稍后重试` | `KnowledgeBase.vue:495`；`zh-CN.ts:6961` |
| 列表页置顶失败 | error | `操作失败` | `KnowledgeBaseList.vue:1315`/`:1329`；`zh-CN.ts:4828` |
| 列表页删除失败 | error | `删除失败` | `KnowledgeBaseList.vue:1442`/`:1445`；`zh-CN.ts:4810` |
| 列表页复制失败 | error | `创建知识库副本失败` | `KnowledgeBaseList.vue:1353`/`:1356`；`zh-CN.ts:4812` |

**成功提示（文案原文）**

| 触发 | 级别 | 文案 | 出处 |
|---|---|---|---|
| 单文档重建已提交 | success | `重建任务已提交` | `KnowledgeBase.vue:1848`；`zh-CN.ts:6912` |
| 批量重建 | success | `已提交 {count} 个重建任务` | `KnowledgeBase.vue:580`；`zh-CN.ts:6983` |
| 停止解析 | success | `已停止解析` | `KnowledgeBase.vue:2104`；`zh-CN.ts:6917` |
| 批量删除 | success | `成功删除 {count} 个文档` | `KnowledgeBase.vue:2035-2038`；`zh-CN.ts:6971` |
| 批量打标签 | success | `已为 {count} 个文档成功设置标签` | `KnowledgeBase.vue:2086`；`zh-CN.ts:6979` |
| 批量下载开始 | success | `已开始保存 ZIP，解压后即可按文件夹批量上传文件` | `KnowledgeBase.vue:492`；`zh-CN.ts:6960` |
| 移动到目录 | success | `已移动 {count} 个文档` | `KnowledgeBase.vue:846`；`zh-CN.ts:6769` |
| 目录重命名 | success | `文件夹已重命名` | `KnowledgeBase.vue:871`；`zh-CN.ts:6755` |
| 文档标签更新 | success | `标签已更新` | `KnowledgeBase.vue:1001`；`zh-CN.ts:6735` |
| URL 导入 | success | `已导入 URL` | `KnowledgeBase.vue:1647`；`zh-CN.ts:6808` |
| 移动完成 | success | `移动完成`；部分失败则 warning `移动完成：{success} 成功，{failed} 失败` | `KnowledgeBase.vue:1527`/`:1525`；`zh-CN.ts:6934-6935` |
| 列表页删除 / 复制 / 置顶 | success | `已删除` / `知识库副本已创建（不包含知识内容）` / `已置顶`、`已取消置顶` | `KnowledgeBaseList.vue:1439`、`:1347`、`:1309`、`:1323`；`zh-CN.ts:4809`、`:4811`、`:4826-4827` |

**进行中 / 不确定态提示（info/warning）**

| 触发 | 级别 | 文案 | 出处 |
|---|---|---|---|
| 文档正在解析中触发重建 | info | `当前文档正在解析中，请稍后重试` | `KnowledgeBase.vue:570`/`:1449`/`:1802`；`zh-CN.ts:6914` |
| 批量重建跳过解析中的 | warning | `已跳过 {count} 个正在解析中的文档` | `KnowledgeBase.vue:574`；`zh-CN.ts:6985` |
| 删除已提交但未完成 | info | `删除任务已提交，正在等待完成。` → 未完成 `删除尚未完成，请稍后刷新查看结果。` → 无法确认 `暂时无法确认删除结果，请稍后刷新查看文档状态。` | `KnowledgeBase.vue:2019`/`:2041`/`:2046`；`zh-CN.ts:6967-6970` |
| 删除任务失败 | error | `删除任务失败，请查看文档错误详情后重试。` | `KnowledgeBase.vue:2039`；`zh-CN.ts:6969` |
| 移动已提交 | info | `移动任务已提交` | `KnowledgeBase.vue:1494`；`zh-CN.ts:6932` |
| 批量下载超限/跳过/无文件 | warning | `所选文件合计超过 512 MiB，请减少选择后分批下载` / `已跳过 {count} 个没有原始文件的文档` / `所选文档没有可下载的原始文件` | `KnowledgeBase.vue:471`/`:475`/`:458`；`zh-CN.ts:6962-6964` |

### 4.4 确认删除的对话框文案（原文）

| 场景 | 标题 | 正文 | 确认键 / 取消键 | 出处 |
|---|---|---|---|---|
| **删除整个知识库**（`DialogPlugin.confirm`，danger 主题） | `删除确认` | `确认要删除知识库"{name}"？删除后不可恢复` | `删除` / `取消` | 文案 `zh-CN.ts:4834-4838`；调用 `KnowledgeBaseList.vue:1431-1449`；实现 `useConfirmDelete.ts:20-35`（标题默认 `确认删除`、确认键默认 `删除`，此处均被覆盖） |
| **删除单个文档**（`t-popconfirm`，`theme="warning"`，`placement="left"`） | 无标题 | `确认删除文档"{fileName}"，删除后将无法恢复` | `删除`（danger）/ `取消` | `DocumentActionMenu.vue:117-126`；`zh-CN.ts:6941-6942` |
| **批量删除文档**（`t-popconfirm`，`placement="top"`） | 无标题 | `确认删除选中的 {count} 个文档？删除后将无法恢复。` | `删除`（danger）/ `取消` | `DocumentBatchBar.vue:97-105`；`zh-CN.ts:6966` |
| **批量重建文档**（`t-popconfirm`） | 无标题 | `确认重建选中的 {count} 个文档？现有内容将被清除并重新解析。` | `确认并重新解析`（warning）/ `取消` | `DocumentBatchBar.vue:65-73`；`zh-CN.ts:6981-6982` |
| **单文档重建**（`t-popconfirm`，`placement="left"`） | 无标题 | `确认重建文档"{fileName}"？该操作会清理现有分块并重新解析。` | `确认` / `取消` | `DocumentActionMenu.vue:75-84`；`zh-CN.ts:6911` |
| **停止解析**（`t-popconfirm`，danger confirm） | 无标题 | `确认停止解析"{title}"？已写入的分块会保留，可稍后通过"重建"重新触发；优化阶段（摘要 / 问答 / 知识图谱）的待执行任务会被立即丢弃。` | `停止解析`（danger）/ `取消` | `DocumentActionMenu.vue:87-96`；`zh-CN.ts:6916` |
| **删除标签** | 无标题 | `确定删除标签"{name}"？该标签下的所有文档将被一并删除` | `删除`（danger）/ `取消` | `KbTagManageDrawer.vue:173-179`（`getDeleteConfirmContent`）；`zh-CN.ts:6792` |
| **取消知识库共享** | 无标题 | `确定要取消对「{name}」的共享吗？` | — | `zh-CN.ts:4243` |
| **关闭未保存的知识库设置** | `有未保存的更改` | `关闭后当前修改将丢失，确定要关闭吗？` | `放弃更改`（danger）/ `继续编辑` | `useModalShell.ts:72-87`；`zh-CN.ts:5038-5043` |
| **上传中关闭进度浮层** | 无标题 | `关闭后将取消剩余 {count} 个文件的上传` | `取消上传`（danger）/ `继续上传` | `upload-tasks/UploadTasksPanel.vue:256-269`；`zh-CN.ts:2656-2658` |
| **更改存储引擎** | 无标题 | `知识库中已有文件，更改存储引擎后旧文件可能无法正常访问。是否确认更改？` | — | `zh-CN.ts:4237` |
| **回滚分块版本** | 无标题 | `确定回滚到 v{revision} 吗？回滚后会生成一个新版本。` | — | `zh-CN.ts:6887` |
| **删除分块的辅助召回问题** | 无标题 | `确定要删除这个问题吗？删除后将同时移除对应的向量索引。` | — | `zh-CN.ts:6854` |

---

## 5. 交互细节清单

### 5.1 hover / 选中 / 拖拽经过的视觉变化

| 交互 | 视觉变化（精确值） | 出处 |
|---|---|---|
| 知识库卡片 hover | 描边 → `--td-brand-color`；阴影 → `0 4px 12px color-mix(brand 12%)`；背景渐变从 brand 4% 提到 8%（`background: linear-gradient(135deg, container 0%, color-mix(brand 8%) 100%)`） | `resource-card.less:34-37`；`KnowledgeBaseList.vue:1985-1988` |
| 文档卡片 hover | 描边 → `color-mix(in srgb, var(--td-component-stroke) 55%, var(--td-brand-color))`（**不是纯品牌色**，比知识库卡轻）；阴影 → `0 4px 14px rgba(0,0,0,.07)` | `DocumentCardView.vue:795-798`；`KnowledgeBase.vue:3393-3396` |
| 文件夹卡片 hover | 同文档卡；`:focus-visible` 额外加 `0 0 0 2px color-mix(brand 30%)` 焦点环 | `DocumentCardView.vue:726-735` |
| 卡片"更多"按钮出现 | 默认 `opacity:0`；卡片 hover 时 `opacity:.6`；自身 hover / 菜单打开（`.active-more`）时 `opacity:1` + 底 `--td-bg-color-container-hover`；**触屏**（`@media (hover:none)`）常驻 `.6` | `resource-card.less:114-160` |
| 卡片收藏星标 | 绝对定位右上角 24×24px，默认 `opacity:0`；卡片 hover 或 `.is-favorited` 时 `opacity:1`；自身 hover 底变 `--td-bg-color-secondarycontainer`、色变 `--td-warning-color`；已收藏时色 = `--td-warning-color` | `KnowledgeBaseList.vue:2030-2064` |
| 列表行 hover / 菜单打开 | 背景 → `--td-bg-color-secondarycontainer`（**已选中行不加 hover 背景**，`:hover:not(.selected)`） | `DocumentListView.vue:577-580` |
| 列表行"更多"按钮出现 | 默认透明；行 hover / 菜单打开 / 行已选中时 `opacity:1`（**与卡片不同：选中行常驻显示**） | `DocumentListView.vue:582-586`、`:844-857` |
| 侧栏项 hover / 选中 | hover 底 `--td-bg-color-container-hover`、字 primary；active 底 `--td-bg-color-secondarycontainer`、字 `--td-brand-color` | `SettingsModalShell.vue:263-272`；`ListSpaceSidebar.vue:379-392` |
| 分组标题（sticky）hover | 字色 secondary → primary；右侧折叠 chevron `opacity .7 → 1` | `KnowledgeBaseList.vue:1926-1928`、`:1943-1947`、`:1969-1971` |
| 菜单项 hover / 按下 | hover 底 `--td-bg-color-container-hover`；`:active` 底 `--td-bg-color-container-active` + `transform: scale(.98)`；图标色 secondary → primary | `DocumentActionMenu.vue:142-159` |
| 详情页"设置"圆按钮 hover | 底 → `--td-success-color-light`，色 → `--td-brand-color` | `KnowledgeBase.vue:3217-3221` |
| 面包屑链接 hover | 色 → `--td-success-color`（**注意：不是 brand**），底 → `--td-bg-color-container`；`.dropdown` 的 chevron 下移 1px | `KnowledgeBase.vue:3081-3103` |
| 视图切换按钮 | 容器底 `--td-bg-color-secondarycontainer`、`padding:2px`、圆角 6px；按钮 28×24px；active = 白底 + 品牌色字 + `0 1px 2px rgba(0,0,0,.06)` | `KnowledgeBase.vue:2888-2919` |
| 标签筛选 chip hover/选中 | chip 24px 高、11px 字、1px 边、圆角 4px；`.active` 边框 `color-mix(brand 35%, stroke)`、字 brand、底 `color-mix(brand 6%)` | `KnowledgeTagFilter.vue:294-312` |
| 标签 chip（列表/卡片内） | `t-tag size="small" variant="light-outline"`；卡片内自绘为 18px 高、pill 圆角；hover 底 `--td-bg-color-secondarycontainer` | `DocumentListView.vue:334-337`；`DocumentCardView.vue:1048-1078` |
| 卡片"保存中"旋转图标 | `animation: wk-spin 1s linear infinite` | `KnowledgeBaseList.vue:2108-2110` |
| 卡片高亮闪烁（新建/跳转定位） | `@keyframes highlightFlash 0.6s ease-in-out 3`：边框品牌色，`box-shadow: 0 0 0 8px` 扩散，`transform: scale(1.02)` | `KnowledgeBaseList.vue:2198-2222` |
| 内容区进入动画 | `@keyframes contentFadeIn 0.32s ease-out`：`opacity 0→1` + `translateY(6px)→0` | `resource-card.less:15`；`KnowledgeBase.vue:3281-3304`；`DocumentListView.vue:486-508` |
| 抽屉 section 进入动画 | `setting-drawer-section-in 0.32s`：`translateY(6px)` → 0；第 1/2/3 个 section 分别延迟 0.04/0.08/0.12s | `SettingDrawer.vue:392`、`:413-423` |

### 5.2 勾选框出现在哪里

| 视图 | 勾选框位置与显隐规则 | 出处 |
|---|---|---|
| 卡片网格 | **在卡片内容区的第一行行首**（`.card-content-nav` 内），且**仅当 `batchMode === true`** 才渲染 → 默认不渲染，避免标题因 hover 抖动（注释明说，`:1932-1935`）。盒子 22×29px，`margin-right:8px` | `DocumentCardView.vue:351-359`；`:800-818` |
| 卡片网格 · batchMode 下点击卡片 | `@click="onCardClick(item)"` —— 批量模式下点击卡片 = 切换勾选，不打开详情 | `DocumentCardView.vue:345`；消费 `KnowledgeBase.vue:2491` |
| 列表视图 | **每行行首的 `.cell-check`**（44px 列）常驻渲染；`@click.stop` 阻止冒泡以免触发行打开 | `DocumentListView.vue:308-311`；列宽 `:515` |
| 列表视图 · 表头 | 表头第一格放"全选"勾选框，`size="small"`，`:indeterminate="someSelected"`，`:disabled="!items.length"`，`title=全选` | `DocumentListView.vue:262-265` |
| 勾选框的渲染权限 | 卡片版与列表版都要求 `(canEdit \|\| canDownload)`，否则整个勾选列不渲染 | `DocumentListView.vue:263`、`:309`；`DocumentCardView.vue:351` |
| 进入批量模式的入口 | 工具栏按钮「批量管理 / 取消选择」（`menu.batchManage` / `knowledgeBase.clearSelection`），仅当 `(canDownloadKnowledge \|\| canMutateKnowledge) && cardList.length` 才显示 | `KnowledgeBase.vue:2416-2421` |
| grid 视图自动补开批量模式 | 从 list 切到 grid 时若已有勾选，自动 `batchMode = true`（否则勾选态不可见） | `KnowledgeBase.vue:1947-1951` |
| Shift 连选 | 行/卡的 checkbox change 事件带 `ctx.e.shiftKey`，从 `lastSelectedIndex` 连选到当前项 | `DocumentListView.vue:193-196`；`KnowledgeBase.vue:1896-1912` |
| 框选（marquee） | 在 `.doc-scroll-container` 上 `@mousedown`；移动 ≥6px 才显示选择框；框**绝对定位**、1px 品牌色边、底 `color-mix(brand 12%)`；起始点落在已选项 → 本次全程**取消选中**（`.is-subtract`，用 `--td-error-color-6` 边 + 12% 底）；落在未选中/空白 → 全程**追加**（`.is-add`，14% 底）；框选期间容器 `cursor: crosshair`、`user-select:none`；结束后 150ms 内抑制 click | `KnowledgeBase.vue:2450`、`:2451-2453`；样式 `:2986-3008`；逻辑 `hooks/useMarqueeSelect.ts`（`minDragDistance = 6`、`suppressClickUntil = Date.now()+150`、忽略 `button/a/input/textarea/select/label/.t-checkbox/.more-wrap/.card-menu/.card-tag-selector/.row-more-btn/.doc-list-header`） |

### 5.3 批量操作条悬浮在哪

- 位置：**悬浮在滚动区底部**，`position: absolute; left:0; right:0; bottom:12px; z-index:6`，水平居中，锚点是 `.doc-batch-bar-anchor`（在 `.doc-card-area` 内，`.doc-card-area` 是定位上下文）—— `KnowledgeBase.vue:3011-3019`、`:2714`（注释 "作为批量工具栏悬浮的定位上下文"）。
- **跟随滚动吗？** 不跟随：它是 `absolute` + 父容器固定，所以视觉上**一直贴在列表底部**，不随内容滚动。（`position:absolute` 而非 `sticky`/`fixed`，`:3011-3015`）
- 指针穿透：锚点 `pointer-events: none`，只有直接子元素 `pointer-events: auto`，避免挡住卡片点击 —— `:3020-3024`。
- 条体本身：`max-width:920px; margin:0 auto`；内层白底 + 1px 描边 + 8px 圆角 + `0 6px 16px rgba(0,0,0,.08)`；出现/消失是 `batch-bar-fade` transition（`opacity` + `translateY(6px)`，200ms）—— `DocumentBatchBar.vue:113-134`、`:177-186`。
- 显隐条件：`v-show="batchMode || selectedIds.size > 0"`，同时组件内 `v-if="visible || count > 0"` —— `KnowledgeBase.vue:2536`；`DocumentBatchBar.vue:39`。
- 内容：左侧 `已选 {count} 项` + 「全选已加载」+「取消选择」（text 按钮）；右侧动作组按权限出现：批量下载（primary，`:disabled` 当 `count===0 || count>200`）、批量重建（outline）、批量打标签（outline）、移动到目录（outline + popup）、批量删除（danger outline） —— `DocumentBatchBar.vue:41-106`。
- 全局的上传进度浮层是**另一个**浮层，固定在右下角（`right/bottom: 24px`），与批量条无关 —— `upload-tasks/UploadTasksPanel.vue:369-372`。

### 5.4 键盘可达性与快捷键

| 项 | 实现 | 出处 |
|---|---|---|
| 列表分组标题可折叠 | `role="button" tabindex="0"`，绑定 `@keydown.enter.prevent` 与 `@keydown.space.prevent` | `KnowledgeBaseList.vue:60-63`（置顶组）、`:85-87`（我创建的）等共 6 处 |
| 分组标题焦点环 | `:focus-visible { box-shadow: 0 0 0 2px var(--td-brand-color-focus) }` | `KnowledgeBaseList.vue:1930-1932` |
| 目录树行 | `role="button" tabindex="0"`，`@keydown.enter` 触发 `select` | `KbFolderTree.vue:48-51` |
| 文件夹卡片 | `role="button" tabindex="0"`，`@keydown.enter` 打开 | `DocumentCardView.vue:325-328` |
| 卡片上的"解析中/失败"文字可点开时间线 | `role="button" tabindex="0"` + `@keydown.enter.stop` + `@keydown.space.prevent.stop` | `DocumentCardView.vue:487-492`、`:508-513` |
| 搜索框回车 | `t-input @enter="loadKnowledgeFiles(kbId)"` —— **回车即搜索** | `KnowledgeBase.vue:2366` |
| URL 导入对话框 | `t-input autofocus clearable @enter="handleUrlDialogConfirm"` —— 打开即聚焦，回车即确认 | `KbUploadSourceDropdown.vue:50-56` |
| 目录重命名 | 内联 `input`：`@keydown.enter="commitRename"`、`@keydown.esc="cancelRename"`、`@blur="commitRename"` | `KbFolderTree.vue:71-81` |
| 新建子目录 | `input`：`@keydown.enter.stop="commitNewFolder"`、`@keydown.esc.stop="cancelCreating"` | `FolderPickerMenu.vue:44-51` |
| 新建标签 / 编辑标签 | `t-input @enter="submitCreateTag"` / `@enter="submitEditTag"`，另有 `@keydown` 处理 Esc 取消（`onEditKeydown`） | `KbTagManageDrawer.vue:63-72`、`:111-120` |
| 批量打标签内新建 | `t-input @enter="handleAddNewTag"` | `BatchTagDialog.vue:67-68` |
| 设置类弹窗 ESC 关闭 | `window.addEventListener('keydown')`：`Escape` → 若**有 TDesign 弹窗/抽屉/弹层开着则让它们先关**（`hasOpenTDesignOverlay()` 查 `.t-dialog__ctx` / `.t-drawer--open` / `.t-popup`），否则 `requestClose()`；有未保存改动则弹二次确认 | `useModalShell.ts:38-49`、`:90-98`、`:65-88` |
| 小对话框 ESC | 未自实现，走 TDesign `t-dialog` 默认（`BatchTagDialog` / `TagEditDialog` 还被设为 `:close-on-overlay-click="false"`）—— **取自 TDesign 默认** | `BatchTagDialog.vue:2-3` |
| 上传确认对话框 ESC | **未发现键盘处理**；关闭只有右上 32×32px 关闭按钮与「取消」按钮 | `UploadConfirmDialog.vue:6-10`、`:556-559` |
| 全局命令面板 | `⌘K` / `Ctrl+K`（组件说明 "全局命令面板 (⌘K)"），可经 `?cmdk=` 唤起 | `platform/index.vue:12-13`、`:222-230` |
| 桌面端 `Ctrl/Cmd+R` | 仅在 Wails 桌面壳拦截并做前端软刷新 | `platform/index.vue:57-70` |
| 图像不可拖拽 | 全局 `img { -webkit-user-drag:none; … user-drag:none }` | `platform/index.vue:282-288` |
| **未发现的快捷键** | 知识库/文档列表**没有** Ctrl+A 全选、Delete 删除、方向键移动焦点等自定义快捷键；批量操作**全部靠鼠标** | —（`grep keydown/ctrlKey/metaKey` 在 `KnowledgeBase.vue` 只命中 1 处：`:2366` 的 `@enter`） |

### 5.5 其它交互细节

| 项 | 行为 | 出处 |
|---|---|---|
| 全局拖拽上传 | `document` 捕获阶段监听 `dragenter/dragover/dragleave/drop`；用**计数器** `dragCounter` 解决子元素反复 dragleave；只有 `dataTransfer.types` 含 `Files` 才算文件拖拽（排除 Wiki 内部元素拖拽）；`effectAllowed='all'`、`dropEffect='copy'` | `platform/index.vue:73`、`:117-166` |
| 拖拽遮罩出现在哪些路由 | 仅 chat 三条路由 或 知识库详情页且有 kbId；设置弹窗打开时由设置自己接管 | `platform/index.vue:127-141` |
| 拖拽落地 | 收集文件（含目录递归）→ 知识库路由先校验初始化（缺 summary_model_id 或需要的 embedding_model_id → warning 拦下）→ 派发 `weknora:knowledge-file-drop`；知识库页监听后走**同一个上传确认流程**（不会绕过标签/解析设置） | `platform/index.vue:168-195`；`KnowledgeBase.vue:1208-1216` |
| 卡片 hover 信息浮层 | 延迟 **300ms** 弹出，`Teleport to="body"`；位置按 12px 偏移 + 估算 360×300px，依次尝试右侧→左侧→下方→上方，并夹紧到视口内 10px；卡片离开立即销毁；列表变化时也销毁（防止浮层飘到视口左上角） | `DocumentCardView.vue:182-186`、`:254-287`、`:198-252` |
| 卡片"更多"菜单 | `t-popup` `trigger="click"` + `destroy-on-close`；card 上的 `item.isMore` 用 `v-model` 双向绑定 | `DocumentCardView.vue:361-369`；`KnowledgeBaseList.vue:405-410` |
| 移动子流程（卡片/列表共用） | 同一 popup 内三态切换：`normal`（动作清单）→ `targets`（目标知识库列表，含 loading/空态）→ `confirm`（复用向量 / 重新解析 二选一 radio + 取消/确认）；选目录时同一 popup 换成 `FolderPickerMenu` | `DocumentListView.vue:390-477`；`DocumentCardView.vue:380-478` |
| 表头吸顶 | `IntersectionObserver` 观察 0 高度哨兵 `.doc-list-sticky-sentinel`；哨兵离开视口即 `headerStuck=true`，表头圆角 8px→0、阴影加深 | `DocumentListView.vue:211-228`、`:260`、`:536-554` |
| 列表列头 | 8 个 `role="columnheader"`；行 `role="row"`；操作列头在无权限时不渲染 | `DocumentListView.vue:261-273` |
| 详情页目录路径面包屑 | 过滤时会静默把范围扩到子目录，因此显式加 `（含子目录）` 提示（`searchingSubtree`） | `KnowledgeBase.vue:2358-2361`；`zh-CN.ts:6746` |
| 详情页 Wails 拖拽区 | header 上标 `--wails-draggable: drag`，按钮标 `no-drag`（桌面壳可拖窗） | `KnowledgeBaseList.vue:7-13` |
| 侧栏宽度拖拽 | 右边缘 12px 热区 `mousedown` → 拖到 ≥120px 吸附展开、否则吸附折叠；结果写 `localStorage`（key 形如 `sidebar-collapsed-list-expanded`）；拖动时 `body.cursor='col-resize'`、`user-select:none` | `ListSpaceSidebar.vue:198-235`、`:220`、`:232` |
| 抽屉宽度拖拽 | 文档抽屉与二级时间线抽屉都有独立 resize handle（`role="separator"` + `aria-orientation="vertical"`），范围 480–`min(1600, 95vw)` | `doc-content.vue:1576-1579`、`:1621-1626`、`:417-431` |
| 上传浮层折叠 | 标题栏 chevron 切换 collapsed；展开时显示图例与逐文件行 | `upload-tasks/UploadTasksPanel.vue:246-255`、`:296-345` |
| 触屏兜底 | "更多"按钮在 `@media (hover: none)` 下常驻 60% 不透明 | `resource-card.less:154-160` |

---

## 6. 我没查到 / 取自 TDesign 默认 / 不确定

### 6.1 无法核对 TDesign 默认值的（**重要限制**）

- **`frontend/node_modules` 不存在**（实测 `Test-Path …\node_modules\tdesign-vue-next` = `False`），因此**本文无法从 TDesign 源码核对任何"默认值"**。凡本界面未覆盖的尺寸/颜色，我只能标注"取自 TDesign 默认（未核）"，不能给出具体 px/色值。例如：
  - `KnowledgeTagFilter.vue:202`、`:217` 用了 `var(--td-comp-margin-s)` —— **未经覆盖，取值未核**（TDesign 文档口径为 8px，但本文不采信未核对数值）。
  - `t-tag` 的 `size="small"` / `variant="light-outline"`、`t-button` 的 `size="small"`、`t-checkbox` 的 `size="small"`、`t-skeleton` 的 `animation="gradient"`、`t-loading` 的 `size="medium"` —— 全是 TDesign 内建尺寸，**未做样式覆盖**，我未核对其具体 px。
  - `t-dialog` 的默认 `width`、`t-popover` 的默认 `placement`/`show-arrow`、`t-popup` 箭头、`t-tooltip` 主题 —— 未覆盖。
  - TDesign 组件 `MessagePlugin` 的 toast 位置/停留时长/图标 —— 未覆盖，未核。

### 6.2 有类名但**没有对应样式**（疑似死类名）

- **`.knowledge-card.is-selected`** —— `DocumentCardView.vue:341` 绑定了 `'is-selected': selectedIds.has(item.id)`，但**在该组件的 scoped 样式里找不到 `.is-selected` 规则**（`grep` 全仓只命中 `BatchTagDialog.vue:372`、`TagEditDialog.vue:379`、`doc-content.vue:2883`、`dropdown-menu.less:559` 等**别的组件**的同名类）。⇒ 卡片"已选中"很可能**只有勾选框状态、没有卡片级高亮**。这是我在静态阅读下的结论，**未在浏览器中实测**。
- **`.knowledge-card.batch-mode`** —— 同样在 `DocumentCardView.vue:341` 绑定，样式里**找不到 `.batch-mode` 规则**（`grep` 仅命中绑定处本身）。⇒ 批量模式疑似没有卡片级视觉差异。
- 两者的替代"选中"视觉只在**列表视图**存在，但**列表行本身也没有选中底色**：`DocumentListView.vue:306` 绑定了 `:class="{ selected: selectedIds.has(item.id), … }"`，而全文件对 `.selected` 只出现在三处 —— `:577` `&:hover:not(.selected)`、`:578` `&.menu-open:not(.selected)`（**用 `:not()` 排除**选中行不加 hover 底色）、`:584` `&.selected .row-more-btn { opacity: 1 }`（**只让"更多"按钮常驻**）。**没有 `.selected { background: … }` 这条规则**。⇒ 列表视图的"已选中"**唯一视觉线索是行首勾选框 + 常驻的"更多"按钮**（`grep "selected"` 全命中清单见上）。这是静态阅读结论，**未在浏览器中实测**。

### 6.3 未查到 / 未做的

- **没有找到 `01-*.md`**：`docs/research/weknora-kb-ui/` 下只有一个空目录 `_parts/`，`grep "weknora-kb-ui|02-components-and-visual-language"` 在 `docs/` 全树**零命中**（`docs/research/weknora-assessment.md` 是另一份文件，未被引用为本文的兄弟篇）。所以本文件的编号/命名是**按任务书指定**，不是既有系列的一环。
- **没有找到 `docs/research/weknora-kb-ui/_parts/` 里的任何文件**（目录存在但为空）。
- **未做运行时验证**：全部结论来自静态阅读源码。**未启动前端、未打开浏览器、未截图**。因此"hover 后实际观感""选中态是否真的没有高亮"这类结论属于**代码推断**，不是实测。
- **未覆盖**：`FAQEntryManager.vue`（161 KB，FAQ 分块/问答管理）、`WikiBrowser.vue`（242 KB）、`OverviewSettings` 系列（`views/knowledge/settings/*`，共 16 个文件）、`KnowledgeBaseActivitySettings.vue`、`DataSourceEditorDialog.vue`、`GraphSettings.vue` 等。任务书要求的是"知识库列表页 + 详情页（文档/分块）+ 它们用到的对话框/抽屉/卡片/空态"，我按此边界收敛；`FAQEntryManager` 只在详情页分流处登记（`KnowledgeBase.vue:2560`）。
- **虚拟滚动**：`vue-virtual-scroller@^2.0.0-beta.8`（`package.json:45`）**只在 `WikiBrowser.vue` 用到**（`RecycleScroller`，`WikiBrowser.vue:355-366`、`import` 在 `:801`）。知识库列表页与文档列表**都不用虚拟滚动**，是普通 DOM + 无限滚动（`KnowledgeBase.vue:1857-1879`）。**没有 `t-pagination` 用于文档列表**；唯一的 `t-pagination` 在文档详情抽屉的分块视图（`doc-content.vue:2130`，每页 25）。
- **明暗两套的完整差异未逐条穷举**：我只核对了品牌/警告/错误/成功/灰阶/背景/描边/文字这 8 组，深色块里 `--td-gray-color-1..14` 与浅色块**字面相同**（`theme.css:47-60`），这是**照抄未改**还是刻意共用，源码没有注释说明，我**不确定**。
- **`--td-line-height-title-large` 疑似笔误**：浅色块里 `--td-line-height-title-large: calc(var(--td-font-size-title-medium) + var(--td-line-height-common))` —— 用 `title-medium`（16px）而不是 `title-large`（20px），算出 24px。深色块同样（`theme.css:92`）。这**看起来是上游/本仓的复制粘贴错误**，但我无法确认是有意还是笔误，**不做结论**。
- **`KnowledgeBase.vue` 的 `.doc-marquee-box` z-index 是 4**（`:2993`），低于批量条锚点的 6（`:3016`）与吸顶表头的 3（`DocumentListView.vue:539`）——与表头 3 相比是高的，与批量条相比是低的，顺序上说得通，但**我没有找到任何注释解释这组层级**，属于推断。
- **共享详情抽屉的 z-index = 1000**（`KnowledgeBaseList.vue:2298`），而同一文件里设置类弹窗壳传的是 `:z-index="1000"`（`KnowledgeBaseEditorModal.vue:4`）——两者同级，若同时打开，叠放顺序**取决于 DOM 顺序**，我没有验证实际表现。
- **未统计**：本块所有 `.vue` 文件的总代码行数/组件数（无意义的口径），以及未做 CSS 字面量残留统计（仓库里有"样式守卫会统计残留字面量"的注释，见 `theme.css:223`，但我**没找到该守卫脚本**，也没运行）。
- **未核实**：`frontend/src/assets/dropdown-menu.less`（18.5 KB）里 `.card-more` / `.card-more-popup` / `.card-menu` 的完整数值——我读了它的规则**目录**（41–443 行的选择器清单）并引用了其中被 KB 区复用的部分（如 `.card-menu`、`.move-menu-*`），但**没有逐条抄出全部数值**；如需精确到 px 请直接读该文件。
