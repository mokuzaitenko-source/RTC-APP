param(
    [string]$Root = (Get-Location).Path,
    [string]$OutputDir = "output/archive",
    [string]$ReportName = "archive_report.json"
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$targetDir = Join-Path $Root (Join-Path $OutputDir $timestamp)
$reportPath = Join-Path $targetDir $ReportName

$files = @(
    ".env.example",
    ".gitignore",
    ".markdownlint.json",
    "10 Advanced Prompt Engineering Techniques for Coding Tasks (1).docx",
    "ACA_v4_Module_Documentation_Plan.md",
    "aca_v4_updated_pdfs.zip",
    "all caht.txt",
    "oversight_state.db",
    "Plan for Regenerating ACA v4 Module Documentation (1).pdf",
    "Plan to Modernize the Flask Learning App and Integrate ACA v4.pdf",
    "README.md",
    "requirements.txt",
    "run_prompt_book_loop.bat",
    "run_quality_gate.bat",
    "SESSION_HANDOFF.md",
    "start_app.bat",
    "start_app.ps1",
    "tmp_docx_sections.txt",
    "tmp_snip.txt"
)

New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

$copied = @()
$missing = @()

foreach ($relPath in $files) {
    $source = Join-Path $Root $relPath
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination $targetDir -Force
        $copied += $relPath
    } else {
        $missing += $relPath
    }
}

$report = [ordered]@{
    timestamp = $timestamp
    root = $Root
    target = $targetDir
    copied = $copied
    missing = $missing
}
$report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Output "Archive target: $targetDir"
Write-Output "Copied: $($copied.Count)"
if ($missing.Count -gt 0) {
    Write-Output "Missing: $($missing.Count)"
    $missing | ForEach-Object { Write-Output "- $_" }
}
Write-Output "Report: $reportPath"
