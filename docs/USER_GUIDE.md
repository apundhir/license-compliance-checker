# License Compliance Checker - User Guide

> Comprehensive guide to using the License Compliance Checker for traditional software and AI/ML license compliance

**Version:** 1.0
**Last Updated:** 2025-01-30

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Concepts](#core-concepts)
5. [CLI Reference](#cli-reference)
6. [Configuration](#configuration)
7. [Real-World Examples](#real-world-examples)
8. [Integration Patterns](#integration-patterns)
9. [Advanced Usage](#advanced-usage)
10. [Troubleshooting](#troubleshooting)

---

## 1. Introduction

### What is License Compliance Checker?

The License Compliance Checker (LCC) is a comprehensive tool for detecting and analyzing software licenses in your projects. It goes beyond traditional package managers to provide:

- **Multi-Source License Detection**: Combines data from package registries, GitHub, ClearlyDefined, and local filesystem scans
- **AI/ML License Support**: Specialized detection for Hugging Face models and datasets with AI-specific licenses (RAIL, Llama, etc.)
- **Policy-Based Compliance**: Define custom policies to enforce license restrictions
- **SBOM Generation**: Create industry-standard SBOMs in CycloneDX and SPDX formats
- **Professional Dashboard**: Web UI for managing scans, policies, and violations

### Why Use LCC?

- **Comprehensive Coverage**: Detects licenses for 8+ languages and package managers
- **AI/ML Awareness**: First-class support for AI model and dataset licenses
- **Multi-Source Resolution**: Doesn't rely on a single source of truth
- **Policy Enforcement**: Automated compliance checking against your organization's rules
- **Production Ready**: REST API, authentication, and dashboard for enterprise use

### Supported Languages & Package Managers

| Language | Package Managers | Detection Method |
|----------|-----------------|------------------|
| Python | pip, poetry, conda | requirements.txt, pyproject.toml, setup.py |
| JavaScript/TypeScript | npm, yarn, pnpm | package.json, yarn.lock, package-lock.json |
| Go | go modules | go.mod, go.sum |
| Java | Maven, Gradle | pom.xml, build.gradle |
| Rust | Cargo | Cargo.toml, Cargo.lock |
| Ruby | Bundler | Gemfile, Gemfile.lock |
| .NET | NuGet | *.csproj, packages.config |
| PHP | Composer | composer.json |
| **AI Models** | Hugging Face | config.json, README.md (model cards) |
| **Datasets** | Hugging Face | dataset_infos.json, README.md |

---

## 2. Installation

### Prerequisites

- **Python**: 3.9 or higher
- **Docker** (optional but recommended)
- **Git**: For GitHub repository scanning

### Method 1: Docker (Recommended)

The easiest way to run LCC with all services (API + Dashboard):

```bash
# Clone the repository
git clone https://github.com/yourusername/license-compliance-checker.git
cd license-compliance-checker

# Start all services
docker-compose up -d

# Access the dashboard
open http://localhost:3000
```

**Services:**
- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Method 2: pip install

For CLI-only usage:

```bash
# Install from PyPI (when published)
pip install license-compliance-checker

# Or install from source
git clone https://github.com/yourusername/license-compliance-checker.git
cd license-compliance-checker
pip install -e .
```

### Method 3: Development Setup

For contributing or development:

```bash
# Clone repository
git clone https://github.com/yourusername/license-compliance-checker.git
cd license-compliance-checker

# Install with development dependencies
pip install -e ".[dev]"

# Install dashboard dependencies
cd dashboard
npm install

# Run backend (terminal 1)
lcc server

# Run dashboard (terminal 2)
cd dashboard
npm run dev
```

### Verify Installation

```bash
# Check CLI version
lcc --version

# Run health check
lcc scan --help
```

---

## 3. Quick Start

### Your First Scan (5 minutes)

#### Step 1: Scan a Local Project

```bash
# Scan current directory
lcc scan .

# Scan specific directory
lcc scan /path/to/your/project

# Scan with a policy
lcc scan . --policy permissive
```

#### Step 2: View the Report

LCC generates a console report by default:

```
╭─ License Compliance Report ─────────────────────────────╮
│ Project: my-project                                      │
│ Generated: 2025-01-30 14:32:15                          │
│ Total Components: 127                                    │
│ Licensed: 125 (98%)                                      │
│ Unlicensed: 2 (2%)                                       │
│ Policy: permissive                                       │
│ Status: ✓ PASS (no violations)                          │
╰──────────────────────────────────────────────────────────╯
```

#### Step 3: Generate Different Report Formats

```bash
# HTML report
lcc scan . --report-format html --output report.html

# JSON report
lcc scan . --report-format json --output report.json

# Markdown report
lcc scan . --report-format markdown --output report.md
```

#### Step 4: Generate an SBOM

```bash
# CycloneDX SBOM (JSON)
lcc sbom generate scan-result.json --format cyclonedx --output sbom.json

# SPDX SBOM (tag-value format)
lcc sbom generate scan-result.json --format spdx --output-format tag-value --output sbom.spdx
```

### Using the Dashboard

1. **Start the services:**
   ```bash
   docker-compose up -d
   ```

2. **Open the dashboard:**
   Navigate to http://localhost:3000

3. **Login:**
   Default credentials:
   - Username: `admin`
   - Password: `admin`

4. **Create a scan:**
   - Click "Scans" in sidebar
   - Click "New Scan" button
   - Enter GitHub URL or select policy
   - View results in real-time

---

## 4. Core Concepts

### License Detection

LCC uses a **multi-source resolution chain** to find licenses:

```
ClearlyDefinedResolver
    ↓ (if not found)
RegistryResolver (PyPI, npm, etc.)
    ↓ (if not found)
GitHubResolver
    ↓ (if not found)
FileSystemResolver (scan LICENSE files)
    ↓ (if not found)
Result: UNKNOWN
```

Each resolver provides:
- License expression (SPDX format where possible)
- Confidence score
- Evidence (source URL, file path, etc.)

### Policy-Based Compliance

Policies define what licenses are acceptable for different contexts:

```yaml
name: permissive
description: Allow permissive open source licenses
contexts:
  development:
    allow:
      - MIT
      - Apache-2.0
      - BSD-3-Clause
    deny:
      - GPL-3.0
      - AGPL-3.0
```

**Policy Decisions:**
- **PASS**: Component uses an allowed license
- **WARNING**: Component requires manual review
- **VIOLATION**: Component uses a denied license

### Component Types

LCC recognizes different types of dependencies:

- **python**: Python packages (pip, conda)
- **javascript**: npm packages
- **go**: Go modules
- **java**: Maven/Gradle dependencies
- **rust**: Cargo crates
- **ruby**: Ruby gems
- **dotnet**: NuGet packages
- **php**: Composer packages
- **ai_model**: AI/ML models (Hugging Face, etc.)
- **dataset**: Training/validation datasets

### AI/ML License Categories

AI models and datasets have specialized licenses:

**AI Model Licenses:**
- OpenRAIL (Open Responsible AI License)
- OpenRAIL-M (Model-specific)
- Llama 2/3 Community Licenses (with MAU limits)
- Creative ML OpenRAIL-M (Stable Diffusion)
- BigScience BLOOM RAIL 1.0

**Dataset Licenses:**
- Creative Commons (CC0, CC-BY, CC-BY-SA, CC-BY-NC, etc.)
- OpenData Commons (ODC-BY, ODbL)
- Community Data License Agreement (CDLA)

---

## 5. CLI Reference

### Main Commands

#### `lcc scan`

Scan a project for license compliance.

**Usage:**
```bash
lcc scan [PATH] [OPTIONS]
```

**Arguments:**
- `PATH`: Directory to scan (default: current directory)

**Options:**
```bash
--policy TEXT           Policy to apply (default: permissive)
--report-format TEXT    Output format: console|json|html|markdown (default: console)
--output PATH           Output file path
--recursive             Scan subdirectories recursively
--max-depth INTEGER     Maximum directory depth
--exclude PATTERN       Exclude patterns (can be used multiple times)
--timeout INTEGER       Scan timeout in seconds (default: 300)
```

**Examples:**
```bash
# Basic scan
lcc scan .

# Scan with strict policy
lcc scan . --policy strict

# Generate HTML report
lcc scan . --report-format html --output compliance-report.html

# Exclude node_modules and .git
lcc scan . --exclude node_modules --exclude .git

# Scan with timeout
lcc scan /large/project --timeout 600
```

#### `lcc policy`

Manage compliance policies.

**Usage:**
```bash
lcc policy [COMMAND]
```

**Commands:**
```bash
list                    List available policies
show NAME               Show policy details
validate PATH           Validate policy file
test PATH LICENSE       Test how policy evaluates a license
```

**Examples:**
```bash
# List all policies
lcc policy list

# Show policy details
lcc policy show permissive

# Validate custom policy
lcc policy validate my-policy.yml

# Test policy
lcc policy test my-policy.yml MIT
```

#### `lcc report`

Generate reports from scan results.

**Usage:**
```bash
lcc report [SCAN_RESULT] [OPTIONS]
```

**Arguments:**
- `SCAN_RESULT`: Path to scan result JSON file

**Options:**
```bash
--format TEXT      Report format: console|json|html|markdown|csv
--output PATH      Output file path
--policy TEXT      Policy to re-evaluate against
```

**Examples:**
```bash
# Generate HTML from previous scan
lcc report scan-result.json --format html --output report.html

# Re-evaluate with different policy
lcc report scan-result.json --policy strict
```

#### `lcc sbom`

Generate Software Bill of Materials.

**Usage:**
```bash
lcc sbom [COMMAND]
```

**Commands:**
```bash
generate SCAN_RESULT    Generate SBOM from scan result
validate SBOM_FILE      Validate SBOM file
sign SBOM_FILE          Sign SBOM with GPG
verify SBOM_FILE SIG    Verify SBOM signature
list-keys               List available GPG keys
```

**Generate Options:**
```bash
--format TEXT           SBOM format: cyclonedx|spdx (default: cyclonedx)
--output-format TEXT    File format: json|xml|yaml|tag-value (default: json)
--output PATH           Output file path
--project-name TEXT     Project name
--project-version TEXT  Project version
--author TEXT           Document author
--supplier TEXT         Component supplier
```

**Examples:**
```bash
# Generate CycloneDX SBOM
lcc sbom generate scan-result.json --format cyclonedx --output sbom.json

# Generate SPDX in tag-value format
lcc sbom generate scan-result.json \\
    --format spdx \\
    --output-format tag-value \\
    --output sbom.spdx

# Sign SBOM
lcc sbom sign sbom.json --key-id YOUR_KEY_ID

# Verify signature
lcc sbom verify sbom.json sbom.json.sig
```

#### `lcc interactive`

Interactive mode for exploring scan results.

**Usage:**
```bash
lcc interactive [SCAN_RESULT]
```

**Features:**
- Browse components
- Search licenses
- Filter by policy status
- Drill down into dependencies
- Export subsets

#### `lcc server`

Start the REST API server.

**Usage:**
```bash
lcc server [OPTIONS]
```

**Options:**
```bash
--host TEXT        Host to bind (default: 0.0.0.0)
--port INTEGER     Port to bind (default: 8000)
--reload           Auto-reload on code changes
--workers INTEGER  Number of worker processes
--config PATH      Configuration file
```

**Examples:**
```bash
# Start server
lcc server

# Development mode with auto-reload
lcc server --reload

# Production with multiple workers
lcc server --workers 4
```

#### `lcc queue`

Manage background job queue.

**Usage:**
```bash
lcc queue [COMMAND]
```

**Commands:**
```bash
worker              Start queue worker
status              Show queue status
list                List queued jobs
cancel JOB_ID       Cancel a job
```

---

## 6. Configuration

### Configuration File

Create `~/.lcc/config.yml`:

```yaml
# General settings
cache_dir: ~/.lcc/cache
database_path: ~/.lcc/lcc.db
policy_dir: ~/.lcc/policies

# Detection settings
detection:
  timeout: 300
  max_depth: 10
  exclude_patterns:
    - node_modules
    - .git
    - __pycache__
    - venv
    - dist
    - build

# Resolution settings
resolution:
  sources:
    - clearlydefined
    - registry
    - github
    - filesystem
  cache_ttl: 86400  # 24 hours

  clearlydefined:
    enabled: true
    url: https://api.clearlydefined.io

  github:
    enabled: true
    token: ${GITHUB_TOKEN}  # Use environment variable

  registries:
    pypi:
      enabled: true
      url: https://pypi.org
    npm:
      enabled: true
      url: https://registry.npmjs.org

# Policy settings
policy:
  default: permissive
  strict_mode: false

# API settings
api:
  host: 0.0.0.0
  port: 8000
  cors_origins:
    - http://localhost:3000
  rate_limit:
    enabled: true
    requests_per_minute: 60

# SBOM settings
sbom:
  default_format: cyclonedx
  default_output_format: json
  include_dependencies: true
  include_licenses: true
```

### Environment Variables

```bash
# GitHub token for API access
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# LCC configuration
export LCC_CONFIG_PATH=~/.lcc/config.yml
export LCC_CACHE_DIR=~/.lcc/cache
export LCC_DATABASE_PATH=~/.lcc/lcc.db

# API settings
export LCC_API_HOST=0.0.0.0
export LCC_API_PORT=8000

# Redis (optional, for caching)
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

### Policy Directory

Policies are stored in `~/.lcc/policies/`:

```
~/.lcc/policies/
├── permissive.yaml
├── strict.yaml
├── copyleft-friendly.yaml
├── ai-ml-permissive.yml
├── ai-ml-research.yml
└── custom-policy.yaml
```

---

## 7. Real-World Examples

### Example 1: Scanning a Python Project

**Scenario:** You're building a Python web application and want to ensure no GPL licenses.

```bash
# Scan with strict policy
lcc scan . --policy strict --report-format html --output compliance.html

# Review report
open compliance.html
```

**Sample Output:**
```
Violations Found: 2
- package-a (GPL-3.0) - Used in src/requirements.txt
- package-b (AGPL-3.0) - Used in src/requirements-dev.txt

Recommendations:
- Replace package-a with alternative-package (MIT)
- Move package-b to dev dependencies only
```

### Example 2: Scanning a JavaScript Monorepo

**Scenario:** Large monorepo with multiple packages, want to enforce consistent licensing.

```bash
# Scan with exclusions
lcc scan . \\
    --exclude node_modules \\
    --exclude dist \\
    --exclude coverage \\
    --policy permissive \\
    --report-format json \\
    --output scan-result.json

# Generate SBOM for each package
for pkg in packages/*; do
    lcc sbom generate scan-result.json \\
        --format cyclonedx \\
        --output "$pkg/sbom.json" \\
        --project-name "$(basename $pkg)"
done
```

### Example 3: GitHub Repository Scanning

**Scenario:** Check license compliance before forking/using an open-source project.

```bash
# Scan via API (using dashboard)
# Or use CLI with cloned repo

# Clone
git clone https://github.com/some/repository.git temp-repo
cd temp-repo

# Scan
lcc scan . --policy permissive

# Cleanup
cd ..
rm -rf temp-repo
```

### Example 4: AI/ML Project with Hugging Face Models

**Scenario:** ML project using Hugging Face models and datasets.

```bash
# Scan project (detects models and datasets)
lcc scan ./ml-project --policy ai-ml-permissive

# View AI-specific licenses
lcc interactive scan-result.json
> filter type:ai_model
> filter type:dataset
```

**Sample Detection:**
```
AI Models Found: 3
- bert-base-uncased (Apache-2.0)
- stable-diffusion-2-1 (OpenRAIL-M)
- llama-2-7b (Llama 2 Community License)

Datasets Found: 2
- squad (CC-BY-SA-4.0)
- common_voice (CC0-1.0)

Warnings:
- Llama 2 license has 700M MAU commercial use limit
- Stable Diffusion OpenRAIL-M has use restrictions
```

### Example 5: CI/CD Integration

**Scenario:** Add license checking to GitHub Actions.

**.github/workflows/license-check.yml:**
```yaml
name: License Compliance

on: [push, pull_request]

jobs:
  license-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install LCC
        run: pip install license-compliance-checker

      - name: Run license scan
        run: |
          lcc scan . --policy strict --report-format json --output scan-result.json

      - name: Upload scan results
        uses: actions/upload-artifact@v3
        with:
          name: license-scan-results
          path: scan-result.json

      - name: Check for violations
        run: |
          violations=$(jq '.summary.violations' scan-result.json)
          if [ "$violations" -gt 0 ]; then
            echo "License violations found!"
            exit 1
          fi
```

### Example 6: Pre-commit Hook

**Scenario:** Check licenses before every commit.

**.git/hooks/pre-commit:**
```bash
#!/bin/bash

echo "Running license compliance check..."

# Scan only staged files
lcc scan . --policy permissive --report-format console

# Check exit code
if [ $? -ne 0 ]; then
    echo "License compliance check failed!"
    echo "Fix violations or use 'git commit --no-verify' to skip"
    exit 1
fi

echo "License compliance check passed!"
```

---

## 8. Integration Patterns

### Docker Compose Setup

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  api:
    image: license-compliance-checker:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_PATH=/app/data/lcc.db
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    volumes:
      - ./data:/app/data
      - ./cache:/app/cache
    command: lcc server --host 0.0.0.0

  dashboard:
    image: lcc-dashboard:latest
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      - api

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

### Kubernetes Deployment

**k8s/deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lcc-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lcc-api
  template:
    metadata:
      labels:
        app: lcc-api
    spec:
      containers:
      - name: api
        image: license-compliance-checker:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_PATH
          value: /data/lcc.db
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: lcc-secrets
              key: github-token
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: lcc-data-pvc
```

### Jenkins Pipeline

**Jenkinsfile:**
```groovy
pipeline {
    agent any

    stages {
        stage('Install LCC') {
            steps {
                sh 'pip install license-compliance-checker'
            }
        }

        stage('License Scan') {
            steps {
                sh '''
                    lcc scan . \\
                        --policy strict \\
                        --report-format json \\
                        --output scan-result.json
                '''
            }
        }

        stage('Generate Reports') {
            steps {
                sh '''
                    lcc report scan-result.json \\
                        --format html \\
                        --output compliance-report.html
                '''
                publishHTML([
                    reportDir: '.',
                    reportFiles: 'compliance-report.html',
                    reportName: 'License Compliance Report'
                ])
            }
        }

        stage('Check Violations') {
            steps {
                script {
                    def result = readJSON file: 'scan-result.json'
                    if (result.summary.violations > 0) {
                        error("License violations found!")
                    }
                }
            }
        }
    }
}
```

---

## 9. Advanced Usage

### Custom Resolvers

Create a custom license resolver:

```python
from lcc.resolution.base import LicenseResolver, Evidence

class MyCustomResolver(LicenseResolver):
    def __init__(self):
        super().__init__(name="my-custom-resolver")

    def resolve(self, component):
        # Custom resolution logic
        license_data = self._fetch_from_custom_source(component)

        if license_data:
            return [Evidence(
                license_expression=license_data['license'],
                source_url=license_data['url'],
                confidence=0.9,
                metadata={'custom': True}
            )]
        return []
```

### Custom Detectors

Create a detector for a new package manager:

```python
from lcc.detection.base import Detector
from lcc.models import Component, ComponentType

class MyPackageDetector(Detector):
    def __init__(self):
        super().__init__(name="my-package")

    def supports(self, path):
        # Check if this detector can handle the path
        return (path / "my-package.lock").exists()

    def discover(self, path):
        # Parse package file and return components
        components = []
        lockfile = path / "my-package.lock"

        for package in self._parse_lockfile(lockfile):
            components.append(Component(
                type=ComponentType.GENERIC,
                name=package['name'],
                version=package['version'],
                namespace=package.get('namespace')
            ))

        return components
```

### Programmatic API Usage

```python
from lcc import Scanner, PolicyManager
from lcc.config import Config
from pathlib import Path

# Initialize
config = Config.load()
scanner = Scanner(config)
policy_manager = PolicyManager(config)

# Scan project
result = scanner.scan(Path("."))

# Apply policy
policy = policy_manager.get_policy("strict")
evaluation = policy.evaluate(result)

# Check violations
if evaluation.violations:
    print(f"Found {len(evaluation.violations)} violations:")
    for violation in evaluation.violations:
        print(f"  - {violation.component.name}: {violation.license}")
```

---

## 10. Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting guide.

**Common Issues:**

1. **Detector not finding packages**
   - Ensure package files exist (package.json, requirements.txt, etc.)
   - Check file permissions
   - Verify package manager is supported

2. **Resolution failures**
   - Check internet connection for registry/GitHub access
   - Verify GitHub token is set (for private repos)
   - Check cache directory permissions

3. **Policy evaluation errors**
   - Validate policy YAML syntax
   - Check policy exists in policy directory
   - Verify SPDX license expressions

4. **API authentication failures**
   - Check JWT token is valid
   - Verify user credentials
   - Check token expiration

---

## Next Steps

- Read the [POLICY_GUIDE.md](POLICY_GUIDE.md) to learn about writing custom policies
- Check [API_GUIDE.md](API_GUIDE.md) for REST API integration
- Review [FAQ.md](FAQ.md) for frequently asked questions
- Join our community discussions

---

**Need Help?**
- 📖 Documentation: https://docs.lcc-project.org
- 💬 Discussions: https://github.com/your/repo/discussions
- 🐛 Issues: https://github.com/your/repo/issues
- 📧 Email: support@lcc-project.org
