# VERIFY-REPORT · spec 007（UI 精修）第二轮独立复核

- 复核人：teammate `verifier2`（worker 角色，可跑命令、可写本报告）
- 冻结点：tag `step-368-ui-polish-spec007-r2` = `d79ec7c8`；提取树 `D:\AI\verify-trees\spec007-ui-polish`（`git worktree add`，依赖为**真拷贝**的 `plugin/node_modules` + 仓库根 `node_modules`，非 junction）
- **开头记录（提取树）**：`git rev-parse HEAD` = `d79ec7c8cd53d3b662f8fd8931dbd2242dd5274b`，`git status --short` = 空
- **结尾记录（提取树）**：HEAD 同上，`git status --short` = 空（全部变异已逐字节还原，见 §7 台账）
- 主仓复核时点 HEAD = `9df6d8b7`（冻结后另有他线提交，与本批无关；故全部验证在提取树做）

## 0. 判定

**PASS** —— 三条被验修复（R1/R2/R3）**全部真堵住了，不是只堵住举例**（逐条证据见 §1–§3）。基线三连全绿、产物↔源码一致、kb-detail 既有红复现、禁碰区不越界。

同时报出 **P1 × 1**（新发现的相邻缺陷：配置态 Key 框 placeholder 仍被截 3px——R3 修复让它从"恒不可见"变"可见"）与 **P2 × 6**。无 P0。

## 1. R1（判据③"裹注释"假绿）→ **真堵住了**；另发现一个 P2 残余洞（`//` 行注释）

**源码级**：`plugin/scripts/smoke-ui-scale.mjs` 第③段引用与定义两个循环现在都跑在 `withoutComments` 上（`d79ec7c8` 的 diff 逐行核对：两处 `rawBody.matchAll` → `withoutComments.matchAll`）；`rawBody` 只剩第 176 行"剥除量会计"在用。第一版空洞（未剥注释同时抠引用与定义）的描述与 diff 事实一致。

**变异记录**（变异对象 `plugin/client/ksGuideStyles.ts`，基线 sha256 `9696AA9D91E095D7DFAA00FCF5D4D5485757262459609F6BE30A210F480D4744`）：

| # | 变异 | 跑出什么 | 判读 |
|---|---|---|---|
| M-R1a | L75 定义整行裹块注释 `/* --ks-radius:var(--dsw-radius-md); */` | **exit 1**，`定义 53 ⇒ 缺失 --ks-radius` | **旧洞堵上**（旧写法此形态报绿）✅ |
| M-R1b | 同行改 `// --ks-radius:…;`（行注释形态） | **exit 0，仍绿** | **残余洞（P2-1）**：剥除器只认 `/* */`；而 CSS 里 `//` 开头的声明**非法**、浏览器**不会**定义该 token ⇒ 判据绿、浏览器病还在（与被修的病同类） |
| M-R1c | 一行内嵌套 `/*`（`/* 定义; /* 理由 */`） | **exit 1**，缺失 `--ks-radius` | 非贪婪剥除从第一个 `/*` 到第一个 `*/`，与 CSS 注释语义一致 ⇒ 红 ✅ |

还原后 sha256 与基线一致、`git status --short` 空（三次各还原核对过）。

**未变异、按口径推断的形态**（写明这是推断不是实测）：
- 未闭合的 `/*`：正则与 CSS 都在**下一个** `*/` 收口 ⇒ 两侧行为一致，不构成分歧；
- 定义写在 `KS_STYLES` 之外：判据会**红**（口径 1 明写"定义必须在本文件"）——fail-loud 方向，不是假绿；
- **作用域型**（`.b{--ks-x:…}` 定义、`.a` 里引用）：正则口径天然不判作用域，理论假绿方向——**未验**（要构造 DOM 级反证，成本超出本条判据的定位），记入 §8。

**判定：R1 真堵住了**（举例形态 + 嵌套形态都红；引用侧剥过注释后"注释里的引用"也不再计数，方向一致）。残余 `//` 洞降级为 P2 的理由：CSS 模板里写 `//` 不是本仓现有形态，且脚本头部"注释不算"的口径本来就只声明了块注释；但它确实能让"浏览器里不存在的定义"判绿，该修（剥除器补一条 `//[^\n]*` 即可，注意先于块注释处理或按序处理避免误伤 URL 里的 `//`）。

