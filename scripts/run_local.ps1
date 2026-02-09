param(
    [int]$Port = 8000,
    [switch]$SkipChecks,
    [switch]$NoStart,
    [switch]$NoKill
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step([string]$Message) {
    Write-Host "[run_local] $Message" -ForegroundColor Cyan
}

function Invoke-Python([string[]]$Args) {
    & python @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: python $($Args -join ' ')"
    }
}

function Clear-Port([int]$TargetPort) {
    $listeners = Get-NetTCPConnection -State Listen -LocalPort $TargetPort -ErrorAction SilentlyContinue
    if (-not $listeners) {
        Write-Step "Port $TargetPort is already clear."
        return
    }

    $pids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        if ($procId -eq $PID) {
            continue
        }
        Write-Step "Stopping process $procId on port $TargetPort"
        Stop-Process -Id $procId -Force -ErrorAction Stop
    }

    Start-Sleep -Milliseconds 300
    $remaining = Get-NetTCPConnection -State Listen -LocalPort $TargetPort -ErrorAction SilentlyContinue
    if ($remaining) {
        throw "Port $TargetPort is still in use after stop attempt."
    }

    Write-Step "Port $TargetPort cleared."
}

if (-not $NoKill) {
    Clear-Port -TargetPort $Port
}

if (-not $SkipChecks) {
    Write-Step "Running lint checks (ruff)."
    Invoke-Python -Args @('-m', 'ruff', 'check', 'app', 'tests')

    Write-Step "Running type checks (mypy)."
    Invoke-Python -Args @('-m', 'mypy', 'app', 'tests')

    Write-Step "Running unit tests."
    Invoke-Python -Args @('-m', 'unittest', 'discover', '-s', 'tests')
}

if ($NoStart) {
    Write-Step "NoStart enabled. Checks complete."
    exit 0
}

Write-Step "Starting app at http://127.0.0.1:$Port/app"
& python -m uvicorn app.backend.main:app --host 127.0.0.1 --port $Port
