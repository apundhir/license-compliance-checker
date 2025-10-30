# License Compliance Checker - Testing Guide

**Version:** Phase 3 (45% Complete)
**Last Updated:** 2025-10-10

---

## 🚀 Quick Start - Docker Deployment

### Start the System

```bash
# Build and start all services
docker-compose up -d --build

# Check services are running
docker-compose ps
```

**Access Points:**
- **Frontend Dashboard:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

**Default Credentials:**
- **Username:** `admin`
- **Password:** `admin`

---

## ✅ Features Ready for Testing

### 1. Authentication & User Management

**Login Page:** http://localhost:3000/login

**Test Cases:**
```bash
# Valid login
Username: admin
Password: admin

# API Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"

# Get current user info
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Features:**
- ✅ JWT authentication
- ✅ Token refresh
- ✅ Role-based access control (Admin, User, Viewer)
- ✅ API key management
- ✅ Password change

### 2. Dashboard & Summary

**Dashboard:** http://localhost:3000/

**Features:**
- ✅ Compliance score visualization (circular progress)
- ✅ Metric cards (scans, violations, warnings, projects)
- ✅ Trend chart (7d, 30d, 90d views)
- ✅ Recent scans table
- ✅ Quick actions
- ✅ System health indicators

**Test:**
1. Navigate to dashboard
2. Check compliance score display
3. View trend charts
4. Click on metric cards to drill down

### 3. License Scanning (CLI & API)

**CLI - Scan a GitHub Repository:**

```bash
# Scan a Python project
docker-compose exec backend lcc scan \
  --git https://github.com/psf/requests \
  --format json \
  --output /data/scan-requests.json

# Scan with policy
docker-compose exec backend lcc scan \
  --git https://github.com/psf/requests \
  --policy permissive \
  --context commercial \
  --format json \
  --output /data/scan-requests-policy.json

# Scan a JavaScript project
docker-compose exec backend lcc scan \
  --git https://github.com/facebook/react \
  --format json \
  --output /data/scan-react.json

# Scan a Go project
docker-compose exec backend lcc scan \
  --git https://github.com/gin-gonic/gin \
  --format json \
  --output /data/scan-gin.json
```

**API - Create Scan:**

```bash
# Get auth token first
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=admin" | jq -r '.access_token')

# Create scan via API
curl -X POST http://localhost:8000/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "https://github.com/psf/requests",
    "policy": "permissive",
    "context": "commercial"
  }'

# List scans
curl http://localhost:8000/scans \
  -H "Authorization: Bearer $TOKEN"

# Get scan details
curl http://localhost:8000/scans/SCAN_ID \
  -H "Authorization: Bearer $TOKEN"
```

**Supported Languages:**
- ✅ Python (pip, pipenv, poetry)
- ✅ JavaScript/TypeScript (npm, yarn, package-lock.json)
- ✅ Go (go.mod)
- ✅ Java (Maven - pom.xml)
- ✅ Gradle (build.gradle, build.gradle.kts)
- ✅ Rust (Cargo.toml)
- ✅ Ruby (Gemfile, Gemfile.lock)
- ✅ .NET (packages.config, .csproj, .fsproj)

### 4. SBOM Generation ⭐ NEW

**CLI Commands:**

```bash
# Generate CycloneDX SBOM from scan
docker-compose exec backend lcc sbom generate \
  /data/scan-requests.json \
  --output /data/sbom-requests.json \
  --format cyclonedx \
  --sbom-format json \
  --project-name "Requests Library" \
  --project-version "2.31.0" \
  --author "Python Software Foundation"

# Generate SPDX SBOM in XML format
docker-compose exec backend lcc sbom generate \
  /data/scan-requests.json \
  --output /data/sbom-requests.xml \
  --format spdx \
  --sbom-format xml \
  --project-name "Requests Library"

# Generate SPDX in Tag-Value format
docker-compose exec backend lcc sbom generate \
  /data/scan-requests.json \
  --output /data/sbom-requests.spdx \
  --format spdx \
  --sbom-format tag-value

