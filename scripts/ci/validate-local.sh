#!/usr/bin/env bash
# Local validation script that mirrors CI validation
set -e

echo "🔍 Running CI-equivalent validation locally..."

# Install dependencies if missing
if ! command -v spectral &> /dev/null; then
    echo "Installing Spectral CLI..."
    npm install -g @stoplight/spectral-cli
fi

if ! command -v redocly &> /dev/null; then
    echo "Installing Redocly CLI..."
    npm install -g @redocly/cli
fi

# Run full validation suite
echo "1. Linting contracts with Spectral..."
spectral lint api-contracts/openapi/v1/**/*.yaml --ruleset api-contracts/.spectral.yaml --fail-severity error

echo "2. Bundling contracts..."
bash scripts/contracts/bundle.sh

echo "3. Validating bundled artifacts..."
spectral lint api-contracts/dist/openapi/v1/*.yaml --ruleset api-contracts/.spectral.yaml --fail-severity error

echo "4. Validating canonical events..."
python scripts/governance/validate_canonical_events.py

echo "✅ All CI-equivalent validations passed locally"