**顺带核第一轮复核者的更正**："`--ks-radius :`（冒号前带空格）不是漏洞"——**成立**。零变异实测：定义正则 `/(--ks-[a-z0-9-]+)\s*:/` 对 `--ks-radius :` 照样命中；CSS 声明中属性名与冒号之间的空白合法，浏览器语义上确实定义了 ⇒ 判绿是对的。

## 2. R2（宽度依赖假绿）→ **真堵住了**（默认档即抓）；`--width 1018` 仍 PASS 属实且**不是开脱**

**源码级**：`PAGES.settings.width` = **600**（`ui-render-shot.mjs` L166），注释完整记录了"为什么不是 1018"的更正留痕。

**实测矩阵**（修复态 = 现提交的短 placeholder `Base URL（可留空）`；变异态 = 改回长句 `Base URL（留空保持不变；输 "-" 恢复内置默认）`，变异对象 `KsSettingsSection.tsx`，sha256 `255CFB6373E1DD27745EAFC6CF424AEB1F372EE6CB58717A3791C5BBAB05E6B9`，还原核对一致）：

| 跑 | 结果 |
|---|---|
| 修复态 @400 / @600（默认） / @1018 | 三档全 **PASS**（exit 0）——与 tasks.md T021 判据一致 |
| 长 placeholder @600（**不传 --width，默认档**） | **exit 1**：`文字实宽 266px > 框内可用 222px` —— 与 tasks.md 预言**逐字一致** ✅ |
| 长 placeholder @1018 | **exit 0（PASS）**；rows 实测 `textW=266, innerW=396`（第二通道 540） |

**对"1018 档仍 PASS"的独立判定**：**作者的说法成立，且不是替判据开脱**——
- 事实层：266 < 396，1018 档下文字**真的放得下** ⇒ PASS 是对那一档的**真命题**，不是假绿（假绿的定义是"有病判没病"；这一档真没病）。
- 门禁层：默认宽度已挪到**能复现截断的 600**，`ui-render-shot.mjs` L164–165 明写"判据不靠调用方记得传对宽度"——我实测默认命令（不带任何参数）即红 ✅。
- 但要如实记录两个边界：**(a)** settings 判据**不在 `smoke-all` 门禁链里**（tasks.md T021 自己声明"不许进 MATRIX……用单独命令量"）⇒ 它的保护强度 = "记得跑文档命令"，这不是本批新问题、是已声明的取舍；**(b)** 判据只对它渲染的那一档说话，"真机设置弹窗可用宽 ≈600"是**推断**（真机观察记录的是窗口宽 1018/1576，弹窗可用宽无存档读数）。若要硬化：同一跑内扫 400/600/1018 三档、逐档给判定（T021 本来就手工跑过三档，自动化代价低）。以上记 **P2-2**。

**P2-3（顺手记）**：`#settingsform` 的 **PASS 打印只报溢出**（"都不越过所在行的内容盒右缘"），不提 `clipped` 这条判据也在判。判据本身有牙（M-R2 的红就是 `clipped` 触发的）、JSON 里有 `clippedCount`，但只看 PASS 行的人会以为只判了溢出。

## 3. R3（已配置态 Key 框不被量）→ **真堵住了**（选择逻辑 + 运行时双重实证）；带两个新发现

**源码级**：挑选逻辑（L2423–2434）= `所在行(parentElement)有保存/测试按钮` **或** placeholder 含 `Base URL`/`API Key`。已配置态 Key 框 placeholder「Key 已配置（留空保持不变；输 "-" 清除）」不含两关键字，但它与 Base URL 框同行、行内有「保存」「🧪 测试连通」按钮（`KsSettingsSection.tsx` L1531–1542）⇒ 按位置被收。注意：注释 L2420 说"不靠 placeholder 文案"**略有夸大**——关键字仍在 OR 兜底里（放宽方向，无害，但口径描述与代码不完全一致，记 P2-4）。

**运行时实证的关键障碍（先如实记录）**：默认跑里两通道恒为**未配置态**——`PROPS.settings` 不喂 api-config 数据、脚本的 fetch 桩**没有** `/ks/settings/api-config` 端点 ⇒ `fetchApiConfig()` 必失败 ⇒ `configured=false`。要看到配置态必须另设实验：