# Validate SBOM
docker-compose exec backend lcc sbom validate \
  /data/sbom-requests.json \
  --check-licenses

# Sign SBOM (if GPG is configured)
docker-compose exec backend lcc sbom sign \
  /data/sbom-requests.json \
  --key admin@example.com \
  --detached

# Generate hash
docker-compose exec backend lcc sbom hash \
  /data/sbom-requests.json \
  --algorithm sha256
```

**API - Download SBOM:**

```bash
# Get CycloneDX SBOM for a scan
curl http://localhost:8000/sbom/scans/SCAN_ID?format=cyclonedx&output_format=json \
  -H "Authorization: Bearer $TOKEN" \
  -o sbom.json

# Get SPDX SBOM
curl http://localhost:8000/sbom/scans/SCAN_ID?format=spdx&output_format=xml \
  -H "Authorization: Bearer $TOKEN" \
  -o sbom.xml

# Get SPDX Tag-Value format
curl http://localhost:8000/sbom/scans/SCAN_ID?format=spdx&output_format=tag-value \
  -H "Authorization: Bearer $TOKEN" \
  -o sbom.spdx
```

**Supported Formats:**
- ✅ CycloneDX 1.5 (JSON, XML)
- ✅ SPDX 2.3 (JSON, XML, YAML, Tag-Value)

### 5. AI/ML License Detection ⭐ NEW

**Test with Hugging Face Model:**

```bash
# Clone a Hugging Face model (example)
docker-compose exec backend bash -c "
  cd /tmp && \
  git clone https://huggingface.co/bert-base-uncased && \
  lcc scan bert-base-uncased --format json --output /data/scan-bert.json
"

# Generate SBOM for AI model
docker-compose exec backend lcc sbom generate \
  /data/scan-bert.json \
  --output /data/sbom-bert.json \
  --format cyclonedx \
  --project-name "BERT Base Uncased"
```

**Detected Information:**
- ✅ Model name and version
- ✅ License from model card
- ✅ Framework (PyTorch, TensorFlow, JAX)
- ✅ Model architecture
- ✅ Tags and categories
- ✅ Training datasets

**Test with Hugging Face Dataset:**

```bash
# Clone a dataset (example)
docker-compose exec backend bash -c "
  cd /tmp && \
  git clone https://huggingface.co/datasets/squad && \
  lcc scan squad --format json --output /data/scan-squad.json
"
```

**Detected Information:**
- ✅ Dataset name
- ✅ License from dataset card
- ✅ Format (Arrow, Parquet, CSV, JSON)
- ✅ Size categories
- ✅ Languages
- ✅ Task categories

### 6. AI/ML Policy Testing ⭐ NEW

**Available Policies:**

1. **ai-ml-permissive** - Balanced policy for most AI/ML projects
2. **ai-ml-strict** - Commercial policy avoiding use restrictions
3. **ai-ml-research** - Academic/non-commercial research policy

**Test Commands:**

```bash
# Scan with AI/ML permissive policy
docker-compose exec backend lcc scan \
  /tmp/ml-project \
  --policy ai-ml-permissive \
  --context commercial \
  --format json \
  --output /data/scan-ml-permissive.json

# Scan with strict policy
docker-compose exec backend lcc scan \
  /tmp/ml-project \
  --policy ai-ml-strict \
  --context production \
  --format json \
  --output /data/scan-ml-strict.json

# Scan with research policy
docker-compose exec backend lcc scan \
  /tmp/ml-project \
  --policy ai-ml-research \
  --context research \
  --format json \
  --output /data/scan-ml-research.json
```

**Policy Features:**
- ✅ AI-specific license handling (RAIL, Llama, OpenRAIL)
- ✅ Dataset license rules (Creative Commons, ODbL)
- ✅ Use restriction warnings
- ✅ User threshold checks (e.g., Llama 2's 700M MAU limit)
- ✅ Context-aware rules

### 7. Policy Management

**Frontend:** http://localhost:3000/policies-list

**Features:**
- ✅ List all policies
- ✅ View policy details
- ✅ Policy templates
- ✅ Export policies

**CLI:**

```bash
# List policies
docker-compose exec backend lcc policy list

