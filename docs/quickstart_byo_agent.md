# BYO-Agent Quickstart Guide

**Goal: Onboard your agent in under 2 hours**

This guide provides everything you need to integrate your custom agent with the Provability Fabric Testbed. Follow the steps below to complete a full end-to-end journey.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Setup (5 minutes)](#quick-setup-5-minutes)
3. [Create Sandbox Tenant (10 minutes)](#create-sandbox-tenant-10-minutes)
4. [Generate API Keys (5 minutes)](#generate-api-keys-5-minutes)
5. [Configure Rate Limits (5 minutes)](#configure-rate-limits-5-minutes)
6. [Implement PF-Sig Middleware (30 minutes)](#implement-pf-sig-middleware-30-minutes)
7. [Test Your Integration (15 minutes)](#test-your-integration-15-minutes)
8. [Production Deployment (30 minutes)](#production-deployment-30-minutes)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

- **Node.js 18+** or **Python 3.11+**
- **cURL** for API testing
- **Git** for cloning examples
- Basic understanding of REST APIs and middleware

## Quick Setup (5 minutes)

### 1. Clone the Examples Repository

```bash
git clone https://github.com/your-org/pf-testbed-examples.git
cd pf-testbed-examples/byo-agent
```

### 2. Install Dependencies

**Node.js:**
```bash
npm install
```

**Python:**
```bash
pip install -r requirements.txt
```

## Create Sandbox Tenant (10 minutes)

### API Endpoint
```
POST /api/v1/tenants/sandbox
```

### cURL Example
```bash
curl -X POST "https://api.pf-testbed.com/api/v1/tenants/sandbox" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "tenant_name": "my-company-sandbox",
    "description": "Sandbox environment for testing",
    "max_requests_per_hour": 1000,
    "features": ["data_access", "model_inference", "audit_logs"],
    "expiry_days": 30
  }'
```

### Response
```json
{
  "tenant_id": "tenant_abc123",
  "tenant_name": "my-company-sandbox",
  "status": "active",
  "created_at": "2024-12-01T10:00:00Z",
  "expires_at": "2024-12-31T10:00:00Z",
  "rate_limits": {
    "requests_per_hour": 1000,
    "requests_per_day": 10000
  },
  "features": ["data_access", "model_inference", "audit_logs"]
}
```

### TypeScript Example
```typescript
interface CreateTenantRequest {
  tenant_name: string;
  description: string;
  max_requests_per_hour: number;
  features: string[];
  expiry_days: number;
}

interface TenantResponse {
  tenant_id: string;
  tenant_name: string;
  status: string;
  created_at: string;
  expires_at: string;
  rate_limits: {
    requests_per_hour: number;
    requests_per_day: number;
  };
  features: string[];
}

async function createSandboxTenant(request: CreateTenantRequest): Promise<TenantResponse> {
  const response = await fetch('https://api.pf-testbed.com/api/v1/tenants/sandbox', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.PF_ADMIN_TOKEN}`
    },
    body: JSON.stringify(request)
  });

  if (!response.ok) {
    throw new Error(`Failed to create tenant: ${response.statusText}`);
  }

  return response.json();
}

// Usage
const tenant = await createSandboxTenant({
  tenant_name: 'my-company-sandbox',
  description: 'Sandbox environment for testing',
  max_requests_per_hour: 1000,
  features: ['data_access', 'model_inference', 'audit_logs'],
  expiry_days: 30
});

console.log('Tenant created:', tenant.tenant_id);
```

## Generate API Keys (5 minutes)

### API Endpoint
```
POST /api/v1/tenants/{tenant_id}/keys
```

### cURL Example
```bash
curl -X POST "https://api.pf-testbed.com/api/v1/tenants/tenant_abc123/keys" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "key_name": "production-key",
    "permissions": ["read", "write", "execute"],
    "expiry_days": 365
  }'
```

### Response
```json
{
  "key_id": "key_xyz789",
  "api_key": "pf_live_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz",
  "key_name": "production-key",
  "permissions": ["read", "write", "execute"],
  "created_at": "2024-12-01T10:05:00Z",
  "expires_at": "2025-12-01T10:05:00Z",
  "last_used": null
}
```

### TypeScript Example
```typescript
interface CreateApiKeyRequest {
  key_name: string;
  permissions: string[];
  expiry_days: number;
}

interface ApiKeyResponse {
  key_id: string;
  api_key: string;
  key_name: string;
  permissions: string[];
  created_at: string;
  expires_at: string;
  last_used: string | null;
}

async function createApiKey(tenantId: string, request: CreateApiKeyRequest): Promise<ApiKeyResponse> {
  const response = await fetch(`https://api.pf-testbed.com/api/v1/tenants/${tenantId}/keys`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.PF_ADMIN_TOKEN}`
    },
    body: JSON.stringify(request)
  });

  if (!response.ok) {
    throw new Error(`Failed to create API key: ${response.statusText}`);
  }

  return response.json();
}

// Usage
const apiKey = await createApiKey('tenant_abc123', {
  key_name: 'production-key',
  permissions: ['read', 'write', 'execute'],
  expiry_days: 365
});

console.log('API Key created:', apiKey.key_id);
console.log('API Key:', apiKey.api_key);
```

## Configure Rate Limits (5 minutes)

### API Endpoint
```
PUT /api/v1/tenants/{tenant_id}/rate-limits
```

### cURL Example
```bash
curl -X PUT "https://api.pf-testbed.com/api/v1/tenants/tenant_abc123/rate-limits" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "requests_per_second": 10,
    "requests_per_minute": 100,
    "requests_per_hour": 1000,
    "requests_per_day": 10000,
    "burst_size": 50
  }'
```

### Response
```json
{
  "tenant_id": "tenant_abc123",
  "rate_limits": {
    "requests_per_second": 10,
    "requests_per_minute": 100,
    "requests_per_hour": 1000,
    "requests_per_day": 10000,
    "burst_size": 50
  },
  "updated_at": "2024-12-01T10:10:00Z"
}
```

### TypeScript Example
```typescript
interface RateLimitRequest {
  requests_per_second: number;
  requests_per_minute: number;
  requests_per_hour: number;
  requests_per_day: number;
  burst_size: number;
}

interface RateLimitResponse {
  tenant_id: string;
  rate_limits: RateLimitRequest;
  updated_at: string;
}

async function updateRateLimits(tenantId: string, rateLimits: RateLimitRequest): Promise<RateLimitResponse> {
  const response = await fetch(`https://api.pf-testbed.com/api/v1/tenants/${tenantId}/rate-limits`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.PF_ADMIN_TOKEN}`
    },
    body: JSON.stringify(rateLimits)
  });

  if (!response.ok) {
    throw new Error(`Failed to update rate limits: ${response.statusText}`);
  }

  return response.json();
}

