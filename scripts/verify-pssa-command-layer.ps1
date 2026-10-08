# 独立复核：PSScriptAnalyzer 能不能抓到「命令层空验证」
#
# 背景：本仓已实测的缺陷 —— 把 scripts/run-gates.ps1 里 8 处 $totalForRatchet
# 逐字改回 $totalRan，22 条相关测试全绿、零红（全仓对该脚本的引用全是注释）。
# 有子代理称 PSScriptAnalyzer 的 PSUseDeclaredVarsMoreThanAssignments 能一次命中。
# 本脚本**只读原件**，变异件另建在 var/tmp，绝不碰主仓文件。
#
# ⚠⚠ **2026-10-09 更正（就地，原结论保留在 §4 的注释里）**：
#   原版只试了「7 个读取点全改回」这一种，于是得出"成立"。
#   补上**逐处**变异后实测：**任意一处单独改回 => 0 命中** => 原结论**只对全改那一种成立**，
#   不能当作"run-gates.ps1 的棘轮接线已有单测"。那一半由
#   `tests/test_run_gates_ratchet_wiring.py` 补（逐处变异 8/8 变红）。
#   另：原版把 PSSA 模块路径写死在 var/tmp（已被 gitignore 清掉）=> 干净机上直接报错。
#   现改为与 `scripts/pssa-guard.ps1` 同一套候选（CurrentUser 优先）。

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$src  = Join-Path $repo 'scripts\run-gates.ps1'
$tmp  = Join-Path $repo 'var\tmp\verify-pssa-command-layer'
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

$pssaCandidates = @(
  (Join-Path $env:USERPROFILE 'Documents\PowerShell\Modules\PSScriptAnalyzer'),
  (Join-Path $repo 'var\tmp\study\r2-pssa\PSScriptAnalyzer')
)
$pssa = $pssaCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $pssa) {
  Write-Host 'PSScriptAnalyzer 未安装 => 本复核**不能跑**（不是"通过"）' -ForegroundColor Red
  Write-Host '  装它：Install-Module PSScriptAnalyzer -Scope CurrentUser -Force' -ForegroundColor Yellow
  exit 2
}
Import-Module $pssa -Force
$ver = (Get-Module PSScriptAnalyzer).Version
"PSScriptAnalyzer 版本: $ver"
"原件: $src  (只读，不修改)"
"原件 SHA256: " + (Get-FileHash $src -Algorithm SHA256).Hash.Substring(0,16)
$text = Get-Content $src -Raw
"原件里 `$totalForRatchet 出现次数: " + ([regex]::Matches($text, '\$totalForRatchet')).Count
""

$rule = 'PSUseDeclaredVarsMoreThanAssignments'
function Get-Hit([string]$path) {
  return @(Invoke-ScriptAnalyzer -Path $path | Where-Object { $_.RuleName -eq $rule }).Count
}

# --- 1. 原始件 ---
$origCount = Get-Hit $src
"【原始件】$rule 命中: $origCount"
""

# --- 2. 逐处变异（2026-10-09 新增）：把第 i 处单独改回 $totalRan ---
$ms = [regex]::Matches($text, '\$totalForRatchet')
"【逐处变异】共 $($ms.Count) 处（含 1 处注释），逐处单独改回 `$totalRan："
$singleHitTotal = 0
for ($i = 0; $i -lt $ms.Count; $i++) {
  $m = $ms[$i]
  $mut = $text.Substring(0, $m.Index) + '$totalRan' + $text.Substring($m.Index + $m.Length)
  $p = Join-Path $tmp ("single-$i.ps1")
  Set-Content -Path $p -Value $mut -Encoding UTF8
  $ln = ($text.Substring(0, $m.Index) -split "`n").Count
  $h = Get-Hit $p
  $singleHitTotal += $h
  "  i=$i (原行 ~$ln) 命中=$h"
}
"  => 逐处命中合计 = $singleHitTotal"
""

# --- 3. 全部读取点变异（原版唯一试过的那一种）：只留赋值点 ---
$ls = $text -split "`r?`n"
$out = foreach ($ln in $ls) {
  if ($ln -match '^\s*\$totalForRatchet\s*=') { $ln } else { $ln -replace '\$totalForRatchet', '$totalRan' }
}
$mut = ($out -join "`r`n")
$mpath = Join-Path $tmp 'run-gates.MUTATED.ps1'
Set-Content -Path $mpath -Value $mut -Encoding UTF8
"【全改回】变异件: $mpath"
"变异件里 `$totalForRatchet 出现次数: " + ([regex]::Matches($mut, '\$totalForRatchet')).Count + "（应为 1，即只剩赋值点）"
$allCount = Get-Hit $mpath
"【全改回】$rule 命中: $allCount"
foreach ($d in @(Invoke-ScriptAnalyzer -Path $mpath | Where-Object { $_.RuleName -eq $rule })) {
  "   Line $($d.Line): $($d.Message)"
}
""

# --- 4. 结论 ---
"=" * 76
"结论："
if ($origCount -eq 0 -and $allCount -ge 1) {
  "  · 「7 个读取点**全**改回」=> 命中 $allCount => **抓得住**（原版结论，成立）。"
} else {
  "  · 「7 个读取点**全**改回」=> 命中 $allCount => **抓不住**（与原版结论相反，请查）。"
}
if ($singleHitTotal -eq 0) {
  '  · 「**任意一处**单独改回」=> 命中 0 => **抓不住**（2026-10-09 实测）。'
  '     => 本门禁**不能**当作「run-gates.ps1 棘轮接线已有单测」；那一半由'
  '       tests/test_run_gates_ratchet_wiring.py 补（逐处变异 8/8 变红）。'
} else {
  "  · 「任意一处单独改回」=> 命中合计 $singleHitTotal => 至少部分抓得住（请逐条看上面）。"
}
"（本脚本只读主仓，未修改任何被跟踪文件）"
