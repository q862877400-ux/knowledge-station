# 证据卡片（Evidence Card）交互契约 v1

> 2026-08-25 冻结。本契约是证据卡片重构的唯一协调文档：并行开发的子代理以本文件为唯一事实源。
> 违反本契约的改动一律退回。改动本契约须同步更新本文件并在 DECISIONS 登记理由。

## 0. 背景与目标（用户需求原文转译）

| # | 需求 | 契约条目 |
|---|---|---|
| R1 | 卡片不得遮挡触发它的蓝色超链接（标准号-条款号） | §2.3 防遮挡规则 |
| R2 | 卡片默认尺寸不得超出屏幕边界 | §2.2 钳制规则 |
| R3 | 卡片只能出现在问答左栏内，不得遮挡 PDF 预览与目录 | §2.1 面板坐标系 |
| R4 | 卡片可按住头部拖动；有固定（📌）按钮；可固定多张置顶对比 | §3 拖拽 / §4 固定 |

## 1. 文件所有权（并行开发零冲突的关键）

| 文件 | 所有者 | 说明 |
|---|---|---|
| `src/renderer/EvidenceCard.tsx` | 子代理 A（新建） | 卡片组件：定位/拖拽/固定/多实例 |
| `src/renderer/App.tsx` | 子代理 A | 仅限集成改动（见 §6 白名单），其余不动 |
| `src/renderer/styles.css` | 子代理 B | 仅限 §5 列出的卡片类，其他区块一行不动 |
| 其余一切文件（后端/PdfViewer/TaskCard/DiscoverDialog/LawFetchPanel/UpdatePanel/TipTapEditor/tableText/api） | 禁改 | — |

## 2. 定位引擎（子代理 A 实现）

### 2.1 面板坐标系（替代视口坐标系）
- 面板 = `.left` 元素（问答左栏）。用 `ResizeObserver`（或等价机制）实时获取面板矩形 `paneRect`。
- **一切定位、拖拽、尺寸钳制都以 `paneRect` 为边界**——卡片天然不可能遮挡右栏 PDF/目录/状态栏（R3）。
- `paneRect` 内边距：四周留 8px。

### 2.2 尺寸与出界钳制（R2）
- 默认宽度：`min(470, paneWidth - 16)`；默认最大高度：`min(76vh, paneHeight - 16)`。
- 渲染后用 `useLayoutEffect` 实测卡片尺寸，**实测后二次钳制**（防止内容撑高后出界）。
- 任何时刻卡片矩形必须完整落在 `paneRect` 内；`ResizeObserver` 监听卡片自身尺寸变化并重新钳制。

### 2.3 防遮挡触发链接（R1）
- `showCard` 改为接收**触发元素矩形** `triggerRect`（`target.closest('.cite-link').getBoundingClientRect()`），不再是鼠标坐标。
- 初始定位优先级：
  1. 首选：链接正下方，`top = triggerRect.bottom + 6`，水平与链接左对齐；
  2. 下方空间不足（按估高 360px 判定）→ 链接正上方，`top = triggerRect.top - cardH - 6`；
  3. 上下都不足 → 贴 `paneRect` 底部（或顶部）留 8px；
  4. 水平钳制：`left ∈ [paneRect.left+8, paneRect.right-cardW-8]`；
  5. **最终校验**：钳制后卡片矩形若仍与 `triggerRect` 相交 → 沿垂直方向偏移至完全不相交（宁可离链接远一点）。
- `treeOpen`（目录打开）时保留现有"固定在目录右侧 left=240"行为，但同样受 2.1/2.2 钳制（不得压住目录抽屉，抽屉宽 232px）。

### 2.4 异步 resolve 的矩形时效
- `resolveEv` 异步返回后才显示卡片的路径：在调用时捕获 `triggerRect` 快照，返回后用快照定位（元素可能已移除）。

## 3. 拖拽（R4a）

- 拖拽手柄 = 卡片头部（`.ev-head.ec-head`）；头部内按钮（收藏★/固定📌/关闭✕）**不触发拖拽**（mousedown 事件里排除 button 目标）。
- Pointer Events + `setPointerCapture`；`cursor: grab`，拖拽中 `grabbing`。
- 拖拽全程钳制在 `paneRect` 内（含卡片尺寸）。
- 拖动中的卡片置顶（见 §5 z-index）。

