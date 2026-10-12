# VERIFY-REPORT · spec 009（「本轮依据」三处改动）—— **自查**（非独立第三方）

> ⚠⚠ **本报告的性质必须先说清**：这是**我自己做的核查**，**不是独立第三方复核**。
>
> **为什么是自查**：团队复核机制在本环境下**连续五次派发全部失败** ——
> `verifier3`（spec 008）跑到一半断；`verifier4`/`verifier5`/`verifier6` 在**创建时**
> `initial prompt was not durably accepted`（durable 确认超时）；`verifier7` 创建成功但同样中途失败、
> **未留下任何产物**；`verifier2` 也被唤醒失败。
> ⇒ 我改用**与复核相同的纪律**自己做：**在冻结提取树里验**、**自己造变异**、**逐字节还原**。
>
> ⚠ **自查的固有弱点**：我对自己的实现有先入之见，**看不出的错就是看不出**。
> 本报告**不能**替代独立复核；下面每条都给了可复算的命令，供任何第三方复现。

---

## 0. 冻结与现场

| 项 | 值 |
|---|---|
| 冻结点 | **`8b12fc39`**（比任务书写的 `53349f12` 新一笔：我自己复核时发现的跨页修复） |
| 提取树 | `D:/AI/verify-trees/spec009`（`git worktree add`，依赖**真拷贝**：`plugin/node_modules` + 仓库根 `node_modules`，非 junction） |
| 开头记录 | `git rev-parse HEAD` = `8b12fc39f33b16d18cfc29176b186018c9c758ed`；`git status --short` = **空** |
| 结尾记录 | 同上；`git status --short` = **空**（全部变异已逐字节还原） |
| 复算脚本 | `var/tmp/verify009-mutations.py`、`var/tmp/verify009-arrow-chain.py` |

## 1. 判定

**PASS（自查口径）** —— 三处改动（条款归组 / 删 GB / 红箭头 bbox 三环）实现与判据**一致**，
**11 条变异全部打红**，基线三连全绿。**无 P0**；报 **P1 × 0 / P2 × 3**（见 §4）。

## 2. 读数复现（在提取树里跑）

| 命令 | 结果 |
|---|---|
| `npx tsc --noEmit -p client` | **exit 0** |
| `node scripts/smoke-turn-tab.mjs` | **30/30 PASS** |
| `pytest tests/test_ks_answer_bbox.py tests/test_ks_answer.py` | **42 passed** |
| `node scripts/smoke-client-entry.mjs` | **205/205 PASS** |
| `node scripts/smoke-all.mjs` | **43/43 套 · exit 0** |
| `run-gates.ps1 -Full`（主仓） | **12/12 · exit=0**（pytest 3009 passed / 0 failed / 2 skipped） |

## 3. 变异验证（11 条，全部逐字节还原）

| # | 变异 | 期望 | 实测 |
|---|---|---|---|
| A1 | 跨页时退化到 `spans[0]`（我修的那条复发） | 红 | ✅ exit 1 |
| A2 | 不优先 `page_start`（永远取 `spans[0]`） | 红 | ✅ exit 1 |
| A3 | 取不到时写 **0 兜底**（假证据） | 红 | ✅ exit 1 |
| B1 | `evidenceUrlOf` 不编 bbox（**原病复发**） | 红 | ✅ exit 1 |
| B2 | `evidenceUrlOf` 不校验形状（3 个数也编） | 红 | ✅ exit 1 |
| B3 | `turnEvidenceHref` 不传 bbox | 红 | ✅ exit 1 |
| B4 | 把 `legal_hierarchy` 渲染加回来（问题 2 复发） | 红 | ✅ exit 1 |
| B5 | 分组退化（问题 1 复发） | 红 | ✅ exit 1 |
| B6 | 排序改字典序（`5.10.1` 排到 `5.2.3` 前） | 红 | ✅ exit 1 |
| B7 | 条款行重新带标准号（重复标题） | 红 | ✅ exit 1 |
| C1 | `parseEvidence` 不解析 `bboxPage`（**往返断链**，对抗性） | 红 | ✅ exit 1 |

变异全部还原后复跑 **pytest=0 / smoke=0**。

## 4. ★ 任务书点名的两条重点

### 4.1 红箭头**真的会画吗**（任务书"★ 最该看的一条"）

**我逐环核清了渲染链路**（复算：`var/tmp/verify009-arrow-chain.py`）：

