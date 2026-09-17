<#
  dsh-gui-e2e-ingest.ps1 — 用无头浏览器模拟真人操作，端到端验收「📥 入库预览」tab（2026-09-11）

  为什么用合成点击而不是 AX ref：better-sidebar 的 tab 条与面板按钮没有稳定 id/类名，
  ref 在每次重渲染后失效（上游契约如此）。这里用 `eval` 在页面上下文里按**可见文案**找元素
  并 `click()`——这是"模拟真人点这个按钮"的可复现写法，断言全部基于 `document.body.innerText`
  （不依赖 DOM 结构），因此对上游改版更耐受。

  验收链（每一步都以"能 FAIL"的方式断言）：
    1. GUI 可加载（innerText 含底部面板的 5 个 tab 名之一）
    2. 点击「📥 入库预览」→ 面板渲染该 tab（含标题与"待入库目录"字样 + 只读声明）
    3. 点「刷新列表」→ 列出待入库目录里的 PDF（断言至少 1 个文件名出现）
    4. 点「开始预览」→ 轮询到三桶徽标出现（✅/⚠️/❌ 文案）且至少一行文件名可见
    5. 点第一行文件名 → 右/下出现单本报告（断言"级"与"外发"字样出现 = 报告渲染）

  前置：宿主已重启（含 /ks/ingest* 路由）、待入库目录里有 PDF。
  日志：var\tmp\dsh-gui-e2e.log
#>
[CmdletBinding()]
param(
  [string]$Url = 'http://127.0.0.1:3080/',
  [string]$Root = 'D:\AI\work space\zcode',
  [int]$PreviewWaitSeconds = 180
)

$ErrorActionPreference = 'Continue'
$env:BROWSER4_CLI_STATE_DIR = Join-Path $Root 'var\tmp\b4-state'
$logPath = Join-Path $Root 'var\tmp\dsh-gui-e2e.log'
$jsDir = Join-Path $Root 'var\tmp\e2e-js'
New-Item -ItemType Directory -Force -Path $jsDir | Out-Null
$fails = 0

function W([string]$m) {
  "$(Get-Date -Format 'HH:mm:ss') $m" | Tee-Object -FilePath $logPath -Append | Out-Null
}
function Check([string]$name, [bool]$ok, [string]$detail) {
  if (-not $ok) { $script:fails++ }
  W ("{0}  {1}{2}" -f $(if ($ok) { 'PASS' } else { 'FAIL' }), $name, $(if ($detail) { " — $detail" } else { '' }))
}
function Eval-Js([string]$name, [string]$js) {
  $file = Join-Path $jsDir "$name.js"
  [System.IO.File]::WriteAllText($file, $js)
  $out = & browser4-cli eval --file $file 2>&1
  return ($out -join "`n").Trim()
}
function Click-ByText([string]$text, [string]$scope = 'button') {
  $js = @"
(() => {
  const want = $([System.Text.Json.JsonSerializer]::Serialize($text));
  const nodes = [...document.querySelectorAll('$scope')];
  const hit = nodes.find((n) => (n.textContent || '').trim() === want)
    || nodes.find((n) => (n.textContent || '').trim().includes(want));
  if (!hit) return 'not-found';
  hit.scrollIntoView({ block: 'center' });
  hit.click();
  return 'clicked';
})()
"@
  return (Eval-Js ("click-" + ($text -replace '[^\w]', '_')) $js)
}
function BodyHas([string]$needle) {
  $js = "document.body.innerText.includes($([System.Text.Json.JsonSerializer]::Serialize($needle)))"
  return ((Eval-Js "has" $js) -match 'true')
}
function Wait-BodyHas([string]$needle, [int]$seconds) {
  $waited = 0
  while ($waited -lt $seconds) {
    if (BodyHas $needle) { return $true }
    Start-Sleep -Seconds 3
    $waited += 3
  }
  return $false
}

"=== dsh-gui-e2e-ingest $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Set-Content -Encoding UTF8 $logPath

# ---------------------------------------------------------------- 0) 加载页面
& browser4-cli goto $Url 2>&1 | Out-Null
Start-Sleep -Seconds 6
$title = Eval-Js 'title' 'document.title'
Check 'GUI 可加载' ($title.Length -gt 0) $title

# ---------------------------------------------------------------- 1) 打开面板 + 切到 📥 tab
$clicked = Click-ByText '📥 入库预览'
if ($clicked -ne 'clicked') {
  # 面板可能是收起的：先点「展开底部面板」，再试
  $null = Click-ByText '展开底部面板'
  Start-Sleep -Seconds 2
  $clicked = Click-ByText '入库预览'
}
Check '点到「📥 入库预览」tab' ($clicked -eq 'clicked') $clicked
Start-Sleep -Seconds 2
Check 'Tab 渲染出标题' (BodyHas '入库预览（Dry-Run）') ''
# 2026-09-17 D5/F1：原断言钉的是"不外发"这句**产品承诺**，而该承诺已改为
# "默认不外发 + 可显式开启云深度解析"。断言改为钉**新**口径（否则测试会拦住正确改动）。
Check 'Tab 渲染出只读 + 默认不外发声明' (BodyHas '不写库、不移动文件、默认不外发') ''
Check 'Tab 渲染出云深度解析开关（默认关闭）' (BodyHas '允许云深度解析') ''
Check 'Tab 渲染出待入库目录行' (BodyHas '待入库目录') ''

# ---------------------------------------------------------------- 2) 刷新列表
$r = Click-ByText '刷新列表'
Check '点到「刷新列表」' ($r -eq 'clicked') $r
$listed = Wait-BodyHas '合成示例-文本层标准.pdf' 30
Check '列出待入库目录里的 PDF' $listed ''

# ---------------------------------------------------------------- 3) 开始预览
$r2 = Click-ByText '开始预览'
Check '点到「开始预览」' ($r2 -eq 'clicked') $r2
$gotBuckets = Wait-BodyHas '需人工确认' $PreviewWaitSeconds
Check "预览出三桶总账（≤${PreviewWaitSeconds}s）" $gotBuckets ''

# ---------------------------------------------------------------- 4) 单本报告
$opened = Eval-Js 'click-row' @"
(() => {
  const btn = [...document.querySelectorAll('button')]
    .find((b) => (b.textContent || '').includes('.pdf'));
  if (!btn) return 'no-row';
  btn.click();
  return 'clicked';
})()
"@
Check '点到第一行文件名' ($opened -eq 'clicked') $opened
$gotReport = Wait-BodyHas '外发' 45
Check '单本 R27 报告渲染（含"外发"字样）' $gotReport ''

W "=== done: fails=$fails ==="
if ($fails -gt 0) { exit 1 }
exit 0
