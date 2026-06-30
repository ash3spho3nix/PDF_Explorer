Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root\..

if (Get-Command ruff -ErrorAction SilentlyContinue) {
    ruff check .
} else {
    Write-Error 'ruff not installed; please install ruff to run static checks'
    exit 1
}

if (Get-Command mypy -ErrorAction SilentlyContinue) {
    mypy .
} else {
    Write-Error 'mypy not installed; please install mypy to run type checks'
    exit 1
}

pytest tests/unit tests/integration --cov=.

$sampleDir = 'tests/integration/fixtures/sample_pdfs'
$outputReport = 'tests/integration/fixtures/generated_report.md'
$expectedReport = 'tests/integration/fixtures/expected_report.md'
python main.py run $sampleDir --report $outputReport

if (-Not (Test-Path $expectedReport)) {
    Write-Error "Expected report file missing: $expectedReport"
    exit 1
}

git diff --no-index -- "$expectedReport" "$outputReport"
if ($LASTEXITCODE -ne 0) {
    exit 1
}
