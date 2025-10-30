# License Compliance Checker - Video Script

**Target Duration**: 10-12 minutes
**Format**: Screen recording with voiceover
**Audience**: Developers, DevOps engineers, compliance teams

---

## Scene 1: Introduction (0:00 - 1:00)

### Visual
- LCC logo and project name
- Tagline: "Automated License Compliance for Modern Software"

### Voiceover
> "Welcome! In this video, we'll explore the License Compliance Checker - or LCC - an open-source tool that helps you manage license compliance for your software projects.
>
> Whether you're building a SaaS application, working on open source, or training AI models, LCC ensures you're using dependencies that comply with your organization's policies.
>
> Today, we'll cover:
> - What LCC does and why you need it
> - A quick installation and first scan
> - Policy configuration
> - The web dashboard
> - API integration
> - And a real-world AI/ML example
>
> Let's get started!"

---

## Scene 2: The Problem (1:00 - 2:30)

### Visual
- Terminal showing `pip freeze` with 50+ packages
- Highlight problematic licenses: GPL-3.0, AGPL-3.0, UNKNOWN

### Voiceover
> "Modern applications depend on hundreds of open-source packages. Each has its own license - MIT, Apache, GPL, and many others.
>
> [Show pip freeze output]
>
> Here's a typical Python project with over 50 dependencies. How do you know if these licenses are compatible with your product?
>
> [Highlight GPL-3.0]
>
> What if you're building a proprietary SaaS product and accidentally include a GPL library? That's a legal risk.
>
> [Highlight UNKNOWN]
>
> Or what if licenses are missing entirely? You have no idea what you're legally allowed to do with this code.
>
> Manual license audits are time-consuming, error-prone, and don't scale. That's where LCC comes in."

---

## Scene 3: Quick Start - Installation (2:30 - 3:30)

### Visual
- Terminal showing installation
- Docker Compose up command
- Health check

### Voiceover
> "Let's install LCC. There are three ways - Docker, pip, or from source. We'll use Docker Compose for the full experience.
>
> [Show terminal]
>
> ```bash
> git clone https://github.com/your-org/lcc.git
> cd lcc
> docker-compose up -d
> ```
>
> This starts the API server on port 8000 and the dashboard on port 3000.
>
> [Show browser - health check]
>
> Let's verify it's running:
>
> ```bash
> curl http://localhost:8000/health
> ```
>
> Perfect! LCC is ready."

---

## Scene 4: First Scan - CLI (3:30 - 5:30)

### Visual
- Terminal in a sample Python project
- Run lcc scan command
- Show output with colored results

### Voiceover
> "Now let's scan our first project. I have a simple Python application here with a few dependencies.
>
> [Show project directory]
>
> ```bash
> lcc scan .
> ```
>
> [Wait for scan to complete]
>
> LCC scans the project, detects all dependencies from requirements.txt, and resolves their licenses from multiple sources - PyPI registry, GitHub, and ClearlyDefined.
>
> [Show results]
>
> The report shows:
> - 15 components found
> - Most have MIT or Apache-2.0 licenses - that's good
> - But we have 2 components with UNKNOWN licenses
> - And 1 component with GPL-3.0 - this might be a problem depending on our policy
>
> Let's apply a policy to evaluate these findings."

---

## Scene 5: Policies (5:30 - 7:00)

### Visual
- Show policy file in editor
- Run scan with policy
- Show violation details

### Voiceover
> "LCC uses policies to define which licenses are acceptable for your project. Let's use the built-in 'permissive' policy, which is designed for SaaS products.
>
> [Show policy file]
>
> ```yaml
> contexts:
>   production:
>     allow:
>       - MIT
>       - Apache-2.0
>     deny:
>       - GPL-*
>       - AGPL-*
>     review:
>       - LGPL-*
> ```
>
> This policy allows permissive licenses like MIT and Apache-2.0, denies strong copyleft like GPL, and flags weak copyleft like LGPL for human review.
>
> [Run scan with policy]
>
> ```bash
> lcc scan . --policy permissive --context production
> ```
>
> [Show violation]
>
> Now we see that the GPL-3.0 component is flagged as a violation! LCC explains why - strong copyleft is incompatible with proprietary software.
>
> This is exactly what we want - automated detection of policy violations before they reach production."

