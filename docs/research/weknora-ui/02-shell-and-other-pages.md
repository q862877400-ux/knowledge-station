# WeKnora 前端精读 02 — 外壳与"知识库/问答之外"的全部界面

> 只读研究记录。源码：`D:\AI\WeKnora`（**未修改任何文件**）。
> 前端 `D:\AI\WeKnora\frontend`，Vue 3 + TDesign Vue Next + Pinia + vue-i18n + vue-router。
> 许可证：MIT（`D:\AI\WeKnora\LICENSE:8`，另附第三方组件声明于 `LICENSE:25` 起；抄代码需随附版权声明）。
>
> **本次范围**：全站外壳/导航/主题/i18n、登录与鉴权、设置、组织与权限、Agent 与集成、平台/系统/开发者页、全局通用件。
> **明确未做（另有代理负责）**：`views/knowledge`、`views/chat`、`views/creatChat`、`views/artifacts`、`components/chat`、`document-preview.vue`。
> 这些在页面清单里列出但标注 `[范围外]`，不对其内容下结论。
>
> 引用格式 `文件:行`。界面文案**原文照抄**（保持原语言，中文为主，取自 `i18n/locales/zh-CN.ts`，路径简写为 `zh-CN.ts`）。
> 未标注的编号（如"某行附近"）表示由读取范围推断，已尽量逐条核过。

---

## 0. 一张图先看结论

WeKnora 的 SPA 是**"无顶栏、全高左侧栏 + 内容区"**的两栏壳（`views/platform/index.vue:249-269`），
导航全部挂在 260px 侧栏里；**设置不是页面而是全屏弹窗**（`views/settings/Settings.vue:477-479`），
所有"管理类"界面（系统设置、任务队列、平台密钥、审计日志、发布集成）都是这个弹窗的 `?section=`；
**权限用"角色最小可见角色表"集中表达**（`config/settingsAccess.ts:10-35`）；
**"这是不是核心/企业版功能"前端基本不表态**，改用后端 `deployment/capabilities` 的能力位 + `Lite` 版本位来隐藏入口
（`config/deploymentCapabilities.ts:1-14`、`stores/deploymentCapabilities.ts:41-47`）。

---

## 1. 全站页面清单表

路由定义全部在 `frontend/src/router/index.ts`。`requiresAuth/requiresInit/requiredCapability/requiresSystemAdmin` 是守卫用的 meta。

| 路由路径 | 路由行 | 文件 | 一句话职责 | 核心/企业版 |
|---|---|---|---|---|
| `/` | `router/index.ts:49-52` | —（redirect） | 直接跳 `/platform/knowledge-bases` | 核心 |
| `/login` | `router/index.ts:53-58` | `views/auth/Login.vue` | 登录 + 自助注册 + OIDC | 核心 |
| `/register` | `router/index.ts:60-70` | `views/auth/Login.vue`（同组件双模式） | 邀请链接落地页（`?token=` 切注册态） | 核心 |
| `/onboarding/workspace` | `router/index.ts:71-76` | `views/auth/WorkspaceOnboarding.vue` | 无有效空间的用户：创建空间 / 查看邀请 | 核心（多租户形态） |
| `/join` | `router/index.ts:77-89` | —（redirect） | 把 `?code=` 转成 `/platform/organizations?invite_code=` | 核心 |
| `/knowledgeBase` | `router/index.ts:90-95` | `views/knowledge/KnowledgeBase.vue` | `[范围外]` | — |
| `/platform` | `router/index.ts:96-217` | `views/platform/index.vue` | **全站外壳**：侧栏 + 路由出口 + 所有全局挂件 | 核心 |
| `/platform/settings` | `router/index.ts:107-112` | `views/settings/Settings.vue` | 设置弹窗（24 个 section + 7 个集成 tab） | 核心 |
| `/platform/knowledge-bases` | `router/index.ts:113-118` | `views/knowledge/KnowledgeBaseList.vue` | `[范围外]` | — |
| `/platform/knowledge-bases/:kbId` | `router/index.ts:119-124` | `views/knowledge/KnowledgeBase.vue` | `[范围外]` | — |
| `/platform/knowledge-search` | `router/index.ts:125-135` | —（redirect） | 旧搜索路径 → `/platform/knowledge-bases?cmdk=<q>` 打开命令面板 | 核心 |
| `/platform/artifacts` | `router/index.ts:136-141` | `views/artifacts/ArtifactLibrary.vue` | `[范围外]`；meta `requiredCapability:'settings.sandbox'` | 依赖沙箱 |
| `/platform/agents` | `router/index.ts:142-147` | `views/agent/AgentList.vue` | 智能体列表；meta `requiredCapability:'agents'` | 能力位控制 |
| `/platform/integrations` | `router/index.ts:148-164` | —（redirect） | → `/platform/settings?section=integration-<tab>` | 能力位控制 |
| `/platform/creatChat` | `router/index.ts:165-170` | `views/creatChat/creatChat.vue` | `[范围外]` | — |
| `/platform/knowledge-bases/:kbId/creatChat` | `router/index.ts:171-176` | `views/creatChat/creatChat.vue` | `[范围外]` | — |
| `/platform/chat/:chatid` | `router/index.ts:177-182` | `views/chat/index.vue` | `[范围外]` | — |
| `/platform/organizations` | `router/index.ts:183-188` | `views/organization/OrganizationList.vue` | 共享空间列表 + 设置弹窗；meta `requiredCapability:'organizations'` | Lite 下隐藏 |
| `/platform/system` | `router/index.ts:193-197` | —（redirect） | → `?section=system-global`；meta `requiresSystemAdmin` | 系统管理员 |
| `/platform/system/settings` | `router/index.ts:198-203` | —（redirect） | → `?section=system-global` | 系统管理员 |
| `/platform/system/admins` | `router/index.ts:204-209` | —（redirect） | → `?section=system-global` | 系统管理员 |
| `/platform/system/queues` | `router/index.ts:210-215` | —（redirect） | → `?section=runtime-queues` | 系统管理员 |
| `/platform/tenant` | `router/index.ts:103-106` | —（redirect） | → `/platform/settings` | 核心 |
| `/platform/dev/markdown` | `router/index.ts:218-224` | `views/dev/MarkdownTestPage.vue` | **仅 DEV 构建存在**的 markdown 渲染回归页 | 非产品页 |

**没有独立路由、但占"一屏"的设置页**（全部由 `Settings.vue` 按 `currentSection` 切换渲染，见 `views/settings/Settings.vue:78-196`）：

| section key | 组件 | 一句话职责 | 核心/企业版 |
|---|---|---|---|
| `general` | `settings/GeneralSettings.vue` | 语言、主题、界面/代码字体、字号、（Lite）自动更新 | 核心 |
| `userprofile` | `settings/UserProfile.vue` | 账户基本信息 + 改密码 | 核心 |
| `browserconnection` | `settings/BrowserConnectionSettings.vue` | 配对本机 Chrome（BrowserSkill） | 能力位无关，产品特性 |
| `mymemory` | `settings/MemorySettings.vue` | 个人长期记忆的查看/修改/删除 | 依赖空间开关 |
| `envvars` | `settings/EnvVarSettings.vue` | 个人沙箱密钥 | 依赖 `settings.sandbox` |
| `tenant` | `settings/TenantInfo.vue` | 当前空间详情 | 核心（多租户形态） |
| `members` | `settings/TenantMembers.vue` | 成员名册 + 邀请 + 角色 + 审计 | 核心（多租户形态） |
| `chathistory` | `settings/ChatHistorySettings.vue` | 对话消息向量化索引 | 核心 |
| `memory` | `settings/MemoryWorkspaceSettings.vue` | 空间级长期记忆开关/写入方式 | 核心 |
| `models` | `settings/ModelSettings.vue` | chat/embedding/rerank/vllm/asr 五类模型增删改 | 核心 |
| `ollama` | `settings/OllamaSettings.vue` | 本地 Ollama 连接与模型下载 | 核心 |
| `weknoracloud` | `settings/WeKnoraCloudSettings.vue` | WeKnora Cloud 的 APPID/APPSECRET + 云模型注册 | 云端服务 |
| `vectorstore` | `settings/VectorStoreSettings.vue` | 向量库实例注册 | 能力位 `settings.vectorstore` |
| `parser` | `settings/ParserEngineSettings.vue` | 文档解析引擎（DocReader/MinerU/vlm） | 核心 |
| `storage` | `settings/StorageBackendSettings.vue` | 对象/文件存储实例 | 能力位 `settings.storage` |
| `sandbox` | `settings/SandboxSettings.vue` | 沙箱配置（Docker/E2B/CubeSandbox） | 能力位 `settings.sandbox` |
| `skills` | `settings/SkillSettings.vue` | 技能目录 + 装机到沙箱 | 依赖 `settings.sandbox` |
| `websearch` | `settings/WebSearchSettings.vue` | 联网搜索引擎多实例 + 代理 | 能力位 `settings.websearch` |
| `mcp` | `settings/McpSettings.vue` | 外部 MCP 服务注册与测试 | 能力位 `settings.mcp` |
| `system` | `settings/SystemInfo.vue` | 版本/构建/引擎/DB 迁移状态 | 核心 |
| `system-global` | `system/SystemSettings.vue` | 平台级运行时配置（5 个 tab） | **系统管理员** |
| `runtime-queues` | `system/RuntimeQueues.vue` | 任务队列运行时 + Worker 池 + 任务明细 | **系统管理员** |
| `platform-api-keys` | `system/PlatformAPIKeys.vue` | 平台级 API Key | **系统管理员** |
| `system-audit-log` | `system/SystemAuditLog.vue` | 平台级审计日志 | **系统管理员** |
| `integration-<tab>` | `integrations/IntegrationSettingsSection.vue` | 发布集成（7 tab，见 §5.4） | 能力位控制 |

> 判据说明：上表"核心/企业版"一栏是我从**能力位键名 + Lite 判定 + 角色门槛**反推的，
> 前端**没有任何"企业版"字样或升级引导**（见 §9）。凡写"能力位控制"的，意思是**核心代码里存在，
> 但是否出现在 UI 由后端 `/deployment/capabilities` 决定**——从 UI 无法判断它属于哪个商业版本。

---

## 2. 一屏 ASCII 骨架

依据 `views/platform/index.vue:1-21,249-269` 与 `components/menu.vue`（根节点 `aside_box`）。

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  .main (display:flex; height:100%; min-width:600px; background:--td-bg-color-container)│
│                                                                                      │
│ ┌── aside_box (260px / 折叠 60px, 可拖右边缘展开) ──┐ ┌── .platform-route-outlet ───┐ │
│ │ [logo_row]  🔷Logo + 搜索图标(⌘K) + 折叠按钮      │ │                             │ │
│ │ ── 仅当可切换空间 ──                              │ │   <RouterView/>             │ │
│ │ [TenantSelector 空间选择器]                       │ │   （每个子页面自带页头，     │ │
│ │                                                   │ │    壳本身无顶栏/无面包屑）   │ │
│ │ ┌ menu_top (可滚动) ────────────────────────────┐ │ │                             │ │
│ │ │ (折叠态) 🔍 搜索                              │ │ │                             │ │
│ │ │ ① 新对话        creatChat                     │ │ │                             │ │
│ │ │ ② 知识库        knowledge-bases               │ │ │                             │ │
│ │ │ ③ 产物          artifacts   ← 能力位          │ │ │                             │ │
│ │ │ ④ 智能体        agents      ← 能力位          │ │ │                             │ │
│ │ │ ⑤ 共享空间      organizations ← admin+Lite隐藏│ │ │                             │ │
│ │ │ ── 会话区（展开态）──                          │ │ │                             │ │
│ │ │ [来源筛选行] 全部/网页/微信/飞书/…             │ │ │                             │ │
│ │ │ ▸ 置顶 / 今天 / 昨天 / 近7天 / 近30天 / …      │ │ │                             │ │
│ │ │   ▸ 会话行(可改名/置顶/删除/批量选择)          │ │ │                             │ │
│ │ └───────────────────────────────────────────────┘ │ │                             │ │
│ │                                                   │ │                             │ │
│ │ [批量管理条] ☐全选   取消 | 删除对话(n)   ← 批量态 │ │                             │ │
│ │ ┌ menu_bottom ──────────────────────────────────┐ │ │                             │ │
│ │ │ UserMenu 头像行：空间名 / 用户名 · 角色徽标    │ │ │                             │ │
│ │ │   展开 → 个人设置 · 空间设置 · 成员管理 ·     │ │ │                             │ │
│ │ │          模型管理 · 技能管理 · 全部设置 ·     │ │ │                             │ │
│ │ │          系统管理(仅 isSystemAdmin) · 帮助与  │ │ │                             │ │
│ │ │          文档 · GitHub ★ · 退出               │ │ │                             │ │
│ │ └───────────────────────────────────────────────┘ │ └─────────────────────────────┘ │
│ └───────────────────────────────────────────────────┘                                │
│                                                                                      │
│  全局覆盖层（都挂在外壳里，不属于任何子路由）：                                        │
│   • Settings 全屏设置弹窗        views/settings/Settings.vue                          │
│   • GlobalCommandPalette ⌘K      components/GlobalCommandPalette.vue                  │
│   • GlobalInvitationBell 🔔      components/GlobalInvitationBell.vue (fixed top:12 right:16) │
│   • UploadTasksPanel 上传浮层    components/upload-tasks/UploadTasksPanel.vue         │
│   • NewUserGuide 新手引导        components/NewUserGuide.vue                          │
│   • UploadMask 拖拽遮罩          components/upload-mask.vue                           │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

关键点：**没有全局顶栏、没有全局面包屑**（全仓 grep `breadcrumb` 只命中知识库 FAQ 内部与 `stores/auth.ts:78` 的一句注释）。
"我在哪"只靠 ① 侧栏菜单项高亮 + ② 页面自己的标题行表达。例如智能体页自己画 `<h2>{{ $t('agent.title') }}</h2>`
（`views/agent/AgentList.vue:10`），并带 Wails 桌面拖拽属性。

---

## 3. §1 全站外壳与导航

### 3.1 壳里放了什么

`views/platform/index.vue:1-21` 一次性挂载：`Menu`、`<RouterView/>`、`UploadMask`、`Settings`、
`GlobalCommandPalette`、`GlobalInvitationBell`、`UploadTasksPanel`、`NewUserGuide`。
注释（原文）：

- `GlobalCommandPalette`：`<!-- 全局命令面板 (⌘K)，随 platform 路由存活 -->`（`views/platform/index.vue:12`）
- `GlobalInvitationBell`：
  `<!-- 全局右上角"待处理邀请"铃铛。固定定位，z-index 低于抽屉，业务页面右侧抽屉弹出时会自然覆盖；仅在有待处理邀请时渲染。 -->`（`:14-16`）
- `UploadTasksPanel`：
  `<!-- 知识库文件上传进度浮层：上传队列放在 store 里，切换页面不中断 -->`（`:17`）
- `NewUserGuide`：
  `<!-- 带遮罩层的新手引导：首次进入自动开启，可从用户菜单顶部昵称旁帮助按钮重新打开 -->`（`:19`）

布局：`.main` 是 `display:flex`（`:250-259`），`.platform-route-outlet` 是 `flex:1; min-width:0; min-height:0; overflow:hidden`
（`:262-269`），即**滚动权交给子页面**。

壳还承担全局文件拖放（OS 文件拖入才接管，元素拖拽不接管，判据见 `:117-141`），
以及 Wails 桌面端拦截 `Ctrl/Cmd+R` 做软刷新（`:57-70`）。

### 3.2 导航项清单与层级

导航的**唯一真源**是 `stores/menu.ts:24-40` 的 `menuArr`（7 项）：

