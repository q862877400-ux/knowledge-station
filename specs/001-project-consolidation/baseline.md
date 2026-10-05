# 开工基线（2026-10-05）

> 本文件是 [tasks.md](tasks.md) T002 的产出。**开工前跑一次、收口再跑一次比。**

## 一、别人的未提交改动（MUST 逐字节不变）

| 文件 | SHA256 |
|---|---|
| `pelican-bike.html` | `4851D3D0FD2A89A94DCCA1D523390A4B60768B5FBCC47337A70C655F85A6DBD1` |
| `tests\test_jev_cn_baseline.py` | `A6B246F4D24FCB44B6F26F0115F40F169DF374D525B362BCDD3E2D17D69E0B66` |
| `docs\research\HINDSIGHT-CAPABILITY-AUDIT-2026-09-28.md` | `0C55948A978989C8C062D696E7A9FF49A0056EA01164A623BEDF9330C0124B6C` |
| `docs\research\HINDSIGHT-FACTCHECK-2026-09-30.md` | `3160C0BA5D8045E3F1DB605E8DB75A240FFA2060FC0313AD610056F9ECFDE933` |
| `plugin/src/compliance-sentry.js.bak-20260927-003328-before-v4-source` | `11FD39B82A80683A16ACC205BEE4C1FC1045AB047A4677332823BB62F8AE3918` |
| `plugin/src/compliance-sentry.js.bak-20260927-003346-before-v4-source` | `11FD39B82A80683A16ACC205BEE4C1FC1045AB047A4677332823BB62F8AE3918` |
| `plugin/src/tool-details.js.bak-20260927-003346-before-v4-source` | `7F43DCF7FBF506291319055EE257736585A23D24BC9AD9DBBC92473C018D3005` |
| `plugin/src/tool-details.js.bak-20260927-003530-before-v4-source` | `7F43DCF7FBF506291319055EE257736585A23D24BC9AD9DBBC92473C018D3005` |

## 二、开工时的 git status

```
(见下)
```

## 三、开工时的规模

- docs/ 下 md：**116 份 / 5298 KB**
- src/ 下 py：**152 个**
- plugin/src 下 js：**19 个**
- 最大单文档：`docs/DEVELOPMENT-HISTORY.md` **1053 KB**
```
 M AGENTS.md
?? docs/research/HINDSIGHT-CAPABILITY-AUDIT-2026-09-28.md
?? docs/research/HINDSIGHT-FACTCHECK-2026-09-30.md
?? pelican-bike.html
?? plugin/src/compliance-sentry.js.bak-20260927-003328-before-v4-source
?? plugin/src/compliance-sentry.js.bak-20260927-003346-before-v4-source
?? plugin/src/tool-details.js.bak-20260927-003346-before-v4-source
?? plugin/src/tool-details.js.bak-20260927-003530-before-v4-source
?? specs/001-project-consolidation/baseline.md
?? tests/test_jev_cn_baseline.py
```

## 四、开工时的断链基线（T005）

命令：`python scripts/docs/check-links.py`
结果：扫描 **147** 个 markdown 文件，检查 **268** 条链接（另跳过 19 条疑似示例），
**断链 12 处**——这是开工前就有的，不是本特征造成的。