---

## Scene 6: Web Dashboard (7:00 - 8:30)

### Visual
- Browser showing dashboard
- Navigate through scans, policies, analytics

### Voiceover
> "LCC includes a modern web dashboard for visualizing your compliance status.
>
> [Show dashboard login]
>
> First, let's create a user:
>
> ```bash
> lcc auth create-user admin password123 --role admin
> ```
>
> [Login to dashboard]
>
> The dashboard gives us:
>
> [Show main dashboard]
> - Overview statistics - total scans, violations, compliance rate
> - License distribution charts
> - Trend analysis over time
>
> [Navigate to Scans page]
> - List of all scans with status indicators
>
> [Click on a scan]
> - Detailed findings for each component
> - License information and policy evaluation
>
> [Show Policies page]
> - All available policies
> - Policy details and contexts
>
> [Show Analytics page]
> - Deeper insights into license usage across all projects
> - Top licenses, component types, project statistics
>
> This is perfect for compliance teams who need visibility without using the command line."

---

## Scene 7: API Integration (8:30 - 9:30)

### Visual
- Show GitHub Actions workflow file
- Show workflow running
- Show failure on violation

### Voiceover
> "One of LCC's strengths is its REST API, which makes it easy to integrate into CI/CD pipelines.
>
> [Show GitHub Actions workflow]
>
> Here's a GitHub Actions workflow that runs LCC on every pull request:
>
> ```yaml
> - name: License Compliance Check
>   run: |
>     pip install license-compliance-checker
>     lcc scan . --policy permissive --fail-on violation
> ```
>
> [Show workflow running]
>
> When a developer opens a PR, LCC automatically scans for license compliance.
>
> [Show failed workflow]
>
> If there's a violation - the workflow fails and the PR can't be merged until it's resolved.
>
> This catches license issues early, before they reach production. You can also integrate with Jenkins, GitLab CI, CircleCI, or any CI system that supports command-line tools."

---

## Scene 8: AI/ML Use Case (9:30 - 11:00)

### Visual
- Show AI/ML project with Hugging Face models
- Run scan with ai-ml-research policy
- Show results with model licenses

### Voiceover
> "LCC has first-class support for AI and machine learning projects. Let's scan a project that uses Hugging Face models and datasets.
>
> [Show project with requirements.txt including transformers]
>
> This project uses the 'transformers' library and several pre-trained models.
>
> [Run scan with AI policy]
>
> ```bash
> lcc scan . --policy ai-ml-research --context research
> ```
>
> [Show results]
>
> LCC detects:
> - Traditional software dependencies (transformers, torch, numpy)
> - Hugging Face models (bert-base-uncased with Apache-2.0)
> - Dataset dependencies (COCO with CC-BY-4.0)
>
> The 'ai-ml-research' policy is designed for academic research, so it allows:
> - Non-commercial licenses (CC-BY-NC)
> - Research-only datasets (ImageNet)
> - AI-specific licenses (Llama 2, OpenRAIL)
>
> But if you're building a commercial product, you'd use 'ai-ml-permissive' instead, which denies non-commercial licenses.
>
> This is crucial for AI teams - model licenses have unique restrictions that traditional tools don't understand."

---

## Scene 9: SBOM Generation (11:00 - 11:45)

### Visual
- Terminal showing SBOM generation
- Show generated SBOM file
- Highlight key fields

### Voiceover
> "LCC can generate Software Bills of Materials - or SBOMs - in industry-standard formats.
>
> [Run SBOM command]
>
> ```bash
> lcc sbom --scan-id <ID> --format cyclonedx --output sbom.json
> ```
>
> [Show SBOM file]
>
> This creates a CycloneDX SBOM that includes:
> - All components and versions
> - License information
> - Dependency relationships
> - Timestamps and metadata
>
> SBOMs are increasingly required by government regulations and enterprise customers. LCC makes it easy to generate them automatically.
>
> We also support SPDX format and multiple output formats - JSON, XML, YAML, and tag-value."

---

## Scene 10: Wrap-Up & Call to Action (11:45 - 12:00)

### Visual
- LCC features summary slide
- Links to documentation and GitHub

