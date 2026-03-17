"""
Speed benchmark for LCC scanning performance.

Measures scan time across project sizes and ecosystems:
- Small project (10 deps)
- Medium project (50 deps)
- Large project (200+ deps)

Breakdown: total time, detection time, resolution time.
Target: <10s for 50 deps (manifest-only scan).
"""

from __future__ import annotations

import json
import statistics
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lcc.cache import Cache
from lcc.config import LCCConfig
from lcc.detection.base import Detector
from lcc.models import Component, ComponentFinding, ScanReport
from lcc.resolution.base import Resolver
from lcc.resolution.fallback import FallbackResolver
from lcc.scanner import Scanner


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TimingResult:
    """Timing measurements for a single benchmark run."""
    label: str
    ecosystem: str
    dependency_count: int
    iterations: int
    total_times: List[float] = field(default_factory=list)
    detection_times: List[float] = field(default_factory=list)
    resolution_times: List[float] = field(default_factory=list)

    def _stats(self, data: List[float]) -> Dict[str, float]:
        if not data:
            return {"mean": 0, "median": 0, "p95": 0, "min": 0, "max": 0, "stdev": 0}
        sorted_data = sorted(data)
        p95_idx = min(int(len(sorted_data) * 0.95), len(sorted_data) - 1)
        return {
            "mean": round(statistics.mean(data), 6),
            "median": round(statistics.median(data), 6),
            "p95": round(sorted_data[p95_idx], 6),
            "min": round(min(data), 6),
            "max": round(max(data), 6),
            "stdev": round(statistics.stdev(data), 6) if len(data) > 1 else 0,
        }

    @property
    def total_stats(self) -> Dict[str, float]:
        return self._stats(self.total_times)

    @property
    def detection_stats(self) -> Dict[str, float]:
        return self._stats(self.detection_times)

    @property
    def resolution_stats(self) -> Dict[str, float]:
        return self._stats(self.resolution_times)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "ecosystem": self.ecosystem,
            "dependency_count": self.dependency_count,
            "iterations": self.iterations,
            "total": self.total_stats,
            "detection": self.detection_stats,
            "resolution": self.resolution_stats,
        }


@dataclass
class SpeedResults:
    """Aggregated speed benchmark results."""
    timestamp: str = ""
    duration_seconds: float = 0.0
    results: List[TimingResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "duration_seconds": round(self.duration_seconds, 3),
            "benchmarks": [r.to_dict() for r in self.results],
        }

    def to_markdown(self) -> str:
        lines = [
            "# LCC Speed Benchmark Results",
            "",
            f"**Date:** {self.timestamp}",
            f"**Duration:** {self.duration_seconds:.1f}s",
            "",
            "## Summary",
            "",
            "| Benchmark | Ecosystem | Deps | Iters | Mean (s) | Median (s) | P95 (s) | Min (s) | Max (s) |",
            "|-----------|-----------|------|-------|----------|------------|---------|---------|---------|",
        ]
        for r in self.results:
            s = r.total_stats
            lines.append(
                f"| {r.label} | {r.ecosystem} | {r.dependency_count} | {r.iterations} | "
                f"{s['mean']:.4f} | {s['median']:.4f} | {s['p95']:.4f} | "
                f"{s['min']:.4f} | {s['max']:.4f} |"
            )

        lines.extend([
            "",
            "## Phase Breakdown (mean seconds)",
            "",
            "| Benchmark | Detection | Resolution | Total |",
            "|-----------|-----------|------------|-------|",
        ])
        for r in self.results:
            lines.append(
                f"| {r.label} | {r.detection_stats['mean']:.4f} | "
                f"{r.resolution_stats['mean']:.4f} | {r.total_stats['mean']:.4f} |"
            )

        # Highlight pass/fail against target
        lines.extend([
            "",
            "## Target Compliance",
            "",
            "| Target | Status |",
            "|--------|--------|",
        ])
        medium_results = [r for r in self.results if "medium" in r.label.lower()]
        if medium_results:
            worst_mean = max(r.total_stats["mean"] for r in medium_results)
            status = "PASS" if worst_mean < 10.0 else "FAIL"
            lines.append(f"| Medium project (<10s for 50 deps) | {status} ({worst_mean:.2f}s) |")
        else:
            lines.append("| Medium project (<10s for 50 deps) | N/A |")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Instrumented scanner — wraps the real scanner to capture per-phase timings
