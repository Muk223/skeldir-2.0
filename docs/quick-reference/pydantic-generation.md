# Pydantic Model Generation Quick Reference

## Regenerate Models

```bash
bash scripts/contracts/bundle.sh
bash scripts/generate-models.sh
```

## Validate Models

```bash
python scripts/validate_model_usage.py
cd backend && pytest tests/test_generated_models.py
```

## Expected Artifacts

- **Bundled Contracts**: `api-contracts/dist/openapi/v1/*.bundled.yaml` (9 files)
- **Generated Models**: `backend/app/schemas/*.py` (8 files)
- **Critical Classes**:
  - `attribution.py`: RealtimeRevenueResponse
  - `auth.py`: LoginRequest, LoginResponse, RefreshRequest, RefreshResponse
  - `reconciliation.py`: ReconciliationStatusResponse
  - `export.py`: ExportRevenueResponse
  - `webhooks_*.py`: Platform-specific request/response models

## Troubleshooting

**Problem**: Generation produces placeholder files

**Solution**: Check that DTOs are in `components/schemas`, not inline

**Problem**: CI fails with "no class definitions"

**Solution**: Verify bundled contracts contain schemas (check dereferencing)

**Problem**: Import error on generated model

**Solution**: Check for unsupported OpenAPI constructs (hyper-nested allOf/oneOf)



