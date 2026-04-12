# License Compliance Checker (LCC)

[![PyPI](https://img.shields.io/pypi/v/license-compliance-checker.svg)](https://pypi.org/project/license-compliance-checker/)
[![CI](https://github.com/aiexponenthq/license-compliance-checker/actions/workflows/ci.yml/badge.svg)](https://github.com/aiexponenthq/license-compliance-checker/actions)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Article%2053-gold.svg)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689)

**Know what you ship. Know what you owe.**

The only open-source scanner that combines dependency license detection, AI model license analysis, and EU AI Act Article 53 compliance — in a single tool.

Built by [AiExponent LLC](https://aiexponent.com). Apache 2.0. Free alternative to FOSSA ($50K+/yr) and Black Duck ($30K+/yr).

---

## Quick Start

```bash
pip install license-compliance-checker

# Scan a project
lcc scan .

# Scan with EU AI Act compliance policy
lcc scan . --policy eu-ai-act-compliance --format json

# Generate a CycloneDX SBOM
lcc sbom generate --input scan-report.json --format cyclonedx --output sbom.json

# Check GPL contamination in a SaaS context
lcc scan . --project-license Apache-2.0 --context saas
```

---

## Why LCC

| | LCC | FOSSA | Black Duck |
|---|---|---|---|
| AI model license detection | ✅ | ❌ | ❌ |
| EU AI Act Article 53 output | ✅ | ❌ | ❌ |
| HuggingFace Hub API resolver | ✅ | ❌ | ❌ |
| GGUF / ONNX model scanning | ✅ | ❌ | ❌ |
| Training data risk registry | ✅ | ❌ | ❌ |
| SBOM (CycloneDX + SPDX) | ✅ | ✅ | ✅ |
| Policy-as-code (OPA / YAML) | ✅ | ✅ | ✅ |
| Price | **Free** | $50K+/yr | $30K+/yr |

---

## Architecture

```mermaid
graph TD
    CLI["CLI · FastAPI Server · GitHub Action · VS Code Extension"]
    DET["Detectors\nPython · Node.js · Go · Rust · Ruby\nJava · .NET · HuggingFace · GGUF/ONNX"]
    RES["Resolvers\nPyPI · npm · Crates.io · Maven\nGitHub API · ClearlyDefined · HF Hub API"]
    POL["Policy Engine\nOPA Rego · YAML policies\nPermissive · Strict · EU AI Act"]
    REG["Regulatory Assessor\nEU AI Act Article 53\nNIST AI RMF · ISO 42001"]
    OUT["Outputs\nJSON · HTML · Markdown · CSV\nCycloneDX SBOM · SPDX SBOM\nArticle 53 compliance pack"]

    CLI --> DET
    DET -->|"detected components"| RES
    RES -->|"resolved licenses"| POL
    POL -->|"violations + warnings"| REG
    REG --> OUT

    style CLI fill:#1e3a5f,color:#fff
    style DET fill:#1e3a5f,color:#fff
    style RES fill:#1e3a5f,color:#fff
    style POL fill:#c9a84c,color:#000
    style REG fill:#c9a84c,color:#000
    style OUT fill:#2d5a2d,color:#fff
```

---

## Ecosystem Coverage

```mermaid
graph LR
    LCC["LCC\nScanner"]

    PY["Python\npip · Poetry · Conda"]
    JS["JavaScript\nnpm · Yarn · pnpm"]
    GO["Go\ngo.mod"]
    RS["Rust\nCargo.toml"]
    JV["Java\nMaven · Gradle"]
    RB["Ruby\nBundler"]
    DN[".NET\nNuGet"]
    HF["HuggingFace\nHub API · Model cards\nGGUF · ONNX"]

    LCC --> PY
    LCC --> JS
    LCC --> GO
    LCC --> RS
    LCC --> JV
    LCC --> RB
    LCC --> DN
    LCC --> HF

    style LCC fill:#1e3a5f,color:#fff
    style HF fill:#c9a84c,color:#000
```

---

## EU AI Act Article 53 Coverage

August 2025 — GPAI obligations are **already enforced**. Providers of general-purpose AI models must publish technical documentation. LCC automates evidence gathering for each sub-obligation:

```mermaid
graph TD
    A53["Article 53\nObligations"]

    A["53(1)(a)\nTechnical documentation\n→ SBOM with model type,\nversion, license metadata"]
    B["53(1)(b)\nDownstream provider info\n→ Model card capabilities\nand limitations extracted"]
    C["53(1)(c)\nCopyright policy\n→ Training data licenses\nand copyright flags"]
    D["53(1)(d)\nTraining data summary\n→ Dataset descriptions\nfrom model cards"]
    E["53(2)\nSystemic risk\n→ 65B+ parameter\nmodel detection"]

    A53 --> A
    A53 --> B
    A53 --> C
    A53 --> D
    A53 --> E

    style A53 fill:#1e3a5f,color:#fff
    style A fill:#1e3a5f,color:#fff
    style B fill:#1e3a5f,color:#fff
    style C fill:#1e3a5f,color:#fff
    style D fill:#1e3a5f,color:#fff
    style E fill:#c9a84c,color:#000
```

> **Scope note:** LCC generates audit evidence for Article 53 documentation obligations. It is not a legal compliance determination. Involve qualified legal counsel for final compliance assessment.

---

## AI Model Detection

LCC scans your codebase for AI model references without requiring a local download:

```bash
# Detects from_pretrained("org/model") references in Python / YAML / JSON
lcc scan .

# Detects GGUF and ONNX model files (Ollama / llama.cpp)
lcc scan /path/to/models

# Full transitive scan with lock file
lcc scan . --include-transitive --policy permissive
```

**Supported AI license formats:** RAIL, OpenRAIL, Llama 2/3/3.1, Gemma, Mistral, Mixtral, BigScience, Falcon, Grok, DeepSeek, and 20+ more.

**Training data risk registry:** Flags datasets with commercial use risk — OpenAI API outputs, ShareGPT, Books3, The Pile classified as high/critical risk.

---

## Policy Enforcement

```bash
# Built-in policies
lcc scan . --policy permissive            # Allow MIT, Apache-2.0, BSD only
lcc scan . --policy strict                # Block all copyleft
lcc scan . --policy eu-ai-act-compliance  # Article 53 GPAI obligations

# Custom policy (YAML)
cat > my-policy.yaml << EOF
name: my-saas-policy
rules:
  - license: GPL-3.0
    action: block
    reason: "GPL-3.0 requires SaaS source disclosure"
  - license: AGPL-3.0
    action: block
  - license: RAIL
    action: warn
    reason: "Review RAIL restrictions before deploying"
EOF

lcc scan . --policy my-policy.yaml
```

---

## CI/CD Integration

```yaml
# .github/workflows/license-check.yml
- name: License compliance scan
  uses: aiexponenthq/license-compliance-checker/.github/actions/license-compliance@v1
  with:
    path: .
    policy: eu-ai-act-compliance
    fail-on: violations
    format: sarif
    output: license-scan.sarif
```

---

## SBOM Generation

```bash
# CycloneDX 1.4 with EU AI Act regulatory extensions
lcc sbom generate --input scan-report.json --format cyclonedx --output sbom.cdx.json

# SPDX 2.3
lcc sbom generate --input scan-report.json --format spdx --output sbom.spdx.json

# Sign with GPG for tamper-evidence
lcc sbom sign --input sbom.cdx.json --key ~/.gnupg/key.gpg
```

---

## AiExponent Toolchain

```mermaid
graph LR
    TF["TraceForge\n(Art. 10 data governance)"]
    LCC["LCC\n(Art. 53 license compliance)"]
    RAG["rag-benchmarking\n(Art. 15 accuracy)"]
    RF["RiskForge\n(Art. 9 risk management)"]
    TD["TransparencyDeck\n(Art. 13 documentation)"]

    TF -->|"data provenance"| LCC
    LCC -->|"license evidence"| RF
    RAG -->|"accuracy evidence"| RF
    RF -->|"rmf.json"| TD

    style LCC fill:#c9a84c,color:#000
    style RF fill:#1e3a5f,color:#fff
    style TF fill:#1e3a5f,color:#fff
    style RAG fill:#1e3a5f,color:#fff
    style TD fill:#1e3a5f,color:#fff
```

---

## Known Limitations

- HuggingFace Hub API scanning requires referenced model IDs (not local downloads only).
- SPDX `AND`/`OR` compound expressions are flagged for manual review, not auto-resolved.
- Transitive dependency resolution requires a lock file (`poetry.lock`, `package-lock.json`).
- Article 53 assessment covers documentation completeness only — not a legal compliance determination.
- Training data risk registry covers top-50 known datasets; unknown datasets flagged for review.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and PRs welcome.

```bash
git clone https://github.com/aiexponenthq/license-compliance-checker
cd license-compliance-checker
pip install -e ".[dev]"
pytest
```

---

## License

[Apache 2.0](LICENSE) — free to use, modify, and distribute.

Built by [AiExponent LLC](https://aiexponent.com) — `hello@aiexponent.com`

---

*Part of the AiExponent open-source AI governance toolchain:
**license-compliance-checker** ·
[rag-benchmarking](https://github.com/aiexponenthq/rag-benchmarking) ·
[RiskForge](https://github.com/aiexponenthq/riskforge)*
