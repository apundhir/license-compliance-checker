# Installation

This page covers every way to install and run the License Compliance Checker.

---

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| Python | 3.9+ | Required for pip / source installs |
| Docker | 20.10+ | Required only for Docker method |
| Docker Compose | 2.0+ | Required only for Docker method |
| Git | Any recent version | Required for GitHub repository scanning |

---

## Method 1: Docker (Recommended)

The Docker method gives you the full stack — API server, background workers, web dashboard, PostgreSQL, and Redis — with a single command.

```bash
# Clone the repository
git clone https://github.com/apundhir/license-compliance-checker.git
cd license-compliance-checker

# Start all services
docker-compose up -d
```

Once the containers are running, the services are available at:

| Service | URL |
|---------|-----|
| Dashboard | [http://localhost:3000](http://localhost:3000) |
| API | [http://localhost:8000](http://localhost:8000) |
| API Docs (Swagger) | [http://localhost:8000/docs](http://localhost:8000/docs) |

For production deployments, use the production compose file:

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

!!! info "Configuration"
    Environment variables can be set in a `.env` file or directly in the compose file. See the [Deployment Guide](../deployment/index.md) for production configuration details.

---

## Method 2: pip Install

For CLI-only usage without the web dashboard or background services:

```bash
# Install from PyPI
pip install license-compliance-checker
```

Or install from a cloned repository:

```bash
git clone https://github.com/apundhir/license-compliance-checker.git
cd license-compliance-checker
pip install -e .
```

Verify the installation:

```bash
lcc --version
lcc scan --help
```

---

## Method 3: From Source (Development)

For contributors or anyone who wants to run the latest code:

```bash
# Clone the repository
git clone https://github.com/apundhir/license-compliance-checker.git
cd license-compliance-checker

# Install with development dependencies
pip install -e ".[dev]"

# Install dashboard dependencies
cd dashboard
npm install
cd ..
```

Run the services in separate terminals:

=== "Backend API"

    ```bash
    lcc server
    ```

=== "Background Worker"

    ```bash
    lcc queue worker
    ```

=== "Dashboard"

    ```bash
    cd dashboard
    npm run dev
    ```

---

## Environment Variables

Key configuration variables for all methods:

| Variable | Description | Default |
|----------|-------------|---------|
| `LCC_DATABASE_URL` | Database connection string | `sqlite:///lcc.db` |
| `LCC_REDIS_URL` | Redis connection for job queue | `redis://localhost:6379/0` |
| `LCC_CACHE_DIR` | Directory for caching license texts | `~/.lcc/cache` |
| `LCC_LLM_PROVIDER` | AI provider for license analysis | _(disabled)_ |
| `LCC_FIREWORKS_API_KEY` | API key for Fireworks AI | _(none)_ |
| `GITHUB_TOKEN` | GitHub token for repository scanning | _(none)_ |

!!! tip "AI-Powered Analysis"
    To enable LLM-based license analysis for ambiguous texts, configure the Fireworks AI integration:

    ```bash
    export LCC_LLM_PROVIDER=fireworks
    export LCC_FIREWORKS_API_KEY=your_api_key
    export LCC_LLM_MODEL=accounts/fireworks/models/llama-v3p1-70b-instruct
    ```

---

## Verifying Your Installation

After installation, run a quick check:

```bash
# Check version
lcc --version

# Show available commands
lcc --help

# Run a test scan on the LCC repository itself
lcc scan .
```

---

## Next Steps

- [Quick Start](quickstart.md) — Run your first scan in 5 minutes
- [User Guide](../guides/user.md) — Full CLI reference and workflows
- [Deployment Guide](../deployment/index.md) — Production deployment with Docker Compose
