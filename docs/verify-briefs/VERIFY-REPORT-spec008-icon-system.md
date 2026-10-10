# VERIFY-REPORT · spec 008（图标体系）—— **自查**（非独立第三方）

> ⚠⚠ **本报告的性质必须先说清**：这是**我自己做的核查**，**不是独立第三方复核**。
>
> **为什么是自查**：团队复核机制在本环境下**三次派发全部失败** ——
> 第一任（`verifier3`）跑到一半进程失败（已完成建提取树 + 复现 `smoke-all` 43/43）；
> 第二、三任（`verifier4`/`verifier5`）在**创建时** `initial prompt was not durably accepted`（durable 确认超时）；
> 第四任（复用 `verifier2`）也进程失败、未留下任何产物。
> ⇒ 我改用**与复核相同的纪律**自己做：**在冻结提取树里验**、**自己造变异**、**逐字节还原**。
>
> ⚠ **自查的固有弱点**：我对自己的实现有先入之见，**看不出的错就是看不出**。
> 本报告**不能**替代独立复核；下面每条都给了可复算的命令，供任何第三方复现。

---

## 0. 冻结与现场

| 项 | 值 |
|---|---|
| 冻结点 | `2c8fbf05`（tag `verify-freeze-spec008-icon-system`） |
| 提取树 | `D:/AI/verify-trees/spec008-icon-system`（`git worktree add`，依赖**真拷贝**：`plugin/node_modules` + 仓库根 `node_modules`，非 junction） |
| 提取树开头 | `git rev-parse HEAD` = `2c8fbf05cb39dfadeb354fe9780cd3a39ef5d649`；`git status --short` = **空** |
| 提取树结尾 | 同上；`git status --short` = **空**（全部变异已逐字节还原） |
| 复算脚本 | `var/tmp/verify008-independent-mutations.py` |

## 1. 判定

**PASS（自查口径）** —— 三组判据**八条变异全部符合预期**；
并在自查中**发现并修掉一个真漏洞**（见 §3），该修复**不在冻结点内**，已单独提交 `6f0fb9fd`。

## 2. 读数复现（在提取树里跑）

| 命令 | 结果 |
|---|---|
| `npx tsc --noEmit -p client` | **exit 0** |
| `node scripts/smoke-icon-system.mjs` | **exit 0**（尺寸显式 18/18 ｜ Button 内嵌 0 ｜ 死声明 0） |
| `node scripts/smoke-client-entry.mjs` | **205/205 PASS** |
| `node scripts/smoke-all.mjs` | **43/43 套 · exit 0**（第一任复核者已复现；我在主仓也复现过） |
| `run-gates.ps1 -Full` | **10/10 · exit=0**（主仓；并行线占锁时退出码 3 = 有人在跑，等锁释放后跑） |

## 3. ★ 自查发现并修掉的真漏洞（判据③口径）

### 漏洞
判据③原来只认 `export const IconXxx`，**漏掉别名导出**。对抗性构造：

```ts
// 在 ksHostPrimitives.d.ts 末尾加一行
export { Button as IconFakeAliasOutlineRegular }
```

⇒ 判据 **exit 0（绿）**，而那个名字**并没有真的作为一个图标被声明**（它是 `Button` 的别名）⇒ **假绿**。

### 修法
两种声明形态都认：① `export const IconXxx…`；② `export { … as IconXxx … }`（抠 `as` **后面**的名字）。
⚠ 反过来**不**把 `export { IconXxx }`（无 `as`）算成新名字 —— 那只是转出，名字在别处声明。

### 修复后的验证
⑧ 现在 **exit 1 命中判据③**（漏洞堵死）；原样件仍 **exit 0**。

## 4. 八条变异（在冻结提取树里逐条打，全部逐字节还原）