// Usage
const rateLimits = await updateRateLimits('tenant_abc123', {
  requests_per_second: 10,
  requests_per_minute: 100,
  requests_per_hour: 1000,
  requests_per_day: 10000,
  burst_size: 50
});

console.log('Rate limits updated:', rateLimits);
```

## Implement PF-Sig Middleware (30 minutes)

### Node.js/Express Middleware

```typescript
import { Request, Response, NextFunction } from 'express';
import crypto from 'crypto';

interface PFRequest extends Request {
  pfSignature?: string;
  pfTimestamp?: string;
  pfNonce?: string;
}

interface PFConfig {
  apiKey: string;
  tenantId: string;
  secretKey: string;
}

class PFMiddleware {
  private config: PFConfig;

  constructor(config: PFConfig) {
    this.config = config;
  }

  // Generate PF-Sig header
  private generateSignature(payload: string, timestamp: string, nonce: string): string {
    const message = `${this.config.tenantId}:${timestamp}:${nonce}:${payload}`;
    const hmac = crypto.createHmac('sha256', this.config.secretKey);
    hmac.update(message);
    return hmac.digest('hex');
  }

  // Add PF-Sig headers to request
  addSignature(req: PFRequest, res: Response, next: NextFunction): void {
    const timestamp = Date.now().toString();
    const nonce = crypto.randomBytes(16).toString('hex');
    const payload = JSON.stringify(req.body || {});
    
    const signature = this.generateSignature(payload, timestamp, nonce);
    
    req.pfSignature = signature;
    req.pfTimestamp = timestamp;
    req.pfNonce = nonce;
    
    // Add headers to response for client
    res.set({
      'X-PF-Signature': signature,
      'X-PF-Timestamp': timestamp,
      'X-PF-Nonce': nonce,
      'X-PF-Tenant-ID': this.config.tenantId
    });
    
    next();
  }