# Show policy details
docker-compose exec backend lcc policy show permissive

# Show AI/ML policy
docker-compose exec backend lcc policy show ai-ml-permissive

# Validate policy file
docker-compose exec backend lcc policy validate /path/to/policy.yml

# Test policy against a scan
docker-compose exec backend lcc policy test ai-ml-strict /data/scan-ml.json
```

### 8. Report Generation

**CLI - Multiple Formats:**

```bash
# JSON report
docker-compose exec backend lcc scan \
  --git https://github.com/psf/requests \
  --format json \
  --output /data/report.json

# Markdown report
docker-compose exec backend lcc report generate \
  /data/scan-requests.json \
  --format markdown \
  --output /data/report.md

# HTML report
docker-compose exec backend lcc report generate \
  /data/scan-requests.json \
  --format html \
  --output /data/report.html

# CSV report
docker-compose exec backend lcc report generate \
  /data/scan-requests.json \
  --format csv \
  --output /data/report.csv
```

**Frontend:**
- ✅ View scan results in dashboard
- ✅ Export reports as JSON

### 9. Interactive Scan Explorer

```bash
# Launch interactive mode
docker-compose exec backend lcc interactive /path/to/project

# Or with existing report
docker-compose exec backend lcc interactive --report /data/scan-requests.json
```

**Features:**
- ✅ Search components
- ✅ Filter by license
- ✅ View evidence chain
- ✅ Export filtered results

---

## 🧪 Test Scenarios

### Scenario 1: Complete Workflow - Python Project

```bash
# 1. Scan a Python project
docker-compose exec backend lcc scan \
  --git https://github.com/psf/requests \
  --policy permissive \
  --context commercial \
  --format json \
  --output /data/scan-requests.json

# 2. Generate SBOM
docker-compose exec backend lcc sbom generate \
  /data/scan-requests.json \
  --output /data/sbom-requests.json \
  --format cyclonedx \
  --project-name "Requests" \
  --project-version "2.31.0"

# 3. Validate SBOM
docker-compose exec backend lcc sbom validate \
  /data/sbom-requests.json \
  --check-licenses

# 4. Generate hash for distribution
docker-compose exec backend lcc sbom hash \
  /data/sbom-requests.json \
  --algorithm sha256

# 5. View results
docker-compose exec backend cat /data/scan-requests.json | jq .
docker-compose exec backend cat /data/sbom-requests.json | jq .
```

### Scenario 2: AI/ML Project Compliance

```bash
# 1. Clone a Hugging Face model
docker-compose exec backend bash -c "
  cd /tmp && \
  git clone https://huggingface.co/gpt2 && \
  lcc scan gpt2 \
    --policy ai-ml-strict \
    --context production \
    --format json \
    --output /data/scan-gpt2.json
"

# 2. Check for AI license violations
docker-compose exec backend cat /data/scan-gpt2.json | jq '.summary.violations'

# 3. Generate SBOM with AI components
docker-compose exec backend lcc sbom generate \
  /data/scan-gpt2.json \
  --output /data/sbom-gpt2.json \
  --format cyclonedx \
  --project-name "GPT-2 Model"

# 4. Review AI-specific licenses
docker-compose exec backend cat /data/sbom-gpt2.json | \
  jq '.components[] | select(.type=="machine-learning-model")'
```

### Scenario 3: Multi-Language Project

```bash
# Scan a project with multiple languages
docker-compose exec backend lcc scan \
  --git https://github.com/vercel/next.js \
  --format json \
  --output /data/scan-nextjs.json

# View detected components by type
docker-compose exec backend cat /data/scan-nextjs.json | \
  jq '.findings | group_by(.component.type) | map({type: .[0].component.type, count: length})'
