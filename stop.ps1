[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "config.json")
)

$ErrorActionPreference = "Stop"
$configPath = [System.IO.Path]::GetFullPath($ConfigPath)
$configDir = Split-Path -Parent $configPath
$guiPidPath = Join-Path $configDir "ntfy-clipboard-gui.pid"
$servicePidPath = Join-Path $configDir "ntfy-clipboard.pid"

foreach ($pidPath in @($guiPidPath, $servicePidPath)) {
    if (-not (Test-Path -LiteralPath $pidPath)) { continue }
    $processId = [int](Get-Content -LiteralPath $pidPath -Raw).Trim()
    if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
        & taskkill /PID $processId /T /F | Out-Null
        Write-Host "Stopped process tree $processId." -ForegroundColor Green
    }
    Remove-Item -LiteralPath $pidPath -Force
}