## 4. 固定与多卡片（R4b）

- 头部新增 📌 固定按钮（`.ec-pin-btn`）：
  - 浮动卡点击 📌 → 转为**固定卡**（加入 `pinnedCards` 数组，位置 = 当前卡片位置）；
  - 固定卡点击 📌（高亮态）→ 取消固定并**关闭该卡**；固定卡另有 ✕ 关闭按钮（`.ec-close`）= 直接关闭。
- 固定卡特性：**不参与 0.5s 渐隐**（鼠标移开不消失）；鼠标悬停/点击仍保持。
- **多实例**：`pinnedCards: Array<{ id, ev, x, y, z }>`；同一证据可固定多张（对比场景）；新固定卡初始位置相对上一张级联偏移 +24px（越界则回绕到面板左上 8,8 起）。
- 置顶规则：固定卡基础 z 高于浮动卡；**最近交互（mousedown）的固定卡置顶**（bring-to-front）。
- 浮动卡（未固定）行为不变：0.5s 渐隐、悬停保持。
- 固定卡仅存于内存（会话级），不持久化、不进 localStorage。
- Esc 键：关闭当前浮动卡（不关固定卡）。

## 5. CSS 类名与 z-index 契约（子代理 B 实现）

| 类名 | 用途 | 归属 |
|---|---|---|
| `.cite-popover` | 卡片基座（保留现名；`position:fixed; resize:both`） | B 更新 |
| `.cite-popover.floating` | 浮动态 | B 新增 |
| `.cite-popover.pinned` | 固定态（更强阴影/品牌色描边以示区别） | B 新增 |
| `.ev-head.ec-head` | 头部 = 拖拽手柄（`cursor:grab`；`.dragging` 时 `grabbing`）；保留 `.ev-head` 既有样式 | B 增补 |
| `.ec-pin-btn` | 固定按钮；`.pinned` 态下高亮（品牌色填充） | B 新增 |
| `.ec-close` | 固定卡关闭按钮 ✕ | B 新增 |
| z-index | 浮动卡 `940`；固定卡 `950 + stack`（由组件内联 style 给出，B 只需保证类默认值不冲突） | B/A |

- B 不得改动 styles.css 中非卡片区块（chat/badge/input/modal/toc/pdf 等一律不动）。

## 6. App.tsx 集成白名单（子代理 A 在 App.tsx 中仅允许改这些）

1. `showCard` / `scheduleHide` / `hoverEv` / `fading` / `hideTimer` 相关逻辑（改为传 `triggerRect`）；
2. `onAnswerHover` / `onAnswerClick` / PdfViewer `onSpanHover` 中传矩形的地方；
3. 原 1213~1255 行内联卡片 JSX → 替换为 `<EvidenceCard …/>` + 固定卡图层；
4. 新增 `pinnedCards` 状态与 Esc 处理扩展；
5. **其余一切不动**（SSE/linkify/loadDocument/审查面板/新组件调用等）。

## 7. 验收清单（验证代理逐条核查）

1. 悬停蓝链：卡片与该链接矩形**不相交**（R1）；
2. 卡片四边始终在左栏内：不压 PDF、不压目录抽屉、不压状态栏（R3）；
3. 默认与拖拽/缩放后都不出屏幕、不出左栏（R2）；
4. 按住头部拖拽顺滑、范围钳制在左栏；头部按钮不误触发拖拽（R4a）；
5. 📌 固定后鼠标移开不消失；可同屏固定 ≥3 张做对比；级联不重叠；✕ 关闭；再点 📌 取消并关闭（R4b）；
6. 无回归：定位原文/纠错/批注/收藏/可信切换/悬停保持/渐隐/treeOpen 定位（§2.3）；
7. 门禁：`npx tsc --noEmit` 0 错误；`npm run build` 通过；`.venv/Scripts/python -m pytest -q` **全量 0 failed**（套件规模随并行批次增长，2026-08-25 时点为 354 项；后端由其他会话并行演进，以运行时实际为准，本契约工作不得引入任何新失败）。

## 8. 并行与验证流程

- 子代理 A（TSX 逻辑+集成）与子代理 B（CSS）**并行**，文件所有权隔离；
- 两者完成后由验证代理按 §7 逐条核查 + 跑三门禁；
- 任何一方需要改契约 → 停手上报，不得自行偏离。
