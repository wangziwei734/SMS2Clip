[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "config.json"),
    [ValidateSet("Manager", "Service")]
    [string]$Mode = "Manager"
)

$ErrorActionPreference = "Stop"
$configPath = [System.IO.Path]::GetFullPath($ConfigPath)
if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Config not found: $configPath. Run .\setup.ps1 first."
}

$exePath = Join-Path $PSScriptRoot "SMS2Clip.exe"
if (Test-Path -LiteralPath $exePath) {
    $targetPath = $exePath
    $launchArguments = if ($Mode -eq "Service") { "--service" } else { "--minimized" }
    $arguments = "$launchArguments --config `"$configPath`""
} else {
    $pythonw = Get-Command pythonw.exe -ErrorAction Stop
    $targetPath = $pythonw.Source
    $module = if ($Mode -eq "Service") { "SMS2Clip" } else { "SMS2Clip.gui" }
    $launchArguments = if ($Mode -eq "Service") { "--service" } else { "--minimized" }
    $arguments = "-m $module $launchArguments --config `"$configPath`""
}

$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "sms2clip.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.WindowStyle = 7
$shortcut.Description = "SMS2Clip - SMS verification code clipboard"
$shortcut.Save()

Write-Host "Installed startup shortcut: $shortcutPath" -ForegroundColor Green
