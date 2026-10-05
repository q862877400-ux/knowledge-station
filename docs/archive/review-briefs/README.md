# 复核任务书（VERIFY-BRIEF）与复核结论的归属层

**这里放独立 verifier 的任务书与结论摘要。**

## 为什么要有这个目录（2026-09-19 整改）

此前任务书写在 `var/tmp/VERIFY-BRIEF-bNN.md`，而 `var/tmp/` 被 [.gitignore(../../../.gitignore) 整体忽略
⇒ **复核任务书与复核结论都不在版本控制里**：换机器就没了，事后想复查"当时让 verifier 验的是哪份代码"
只能从史书里人工摘录的几句去猜。实测清理后 `var/tmp/` 里 `VERIFY-BRIEF*` **0 个**。

官方对应物是 PR body 里的 `<details><summary>Proof</summary>`（证据有归属层）。
我们等价的做法就是：**任务书与结论进版本控制**。

## 约定

- 文件名：`bNN-<短slug>.md`（`NN` 与批次号一致，与 `verify-freeze-bNN` 标签同号）。
- 任务书**必须写冻结端点**：`git tag verify-freeze-bNN` 打在要复核的 HEAD 上，
  并用 `git rev-list --count <base>..<frozen>` **数出**提交条数写进去（不凭印象写"8 个提交"）。
- verifier **在冻结提交的提取树上验**（`git worktree add` / `git archive`），
  并在报告**首尾各记一次** `git rev-parse HEAD` + `git status --short`。
- 结论只往这里写**摘要**；逐条详述可以落在这里，也可以只在史书里留一行链接。
- 这条纪律的正文在根 [AGENTS.md(../../../AGENTS.md) 的"复核"一节——**这里是它的证据落地处**。
- **⚠ 复核也要守门禁的锁**（2026-09-19 起，用血换的）：verifier 在提取树里跑冒烟时**必须**走
  `npm run smoke`（= `plugin/scripts/smoke-all.mjs`，它与 `run-gates.ps1` **共用同一个锁文件**）；
  拿到**退出码 3 = 有人在跑**，要**等**，不是失败。写成这条的原因是：上一轮的 `-Full` 里
  `smoke-chatmode` 红了 `172/173`，追下来正是**复核子代理绕过 `run-gates.ps1` 直接跑冒烟**、
  而当时的锁拦不住那条路 ⇒ 一次假红 + 一次全量重跑。**单跑某一条 `node scripts/smoke-*.mjs`
  仍然不受锁保护**，只应在确认没有别的门禁在跑时用。
- **⚠ 在提取树里跑冒烟前必须把 `KS_DATA_DIR` 指到临时目录**（2026-09-19 起）：冻结提交里的
  冒烟**可能还没有**"数据目录隔离"那个修复，而 `KS_DATA_DIR` 决定 `ks-ingest.json` /
  `ks-inspection.json` / `ks-chatmode.json` 落哪。实测后果：复核在 `35f024a` 树上跑
  `smoke-ingest` 把一条**假任务**（`pjob_smoke1`/`pending`）写进了**真实**
  `%APPDATA%\KnowledgeStation`，而真产品启动时会去**接管**它。⇒ `$env:KS_DATA_DIR = <temp>`。
  **2026-09-19 加固**：`run-gates.ps1` 现在**自己**给整轮设临时 `KS_DATA_DIR`（并在结束时恢复）
  ⇒ 走脚本这条路不会再污染；但**直接 `node scripts/smoke-*.mjs` 仍不受保护**，那条要自己设。
- **⚠ 门禁的 `-Full` 退出码才是判据**：汇总行「6/6 步通过」在 2026-09-19 之前可能伴随
  **exit 1**（棘轮红）——那次是"棘轮与环境耦合"的假绿，已修；此后棘轮结论直接印在汇总行上。
  复核若见到红，先看**棘轮那一行**（`passed+skipped` 总账与 `skip_reasons` 有没有新理由），
  再看是不是任务书要求的等锁。

## 已入库的复核材料（2026-09-24 补录）

⚠ **上面那条病根又犯了一次**：任务书与结论仍写在 `var/tmp/`，而它被整体忽略 ⇒ 2026-09-24 收工时
才发现 `var/tmp/verify-reports/` 里 **7 份复核报告 + 3 份任务书都不在版本控制里**（清一次树就全没）。
现按**字节级复制**（`Copy-Item`，不手抄）搬进本目录，`var/tmp/` 那一份**保留不动**：

| 批次 | 任务书 | 复核结论 |
|---|---|---|
| B1+B2（重新解析丢归属 / 叠字假绿） | `b1b2-brief.md` | `b1b2-report.md` |
| B3a（分类号引擎自愈） | —（任务书未留盘） | `b3a-engine-report.md` |
| B3b（分类号界面半边） | `b3b-ccs-ui-brief.md` | `b3b-ccs-ui-report.md` |
| B5（门禁白名单只增不减） | `b5-gate-brief.md` | `b5-gate-report.md` |
| B6（黑屏修复 + 棘轮基线） | — | `b6-p0-report.md` |
| B4（分类号 5 提交） | — | `ccs-chain-report.md` |
| 判据补硬（`d508773`） | — | `d508773-report.md` |
| 征求意见稿入库 + 公告批量入库（冻结 `verify-freeze-ingest` = `1da33f8`，基线 `4850f12`，8 笔） | 任务书在会话里（未单独留盘，见下） | [[VERIFY-REPORT-ingest.md]] |
| **Jev 合规护栏**（冻结 `verify-freeze-jev-b1` = `7cbaf4a`，基线 `2f5c2f6`，1 笔） | 任务书在会话里（未单独留盘） | [[VERIFY-REPORT-jev-b1.md]] |

**`VERIFY-REPORT-ingest.md`（2026-09-24）**：结论 **PASS-with-gaps** —— 产品行为零错
（真库只读四条事实全对、统计三数自洽、16 条 `reference` 逐字对上、`client.js` 与源码现构建逐字节一致），
判据/记账上 2 HIGH + 5 MED + 8 LOW，**已逐条落地**（修单见开发史 §10.193 末"复核修单"与提交 `74d51a8`）。
⚠ 两条最要紧的：① **`PRAGMA foreign_keys=OFF` 零牙齿**（去掉它迁移用例仍全绿，而真库会因此
被级联删掉 52 万行 `clause_revision`）—— 现补"迁移前后子表行数不变"的断言；
② **冻结提交上 `mypy` 是红的**（本批引入 4 处 arg-type，作者 12 分钟后才修）⇒
"全绿"只对**修后那棵树**成立。另附 `announce-nav-cleanup-20260924.md`：
那次真库删除（22 行栏目导航型误发现）的**完整清单与复算办法** ——
它是本轮唯一一次删真实数据，证据不能只留在被 `.gitignore` 挡着的 `var/tmp/`。

**`VERIFY-REPORT-jev-b1.md`（2026-09-24）结论：FAIL —— 5 个 MED + 1 个 HIGH 门禁阻塞，全部已修。**
复核确认的部分：9/9 必测变异全红、额外的宽泛词表变异也红、新增断言**无恒真**、
`def`/422/`available=false`/词表直达三类静默回落都用桩验过、`registerKsComplianceRoutes`
三个调用点都改到、Jev 不参与内容/引用正确性。**它抓到的（都已修 + 补了"修后牙"）**：

1. **MED-1 熔断冷却是坏的**：`_opened_at` 只在 streak **恰好等于**阈值时刷新 ⇒ 冷却 60s 后
   再失败多少次都**开不了熔断**（每条消息都去等一次超时）。改为按"上次熔断时刻"判、
   冷却后的失败**重新计时**。
2. **MED-2 契约过浅**：`bool=True`（Python bool 是 int 子类）、`noul=1.1`、回包
   `model=jev-latest` 都被当合法。新增 `_validate_body`：**逐题**验键一一对应、数值在 0~1
   （显式排除 bool）、`model` 必须等于钉住的版本号。
3. **MED-3 2s 外网没进限流**：`/api/v1/laws/compliance-guard` 原先 `is_heavy_path=false`
   ⇒ 每条用户消息都占线程池令牌。已加进 `HEAVY_PREFIXES`（**逐条列**，不用 `/laws/` 前缀——
   那会把两条廉价端点也关进闸门，§10.82 记的"闸门自己造排队"）。
4. **MED-4 "2s"没钉死**：原断言是 `== JEV_TIMEOUT_S`（跟着常量走）⇒ 改成 20s 用例照样绿。
   现在断言**字面值 2.0**。
5. **MED-5 新端点无契约测试**：禁掉 `if verdict is None` 那支，Jev+threadpool 相关 26 条测试
   仍全绿。补三条端点契约（422 缺 text / `available=false` / 正常透出）+ 重活闸门断言。
6. **MED-6 审计两头不准**：原先只有**成功路径**登记 ⇒ HTTP 503 那次外发在审计里查不到；
   而且源码写"只读"是错的（`record_egress` **会写** `debug_dump`）。改为**每次外发都审计**
   （成功/HTTP 失败/异常三路），并把不准确的说法删掉。
7. **HIGH 门禁阻塞（CRLF 检出）**：`smoke-compliance-sentry.mjs` 的 `split('---\n')`
   在 CRLF 检出里切不开 ⇒ 整份 SKILL.md（含 front-matter）被当正文 ⇒ 必红。
   改为**先归一换行再切**；已用 `var/tmp/verify-crlf-skill.py` **实测**（临时转 CRLF 跑 ⇒ exit 0，
   再字节级还原）。
8. **LOW（复核说的"注释错路"）**：父代理核过 5 处路径引用**全对**（`jev_guard.py` 确实在
   `src/core/llm/`）⇒ 记为**复核误报**，留痕不静默丢弃。

**修后自证**：`var/tmp/mutate-jev-guard.py` **17/17 变异全红、全部字节级还原**
（9 条原有 + 8 条针对这 6 MED 与 HIGH 的"修后牙"）。

- **两边内容不同时以本目录为准**，并当场把差异登记到 [开发史(../../DEVELOPMENT-HISTORY.md)。
- ⚠ **还只在 `var/tmp/` 的**：`verify-reports/B7-REPORT.md`（B7 那批的**实施**报告，与上面这批
  "复核结论"不同类；根目录已有 `B3A-REPORT.md`/`B3B-REPORT.md` 的先例，搬不搬**待定**）
  ＋ 三份 `verify-*-residuals.md` 笔记（残余清单，内容已进史书）。