# ---------------------------------------------------------------------------

class InstrumentedScanner:
    """
    Wraps a Scanner instance to measure detection and resolution phases
    separately, without modifying the core Scanner code.
    """

    def __init__(
        self,
        detectors: List[Detector],
        resolvers: List[Resolver],
        config: LCCConfig,
    ) -> None:
        self.detectors = detectors
        self.resolvers = resolvers
        self.config = config

    def scan_timed(self, project_root: Path) -> Tuple[ScanReport, float, float]:
        """
        Run a scan and return (report, detection_seconds, resolution_seconds).
        """
        # Detection phase
        det_start = time.perf_counter()
        findings: List[ComponentFinding] = []
        for detector in self.detectors:
            if not detector.supports(project_root):
                continue
            for component in detector.discover(project_root):
                component.metadata.setdefault("project_root", str(project_root))
                findings.append(ComponentFinding(component=component))
        det_elapsed = time.perf_counter() - det_start

        # Resolution phase
        res_start = time.perf_counter()
        fallback = FallbackResolver(self.resolvers)
        for finding in findings:
            fallback.resolve(finding)
        res_elapsed = time.perf_counter() - res_start

        from lcc.models import ScanSummary
        summary = ScanSummary(
            component_count=len(findings),
            violations=0,
            duration_seconds=det_elapsed + res_elapsed,
        )
        report = ScanReport(findings=findings, summary=summary, errors=[])
        return report, det_elapsed, res_elapsed


# ---------------------------------------------------------------------------
# Fixture generators — create projects of different sizes
# ---------------------------------------------------------------------------

_PYTHON_PACKAGES = [
    "requests", "flask", "django", "numpy", "pandas", "scipy", "click",
    "pydantic", "sqlalchemy", "celery", "pytest", "boto3", "pillow",
    "cryptography", "aiohttp", "httpx", "fastapi", "uvicorn", "gunicorn",
    "black", "isort", "mypy", "ruff", "tox", "coverage", "sphinx",
    "jinja2", "werkzeug", "markupsafe", "itsdangerous", "blinker",
    "typing-extensions", "packaging", "setuptools", "wheel", "pip",
    "virtualenv", "pipenv", "poetry", "flit", "hatchling", "maturin",
    "cython", "cffi", "pycparser", "six", "chardet", "certifi", "idna",
    "urllib3", "charset-normalizer",
    "decorator", "attrs", "cattrs", "marshmallow", "dataclasses-json",
    "orjson", "ujson", "msgpack", "protobuf", "grpcio", "grpcio-tools",
    "pyyaml", "toml", "tomli", "configparser", "python-dotenv",
    "loguru", "structlog", "rich", "colorama", "tqdm", "alive-progress",
    "arrow", "pendulum", "python-dateutil", "pytz", "babel",
    "psycopg2", "pymongo", "redis", "elasticsearch", "cassandra-driver",
    "paramiko", "fabric", "invoke", "plumbum", "pexpect", "sshtunnel",
    "beautifulsoup4", "lxml", "scrapy", "selenium", "playwright",
    "matplotlib", "seaborn", "plotly", "bokeh", "altair", "dash",
    "networkx", "igraph", "graphviz", "pydot", "pygraphviz",
    "scikit-learn", "xgboost", "lightgbm", "catboost", "optuna",
    "transformers", "tokenizers", "datasets", "accelerate", "diffusers",
    "torch", "torchvision", "torchaudio", "tensorflow", "keras",
    "sympy", "mpmath", "gmpy2", "primesieve", "galois",
    "imageio", "scikit-image", "opencv-python", "albumentations",
    "pyarrow", "polars", "dask", "vaex", "modin",
    "airflow", "prefect", "dagster", "luigi", "mlflow",
    "boto3", "google-cloud-storage", "azure-storage-blob",
    "sentry-sdk", "prometheus-client", "opentelemetry-api",
    "pyjwt", "passlib", "bcrypt", "argon2-cffi", "python-jose",
    "httptools", "uvloop", "websockets", "starlette", "anyio",
    "tenacity", "backoff", "retrying", "stamina", "circuit-breaker",
    "click-plugins", "click-completion", "typer", "fire", "docopt",
    "apscheduler", "schedule", "croniter", "rq", "dramatiq",
    "alembic", "flyway", "yoyo", "peewee", "tortoise-orm",
    "faker", "factory-boy", "hypothesis", "mimesis", "polyfactory",
    "bandit", "safety", "pip-audit", "cyclonedx-python-lib",
    "pre-commit", "commitizen", "semantic-release", "bumpversion",
    "mkdocs", "mkdocs-material", "pdoc", "pydoc-markdown",
    "pygments", "docutils", "readme-renderer", "towncrier",
    "pathlib2", "watchdog", "inotify", "pyinotify", "fsspec",
    "psutil", "py-cpuinfo", "gputil", "nvidia-ml-py", "pynvml",
    "anthropic", "openai", "cohere", "replicate", "langchain",
]

