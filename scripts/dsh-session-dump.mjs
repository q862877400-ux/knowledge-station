/**
 * dsh-session-dump.mjs — 读 DSH 会话日志（多帧 zstd 也要能全解）+ 活跃度/命令行链路判据
 *
 * 为什么需要它：
 *   1) DSH 的 session.jsonl 是**按帧追加的 zstd 多帧文件**，Node 的 `zstdDecompressSync`
 *      只解第一帧（实测 13.6MB 的文件只吐出 1 个事件）。这里按 zstd 魔数切帧逐帧解。
 *   2) 自主开发期间要判断「别的会话是否正在跑」——重启宿主会打断别人的 in-flight turn，
 *      这是不可接受的副作用，必须先有机器判据（turn/start 未闭合 = 正在跑）。
 *   3) 斜杠命令的验收判据：`command/run` + `command/done` 存在且**没有** `turn/start`。
 *
 * 用法：
 *   node scripts/dsh-session-dump.mjs <session.jsonl[.zstd]>                 # 事件类型概览
 *   node scripts/dsh-session-dump.mjs <file> --full                          # 打印事件内容（截断）
 *   node scripts/dsh-session-dump.mjs <file> --grep '正则'                    # 只打印匹配行
 *   node scripts/dsh-session-dump.mjs <file> --json                          # 机器可读摘要
 *   node scripts/dsh-session-dump.mjs --active [--minutes 10]                 # 扫描全部会话，报告"正在跑"的
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { homedir } from 'node:os'

const ZSTD_MAGIC = Buffer.from([0x28, 0xb5, 0x2f, 0xfd])

/** 按 zstd 魔数把多帧文件切成帧（帧内出现魔数的概率极低，且解压失败会被跳过）。 */
function splitFrames(buf) {
  const starts = []
  for (let i = 0; i + 4 <= buf.length; i++) {
    if (buf[i] === 0x28 && buf[i + 1] === 0xb5 && buf[i + 2] === 0x2f && buf[i + 3] === 0xfd) starts.push(i)
  }
  if (starts.length === 0) return [{ data: buf, framed: false }]
  const frames = []
  for (const [i, s] of starts.entries()) {
    const end = i + 1 < starts.length ? starts[i + 1] : buf.length
    frames.push({ data: buf.subarray(s, end), framed: true })
  }
  return frames
}

async function decompressAll(file) {
  const { zstdDecompressSync } = await import('node:zlib')
  const buf = readFileSync(file)
  const isZstd = buf[0] === 0x28 && buf[1] === 0xb5 && buf[2] === 0x2f && buf[3] === 0xfd
  if (!isZstd) return buf.toString('utf8')
  const frames = splitFrames(buf)
  const parts = []
  let failed = 0
  for (const f of frames) {
    try { parts.push(zstdDecompressSync(f.data).toString('utf8')) } catch { failed++ }
  }
  if (parts.length === 0) throw new Error(`无法解压任何帧（共 ${frames.length} 帧）`)
  return { text: parts.join(''), frames: frames.length, failed }
}

function parseEvents(text) {
  const events = []
  for (const line of text.split('\n')) {
    const s = line.trim()
    if (s.length === 0) continue
    try { events.push(JSON.parse(s)) } catch { /* 帧边界的半行忽略 */ }
  }
  return events
}

/** turn/start 减去 turn/end 得到未闭合回合数；>0 表示该会话正在跑。 */
function summarize(events) {
  const types = events.map(e => String(e.type ?? '?'))
  const count = t => types.filter(x => x === t).length
  return {
    events: events.length,
    turnStart: count('turn/start'),
    turnEnd: count('turn/end'),
    openTurns: count('turn/start') - count('turn/end'),
    commandRun: count('command/run'),
    commandDone: count('command/done'),
    toolCalls: count('tool/call'),
    types: [...new Set(types)].sort().map(t => `${t}×${count(t)}`),
  }
}

const argv = process.argv.slice(2)
const arg = (name, dflt) => {
  const i = argv.indexOf(name)
  return i >= 0 ? argv[i + 1] : dflt
}

if (argv.includes('--active')) {
  const minutes = Number(arg('--minutes', '15'))
  const root = join(homedir(), '.dsh', 'sessions')
  const rows = []
  for (const ws of readdirSync(root, { withFileTypes: true })) {
    if (!ws.isDirectory()) continue
    for (const s of readdirSync(join(root, ws.name), { withFileTypes: true })) {
      if (!s.isDirectory()) continue
      const file = join(root, ws.name, s.name, 'session.jsonl.zstd')
      try {
        const st = statSync(file)
        if ((Date.now() - st.mtimeMs) / 60000 > minutes) continue
        const out = await decompressAll(file)
        const text = typeof out === 'string' ? out : out.text
        const sum = summarize(parseEvents(text))
        rows.push({ session: s.name, workspace: ws.name, mtime: st.mtime.toISOString(), ...sum })
      } catch (e) { rows.push({ session: s.name, error: String(e.message ?? e) }) }
    }
  }
  rows.sort((a, b) => (b.openTurns ?? 0) - (a.openTurns ?? 0))
  const running = rows.filter(r => (r.openTurns ?? 0) > 0)
  console.log(JSON.stringify({ scanned: rows.length, running: running.length, rows }, null, 2))
  process.exit(0)
}

const file = argv.find(a => !a.startsWith('--') && !argv[argv.indexOf(a) - 1]?.startsWith('--'))
if (!file) {
  console.error('用法见文件头注释')
  process.exit(2)
}
const out = await decompressAll(file)
const text = typeof out === 'string' ? out : out.text
const events = parseEvents(text)
const sum = summarize(events)

if (argv.includes('--json')) {
  console.log(JSON.stringify(sum, null, 2))
  process.exit(0)
}

const full = argv.includes('--full')
const grep = arg('--grep', null)
if (out.framed) console.log(`# 多帧 zstd：${out.frames} 帧（解压失败 ${out.failed}）`)
console.log(`# ${file.split(/[\\/]/).slice(-2).join('/')} — ${sum.events} events`)
for (const [i, ev] of events.entries()) {
  const line = `${String(i).padStart(4)} ${String(ev.type)} ${JSON.stringify(ev.data ?? null)}`
  if (grep && !new RegExp(grep, 'u').test(line)) continue
  console.log(full || grep ? line.slice(0, 2000) : `${String(i).padStart(4)} ${ev.type}`)
}
console.log('\n# 统计: ' + sum.types.join('  '))
console.log(`# 未闭合回合=${sum.openTurns}（>0 = 正在跑）· 命令 run=${sum.commandRun}/done=${sum.commandDone}`
  + (sum.commandRun > 0 && sum.turnStart === 0 ? '  ✓ 命令未进入模型' : ''))
