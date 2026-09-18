# DSH 客户端插件（右栏 UI）开发摘要

阅读范围（仅英文原文）：`docs/subsystems/sidebar-right.md`、`web-client.md`、`client-modules.md`、`client-resources.md`、`slots.md`；
按 sidebar-right.md:109 的一级链接补读 `packages/client/ui-sidebar-documentpreview/README.md`、`packages/client/ui-sidebar-right/README.md`。
下文 `SR:` = `docs/subsystems/sidebar-right.md`，`SL:` = `docs/subsystems/slots.md`，`CR:` = `docs/subsystems/client-resources.md`，`WC:` = `docs/subsystems/web-client.md`，`CM:` = `docs/subsystems/client-modules.md`。

## 现成能力清单

| 能力 | 官方怎么用（精确 API/槽位名/函数签名） | 出处 |
|---|---|---|
| 注册一个 tab 类型（静态定义，id 全局唯一） | `ctx.sidebarRightTabs.register({ id, kind, patterns?, priority?, canOpen?, title, guide? })`，返回 disposer；必须包在 `ctx.effect` 里。字段表：`id/kind/patterns/priority/canOpen(address)/title(address)/guide` | SR:36-46；`packages/client/ui-sidebar-right/README.md:77` |
| 注册 tab 正文 | `ctx.slots.register({ name: 'sidebar.right.pane.tab', key: definition.id }, Body)`，外层用 `ctx.slots.inject('sidebar.right.pane.tab', () => …)` 等待父席位 | SR:66-69, SR:97 |
| 打开资源/页面的唯一导航入口 | `ctx.sidebarRight.openResource(address, options?)` / `openTab(kind, options?)`；选项 `paneId/replaceTab/revealIfOpened/kind/params` | SR:73-83 |
| 布局操作（不用碰 dockkit） | `close(tabId)`、`active()`、`isExpanded()`、`toggleExpanded()`、`focus(tabId)`、`split(paneId?)`、`float(tabId, rect?)`、`dock(paneId)` | SR:87-89 |
| tab 内取信息 | 框架注入 `useTabInfo()` → `{ sidebar, panel, tab }`；`tab` 含 record 字段 + `visible`/`navigation`/`signal`/`actions`；`tab.actions` = `openResource/openTab/close`（绑定本 tab 的 Session） | SR:103；`ui-sidebar-right/README.md:78,94` |
| 读资源的全局标准 prop | `useResource<P>(address)` → `{ status, value, failure }`，**每个 slot 组件都有，与 scope 无关** | CR:54-61；SR:121 |
| 观察（不订阅）一个资源 / 保活 | `ctx.resources.source(address)`（引用稳定）；`ctx.resources.pin(address, signal)`；Sidebar 已为每个打开的 tab pin 地址 | CR:85 |
| 自己提供一种协议（内容类型） | `ResourceProtocolMap` 声明合并 + `ctx.resources.register({ protocol, open(address,{signal}) })`，`open` 为 async 迭代器，yield `RemoteResult` 帧；同一协议第二个 provider 抛错 | CR:23, CR:32-48 |
| 会话/工作区数据 | `useSessions`、`useSession`、`useSessionPendingInteraction`、`useProjection`、`useWorkspaces`、`usePanelInfo`、`useConversation`、`useInput`、`inputActions`、`useChat`、`useTrajectory` | SL:83-91 |
| 文件地址语法（不要自己拼字符串） | `fileAddressFor(sessionId, cwd, path)` / `parseFileAddress(address)`；`dsh-resource://file/session/<sid>/<rel>`、`.../absolute/<path>` | SR:28；CR:11 |
| 文件内容读取（元数据≠内容） | Host `ctx.workspaceFiles` / Remote `workspaceFiles`：`stat`、`read(path,{offset?,limit?})`、`readBytes`、`list`、`changes()` | SR:127；CR:87 |
| 本地化 | 注册时声明 `locale` 命名空间 → 组件拿到 `t` | SL:71, SL:93 |
| 共享视图状态 | 注册时声明 `store` → `useStore` + bound actions（private 数据用注册的 `inject` 工厂） | SL:69, SL:99-105 |
| 关闭时清理 | `ctx.sidebarRight.registerCloseHandler(kind, handler)`（用 effect 持有） | `ui-sidebar-right/README.md:96` |
| 在 document tab 内做文件渲染器 | `ctx.documentPreviews.register({ id, extensions, binaryExtensions?, priority, title, loading, wrap? })` + 以同一 `id` 注册 keyed slot `sidebar.right.tab.document` | `ui-sidebar-documentpreview/README.md:33` |

## 槽位目录

