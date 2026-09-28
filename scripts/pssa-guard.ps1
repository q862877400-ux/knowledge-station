# 门禁：命令层空验证的机械检测（PSScriptAnalyzer）
#
# 治哪条缺陷（本仓已实测过的）：
#   把 scripts/run-gates.ps1 里 8 处 $totalForRatchet 逐字改回 $totalRan
#   ⇒ 22 条相关测试全绿、零红；全仓对该脚本的引用全是注释 ⇒ 该脚本自身没有单测。
#
# 为什么用 PSSA（本机实测 2026-09-28）：
#   原始件命中 0 条；把 7 处读取改回、只留赋值点 ⇒ 命中 1 条
#   「Line 475: The variable 'totalForRatchet' is assigned but never used.」
#   ⇒ 一次命中、原始件零误报。复现命令见 docs/research/TECH-PATH-2026-09-28.md §6。
#
# 只扫两条规则，不扫全规则集：run-gates.ps1 本身就有 64 条诊断
# （WriteHost / PositionalParams / EmptyCatch / BOM），全扫等于永久红。
# 这两条分别治「变量算了没人用」「参数声明了没人读」——正是命令层空验证的两种形态。

$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot

# PSSA 可能装在系统模块路径，也可能只在 var/tmp 下（见 TECH-PATH §1.14.1）
$pssaCandidates = @(
  (Join-Path $env:USERPROFILE 'Documents\PowerShell\Modules\PSScriptAnalyzer'),
  (Join-Path $repo 'var\tmp\study\r2-pssa\PSScriptAnalyzer')
)
$pssa = $pssaCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $pssa) {
  Write-Host 'PSSA-guard: PSScriptAnalyzer 未安装 —— **本门禁判失败（不是跳过）**' -ForegroundColor Red
  Write-Host "  装它：Install-Module PSScriptAnalyzer -Scope CurrentUser -Force" -ForegroundColor Yellow
  exit 2
}
Import-Module $pssa -Force
Write-Host "PSSA-guard: $((Get-Module PSScriptAnalyzer).Version)  ($pssa)"

# 目标两条：治「算了没人用」与「参数没人读」
$rules = @('PSUseDeclaredVarsMoreThanAssignments')
# ⚠ 实测取舍（2026-09-28，我本机跑过）：两条里**只留上面这一条**。
#   PSReviewUnusedParameter 是**误报源**：dsh-host-restart.ps1:25 与 dsh-host-watchdog.ps1:36 的
#   $Url 都被报「declared but not used」，但它们**在 PowerShell 闭包里真被用了**
#   （restart:36 `Invoke-WebRequest -Uri $Url`；watchdog:52 同）——该规则不跟踪闭包捕获。
#   ⇒ 放进门禁会造成**永久红**（正是本仓吃过多次的假红）。**故意不启用，留档。**

# 扫本仓的 PowerShell 脚本目录
$targets = Get-ChildItem -Path (Join-Path $repo 'scripts') -Filter '*.ps1' -Recurse -File
if (-not $targets) {
  Write-Host 'PSSA-guard: scripts/ 下没有 .ps1 —— 路径不对，判失败' -ForegroundColor Red
  exit 3
}

$hits = @()
foreach ($f in $targets) {
  $d = Invoke-ScriptAnalyzer -Path $f.FullName | Where-Object { $_.RuleName -in $rules }
  foreach ($x in $d) {
    $hits += [pscustomobject]@{
      File = $f.FullName.Substring($repo.Length + 1)
      Line = $x.Line
      Rule = $x.RuleName
      Msg = $x.Message
    }
  }
}

if ($hits.Count -eq 0) {
  Write-Host "PSSA-guard: OK —— 扫了 $($targets.Count) 个脚本，两条规则零命中。" -ForegroundColor Green
  exit 0
}

Write-Host "PSSA-guard: 命中 $($hits.Count) 条 —— 判失败" -ForegroundColor Red
$hits | ForEach-Object { Write-Host ("  {0}:{1}  [{2}] {3}" -f $_.File, $_.Line, $_.Rule, $_.Msg) -ForegroundColor Red }
Write-Host ''
Write-Host '这两条的含义：变量算了没人用 / 参数声明了没人读。' -ForegroundColor Yellow
Write-Host '若某条确实是**故意**留着（例如为将来接线），在该处加抑制注释，不要改宽规则。' -ForegroundColor Yellow
exit 1
