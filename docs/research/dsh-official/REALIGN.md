# DSH 升级后：文档与记忆的重对齐手册

**谁用**：业主让**别的对话**去升级 DSH；升完告诉本会话，本会话按本文更新文档与记忆。
**为什么需要**：本仓 `docs/research/dsh-official/` 的 8 份分片 + Hindsight 记忆里的条目，
都是**对着某一个 DSH 版本**写的。升级后它们可能过期——而**过期不会报错**，只会让人写出对不上宿主的行为。

---

## 一、当前基线

> ✅ **升级已于 2026-09-19 完成**（业主执行，报"废了好大劲"）。本节已更新为新基线。
> **这次升级的逐条影响见 [`ERRATA-alpha.2.md`](ERRATA-alpha.2.md)** —— 哪句话过期了、现在是什么，逐条列。

| 项 | 值 | 怎么核出来的 |
|---|---|---|
| DSH 检出 | `D:\AI\DSH\deepseek-harness` | — |
| **运行中的 harness 就是这个目录** | `C:\Users\Zegel\.dsh\profiles\web\harness` 是**指向它的 Junction** | `Get-Item .../harness -Force` → `LinkType=Junction, Target=D:\AI\DSH\deepseek-harness` |
| 当前发行 tag | **`dsh-v0.1.6-alpha.2`** | `git tag --points-at HEAD` |
| 当前 sha | **`ddefc45fbc`**（`ddefc45fbc7f8e46dd73185e68295696d1297887`） | `git rev-parse HEAD` |
| package.json version | `0.1.6-alpha.2` | — |
| **上一次基线**（8 份分片与 Hindsight 条目写的是它） | tag `dsh-v0.1.6-alpha.1` / sha `0a15e36e7f` / version `0.1.6-alpha.1` | 分片口径；`-From` 默认值现在已改为 alpha.2 |
| 文档量（现在） | **171 篇英文正本 / 337 篇 `.md`**（`docs/`）；基线时是 167 / 329 | `git ls-tree -r --name-only HEAD -- docs` |
| 决策记录量 | `.agents/notes/` **2056 篇**（implemented 712 / proposed 54 / rejected 28 / archived 1259） | 目录统计 |
| 我们插件的加载路径 | `ks-dsh-plugin` → `link:C:/Users/Zegel/dsh-ks-src/ks-dsh-plugin`，该路径是**指向本仓 `plugin/` 的 Junction** | profile 的 `package.json` |
| ⚠ **检出里有未提交的本地补丁** | **6 文件 +19/−6**（升级时为让 alpha.2 跑起来而打，**未提交 ⇒ 下次升级会丢**）——逐条见 ERRATA §F | `git status --short` / `git diff --stat` |

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

**现在有脚本了**（2026-09-19 起）：`scripts/ingest-dsh-docs-into-memory.mjs`
直连 Hindsight HTTP API（`POST /v1/default/banks/<bank>/memories`），**从磁盘按字节读原文**灌库。
⇒ 升级后**重灌原文不再需要手抄**（手抄实测 2.6% 失真），也不再受"子代理不能写记忆"限制。

```powershell
node scripts/ingest-dsh-docs-into-memory.mjs --dry-run   # 先看清单（会列出"将被原地覆盖"的）
node scripts/ingest-dsh-docs-into-memory.mjs             # 幂等 + 可续跑，重复跑只补差异
```

- 幂等：先 `GET /documents` 比长度，一致就跳过；`update_mode` 默认 `replace` ⇒
  同 `document_id` 再灌是**原地覆盖**，不会留两份同文。
- 对账：默认对每篇 `GET /documents/<id>` 取回 `original_text` 算 sha256 与磁盘比对
  （**逐字级证明**，比"长度一致"强）；账本写 `docs/research/dsh-official/INGEST-LEDGER.md`。
- 基线变了要重跑：源文件改了，哈希自然不同 ⇒ 会被重新灌（这正是我们要的）。

其余纪律（**仍然有效**）：

1. 先补一条 `Correction:` 件，写清"哪些条目是按哪个版本写的、现在版本变了"——
   这是 Hindsight 自己的规矩（新事实取代旧事实），比删了重灌安全。
2. 受影响的**摘要分片**重灌：最少 `dsh-a-ui`、`dsh-g-ui-inject-vs-external-peer`。
   （原文层已由上面的脚本负责；分片是"导航+提炼"层，与原文层职责不同、仍要维护。）
