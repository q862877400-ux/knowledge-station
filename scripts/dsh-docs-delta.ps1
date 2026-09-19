<#
.SYNOPSIS
  DSH 升级后，把「要重新对齐的文档/契约」一次列出来（只读报告，不改任何东西）。

.DESCRIPTION
  背景：KnowledgeStation 的插件跑在定点检出的 DSH 上（见 docs/research/dsh-official/REALIGN.md 的基线）。
  升级 DSH 之后，本仓 docs/research/dsh-official/ 的 8 份分片与 Hindsight 记忆里的条目都**可能过期**，
  而过期不会报错——只会让人写出对不上宿主的行为。

  本脚本只回答一个问题：**这次升级动了哪些「我们的东西」**。它不重读整个仓库，
  而是把 diff 收敛到分片实际引用的 43 条路径 + 我们插件依赖的 3 个客户端包 + 契约关键词。

.PARAMETER Repo
  DSH 检出路径。默认 D:\AI\DSH\deepseek-harness。

.PARAMETER From
  基线 ref（tag/sha）。默认读 REALIGN.md 里登记的基线 tag。

.PARAMETER To
  目标 ref。默认 HEAD。

.PARAMETER ScopeFile
  分片引用路径清单。默认 docs/research/dsh-official/referenced-files.txt（相对本仓根）。

.EXAMPLE
  pwsh -File scripts/dsh-docs-delta.ps1
  pwsh -File scripts/dsh-docs-delta.ps1 -From dsh-v0.1.6-alpha.1 -To dsh-v0.1.6-alpha.2
#>
[CmdletBinding()]
param(
  [string]$Repo = 'D:\AI\DSH\deepseek-harness',
  [string]$From = 'dsh-v0.1.6-alpha.2',
  [string]$To = 'HEAD',
  [string]$ScopeFile = ''
)

$ErrorActionPreference = 'Continue'
$repoRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ScopeFile)) {
  $ScopeFile = Join-Path $repoRoot 'docs/research/dsh-official/referenced-files.txt'
}

Write-Host '==============================================================='
Write-Host ' DSH 升级重对齐报告（只读）'
Write-Host '==============================================================='
Write-Host ("检出      : {0}" -f $Repo)
Write-Host ("基线 From : {0}" -f $From)

if (-not (Test-Path $Repo)) { Write-Host "❌ 检出不存在：$Repo"; exit 1 }
Push-Location $Repo

# --- 0. 浅克隆陷阱：本仓被 --depth 抓过时，祖先判定会给出**假结论**（我实测把正常递进读成了"强推"）---
$isShallow = (Test-Path (Join-Path $Repo '.git/shallow'))
if ($isShallow) {
  Write-Host ''
  Write-Host '⚠️  这是浅克隆（.git/shallow 存在）。'
  Write-Host '   ⇒ **不要**用 merge-base / "forced update" 的消息判断祖先或强推——浅克隆下会得出假结论。'
  Write-Host '   要判祖先先加深：git fetch --depth=400 origin "<tag>"'
}

$toSha = (git rev-parse --short $To 2>&1 | Select-Object -First 1)
Write-Host ("From sha  : {0}" -f (git rev-parse --short $From 2>&1 | Select-Object -First 1))
Write-Host ("To   ref  : {0}  ({1})" -f $To, $toSha)

# --- 1. 祖先关系（仅在非浅克隆下可信）---
if (-not $isShallow) {
  git merge-base --is-ancestor $From $To 2>$null
  if ($LASTEXITCODE -eq 0) { Write-Host "祖先关系  : ✅ $From 是 $To 的祖先（正常递进）" }
  else { Write-Host "祖先关系  : ⚠️ 非祖先（可能换了分支线，或历史被重写）——此时下面的 diff 仍有效，但'升级幅度'要另判" }
}

# --- 2. 规模 ---
Write-Host ''
Write-Host '--- 整体规模 ---'
git diff --shortstat $From $To 2>&1 | ForEach-Object { Write-Host ("  $_") }

