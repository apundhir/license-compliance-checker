# License Compliance Checker - Policy Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Policy Basics](#policy-basics)
3. [Writing Your First Policy](#writing-your-first-policy)
4. [Context System](#context-system)
5. [Rule Configuration](#rule-configuration)
6. [Built-in Policy Templates](#built-in-policy-templates)
7. [Advanced Topics](#advanced-topics)
8. [Best Practices](#best-practices)

---

## Introduction

Policies are the heart of the License Compliance Checker. They define what licenses are acceptable, which require review, and which must be denied for your specific use case. LCC uses YAML-based policy files that are flexible, human-readable, and version-controllable.

### Why Policy-Based Compliance?

- **Contextual**: Different rules for development, production, SaaS, embedded systems, research, etc.
- **Auditable**: Version control your compliance decisions alongside your code
- **Collaborative**: Legal, engineering, and compliance teams work from the same source of truth
- **Automated**: Integrate into CI/CD pipelines for continuous compliance checking
- **Flexible**: Wildcard patterns, dual-license handling, and custom reasoning

### Policy Philosophy

LCC follows a **defense-in-depth** approach:

1. **Allow**: Licenses explicitly approved for this context
2. **Review**: Licenses that require human review before use
3. **Deny**: Licenses that are prohibited for this context

When in doubt, LCC defaults to **review** rather than auto-deny, encouraging informed decisions.

---

## Policy Basics

### Policy File Structure

Every policy file is a YAML document with the following structure:

```yaml
name: my-policy
version: "1.0"
description: Brief description of this policy's purpose
disclaimer: Legal disclaimer and usage guidance
default_context: production  # Which context to use by default
contexts:
  production:
    description: Rules for production deployments
    allow: [...]
    deny: [...]
    review: [...]
    deny_reasons: {...}
    review_reasons: {...}
    dual_license_preference: most_permissive
    explanation: [...]
```

### Required Fields

- **name**: Unique identifier for the policy (alphanumeric and hyphens)
- **version**: Semantic version string (e.g., "1.0", "2.1.3")
- **description**: Brief explanation of the policy's purpose
- **contexts**: At least one context with allow/deny/review rules

### Optional Fields

- **disclaimer**: Legal disclaimer or usage guidance
- **default_context**: Which context to use when not explicitly specified
- **explanation**: Additional context for policy decisions

### File Naming

Policy files should use either `.yaml` or `.yml` extension:
- `my-policy.yaml`
- `ai-ml-research.yml`

Store policies in:
- System default: `~/.lcc/policies/`
- Custom location: Set `policy_dir` in config or `LCC_POLICY_DIR` environment variable

---

## Writing Your First Policy

Let's create a simple policy for a startup building a SaaS product.

### Step 1: Basic Metadata

```yaml
name: startup-saas
version: "1.0"
description: Policy for a SaaS startup avoiding copyleft licenses
disclaimer: |
  This policy reflects our current business model and compliance capacity.
  Consult legal counsel before making exceptions.
default_context: production
```

### Step 2: Define Production Context

```yaml
contexts:
  production:
    description: Rules for production SaaS deployment

    # Explicitly allowed - permissive licenses
    allow:
      - MIT
      - Apache-2.0
      - BSD-2-Clause
      - BSD-3-Clause
      - ISC
      - CC0-1.0

    # Denied - copyleft and restrictive licenses
    deny:
      - GPL-*        # Strong copyleft
      - AGPL-*       # Network copyleft
      - SSPL-1.0     # Service-Source copyleft
      - BUSL-1.1     # Business Source (time-delayed)

    # Review - weak copyleft and uncommon licenses
    review:
      - LGPL-*       # Weak copyleft (may be OK with dynamic linking)
      - MPL-2.0      # File-level copyleft
      - EPL-2.0      # Eclipse Public License
```

### Step 3: Add Reasoning

```yaml
    deny_reasons:
      GPL-*: "Strong copyleft incompatible with proprietary SaaS model"
      AGPL-*: "Network copyleft requires source distribution to users"
      SSPL-1.0: "Service-Source obligations conflict with hosted service"
      BUSL-1.1: "Time-delayed open source creates uncertainty"

    review_reasons:
      LGPL-*: "May be acceptable if dynamically linked; verify architecture"
      MPL-2.0: "File-level copyleft acceptable with proper isolation"
      EPL-2.0: "Weak copyleft; verify compatibility with distribution model"
```

### Step 4: Configure Dual-License Handling

```yaml
    dual_license_preference: most_permissive
    explanation:
      - "When components offer multiple licenses, select the most permissive"
      - "Example: MIT OR GPL-3.0 → choose MIT"
```

### Step 5: Add Development Context

```yaml
  development:
    description: Rules for development and testing (more permissive)

    allow:
      - MIT
      - Apache-2.0
      - BSD-*
      - ISC
      - LGPL-*       # OK for development/testing

    review:
      - GPL-*        # Flag but don't block in development
      - AGPL-*

    deny:
      - SSPL-1.0     # Never acceptable

    deny_reasons:
      SSPL-1.0: "Not OSI-approved; potential licensing contamination"

    review_reasons:
      GPL-*: "Flag for legal review before production use"
      AGPL-*: "Network copyleft; acceptable for dev tools but not production"

    dual_license_preference: avoid_copyleft
```

### Complete Example

Save this as `~/.lcc/policies/startup-saas.yaml`:

```yaml
name: startup-saas
version: "1.0"
description: Policy for a SaaS startup avoiding copyleft licenses
disclaimer: |
  This policy reflects our current business model and compliance capacity.
  Consult legal counsel before making exceptions.
default_context: production

contexts:
  production:
    description: Rules for production SaaS deployment
    allow:
      - MIT
      - Apache-2.0
      - BSD-2-Clause
      - BSD-3-Clause
      - ISC
      - CC0-1.0
    deny:
      - GPL-*
      - AGPL-*
      - SSPL-1.0
      - BUSL-1.1
    review:
      - LGPL-*
      - MPL-2.0
      - EPL-2.0
    deny_reasons:
      GPL-*: "Strong copyleft incompatible with proprietary SaaS model"
      AGPL-*: "Network copyleft requires source distribution to users"
      SSPL-1.0: "Service-Source obligations conflict with hosted service"
      BUSL-1.1: "Time-delayed open source creates uncertainty"
    review_reasons:
      LGPL-*: "May be acceptable if dynamically linked; verify architecture"
      MPL-2.0: "File-level copyleft acceptable with proper isolation"
      EPL-2.0: "Weak copyleft; verify compatibility with distribution model"
    dual_license_preference: most_permissive
    explanation:
      - "When components offer multiple licenses, select the most permissive"
      - "Example: MIT OR GPL-3.0 → choose MIT"

  development:
    description: Rules for development and testing (more permissive)
    allow:
      - MIT
      - Apache-2.0
      - BSD-*
      - ISC
      - LGPL-*
    review:
      - GPL-*
      - AGPL-*
    deny:
      - SSPL-1.0
    deny_reasons:
      SSPL-1.0: "Not OSI-approved; potential licensing contamination"
    review_reasons:
      GPL-*: "Flag for legal review before production use"
      AGPL-*: "Network copyleft; acceptable for dev tools but not production"
    dual_license_preference: avoid_copyleft
```

### Testing Your Policy

```bash
# Test the policy against your project
lcc scan . --policy startup-saas --context production

# Test with development context
lcc scan . --policy startup-saas --context development

# Validate policy syntax
lcc policy validate startup-saas
```

---

## Context System

Contexts allow you to define different compliance rules for different use cases within a single policy file.

### Common Context Patterns

#### 1. Deployment Contexts

```yaml
contexts:
  development:
    description: Local development and testing
    # More permissive

  staging:
    description: Staging environment for QA
    # Moderate restrictions

  production:
    description: Production deployment
    # Strictest rules
```

#### 2. Distribution Contexts

```yaml
contexts:
  internal:
    description: Internal tools and prototypes
    # Permissive, including copyleft

  saas:
    description: Hosted service
    # Avoid copyleft, especially AGPL

  distribution:
    description: Distributing binaries or source
    # Copyleft acceptable with compliance workflow

  embedded:
    description: Embedded systems and IoT
    # Very restrictive, avoid copyleft
```

#### 3. Research/Commercial Contexts

```yaml
contexts:
  research:
    description: Academic and non-commercial research
    # Very permissive, allow non-commercial licenses

  publication:
    description: Code/models included in academic papers
    # Restrictive, must be redistributable

  teaching:
    description: Educational use in courses
    # Moderate, allow non-commercial

  commercial:
    description: Commercial products and services
    # Strict, no non-commercial licenses
```

### Choosing the Right Context

When scanning, specify the context explicitly:

```bash
# Use specific context
lcc scan . --policy my-policy --context production

# Use default context (from policy's default_context field)
lcc scan . --policy my-policy

# Override default context
lcc scan . --policy my-policy --context development
```

### Context Inheritance

Contexts are independent; they do not inherit from each other. If you want shared rules, consider:

1. **YAML anchors and aliases**:

```yaml
contexts:
  _base: &base
    allow:
      - MIT
      - Apache-2.0

  production:
    <<: *base
    deny:
      - GPL-*

  development:
    <<: *base
    review:
      - GPL-*
```

2. **Multiple policies**: Create a base policy and specialized policies that reference it

---

## Rule Configuration

### Allow Lists

Licenses explicitly approved for use:

```yaml
allow:
  - MIT
  - Apache-2.0
  - BSD-2-Clause
  - BSD-3-Clause
```

### Deny Lists

Licenses that are prohibited:

```yaml
deny:
  - GPL-3.0
  - AGPL-3.0
  - SSPL-1.0
```

### Review Lists

Licenses requiring human review:

```yaml
review:
  - LGPL-2.1
  - LGPL-3.0
  - MPL-2.0
```

### Wildcard Patterns

Use wildcards for license families:

```yaml
allow:
  - BSD-*          # Matches BSD-2-Clause, BSD-3-Clause, BSD-4-Clause, etc.
  - Apache-*       # Matches Apache-2.0, Apache-1.1, etc.

deny:
  - GPL-*          # Matches GPL-2.0, GPL-3.0, GPL-2.0-or-later, etc.
  - AGPL-*         # Matches all AGPL variants

review:
  - LGPL-*         # Matches all LGPL versions
  - CC-BY-NC-*     # Matches all Creative Commons Non-Commercial licenses
```

### Reasoning

Always provide clear reasoning for deny and review decisions:

```yaml
deny_reasons:
  GPL-3.0: "Strong copyleft requires source distribution"
  AGPL-3.0: "Network copyleft incompatible with SaaS model"
  SSPL-1.0: "Not OSI-approved; Service-Source obligations unclear"

review_reasons:
  LGPL-2.1: "Weak copyleft acceptable with dynamic linking"
  MPL-2.0: "File-level copyleft requires architectural review"
  Unlicense: "Public domain dedication may have jurisdiction issues"
```

### Dual-License Preferences

When a component offers multiple licenses (e.g., "MIT OR GPL-3.0"), specify preference:

#### most_permissive

Choose the most permissive license:

```yaml
dual_license_preference: most_permissive
```

Example: `MIT OR GPL-3.0` → selects MIT

#### avoid_copyleft

Choose non-copyleft licenses when available:

```yaml
dual_license_preference: avoid_copyleft
```

Example: `Apache-2.0 OR GPL-3.0` → selects Apache-2.0

#### prefer_order

Specify explicit preference order:

```yaml
dual_license_preference: prefer_order
preferred_order:
  - GPL-3.0
  - GPL-2.0
  - LGPL-3.0
  - Apache-2.0
  - MIT
```

Example: `MIT OR GPL-3.0` → selects GPL-3.0 (higher preference)

#### prefer_copyleft

Choose copyleft licenses when available:

```yaml
dual_license_preference: prefer_copyleft
```

Example: `MIT OR GPL-3.0` → selects GPL-3.0

---

## Built-in Policy Templates

LCC includes five built-in policy templates that you can use as-is or customize.

### 1. permissive

**Use case**: Startups, SaaS, proprietary software

```yaml
name: permissive
description: Permissive baseline policy that flags copyleft for review
contexts:
  internal:  # Development and internal tools
    allow: [MIT, Apache-2.0, BSD-*, ISC, CC0-1.0]
    deny: [SSPL-1.0]
    review: [GPL-*, AGPL-*, LGPL-*]

  saas:  # Hosted services
    allow: [MIT, Apache-2.0, BSD-*, ISC]
    deny: [SSPL-1.0, AGPL-*, GPL-3.0]
    review: [LGPL-*, MPL-*]
```

**When to use**:
- Building SaaS applications
- Proprietary software with no source distribution
- Want to avoid copyleft obligations

### 2. copyleft-friendly

**Use case**: Open source projects, companies with compliance workflows

```yaml
name: copyleft-friendly
description: Favors strong copyleft with compliance support
contexts:
  distribution:  # Shipping binaries or source
    allow: [GPL-2.0, GPL-3.0, LGPL-*, MIT, Apache-2.0]
    deny: [AGPL-3.0, SSPL-1.0]
    review: [EPL-*, MPL-*]

  embedded:  # Embedded devices
    allow: [MIT, Apache-2.0, BSD-*]
    review: [GPL-*, LGPL-*]
    deny: [AGPL-*]
```

**When to use**:
- Building open source projects
- Shipping on-premise software
- Have established compliance processes for GPL

### 3. ai-ml-research

**Use case**: Academic research, student projects, non-commercial AI/ML

```yaml
name: ai-ml-research
description: Permissive policy for academic and non-commercial AI/ML research
contexts:
  research:  # Academic research and experiments
    allowed:
      - MIT, Apache-2.0, BSD-*
      - All AI model licenses (OpenRAIL, Llama, Gemma, etc.)
      - All dataset licenses including non-commercial (CC-BY-NC, ImageNet)
    review:
      - No-derivatives (CC-BY-ND)
      - Proprietary APIs (OpenAI, Anthropic)
    denied: []  # Very permissive

  publication:  # Code/models in papers
    allowed: [MIT, Apache-2.0, OpenRAIL-M, CC0, CC-BY, ImageNet]
    denied: [OpenAI-GPT, Anthropic-Claude, Kaggle-Competition]

  teaching:  # Educational use
    allowed: [All non-commercial licenses, ImageNet, COCO]
    denied: [Kaggle-Competition]
```

**When to use**:
- Academic research projects
- Student coursework and theses
- Non-commercial AI/ML experiments
- No plans for commercialization

**Key features**:
- Accepts non-commercial licenses (CC-BY-NC)
- Allows research-only datasets (ImageNet)
- Permits all AI model licenses (Llama, OpenRAIL, etc.)

### 4. ai-ml-permissive

**Use case**: Commercial AI/ML products with permissive license preference

Similar to `ai-ml-research` but:
- Denies non-commercial licenses (CC-BY-NC)
- Denies research-only datasets (ImageNet)
- Reviews restrictive AI licenses (Llama with commercial restrictions)

### 5. ai-ml-strict

**Use case**: Enterprise AI/ML with strict compliance requirements

Most restrictive AI/ML policy:
- Only truly permissive licenses
- No use-based restrictions
- No attribution-only variants
- Comprehensive legal review for edge cases

### Using Built-in Policies

```bash
# List available policies
lcc policy list

# Show policy details
lcc policy show permissive

# Use built-in policy
lcc scan . --policy permissive --context saas

# Copy and customize
cp ~/.lcc/policies/permissive.yaml ~/.lcc/policies/my-custom-policy.yaml
# Edit my-custom-policy.yaml
lcc scan . --policy my-custom-policy
```

---

## Advanced Topics

### License Compatibility

Understanding license compatibility is crucial for policy design.

#### Permissive Licenses

Compatible with almost everything:
- MIT, BSD, Apache-2.0, ISC

Can be combined with:
- Other permissive licenses
- Weak copyleft (LGPL)
- Strong copyleft (GPL)
- Proprietary code

#### Weak Copyleft (LGPL, MPL)

Compatible with:
- Permissive licenses
- Proprietary code (with dynamic linking for LGPL)
- Strong copyleft (GPL)

May require:
- Dynamic linking (LGPL)
- File-level isolation (MPL)
- Source distribution for modified files

#### Strong Copyleft (GPL)

Requires:
- Entire program to be GPL-licensed
- Source distribution to users
- Can include permissive and weak copyleft code

Not compatible with:
- Proprietary code (in most cases)
- AGPL (GPL-2.0 not compatible with AGPL-3.0)

#### Network Copyleft (AGPL)

Most restrictive:
- Triggers on network access (not just distribution)
- Requires source availability to network users
- Compatible with GPL-3.0 (but not GPL-2.0)

#### AI/ML License Compatibility

AI licenses often have unique restrictions:
- **Use-based restrictions**: Llama 2 restricts certain applications
- **Attribution requirements**: OpenRAIL requires model card attribution
- **Non-commercial**: Many dataset licenses (CC-BY-NC, ImageNet)
- **No-derivatives**: Some datasets prohibit modifications

### SPDX License Expressions

LCC supports SPDX license expressions for dual/multi-licensing:

```
MIT                          # Single license
MIT OR Apache-2.0            # Dual license (choice)
MIT AND Apache-2.0           # Both licenses apply
GPL-3.0+ WITH Classpath      # License with exception
(MIT OR BSD-3-Clause) AND GPL-3.0  # Complex expression
```

Policy evaluation:
1. Parse SPDX expression
2. Apply dual_license_preference
3. Select appropriate license
4. Check against allow/deny/review lists

### Unknown Licenses

When LCC encounters unknown licenses:

1. **Default behavior**: Flag for review (not auto-deny)
2. **In reports**: Marked as "UNKNOWN" or "NOASSERTION"
3. **Policy evaluation**: Treated as unlisted → review

Configure unknown license handling:

```yaml
contexts:
  production:
    # ... allow/deny/review lists ...

    # Unknown licenses are flagged for review by default
    # Add to review list to make explicit
    review:
      - UNKNOWN

    review_reasons:
      UNKNOWN: "Unknown license requires manual investigation"
```

### Custom License Identifiers

For proprietary or custom licenses:

```yaml
contexts:
  production:
    allow:
      - MIT
      - Apache-2.0
      - Proprietary-CompanyName  # Custom identifier

    deny:
      - Custom-Restrictive-License

    deny_reasons:
      Custom-Restrictive-License: "Incompatible with our distribution model"
```

### Policy Versioning

Version your policies for auditability:

```yaml
name: my-policy
version: "2.1.0"  # Semantic versioning
description: Updated to allow MPL-2.0 after legal review (2024-10-30)

# In git commit message:
# v2.1.0: Add MPL-2.0 to allow list after legal review
#
# JIRA: LEGAL-1234
# Approved-by: Jane Doe (Legal)
# Review-date: 2024-10-25
```

Track changes in CHANGELOG:

```markdown
## [2.1.0] - 2024-10-30
### Added
- MPL-2.0 to production allow list after legal review

### Changed
- LGPL-3.0 moved from review to allow for development context

### Removed
- BUSL-1.1 from review list (now denied)
```

### Multi-Policy Workflows

Use multiple policies for different projects:

```bash
# Project A: Strict SaaS policy
lcc scan ./project-a --policy saas-strict --context production

# Project B: Research policy
lcc scan ./project-b --policy ai-ml-research --context research

# Project C: Custom policy
lcc scan ./project-c --policy custom-enterprise --context distribution
```

Directory structure:

```
~/.lcc/policies/
├── saas-strict.yaml
├── ai-ml-research.yaml
├── custom-enterprise.yaml
├── team-frontend.yaml
└── team-backend.yaml
```

---

## Best Practices

### 1. Start with a Template

Don't write policies from scratch:

```bash
# Copy built-in template
cp ~/.lcc/policies/permissive.yaml ~/.lcc/policies/my-company.yaml

# Customize for your needs
vim ~/.lcc/policies/my-company.yaml
```

### 2. Version Control Policies

Store policies in git with your projects:

```
my-project/
├── .lcc/
│   └── policies/
│       └── project-policy.yaml
├── src/
└── pyproject.toml
```

Configure LCC to use project-local policies:

```bash
# In .lcc/config.yaml
policy_dir: .lcc/policies
```

### 3. Document Your Decisions

Add comprehensive reasoning:

```yaml
deny_reasons:
  AGPL-3.0: |
    Network copyleft incompatible with SaaS model.
    Legal review: LEGAL-1234 (2024-01-15)
    Decision: Prohibited in all contexts
    Contact: legal-team@company.com for exceptions
```

### 4. Use Contexts Strategically

Map contexts to your deployment pipeline:

```yaml
contexts:
  development:   # CI on feature branches
    # Permissive, flag issues

  staging:       # CI on develop branch
    # Moderate, block violations

  production:    # CI on main branch, releases
    # Strict, block all violations
```

### 5. Regular Policy Reviews

Schedule periodic reviews:

- **Quarterly**: Review and update license allow/deny lists
- **When adding dependencies**: Check if new licenses need evaluation
- **After legal guidance**: Update policies based on legal counsel
- **Industry changes**: Adjust for new license types (e.g., AI licenses)

### 6. Collaboration Workflow

Involve stakeholders:

1. **Engineering**: Proposes policy changes for new dependencies
2. **Legal**: Reviews and approves policy changes
3. **Security**: Evaluates license implications for supply chain
4. **Compliance**: Audits policy adherence and reporting

Use pull requests for policy changes:

```bash
# Feature branch for policy update
git checkout -b policy/add-mpl-support

# Edit policy
vim .lcc/policies/company-policy.yaml

# Test locally
lcc scan . --policy company-policy --context production

# Commit and PR
git add .lcc/policies/company-policy.yaml
git commit -m "policy: Add MPL-2.0 after legal review LEGAL-1234"
git push origin policy/add-mpl-support
# Create PR for legal + engineering review
```

### 7. Test Policies

Validate before deploying:

```bash
# Syntax validation
lcc policy validate my-policy

# Dry-run on codebase
lcc scan . --policy my-policy --context production --dry-run

# Compare with previous policy
lcc scan . --policy old-policy > old-results.json
lcc scan . --policy new-policy > new-results.json
diff old-results.json new-results.json
```

### 8. Handle Exceptions Gracefully

Create exception processes:

```yaml
# In policy
contexts:
  production:
    # ... standard rules ...

    explanation:
      - "For exceptions, create ticket in JIRA project LEGAL"
      - "Provide: component, license, justification, timeline"
      - "Approval required from legal-team@company.com"
```

Track exceptions in separate file:

```
.lcc/
├── policies/
│   └── company-policy.yaml
└── exceptions/
    └── exceptions.yaml
```

```yaml
# exceptions.yaml
exceptions:
  - component: special-library
    version: 1.2.3
    license: GPL-3.0
    approved_by: legal-team@company.com
    approved_date: 2024-10-15
    expires: 2025-10-15
    justification: "Critical feature, no alternatives available"
    ticket: LEGAL-5678
```

### 9. AI/ML Specific Considerations

For AI/ML projects, consider:

```yaml
contexts:
  research:
    # Very permissive, allow non-commercial
    allowed: [CC-BY-NC-*, ImageNet, ...]

  internal-demo:
    # Moderate, allow some restrictions
    allowed: [OpenRAIL, Llama-2, ...]

  production:
    # Strict, commercial-use only
    allowed: [MIT, Apache-2.0, Apache-2.0-AI, Mistral-AI]
    denied: [CC-BY-NC-*, Llama-2, ImageNet]
```

### 10. Monitor and Alert

Integrate with CI/CD:

```yaml
# .github/workflows/compliance.yml
name: License Compliance
on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run LCC
        run: |
          lcc scan . --policy company-policy --context production --fail-on violation
```

Set up notifications:

```bash
# Fail CI on violations
lcc scan . --policy my-policy --fail-on violation

# Fail on violations and warnings
lcc scan . --policy my-policy --fail-on warning

# Send notification on review items
lcc scan . --policy my-policy --notify-on review --slack-webhook $WEBHOOK
```

---

## Summary

Policies are the foundation of effective license compliance:

1. **Start simple**: Use built-in templates and customize incrementally
2. **Be explicit**: Document reasoning for every decision
3. **Use contexts**: Different rules for different environments
4. **Version control**: Track changes and involve stakeholders
5. **Test thoroughly**: Validate policies before production deployment
6. **Review regularly**: Keep policies updated with legal guidance
7. **Collaborate**: Engineering, legal, and compliance work together

### Next Steps

- Read [USER_GUIDE.md](USER_GUIDE.md) for CLI usage
- Read [API_GUIDE.md](API_GUIDE.md) for programmatic access
- Check [FAQ.md](FAQ.md) for common questions
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for debugging

### Getting Help

- Documentation: https://docs.lcc.dev
- Issues: https://github.com/your-org/lcc/issues
- Discussions: https://github.com/your-org/lcc/discussions
- Email: support@lcc.dev

---

*This guide reflects best practices as of 2024. License compliance is an evolving field; consult legal counsel for authoritative guidance.*
