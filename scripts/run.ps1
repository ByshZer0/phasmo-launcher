#requires -Version 5.1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $env:PYTHONUTF8 = "1"
    python main.py @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