**变异记录**（两个文件，均还原核对）：

| # | 变异 | 跑出什么 |
|---|---|---|
| M-R3a | `ui-render-shot.mjs` fetch 桩加 `GET /ks/settings/api-config` → 两通道 `configured:true`；单跑 | **仍全未配置** ⇒ 发现：`settings-creds` 点击后 `details.open===true`（mustLand 过、exit 0）但 React 的 `onToggle` 在 jsdom 里**不触发** ⇒ `apiOpen` 状态没变 ⇒ `useEffect` 不跑 `load()` ⇒ SSR 恒未配置。**shipped harness 的文档命令永远量不到配置态**（P2-5，作者未声明此限制） |
| M-R3b | 桩（修正为扁平形状 `{ok, mineru_cloud, llm}`——第一版照 `/ks/channels` 写成 `{ok,data}` 被 `fetchApiConfig` 的形状校验拒了）+ `KsSettingsSection.tsx` `apiOpen` 初始 `useState(false)`→`(true)`；`--interact ""` | rows 含 **`Key 已配置（留空保持不变；输 "-" 清除）` ×2** ⇒ **配置态 Key 框被量到了** ✅；且实测 **`clipped:true`，textW 223 > innerW 220** ⇒ 整跑 exit 1 |
| M-R3c | 同上两变异 + 挑选逻辑**退回旧版**（只认两关键字） | **n=2**（只剩两个 Base URL 框），`Key 已配置` 完全不量，带着 223>220 的截断 **exit 0 绿着** ⇒ 旧逻辑确实漏、新逻辑堵上，差异实锤 |

还原后：`KsSettingsSection.tsx` = `255CFB63…`、`ui-render-shot.mjs` = `6936C81EE6B5950DB28BE97C3B562FFD15BA049B4A335504363A7468694D7C6B`，均与变异前一致；`git status --short` 空。

**新发现 A（P1-1）**：**配置态 Key placeholder 本身超宽 3px**（`Key 已配置（留空保持不变；输 "-" 清除）` 实宽 223px > 框内可用 220px）。Key 框是定宽 220（`flex:'0 0 auto'`），**与窗口宽无关** ⇒ 真机配置态下收尾 `）`同样被截 ~3px。这是 D3 同族病（"框放不下自己的说明"），批前就存在、被旧挑选逻辑恒掩盖，R3 修复让它显形。视觉上轻微（一个全角括号的左侧 ~1/4），但恰是 spec 007 D3 的靶子类缺陷，且现判据在 shipped harness 里**永远看不见它**（P2-5）。修法建议：Key 框 220→228，或该 placeholder 再缩一句。

**新发现 B（核对性）**：settings 面共 5 个 input，第 5 个是「显示红色定位箭头」checkbox（证据查看器类目）——非凭据输入框，旧/新挑选都不收它，**正确**。源管理加源表单的两个 input（`源名称`/`https://…`）在本跑 SSR 里未渲染（其类目数据未喂），未构成覆盖面问题，如实记录。

**判定：R3 真堵住了**（M-R3b/M-R3c 对照实验），但要附带说明：**"会被量到"在 shipped 命令的常态跑里并不发生**——常态只能量到未配置态（P2-5）；配置态覆盖是我注入桩+初始态才实证到的。

## 4. 读数复现（任务书 item 4/5）

| 命令（提取树内实跑） | 结果 |
|---|---|
| `npx tsc --noEmit -p plugin/client` | **exit 0** ✅（⚠ 任务书写 `-p client`：树根无 `client` 目录会 TS5058，实际路径 `plugin/client`——就地更正） |
| `node plugin/scripts/smoke-client-entry.mjs` | **205/205 PASS、exit 0** ✅；含关键断言「交付产物与从源码现构建**整份一致**：交付 1770066 字符 / 现构建 1770066 字符」 |
| `node plugin/scripts/smoke-ui-scale.mjs` | **exit 0**：引用 48 / 定义 54 / 缺失 0（带兜底放行 1：`--ks-font-mono`）✅ |
| `node plugin/scripts/ui-render-shot.mjs --page settings` | exit 0，`n=4`、`clippedCount=0`（未配置态）✅ |

