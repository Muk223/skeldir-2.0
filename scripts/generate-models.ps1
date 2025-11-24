# Pydantic Model Generation Script (PowerShell)
# Generates Pydantic v2 models from OpenAPI contracts using datamodel-code-generator

$ErrorActionPreference = "Stop"

# Configuration
$BUNDLED_DIR = "api-contracts/dist/openapi/v1"
$SCHEMAS_DIR = "backend/app/schemas"
$PYTHON_VERSION = "3.11"

Write-Host "Generating Pydantic models from bundled OpenAPI contracts..." -ForegroundColor Green

# Check if bundled files exist
if (-not (Test-Path $BUNDLED_DIR)) {
    Write-Host "Error: Bundled contracts not found in $BUNDLED_DIR" -ForegroundColor Red
    Write-Host "Please run scripts/contracts/bundle.ps1 first to generate bundled artifacts." -ForegroundColor Yellow
    exit 1
}

# Create schemas directory if it doesn't exist
New-Item -ItemType Directory -Force -Path $SCHEMAS_DIR | Out-Null

# Generate models for each domain contract
$domains = @("attribution", "auth", "reconciliation", "export")
$GENERATION_ERRORS = 0

foreach ($domain in $domains) {
    $BUNDLED_FILE = "$BUNDLED_DIR\$domain.bundled.yaml"
    if (Test-Path $BUNDLED_FILE) {
        Write-Host "Generating models from $domain.bundled.yaml..." -ForegroundColor Cyan
        $OUTPUT_FILE = "$SCHEMAS_DIR\$domain.py"
        
        try {
            python -m datamodel_code_generator --input $BUNDLED_FILE --output $OUTPUT_FILE --target-python-version $PYTHON_VERSION --use-annotated --use-standard-collections --use-schema-description --use-field-description --disable-timestamp --input-file-type openapi 2>&1 | Out-Null
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "X ERROR: Code generation failed for $domain" -ForegroundColor Red
                $GENERATION_ERRORS++
                continue
            }
            
            if (-not (Test-Path $OUTPUT_FILE)) {
                Write-Host "X ERROR: $OUTPUT_FILE was not created" -ForegroundColor Red
                $GENERATION_ERRORS++
                continue
            }
            
            $fileSize = (Get-Item $OUTPUT_FILE).Length
            if ($fileSize -lt 100) {
                Write-Host "X ERROR: $OUTPUT_FILE is too small ($fileSize bytes)" -ForegroundColor Red
                $GENERATION_ERRORS++
                continue
            }
            
            $CLASS_COUNT = (Select-String -Path $OUTPUT_FILE -Pattern "^class " | Measure-Object).Count
            if ($CLASS_COUNT -eq 0) {
                Write-Host "X ERROR: $OUTPUT_FILE contains no class definitions" -ForegroundColor Red
                $GENERATION_ERRORS++
                continue
            }
            
            Write-Host "+ Generated $OUTPUT_FILE with $CLASS_COUNT classes ($fileSize bytes)" -ForegroundColor Green
            
        } catch {
            Write-Host "X ERROR: Exception during generation for $domain : $_" -ForegroundColor Red
            $GENERATION_ERRORS++
        }
    } else {
        Write-Host "! Warning: $BUNDLED_FILE not found, skipping..." -ForegroundColor Yellow
    }
}

# Generate models for webhook contracts
$webhooks = @("shopify", "woocommerce", "stripe", "paypal")

foreach ($webhook in $webhooks) {
    $BUNDLED_FILE = "$BUNDLED_DIR\webhooks.$webhook.bundled.yaml"
    if (Test-Path $BUNDLED_FILE) {
        Write-Host "Generating models from webhooks.$webhook.bundled.yaml..." -ForegroundColor Cyan
        $OUTPUT_FILE = "$SCHEMAS_DIR\webhooks_$webhook.py"
        
        try {
            python -m datamodel_code_generator --input $BUNDLED_FILE --output $OUTPUT_FILE --target-python-version $PYTHON_VERSION --use-annotated --use-standard-collections --use-schema-description --use-field-description --disable-timestamp --input-file-type openapi 2>&1 | Out-Null
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "X ERROR: Code generation failed for webhooks_$webhook" -ForegroundColor Red
                $GENERATION_ERRORS++
                continue
            }
            
            if (-not (Test-Path $OUTPUT_FILE)) {
                Write-Host "X ERROR: $OUTPUT_FILE was not created" -ForegroundColor Red
                $GENERATION_ERRORS++
                continue
            }
            
            $fileSize = (Get-Item $OUTPUT_FILE).Length
            if ($fileSize -lt 100) {
                Write-Host "X ERROR: $OUTPUT_FILE is too small ($fileSize bytes)" -ForegroundColor Red
                $GENERATION_ERRORS++
                continue
            }
            
            $CLASS_COUNT = (Select-String -Path $OUTPUT_FILE -Pattern "^class " | Measure-Object).Count
            if ($CLASS_COUNT -eq 0) {
                Write-Host "X ERROR: $OUTPUT_FILE contains no class definitions" -ForegroundColor Red
                $GENERATION_ERRORS++
                continue
            }
            
            Write-Host "+ Generated $OUTPUT_FILE with $CLASS_COUNT classes ($fileSize bytes)" -ForegroundColor Green
            
        } catch {
            Write-Host "X ERROR: Exception during generation for webhooks_$webhook : $_" -ForegroundColor Red
            $GENERATION_ERRORS++
        }
    } else {
        Write-Host "! Warning: $BUNDLED_FILE not found, skipping..." -ForegroundColor Yellow
    }
}

# Summary
Write-Host "" 
Write-Host "========================================" -ForegroundColor White
if ($GENERATION_ERRORS -eq 0) {
    Write-Host "+ SUCCESS: Model generation completed!" -ForegroundColor Green
    Write-Host "Generated 8 Pydantic model files in $SCHEMAS_DIR" -ForegroundColor Green
    exit 0
} else {
    Write-Host "X FAILED: Model generation completed with $GENERATION_ERRORS errors" -ForegroundColor Red
    exit 1
}