# --- 3. 分片引用的路径：谁变了 ---
Write-Host ''
Write-Host '--- ① 分片引用到的路径，在这次升级里变了哪些 ---'
if (Test-Path $ScopeFile) {
  $scope = Get-Content $ScopeFile | Where-Object { $_ -and $_ -notmatch '^\s*#' }
  $changed = @(); $missing = @()
  foreach ($p in $scope) {
    $st = git diff --name-status $From $To -- $p 2>&1
    if ($LASTEXITCODE -ne 0 -or -not $st) {
      # 也可能是路径在 To 里根本不存在了
      git cat-file -e "${To}:$p" 2>$null
      if ($LASTEXITCODE -ne 0) { $missing += $p }
      continue
    }
    foreach ($line in @($st)) { if ($line -match '^[AMD]') { $changed += $line } }
  }
  if ($changed.Count -eq 0) { Write-Host '  （引用到的路径都没有变化 —— 分片结论很可能仍成立）' }
  else {
    Write-Host ("  变化 {0} 条（docs 的带改动行数，用来判断'重读'还是'只需核对'）：" -f $changed.Count)
    foreach ($line in $changed) {
      $p = ($line -split "\s+")[1]
      $s = git diff --shortstat $From $To -- $p 2>&1
      $size = if ($s) { ($s -replace '^\s+', '' ) -replace '\s+file[s]? changed,?', '' } else { '' }
      Write-Host ("    {0}  {1,-62} {2}" -f ($line -split "\s+")[0], $p, $size)
    }
  }
  if ($missing.Count -gt 0) {
    # ⚠ 清单是从分片正文里正则抽的，会混进两种**假阳性**，别当成"契约没了"：
    #   ① 分片里写的省略号路径（如 `packages/.../src/index.ts`）；
    #   ② 正则从更长的路径里截出来的碎片（如 `.agents/skills/dsh-doc/SKILL.md` → `docs/SKILL.md`）。
    $real = $missing | Where-Object { $_ -notmatch '\.\.\.' -and $_ -ne 'docs/SKILL.md' }
    $fake = $missing | Where-Object { $_ -match '\.\.\.' -or $_ -eq 'docs/SKILL.md' }
    if ($fake.Count -gt 0) {
      Write-Host '  ℹ️ 以下条目是**抽取假阳性**（省略号路径 / 正则碎片），不是契约消失：'
      $fake | ForEach-Object { Write-Host ("    · $_") }
    }
    if ($real.Count -gt 0) {
      Write-Host '  ⚠️ 真·在目标版本里已不存在（分片里对应说法必须重写）：'
      $real | ForEach-Object { Write-Host ("    ✗ $_") }
    }
  }
} else { Write-Host "  （找不到清单 $ScopeFile，跳过）" }

# --- 4. 新增文档 ---
Write-Host ''
Write-Host '--- ② 新增的文档（英文正本，非 .zh.md）---'
$oldDocs = git ls-tree -r --name-only $From -- docs 2>&1
$newDocs = git ls-tree -r --name-only $To   -- docs 2>&1
Compare-Object $oldDocs $newDocs |
  Where-Object { $_.SideIndicator -eq '=>' -and $_.InputObject -like '*.md' -and $_.InputObject -notlike '*.zh.md' } |
  ForEach-Object { Write-Host ("  + {0}" -f $_.InputObject) }
Write-Host ("  docs 英文正本：{0} 篇 → {1} 篇" -f `
  (@($oldDocs | Where-Object { $_ -like '*.md' -and $_ -notlike '*.zh.md' }).Count), `
  (@($newDocs | Where-Object { $_ -like '*.md' -and $_ -notlike '*.zh.md' }).Count))

# --- 5. 新增包 ---
Write-Host ''
Write-Host '--- ③ 新增/移除的包 ---'
$oldPk = git ls-tree -r --name-only $From -- packages 2>&1 | Where-Object { $_ -like '*/package.json' } | ForEach-Object { ($_ -split '/')[0..2] -join '/' }
$newPk = git ls-tree -r --name-only $To   -- packages 2>&1 | Where-Object { $_ -like '*/package.json' } | ForEach-Object { ($_ -split '/')[0..2] -join '/' }
Compare-Object $oldPk $newPk | Where-Object SideIndicator -eq '=>' | ForEach-Object { Write-Host ("  + {0}" -f $_.InputObject) }
Compare-Object $oldPk $newPk | Where-Object SideIndicator -eq '<=' | ForEach-Object { Write-Host ("  - {0}" -f $_.InputObject) }
Write-Host ("  包数：{0} → {1}" -f @($oldPk).Count, @($newPk).Count)

