"""Direct test of RegistryResolver"""
import sys
sys.path.insert(0, 'src')

from lcc.cache import Cache
from lcc.config import load_config
from lcc.models import Component, ComponentType
from lcc.resolution.registries import RegistryResolver

# Create test component
component = Component(
    name="fastapi",
    type=ComponentType.PYTHON,
    version="*",
    namespace=None,
    path=None,
    metadata={}
)

config = load_config()
cache = Cache(config)
resolver = RegistryResolver(cache, config)

print("Testing RegistryResolver._resolve_pypi for fastapi")
print("=" * 80)

# Directly test _resolve_pypi
evidences = list(resolver._resolve_pypi(component))

print(f"\nReturned {len(evidences)} evidences:")
for i, ev in enumerate(evidences, 1):
    print(f"\nEvidence {i}:")
    print(f"  Source: {ev.source}")
    print(f"  License: {ev.license_expression}")
    print(f"  Confidence: {ev.confidence}")
    print(f"  Raw data: {ev.raw_data}")
    print(f"  URL: {ev.url}")
