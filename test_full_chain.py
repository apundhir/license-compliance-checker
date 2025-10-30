"""Test the full resolution chain"""
import sys
sys.path.insert(0, 'src')

from lcc.cache import Cache
from lcc.config import load_config
from lcc.models import Component, ComponentType, ComponentFinding
from lcc.resolution.fallback import FallbackResolver
from lcc.factory import build_resolvers

# Create test component
component = Component(
    name="fastapi",
    type=ComponentType.PYTHON,
    version="*",
    namespace=None,
    path=None,
    metadata={}
)

finding = ComponentFinding(component=component)

config = load_config()
cache = Cache(config)
resolvers = build_resolvers(config, cache)

print("Testing full resolution chain for fastapi")
print("=" * 80)
print(f"Resolvers: {[r.name for r in resolvers]}")
print(f"Offline mode: {getattr(config, 'offline', False)}")
print()

# Manually test each resolver
for resolver in resolvers:
    print(f"\nTesting {resolver.name}:")
    try:
        evidences = list(resolver.resolve(component))
        print(f"  Returned {len(evidences)} evidences")
        for ev in evidences:
            print(f"    - {ev.source}: {ev.license_expression[:60]} (conf={ev.confidence})")
            if 'assumed_version' in ev.raw_data:
                print(f"      * assumed_version: {ev.raw_data['assumed_version']}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("Now testing with FallbackResolver:")
fallback = FallbackResolver(resolvers)
fallback.resolve(finding)

print(f"\nFinding after resolution:")
print(f"  Resolution path: {finding.component.metadata.get('resolution_path', [])}")
print(f"  Version: {finding.component.version}")
print(f"  Assumed version: {finding.component.metadata.get('assumed_version')}")
print(f"  Total evidences: {len(finding.evidences)}")
for ev in finding.evidences:
    print(f"    - {ev.source}: {ev.license_expression[:60]}")
