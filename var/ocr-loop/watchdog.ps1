# VLM 批量看门狗（2026-09-15 立，2026-09-15 二次修订）
#
# 为什么需要：批量是"独立进程"，**死了没人知道**——实测一次因并发 bug 抛
# AttributeError 直接终结整个进程，是靠人工看日志才发现的。35,000 部跨天运行
# 不能靠人盯，故加此自愈。
#
# 判据：**进程存活**（而非"状态文件是否在推进"）——因为本地 VLM 兜底跑一部
# 62 页文档要 37 分钟，用文件 mtime 判"卡住"会误杀正在正常工作的进程。
#
# 二次修订（实测教训）：本脚本**自己也可能没在运行**——交接时发现
# `watchdog_loop.ps1` 早已不在，批量静默死了两次无人拉起。故：
#   1) 进程匹配同时含 python.exe / pythonw.exe（曾只匹配 python.exe）；
#   2) 拉起时用 -PassThru 取 PID 并回写 `watchdog.log`——静默死亡至少留下
#      「某 PID 启动过」的痕迹，配合 vlm_ocr_log.jsonl 的时间戳即可定位死亡点；
#   3) 启动后 3 秒复查一次存活，把"起了就死"（如启动即抛异常）与"跑一段才死"
#      区分开，前者当场可见，不必等到下一次巡检。
#
# 三次修订（2026-09-15 用户指令）：语料换成**全新文档**——原 260 部被反复审计
# 修复已过拟合，故改跑全新语料。首批 231 部已跑完（零失败、无达线类），
# 现按批推进，目标 35,243 部全量。
#
# **四次修订：语料清单不再硬编码**。原先 $corpus/$log/$err 写死在脚本里，
# 每换一批都要手工改脚本——无人值守推进时这就是断点（改漏一次就白跑一批）。
# 现改读 `evolve/current_batch.json`（单一所有者 = `batch_config.py`），
# 换批只需 `next_batch.py` + `batch_config.py set …`。
#
# 用法（由本文件的常驻循环或 task-board cron 调用）：
#   pwsh -NoProfile -File var\ocr-loop\watchdog.ps1
$ErrorActionPreference = "SilentlyContinue"
$root = "D:\AI\work space\zcode"
$script = "var\ocr-loop\vlm_ocr.py"
$wdlog = "var\ocr-loop\watchdog.log"

# 当前批次（读单一所有者；取不到则回退首批）
$corpusRel = "evolve/fresh_corpus_work.json"
$logRel = "vlm_fresh.log"
$errRel = "vlm_fresh.err"
$chanRel = "auto"
$cfgPath = Join-Path $root "var\ocr-loop\evolve\current_batch.json"
if (Test-Path $cfgPath) {
    try {
        $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
        if ($cfg.list) { $corpusRel = $cfg.list }
        if ($cfg.log)  { $logRel = $cfg.log }
        if ($cfg.err)  { $errRel = $cfg.err }
        # channel ∈ {auto, local}：**local = 不提交任何云任务**（零 API 消耗），
        # 用途："本地跑着、等谷价再走 API"。默认 auto。
        if ($cfg.channel) { $chanRel = $cfg.channel }
    } catch { }
}
$corpus = ("var/ocr-loop/" + $corpusRel) -replace '\\', '/'
$log = Join-Path $root ("var\ocr-loop\" + ($logRel -replace '/', '\'))
$err = Join-Path $root ("var\ocr-loop\" + ($errRel -replace '/', '\'))

function Write-Wd($msg) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path "$root\$wdlog" -Value "[$stamp] $msg" -Encoding utf8
}

$alive = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -like "*$script*" }

if ($alive) {
    Write-Output "[watchdog] 批量存活 pid=$($alive.ProcessId -join ',') 无需干预"
    exit 0
}

