# 门禁：命令层空验证的机械检测（PSScriptAnalyzer）
#
# 治哪条缺陷（本仓已实测过的）：
#   把 scripts/run-gates.ps1 里 8 处 $totalForRatchet 逐字改回 $totalRan
#   ⇒ 22 条相关测试全绿、零红；全仓对该脚本的引用全是注释 ⇒ 该脚本自身没有单测。
#
# 为什么用 PSSA（本机实测 2026-09-28）：
#   原始件命中 0 条；把 7 处读取改回、只留赋值点 ⇒ 命中 1 条
#   「Line 475: The variable 'totalForRatchet' is assigned but never used.」
#   ⇒ 一次命中、原始件零误报。
#
# ⚠⚠ **覆盖面的边界（2026-10-09 本机实测，PSSA 1.25.0）—— 就地更正，上面原话保留**：
#   本条规则判的是"**赋值了没人用**"，所以它**只抓得住"7 个读取点全改回、只留赋值点"那一种**。
#   实测（`var/tmp/ratchet-mutation-probe.ps1`，主仓只读、变异件建在 var/tmp）：
#     原样件 0 命中 ／ **8 处里任意一处**单独改回 $totalRan ⇒ **0 命中** ／ 7 处全改回 ⇒ 1 命中。
#   ⇒ 别把本门禁当成"run-gates.ps1 的棘轮接线已有单测"：**任意一处**改坏它看不见。
#   那一半由 `tests/test_run_gates_ratchet_wiring.py` 补（逐处变异 8/8 变红）。
#   ⚠ 本门禁仍不可删：它跑在 `-Quick` 档、pytest 那套只在 `-Full` 档。
#
# 扫的范围（**不是**全规则集）：run-gates.ps1 本身就有 60+ 条诊断
#   （WriteHost / PositionalParams / EmptyCatch / BOM），全扫等于永久红。
#   这里只判两条，**含义不同**：
#     ① PSUseDeclaredVarsMoreThanAssignments —— 变量算了没人用（治本缺陷）
#     ② Severity=ParseError/FileReadError —— 文件读不动/语法坏（防假绿，见下）
#   ⚠ 独立复核（verify-freeze-pssa-guard）抓到：只筛 RuleName 会把 ParseError 静默吞掉，
#     语法坏掉的文件照样拿绿灯 ⇒ ② 是复核逼出来的那一条，不是可有可无。

$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot

# PSSA 优先取**正式的 CurrentUser 模块**（自包含：任何干净检出/提取树都认）。
# var/tmp 那条回落是历史路径、已被 gitignore，只为老环境留个兜底。
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

# 🔴 独立复核（2026-09-28，`verify-freeze-pssa-guard`）抓到的 fail-open 洞，已修：
#   只按 `RuleName -in $rules` 筛 ⇒ PSSA 的 `Severity=ParseError`
#   （MissingEndCurlyBrace / FileReadError 等）**被静默丢**。
#   ⇒ 把一个 .ps1 打成语法错误、或用 FileShare.None 锁住文件，本门禁**照样 exit 0 报"零命中"**。
#   这与本仓 2026-09-19 修过的「命令不存在 ⇒ 恒绿」是同一族假绿。
# 修法：ParseError / FileReadError 一律**单独收集并计为命中**（无论是否在 $rules 里），
#   且"有文件读不动/解析不了"与"规则零命中"在输出上分开讲——绝不让前者显示成绿色 OK。
$hits = @()        # 目标规则命中
$unreadable = @()  # 解析错误 / 读不到的文件
foreach ($f in $targets) {
  $d = Invoke-ScriptAnalyzer -Path $f.FullName
  foreach ($x in $d) {
    $rel = $f.FullName.Substring($repo.Length + 1)
    if ($x.Severity -eq 'ParseError') {
      $unreadable += [pscustomobject]@{ File = $rel; Line = $x.Line; Rule = $x.RuleName; Msg = $x.Message }
    } elseif ($x.RuleName -in $rules) {
      $hits += [pscustomobject]@{ File = $rel; Line = $x.Line; Rule = $x.RuleName; Msg = $x.Message }
    }
  }
}

if ($unreadable.Count -gt 0) {
  Write-Host "PSSA-guard: 有 $($unreadable.Count) 个文件**未能分析**（解析错误/读不到）—— 判失败" -ForegroundColor Red
  $unreadable | ForEach-Object { Write-Host ("  {0}:{1}  [{2}] {3}" -f $_.File, $_.Line, $_.Rule, $_.Msg) -ForegroundColor Red }
  Write-Host '' -ForegroundColor Red
  Write-Host '这一类**不算"通过"**：语法坏掉或读不到的文件拿绿灯，就是假绿。' -ForegroundColor Yellow
  exit 4
}

if ($hits.Count -eq 0) {
  $ruleStr = ($rules -join ', ')
  Write-Host "PSSA-guard: OK —— 扫了 $($targets.Count) 个脚本，规则[$ruleStr]零命中、零未能分析。" -ForegroundColor Green
  exit 0
}

Write-Host "PSSA-guard: 命中 $($hits.Count) 条 —— 判失败" -ForegroundColor Red
$hits | ForEach-Object { Write-Host ("  {0}:{1}  [{2}] {3}" -f $_.File, $_.Line, $_.Rule, $_.Msg) -ForegroundColor Red }
Write-Host ''
Write-Host '命中的含义：变量算了没人用（PSUseDeclaredVarsMoreThanAssignments）。' -ForegroundColor Yellow
Write-Host '若某处确实是**故意**留着（例如为将来接线），在该处加抑制注释，不要改宽规则。' -ForegroundColor Yellow
exit 1
