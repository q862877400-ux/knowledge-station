<#
.SYNOPSIS
  KS 施工快照：给当前提交打一个可回滚的标签（可选再落一份实体备份）。

.DESCRIPTION
  用途（业主 2026-09-17 定的施工纪律）：「小步走、多次提交，每次都做一个快照备份，
  出问题了能回滚」。

  快照 = **git 附注标签**（精确、便宜、可回滚），命名 `step-NN-<label>`，NN 自动递增。
  需要更重的保险时用 -Full 额外落一份实体拷贝（排除可重建目录）。
  `-Full` 的拷贝**不含** .venv/node_modules/缓存，但**含 .git**，所以它本身就是一个
  可以 git log / checkout 的完整副本。

.PARAMETER Label
  这一步的短名（会进标签名），如 `phaseA-materials-table`。只允许 [A-Za-z0-9._-]。

.PARAMETER Note
  这一步做了什么（进标签附注）。

.PARAMETER Full
  除标签外，再复制一份实体备份到 D:\AI\backups\。

.PARAMETER List
  只列出已有快照，不做任何事。

.EXAMPLE
  pwsh scripts/snapshot-project.ps1 -Label phaseA-step1 -Note "材料平面建表 + 评审闸门骨架"

.EXAMPLE
  pwsh scripts/snapshot-project.ps1 -List
#>
[CmdletBinding()]
param(
  [string]$Label,
  [string]$Note = '',
  [switch]$Full,
  [switch]$List
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot   # scripts/ 的上一级 = 仓库根

# 注意：参数名**不能**叫 $Args —— 那是 PowerShell 的自动变量，会被吞掉，
# 结果 git 收不到子命令、只打印 usage（已实测踩过）。
function Invoke-Git { param([string[]]$ArgList) & git -C $repo @ArgList }

if ($List) {
  Write-Host '=== 已有快照（step-* / pre-* 标签）==='
  Invoke-Git -ArgList @('tag', '-l', 'step-*', '--sort=creatordate', '-n1') | ForEach-Object { Write-Host "  $_" }
  Invoke-Git -ArgList @('tag', '-l', 'pre-*', '--sort=creatordate', '-n1') | ForEach-Object { Write-Host "  $_" }
  exit 0
}

if ([string]::IsNullOrWhiteSpace($Label)) {
  throw '需要 -Label <短名>（或 -List 只看已有快照）'
}
if ($Label -notmatch '^[A-Za-z0-9._-]+$') {
  throw "Label 只允许 [A-Za-z0-9._-]，收到：$Label"
}

# ---- 1. 状态检查：有未提交改动就明确报出来（快照只覆盖已提交内容）----
$dirty = Invoke-Git -ArgList @('status', '--porcelain')
if ($dirty) {
  Write-Warning '工作区有未提交改动——快照标签只覆盖**已提交**内容，未提交部分不会进快照：'
  $dirty | ForEach-Object { Write-Host "    $_" }
}

# ---- 2. 自动递增序号 ----
$existing = Invoke-Git -ArgList @('tag', '-l', 'step-*')
$max = 0
foreach ($t in $existing) {
  if ($t -match '^step-(\d+)-') { $n = [int]$Matches[1]; if ($n -gt $max) { $max = $n } }
}
$next = '{0:D2}' -f ($max + 1)
$tag = "step-$next-$Label"

$head = (Invoke-Git -ArgList @('rev-parse', '--short', 'HEAD')) -join ''
$subject = (Invoke-Git -ArgList @('log', '-1', '--format=%s')) -join ''
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

$body = @"
KS 施工快照 step-$next

- 时间  : $stamp
- 提交  : $head  $subject
- 这一步: $Note
"@

if ($tag -in $existing) { throw "标签已存在：$tag" }
Invoke-Git -ArgList @('tag', '-a', $tag, '-m', $body) | Out-Null

Write-Host "OK  快照标签: $tag  ->  $head"
Write-Host "    回滚单步: git -C `"$repo`" reset --hard $tag"
Write-Host "    回滚并看: git -C `"$repo`" checkout $tag"

# ---- 3. 可选实体备份 ----
if ($Full) {
  $snapDir = Join-Path 'D:\AI\backups' "zcode-$tag-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
  New-Item -ItemType Directory -Force -Path $snapDir | Out-Null
  Write-Host "    实体备份 -> $snapDir （可能耗时几分钟）"
  robocopy $repo $snapDir /E /XD .venv node_modules .mypy_cache .pytest_cache __pycache__ .browser4-cli /NFL /NDL /NJH /NJS /R:1 /W:1 | Out-Null
  $rc = $LASTEXITCODE
  if ($rc -ge 8) { throw "robocopy 失败 exit=$rc" }
  Write-Host "    实体备份完成（robocopy exit=$rc，0-7 为正常）"
}