# **driver 仲裁**：`batch_advance.py` 在跑时由它负责跨批推进（它会拉起下一批），
# 本脚本必须退让——否则两者会各自拉起一个 vlm_ocr 跑同一批（重复烧云额度）。
#
# **心跳新鲜度必须校验**（2026-09-15 实测缺陷）：原判据只看"心跳文件里的 pid 是否
# 存在"——driver 进程被任务管理器/会话清理杀掉后，**旧 pid 被 OS 复用给别的进程**，
# 或 `Get-Process` 恰好命中残留项，于是 watchdog 以为 driver 还活着、**永远退让**，
# 跨批推进彻底停滞（实测停在批次 #2 结束前 27 分钟无人推进）。
# 现加两道：① pid 必须真在跑；② 心跳**不超过 STALE_MIN 分钟**（driver 每 5 分钟
# 至少写一次日志，超时即视为已死）。
$owner = Join-Path $root "var\ocr-loop\batch_advance.owner"
$STALE_MIN = 12
if (Test-Path $owner) {
    $opid = 0
    $ots = $null
    try {
        $oj = Get-Content $owner -Raw | ConvertFrom-Json
        $opid = [int]$oj.pid
        try { $ots = [datetime]::ParseExact($oj.ts, "yyyy-MM-dd HH:mm:ss", $null) } catch { }
    } catch { }
    $orun = ($opid -gt 0) -and [bool](Get-Process -Id $opid -ErrorAction SilentlyContinue)
    $ageMin = if ($ots) { ((Get-Date) - $ots).TotalMinutes } else { 9999 }
    # **只要 driver 进程真的活着就让位**（2026-09-15 实测修正）。
    # 原先只在"心跳新鲜"时退让，而心跳曾因 driver 主循环被慢查询卡住 37 分钟
    # 而变旧 → 本脚本判定"driver 卡死"→ 另拉起一份 vlm_ocr → **进程增殖到 5 个**
    # （driver 与 watchdog 抢着拉；state 无跨进程锁，会互相覆盖台账）。
    # 判据改用"进程存活"（`Get-Process -Id` 快且准）：
    #   - driver 活着 → 一律退让（它在管批次；慢≠死，见 batch_advance 的 CPU 判活）；
    #   - driver 真死了（pid 不存在）→ 才接管。
    # 心跳仍记录在日志里供人工回看，但**不再作为接管依据**。
    if ($orun) {
        Write-Output "[watchdog] batch_advance 驱动存活 pid=$opid（心跳 $([math]::Round($ageMin,1)) 分钟前）→ 退让（慢≠死，跨批仍由它负责）"
        exit 0
    }
    if ($orun) {
        Write-Wd "driver pid=$opid 在跑但心跳已 $([math]::Round($ageMin,0)) 分钟未刷新（>${STALE_MIN}）→ 视为卡死，本脚本接管"
    } else {
        Write-Wd "driver 心跳文件在但 pid=$opid 已死 → 本脚本接管拉起"
    }
}

Write-Wd "批量不在运行 → 拉起（通道 $chanRel；状态文件 + 日志自愈保证从断点续跑）"
# **推进缺口警告**（2026-09-15 实测教训）：本脚本只按 current_batch 拉起**当前批**，
# **不懂跨批推进**——批次切换是 driver（batch_advance.py）的职责。所以 driver 死掉时，
# 批量会照跑、批次却永远不换，而日志看上去一切正常（"批量存活 pid=… 无需干预"）。
# 实测：driver 因路径 bug 每批都"交人工"停下，推进链静默断掉数小时无人察觉。
# 故此处**显式记下"我在没有 driver 的情况下接管了"**，让这个缺口至少可被检索
# （`Select-String '无 driver 接管' watchdog.log`）。
if (-not (Test-Path $owner)) {
    Write-Wd "⚠ 注意：本次接管时**无 driver 心跳**——批次推进无人负责（跨批由 batch_advance.py 负责，请确认它在跑）"
}
$env:KS_VLM_ONLY = "1"
$env:KW_DAILY_CLOUD_FILES = "5000"
# **必须用绝对路径并加引号**（2026-09-15 实测）：Python 脚本路径与语料清单路径都
# 含空格（"D:\AI\work space\..."），不带引号时 PowerShell 会把一个路径**拆成多个
# 参数**传给 python，进程启动即失败（表现为"pid= 启动即退出"、err 无输出）。
# 实测：带引号的绝对路径写法可稳定拉起，不带引号的相对路径写法启动即退。
$pyExe = Join-Path $root ".venv\Scripts\python.exe"
$scriptAbs = Join-Path $root $script
$corpusAbs = Join-Path $root ($corpus -replace '/', '\')
$proc = Start-Process -FilePath $pyExe `
    -ArgumentList '-X', 'utf8', "`"$scriptAbs`"",
                  '--corpus-list', "`"$corpusAbs`"",
                  '--docs', '9999', '--channel', $chanRel,
                  '--cloud-timeout', '900', '--cloud-attempts', '3',
                  '--parallel', '8' `
    -RedirectStandardOutput $log `
    -RedirectStandardError $err `
    -PassThru -WindowStyle Hidden -WorkingDirectory $root

Start-Sleep -Seconds 5
$still = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
if ($still) {
    Write-Wd "已拉起 pid=$($proc.Id)（5 秒后仍存活）"
    Write-Output "[watchdog] 已拉起 pid=$($proc.Id)，日志 $log"
} else {
    $tail = (Get-Content $err -Tail 5 -ErrorAction SilentlyContinue | Out-String)
    Write-Wd "拉起 pid=$($proc.Id) 但 5 秒内已退出——err 尾部：$tail"
    Write-Output "[watchdog] 警告：pid=$($proc.Id) 启动即退出，检查 $err"
}
exit 0
