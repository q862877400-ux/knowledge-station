# D2 冒烟失败根因分析（只读分析，未改任何代码）

> 分析对象：`plugin/scripts/smoke-lifecycle.mjs` 的 D2 断言
> 仓根：`D:\Agent-Studio\Deepseek-Harness\DSH-Data\workspace\zcode`
> 分析日期：本轮（只读，未修改任何代码、未修改任何断言）

---

## 一句话结论

**D2 是既有缺陷，不是本轮改动造成的，也不是"结果没写进状态文件"——写入代码是对的、在绝大多数运行里也确实写成功了；失败的原因是「D 段读状态文件时，写盘还没落地」，而读之前只等了"入库请求发出去了"这一个事件，没等"结果落盘了"这个事件。**

---

## 五条要点

1. **定性：既有缺陷，与 2026-10-19 超时/重试改动无关。** 本轮改动只碰 `plugin/src/index.js`（两处 `timeoutMs` 120s→300s）、`src/core/config.py`、`src/core/llm/ks_answer.py`、`src/core/verification/typed_verifier.py`；`plugin/src/announce.js` 与 `plugin/scripts/smoke-lifecycle.mjs` 本轮**零改动**。用 `git stash` 撤掉本轮改动后重跑，D2 一样 FAIL。

2. **D2 是偶发（flake），不是稳定红。** 我实测 25 次真冒烟：24 次 23/23 全过、1 次 22/23（只有 D2 红）。另外 10 次一轮的取样里红 2 次。失败率约 4%–20%，随机器负载浮动。这解释了为什么它有时绿有时红，也解释了为什么"干净树上一样失败"和"现在跑又是绿的"可以同时成立。

3. **不是"没写"，是"读了还没写的旧版本"。** 失败那一次的状态文件内容是 **B4 段的旧快照**（`"scan_id": "scan-smoke-B4"`、`"ingest": null`），而不是 D 段应有的 `scan-…` 快照。即：`last.ingest` 是 `null` 是因为读到的是**上一段落盘的那一版**，D 段自己那一版当时还没落盘。这与"根本没写"在文件内容上可区分——没写的话会读不到文件或读到 D 段的 `last` 但没有 `ingest` 键，实际读到的是 B4 的完整快照。

4. **缺口在时序等待，不在写盘逻辑。** 写盘那段（`autoIngestTail` 的 `update((s) => { if (s.last) s.last.ingest = clean; return s })`）是对的，`sanitizeIngest` 白名单也是对的，D4（失败留痕 `{"error":"自动入库失败：引擎 HTTP 500"}`）能过就是证据：同一个写盘路径在错误分支上落盘成功了。缺的是 D 段在 `await drive()` 之后**只等了 `ingestCalls.length > 0`**（请求发出）就立刻 `readFile`，而写盘是 `void schedulePersist()` 挂到 promise 链上的异步尾巴，**没有 await 住**。

5. **修复方向：两处小改，都在 `plugin/` 内，不动 `src/`（引擎侧）。** ① 产品侧：把写盘从"fire-and-forget 的 promise 链"改成"返回可 await 的句柄"，让调用方能等落盘；② 冒烟侧：把"等请求发出"换成"等落盘可见"的有界轮询。两者都不影响 D1/D3a/D3b/D4/D5/D6。

---

## 一、根因：证据链

### 1.1 写入链路：谁负责把入库结果写进状态文件

文件：`plugin/src/announce.js`

扫描收尾的终态分支里，先落扫描快照，再跑自动入库尾巴：

```js
    update((s) => {
      s.last = sanitizeLast(finalData)
      s.stale_run = false
      return s
    })
```

```js
    if (status === 'done') {
      // ⚠ 先确保状态文件**读过**再判开关：`getState()` 在未加载时给的是**内存默认值**（开），
      //   那会让"业主已经关掉了"这一事实被忽略（他会以为关掉了、其实还在入库）。
      await initAnnounceState()
      if (getState().auto_ingest !== false) await autoIngestTail(ctx, sess)
    }
```

自动入库尾巴确实把结果写进 `last.ingest`：

```js
  const clean = sanitizeIngest(out) ?? { error: '自动入库：引擎未返回可读结果' }
  update((s) => {
    if (s.last) s.last.ingest = clean
    return s
  })
```

