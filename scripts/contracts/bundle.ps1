# Manifest-Driven OpenAPI Contract Bundling Script (PowerShell)
# Single Source of Truth: scripts/contracts/entrypoints.json

$ErrorActionPreference = "Continue"

# Configuration
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$REPO_ROOT = Split-Path -Parent (Split-Path -Parent $SCRIPT_DIR)
$MANIFEST = Join-Path $SCRIPT_DIR "entrypoints.json"
$CONTRACTS_DIR = Join-Path $REPO_ROOT "api-contracts"

Write-Host "========================================" -ForegroundColor Green
Write-Host "Manifest-Driven Contract Bundling" -ForegroundColor Green
Write-Host "Source: $MANIFEST" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Validate manifest exists
if (-not (Test-Path $MANIFEST)) {
    Write-Host "ERROR: Manifest not found: $MANIFEST" -ForegroundColor Red
    exit 2
}

# Check dependencies
if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: npx not found. Install Node.js and npm." -ForegroundColor Red
    exit 2
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found." -ForegroundColor Red
    exit 2
}

# Load manifest
$manifestContent = Get-Content $MANIFEST | ConvertFrom-Json
$entrypoints = $manifestContent.entrypoints
$TOTAL_ENTRYPOINTS = $entrypoints.Count

Write-Host "[1/4] Bundling $TOTAL_ENTRYPOINTS contracts from manifest..." -ForegroundColor Green
Write-Host ""

# Bundle each entrypoint from manifest
Set-Location $CONTRACTS_DIR
$BUNDLE_ERRORS = 0

foreach ($entry in $entrypoints) {
    $apiName = $entry.api_name
    $bundlePath = $entry.bundle
    
    Write-Host "  Bundling $apiName..." -ForegroundColor Gray
    
    # Extract output path relative to api-contracts
    $bundleFile = Split-Path -Leaf $bundlePath
    $bundleDir = Split-Path -Parent $bundlePath
    $outputPath = $bundleDir.Replace("api-contracts/", "") + "/" + $bundleFile
    
    $null = npx @redocly/cli bundle $apiName --config=redocly.yaml --output=$outputPath --ext yaml --dereferenced 2>&1
    
    if (Test-Path $outputPath) {
        Write-Host "  + Bundled $bundleFile" -ForegroundColor Green
    } else {
        Write-Host "  X Failed to bundle $apiName" -ForegroundColor Red
        $BUNDLE_ERRORS++
    }
}

Set-Location $REPO_ROOT

if ($BUNDLE_ERRORS -gt 0) {
    Write-Host ""
    Write-Host "X Step 1 FAILED: $BUNDLE_ERRORS bundling errors" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "+ Step 1 PASSED: All contracts bundled from manifest" -ForegroundColor Green
Write-Host ""

# Gate 1: Validate completeness
Write-Host "[2/4] Gate 1: Validating bundle completeness..." -ForegroundColor Green
$null = python scripts/contracts/check_dist_complete.py 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "X Gate 1 FAILED: Bundle completeness check failed" -ForegroundColor Red
    python scripts/contracts/check_dist_complete.py --json
    exit 1
}
Write-Host "+ Gate 1 PASSED: All bundles present" -ForegroundColor Green
Write-Host ""

# Gate 2: Validate zero external refs
Write-Host "[3/4] Gate 2: Validating full dereferencing..." -ForegroundColor Green
$null = python scripts/contracts/assert_no_external_refs.py 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "X Gate 2 FAILED: External references found" -ForegroundColor Red
    python scripts/contracts/assert_no_external_refs.py --json
    exit 1
}
Write-Host "+ Gate 2 PASSED: Zero external refs (fully dereferenced)" -ForegroundColor Green
Write-Host ""

# Gate 3: OpenAPI semantic validation
Write-Host "[4/4] Gate 3: OpenAPI semantic validation..." -ForegroundColor Green
$VALIDATION_ERRORS = 0

foreach ($entry in $entrypoints) {
    $bundlePath = $entry.bundle
    $bundleFile = Split-Path -Leaf $bundlePath
    
    $null = npx @openapitools/openapi-generator-cli validate -i $bundlePath 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  + $bundleFile valid" -ForegroundColor Green
    } else {
        Write-Host "  X $bundleFile has validation errors" -ForegroundColor Red
        $VALIDATION_ERRORS++
    }
}

if ($VALIDATION_ERRORS -gt 0) {
    Write-Host ""
    Write-Host "X Gate 3 FAILED: $VALIDATION_ERRORS bundles have OpenAPI validation errors" -ForegroundColor Red
    exit 1
}

Write-Host "+ Gate 3 PASSED: All bundles are valid OpenAPI 3.x" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Green
Write-Host "+ BUNDLING COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Evidence:" -ForegroundColor Green
Write-Host "  - Bundled $TOTAL_ENTRYPOINTS contracts from manifest"
Write-Host "  - All bundles present (completeness validated)"
Write-Host "  - Zero external refs (fully dereferenced)"
Write-Host "  - All bundles are valid OpenAPI 3.x"
Write-Host ""
Write-Host "Manifest-Driven: VALIDATED" -ForegroundColor Green
Write-Host ""

exit 0
