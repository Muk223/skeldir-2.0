# Skeldir Multi-Process Orchestration - Phase D Runtime Infrastructure
# Replit-native process management for coordinated service execution
#
# Service Architecture:
#   - db: PostgreSQL database (port 5432, unix socket)
#   - queue: Redis task queue (port 6379)
#   - web: FastAPI application (port 8000)
#   - worker: Celery background worker
#   - mocks: Prism contract mock servers (ports 4010+)
#
# Usage:
#   - Replit: Automatically started
#   - Local: overmind start (or foreman start)
#   - Mocks only: bash scripts/start-mocks.sh

# Core Services
db: postgres -D $PGDATA -k $PGSOCKET -h localhost -p 5432
queue: redis-server --port 6379 --bind 127.0.0.1
web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
worker: cd backend && celery -A app.tasks worker --loglevel=info

# Mock Servers (Contract-First Development)
mock_auth: prism mock api-contracts/dist/openapi/v1/auth.bundled.yaml -p 4010 -h 0.0.0.0
mock_attribution: prism mock api-contracts/dist/openapi/v1/attribution.bundled.yaml -p 4011 -h 0.0.0.0
mock_health: prism mock api-contracts/dist/openapi/v1/health.bundled.yaml -p 4012 -h 0.0.0.0

