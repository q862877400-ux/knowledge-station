# plugin-tools（插件对 agent 暴露的工具）

**位置**：`plugin/src/index.js`
**一句话**：这是本产品对 agent 的「手」——它只暴露少数几个动作。

## 职责

插件把引擎能力包成**模型可见的工具**。实测暴露 5 个（`plugin/src/index.js`）：

| 工具 | 用途 | 定义位置 |
|---|---|---|
| `ks_ping` | 探活（`GET /api/v1/health`，**无 token**） | index.js L820 |
| `ks_resolve_clause` | **条款定位**——按标准号/条款号取原文（`GET /clauses/resolve`，Bearer） | L908 |
| `ks_answer` | 问答（`POST /ks/answer`，Bearer） | L1075 |
| `ks_effect_report` | 效果上报 | L604 |
| `ks_materials` | 材料平面**只读** | 见 `materials_routes.js` |

**另有一批错误码常量**（不是工具）：`ks_engine_unavailable` / `ks_engine_auth` / `ks_bbox_unavailable` / `ks_doc_image_unavailable` / `ks_image_not_found`。

**它不负责**：不做业务逻辑：**插件是搬运工**，判断都在引擎里。

## 对外提供什么

| 5 个模型可见工具 | DSH 工具注册 | agent |
| 宿主桥 | `plugin/src/index.js` | DSH 宿主 |
| 侧栏 React 界面 | `plugin/client/` | 用户 |

## 依赖什么

| 引擎 HTTP API | 外部（本地） | 全部工具的落地 |
| DSH 宿主 | 外部 | 工具注册与界面容器 |

## 明确不做什么

- **MUST NOT 把能力只写在插件里**：所有能力**先进引擎的 HTTP 接口**，插件只当「其中一种入口」。
  理由：这样换宿主（或让别人接）时不用重写。（业主 2026-10-05 认可的兼容路线）
- **材料工具 MUST 保持只读**：注释里明写「**只读是纪律**：评审是用户的判断」。
- **不做检索排序**：它调引擎，不自己排。

## 已知边界（诚实）

- 🔴 **已知缺陷（登记未修）**：`plugin/client/` 三个页面（`KsCapabilityPage` / `KsChannelsPanel` / `KsKnowledgePage`）
  引用的图标导出名（`Icon*OutlineRegular`）与 DSH 当前版本不匹配，**`tsc` 报错**。
  根因是 DSH 在 2026-09-28 之后又改了图标导出名。详见 `specs/001-project-consolidation/baseline.md`。
- ⚠ **`plugin/src/*.bak-20260927-*` 是别人的未提交件**，不许动。
