"""Performance tests for database operations."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lcc.api.repository import ScanRepository
from lcc.auth.core import UserRole
from lcc.auth.repository import UserRepository


@pytest.mark.performance
@pytest.mark.benchmark
class TestDatabaseWritePerformance:
    """Test database write performance."""

    def test_user_creation_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark user creation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "perf.db"
            repo = UserRepository(db_path)

            benchmark = performance_benchmark("Create User", iterations=100, warmup=10)

            counter = [0]

            def create_user():
                repo.create_user(
                    username=f"user_{counter[0]}",
                    password="password123",
                    email=f"user{counter[0]}@example.com"
                )
                counter[0] += 1

            result = benchmark.run(create_user)
            result.metadata = {"operation": "create", "entity": "user"}

            print(result)
            save_performance_results(result)

            assert result.mean_time < 0.05, f"User creation too slow: {result.mean_time:.4f}s"

    def test_scan_creation_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark scan record creation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "perf.db"
            repo = ScanRepository(db_path)

            benchmark = performance_benchmark("Create Scan", iterations=100, warmup=10)

            counter = [0]

            def create_scan():
                scan_data = {
                    "project": f"project-{counter[0]}",
                    "status": "completed",
                    "generated_at": datetime.now(timezone.utc),
                    "duration_seconds": 1.5,
                    "violations": 2,
                    "warnings": 3
                }
                repo.create_scan(scan_data)
                counter[0] += 1

            result = benchmark.run(create_scan)
            result.metadata = {"operation": "create", "entity": "scan"}

            print(result)
            save_performance_results(result)

            assert result.mean_time < 0.05, f"Scan creation too slow: {result.mean_time:.4f}s"

    def test_bulk_insert_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark bulk insert operations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "perf.db"
            repo = ScanRepository(db_path)

            benchmark = performance_benchmark("Bulk Insert (100 scans)", iterations=10, warmup=2)

            def bulk_insert():
                for i in range(100):
                    scan_data = {
                        "project": f"bulk-project-{i}",
                        "status": "completed",
                        "generated_at": datetime.now(timezone.utc),
                        "duration_seconds": 1.0,
                        "violations": i % 5,
                        "warnings": i % 3
                    }
                    repo.create_scan(scan_data)

            result = benchmark.run(bulk_insert)
            result.metadata = {
                "operation": "bulk_insert",
                "count": 100,
                "entity": "scan"
            }

            print(result)
            save_performance_results(result)

            assert result.mean_time < 5.0, f"Bulk insert too slow: {result.mean_time:.2f}s"


@pytest.mark.performance
@pytest.mark.benchmark
class TestDatabaseReadPerformance:
    """Test database read performance."""

    def test_user_lookup_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark user lookup by username."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "perf.db"
            repo = UserRepository(db_path)

            # Create test users
            for i in range(100):
                repo.create_user(
                    username=f"lookup_user_{i}",
                    password="password123",
                    email=f"user{i}@example.com"
                )

            benchmark = performance_benchmark("User Lookup", iterations=500, warmup=50)

            def lookup_user():
                user = repo.get_user_by_username("lookup_user_50")
                assert user is not None

            result = benchmark.run(lookup_user)
            result.metadata = {
                "operation": "lookup",
                "entity": "user",
                "table_size": 100
            }

            print(result)
            save_performance_results(result)

            assert result.mean_time < 0.01, f"User lookup too slow: {result.mean_time:.4f}s"

    def test_scan_retrieval_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark scan retrieval."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "perf.db"
            repo = ScanRepository(db_path)

            # Create test scans
            scan_ids = []
            for i in range(100):
                scan_data = {
                    "project": f"retrieve-project-{i}",
                    "status": "completed",
                    "generated_at": datetime.now(timezone.utc),
                    "duration_seconds": 1.0,
                    "violations": i % 5,
                    "warnings": i % 3
                }
                scan_id = repo.create_scan(scan_data)
                scan_ids.append(scan_id)

            benchmark = performance_benchmark("Scan Retrieval", iterations=500, warmup=50)

            def retrieve_scan():
                scan = repo.get_scan(scan_ids[50])
                assert scan is not None

            result = benchmark.run(retrieve_scan)
            result.metadata = {
                "operation": "retrieve",
                "entity": "scan",
                "table_size": 100
            }

            print(result)
            save_performance_results(result)

            assert result.mean_time < 0.01, f"Scan retrieval too slow: {result.mean_time:.4f}s"

    def test_list_all_scans_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark listing all scans."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "perf.db"
            repo = ScanRepository(db_path)

            # Create many scans
            for i in range(500):
                scan_data = {
                    "project": f"list-project-{i % 50}",  # 50 unique projects
                    "status": "completed",
                    "generated_at": datetime.now(timezone.utc),
                    "duration_seconds": 1.0,
                    "violations": i % 10,
                    "warnings": i % 5
                }
                repo.create_scan(scan_data)

            benchmark = performance_benchmark("List All Scans (500 records)", iterations=50, warmup=5)

            def list_scans():
                scans = repo.list_scans()
                assert len(scans) == 500

            result = benchmark.run(list_scans)
            result.metadata = {
                "operation": "list_all",
                "entity": "scan",
                "table_size": 500
            }

            print(result)
            save_performance_results(result)

            assert result.mean_time < 0.5, f"List all scans too slow: {result.mean_time:.2f}s"


@pytest.mark.performance
@pytest.mark.benchmark
class TestDatabaseUpdatePerformance:
    """Test database update performance."""

    def test_user_update_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark user updates."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "perf.db"
            repo = UserRepository(db_path)

            # Create test user
            repo.create_user(
                username="update_test_user",
                password="password123",
                email="original@example.com"
            )

            benchmark = performance_benchmark("Update User", iterations=100, warmup=10)

            counter = [0]

            def update_user():
                repo.update_user(
                    username="update_test_user",
                    email=f"updated{counter[0]}@example.com"
                )
                counter[0] += 1

            result = benchmark.run(update_user)
            result.metadata = {"operation": "update", "entity": "user"}

            print(result)
            save_performance_results(result)

            assert result.mean_time < 0.05, f"User update too slow: {result.mean_time:.4f}s"

    def test_scan_status_update_performance(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Benchmark scan status updates."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "perf.db"
            repo = ScanRepository(db_path)

            # Create test scan
            scan_data = {
                "project": "status-test",
                "status": "pending",
                "generated_at": datetime.now(timezone.utc),
                "duration_seconds": 0.0,
                "violations": 0,
                "warnings": 0
            }
            scan_id = repo.create_scan(scan_data)

            benchmark = performance_benchmark("Update Scan Status", iterations=100, warmup=10)

            statuses = ["pending", "running", "completed"]
            counter = [0]

            def update_status():
                status = statuses[counter[0] % len(statuses)]
                repo.update_scan_status(scan_id, status)
                counter[0] += 1

            result = benchmark.run(update_status)
            result.metadata = {"operation": "update_status", "entity": "scan"}

            print(result)
            save_performance_results(result)

            assert result.mean_time < 0.05, f"Status update too slow: {result.mean_time:.4f}s"


@pytest.mark.performance
class TestDatabaseScalability:
    """Test database scalability with increasing data."""

    def test_query_performance_scaling(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Test how query performance scales with table size."""
        results = []

        for table_size in [100, 500, 1000]:
            with tempfile.TemporaryDirectory() as tmp_dir:
                db_path = Path(tmp_dir) / "perf.db"
                repo = ScanRepository(db_path)

                # Populate database
                scan_ids = []
                for i in range(table_size):
                    scan_data = {
                        "project": f"scale-project-{i % 20}",
                        "status": "completed",
                        "generated_at": datetime.now(timezone.utc),
                        "duration_seconds": 1.0,
                        "violations": i % 10,
                        "warnings": i % 5
                    }
                    scan_id = repo.create_scan(scan_data)
                    scan_ids.append(scan_id)

                benchmark = performance_benchmark(
                    f"Query with {table_size} records",
                    iterations=50,
                    warmup=5
                )

                def query_operation():
                    # Query middle record
                    scan = repo.get_scan(scan_ids[table_size // 2])
                    assert scan is not None

                result = benchmark.run(query_operation)
                result.metadata = {"table_size": table_size, "operation": "query"}
                results.append(result)

                print(result)

        # Save all results
        for result in results:
            save_performance_results(result, "database_scalability.json")

        # Check scalability
        # Query time should remain constant (O(1) with indexed lookups)
        if len(results) >= 2:
            time_increase = results[-1].mean_time / results[0].mean_time
            size_increase = results[-1].metadata["table_size"] / results[0].metadata["table_size"]

            print(f"\nScalability: {size_increase}x size -> {time_increase:.2f}x time")
            # With proper indexing, should be near constant time
            assert time_increase < 2.0, f"Poor scalability: {time_increase:.2f}x slowdown"


@pytest.mark.performance
@pytest.mark.slow
class TestDatabaseConcurrency:
    """Test database concurrent access performance."""

    def test_concurrent_writes(
        self,
        performance_benchmark,
        save_performance_results
    ):
        """Test concurrent write performance."""
        import concurrent.futures
        import time

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "perf.db"
            repo = ScanRepository(db_path)

            def write_operation(i: int):
                start = time.perf_counter()
                scan_data = {
                    "project": f"concurrent-{i}",
                    "status": "completed",
                    "generated_at": datetime.now(timezone.utc),
                    "duration_seconds": 1.0,
                    "violations": 0,
                    "warnings": 0
                }
                repo.create_scan(scan_data)
                end = time.perf_counter()
                return end - start

            # Test with concurrent writes
            start_time = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(write_operation, i) for i in range(50)]
                times = [f.result() for f in concurrent.futures.as_completed(futures)]

            end_time = time.perf_counter()

            total_time = end_time - start_time
            avg_time = sum(times) / len(times)
            throughput = len(times) / total_time

            print(f"\nConcurrent Writes (50 operations, 5 workers):")
            print(f"  Total Time: {total_time:.2f}s")
            print(f"  Avg Time: {avg_time:.4f}s")
            print(f"  Throughput: {throughput:.2f} ops/s")

            assert throughput > 5, f"Concurrent write throughput too low: {throughput:.2f} ops/s"
