<#
.SYNOPSIS
Run an authenticated Android 14 mitmproxy capture session for Astrotalk and analyze
whether POST user/apps/installed fires after test-account login.

.DESCRIPTION
1. Starts `mitmdump` writing to D:\ASTRO\captures\emulator_auth_session.flow on port 8080.
2. Prompts the researcher to sign into Astrotalk in the isolated Android 14 emulator
   using the fictional test account and open the home/chat-list screen.
3. On Ctrl+C stop, automatically runs tools/analyze_capture.py (redacting tokens/IDs/phones)
   and prints whether POST user/apps/installed and save/user-upi-apps were observed.
#>

param(
    [string]$CapturePath = "D:\ASTRO\captures\emulator_auth_session.flow",
    [int]$Port = 8080,
    [string]$ApkPath = "D:\ASTRO\Astrotalk.apk",
    [switch]$AnalyzeOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$AnalyzeScript = Join-Path $RepoRoot "tools\analyze_capture.py"

if (-not (Test-Path $PythonExe)) {
    throw "Virtualenv Python not found at $PythonExe"
}

$CaptureDir = Split-Path -Parent $CapturePath
if (-not (Test-Path $CaptureDir)) {
    New-Item -ItemType Directory -Path $CaptureDir -Force | Out-Null
}

if (-not $AnalyzeOnly) {
    $mitmdump = Get-Command mitmdump -ErrorAction SilentlyContinue
    if (-not $mitmdump) {
        throw "mitmdump not found on PATH. Install mitmproxy first (e.g., pipx install mitmproxy)."
    }

    Write-Host ""
    Write-Host "=== AstroTrust Authenticated Android 14 MITM Capture ===" -ForegroundColor Cyan
    Write-Host "Capture file : $CapturePath"
    Write-Host "Listen port  : $Port"
    Write-Host ""
    Write-Host "Next steps on the isolated Android 14 emulator (System CA + proxy $Port configured):" -ForegroundColor Yellow
    Write-Host "  1. Launch Astrotalk and sign in using the FICTIONAL test account ONLY."
    Write-Host "  2. Wait on the Home / Chat Astrologer List screen for 10-15 seconds so"
    Write-Host "     AuthViewModel`$checkExternalPackages / execute_24h_check can execute."
    Write-Host "  3. Press Ctrl+C in this terminal to stop mitmdump and run offline redaction + analysis."
    Write-Host ""

    try {
        & mitmdump -w $CapturePath --listen-port $Port
    }
    finally {
        Write-Host ""
        Write-Host "Stopping capture; running offline redaction and endpoint audit..." -ForegroundColor Cyan
    }
}

if (-not (Test-Path $CapturePath)) {
    throw "Capture file not created: $CapturePath"
}

& $PythonExe $AnalyzeScript $CapturePath --apk $ApkPath
if ($LASTEXITCODE -ne 0) {
    throw "tools/analyze_capture.py failed with exit code $LASTEXITCODE"
}

$Stem = [System.IO.Path]::GetFileNameWithoutExtension($CapturePath)
$SafeStem = ($Stem -replace "[^A-Za-z0-9._-]+", "_").Trim("_")
$SummaryJson = Join-Path $RepoRoot "data\captures\${SafeStem}_summary.json"

if (Test-Path $SummaryJson) {
    $Summary = Get-Content $SummaryJson -Raw | ConvertFrom-Json
    $InstalledHits = @($Summary.tracker_endpoint_requests | Where-Object { $_.path -like "*user/apps/installed*" })
    $UpiHits = @($Summary.tracker_endpoint_requests | Where-Object { $_.path -like "*save/user-upi-apps*" })

    Write-Host ""
    Write-Host "=== Authenticated Capture Check ===" -ForegroundColor Green
    Write-Host ("Total parsed requests      : {0}" -f $Summary.total_requests_parsed)
    Write-Host ("Astrotalk-host requests    : {0}" -f $Summary.astrotalk_host_request_count)
    Write-Host ("POST user/apps/installed   : {0}" -f $(if ($InstalledHits.Count -gt 0) { "DETECTED ($($InstalledHits.Count) hit(s))" } else { "NOT OBSERVED (0 hits)" }))
    Write-Host ("POST save/user-upi-apps    : {0}" -f $(if ($UpiHits.Count -gt 0) { "DETECTED ($($UpiHits.Count) hit(s))" } else { "NOT OBSERVED (0 hits)" }))
    Write-Host ("Unique packages sent       : {0}" -f $Summary.package_comparison.total_unique_packages_sent)
    Write-Host ("Overlap w/ apppackges.json : {0}" -f $Summary.package_comparison.overlap_with_catalog_count)
    Write-Host ("Redacted summary saved to  : {0}" -f $SummaryJson)
}
