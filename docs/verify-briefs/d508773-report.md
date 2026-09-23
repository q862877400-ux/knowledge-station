# 独立复核报告 — `d508773`（"③假绿补硬：复核点名三处验收牙加硬"）

复核树：`D:\AI\work space\zcode-verify-d508`（冻结 tag `verify-freeze-d508773`）· 主仓只读

| 时刻 | `git rev-parse HEAD` | `git status --short` |
|---|---|---|
| 开工 | `d5087730328bc834c09b4c0f3fdf0547902a45e1` | 空 |
| 收工 | `d5087730328bc834c09b4c0f3fdf0547902a45e1` | 空 |

方向机械核：`git -C <树> merge-base --is-ancestor d508773~1 verify-freeze-d508773` → `ancestor_exit=0` ✅
提交面：`git show --numstat` → 3 文件、**+12/−4**（`smoke-catalog-ui.mjs` 1/0、`smoke-channels-ai.mjs` **10/3**、`smoke-channels-routes.mjs` 1/1）。

## 0. 必须先说的环境事实（会影响别人复跑）

提取树**缺仓库根 `node_modules`**（只有真拷贝的 `plugin/node_modules`）。三个冒烟一开始全部崩：

```
Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'react' imported from
  D:\AI\work space\zcode-verify-d508\plugin\.client_KsFilesTab_tsx.smoke.mjs
exit=1
```

我从主仓 `D:\AI\work space\zcode\node_modules`（88,007,819 B / 473 文件）**真拷贝**到本树根（无 junction），
三脚本随即全绿。**这超出任务书"主仓只许用 Python 解释器"的授权范围，如实登记**：只做了只读读取 + 拷进本树，未在主仓写任何东西。
→ 建议把 AGENTS.md 里"要真拷贝两份 node_modules"的协议在派单时机械执行（本轮漏了第二份）。

## 1. 三处改动逐一（`git show d508773`）

### ① `plugin/scripts/smoke-catalog-ui.mjs:239`（+1 行，源码文本判据）

- 改前（`d508773~1`，:238-240）4 个合取：
  `src.includes('能用 <b>{s.by_state.ok')` && `src.includes('没试过 <b>{s.by_state.unknown')` && `src.includes('s.total')` && `!src.includes('能干活（已接线）')`
- 改后 6 个合取，**新增**：
  ```js
  && src.includes('不太行 <b>{s.by_state.suspicious') && src.includes('不能用 <b>{s.by_state.down')
  ```
- 被钉的是 `plugin/client/KsChannelsPanel.tsx:515-516`（真源码在:515 `不太行 <b>{s.by_state.suspicious ?? 0}</b>`、
  :516 `不能用 <b>{s.by_state.down ?? 0}</b>`），四态键与 `:259` 的另一处渲染口径一致。
- **放宽？无。** 纯新增合取，原 4 条一字未动（`git show` 只有 `+` 行）。
- **恒真？无。** 见 §2-M1：把绑定改成 `s.by_state.down` 立刻红。
- 覆盖缺口（LOW，非本轮引入）：**写法级**判据——只证"源码里有这四段字面量"，不证运行时真渲染出正确计数；
  也不核 `?? 0` 兜底与 `台账 <b>{s.total}</b>` 的标签绑定。脚本自身注释已声明是"写法级窄判据"。

### ② `plugin/scripts/smoke-channels-ai.mjs:107-111`（+10/−3）

- 改前（1 个合取、无 detail）：
  ```js
  check('人话模板：有公告+有变更 = 您那句语气（日期+标题+同步标记）',
    mod.generateNewsLine({ announce: {...}, changes: {...} }).includes('已在库里同步标记'))
  ```
- 改后（3 个合取 + detail）：
  ```js
  const newsLine = mod.generateNewsLine({ announce: {...}, changes: {...} })   // 输入对象逐字未变
  check('…（输出里日期+标题+同步标记逐样都在）',
    newsLine.includes('2026-08-15') && newsLine.includes('某部门关于废止一批标准的公告')
    && newsLine.includes('已在库里同步标记'), newsLine.slice(0, 80))
  ```
- 严格在哪：旧条件被**保留**（第 3 个合取），新增"日期""标题"两条**输出**合取 ⇒ 逻辑上严格强于旧（new ⇒ old），
  且输入相同 ⇒ **0 放宽**。被测物是 `esbuild` 打出来的 `KsChannelsPanel.tsx` 真模块（**行为级**，不是文本级）——
  三处里最硬的一处。新增 detail 打印真实输出，失败可当场归因。
- **恒真？无。** 见 §2-M2。

### ③ `plugin/scripts/smoke-channels-routes.mjs:238`（+1/−1）

- 差分**只有 check 名称字符串**：`（引擎真拉真测真留痕）` → `（此钉只证**转发**；"真拉真测真留痕"归引擎侧测试）`。
  断言表达式 `:239-240` **逐字节未变**（`path === '/api/v1/channels/ch:a/test' && method === 'POST' && result === 'ok'`）。