**结论：写入代码存在、位置正确、条件正确。** `if (s.last)` 的守卫也成立——上面那次 `update` 刚把 `s.last` 设上。

### 1.2 为什么读不到：`update()` 不 await 写盘

文件：`plugin/src/announce.js`

```js
function update(fn) {
  const s = getState()
  const out = fn(s)
  void schedulePersist()
  return out
}
```

```js
function schedulePersist() {
  _persistChain = _persistChain
    .then(() => writeFile(announceFilePath(), JSON.stringify(getState(), null, 2), 'utf8'))
    .catch(() => { /* best-effort */ })
  return _persistChain
}
```

`update()` 把 `schedulePersist()` 的 promise **丢掉了**（`void`），只返回同步计算的 `out`。所以：

- 内存里的 `_state.last.ingest` 立刻就是对的；
- 磁盘上的 `ks-announce.json` 要等 `_persistChain` 这个 promise 链轮到自己才更新；
- **`autoIngestTail` 的 `await` 只等到了"内存改了"，没等到"磁盘写了"**。

而且 `schedulePersist()` 是把任务**追加到同一条链的尾部**——D 段之前 B4 段已经往链上排过写任务，D 段的写盘要排在那之后。机器一忙，这个排队时间就会被拉长。

### 1.3 冒烟侧的等待只等了"请求发出"

文件：`plugin/scripts/smoke-lifecycle.mjs`

```js
  const drive = async () => {
    const res = fakeRes()
    await scanRoute.handler(fakeReq('POST', {}), res)
    // 轮询是 fire-and-forget：等它把入库那一步做完
    await waitFor(() => ingestCalls.length > 0, 6000, 20)
    return res
  }
```

`ingestCalls.length > 0` 是在**桩 fetch 被调用时**成立的：

```js
    if (u.endsWith('/api/v1/update/announce-ingest')) {
      ingestCalls.push({ url: u, body: init?.body ?? null, method: init?.method ?? 'GET' })
```

桩 fetch 一被调用就 push，**此时 HTTP 响应还没返回**，`autoIngestTail` 后面的 `sanitizeIngest` + `update` + `schedulePersist` 全都没跑。紧接着就是读盘：

```js
  const stD = JSON.parse(await readFile(announceFilePath(), 'utf8'))
```

**这就是根因：等待条件比真实完成点早了一整段异步尾巴。** 它读到的必然是"上一次落盘的那一版"——也就是 B4 段留下的快照。

### 1.4 实测证据

**（a）真冒烟重复取样**

```
run  1 exit=0 23/23 assertions passed  fails=[0]
...
run 13 exit=1 22/23 assertions passed  fails=[1]
      FAIL  D2 自动入库的结果落进状态文件（界面靠它显示"上次自动入了几条"） — null
run 14 exit=0 23/23 assertions passed  fails=[0]
...
run 25 exit=0 23/23 assertions passed  fails=[0]
```

25 次里红 1 次；另一轮 10 次里红 2 次。**同代码一红一绿 ⇒ flake，不是稳定回归。**

**（b）失败那次的状态文件内容（决定性证据）**

```json
{ "last": { "scan_id": "scan-smoke-B4", "status": "done", "trigger": null, "started_at": null,
  "finished_at": null, "sources_total": 0, "sources_done": 0, "items_seen": 0, "new_count": 0,
  "baseline_count": 0, "per_source": [], "recent": [], "error": null, "ingest": null },
  "stale_run": false, "auto_ingest": true }
```

`scan_id` 是 **`scan-smoke-B4`**，不是 D 段的 `scan-D`。读到的是 **B4 段的旧快照**，`ingest: null` 是那份旧快照本来就有的值。⇒ 不是"没写"，是"读到了上一版"。

**（c）同一个失败次里 D1 是 PASS**

