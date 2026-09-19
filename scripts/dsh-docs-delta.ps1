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

# --- 7. 开始页胶囊的 order：**跨插件共享的排序空间**，出货条目抢号会把我们挤成"随机顺序" ---
# 背景（真实踩到的 bug，2026-09-19）：我们原来取 30，alpha.2 新增的 ui-sidebar-browser
# **也取 30**。开始页按 order 升序排，**同号时谁在前只由注册顺序（bundle 顺序）决定**，
# 而 V8 的 sort 是稳定的 ⇒ 看起来"总是那样"，极难发现。我们当初的注释写了
# "上游新增条目时可能需要重排"，但**没有任何东西去检查它**，所以没防住。
# 本节就是把那句话变成升级时真会跑的一步。
#
# 实现注意（我前两版都写错过，别再踩）：
#   ① 别把两次 -match 串进一个 `-and` 条件再读 $Matches —— 那时 $Matches 只剩**最后一次**
#      匹配的组号，`$Matches[1]` 取到的是 order 而不是路径；
#   ② git 的 pathspec 里 `*` **不跨 `/`**（wildmatch 要求整条路径匹配），所以
#      `packages/client/*/src/client` **一个文件都匹配不到** ⇒ 我第一版静默输出空集，
#      也就是"检查装成通过"。改用 `packages/client` 全扫 + 自己按 `/src/client/` 过滤；
#   ③ `guide: [` 有单行（terminal）和多行（files/browser）两种写法，**按行 grep 抓不住**
#      ⇒ 先找 `guide: [` 行，再按方括号配平把整块取出来，收块内**所有** order。
function Get-GuideOrdersFromText {
  param([string]$Text)
  $found = @()
  $lines = $Text -split "`r?`n"
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -notmatch 'guide:\s*\[') { continue }
    $depth = 0; $block = ''
    for ($j = $i; $j -lt [Math]::Min($i + 40, $lines.Count); $j++) {
      $block += $lines[$j] + "`n"
      $depth += ([regex]::Matches($lines[$j], '\[')).Count
      $depth -= ([regex]::Matches($lines[$j], '\]')).Count
      if ($depth -le 0) { break }
    }
    foreach ($om in [regex]::Matches($block, 'order:\s*([0-9]+)')) { $found += [int]$om.Groups[1].Value }
  }
  return $found
}

Write-Host ''
Write-Host '--- 7. 开始页胶囊 order 空间（我们的号必须避开出货条目占用的号）---'
$shippedOrders = @()
$guideFiles = git grep -l 'guide:' $To -- packages/client 2>$null
foreach ($entry in $guideFiles) {
  $gf = $entry -replace ("^" + [regex]::Escape($To) + ":"), ''   # git grep -l 输出 "ref:path"
  if ($gf -notmatch '/src/client/') { continue }                 # 只要生产源码（排掉 tests）
  $txt = (git show ("{0}:{1}" -f $To, $gf) 2>$null) -join "`n"
  if ([string]::IsNullOrWhiteSpace($txt)) { continue }
  foreach ($o in (Get-GuideOrdersFromText $txt)) {
    $shippedOrders += $o
    Write-Host ("    出货 {0,-40} order = {1,-4}  ({2})" -f $gf, $o, $To)
  }
}
if ($shippedOrders.Count -eq 0) {
  Write-Host '    ⚠ 一个出货 guide order 都没扫到 —— 很可能是**检查本身坏了**（不是"没有"）。'
  Write-Host '      别把这条当通过：先核 git grep 的 pathspec 与 guide 块的写法是否变了。'
}
# 我们自己的值：从本仓源码读，避免脚本里再抄一份（抄一份就会再次不同步）
$ksSidebar = Join-Path $repoRoot 'plugin/client/ksSidebar.ts'
if (Test-Path $ksSidebar) {
  $m2 = [regex]::Match((Get-Content $ksSidebar -Raw), 'export const KS_GUIDE_ORDER_PDF = (\d+)')
  if ($m2.Success) {
    $myOrder = [int]$m2.Groups[1].Value
    Write-Host ("    ── 我们 KS_GUIDE_ORDER_PDF = {0}" -f $myOrder)
    if ($shippedOrders -contains $myOrder) {
      Write-Host ("    ⛔ **撞号**：出货条目也占 {0} ⇒ 两张卡先后只由注册顺序决定（等于随机）。**必须让开**。" -f $myOrder)
    } else {
      Write-Host ("    ✅ 未与任何出货条目同号（出货占用：{0}）" -f (($shippedOrders | Sort-Object -Unique) -join ', '))
    }
  } else {
    Write-Host '    ⚠ 没在 ksSidebar.ts 里找到 KS_GUIDE_ORDER_PDF —— 脚本与本仓已不同步，请核。'
  }
} else {
  Write-Host ("    ⚠ 未找到 {0}（换机器/换检出时请核）" -f $ksSidebar)
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