| 顺序 | `titleKey` | `path` | 图标 | 门槛 | 出处 |
|---|---|---|---|---|---|
| 1 | `menu.newChat` | `creatChat` | `prefixIcon` | — | `stores/menu.ts:25-32` |
| 2 | `menu.knowledgeBase` | `knowledge-bases` | `zhishiku` | — | `:33` |
| 3 | `menu.artifacts` | `artifacts` | `artifact` | `settings.sandbox` | `:34-35` |
| 4 | `menu.agents` | `agents` | `agent` | `agents` | `:36` |
| 5 | `menu.organizations` | `organizations` | `organization` | `organizations` | `:37` |
| 6 | `menu.settings` | `settings` | `setting` | — | `:38` |
| 7 | `menu.logout` | `logout` | `logout` | — | `:39` |

中文文案（`zh-CN.ts:7402-7410`）：
`menu.newChat: '新对话'`、`menu.knowledgeBase: '知识库'`、`menu.agents: '智能体'`、`menu.artifacts: '产物'`、
`menu.organizations: '共享空间'`、`menu.settings: '系统设置'`（原文如此，虽然设置页自称"设置"）、`menu.logout: '退出登录'`。

**层级是"两段式"而不是树**：`menu.vue:444` 定义
`const TOP_MENU_PATHS = new Set(['creatChat', 'knowledge-bases', 'artifacts', 'agents', 'organizations']);`
`topMenuItems` = 这 5 项（`:446-448`），`bottomMenuItems` = 其余（`:450-452`，实际只有 settings/logout，但渲染上 settings/logout 由 `UserMenu` 承担，见 `:194-196`）。
第 1 项下的"子项"不是页面层级，而是**会话列表**（`menuArr[0].children`，`:31`、`:99-116`）。

可见性过滤（`stores/menu.ts:73-88`）：

```ts
if (authStore.isLiteMode && liteHiddenPaths.has(item.path)) return false
if (item.path === 'organizations' && !authStore.hasRole('admin')) return false
if (!deploymentCapabilities.isSupported(item.requiredCapability)) return false
```
`liteHiddenPaths = new Set(['logout', 'organizations'])`（`:68`），并附注原文：
`// 共享空间 (organizations) 仅对当前空间的 admin / owner 暴露入口。`（`:70-72`）

路由守卫里还有一层（同步的）：`requiredCapability` 不满足 → `MessagePlugin.warning(t('settings.capabilityUnavailable'))` 并弹回知识库列表
（`router/index.ts:409-416`；文案 `zh-CN.ts:6296`：`'当前部署不支持此功能，已返回可用页面。'`）。

### 3.3 "现在在哪"的表达

1. **菜单高亮**：`isMenuItemActive()`（`menu.vue:403-425`）按 `route.name` 判断，例如
   `case 'knowledge-bases': return currentRoute === 'knowledgeBaseList' || 'knowledgeBaseDetail' || 'knowledgeBaseSettings'`。
2. **图标换色**：菜单项激活时把图标换成 `*-green.svg`（`menu.vue:1088-1117`，注释原文 `// 知识库图标：只在知识库页面显示绿色`）。
3. **会话行高亮**：`session-chat-row--active`（`menu.vue:142-147`）。
4. **没有面包屑、没有全局 tab 条**。页面内的"当前位置"由页面自己解决——例如设置弹窗用左侧 nav 高亮
   （`Settings.vue:7-11` 的 `'active': currentSection === item.key`），列表/详情用页面标题。

### 3.4 可折叠 / 响应式

- 折叠按钮在 logo 行右侧（`menu.vue:22-29`），折叠后变成一个可点击的展开项（`:32-50`）。
- 宽度：展开 `min-width:260px; width:260px`（`menu.vue:1227-1228`），折叠 `min-width:60px; width:60px`（`:1250-1253`），
  过渡 `transition: width 0.25s ease, min-width 0.25s ease`（`:1242`）。
- **拖拽展开**：折叠态右侧有一条 `sidebar-drag-handle`（`:56`），`onDragHandleMouseDown` 向右拖过 40px 即展开（`:1196-1214`）。
- 折叠状态持久化到 `localStorage['sidebar_collapsed']`（`stores/ui.ts:23`、`:123-136`）。
- 响应式：壳层**没有 `@media`**（`views/platform/index.vue` grep 无命中）；只有 `min-width:600px`（`:255`）。
  真正写 `@media` 的是业务页（`AgentList.vue` 5 处、`OrganizationList.vue` 5 处、`TenantMembers.vue` 3 处、
  `OrganizationSettingsModal.vue` 3 处、`RuntimeQueues.vue` 2 处、`ApiIntegrationSettings.vue` 2 处等）。
  另有 macOS 桌面让位：`html.wails-desktop & { padding-top: 30px; }`（`menu.vue:1245-1248`）。

### 3.5 主题（明暗切换在哪、是否跟随系统）

真源：`composables/useTheme.ts`。

- 三态 `export type ThemeMode = 'light' | 'dark' | 'system'`（`:8`）。
- **默认 light**：`return 'light'`（`:12-16`）。
- 存储键 `'theme'`，走 `preferenceStorage`（`:10`、`:75`）；换用户会 `migratePreferencesIntoUser()` 后重读（`:97-101`）。
- 生效方式：写 `<html theme-mode="light|dark">`（`:67`），并同步桌面原生窗口底色（`:28-61`）。
- **跟随系统是真实时跟随**：`window.matchMedia('(prefers-color-scheme: dark)')` +
  `addEventListener('change', ...)`，仅当 `currentTheme === 'system'` 时重算（`:88-93`）。
- 初始化在挂载前：`initTheme()`（`main.ts:26`）。
- 另有 `color-scheme: light dark` 提示 UA 画滚动条（`App.vue:288-290`）。

**切换入口只有一个：设置 → 常规**。`views/settings/GeneralSettings.vue:31-49` 是唯一的 `t-select`，
三个取值 `light/dark/system`（`:44-46`）。文案 `zh-CN.ts:2729-2735`：

```
theme: '主题模式'
themeDescription: '选择界面的显示主题，支持跟随系统自动切换'
light: '浅色'  dark: '深色'  system: '跟随系统'
selectTheme: '选择主题'
```

**登录页没有主题开关**（`Login.vue` 顶部只有 官网 / GitHub / 语言，见 `:104-142`）。
有一条纪律值得注意（其他代理范围，但证据在 `views/chat/components/SandboxTerminal.vue:53-56` 注释）：
`// 主题必须从 useTheme 的共享 ref 派生，不能读 theme-mode DOM 属性`——即"主题状态是应用状态，不是 DOM 的投影"。

### 3.6 语言切换入口

两处，都是写 `localStorage['locale']` + `locale.value = x` + toast：

1. **登录页右上角**：`language-switch` 按钮 + 下拉（`Login.vue:123-142`），
   `const languageOptions` 硬编码五项与国旗 emoji（`Login.vue:437-443`）；
   `selectLanguage()` 写 `localStorage.setItem('locale', lang)`（`:522-528`）。
2. **设置 → 常规**：`t-select`（`GeneralSettings.vue:16-27`），
   `handleLanguageChange()` 写 `localStorage.setItem('locale', ...)` 并
   `MessagePlugin.success(t('language.languageSaved'))`（`:235-239`，文案 `zh-CN.ts:2755`: `'语言设置已保存'`）。

---

## 4. §2 登录与鉴权

### 4.1 有哪几种方式

`views/auth/Login.vue` 一个组件承担**全部**入口（路由 `/login` 与 `/register` 共用，`router/index.ts:60-70` 注释原文：
`Share-link landing page reuses the Login form: the same Vue component renders both modes and detects ?token=xxx on mount`）。

| 方式 | 判定与入口 | 出处 |
|---|---|---|
| **账号密码** | `email` + `password` 两个 `t-form-item`，按钮 `auth.login` | `Login.vue:204-216` |
| **自助注册** | `registrationEnabled` 为真时显示 `首次使用 WeKnora？` 分隔 + `创建账户` 按钮切模式 | `Login.vue:218-226`；`registrationEnabled` 来自 `/auth/config` 的 `registration_mode !== 'invite_only'`（`:615-621`） |
| **OIDC / SSO（单提供商）** | `oidcEnabled` 为真时显示分隔 `或使用以下方式继续` + 按钮 | `Login.vue:228-235`；`loadOIDCConfig()` 调 `getOIDCConfig()`，按钮文案 `auth.oidcLoginWithProvider` 插值 `provider_display_name`（`:446-451`、`:604-612`） |
| **邀请链接注册** | URL `?token=xxx` → `getInvitationByToken` → 切 `isRegisterMode` 并顶部显示邀请横幅 | `Login.vue:260-336`、`:425-434` |
| **首次运行自动开通（auto-setup）** | 路由守卫里 `autoSetup()` 成功即视为已登录 | `router/index.ts:381-396` |

英文界面文案（`zh-CN.ts:5105-5153`，原文）：
`login: '登录'`、`loggingIn: '登录中...'`、`register: '注册'`、`createAccount: '创建账户'`、
`haveAccount: '已有账户？'`、`backToLogin: '返回登录'`、
`loginHint: '登录以继续使用；首次使用请在下方创建账户。'`、`firstTime: '首次使用 WeKnora？'`、
`oidcLogin: '使用 OIDC 登录'`、`oidcLoginWithProvider: '使用 {provider} 登录'`、
`redirectingToOIDC: '正在跳转到身份提供商...'`、`orContinueWith: '或使用以下方式继续'`、
`subtitle: 'RAG 问答、ReAct 智能体与 Wiki 知识库，大模型驱动的企业级知识框架'`、
`registerSubtitle: '创建账户并开始使用 WeKnora'`。

校验规则（`Login.vue:468-506`）：邮箱 required+email；密码 `min:8 / max:32`；
用户名 `min:2 / max:20` 且 `pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/`（中文错误提示 `zh-CN.ts:5145-5148`）；
注册密码走 `newPasswordRules(t, complexPasswordEnabled)`（`utils/passwordPolicy`），复杂度开关来自 `/auth/config` 的 `complex_password_enabled`。

**没有 LDAP、没有短信/验证码、没有二维码登录**：在 `Login.vue` 内对 `ldap|LDAP|sso|SSO|sms|SMS` 的 grep **零命中**；
`api/auth/index.ts` 的导出里也只有 `login / register / registerByInvite / getOIDC* / getAuthConfig / getCurrentUser / logout / changePassword / refreshToken / validateToken`（`:211-538`）。
这一条是**否定证据**：我只能证明前端没有这些入口，不能证明后端没有。

OIDC 回跳：后端回调地址 `window.location.origin + '/api/v1/auth/oidc/callback'`（`Login.vue:602`）；
结果由 `App.vue` 消费 URL hash 的 `oidc_result=` / `oidc_error=`（`App.vue:128-172`），
且路由守卫**专门为它让路**（`router/index.ts:318-323` 注释原文：
`OIDC 回跳登录结果依赖 App.vue 在挂载后消费 URL hash。如果这里先按"未登录"拦截到 /login，会导致回调结果没有机会落盘。`）。
OIDC 登录后的成员关系会强制刷新（`App.vue:76-82` 注释：`Without this, memberships stay frozen at the login-time snapshot and the UI silently lies about our authority.`）。

### 4.2 登录页还放了什么

- 左半屏"showcase"：产品标语 + 4 个能力标签 + Swiper 轮播 4 张截图（`Login.vue:145-173`、`:384-406`）。
  标签文案（`zh-CN.ts:2672-2675`）：`'RAG 增强生成'`、`'ReAct 智能体'`、`'Wiki 知识库'`、`'混合检索'`。
  轮播标题：`Agentic RAG` / `混合检索策略` / `Wiki 知识库` / `智能文档检索`（`zh-CN.ts:2682-2691`）。
- 右上角三件事：官网、GitHub、语言切换（`Login.vue:104-142`）。
- 表单下方 3 条 `✓` 卖点：`多模态文档解析` / `混合检索 + 知识图谱` / `ReAct 智能体问答`（`Login.vue:239-252`，文案 `zh-CN.ts:2676-2678`）。
- 注册卡下方 3 条：`独立空间` / `完整 API 访问` / `知识库管理`（`Login.vue:321-334`）。
- **无版本号、无隐私/服务条款链接**（模板里只有那三个外链）。

### 4.3 首次进入的引导（onboarding / 向导）

**(a) 空间 onboarding（真·必经门）**：`views/auth/WorkspaceOnboarding.vue`。
守卫在"已登录但没有有效空间"时强制进入（`router/index.ts:402-405`）。
页面是单卡双按钮：`创建空间` / `查看邀请`（`WorkspaceOnboarding.vue:34-51`）。
文案（`zh-CN.ts:5154-5167`，原文）：

```
title: '选择你的工作空间'
description: '创建一个空间即可开始使用，或接受邀请加入已有空间。'
create: '创建空间'
invitations: '查看邀请'
loadingPolicy: '正在确认可用的空间加入方式…'
policyLoadFailed: '暂时无法获取空间权限，请检查网络后重试。'
retry: '重新加载'
inviteOnlyTitle: '等待加入工作空间'
inviteOnlyDescription: '当前系统不开放个人创建空间。你可以查看并接受管理员发来的空间邀请。'
inviteOnlyNotice: '此账户只能通过邀请加入已有空间'
help: '你现在可以创建空间，也可以稍后回来接受邀请。'
inviteOnlyHelp: '还没有邀请？请把你的注册邮箱提供给空间管理员，由管理员向你发送邀请。'
```

**(b) 产品新手引导（可跳过、可重开）**：两层。
- 全局一次：`components/NewUserGuide.vue`，7 步 `welcome → knowledge → agents → chat → settings → models → done`
  （`:16-53`），首开延迟 700ms（`:87-91`），完成写 `GLOBAL_USER_GUIDE_KEY = 'weknora:new-user-guide-done:v1'`（`config/contextualGuides.ts:3`、`NewUserGuide.vue:65`）。
  重开入口：用户菜单昵称旁的帮助按钮（`components/UserMenu.vue:45-50`，tooltip `newUserGuide.reopen`），
  或命令面板"新手引导"（`GlobalCommandPalette/commands.ts:86-95`）。
- 按场景各一次：`config/contextualGuides.ts:46-135` 定义了 7 个 tour
  `kbList / kbCreate / kbDetail / chat / tenantModels / agentList / agentCreate`，
  各自独立 localStorage 键（版本化，如 `'weknora:contextual-guide-kb-list:v2'`，`:48`），
  并有"完成本引导时一并标记其他引导已完成"的 `alsoCompleteTours`（`:42-43`、`:66`、`:132`）。
  步骤用 DOM 选择器定位，例如 `target: '.empty-state-btn[data-guide="kb-list-create"], [data-guide="kb-list-create"]'`（`:55`）。
  引导通用按钮文案（`zh-CN.ts:7091-7098`）：`stepOf: '{current} / {total}'`、`skip: '跳过'`、`prev: '上一步'`、`next: '下一步'`、`done: '知道了'`、`interactHint: '请直接点击高亮区域继续'`。

**(c) 其它引导件**：`SpotlightGuide.vue`（遮罩高亮引擎）、`ContextualGuide.vue`、
`AgentCreateContextualGuide.vue`、`KbCreateContextualGuide.vue`、`TenantModelsGuide.vue`（模型未配时引导去设置）。

### 4.4 会话与身份

- 令牌：`localStorage['weknora_token']` + `weknora_refresh_token`，`hydrateSessionFromToken()` 在守卫里恢复（`router/index.ts:246-309`）。
- 邀请轮询：登录后每 2 分钟拉一次待处理邀请数（`App.vue:176-199`，常量 `INVITATION_POLL_INTERVAL_MS = 2 * 60 * 1000`，`:182`）。
- 切换空间后**硬刷新**，因此把 toast 暂存到下次加载再弹（`App.vue:213-239` 注释：
  `切换空间后会 hard reload；切换前 stash 的 toast 这里 consume 并弹出，这样 toast 显示在新页面上`）。