```
PASS  D1 扫描成功后**确实**自动入库一次，请求体是 {limit: 20} — calls=1 body={"limit":20}
FAIL  D2 自动入库的结果落进状态文件（界面靠它显示"上次自动入了几条"） — null
PASS  D3a 开关路由能写状态（关） — 200 {"ok":true,"data":{"auto_ingest":false}}
PASS  D3b 开关关掉 ⇒ **一次都不发**（反向对照，防"永远入库"的实现） — calls=0
PASS  D4 自动入库失败 ⇒ 状态文件里留 error（**不许静默**） — {"error":"自动入库失败：引擎 HTTP 500"}
PASS  D5 新进程 + 磁盘上开关=关 ⇒ 一次都不入库（重启后第一次扫描也守规矩） — calls=0
PASS  D6 正向对照：新进程 + 磁盘上开关=开 ⇒ 确实入库一次（证明 D5 不是"永远不入库"） — calls=1
```

D4 在**同一次运行里**把 `last.ingest` 写进了磁盘并读到了。⇒ 写盘路径本身是好的，D2 红是时序问题。

**（d）延迟量测（独立探针，仓外临时脚本，不改仓）**

照 D2 的时序读：30 次里 1 次读到 `null`；改为"有界轮询直到落盘"后，**落盘延迟** 分布为 `min=0.4ms p50=0.7ms max=3015ms`（3015ms 是那次超时值，其余全在 1ms 内）。⇒ 绝大多数时候写盘比读盘快（所以 D2 常绿），少数时候被调度拖慢（所以 D2 偶红）。**这正是竞态的定义。**

### 1.5 被排除的其他候选解释

| 候选 | 排除依据 |
|---|---|
| `last.ingest` 写到了别的键 | 读到的状态文件里 `last` 是 B4 的快照，键名结构正确，只是内容属于上一段 |
| 某条早退分支跳过了写入 | `autoIngestTail` 无早退；D4 同一次运行里写成功 |
| `sanitizeIngest` 把结果洗成 null | 失败那次读到的 `ingest` 来自 B4 快照，根本没经过 D 段的 `sanitizeIngest`；D4 证明清洗后能正常落盘 |
| `AUTO_INGEST_LIMIT` / `KS_ANNOUNCE_AUTO_INGEST_PATH` / `ENGINE_INGEST_PATH` 写错 | D1 断言 `{limit:20}` 与路径全等，实测 PASS |
| `auto_ingest` 开关被读成 false | 失败那次状态文件里 `"auto_ingest": true` |
| 本轮改动引入 | 本轮未碰 `announce.js` / `smoke-lifecycle.mjs`；stash 后重跑同样失败 |

---

## 二、修复方案（只给方案，未实施）

两处改动，都在 `plugin/` 内，不碰引擎侧 `src/`。两处**互相独立**，可以只做②先把红压掉，再做①治本。

### 方案 A（治本，产品侧）：让写盘可等待

文件：`plugin/src/announce.js`

- 给 `update()` 增加一个可选返回：把 `schedulePersist()` 的 promise 暴露出来（例如新增 `async function updateAndPersist(fn)`，或让 `update` 返回 `{ out, persisted }`）。
- `autoIngestTail` 结尾改成 `await` 住落盘，而不是 `void` 掉。
- 保持现有 `update()` 签名不变，供其余调用点（`runScanPoll`、`auto_ingest` 路由等）继续 fire-and-forget。

**影响面**：只影响 `autoIngestTail` 的返回时机，不改任何写盘内容、不改键名、不改白名单。

**对已过断言的影响**：

| 断言 | 影响 | 判断依据 |
|---|---|---|
| D1（发一次 `{limit:20}`） | 无影响 | 请求在 `await` 之前就发了 |
| D3a（开关路由写状态） | 无影响 | 走 `update()`，签名不变 |
| D3b（关掉后 0 次） | 无影响 | 不进 `autoIngestTail` |
| D4（失败留痕） | 无影响（只会更稳） | 错误分支同样走这条 await，写盘更早可见 |
| D5/D6（新进程开关） | 无影响 | 子进程里 `triggerAfterInspection` 只数请求次数，不读状态文件 |

### 方案 B（治标，冒烟侧）：把等待条件换成"落盘可见"

文件：`plugin/scripts/smoke-lifecycle.mjs`

把 `drive()` 里的等待改成有界轮询到真正关心的条件：

```js
await waitFor(async () => {
  try {
    const s = JSON.parse(await readFile(announceFilePath(), 'utf8'))
    return s?.last?.ingest !== null && s?.last?.scan_id === 'scan-D'
  } catch { return false }
}, 6000, 20)
```