3. ⚠ **子代理不能写记忆**（官方插件对 `origin === "subagent"` 直接禁用，
   源码 `@vectorize-io/hindsight-coding-agents/dist/dsh.js:18114`）——
   走上面那个脚本可绕开该限制（脚本不是子代理），但**脚本是写入操作，按用户级规则须先获批**。
4. ⚠ **不要手抄长文档**：实测 77 行错 2 处（2.6%），且读起来通顺、不报错。
   逐字件只在**极短且极权威**时做，并标注"手抄，引用请回磁盘核对"。
5. ⚠ **凭记忆写 id 会制造重复事实**：我第一次写覆盖表时把 AGENTS.md 的 id 少写一段，
   "原地覆盖"静默变成"新增一份"。凡涉及 id 一律**从库里逐字读**（`GET /documents`）。

---

## 五之二、`reflect` 报 500 时：那是**服务端传输层上限**，不是请求里的 `max_tokens`

宽问题可能撞上这个 500：

```
500 {"detail":"LLM output exceeded token limits (openai/deepseek-flash, scope=reflect).
     Input may need to be split into smaller chunks."}
```

### ⚠ 更正：我第一版把根因说错了（2026-09-19，独立复核 + 我自己核源码后改）

**错的说法**（我写过、还灌进了记忆里的 `dsh` 条目）：
「`ReflectRequest.max_tokens` 默认 4096 就是输出上限，改成 8192 就好了。」

**对的说法**（0.10.0 服务端源码，逐条核过）：

| 事实 | 出处 |
|---|---|
| 请求里的 `max_tokens`（默认 4096）**不是** provider 输出上限，而是**"想要的可见长度"**，以 **prompt 指令**下达 | `engine/reflect/agent.py:794-798`、`:542-547`（注释原文：*"NOT passed as the provider's max_completion_tokens"*） |
| **真正的传输层上限** = 服务端配置 `reflect_max_completion_tokens`，**默认 `None`**（⇒ 不传该参数，用 provider 自己的默认） | `config.py:1819`；env `HINDSIGHT_API_REFLECT_MAX_COMPLETION_TOKENS`（`config.py:968/4924`） |
| 那个 500 **只在真被截断时**抛（`finish_reason == 'length'`） | `providers/openai_compatible_llm.py:372-376` |

**实测反证**：本库唯一一条 reflect 失败记录是 **`output_tokens=8192`**，而且它是
**split-synthesis 的 map 调用**（拿的是 `reflect_max_completion_tokens`，从来不是请求里的 `max_tokens`）。
⇒ 我当初"改成 8192 就成功"是**巧合**，不是修好了。

### 能真正缓解的四种办法（按建议顺序）

1. **把问题问窄**（唯一被官方报错文案也说对的建议）；
2. **`--budget low`**：少喂数据 ⇒ map 调用不容易撑爆；
3. **`--tags` 圈小范围**（配 `--tags-match any_strict` 才是"只在该域里找"，
   服务端默认 `any` 是**包含未打标签**的，不算严格作用域）；
4. 改服务端 `HINDSIGHT_API_REFLECT_MAX_COMPLETION_TOKENS` 并重启 —— ⚠ **不一定有用**：
   默认 `None` 时用 provider 自己的上限，而本库实测就是在 **8192** 上截断的；
   若 provider（`deepseek-flash`）本身上限就是 8192，**调高这个配置也超不过去**。
   （此路未实测，因为改完要重启正在用的记忆服务。）

用仓库脚本走 1–3：`node scripts/hindsight-reflect.mjs --budget low --tags <域> "问题"`
（脚本还会在 500 时明确告诉你"这不是 `--visible-tokens` 能调的"）。

**尚未纳入的语料**（想灌另说，别默认以为在库里）：

| 语料 | **实测规模（alpha.2）** | 状态 |
|---|---|---|
| `docs/**/*.zh.md` 中文译本 | **166 篇 / 2.7 MB** | ✅ **已入**（2026-09-19，`INGEST-LEDGER-docs-zh.md`，标签域 `dsh-official-docs-zh`） |
| `.agents/notes/**` 决策记录（非 zh） | **1105 篇 / 7.6 MB** | ⚠ **只入了与客户端/UI 有关的 10 篇**（`INGEST-LEDGER-notes-client-ui.md`，标签 `dsh-notes-client-ui`）；**其余 1095 篇未入** |

⚠ **更正**：本手册此前写「`.agents/notes/` 2056 篇 / 约 14.3 MB」「`.zh.md` 约 158 篇」——
**两个数都不对**（那是从分片转述里抄来的，没实测）。以本表的实测值为准。

一次命令即可补齐（脚本已支持 `--root` / `--match` / `--tag` / `--id-prefix`，语料分开记账分域）：