---

## 5. §3 设置

### 5.1 形态：不是页面，是全屏弹窗

`Settings.vue` 用共享壳 `SettingsModalShell`（`Settings.vue:2`），它的注释说明了规格（`components/SettingsModalShell.vue:60-67`，原文）：

```
全屏"设置类"弹窗壳：遮罩 + 1080×780 面板 + 左侧分组导航 + 右侧内容 + 可选底栏。
被 Settings / AgentEditorModal / OrganizationSettingsModal / KnowledgeBaseEditorModal 共用，
关闭行为（Esc / 遮罩 / 未保存守卫）由消费方通过 useModalShell 决定，本组件只发出 `close`。
```

显示条件（`Settings.vue:477-479`）：`route.path === '/platform/settings' || uiStore.showSettingsModal`。
也就是说**它同时是路由页和全局弹窗**：侧栏点"系统设置"走 `uiStore.openSettings()` + `router.push('/platform/settings')`（`menu.vue:1133-1136`）。

URL 是位置的唯一真源：`?section=<navKey>`（`config/settingsRoute.ts:47-62` 注释原文：
`Settings left-nav → URL. Every page, including integrations, is ?section=<navKey> (e.g. integration-claw). tab is dropped.`）。
旧 `?tab=` 与裸 tab 名做兼容归一（`settingsRoute.ts:32-45`）。
`/platform/integrations?tab=api` 也在这里被折成 `?section=integration-api`（`router/index.ts:148-164`）。
关闭时若当前是系统管理类 section，则回知识库列表而非 `router.back()`（`Settings.vue:488-496`）。

### 5.2 页签清单与分组

`navGroups`（`Settings.vue:387-439`）分 7 组，注释把设计取舍写清楚了（`:390-393`，原文）：

```
// 分组：账户 → 空间 → 模型 → 发布集成 → 数据与扩展 → 系统管理 → 平台
// 关键调整：把个人偏好(general)和用户信息收进「账户」；
// 把空间内功能开关(chathistory)从「平台」挪到「空间」；
// 把检索引擎和外部集成合并为「数据与扩展」，避免两个 2~3 项的窄分组。
```

| 组 key | 组标题 | 成员（顺序即数组顺序） | 出处 |
|---|---|---|---|
| `account` | `账户` | `general, userprofile, browserconnection, mymemory, envvars` | `Settings.vue:395-399` |
| `workspace` | `空间` | `tenant, members, chathistory, memory` | `:400-404` |
| `models_runtime` | `模型` | `models, ollama, weknoracloud` | `:405-409` |
| `integrations` | `发布集成` | `integration-im / -embed / -api / -mcpserver / -cli / -chrome / -claw` | `:410-414` |
| `data_extensions` | `数据与扩展` | `vectorstore, parser, storage, sandbox, skills, websearch, mcp` | `:415-427` |
| `system_administration` | `系统管理` | `system-global, runtime-queues, platform-api-keys, system-audit-log` | `:428-432` |
| `platform` | `平台` | `system`（版本信息） | `:433-437` |

组标题文案 `zh-CN.ts:6297-6304`：`account: '账户'`、`workspace: '空间'`、`modelsRuntime: '模型'`、
`dataExtensions: '数据与扩展'`、`systemAdministration: '系统管理'`、`platform: '平台'`。
空组会被 `.filter((group) => group.items.length > 0)` 丢掉（`Settings.vue:438`）。

页签 label 来源见 `Settings.vue:351-377`（部分直接硬编码，如 `{ key: 'ollama', icon: 'server', label: 'Ollama' }`、
`{ key: 'weknoracloud', icon: '', label: 'WeKnora Cloud' }`）。
另有**子菜单**机制：`item.children` 非空时展开并 `scrollIntoView`（`Settings.vue:49-57`、`:463-474`），
目前实际用的是 `skills` 的"预选沙箱"（`:525-528`，注释：
`Sandbox config id from the agent editor / sandbox cards. Skills has no nav children, so this is the only way to preselect the target image.`）。

### 5.3 每页管什么（原文描述）

| section | 标题 / 描述（原文） | 出处 |
|---|---|---|
| `general` | `常规设置` / `配置语言、外观等基础选项` | `zh-CN.ts:2738,2742` |
| `userprofile` | `用户信息` / `查看您的账户基础信息（用户 ID、用户名、邮箱、注册时间），并可修改登录密码` | `:345-346` |
| `browserconnection` | `浏览器连接` / `通过 BrowserSkill 连接本机 Chrome，配对后即可在对话中操作真实网页。` | `:65-66` |
| `mymemory` | `我的记忆` / `这里是助手跨会话记住的关于你的内容。你可以随时查看、修改和删除，删除后不会再被使用。` | `:5268-5269` |
| `envvars` | `沙箱密钥` / `给技能和沙箱用的个人密钥，不是 WeKnora 的系统或部署配置。` | `:5407-5408` |
| `tenant` | `空间信息` / `查看空间的详细配置信息` | `:3628,3631` |
| `members` | `成员管理` / `邀请伙伴加入当前空间并分配角色。只有 Owner 可以新增或移除成员。` | `:239-240` |
| `chathistory` | `消息管理` / `配置聊天历史知识库，将对话消息自动向量化索引，实现语义搜索` | `:5495-5496` |
| `memory` | `长期记忆` / `让助手跨会话记住成员说过的个人信息、偏好、事实与在办事项。` | `:5458-5459` |
| `models` | `模型配置` / `管理不同类型的 AI 模型，支持 Ollama 本地模型和远程 API` | `:2348-2349` |
| `ollama` | `Ollama 配置` / `管理本地 Ollama 服务，查看和下载模型` | `:2307-2308` |
| `weknoracloud` | `WeKnora Cloud` / `配置 WeKnora Cloud 的 APPID 和 APPSECRET 凭证。凭证用于模型服务和文档解析引擎。` | `:6240-6241` |
| `vectorstore` | `向量数据库引擎` / `注册和管理用于知识库搜索的向量数据库实例。` | `:5512-5513` |
| `parser` | `解析引擎` / `文档解析引擎状态及配置。此处设置优先于服务端环境变量，留空则使用环境变量默认值。` | `:6190-6191` |
| `storage` | `存储引擎` / `管理文件与图片使用的存储实例；同一种类型可以配置多个实例。` | `:6073,6147` |
| `sandbox` | `沙箱配置` / `配置智能体运行技能脚本的隔离环境。每个智能体选择一份配置。` | `:5593-5594` |
| `skills` | `技能管理` / `技能属于空间目录，可以只登记，也可以装到一份或多份沙箱。智能体只能启用当前沙箱里已就绪的技能。` | `:6002-6003` |
| `websearch` | `网络搜索配置` / `配置网络搜索功能，在回答问题时可以从互联网获取实时信息补充知识库内容` | `:5547-5548` |
| `mcp` | `MCP 服务管理` / `管理外部 MCP (Model Context Protocol) 服务，在 Agent 模式下调用外部工具和资源` | `:2494-2495` |
| `system` | `系统信息` / `查看系统版本信息和用户账户配置` | `:3064-3065` |
| `system-global` | `系统设置` / `平台级运行时配置，保存后立即对所有空间生效。仅系统管理员可见可改。` | `:3100-3101` |
| `runtime-queues` | `任务队列运行时` / `后台任务队列的实时负载，以及各独立 worker 池的每实例并发配置。支持查看任务明细和安全管理，每 5 秒自动刷新。` | `:3377-3378` |
| `platform-api-keys` | `平台 API Key` / `平台 API Key 默认可选择任意空间。请只授予必要能力；密钥明文仅在创建时显示一次。` | `:120,122` |
| `system-audit-log` | `审计日志`（键 `system.globalSettings.audit.tabLabel`） | `:3115` |
| `retrieval` | `搜索设置` / `配置知识库搜索和消息搜索的全局检索参数` | `:5252-5253` |

`retrieval` 特殊：**不是**左侧 nav 项，而是命令面板右上角齿轮抽屉里渲染（`GlobalCommandPalette.vue:154-157`，
`<t-drawer ... :header="t('retrievalSettings.title')" size="420px">`），让"检索参数"贴着搜索。

### 5.4 表单形态（分组 / 保存 / 校验）

**(a) 保存方式：设置面基本是"控件即提交"，没有 Save 按钮。**
`views/system/SystemSettings.vue:14-32` 把这条纪律写成了契约（原文）：

```
UI principle: every control auto-persists, no Save button. The commit signal differs by control type so the user isn't surprised by writes while they're still composing:
  - Switch / Select (single-pick)         → @change. Selecting an option IS the commit signal; there's no "in-progress" state.
  - Input / InputNumber                   → @blur (not @change — t-input-number fires @change on every digit).
  - SSRF whitelist (string_list)          → controlled tag-input + per-tag inline popconfirm.
  - System admins                         → tag-input @change with inline popconfirm per delta.
```

局部反例：语言切换是"选完即存 + toast"（`GeneralSettings.vue:235-239`）。
需要显式按钮的是**编辑类抽屉/弹窗**（如 `AgentEmbedChannelPanel` 的保存、`ModelEditorDialog`、`SettingDrawer`）。

**(b) 分组骨架是同一套 CSS 契约**：`.section-header` + `.settings-group` + `.setting-row` / `.setting-info` / `.setting-control`。
出处：`SystemSettings.vue:8-12` 注释（原文：`Visual contract: matches the canonical Settings-modal pane skeleton`），
样式定义在 `components/css/settings-section.less`，各页 `@import (reference)` 后 mixin 化（如 `GeneralSettings.vue:275-301`、`IntegrationSettingsSection.vue:90-107`）。

**(c) 校验与错误**：TDesign `t-form` rules 内联提示（`Login.vue:468-506`）；
"测试连接"是标准动作，按钮文案 `测试连接 / 测试中...`（`zh-CN.ts:6217`、`5559-5560`），
失败有专门文案 `checkFailed: '检测失败'`（`:6223`）；
设置保存类 toast 统一 `已保存 / 保存失败`（`:6224-6225`）。
有未保存守卫的通用弹窗（`common.unsavedChanges`，`zh-CN.ts:5036-5040`）：

```
title: '有未保存的更改'
body: '关闭后当前修改将丢失，确定要关闭吗？'
discard: '放弃更改'
keepEditing: '继续编辑'
```

**(d) 模型页的分类**：`chat / embedding / rerank / vllm / asr` 五个 tab，tab label 带计数
（`ModelSettings.vue:42-45`，`type ModelType = 'chat' | 'embedding' | 'rerank' | 'vllm' | 'asr'`，`:307`）。
供应商 logo 走 `providerLogos.ts` 的 `color/` 多色 SVG 或 `mono/` 单色 mask 染色两档（`:1-10`、`:47-57`）。

**(e) 沙箱页是多步向导**：`stepConnection → stepTemplate → stepRuntime → stepSkills`
（`settings/sandbox.title` 附近，`zh-CN.ts:5599-5602`），并有"技能需要装进这份配置的镜像，先保存配置再回到这一步。"的锁定态（`:5603`）。

---

## 6. §4 组织与权限

### 6.1 概念：这里有两个词，别混

- **tenant（空间）= 账号与数据的隔离单位**。"空间信息"页 = `TenantInfo.vue`，路由 `/platform/settings?section=tenant`。
- **organization（共享空间）= 跨空间协作单位**。菜单项 `共享空间`，页面 `/platform/organizations`。
  它的定位原文（`zh-CN.ts:1861`）：`'创建或加入共享空间，让多个空间互相协作，共享知识库与智能体'`。

### 6.2 共享空间列表页

`views/organization/OrganizationList.vue`。左侧是共享的 `ListSpaceSidebar`（`mode="organization"`，`:3`），
`spaceSelection` 三值 `'all' | 'created' | 'joined'`（`:660`），`'created'` 过滤 `o.is_owner`、`'joined'` 过滤 `!o.is_owner`（`:670-671`）。
列表在 `all` 视图下插小标题把"我创建的/我加入的"分组（`:53-70`）。

空态文案（`zh-CN.ts:1900-1907`，原文）：

```
empty: '您还没有加入任何共享空间'
emptyDesc: '创建一个共享空间或通过邀请码加入现有共享空间'
emptyCreated: '您还没有创建任何共享空间'
emptyCreatedDesc: '点击「创建共享空间」创建一个新的共享空间'
emptyJoined: '您还没有加入任何共享空间'
emptyJoinedDesc: '通过邀请码加入现有共享空间'
```

### 6.3 界面上怎么表达"我能做什么 / 不能做什么"

这是 WeKnora 做得最集中的一块，共 **4 层**：

**第 1 层：菜单项级**。`organizations` 只对 `hasRole('admin')` 可见（`stores/menu.ts:80-82`），
注释解释了为什么连 viewer 都不给（`:70-72`）：

```
// 共享空间 (organizations) 仅对当前空间的 admin / owner 暴露入口。
// viewer / contributor 即便在共享空间里拥有资源，也无需自行管理共享关系，
// 入口在侧栏只会徒增噪音；后端 RBAC 才是权限的最终来源（见 middleware/rbac.go）。
```

**第 2 层：页面按钮级 —— 禁用 + tooltip 说原因**。
`OrganizationList.vue:11-19`：`创建/加入` 按钮 `:disabled="!canManageOrg"`，外面套
`<t-tooltip :content="canManageOrg ? $t('organization.joinOrg') : noPermissionTip">`。
判据 `const canManageOrg = computed(() => authStore.hasRole('admin') || authStore.canAccessAllTenants)`（`:463-464`）。

**第 3 层：设置 section 级 —— 白名单表 + "权限不足"整页兜底**。
白名单在 `config/settingsAccess.ts:10-35`（`SETTINGS_SECTION_MIN_ROLE`），
文件头注释声明它是"唯一真源"（`:3-9`）：
`Keep this as the single frontend source of truth for both the complete Settings navigation and any shortcuts that lead into it. Backend route guards remain authoritative.`

同表把**为什么这么定**写成了注释（`Settings.vue:284-298`，原文摘要）：
`// 以「页面里至少有 1 个有意义的写操作所要求的最低角色」为基准…`
`// - chathistory 页面唯一的「启用消息索引」开关 PUT /tenants/kv/chat-history-config 后端走 g.Admin()。给 viewer/contributor 看到入口、点开开关、保存时 403，体验很差，所以入口本身归 admin。`

兜底 UI（`Settings.vue:69-75` + `:742-768` 样式）：

```
roleDenied.title: '权限不足'
roleDenied.desc: '你当前的角色无权访问此设置项。请联系本空间的管理员获取所需角色。'
```
（`zh-CN.ts:6292-6294`）

**第 4 层：头像菜单的快捷入口用更严的门槛**。
`config/settingsAccess.ts:37-45` 的 `SETTINGS_MANAGEMENT_SHORTCUT_MIN_ROLE`：
`members: 'owner'`、`models: 'admin'`、`skills: 'admin'`（注释：`A management-labelled avatar shortcut has a stricter threshold than the corresponding read-only Settings page.`）。
落地在 `UserMenu.vue:85-98`：`v-if="canManageMembers"` / `canManageModels` / `canManageSkills`，
注释原文（`:85-86`）：`// "管理"类快捷入口只对真正具备写权限的人展示。只读名册和模型列表仍可从「全部设置」进入，避免 viewer 看到名不副实的管理入口。`

### 6.4 角色与权限点

**空间角色（tenant role）**：四值 `owner < admin < contributor < viewer`。

- 枚举与序：`stores/auth.ts:173-181`
  ```ts
  const ROLE_LEVEL: Record<string, number> = { viewer: 10, contributor: 20, admin: 30, owner: 40 }
  const hasRole = (min: 'viewer'|'contributor'|'admin'|'owner') => (ROLE_LEVEL[currentTenantRole.value] ?? 0) >= ROLE_LEVEL[min]
  ```
