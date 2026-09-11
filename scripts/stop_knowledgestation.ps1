# KnowledgeStation stop script (desktop entry).
# Kills the engine (pid from engine.session.json) and the vite dev server
# (the process listening on 127.0.0.1:5173), then removes the stale session file.
$ErrorActionPreference = 'SilentlyContinue'

$SESSION = Join-Path $env:APPDATA 'KnowledgeStation\engine.session.json'

if (Test-Path $SESSION) {
    try {
        $info = Get-Content $SESSION -Raw | ConvertFrom-Json
        if ($info.pid) {
            Stop-Process -Id $info.pid -Force
            Write-Host "[KS] Engine stopped (pid $($info.pid))."
        }
    } catch {}
    Remove-Item $SESSION -Force
}

$conns = Get-NetTCPConnection -LocalPort 5173 -State Listen
foreach ($c in $conns) {
    Stop-Process -Id $c.OwningProcess -Force
    Write-Host "[KS] Frontend stopped (pid $($c.OwningProcess))."
}
if (-not $conns) { Write-Host "[KS] No frontend process found on :5173 (already stopped?)." }

Write-Host "[KS] Done. You can now close this window."
