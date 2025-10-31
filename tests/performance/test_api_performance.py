"""Performance tests for API endpoints."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.mark.performance
@pytest.mark.benchmark
class TestAPIEndpointPerformance:
    """Test API endpoint performance."""

    @pytest.fixture
    def test_client(self, temp_project_dir: Path):
        """Create test API client."""
        import os
        import tempfile
        from lcc.api.server import create_app
        from lcc.auth.repository import UserRepository
        from lcc.auth.core import UserRole

        with tempfile.TemporaryDirectory() as tmp_dir:
            os.environ["LCC_DB_PATH"] = f"{tmp_dir}/test.db"
            os.environ["LCC_POLICY_DIR"] = f"{tmp_dir}/policies"
            os.environ["LCC_CACHE_DIR"] = f"{tmp_dir}/cache"

            # Create app
            app = create_app()
            client = TestClient(app)

            # Create test user
            user_repo = UserRepository(Path(tmp_dir) / "test.db")
            user_repo.create_user(
                username="perftest",
                password="password123",
                role=UserRole.ADMIN
            )

            # Login
            response = client.post(
                "/auth/login",
                data={"username": "perftest", "password": "password123"}
            )
            token = response.json()["access_token"]

            # Store token for tests
            client.headers = {"Authorization": f"Bearer {token}"}

            yield client

            # Cleanup
            for key in ["LCC_DB_PATH", "LCC_POLICY_DIR", "LCC_CACHE_DIR"]:
                os.environ.pop(key, None)

    def test_health_endpoint_performance(
        self,
        test_client: TestClient,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark /health endpoint."""
        benchmark = performance_benchmark("Health Endpoint", iterations=1000, warmup=100)

        def health_check():
            response = test_client.get("/health")
            assert response.status_code == 200

        result = benchmark.run(health_check)
        result.metadata = {"endpoint": "/health", "method": "GET"}

        print(result)
        save_performance_results(result)

        # Health check should be extremely fast
        assert result.mean_time < 0.01, f"Health check too slow: {result.mean_time:.4f}s"
        assert result.operations_per_second > 100, f"Too few ops/sec: {result.operations_per_second:.2f}"

    def test_list_policies_performance(
        self,
        test_client: TestClient,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark GET /policies endpoint."""
        benchmark = performance_benchmark("List Policies", iterations=200, warmup=20)

        def list_policies():
            response = test_client.get("/policies")
            assert response.status_code == 200
            assert isinstance(response.json(), list)

        result = benchmark.run(list_policies)
        result.metadata = {"endpoint": "/policies", "method": "GET"}

        print(result)
        save_performance_results(result)

        assert result.mean_time < 0.1, f"List policies too slow: {result.mean_time:.4f}s"

    def test_create_policy_performance(
        self,
        test_client: TestClient,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark POST /policies endpoint."""
        policy_content = """
name: perf-test-policy
version: 1.0
disclaimer: Performance test policy
contexts:
  production:
    allow: [MIT]
        """.strip()

        benchmark = performance_benchmark("Create Policy", iterations=50, warmup=5)

        counter = [0]  # Use list for mutable counter

        def create_policy():
            response = test_client.post(
                "/policies",
                json={
                    "name": f"perf-policy-{counter[0]}",
                    "content": policy_content.replace("perf-test-policy", f"perf-policy-{counter[0]}"),
                    "format": "yaml"
                }
            )
            counter[0] += 1
            assert response.status_code == 201

        result = benchmark.run(create_policy)
        result.metadata = {"endpoint": "/policies", "method": "POST"}

        print(result)
        save_performance_results(result)

        # Cleanup: delete created policies
        for i in range(counter[0]):
            test_client.delete(f"/policies/perf-policy-{i}")

        assert result.mean_time < 0.2, f"Create policy too slow: {result.mean_time:.4f}s"

    def test_dashboard_performance(
        self,
        test_client: TestClient,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark GET /dashboard endpoint."""
        benchmark = performance_benchmark("Dashboard", iterations=100, warmup=10)

        def get_dashboard():
            response = test_client.get("/dashboard")
            assert response.status_code == 200
            data = response.json()
            assert "totalScans" in data

        result = benchmark.run(get_dashboard)
        result.metadata = {"endpoint": "/dashboard", "method": "GET"}

        print(result)
        save_performance_results(result)

        assert result.mean_time < 0.5, f"Dashboard too slow: {result.mean_time:.4f}s"


@pytest.mark.performance
class TestAPIConcurrency:
    """Test API performance under concurrent load."""

    @pytest.fixture
    def test_client(self):
        """Create test API client."""
        import os
        import tempfile
        from lcc.api.server import create_app
        from lcc.auth.repository import UserRepository
        from lcc.auth.core import UserRole

        with tempfile.TemporaryDirectory() as tmp_dir:
            os.environ["LCC_DB_PATH"] = f"{tmp_dir}/test.db"
            os.environ["LCC_POLICY_DIR"] = f"{tmp_dir}/policies"
            os.environ["LCC_CACHE_DIR"] = f"{tmp_dir}/cache"

            app = create_app()
            client = TestClient(app)

            user_repo = UserRepository(Path(tmp_dir) / "test.db")
            user_repo.create_user(
                username="concurrency_test",
                password="password123",
                role=UserRole.ADMIN
            )

            response = client.post(
                "/auth/login",
                data={"username": "concurrency_test", "password": "password123"}
            )
            token = response.json()["access_token"]
            client.headers = {"Authorization": f"Bearer {token}"}

            yield client

            for key in ["LCC_DB_PATH", "LCC_POLICY_DIR", "LCC_CACHE_DIR"]:
                os.environ.pop(key, None)

    @pytest.mark.slow
    def test_concurrent_requests_performance(
        self,
        test_client: TestClient,
        performance_benchmark,
        save_performance_results
    ):
        """Test API performance with concurrent requests."""
        import time

        def make_request(i: int):
            start = time.perf_counter()
            response = test_client.get("/health")
            end = time.perf_counter()
            return {
                "success": response.status_code == 200,
                "duration": end - start
            }

        # Test different concurrency levels
        for concurrency in [1, 5, 10]:
            start_time = time.perf_counter()

            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(make_request, i) for i in range(100)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            end_time = time.perf_counter()
            total_time = end_time - start_time

            success_count = sum(1 for r in results if r["success"])
            avg_latency = sum(r["duration"] for r in results) / len(results)
            throughput = len(results) / total_time

            print(f"\nConcurrency {concurrency}:")
            print(f"  Total Time: {total_time:.2f}s")
            print(f"  Success Rate: {success_count}/{len(results)}")
            print(f"  Avg Latency: {avg_latency:.4f}s")
            print(f"  Throughput: {throughput:.2f} req/s")

            # Assert reasonable performance
            assert success_count == len(results), "Some requests failed"
            assert throughput > 10, f"Throughput too low: {throughput:.2f} req/s"


@pytest.mark.performance
class TestAPIThroughput:
    """Test API throughput and sustained load."""

    @pytest.fixture
    def test_client(self):
        """Create test API client."""
        import os
        import tempfile
        from lcc.api.server import create_app
        from lcc.auth.repository import UserRepository
        from lcc.auth.core import UserRole

        with tempfile.TemporaryDirectory() as tmp_dir:
            os.environ["LCC_DB_PATH"] = f"{tmp_dir}/test.db"
            os.environ["LCC_POLICY_DIR"] = f"{tmp_dir}/policies"
            os.environ["LCC_CACHE_DIR"] = f"{tmp_dir}/cache"

            app = create_app()
            client = TestClient(app)

            user_repo = UserRepository(Path(tmp_dir) / "test.db")
            user_repo.create_user(
                username="throughput_test",
                password="password123",
                role=UserRole.ADMIN
            )

            response = client.post(
                "/auth/login",
                data={"username": "throughput_test", "password": "password123"}
            )
            token = response.json()["access_token"]
            client.headers = {"Authorization": f"Bearer {token}"}

            yield client

            for key in ["LCC_DB_PATH", "LCC_POLICY_DIR", "LCC_CACHE_DIR"]:
                os.environ.pop(key, None)

    @pytest.mark.slow
    def test_sustained_load_performance(
        self,
        test_client: TestClient,
        performance_benchmark,
        save_performance_results
    ):
        """Test API performance under sustained load."""
        import time

        duration_seconds = 10
        request_count = 0
        errors = 0
        start_time = time.perf_counter()

        while time.perf_counter() - start_time < duration_seconds:
            try:
                response = test_client.get("/health")
                if response.status_code == 200:
                    request_count += 1
                else:
                    errors += 1
            except Exception:
                errors += 1

        end_time = time.perf_counter()
        actual_duration = end_time - start_time
        throughput = request_count / actual_duration

        print(f"\nSustained Load Test ({duration_seconds}s):")
        print(f"  Requests: {request_count}")
        print(f"  Errors: {errors}")
        print(f"  Throughput: {throughput:.2f} req/s")
        print(f"  Error Rate: {errors / (request_count + errors) * 100:.2f}%")

        # Assert sustained performance
        assert throughput > 50, f"Sustained throughput too low: {throughput:.2f} req/s"
        assert errors / (request_count + errors) < 0.01, "Too many errors"
