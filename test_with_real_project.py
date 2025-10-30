"""Test with real project directory"""
import sys
sys.path.insert(0, 'src')

from lcc.cache import Cache
from lcc.config import load_config
from lcc.models import Component, ComponentType, ComponentFinding
from lcc.resolution.fallback import FallbackResolver
from lcc.factory import build_resolvers

# Create test component WITH real project_root
component = Component(
    name="fastapi",
    type=ComponentType.PYTHON,
    version="*",
    namespace=None,
    path=None,
    metadata={"project_root": "/tmp/test-rag-proj"}
)

finding = ComponentFinding(component=component)

config = load_config()
cache = Cache(config)
resolvers = build_resolvers(config, cache)

print("Testing with REAL project directory containing LICENSE")
print("=" * 80)

# Test each resolver
for resolver in resolvers:
    print(f"\n{resolver.name}:")
    try:
        evidences = list(resolver.resolve(component))
        print(f"  Evidences: {len(evidences)}")
        for ev in evidences:
            print(f"    - {ev.source}: {ev.license_expression} (conf={ev.confidence})")
            if 'assumed_version' in ev.raw_data:
                print(f"      * assumed_version: {ev.raw_data['assumed_version']}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "=" * 80)
print("With FallbackResolver:")
fallback = FallbackResolver(resolvers)
fallback.resolve(finding)

print(f"  Resolution path: {finding.component.metadata.get('resolution_path', [])}")
print(f"  Version: {finding.component.version}")
print(f"  Assumed version: {finding.component.metadata.get('assumed_version')}")
print(f"  Version source: {finding.component.metadata.get('version_source')}")
print(f"  Evidences: {len(finding.evidences)}")
for ev in finding.evidences:
    print(f"    - {ev.source}: {ev.license_expression}")
