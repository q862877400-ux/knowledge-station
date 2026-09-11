# Bulk ingestion campaign driver v2 - sharded parallel capable.
# Usage: pwsh -File scripts\campaign_driver.ps1 [-StartSkip N] [-SliceSize N] [-EndCap N] [-ProgressLog path] [-Jsonl path]
param(
    [int]$StartSkip = 0,
    [int]$SliceSize = 1000,
    [int]$EndCap = 0,
    [string]$ProgressLog = '',
    [string]$Jsonl = 'D:\AI\work space\标准\体检结果\results.jsonl'
)
$ErrorActionPreference = 'Continue'
$repo = 'D:\AI\work space\zcode'
$py   = Join-Path $repo '.venv\Scripts\python.exe'
$env:PYTHONIOENCODING = 'utf-8'
if (-not $env:MINERU_VIRTUAL_VRAM_SIZE) { $env:MINERU_VIRTUAL_VRAM_SIZE = '9000' }
Push-Location $repo
try {
    $cliArgs = @('scripts\std_bulk_import.py',
                 '--dir',   'D:\AI\work space\标准',
                 '--jsonl', $Jsonl)
    if ($ProgressLog) { $cliArgs += @('--progress', $ProgressLog) }
    $pos = $StartSkip
    $batchNo = 1
    while ($true) {
        if ($EndCap -gt 0 -and $pos -ge $EndCap) {
            Write-Host "`n[SHARD-DONE] reached EndCap=$EndCap"
            break
        }
        $thisMax = $SliceSize
        if ($EndCap -gt 0) { $thisMax = [Math]::Min($SliceSize, $EndCap - $pos) }
        Write-Host "`n===== BATCH #$batchNo start=$pos max=$thisMax ====="
        & $py @cliArgs --start $pos --max $thisMax 2>&1 | ForEach-Object { "$_" }
        $code = $LASTEXITCODE
        if ($code -eq 3) {
            Write-Host "`n[SHARD-COMPLETE] queue/endpoint drained"
            break
        }
        if ($code -ne 0) {
            Write-Host "[warn] batch exit=$code -> continue next slice (overwrite semantics)"
        }
        $pos += $thisMax
        $batchNo++
        Start-Sleep -Seconds 3
    }
}
finally {
    Pop-Location
}
