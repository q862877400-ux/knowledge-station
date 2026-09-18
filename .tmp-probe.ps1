param([string]$UrlsFile)
$ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
$urls = Get-Content $UrlsFile | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") }
foreach ($u in $urls) {
  $parts = $u -split "\s*\|\|\s*"
  $url = $parts[0].Trim()
  $name = if ($parts.Count -gt 1) { $parts[1].Trim() } else { $url }
  Write-Output "===== $name"
  Write-Output "URL: $url"
  try {
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 25 -MaximumRedirection 5 -Headers @{
      "User-Agent" = $ua
      "Accept" = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
      "Accept-Language" = "zh-CN,zh;q=0.9,en;q=0.8"
    }
    Write-Output "STATUS: $($r.StatusCode)"
    Write-Output "LEN: $($r.RawContentLength)"
    $ct = $r.Headers["Content-Type"]
    Write-Output "CTYPE: $ct"
    if ($r.Content -is [byte[]]) {
      $txt = [System.Text.Encoding]::UTF8.GetString($r.Content)
    } else { $txt = [string]$r.Content }
    # detect charset
    if ($txt -match 'charset=["'']?(gb2312|gbk|GB2312|GBK)') {
      try { $txt = [System.Text.Encoding]::GetEncoding("GB18030").GetString($r.Content) } catch {}
    }
    $plain = $txt -replace '(?s)<script.*?</script>', ' ' -replace '(?s)<style.*?</style>', ' ' -replace '<[^>]+>', ' ' -replace '&nbsp;', ' ' -replace '&#\d+;', ' ' -replace '\s+', ' '
    $plain = $plain.Trim()
    if ($plain.Length -gt 460) { $plain = $plain.Substring(0, 460) }
    Write-Output "TEXT: $plain"
    # title tag
    if ($txt -match '(?s)<title[^>]*>(.*?)</title>') { Write-Output "TITLE: $($Matches[1].Trim())" }
    if ($txt -match '(?s)(vue|react|__NUXT__|webpack|bundle\.js|app\.js|chunk)') { Write-Output "JSAPP: yes-spa-marker" }
  } catch {
    $m = $_.Exception.Message
    Write-Output "ERR: $m"
    if ($_.Exception.Response) {
      try { Write-Output "ERRSTATUS: $([int]$_.Exception.Response.StatusCode)" } catch {}
    }
  }
  Write-Output ""
  Start-Sleep -Milliseconds 250
}
