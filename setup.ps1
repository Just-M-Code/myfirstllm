$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host 'Hyper Coder setup — Windows 11' -ForegroundColor Cyan
$Python = $null
$Candidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
)
$Python = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Python) {
    $Launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($Launcher) {
        try { & $Launcher.Source -3 --version *> $null; if ($LASTEXITCODE -eq 0) { $Python = $Launcher.Source } } catch { }
    }
}
if (-not $Python) { throw 'Python 3.10–3.12 is required. Install Python from python.org, then rerun setup.ps1.' }
& $Python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Could not create the virtual environment.' }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip wheel
if ($LASTEXITCODE -ne 0) { throw 'Could not upgrade pip.' }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host 'llama-cpp-python may need Microsoft C++ Build Tools on this machine.' -ForegroundColor Yellow
    Write-Host 'Install Visual Studio Build Tools with the Desktop development with C++ workload, then rerun setup.ps1.' -ForegroundColor Yellow
    throw 'Dependency installation failed.'
}
Write-Host 'Setup complete. Launch with .\run.ps1' -ForegroundColor Green