_JS_PACKAGES = [
    "express", "react", "react-dom", "next", "vue", "angular",
    "axios", "lodash", "moment", "dayjs", "date-fns", "luxon",
    "webpack", "vite", "rollup", "esbuild", "parcel", "turbopack",
    "typescript", "eslint", "prettier", "stylelint", "husky",
    "jest", "mocha", "vitest", "cypress", "playwright", "puppeteer",
    "tailwindcss", "bootstrap", "material-ui", "antd", "chakra-ui",
    "prisma", "sequelize", "typeorm", "mongoose", "knex", "drizzle-orm",
    "fastify", "koa", "hapi", "nestjs", "socket.io", "ws",
    "zod", "yup", "joi", "ajv", "class-validator", "superstruct",
    "redux", "zustand", "mobx", "recoil", "jotai", "valtio",
    "react-query", "swr", "apollo-client", "urql", "relay",
    "chalk", "inquirer", "commander", "yargs", "ora", "listr2",
    "dotenv", "config", "convict", "env-var", "cross-env",
    "winston", "pino", "bunyan", "morgan", "debug", "loglevel",
    "uuid", "nanoid", "cuid", "ulid", "shortid",
    "bcryptjs", "jsonwebtoken", "passport", "helmet", "cors",
    "sharp", "jimp", "canvas", "imagemin", "svgo",
    "cheerio", "jsdom", "node-html-parser", "linkedom",
    "nodemailer", "sendgrid", "mailgun-js", "postmark",
    "stripe", "paypal-rest-sdk", "braintree", "square",
    "aws-sdk", "firebase", "supabase", "convex",
    "bull", "bullmq", "agenda", "bee-queue", "node-cron",
    "puppeteer", "selenium-webdriver", "nightwatch",
    "d3", "chart.js", "highcharts", "echarts", "three",
    "rxjs", "ramda", "immutable", "immer", "mori",
    "glob", "minimatch", "micromatch", "picomatch",
    "fs-extra", "graceful-fs", "chokidar", "watchpack",
    "node-fetch", "got", "undici", "superagent", "ky",
    "formidable", "multer", "busboy", "form-data",
    "compression", "serve-static", "http-proxy-middleware",
    "cookie-parser", "express-session", "connect-redis",
    "rate-limiter-flexible", "express-rate-limit", "bottleneck",
    "async", "p-limit", "p-queue", "p-retry", "p-map",
    "semver", "compare-versions", "resolve",
    "cross-spawn", "execa", "shelljs", "zx",
    "lerna", "nx", "turborepo", "changesets",
    "storybook", "docusaurus", "nextra", "vuepress",
    "sentry-node", "newrelic", "datadog-metrics",
    "openai", "langchain", "anthropic-sdk", "cohere-ai",
]