| 槽位名 | kind | 作用 |
|---|---|---|
| `root` | 唯一内建声明 | 框架级：`ui-renderer` 调 `ctx.slots.renderSlot('root', {})`；其余都通过父条目的 `renderSlot`/`renderSlotChain` prop 渲染 |
| `sidebar.right.pane.tab` | keyed（key = 定义 `id`），Session scope | 一个 tab 的正文；席位按该 kind「生效实现」的 `id` 派发，docked/floating 都进这里；该 kind 无正文时渲染 owner 的 "nothing can view this" 提示（SR:97） |
| `sidebar.right.pane.tab.title` | keyed（key = 定义 `id`），Session scope | chip 标题；可选，不注册就用开 tab 时抓取的 `title(address)` 文本（SR:98） |
| `sidebar.right.tab.guide` | chain，Session scope | 替换 guide tab 的正文而不替换 tab；第一个不 decline 的条目接管，否则渲染内建 guide（SR:99） |
| `sidebar.right.tab.menu.item` | list，Session scope | 在 kit 自己的布局动作之后追加内容级动作；**动作后必须调 owner 的 `dismiss()`**（SR:100） |
| `sidebar.right.tab.document` | keyed（key = 文档实现 `id`），Session scope | document tab 内被选中的文件渲染器；父级持有共享加载与工具栏（SR:101；SL 层级图未列该槽，见未解答） |
| `sidebar.right.tab.guide.entry` | keyed（按生效定义 id），Session scope | guide 页里每个 guide 条目的卡片，可自定义（`ui-sidebar-right/README.md:101`）；SL:170 列出 |
| 非右栏（对照，勿混） | | `sidebar.*` / `main.conversation*` / `conversation.composer*` / `shell.overlay`，见 SL:111-174 |

## 不许自己造的东西

- 自己写 tab/标签页容器、拖拽、分屏、浮动面板、历史 → `ctx.sidebarRight` 的 `openResource/openTab/focus/split/float/dock/close` + dockkit（内部引擎，不是稳定接口）→ SR:73-89, SR:18。
- 自己写「打开文件」的路径解析和 URL 拼接 → `fileAddressFor(sessionId, cwd, path)` / `parseFileAddress`；`dsh-resource://<type>/…` 只有一套 scheme → SR:28, SR:26。
- 自己写资源加载器 / fetch 循环 / 轮询 → `useResource` / `ctx.resources.register` / `ctx.workspaceFiles` → CR:23,54；SR:127。
- 自己写 React context、`useSyncExternalStore` 订阅总线 → `ui-renderer` 是唯一绑定 bare observable 的包；用注册 `inject` 的 `hooks: { … }`（renderer 转成组件 prop）→ WC:60, SL:101-103。
- 自己给组件传 `ctx`、transport 对象、别的 feature 包的实现 → 组件永远不接收 `ctx`；跨包 UI 只走 slots → WC:18, SL:75-76。
- 自己写 tab 关闭/替换的异步清理逻辑 → `registerCloseHandler(kind, handler)` → `ui-sidebar-right/README.md:96`。
- 自己写文档预览/文件查看器（markdown、代码、PDF、HTML、纯文本兜底、换行开关、刷新） → document tab + `ctx.documentPreviews` + 内建 fallback；未知后缀自动纯文本 → SR:109-115, SR:134。
- 自己写文件树 → 内建 `files` kind，`openTab('files')` → SR:135。
- 自己写 guide/新手引导页和「默认页」逻辑 → 内建 `guide` kind + 定义里的 `guide` 入口盒；默认页由「注册的 guide 条目数」决定 → SR:133, `ui-sidebar-right/README.md:105`。
- 自己写 Session/Workspace 状态镜像 → Client model（`ctx.sessions`、`ctx.workspaces`）+ `useSession`/`useWorkspaces` → WC:36-52。
- 自己加 `dsh.client.external` 绕过包边界 → 明确禁止 → WC:88。
- 自己写 bundle 服务器 / HMR / manifest → `dsh.client` + `exports["./client"]` + `/plugins/??…&rev=` 路由 → CM:77, CM:85。

## 坑