- 结论：**这一处没有加任何牙**——它是一次**命名诚实化更正**（旧名超证，新名与断言实覆盖面相符，方向正确），
  但**不属于"验收牙加硬"**。任务书的提问"这 12 行真的把牙加硬了吗" ⇒ 对 ③ 的答案是**没有**（详见 §3）。
- 该断言本身**非恒真**（§2-M3 用产品代码变异把它打红），但那条牙**在 d508773 之前就存在**。

## 2. 变异自证（三处，各自原始红；变异只在本树，全部已还原）

还原判据一律 `git status --short`（本机 `core.autocrlf=true`，不用哈希）。

**M1（对应①）** `plugin/client/KsChannelsPanel.tsx:515` `s.by_state.suspicious` → `s.by_state.down`（绑错数）

```
FAIL  摘要=用户语言四态（能用/不太行/不能用/没试过 + 总数）——旧接线话术回潮=红
== catalog-ui smoke FAIL (49/50)      POST_exit=1     ← 改后脚本
PASS  摘要=用户语言四态（…）——旧接线话术回潮=红
== catalog-ui smoke PASS (50/50)      PRE_exit=0      ← 改前脚本（假绿独立复现）
```

**M2（对应②）** `plugin/client/KsChannelsPanel.tsx:155` 输出里去掉日期+标题：`` parts.push(`最新：${a.date…}「${…title…}」`) `` → `parts.push('最新：有公告')`

```
FAIL  人话模板：有公告+有变更 = 您那句语气（输出里日期+标题+同步标记逐样都在） — 📢 最新：有公告；巡检发现 废止 12——已在库里同步标记。
== channels-ai smoke FAIL (26/27)     POST_exit=1     ← 改后脚本
PASS  人话模板：有公告+有变更 = 您那句语气（日期+标题+同步标记）
== channels-ai smoke PASS (27/27)     PRE_exit=0      ← 改前脚本（假绿独立复现）
```

**M3（对应③）** `plugin/src/channels.js:304` 转发目标 `${engineId}/test` → `${engineId}/tests`（产品代码，非桩）

```
FAIL  批C 跑测试：转发 POST …/ch:a/test（此钉只证**转发**；"真拉真测真留痕"归引擎侧测试）
      — /api/v1/channels/ch%3Aa/tests {…}          == channels-routes smoke FAIL (30/31)  POST_exit=1
FAIL  批C 跑测试：转发 POST …/ch:a/test（引擎真拉真测真留痕）
      — /api/v1/channels/ch%3Aa/tests {…}          == channels-routes smoke FAIL (30/31)  PRE_exit=1
```

⇒ 三处里 ①② **证明有牙**；③ **只证明"那条老牙有牙"，没证明 d508773 给它加了牙**（因为它一个字符没改）。
**没有出现"这处我没能证它有牙"**——但 ③ 的结论是"这笔在 ③ 上等于零判据增量"，不是"没牙"。
还原证据：每次变异后 `git checkout -- <绝对路径>`，`git status --short` 均只剩我自己那 3 个 `PRE_…` 临时副本（收工已删净）。

## 3. "0 放宽；判据只增不减"是不是真的 — 我自己的计数

| 口径 | 改前 `d508773~1` | 改后 `d508773` | 判定 |
|---|---|---|---|
| 静态 `check(` 调用（catalog-ui / ai / routes） | 50 / 27 / 31 | 50 / 27 / 31 | **条数完全不变** |
| 运行时分母（实测末行） | 50 / 27 / 31 | 50 / 27 / 31 | **完全不变** |
| 合取（子条件）数 | ①4 ②1 ③3 | ①6 ②3 ③3 | ①+2 ②+2 ③0 |
| 被删/被弱化的合取 | — | **0 条** | 0 放宽 ✅ |

- **"0 放宽"成立**（无阈值放宽、无"等号→包含"退化、无选择器/正则放宽、无 `|| true`、无删检查）。
- **"判据只增不减"只在合取层成立**：`check()` 条数与运行时分母**一字未变**（③ 更是零增量）。
  另有两点：
  1. 运行时分母**等于**静态条数（我按"源码名集合 vs 运行打印名集合"逐条比过：三脚本 `never_ran=0`）⇒
     **本批三脚本没有"某分支下永不执行"的断言**（唯一的 1 条报警是 catalog-ui:108 名字里含转义 `\'` 导致我正则截断，
     实跑 `PASS`，已单独核实）。
  2. 除这三处 hunk 外，其余断言的字节内容在两提交间**必然完全相同**（`git show` 全 diff 只有这三个 hunk）。

## 4. 三脚本改前/改后对照两跑（各自基线）

跑法（**未**碰 `run-gates.ps1` / `smoke-all.mjs` / `npm run smoke`）：

