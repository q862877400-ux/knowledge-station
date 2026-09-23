"""B6 verify: copy ui-render-shot.mjs and add ONLY a --face switch arg (really clicks the top tabs).
The shipped --interact scenario table has NO face-switch scenario and --nav-page is never read.
Only my own copy is modified; the shipped script is untouched."""
import io, os, re

SRC = r"D:\AI\work space\zcode-verify-b6\plugin\scripts\ui-render-shot.mjs"
DST = r"D:\AI\work space\zcode-verify-b6\plugin\scripts\zz-b6-faceswitch.mjs"

src = io.open(SRC, encoding="utf-8", newline="").read()

def rep(old, new, why):
    global src
    n = src.count(old)
    assert n == 1, "ANCHOR NOT UNIQUE (%d) for %s" % (n, why)
    src = src.replace(old, new, 1)
    print("PATCH OK:", why)

# 1. new arg --face
rep(
    "const interacts = arg('interact', PAGES[page].interact.join(',')) .split(',').map((s) => s.trim()).filter(Boolean)",
    "const interacts = arg('interact', PAGES[page].interact.join(',')) .split(',').map((s) => s.trim()).filter(Boolean)\n"
    "/* B6-VERIFY: --face <capabilities|channels|manage|none> = after mount, really click the top tab to switch face */\n"
    "const b6face = arg('face', '')\n"
    "/* B6-VERIFY: --initial-face = the face the tab is OPENED on (host params.page) */\n"
    "const b6initial = arg('initial-face', 'manage')",
    "--face arg",
)

# 1b. make the opening face configurable (defaults to the shipped 'manage')
rep(
    "navigation: { address: 'ks:kb', revision: 1, params: { page: 'manage' } }",
    "navigation: { address: 'ks:kb', revision: 1, params: { page: b6initial } }",
    "--initial-face",
)

# 2. error capture (must be installed BEFORE mount)
rep(
    "const root = mount(container, PROPS[page])",
    "/* B6-VERIFY: catch the hook-count error React throws on the 2nd render */\n"
    "const b6errors = []\n"
    "const b6origErr = console.error.bind(console)\n"
    "process.on('uncaughtException', (e) => { b6errors.push('uncaughtException: ' + String((e && e.message) || e)) })\n"
    "process.on('unhandledRejection', (e) => { b6errors.push('unhandledRejection: ' + String((e && e.message) || e)) })\n"
    "console.error = (...a) => { const s = a.map((x) => String(x)).join(' '); if (/React|Minified|hook/i.test(s)) b6errors.push('console.error: ' + s); b6origErr(...a) }\n"
    "\n"
    "const root = mount(container, PROPS[page])",
    "error capture",
)

# 3. face switch block, inserted right after mount + 2 flushes (regex anchor: disk file is CRLF)
m = list(re.finditer(r"const root = mount\(container, PROPS\[page\]\)(\r?\n)await flush\(\)(\r?\n)await flush\(\)", src))
assert len(m) == 1, "MOUNT BLOCK count=%d" % len(m)
nl = m[0].group(1)
block = nl.join([
    "",
    "/* ----- B6-VERIFY: face switch = the SECOND render of the same instance ----- */",
    "if (b6face === 'none') {",
    "  b6origErr('B6-NOSWITCH initial=' + b6initial + ' nodes=' + String(container.querySelectorAll('*').length) + ' capturedErrors=' + String(b6errors.length))",
    "  b6origErr(b6errors.length === 0 ? 'B6-VERDICT GREEN-NOSWITCH: single render, no error (this proves NOTHING about #300)' : 'B6-VERDICT RED-NOSWITCH')",
    "  process.exit(b6errors.length === 0 ? 0 : 1)",
    "}",
    "if (b6face !== '') {",
    "  const labelOf = { capabilities: '\\u529e\\u4e8b\\u53f0', channels: '\\u6e20\\u9053\\u5e93', materials: '\\u5907\\u6599', manage: '\\u77e5\\u8bc6\\u5e93' }",
    "  const want = labelOf[b6face] ?? b6face",
    "  const strip = [...container.querySelectorAll('.ks-tabfolder')]",
    "  b6origErr('B6-MOUNTED initial=' + b6initial + ' face-arg=' + b6face + ' tabs=[' + strip.map((e) => e.textContent).join('|') + '] active=[' + [...container.querySelectorAll('.ks-tabfolder-on')].map((e) => e.textContent).join('|') + ']')",
    "  const btn = strip.find((el) => (el.textContent ?? '').includes(want))",
    "  if (btn === undefined) { b6origErr('B6-CANNOT-SWITCH no tab named ' + want + ' => cannot reach face ' + b6face + ' (NOT a pass)'); process.exit(3) }",
    "  btn.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }))",
    "  for (let i = 0; i < 5; i += 1) await flush()",
    "  b6origErr('B6-AFTER-SWITCH active=[' + [...container.querySelectorAll('.ks-tabfolder-on')].map((e) => e.textContent).join('|') + '] nodes=' + String(container.querySelectorAll('*').length) + ' capturedErrors=' + String(b6errors.length))",
    "  for (const e of b6errors) b6origErr('B6-ERR ' + e.split(String.fromCharCode(10))[0].slice(0, 400))",
    "  b6origErr(b6errors.length === 0 ? 'B6-VERDICT GREEN: no React hook error after face switch' : 'B6-VERDICT RED: React error after face switch')",
    "  process.exit(b6errors.length === 0 ? 0 : 1)",
    "}",
])
src = src[: m[0].end()] + block + src[m[0].end():]
print("PATCH OK: face switch block")

io.open(DST, "w", encoding="utf-8", newline="").write(src)
print("WROTE", DST, os.path.getsize(DST), "bytes")
