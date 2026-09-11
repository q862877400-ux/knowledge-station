<#
  dsh-host-restart.ps1 — 带自愈的 dsh web 宿主重启（自主开发用，2026-09-11）

  与 var\tmp\restart-verify.ps1（一次性脚本，假设守护会救场）的区别：
  本脚本**自带恢复能力**，不假设任何人来救场 —— 先拉起看门狗，再杀宿主，
  由看门狗按 `~/.dsh/guard/launch.json` 的 argv 把它拉回来，然后验证插件真的挂上了。

  为什么必须先起看门狗：2026-09-11 实测，dsh-doctor supervisor 不会救场（详见
  scripts/dsh-host-watchdog.ps1 头注：profiles:[] + autoRepair:false + `spawn dsh ENOENT`
  + 计划任务只有 ONLOGON 触发器）。没有看门狗时杀宿主 = 把用户的界面弄死。

  步骤与判据：
    1. 确保看门狗在跑（已在跑则复用）
    2. 杀掉所有 `bin.ts web` 宿主进程
    3. 等宿主回来（默认 ≤150s）
    4. 探针：`/`→200、`/ks/chat-mode` 无 session→**400**（404 = 插件没挂上，FATAL）、
       `/ks/session`→200、伪造 Host→403
    5. 退出码：0 = 全绿；3 = 宿主没回来；4 = 宿主回来了但插件没挂上
  日志：var\tmp\dsh-host-restart.log（看门狗自己的日志另见 dsh-host-watchdog.log）
#>
[CmdletBinding()]
param(
  [int]$WaitTimeoutSeconds = 150,
  [int]$DelaySeconds = 0,
  [string]$Url = 'http://127.0.0.1:3080/',
  [string]$Root = 'D:\AI\work space\zcode',
  [switch]$KeepWatchdogRunning
)

$ErrorActionPreference = 'Continue'
$logPath = Join-Path $Root 'var\tmp\dsh-host-restart.log'
function W([string]$m) {
  "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Tee-Object -FilePath $logPath -Append | Out-Null
}
function Test-Up {
  try { return (Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing).StatusCode -eq 200 } catch { return $false }
}
function ProbePath([string]$path, [string[]]$headers) {
  $a = @('-s', '-o', 'NUL', '-w', '%{http_code}', '--max-time', '15')
  if ($headers) { $a += $headers }
  return (& curl.exe @a "${Url}$path")
}

"=== dsh-host-restart $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Set-Content -Encoding UTF8 $logPath

# 延迟：让调用方（agent 的最终回复 / 用户的当前操作）先落地，再掐宿主。
if ($DelaySeconds -gt 0) {
  W "延迟 ${DelaySeconds}s 后重启（给调用方留出收尾时间）"
  Start-Sleep -Seconds $DelaySeconds
}

# ---------------------------------------------------------------- 1) 看门狗就位
$wdPidPath = Join-Path $Root 'var\tmp\dsh-host-watchdog.pid'
$wdRunning = $false
if (Test-Path $wdPidPath) {
  try {
    $prev = Get-Content $wdPidPath -Raw | ConvertFrom-Json
    $p = Get-Process -Id $prev.pid -ErrorAction SilentlyContinue
    if ($p -and $p.StartTime.ToString('o') -eq $prev.started) { $wdRunning = $true; W "看门狗已在跑 pid=$($prev.pid)" }
  } catch { }
}
if (-not $wdRunning) {
  $wd = Start-Process -FilePath 'pwsh' -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$Root\scripts\dsh-host-watchdog.ps1`"",
    '-MaxHours', '8', '-MaxRelaunches', '12'
  ) -WindowStyle Hidden -PassThru
  W "看门狗已启动 pid=$($wd.Id)（8h / 最多复活 12 次）"
  Start-Sleep -Seconds 4
} else {
  Remove-Item (Join-Path $Root 'var\tmp\dsh-host-watchdog.stop') -ErrorAction SilentlyContinue
}

# ---------------------------------------------------------------- 2) 杀宿主
$hosts = Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
  Where-Object { $_.CommandLine -like '*bin.ts*web*' }
if (-not $hosts) { W '没找到宿主进程 —— 可能本来就没起来，直接等看门狗复活' }
foreach ($h in $hosts) { W "kill web host pid=$($h.ProcessId)"; Stop-Process -Id $h.ProcessId -Force -ErrorAction SilentlyContinue }

# ---------------------------------------------------------------- 3) 等回来
# 双保险：先等看门狗（它会在连续 3 次探测失败后按 launch.json 拉起宿主）；
# 若超时仍没回来，**本脚本自己**再拉一次（不把用户的界面押在单一机制上）。
function Start-HostFromLaunchSpec([string]$tag) {
  $specPath = Join-Path $env:USERPROFILE '.dsh\guard\launch.json'
  if (-not (Test-Path $specPath)) { W "RELAUNCH($tag) FAILED: 找不到 $specPath"; return $false }
  try { $spec = Get-Content $specPath -Raw | ConvertFrom-Json } catch { W "RELAUNCH($tag) FAILED: launch.json 解析失败"; return $false }
  if (-not (Test-Path $spec.file) -or -not (Test-Path $spec.cwd)) {
    W "RELAUNCH($tag) FAILED: 启动器或 cwd 不存在（$($spec.file) / $($spec.cwd)）"; return $false
  }
  try {
    $p = Start-Process -FilePath $spec.file -ArgumentList $spec.args -WorkingDirectory $spec.cwd `
      -WindowStyle Hidden -PassThru
    W "RELAUNCH($tag): $($spec.file) $($spec.args -join ' ') (cwd=$($spec.cwd)) -> pid=$($p.Id)"
    return $true
  } catch { W "RELAUNCH($tag) FAILED: $($_.Exception.Message)"; return $false }
}

