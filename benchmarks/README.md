# LCC Benchmark Framework

Comprehensive benchmark suite for measuring License Compliance Checker (LCC) performance across three dimensions: **detection accuracy**, **scan speed**, and **AI model license detection**.

## Quick Start

```bash
# Run all benchmarks
python -m benchmarks.run_benchmarks --all -v

# Run individual benchmarks
python -m benchmarks.run_benchmarks --accuracy -v
python -m benchmarks.run_benchmarks --speed -v
python -m benchmarks.run_benchmarks --ai-models -v

# Filter by ecosystem
python -m benchmarks.run_benchmarks --accuracy --ecosystem python --ecosystem javascript -v

# Run speed benchmark with more iterations
python -m benchmarks.run_benchmarks --speed --iterations 20 -v
```

Results are written to `benchmarks/results/` and a combined summary is generated at `benchmarks/RESULTS.md`.

## Benchmarks

### 1. Accuracy Benchmark (`accuracy_benchmark.py`)

Measures how correctly LCC identifies licenses across 50 open source projects spanning all 8 supported ecosystems.

**Corpus:** `corpus/manifest.json` — 50 projects with manually verified ground-truth licenses.

| Ecosystem  | Projects |
|------------|----------|
| Python     | 10       |
| JavaScript | 10       |
| Go         | 8        |
| Java       | 7        |
| Rust       | 5        |
| Ruby       | 5        |
| .NET       | 5        |

**Metrics reported:**
- Overall accuracy (correct license / total components)
- Per-ecosystem accuracy
- False positive rate (wrong license assigned)
- False negative rate (license not detected)
- Unknown rate (license could not be resolved)

**How it works:**
1. For each project in the corpus, a minimal manifest file is generated (requirements.txt, package.json, go.mod, pom.xml, Cargo.toml, Gemfile, .csproj).
2. LCC runs in **offline mode** — no network calls are made.
3. Detected licenses are compared against ground truth using normalized SPDX identifiers.
4. Metrics are computed per-component, per-project, and per-ecosystem.

### 2. Speed Benchmark (`speed_benchmark.py`)

Measures scan latency across different project sizes and ecosystems.

**Test matrix:**

| Size   | Dependencies |
|--------|-------------|
| Small  | 10          |
| Medium | 50          |
| Large  | 200+        |

**Ecosystems tested:** Python, JavaScript, Go (by default).

**Metrics reported:**
- Total scan time (mean, median, P95, min, max)
- Detection phase time
- Resolution phase time
- Compliance check against target: **<10s for 50 deps**

### 3. AI Model Benchmark (`ai_model_benchmark.py`)

Measures accuracy of HuggingFace model license detection.

**Corpus:** `corpus/ai_models.json` — 20 HuggingFace models with verified licenses.

**License types covered:** Open, Restricted, RAIL (Responsible AI License), Commercial.

**Metrics reported:**
- License detection accuracy
- License type classification accuracy
- Target: **>=95% accuracy**

**How it works:**
1. Mock model directories are created with config.json, README.md (model card with YAML front-matter), and a placeholder weights file.
2. The HuggingFace detector discovers the model.
3. Offline resolvers attempt license resolution.
4. Detected licenses are compared against ground truth.

## Directory Structure

```
benchmarks/
    __init__.py
    README.md                  # This file
    RESULTS.md                 # Generated combined results summary
    accuracy_benchmark.py      # Accuracy measurement
    speed_benchmark.py         # Speed measurement
    ai_model_benchmark.py      # AI model detection measurement
    run_benchmarks.py          # Main runner / orchestrator
    corpus/
        manifest.json          # 50-project ground truth corpus
        ai_models.json         # 20-model ground truth corpus
    results/
        accuracy_results.json  # Generated accuracy data
        accuracy_results.md    # Generated accuracy report
        speed_results.json     # Generated speed data
        speed_results.md       # Generated speed report
        ai_model_results.json  # Generated AI model data
        ai_model_results.md    # Generated AI model report
```

## Methodology

### Offline Mode

All benchmarks run LCC in **offline mode** (`LCCConfig(offline=True)`). This means:
- No network calls to registries (PyPI, npm, crates.io, etc.)
- No ClearlyDefined API calls
- No GitHub API calls
- Only filesystem-based and ScanCode resolvers are active

This ensures benchmarks are **reproducible**, **fast**, and **CI-friendly**.

### Ground Truth

Ground truth licenses are manually verified from:
- Official project documentation
- SPDX license identifiers in source repositories
- Package registry metadata (PyPI, npm, crates.io, etc.)

### License Comparison

Detected licenses are compared using normalized SPDX identifiers:
- Case-insensitive matching
- Common alias resolution (e.g., "Apache License 2.0" -> "Apache-2.0")
- Compound expression support ("MIT AND Apache-2.0")
- Substring matching for partial expressions

### Performance Targets

| Metric | Target |
|--------|--------|
| Accuracy (all ecosystems) | Tracked (no fixed target yet) |
| Speed (50 deps) | < 10 seconds |
| AI Model License Detection | >= 95% accuracy |

## Contributing to the Test Corpus

### Adding a project to `corpus/manifest.json`

1. Choose a well-known open source project with a clear, unambiguous license.
2. Add an entry with the following fields:
   - `name`: Short project name
   - `ecosystem`: One of python, javascript, go, java, rust, ruby, dotnet
   - `github_url`: GitHub repository URL
   - `manifest_file`: Primary manifest file name
   - `known_license`: SPDX license identifier
   - `expected_component_count`: `{"min": N, "max": M}` range
   - `dependencies`: Array of `{"name": "...", "version": "...", "license": "..."}`
3. Verify all license fields against official sources.
4. Run the accuracy benchmark to confirm the new entry works:
   ```bash
   python -m benchmarks.run_benchmarks --accuracy -v
   ```

### Adding a model to `corpus/ai_models.json`

1. Choose a HuggingFace model with a known license.
2. Add an entry with:
   - `name`: Full HuggingFace model ID (e.g., "meta-llama/Llama-3.1-8B")
   - `known_license`: License identifier as shown on HuggingFace
   - `license_type`: One of "open", "restricted", "RAIL", "commercial"
   - `model_type`: Architecture class name
   - `framework`: "pytorch", "tensorflow", etc.
   - `rail_restrictions`: List of restriction strings, or null
3. Run the AI model benchmark:
   ```bash
   python -m benchmarks.run_benchmarks --ai-models -v
   ```

## Running Individual Benchmarks

Each benchmark module can be run standalone:

```bash
# Accuracy only, with JSON and Markdown output
python -m benchmarks.accuracy_benchmark -v \
    --output benchmarks/results/accuracy_results.json \
    --markdown benchmarks/results/accuracy_results.md

# Speed only, filtered to Python
python -m benchmarks.speed_benchmark -v \
    --ecosystem python \
    --iterations 10 \
    --output benchmarks/results/speed_results.json

# AI models only
python -m benchmarks.ai_model_benchmark -v \
    --output benchmarks/results/ai_model_results.json
```