（任务书简写 `scripts/smoke-client-entry.mjs` 实际在 `plugin/scripts/` 下——首次按简写跑会 MODULE_NOT_FOUND，属路径笔误非产品问题。）

## 5. 产物一致性（item 5）与 lead 的"字节数没变"说法

- `git show --name-status`：`1ee35df0`（本批产品提交）**重建了** `plugin/client.js`（同批改了 `KsSettingsSection.tsx` + `ksGuideStyles.ts`，不重建才是问题）；`d79ec7c8`（复核驱动修复批）**只动两个脚本** ⇒ **lead 说的"这批 client.js 字节数没变"成立**（构造上未触碰）。
- 交付产物关键标记在场核验（node 文件级探针，见 §9 方法更正）：新短 placeholder `Base URL（可留空）` ✅、配置态 `Key 已配置（留空保持不变` ✅、`粘贴 API Key` ✅、`--ks-radius` ✅、类目名 `API配置` ✅；**旧长 placeholder 不在场** ✅（产物跟上了源码）。产物内 CJK 是**大写十六进制 `\uXXXX` 转义形态**（如 `\u53EF\u7559\u7A7A`），raw 检索全为假阴性是正常形态不是缺失。
- 加上 smoke-client-entry 的"交付 == 现构建（1770066 字符）"断言 ⇒ **产物与源码一致成立**。

## 6. 其余三项

**加法边界（item 6）✅**：`--page kb` 默认档打印 `· #settingsform 自检：**这一跑不判**（本页不是设置面（page=kb）—— 凭据表单可见性这一跑不判）`，exit 0——"不判"是**打印出来的**，不是静默。

**kb-detail 既有红（item 7）✅ 独立复现**：当前脚本 `--page kb --interact kb-detail` → **exit 1**，报 `kb|kb-detail 没有在 PAD_REQUIRED 里声明期望元素`；用 `git show c136363b:plugin/scripts/ui-render-shot.mjs`（临时落 `plugin/scripts/_verify-old-render.mjs`，跑完已删）跑同一场景 → **同样 exit 1、同一句红** ⇒ "既有状态、非本批回归"主张成立。

**禁碰区（item 8）✅，但任务书的基写错了（就地更正）**：任务书让核 `git diff 1ee35df0..d79ec7c8 -- KsSettingsSection.tsx` 的 hunk 头——**该区间零 hunk**，因为 `1ee35df0` 本身就是本批的产品提交（改动已在其中），从它起 diff 自然为空，这个检查形式上恒过、没有内容。**正确基 = `c136363b`（= `1ee35df0~1`，恰是作者自己给"冻结前脚本"用的同一提交）**：`c136363b..d79ec7c8` 共 4 个 hunk，新侧行号 **1501–1549**，hunk 头上下文函数全是 `KsApiConfigSection` ⇒ 按 137–213（第一轮更正口径）与 137–336（任务书原口径）**都不越界** ✅。本批产品文件面 = `KsSettingsSection.tsx` + `ksGuideStyles.ts` + 两脚本，与自述一致。

**诚实边界（item 9）✅ 一致性核验通过，现场未复现（如实声明）**：`docs/UI-BASELINE.md` §五.一（2247–2253 行）与 `docs/DEVELOPMENT-HISTORY.md` §10.232 两处**一致**写明"四个主面没能在真宿主点进去、改用离屏渲染、**不是真机**"；控制台报错归因**宿主主包** `assets/index-*.js`（Vite 宿主产物命名，非插件 `ks-dsh-plugin/client.js`）——归因内部自洽。**未验**：2026-10-10 的 GUI 现场无法复现（宿主已前进），"会话树渲染不出节点 + TypeError"这一**原因**陈述我未独立观察；"真机看到缺陷的是设置面"无存档截图（沿第一轮结论）。无过度声称。

## 7. 变异台账（每次 sha256 + 还原核对）

| 变异 | 文件 | 还原后 sha256（与变异前一致） |
|---|---|---|
| M-R1a / M-R1b / M-R1c | `plugin/client/ksGuideStyles.ts` | `9696AA9D91E095D7DFAA00FCF5D4D5485757262459609F6BE30A210F480D4744` ✅ |
| M-R2 | `plugin/client/KsSettingsSection.tsx` | `255CFB6373E1DD27745EAFC6CF424AEB1F372EE6CB58717A3791C5BBAB05E6B9` ✅ |
| M-R3a/b/c（桩 + 挑选逻辑两处） | `plugin/scripts/ui-render-shot.mjs` | `6936C81EE6B5950DB28BE97C3B562FFD15BA049B4A335504363A7468694D7C6B` ✅ |
| M-R3b/c（apiOpen 初始态） | `plugin/client/KsSettingsSection.tsx` | 同上 `255CFB63…` ✅ |

