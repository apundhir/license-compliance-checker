# License Compliance Checker - Frequently Asked Questions (FAQ)

## Table of Contents

1. [General Questions](#general-questions)
2. [Installation & Setup](#installation--setup)
3. [Scanning & Detection](#scanning--detection)
4. [License Resolution](#license-resolution)
5. [Policies](#policies)
6. [AI/ML Specific](#aiml-specific)
7. [API & Integration](#api--integration)
8. [Dashboard](#dashboard)
9. [Legal & Compliance](#legal--compliance)
10. [Performance & Scale](#performance--scale)

---

## General Questions

### What is the License Compliance Checker?

LCC is an open-source tool for automated license compliance checking. It scans your projects, detects dependencies, resolves their licenses, and evaluates them against your compliance policies. It supports traditional software dependencies as well as AI/ML models and datasets.

### Why do I need license compliance checking?

License compliance is critical for:
- **Legal risk management**: Avoid license violations and lawsuits
- **Open source governance**: Ensure your use of open source aligns with your policies
- **Supply chain security**: Know what's in your software
- **Regulatory compliance**: Meet requirements like NTIA SBOM mandates
- **Business protection**: Avoid copyleft obligations in proprietary products

### What languages and package managers are supported?

**Traditional Software**:
- **Python**: pip, poetry, pipenv, requirements.txt, pyproject.toml
- **JavaScript/TypeScript**: npm, yarn, pnpm, package.json, package-lock.json
- **Go**: go.mod, go.sum
- **Rust**: Cargo.toml, Cargo.lock
- **Java**: Maven (pom.xml), Gradle (build.gradle)
- **Ruby**: Gemfile, Gemfile.lock
- **.NET**: .csproj, packages.config, PackageReference

**AI/ML**:
- **Hugging Face**: Models and datasets from Hugging Face Hub
- **Datasets**: ImageNet, COCO, OpenImages, and custom datasets
- **Model formats**: PyTorch, TensorFlow, ONNX, Safetensors

### Is LCC free?

Yes, LCC is completely free and open source (Apache-2.0 license). There are no premium tiers, subscriptions, or paid features.

### Who maintains LCC?

LCC is maintained by [your organization/team]. We welcome community contributions!

### How is LCC different from other tools?

**Unique features**:
- **AI/ML native**: First-class support for AI models and datasets
- **Multi-source resolution**: Combines PyPI, npm, GitHub, ClearlyDefined, and more
- **Flexible policies**: YAML-based policies with contexts for different environments
- **Modern architecture**: FastAPI backend, Next.js dashboard, OpenAPI docs
- **Developer-friendly**: CLI, API, SDK, and web UI

**Compared to alternatives**:
- **FOSSA**: LCC is free and open source; FOSSA is commercial
- **Snyk**: LCC focuses on licensing; Snyk focuses on vulnerabilities
- **Black Duck**: LCC is lightweight and fast; Black Duck is enterprise-focused
- **SPDX Tools**: LCC includes policy engine; SPDX Tools are format-focused

---

## Installation & Setup

### How do I install LCC?

Three methods:

1. **Docker (recommended)**:
   ```bash
   docker-compose up -d
   ```

2. **pip**:
   ```bash
   pip install license-compliance-checker
   ```

3. **From source**:
   ```bash
   git clone https://github.com/your-org/lcc.git
   cd lcc
   pip install -e .
   ```

See [USER_GUIDE.md](USER_GUIDE.md) for details.

### What are the system requirements?

**Minimum**:
- Python 3.9+
- 512 MB RAM
- 100 MB disk space

**Recommended**:
- Python 3.11+
- 2 GB RAM
- 1 GB disk space (for cache)
- Docker and Docker Compose (for full stack)

### Do I need a GitHub token?

Not required, but **highly recommended** for:
- Better rate limits (5000/hour vs 60/hour)
- Access to private repositories
- Faster license resolution

Create a token at: https://github.com/settings/tokens

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

### How do I configure LCC?

Three ways (in order of precedence):

1. **Command-line arguments**: `lcc scan . --policy strict`
2. **Environment variables**: `export LCC_POLICY=strict`
3. **Config file**: `~/.lcc/config.yaml`

Example config.yaml:
```yaml
cache_dir: ~/.lcc/cache
database_path: ~/.lcc/lcc.db
policy_dir: ~/.lcc/policies
default_policy: permissive
policy_context: production
```

---

## Scanning & Detection

### How do I run my first scan?

```bash
# Basic scan
lcc scan .

# With policy
lcc scan . --policy permissive --context production

# With output
lcc scan . --output report.json --format json
```

### Why does my scan find 0 components?

Common causes:
1. **Wrong directory**: Ensure you're in the project root
2. **No manifest files**: Check if package.json, requirements.txt, etc. exist
3. **Unsupported language**: Verify your language is supported
4. **Manifest in subdirectory**: Use `--recursive` flag

Debug:
```bash
# Check what files LCC sees
lcc scan . --verbose

# List supported detectors
lcc detectors list
```

### Can I scan a GitHub repository without cloning it?

Yes, use the API:

```bash
curl -X POST http://localhost:8000/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'
```

Or scan after cloning:
```bash
git clone https://github.com/user/repo
cd repo
lcc scan .
```

### How do I exclude directories from scanning?

```bash
# Single exclude
lcc scan . --exclude "node_modules"

# Multiple excludes
lcc scan . --exclude "node_modules" --exclude "vendor" --exclude ".venv"

# Wildcard patterns
lcc scan . --exclude "*/test/*" --exclude "*.min.js"
```

Or in config.yaml:
```yaml
detection:
  exclude_patterns:
    - node_modules
    - vendor
    - .venv
    - "*/test/*"
```

### How long does a scan take?

**Typical times**:
- Small project (< 50 deps): 10-30 seconds
- Medium project (50-200 deps): 30-120 seconds
- Large project (200-500 deps): 2-5 minutes
- Very large project (500+ deps): 5-15 minutes

**Factors**:
- Number of dependencies
- Network speed (for remote resolution)
- GitHub rate limits
- Cache hit rate

**Speed up scans**:
- Use cache
- Set GitHub token
- Exclude unnecessary directories
- Use faster resolvers only

---

## License Resolution

### How does license resolution work?

LCC uses a multi-source resolution chain:

1. **Registry metadata**: npm, PyPI, crates.io, etc. (fastest)
2. **ClearlyDefined**: Curated license data
3. **GitHub API**: License detection from repo
4. **Filesystem**: Local LICENSE files

First successful resolution wins.

### What does "UNKNOWN" license mean?

"UNKNOWN" means LCC couldn't determine the license from any source. This happens when:
- Package has no license metadata in registry
- No LICENSE file in repository
- Private/proprietary package
- Incorrect package metadata

**How to fix**:
1. Check upstream source manually
2. Add override in policy:
   ```yaml
   overrides:
     package-name:
       license: MIT
       reason: "Verified from GitHub"
   ```

### Can I override license detection?

Yes, use overrides in your policy:

```yaml
overrides:
  my-package:
    license: Apache-2.0
    reason: "Upstream fixed metadata after version X"

  proprietary-lib:
    license: Proprietary-CompanyName
    reason: "Internal library"
```

### How are dual licenses handled?

LCC supports SPDX expressions like `MIT OR Apache-2.0`. Policy controls preference:

```yaml
contexts:
  production:
    dual_license_preference: most_permissive  # Choose MIT
    # or
    dual_license_preference: avoid_copyleft  # Choose Apache-2.0
    # or
    dual_license_preference: prefer_order
    preferred_order:
      - Apache-2.0
      - MIT
```

---

## Policies

### What policies are included?

Five built-in policies:

1. **permissive**: For SaaS and proprietary software (avoid copyleft)
2. **copyleft-friendly**: For open source projects (allow GPL)
3. **ai-ml-research**: For academic AI/ML research (very permissive)
4. **ai-ml-permissive**: For commercial AI/ML (no non-commercial licenses)
5. **ai-ml-strict**: For enterprise AI/ML (very strict)

See [POLICY_GUIDE.md](POLICY_GUIDE.md) for details.

### How do I create a custom policy?

Start with a template:

```bash
# Copy existing policy
cp ~/.lcc/policies/permissive.yaml ~/.lcc/policies/my-policy.yaml

# Edit
vim ~/.lcc/policies/my-policy.yaml

# Test
lcc scan . --policy my-policy --dry-run

# Validate
lcc policy validate my-policy
```

See [POLICY_GUIDE.md](POLICY_GUIDE.md) for complete guide.

### What's the difference between "deny" and "review"?

- **Deny**: License is prohibited; scan fails (violation)
- **Review**: License requires human review; scan warns but doesn't fail
- **Allow**: License is approved; no action needed

Example:
```yaml
allow:
  - MIT
  - Apache-2.0
review:
  - LGPL-3.0  # May be OK with dynamic linking
deny:
  - GPL-3.0   # Never acceptable for our product
```

### Can I have different policies for different projects?

Yes! Use policy contexts or separate policy files:

**Option 1: Contexts within one policy**
```yaml
# company-policy.yaml
contexts:
  saas-product:
    deny: [GPL-*, AGPL-*]
  open-source:
    allow: [GPL-*, AGPL-*]
```

```bash
lcc scan ./saas --policy company-policy --context saas-product
lcc scan ./oss --policy company-policy --context open-source
```

**Option 2: Separate policies**
```bash
lcc scan ./saas --policy saas-strict
lcc scan ./oss --policy open-source-friendly
```

---

## AI/ML Specific

### What AI/ML licenses are supported?

**Model licenses**:
- OpenRAIL (variants: OpenRAIL-M, OpenRAIL++, CreativeML-OpenRAIL-M)
- Llama 2, Llama 3, Llama 3.1
- DeepMind Gemma
- BigScience BLOOM RAIL
- Mistral AI
- Apache-2.0-AI, MIT-AI (AI-specific versions)

**Dataset licenses**:
- Creative Commons (CC0, CC-BY, CC-BY-SA, CC-BY-NC, CC-BY-ND)
- Open Data Commons (ODC-BY, ODbL, PDDL)
- CDLA (Permissive, Sharing)
- ImageNet, COCO, OpenImages (research-only)

### How do I scan Hugging Face models?

LCC automatically detects models referenced in your code:

```python
# models.txt or requirements.txt
transformers
bert-base-uncased

# Or in code
from transformers import AutoModel
model = AutoModel.from_pretrained("bert-base-uncased")
```

LCC will detect and resolve the model license from Hugging Face Hub.

### Can I use non-commercial licenses for research?

Yes! Use the `ai-ml-research` policy:

```bash
lcc scan . --policy ai-ml-research --context research
```

This allows:
- CC-BY-NC (non-commercial)
- ImageNet (research-only)
- Kaggle competition datasets
- All model licenses

### What's the difference between the AI/ML policies?

| Policy | Use Case | Non-Commercial | Research-Only | Restrictions |
|--------|----------|----------------|---------------|--------------|
| **ai-ml-research** | Academia | ✅ Allowed | ✅ Allowed | Very few |
| **ai-ml-permissive** | Commercial | ❌ Denied | ❌ Denied | Moderate |
| **ai-ml-strict** | Enterprise | ❌ Denied | ❌ Denied | Many |

See [POLICY_GUIDE.md](POLICY_GUIDE.md) for complete comparison.

---

## API & Integration

### How do I start the API server?

Three methods:

1. **Docker** (recommended):
   ```bash
   docker-compose up -d
   # API at http://localhost:8000
   ```

2. **CLI**:
   ```bash
   lcc server
   ```

3. **Python**:
   ```python
   from lcc.api.server import create_app
   app = create_app()
   # Run with uvicorn
   ```

### How do I authenticate with the API?

1. Create user:
   ```bash
   lcc auth create-user admin password123 --role admin
   ```

2. Login:
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -d "username=admin&password=password123"
   ```

3. Use token:
   ```bash
   TOKEN="eyJ..."
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/scans
   ```

See [API_GUIDE.md](API_GUIDE.md) for complete documentation.

### Can I integrate LCC with CI/CD?

Yes! Examples for popular platforms:

**GitHub Actions**:
```yaml
- name: License Compliance
  run: |
    pip install license-compliance-checker
    lcc scan . --policy strict --fail-on violation
```

**GitLab CI**:
```yaml
license-check:
  script:
    - lcc scan . --policy strict --fail-on violation
```

**Jenkins**:
```groovy
stage('License Compliance') {
  sh 'lcc scan . --policy strict --fail-on violation'
}
```

See [USER_GUIDE.md](USER_GUIDE.md) for complete examples.

### Is there a Python SDK?

Yes! LCC is a Python library:

```python
from lcc.scanner import Scanner
from lcc.factory import build_detectors, build_resolvers
from lcc.config import load_config
from lcc.cache import Cache

config = load_config()
cache = Cache(config)
scanner = Scanner(build_detectors(), build_resolvers(config, cache), config)

report = scanner.scan("/path/to/project")
for finding in report.findings:
    print(f"{finding.component.name}: {finding.resolved_license}")
```

See [API_GUIDE.md](API_GUIDE.md) for programmatic API examples.

---

## Dashboard

### How do I access the dashboard?

1. Start services:
   ```bash
   docker-compose up -d
   ```

2. Visit: http://localhost:3000

3. Login with credentials created via CLI:
   ```bash
   lcc auth create-user admin password123 --role admin --email admin@company.com
   ```

### What features does the dashboard have?

- **Scans page**: View all scans, filter, search
- **Scan details**: Detailed findings, violations, warnings
- **Policies page**: View and manage policies
- **Analytics page**: License distribution, trends, top projects
- **Dashboard**: Summary statistics and visualizations
- **SBOM page**: Instructions for generating SBOMs
- **Account page**: User profile and settings

### Can I customize the dashboard?

Yes! The dashboard is built with Next.js and shadcn/ui. Fork the repo and modify:

```bash
cd dashboard/
npm install
npm run dev
```

See [dashboard/README.md](../dashboard/README.md) for development guide.

### Does the dashboard work offline?

No, the dashboard requires the API server to be running. Both can run locally without internet access, but you need both services.

---

## Legal & Compliance

### Is LCC legally binding?

**No.** LCC is an automation tool that provides information and analysis. It should not be considered legal advice. Always consult qualified legal counsel for compliance decisions.

Every policy includes a disclaimer to this effect.

### Can LCC guarantee 100% license detection accuracy?

No tool can guarantee 100% accuracy because:
- Package metadata can be wrong or missing
- Licenses can change between versions
- Custom/proprietary licenses may not be in databases
- Dual licenses require interpretation

**Best practices**:
- Review "UNKNOWN" licenses manually
- Audit critical dependencies
- Maintain overrides for known issues
- Regularly update scans

### How do I handle license violations?

1. **Identify**: LCC flags violations based on policy
2. **Investigate**: Check why the component is included
3. **Options**:
   - **Replace**: Find alternative with compatible license
   - **Remove**: Remove dependency if not critical
   - **Relicense**: Contact upstream to change license
   - **Exception**: Get legal approval for exception
   - **Isolate**: Architect around copyleft restrictions (e.g., dynamic linking)

4. **Document**: Add to policy overrides with reasoning

### What about license compatibility?

LCC evaluates individual licenses against policy, but doesn't check cross-license compatibility (e.g., GPL-2.0 incompatible with Apache-2.0).

**Manual check needed for**:
- Combining GPL-2.0 with Apache-2.0
- Mixing GPL and AGPL
- Combining copyleft licenses
- License compatibility in derivatives

### How do I comply with NTIA SBOM requirements?

Generate SBOM in CycloneDX or SPDX format:

```bash
# CycloneDX (recommended for NTIA)
lcc sbom --scan-id <ID> --format cyclonedx --output sbom.json

# SPDX
lcc sbom --scan-id <ID> --format spdx --output sbom.spdx.json
```

NTIA minimum elements:
- ✅ Supplier name
- ✅ Component name
- ✅ Version
- ✅ Other unique identifiers
- ✅ Dependency relationships
- ✅ Timestamp

All included in LCC SBOM output.

---

## Performance & Scale

### How many dependencies can LCC handle?

**Tested scales**:
- **Small projects**: < 50 deps (10-30s)
- **Medium projects**: 50-200 deps (30-120s)
- **Large projects**: 200-500 deps (2-5 min)
- **Very large projects**: 500-1000 deps (5-15 min)
- **Enterprise monorepos**: 1000+ deps (15-60 min)

**Bottlenecks**:
- GitHub API rate limits (5000/hour with token)
- Network latency
- Database I/O (SQLite can be slow for many concurrent writes)

### How do I speed up scans?

1. **Use cache**:
   ```yaml
   cache:
     enabled: true
     ttl: 604800  # 7 days
   ```

2. **Set GitHub token**:
   ```bash
   export GITHUB_TOKEN="ghp_..."
   ```

3. **Exclude unnecessary directories**:
   ```bash
   lcc scan . --exclude "node_modules" --exclude "vendor"
   ```

4. **Use faster resolvers**:
   ```yaml
   resolvers:
     - registry  # Fastest
     - clearlydefined
     # Disable GitHub resolver if not needed
   ```

5. **Scan in parallel** (for multiple projects):
   ```bash
   # Using GNU parallel
   find . -name package.json -exec dirname {} \; | parallel lcc scan {}
   ```

### Can I run LCC in production?

Yes! LCC is designed for production use:

**Architecture**:
- FastAPI for high-performance API
- SQLite for simple deployments (or PostgreSQL for scale)
- Redis for caching (optional)
- Docker for easy deployment

**Scaling**:
- Horizontal scaling: Run multiple API instances behind load balancer
- Vertical scaling: Increase resources per instance
- Caching: Use Redis for shared cache across instances

**Monitoring**:
- Health check: `GET /health`
- Metrics: Prometheus-compatible (planned)
- Logging: Structured JSON logs

### What are the resource requirements for production?

**Small deployment** (< 100 scans/day):
- 1 vCPU
- 2 GB RAM
- 10 GB disk

**Medium deployment** (100-1000 scans/day):
- 2-4 vCPU
- 4-8 GB RAM
- 50 GB disk

**Large deployment** (1000+ scans/day):
- 4-8 vCPU
- 8-16 GB RAM
- 100+ GB disk
- Consider PostgreSQL instead of SQLite
- Consider Redis for distributed cache
- Multiple API instances

---

## Still Have Questions?

### Documentation

- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md) - Complete CLI and usage guide
- **Policy Guide**: [POLICY_GUIDE.md](POLICY_GUIDE.md) - Policy creation and management
- **API Guide**: [API_GUIDE.md](API_GUIDE.md) - REST API documentation
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions

### Community

- **GitHub Issues**: https://github.com/your-org/lcc/issues - Bug reports and feature requests
- **GitHub Discussions**: https://github.com/your-org/lcc/discussions - Q&A and community help
- **Email**: support@lcc.dev - Direct support

### Contributing

Want to help improve LCC? See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to contribute code
- How to report bugs
- How to suggest features
- Development setup guide

---

*Last updated: 2024-10-30*
