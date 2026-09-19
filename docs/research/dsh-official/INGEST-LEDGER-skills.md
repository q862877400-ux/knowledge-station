# DSH 官方文档原文入库账本

> 由 `scripts/ingest-dsh-docs-into-memory.mjs` 生成，**不要手改**（改状态文件请用脚本重跑）。
> 检出：`D:\AI\DSH\deepseek-harness` @ `ddefc45fbc`　记忆库：`coding-agent::zcode`　生成时间：2026-09-19 14:45:11（本地时间）

- 文档总数：**28** 篇 / 221,081 字节
- **逐字一致（库里 `original_text` 的 sha256 = 磁盘文件的 sha256）：28** / 28
- 不一致 / 缺失 / 取不回：**0** 篇

核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。

⚠ 哈希一致证明"库里存的正文与磁盘那份逐字节相同（按 UTF-8 文本口径）"，
**不**证明服务端抽取出的事实条数/质量正确，也不覆盖 `.agents/notes/`、`.zh.md` 译本等未纳入本账本的语料。
⚠ 「抽取事实数」为空 = 本次跑**没有重新灌它**（它先前已入且逐字一致，被跳过），不是"抽取出了 0 条"。

| 文档 | document_id | 字符 | 源 sha256(16) | 核对 | 抽取事实数 |
|---|---|---|---|---|---|
| `.agents/skills/dsh-archive-agent-notes/SKILL.md` | `dsh-skills-dsh-archive-agent-notes-skill` | 6,126 | 86b7c6338f2ed290 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-ci-test-reliability/SKILL.md` | `dsh-skills-dsh-ci-test-reliability-skill` | 9,432 | 58e5de5c9cf7061e | ✅ 逐字一致 |  |
| `.agents/skills/dsh-ci-test-reliability/references/ci-flake-diagnosis.md` | `dsh-skills-dsh-ci-test-reliability-references-ci-flake-diagnosis` | 5,346 | 9fb8d3a56e9e9033 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-code-review/SKILL.md` | `dsh-skills-dsh-code-review-skill` | 9,219 | 6c862b17bca7d15f | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/SKILL.md` | `dsh-skills-dsh-doc-skill` | 17,989 | 5704dcf1d81dcda3 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/references/metadata-links-i18n.md` | `dsh-skills-dsh-doc-references-metadata-links-i18n` | 8,922 | 7bc08f3c8270ce1c | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/references/review.md` | `dsh-skills-dsh-doc-references-review` | 6,050 | 81f5bb876ad13bd2 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/references/structure-hierarchy.md` | `dsh-skills-dsh-doc-references-structure-hierarchy` | 6,272 | 869ae393be457951 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/references/style.md` | `dsh-skills-dsh-doc-references-style` | 4,109 | 62600401bc7d771e | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/references/website-sync.md` | `dsh-skills-dsh-doc-references-website-sync` | 6,848 | 6ab2dc43aa43c964 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/templates/package-bundle.md` | `dsh-skills-dsh-doc-templates-package-bundle` | 3,397 | 9f6751700f4886b8 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/templates/package-group.md` | `dsh-skills-dsh-doc-templates-package-group` | 1,859 | 53cb8a73b3d465e8 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/templates/package-library.md` | `dsh-skills-dsh-doc-templates-package-library` | 3,538 | e65883a53950806e | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/templates/package-reference.md` | `dsh-skills-dsh-doc-templates-package-reference` | 3,844 | b9e75748bd32b409 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/templates/persistence-change.md` | `dsh-skills-dsh-doc-templates-persistence-change` | 3,936 | 984451269be8f0d5 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/templates/persistence-format.md` | `dsh-skills-dsh-doc-templates-persistence-format` | 2,412 | 8e2cfd248807a49f | ✅ 逐字一致 |  |
| `.agents/skills/dsh-doc/templates/persistence-release.md` | `dsh-skills-dsh-doc-templates-persistence-release` | 3,123 | 641b2c8a78da2d88 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-find-simplifications/SKILL.md` | `dsh-skills-dsh-find-simplifications-skill` | 15,988 | 03d56b6412abfaa7 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-merging-stacked-prs/SKILL.md` | `dsh-skills-dsh-merging-stacked-prs-skill` | 7,835 | d7b45f7c56f741e7 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-pre-push-checks/SKILL.md` | `dsh-skills-dsh-pre-push-checks-skill` | 10,967 | 7091f3061de122d2 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-prose-standard/SKILL.md` | `dsh-skills-dsh-prose-standard-skill` | 9,615 | df56be84f9ee917a | ✅ 逐字一致 |  |
| `.agents/skills/dsh-prose-standard/references/examples.md` | `dsh-skills-dsh-prose-standard-references-examples` | 9,329 | ea37f63a96458206 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-speed-up-perf/SKILL.md` | `dsh-skills-dsh-speed-up-perf-skill` | 12,146 | f71345f9e7b398b5 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-translate-docs/SKILL.md` | `dsh-skills-dsh-translate-docs-skill` | 10,535 | 198f0edaed6322d8 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-trim-cot-leakage/SKILL.md` | `dsh-skills-dsh-trim-cot-leakage-skill` | 7,597 | 13034b0f3950cc5c | ✅ 逐字一致 |  |
| `.agents/skills/dsh-trim-cot-leakage/references/examples.md` | `dsh-skills-dsh-trim-cot-leakage-references-examples` | 12,510 | 893ad4a0680ecd18 | ✅ 逐字一致 |  |
| `.agents/skills/dsh-trim-cot-leakage/references/recall-batteries.md` | `dsh-skills-dsh-trim-cot-leakage-references-recall-batteries` | 4,821 | 449529dfba146c46 | ✅ 逐字一致 |  |
| `.agents/skills/record-browser-gif/SKILL.md` | `dsh-skills-record-browser-gif-skill` | 16,514 | 9696ca959e1f1941 | ✅ 逐字一致 |  |
