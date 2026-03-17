# LCC v2.0 — Phased Implementation Plan

**Source:** PRD v1.0 (March 2026, AiExponent)
**Focus:** Core functional gaps only (branding/cosmetic deferred)
**Status:** In Progress

---

## Phase 1: Foundation & Quick Wins (Weeks 1-2)

*Goal: Remove friction, make LCC installable and CI-ready in minutes.*

| Task | Gap | Description | Effort | Status |
|------|-----|------------|--------|--------|
| 1.1 | GAP-11 | PyPI publish workflow — GH Actions: build → test → twine upload on tag push | 1 day | DONE |
| 1.2 | GAP-05 | GitHub Action Marketplace — release tags, fail-on input, SBOM output, publish | 2 days | DONE |
| 1.3 | GAP-12 | Hosted docs site — mkdocs + Material theme, wire existing docs, GH Pages deploy | 2 days | DONE |
| 1.4 | GAP-03 | Benchmark framework — 50-project corpus, accuracy scorer, scan time, FP rate | 1 week | DONE |

**Exit Criteria:**
- [ ] `pip install license-compliance-checker` works
- [ ] GitHub Action on Marketplace with v1 tag
- [ ] Docs site live on GitHub Pages
- [ ] Benchmark numbers public in README

---

## Phase 2: AI/ML & Regulatory — The Moat (Weeks 3-5)

*Goal: Make LCC the only open-source tool with EU AI Act compliance features.*

| Task | Gap | Description | Effort | Status |
|------|-----|------------|--------|--------|
| 2.1 | GAP-06 | Enhanced model card parser — training data, limitations, metrics, env impact | 3 days | NOT STARTED |
| 2.2 | GAP-06 | Regulatory metadata model — RegulatoryMetadata dataclass, Component extension | 2 days | NOT STARTED |
| 2.3 | GAP-06 | EU AI Act Article 53 mapping engine — scan results → Art.53 obligations | 1 week | NOT STARTED |
| 2.4 | GAP-06 | Regulatory policy templates — eu-ai-act, nist-ai-rmf, iso-42001 | 3 days | NOT STARTED |
| 2.5 | GAP-06 | EU AI Act compliance report generator — regulatory_reporter.py | 4 days | NOT STARTED |
| 2.6 | GAP-06 | SBOM regulatory extensions — regulatory:* properties in CycloneDX/SPDX | 2 days | NOT STARTED |
| 2.7 | GAP-07 | Dashboard AI Model tab enhancements — RAIL panel, EU AI Act flags, filtering | 1 week | NOT STARTED |
| 2.8 | GAP-07 | Dashboard EU AI Act export — compliance pack bundle download | 3 days | NOT STARTED |

**Exit Criteria:**
- [ ] Scan HuggingFace model → see EU AI Act obligations in dashboard
- [ ] Export compliance pack (SBOM + training data summary + copyright policy)
- [ ] RAIL restrictions shown in plain English
- [ ] Regulatory reports generated

---

## Phase 3: Dependency Intelligence (Weeks 6-8)

*Goal: Close enterprise credibility gap — transitive deps + license compatibility.*

| Task | Gap | Description | Effort | Status |
|------|-----|------------|--------|--------|
| 3.1 | GAP-09 | Component model depth tracking — dependency_depth, is_direct, parent_packages | 2 days | NOT STARTED |
| 3.2 | GAP-09 | Python transitive resolution — poetry.lock requires, pip-tools output | 3 days | NOT STARTED |
| 3.3 | GAP-09 | JavaScript transitive resolution — package-lock.json parent-child map | 3 days | NOT STARTED |
| 3.4 | GAP-09 | Go transitive resolution — enhance indirect marker, go mod graph | 2 days | NOT STARTED |
| 3.5 | GAP-09 | Java/Maven lock file support — dependency:tree parsing | 3 days | NOT STARTED |
| 3.6 | GAP-09 | .NET lock file support — packages.lock.json parsing | 2 days | NOT STARTED |
| 3.7 | GAP-10 | License compatibility matrix — SPDX-based rules, contamination detection | 1 week | NOT STARTED |
| 3.8 | GAP-10 | Compatibility policy extensions — incompatible_pairs, copyleft_groups in YAML | 3 days | NOT STARTED |
| 3.9 | GAP-09 | Dashboard dependency tree view — depth badges, filter by depth | 4 days | NOT STARTED |
| 3.10 | GAP-10 | Dashboard compatibility warnings — contamination banners, plain English | 3 days | NOT STARTED |

**Exit Criteria:**
- [ ] Transitive deps shown with depth markers
- [ ] License conflicts flagged with plain-English explanation
- [ ] Policy can distinguish direct vs transitive GPL
- [ ] Contamination chains visible in dashboard

---

## Phase 4: Developer Experience — VS Code Extension (Weeks 9-12)

*Goal: Shift-left — catch violations before commit.*

| Task | Gap | Description | Effort | Status |
|------|-----|------------|--------|--------|
| 4.1 | GAP-08 | VS Code extension scaffold — manifest, activation events, language support | 2 days | NOT STARTED |
| 4.2 | GAP-08 | Manifest file scanning on save — inline diagnostics | 1 week | NOT STARTED |
| 4.3 | GAP-08 | Hover provider — license risk on dependency hover | 4 days | NOT STARTED |
| 4.4 | GAP-08 | Workspace scan command — results panel with findings | 4 days | NOT STARTED |
| 4.5 | GAP-08 | Status bar integration — compliance status indicator | 2 days | NOT STARTED |
| 4.6 | GAP-07 | Dashboard PDF report export — Puppeteer-based, branded | 4 days | NOT STARTED |
| 4.7 | GAP-07 | Dashboard advanced filtering — cross-page filter bar, URL state | 3 days | NOT STARTED |

**Exit Criteria:**
- [ ] VS Code extension on Marketplace
- [ ] Inline license warnings in manifest files
- [ ] "LCC: Scan Workspace" command works
- [ ] PDF reports downloadable from dashboard

---

## Deferred (Post-Core)

- GAP-01: Brand identity, logo, design language
- GAP-02: Dashboard design system (dark mode, AiExponent colours)
- GAP-04: Repo transfer to aiexponent org
- README hero rewrite / social preview
- Enterprise SaaS tier (v3.0)

---

## Dependency Graph

```
Phase 1 (all parallel)
  ├── 1.1 PyPI
  ├── 1.2 GitHub Action
  ├── 1.3 Docs Site
  └── 1.4 Benchmarks

Phase 2 (AI/Regulatory) ← after Phase 1
  2.1 → 2.2 → 2.3 → 2.5 → 2.6
                  └→ 2.7 → 2.8

Phase 3 (Deps) ← can parallel with Phase 2
  3.1 → 3.2-3.6 (parallel per language)
  3.7 ← 3.1
  3.8 ← 3.7
  3.9-3.10 ← 3.1, 3.7

Phase 4 (VS Code) ← after Phase 1, benefits from Phase 3
  4.1 → 4.2-4.5 (sequential)
```
