# 门禁自身的回归测试（PSSA-guard）
#
# 为什么要有这个（独立复核 verify-freeze-pssa-guard 建议②）：
# pssa-guard.ps1 是一条**判据**——而"判据自己零测试"正是它治的那种病。
# 棘轮看不见"断言被换成恒真"，所以这里给三条**行为锁**：
#   T1 原样件 ⇒ exit 0 且输出含 PSSA 版本号（证非空闸门：真加载了、真扫了）
#   T2 注入未用变量 ⇒ exit 1 且输出含**文件名+行号**（证真能定位、不是泛泛报错）
#   T3 注入语法错误 ⇒ exit ≠ 0（作那条 fail-open 假绿的**回归锁**——复核抓到的就是它）
#
# 跑法：pwsh -NoProfile -File scripts/pssa-guard-selftest.ps1
# 边界：只在本机 var/tmp 造变异副本，**绝不改主仓任何被跟踪文件**；跑完自动清理。

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$guard = Join-Path $repo 'scripts\pssa-guard.ps1'
$work = Join-Path $repo 'var\tmp\pssa-guard-selftest'
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Join-Path $work 'scripts') | Out-Null
Copy-Item $guard (Join-Path $work 'scripts\pssa-guard.ps1') -Force

function Invoke-Guard([string]$dir) {
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = 'pwsh'
  $psi.Arguments = "-NoProfile -File `"$dir\scripts\pssa-guard.ps1`""
  $psi.RedirectStandardOutput = $true; $psi.UseShellExecute = $false
  $p = [System.Diagnostics.Process]::Start($psi)
  $out = $p.StandardOutput.ReadToEnd(); $p.WaitForExit()
  [pscustomobject]@{ Code = $p.ExitCode; Out = $out }
}

$pass = 0; $fail = 0
function Assert([string]$name, [bool]$ok, [string]$detail) {
  if ($ok) { $script:pass++; Write-Host "  [PASS] $name" -ForegroundColor Green }
  else { $script:fail++; Write-Host "  [FAIL] $name  —— $detail" -ForegroundColor Red }
}

# ── T1：原样件（目录里**只有 guard 自己**，无探针）⇒ 0 且输出含版本号（证非空闸门）──
# ⚠ 设计坑（我第一版踩了）：若此处已放了含未用变量的探针，"原样件"就不原样、必然 exit 1。
#   所以 T1 必须在**放探针之前**跑；探针从 T2 才开始加。
Write-Host 'T1 原样件 ⇒ exit 0 + 输出含 PSSA 版本号' -ForegroundColor Cyan
$r1 = Invoke-Guard $work
Assert 'T1 exit==0' ($r1.Code -eq 0) "实际 exit=$($r1.Code)"
Assert 'T1 输出含版本号(证非空闸门)' ($r1.Out -match 'PSScriptAnalyzer' -or $r1.Out -match 'PSSA-guard: 1\.') $r1.Out
Assert 'T1 输出含"扫了 N 个脚本"' ($r1.Out -match '扫了 \d+ 个脚本') $r1.Out

# ── 现在才放探针 ──
# 造一个只含「未用变量」的小脚本
$probe = @'
$neverRead = 1
Write-Host "hello"
'@
Set-Content -Path (Join-Path $work 'scripts\probe-unused.ps1') -Value $probe -Encoding UTF8

# ── T2：注入未用变量 ⇒ 1 且含文件名+行号（证真能定位）──
Write-Host 'T2 未用变量 ⇒ exit 1 + 含 probe-unused.ps1 与行号' -ForegroundColor Cyan
$r2 = Invoke-Guard $work
Assert 'T2 exit==1' ($r2.Code -eq 1) "实际 exit=$($r2.Code)"
Assert 'T2 定位到文件名' ($r2.Out -match 'probe-unused\.ps1') $r2.Out
Assert 'T2 含行号 :1' ($r2.Out -match 'probe-unused\.ps1:1\b') $r2.Out
Remove-Item (Join-Path $work 'scripts\probe-unused.ps1') -Force

# ── T3：注入语法错误 ⇒ exit≠0（回归锁：复核抓到的 fail-open）──
Write-Host 'T3 语法错误 ⇒ exit≠0（作 fail-open 假绿的回归锁）' -ForegroundColor Cyan
$broken = Join-Path $work 'scripts\probe-broken.ps1'
Set-Content -Path $broken -Value 'function X { if ($true) { ' -Encoding UTF8
$r3 = Invoke-Guard $work
Assert 'T3 exit≠0（不得静默吞 ParseError）' ($r3.Code -ne 0) "实际 exit=$($r3.Code)"
Assert 'T3 输出说"未能分析"' ($r3.Out -match '未能分析') $r3.Out
Remove-Item $broken -Force

# ── 清理 ──
Remove-Item $work -Recurse -Force

Write-Host ''
Write-Host "PSSA-guard-selftest: $pass passed, $fail failed"
if ($fail -gt 0) { exit 1 } else { exit 0 }