_GO_MODULES = [
    "github.com/gin-gonic/gin", "github.com/labstack/echo/v4",
    "github.com/gofiber/fiber/v2", "github.com/gorilla/mux",
    "github.com/go-chi/chi/v5", "github.com/julienschmidt/httprouter",
    "google.golang.org/grpc", "google.golang.org/protobuf",
    "github.com/spf13/cobra", "github.com/spf13/viper",
    "github.com/spf13/pflag", "github.com/spf13/afero",
    "go.uber.org/zap", "github.com/sirupsen/logrus",
    "github.com/rs/zerolog", "go.uber.org/fx",
    "gorm.io/gorm", "gorm.io/driver/postgres",
    "github.com/jmoiron/sqlx", "github.com/jackc/pgx/v5",
    "github.com/go-redis/redis/v9", "go.mongodb.org/mongo-driver",
    "github.com/stretchr/testify", "github.com/onsi/ginkgo/v2",
    "github.com/prometheus/client_golang", "go.opentelemetry.io/otel",
    "github.com/golang-jwt/jwt/v5", "golang.org/x/crypto",
    "golang.org/x/net", "golang.org/x/sys",
    "golang.org/x/text", "golang.org/x/sync",
    "github.com/docker/docker", "github.com/docker/cli",
    "k8s.io/client-go", "k8s.io/api",
    "k8s.io/apimachinery", "sigs.k8s.io/controller-runtime",
    "github.com/aws/aws-sdk-go-v2", "github.com/Azure/azure-sdk-for-go",
    "cloud.google.com/go", "cloud.google.com/go/storage",
    "github.com/hashicorp/consul/api", "github.com/hashicorp/vault/api",
    "github.com/nats-io/nats.go", "github.com/segmentio/kafka-go",
    "github.com/go-playground/validator/v10", "github.com/go-playground/universal-translator",
    "github.com/mitchellh/mapstructure", "github.com/pelletier/go-toml/v2",
]


def _generate_python_deps(count: int) -> List[Dict[str, str]]:
    deps = []
    for i, pkg in enumerate(_PYTHON_PACKAGES[:count]):
        deps.append({"name": pkg, "version": f"1.{i}.0"})
    # If we need more than the list provides, generate synthetic ones
    for i in range(len(deps), count):
        deps.append({"name": f"bench-pkg-{i}", "version": f"0.{i}.0"})
    return deps


def _generate_js_deps(count: int) -> List[Dict[str, str]]:
    deps = []
    for i, pkg in enumerate(_JS_PACKAGES[:count]):
        deps.append({"name": pkg, "version": f"1.{i}.0"})
    for i in range(len(deps), count):
        deps.append({"name": f"bench-pkg-{i}", "version": f"0.{i}.0"})
    return deps


def _generate_go_deps(count: int) -> List[Dict[str, str]]:
    deps = []
    for i, mod in enumerate(_GO_MODULES[:count]):
        deps.append({"name": mod, "version": f"v1.{i}.0"})
    for i in range(len(deps), count):
        deps.append({"name": f"github.com/bench/mod-{i}", "version": f"v0.{i}.0"})
    return deps


def _create_speed_fixture(
    project_dir: Path,
    ecosystem: str,
    dep_count: int,
) -> None:
    """Create a benchmark fixture project with the requested number of dependencies."""
    if ecosystem == "python":
        deps = _generate_python_deps(dep_count)
        lines = [f"{d['name']}=={d['version']}" for d in deps]
        (project_dir / "requirements.txt").write_text("\n".join(lines) + "\n")
    elif ecosystem == "javascript":
        deps = _generate_js_deps(dep_count)
        pkg_deps = {d["name"]: f"^{d['version']}" for d in deps}
        pkg = {
            "name": "speed-benchmark",
            "version": "1.0.0",
            "license": "MIT",
            "dependencies": pkg_deps,
        }
        (project_dir / "package.json").write_text(json.dumps(pkg, indent=2) + "\n")
    elif ecosystem == "go":
        deps = _generate_go_deps(dep_count)
        lines = ["module github.com/benchmark/speed-test", "", "go 1.22", "", "require ("]
        for d in deps:
            lines.append(f"\t{d['name']} {d['version']}")
        lines.append(")")
        (project_dir / "go.mod").write_text("\n".join(lines) + "\n")
    else:
        # Generic fallback — create requirements.txt-style
        deps = _generate_python_deps(dep_count)
        lines = [f"{d['name']}=={d['version']}" for d in deps]
        (project_dir / "requirements.txt").write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------