- 显示名（`zh-CN.ts:330-335`）：`owner: '所有者'`、`admin: '管理员'`、`contributor: '编辑'`、`viewer: '访客'`。
- 图标映射（`composables/useRoleLabel.ts:26-31`）：`owner → secured`、`admin → user-circle`、`contributor → edit`、`viewer → browse`。

**共享空间角色（organization role）**：三值 `admin / editor / viewer`。
Options 与权限矩阵在 `OrganizationSettingsModal.vue:938-940`、`:1029-1031`、`:1059-1077`。
显示名（`zh-CN.ts:2061-2065`）：`admin: '管理员'`、`editor: '编辑'`、`viewer: '只读'`。
权限说明表（"权限说明"页签）文案原文（`zh-CN.ts:1970-1988`）：

```
permissionsTitle: '成员权限'
permissionsDesc: '了解共享空间中不同角色对知识库与智能体的权限范围'
permissionFeature: '权限功能'
fullAccess: '完整权限'   editAccess: '编辑权限'   viewAccess: '只读权限'
adminPerm1: '管理共享空间设置、成员及知识库与智能体共享'
adminPerm2: '共享和管理知识库与智能体'
adminPerm3: '编辑共享知识库内容'
adminPerm4: '查看和检索知识库'
useSharedAgentsPerm: '使用共享智能体'
shareKBPerm: '共享知识库到共享空间'
ownerNote: '作为共享空间创建者，您将自动成为共享空间管理员，拥有完整权限。'
```

**系统管理员（platform-wide）**：与空间角色**正交**。`stores/auth.ts:109-123` 注释原文：
`It is independent of per-tenant Owner/Admin/Contributor/Viewer roles — a system admin can manage global settings, built-in models, and other system admins regardless of which tenant they're currently scoped into.`
它的 4 个页面由 `SYSTEM_ADMIN_SETTINGS_SECTIONS = new Set(['system-global','runtime-queues','platform-api-keys','system-audit-log'])`（`settingsAccess.ts:47-52`）挂载，
路由 meta `requiresSystemAdmin` 再拦一次（`router/index.ts:422-427` + `:193-215`）。

**跨空间超级用户（superuser）**：`canAccessAllTenants`（`user.can_access_all_tenants`，`stores/auth.ts:105-107`），
它 bypass 所有 `hasRole` 门槛（`Settings.vue:335-338` 注释：
`// canAccessAllTenants（superuser）和路由层一样必须 bypass，否则 cross-tenant 管理员看不到自己有权操作的入口`），
并且在非成员的 tenant 里被后端临时授予 `'admin'`（**永不给 owner**）——前端镜像了这个规则（`stores/auth.ts:153-161`，注释原文：
`Never surface Owner — the backend caps the temporary grant at Admin too (Owner-only ops like tenant deletion stay reserved for a real Owner inside the target tenant).`）。

**一个必须记住的安全纪律**（`stores/auth.ts:137-142`，原文）：

```
SECURITY: This value is read from localStorage (`weknora_memberships`) and therefore MUST be treated as UI-rendering-only — any user can tamper with localStorage and grant themselves "owner" here. All real authorisation decisions live on the server (auth middleware resolves the role from tenant_members on every request). Never branch security-sensitive logic on this value alone.
```

### 6.5 邀请

四条路径并存：

1. **空间邀请（站内）**：给已注册邮箱发邀请，对方在"我的邀请"里接受/拒绝。
   文案 `zh-CN.ts:169-200`（`tenantInvitation`）：`inboxTooltip: '查看待接受的邀请'`、
   `pendingSectionDesc: '发出后等待对方在站内确认。{days} 天未响应将自动过期。'`、
   `confirmInviteBody: '将向 {email} 发出加入邀请（角色：{role}）。TA 在站内接受后才会成为成员。'`、
   `myInbox: { title: '我的邀请', acceptButton: '接受', declineButton: '拒绝', acceptSuccess: '已加入 "{tenant}"。' }`。
2. **邀请链接**：`复制邀请链接`（`zh-CN.ts:179`）。`/join?code=` 与 `?invite_code=` 双收（`router/index.ts:77-89`）。
3. **注册邀请 token**：`/register?token=`，绕过 `invite_only` 门（`Login.vue:425-434`）。
4. **共享空间邀请码**：`邀请码` + `刷新邀请码`（`zh-CN.ts:1875-1880`），有效期 1/7/30 天/永不过期（`:2023-2028`、`OrganizationSettingsModal.vue:1248-1251`）。

铃铛：`components/GlobalInvitationBell.vue` 只在 `pendingInvitationCount > 0` 时渲染（`:8`），
位置 `fixed; top:12px; right:16px; z-index:100`（`:36-43`，注释解释了为何要低于 TDesign 抽屉的 2500）。

**加入申请（审批流）**：共享空间可开 `需要审核`（`zh-CN.ts:2037-2038`）、
`开放可被搜索`（`:2039-2040`，开启后他人在"加入共享空间"搜索列表里申请，无需邀请码）、
`成员数量上限`（`:2041-2044`，`0 表示不限制`）。
审批页签文案：`加入申请` / `审核待加入共享空间的申请` / `暂无待审核的申请`（`:2045-2047`）。
菜单项上有待审徽标（`menu.vue:93-96`，title `organization.settings.pendingJoinRequestsBadge: '有待审批的加入申请'`）。

**角色升级申请**（向管理员申请更高角色）：`organization.upgrade`（`zh-CN.ts:1949-1961`）：
`requestUpgrade: '申请升级'`、`pending: '审核中'`、`dialogDesc: '管理员审核通过后更新您的角色。'`、
`reason: '申请理由（选填）'`、`submitSuccess: '权限升级申请已提交，等待管理员审核'`。
申请列表区分 `typeJoin: '加入'` / `typeUpgrade: '升级'`（`:2082-2083`）。
> 注意：这里的 "升级" 是**空间内角色**升级，与商业版本升级无关。

### 6.6 成员管理

`views/settings/TenantMembers.vue`（86KB）。页头描述原文（`zh-CN.ts:240`）：
`'邀请伙伴加入当前空间并分配角色。只有 Owner 可以新增或移除成员。'`
表格列 `member/role/joinedAt/operations`（`:336-340`）。
关键错误文案（`:329-335`）：

```
lastOwner: '无法降级、移除或退出最后一位 Owner，请先把其他成员提升为 Owner。'
userNotFound: '该邮箱尚未注册，请先邀请对方注册账号。'
invalidRole: '角色必须是 owner / admin / contributor / viewer 之一。'
```

它还有一个内嵌的**空间级审计日志**页签（`tenantMember.audit`，`zh-CN.ts:246-286`），
列 `time/actor/action/target/path/outcome`，结果只有 `success: '成功'` / `denied: '拒绝'`，
事件词汇表（`:280-285`）：`rbac.member_added → '新增成员'`、`rbac.member_removed → '移除成员'`、
`rbac.member_role_changed → '角色变更'`、`rbac.member_left → '成员退出'`、`rbac.access_denied → '访问被拒'`、
`rbac.invitation_sent/accepted/declined/revoked/expired → '发出邀请/接受邀请/拒绝邀请/撤销邀请/邀请过期'`。

### 6.7 空间切换

`components/TenantSelector.vue` 与 `UserMenu.vue` 的浮层双入口。
浮层标题 `tenant.switcher.menuLabel: '切换空间'`，当前行有 `currentBadge: '当前'`，
home 空间在头像角上打 home 点、tooltip `homeTooltip: '我的空间'`，
只有一条成员关系时显示 `empty: '你目前只属于这一个空间'`（`zh-CN.ts` tenant.switcher 段；见 `UserMenu.vue:149-195`）。
浮层底部 "创建空间" 入口受 `authStore.canCreateTenant` 控制（`UserMenu.vue:190-194`）。
"home tenant" 的定义与陷阱写在 `composables/useRoleLabel.ts:37-53`：
必须读 `user.tenant_id` 而不是 `authStore.tenant?.id`（后者是 *active* tenant）。

---

## 7. §5 Agent 与集成

### 7.1 Agent 是什么

列表页页头（`zh-CN.ts:6334-6336`）：`title: '智能体'`、`subtitle: '配置和管理您的智能体，自定义对话行为和能力'`、`createAgent: '创建智能体'`。
创建按钮门槛是 `contributor`（`AgentList.vue:11` 的 `v-if="authStore.hasRole('contributor')"`）。

列表分成 7 个 section（`agent.sections`，`zh-CN.ts:6546-6554`）：
`builtin: '内置'`、`mine: '我创建的'`、`tenantOthers: '本空间 · 其他成员'`、`tenantReadonly: '本空间 · 仅查看'`、
`sharedByMe: '我共享的'`、`sharedEditable: '共享给我 · 可编辑'`、`sharedReadonly: '共享给我 · 仅查看'`。
卡片上直接打能力徽标：`agent.mode.agent / agent.mode.normal`（`AgentList.vue:255`）、
`features.webSearch: '支持网络搜索'`、`features.knowledgeBase: '关联知识库'`、`features.mcp: '支持MCP服务'`、`features.multiTurn`（`:263-286`，文案 `zh-CN.ts:6558-6563`）。
空态（`zh-CN.ts:6536-6544`）：`empty.title: '暂无自定义智能体'` / `empty.description: '点击右上角按钮创建您的第一个智能体'`。

### 7.2 Agent 编辑器

`views/agent/AgentEditorModal.vue`（254KB，6546 行）——**和设置共用同一个全屏弹窗壳**（§5.1）。

`navItems`（`AgentEditorModal.vue:2684-2711`）是**动态的**：能力未满足就不出现该页签。

| key | label key / 原文 | 出现条件 | 出处 |
|---|---|---|---|
| `basic` | `agent.editor.basicInfo` = `基本信息` | 恒有 | `:2686` |
| `prompts` | `agent.editor.promptsConfig` = `提示词` | 恒有；badge = 提示词条目数（>1 时） | `:2687` |
| `model` | `agent.editor.modelConfig` = `模型配置` | 恒有 | `:2688` |
| `suggestions` | `agentEditor.questionSuggestions.navLabel` | 恒有 | `:2689` |
| `conversation` | `agent.editor.conversationSettings` = `多轮对话` | 恒有 | `:2692` |
| `knowledge` | `agent.editor.knowledgeConfig` = `知识库` | 恒有 | `:2694` |
| `retrieval` | `agent.editor.retrievalStrategy` = `检索策略` | `hasKnowledgeBase` | `:2695-2697` |
| `websearch` | `agent.editor.webSearchConfig` = `网络搜索` | 恒有 | `:2698` |
| `multimodal` | `agentEditor.imageUpload.navLabel` = `附件上传` | 恒有 | `:2699` |
| `tools` | `agent.editor.toolsConfig` = `工具配置` | `isAgentMode` | `:2701-2702` |
| `mcp` | `agentEditor.mcp.label` | `isAgentMode` | `:2703` |
| `skills` | `agent.editor.skillsConfig` = `技能` | `isAgentMode` | `:2704` |
| `share` | `knowledgeEditor.sidebar.share` | 编辑模式 && 有 id && 非内置 && 非 Lite | `:2706-2709` |

分组（`AgentEditorModal.vue:2713-2740`）+ 组标题（`zh-CN.ts:1473-1478`）：
`基础 / 知识检索 / 能力扩展 / 发布集成`。
即：`basic, prompts, model, conversation, suggestions` → 基础；
`knowledge, retrieval, websearch` → 知识检索；
`multimodal, tools, mcp, skills` → 能力扩展；
`share` → 发布集成。

**运行模式是二选一**：`agent_mode: 'quick-answer' | 'smart-reasoning'`（`AgentEditorModal.vue:2749`）。
文案（`zh-CN.ts:6400-6401`）：`normalDesc: '快速响应，直接回答问题'`、`agentDesc: '多步思考，深度分析复杂问题'`。
Agent 模式下与普通模式**不是同一套表单**：
- 系统提示词在 Agent 模式下"定义角色和工作要求，工具权限与本轮来源选择由系统单独控制"（`zh-CN.ts:1361` 的 `promptInheritance`）。
- 提示词子导航也不同（`AgentEditorModal.vue:2969-3011`）：普通模式有
  `系统 / 上下文 / 意图 / 改写系统 / 改写用户 / 兜底`；Agent 模式只有 `系统`。
  这由 `if (!isAgentMode.value)` 控制（`:2978`）。
- 多轮对话：Agent 模式**强制多轮**（`zh-CN.ts:1408` 的 `conversationSectionAgent`：
  `'智能推理始终为多轮模式：按模型上下文窗口保留历史对话，超出时自动把较早的内容压缩成摘要。'`）。

**默认配置值**（`AgentEditorModal.vue:2743-2769`，可作为"一个 Agent 最少要配什么"的清单）：
`system_prompt`、`context_template`、`model_id`、`rerank_model_id`、`temperature: 0.7`、
`max_completion_tokens: 0`、`thinking: false`、`citation_enabled: true`、
`max_iterations: 10`、`llm_call_timeout: 120`、`allowed_tools: []`、`reflection_enabled: false`、
`mcp_selection_mode: 'none' | 'all' | 'selected'`、`mcp_services`、`mcp_auth_wait_timeout: 600`。

**知识库选择是三态**（`zh-CN.ts:6432-6440`）：
`allKnowledgeBases: '全部知识库'` / `selectedKnowledgeBases: '指定知识库'` / `noKnowledgeBase: '不使用知识库'`，
列表再分 `myKnowledgeBases: '我的知识库'` / `sharedKnowledgeBases: '协作知识库'`（`AgentEditorModal.vue:1480,1496`）。
还有个很实用的开关 `retrieveKBOnlyWhenMentioned: '仅在 @ 提及时检索'`（`zh-CN.ts:6440`）。

### 7.3 Agent 的工具

工具注册表在 `AgentEditorModal.vue:2407-2434`，按 6 组渲染（`:2436-2442`）。
组名（`zh-CN.ts:1355-1360`）：`基础 / 知识库检索（RAG）/ Wiki 读取 / Wiki 编辑 / Wiki 巡检 / 数据分析`。

分组与工具（`value` 即后端工具名，label 原文照抄）：

| 组 | 工具（value → label） |
|---|---|
| `base` | `thinking → 思考`、`todo_write → 计划管理` |
| `rag` | `search_knowledge → 知识库检索`、`read_document → 阅读文档`、`list_documents → 浏览文档列表`、`query_knowledge_graph → 知识图谱查询`、`database_query → 数据库查询` |
| `wiki_read` | `wiki_search → 搜索 Wiki`、`wiki_read_page → 阅读 Wiki 页面`、`wiki_flag_issue → 标记 Wiki 问题` |
| `wiki_edit`（`danger: true`） | `wiki_write_page → 创建/覆盖 Wiki`、`wiki_replace_text → 局部替换 Wiki`、`wiki_rename_page → 重命名 Wiki`、`wiki_delete_page → 删除 Wiki` |
| `wiki_issue` | `wiki_read_issue → 查看 Wiki 问题`、`wiki_update_issue → 更新 Wiki 问题` |
| `data` | `data_analysis → 数据分析`、`data_schema → 数据结构` |

三个设计点值得记：

1. **写类工具单独打标**：`writeWarning: '会修改 Wiki 内容'`、`dangerTag: '可写'`（`zh-CN.ts:1361-1362`）。
2. **不可用的工具不是隐藏而是灰显 + 说缺什么**：`availableTools` 用 `evaluateToolRequirement` 算出
   `disabled` / `disabledReason`（`AgentEditorModal.vue:2532-2543`），原因文案
   `requiresKb: '（需要关联启用向量/关键词索引的知识库）'`、`requiresWikiKb: '（需要关联启用 Wiki 能力的知识库）'`、`requiresRagKb`（`zh-CN.ts:1352-1354`）。
