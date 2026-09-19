# DSH 官方文档原文入库账本

> 由 `scripts/ingest-dsh-docs-into-memory.mjs` 生成，**不要手改**（改状态文件请用脚本重跑）。
> 检出：`D:\AI\DSH\deepseek-harness` @ `ddefc45fbc`　记忆库：`coding-agent::zcode`　生成时间：2026-09-19 15:41:59（本地时间）

- 文档总数：**12** 篇 / 34,241 字节
- **逐字一致（库里 `original_text` 的 sha256 = 磁盘文件的 sha256）：12** / 12
- 不一致 / 缺失 / 取不回：**0** 篇

核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。

⚠ 哈希一致证明"库里存的正文与磁盘那份逐字节相同（按 UTF-8 文本口径）"，
**不**证明服务端抽取出的事实条数/质量正确，也不覆盖 `.agents/notes/`、`.zh.md` 译本等未纳入本账本的语料。
⚠ 「抽取事实数」为空 = 本次跑**没有重新灌它**（它先前已入且逐字一致，被跳过），不是"抽取出了 0 条"。

| 文档 | document_id | 字符 | 源 sha256(16) | 核对 | 抽取事实数 |
|---|---|---|---|---|---|
| `packages/CLAUDE.md` | `dsh-pkg-docs-claude` | 9 | a54ff182c7e8acf5 | ✅ 逐字一致 |  |
| `packages/experimental/webworker-runtime/tests/fixtures/vfs-example/workspace/.agents/skills/preview-tour/SKILL.md` | `dsh-pkg-docs-experimental-webworker-runtime-tests-fixtures-vfs-example-workspace-agents-skills-preview-tour-skill` | 257 | 4486d12747d1c0fd | ✅ 逐字一致 |  |
| `packages/experimental/webworker-runtime/tests/fixtures/vfs-example/workspace/PREVIEW.md` | `dsh-pkg-docs-experimental-webworker-runtime-tests-fixtures-vfs-example-workspace-preview` | 360 | 87fed9d353c14ff8 | ✅ 逐字一致 |  |
| `packages/preset/agent-presets/presets/cordis/skills/cordis-plugin-development/SKILL.md` | `dsh-pkg-docs-preset-agent-presets-presets-cordis-skills-cordis-plugin-development-skill` | 8,287 | 84daca3e10f6e557 | ✅ 逐字一致 |  |
| `packages/preset/agent-presets/presets/cordis/skills/editing-cordis-compositions/SKILL.md` | `dsh-pkg-docs-preset-agent-presets-presets-cordis-skills-editing-cordis-compositions-skill` | 8,950 | dbf68650fc61260b | ✅ 逐字一致 |  |
| `packages/skill/skill-badge/assets/dsh-badge.md` | `dsh-pkg-docs-skill-skill-badge-assets-dsh-badge` | 1,299 | d5eea609823a8d72 | ✅ 逐字一致 |  |
| `packages/skill/skill-office/assets/office-docx/SKILL.md` | `dsh-pkg-docs-skill-skill-office-assets-office-docx-skill` | 4,286 | 6ffd5866a8b025db | ✅ 逐字一致 |  |
| `packages/skill/skill-office/assets/office-pptx/SKILL.md` | `dsh-pkg-docs-skill-skill-office-assets-office-pptx-skill` | 5,249 | 56c3eb3a6e1a8d9a | ✅ 逐字一致 |  |
| `packages/skill/skill-office/assets/office-xlsx/SKILL.md` | `dsh-pkg-docs-skill-skill-office-assets-office-xlsx-skill` | 5,411 | b8394b54de0d14c9 | ✅ 逐字一致 |  |
| `packages/test-support/session-snapshot/tests/fixtures/record-suite/rec-pin/system-prompt.expected.md` | `dsh-pkg-docs-test-support-session-snapshot-tests-fixtures-record-suite-rec-pin-system-prompt-expected` | 11 | 698951a08c1bd1e2 | ✅ 逐字一致 |  |
| `packages/test-support/session-snapshot/tests/fixtures/suite/pin-turn/system-prompt.expected.md` | `dsh-pkg-docs-test-support-session-snapshot-tests-fixtures-suite-pin-turn-system-prompt-expected` | 74 | 4606297b0d8b7dda | ✅ 逐字一致 |  |
| `packages/test-support/session-snapshot/tests/fixtures/suite/plain-turn/system-prompt.1.expected.md` | `dsh-pkg-docs-test-support-session-snapshot-tests-fixtures-suite-plain-turn-system-prompt-1-expected` | 27 | 287b0a2e80e192b3 | ✅ 逐字一致 |  |