```

---

## 🔗 Testing from Frontend

### Dashboard Testing

**URL:** http://localhost:3000/

**Steps:**
1. Login with admin/admin
2. View compliance score (should show circular progress)
3. Check metric cards for scans, violations, warnings
4. View trend chart (toggle between 7d, 30d, 90d)
5. Click on recent scans to view details
6. Use quick actions to navigate

### Scan Detail Page

**URL:** http://localhost:3000/scans/[id]

**Steps:**
1. Navigate from dashboard or recent scans
2. View scan overview and summary cards
3. Check license distribution grid
4. Browse components table
5. Expand components to see evidence chain
6. Export scan as JSON

### Policy Management

**URL:** http://localhost:3000/policies-list

**Steps:**
1. View all available policies
2. Check policy templates (Permissive, Copyleft-friendly, Commercial)
3. Click on policy to view details
4. Review allowed/review/denied licenses
5. See usage examples (CLI, API, GitHub Actions)

**Policy Detail URL:** http://localhost:3000/policies-detail/[name]

Example: http://localhost:3000/policies-detail/ai-ml-permissive

---

## 📊 Expected Test Results

### Python Project (requests)

**Components Expected:**
- urllib3
- charset-normalizer
- idna
- certifi
- ~50+ total dependencies

**Licenses Expected:**
- MIT (most common)
- Apache-2.0
- BSD-3-Clause
- PSF (Python Software Foundation)

### JavaScript Project (react)

**Components Expected:**
- loose-envify
- js-tokens
- ~10+ total dependencies

**Licenses Expected:**
- MIT (dominant)
- BSD-3-Clause

### AI/ML Model (BERT)

**Component Type:** AI_MODEL

**License Expected:**
- Apache-2.0 or model-specific license from card

**Metadata Expected:**
- Framework: PyTorch
- Architecture: BertModel
- Tags: transformers, pytorch, bert

---

## 🐛 Known Issues & Limitations

### Current Phase (45% Complete)

**Not Yet Implemented:**
- ❌ Frontend SBOM download UI (use API instead)
- ❌ Frontend AI/ML components view (use CLI instead)
- ❌ PyTorch Hub detection
- ❌ TensorFlow Hub detection
- ❌ DVC dataset detection
- ❌ Kaggle dataset detection

**Workarounds:**
- Use CLI for SBOM generation
- Use API for SBOM download
- Use CLI for AI/ML scanning

### Testing Limitations

**Mock Data:**
- Frontend dashboard uses mock data if backend is unavailable
- This is for development only

**GPG Signing:**
- Requires GPG keys configured in container
- Can be skipped for testing

---

## 🔧 Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Restart services
docker-compose restart

# Rebuild if needed
docker-compose down
docker-compose up -d --build
```

### Authentication Issues

```bash
# Reset admin password
docker-compose exec backend python -c "
from lcc.auth.repository import UserRepository
from lcc.config import load_config
config = load_config()
repo = UserRepository(config.database_path)
repo.update_password('admin', 'admin')
print('Password reset to: admin')
"
```

### Database Issues

```bash
# Reset database
docker-compose down -v
docker-compose up -d --build
```

---

## 📝 API Documentation

**Interactive API Docs:** http://localhost:8000/docs

**Key Endpoints:**

```
POST   /auth/login              - Get JWT token
GET    /auth/me                 - Current user info
GET    /dashboard               - Dashboard summary
POST   /scans                   - Create scan
GET    /scans                   - List scans
GET    /scans/{id}              - Scan details
GET    /sbom/scans/{id}         - Download SBOM
POST   /sbom/generate           - Generate SBOM
GET    /policies                - List policies
GET    /policies/{name}         - Policy details
```

---

## 📞 Support

**Questions?**
- Check API docs: http://localhost:8000/docs
- Review logs: `docker-compose logs -f`
- Open issue on GitHub

**Ready to Test!** 🚀

Start with the Quick Start section and work through the test scenarios.