3. **"最终启用的工具"预览区**：根据当前配置算出保存后真正能调用的集合
   （`AgentEditorModal.vue:2561-2581`；文案 `zh-CN.ts:1366-1368`：
   `effectiveLabel: '最终启用的工具'`、`effectiveDesc: '根据当前配置计算，这是智能体保存后实际能调用的工具集合'`、
   `effectiveEmpty: '当前没有可用工具，智能体将退化为纯模型问答'`）。
   而 `allowed_tools` 被明确定义为"用户意图"：注释原文
   `// 从"有"变"无"：**不再**自动擦工具，依赖不满足时由 availableTools 灰显 + 运行时工具注册器过滤。allowed_tools 代表用户意图，只应在用户显式操作`（`:3801-3802`）。

MCP 与 Skills 是另外两个页签：MCP 有 OAuth 授权等待与超时（`chat/components/McpOAuthCard.vue`、`McpToolResult.vue`，
文案 `zh-CN.ts:1654-1671`），Skills 必须先选"运行沙箱"才能勾（`zh-CN.ts:6466`，
`skillsConfigDesc: '先选择运行沙箱，再从下面列表选用技能。没装到该沙箱的会显示「安装」，装好后才能勾选。'`）。

### 7.4 Agent 发布：分享设置 / 网页嵌入 / IM

**(a) 共享范围说明** `agent.shareScope`（`zh-CN.ts:6512` 起）——一段罕见的坦白文案，值得整段抄：

```
desc: '空间成员以只读方式使用该智能体，将遵循您当前配置的能力与资源；您对智能体的修改会同步给已共享的空间。如需允许空间成员编辑知识库内容，请将知识库共享到空间。'
skillSecretsWarning: '该智能体启用了技能：空间成员使用时，技能会在本空间的沙箱中运行，并带上管理员为技能配置的环境变量（如 API Key），成员可以让智能体读出这些值。请在可以接受这一点时再共享。'
```

**(b) 网页嵌入渠道** `components/AgentEmbedChannelPanel.vue`（52KB）——**6 步向导**：
`stepChannel / stepSecurity / stepCapabilities / stepAppearance / stepWebhook / stepDeploy`（`:603-609`，编辑态才追加最后一步）。

配置项与文案（`zh-CN.ts` 的 `embedPublish` 段，起点 `:4655`；下列行号已逐条核过）：
`name`（后台管理用）、`allowedOrigins: '域名白名单'`（`:4660`；提示原文 `:4689`：
`'填写允许嵌入的宿主网站来源（A），不是 WeKnora 地址（B）。每行一个完整 Origin，如 https://shop.example.com；至少一项，支持 *.example.com 子域通配'`）、
`rateLimitLabel: '每分钟请求上限'`（`:4694`，描述默认 30）、
`rateLimitDayLabel: '每日请求总上限'`（`:4696`，描述默认 10000，`:4697`）、
`welcomeMessage: '欢迎语'`（`:4684`，描述 `:4686`）、`showSuggestedQuestions: '推荐问题'`（`:4687`）、
`allowWebSearch`（`:4742`）/ `allowFileUpload`（`:4744`，默认 false，`AgentEmbedChannelPanel.vue:513`）、
`primaryColor: '主题色'`（`:4699`）、`pageTitle: '页面标题'`（`:4700`）、
`headerTitleMode: '顶栏标题'`（`:4703`，两值 `headerTitleModeChannel: '固定渠道标题'` / `headerTitleModeSession: '跟随会话标题'`，`:4704-4705`）、
`widgetPosition: '浮窗位置'`（`:4723`，四角 `positionBottomRight` 起 `:4725-4728`）、`defaultLocale`（`:4778`）、webhook url/secret。

安全模型写得非常直白（`zh-CN.ts:4698` 的 `publishTokenWarning`，原文）：

```
发布 Token 会以明文出现在嵌入页面源码中，任何访问该网站的人都能看到，请将其视为「可公开密钥」而非机密：切勿把含敏感数据的智能体做成嵌入渠道；务必配置域名白名单与请求上限；Token 泄露时可随时「重置 Token」作废旧值。
```

三档部署形态（tab）：`tabIframe: 'iframe'`（`:4720`）/ `tabWidget: '浮窗'`（`:4721`）/ `tabSecure: '安全模式'`（`:4722`）。
向导步骤标签 `stepChannel / stepSecurity / stepCapabilities / stepAppearance / stepWebhook / stepDeploy`（`AgentEmbedChannelPanel.vue:603-609`，`:4758` 起）。
代码片段生成在 `api/embed/index.ts:601-651`（这正是"抄得动的部分"）：

```ts
// iframe：token 挂在 URL 里
`<iframe src="${url}" style="width:400px;height:600px;border:none;border-radius:12px" allow="clipboard-write"></iframe>`
// 浮窗：宿主页面放一个 script，token 走 data-token
`<script src="${base}/weknora-widget.js" data-channel="…" data-token="…" data-position="…"></script>`
// 安全模式：token 不落浏览器，改指向调用方后端的换票端点
data-token-endpoint="https://your-backend.example.com/weknora/embed-token"
```

同时给 Node/Go 两种换票服务端样例（`AgentEmbedChannelPanel.vue:334-335`、`:1038-1040`）。

**(c) 嵌入运行时是独立入口，不是本 SPA**。
`router/index.ts:59` 注释原文：`// Embed chat is a separate entry (embed.html + embed-main.ts), not this SPA.`
`src/embed-main.ts` 只注册一条路由 `path: '/embed/:channelId'`（`:17-22`），
用 runtime-only 渲染函数挂载（`:25-26`，注释：`Runtime-only Vue build cannot compile string templates — use a render fn.`）。
宿主通信：`postMessage` 四类事件（`api/embed/index.ts:498-545`：
`ready` / `bootstrap_request` / `message_sent` / `message_received`），
父窗口 origin 采用 **trust-on-first-use** 策略（`:442-448`、`:480-494`）。
URL 参数至少支持 `?token=`（`composables/useEmbedBridge.ts:230`）与 `?locale=`（`i18n/embed.ts:2080-2082`）。
安全模式不再把 publish token 给浏览器，而是先换短期 session token，并且
**生产环境不允许回落到 publish token**（`useEmbedBridge.ts:126-137`，注释：
`In production we refuse to downgrade to the publish token; only the dev build keeps the convenience fallback for local testing.`）。

**(d) IM 渠道** `components/IMChannelPanel.vue`——**9 个平台**
（`IMChannelPanel.vue:665-673`）：企业微信 `wecom`、飞书 `feishu`、Lark `lark`、Slack、Telegram、
钉钉 `dingtalk`、Mattermost、微信 `wechat`、QQ 机器人 `qqbot`。
接入模式二选一 `WebSocket` / `webhook`（`:157-167`），其中 `dingtalk`/`qqbot` 仅 `websocket`（`:791`）、`mattermost` 仅 webhook。
微信是**扫码绑定 + 轮询状态**（`:547-573`、`:853-918`，状态 `wait / scaned / expired`）。

### 7.5 集成总表与四个落地页

注册表在 `config/integrations.ts:8-42`：

```ts
export type IntegrationTab = 'im' | 'embed' | 'api' | 'mcpserver' | 'cli' | 'chrome' | 'claw'
```
`INTEGRATION_PREVIEW_ITEMS`（`:31-42`）给每组一个 icon/emoji（`claw` 用 🦞）。
角色门槛只有一条（`:15-17`）：`INTEGRATION_TAB_MIN_ROLE = { api: 'owner' }`，
注释原文（`:12`）：`Aligns with Settings.vue SECTION_MIN_ROLE.api and router.go g.Owner() on /api-principal-config.`
能力位映射（`:19-24`）：`im / embed / api / mcpserver` 四个有键，`cli / chrome / claw` **没有**能力位（永远可见）。

页面分发在 `views/integrations/IntegrationSettingsSection.vue:4-49`：

| tab | 组件 | 一句话 |
|---|---|---|
| `im` | `components/IMChannelPanel.vue` | 9 平台 IM 渠道 |
| `embed` | `components/AgentEmbedChannelPanel.vue` | 网页嵌入渠道（6 步向导） |
| `api` | `views/integrations/ApiIntegrationSettings.vue`（84KB） | API Key + 终端用户身份模式 + Playground |
| `mcpserver` | `views/integrations/McpServerIntegrationSettings.vue` | 把空间发布为 MCP Server |
| `cli` | `CliIntegrationLanding.vue` | CLI 落地页 |
| `chrome` | `ChromeExtensionLanding.vue` | Chrome 插件落地页 |
| `claw` | `ClawSkillLanding.vue` | ClawHub Skill 落地页 |

`cli/chrome/claw` 三个是**纯落地页**（`isLandingSection`，`:74-76`，并把内容宽度收到 760px，`:101-103`），
统一外壳 `IntegrationLandingLayout.vue` + `IntegrationExternalCta.vue`（外链 CTA）。
它们的文案本身就是"这个集成怎么用"的说明书，原文摘（`zh-CN.ts`）：

- CLI（`:381-403`）：`subtitle: '在终端中管理知识库和文档、检索内容并发起问答，也可通过脚本或 MCP 接入 AI 工具。'`，
  有 `快速开始` 四段 `安装 CLI / 连接当前服务 / 验证连接 / 常用命令` + `接入 MCP 客户端`。
- Chrome（`:455-...`）：`title: '知识管理助手'`，
  `subtitle: '配合 WeKnora 自建服务使用：在任意网页侧边栏提问、剪藏内容、Markdown 速记，将浏览中的知识沉淀到你的知识库。'`，
  四步 `获取 API 凭证 / 安装 Chrome 插件 / 在插件中完成连接 / 桌面版配置固定端口（推荐）`。
  注意它的连接说明：`'打开插件设置，选择「企业/开发者」模式，填入服务 API 地址与 API Key。'`（`zh-CN.ts:475`）——
  这是全仓唯一出现"企业"字样的地方，指的是**插件自身的模式名**，不是 WeKnora 的商业版本。
- ClawHub Skill（`:407-453`）：`subtitle: '通过 WeKnora REST API 导入文档并执行混合检索（向量 + 关键词）。'`，
  5 项能力 `浏览知识库 / 混合检索 / 写入 Markdown / 导入网页 / 上传文件`，
  外链常量 `CLAWHUB_SKILL_URL = 'https://clawhub.ai/lyingbug/weknora'`（`config/integrations.ts:6`）。

### 7.6 API 集成页（权限模型最细的一块）

**(a) API Key 的能力位是 18 + 7 个**（`config/apiKeyCapabilities.ts:15-28`）：

```ts
TENANT: ['retrieve','chat','read_agents','ingest','manage_kbs','message_history','manage_agents',
         'manage_mcp_services','manage_datasources','manage_models','manage_vector_stores',
         'manage_storage_backends','manage_web_search','manage_channels','run_evaluations',
         'manage_members','manage_spaces','manage_tenant_settings']
SYSTEM: ['system_tenants_read','system_tenants_manage','system_settings_read','system_settings_manage',
         'system_runtime_read','system_runtime_manage','system_audit_read']
```
默认集 `DEFAULT_TENANT_API_KEY_CAPABILITIES = {retrieve, chat, read_agents}`（`:30-32`）。
分组展示为 4 组：`知识库数据 / 智能体与集成 / 成员与空间 / 空间配置`（`zh-CN.ts:533-536`）。
每条能力都有 label + **一句 hint 说明边界**，且 hint 写法很讲究（节选原文，`zh-CN.ts:537-580`）：

```
capabilityRetrieveHint: '允许读取、查询和检索所选知识库范围内的数据；不创建会话，也不修改内容。'
capabilityChatHint: '允许该密钥发起对话并管理自己的会话；不修改知识库内容。'
capabilityIngestHint: '允许向授权范围内的知识库写入内容（上传文档、编辑分块/FAQ/标签/wiki）；不能新建知识库、不能新建智能体、不能清空知识库，且仅限所选知识库范围。'
capabilityManageKbsHint: '允许管理知识库全生命周期…针对已有知识库的操作（复制/更新/删除）仍受所选知识库范围限制；新建不受限（新知识库归本空间）。'
capabilityManageAgentsHint: '允许创建、修改、删除、复制智能体。智能体配置可能含模型/MCP 等敏感绑定，默认关闭，按需开启。'
capabilityTenantFull: '空间完全访问'
capabilityTenantFullHint: '允许调用模型、向量库、数据源、渠道等全部空间级接口；知识库范围不再生效。'
```

**(b) 终端用户身份模式（`principalMode`）三选一**（`zh-CN.ts:592-610`）：
`modeTenant: '仅空间'` / `modeDirect: '直接传用户 ID'` / `modeSigned: '签名 Token'`。
风险提示写得比多数产品都诚实：

```
directWarning: '直接传用户 ID 会信任调用方请求头，仅适用于可信服务端到服务端调用。'
directWarningDetail: '任何持有 API Key 的调用方都可以通过修改用户 ID 请求头冒充其他外部用户，从而共用或劫持其 MCP OAuth 授权。请勿用于浏览器或不可信客户端；面向终端用户请使用「签名 Token」。'
signedRecommended: '推荐给面向用户的应用：由你的业务后端为外部用户签发短期 HS256 JWT。'
signedFlowDetail: 'HMAC 密钥仅保存在 WeKnora 与你的可信后端，切勿放入请求或下发给浏览器。请求头里传的是用该密钥签出的 JWT 字符串（每次签发或过期后会变），不是密钥本身。JWT 须包含 sub（外部用户 ID）、tenant_id、aud=weknora、exp（有效期不超过 24 小时）。'
hmacSecretResetConfirmBody: '重置后，旧的 HMAC 密钥会立即失效，所有使用旧密钥签发 JWT 的后端服务必须更换为新密钥才可继续通过签名 Token 调用。此操作不可撤销。'
```

**(c) API Playground**：右侧抽屉，输入 `Agent + 外部用户 ID + 问题`，
先展示**请求预览**（密钥打码成 `<JWT>`），再执行 `创建会话 → Agent 对话（SSE）` 两步并分步展示状态
（`ApiIntegrationSettings.vue:326-458`；`buildPlaygroundHeaders(maskSecrets)` 在 `:1583-1593`；
SSE 消费在 `views/integrations/apiPlaygroundSSE.ts`）。
入口文案（`zh-CN.ts`）：`playgroundTitle: 'API Playground'`。

### 7.7 MCP Server 页（把空间"反向"发布出去）

`McpServerIntegrationSettings.vue`（27KB）。定位原文（`zh-CN.ts:684`）：
`subtitle: '把当前空间发布为 MCP 服务，供 Claude Desktop、Cursor、Claude Code 等 MCP 客户端直接连接。每个端点有独立的令牌、知识库范围和工具清单。'`

端点（endpoint）配置：`基本信息 → 知识库范围 → 暴露的工具 → 问答设置 → 限流 → 连接信息`（`:698-720`）。
工具清单按 4 组（`:707-712`）：`检索与阅读 / 问答 / Wiki / 写入（谨慎开启）`，
共 13 个工具（`:713-740`）：`list_knowledge_bases / search_knowledge / grep_chunks / list_documents / read_document / ask / wiki_search / wiki_read_page / wiki_index / add_document / update_document / delete_document`。
两条纪律原文：

```
toolsHint: '只有勾选的工具会出现在客户端的工具列表中，未勾选的工具即使按名字调用也会被拒绝。写入类工具默认关闭。'
toolsRequired: '至少勾选一个工具'
tokenOnce: '令牌只展示这一次，关闭后无法再次查看。请立即复制并妥善保存。'
```

**令牌只展示一次**，忘了只能轮换；连接信息里给出各客户端配置片段（`:735-740`）。

---

## 8. §6 平台 / 系统 / 开发者页

### 8.1 关键事实：这些不是独立页面

`router/index.ts:189-192` 注释原文：

```
Compatibility redirects for /platform/system/* URLs. System administration surfaces live as dedicated sections inside the standard Settings modal; keep stable URLs for bookmarks and external links.
```