临时产物：`plugin/scripts/_verify-old-render.mjs`（旧脚本对照）已删；`var/tmp/verify-marker-probe.mjs`（关键标记探针）留在提取树 `var/tmp/`（gitignore 内，`git status` 不显示）；截图/HTML 在提取树 `var/tmp/ui-shots/`（同上）。

## 8. 发现分级汇总

- **P1-1**：配置态 Key 框 placeholder 超宽 3px（223>220，定宽、与窗口宽无关）——D3 同族病，R3 修复后显形，shipped harness 恒看不见（与 P2-5 叠加）。建议：Key 框 220→228 或再缩该 placeholder。
- **P2-1**：判据③对 `//` 行注释形态仍会假绿（M-R1b 实测 exit 0）。
- **P2-2**：settings 判据不在 `smoke-all` 链（既有已声明取舍）+ 真机弹窗可用宽 ≈600 属推断；建议同跑扫 400/600/1018 三档。
- **P2-3**：`#settingsform` PASS 打印不提 `clipped`（只报溢出）。
- **P2-4**：`ui-render-shot.mjs` L2420 注释"不靠 placeholder 文案"与代码（OR 关键字兜底仍在）不完全一致。
- **P2-5**：shipped harness 的 settings 跑**到不了配置态**（jsdom 里 React `onToggle` 不触发 ⇒ `load()` 不跑 ⇒ SSR 恒未配置）——R3 的配置态覆盖在常态门禁里不生效，需作者声明或给桩。
- **P2-6**：`docs/DEVELOPMENT-HISTORY.md` §10.232 编号重复（483 行 gov-qa / 484 行 UI 精修）——第一轮已发现，本轮确认仍在。

## 9. 方法更正留痕（我自己的错话，不悄悄删）

1. **inline `node -e` 的 CJK 探针不可信**：我先三轮用 `node -e "…s.includes('粘贴 API Key')…"` 检查产物，全部假阴性（`raw:false esc:false`）——CJK 经 pwsh 命令行传给 node 时被编码损坏；`--ks-radius`（纯 ASCII）能中就是铁证。改用**文件版纯 ASCII 探针**（JS 源内 `\uXXXX`）后五个标记全部在场。**上面 §5 的结论以文件版探针为准。**
2. **M-R3a 第一版桩形状错了**（`{ok,data:{…}}`）：`fetchApiConfig` 的形状校验（`body.ok !== true` 或字段缺失即抛）要求**扁平** `{ok, mineru_cloud, llm}`；我先照 `/ks/channels` 的 `{ok,data}` 形状写、跑出"仍全未配置"，一度误判成"桩没接上"，实际是形状被拒。修正后才有 §3 的结果。
3. **任务书两处口径错误**（更正见 §4/§6）：`-p client` → `-p plugin/client`；禁碰区 diff 基 `1ee35df0..` → `c136363b..`（原基下检查恒空、无内容）。

## 10. 明确未验（不许被读成"验过"）

- 真宿主（DSH Web GUI）现场：四个主面点不进去的**原因**（会话树空节点 + 宿主 `TypeError`）未独立复现——2026-10-10 现场不可重现，宿主已更新。
- "真机看到缺陷的是设置面"：无存档截图可查（沿第一轮）。
- 判据③的**作用域型**假绿方向（`.b` 定义 `.a` 引用）与 `content:"…*/…"` 字符串内 `*/` 形态：未构造反证。
- `smoke-settings.mjs` / `smoke-settings-guard.mjs` / `run-gates.ps1` / `smoke-all.mjs`：**未跑**（前者不在任务书基线内；后两者有全局锁，任务书明令不跑）。
- 400 档配置态、dark 主题下的 settings 面：未跑（本批判据只声明了 light 默认档）。
- 深色主题、`--nav-page channels` 等其余面：本批未触碰，未验。