# --- 6. 我们插件依赖的 3 个客户端包 + 契约关键词是否还在 ---
Write-Host ''
Write-Host '--- ④ 我们插件挂靠的包，这次动了多少 ---'
foreach ($p in @('packages/client/ui-sidebar-right', 'packages/client/ui-primitives', 'packages/client/ui-slots', 'packages/client/ui-dockkit')) {
  $s = git diff --shortstat $From $To -- $p 2>&1
  if ($s) { Write-Host ("  {0,-38} {1}" -f $p, ($s -replace '^\s+', '')) } else { Write-Host ("  {0,-38} (无变化)" -f $p) }
}

Write-Host ''
Write-Host '--- ⑤ 契约关键词/组件在目标版本里是否仍然存在（不存在 ⇒ 我们的插件会坏或要改写法）---'
# ⚠ 探针字符串别写死成 `export const X`：ui-primitives 用的是
#   `export function Button(...)` + barrel `export { Button } from './Button.tsx'`。
#   我第一版就写成 `export const Button` → 两个版本都报 ❌ 的**假警报**（实测已核）。
#   故组件一律查 barrel 的 `export { X }` 形式。
$probes = [ordered]@{
  'slot 座位 sidebar.right.pane.tab'      = 'sidebar.right.pane.tab'
  'guide 卡片座位 guide.entry'            = 'sidebar.right.tab.guide.entry'
  'tab 类型注册 sidebarRightTabs'          = 'sidebarRightTabs'
  'run-time hook useTabInfo'              = 'useTabInfo'
  '资源模型 useResource'                   = 'useResource'
  "band 字面量 'extension'"                = "'extension'"
  '样式注入标记 data-plugin-css'            = 'data-plugin-css'
}
foreach ($k in $probes.Keys) {
  $hit = git grep -l --fixed-strings $probes[$k] $To -- packages/client 2>$null | Select-Object -First 1
  if ($hit) { Write-Host ("  ✅ {0,-40} 仍在（{1}）" -f $k, ($hit -replace "^$To`:", '')) }
  else { Write-Host ("  ❌ {0,-40} **在目标版本里没找到** —— 需要改我们插件的写法" -f $k) }
}

# 我们**已用**的组件 + **计划改用**的官方组件：都查 ui-primitives 的 barrel。
$barrel = 'packages/client/ui-primitives/src/index.ts'
$components = @('Button', 'Menu', 'IconChevronDownOutline14', 'Tag', 'Pill', 'Input', 'Checkbox', 'Switch', 'StateDot', 'DisclosureRow', 'Tooltip', 'Toast')
Write-Host ''
Write-Host ("  以 {0} 的 barrel 导出为准：" -f $barrel)
foreach ($c in $components) {
  $hit = git grep -n --fixed-strings "export { $c }" $To -- $barrel 2>$null | Select-Object -First 1
  if ($hit) { Write-Host ("    ✅ {0,-28} 可用" -f $c) }
  else {
    # 兜底：也许写成 export { X, Y } 一行多项，或 export function X
    $hit2 = git grep -n -E "export \{[^}]*\b$c\b[^}]*\}|export (function|const) $c\b" $To -- 'packages/client/ui-primitives/src' 2>$null | Select-Object -First 1
    if ($hit2) { Write-Host ("    ✅ {0,-28} 可用（{1}）" -f $c, (($hit2 -split ':')[1..2] -join ':')) }
    else { Write-Host ("    ⛔ {0,-28} **不存在**（要改我们的实现或换别的组件）" -f $c) }
  }
}

Pop-Location
Write-Host ''
Write-Host '==============================================================='
Write-Host ' 做完这一步之后：'
Write-Host '  1) 按 REALIGN.md 的清单逐条判定分片是否仍成立；'
Write-Host '  2) 对受影响的记忆条目补一条 "Correction:" 或重灌（doc_id 见 REALIGN.md）；'
Write-Host '  3) 基线 ref 换成新版本（改 REALIGN.md 与本脚本默认 -From）。'
Write-Host '==============================================================='
exit 0
