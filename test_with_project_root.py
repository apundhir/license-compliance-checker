"""Test with project_root metadata like in real scan"""
import sys
sys.path.insert(0, 'src')

from lcc.cache import Cache
from lcc.config import load_config
from lcc.models import Component, ComponentType, ComponentFinding
from lcc.resolution.fallback import FallbackResolver
from lcc.factory import build_resolvers

# Create test component WITH project_root metadata
component = Component(
    name="fastapi",
    type=ComponentType.PYTHON,
    version="*",
    namespace=None,
    path=None,
    metadata={"project_root": "/tmp/test-project"}
)

finding = ComponentFinding(component=component)

config = load_config()
cache = Cache(config)
resolvers = build_resolvers(config, cache)

print("Testing with project_root metadata")
print("=" * 80)

# Test each resolver
for resolver in resolvers:
    print(f"\n{resolver.name}:")
    try:
        evidences = list(resolver.resolve(component))
        print(f"  Evidences: {len(evidences)}")
        for ev in evidences[:2]:  # Show first 2
            print(f"    - {ev.source}: {ev.license_expression[:40]}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "=" * 80)
print("With FallbackResolver:")
fallback = FallbackResolver(resolvers)
fallback.resolve(finding)

print(f"  Resolution path: {finding.component.metadata.get('resolution_path', [])}")
print(f"  Version: {finding.component.version}")
print(f"  Evidences: {len(finding.evidences)}")
