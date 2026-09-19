# 复核任务书（VERIFY-BRIEF）与复核结论的归属层

**这里放独立 verifier 的任务书与结论摘要。**

## 为什么要有这个目录（2026-09-19 整改）

此前任务书写在 `var/tmp/VERIFY-BRIEF-bNN.md`，而 `var/tmp/` 被 [.gitignore](../.gitignore) 整体忽略
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
- 这条纪律的正文在根 [AGENTS.md](../AGENTS.md) 的"复核"一节——**这里是它的证据落地处**。
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
