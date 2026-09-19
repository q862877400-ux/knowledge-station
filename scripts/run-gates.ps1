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
#      ⚠ 2026-09-19 起**锁也盖住冒烟自己**（`plugin/scripts/smoke-all.mjs` 取同一个锁文件）：
#      那次假红的真正来源是**复核子代理绕过本脚本直接跑冒烟**，而当时锁拦不住它。
#      ⇒ 只盖住"推荐的那条路"等于没盖住。
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
#: 锁的**最长合理寿命**：门禁（全量）实测 ~7 分钟；超过这个时长还"活着"的锁按陈旧处理
#: （防的是 pid 被复用 / 长命进程恰好占了这个号 ⇒ 之后所有门禁被永久堵死，只能手删锁文件）。
#: 复核（2026-09-19）把"无时效校验"列为缺陷；这里给一个保守上限并**打印为什么清掉**。
$lockMaxAgeHours = 6
if (Test-Path $lockPath) {
  $prev = (Get-Content $lockPath -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json -ErrorAction SilentlyContinue)
  $alive = $false
  if ($prev -and $prev.pid) {
    $alive = $null -ne (Get-Process -Id $prev.pid -ErrorAction SilentlyContinue)
  }
  $tooOld = $false
  if ($prev -and $prev.startedAt) {
    try {
      $tooOld = ((Get-Date) - [datetime]::Parse($prev.startedAt)).TotalHours -gt $lockMaxAgeHours
    } catch { $tooOld = $false }
  }
  if ($alive -and $tooOld) {
    Write-Host ("（清掉一把**过期**的锁：pid=$($prev.pid) 仍活着，但起于 $($prev.startedAt)，" +
      "超过 $lockMaxAgeHours 小时 ⇒ 按陈旧处理；若确有门禁在跑，这行就是误判，请复核）") -ForegroundColor DarkGray
    $alive = $false
  }
  if ($alive) {
    Write-Host "⛔ 已经有一个门禁在跑（pid=$($prev.pid)，起于 $($prev.startedAt)）。" -ForegroundColor Red
    Write-Host "   并发跑门禁会制造**假红**（见 AGENTS.md 的门禁一节）⇒ 这次**不跑**，退出码 3。" -ForegroundColor Red
    Write-Host "   确认它其实已经死了：Remove-Item `$env:TEMP\ks-gates.lock" -ForegroundColor DarkGray
    exit 3
  }
  Write-Host "（清掉一个失效的锁：pid=$($prev.pid) 已不在）" -ForegroundColor DarkGray
  Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
}
# ⚠ 锁文件**必须无 BOM**：PS 5.1 的 `Set-Content -Encoding utf8` 会写 BOM，而 node 侧
#   （`gate-lock.mjs`）用 `JSON.parse` 读它 ⇒ 遇 BOM **抛错** ⇒ 它以为"没有锁"直接放行。
#   复核（2026-09-19）实测过这条：用 `powershell.exe` 跑本脚本时冒烟侧看不到锁。
#   两边都加固：这里写无 BOM，node 侧读时也剥 BOM。
$lockToken = [guid]::NewGuid().ToString('n')
$lockJson = @{ pid = $PID; startedAt = (Get-Date).ToString('s')
               mode = $(if ($Full) { 'full' } else { 'quick' }); token = $lockToken } | ConvertTo-Json -Compress