| # | 变异 | 期望 | 实测 |
|---|---|---|---|
| ① | 删一处 `size={16}` | 红 | ✅ exit 1 命中判据① |
| ② | `size={14}`（不在允许档） | 红 | ✅ exit 1 命中 |
| ③ | `size={32}`（不在允许档） | 红 | ✅ exit 1 命中 |
| ④ | `size = {16}`（等号带空格） | 红 | ✅ exit 1 命中 |
| ⑤ | 图标跨行书写（无 size） | 红 | ✅ exit 1 命中 |
| ⑥ | `icon` prop 改回 children | 红 | ✅ exit 1 命中判据② |
| ⑦ | 加一条死声明（`export const`） | 红 | ✅ exit 1 命中判据③ |
| ⑧ | **`export { X as IconFake }`（对抗）** | 红 | **修前绿（漏洞）→ 修后 ✅ exit 1** |

变异全部还原后复跑 **exit 0**。

## 5. 尺寸统一的独立复核（真浏览器 DOM 读数）

复算：`var/tmp/measure-icons.py` + `var/tmp/icon-system-audit.py`（读 `ui-render-shot` 写出的自包含 HTML）。

| 页面 / 档位 | 修前 | 修后 |
|---|---|---|
| kb @520 | `{14:12, 16:17}` | **`{16:29}`** |
| kb @1300 | — | **`{16:29}`** |
| capabilities @520 / @1300 | `{14:3}` | **`{16:3}`** |
| ingest / materials / settings | 本轮渲染**无 svg** | 同（无 svg） |

⇒ **凡本轮渲染到图标的页面，尺寸 100% 统一到 16**；同容器混用 **0 处**。
⚠ **诚实边界**：`ingest` / `materials` / `settings` 三页在这几跑里**没有 svg** ⇒
它们的图标**没有被量到**，**不能**声称"没问题"。

## 6. 几何没被撑破

`ui-render-shot --page kb`（520 与 1300 两档）全部自检通过：
`#cols` / `#kbtree` / `#dircols` / `#rows` / `#dirhead` / `#kspad` —— **列宽、行高、留边与改动前一致**。

## 7. 禁碰区

`git show --name-only 2c8fbf05` 的改动面：
`plugin/client/{KsCapabilityPage,KsChannelsPanel,KsKnowledgePage}.tsx`、`plugin/client/ksHostPrimitives.d.ts`、
`plugin/client.js`、`plugin/scripts/smoke-all.mjs`、`plugin/scripts/smoke-icon-system.mjs`、
`docs/UI-ICON-SYSTEM.md`、`specs/008-icon-system/**`。
⇒ **未碰** `tools/gov-qa/**`、`scripts/run-gates.ps1`、`specs/004`、`specs/006`、公告更新组件。

## 8. 我**没有**验的（不许被读成"验过"）

1. **独立第三方复核** —— 见开头，本报告是自查。
2. **真宿主**现场：图标读数全部来自**离屏渲染**（真 Edge + 真组件），**不是真宿主**。
3. **`ingest` / `materials` / `settings` 三页的图标**（本轮渲染无 svg，见 §5 边界）。
4. **深色主题**下的图标表现（本批只跑 light）。
5. **`Medium` 档在真机上的观感** —— 我只看了离屏对照图（`medium-vs-regular-2x.png`），
   以及改后截图（`icon-medium-520.png`）；**没在真宿主里看过**。
6. **`size` 属性与最终渲染尺寸的等价性**：判据①只保证"显式给了 size 且在允许档"，
   真渲染尺寸由 `ui-render-shot` 的 DOM 读数负责（我在 kb / capabilities 上核过一致，**其它页面没核**）。
7. `run-gates.ps1 -Full` 我只在**主仓**跑过（10/10）；**提取树里没跑**（有全局锁，任务书明令不跑）。

## 9. 建议（留给真正的独立复核）

按优先级，若有第三方接手，请优先打这三条：
1. **判据③的口径**：我修完别名导出后，还有别的声明形态能逃过吗？
   （例如 `export * from`、`declare const IconFake: …`、`export type`）
2. **判据①的等价性**：`size={16}` 与实际渲染 16px 是否在所有页面都成立？
3. **`Medium` 档的语义选择**：左树"当前选中"用 1.3px 是否真比 Regular 好？
   （我只做了并排对照图，**没做可用性判断**）