```powershell
# 决策记录全量（1105 篇 / 7.6 MB，约 30 分钟后台）
node scripts/ingest-dsh-docs-into-memory.mjs --root .agents/notes `
  --id-prefix dsh-notes --tag dsh-notes `
  --ledger docs/research/dsh-official/INGEST-LEDGER-notes.md
```

⚠ **灌之前想清楚**：决策记录是 **DSH 内部工程决策**，大部分与 KnowledgeStation 无关；
全量入库可能**稀释**召回（我们检索时会被 DSH 内部细节淹没）。
⇒ 建议只在确实需要"为什么这么设计"时才灌，**或**先灌某个子集（用 `--match` 限定目录/名字），
并**始终带标签域**，这样将来能用 `--tags` 把它单独圈进来或排除掉。

---

## 六、升级后还要查我们插件本身（否则可能静默坏掉）

1. **跑门禁**：`npx tsc --noEmit -p plugin/client` · `cd plugin && npm run smoke` ·
   `npm run verify:commands` · `python scripts/verify-engine-uvicorn.py` · `mypy` · `pytest`。
   ⚠ `npm run smoke` 里最后一条 `smoke-kb-page-render` 是**渲染级**用例，
   它**需要 DSH 检出里存在 jsdom/react**（用 `--harness <检出>` 或 `KS_HARNESS_DIR` 指路）；
   **找不到就明确报红**（不静默跳过）——这是有意的，别把它改成 skip。
2. **重建 + 看真机**：`cd plugin && npm run build:client`。
   ⚠ **不要再说"必须重启宿主"** —— 这句话我此前说过**两次**，**两次都被证伪**：
   alpha.1 起 `@deepseek-ai/dsh-client-hmr` 就在 `packages/bundle/web-app/cordis.patch.yml` 里
   （alpha.1 :166-167 / alpha.2 :167-168），alpha.2 又加了 `### Live graph reconciliation`（SSE、
   逐插件 `entry.refresh()`、CSS 在旧 disposer 排空后重注）。
   ⇒ **插件改动是热重载的**；只有 **bootstrap / 静态装配库 / shell** 才需要重建页面。
   （详见 `ERRATA-alpha.2.md` §D5/§H 与 §I 的 `client-plugin-loading-model` 行。）
3. **重点看这四处**（我们插件直接依赖）：
   - `sidebar.right.tab.guide.entry` 卡片的 **key 用定义 id**（不是 kind）；
   - `priority` 是**字面量 band 字符串**，不是数字、也不 import 常量；
   - **开始页胶囊的 `order` 是跨插件共享排序空间** —— 出货条目占号会被上游新增类型抢走，
     **同号 ⇒ 先后由注册顺序决定（等于随机）**。
     **已自动化**：`scripts/dsh-docs-delta.ps1` 第 7 节扫出全部出货 guide order 并与我们的
     `KS_GUIDE_ORDER_PDF` 比对，撞号打 ⛔；"一条都没扫到"会被判成**检查坏了**而不是通过。
     手工版：`git grep -l 'guide:' <ref> -- packages/client`，再逐文件看 guide 块里的 `order:`
     （⚠ 路径 glob 里的 `*` **不跨 `/`**，用 `packages/client/*/src/client` 会**静默扫空**）。
     （alpha.2 实测：files 10 / terminal 20 / browser 30；我们已让到 **25**。
     详见 `ERRATA-alpha.2.md` §K —— 这是**真实踩到的 bug**，不是理论风险。）
   - 样式注入是**运行时 `<style>`**（我们 esbuild 无 CSS loader），
     而 alpha.2 里 `tsdown.client.ts` 动了 +52/−7 —— 官方通道若是 `data-plugin-css` 那套，
     我们要考虑给自己的 `<style>` 打同样的标记。
4. **顺手该做的**（与本手册独立、但同一批）：删 `entry.ts` 的 `export default`；
   1px 中性边框 → 0.5px；改用官方 `Tag`/`Pill`/`Checkbox`；文案走 locale。
   ⚠ **`peerDependencies` 不要补** —— 我此前的建议**已被 alpha.2 推翻**：
   新文写明 Desktop「**does not recursively check peer versions, duplicate packages, linked packages,
   or ancestor dependency resolution**」（理由是那套校验重复了包管理器与 loader 的职责、且会拒掉
   pnpm 支持的安装源）。⇒ 我们**不补就是对的**，见 `ERRATA-alpha.2.md` §I 的
   `desktop-bundled-runtime-and-external-plugins` 行。

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
