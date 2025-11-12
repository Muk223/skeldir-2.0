# SKELDIR Frontend

Replit UI frontend application for Skeldir Attribution Intelligence.

## Structure

```
frontend/
├── src/               # Frontend source code
│   ├── components/    # React components
│   ├── generated/     # Generated API SDK
│   └── ...
├── public/            # Static assets
└── package.json       # Dependencies
```

## Status

**Note:** Frontend application code is not yet migrated. This directory structure is prepared for when frontend code is available.

## Development

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm start

# Run tests
npm test
```

## Contract-First Development

The frontend uses TypeScript SDKs generated from OpenAPI contracts:

```bash
# Generate SDK from contracts
npm run generate-sdk
```

SDK is generated in `frontend/src/generated/api/`.

## Mock Servers

For local development, use Prism mock servers:

```bash
# Start mock servers
make mocks-start
# or
./scripts/start-mocks.sh
```

**Service URLs:**
- Auth: `http://localhost:4010`
- Attribution: `http://localhost:4011`
- Reconciliation: `http://localhost:4012`
- Export: `http://localhost:4013`
- Health: `http://localhost:4014`

## Environment Variables

```bash
REACT_APP_API_URL=http://localhost:4011
REACT_APP_AUTH_API_URL=http://localhost:4010
REACT_APP_RECONCILIATION_API_URL=http://localhost:4012
REACT_APP_EXPORT_API_URL=http://localhost:4013
REACT_APP_HEALTH_API_URL=http://localhost:4014
```

## Testing

```bash
# Run unit tests
npm test

# Run integration tests (from root)
make tests-integration
```

## Documentation

- [Frontend Mock Integration](../docs/frontend-mock-integration.md)
- [Development Workflow](../docs/DEVELOPMENT_WORKFLOW.md)
- [Monorepo Structure](../docs/MONOREPO_STRUCTURE.md)

