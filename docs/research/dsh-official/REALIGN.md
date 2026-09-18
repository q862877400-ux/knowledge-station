# DSH 升级后：文档与记忆的重对齐手册

**谁用**：业主让**别的对话**去升级 DSH；升完告诉本会话，本会话按本文更新文档与记忆。
**为什么需要**：本仓 `docs/research/dsh-official/` 的 8 份分片 + Hindsight 记忆里的条目，
都是**对着某一个 DSH 版本**写的。升级后它们可能过期——而**过期不会报错**，只会让人写出对不上宿主的行为。

---

## 一、当前基线（**升级前就是它**）

| 项 | 值 | 怎么核出来的 |
|---|---|---|
| DSH 检出 | `D:\AI\DSH\deepseek-harness` | — |
| **运行中的 harness 就是这个目录** | `C:\Users\Zegel\.dsh\profiles\web\harness` 是**指向它的 Junction** | `Get-Item .../harness -Force` → `LinkType=Junction, Target=D:\AI\DSH\deepseek-harness` |
| 基线发行 tag | **`dsh-v0.1.6-alpha.1`** | `git tag --points-at HEAD` |
| 基线 sha | **`0a15e36e7f`** | `git rev-parse --short HEAD` |
| package.json version | `0.1.6-alpha.1` | — |
| 文档量（基线） | **167 篇英文正本 / 329 篇 `.md`**（`docs/`） | `git ls-tree -r --name-only HEAD -- docs` |
| 决策记录量（基线） | `.agents/notes/` **2056 篇**（implemented 712 / proposed 54 / rejected 28 / archived 1259） | `Get-ChildItem -Recurse` |
| 我们插件的加载路径 | `ks-dsh-plugin` → `link:C:/Users/Zegel/dsh-ks-src/ks-dsh-plugin`，该路径是**指向本仓 `plugin/` 的 Junction**，两边 `client.js` sha256 一致 | profile 的 `package.json` + `Get-FileHash` |

> ⚠️ 基线 sha 换了就要更新本表**和** `scripts/dsh-docs-delta.ps1` 的 `-From` 默认值。

---

## 二、升级后第一件事：跑这个脚本

```powershell
cd "D:\AI\work space\zcode"
pwsh -NoProfile -File scripts/dsh-docs-delta.ps1            # 默认 From=基线 tag, To=HEAD
```

它**只读**，把 diff 收敛到「我们的东西」上，输出五节：

1. **分片引用到的 43 条路径里，谁变了**（带改动行数——用来判断"要重读"还是"只需核对"）
2. 新增的文档（英文正本）
3. 新增/移除的包
4. 我们插件挂靠的 4 个客户端包改了多少
5. 契约关键词与 `ui-primitives` 组件是否还在（**不存在 ⇒ 我们的插件会坏或要改写法**）

---

## 三、已经实测过的 delta：`alpha.1 → alpha.2`（2026-09-19 跑出，存档备用）

整体：**887 commit（非 merge 548）· 2622 文件 · +101460 / −23708**。
`alpha.2` 的 commit `ddefc45fbc` **同时就是当时的 `origin/master` tip**（所以"首页 master"与"最新发行版"当时是同一个点）。

### ① 分片引用到的路径：**19 条变了**（只有这些需要看）

