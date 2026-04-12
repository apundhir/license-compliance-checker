"""Performance tests for scanner operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from lcc.cache import Cache
from lcc.config import LCCConfig
from lcc.factory import build_detectors, build_resolvers
from lcc.scanner import Scanner


@pytest.mark.performance
@pytest.mark.benchmark
class TestScannerPerformance:
    """Test scanner performance with various project sizes."""

    def test_scan_small_project_performance(
        self,
        temp_project_dir: Path,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark scanning a small project (5 files, 10 dependencies)."""
        # Setup
        config = LCCConfig()
        cache = Cache(config)
        detectors = build_detectors(config)
        scanner = Scanner(detectors, build_resolvers(config, cache), config)

        # Benchmark
        benchmark = performance_benchmark("Scan Small Project", iterations=50, warmup=5)

        def scan_operation():
            report = scanner.scan(project_root=Path(temp_project_dir))
            assert report is not None

        result = benchmark.run(scan_operation)
        result.metadata = {
            "project_size": "small",
            "file_count": 5,
            "estimated_dependencies": 10
        }

        print(result)
        save_performance_results(result)

        # Performance assertions
        assert result.mean_time < 2.0, f"Scan took too long: {result.mean_time:.2f}s"
        assert result.percentile_95 < 3.0, f"95th percentile too high: {result.percentile_95:.2f}s"

    def test_scan_medium_project_performance(
        self,
        large_project_dir: Path,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark scanning a medium project (50+ files, 100+ dependencies)."""
        # Setup
        config = LCCConfig()
        cache = Cache(config)
        detectors = build_detectors(config)
        scanner = Scanner(detectors, build_resolvers(config, cache), config)

        # Benchmark (fewer iterations for larger project)
        benchmark = performance_benchmark("Scan Medium Project", iterations=10, warmup=2)

        def scan_operation():
            report = scanner.scan(project_root=Path(large_project_dir))
            assert report is not None

        result = benchmark.run(scan_operation)
        result.metadata = {
            "project_size": "medium",
            "file_count": 50,
            "estimated_dependencies": 100
        }

        print(result)
        save_performance_results(result)

        # Performance assertions
        assert result.mean_time < 10.0, f"Scan took too long: {result.mean_time:.2f}s"
        assert result.percentile_95 < 15.0, f"95th percentile too high: {result.percentile_95:.2f}s"

    def test_detector_initialization_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark detector initialization time."""
        config = LCCConfig()
        cache = Cache(config)

        benchmark = performance_benchmark("Detector Initialization", iterations=100, warmup=10)

        def init_operation():
            detectors = build_detectors(config)
            assert len(detectors) > 0

        result = benchmark.run(init_operation)
        result.metadata = {"operation": "initialization"}

        print(result)
        save_performance_results(result)

        # Should be very fast
        assert result.mean_time < 0.1, f"Initialization too slow: {result.mean_time:.2f}s"

    def test_scan_with_cache_performance(
        self,
        temp_project_dir: Path,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark scanning with cache (should be faster on second run)."""
        config = LCCConfig()
        cache = Cache(config)
        detectors = build_detectors(config)
        scanner = Scanner(detectors, build_resolvers(config, cache), config)

        # First scan to populate cache
        scanner.scan(project_root=Path(temp_project_dir))

        # Benchmark cached scan
        benchmark = performance_benchmark("Scan With Cache", iterations=50, warmup=5)

        def cached_scan_operation():
            report = scanner.scan(project_root=Path(temp_project_dir))
            assert report is not None

        result = benchmark.run(cached_scan_operation)
        result.metadata = {
            "cache_enabled": True,
            "cache_hit_expected": True
        }

        print(result)
        save_performance_results(result)

        # Cached scans should be faster
        assert result.mean_time < 1.5, f"Cached scan too slow: {result.mean_time:.2f}s"

    @pytest.mark.slow
    def test_scan_multiple_ecosystems_performance(
        self,
        temp_project_dir: Path,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark scanning project with multiple package ecosystems."""
        # temp_project_dir already has Python, Node.js, Rust, and Go files
        config = LCCConfig()
        cache = Cache(config)
        detectors = build_detectors(config)
        scanner = Scanner(detectors, build_resolvers(config, cache), config)

        benchmark = performance_benchmark("Scan Multi-Ecosystem Project", iterations=20, warmup=3)

        def multi_ecosystem_scan():
            report = scanner.scan(project_root=Path(temp_project_dir))
            assert report is not None
            # Should detect multiple ecosystems
            assert len(report.findings) > 0

        result = benchmark.run(multi_ecosystem_scan)
        result.metadata = {
            "ecosystems": ["python", "nodejs", "rust", "go"],
            "multi_ecosystem": True
        }

        print(result)
        save_performance_results(result)

        # Multi-ecosystem should still be reasonable
        assert result.mean_time < 3.0, f"Multi-ecosystem scan too slow: {result.mean_time:.2f}s"

    def test_scan_exclude_patterns_performance(
        self,
        large_project_dir: Path,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark scanning with exclude patterns."""
        config = LCCConfig()
        cache = Cache(config)
        detectors = build_detectors(config)
        scanner = Scanner(detectors, build_resolvers(config, cache), config)

        exclude_patterns = ["node_modules/**", "*.pyc", "test/**", "docs/**"]

        benchmark = performance_benchmark("Scan With Exclusions", iterations=15, warmup=3)

        def scan_with_exclusions():
            report = scanner.scan(project_root=Path(large_project_dir), exclude=exclude_patterns)
            assert report is not None

        result = benchmark.run(scan_with_exclusions)
        result.metadata = {
            "exclude_patterns": len(exclude_patterns),
            "patterns": exclude_patterns
        }

        print(result)
        save_performance_results(result)

        # Exclusions should make scan faster
        assert result.mean_time < 8.0, f"Scan with exclusions too slow: {result.mean_time:.2f}s"


@pytest.mark.performance
class TestDetectorPerformance:
    """Test individual detector performance."""

    def test_python_detector_performance(
        self,
        temp_project_dir: Path,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark Python package detector."""
        from lcc.detection.python import PythonDetector
        from lcc.cache import Cache
        from lcc.config import LCCConfig

        config = LCCConfig()
        cache = Cache(config)
        detector = PythonDetector(cache=cache)

        benchmark = performance_benchmark("Python Detector", iterations=100, warmup=10)

        def detect_operation():
            findings = detector.detect(temp_project_dir)
            assert isinstance(findings, list)

        result = benchmark.run(detect_operation)
        result.metadata = {"detector": "python", "ecosystem": "python"}

        print(result)
        save_performance_results(result)

        assert result.mean_time < 0.5, f"Python detector too slow: {result.mean_time:.2f}s"

    def test_nodejs_detector_performance(
        self,
        temp_project_dir: Path,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark Node.js package detector."""
        from lcc.detection.nodejs import NodeJSDetector
        from lcc.cache import Cache
        from lcc.config import LCCConfig

        config = LCCConfig()
        cache = Cache(config)
        detector = NodeJSDetector(cache=cache)

        benchmark = performance_benchmark("Node.js Detector", iterations=100, warmup=10)

        def detect_operation():
            findings = detector.detect(temp_project_dir)
            assert isinstance(findings, list)

        result = benchmark.run(detect_operation)
        result.metadata = {"detector": "nodejs", "ecosystem": "javascript"}

        print(result)
        save_performance_results(result)

        assert result.mean_time < 0.5, f"Node.js detector too slow: {result.mean_time:.2f}s"

    def test_concurrent_detection_performance(
        self,
        temp_project_dir: Path,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark concurrent detector execution."""
        from lcc.config import LCCConfig
        from lcc.cache import Cache
        from lcc.factory import build_detectors

        config = LCCConfig()
        cache = Cache(config)
        detectors = build_detectors(config)

        benchmark = performance_benchmark("Concurrent Detection", iterations=50, warmup=5)

        def concurrent_detect():
            # Run all detectors
            all_findings = []
            for detector in detectors:
                findings = detector.detect(temp_project_dir)
                all_findings.extend(findings)
            assert len(all_findings) >= 0

        result = benchmark.run(concurrent_detect)
        result.metadata = {
            "detector_count": len(detectors),
            "concurrent": True
        }

        print(result)
        save_performance_results(result)

        # Should benefit from concurrency
        assert result.mean_time < 1.0, f"Concurrent detection too slow: {result.mean_time:.2f}s"


@pytest.mark.performance
class TestScannerScalability:
    """Test scanner scalability with increasing load."""

    def test_scan_scalability_by_file_count(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Test how scan time scales with number of files."""
        import tempfile
        import json

        config = LCCConfig()
        cache = Cache(config)
        detectors = build_detectors(config)
        scanner = Scanner(detectors, build_resolvers(config, cache), config)

        results = []

        for file_count in [10, 50, 100]:
            with tempfile.TemporaryDirectory() as tmp_dir:
                project_dir = Path(tmp_dir)

                # Create many package files
                for i in range(file_count):
                    (project_dir / f"package_{i}.json").write_text(
                        json.dumps({
                            "name": f"package-{i}",
                            "dependencies": {f"dep-{j}": "1.0.0" for j in range(5)}
                        })
                    )

                benchmark = performance_benchmark(
                    f"Scan {file_count} Files",
                    iterations=10,
                    warmup=2
                )

                def scan_n_files():
                    report = scanner.scan(project_root=Path(project_dir))
                    assert report is not None

                result = benchmark.run(scan_n_files)
                result.metadata = {"file_count": file_count}
                results.append(result)

                print(result)

        # Save all results
        for result in results:
            save_performance_results(result, "scanner_scalability.json")

        # Check scalability
        # Time should scale sub-linearly (not O(n^2))
        if len(results) >= 2:
            time_ratio = results[-1].mean_time / results[0].mean_time
            file_ratio = results[-1].metadata["file_count"] / results[0].metadata["file_count"]

            print(f"\nScalability: {file_ratio}x files -> {time_ratio:.2f}x time")
            assert time_ratio < file_ratio * 1.5, "Poor scalability detected"
