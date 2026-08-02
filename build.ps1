$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

python -m pip install pyinstaller --quiet

python -m PyInstaller --noconfirm --clean ZifyVPN.spec

Write-Host ""
Write-Host "Build complete: dist\ZifyVPN.exe"
Write-Host "Data (storage.json, logs) will be created next to the exe on first run."
