[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root
try {
    $python = Get-Command python -ErrorAction Stop
    & $python.Source -m pip install --disable-pip-version-check --quiet --upgrade pyinstaller "pystray>=0.19.5" "Pillow>=10,<13" "qrcode>=7.4" "windows-toasts>=1.3.1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $python.Source -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name NtfyClipboard `
        --icon "assets\ntfy-clipboard.ico" `
        --add-data "assets;assets" `
        --collect-submodules pystray `
        --hidden-import pystray._win32 `
        --collect-submodules windows_toasts `
        --collect-submodules winrt `
        --hidden-import winrt.windows.ui.notifications `
        --hidden-import winrt.runtime `
        --hidden-import winrt.system `
        --exclude-module numpy `
        --exclude-module psutil `
        --exclude-module setuptools `
        --exclude-module charset_normalizer `
        --version-file "version_info.txt" `
        ntfy_clipboard\entry.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Copy-Item -LiteralPath "dist\NtfyClipboard.exe" -Destination "NtfyClipboard.exe" -Force
    Write-Host "Built: $(Join-Path $root 'NtfyClipboard.exe')" -ForegroundColor Green
} finally {
    Pop-Location
}
