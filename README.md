# License Compliance Checker (LCC)

Phase 1 (Foundation) focuses on the core license detection engine, multi-source resolution, CLI tooling, and reporting as described in `PRD-v1.2.md`.

## Getting Started

```bash
conda env create --prefix ./.conda-lcc --file environment.yml
conda activate ./.conda-lcc
pre-commit install
python -m pip install -e .
python -m pip install .[test]
```

Run the automated test suite:

```bash
python -m pytest
```

## Supported Language Detectors

- Python (pip, Poetry, Conda and dist-info metadata)
- JavaScript/TypeScript (npm, Yarn, pnpm, workspaces, node_modules)
- Go modules (go.mod, go.sum, vendor tree, go.work)
- Maven (pom.xml, dependency management, plugins)
- Gradle (Groovy/Kotlin DSL and lock files)
- Cargo (Cargo.toml, workspaces, Cargo.lock)

## CLI Usage

```bash
lcc scan . --format console --threshold 0.7
lcc scan path/to/project --manifest path/to/requirements.txt --format json --output report.json
lcc interactive --report report.json
```

- `--offline` forces cached-only resolution.
- `--exclude` filters directories using glob patterns.
- `--recursive` scans subdirectories for recognised manifests.
- `--git url[@ref]` clones git repositories before scanning.
- `--policy name-or-path` evaluates findings against a policy definition.
- `lcc interactive --report report.json` launches the interactive explorer for a previously generated JSON report.
- `LCC_OPA_URL=http://localhost:8181` enables remote policy evaluation through an OPA service.

## REST API

The FastAPI service exposes the scanning engine and policy metadata over HTTP. Launch it locally with:

```bash
lcc server --host 0.0.0.0 --port 8000
```

Key endpoints:

- `GET /health` – readiness probe.
- `GET /dashboard` – aggregated metrics (totals, distribution, trend).
- `GET /scans` / `GET /scans/{id}` – near-real-time scan history and detailed reports.
- `POST /scans` – run a scan (`{"path": "/workspace/project", "policy": "permissive"}`).
- `GET /policies` / `GET /policies/{name}` – bundled policy catalogue for the UI.

The SQLite database defaults to `~/.lcc/lcc.db`. Override via `LCC_DB_PATH`.

## Docker

```bash
docker build -t lcc:dev .
docker run --rm -v "$PWD":/workspace lcc:dev scan .
docker compose up --build
```

Adjust the override template (`docker-compose.override.yml.example`) to customise commands per environment.

The default compose stack exposes the REST API at `http://localhost:8000` (service name `api`). Mount a workspace volume to surface local projects inside the container; user state (policies, database) is persisted under `/workspace/.lcc/`.

### Policy Management

```bash
lcc policy list
lcc policy show permissive
lcc policy apply permissive
lcc policy test permissive report.json
lcc policy import policies/permissive.yaml
lcc policy export permissive permissive-copy.yaml
lcc policy create --name custom
lcc policy delete permissive --yes
```

Policies are stored under `~/.lcc/policies` and seeded with defaults from the repository `policies/` directory.

### Report Generation

```bash
lcc report generate . --format markdown --output compliance.md
lcc report generate report.json --format html --include-evidence
lcc report generate report.json --format csv --output compliance.csv
```

Markdown and HTML reporters support grouping, evidence inclusion, report comparisons, and optional SHA256 signatures. The CSV reporter produces a tabular view you can import into spreadsheets or BI tools.

### OPA Integration & Decision Logging

1. Build the policy bundle and start the local reference stack:
   ```bash
   scripts/build_policy_bundle.py --output dist/policy.bundle.tar.gz
   (cd deploy/opa && docker compose up)
   ```
2. Point the CLI at the running OPA server:
   ```bash
   export LCC_OPA_URL=http://localhost:8181
   lcc scan . --format json --output report.json
   ```

Each decision is appended to `~/.lcc/decisions.jsonl`. Override the location via `LCC_DECISION_LOG` when running in containerized or ephemeral environments.

### Redis Caching & Asynchronous Jobs

- Set `LCC_REDIS_URL=redis://localhost:6379/0` to enable Redis-backed caching and the job queue.
- Submit and process background scan jobs:
  ```bash
  lcc queue submit /path/to/project --output queued-report.json
  lcc queue worker
  lcc queue status
  ```
  Workers use the same scanning engine under the hood and write JSON reports if `--output` is provided. Failed jobs are retried automatically and eventually moved to a dead-letter list.

### GitHub Actions Integration

- Reuse the bundled workflow `.github/workflows/lcc-scan.yml` or call the composite action directly:
  ```yaml
  jobs:
    compliance:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: ./\.github/actions/license-compliance
          with:
            path: .
            format: json
            output: lcc-report.json
          env:
            LCC_OPA_URL: \\${{ secrets.LCC_OPA_URL }}
            LCC_OPA_TOKEN: \\${{ secrets.LCC_OPA_TOKEN }}
            LCC_REDIS_URL: \\${{ secrets.LCC_REDIS_URL }}
  ```
- Reports are uploaded via `actions/upload-artifact` in the sample workflow for easy download from the Actions tab.

## Development Notes

- Detectors live in `src/lcc/detection/`
- Resolvers and the fallback chain live in `src/lcc/resolution/`
- CLI entrypoint: `src/lcc/cli/main.py`
- Reporting: `src/lcc/reporting/`
- Web dashboard: `dashboard/` (Next.js 15 + Tailwind + Radix UI)
- Policy templates: `policy/templates/`

See `docs/phase1_todo.md` for delivery tracking.

### Dashboard (Phase 2)

```bash
cd dashboard
npm install
npm run dev -- --hostname 0.0.0.0 --port 3000
# open http://localhost:3000
```

Environment variables:

- `NEXT_PUBLIC_LCC_API_BASE_URL` – REST endpoint for live data (defaults to `http://localhost:8000`).
- `LCC_OPA_URL`, `LCC_OPA_TOKEN`, `LCC_REDIS_URL` – forwarded automatically when running in CI for policy evaluation, decision logging, and queue metrics.

## Kubernetes Deployment

Reference manifests are available in `deploy/k8s/` (Deployment, Service, Ingress, HPA, RBAC, NetworkPolicy, ConfigMap, Secret) along with a starter Helm chart (`deploy/k8s/helm`). Update image references and apply:

```bash
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/secret.yaml
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
```