[System.IO.File]::WriteAllText($lockPath, $lockJson, (New-Object System.Text.UTF8Encoding($false)))
# ⚠ **再入凭据 = 锁文件里的 token**（不是"环境变量说有就有"）：子步骤（`npm run smoke` →
#   `scripts/smoke-all.mjs`）也会去取**同一个**锁，它是我们拉起来的 ⇒ 必须告诉它"别取"。
#   复核（2026-09-19）指出无条件信任 `KS_GATES_LOCK_HELD=1` 等于锁形同虚设；
#   我第一版改"校验 pid 是不是祖先"，**当场把真·再入也锁死了**（进程树是
#   `pwsh → npm.cmd → node`，`process.ppid` 只给一级，走到祖父就断）⇒ 改成一次性 token。
$prevLockHeld = $env:KS_GATES_LOCK_HELD
$prevLockToken = $env:KS_GATES_LOCK_TOKEN
$env:KS_GATES_LOCK_HELD = '1'
$env:KS_GATES_LOCK_TOKEN = $lockToken
# ⚠ **官方入口自己给冒烟隔离数据目录**（复核 2026-09-19 的建议②）：`KS_DATA_DIR` 决定
#   `ks-ingest.json`/`ks-inspection.json`/`ks-chatmode.json` 落哪。老树里的冒烟可能**还没有**
#   各自的隔离（实测：复核在 35f024a 树上跑门禁，把一条假任务写进了**真实** %APPDATA%，
#   真产品下次启动会去接管它）⇒ 在这里设一次，比"写进复核约定"可靠得多。
$prevDataDir = $env:KS_DATA_DIR
$env:KS_DATA_DIR = Join-Path ([System.IO.Path]::GetTempPath()) ("ks-gates-data-" + $PID)

$steps = @()
function Add-Step([string]$name, [string]$exe, [string[]]$argv, [string]$workdir) {
  $script:steps += [pscustomobject]@{ name = $name; exe = $exe; argv = $argv; workdir = $workdir; ok = $false; note = '' }
}

$py = Join-Path $repo '.venv\Scripts\python.exe'
$plugin = Join-Path $repo 'plugin'

# ── 自检开关（**只在验证"失败路径"本身时用**）：把门禁换成一个必定失败的假步骤，
#    用来确认"失败行 + 完整日志路径"真的会打出来。默认关。
if ($env:KS_GATES_SELFTEST -eq '1') {
  # 用真解释器而不是 `cmd /c "… ; exit 7"`：cmd 不认 `;` 作分隔符，
  # 第一版自检因此"通过"了（自检工具自己不可信，等于没自检）。
  Add-Step 'selftest（必失败）' $py @('-c', "print('FAIL  selftest-assertion'); import sys; sys.exit(7)") $repo
} elseif ($env:KS_GATES_SELFTEST -eq '2') {
  # 假绿自检（复核 2026-09-19 抓到的那条）：命令**不存在**时必须判失败并照常打汇总，
  # 而不是"弹出 try、静默退出 0"。提取树里没有 `.venv` 时踩的就是这条路。
  Add-Step 'selftest（命令不存在）' 'ks-no-such-command-xyz' @('--nope') $repo
} else {
# 快档：按"最快能发现破坏"的顺序（tsc → mypy → 命令契约 → 全链 smoke）
Add-Step 'tsc（客户端类型）'      'npx' @('tsc', '--noEmit', '-p', 'plugin/client') $repo
Add-Step 'mypy（引擎类型）'        $py  @('-m', 'mypy') $repo
Add-Step 'verify:commands'        'npm' @('run', 'verify:commands') $plugin
Add-Step 'smoke（全链）'           'npm' @('run', 'smoke') $plugin
if ($Full) {
  Add-Step 'pytest（引擎用例）'     $py  @('-m', 'pytest', '-q', '-rs') $repo
  Add-Step '引擎门禁（uvicorn）'     $py  @('scripts/verify-engine-uvicorn.py') $repo
}
}

$results = @()
$pytestPassed = $null
$pytestSkipped = $null
$hardError = $null

