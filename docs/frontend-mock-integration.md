# SKELDIR 2.0 Mock Server Integration Guide

This guide enables frontend developers to consume SKELDIR mock APIs immediately, without waiting for backend implementation.

## Quick Start

### 1. Start Mock Servers

```bash
./scripts/start-mocks.sh
```

All 9 mock servers will start in the background. Verify with:

```bash
curl http://localhost:4014/api/health | jq
```

Expected output:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T14:30:00Z"
}
```

### 2. Stop Mock Servers

```bash
./scripts/stop-mocks.sh
```

## Service URLs

| Domain | Base URL | Port | Endpoints |
|--------|----------|------|-----------|
| Authentication | http://localhost:4010 | 4010 | `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout` |
| Attribution | http://localhost:4011 | 4011 | `/api/attribution/revenue/realtime` |
| Reconciliation | http://localhost:4012 | 4012 | `/api/reconciliation/status` |
| Export | http://localhost:4013 | 4013 | `/api/export/revenue` |
| Health | http://localhost:4014 | 4014 | `/api/health` |
| Webhooks (Shopify) | http://localhost:4015 | 4015 | `/webhooks/shopify/orders/create` |
| Webhooks (WooCommerce) | http://localhost:4016 | 4016 | `/webhooks/woocommerce/order/created` |
| Webhooks (Stripe) | http://localhost:4017 | 4017 | `/webhooks/stripe/charge/succeeded` |
| Webhooks (PayPal) | http://localhost:4018 | 4018 | `/webhooks/paypal/payment/sale/completed` |

**Note**: Webhook endpoints are for backend integration testing. Frontend applications typically do not consume webhooks directly.

## Environment Variables

Add these to your `.env` file or environment configuration:

```bash
REACT_APP_API_URL=http://localhost:4011
REACT_APP_AUTH_API_URL=http://localhost:4010
REACT_APP_RECONCILIATION_API_URL=http://localhost:4012
REACT_APP_EXPORT_API_URL=http://localhost:4013
REACT_APP_HEALTH_API_URL=http://localhost:4014
```

## SDK Configuration

### Base URL Setup

#### Using Fetch API

```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:4011';
const AUTH_BASE_URL = process.env.REACT_APP_AUTH_API_URL || 'http://localhost:4010';

// Generate correlation ID for each request
function generateCorrelationId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

async function apiRequest(endpoint, options = {}) {
  const correlationId = generateCorrelationId();
  const headers = {
    'Content-Type': 'application/json',
    'X-Correlation-ID': correlationId,
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  return response;
}
```

#### Using Axios

```javascript
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:4011';
const AUTH_BASE_URL = process.env.REACT_APP_AUTH_API_URL || 'http://localhost:4010';

// Generate correlation ID
function generateCorrelationId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

// Add X-Correlation-ID to all requests
apiClient.interceptors.request.use((config) => {
  config.headers['X-Correlation-ID'] = generateCorrelationId();
  return config;
});

export default apiClient;
```

### Error Handling

All error responses follow RFC7807 Problem schema with Skeldir extensions:

```typescript
interface ProblemResponse {
  type: string;           // URI identifying problem type
  title: string;          // Human-readable summary
  status: number;        // HTTP status code
  detail: string;        // Human-readable explanation
  error_id: string;      // UUID (Skeldir extension)
  correlation_id: string; // UUID from X-Correlation-ID header (Skeldir extension)
}
```

Example error handler:

```javascript
async function handleApiError(response) {
  if (!response.ok) {
    const problem = await response.json();
    console.error('API Error:', {
      errorId: problem.error_id,
      correlationId: problem.correlation_id,
      status: problem.status,
      detail: problem.detail,
    });
    throw new Error(problem.detail);
  }
  return response.json();
}
```

## Authentication Flow

### Login

```javascript
async function login(email, password) {
  const correlationId = generateCorrelationId();
  const response = await fetch(`${AUTH_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Correlation-ID': correlationId,
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const problem = await response.json();
    throw new Error(problem.detail);
  }

  const data = await response.json();
  // Store tokens
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  return data;
}
```

### Token Refresh

```javascript
async function refreshToken(refreshToken) {
  const correlationId = generateCorrelationId();
  const response = await fetch(`${AUTH_BASE_URL}/api/auth/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
      'X-Correlation-ID': correlationId,
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    const problem = await response.json();
    throw new Error(problem.detail);
  }

  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  return data;
}
```

### Logout

```javascript
async function logout() {
  const correlationId = generateCorrelationId();
  const accessToken = localStorage.getItem('access_token');
  
  await fetch(`${AUTH_BASE_URL}/api/auth/logout`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
      'X-Correlation-ID': correlationId,
    },
  });

  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}
