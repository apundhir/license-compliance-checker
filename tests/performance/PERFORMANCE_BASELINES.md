# Performance Baselines

This document defines expected performance baselines for the License Compliance Checker.

## Test Environment

Baselines are measured on:
- **Hardware**: Developer machine (varies)
- **Python**: 3.11+
- **Database**: SQLite (in-memory or file-based)
- **Cache**: Redis or in-memory

## Scanner Performance

### Small Project (5 files, ~10 dependencies)
- **Mean Time**: < 2.0 seconds
- **95th Percentile**: < 3.0 seconds
- **Operations/sec**: > 0.5

### Medium Project (50+ files, ~100 dependencies)
- **Mean Time**: < 10.0 seconds
- **95th Percentile**: < 15.0 seconds
- **Operations/sec**: > 0.1

### Detector Initialization
- **Mean Time**: < 0.1 seconds
- **95th Percentile**: < 0.15 seconds
- **Operations/sec**: > 10

### Cached Scans
- **Mean Time**: < 1.5 seconds (50% faster than uncached)
- **Cache Hit Improvement**: 2x faster minimum

### Multi-Ecosystem Projects
- **Mean Time**: < 3.0 seconds
- **Ecosystems Supported**: Python, Node.js, Rust, Go, Ruby, .NET

## Resolver Performance

### Registry-Based Resolution
- **Mean Time per Package**: < 1.0 second
- **Batch (4 packages)**: < 5.0 seconds
- **Cache Hit Rate**: > 80% expected

### Cached Resolution
- **Mean Time**: < 0.1 seconds
- **95th Percentile**: < 0.15 seconds
- **Speedup vs Cold**: 10x faster minimum

### Bulk Resolution (50 packages)
- **Mean Time**: < 30.0 seconds
- **Operations/sec**: > 1.5 packages/second

## API Performance

### Health Endpoint
- **Mean Time**: < 0.01 seconds (10ms)
- **95th Percentile**: < 0.02 seconds
- **Operations/sec**: > 100 requests/second

### List Policies
- **Mean Time**: < 0.1 seconds
- **95th Percentile**: < 0.2 seconds
- **Operations/sec**: > 10

### Create Policy
- **Mean Time**: < 0.2 seconds
- **95th Percentile**: < 0.3 seconds

### Dashboard Endpoint
- **Mean Time**: < 0.5 seconds
- **95th Percentile**: < 0.8 seconds
- **With 1000+ scans**: < 1.0 seconds

### Concurrent Requests
- **5 concurrent**: Success rate 100%, throughput > 10 req/s
- **10 concurrent**: Success rate 100%, throughput > 20 req/s
- **50 concurrent**: Success rate > 95%, throughput > 30 req/s

### Sustained Load
- **Duration**: 10 seconds minimum
- **Throughput**: > 50 requests/second
- **Error Rate**: < 1%

## Database Performance

### User Operations
- **Create**: < 0.05 seconds
- **Lookup**: < 0.01 seconds (with index)
- **Update**: < 0.05 seconds

### Scan Operations
- **Create**: < 0.05 seconds
- **Retrieve**: < 0.01 seconds (with index)
- **List All (500 records)**: < 0.5 seconds
- **Update Status**: < 0.05 seconds

### Bulk Operations
- **100 Inserts**: < 5.0 seconds
- **Operations/sec**: > 20 inserts/second

### Scalability
- **Query Time vs Table Size**: O(log n) or O(1) with proper indexing
- **1000x data increase**: < 2x query time increase

### Concurrent Access
- **5 concurrent writes**: > 5 operations/second throughput
- **Success Rate**: 100%

## Scalability Goals

### Scanner Scalability
- **Time Complexity**: O(n) where n = number of files
- **10x file increase**: < 15x time increase
- **Memory**: < 500MB for 1000 files

### Resolver Scalability
- **Time Complexity**: O(n) where n = number of packages
- **Package resolution**: Linear with count
- **Network impact**: Minimal with caching

### API Scalability
- **Concurrent Users**: Support 50+ simultaneous users
- **Request Queue**: Handle 1000+ requests/minute
- **Response Time Degradation**: < 50% at max load

### Database Scalability
- **Table Size**: Support 10,000+ records efficiently
- **Query Time**: Remain constant with proper indexing
- **Write Throughput**: > 100 writes/second

## Performance Testing

### Running Performance Tests

```bash
# Run all performance tests
pytest tests/performance/ -v -m performance

# Run specific test category
pytest tests/performance/test_scanner_performance.py -v

# Run with benchmark markers only
pytest tests/performance/ -v -m benchmark

# Skip slow tests
pytest tests/performance/ -v -m "performance and not slow"
```

### Generating Performance Reports

Performance results are automatically saved to `tests/performance/results/` as JSON files.

Each result includes:
- Test name
- Iterations
- Mean, median, min, max times
- Standard deviation
- 95th and 99th percentiles
- Operations per second
- Metadata (test configuration)

### Analyzing Results

```python
import json
from pathlib import Path

results_file = Path("tests/performance/results/scan_small_project.json")
with open(results_file) as f:
    results = json.load(f)

# Compare latest vs baseline
latest = results[-1]
baseline = results[0]

improvement = (baseline["mean_time_seconds"] - latest["mean_time_seconds"]) / baseline["mean_time_seconds"]
print(f"Performance improvement: {improvement * 100:.1f}%")
```

## Performance Regression Detection

Performance tests should fail if:
1. Mean time exceeds baseline by > 50%
2. 95th percentile exceeds baseline by > 100%
3. Operations/sec drops below baseline by > 50%
4. Error rate exceeds 1%
5. Scalability degrades (non-linear growth)

## Optimization Priorities

### High Priority
1. Scanner caching effectiveness
2. Database query optimization
3. API response times for common operations
4. Concurrent request handling

### Medium Priority
1. Resolver retry logic and timeouts
2. Large project scanning (1000+ files)
3. Dashboard data aggregation
4. Background task performance

### Low Priority
1. Rare edge cases
2. Administrative operations
3. One-time initialization tasks

## Continuous Monitoring

Performance benchmarks should be run:
- **Before major releases**: Full suite
- **After significant changes**: Affected components
- **Weekly**: Core operations (scanner, API)
- **On CI/CD**: Critical path tests only (fast subset)

## Notes

- Baselines may vary based on hardware, network conditions, and system load
- Results are statistical averages over multiple iterations
- Warmup iterations are excluded from measurements
- All times are wall-clock time, not CPU time
- Network-dependent operations (resolvers) may have higher variance
- Database performance depends on disk I/O and caching

## Version History

- **v1.0** (2024-10-31): Initial performance baselines established
  - Scanner: Small project < 2s, Medium < 10s
  - API: Health check < 10ms, List policies < 100ms
  - Database: CRUD operations < 50ms
  - Concurrent API: 100 req/s sustained load