### Voiceover
> "Let's recap what we've covered:
>
> - LCC automates license compliance checking for all your dependencies
> - Flexible policies let you define rules for different contexts
> - The web dashboard provides visibility for compliance teams
> - REST API enables seamless CI/CD integration
> - First-class AI/ML support handles model and dataset licenses
> - Generate SBOMs for regulatory compliance
>
> LCC is free, open source, and actively maintained.
>
> Get started today:
> - Documentation: docs.lcc.dev
> - GitHub: github.com/your-org/lcc
> - Docker: docker pull lcc:latest
>
> Thanks for watching! If you have questions, open an issue or discussion on GitHub. Happy scanning!"

---

## B-Roll & Supplementary Footage

### Quick Cuts (can be inserted throughout)
- Fast-forward of long scan running
- Zooming in on specific license identifiers
- Highlighting violations in red
- Showing PASS status in green
- Dashboard loading animations
- API request/response in terminal

### Code Snippets to Show
```python
# Python integration
from lcc.scanner import Scanner
report = scanner.scan("/path/to/project")
```

```yaml
# Policy snippet
contexts:
  production:
    deny: [GPL-*, AGPL-*]
```

```bash
# CI/CD snippet
lcc scan . --fail-on violation
```

---

## Technical Setup

### Required Tools
- **Screen recording**: OBS Studio or ScreenFlow
- **Video editing**: DaVinci Resolve or Premiere Pro
- **Audio**: USB microphone for clear voiceover
- **Terminal**: Use a clean terminal with large font (16-18pt)
- **Browser**: Increase zoom to 125-150% for visibility

### Visual Settings
- **Terminal color scheme**: Use a high-contrast theme (e.g., Dracula, Nord)
- **Font size**: Minimum 16pt for terminal, 14pt for editor
- **Recording resolution**: 1920x1080 or 2560x1440
- **Frame rate**: 30 or 60 fps

### Audio Settings
- **Bitrate**: 128 kbps or higher
- **Format**: AAC or MP3
- **Remove background noise**: Use noise gate in post-production

### Pacing Tips
- Pause for 1-2 seconds when commands finish executing
- Let viewers read terminal output before scrolling
- Use slow, deliberate mouse movements
- Add captions for key concepts and commands

---

## Publishing

### Platforms
- **YouTube**: Main distribution channel
- **Vimeo**: Professional/business audience
- **Website**: Embed on docs.lcc.dev
- **Social**: Clips for Twitter, LinkedIn

### Metadata
**Title**: "License Compliance Checker - Automated License Compliance for Modern Software"

**Description**:
```
Learn how to use the License Compliance Checker (LCC) to automate license compliance for your software projects.

In this video:
- Installation and setup
- Running your first scan
- Creating compliance policies
- Web dashboard tour
- CI/CD integration
- AI/ML license detection
- SBOM generation

🔗 Links:
- Documentation: https://docs.lcc.dev
- GitHub: https://github.com/your-org/lcc
- Download: https://github.com/your-org/lcc/releases

📚 Timestamps:
0:00 Introduction
1:00 The Problem
2:30 Installation
3:30 First Scan
5:30 Policies
7:00 Web Dashboard
8:30 API Integration
9:30 AI/ML Use Case
11:00 SBOM Generation
11:45 Wrap-Up

💬 Questions? Drop a comment or open an issue on GitHub!

⭐ Star the project: https://github.com/your-org/lcc
```

**Tags**: license compliance, open source, software compliance, SBOM, software bill of materials, license scanning, DevOps, CI/CD, AI ML, Hugging Face

**Thumbnail**: Eye-catching graphic with:
- "License Compliance Checker" text
- Checkmark icon
- "Automate License Compliance" tagline
- Bright, contrasting colors

---

## Video Variations

### Short Version (3-5 minutes)
Focus on:
- Problem statement
- Quick demo
- Key features
- Call to action

### Tutorial Series
Break into 5-6 short videos:
1. "Getting Started with LCC"
2. "Creating Custom Policies"
3. "Using the Web Dashboard"
4. "CI/CD Integration"
5. "AI/ML License Compliance"
6. "Generating SBOMs"

### Live Demo (20-30 minutes)
Interactive walkthrough with Q&A

---

*This script is a guideline - adapt based on your audience and platform. For questions, contact support@lcc.dev*