| 变化 | 路径 | 改动量 | 对我们的含义 |
|---|---|---|---|
| M | `docs/subsystems/sidebar-right.md` | +10 / −5 | 右栏契约说明——**分片 A/G 的命根子** |
| M | `docs/subsystems/slots.md` | +10 / −6 | 槽位目录——同上 |
| M | `docs/subsystems/client-modules.md` | +13 / −12 | 客户端模块加载——分片 A |
| M | `docs/subsystems/client-resources.md` | +2 / −1 | 资源模型——分片 A |
| M | `docs/subsystems/web-client.md` | +4 / −4 | 分片 A |
| M | `docs/web-styling.md` | **+1 / −1** | 样式权威——分片 G；**我们入库的"逐字件"就是它，必须换** |
| M | `docs/AGENTS.md` | **+1 / −1** | 同上，也是我们入库的逐字件 |
| M | `docs/architecture.md` | +7 / −5 | 分片 C |
| M | `docs/cordis-api/inherited.md` | −3 | 分片 B |
| M | `docs/config-catalog.md` | **+199 / −15** | 生成物，体积大但只影响"查法"不变 |
| M | `docs/user/develop/practice/dynamic-cordis.md` | +8 / −8 | 分片 C |
| M | `docs/user/guide/python-sdk.md` | +40 / −20 | 分片 C |
| M | `packages/client/tsdown.client.ts` | **+52 / −7** | **构建 preset**——直接关系"样式怎么注入"（我用的是运行时注入 `<style>`） |
| M | `packages/client/ui-sidebar-right/src/client/index.ts` | +6 / −2 | 我们挂载的包 |
| M | `packages/client/ui-sidebar-terminal/src/client/index.ts` | +14 / −4 | **我们那张卡的模板来源**（`key: id` 与 guide 注册） |
| M | `packages/bundle/web-app/cordis.patch.yml` | +36 / −11 | 宿主图编排 |
| M | `scripts/gen-config-catalog.ts` · `gen-tool-catalog.ts` · `run-gates.ts` | 小 | 生成器/门禁 |

### ② 新增文档 4 篇（**都是新子系统的**）

`docs/subsystems/boot.md`(159行) · `docs/subsystems/deliverables.md`(150行) ·
`docs/subsystems/office-to-pdf.md`(60行) · `docs/persistence-changes/2026-09-14-workspace-changes-event.md`(34行)

### ③ 包：290 → **298**（新增 9 / 移除 1）

```
+ packages/boot/hmr                       + packages/deliverables/tool-present
+ packages/boot/plugin-manager            + packages/deliverables/workspace-changes
+ packages/client/ui-plugin-manager       + packages/document/office-to-pdf
+ packages/client/ui-sidebar-browser      + packages/skill/skill-office
+ packages/util/lazy-require
- packages/fs/tool-present        （并进 deliverables/tool-present）
```

### ④ 我们挂靠的包

| 包 | 改动 |
|---|---|
| `packages/client/ui-primitives` | **36 文件，+1394 / −81** ← 最大，正是我们计划改用 `Tag`/`Pill`/`Checkbox` 的地方 |
| `packages/client/ui-slots` | 8 文件，+710 / −68 |
| `packages/client/ui-sidebar-right` | 20 文件，+649 / −39 |
| `packages/client/ui-dockkit` | 2 文件，+5 / −2 |

### ⑤ 契约与组件：**全部仍在**（✅）

`sidebar.right.pane.tab` · `sidebar.right.tab.guide.entry` · `sidebarRightTabs` · `useTabInfo` ·
`useResource` · band 字面量 `'extension'` · `data-plugin-css` —— 一个都没消失。

`ui-primitives` barrel 导出实测可用：`Button` `Menu` `IconChevronDownOutline14` `Tag` `Pill` `Input`
**`Checkbox`（新增，正好替我手搓的勾选框）** `Switch` `StateDot` `DisclosureRow` `Tooltip` `Toast`。
且 `Button`/`Menu` 的**签名写法两版一致**（`export function Button(...)` + barrel 再导出），
我们现在的用法（`Button variant="ghost"` / `Menu open portal autoFocus align items onClose onSelect anchor`）**不用改**。

---

## 四、逐分片判定清单（升级后照这个走）

| 分片 | doc_id | 依赖的文件这次动了吗 | 判定动作 |
|---|---|---|---|
| A 客户端半边 | `dsh-a-ui` | sidebar-right · slots · client-modules · client-resources · web-client **全动** | 逐篇看上述 5 处 diff（共约 39 行），核对"槽位目录/静默失败/不许自己造"是否仍成立 |
| B 插件契约与生命周期 | `dsh-b-effect-26` | `cordis-api/inherited.md`(−3) | 只需核对那 3 行 |
| C 官方菜谱 24 条 | `dsh-c-24` | architecture · dynamic-cordis · python-sdk · config-catalog | 看 4 处 diff；config-catalog +199 只看"查法"是否变 |
| D 宿主半边 | `dsh-d-llm-projection` | 本批未列（session/llm-streaming/subagent 未在 19 条内） | 若脚本这次列出才动 |
| E 持久化/配置/事件 | `dsh-e-ctx-fs` | config-catalog 同 C | 同 C |
| F 破坏性变更/i18n | `dsh-f-i18n` | 需另查 `docs/persistence-changes/` | 跑一次 `git diff --name-status <from> <to> -- docs/persistence-changes` |
| G 客户端 UI 决策记录 | `dsh-g-ui-inject-vs-external-peer` | **web-styling(+1/−1) · ui-sidebar-right/index.ts · ui-sidebar-terminal/index.ts · tsdown.client.ts(+52/−7)** | 重点看 `tsdown.client.ts`（样式注入通道）与两个 `index.ts`（注册写法） |
| H 官方技能与门禁 | `dsh-h-12` | `scripts/run-gates.ts`(+3/−1) 等 | 跑一次 `git diff <from> <to> -- .agents/skills scripts/run-gates.ts` |
| 逐字件：`web-styling.md` / `docs/AGENTS.md` | 见下 | **两篇都各改 1 行** | **必须重新入库**（旧的已过期） |

