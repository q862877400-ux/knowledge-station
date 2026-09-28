# 独立复核：PSScriptAnalyzer 能不能抓到「命令层空验证」
#
# 背景：本仓已实测的缺陷 —— 把 scripts/run-gates.ps1 里 8 处 $totalForRatchet
# 逐字改回 $totalRan，22 条相关测试全绿、零红（全仓对该脚本的引用全是注释）。
# 有子代理称 PSScriptAnalyzer 的 PSUseDeclaredVarsMoreThanAssignments 能一次命中。
# 本脚本**只读原件**，变异件另建在 var/tmp，绝不碰主仓文件。

$ErrorActionPreference = 'Stop'
$repo = 'D:\AI\work space\zcode'
$src  = Join-Path $repo 'scripts\run-gates.ps1'
$mod  = Join-Path $repo 'var\tmp\study\r2-pssa\PSScriptAnalyzer'
$tmp  = Join-Path $repo 'var\tmp\verify-pssa-20260928'
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

Import-Module $mod -Force
$ver = (Get-Module PSScriptAnalyzer).Version
"PSScriptAnalyzer 版本: $ver"
"原件: $src  (只读，不修改)"
"原件 SHA256: " + (Get-FileHash $src -Algorithm SHA256).Hash.Substring(0,16)
"原件里 `$totalForRatchet 出现次数: " + ([regex]::Matches((Get-Content $src -Raw), '\$totalForRatchet')).Count
""

$rule = 'PSUseDeclaredVarsMoreThanAssignments'

# --- 1. 原始件 ---
$orig = Invoke-ScriptAnalyzer -Path $src | Where-Object { $_.RuleName -eq $rule }
"【原始件】PSUseDeclaredVarsMoreThanAssignments 命中: $(@($orig).Count)"

# --- 2. 变异件：把读取点改回 $totalRan，只留赋值点 ---
$text = Get-Content $src -Raw
# 赋值点形如：$totalForRatchet = if (...) {...}  —— 保留
# 其余 $totalForRatchet 出现在表达式里 → 替换
$lines = $text -split "`r?`n"
$out = foreach($ln in $lines){
  if($ln -match '^\s*\$totalForRatchet\s*='){ $ln }                 # 赋值：留
  else { $ln -replace '\$totalForRatchet', '$totalRan' }            # 读取：换
}
$mut = ($out -join "`r`n")
$mpath = Join-Path $tmp 'run-gates.MUTATED.ps1'
Set-Content -Path $mpath -Value $mut -Encoding UTF8
"变异件: $mpath"
"变异件里 `$totalForRatchet 出现次数: " + ([regex]::Matches($mut, '\$totalForRatchet')).Count
"（应为 1，即只剩赋值点）"
""

# --- 3. 变异件跑同一条规则 ---
$mutd = Invoke-ScriptAnalyzer -Path $mpath | Where-Object { $_.RuleName -eq $rule }
"【变异件】PSUseDeclaredVarsMoreThanAssignments 命中: $(@($mutd).Count)"
foreach($d in $mutd){
  "   Line $($d.Line): $($d.Message)"
  "   Extent: $(($d.Extent.Text -replace '\s+',' '))"
}

# --- 4. 结论 ---
""
"=" * 76
if(@($orig).Count -eq 0 -and @($mutd).Count -ge 1){
  "结论: **成立** —— 原始件零误报，变异件命中。"
} elseif(@($orig).Count -eq 0 -and @($mutd).Count -eq 0){
  "结论: **不成立** —— 变异件也没命中。"
} else {
  "结论: **有误报** —— 原始件也命中了 $(@($orig).Count) 条。"
}
"（本脚本只读主仓，未修改任何被跟踪文件）"
