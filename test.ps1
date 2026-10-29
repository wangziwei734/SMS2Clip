[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "config.json")
)

$ErrorActionPreference = "Stop"
$python = Get-Command python -ErrorAction Stop

Push-Location $PSScriptRoot
try {
    & $python.Source -m unittest discover -s (Join-Path $PSScriptRoot "tests") -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $python.Source -m ntfy_clipboard --config $ConfigPath --check
} finally {
    Pop-Location
}
