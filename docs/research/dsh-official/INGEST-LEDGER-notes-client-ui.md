# DSH 官方文档原文入库账本

> 由 `scripts/ingest-dsh-docs-into-memory.mjs` 生成，**不要手改**（改状态文件请用脚本重跑）。
> 检出：`D:\AI\DSH\deepseek-harness` @ `ddefc45fbc`　记忆库：`coding-agent::zcode`　生成时间：2026-09-19 13:57:10（本地时间）

- 文档总数：**10** 篇 / 121,128 字节
- **逐字一致（库里 `original_text` 的 sha256 = 磁盘文件的 sha256）：10** / 10
- 不一致 / 缺失 / 取不回：**0** 篇

核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。

⚠ 哈希一致证明"库里存的正文与磁盘那份逐字节相同（按 UTF-8 文本口径）"，
**不**证明服务端抽取出的事实条数/质量正确，也不覆盖 `.agents/notes/`、`.zh.md` 译本等未纳入本账本的语料。
⚠ 「抽取事实数」为空 = 本次跑**没有重新灌它**（它先前已入且逐字一致，被跳过），不是"抽取出了 0 条"。

| 文档 | document_id | 字符 | 源 sha256(16) | 核对 | 抽取事实数 |
|---|---|---|---|---|---|
| `.agents/notes/implemented/architecture/2026-07-23-client-plugin-loading-model.md` | `dsh-notes-implemented-architecture-2026-07-23-client-plugin-loading-model` | 28,197 | e5d43a58c7279a4e | ✅ 逐字一致 |  |
| `.agents/notes/implemented/architecture/2026-08-15-client-shells-and-dynamic-packages.md` | `dsh-notes-implemented-architecture-2026-08-15-client-shells-and-dynamic-packages` | 10,771 | 6495c2402f0e8f7e | ✅ 逐字一致 |  |
| `.agents/notes/implemented/architecture/2026-09-05-client-resource-model.md` | `dsh-notes-implemented-architecture-2026-09-05-client-resource-model` | 12,209 | 90d16546025b6ac6 | ✅ 逐字一致 |  |
| `.agents/notes/implemented/architecture/2026-09-05-shared-client-control-primitives.md` | `dsh-notes-implemented-architecture-2026-09-05-shared-client-control-primitives` | 11,797 | 1a0c4c2b792d4891 | ✅ 逐字一致 |  |
| `.agents/notes/implemented/architecture/2026-09-05-sidebar-tab-types-and-navigation.md` | `dsh-notes-implemented-architecture-2026-09-05-sidebar-tab-types-and-navigation` | 20,566 | fa39921cb403e7d8 | ✅ 逐字一致 |  |
| `.agents/notes/implemented/architecture/2026-09-08-desktop-bundled-runtime-and-external-plugins.md` | `dsh-notes-implemented-architecture-2026-09-08-desktop-bundled-runtime-and-external-plugins` | 9,541 | 6cc74135ba5be067 | ✅ 逐字一致 |  |
| `.agents/notes/implemented/architecture/2026-09-11-plugin-owned-message-projections.md` | `dsh-notes-implemented-architecture-2026-09-11-plugin-owned-message-projections` | 3,915 | df1d55649cd2fe05 | ✅ 逐字一致 |  |
| `.agents/notes/implemented/architecture/2026-09-14-sidebar-layout-provider-recovery.md` | `dsh-notes-implemented-architecture-2026-09-14-sidebar-layout-provider-recovery` | 3,892 | 253f2fce1a83d699 | ✅ 逐字一致 |  |
| `.agents/notes/implemented/feature/2026-09-04-right-sidebar-docking-infrastructure.md` | `dsh-notes-implemented-feature-2026-09-04-right-sidebar-docking-infrastructure` | 18,222 | a5c8c0885a976fdd | ✅ 逐字一致 |  |
| `.agents/notes/implemented/feature/2026-09-08-sidebar-default-pages.md` | `dsh-notes-implemented-feature-2026-09-08-sidebar-default-pages` | 1,710 | ffd8bc6290b85462 | ✅ 逐字一致 |  |
