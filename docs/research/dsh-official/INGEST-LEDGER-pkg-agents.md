# DSH 官方文档原文入库账本

> 由 `scripts/ingest-dsh-docs-into-memory.mjs` 生成，**不要手改**（改状态文件请用脚本重跑）。
> 检出：`D:\AI\DSH\deepseek-harness` @ `ddefc45fbc`　记忆库：`coding-agent::zcode`　生成时间：2026-09-19 14:44:41（本地时间）

- 文档总数：**5** 篇 / 37,009 字节
- **逐字一致（库里 `original_text` 的 sha256 = 磁盘文件的 sha256）：5** / 5
- 不一致 / 缺失 / 取不回：**0** 篇

核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。

⚠ 哈希一致证明"库里存的正文与磁盘那份逐字节相同（按 UTF-8 文本口径）"，
**不**证明服务端抽取出的事实条数/质量正确，也不覆盖 `.agents/notes/`、`.zh.md` 译本等未纳入本账本的语料。
⚠ 「抽取事实数」为空 = 本次跑**没有重新灌它**（它先前已入且逐字一致，被跳过），不是"抽取出了 0 条"。

| 文档 | document_id | 字符 | 源 sha256(16) | 核对 | 抽取事实数 |
|---|---|---|---|---|---|
| `packages/AGENTS.md` | `dsh-pkg-agents-agents` | 6,160 | 963fb95f390bc420 | ✅ 逐字一致 |  |
| `packages/client/AGENTS.md` | `dsh-pkg-agents-client-agents` | 26,477 | cae453e2c876e560 | ✅ 逐字一致 |  |
| `packages/experimental/AGENTS.md` | `dsh-pkg-agents-experimental-agents` | 2,005 | 384f7adf154d444a | ✅ 逐字一致 |  |
| `packages/schedule/AGENTS.md` | `dsh-pkg-agents-schedule-agents` | 1,700 | bbcbacf90a34764c | ✅ 逐字一致 |  |
| `packages/web/AGENTS.md` | `dsh-pkg-agents-web-agents` | 579 | 937a0037eff925df | ✅ 逐字一致 |  |
