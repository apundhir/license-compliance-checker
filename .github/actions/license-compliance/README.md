# License Compliance Checker Action

A GitHub Action that runs License Compliance Checker (LCC) against your repository to detect license violations, generate compliance reports, and produce SBOMs.

[![License Compliance](https://img.shields.io/badge/license--compliance-checked-blue?logo=github)](https://github.com/marketplace/actions/license-compliance-checker)

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `path` | Project path to scan | No | `.` |
| `format` | Report format (`json`, `markdown`, `html`, `csv`) | No | `json` |
| `policy` | Policy name to apply | No | |
| `output` | Report output path | No | `lcc-report.json` |
| `threshold` | Confidence threshold for violations (0.0 - 1.0) | No | `0.5` |
| `fail-on` | When to fail the action: `violations`, `warnings`, `none` | No | `violations` |
| `ecosystems` | Comma-separated list of ecosystems to scan (`python`, `node`, `go`, `conda`). Use `all` for everything | No | `all` |
| `exclude` | Comma-separated glob patterns to exclude (e.g. `tests/**,docs/**`) | No | |
| `sbom-format` | SBOM format to generate: `cyclonedx`, `spdx`, `none` | No | `none` |

## Outputs

| Output | Description |
|--------|-------------|
| `report` | Path to the generated compliance report |
| `status` | Compliance status: `pass`, `warning`, or `violation` |
| `violation-count` | Number of violations found |
| `warning-count` | Number of warnings found |
| `sbom-path` | Path to generated SBOM file (empty if `sbom-format` is `none`) |

## Usage Examples

### Basic scan (block PRs on violations)

```yaml
name: License Compliance
on: [pull_request]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run license compliance check
        id: lcc
        uses: ./.github/actions/license-compliance
        with:
          path: .
          format: json
          fail-on: violations

      - name: Comment on PR
        if: always()
        run: |
          echo "Compliance status: ${{ steps.lcc.outputs.status }}"
          echo "Violations: ${{ steps.lcc.outputs.violation-count }}"
          echo "Warnings: ${{ steps.lcc.outputs.warning-count }}"
```

### Scan with SBOM generation

```yaml
name: License Compliance with SBOM
on:
  push:
    branches: [main]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run license compliance check
        id: lcc
        uses: ./.github/actions/license-compliance
        with:
          path: .
          format: json
          sbom-format: cyclonedx
          fail-on: violations

      - name: Upload SBOM
        if: steps.lcc.outputs.sbom-path != ''
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: ${{ steps.lcc.outputs.sbom-path }}

      - name: Upload compliance report
        uses: actions/upload-artifact@v4
        with:
          name: compliance-report
          path: ${{ steps.lcc.outputs.report }}
```

### Scan specific ecosystems with custom policy

```yaml
name: Python License Check
on: [pull_request]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run license compliance check
        id: lcc
        uses: ./.github/actions/license-compliance
        with:
          path: .
          ecosystems: python
          policy: permissive
          threshold: '0.7'
          exclude: 'tests/**,docs/**'
          fail-on: warnings

      - name: Report results
        if: always()
        run: |
          echo "## License Compliance Results" >> $GITHUB_STEP_SUMMARY
          echo "- Status: ${{ steps.lcc.outputs.status }}" >> $GITHUB_STEP_SUMMARY
          echo "- Violations: ${{ steps.lcc.outputs.violation-count }}" >> $GITHUB_STEP_SUMMARY
          echo "- Warnings: ${{ steps.lcc.outputs.warning-count }}" >> $GITHUB_STEP_SUMMARY
```

## Badge

Add a compliance badge to your project README:

```markdown
[![License Compliance](https://img.shields.io/badge/license--compliance-checked-blue?logo=github)](https://github.com/marketplace/actions/license-compliance-checker)
```
