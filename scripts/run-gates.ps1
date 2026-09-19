# run-gates.ps1 — 本仓库**唯一**的门禁入口（AGENTS.md 的"门禁"一节指向这里）
#
# 为什么要有这个脚本（官方 `docs/development.md:131` 的口径是"门禁即代码"）：
#   在此之前，"门禁只涨不跌"是**散文**——每轮靠人记得手敲 5–6 条命令、手抄数字
#   （`docs/DEVELOPMENT-HISTORY.md` 里那几处"五件套/六件套"就是活证据）。
#   人记得 ⇒ 早晚会漏。这个脚本把它变成**一条命令 + 退出码**。
#
# 用法：
#   pwsh -File scripts/run-gates.ps1 -Quick      # 改动面：tsc / mypy / verify:commands / smoke
#   pwsh -File scripts/run-gates.ps1 -Full       # 全量：再加 pytest / 引擎门禁
#   pwsh -File scripts/run-gates.ps1 -Quick -UpdateBaseline   # 绿了之后把新基线写回
#
# 三条纪律（都在 AGENTS.md 里，这里实现它们）：
#   1. **一次只跑一个**：并发跑会制造假红（`smoke-chatmode` 实测两次 172/173 都发生在与全量
#      pytest 并发时）。这里用锁文件把它变成**当场报错**，而不是靠人记得。
#   2. **只涨不跌**：pytest 的 passed 数只许涨；掉了就红（基线在 `scripts/gates-baseline.json`）。
#   3. **退出码为准**：任何一步失败即非零退出，且失败步骤逐条列出。
[CmdletBinding()]
param(
  [switch]$Quick,
  [switch]$Full,
  [switch]$UpdateBaseline
)

$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $PSScriptRoot
$baselinePath = Join-Path $PSScriptRoot 'gates-baseline.json'

if (-not $Quick -and -not $Full) { $Quick = $true }   # 缺省 = 快档（避免误触全量）
if ($Quick -and $Full) { $Quick = $false }            # 同时给 ⇒ 按全量

# ── 锁：把"并发跑门禁"变成当场报错 ─────────────────────────────────────────────
$lockPath = Join-Path ([System.IO.Path]::GetTempPath()) 'ks-gates.lock'
if (Test-Path $lockPath) {
  $prev = (Get-Content $lockPath -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json -ErrorAction SilentlyContinue)
  $alive = $false
  if ($prev -and $prev.pid) {
    $alive = $null -ne (Get-Process -Id $prev.pid -ErrorAction SilentlyContinue)
  }
  if ($alive) {
    Write-Host "⛔ 已经有一个门禁在跑（pid=$($prev.pid)，起于 $($prev.startedAt)）。" -ForegroundColor Red
    Write-Host "   并发跑门禁会制造**假红**（见 AGENTS.md 的门禁一节）⇒ 这次**不跑**，退出码 3。" -ForegroundColor Red
    exit 3
  }
  Write-Host "（清掉一个失效的锁：pid=$($prev.pid) 已不在）" -ForegroundColor DarkGray
  Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
}
@{ pid = $PID; startedAt = (Get-Date).ToString('s'); mode = $(if ($Full) { 'full' } else { 'quick' }) } |
  ConvertTo-Json -Compress | Set-Content -Path $lockPath -Encoding utf8

$steps = @()
function Add-Step([string]$name, [string]$exe, [string[]]$argv, [string]$workdir) {
  $script:steps += [pscustomobject]@{ name = $name; exe = $exe; argv = $argv; workdir = $workdir; ok = $false; note = '' }
}

$py = Join-Path $repo '.venv\Scripts\python.exe'
$plugin = Join-Path $repo 'plugin'

# 快档：按"最快能发现破坏"的顺序（tsc → mypy → 命令契约 → 全链 smoke）
Add-Step 'tsc（客户端类型）'      'npx' @('tsc', '--noEmit', '-p', 'plugin/client') $repo
Add-Step 'mypy（引擎类型）'        $py  @('-m', 'mypy') $repo
Add-Step 'verify:commands'        'npm' @('run', 'verify:commands') $plugin
Add-Step 'smoke（全链）'           'npm' @('run', 'smoke') $plugin
if ($Full) {
  Add-Step 'pytest（引擎用例）'     $py  @('-m', 'pytest', '-q') $repo
  Add-Step '引擎门禁（uvicorn）'     $py  @('scripts/verify-engine-uvicorn.py') $repo
}

