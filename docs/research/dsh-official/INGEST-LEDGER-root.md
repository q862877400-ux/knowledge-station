# DSH 官方文档原文入库账本

> 由 `scripts/ingest-dsh-docs-into-memory.mjs` 生成，**不要手改**（改状态文件请用脚本重跑）。
> 检出：`D:\AI\DSH\deepseek-harness` @ `ddefc45fbc`　记忆库：`coding-agent::zcode`　生成时间：2026-09-19 15:34:03（本地时间）

- 文档总数：**12** 篇 / 55,075 字节
- **逐字一致（库里 `original_text` 的 sha256 = 磁盘文件的 sha256）：12** / 12
- 不一致 / 缺失 / 取不回：**0** 篇

核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。

⚠ 哈希一致证明"库里存的正文与磁盘那份逐字节相同（按 UTF-8 文本口径）"，
**不**证明服务端抽取出的事实条数/质量正确，也不覆盖 `.agents/notes/`、`.zh.md` 译本等未纳入本账本的语料。
⚠ 「抽取事实数」为空 = 本次跑**没有重新灌它**（它先前已入且逐字一致，被跳过），不是"抽取出了 0 条"。

| 文档 | document_id | 字符 | 源 sha256(16) | 核对 | 抽取事实数 |
|---|---|---|---|---|---|
| `AGENTS.md` | `dsh-root-agents` | 17,174 | e232924a880ba8ba | ✅ 逐字一致 |  |
| `BENCHMARK.md` | `dsh-root-benchmark` | 231 | 3e38b63e4507b4db | ✅ 逐字一致 |  |
| `BRAND_GUIDELINES.md` | `dsh-root-brand-guidelines` | 1,980 | 0f3e1150bfa3d488 | ✅ 逐字一致 |  |
| `BRAND_GUIDELINES.zh.md` | `dsh-root-brand-guidelines-zh` | 689 | da32025bf0f7e36c | ✅ 逐字一致 |  |
| `CLAUDE.md` | `dsh-root-claude` | 9 | a54ff182c7e8acf5 | ✅ 逐字一致 |  |
| `CONTRIBUTING.md` | `dsh-root-contributing` | 1,570 | 9cd02c5b784b4a61 | ✅ 逐字一致 |  |
| `CONTRIBUTING.zh.md` | `dsh-root-contributing-zh` | 624 | 260a72b70330f68e | ✅ 逐字一致 |  |
| `README.md` | `dsh-root-readme` | 2,440 | b43a2af65d10028e | ✅ 逐字一致 |  |
| `README.zh.md` | `dsh-root-readme-zh` | 2,595 | 8037f870a6eac6ee | ✅ 逐字一致 |  |
| `SAFETY.md` | `dsh-root-safety` | 1,669 | 62075bb51e0f7790 | ✅ 逐字一致 |  |
| `SAFETY.zh.md` | `dsh-root-safety-zh` | 610 | d021947c09c83eb3 | ✅ 逐字一致 |  |
| `THIRD_PARTY_NOTICES.md` | `dsh-root-third-party-notices` | 22,022 | ab35d5fe3d073ccb | ✅ 逐字一致 |  |