- **静默空白**：address 协议拼错或地址格式非法 → `useResource` 返回 `status: 'none'`，**没有任何其它诊断**（CR:91）；`sidebar://guide` 也读作 `none`（CR:19）。
- **静默空白**：给某个 kind 注册了类型但没注册 `sidebar.right.pane.tab` 正文 → 只渲染「nothing can view this」提示，不报错（SR:97）。
- **静默不生效**：把子槽位注册放在 `apply` 里直接调、不用 `ctx.slots.inject(key, cb)` → owner 卸载/重挂后不再运行；owner 折叠时要递归移除 → SL:17。
- **失败不在模型里**：provider `open` 抛异常 = 编程错误，模型**不 catch**；失败必须 yield `{ ok:false, error }` 帧（CR:23）。消费者要自己展示 `failed`，并把旧值当 stale 内容显示（CR:81）。
- **`useResource` 可能读到别人的内容**：Sidebar 为每个打开的 tab pin 地址，切换 tab **卸载正文但不关流**；资源在所有 holder 释放后才 abort 并丢弃值 → CR:85, SR:123。
- **同一地址两个类型 = 两个 tab**；tab 身份是 `(kind, address)`，地址按字符串比较：`DSH-RESOURCE://File/…` 与大写协议名是**另一条记录**，且 `openResource` 只接受 `fileAddressFor` 产出的规范小写拼法（CR:17, SR:32）。
- **地址 no type claims / kind 未注册 → 抛错**：这是 wiring mistake，不是用户错误，会在打开时炸（SR:48, SR:75）。
- **写操作需要已挂载的 Session surface**，否则抛错（读取返回 `undefined`/`false`）（SR:87）。
- **`priority` 方向反直觉**：值越小越先（`single/list/keyed` 是遮蔽排名，`chain` 是选举顺序）；`extension` 是默认且最高 band，会**顶掉内建同 kind**（SR:43,50；SL:58）。
- **复用已占的 keyed key / 相同 list id 是「替换」而非追加**；要追加必须用新 key/id（SL:184）。
- **`title(address)` 在开 tab 时被捕获且永不重写**；动态标题只能来自 `sidebar.right.pane.tab.title` 席位（SR:45,98,144）。
- **布局是内存态**：刷新后所有 Session 回到折叠默认；`rightbar` 控制器只在 Conversation 选中时挂载 `rightbar.session` 座位（SR:11,141）。
- **`signal` 的语义**：只在记录消失或插件卸载时 abort，**切 tab / 切 Session 不 abort**（SR:103）。
- **`select` 是纯函数**：chain 条目返回 `null` 表示 decline；第一个非 null 的渲染并收到 `matched`（SL:53）。
- **`single` 不是加法列表**：要加东西用 list id 或 keyed key（SL:50）。
- **禁止跨 feature 包的运行时 import/再导出**（只允许 `import type`）；共享运行时值必须放到无 feature 生命周期的静态 owner（WC:86-88, SL:180）。
- **`ctx.slots.register` 进未声明槽位、或声明一个已被别处拥有的子槽** → 插件激活期失败（SL:13）。
- **`dsh.client` 声明写坏或 bundle 缺失**：激活期是一个列出所有坏包的 `AggregateError`（fiber FAILED）；稳态只打 warning，不污染其它包（CM:79）。
- **每个资源地址的记录活到页面结束**：内存随「曾经读过的不同地址数」增长（CR:91）。
- **`wrap` / `loading` / `scrollportRef` 是 document 渲染器契约的一部分**：`loading: 'text-pages'|'bytes-complete'`；`content` 是 borrowed 只读 buffer，**不得进入持久化布局或 Session JSON**（SR:111-113）。

## 未解答

- `sidebar.right.tab.document` 到底由谁声明：SR:93/101 说「document tab 声明了额外的 keyed 正文槽」，但 SL:111-174 的层级图里 `sidebar.right.pane.tab` 下只有 `guide`/`guide.entry`/`title`/`menu.item`，没有 `document`——层级图与文字不一致，未给出 document 槽的父条目（也未说明它是否由 `text` 类型的实现声明）。
- `sidebar.right.tab.menu.item` 与 chain `sidebar.right.tab.guide` 的**条目签名/owner props 类型**（除「必须调 `dismiss()`」和「chain 提供 `select(owner)`」外）未在五篇文档中给出。
- `sidebar.right.pane.tab.title` 与 `sidebar.right.tab.guide` 的注册 `key` 规则细节（title 用定义 id 已给；guide chain 的条目 id/order 约定未给）。
- 一个 `useResource` 上的 `P` 与地址协议不一致时的运行时行为（类型层是否有校验）未说明。
- `useTabInfo` 的 `tab.record` **全部字段名**未列出（只说 "contains its record fields plus visible/navigation/signal/actions"）。
- `params` 的类型合并（`SidebarRightResourceParamsMap`/`SidebarRightTabParamsMap`）之外，body 如何声明自己的参数类型未给示例。
- 客户端插件在一个**动态 Cordis Package**（`cordis_define` 的 client 半）里能否注册 `sidebarRightTabs`/slots、需要哪些声明合并——五篇文档只描述包级插件，未提动态包路径。
- 是否支持在右栏之外新增 pane 级动作或折叠态控件：SR:100 明确「没有面向格级动作或折叠态控件的席位，因为还没有东西需要它」——未来是否计划未说。