四条旧 URL 全部 302 进设置弹窗（`router/index.ts:193-215`）：

| 旧 URL | 落到 | 组件 |
|---|---|---|
| `/platform/system` | `?section=system-global` | `views/system/SystemSettings.vue` |
| `/platform/system/settings` | 同上 | 同上 |
| `/platform/system/admins` | 同上（管理员管理内嵌在该页"访问控制"tab 顶部，`SystemSettings.vue:92-101`） | 同上 |
| `/platform/system/queues` | `?section=runtime-queues` | `views/system/RuntimeQueues.vue` |

多一层保护：`requiresSystemAdmin: true`（`:196,202,208,214`），
且守卫把它放在**认证之后**（`router/index.ts:418-427` 注释原文：
`SystemAdmin gate — checked AFTER auth so a non-admin who's logged out gets redirected to /login first (consistent with how the rest of the auth flow works), and only an authenticated non-admin sees the bounce. This is UI-only; the server enforces the real check.`）。

### 8.2 系统设置（`SystemSettings.vue`）

`settings` 列表来自后端 `/system/settings`（`api/system/index.ts:470-508` 有 list/get/update/reset 四个）。
页面按 `section` 分 5 个 tab（`SystemSettings.vue:69-75`）：
`access / tenant / runtime / security / other`（`other` 仅在出现未知 key 时显示，`:74`）。
`runtime` tab 有 `需重启` 标签（`:81-83`，文案 `system.globalSettings.sections.runtime.restartHint`）。

页头有一个**优先级披露**弹窗（`:38-52`），三条 `tier1/2/3`（`system.globalSettings.priorityHint.*`），
配合值上的 `badgeOverride: '已覆盖'` 与 tooltip
`badgeOverrideTooltip: '该值已由管理员保存到数据库，覆盖了环境变量与默认值'`（`zh-CN.ts:3110-3111`），
以及 `badgeRequiresRestart: '需重启'` / `badgeSecret: '敏感'` / `badgeHighRisk: '高风险'`（`:3107-3109`）。
也就是说：**"数据库 > 环境变量 > 默认值"这条覆盖链是显式画给用户看的**。

页内嵌了三个高危操作（都是"标签输入 + 就地 popconfirm"）：
系统管理员名单（`admins`，`:102-130`，当前用户被排除在可见 tag 之外，理由见 `:97-101` 注释）、
批量把某值应用到所有现有空间（`bulkApply`，`zh-CN.ts:3150-3156`）、
重置他人密码（`passwordReset`，`:3158-3172`）与创建用户（`createUser`，`:3173-...`）。
创建用户/重置密码的警告文案（`:3161`、`:3175`）：

```
passwordReset.warning: '这是高风险操作。请核对用户邮箱；出于安全考虑，不能在这里重置自己的密码。'
createUser.warning: '这是高风险操作。请仔细核对用户名和邮箱——它们将作为该用户登录的唯一凭据。'
```

### 8.3 任务队列运行时（`RuntimeQueues.vue`，60KB）——最像"运维台"的一页

页面结构（`:1-200`）：

1. **页头**：标题 + `自动刷新（每 5 秒）` 开关（`:9-17`）+ 手动刷新按钮（`:18-30`）。
   描述原文（`zh-CN.ts:3378`）：`'后台任务队列的实时负载，以及各独立 worker 池的每实例并发配置。支持查看任务明细和安全管理，每 5 秒自动刷新。'`
2. **总览 4 个指标**（`:75-98`）：`运行中 / 排队中 / 重试中 / 最终失败`（`summary.*`），
   后两个在 >0 时变 warning/danger 色（`:89`、`:93`）。
3. **Worker 池卡片**（`:100-129`）：主值是 `运行中/容量`，副信息 `单实例配置 / N 个实例 / 利用率 / N 个队列`（`:118-125`）。
   注释原文（`:3379` 页脚）：`'卡片主值为集群运行中/实时容量；单实例配置修改后需重启。共享弹性池只消费核心解析和内容富化队列。'`
4. **队列明细表**（`:131-200+`）：点击某状态的计数下钻到任务列表。
5. **模型并发占用**（`runtime.models`，`zh-CN.ts:3398-3405`）：标题 `'模型并发占用'`（`:3399`），
   描述原文说明它与任务调度的区别：
   `'观察后台任务实际进入模型服务时的并发占用；上方是任务调度，这里是模型服务限流，两者处于不同处理阶段。'`，
   `backgroundOnly: '仅统计后台任务，不包含交互式对话'`（`:3404`），状态 `queued: '限流中'` / `full: '已满载'`。
6. **任务明细**：状态六值（`runtime.tasks.states`，`zh-CN.ts:3479-3485`）：`运行中 / 排队中 / 定时执行 / 重试中 / 最终失败 / 已完成`；
   每个状态配一段**引导语**解释能做什么（`tasks.guides.*`，`zh-CN.ts:3471-3477`，原文节选）：
   ```
   active: '运行中任务可查看执行实例、开始时间和截止时间。只有具备完整业务取消语义的任务才允许终止。'
   pending: '排队任务尚未被 worker 领取。终止操作会同步更新业务状态，而不是只删除 Redis 记录。'
   archived: '请先修复失败原因再立即执行。清除记录不会完成原业务任务。'
   completed: '这里只展示设置了结果保留时间的近期完成任务，不提供管理动作。'
   ```
   三个管理动作各有确认文案，且都写明**副作用边界**（`zh-CN.ts:3451-3458`）：
   ```
   cancelConfirm: '将通过业务取消流程终止该任务及同一文档的相关队列任务。确认终止？'
   runNowConfirm: '该任务将立即进入待执行队列，重试次数不会重置。确认继续？'
   deleteConfirm: '仅从当前队列移除这条失败记录，不会执行或完成原任务，历史日志仍会保留。确认清除？'
   purgeArchivedConfirm: '将从当前队列一次性移除全部 {count} 条失败记录，仅清理队列里的失败任务，不影响运行中或排队中的任务，也不会回滚已失败文档的业务状态。确认清除？'
   ```
   任务还会标 `orphaned: '执行实例已失联，等待恢复'`（`zh-CN.ts:3449`）。
   队列不可用时也把原因说清：`unavailable: '当前部署未启用 Redis / asynq 队列（Lite 模式），无队列可展示。'`（`zh-CN.ts:3384`）。

### 8.4 平台审计日志（`SystemAuditLog.vue`）

描述原文（`zh-CN.ts:3116`）：
`'记录平台级操作：系统设置变更、系统管理员授予/回收、配额批量同步等。按时间倒序展示。'`
列 `time / actor / action / target / path / outcome`（`:3144-3151`），结果 `成功 / 拒绝`（`:3132-3135`）。
事件词汇表 12 条（`:3136-3143`）：

```
system.setting_changed: '系统设置变更'
system.admin_promoted: '授予系统管理员'
system.admin_revoked: '回收系统管理员'
system.user_password_reset: '重置用户密码'
system.user_created: '创建用户'
system.api_key_created: '创建平台 API Key'
system.api_key_revoked: '吊销平台 API Key'
system.queue_task_retried: '重新执行失败任务'
system.queue_task_deleted: '清除失败任务记录'
system.queue_task_run_now: '立即执行队列任务'
system.queue_task_cancelled: '终止队列任务'
system.queue_archived_purged: '清除全部失败任务'
```
`actorRole.system_admin: '系统管理员'`，actor 为系统时显示 `systemActor: '系统'`（`:3130,3152-3154`）。
每条可展开出 `操作人 ID / 目标用户 ID / 目标类型 / 目标 ID / 原始详情`（`:3125-3129`），
且目标类型有专门的可读化（如 `bulkQuotaDiff: '应用到 {count} 个空间（{gb} GB）'`、`:3124`）。

### 8.5 平台 API Key（`PlatformAPIKeys.vue`）

与 §7.6 的租户 API Key **不是一套东西**：这里是 **system 级** 7 个能力位
（`config/apiKeyCapabilities.ts:24-28`）。
表格列：`名称 / API Key / 能力 / 最近使用 / 创建时间 / 操作`（`PlatformAPIKeys.vue:31-39`），
能力列内联只显示前几个 chip，多余的折进 popup（`:49-94`）。
页头一条 warning alert + 创建按钮（`:8-15`）。
> 不确定性：`platformApiKeys.title / description / securityNotice` 的**具体文案我没读到**（该 locale 段在 `zh-CN.ts:119` 起，我只读了键名未逐字核对）；此处不做转述。

### 8.6 开发者页（`views/dev/MarkdownTestPage.vue`）

页面自述（`:3-8`）：`Markdown Rendering Test`，
`Dev-only page for visual regression testing of chat answer markdown (same typography as botmsg / AgentStreamDisplay / embed).`
**仅 DEV 构建注册路由**（`router/index.ts:218-224`）：

```ts
...(import.meta.env.DEV ? [{ path: '/platform/dev/markdown', name: 'markdownTest', component: () => import('../views/dev/MarkdownTestPage.vue'), meta: { requiresAuth: false, requiresInit: false } }] : []),
```
它含 `Basic Text Styles / LaTeX Formulas / Code Blocks / Tables / Lists & Blockquotes` 等分区（`:11-45`）。
生产构建里这个页面**不存在**。这是全仓唯一"开发者页"。

### 8.7 系统信息（`views/settings/SystemInfo.vue`）

不是管理页，是**只读状态页**。字段（`zh-CN.ts:3067-3097`）：
`应用版本(weknora-app) / UI 版本(weknora-ui) / 构建时间 / Go 版本 / 服务启动时间 / 运行时长 / 数据库版本`
+ 三个引擎 `关键词索引引擎 / 向量存储引擎 / 图数据库引擎`。
UI 版本与应用版本不一致时打 `versionMismatch: '与应用版本不一致'` 警告标签（`SystemInfo.vue:58-63`）。
DB 迁移失败是一条独立的红色说明块（`system.dbMigrationFailedTitle/Desc`，`zh-CN.ts:3088-3089`，
原文：`'启动时数据库迁移未成功完成，部分表或索引可能未创建，会导致 Wiki、知识图谱等功能异常。'`）并给排查文档与 Issue 两个出口。
**版本行带 `Lite` / `Standard` 标签**（`SystemInfo.vue:34-40`）——这是全站唯一能看出"版本"的地方（见 §9）。

---

## 9. §7 全局通用件

### 9.1 命令面板 `GlobalCommandPalette.vue`（868 行）

**(a) 唤起方式**（`GlobalCommandPalette.vue:560-574`，原文）：

```ts
if (isCmd && e.key.toLowerCase() === 'k') {   // Always allow ⌘K to open, even from an input.
  ... commandPaletteStore.openPalette('')
}
// Plain "/" opens the palette when nothing is focused.
if (e.key === '/' && !open.value && !isEditingElement(e.target)) { ... }
```
也就是 **⌘K / Ctrl+K（任何位置，含输入框内）** 与 **`/`（未聚焦输入元素时）**。
侧栏两处视觉入口：展开态的搜索图标（`menu.vue:10-21`，tooltip 显示 `搜索  ⌘K`）与折叠态图标项（`:62-78`）。
修饰键标签按平台算：`const cmdModKeyLabel = isMacLike ? '⌘' : 'Ctrl'`（`menu.vue:304-305`，注释承认 `navigator.platform` 已废弃但可用）。
另有 URL 入口：`?cmdk=<q>`（`views/platform/index.vue:210-230`，用完即 `router.replace` 清掉 query）。
状态在 `stores/commandPalette.ts`，**随 platform 路由存活**（`views/platform/index.vue:12` 注释）。

**(b) 能搜什么**：分 8 组，id 即分组键（`GlobalCommandPalette.vue:55-123` + `zh-CN.ts` `commandPalette.group.*`）：

| 组 | 中文标题 | 内容 | 出处 |
|---|---|---|---|
| `chunks` | `知识库文件` | 按文件聚合的分块命中，带 `向量 / 关键字` 命中方式徽标 | `:55-72` |
| `messages` | `对话消息` | 历史消息命中，标 `Q`/`A` | `:75-90` |
| `kbs` | `知识库` | 知识库名匹配 | `:93-97` |
| `agents` | `智能体` | 智能体名/描述匹配 | `:100-105` |
| `sessions` | `对话（按标题）` | 会话标题匹配 | `:108-114` |
| `commands` | `命令` | 静态命令过滤命中 | `:117-123` |
| `recent` | `最近搜索` | 空查询时显示，可 `清除` | `:36-42` |
| `quickActions` | `快捷操作` | 空查询时显示 | `:44-49` |

空查询时的 6 条静态命令（`GlobalCommandPalette/commands.ts:36-96`）：
`新建对话 / 打开知识库 / 打开智能体 / 打开共享空间 / 打开设置 / 新手引导`（`zh-CN.ts` `commandPalette.quick.*`），
每条带 `keywords` 数组做多语言模糊匹配（如 `keywords: ['org','organization','team','space','组织','共享']`，`commands.ts:70`）。

**(c) 键盘操作**（`GlobalCommandPalette.vue:501-542`，footer 在 `:143-150`）：

```
↑ ↓ 选择    ↵ 打开    ⌘1-⌘9 直接打开    ⌘↵ 发起对话    Esc 关闭
```
`⌘1-9` 只在前 9 项生效（`shortcutFor`，`:496-499`）；`Enter` 与 `⌘Enter` 是**两个不同动作**
（`primaryActionForSelected({ cmd })`，`:521-523`）。
范围过滤：可以锁定"在本知识库中搜索"，用 chip 展示，`Backspace` 在空输入时摘掉 chip（`:533-542`，
文案 `scope.placeholder: '在本知识库中搜索…'`、`scope.remove: '移除范围过滤（Backspace）'`）。

**(d) 零结果不是死路**（`:126-138`）：给两个出口
`empty.noResults: '没有找到匹配结果'` → `直接向 AI 提问` / `调整检索参数`（后者打开右侧 420px 检索参数抽屉）。

### 9.2 全局提示（Toast / Notification / Dialog）

**用量是压倒性的 Message 派**（我对 `frontend/src` 全量 `.vue/.ts` 做了行计数，**这是计数不是穷举审计**）：

| API | 命中行数 | 说明 |
|---|---|---|
| `MessagePlugin.success/error/warning/info` | **828** | 主力，散落在各组件里 |
| `DialogPlugin.*` | 11 | 破坏性确认（如删除智能体 `AgentList.vue:1461-1463`） |
| `NotifyPlugin.*` | **2** | 仅 `App.vue:227`（切换空间成功）与 `utils/loginNotify.ts:57`（登录成功） |

**文案风格**（从 `zh-CN.ts` 归纳，均为原文）：
- 成功：`common.copied: '已复制'`、`agent.messages.created: '已创建智能体'`、`agent.messages.deleted: '已智能体已删除'`（实际为 `'智能体已删除'`）
- 失败：几乎都带"请稍后再试"或原因插值，如 `menu.renameSessionFailed: '修改标题失败，请稍后再试'`、
  `chatHistorySettings.toasts.saveFailed: '保存配置失败: {message}'`
- 警告：`settings.capabilityUnavailable: '当前部署不支持此功能，已返回可用页面。'`、
  `crew/warning` 类如 `AgentEmbedChannelPanel.vue:1008` 的 `embedPublish.previewUnavailable`
- **确认类弹窗的 body 必写"不可撤销/副作用边界"**，例（`zh-CN.ts:1887`）：
  `deleteConfirmMessage: '确定要删除共享空间「{name}」吗？删除后所有成员将被移除，此操作不可撤销。'`

**内联确认（popconfirm）优于居中弹窗**——这条被显式写成了理由（`components/credentials/CredentialResource.vue:46-50`）：

```
We use a sub-state instead of a global modal because the modal forces the user to context-switch to the screen center, then back to this row to see the result. Inline confirm keeps focus on the row that's actually changing.
```

