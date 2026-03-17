# LCC — License Compliance Checker

**Automated License Compliance for the AI Era.**

LCC is an enterprise-grade, open-source compliance platform designed to secure your software supply chain. It automates license detection, policy enforcement, and compliance reporting across complex polyglot repositories — with first-class support for AI/ML models and datasets.

---

## Why LCC?

In the age of AI and modular software, dependency chains are exploding. Manual compliance reviews effectively halt development velocity. LCC solves this with a single scan command that covers your entire stack.

<div class="grid cards" markdown>

-   :material-language-python:{ .lg .middle } **8+ Ecosystems**

    ---

    Scans Python, JavaScript, Go, Java, Rust, Ruby, .NET, PHP — plus monorepos and nested structures.

-   :material-robot:{ .lg .middle } **AI Model Scanning**

    ---

    First-class support for Hugging Face models and datasets with AI-specific licenses (RAIL, Llama, OpenRAIL).

-   :material-file-document-outline:{ .lg .middle } **SBOM Generation**

    ---

    Produce industry-standard CycloneDX and SPDX Software Bills of Materials with a single command.

-   :material-shield-check:{ .lg .middle } **Policy Engine**

    ---

    Define and enforce compliance policies (e.g., "Ban GPL-3.0 in proprietary projects") using OPA or built-in rules.

</div>

---

## Quick Install

```bash
pip install license-compliance-checker
```

Or run the full stack with Docker:

```bash
git clone https://github.com/apundhir/license-compliance-checker.git
cd license-compliance-checker
docker-compose up -d
```

---

## Quick Scan

```bash
# Scan a local project
lcc scan /path/to/your/project

# Scan a GitHub repository
lcc scan https://github.com/expressjs/express

# Generate an SBOM
lcc sbom /path/to/your/project --format cyclonedx --output sbom.json

# Check against a policy
lcc scan /path/to/your/project --policy my-policy.yml
```

---

## Feature Highlights

| Feature | Description |
|---------|-------------|
| **Multi-Source Resolution** | Combines data from package registries, GitHub, ClearlyDefined, and local filesystem scans |
| **AI-Powered Analysis** | LLM-based license analysis for ambiguous license texts via Fireworks AI |
| **Web Dashboard** | Next.js-based UI for exploring scan results, attribution reports, and policy management |
| **Async Processing** | Redis-backed background job processing for scanning large repositories |
| **Attribution Generation** | Automatically generate compliant NOTICE files for distribution |
| **CI/CD Integration** | Block pull requests that introduce restricted licenses before they merge |

---

## Explore the Docs

| Section | What you will find |
|---------|-------------------|
| [Quick Start](getting-started/quickstart.md) | Go from zero to your first scan in 5 minutes |
| [Installation](getting-started/installation.md) | All installation methods — pip, Docker, from source |
| [User Guide](guides/user.md) | Complete CLI usage, configuration, and workflows |
| [Policy Guide](guides/policies.md) | Create and manage compliance policies |
| [API Reference](reference/api.md) | REST API endpoints, authentication, and examples |
| [Deployment Guide](deployment/index.md) | Production deployment with Docker Compose |
| [Troubleshooting](reference/troubleshooting.md) | Common issues and solutions |
| [FAQ](reference/faq.md) | Frequently asked questions |

---

## License

LCC is licensed under the [Apache 2.0 License](https://github.com/apundhir/license-compliance-checker/blob/main/LICENSE).