| # | 位置 | 目标 | 判定 |
|---:|---|---|---|
| 1 | `docs/CHANNEL-COVERAGE-PLAN.md:735` | `../NOT-DOING.md` | 真错：从 `docs/` 出发应写 `NOT-DOING.md` |
| 2 | `docs/UI-BASELINE.md:7` | `../NOT-DOING.md` | 真错：同上 |
| 3 | `docs/UI-BASELINE.md:10` | `../NOT-DOING.md` | 真错：同上 |
| 4 | `docs/research/weknora-assessment.md:124` | `NOT-DOING.md` | 真错：从 `docs/research/` 出发应写 `../NOT-DOING.md` |
| 5 | `docs/research/weknora-assessment.md:145` | `../weknora-ui/01-chat-and-citations.md` | 真错：应是 `weknora-ui/...` |
| 6 | `docs/research/weknora-ui/00-index-and-proposal.md:5` | `../INTERACTION-DESIGN.md` | 真错：应是 `../../INTERACTION-DESIGN.md` |
| 7 | `docs/verify-briefs/README.md:7` | `../.gitignore` | 真错：应是 `../../.gitignore` |
| 8 | `docs/verify-briefs/README.md:22` | `../AGENTS.md` | 真错：应是 `../../AGENTS.md` |
| 9 | `docs/research/retrieval-pipeline-design-merge.md:66` | `../storage/schema.sql#L137-L147` | 待判：目标在 `src/core/storage/` |
| 10 | `docs/research/dsh-official/ERRATA-alpha.2.md:166` | `../architecture/2026-09-14-*.md` | 待判：指向的是 **DSH 官方仓**的路径，不是本仓 |
| 11 | `docs/research/dsh-official/dshdocs-F.md:55` | `foo.md` / `foo.zh.md` | 疑似示例文本，非真引用 |

**⇒ SC-001 要求收口时断链为 0，因此这 12 处必须逐条定性并修掉（不能只把计数改掉）。**

### 断链基线的处置（T005 收口）

上表 **12 处已全部清掉，现为 0**。分两类：

**真路径错，改了引用（9 处）**：这是开工前就存在的错，不是本特征造成的
- `docs/CHANNEL-COVERAGE-PLAN.md`：`../NOT-DOING.md` → `NOT-DOING.md`
- `docs/UI-BASELINE.md`：同上（2 处）
- `docs/research/weknora-assessment.md`：`NOT-DOING.md` → `../NOT-DOING.md`；`../weknora-ui/...` → `weknora-ui/...`
- `docs/research/weknora-ui/00-index-and-proposal.md`：`../INTERACTION-DESIGN.md` → `../../INTERACTION-DESIGN.md`
- `docs/verify-briefs/README.md`：`../.gitignore` → `../../.gitignore`；`../AGENTS.md` → `../../AGENTS.md`
- `docs/research/retrieval-pipeline-design-merge.md`：`../storage/schema.sql` → `../../src/core/storage/schema.sql`

**不是本仓的引用，改成行内代码（3 处，含检查器自身的假阳性）**
- `docs/research/dsh-official/dshdocs-F.md`：`foo.md` / `foo.zh.md`——原文是**举例**，被检查器误判；
  根因是检查器**没有剥掉行内代码段**。已修检查器（`INLINE_CODE_RE`）
- `docs/research/dsh-official/ERRATA-alpha.2.md`：那是一条**引用 DSH 官方文档原话**里的链接，
  路径指 DSH 官方仓的 `architecture/`，本仓没有该文件。已改为行内代码并写明出处

**⇒ 结论：断链基线现在是 0。改名之后若不为 0，那就是改名造成的。**

## 五、实施过程踩到的坑（本次新增，防重犯）

**坑 1：`git add -A -- docs/` 会扫进别人的未提交件。**
同一个错在本次会话里犯了 **3 次**（每次都要 `reset`/`restore --staged` 摘出来）。
- 根因：`-A` 把**未跟踪**文件也算作新增。
- 防法：**只加明确列出的路径**；提交前先看 `git diff --cached --name-only`。
- 本仓有两份**永远不会被提交**的别人的文件：
  `docs/research/HINDSIGHT-CAPABILITY-AUDIT-2026-09-28.md`、
  `docs/research/HINDSIGHT-FACTCHECK-2026-09-30.md`。

**坑 2：文件遍历不要用 `rglob` 走全树。**
`REPO.rglob("*.md")` 会先走完 `node_modules` 与 `.venv`（数万个文件）再过滤，
实测**卡死超 120 秒**。改用 `os.walk` + `dirnames[:]` 剪枝后 **0.2 秒**。
`var/` 也必须剪——它是本机产物，实测不剪会扫到 3590 个 md，把真问题淹掉。

