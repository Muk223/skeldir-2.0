#!/usr/bin/env bash
# Bundles OpenAPI specs into api-contracts/dist/openapi/v1 for CI workflows.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_DIR="$REPO_ROOT/api-contracts/openapi/v1"
DIST_DIR="$REPO_ROOT/api-contracts/dist/openapi/v1"

log() {
    printf '[bundle] %s\n' "$1"
}

log "Preparing output directory: $DIST_DIR"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

shopt -s nullglob
contracts=("$SOURCE_DIR"/*.yaml)
if (( ${#contracts[@]} == 0 )); then
    log "No OpenAPI files were found under $SOURCE_DIR"
    exit 1
fi

for contract in "${contracts[@]}"; do
    filename=$(basename "$contract")
    log "Copying $filename"
    cp "$contract" "$DIST_DIR/$filename"
    # Normalize to LF endings to keep diffs stable
    if command -v dos2unix >/dev/null 2>&1; then
        dos2unix "$DIST_DIR/$filename" >/dev/null 2>&1 || true
    fi
    log "✓ $filename"
done

# Copy _common directory if it exists
if [ -d "$SOURCE_DIR/_common" ]; then
    log "Copying _common directory"
    cp -r "$SOURCE_DIR/_common" "$DIST_DIR/_common"
    log "✓ _common directory"
fi

log "All OpenAPI contracts copied successfully."
log "Artifacts ready under api-contracts/dist/openapi/v1/."
