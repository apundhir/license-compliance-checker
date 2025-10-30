# License Compliance Checker - API Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Authentication](#authentication)
4. [Scan Endpoints](#scan-endpoints)
5. [Policy Endpoints](#policy-endpoints)
6. [Dashboard Endpoints](#dashboard-endpoints)
7. [SBOM Endpoints](#sbom-endpoints)
8. [User Management](#user-management)
9. [Error Handling](#error-handling)
10. [Rate Limiting](#rate-limiting)
11. [Programmatic API](#programmatic-api)
12. [Examples](#examples)

---

## Introduction

The License Compliance Checker REST API provides programmatic access to all LCC functionality. Built with FastAPI, it offers:

- **OpenAPI 3.0 documentation** at `/docs` (Swagger UI) and `/redoc` (ReDoc)
- **JWT-based authentication** with access and refresh tokens
- **Role-based access control** (RBAC) with admin and user roles
- **Rate limiting** (100 requests/minute per endpoint)
- **CORS support** for cross-origin requests
- **GitHub repository scanning** via API
- **Real-time scan results** with detailed reports

### API Specifications

- **Base URL**: `http://localhost:8000` (default)
- **Protocol**: HTTP/HTTPS
- **Format**: JSON
- **Authentication**: Bearer Token (JWT)
- **API Version**: 0.1.0

---

## Getting Started

### Starting the API Server

#### Method 1: Docker Compose (Recommended)

```bash
# Start API and Dashboard together
docker-compose up -d

# API available at: http://localhost:8000
# Dashboard available at: http://localhost:3000
```

#### Method 2: Direct Python

```bash
# Start API server
lcc server

# Or with custom configuration
lcc server --host 0.0.0.0 --port 8000 --reload
```

### Interactive API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Quick Test

```bash
# Health check (no auth required)
curl http://localhost:8000/health

# Expected response:
{"status": "ok"}
```

---

## Authentication

All endpoints (except `/health`) require JWT authentication.

### 1. Create Admin User (First Time Only)

```bash
# Using CLI
lcc auth create-user admin password123 --role admin --email admin@company.com

# Or via Docker
docker-compose exec api lcc auth create-user admin password123 --role admin
```

### 2. Login to Get Access Token

**Endpoint**: `POST /auth/login`

**Request**:
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=password123"
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1440
}
```

### 3. Use Access Token

Include the token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  http://localhost:8000/scans
```

### Token Management

#### Access Tokens
- **Lifetime**: 24 hours (1440 minutes)
- **Usage**: Include in `Authorization: Bearer <token>` header
- **Scope**: Full API access based on user role

#### Refresh Tokens
- **Lifetime**: 7 days
- **Usage**: Get new access token without re-login
- **Endpoint**: `POST /auth/refresh`

**Refresh Example**:
```bash
curl -X POST "http://localhost:8000/auth/refresh" \
  -H "Authorization: Bearer <refresh_token>"
```

### API Keys (Alternative to Tokens)

Create long-lived API keys for CI/CD and automation:

```bash
# Create API key
lcc auth create-key --name "CI Pipeline" --role user --expires-days 365

# Response:
# API Key created:
#   Key ID: api_key_abc123
#   API Key: lcc_live_xyz789... (save this securely)
```

Use API key in Authorization header:
```bash
curl -H "Authorization: Bearer lcc_live_xyz789..." \
  http://localhost:8000/scans
```

---

## Scan Endpoints

### List Scans

**Endpoint**: `GET /scans`

**Description**: List all scans (most recent first, limit 100)

**Authentication**: Required

**Rate Limit**: 100/minute

**Request**:
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/scans
```

**Response**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "project": "my-project",
    "status": "pass",
    "violations": 0,
    "warnings": 2,
    "generatedAt": "2024-10-30T10:00:00Z",
    "durationSeconds": 12.5,
    "reportUrl": "/scans/550e8400-e29b-41d4-a716-446655440000"
  }
]
```

**Status Values**:
- `pass`: No violations or warnings
- `warning`: Has warnings but no violations
- `violation`: Has policy violations

### Get Scan Details

**Endpoint**: `GET /scans/{scan_id}`

**Description**: Get detailed scan results including all findings

**Authentication**: Required

**Rate Limit**: 100/minute

**Request**:
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/scans/550e8400-e29b-41d4-a716-446655440000
```

**Response**:
```json
{
  "summary": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "project": "my-project",
    "status": "pass",
    "violations": 0,
    "warnings": 2,
    "generatedAt": "2024-10-30T10:00:00Z",
    "durationSeconds": 12.5,
    "reportUrl": "/scans/550e8400-e29b-41d4-a716-446655440000"
  },
  "report": {
    "findings": [
      {
        "component": {
          "name": "requests",
          "version": "2.31.0",
          "type": "pypi"
        },
        "resolved_license": "Apache-2.0",
        "status": "pass",
        "sources": ["pypi", "github"]
      }
    ],
    "summary": {
      "componentCount": 42,
      "violations": 0,
      "warnings": 2,
      "licenseDistribution": [
        {"license": "Apache-2.0", "count": 15},
        {"license": "MIT", "count": 20},
        {"license": "UNKNOWN", "count": 2}
      ]
    }
  }
}
```

### Create Scan (Local Path)

**Endpoint**: `POST /scans`

**Description**: Scan a local filesystem path

**Authentication**: Required

**Request Body**:
```json
{
  "path": "/path/to/project",
  "policy": "permissive",
  "context": "production",
  "exclude": ["node_modules", "*.pyc"]
}
```

**Request**:
```bash
curl -X POST "http://localhost:8000/scans" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/Users/john/my-project",
    "policy": "permissive",
    "context": "production"
  }'
```

**Response**: Same as GET /scans/{scan_id} summary

### Create Scan (GitHub Repository)

**Endpoint**: `POST /scans`

**Description**: Clone and scan a GitHub repository

**Authentication**: Required

**Request Body**:
```json
{
  "repo_url": "https://github.com/user/repo",
  "project_name": "custom-name",
  "policy": "ai-ml-research",
  "context": "research"
}
```

**Request**:
```bash
curl -X POST "http://localhost:8000/scans" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/pytorch/pytorch",
    "project_name": "pytorch-scan",
    "policy": "ai-ml-permissive",
    "context": "production"
  }'
```

**Notes**:
- Repository is cloned with `--depth 1` (shallow clone) for speed
- Temporary directory is created and cleaned up automatically
- 5-minute timeout for cloning
- Only GitHub repositories are supported
- `project_name` is optional (defaults to repo name from URL)

**Errors**:
- `400`: Invalid GitHub URL or repository not found
- `408`: Clone operation timed out (repository too large)
- `500`: Internal error during scan

---

## Policy Endpoints

### List Policies

**Endpoint**: `GET /policies`

**Description**: List all available policies

**Authentication**: Required

**Rate Limit**: 100/minute

**Request**:
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/policies
```

**Response**:
```json
[
  {
    "name": "permissive",
    "description": "Permissive baseline policy that flags copyleft for review",
    "status": "active",
    "lastUpdated": null,
    "disclaimer": "Consult legal counsel for authoritative guidance."
  },
  {
    "name": "ai-ml-research",
    "description": "Permissive policy for academic and non-commercial AI/ML research",
    "status": "active",
    "lastUpdated": "2024-10-15",
    "disclaimer": "This research policy is designed for academic use only."
  }
]
```

### Get Policy Details

**Endpoint**: `GET /policies/{policy_name}`

**Description**: Get detailed policy configuration including all contexts

**Authentication**: Required

**Rate Limit**: 100/minute

**Request**:
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/policies/permissive
```

**Response**:
```json
{
  "name": "permissive",
  "description": "Permissive baseline policy that flags copyleft for review",
  "status": "active",
  "lastUpdated": null,
  "disclaimer": "Consult legal counsel for authoritative guidance.",
  "contexts": [
    {
      "name": "internal",
      "description": "Internal tooling and research prototypes",
      "allow": ["MIT", "Apache-2.0", "BSD-*", "ISC", "CC0-1.0"],
      "deny": ["SSPL-1.0"],
      "review": ["GPL-*", "AGPL-*", "LGPL-*"],
      "dualLicensePreference": "most_permissive",
      "overrides": {}
    },
    {
      "name": "saas",
      "description": "Hosted or managed service deployments",
      "allow": ["MIT", "Apache-2.0", "BSD-*", "ISC"],
      "deny": ["SSPL-1.0", "AGPL-*", "GPL-3.0"],
      "review": ["LGPL-*", "MPL-*"],
      "dualLicensePreference": "avoid_copyleft",
      "overrides": {}
    }
  ]
}
```

### Policy Write Operations (Planned)

The following endpoints are planned for implementation:

#### Create Policy
**Endpoint**: `POST /policies`

#### Update Policy
**Endpoint**: `PUT /policies/{policy_name}`

#### Delete Policy
**Endpoint**: `DELETE /policies/{policy_name}`

#### Evaluate Policy (Dry-Run)
**Endpoint**: `POST /policies/{policy_name}/evaluate`

---

## Dashboard Endpoints

### Get Dashboard Summary

**Endpoint**: `GET /dashboard`

**Description**: Get aggregated statistics for dashboard visualization

**Authentication**: Required

**Rate Limit**: 100/minute

**Request**:
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/dashboard
```

**Response**:
```json
{
  "totalProjects": 15,
  "totalScans": 47,
  "totalViolations": 3,
  "totalWarnings": 12,
  "highRiskProjects": 2,
  "pendingScans": 0,
  "licenseDistribution": [
    {"license": "MIT", "count": 150, "percentage": 45.5},
    {"license": "Apache-2.0", "count": 100, "percentage": 30.3},
    {"license": "GPL-3.0", "count": 25, "percentage": 7.6},
    {"license": "UNKNOWN", "count": 55, "percentage": 16.7}
  ],
  "trend": [
    {
      "date": "2024-10-24",
      "scans": 5,
      "violations": 0,
      "warnings": 2
    },
    {
      "date": "2024-10-25",
      "scans": 8,
      "violations": 1,
      "warnings": 3
    }
  ]
}
```

---

## SBOM Endpoints

### Generate SBOM (CLI Only)

**Note**: SBOM API endpoints are currently disabled due to library migration. Use CLI commands instead:

```bash
# Generate CycloneDX SBOM
lcc sbom --scan-id <SCAN_ID> --format cyclonedx --output sbom.json

# Generate SPDX SBOM (JSON)
lcc sbom --scan-id <SCAN_ID> --format spdx --output sbom.spdx.json

# Generate SPDX SBOM (Tag-Value)
lcc sbom --scan-id <SCAN_ID> --format spdx --output-format tag-value --output sbom.spdx
```

### Planned API Endpoints

Once re-enabled, the following endpoints will be available:

#### Get SBOM
**Endpoint**: `GET /sbom/scans/{scan_id}`

Query Parameters:
- `format`: `cyclonedx` or `spdx`
- `output_format`: `json`, `xml`, `yaml`, or `tag-value`
- `project_name`: Optional project name
- `project_version`: Optional version
- `author`: Optional author name
- `supplier`: Optional supplier name

#### Generate SBOM (Async)
**Endpoint**: `POST /sbom/generate`

Returns a download URL for later retrieval.

---

## User Management

### Get User Profile

**Endpoint**: `GET /auth/me`

**Description**: Get current user's profile

**Authentication**: Required

**Request**:
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/auth/me
```

**Response**:
```json
{
  "username": "admin",
  "email": "admin@company.com",
  "full_name": "Administrator",
  "role": "admin",
  "disabled": false,
  "created_at": "2024-10-15T10:00:00Z"
}
```

### Register New User (Admin Only)

**Endpoint**: `POST /auth/register`

**Description**: Create a new user account (admin role required)

**Authentication**: Required (admin)

**Request**:
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "password": "secure123",
    "email": "dev@company.com",
    "full_name": "Developer User"
  }'
```

**Response**:
```json
{
  "username": "developer",
  "email": "dev@company.com",
  "full_name": "Developer User",
  "role": "user",
  "disabled": false
}
```

### Change Password

**Endpoint**: `POST /auth/change-password`

**Description**: Change current user's password

**Authentication**: Required

**Request**:
```bash
curl -X POST "http://localhost:8000/auth/change-password" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "old123",
    "new_password": "new_secure456"
  }'
```

### Create API Key

**Endpoint**: `POST /auth/keys`

**Description**: Create a long-lived API key

**Authentication**: Required

**Request**:
```bash
curl -X POST "http://localhost:8000/auth/keys" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI Pipeline Key",
    "role": "user",
    "expires_days": 365
  }'
```

**Response**:
```json
{
  "key_id": "api_key_abc123",
  "api_key": "lcc_live_xyz789...",
  "warning": "Save this key securely. It will not be shown again."
}
```

**Important**: Save the `api_key` immediately; it cannot be retrieved later.

### List API Keys

**Endpoint**: `GET /auth/keys`

**Description**: List all API keys (without secrets)

**Authentication**: Required

### Revoke API Key

**Endpoint**: `DELETE /auth/keys/{key_id}`

**Description**: Revoke an API key

**Authentication**: Required

---

## Error Handling

### Standard Error Response

All errors return a consistent JSON structure:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created (e.g., scan) |
| 400 | Bad Request | Invalid input, missing required fields |
| 401 | Unauthorized | Missing or invalid auth token |
| 403 | Forbidden | Insufficient permissions (role) |
| 404 | Not Found | Resource doesn't exist (scan, policy) |
| 408 | Request Timeout | Operation timed out (e.g., git clone) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |

### Error Examples

#### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

#### 400 Bad Request
```json
{
  "detail": "Either 'path' or 'repo_url' must be provided"
}
```

#### 404 Not Found
```json
{
  "detail": "Scan 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

#### 429 Rate Limit
```json
{
  "detail": "Rate limit exceeded: 100 per 1 minute"
}
```

---

## Rate Limiting

All authenticated endpoints have rate limits to prevent abuse:

- **Limit**: 100 requests per minute per endpoint
- **Key**: Based on client IP address
- **Headers**: Rate limit info in response headers

**Rate Limit Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1698672000
```

When rate limit is exceeded:
- **Status Code**: `429 Too Many Requests`
- **Retry-After**: Header indicates wait time in seconds

**Avoiding Rate Limits**:
- Cache scan results
- Use webhooks for long-running operations
- Batch operations when possible
- Consider self-hosting for higher limits

---

## Programmatic API

For advanced integration, use the Python SDK directly.

### Installation

```bash
pip install license-compliance-checker
```

### Basic Usage

```python
from lcc.factory import build_detectors, build_resolvers
from lcc.scanner import Scanner
from lcc.config import load_config
from lcc.cache import Cache
from lcc.policy import PolicyManager, evaluate_policy

# Load configuration
config = load_config()
cache = Cache(config)

# Create scanner
detectors = build_detectors()
resolvers = build_resolvers(config, cache)
scanner = Scanner(detectors, resolvers, config)

# Scan a project
report = scanner.scan("/path/to/project")

# Print results
print(f"Found {len(report.findings)} components")
for finding in report.findings:
    print(f"  {finding.component.name}: {finding.resolved_license}")

# Evaluate against policy
policy_manager = PolicyManager(config)
policy = policy_manager.load_policy("permissive")

for finding in report.findings:
    decision = evaluate_policy(
        policy.data,
        [finding.resolved_license],
        context="production"
    )
    print(f"{finding.component.name}: {decision.status}")
```

### Custom Detector

```python
from lcc.detection.base import Detector
from lcc.models import Component

class MyCustomDetector(Detector):
    def detect(self, root_path):
        # Scan for components
        components = []

        # Your custom detection logic
        manifest = root_path / "custom.manifest"
        if manifest.exists():
            # Parse manifest and create components
            components.append(Component(
                name="my-package",
                version="1.0.0",
                type="custom",
                metadata={"source": "custom.manifest"}
            ))

        return components

# Use custom detector
from lcc.factory import build_detectors, build_resolvers
from lcc.scanner import Scanner

detectors = build_detectors()
detectors.append(MyCustomDetector())

scanner = Scanner(detectors, build_resolvers(config, cache), config)
report = scanner.scan("/path/to/project")
```

### Custom Resolver

```python
from lcc.resolution.base import Resolver

class MyCustomResolver(Resolver):
    def resolve(self, component):
        # Custom license resolution logic
        if component.name == "proprietary-lib":
            return "Proprietary-CompanyName"
        return None

# Use custom resolver
from lcc.factory import build_resolvers

resolvers = build_resolvers(config, cache)
resolvers.insert(0, MyCustomResolver())  # Higher priority

scanner = Scanner(build_detectors(), resolvers, config)
```

### Async Scanning

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def scan_projects(projects):
    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor(max_workers=5) as executor:
        tasks = [
            loop.run_in_executor(executor, scanner.scan, project)
            for project in projects
        ]
        results = await asyncio.gather(*tasks)

    return results

# Run async
projects = ["/path/to/proj1", "/path/to/proj2", "/path/to/proj3"]
results = asyncio.run(scan_projects(projects))
```

---

## Examples

### Complete Workflow Example

```bash
#!/bin/bash
# Automated CI/CD license compliance check

API_URL="http://localhost:8000"
USERNAME="ci-bot"
PASSWORD="secure-password"

# 1. Login
TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$USERNAME&password=$PASSWORD")

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

# 2. Create scan
SCAN_RESPONSE=$(curl -s -X POST "$API_URL/scans" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"repo_url\": \"https://github.com/myorg/myrepo\",
    \"policy\": \"permissive\",
    \"context\": \"production\"
  }")

SCAN_ID=$(echo $SCAN_RESPONSE | jq -r '.id')
STATUS=$(echo $SCAN_RESPONSE | jq -r '.status')
VIOLATIONS=$(echo $SCAN_RESPONSE | jq -r '.violations')

# 3. Check results
if [ "$STATUS" = "violation" ]; then
  echo "❌ License compliance check failed!"
  echo "Violations: $VIOLATIONS"

  # Get detailed report
  curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
    "$API_URL/scans/$SCAN_ID" | jq '.report.findings[] | select(.status == "violation")'

  exit 1
elif [ "$STATUS" = "warning" ]; then
  echo "⚠️  License compliance check passed with warnings"
  exit 0
else
  echo "✅ License compliance check passed"
  exit 0
fi
```

### Python Integration Example

```python
import requests
from typing import Dict, List

class LCCClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.token = self._login(username, password)

    def _login(self, username: str, password: str) -> str:
        response = requests.post(
            f"{self.base_url}/auth/login",
            data={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def scan_project(self, path: str, policy: str = "permissive",
                    context: str = "production") -> Dict:
        response = requests.post(
            f"{self.base_url}/scans",
            json={
                "path": path,
                "policy": policy,
                "context": context
            },
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    def scan_github_repo(self, repo_url: str, policy: str = "permissive",
                         context: str = "production") -> Dict:
        response = requests.post(
            f"{self.base_url}/scans",
            json={
                "repo_url": repo_url,
                "policy": policy,
                "context": context
            },
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    def get_scan(self, scan_id: str) -> Dict:
        response = requests.get(
            f"{self.base_url}/scans/{scan_id}",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    def list_scans(self) -> List[Dict]:
        response = requests.get(
            f"{self.base_url}/scans",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    def get_dashboard(self) -> Dict:
        response = requests.get(
            f"{self.base_url}/dashboard",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

# Usage
client = LCCClient("http://localhost:8000", "admin", "password123")

# Scan local project
scan = client.scan_project("/path/to/project", policy="ai-ml-permissive")
print(f"Scan ID: {scan['id']}, Status: {scan['status']}")

# Scan GitHub repo
scan = client.scan_github_repo(
    "https://github.com/pytorch/pytorch",
    policy="ai-ml-research",
    context="research"
)

# Get dashboard stats
dashboard = client.get_dashboard()
print(f"Total Scans: {dashboard['totalScans']}")
print(f"Total Violations: {dashboard['totalViolations']}")
```

### GitHub Actions Integration

```yaml
# .github/workflows/license-compliance.yml
name: License Compliance Check

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  compliance:
    runs-on: ubuntu-latest

    services:
      lcc:
        image: lcc:latest
        ports:
          - 8000:8000
        env:
          LCC_SECRET_KEY: ${{ secrets.LCC_SECRET_KEY }}

    steps:
      - uses: actions/checkout@v3

      - name: Wait for API
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'

      - name: Run compliance check
        env:
          LCC_USERNAME: ${{ secrets.LCC_USERNAME }}
          LCC_PASSWORD: ${{ secrets.LCC_PASSWORD }}
        run: |
          # Login
          TOKEN=$(curl -X POST http://localhost:8000/auth/login \
            -d "username=$LCC_USERNAME&password=$LCC_PASSWORD" | jq -r '.access_token')

          # Scan
          RESULT=$(curl -X POST http://localhost:8000/scans \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"path\": \"$GITHUB_WORKSPACE\", \"policy\": \"permissive\", \"context\": \"production\"}")

          # Check status
          STATUS=$(echo $RESULT | jq -r '.status')
          if [ "$STATUS" = "violation" ]; then
            echo "License compliance check failed!"
            exit 1
          fi
```

---

## Summary

The LCC REST API provides:

1. **Complete functionality**: All CLI features available via API
2. **Security**: JWT authentication, RBAC, API keys
3. **Performance**: Rate limiting, efficient scanning, caching
4. **Integration**: Easy integration with CI/CD, dashboards, tools
5. **Documentation**: Interactive OpenAPI docs at `/docs`

### Quick Links

- **API Documentation**: http://localhost:8000/docs
- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Policy Guide**: [POLICY_GUIDE.md](POLICY_GUIDE.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Next Steps

1. Start the API server: `lcc server` or `docker-compose up`
2. Create admin user: `lcc auth create-user admin password123 --role admin`
3. Visit http://localhost:8000/docs for interactive API documentation
4. Try the examples above
5. Integrate into your CI/CD pipeline

---

*For support and questions, visit https://github.com/your-org/lcc/issues*
