<#
  dsh-host-watchdog.ps1 — 自主开发期间的 dsh web 宿主看门狗（2026-09-11）

  ## 为什么需要它（不是"以防万一"，是已知会踩的坑）
  2026-09-11 的真机重启暴露：**自动复活不可依赖**。
    · dsh-doctor supervisor 虽然 phase=armed，但 `profiles: []`（没登记任何 profile）
      且 `policy.autoRepair=false` —— 它每 5s 心跳，却没有任何东西可守护；
    · 它的复活路径调用 PATH 上的 `dsh`，而本机根本没有该可执行文件
      （`~/.dsh-doctor/state/deployed.json` 记着 `ok:false, error:"spawn dsh ENOENT"`）；
    · 那个计划任务只有 **ONLOGON** 触发器（`dsh-doctor service-plan` 原文），
      所以它只在登录时启动，不会盯着端口做复活。
  结论：agent 杀掉宿主后不会有人救场（实测 180s 无复活，最后由用户点复活币）。

  ## 这个脚本做什么 / 不做什么
  只做一件事：**宿主不在，就按 `~/.dsh/guard/launch.json` 的 argv 把它拉回来**。
  不装计划任务、不改 DSH 配置、不动 dsh-doctor / dsh-fuhuobi 的策略与状态
  （那些属于用户的启动链，风险不对称，留给他本人决定）。

  ## 用法
  pwsh -File scripts\dsh-host-watchdog.ps1                      # 默认跑 8 小时
  pwsh -File scripts\dsh-host-watchdog.ps1 -Once                # 只检查一次（自检用）
  pwsh -File scripts\dsh-host-watchdog.ps1 -MaxHours 1 -Once:$false
  停止：写一个 stop 文件（或 kill 日志里记录的 pid）
      New-Item var\tmp\dsh-host-watchdog.stop -ItemType File

  日志：var\tmp\dsh-host-watchdog.log（只记状态变化与心跳，避免刷屏）
  单实例：pid 文件 var\tmp\dsh-host-watchdog.pid（含 pid + 进程启动时刻，防 PID 复用误判）
#>
[CmdletBinding()]
param(
  [int]$IntervalSeconds = 8,
  [int]$DownProbesToAct = 3,
  [int]$MaxHours = 8,
  [int]$MaxRelaunches = 12,
  [int]$RelaunchWaitSeconds = 120,
  [string]$Url = 'http://127.0.0.1:3080/',
  [string]$Root = 'D:\AI\work space\zcode',
  [switch]$Once
)

$ErrorActionPreference = 'Continue'
$logPath = Join-Path $Root 'var\tmp\dsh-host-watchdog.log'
$pidPath = Join-Path $Root 'var\tmp\dsh-host-watchdog.pid'
$stopPath = Join-Path $Root 'var\tmp\dsh-host-watchdog.stop'

function W([string]$m) {
  "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Tee-Object -FilePath $logPath -Append | Out-Null
}

function Test-HostUp {
  try {
    $r = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing
    return ($r.StatusCode -eq 200)
  } catch { return $false }
}

# 起插件健康度（宿主起来 ≠ 插件挂上）：/ks/chat-mode 无 session 应当是 400；404 说明插件没加载
function Get-PluginProbe {
  try {
    $code = & curl.exe -s -o NUL -w '%{http_code}' --max-time 10 "${Url}ks/chat-mode"
    return $code
  } catch { return 'ERR' }
}

function Get-LaunchSpec {
  $p = Join-Path $env:USERPROFILE '.dsh\guard\launch.json'
  if (-not (Test-Path $p)) { return $null }
  try { return Get-Content $p -Raw | ConvertFrom-Json } catch { return $null }
}

