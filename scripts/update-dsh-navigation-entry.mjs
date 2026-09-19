#!/usr/bin/env node
/**
 * 更新 Hindsight 里 `dsh` 那条**导航件**：在它原有正文之外**加**「原文层」与「本条更正」两节。
 *
 * 为什么用脚本而不是 `hindsight_ingest_document` 重写一遍：
 *   那条现有 8,267 字符是**亲读第一手结论**，我手工重打=又抄一次（本项目已实测手抄 2.6% 失真）。
 *   这里 GET 回 `original_text`、**原样拼**新节、再 POST 写回 ⇒ 旧正文**字节级保持**，
 *   且写回后**校验旧正文仍是子串**（校验不过就算失败，不假装成功）。
 *
 * 幂等：看门标记（MARKER）已在正文里就直接退出，不会越加越长。
 *
 * 写入协议同 `ingest-dsh-docs-into-memory.mjs`（POST /memories，update_mode 默认 replace）。
 */
import { createHash } from 'node:crypto'

const API = 'http://127.0.0.1:8888'
const BANK = 'coding-agent::zcode'
const ID = 'dsh'
const MARKER = '## 〇、本条之上还有一层：官方原文已**逐字入库**'

const url = `${API}/v1/default/banks/${encodeURIComponent(BANK)}/documents/${encodeURIComponent(ID)}`

const cur = await (await fetch(url)).json()
const before = cur.original_text
if (typeof before !== 'string' || before.length === 0) {
  console.error('❌ 没取到 dsh 的 original_text，不继续。')
  process.exit(1)
}
const beforeHash = createHash('sha256').update(Buffer.from(before, 'utf8')).digest('hex')
if (before.includes(MARKER)) {
  console.log('已是更新后的版本（看门标记在），无需重复写。')
  process.exit(0)
}

const header = `${MARKER}

**2026-09-19 增补。** 本条下面是"提炼 + 导航"层（我自己读后的结论、带 file:line）。
**原文层现在也在库里了**，两层职责不同：

| 层 | 在哪 | 用途 |
|---|---|---|
| **原文层（逐字）** | Hindsight，171 条，doc_id 前缀 **\`dsh-docs-\`**（如 \`dsh-docs-subsystems-sidebar-right\`） | **引用/核对**：回答"官方原话到底是什么" |
| **提炼层** | 本条 + 8 份分片（\`dsh-a-ui\`…\`dsh-h-12\`） | **导航/判断**：回答"该用哪个现成件、哪里有坑" |
| 账本 | 仓库 \`docs/research/dsh-official/INGEST-LEDGER.md\` | 每篇的 doc_id / 字符数 / **源文件 sha256** |
| 入库与核对脚本 | 仓库 \`scripts/ingest-dsh-docs-into-memory.mjs\` | 幂等可续跑；**逐字核对**（库里 \`original_text\` 的 sha256 = 磁盘文件 sha256） |

事实与口径：
- 范围 = \`docs/\` **171 篇英文正本**（171/171 逐字核对一致，异常 0）；盘点于检出 \`ddefc45fbc\`（alpha.2）。
- 原先只有 2 篇**手抄**逐字件（\`web-styling.md\`、\`AGENTS.md\`）。**已用原 document_id 原地覆盖成字节级**
  ⇒ 库里不会再留"手抄版"和"字节版"两份同文。手抄错在哪（长度本身就是证据）：
  \`AGENTS.md\` 手抄 10,828 / 磁盘 10,761（多 67 字符）；\`web-styling.md\` 手抄 4,778 / 磁盘 5,088（**少 310 字符**）。
- ⚠ **仍未入的语料**：\`.agents/notes/\` 决策记录（2056 篇 / 约 14.3 MB）、\`docs/**/*.zh.md\` 中文译本（约 158 篇）。
  本条下文凡引用 \`.agents/notes/\` 的结论，来源仍是分片提炼，**不是**库里的原文条目。
- ⚠ 原文是**活文档**：升级 DSH 后要重跑入库脚本（源文件变了哈希自然不同 ⇒ 会被重新灌）。
- **权威仍是磁盘**（\`D:\\AI\\DSH\\deepseek-harness\\docs\\…\`）；库里的好处是**能被检索到**，不是取代磁盘。

---

`

