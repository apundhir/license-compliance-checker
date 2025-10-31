"""Shared fixtures and utilities for performance tests."""

from __future__ import annotations

import json
import os
import statistics
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List

import pytest


@dataclass
class PerformanceResult:
    """Results from a performance test."""

    name: str
    iterations: int
    total_time: float
    min_time: float
    max_time: float
    mean_time: float
    median_time: float
    std_dev: float
    percentile_95: float
    percentile_99: float
    operations_per_second: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_time_seconds": round(self.total_time, 4),
            "min_time_seconds": round(self.min_time, 4),
            "max_time_seconds": round(self.max_time, 4),
            "mean_time_seconds": round(self.mean_time, 4),
            "median_time_seconds": round(self.median_time, 4),
            "std_dev": round(self.std_dev, 4),
            "percentile_95": round(self.percentile_95, 4),
            "percentile_99": round(self.percentile_99, 4),
            "operations_per_second": round(self.operations_per_second, 2),
            "metadata": self.metadata
        }

    def __str__(self) -> str:
        """String representation."""
        return (
            f"\n{self.name}:\n"
            f"  Iterations: {self.iterations}\n"
            f"  Total Time: {self.total_time:.4f}s\n"
            f"  Mean Time: {self.mean_time:.4f}s\n"
            f"  Median Time: {self.median_time:.4f}s\n"
            f"  Std Dev: {self.std_dev:.4f}s\n"
            f"  95th %ile: {self.percentile_95:.4f}s\n"
            f"  99th %ile: {self.percentile_99:.4f}s\n"
            f"  Ops/sec: {self.operations_per_second:.2f}\n"
        )


class PerformanceBenchmark:
    """Utility for running performance benchmarks."""

    def __init__(self, name: str, iterations: int = 100, warmup: int = 10):
        """
        Initialize benchmark.

        Args:
            name: Name of the benchmark
            iterations: Number of iterations to run
            warmup: Number of warmup iterations (not measured)
        """
        self.name = name
        self.iterations = iterations
        self.warmup = warmup
        self.times: List[float] = []
        self.metadata: Dict[str, Any] = {}

    def run(self, func: Callable[[], Any]) -> PerformanceResult:
        """
        Run benchmark on a function.

        Args:
            func: Function to benchmark (should be callable with no args)

        Returns:
            Performance results
        """
        # Warmup
        for _ in range(self.warmup):
            func()

        # Actual benchmark
        self.times = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            self.times.append(end - start)

        return self._calculate_results()

    def _calculate_results(self) -> PerformanceResult:
        """Calculate performance statistics."""
        sorted_times = sorted(self.times)
        total_time = sum(self.times)
        mean_time = statistics.mean(self.times)
        median_time = statistics.median(self.times)

        # Standard deviation
        std_dev = statistics.stdev(self.times) if len(self.times) > 1 else 0.0

        # Percentiles
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        percentile_95 = sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1]
        percentile_99 = sorted_times[p99_idx] if p99_idx < len(sorted_times) else sorted_times[-1]

        # Operations per second
        ops_per_second = self.iterations / total_time if total_time > 0 else 0.0

        return PerformanceResult(
            name=self.name,
            iterations=self.iterations,
            total_time=total_time,
            min_time=min(self.times),
            max_time=max(self.times),
            mean_time=mean_time,
            median_time=median_time,
            std_dev=std_dev,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            operations_per_second=ops_per_second,
            metadata=self.metadata
        )


@pytest.fixture
def performance_benchmark():
    """Factory fixture for creating performance benchmarks."""
    def _create_benchmark(name: str, iterations: int = 100, warmup: int = 10) -> PerformanceBenchmark:
        return PerformanceBenchmark(name=name, iterations=iterations, warmup=warmup)
    return _create_benchmark


@pytest.fixture
def performance_results_dir() -> Generator[Path, None, None]:
    """Directory for storing performance test results."""
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    yield results_dir