$waited = 0
$up = $false
$relaunched = $false
while ($waited -lt $WaitTimeoutSeconds) {
  Start-Sleep -Seconds 3; $waited += 3
  if (Test-Up) { $up = $true; break }
  # 等了一半时间还没动静 → 本脚本兜底拉一次（随后继续等）
  if (-not $relaunched -and $waited -ge [int]($WaitTimeoutSeconds / 2)) {
    $relaunched = $true
    W "看门狗在 ${waited}s 内未拉起宿主 → 本脚本兜底重启"
    $null = Start-HostFromLaunchSpec 'fallback'
  }
}
if (-not $up) {
  W "FATAL: ${WaitTimeoutSeconds}s 内宿主没回来（看门狗与兜底重启都试过了；看 var\tmp\dsh-host-watchdog.log）"
  exit 3
}
$newPid = (Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
  Where-Object { $_.CommandLine -like '*bin.ts*web*' } | Select-Object -First 1).ProcessId
W "宿主已回来：${waited}s，pid=$newPid（兜底重启=$relaunched）"

# ---------------------------------------------------------------- 4) 探针
Start-Sleep -Seconds 4
$fails = 0
function Check([string]$name, [string]$got, [string]$want, [string]$note) {
  $ok = ($got -eq $want)
  if (-not $ok) { $script:fails++ }
  W ("{0,-40} -> {1,-4} 期望 {2,-4} {3}  {4}" -f $name, $got, $want, $(if ($ok) { 'OK  ' } else { 'FAIL' }), $note)
}
Check 'GET / (home)'          (ProbePath '' '') '200' '宿主在服务'
Check 'GET /ks/chat-mode'     (ProbePath 'ks/chat-mode' '') '400' '插件宿主半已加载（404=插件没挂上）'
Check 'GET /ks/session'       (ProbePath 'ks/session' '') '200' '回环放行'
Check 'GET /ks/inspection/summary' (ProbePath 'ks/inspection/summary' '') '200' '巡检路由'
Check 'GET /ks/announce/summary'   (ProbePath 'ks/announce/summary' '') '200' '公告路由'
Check 'GET /ks/settings/api-config' (ProbePath 'ks/settings/api-config' '') '200' '凭据路由'
Check 'GET /ks/report/effect'      (ProbePath 'ks/report/effect' '') '200' '效力报告路由（引擎已拉起）'
Check 'GET /ks/ingest/inbox-default' (ProbePath 'ks/ingest/inbox-default' '') '200' 'R27 入库预览路由（本轮新增）'
Check 'GET /ks/ingest/inbox'       (ProbePath 'ks/ingest/inbox' '') '200' 'R27 待入库目录列表（含 host 兜底）'
Check 'forged Host /ks/session'    (ProbePath 'ks/session' @('-H', 'Host: evil.example.com')) '403' '信任栅栏'

# 客户端产物：宿主按请求从磁盘读 client.js → 只需 Ctrl+F5；这里断言服务端给出的那一份
# 已经含新 tab（浏览器缓存是另一回事）。
$bundle = Join-Path $Root 'plugin\client.js'
if (Test-Path $bundle) {
  $text = [System.IO.File]::ReadAllText($bundle)
  $hasTab = $text.Contains('ks:ingest') -and $text.Contains('入库预览')
  if (-not $hasTab) { $script:fails++ }
  W ("client bundle contains the 入库预览 tab (ks:ingest) -> {0}  ({1} bytes)" -f `
    $(if ($hasTab) { 'OK' } else { 'FAIL' }), $text.Length)
} else {
  $script:fails++
  W 'client.js 不存在（客户端半未构建）'
}

if ($fails -gt 0) { W "FATAL: 宿主活着但插件不正常（fails=$fails）"; exit 4 }

# ---------------------------------------------------------------- 5) 收尾
if (-not $KeepWatchdogRunning) {
  New-Item -ItemType File -Force -Path (Join-Path $Root 'var\tmp\dsh-host-watchdog.stop') | Out-Null
  W '已写 stop 文件，看门狗将在下个循环退出（本轮开发若不再重启则无需它常驻）'
}
W "=== OK: 重启完成且全部探针通过 (pid=$newPid) ==="
exit 0