  // Verify PF-Sig headers
  verifySignature(req: PFRequest, res: Response, next: NextFunction): void {
    const signature = req.headers['x-pf-signature'] as string;
    const timestamp = req.headers['x-pf-timestamp'] as string;
    const nonce = req.headers['x-pf-nonce'] as string;
    const tenantId = req.headers['x-pf-tenant-id'] as string;
    
    if (!signature || !timestamp || !nonce || !tenantId) {
      return res.status(401).json({ error: 'Missing PF-Sig headers' });
    }
    
    // Verify tenant ID
    if (tenantId !== this.config.tenantId) {
      return res.status(403).json({ error: 'Invalid tenant ID' });
    }
    
    // Verify timestamp (within 5 minutes)
    const requestTime = parseInt(timestamp);
    const currentTime = Date.now();
    if (Math.abs(currentTime - requestTime) > 5 * 60 * 1000) {
      return res.status(401).json({ error: 'Request timestamp expired' });
    }
    
    // Verify signature
    const payload = JSON.stringify(req.body || {});
    const expectedSignature = this.generateSignature(payload, timestamp, nonce);
    
    if (signature !== expectedSignature) {
      return res.status(401).json({ error: 'Invalid signature' });
    }
    
    next();
  }

  // Add receipt headers
  addReceipt(req: PFRequest, res: Response, next: NextFunction): void {
    const receiptId = crypto.randomBytes(16).toString('hex');
    const timestamp = Date.now().toString();
    
    res.set({
      'X-PF-Receipt-ID': receiptId,
      'X-PF-Receipt-Timestamp': timestamp,
      'X-PF-Receipt-Hash': crypto.createHash('sha256').update(receiptId + timestamp).digest('hex')
    });
    
    next();
  }
}

// Usage in Express app
const pfMiddleware = new PFMiddleware({
  apiKey: process.env.PF_API_KEY!,
  tenantId: process.env.PF_TENANT_ID!,
  secretKey: process.env.PF_SECRET_KEY!
});

app.use('/api', pfMiddleware.addSignature.bind(pfMiddleware));
app.use('/api', pfMiddleware.verifySignature.bind(pfMiddleware));
app.use('/api', pfMiddleware.addReceipt.bind(pfMiddleware));
```

### Python/Flask Middleware

```python
import hashlib
import hmac
import json
import os
import time
import uuid
from functools import wraps
from flask import Flask, request, g
from typing import Dict, Any

