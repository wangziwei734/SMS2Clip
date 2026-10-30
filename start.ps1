[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "config.json")
)

$ErrorActionPreference = "Stop"
$configPath = [System.IO.Path]::GetFullPath($ConfigPath)
if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Config not found: $configPath. Run .\setup.ps1 first."
}

$exePath = Join-Path $PSScriptRoot "SMS2Clip.exe"
if (Test-Path -LiteralPath $exePath) {
    $targetPath = $exePath
    $arguments = "--config `"$configPath`""
} else {
    $pythonw = Get-Command pythonw.exe -ErrorAction Stop
    $targetPath = $pythonw.Source
    $arguments = "-m SMS2Clip.gui --config `"$configPath`""
}

$process = Start-Process -FilePath $targetPath -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -PassThru
$guiPidPath = Join-Path (Split-Path -Parent $configPath) "sms2clip-gui.pid"
Set-Content -LiteralPath $guiPidPath -Value $process.Id -Encoding ascii
Write-Host "Started SMS2Clip (PID $($process.Id))." -ForegroundColor Green
Write-Host "Look for the tray icon in the Windows notification area."