const footer = `

---

## 附、对**本条自身**的更正（2026-09-19 复核后加，避免旧结论继续被召回）

本条写于 alpha.1（167 篇 \`docs/\`）时期，以下几处**已不成立**，以本节为准：

| 本条里的旧说法 | 现状 |
|---|---|
| 「来源：…的 **167 篇** \`docs/\`」 | **171 篇**（alpha.2 新增 4 篇：\`subsystems/boot.md\`、\`subsystems/deliverables.md\`、\`subsystems/office-to-pdf.md\`、\`persistence-changes/2026-09-14-workspace-changes-event.md\`） |
| §2.5「**布局仅内存**（刷新即折叠，:141）」 | **作废**。新权威 \`.agents/notes/implemented/architecture/2026-09-14-sidebar-layout-provider-recovery.md\`：侧栏按 **Session** 持久化"经校验的布局快照 + identity 计数器"，**先恢复布局与 tab 身份再渲染 body**；provider 自己负责恢复内容；**瞬态导航参数与资源内容不进快照**；"布局永不进入会话日志"仍成立 |
| §七「分片 D/F/G/H **尚未回流**」 | **已回流**：8 份分片全部在库里（\`dsh-a-ui\`…\`dsh-h-12\`） |
| §2.4/§2.5 由分片 A 转述的槽位/priority 细节 | 未变（alpha.2 复核过：\`sidebar.right.pane.tab\`、\`guide.entry\`、\`extension\` band、\`data-plugin-css\` 仍在） |
| （本条未涉及，但同期被推翻、别再从别处召回）「外置插件**必须**声明 peerDependencies」 | **作废**：alpha.2 有意移除该套校验（"External plugins use normal Node package resolution…"），**不补就是对的** |
| （同上）「改插件**必须重启** DSH 宿主」 | **作废**：插件改动**是热重载的**（\`@deepseek-ai/dsh-client-hmr\` 自 alpha.1 起装配；alpha.2 加 SSE + 逐插件 \`entry.refresh()\`）；只有 bootstrap / 静态装配库 / shell 需要重建页面 |

§2.2（0.5px 中性边框、只用 \`--dsw-alias-*\` token）与 §2.3（文案必须走 locale）这两条**仍然有效**
—— 我们在这两处**仍然不合规**（\`ksGuideStyles.ts\` 用了 1px；文案硬编码中文），门禁扫不到仓外，别因为"没报错"就当合规。
`

const after = header + before + footer

const post = await fetch(`${API}/v1/default/banks/${encodeURIComponent(BANK)}/memories`, {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify({
    async: true,
    items: [{
      content: after,
      context: `DSH 官方文档导航件（更新：加原文层说明与本条更正），${new Date().toLocaleString('sv-SE')}`,
      document_id: ID,
      tags: ['source:upload', 'harness:dsh', 'dsh-official-docs'],
      strategy: 'document',
      observation_scopes: 'shared',
    }],
  }),
})
if (!post.ok) {
  console.error(`❌ 写入失败 ${post.status} ${await post.text()}`)
  process.exit(1)
}
const { operation_id: op } = await post.json()
console.log(`已提交（op=${op}），等待抽取…`)

// 等终态
const TERMINAL = new Set(['completed', 'failed', 'cancelled', 'error'])
for (let i = 0; i < 120; i++) {
  await new Promise((r) => setTimeout(r, 5000))
  const r = await (await fetch(`${API}/v1/default/banks/${encodeURIComponent(BANK)}/operations/${encodeURIComponent(op)}`)).json()
  const st = String(r.status ?? '').toLowerCase()
  if (TERMINAL.has(st)) {
    console.log(`op 终态：${st}${r.error_message ? ` — ${r.error_message}` : ''}`)
    if (st !== 'completed') process.exit(1)
    break
  }
}

// 复核：① 长度 = 新文长度；② **旧正文仍是逐字子串**
const back = await (await fetch(url)).json()
const written = back.original_text
const lenOk = written.length === after.length
const keepOk = written.includes(before)
console.log(`复核：长度一致=${lenOk}（${written.length} vs ${after.length}）　旧正文逐字仍在=${keepOk}`)
console.log(`旧正文 sha256=${beforeHash.slice(0, 16)}（写前；它必须仍是新正文的子串）`)
if (!lenOk || !keepOk) {
  console.error('❌ 复核未过 —— 说明写回时被改写/截断，需要人工查。')
  process.exit(1)
}
console.log('✅ 更新完成：旧导航正文字节保持，新节已加。')