要点：**同时校验 `scan_id`**，否则会被上一段落的旧快照（`ingest` 恰好非 null 时）骗过——这正是本次失败暴露的陷阱。文件里已有现成的 `waitFor`（有界、非 busy-poll），不需要引入新工具。

**影响面**：只改 D 段 `drive()` 的等待条件，不改任何断言原文、不改 D1/D3/D4/D5/D6。

### 方案 C（补充，可选）：把写盘做成原子替换

文件：`plugin/src/announce.js` 的 `schedulePersist()`

现在直接 `writeFile` 到目标路径，读者可能读到写了一半的 JSON。改成"同目录临时文件 + rename"。详见第三节。

### 回退性

三处都是文件级、可单独回退：A/B/C 各自独立，`git checkout -- plugin/src/announce.js` 或 `git checkout -- plugin/scripts/smoke-lifecycle.mjs` 即可逐处退回，不涉及数据迁移、不涉及状态文件格式变更（C 只改写法，不改内容）。

### 风险

- **方案 B 会让 D2 变慢**：从"立刻读"变成"最多等 6s"。实测正常路径 <1ms，只有真出问题才会等满，可接受。
- **方案 A 会让扫描收尾变慢**：`autoIngestTail` 现在要等一次真实写盘（亚毫秒级）才返回。这个函数在无人值守路径上跑，多等一次 `writeFile` 无实质影响。
- **方案 C 有 Windows 特有问题**：Windows 上 `rename` 覆盖已存在文件的行为与 POSIX 不同，需要用 `fs.rename` 且处理 `EEXIST`/`EPERM` 重试；本仓在 `%TEMP%` 上已经踩过 360 主动防御的坑（见 `docs/TEST-FLAKES.md`），新增临时文件写法要先确认不触发它。

---

## 三、外部借鉴（业界做法，不是我们的证据）

> 以下每条都是**业界通行做法**，用来说明本仓现有实现的差距，**不构成本仓的证据**。

### 3.1 原子写：临时文件 + rename

**业界做法**：写状态文件时先写同目录临时文件，再 `rename` 覆盖目标。POSIX 上 rename 是原子的，读者要么看到完整旧版、要么看到完整新版，**永远不会看到半截 JSON**。

