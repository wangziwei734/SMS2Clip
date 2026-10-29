[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "config.json")
)

$ErrorActionPreference = "Stop"
$configPath = [System.IO.Path]::GetFullPath($ConfigPath)
if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Config not found: $configPath. Run .\setup.ps1 first."
}

$exePath = Join-Path $PSScriptRoot "NtfyClipboard.exe"
if (Test-Path -LiteralPath $exePath) {
    $targetPath = $exePath
    $arguments = "--minimized --config `"$configPath`""
} else {
    $pythonw = Get-Command pythonw.exe -ErrorAction Stop
    $targetPath = $pythonw.Source
    $arguments = "-m ntfy_clipboard.gui --minimized --config `"$configPath`""
}

$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "ntfy-clipboard.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.WindowStyle = 7
$shortcut.Description = "Ntfy Clipboard - SMS verification code clipboard"
$shortcut.Save()

Write-Host "Installed startup shortcut: $shortcutPath" -ForegroundColor Green
