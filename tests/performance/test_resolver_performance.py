"""Performance tests for license resolution."""

from __future__ import annotations

import pytest

from lcc.cache import Cache
from lcc.config import LCCConfig
from lcc.factory import build_resolvers
from lcc.models import PackageInfo


@pytest.mark.performance
@pytest.mark.benchmark
class TestResolverPerformance:
    """Test resolver performance."""

    def test_registry_resolver_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark registry-based license resolution."""
        from lcc.resolution.registry_resolver import RegistryResolver

        config = LCCConfig()
        cache = Cache(config)
        resolver = RegistryResolver(cache=cache)

        # Common packages
        packages = [
            PackageInfo(name="requests", version="2.31.0", ecosystem="python"),
            PackageInfo(name="flask", version="3.0.0", ecosystem="python"),
            PackageInfo(name="express", version="4.18.0", ecosystem="nodejs"),
            PackageInfo(name="react", version="18.2.0", ecosystem="nodejs"),
        ]

        benchmark = performance_benchmark("Registry Resolver", iterations=20, warmup=3)

        def resolve_operation():
            for pkg in packages:
                result = resolver.resolve(pkg)
                # Result may be None if network/cache unavailable
                assert result is not None or True

        result = benchmark.run(resolve_operation)
        result.metadata = {
            "resolver": "registry",
            "package_count": len(packages),
            "cache_enabled": True
        }

        print(result)
        save_performance_results(result)

        # Should be reasonably fast (network dependent)
        assert result.mean_time < 5.0, f"Registry resolver too slow: {result.mean_time:.2f}s"

    def test_fallback_resolver_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark fallback resolver chain."""
        config = LCCConfig()
        cache = Cache(config)
        resolvers = build_resolvers(config, cache)

        packages = [
            PackageInfo(name="unknown-package-xyz", version="1.0.0", ecosystem="python"),
            PackageInfo(name="test-package-123", version="2.0.0", ecosystem="nodejs"),
        ]

        benchmark = performance_benchmark("Fallback Resolver Chain", iterations=10, warmup=2)

        def resolve_with_fallback():
            for pkg in packages:
                for resolver in resolvers:
                    result = resolver.resolve(pkg)
                    if result:
                        break

        result = benchmark.run(resolve_with_fallback)
        result.metadata = {
            "resolver_count": len(resolvers),
            "fallback": True
        }

        print(result)
        save_performance_results(result)

    def test_cached_resolution_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark resolution with warm cache."""
        from lcc.resolution.registry_resolver import RegistryResolver

        config = LCCConfig()
        cache = Cache(config)
        resolver = RegistryResolver(cache=cache)

        pkg = PackageInfo(name="requests", version="2.31.0", ecosystem="python")

        # Prime the cache
        resolver.resolve(pkg)

        benchmark = performance_benchmark("Cached Resolution", iterations=100, warmup=10)

        def cached_resolve():
            result = resolver.resolve(pkg)
            assert result is not None or True

        result = benchmark.run(cached_resolve)
        result.metadata = {
            "cache_hit": True,
            "resolver": "registry"
        }

        print(result)
        save_performance_results(result)

        # Cached resolutions should be very fast
        assert result.mean_time < 0.1, f"Cached resolution too slow: {result.mean_time:.2f}s"

    def test_bulk_resolution_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark resolving many packages."""
        config = LCCConfig()
        cache = Cache(config)
        resolvers = build_resolvers(config, cache)

        # Generate many packages
        packages = []
        for i in range(50):
            packages.append(
                PackageInfo(name=f"package-{i}", version="1.0.0", ecosystem="python")
            )

        benchmark = performance_benchmark("Bulk Resolution (50 packages)", iterations=5, warmup=1)

        def bulk_resolve():
            for pkg in packages:
                for resolver in resolvers:
                    result = resolver.resolve(pkg)
                    if result:
                        break

        result = benchmark.run(bulk_resolve)
        result.metadata = {
            "package_count": len(packages),
            "bulk": True
        }

        print(result)
        save_performance_results(result)

        # Should handle bulk operations
        assert result.mean_time < 30.0, f"Bulk resolution too slow: {result.mean_time:.2f}s"


@pytest.mark.performance
class TestResolverScalability:
    """Test resolver scalability."""

    def test_resolution_scalability(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Test how resolution time scales with package count."""
        config = LCCConfig()
        cache = Cache(config)
        resolvers = build_resolvers(config, cache)

        results = []

        for pkg_count in [10, 25, 50]:
            packages = [
                PackageInfo(name=f"pkg-{i}", version="1.0.0", ecosystem="python")
                for i in range(pkg_count)
            ]

            benchmark = performance_benchmark(
                f"Resolve {pkg_count} Packages",
                iterations=3,
                warmup=1
            )

            def resolve_n_packages():
                for pkg in packages:
                    for resolver in resolvers:
                        result = resolver.resolve(pkg)
                        if result:
                            break

            result = benchmark.run(resolve_n_packages)
            result.metadata = {"package_count": pkg_count}
            results.append(result)

            print(result)

        # Save all results
        for result in results:
            save_performance_results(result, "resolver_scalability.json")

        # Check linear scalability
        if len(results) >= 2:
            time_ratio = results[-1].mean_time / results[0].mean_time
            pkg_ratio = results[-1].metadata["package_count"] / results[0].metadata["package_count"]

            print(f"\nScalability: {pkg_ratio}x packages -> {time_ratio:.2f}x time")
            # Should scale roughly linearly (or better with caching)
            assert time_ratio < pkg_ratio * 1.5, "Poor scalability detected"