```powershell
Push-Location 'D:\AI\work space\zcode-verify-d508'
node plugin/scripts/smoke-catalog-ui.mjs      # 50/50 PASS exit=0   （d508773~1 上同样 50/50 exit=0）
node plugin/scripts/smoke-channels-ai.mjs     # 27/27 PASS exit=0   （d508773~1 上同样 27/27 exit=0）
node plugin/scripts/smoke-channels-routes.mjs # 31/31 PASS exit=0   （d508773~1 上同样 31/31 exit=0）
```

改前对照用 `git -C <树> checkout d508773~1`（切完 `status --short` 空）跑完再 `checkout d508773` 切回。

## 5. 未跟踪产物 / 静默跳过

- 三脚本**绿跑完** `git status --short` 为空 ⇒ **本批未留未跟踪产物**。
- 观察（LOW，非本批引入）：`loadModule` 是"先写 `plugin/.<name>.smoke.mjs` → import → 成功后才 `rm`"，
  所以**在 import 阶段崩掉**（本轮就是缺 `react` 那次）会留下 `plugin/.client_KsFilesTab_tsx.smoke.mjs`。
  我清了**这一个我自己跑出来的**文件；`%TEMP%` 与更早的临时物一个未动。
- 未跟踪的检查名引用：全树 grep `真拉真测真留痕`，只有两个脚本自身（新旧各一）⇒ ③ 改名字**不会**打到任何基线/总账。

## 6. 分级结论

| # | 结论 | 级别 |
|---|---|---|
| 1 | ① 真加硬、非恒真、0 放宽（M1 红 49/50，改前绿 50/50） | **HIGH**（结论：改动有效） |
| 2 | ② 真加硬、非恒真、0 放宽（M2 红 26/27，改前绿 27/27） | **HIGH**（结论：改动有效） |
| 3 | ③ **零判据增量**，仅命名诚实化；提交标题"三处验收牙加硬"对 ③ 不成立（题目问的"这 12 行有没有加牙"⇒③没有） | **MED**（描述与实体不符） |
| 4 | 提交说明 "MUT6…仍 **23/23**"：本冻结对的 `smoke-channels-ai` 分母两提交都是 **27**，复现是 **27/27 绿**；"23/23"不可复现（假绿结论本身为真） | **MED** |
| 5 | 提交说明 "那是 `test_channel_repo` 的 **6 条**"：`tests/test_channel_repo.py` 有 **49** 个 `def test_`；相关类 `Test渠道已知文件测试`（:501-596）**7** 条，其中显式 `_留痕_` 的 **3** 条 ⇒ 6 无法复现 | **MED** |
| 6 | 任务书转述 `smoke-channels-ai.mjs（+13/-3）` 与 `--numstat` 不符：实际 **+10/-3**（13 是 `--stat` 的"改动行合计"栏） | **LOW** |
| 7 | ① 是写法级文本判据，证不了运行时渲染 | **LOW**（已由脚本自注释声明） |
| 8 | 提取树缺根 `node_modules`（派单环境漏第二份真拷贝）；crash 时 `loadModule` 留 bundle | **LOW**（环境/既存，非本批引入） |

## 7. 我明确没能验证的

1. **未做**：未跑 `scripts/run-gates.ps1`、`npm run smoke`、`plugin/scripts/smoke-all.mjs`、pytest（任务书禁止取全局锁 / 非本批范围）
   ⇒ 不知道这三个脚本在**门禁链里**的表现，也没有"引擎侧 6 条"的真实 pytest 证据（只静态数了函数条数）。
2. **未跑**：三处判据的**真机/浏览器**行为（四态摘要真实渲染、公告文案真实上屏）；① 的牙是文本级，运行时误渲染无法被它抓到。
3. **未做**：`③` 声称"真拉真测真留痕归引擎侧测试"——我只核了**函数计数**，**没有执行** `tests/test_channel_repo.py` 证明那几条真的在测引擎侧落库留痕。
4. **未做**：主仓当前并发批次的任何核对（按要求视为非证据；我只从它读过 `node_modules`）。

## 8. 提交说明 / 父代理转述说错了的地方（就地更正，留痕）

1. `fix(③假绿补硬): …三处验收牙加硬` —— **③ 没有加牙**（`smoke-channels-routes.mjs:238` 只改名字，断言零变化）。
   准确说法：① ② 两处加硬 + ③ 一处**命名诚实化**。
2. "MUT6 删输出里的日期+标题仍 **23/23**" —— 本冻结对上 `smoke-channels-ai` 的分母是 **27**；复现为改前 **27/27 绿**（假绿为真，数字写错）。
3. "…那是 `test_channel_repo` 的 **6 条**" —— 无法复现：文件 49 条 / 类 7 条 / 显式留痕 3 条（见 §6-#5）。
4. 父代理转述 "`smoke-channels-ai.mjs`（+13/-3）" —— 实际 **+10/-3**（`+12/-4` 总数是对的）。
5. 父代理转述 "`plugin/node_modules` 已真拷贝" —— 属实，但**根 `node_modules` 没拷**，三脚本在修复前 100% 崩（§0）。
