param(
    [int]$Port = 8000,
    [switch]$NoBrowser,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

function Resolve-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    throw "Python was not found. Install Python 3 and ensure it is on PATH."
}

$pythonCmd = Resolve-PythonCommand
$uvicornArgs = @("-m", "uvicorn", "app.backend.main:app", "--host", "127.0.0.1", "--port", "$Port")
if (-not $NoReload) {
    $uvicornArgs += "--reload"
}

$url = "http://127.0.0.1:$Port/learn"
Write-Host "Starting RTC-APP on $url" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor DarkGray

if (-not $NoBrowser) {
    try {
        Start-Process $url | Out-Null
    }
    catch {
        Write-Host "Browser auto-open failed. Open this URL manually: $url" -ForegroundColor Yellow
    }
}

$pythonExe = $pythonCmd[0]
$pythonPrefixArgs = @()
if ($pythonCmd.Length -gt 1) {
    $pythonPrefixArgs = $pythonCmd[1..($pythonCmd.Length - 1)]
}

& $pythonExe @pythonPrefixArgs @uvicornArgs
