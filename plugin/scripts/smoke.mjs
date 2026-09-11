/**
 * ks-dsh-plugin — scripts/smoke.mjs
 *
 * Standalone host-side smoke (does NOT depend on cordis). It mirrors the
 * plugin's single-instance rules exactly:
 *   1. read engine.session.json + probe GET /api/v1/health
 *   2. healthy instance  -> REUSE (never kill it)
 *   3. no healthy instance -> SPAWN `python -m src.core.main`, poll until health
 *   4. fetch /api/v1/health (no token) and GET /api/v1/documents (Bearer)
 *   5. print both result summaries (HTTP status + data field shape)
 *   6. clean up: only an engine WE spawned is stopped (Stop-Process -Id)
 *   7. exit 0 on success (health 200 AND documents HTTP 200 with JSON body),
 *      exit 1 otherwise.
 *
 * Run:  node scripts/smoke.mjs
 */

import { existsSync } from 'node:fs'
import {
  EngineManager,
  apiGet,
  originUrl,
  readSessionFile,
  sessionFilePath,
  HEALTH_PATH,
  isProcessAlive,
} from '../src/engine.js'

const DOCUMENTS_PATH = '/api/v1/documents'

function summary(prefix, probe) {
  let dataShape = 'none'
  let dataJson = null
  if (probe.body && typeof probe.body === 'object') {
    if (probe.body.data !== undefined) {
      const d = probe.body.data
      if (Array.isArray(d)) dataShape = `array(${d.length})`
      else if (d && typeof d === 'object') dataShape = `object{keys:[${Object.keys(d).join(',')}]}`
      else dataShape = `${typeof d}(${String(d)})`
      dataJson = d
    } else {
      dataShape = `object{keys:[${Object.keys(probe.body).join(',')}]}`
      dataJson = probe.body
    }
  }
  console.log(`[${prefix}] HTTP ${probe.status}${probe.error ? ` error=${probe.error}` : ''}`)
  console.log(`[${prefix}] data shape: ${dataShape}`)
  console.log(`[${prefix}] data: ${JSON.stringify(dataJson)}`)
  return { status: probe.status, ok: probe.status === 200, dataShape }
}

async function main() {
  console.log('=== ks-dsh-plugin smoke ===')
  console.log(`session file: ${sessionFilePath()}`)
  const pre = await readSessionFile()
  const preAlive = pre && isProcessAlive(pre.pid)
  console.log(`pre-existing session: ${pre ? `port=${pre.port} pid=${pre.pid}` : 'none'}${preAlive ? ' (alive)' : ''}`)

  const manager = new EngineManager({ startupTimeoutMs: 90_000, startupProbeTimeoutMs: 25_000 })

  let session
  try {
    session = await manager.ensureLive()
  } catch (err) {
    console.error(`[fail] engine ensure failed: ${err.message}`)
    await manager.dispose()
    process.exit(1)
  }
  const reused = !session.spawnedByUs
  console.log(
    `[engine] connected via session.json: port=${session.port} pid=${session.pid} ` +
      `reused=${reused}${reused ? ' (pre-existing healthy instance — will NOT kill)' : ' (spawned by smoke)'}`,
  )

  // Evidence 1: /api/v1/health (no token).
  const health = await apiGet(originUrl(session.port), HEALTH_PATH, { timeoutMs: 12_000 })
  console.log('\n-- /api/v1/health --')
  const h = summary('health', health)

  // Evidence 2: /api/v1/documents (Bearer token).
  const docs = await apiGet(originUrl(session.port), DOCUMENTS_PATH, {
    token: session.token,
    timeoutMs: 15_000,
  })
  console.log('\n-- /api/v1/documents --')
  const d = summary('documents', docs)

  console.log('\n-- cleanup --')
  if (!reused) {
    const stopped = isProcessAlive(session.pid)
    console.log(
      `[cleanup] spawned engine pid=${session.pid}: ${stopped ? 'alive — stopping via dispose' : 'already exited'}`,
    )
  } else {
    console.log('[cleanup] engine was reused (pre-existing) — left it running (single-instance rule)')
  }
  // dispose() stops OUR engine (session pid) + the venv launcher; reused
  // (external) engines are left untouched.
  await manager.dispose()

  const pass = h.status === 200 && d.status === 200
  console.log(`\n== smoke ${pass ? 'PASS' : 'FAIL'} (health=${h.status}, documents=${d.status}) ==`)
  process.exit(pass ? 0 : 1)
}

main().catch((err) => {
  console.error(`[fatal] ${err && err.stack ? err.stack : err}`)
  process.exit(1)
})
