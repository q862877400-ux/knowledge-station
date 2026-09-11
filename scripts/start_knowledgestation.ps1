# KnowledgeStation one-click launcher (desktop entry).
# Idempotent: if the frontend is already running, just open the browser.
# Otherwise starts the engine + vite, waits for readiness, opens the browser.
# Stop with scripts/stop_knowledgestation.ps1 (or close the two minimized windows).
$ErrorActionPreference = 'Stop'

$ROOT     = 'D:\AI\work space\zcode'
$FRONT    = 'http://127.0.0.1:5173/'
$SESSION  = Join-Path $env:APPDATA 'KnowledgeStation\engine.session.json'
$PY       = Join-Path $ROOT '.venv\Scripts\python.exe'
$NPM      = 'C:\Program Files\nodejs\npm.cmd'

function Test-Url([string]$url) {
    try {
        $r = Invoke-WebRequest -Uri $url -TimeoutSec 3 -UseBasicParsing
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

# 1) Frontend already up -> just open the browser
if (Test-Url $FRONT) {
    Write-Host "[KS] Frontend already running at $FRONT - opening browser (skip start)."
    Start-Process $FRONT
    exit 0
}

# 2) Engine running? (session file + health probe)
$engineRunning = $false
$info = $null
if (Test-Path $SESSION) {
    try {
        $info = Get-Content $SESSION -Raw | ConvertFrom-Json
        if (Test-Url ("http://127.0.0.1:{0}/api/v1/health" -f [int]$info.port)) {
            $engineRunning = $true
        }
    } catch { $info = $null }
}

if (-not $engineRunning) {
    if (-not (Test-Path $PY)) { Write-Host "[KS] ERROR: venv python not found: $PY"; exit 1 }
    Write-Host "[KS] Starting engine (minimized window) ..."
    Start-Process -FilePath $PY -ArgumentList '-m','src.core.main' `
        -WorkingDirectory $ROOT -WindowStyle Minimized | Out-Null
    $deadline = (Get-Date).AddSeconds(60)
    while (-not (Test-Path $SESSION) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 800 }
    if (-not (Test-Path $SESSION)) { Write-Host "[KS] ERROR: engine not ready in 60s."; exit 1 }
    $info = Get-Content $SESSION -Raw | ConvertFrom-Json
    Write-Host "[KS] Engine ready on 127.0.0.1:$($info.port)"
} else {
    Write-Host "[KS] Engine already running on 127.0.0.1:$($info.port) - reusing."
}

# 3) Start vite with engine env
$env:VITE_ENGINE_PORT = "$([int]$info.port)"
$env:VITE_ENGINE_TOKEN = "$($info.token)"
Write-Host "[KS] Starting vite frontend (minimized window) ..."
Start-Process -FilePath $NPM -ArgumentList 'run','dev:vite','--','--host','127.0.0.1' `
    -WorkingDirectory $ROOT -WindowStyle Minimized | Out-Null

# 4) Wait for frontend, then open browser
$deadline = (Get-Date).AddSeconds(60)
while (-not (Test-Url $FRONT) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 1000 }
if (Test-Url $FRONT) {
    Write-Host "[KS] Frontend ready: $FRONT"
    Start-Process $FRONT
} else {
    Write-Host "[KS] Frontend not ready yet - open $FRONT manually in a moment."
}
exit 0