try {
  foreach ($s in $steps) {
    Write-Host ""
    Write-Host ("── {0} ─────────────────────────────────" -f $s.name) -ForegroundColor Cyan
    # ⛔ **"命令不存在"必须判失败，不能变成绿**（2026-09-19 复核抓到的假绿）：
    #   原来直接 `& $s.exe @(…)`；命令不存在时它是**非终止错误**，不会写入 `$LASTEXITCODE`
    #   ⇒ `$code` 拿到的是**上一步残留的退出码**（常常是 0）⇒ 这一步被判"通过"。
    #   受害面恰好是最要紧的地方：**提取树里没有 `.venv`**（复核与冻结验证都在那里跑），
    #   `mypy` 那步的 `python.exe` 找不到 ⇒ 门禁恒绿。
    #   ⇒ 三步一起：① `Get-Command` 预检；② 每次调用前把 `$LASTEXITCODE` 显式清空；
    #     ③ 调用后仍为 `$null` ⇒ 判失败（"没跑"≠"通过"）。
    $code = $null
    $out = @()
    $exePath = $null
    $skipReasonsOfStep = @()
    try { $exePath = (Get-Command $s.exe -ErrorAction Stop).Source } catch { $exePath = $null }
    if (-not $exePath) {
      $out = @("⛔ 找不到命令 '$($s.exe)' ⇒ 这一步**根本没跑**（判失败，不是跳过）",
               "   检查 PATH / venv 是否存在（提取树里通常没有 .venv）")
      $code = 127
    } else {
      Push-Location $s.workdir
      try {
        $global:LASTEXITCODE = $null
        $out = & $exePath @($s.argv) 2>&1
        $code = $LASTEXITCODE
      } finally { Pop-Location }
      if ($null -eq $code) { $code = 126 }   # 没设退出码 ⇒ 也判失败
    }
    $text = ($out | Out-String)

    # 让输出仍然可见（但只留尾部，避免刷屏）
    $tail = ($out | Select-Object -Last 6)
    $tail | ForEach-Object { Write-Host ("   " + $_) }

    # ⛔ **失败时必须给出可诊断的证据**（2026-09-19 补）：
    #   全量跑里 `smoke-chatmode` 红过一次 172/173，而当时只留了尾部 6 行 ⇒ **哪条断言红的
    #   就此丢失**，只能靠单独重跑猜。假红的根因分析恰恰需要那条断言的原文。
    #   ⇒ 失败步骤：① 把 FAIL/error 行**当场**打出来（不必再翻日志）；② 完整输出落一个文件并报路径。
    if ($code -ne 0) {
      $failLines = @($out | Where-Object { $_ -match '^\s*(FAIL|FAILED|ERROR)\b' } | Select-Object -First 12)
      if ($failLines.Count -gt 0) {
        Write-Host "   ── 失败行 ──" -ForegroundColor Red
        $failLines | ForEach-Object { Write-Host ("   " + $_) -ForegroundColor Red }
      }
      $logDir = Join-Path ([System.IO.Path]::GetTempPath()) 'ks-gates-logs'
      New-Item -ItemType Directory -Force -Path $logDir | Out-Null
      $logPath = Join-Path $logDir ("{0}-{1}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss'),
        ($s.name -replace '[^\w\-]', '_'))
      $text | Set-Content -Path $logPath -Encoding utf8
      Write-Host ("   ⛔ 该步完整输出：{0}" -f $logPath) -ForegroundColor Red
    }

    # pytest 的"只涨不跌"要读数字；`-rs` 是为了拿到 **skip 理由**（棘轮要按"账要平 + 理由集"
    # 判，见下面那段；没有理由集就只能比 passed，而 passed 是**环境相关**的）。
    if ($s.name -like 'pytest*') {
      $m = [regex]::Match($text, '(\d+) passed')
      if ($m.Success) { $pytestPassed = [int]$m.Groups[1].Value }
      $m2 = [regex]::Match($text, '(\d+) skipped')
      if ($m2.Success) { $pytestSkipped = [int]$m2.Groups[1].Value }
      $reasons = @($out | Where-Object { "$_" -match '^SKIPPED\s' } |
        ForEach-Object { ("$_" -replace '^\s*SKIPPED\s+\[\d+\]\s+', '') -replace '^[^:]*:\d+:\s*', '' })
      $skipReasonsOfStep = @($reasons | Where-Object { $_ } | Sort-Object -Unique)
    }
    $ok = ($code -eq 0)
    $results += [pscustomobject]@{ name = $s.name; ok = $ok; code = $code
      skipReasons = $(if ($s.name -like 'pytest*') { $skipReasonsOfStep } else { @() })
      note = $(if ($s.name -like 'pytest*' -and $null -ne $pytestPassed) { "passed=$pytestPassed skipped=$pytestSkipped" } else { "exit=$code" }) }
    Write-Host ("   ⇒ {0}" -f $(if ($ok) { '✅ 通过' } else { "⛔ 失败（exit=$code）" })) -ForegroundColor $(if ($ok) { 'Green' } else { 'Red' })
  }
} catch {
  # 兜底：任何**逃出**上面循环的终止错误（例如某个步骤把控制流弹出去）都必须留痕，
  # 否则汇总段根本不执行、脚本以 0 退出 —— 那就是"门禁假绿"的另一种形态。
  $hardError = $_
  Write-Host ("⛔ 门禁执行中断：{0}" -f $hardError.Exception.Message) -ForegroundColor Red
}