### 9.3 上传任务中心 `components/upload-tasks/`

- 挂载点在外壳（`views/platform/index.vue:18`），状态在 Pinia store（`stores/uploadTasks.ts` 薄封装 + `stores/uploadTasksState.ts` 9KB 纯逻辑 + `stores/uploadTasksCore.ts`），
  所以**切页面不中断**（`views/platform/index.vue:17` 注释原文：`上传队列放在 store 里，切换页面不中断`）。
- 面板由 `UploadTasksPanel.vue`（720 行）+ `UploadTaskRow.vue` + `ProgressRing.vue` 组成。
- **两阶段文案分离**是核心设计（`UploadTasksPanel.vue:97-115`）：
  `titleUploading: '正在上传 {done}/{total}'` → `titleParsing: '正在解析 {done}/{total}'`；
  副行上传阶段显示 `已传/总量 · 剩余约 {time}`，解析阶段显示目标位置。
- 阶段态有 11 种（`zh-CN.ts:2638-2648`）：
  `等待上传 / 正在保存… / 排队解析 / 解析中 / 可检索，后台优化中 / 已完成 / 上传失败 / 解析失败 / 知识库中已有相同文件 / 已取消 / 已删除`。
- **两条行为承诺**（`:2626-2627`）：
  `hintUploading: '上传完成前请不要关闭或刷新页面'`、
  `hintParsing: '文件已全部上传，解析在后台继续，可以放心离开此页面'`——即明确告诉用户"什么时候可以走"。
- 图例 5 态 `可检索 / 处理中 / 等待中 / 失败 / 已存在`（`:2629-2635`），
  筛选 `全部 / 未成功`（`:2636-2637`），失败可批量 `重试 {count} 个`（`:2652`）。
- 完成后 6 秒无人悬停自动消失（`AUTO_DISMISS_MS = 6000`，`UploadTasksPanel.vue:20`）+ 悬停暂停（`:28-34`）。
- 上传窄条还有速率采样与 ETA 估算（`:47-82`，`estimateRate` / `estimateRemainingSeconds` 在 `stores/uploadTasksState.ts`）。

### 9.4 凭据组件 `components/credentials/CredentialResource.vue`（525 行）

这是全仓**最好的一个"小状态机"**，文件头注释把设计动机写全了（`:1-26`，原文摘）：

```
The previous UX (PR #990) showed a password input pre-filled with a redacted placeholder plus a red "Remove this credential" checkbox below it. That conflated three distinct user intents (preserve / replace / clear) into a single form field, and bundled credential changes with unrelated config edits in the same submit. Users could accidentally wipe a working key by toggling the wrong checkbox.
This component splits credentials out as an independent resource:
  - Read-only "configured" badge by default, derived from the `meta` prop.
  - "Replace" expands an input + Save/Cancel; commit is an explicit PUT to the credential subresource (no main-form submit needed).
  - "Remove" pops a danger-themed confirmation and on confirm calls DELETE immediately. No "save form to apply" intermediate state.
```

三态渲染：`configured`（`:39-84`）、`unconfigured`（`:86-...`）、编辑中。
`configured` 内部还分正常态与"确认移除"子态（`:41-83`）：
正常 `✓ 已配置 + [更换 | 移除]`，确认态 `⚠ 确认移除？此操作不可撤销 + [取消 | 确认移除]`。
文案（`zh-CN.ts:366-379`）：

```
configured: '已配置'   unconfigured: '未配置'   configure: '配置'   update: '更换'   remove: '移除'
inputPlaceholder: '请输入'
savedToast: '凭据已保存'   saveFailed: '保存凭据失败'
removedToast: '凭据已移除'   removeFailed: '移除凭据失败'
confirmRemovePrompt: '确认移除？此操作不可撤销'
confirmRemove: '确认移除'
```
`meta` 是唯一真源，来自父资源主 GET 响应的 `<resource>.credentials`，**没有独立的 GET /credentials 端点**（`:19-22` 注释）。

### 9.5 其它全局件

| 组件 | 作用 | 出处 |
|---|---|---|
| `SettingsModalShell.vue` | 全屏设置壳（1080×780、左分组导航 + 右内容 + 可选底栏），被 4 个编辑器共用 | `:60-67` |
| `upload-mask.vue` | 全局拖放遮罩 | `views/platform/index.vue:7-9`、`:271-280` |
| `ListSpaceSidebar.vue` | 知识库/智能体/共享空间三页**共用的左侧空间筛选栏**（折叠态是图标条，可拖宽） | `:1-75` |
| `EmptyState.vue` | 统一空态（`icon` / `title` / `description` + 可选 slot 放主 CTA） | `AgentList.vue:640-671` |
| `SpotlightGuide.vue` | 遮罩高亮引导引擎，步骤由 `data-guide` 属性定位 | `menu.vue:83` 的 `:data-guide="\`nav-${item.path}\`"` |
| `ResourceOriginBadge.vue` / `SpaceAvatar.vue` / `VectorStoreBadge.vue` / `settings/SandboxBackendBadge.vue` | 统一徽标语义 | — |
| `utils/clipboard.ts` 的 `copyWithToast` | 复制统一走一个函数并自带 toast | `AgentEmbedChannelPanel.vue:400`、`:754` |

---

## 10. §8 国际化

### 10.1 组织方式

- 入口 `src/i18n/index.ts`：`createI18n({ legacy: false, locale: savedLocale, fallbackLocale: BUILT_IN_DEFAULT, globalInjection: true, warnHtmlMessage: false, messages })`（`:23-33`）。
  `legacy: false` ⇒ Composition API 模式（组件里 `const { t } = useI18n()`；模板里 `$t`）。
  `warnHtmlMessage: false` 有原因注释（`:28-31`）：部分译文**故意内嵌 `<strong>`**（如 `agent.webSearchFound: '找到 <strong>{count}</strong> 个网络搜索结果'`，`zh-CN.ts` `agent` 段；以及 `agent.stepsCompleted`、`agent.reasoningRounds`），由 `v-html` + 自己的 sanitizer 渲染。
  `globalInjection: true` 是为了能在**非组件上下文**里用 `i18n.global.t`（例：`stores/menu.ts:54` 的菜单翻译）。
- 语言列表（`src/i18n/resolveDefaultLocale.ts:1-4`）：
  ```ts
  export const SUPPORTED_LOCALES = ['zh-CN', 'en-US', 'ru-RU', 'ko-KR', 'ja-JP'] as const
  export const BUILT_IN_DEFAULT: SupportedLocale = 'zh-CN'
  ```
  **5 种语言，内置默认中文**。
- 默认语言解析顺序：`localStorage['locale']` > `window.__RUNTIME_CONFIG__.DEFAULT_LOCALE`（运行时注入）> `import.meta.env.VITE_DEFAULT_LOCALE`（构建期）> `zh-CN`。
  见 `i18n/index.ts:18-21` 与 `resolveDefaultLocale.ts:11-18`。
  TDesign 组件自身的语言包也随 locale 切（`App.vue:18-38` 的 `tdLocaleMap` + `<t-config-provider :globalConfig>`，`:277`）。

### 10.2 命名空间与键命名风格

- **单个巨型 TS 模块，非 JSON、非分文件**。行数（实测）：

| 文件 | 行数 |
|---|---|
| `i18n/locales/zh-CN.ts` | **7424** |
| `i18n/locales/en-US.ts` | 7422 |
| `i18n/locales/ja-JP.ts` | 7422 |
| `i18n/locales/ko-KR.ts` | 7422 |
| `i18n/locales/ru-RU.ts` | 7422 |
| `i18n/embed.ts`（**嵌入端独立一份**） | 2130 |

- 顶层键 ≈ 80+ 个命名空间，**按"域/页面"切，不按"通用/业务"切**。
  我实测到行号的顶层键（`zh-CN.ts`）：`localBrowser:2`、`platformApiKeys:119`、`tenantInvitation:169`、`tenantMember:238`、`userProfile:344`、`credential:366`、`integrations:380`、`agentEditor:1100`、`organization:1859`、`ollamaSettings:2306`、`modelSettings:2347`、`mcpSettings:2491`、`uploadTasks:2611`、`time:2660`、`platform:2669`、`font:2693`、`theme:2729`、`general:2737`、`language:2746`、`system:3063`、`tenant:3627`、`common:5033`、`retrievalSettings:5251`、`memorySettings:5267`、`envVarSettings:5406`、`memoryWorkspaceSettings:5457`、`chatHistorySettings:5494`、`vectorStoreSettings:5511`、`webSearchSettings:5546`、`settings:`（内含 `sandbox:5592`、`skills:6001`、`storage:6072`、`storageBackend:6146`、`parser:6189`、`weknoraCloud:6239`、`roleDenied:6292`、`capabilityUnavailable:6296`、`navGroups:6297`）、`agent:6306`、`agentStream:1480`、`batchManage:7081`、`contextualGuide:7091`、`newUserGuide:7294`、`menu:7402`、`embedPublish:4655`。
  注意 `settings` 是个**混合命名空间**：既放 own 键（`capabilityUnavailable`、`navGroups`），又当**父级**放各子页（`sandbox`、`skills`、`parser`…）——这是历史分层痕迹。
- **键名风格**：`camelCase` 段用 `.` 连接（`agent.editor.basicInfo`），
  但**动作/状态叶子键本身也是 camelCase 短语**（`saveFailed`、`apiKeyCapabilitiesRequired`），
  不用 snake_case（例外：审计事件键是**点分的事件名本身**，见下）。
- **动态拼接键**有两种受控写法：模板串 `` t(`font.sans.${key}`) ``（`GeneralSettings.vue:188`）与
  字符串前缀拼接（`tenantMember.role.${role}`，`useRoleLabel.ts:22`）。
  为了能审计这类键，仓库自建了静态扫描器（见 10.4）。

### 10.3 插值 / 复数 / HTML

- **插值用 vue-i18n 命名占位符 `{name}`**，例：
  `tenant.switchSuccessContent` 类、`agent.delete.confirmMessage: '确定要删除智能体「{name}」吗？此操作不可恢复。'`、
  复数式命名 `organization.join.memberCount: '{count} 个成员'`、`shareCount: '{count} 个共享知识库'`、
  `share.join.agentShareCount: '{count} 个智能体'`（见 `zh-CN.ts:2144-2146`）。
- **没有复数管道语法**：我在 `zh-CN.ts` / `en-US.ts` 里对 `one |`、`| other`、`plural` 做了搜索，**零命中**。
  即 WeKnora **不用 vue-i18n 的 pluralization**，数量语义一律靠"名词 + {count}"或另立键
  （如 `auth.uptimeDays/uptimeHours/uptimeMinutes/uptimeSeconds`，`zh-CN.ts:3081-3084`——同一件事拆四个键）。
- **空值兜底**：`tm()` 而非 `t()` 用于"模板里含可选占位符、需要自己渲染"的场景。理由写在 `App.vue:221-226`（原文）：
  `Use tm() not t() — vue-i18n v11's t() replaces unspecified named placeholders with empty strings, which would strip {name}/{role} before the chip renderer can split on them. tm() returns the raw message verbatim.`
- **`@` 必须转义**：`inviteRegister.emailPlaceholder: 'your{\'@\'}example.com'`（`zh-CN.ts:5180`）、
  `tenantMember.add.emailPlaceholder: 'invitee{\'@\'}example.com'`、`claw.ecosystemNote: '…（{\'@\'}lyingbug/weknora）…'`。
  这是 vue-i18n 的消息语法（`@` 是 linked message 前缀）。
- **不允许直接嵌 HTML**（除非走 sanitizer），例外已在 10.1 说明。

### 10.4 防漂移的工程化（这块比翻译本身更有价值）

仓库有**三个** i18n 审计模块（都在 `src/i18n/`，都是 `.ts` 非测试）：

| 文件 | 作用 | 关键行 |
|---|---|---|
| `localeKeyAudit.ts`（24KB，739 行） | 反向扫描源码，收集所有 `$t/t/i18n.global.t/te/globalSettingsText/tm` 的**静态键、模板键前缀、拼接键前缀**，以及 `labelKey/hintKey/titleKey/i18nKey/stepI18nPrefix` 这类**元数据键**与 `step-i18n-prefix` 属性，再与 locale bundle 对账 | `:38-66`（正则表）、`:25-33`（`LOCALE_BUNDLES`） |
| `localeGapScan.ts`（8.6KB） | 独立走文件树（跳过 locales 自身与测试）做缺口巡检 | `:13-24`、`:41-47` |
| `localeSerialize.ts` | 把对象按稳定顺序写回 locale 模块（供自动补键/裁剪） | — |
| `regeneratePrunedLocales.ts` | 触发一次裁剪重生成 | — |
| `auditActionRegistry.ts` + `auditActionLocaleDefaults.ts` | **审计事件名 → 翻译键**的注册表 + 默认译文兜底 | 见 `localeKeyAudit.ts:9-17` 的 import |
| `locales/workspaceTerminology.test.ts` | 术语一致性测试（48 行） | — |

也就是说：**"事件名是代码常量、展示名是翻译"这条纪律是被 CI 兜住的**，
`EXTRA_PREFIXES`（`localeKeyAudit.ts:68-80`）专门列出无法从源码静态推断的键前缀
（如 `system.globalSettings.keyLabels.`、`knowledgeEditor.activity.actions.`）。

### 10.5 嵌入端另起一套 i18n

`i18n/embed.ts`（2130 行）是一份**独立的、内联的** 5 语言 bundle（`EMBED_MESSAGES`，`:2108`），
入口注释说明了分工（`i18n/locales/embed/index.ts:1-8`，原文）：

