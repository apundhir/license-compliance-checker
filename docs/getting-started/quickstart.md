# Quick Start

Get from zero to your first compliance scan in under 5 minutes.

---

## 1. Install

```bash
pip install license-compliance-checker
```

Verify the installation:

```bash
lcc --version
```

!!! tip "Prefer Docker?"
    If you want the full stack (API + Dashboard + Workers), see the [Installation Guide](installation.md#method-1-docker-recommended) for Docker instructions.

---

## 2. Scan a Project

Point LCC at any local project directory:

```bash
lcc scan /path/to/your/project
```

Or scan a remote GitHub repository directly:

```bash
lcc scan https://github.com/expressjs/express
```

**Expected output:**

```
Scanning /path/to/your/project...
Found 3 manifest files
Detected 47 dependencies

Results:
  MIT          : 32
  Apache-2.0   : 10
  BSD-3-Clause :  3
  ISC          :  2

✓ Scan complete. No policy violations found.
```

---

## 3. View Results

Get a detailed report with the `--format` flag:

```bash
lcc scan /path/to/your/project --format table
```

Or export to JSON for programmatic use:

```bash
lcc scan /path/to/your/project --format json --output results.json
```

---

## 4. Generate an SBOM

Create a Software Bill of Materials in CycloneDX or SPDX format:

```bash
# CycloneDX format
lcc sbom /path/to/your/project --format cyclonedx --output sbom.json

# SPDX format
lcc sbom /path/to/your/project --format spdx --output sbom.spdx.json
```

---

## 5. Check Against a Policy

Enforce compliance rules by scanning with a policy file:

```bash
lcc scan /path/to/your/project --policy my-policy.yml
```

Example policy file (`my-policy.yml`):

```yaml
name: proprietary-safe
description: Block copyleft licenses in proprietary projects
rules:
  - license: GPL-3.0-only
    action: deny
  - license: AGPL-3.0-only
    action: deny
  - license: GPL-2.0-only
    action: warn
```

**Expected output with violations:**

```
Scanning /path/to/your/project...
Found 47 dependencies

⚠ Policy Violations:
  DENY  : some-package@1.2.0 — GPL-3.0-only
  WARN  : another-pkg@0.9.1 — GPL-2.0-only

✗ Scan complete. 1 deny violation, 1 warning.
```

---

## Next Steps

| Topic | Link |
|-------|------|
| All installation methods (Docker, pip, source) | [Installation Guide](installation.md) |
| Full CLI reference and configuration options | [User Guide](../guides/user.md) |
| Creating and managing compliance policies | [Policy Guide](../guides/policies.md) |
| REST API for CI/CD integration | [API Reference](../reference/api.md) |
| Deploy the full stack to production | [Deployment Guide](../deployment/index.md) |