$results = @()
$pytestPassed = $null
$pytestSkipped = $null

try {
  foreach ($s in $steps) {
    Write-Host ""
    Write-Host ("── {0} ─────────────────────────────────" -f $s.name) -ForegroundColor Cyan
    Push-Location $s.workdir
    try {
      $out = & $s.exe @($s.argv) 2>&1
      $code = $LASTEXITCODE
    } finally { Pop-Location }
    $text = ($out | Out-String)

    # 让输出仍然可见（但只留尾部，避免刷屏）
    $tail = ($out | Select-Object -Last 6)
    $tail | ForEach-Object { Write-Host ("   " + $_) }

    # pytest 的"只涨不跌"要读数字
    if ($s.name -like 'pytest*') {
      $m = [regex]::Match($text, '(\d+) passed')
      if ($m.Success) { $pytestPassed = [int]$m.Groups[1].Value }
      $m2 = [regex]::Match($text, '(\d+) skipped')
      if ($m2.Success) { $pytestSkipped = [int]$m2.Groups[1].Value }
    }
    $ok = ($code -eq 0)
    $results += [pscustomobject]@{ name = $s.name; ok = $ok; code = $code
      note = $(if ($s.name -like 'pytest*' -and $null -ne $pytestPassed) { "passed=$pytestPassed skipped=$pytestSkipped" } else { "exit=$code" }) }
    Write-Host ("   ⇒ {0}" -f $(if ($ok) { '✅ 通过' } else { "⛔ 失败（exit=$code）" })) -ForegroundColor $(if ($ok) { 'Green' } else { 'Red' })
  }

  # ── 只涨不跌（读基线比对） ────────────────────────────────────────────────
  $baselineDrop = $false
  if ($null -ne $pytestPassed) {
    if (Test-Path $baselinePath) {
      $base = Get-Content $baselinePath -Raw | ConvertFrom-Json
      if ($base.pytest_passed -and $pytestPassed -lt [int]$base.pytest_passed) {
        Write-Host ""
        Write-Host ("⛔ **只涨不跌被破**：pytest passed {0} < 基线 {1}" -f $pytestPassed, $base.pytest_passed) -ForegroundColor Red
        $baselineDrop = $true
      } elseif ($base.pytest_passed) {
        Write-Host ("   pytest passed {0} ≥ 基线 {1} ✅" -f $pytestPassed, $base.pytest_passed) -ForegroundColor Green
      }
    } else {
      Write-Host "   （还没有基线文件：用 -UpdateBaseline 记一次）" -ForegroundColor DarkGray
    }
    if ($UpdateBaseline) {
      @{ pytest_passed = $pytestPassed; pytest_skipped = $pytestSkipped
         updatedAt = (Get-Date).ToString('s') } | ConvertTo-Json | Set-Content -Path $baselinePath -Encoding utf8
      Write-Host ("   基线已更新：passed={0} skipped={1}" -f $pytestPassed, $pytestSkipped) -ForegroundColor Yellow
    }
  }

  $failed = @($results | Where-Object { -not $_.ok })
  Write-Host ""
  Write-Host "==============================================================="
  Write-Host (" 门禁汇总（{0} 档）：{1}/{2} 步通过" -f $(if ($Full) { '全量' } else { '快档' }), ($results.Count - $failed.Count), $results.Count)
  $results | ForEach-Object { Write-Host ("   {0} {1,-26} {2}" -f $(if ($_.ok) { '✅' } else { '⛔' }), $_.name, $_.note) }
  Write-Host "==============================================================="
  if ($failed.Count -gt 0 -or $baselineDrop) {
    if ($failed.Count -gt 0) { Write-Host (" 失败步骤：" + (($failed | ForEach-Object { $_.name }) -join '、')) -ForegroundColor Red }
    exit 1
  }
  exit 0
} finally {
  Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
}