```
Embed i18n entry point.
- Visitor UI strings: `frontend/src/i18n/embed.ts` (loaded by embed-main.ts)
- Admin `embedPublish` strings: `frontend/src/i18n/locales/*.ts`
```

嵌入端的 locale 解析独立：`?locale=` URL 参数（`:2080-2082`）> 渠道配置的 `default_locale` > localStorage（`:2088-2100`），
且 URL 参数一旦出现就"钉住"，宿主再通过 postMessage 改也会生效但记 `hostLocalePinned = true`（`useEmbedBridge.ts:99-105`、`:215-218`）。

---

## 11. §9 哪些是 OSS 核心、哪些是企业版/平台版

### 11.1 结论先说

**前端几乎不表态"这是企业版"。** 我对 `frontend/src`（排除 locales）搜 `企业版 / Enterprise / enterprise / 升级到 / pro plan / 付费`，
只命中 1 处非文案代码（`api/organization/index.ts:235` 的注释 `// The role user wants to upgrade to`）
和 1 处 chunking 示例文案（`views/knowledge/settings/chunkingSamples.ts:282` 里提到 reranker"付费"）。
唯一出现"企业"二字在用户可见文案里的是 Chrome 插件自己的模式名：
`'打开插件设置，选择「企业/开发者」模式，填入服务 API 地址与 API Key。'`（`zh-CN.ts:493` 附近，§7.5）。

**取代"企业版"的是三套正交机制**：

1. **部署能力位（后端说了算）**
   `export const DEPLOYMENT_CAPABILITY_KEYS = ['organizations','agents','integrations.im','integrations.embed','integrations.api','integrations.mcpserver','settings.mcp','settings.websearch','settings.vectorstore','settings.storage','settings.sandbox','settings.sandbox.docker'] as const`
   （`config/deploymentCapabilities.ts:1-14`），共 **12 个键**。
   探测接口未知（`stores/deploymentCapabilities.ts:24`，`getDeploymentCapabilities()`）。
   **语义纪律**（`config/deploymentCapabilities.ts:25-47`，原文摘要）：
   - 探测失败 → **fail-open**（保持可见），理由：
     `// 能力接口失败或旧版后端没有返回某个键时保持可见，避免一次探测失败把整个菜单清空。只有后端明确返回 supported: false 时才隐藏入口。`（`:26-28`）
   - 唯一**fail-closed** 的是 Docker：
     `// Docker talks to a local Engine API (often docker.sock = host root), so missing or failed capability probes must not leave the picker visible.`（`:41-42`），`return capabilities[key]?.supported === true`（`:44`）
   - `organizations` 额外被 Lite 强制关闭（`:35-40`）。
   settings section → capability 的映射表 `SETTINGS_SECTION_CAPABILITY`（`:49-61`），含
     `skills → settings.sandbox`、`envvars → settings.sandbox`（各有理由注释，`:53-60`）。**它是"部署有没有这个能力"，不是"服务健康不健康"**（`router/index.ts:407-408` 注释原文：
     `部署能力只描述"后端是否提供该功能"，不反映服务健康或是否已配置。探测失败时 Store 会 fail-open，真正的权限和可用性仍由后端接口校验。`）。

2. **版本位（Lite）**
   `stores/deploymentCapabilities.ts:12,25` 收 `edition`；`isDeploymentCapabilitySupported(..., { edition })` 里
   `edition.trim().toLowerCase() === 'lite'` 即判 Lite（`config/deploymentCapabilities.ts:36-39`）。
   前端另有本地 `isLiteMode`（`stores/auth.ts:47`，从 `localStorage['weknora_lite_mode']` 与 auto-setup 得来，
   `router/index.ts:387`、`stores/auth.ts:538`）。Lite 的影响：
   - 侧栏隐藏 `logout` 与 `organizations`（`stores/menu.ts:68`）；
   - 禁止 `share` 发布页签（`AgentEditorModal.vue:2707`）、隐藏 UserMenu 的空间面板与退出项（`UserMenu.vue:56,81,136`）；
   - 显示 `自动下载更新` 开关（`GeneralSettings.vue:126`，注释 `(Lite edition only)`）；
   - 显示 Lite 徽标：侧栏 logo 右上角 `<sup class="lite-badge">Lite</sup>`（`menu.vue:7`），
     系统信息页版本行标签（`SystemInfo.vue:34-40`：`systemInfo.edition === 'lite' ? 'Lite' : 'Standard'`）；
   - 无 Redis/asynq 队列时任务队列页显示
     `unavailable: '当前部署未启用 Redis / asynq 队列（Lite 模式），无队列可展示。'`（`zh-CN.ts` runtime.unavailable）。

3. **角色位（空间/系统）**——见 §6.4，与商业版本无关。

### 11.2 我的判断（并标明证据强度）

| 面 | 判断 | 证据 | 强度 |
|---|---|---|---|
| 账号/登录/空间/成员/RBAC | **核心** | 全在 `views/auth`、`views/settings/TenantMembers.vue`、`stores/auth.ts`，无任何能力位 | 强 |
| 知识库/问答/引用（范围外） | **核心** | 是默认落地页（`router/index.ts:49-52`） | 强 |
| 模型管理（含 Ollama） | **核心**，但 `weknoracloud` 子页是**云端服务** | `models` 无能力位；`weknoracloud` 在 nav 中无能力位键，但整页围绕 WeKnora Cloud 的 APPID/APPSECRET（`zh-CN.ts:6240-6241`） | 中（凭"页面内容 + 无能力位"推断） |
| Artifacts（产物） | **依赖沙箱**，非独立商业版 | `menu.ts:35` 与 `router/index.ts:140` 都挂 `settings.sandbox` | 强 |
| Agents | **能力位控制**（`agents`） | `router/index.ts:146`、`menu.ts:36` | 强 |
| 组织/共享空间 | **能力位 + Lite 双重控制**，`admin` 起可见 | `menu.ts:37,68,80`、`deploymentCapabilities.ts:35-40` | 强 |
| 发布集成 im/embed/api/mcpserver | **能力位控制**（4 个键）；`api` 额外 owner-only | `config/integrations.ts:15-24` | 强 |
| 发布集成 cli/chrome/claw | **无能力位 ⇒ 永远可见**（落地页形态，功能在外部） | `INTEGRATION_TAB_CAPABILITY` 不含这三者（`config/integrations.ts:19-24`） | 强 |
| Sandbox / Skills / EnvVars | **能力位控制**（`settings.sandbox`，Docker 另有 fail-closed 键） | `deploymentCapabilities.ts:56-60`、`:43-45` | 强 |
| VectorStore / Storage / WebSearch / MCP | **能力位控制** | `SETTINGS_SECTION_CAPABILITY`（`:49-61`） | 强 |
| 长期记忆（空间/个人） | **角色门槛控制**（`memory: 'admin'`），无能力位 | `settingsAccess.ts:31` | 强 |
| 系统设置/队列/平台 Key/审计 | **系统管理员专属**（`isSystemAdmin`），无能力位 | `settingsAccess.ts:47-52`、`router/index.ts:422-427` | 强 |
| 浏览器连接（本机 Chrome） | 无能力位、无角色门槛，产品特性 | `settingsAccess.ts:27`（`viewer`） | 强 |
| **"哪个是 OSS、哪个是商业版"** | **前端无从判断** | 无版本横幅、无升级 CTA、无"企业版"锁 | 强（否定证据） |

> 一句提醒：`edition` 只有 `lite` / 空两种被前端识别（`config/deploymentCapabilities.ts:36-39` 只在 `=== 'lite'` 时特判），
> `SystemInfo.vue:40` 非 lite 一律显示 `Standard`。所以**即使后端存在"企业版"这个 edition，前端也会把它显示成 `Standard`** —— 这是我推断，未读到后端代码。

---

## 12. 值得我们抄的（10 条，每条一句理由）

1. **能力位探测 + fail-open + 唯一例外显式标注**（`config/deploymentCapabilities.ts:26-47`）：
   用"部署能力位"而不是"版本号"决定入口，探测失败保持可见，只对"= 拿 host root 的危险项"（Docker）反向 fail-closed——
   把"宁可少藏一个入口"写成代码默认值，比写进文档可靠。
2. **`?section=<navKey>` 作为设置位置的唯一真源，并保留旧 URL 重定向**（`config/settingsRoute.ts:47-62`、`router/index.ts:148-164,193-215`）：
   任何"深链到某个设置项"的需求（引导、命令面板、外部书签、错误提示"去改配置"）都变成一次 push，不用额外状态。
3. **"角色 → 最小可见角色"单表 + "权限不足"整页兜底**（`config/settingsAccess.ts:10-35`、`Settings.vue:69-75`）：
   入口可见性一处改口径，且被 deep-link 绕过时有体面降级而不是 403 白屏。
4. **命令面板的空态是"最近 + 快捷操作"，零结果给两个出口**（`GlobalCommandPalette.vue:35-49,126-138`）：
   搜索无果时"直接问 AI / 调检索参数"把失败转成下一步，而不是只写一句"没有结果"。
5. **键盘可达性做到 ⌘1-9 直达，且 `Enter` 与 `⌘Enter` 是两个动作**（`GlobalCommandPalette.vue:496-527`、`:143-150` 的 footer 提示）：
   让人不用鼠标就能完成"打开"与"用这条发起对话"两种不同意图。
6. **上传任务的"能不能走"被明确写在界面上**（`UploadTasksPanel.vue:97-115` + `zh-CN.ts:2626-2627`）：
   区分上传期/解析期，并直接告诉用户"现在别关"和"现在可以走"——长任务最缺的就是这句话。
7. **凭据三态组件把"保留/更换/清除"拆成三个独立动作**（`credentials/CredentialResource.vue:1-26`）：
   一个密码框 + 一个"移除"勾选框会把三种意图混在一起，能误删掉在用的 key。
8. **危险动作就地 popconfirm，并把副作用边界写进确认文案**（`CredentialResource.vue:46-50`、`RuntimeQueues.vue` 的
   `cancelConfirm/deleteConfirm/purgeArchivedConfirm`，`zh-CN.ts:3426-3434`）：
   确认框写清"只删 Redis 记录、不回滚业务状态"这种边界，能省掉大量事后解释。
9. **审计事件用注册表 + 默认译文兜底，并由静态扫描兜住**（`i18n/auditActionRegistry.ts`、`auditActionLocaleDefaults.ts`，
   被 `localeKeyAudit.ts:9-17` 引用）：事件名是代码常量、展示名是翻译，新增事件忘了翻译时审计脚本会报，不会悄悄漏。
10. **引导分层：全局一次 + 按场景各一次，各有独立 storage key 且支持"完成 A 顺带完成 B"**（`config/contextualGuides.ts:46-135`）：
    引导不该只有"一次性冷启动"，也不该每次进页面都弹；两个诉求用两个键位解决。

补充两条小但好用的（不计入 10 条）：
`tooltip 在权限不足时换文案`（`OrganizationList.vue:11` 的 `:content="canManageOrg ? … : noPermissionTip"`）、
`空态组件的 slot 直接放主 CTA`（`EmptyState.vue` + `AgentList.vue:660-666`）。

---

## 13. 我们不抄 / 抄不动（9 条，每条一句理由）

1. **整套多租户 + 空间切换（`stores/auth.ts:105-186`、`components/TenantSelector.vue`、`TenantInfo/TenantMembers`）**——
   我们寄生在宿主的 IDE 里、用宿主的会话与本地单机，第二个"空间"这个概念对我们不存在；照抄只会引入一个永远只有一行的列表。
2. **Vue 3 + TDesign + Pinia 的技术栈本身**——我们是 React + 宿主原生组件；能搬的是信息架构与文案纪律，不是组件代码。
3. **828 处 `MessagePlugin.*` 直接散在组件里**——没有统一出口，级别与文案风格必然漂；
   我们该反过来做：一个 notify 封装 + 强制走它，而不是抄它的自由度。
4. **`components/menu.vue` 1724 行的单体侧栏**——导航、会话列表、批量删除、拖拽展开、品牌图标状态机全在一个文件；
   我们要的话必须拆成"导航 + 面板"两层。
5. **i18n 用 5 个 7422~7424 行的巨型 TS 单文件**——它靠事后 `localeGapScan`/`localeKeyAudit` 兜漏键；
   我们文案量小一个数量级，按命名空间拆文件 + 键即类型更省事。
6. **Sandbox / Skills / Artifacts 体系（Docker/E2B/Cube 三后端 + 技能镜像 + 装机向导）**——
   它解决的是"让 Agent 执行任意脚本"的问题，与我们"证据 PDF 侧栏 + 取证链"是两条路，运维成本也远超收益。
7. **WeKnora Cloud / Ollama 本地拉取 / 向量库 / 存储后端多实例注册**——这些是"让用户自己接基础设施"的形态；
   我们的部署形态是本地单机、基础设施固定，暴露这些只会让用户多填一堆用不到的框。
8. **IM 九平台渠道 + 微信扫码绑定（`IMChannelPanel.vue`，52KB）**——我们不往外发布助手；
   而且它有一半代码在处理各平台凭证差异与二维码轮询，属于纯粹的外部对接成本。
9. **全局 OS 文件拖放接管（`views/platform/index.vue:117-195`）**——在 IDE 宿主里，拖放语义属于宿主编辑器；
   我们在侧栏里抢 `dragover/drop` 会和宿主的拖放打架。

（第 10 条候选：`AgentEditorModal.vue` 6546 行单文件 + 内置占位符弹出器，也不该抄；但它是"功能太大"的结果而非设计选择，故不单列。）

---

## 14. 我没查到 / 不确定

**范围性未查**

1. **`views/knowledge`、`views/chat`、`views/creatChat`、`views/artifacts`、`components/chat`、`document-preview.vue` 全部未读**（任务明确划出）。
   因此本报告中凡涉及它们的结论都只是"引用方视角"（例如 `router/index.ts` 里的 meta、`stores/menu.ts` 里的门槛）。
2. **前端之外的一切**：`internal/`（Go 后端）、RBAC 的 `middleware/rbac.go`、`g.Admin()/g.Owner()` 路由组、
   `/api/v1/deployment/capabilities` 的真实返回、`edition` 的可能取值、`system_settings` 的键清单——
   我一次都没读。所有"后端是权威"的说法都只是**前端注释的自述**，不是我的验证结果。
3. **未验证的运行时行为**：我没有启动过这个前端，没有登录过，没有点过任何一个按钮。
   所有"点击后会…"都来自代码路径，不是实测。

**具体不确定项**

4. **`platformApiKeys` 的具体文案**：我只读到键名（`zh-CN.ts:119` 起），
   没有逐字核对 `title / description / securityNotice / capabilityMore` 的原文，故 §8.5 未引用文案。
5. **`organization` 设置弹窗的完整页签清单**：我从 `OrganizationSettingsModal.vue:957-1027` 读到
   `basic / permissions / members / joinRequests / sharedKb / sharedAgents`（其中部分带条件），
   但**没有逐个验证每个页签的显示条件**，也没读它 109KB 里的全部表单。
6. **`skills` 的 nav children 机制到底有没有真正启用**：`Settings.vue:49-57` 支持 `item.children` 渲染子菜单，
   但 `Settings.vue:351-377` 构造的 `all` 数组里**没有任何 item 带 `children`**，
   只有 `:511-517` 的兜底代码在 `navItem.children` 存在时才展开——所以这段子菜单 UI 目前**可能是死代码**。标注为不确定。
7. **`retrieval` section 是否曾作为左侧 nav 项存在**：它不在 `navItems` 里（`Settings.vue:351-377` 无 `retrieval`），
   只在命令面板抽屉里用（`GlobalCommandPalette.vue:175`）。但 `Settings.vue:78-196` 的 section 渲染里也**没有** `retrieval` 分支——
   即 `?section=retrieval` 会落到 `canSeeSection('retrieval')` 为真（`settingsAccess.ts` 无该键 ⇒ 默认 `'viewer'`）
   但内容区什么都不渲染。这是我从代码推出的一个**疑似缺陷**，未实测。
8. **`MessagesPlugin` 828 这个数字是"命中行数"不是"调用次数"**：我用 `Select-String -AllMatches` 计数的行数，
   一行可能多个调用；且这是**抽样口径的统计**，不代表精确调用数。
9. **`OrganizationList` 的 `noPermissionTip` 原文**：我读到模板里用了这个变量（`:11,17,180,187`），
   但没定位它的定义与文案，故 §6.3 只引用了 `canManageOrg` 的判据。
10. **`views/system/SystemSettings.vue` 的全部设置键清单**：该页 1492 行、由后端 `system_settings` 驱动，
    我读了页头/tab/三类控件与 `keyLabels/keyDescriptions/enumLabels` 的存在（`localeKeyAudit.ts:71-73`），
    但**没有列出具体管理了哪些键**。
11. **`embedPublish` 的 webhook 段文案**：我读到模板里有 `webhookUrl/webhookSecret`（`AgentEmbedChannelPanel.vue:258-276`），
    但没读这两个键的完整原文。
12. **"是否跟随系统"在 Wails 桌面端的实际表现**：`useTheme.ts:28-61` 会调 `runtime.WindowSetDarkTheme` 等，
    我只能读代码判断它同步原生底色，无法确认桌面壳里的最终观感。
13. **`views/dev` 是否只有这一个页面**：我按目录列举确认只有 `MarkdownTestPage.vue`，
    但**没有检查 vite 配置里是否有别的 dev-only 入口**（只确认了 `embed-main.ts` 这个第二入口）。
14. **`claw` / `chrome` / `cli` 三个落地页的完整文案**：我只摘了标题与步骤结构，未逐字读完三个文件（`ClawSkillLanding.vue` 等）。
15. **未核对 `en-US` / `ja-JP` / `ko-KR` / `ru-RU` 的实际翻译质量**：我只用行数确认了 5 份 bundle 结构对称，
    没有抽样比对任何一条译文是否准确或是否漏译。

---

*记录者：WeKnora 前端精读（第 2 篇，外壳与其余页面）。全部结论来自只读阅读；未修改 `D:\AI\WeKnora` 下任何文件。*