class PFMiddleware:
    def __init__(self, config: Dict[str, str]):
        self.config = config
    
    def generate_signature(self, payload: str, timestamp: str, nonce: str) -> str:
        """Generate PF-Sig header"""
        message = f"{self.config['tenant_id']}:{timestamp}:{nonce}:{payload}"
        signature = hmac.new(
            self.config['secret_key'].encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def add_signature(self, f):
        """Decorator to add PF-Sig headers"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            timestamp = str(int(time.time() * 1000))
            nonce = uuid.uuid4().hex
            payload = json.dumps(request.get_json() or {})
            
            signature = self.generate_signature(payload, timestamp, nonce)
            
            # Store in request context
            g.pf_signature = signature
            g.pf_timestamp = timestamp
            g.pf_nonce = nonce
            
            # Add headers to response
            response = f(*args, **kwargs)
            response.headers['X-PF-Signature'] = signature
            response.headers['X-PF-Timestamp'] = timestamp
            response.headers['X-PF-Nonce'] = nonce
            response.headers['X-PF-Tenant-ID'] = self.config['tenant_id']
            
            return response
        return decorated_function
    
    def verify_signature(self, f):
        """Decorator to verify PF-Sig headers"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            signature = request.headers.get('X-PF-Signature')
            timestamp = request.headers.get('X-PF-Timestamp')
            nonce = request.headers.get('X-PF-Nonce')
            tenant_id = request.headers.get('X-PF-Tenant-ID')
            
            if not all([signature, timestamp, nonce, tenant_id]):
                return {'error': 'Missing PF-Sig headers'}, 401
            
            # Verify tenant ID
            if tenant_id != self.config['tenant_id']:
                return {'error': 'Invalid tenant ID'}, 403
            
            # Verify timestamp (within 5 minutes)
            request_time = int(timestamp)
            current_time = int(time.time() * 1000)
            if abs(current_time - request_time) > 5 * 60 * 1000:
                return {'error': 'Request timestamp expired'}, 401
            
            # Verify signature
            payload = json.dumps(request.get_json() or {})
            expected_signature = self.generate_signature(payload, timestamp, nonce)
            
            if signature != expected_signature:
                return {'error': 'Invalid signature'}, 401
            
            return f(*args, **kwargs)
        return decorated_function
    
    def add_receipt(self, f):
        """Decorator to add receipt headers"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            receipt_id = uuid.uuid4().hex
            timestamp = str(int(time.time() * 1000))
            receipt_hash = hashlib.sha256(f"{receipt_id}{timestamp}".encode()).hexdigest()
            
            response = f(*args, **kwargs)
            response.headers['X-PF-Receipt-ID'] = receipt_id
            response.headers['X-PF-Receipt-Timestamp'] = timestamp
            response.headers['X-PF-Receipt-Hash'] = receipt_hash
            
            return response
        return decorated_function

# Usage in Flask app
app = Flask(__name__)

pf_middleware = PFMiddleware({
    'api_key': os.environ['PF_API_KEY'],
    'tenant_id': os.environ['PF_TENANT_ID'],
    'secret_key': os.environ['PF_SECRET_KEY']
})

@app.route('/api/test', methods=['POST'])
@pf_middleware.add_signature
@pf_middleware.verify_signature
@pf_middleware.add_receipt
def test_endpoint():
    return {'message': 'PF-Sig middleware working!'}
```

## Test Your Integration (15 minutes)

### 1. Test Basic Authentication

```bash
curl -X POST "https://api.pf-testbed.com/api/v1/test" \
  -H "Content-Type: application/json" \
  -H "X-PF-Signature: YOUR_SIGNATURE" \
  -H "X-PF-Timestamp: $(date +%s)000" \
  -H "X-PF-Nonce: $(openssl rand -hex 16)" \
  -H "X-PF-Tenant-ID: tenant_abc123" \
  -d '{"test": "data"}'
```

### 2. Test Rate Limiting

```bash
# Make multiple requests to test rate limiting
for i in {1..15}; do
  curl -X POST "https://api.pf-testbed.com/api/v1/test" \
    -H "Content-Type: application/json" \
    -H "X-PF-Signature: YOUR_SIGNATURE" \
    -H "X-PF-Timestamp: $(date +%s)000" \
    -H "X-PF-Nonce: $(openssl rand -hex 16)" \
    -H "X-PF-Tenant-ID: tenant_abc123" \
    -d "{\"request_number\": $i}"
  echo "Request $i completed"
  sleep 0.1
done
```

### 3. Test Receipt Generation

```bash
response=$(curl -s -X POST "https://api.pf-testbed.com/api/v1/test" \
  -H "Content-Type: application/json" \
  -H "X-PF-Signature: YOUR_SIGNATURE" \
  -H "X-PF-Timestamp: $(date +%s)000" \
  -H "X-PF-Nonce: $(openssl rand -hex 16)" \
  -H "X-PF-Tenant-ID: tenant_abc123" \
  -d '{"test": "receipt"}')

echo "Response: $response"
echo "Receipt ID: $(echo $response | jq -r '.receipt_id')"
```

## Production Deployment (30 minutes)

### 1. Environment Configuration

Create `.env` file:
```bash
PF_API_KEY=pf_live_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
PF_TENANT_ID=tenant_abc123
PF_SECRET_KEY=your_secret_key_here
PF_ENVIRONMENT=production
PF_LOG_LEVEL=info
```

### 2. Health Check Endpoint

```typescript
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: process.env.npm_package_version || '1.0.0',
    environment: process.env.PF_ENVIRONMENT || 'development'
  });
});
```

### 3. Error Handling

```typescript
app.use((error: Error, req: Request, res: Response, next: NextFunction) => {
  console.error('Error:', error);
  
  res.status(500).json({
    error: 'Internal server error',
    timestamp: new Date().toISOString(),
    request_id: req.headers['x-request-id'] || 'unknown'
  });
});
```

### 4. Logging

```typescript
import winston from 'winston';

const logger = winston.createLogger({
  level: process.env.PF_LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'pf-agent.log' })
  ]
});

// Log all PF requests
app.use((req: Request, res: Response, next: NextFunction) => {
  logger.info('PF Request', {
    method: req.method,
    url: req.url,
    tenant_id: req.headers['x-pf-tenant-id'],
    timestamp: req.headers['x-pf-timestamp'],
    user_agent: req.headers['user-agent']
  });
  next();
});
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check API key and signature generation
2. **403 Forbidden**: Verify tenant ID and permissions
3. **429 Too Many Requests**: Check rate limits and burst settings
4. **500 Internal Server Error**: Verify request format and middleware setup

### Debug Mode

Enable debug logging:
```bash
export PF_LOG_LEVEL=debug
```

---

**Time to Complete**: ~2 hours  
**Difficulty**: Beginner to Intermediate  
**Support**: Available via email and community forums