```

### Error Handling

Handle 401 Unauthorized responses:

```javascript
async function apiRequestWithAuth(endpoint, options = {}) {
  let response = await apiRequest(endpoint, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    },
  });

  // Handle token expiration
  if (response.status === 401) {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        await refreshToken(refreshToken);
        // Retry original request
        response = await apiRequest(endpoint, {
          ...options,
          headers: {
            ...options.headers,
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
        });
      } catch (error) {
        // Refresh failed, redirect to login
        window.location.href = '/login';
        throw error;
      }
    } else {
      window.location.href = '/login';
      throw new Error('Authentication required');
    }
  }

  return response;
}
```

## Error Simulation

Use Prism's `Prefer` header to simulate different error scenarios for testing your error handlers:

### Simulate 401 Unauthorized

```javascript
const response = await fetch(`${API_BASE_URL}/api/attribution/revenue/realtime`, {
  headers: {
    'Authorization': 'Bearer valid-token',
    'X-Correlation-ID': generateCorrelationId(),
    'Prefer': 'code=401', // Simulate 401 error
  },
});
// Response will be 401 with RFC7807 Problem schema
```

### Simulate 429 Rate Limit

```javascript
const response = await fetch(`${API_BASE_URL}/api/attribution/revenue/realtime`, {
  headers: {
    'Authorization': 'Bearer valid-token',
    'X-Correlation-ID': generateCorrelationId(),
    'Prefer': 'code=429', // Simulate rate limiting
  },
});
// Response will be 429 with rate limit headers
```

### Simulate 500 Internal Server Error

```javascript
const response = await fetch(`${API_BASE_URL}/api/attribution/revenue/realtime`, {
  headers: {
    'Authorization': 'Bearer valid-token',
    'X-Correlation-ID': generateCorrelationId(),
    'Prefer': 'code=500', // Simulate server error
  },
});
// Response will be 500 with RFC7807 Problem schema
```

## Troubleshooting

### Check Service Status

```bash
docker-compose -f docker-compose.mock.yml ps
```

All services should show status "Up" (or "healthy" for services with healthchecks).

### View Logs

View logs for a specific service:

```bash
docker-compose -f docker-compose.mock.yml logs auth
```

View logs for all services:

```bash
docker-compose -f docker-compose.mock.yml logs
```

Follow logs in real-time:

```bash
docker-compose -f docker-compose.mock.yml logs -f auth
```

### Restart Service

Restart a specific service:

```bash
docker-compose -f docker-compose.mock.yml restart auth
```

Restart all services:

```bash
docker-compose -f docker-compose.mock.yml restart
```

Or use the convenience script:

```bash
./scripts/restart-mocks.sh auth
./scripts/restart-mocks.sh all
```

### Validate Contracts

Validate a specific contract file:

```bash
openapi-generator-cli validate -i api-contracts/openapi/v1/auth.yaml
```

### Common Errors

#### Port Conflicts

**Error**: `Bind for 0.0.0.0:4010 failed: port is already allocated`

**Solution**: 
1. Check what's using the port: `netstat -ano | findstr :4010` (Windows) or `lsof -i :4010` (macOS/Linux)
2. Stop the conflicting service or change the port in `docker-compose.mock.yml`

#### Docker Not Running

**Error**: `Cannot connect to the Docker daemon`

**Solution**: Start Docker Desktop or Docker daemon

#### Contract File Not Found

**Error**: `Error: Contract file not found`

**Solution**: 
1. Verify contract files exist: `ls api-contracts/openapi/v1/*.yaml`
2. Ensure you're running scripts from repository root

#### Service Not Responding

**Error**: `Connection refused` or `502 Bad Gateway`

**Solution**:
1. Check service status: `docker-compose -f docker-compose.mock.yml ps`
2. View service logs: `docker-compose -f docker-compose.mock.yml logs [service-name]`
3. Restart the service: `docker-compose -f docker-compose.mock.yml restart [service-name]`

### Expected Uptime

Mock servers should maintain 99.9% uptime during development sessions. If services crash frequently:

1. Check Docker resource limits (memory, CPU)
2. Review logs for errors: `docker-compose -f docker-compose.mock.yml logs`
3. Verify contract files are valid: `openapi-generator-cli validate -i api-contracts/openapi/v1/[domain].yaml`

### Health Check Status

Services with healthchecks (health, auth, attribution) should show "healthy" status:

```bash
docker-compose -f docker-compose.mock.yml ps
```

If a service shows "unhealthy":
1. Check logs: `docker-compose -f docker-compose.mock.yml logs [service-name]`
2. Verify endpoint is accessible: `curl http://localhost:[port]/api/health`
3. Restart the service: `docker-compose -f docker-compose.mock.yml restart [service-name]`

## Next Steps

- Review [API Contracts README](../api-contracts/README.md) for detailed endpoint documentation
- Check [Contributing Guide](../CONTRIBUTING.md) for contract-first development workflow
- See [Security Policy](../SECURITY.md) for security best practices