**坑 3：中文引号不能直接写进 Python 字符串。**
`print(f"...条"疑似示例"（...")` 会被内层直引号截断，**语法错**。
写中文引号要么用「」，要么用单引号包裹字符串。改完 **MUST 跑一次 `py_compile`**。

**坑 4：markdown 链接检查必须先剥行内代码段。**
`\\[English](foo.md)\\ ` 这种是**讲约定的举例**，不是引用；
不剥会把举例报成断链（实测 2 处假阳性）。已加 `INLINE_CODE_RE`。

## 六、门禁基线（补记 —— 我开工时漏抓了）

**⚠ 我开工时门禁卡住（僵尸锁，见 §五 坑 1 的同类问题），因此没有抓到开工时的门禁基线。
这是疏漏：现在知道它当时就是红的。**

### 门禁 -Quick 实测结果（2026-10-05 23:10，改名提交 1427060 之后）

| 步骤 | 结果 |
|---|---|
| `tsc`（客户端类型） | ⛔ **失败** —— 6+ 处 Icon*OutlineRegular 不存在 |
| `mypy`（引擎类型） | ✅ 通过（152 个源文件，0 问题） |
| `verify:commands` | ✅ 22/22 通过 |
| `pssa-guard` | ✅ 通过（9 个脚本，零命中） |
| `smoke`（全链） | 见下 |

### tsc 失败的真实根因（**不是本特征造成的**，机械可证）

**机械证据**：
1. 本特征只改了 `src/` 下的 Python **注释文本**、`docs/`、`scripts/`——
   **一个 `plugin/client/*.tsx` 都没碰**（`git diff --name-only 4b4c2cb..HEAD` 可验）
2. 报错文件的最后一次改动是 `dbe39bc 2026-09-28`
   ——「**fix(客户端): DSH 升级后图标导出改名 —— 74 处 Icon\*Outline14|16 → Icon\*OutlineRegular**」
3. **而现在的报错说 `*Regular` 不存在，应该用 `*14` / `*16`** —— 与 09-28 那次**方向相反**

**⇒ 结论：DSH 宿主在 09-28 之后又调整了图标导出名，本仓 `plugin/client/` 的三个页面跟不上。**
**⇒ 这是开工前就存在的红，与本次改名无关。**

### 受影响文件（3 个）

`plugin/client/KsCapabilityPage.tsx` / `KsChannelsPanel.tsx` / `KsKnowledgePage.tsx`

**⚠ 未修。** 理由：本特征的边界是"文件组织与文档"，不包含 DSH 客户端适配；
且修它需要先确认 DSH 当前真实的导出名。**登记为独立缺陷，不动它。**

### smoke（全链）失败：**原因未确定，不声称与本特征无关**

| 项 | 值 |
|---|---|
| 结果 | ⛔ exit=1，失败于 `scripts/smoke-kb-pad-pixels.mjs` |
| 红的场景 | **2 / 约 30**：`kb|kb-filemenu@520`、`kb|kb-dirmenu@520` |
| 现象 | 两者都是 `ui-render-shot exit=null`（截图子进程没跑完） |
| 该步耗时 | **761.4 秒 / 预算 240 秒**（日志自标"性能异常，不是正常的慢"） |

**证据不足以判定归属**：
- **支持"无关"的**：红的两个是 **UI 菜单场景**，而本特征改的是文档链接与 Python 注释，
  一个 `plugin/client/*.tsx` 都没碰
- **支持"存疑"的**：**没有开工前的 smoke 基线可对照**（开工时门禁卡在僵尸锁上）；
  且该步超预算 3 倍，**跑的时候本机同时在跑别的作业**（本轮的门禁本身也是后台作业）

**⇒ 判定：原因未确定。** 处置：
1. **不许把它记成"与本特征无关"**——没有证据
2. **收口前 MUST 在安静机器上（无并发作业）重跑一次 smoke**；
   若仍红，再用 `git worktree` 在改名前的提交上跑同一脚本做对照
3. 本仓 `docs/TEST-FLAKES.md` 有已知竞态型 flake 清单，重跑时先对一遍

**⚠ 未办**：重跑与对照两条都还没做。登记为收口前的必办项。
