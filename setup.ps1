[CmdletBinding()]
param(
    [string]$Topic = "",
    [string]$Server = "https://ntfy.sh",
    [switch]$InstallStartup,
    [ValidateSet("Manager", "Service")]
    [string]$StartupMode = "Manager",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $root "config.json"

if ((Test-Path -LiteralPath $configPath) -and -not $Force) {
    Write-Host "config.json already exists. Use -Force to overwrite it." -ForegroundColor Yellow
    Write-Host "Current config: $configPath"
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Topic)) {
    $Topic = [guid]::NewGuid().ToString("N").Substring(0, 24)
}

$config = [ordered]@{
    server = $Server.TrimEnd("/")
    topic = $Topic
    token = ""
    username = ""
    password = ""
    since = ""
    clipboard_gap_ms = 350
    state_file = "state.json"
    log_file = "logs/sms2clip.log"
    reconnect_min_seconds = 1
    reconnect_max_seconds = 60
    language = "zh-CN"
    auto_copy_code = $true
}

$json = $config | ConvertTo-Json
[System.IO.File]::WriteAllText($configPath, $json + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "Created $configPath" -ForegroundColor Green
Write-Host "Topic: $Topic"
Write-Host "Publish URL: $($config.server)/$Topic"

Push-Location $root
try {
    $python = Get-Command python -ErrorAction Stop
    & $python.Source -m SMS2Clip --config $configPath --check
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

if ($InstallStartup) {
    & (Join-Path $root "install-startup.ps1") -ConfigPath $configPath -Mode $StartupMode
}