try {
  # ── 只涨不跌（读基线比对） ────────────────────────────────────────────────
  # ⚠ 棘轮曾经**与环境耦合**（复核 2026-09-19 实测：同一提交在两个环境里 2143/3 与 2142/4，
  #   基线记的是前者 ⇒ 后者的 `-Full` 红在 6/6 全绿之下，成了假绿/假红的混合体）。
  #   现在按**"账要平"**判，不再只看 passed：
  #     ① `passed + skipped ≥ 基线总账`（删掉用例 ⇒ 红；新增用例 ⇒ 绿并提示更新基线）；
  #     ② **不许出现基线里没有的 skip 理由**（环境性 skip 如 RUN_LIVE 已记在基线里，
  #        于是"换环境少跑一条"不再假红；而"某个依赖坏了导致新出现一批 skip"照样红）。
  $baselineDrop = $false
  $skipReasons = @($results | Where-Object { $_.name -like 'pytest*' } | ForEach-Object { $_.skipReasons } |
    Where-Object { $_ } | Sort-Object -Unique)
  $totalRan = $null
  if ($null -ne $pytestPassed) { $totalRan = $pytestPassed + ([int]$pytestSkipped) }
  if ($null -ne $pytestPassed) {
    if (Test-Path $baselinePath) {
      $base = Get-Content $baselinePath -Raw | ConvertFrom-Json
      $baseTotal = [int]$base.pytest_total
      if ($baseTotal -le 0) { $baseTotal = [int]$base.pytest_passed + [int]$base.pytest_skipped }
      $why = @()
      if ($totalRan -lt $baseTotal) {
        $why += ("总账 {0} < 基线 {1}（passed {2} + skipped {3}）" -f $totalRan, $baseTotal,
          $pytestPassed, $pytestSkipped)
      }
      $knownReasons = @($base.skip_reasons)
      $newReasons = @($skipReasons | Where-Object { $knownReasons -notcontains $_ })
      if ($newReasons.Count -gt 0) {
        $why += ("出现基线里没有的 skip 理由：{0}" -f ($newReasons -join ' / '))
      }
      if ($why.Count -gt 0) {
        Write-Host ""
        Write-Host ("⛔ **只涨不跌被破**：" + ($why -join '；')) -ForegroundColor Red
        $baselineDrop = $true
      } else {
        $msg = "   pytest 总账 $totalRan ≥ 基线 $baseTotal（passed $pytestPassed / skipped $pytestSkipped），skip 理由全在基线里"
        Write-Host $msg -ForegroundColor Green
      }
    } else {
      Write-Host "   （还没有基线文件：用 -UpdateBaseline 记一次）" -ForegroundColor DarkGray
    }
    if ($UpdateBaseline) {
      @{ pytest_passed = $pytestPassed; pytest_skipped = $pytestSkipped; pytest_total = $totalRan
         skip_reasons = $skipReasons; runLive = [bool]$env:RUN_LIVE
         updatedAt = (Get-Date).ToString('s') } | ConvertTo-Json -Depth 4 |
        Set-Content -Path $baselinePath -Encoding utf8
      Write-Host ("   基线已更新：总账=" + $totalRan + "（passed=" + $pytestPassed + " skipped=" + $pytestSkipped + "，skip 理由 " + $skipReasons.Count + " 条）") -ForegroundColor Yellow
    }
  }

  $failed = @($results | Where-Object { -not $_.ok })
  $ratchetBad = ($baselineDrop -or $null -ne $hardError)
  Write-Host ""
  Write-Host "==============================================================="
  # ⚠ 汇总行必须把**棘轮**也算进去（2026-09-19 复核抓到："6/6 步通过" 与 exit 1 同时出现，
  #   读起来是绿的）。棘轮与环境有关（`RUN_LIVE=1` 会多跑一条联网用例），所以它单独一行。
  Write-Host (" 门禁汇总（{0} 档）：{1}/{2} 步通过{3}" -f $(if ($Full) { '全量' } else { '快档' }),
    ($results.Count - $failed.Count), $results.Count,
    $(if ($ratchetBad) { ' · ⛔ 棘轮/执行未过 ⇒ **整体失败**' }
      elseif ($Full) { ' · ✅ 棘轮（只涨不跌）' }
      else { '（快档不含 pytest 棘轮，棘轮只在 -Full 判）' }))
  $results | ForEach-Object { Write-Host ("   {0} {1,-26} {2}" -f $(if ($_.ok) { '✅' } else { '⛔' }), $_.name, $_.note) }
  if ($Full) {
    Write-Host ("   {0} {1,-26} {2}" -f $(if ($ratchetBad) { '⛔' } else { '✅' }), '棘轮（pytest 只涨不跌）',
      $(if ($null -eq $pytestPassed) { 'pytest 没跑出数字' }
        elseif ($baselineDrop) { "被破：$($why -join '；')" }
        else { "passed=$pytestPassed skipped=$pytestSkipped ≥ 基线" }))
    Write-Host ("      环境：RUN_LIVE=[{0}]（=1 时多跑 1 条联网用例 ⇒ 基线按**默认环境**记）" -f $env:RUN_LIVE)
  }
  Write-Host "==============================================================="
  if ($failed.Count -gt 0 -or $ratchetBad) {
    if ($failed.Count -gt 0) { Write-Host (" 失败步骤：" + (($failed | ForEach-Object { $_.name }) -join '、')) -ForegroundColor Red }
    if ($null -ne $hardError) { Write-Host " ⛔ 执行中断（见上方日志）" -ForegroundColor Red }
    exit 1
  }
  exit 0
} finally {
  Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
  # ⚠ **恢复**而不是删除：删除会把调用方原本的值（若有）抹掉，
  #    而"再入开关"靠它 —— 见 gate-lock.mjs 里的祖先校验。
  if ($null -ne $prevLockHeld) { $env:KS_GATES_LOCK_HELD = $prevLockHeld }
  else { Remove-Item Env:\KS_GATES_LOCK_HELD -ErrorAction SilentlyContinue }
  if ($null -ne $prevLockToken) { $env:KS_GATES_LOCK_TOKEN = $prevLockToken }
  else { Remove-Item Env:\KS_GATES_LOCK_TOKEN -ErrorAction SilentlyContinue }
  if ($null -ne $prevDataDir) { $env:KS_DATA_DIR = $prevDataDir }
  else { Remove-Item Env:\KS_DATA_DIR -ErrorAction SilentlyContinue }
}