---

## 五、记忆怎么更新（Hindsight，`coding-agent::zcode`）

1. **先补一条 `Correction:` 件**，写清"哪些条目是按哪个版本写的、现在版本变了"——
   这是 Hindsight 自己的规矩（新事实取代旧事实），比删了重灌安全。
2. 受影响的条目**重灌**（用 `hindsight_ingest_document`，标题沿用原 doc_id 对应的标题 + 新版本号），
   最少要重灌：`dsh-a-ui`、`dsh-g-ui-inject-vs-external-peer`、两份 `DSH 原文 …`。
3. ⚠ **子代理不能写记忆**（官方插件对 `origin === "subagent"` 直接禁用，
   源码 `@vectorize-io/hindsight-coding-agents/dist/dsh.js:18114`）——**必须由主会话本人入库**。
4. ⚠ **不要手抄长文档**：实测 77 行错 2 处（2.6%），且读起来通顺、不报错。
   逐字件只在**极短且极权威**时做，并标注"手抄，引用请回磁盘核对"。

---

## 六、升级后还要查我们插件本身（否则可能静默坏掉）

1. **跑门禁**：`npx tsc --noEmit -p plugin/client` · `cd plugin && npm run smoke` ·
   `npm run verify:commands` · `python scripts/verify-engine-uvicorn.py` · `mypy` · `pytest`。
2. **重建 + 看真机**：`cd plugin && npm run build:client`，然后**必须重启 DSH 宿主**（生产模式无 watcher，
   bundle 图只在启动时组合）才可能看到新 UI。
3. **重点看这三处**（我们插件直接依赖）：
   - `sidebar.right.tab.guide.entry` 卡片的 **key 用定义 id**（不是 kind）；
   - `priority` 是**字面量 band 字符串**，不是数字、也不 import 常量；
   - 样式注入是**运行时 `<style>`**（我们 esbuild 无 CSS loader），
     而 alpha.2 里 `tsdown.client.ts` 动了 +52/−7 —— 官方通道若是 `data-plugin-css` 那套，
     我们要考虑给自己的 `<style>` 打同样的标记。
4. **顺手该做的**（与本手册独立、但同一批）：删 `entry.ts` 的 `export default`；
   1px 中性边框 → 0.5px；改用官方 `Tag`/`Pill`/`Checkbox`；补 `peerDependencies`；文案走 locale。

---

## 七、踩过的坑（别再踩）

- **浅克隆会造成"假强推"**：本仓被 `git fetch --depth=1` 抓过，`--depth=1` 下 `merge-base` 判不出祖先，
  我据此说过"master 被强推"，**加深后证明是错的**（alpha.1 是 alpha.2 的祖先，正常递进）。
  ⇒ 脚本里已加浅克隆警告；判祖先前先 `git fetch --depth=400 origin <tag>`。
- **探针字符串别写死**：我第一版用 `export const Button` 查组件，两版都报 ❌ 的**假警报**——
  `ui-primitives` 用的是 `export function Button(...)` + barrel `export { Button } from './Button.tsx'`。
  ⇒ 脚本已改为查 barrel 的 `export { X }`，并对 `export { X, Y }` 多成员写法加了兜底。
- **`referenced-files.txt` 是抽取下限**：分片里用相对路径写的引用（如 `subsystems/xxx.md`）抓不到，
  所以"没列进 ①"**不等于**"没变"。要更全就在升级后按分片各自声明的"读取范围"补查。