- [perses PR #4513 — make file database writes atomic](https://github.com/perses/perses/pull/4513)：原文说明 `os.WriteFile` 会先 truncate 目标文件，并发读者可能读到空文件或半截内容，JSON 数据库因此报 `unexpected end of JSON input`；改成同目录临时文件 + rename 后，"Readers therefore see either the previous complete file or the new complete file, rather than an intermediate state"。该 PR 还提到 **Windows 上 rename 不是原子的**，需要针对 `EEXIST`/共享冲突做重试。
- [atomicfile 包文档](https://pkg.go.dev/latere.ai/x/pkg@v0.77.0/atomicfile)：同样模式的独立实现，并区分了 `Write`（只保证原子，不 fsync）与 `WriteSync`（fsync 临时文件 + 目录项），说明"rename 原子 ≠ 崩溃后不丢数据"。

**本仓差距**：`plugin/src/announce.js` 的 `schedulePersist()` 直接 `writeFile(announceFilePath(), ...)`。**这不是本次 D2 的原因**（D2 是读到旧版，不是读到半截），但它是一个**尚未暴露的同族缺陷**：读者（`GET /ks/announce/summary` 路由）与写者并发时可能读到半截 JSON。`loadStateFile()` 的 `catch { /* absent or corrupt -> defaults */ }` 会把半截 JSON **静默当成"文件不存在"**，于是返回全默认状态——那会让界面显示"从来没扫描过"，比报错更难查。

### 3.2 last-write-wins vs 事件日志

**业界做法**：单文件状态快照天然是 last-write-wins——只保留最后一次的状态，历史不可追溯。需要追溯时用事件日志（append-only），状态由日志重放得出。

- [Activepieces — Durable Execution](https://www.activepieces.com/docs/install/architecture/durable-execution)：其 run log 是"每个已完成步骤一条记录（input / output / status / duration / error）"，写入时机是"开始时一次、执行中每 15 秒一次、**终态（success、failure、pause）再一次**"。这个"终态必写"的纪律值得对照：本仓 `autoIngestTail` 的写入确实覆盖了成功和失败两种终态，这点是对的。
- 同一文档指出 run log 的写入是"快照自上次写入以来完成的步骤"——即**显式的、可枚举的写入点**，而不是散落在各处的 fire-and-forget。

**本仓差距**：本仓是 last-write-wins（对界面需求足够），但写入点是**隐式**的——`update()` 里 `void schedulePersist()`，调用方无法知道"什么时候真的写完了"。这正是 D2 的直接成因。业界的做法是把写入点做成可观察的（要么返回句柄，要么显式 await）。

### 3.3 状态 schema 版本化 / 字段可缺省

**业界做法**：持久化的状态文件带一个 `schema_version` 字段；读取时按版本决定如何处理，**字段缺失视为旧版本而不是错误**。

- [GKS v3 — Schema Migrations](https://github.com/freshair129/gksv3/blob/HEAD/docs/MIGRATIONS.md)：明确列出"新增一个老读者可以忽略的可选字段 ⇒ PATCH（静默）"、"新增一个带合理默认值的必填字段 ⇒ MINOR"、"重命名/删除/改变序列化 ⇒ MAJOR"；并且"没有 `schema_version` 字段的老存储按 1.0.0 对待"。
- [ctm 的 migrate 包](https://pkg.go.dev/github.com/RandomCodeSpace/ctm@v0.1.16/internal/migrate)：每个状态文件顶层带 `schema_version` 整数；**拒绝处理版本高于当前程序的文件**（防旧二进制把新二进制写的状态写坏）。
- [json-patch-to-crdt issue #106](https://github.com/samlaycock/json-patch-to-crdt/issues/106)：问题陈述很贴切——没有版本号时，反序列化**无法区分"旧格式"和"数据损坏"**。

**本仓差距**：`plugin/src/announce.js` 的 `defaultState()` 产出的状态文件**没有版本字段**（只有 `last` / `stale_run` / `auto_ingest`）。本仓用另一套等价手段替代：`sanitizeLast()` / `sanitizeIngest()` 两个白名单函数，缺字段一律给默认值（`Number(raw.tried) || 0`、`typeof raw.error === 'string' ? ... : null`）。**这套做法在"字段可缺省"这一半上是对的**（结构漂移不会炸），但**在"区分旧版与损坏"这一半上是缺的**——`loadStateFile()` 的 `catch` 把两者合并成同一条路径。

### 3.4 失败也留痕

**业界做法**：状态写入必须覆盖失败路径，不能只在成功时写。否则"没消息"既可能是"成功了"也可能是"根本没跑"。

- [Activepieces — Durable Execution](https://www.activepieces.com/docs/install/architecture/durable-execution)：run log 的写入时机包含 `failure`，并且每条 step 记录带 `error message`。
- [ones.com — How to Fix Flaky Tests Caused by Timing Issues](https://ones.com/blog/how-to-fix-flaky-tests-caused-by-timing-issues/)：失败信息要写清"期望条件、观察到的状态、已耗时"，而不是只报"没找到"。

**本仓差距**：**这一条本仓做得比业界要求还好**，应作为既有优点保留：`autoIngestTail` 在失败时写 `{error: "..."}`，`sanitizeIngest` 保留 `error` 字段，D4 断言专门钉住了这一点，实测 PASS。本次分析不需要改这里。

### 3.5 等"条件达成"而不是等"动作发生"（直接对应 D2）

**业界做法**：异步测试里，等待条件必须是**被测方真正完成时才会成立的那个条件**；用"动作已发起"或固定 sleep 当同步手段是已知的 flake 来源。

- [guess/claude_code PR #43 — Harden timing-sensitive tests](https://github.com/guess/claude_code/pull/43)：把 13 处 `Process.sleep(50-100)` 换成 `poll_until` / `assert_receive` 等确定性同步，理由是固定 sleep "too short on slow runners, unnecessarily slow on fast ones"。
- [asupersync — e2e hardening 分析](https://github.com/Dicklesworthstone/asupersync/blob/main/e2e_hardening_11_analysis.md)：把"固定延迟做同步"列为反模式，正例是"poll until actual condition is met"，并给出 `wait_for_server_ready` / `wait_for_supervision_action` 这类轮询函数。
- [dsh-plugin-hub PR #341](https://github.com/wingsky-1/dsh-plugin-hub/pull/341)：同一条纪律的中文实践——把"同步调用 async handler 后固定 sleep 再读外联变量"系统性收敛为 `pollUntil`。
- [ones.com 同一篇](https://ones.com/blog/how-to-fix-flaky-tests-caused-by-timing-issues/)：验收标准是"在相关执行条件下反复通过"，并明确"单次通过不能证明确定性"（"A single passing run does not establish determinism"）。

**本仓差距**：`drive()` 等的是 `ingestCalls.length > 0`——**动作已发起**，不是**结果已落盘**。这是 3.5 里被点名的反模式的一个变体（不是固定 sleep，但同样等错了点）。冒烟文件里**已经有正确的工具**（`waitFor` 有界轮询），只是 D 段没用它等对条件。

---

## 四、诚实边界（未确认项）

1. **本仓 D2 的失败率未精确测定。** 我跑了 25 次真冒烟（红 1）+ 10 次取样（红 2）+ 独立探针 50 次（红 2）。样本量不足以给出稳定概率，只能定性为"偶发、随负载浮动"。**未确认**它在门禁串行链里（`smoke-all.mjs` / `run-gates.ps1`）的失败率是否更高——那需要跑多次完整门禁，本轮未做。

2. **为什么是"B4 的旧快照"而不是"更早的版本"未完全确认。** 我确认了失败那次读到的是 B4 段落的快照，但没有逐次打点记录 `_persistChain` 上每次写入的排队顺序。**未确认** B4 → D 之间是否还有别的写任务排在链上（`runScanPoll` 的 `update`、`triggerAfterInspection` 的 `update` 都会往链上排）。

3. **方案 A 的具体代码形状未实现、未验证。** 我只读了代码并给出方向，没有写代码、没有跑改后冒烟。"会不会把 D1/D3/D4/D5/D6 弄红"的结论来自**读代码推断**（这些断言不读状态文件或走的路径不受影响），**不是实测**。

4. **方案 C 的 Windows rename 语义未在本机验证。** 引用的 perses PR 明确说 Windows 上 rename 不原子、需要重试，但我没有在本仓实测 `fs.rename` 覆盖已存在文件的失败率。

5. **没有跑完整门禁。** 本轮只单跑了 `plugin/scripts/smoke-lifecycle.mjs`（25 次）与两个仓外探针脚本。**未跑** `pwsh -File scripts/run-gates.ps1 -Quick/-Full`，因此"本轮改动没有别的影响"这一说法只覆盖我实测的这一个冒烟文件。

6. **本轮改动与 D2 无关的判断依据是文件面隔离，不是逐行审阅。** 我确认 `plugin/src/announce.js` 与 `plugin/scripts/smoke-lifecycle.mjs` 的最近提交是 `a16108eb`（2026-10-09），本轮 `git status` 未显示这两个文件被修改；我没有逐行审阅本轮改动的那四个文件是否可能间接影响（例如 `plugin/src/index.js` 的 timeout 改动是否影响 `manager.ensureLive()`）。

7. **外部资料是"业界做法"，不是本仓的证据。** 第三节所有 URL 只用于说明通行做法与本仓差距，不能用来论证本仓的行为。其中 GKS v3、ctm、json-patch-to-crdt、guess/claude_code、asupersync、dsh-plugin-hub 都是第三方仓库的文档/PR/issue，未经本仓验证。

8. **仓外探针脚本未纳入版本控制。** 我写的三个探针（`probe.mjs` / `probe2.mjs` / `probe3.mjs` / `probe4.mjs`）放在 `%TEMP%\d2-probe\`，**不在仓内**，不属于交付物，也未提交。它们的作用是产出第一节 1.4 的实测数字。

---

## 五、给主代理的一句话建议

先做**方案 B**（一行等待条件，立刻把红压掉、风险最低、可单独回退），再做**方案 A**（治本，让写盘可 await）。**方案 C 建议单独立项**——它是同族的真缺陷（半截 JSON + 静默降级成默认状态），但不是 D2 的成因，混在一起改会让"D2 修好了没有"变得不可验证。
