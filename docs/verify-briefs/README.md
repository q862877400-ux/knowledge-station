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