@pytest.fixture
def save_performance_results(performance_results_dir: Path):
    """Fixture to save performance results to a file."""
    def _save_results(results: PerformanceResult, filename: str = None):
        if filename is None:
            filename = f"{results.name.replace(' ', '_').lower()}.json"

        filepath = performance_results_dir / filename

        # Load existing results if any
        all_results = []
        if filepath.exists():
            with open(filepath, 'r') as f:
                all_results = json.load(f)

        # Add timestamp
        import datetime
        result_dict = results.to_dict()
        result_dict["timestamp"] = datetime.datetime.now().isoformat()

        all_results.append(result_dict)

        # Save updated results
        with open(filepath, 'w') as f:
            json.dump(all_results, f, indent=2)

        print(f"\n✅ Performance results saved to: {filepath}")

    return _save_results


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory for performance testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_dir = Path(tmp_dir) / "test_project"
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create a realistic project structure
        # package.json
        (project_dir / "package.json").write_text(
            json.dumps({
                "name": "test-project",
                "version": "1.0.0",
                "license": "MIT",
                "dependencies": {
                    "express": "^4.18.0",
                    "lodash": "^4.17.21",
                    "react": "^18.2.0"
                }
            }, indent=2)
        )

        # requirements.txt
        (project_dir / "requirements.txt").write_text(
            "requests==2.31.0\n"
            "flask==3.0.0\n"
            "django==4.2.0\n"
            "numpy==1.24.0\n"
            "pandas==2.0.0\n"
        )

        # pyproject.toml
        (project_dir / "pyproject.toml").write_text(
            "[project]\n"
            'name = "test-project"\n'
            'version = "1.0.0"\n'
            "dependencies = [\n"
            '    "requests>=2.31.0",\n'
            '    "click>=8.1.0",\n'
            "]\n"
        )

        # Cargo.toml
        (project_dir / "Cargo.toml").write_text(
            "[package]\n"
            'name = "test-project"\n'
            'version = "1.0.0"\n'
            'license = "Apache-2.0"\n'
            "\n"
            "[dependencies]\n"
            'serde = "1.0"\n'
            'tokio = "1.35"\n'
        )

        # go.mod
        (project_dir / "go.mod").write_text(
            "module github.com/test/project\n"
            "\n"
            "go 1.21\n"
            "\n"
            "require (\n"
            "\tgithub.com/gorilla/mux v1.8.0\n"
            "\tgithub.com/sirupsen/logrus v1.9.0\n"
            ")\n"
        )

        # LICENSE file
        (project_dir / "LICENSE").write_text(
            "MIT License\n\n"
            "Copyright (c) 2024 Test Project\n\n"
            "Permission is hereby granted...\n"
        )

        # Create some source files
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "main.py").write_text(
            "# Main application file\n"
            "import requests\n"
            "import flask\n"
        )

        yield project_dir


@pytest.fixture
def large_project_dir() -> Generator[Path, None, None]:
    """Create a large project directory for stress testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_dir = Path(tmp_dir) / "large_project"
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create many dependency files
        for i in range(10):
            (project_dir / f"requirements_{i}.txt").write_text(
                "\n".join([f"package-{j}=={i}.{j}.0" for j in range(50)])
            )

        # Create nested directory structure
        for i in range(5):
            subdir = project_dir / f"module_{i}" / "submodule" / "nested"
            subdir.mkdir(parents=True, exist_ok=True)
            (subdir / "package.json").write_text(
                json.dumps({
                    "name": f"module-{i}",
                    "dependencies": {f"dep-{j}": f"^{i}.0.0" for j in range(20)}
                }, indent=2)
            )

        yield project_dir


# Performance test markers
def pytest_configure(config):
    """Add custom markers for performance tests."""
    config.addinivalue_line(
        "markers",
        "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (may take several seconds)"
    )
    config.addinivalue_line(
        "markers",
        "benchmark: mark test as a benchmark"
    )
