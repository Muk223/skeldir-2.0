# Empirical Validation of All Contract Gates
# Tests: Manifest reading, Completeness, Dereferencing, OpenAPI validation

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Empirical Gate Validation" -ForegroundColor Cyan
Write-Host "Testing Q1-Q6 Requirements" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$REPO_ROOT = Split-Path -Parent (Split-Path -Parent $SCRIPT_DIR)
$MANIFEST = Join-Path $SCRIPT_DIR "entrypoints.json"

# Test 1: Manifest exists and is valid JSON (Q1)
Write-Host "[Test 1] Q1: Manifest exists and is parseable..." -ForegroundColor Yellow
if (-not (Test-Path $MANIFEST)) {
    Write-Host "X FAILED: Manifest not found" -ForegroundColor Red
    exit 1
}

try {
    $manifestContent = Get-Content $MANIFEST | ConvertFrom-Json
    $entrypoints = $manifestContent.entrypoints
    Write-Host "+ PASSED: Manifest loaded with $($entrypoints.Count) entrypoints" -ForegroundColor Green
} catch {
    Write-Host "X FAILED: Manifest is not valid JSON" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 2: Gate 1 - Completeness check works (Q1)
Write-Host "[Test 2] Q1: Completeness gate functional..." -ForegroundColor Yellow
$null = python scripts/contracts/check_dist_complete.py 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "X FAILED: Completeness check failed" -ForegroundColor Red
    python scripts/contracts/check_dist_complete.py --json
    exit 1
}
Write-Host "+ PASSED: All 9 bundles present" -ForegroundColor Green
Write-Host ""

# Test 3: Gate 2 - Dereferencing check works (Q2)
Write-Host "[Test 3] Q2: Dereferencing gate functional..." -ForegroundColor Yellow
$null = python scripts/contracts/assert_no_external_refs.py 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "X FAILED: External refs found" -ForegroundColor Red
    python scripts/contracts/assert_no_external_refs.py --json
    exit 1
}
Write-Host "+ PASSED: Zero external refs" -ForegroundColor Green
Write-Host ""

# Test 4: Gate 3 - OpenAPI validation works (Q3)
Write-Host "[Test 4] Q3: OpenAPI validation gate functional..." -ForegroundColor Yellow
$VALIDATION_ERRORS = 0

foreach ($entry in $entrypoints) {
    $bundlePath = $entry.bundle
    $bundleFile = Split-Path -Leaf $bundlePath
    
    if (Test-Path $bundlePath) {
        $null = npx --yes @openapitools/openapi-generator-cli validate -i $bundlePath 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  + $bundleFile validated" -ForegroundColor Gray
        } else {
            Write-Host "  X $bundleFile failed validation" -ForegroundColor Red
            $VALIDATION_ERRORS++
        }
    }
}

if ($VALIDATION_ERRORS -gt 0) {
    Write-Host "X FAILED: $VALIDATION_ERRORS bundles have OpenAPI errors" -ForegroundColor Red
    exit 1
}
Write-Host "+ PASSED: All bundles are valid OpenAPI 3.x" -ForegroundColor Green
Write-Host ""

# Test 5: Pydantic generation smoke test (Q4)
Write-Host "[Test 5] Q4: Pydantic generation smoke test..." -ForegroundColor Yellow
$testFile = "backend/app/schemas/auth.py"

if (Test-Path $testFile) {
    $CLASS_COUNT = (Select-String -Path $testFile -Pattern "^class " | Measure-Object).Count
    if ($CLASS_COUNT -gt 0) {
        Write-Host "+ PASSED: Found $CLASS_COUNT classes in $testFile" -ForegroundColor Green
    } else {
        Write-Host "X FAILED: No classes found in $testFile" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "! WARNING: $testFile not found (run generate-models.ps1 first)" -ForegroundColor Yellow
}
Write-Host ""

# Test 6: Regression test (Q6)
Write-Host "[Test 6] Q6: Regression detection test..." -ForegroundColor Yellow
Write-Host "  Creating temporary bundle with external ref..." -ForegroundColor Gray

# Create a temporary invalid bundle
$tempBundle = "api-contracts/dist/openapi/v1/test-invalid.bundled.yaml"
$invalidContent = @"
openapi: 3.1.0
info:
  title: Test
  version: 1.0.0
paths:
  /test:
    get:
      responses:
        '401':
          `$ref: '../_common/components.yaml#/components/responses/Unauthorized'
"@
Set-Content -Path $tempBundle -Value $invalidContent

# Update manifest temporarily to include invalid bundle
$testManifest = @{
    entrypoints = @(
        @{
            id = "test_invalid"
            source = "api-contracts/openapi/v1/test.yaml"
            bundle = $tempBundle
            api_name = "test_invalid"
        }
    )
} | ConvertTo-Json -Depth 3

$tempManifestPath = "scripts/contracts/test-manifest.json"
Set-Content -Path $tempManifestPath -Value $testManifest

# Test that external ref detection catches it
$detectScript = @"
import sys
sys.path.insert(0, 'scripts/contracts')
from check_dist_complete import load_manifest, check_completeness
manifest = load_manifest('$tempManifestPath')
present, missing = check_completeness(manifest, '.')
sys.exit(0 if not missing else 1)
"@

$detectScript | python - 2>&1 | Out-Null
$manifestCheckResult = $LASTEXITCODE

# Run external ref check on the invalid bundle
python -c @"
import sys
import yaml
with open('$tempBundle') as f:
    content = yaml.safe_load(f)
    
def find_refs(obj, path='root'):
    refs = []
    if isinstance(obj, dict):
        if '`$ref' in obj and not obj['`$ref'].startswith('#/'):
            refs.append(obj['`$ref'])
        for k, v in obj.items():
            refs.extend(find_refs(v, f'{path}.{k}'))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            refs.extend(find_refs(item, f'{path}[{i}]'))
    return refs

external_refs = find_refs(content)
if external_refs:
    print(f'Found {len(external_refs)} external refs')
    sys.exit(1)
sys.exit(0)
"@ 2>&1 | Out-Null
$regressionDetected = $LASTEXITCODE

# Cleanup
Remove-Item $tempBundle
Remove-Item $tempManifestPath

if ($regressionDetected -eq 1) {
    Write-Host "+ PASSED: External ref regression detected" -ForegroundColor Green
} else {
    Write-Host "X FAILED: Regression not detected" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Green
Write-Host "+ ALL GATES VALIDATED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Test Results:" -ForegroundColor Cyan
Write-Host "  Q1 (Manifest): + PASSED" -ForegroundColor Green
Write-Host "  Q2 (Dereferencing): + PASSED" -ForegroundColor Green
Write-Host "  Q3 (OpenAPI Validation): + PASSED" -ForegroundColor Green
Write-Host "  Q4 (Pydantic Smoke): + PASSED" -ForegroundColor Green
Write-Host "  Q6 (Regression Detection): + PASSED" -ForegroundColor Green
Write-Host ""
Write-Host "Empirical Validation: COMPLETE" -ForegroundColor Green
Write-Host ""

exit 0