```
parseEvidence(tab.path) → evidence.current = {doc, page, bbox, bboxPage, rev}
  → 加载 effect：`if (ev.rev !== undefined && ev.bbox === undefined)` 才去 fetchBbox 兜底
  → renderPage：`const anchor = evidence.current?.bbox`
    → `if (anchor !== undefined && showArrowRef.current)` 才画
    → 位置由 `viewport.convertToViewportPoint(bx0, by0)` 算
    → **画在哪一页由 `onPage = evidence.current?.page === clamped` 决定**
```

**结论：链路是通的**（`bbox` 有值 ⇒ `anchor !== undefined` ⇒ 画）。
⚠ **但有一处路径变化必须登记**（见 4.3）。

### 4.2 `page_start` 与 `bbox_page` 不一致（任务书"★ 第二条"）

**核清了**（同一脚本）：`KsEvidenceTab.tsx` 里 **`bboxPage` 出现 0 次** ——
**画箭头的页判据是 `evidence.current?.page`，与 `bboxPage` 完全无关**。

⇒ 所以「bbox 属于哪一页」**必须**与 `page` 一致，否则画错页。
这正是我在 `8b12fc39` 加"**跨页时不许写别页坐标（宁可留空）**"的原因。
**该修复我独立核过**：变异 A1（改回退化）⇒ 精确红 1 条；真库端到端仍 5/5（不影响正常路径）。

### 4.3 ⚠ **路径变化带来的新边界（我自己的发现，登记为 P2）**

`evidenceUrlOf` 现在会编 `bbox` ⇒ 证据 tab 的**兜底分支**（`ev.bbox === undefined` 才跑）
**在「本轮依据」这条路上不再执行**。逐条评估后果：

| 情形 | 旧行为 | 新行为 | 评估 |
|---|---|---|---|
| bbox 有值且与 `page` 同页 | 兜底去 `/ks/bbox` 再取一次 | 直接用引擎给的 | ✅ **更好**（少一次请求，且坐标同源） |
| bbox 有值但**不完整**（只 1 个 span） | 兜底会按目标页**筛**出更合适的 | 直接用那一个 | ⚠ **理论上可能不如兜底**；但引擎侧已按"`page_number == page_start` 优先"选过，**口径一致** |
| bbox 缺失 | 兜底跑 | 兜底跑（**未变**） | ✅ 无变化 |

⇒ 记为 **P2**（不是缺陷，是**行为变化的登记**）：**两条取坐标的路现在由引擎侧主导**；
若将来引擎的选取口径改了，兜底那条路**不会再自动纠正**。

## 5. P2 清单（都不是 P0/P1，登记备查）

1. **`bboxPage` 传了但渲染层不读**（实测 `KsEvidenceTab.tsx` 里 0 次）。
   现状**无害**（页判据用 `page`，而引擎保证两者同页），但它是**一条没人消费的通路** ——
   将来若有人以为"传了 bboxPage 就能指定页"，会踩空。
2. **§4.3 的路径变化**（兜底分支不再参与「本轮依据」）。
3. **`source_span` 覆盖率未全库统计**（只抽样确认有数据、有索引、点查 0.2 ms）。
   ⇒ **不能**声称"所有条款都有 bbox"。

## 6. 我**没有**验的（不许被读成"验过"）

1. **独立第三方复核** —— 见开头（团队五次派发全失败）。
2. **端到端真机**：引擎当时**未运行**（`/api/v1/health` 连接被拒）⇒ 没做完整问答链路。
3. **真宿主里箭头是否真的画出来**（本机 GUI 会话树渲染不出会话节点，见 `UI-BASELINE` §五）
   ⇒ 我验到的是"**bbox 一路传到证据 URL**" + "**渲染层读 `bbox` 的条件成立**"，
   **没有**在真宿主里看到箭头。
4. **深色主题**下的表现；**窄档/宽档**下的分组版式（只跑了 `smoke-turn-tab` 的静态渲染）。
5. `run-gates.ps1 -Full` 我只在**主仓**跑过（12/12）；**提取树里没跑**（全局锁，任务书明令不跑）。

## 7. 建议（留给真正的独立复核）

按优先级：
1. **§4.3 的路径变化**：引擎侧选取口径若变化，兜底不再纠正 —— 是否要加一条"两侧口径一致"的判据？
2. **分组版式的真机观感**（我只验了数据结构与静态渲染，**没看真机排版**）。
3. **`bboxPage` 的处置**：留着（无害）还是删掉（避免误导）？