function Start-Host {
  $spec = Get-LaunchSpec
  if ($null -eq $spec) { W 'RELAUNCH FAILED: 找不到/无法解析 ~/.dsh/guard/launch.json'; return $null }
  if (-not (Test-Path $spec.file)) { W "RELAUNCH FAILED: 启动器不存在 $($spec.file)"; return $null }
  if (-not (Test-Path $spec.cwd)) { W "RELAUNCH FAILED: cwd 不存在 $($spec.cwd)"; return $null }
  try {
    $proc = Start-Process -FilePath $spec.file -ArgumentList $spec.args -WorkingDirectory $spec.cwd `
      -WindowStyle Hidden -PassThru
    W "RELAUNCH $($spec.file) $($spec.args -join ' ')  (cwd=$($spec.cwd)) -> pid=$($proc.Id)"
    return $proc
  } catch {
    W "RELAUNCH FAILED: $($_.Exception.Message)"
    return $null
  }
}

# ------------------------------------------------------------------ 单实例
$myStart = (Get-Process -Id $PID).StartTime
if (Test-Path $pidPath) {
  try {
    $prev = Get-Content $pidPath -Raw | ConvertFrom-Json
    $p = Get-Process -Id $prev.pid -ErrorAction SilentlyContinue
    if ($p -and $p.StartTime.ToString('o') -eq $prev.started) {
      "watchdog 已在运行 (pid=$($prev.pid))，退出。" | Write-Host
      exit 2
    }
    W "pid 文件是陈的（pid=$($prev.pid) 不存在或已复用），接管"
  } catch { W '无法解析 pid 文件，接管' }
}
@{ pid = $PID; started = $myStart.ToString('o') } | ConvertTo-Json -Compress |
  Set-Content -Encoding UTF8 $pidPath
Remove-Item $stopPath -ErrorAction SilentlyContinue

$deadline = (Get-Date).AddHours($MaxHours)
$startMsg = "=== watchdog START pid=$PID interval=${IntervalSeconds}s down_probes=$DownProbesToAct max_hours=$MaxHours max_relaunches=$MaxRelaunches once=$($Once.IsPresent) ==="
W $startMsg

if ($Once) {
  $up = Test-HostUp
  W "ONCE: host_up=$up plugin=/ks/chat-mode -> $(if ($up) { Get-PluginProbe } else { 'n/a' })"
  Remove-Item $pidPath -ErrorAction SilentlyContinue
  exit $(if ($up) { 0 } else { 1 })
}

# ------------------------------------------------------------------ 主循环
$downCount = 0
$relaunches = 0
$lastHeartbeat = Get-Date
$up0 = Test-HostUp
W "初始状态: host_up=$up0"

while ((Get-Date) -lt $deadline) {
  if (Test-Path $stopPath) { W '收到 stop 文件，正常退出'; break }

  if (Test-HostUp) {
    if ($downCount -ge $DownProbesToAct) {
      W "宿主已恢复（连续 $downCount 次探测失败后）"
    }
    $downCount = 0
    if (((Get-Date) - $lastHeartbeat).TotalMinutes -ge 30) {
      W "heartbeat: host_up=True plugin=$(Get-PluginProbe) relaunches=$relaunches"
      $lastHeartbeat = Get-Date
    }
    Start-Sleep -Seconds $IntervalSeconds
    continue
  }

  $downCount++
  if ($downCount -eq 1) { W '探测失败（第 1 次）' }
  if ($downCount -lt $DownProbesToAct) { Start-Sleep -Seconds $IntervalSeconds; continue }

  if ($relaunches -ge $MaxRelaunches) {
    W "已达复活上限 $MaxRelaunches 次，停止（避免 spawn 风暴）。手工排查：var\tmp\dsh-host-watchdog.log"
    break
  }

  $relaunches++
  W "--- 宿主连续 $downCount 次无响应 → 第 $relaunches 次复活 ---"
  $null = Start-Host

  $waited = 0
  $ok = $false
  while ($waited -lt $RelaunchWaitSeconds) {
    Start-Sleep -Seconds 3; $waited += 3
    if (Test-HostUp) { $ok = $true; break }
  }
  if ($ok) {
    $plugin = Get-PluginProbe
    W "复活成功：${waited}s 后宿主 200；插件探针 /ks/chat-mode -> $plugin (期望 400)"
    $downCount = 0
    $lastHeartbeat = Get-Date
  } else {
    W "复活失败：${RelaunchWaitSeconds}s 内仍未起来（见上方 RELAUNCH 行）"
  }
  Start-Sleep -Seconds $IntervalSeconds
}

W "=== watchdog EXIT (relaunches=$relaunches) ==="
Remove-Item $pidPath -ErrorAction SilentlyContinue
