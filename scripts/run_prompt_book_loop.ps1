param(
    [int]$Iterations = 100,
    [double]$Sleep = 0,
    [double]$TargetX = 100,
    [int]$MaxCycles = 12,
    [int]$MaxMinutes = 180,
    [string]$Model = "",
    [ValidateSet("strict", "compat")]
    [string]$Profile = "strict",
    [int]$UpgradeTarget = 10,
    [ValidateSet("local", "cloud", "hybrid")]
    [string]$Dev3Mode = "local",
    [ValidateSet("strict", "balanced")]
    [string]$Dev4Policy = "strict",
    [ValidateSet("primary_docs", "broad_web", "local_only")]
    [string]$ResearchPolicy = "primary_docs",
    [ValidateSet("standard", "extended")]
    [string]$DebugPack = "standard",
    [int]$MaxRevisionAttempts = 1,
    [switch]$DryRun,
    [switch]$DevStackV2,
    [switch]$Dev7BlockOnSafety,
    [switch]$Dev8RequireReleasePass,
    [switch]$Autocommit,
    [switch]$AllowDocEdits,
    [string]$Output = "",
    [string]$PromptBook = "",
    [string]$ResumeRunId = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Resolve-PythonCommand {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return ,@("python")
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return ,@("py", "-3")
    }
    throw "Python was not found. Install Python 3 and ensure it is on PATH."
}

$pythonCmd = Resolve-PythonCommand
$pythonExe = $pythonCmd[0]
$pythonPrefixArgs = @()
if ($pythonCmd.Length -gt 1) {
    $pythonPrefixArgs = $pythonCmd[1..($pythonCmd.Length - 1)]
}

$args = @(
    "scripts/run_prompt_book_loop.py",
    "--iterations", "$Iterations",
    "--sleep", "$Sleep",
    "--target-x", "$TargetX",
    "--max-cycles", "$MaxCycles",
    "--max-minutes", "$MaxMinutes",
    "--profile", "$Profile",
    "--upgrade-target", "$UpgradeTarget",
    "--dev3-mode", "$Dev3Mode",
    "--dev4-policy", "$Dev4Policy",
    "--research-policy", "$ResearchPolicy",
    "--debug-pack", "$DebugPack",
    "--max-revision-attempts", "$MaxRevisionAttempts"
)
if ($Model) { $args += @("--model", $Model) }
if ($DryRun) { $args += "--dry-run" }
if ($DevStackV2) { $args += "--dev-stack-v2" }
if ($Dev7BlockOnSafety) { $args += "--dev7-block-on-safety" }
if ($Dev8RequireReleasePass) { $args += "--dev8-require-release-pass" }
if ($Autocommit) { $args += "--autocommit" }
if ($AllowDocEdits) { $args += "--allow-doc-edits" }
if ($Output) { $args += @("--output", $Output) }
if ($PromptBook) { $args += @("--prompt-book", $PromptBook) }
if ($ResumeRunId) { $args += @("--resume-run-id", $ResumeRunId) }

& $pythonExe @pythonPrefixArgs @args
exit $LASTEXITCODE
