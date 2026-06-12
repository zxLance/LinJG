$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Port = 8765
$ChromeCandidates = @(
  "C:\Program Files\Google\Chrome\Application\chrome.exe",
  "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$Chrome = $ChromeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Chrome) {
  throw "Chrome was not found. Install Chrome or edit start-viewer.ps1 with your browser path."
}

$ExistingServer = Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -match "node" -and
    $_.CommandLine -like "*serve-viewer.mjs*" -and
    $_.CommandLine -like "*$Root*"
  }

if (-not $ExistingServer) {
  Start-Process -FilePath "node" `
    -ArgumentList "serve-viewer.mjs" `
    -WorkingDirectory $Root `
    -WindowStyle Hidden
  Start-Sleep -Milliseconds 900
}

Start-Process -FilePath $Chrome -ArgumentList @(
  "--new-window",
  "--disable-background-timer-throttling",
  "--disable-renderer-backgrounding",
  "http://127.0.0.1:$Port/demo/viewer.html?ts=$([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())"
)

Write-Host "Opened http://127.0.0.1:$Port/demo/viewer.html"
