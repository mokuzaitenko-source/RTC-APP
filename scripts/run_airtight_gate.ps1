param(
    [switch]$SkipChecks,
    [switch]$SkipSmoke,
    [switch]$SkipStress
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
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
$pythonExe = $pythonCmd[0]
$pythonPrefixArgs = @()
if ($pythonCmd.Length -gt 1) {
    $pythonPrefixArgs = $pythonCmd[1..($pythonCmd.Length - 1)]
}

$args = @("scripts/run_airtight_gate.py")
if ($SkipChecks) { $args += "--skip-checks" }
if ($SkipSmoke) { $args += "--skip-smoke" }
if ($SkipStress) { $args += "--skip-stress" }

& $pythonExe @pythonPrefixArgs @args
exit $LASTEXITCODE