def _build_instrumented_scanner() -> InstrumentedScanner:
    config = LCCConfig(offline=True)
    cache_dir = Path(tempfile.mkdtemp(prefix="lcc_speed_bench_"))
    config.cache_dir = cache_dir
    cache = Cache(config)

    from lcc.factory import build_detectors, build_resolvers
    detectors = build_detectors(config)
    resolvers = build_resolvers(config, cache)
    return InstrumentedScanner(detectors, resolvers, config)


def run_speed_benchmark(
    ecosystems: Optional[List[str]] = None,
    iterations: int = 5,
    warmup: int = 1,
    verbose: bool = False,
) -> SpeedResults:
    """
    Run the speed benchmark across project sizes and ecosystems.

    Args:
        ecosystems: Ecosystems to test. Defaults to ["python", "javascript", "go"].
        iterations: Number of measured iterations per test.
        warmup: Number of warmup iterations (not counted).
        verbose: Print progress.

    Returns:
        SpeedResults with all timing data.
    """
    from datetime import datetime, timezone

    if ecosystems is None:
        ecosystems = ["python", "javascript", "go"]

    sizes = [
        ("small", 10),
        ("medium", 50),
        ("large", 200),
    ]

    results = SpeedResults(timestamp=datetime.now(timezone.utc).isoformat())
    bench_start = time.time()

    scanner = _build_instrumented_scanner()

    for ecosystem in ecosystems:
        for size_label, dep_count in sizes:
            label = f"{ecosystem}/{size_label} ({dep_count} deps)"
            if verbose:
                print(f"  {label} ...", end=" ", flush=True)

            timing = TimingResult(
                label=label,
                ecosystem=ecosystem,
                dependency_count=dep_count,
                iterations=iterations,
            )

            with tempfile.TemporaryDirectory(prefix=f"lcc_speed_{ecosystem}_{size_label}_") as tmp_dir:
                project_dir = Path(tmp_dir)
                _create_speed_fixture(project_dir, ecosystem, dep_count)

                # Warmup
                for _ in range(warmup):
                    scanner.scan_timed(project_dir)

                # Measured iterations
                for _ in range(iterations):
                    t_start = time.perf_counter()
                    _report, det_time, res_time = scanner.scan_timed(project_dir)
                    total_time = time.perf_counter() - t_start

                    timing.total_times.append(total_time)
                    timing.detection_times.append(det_time)
                    timing.resolution_times.append(res_time)

            results.results.append(timing)

            if verbose:
                s = timing.total_stats
                print(f"mean={s['mean']:.4f}s  p95={s['p95']:.4f}s")

    results.duration_seconds = time.time() - bench_start
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LCC Speed Benchmark")
    parser.add_argument("--ecosystem", action="append", dest="ecosystems", help="Ecosystems to test (repeatable)")
    parser.add_argument("--iterations", "-n", type=int, default=5, help="Measured iterations per test")
    parser.add_argument("--warmup", "-w", type=int, default=1, help="Warmup iterations")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--output", type=Path, help="Write JSON results")
    parser.add_argument("--markdown", type=Path, help="Write markdown report")
    args = parser.parse_args()

    print("=" * 60)
    print("LCC Speed Benchmark")
    print("=" * 60)
    print()

    results = run_speed_benchmark(
        ecosystems=args.ecosystems,
        iterations=args.iterations,
        warmup=args.warmup,
        verbose=args.verbose,
    )

    # Summary
    print()
    print(f"Completed in {results.duration_seconds:.1f}s")
    print()
    print(f"{'Benchmark':<40} {'Mean':>10} {'P95':>10} {'Min':>10}")
    print("-" * 72)
    for r in results.results:
        s = r.total_stats
        print(f"{r.label:<40} {s['mean']:>9.4f}s {s['p95']:>9.4f}s {s['min']:>9.4f}s")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results.to_dict(), f, indent=2)
        print(f"\nJSON results written to {args.output}")

    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(results.to_markdown(), encoding="utf-8")
        print(f"Markdown report written to {args.markdown}")


if __name__ == "__main__":
    main()
