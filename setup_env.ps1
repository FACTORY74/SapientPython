$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

$venvPath = if ($env:SAPIENT_VENV) { $env:SAPIENT_VENV } else { Join-Path $PSScriptRoot ".venv" }
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    uv venv --python 3.15 $venvPath
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
uv pip install --python $pythonExe -r requirements.txt -e .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $pythonExe scripts\quick_test.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $pythonExe -m pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "SAPIENT environment is ready."
Write-Host "Activate it with: $venvPath\Scripts\Activate.ps1"
