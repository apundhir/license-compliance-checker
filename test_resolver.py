import asyncio
from pathlib import Path
from lcc.config import LCCConfig
from lcc.cache import Cache
from lcc.resolution.registry import RegistryResolver
from lcc.resolution.fallback import FallbackResolver
from lcc.models import Component, ComponentType, ComponentFinding
config = LCCConfig()
cache = Cache(config)
resolver = RegistryResolver(cache, config)
fallback = FallbackResolver([resolver])
comp = Component(type=ComponentType.PYTHON, name="requests", version="2.31.0", metadata={})
finding = ComponentFinding(comp)
fallback.resolve(finding)
print(f"Confidence: {finding.confidence}, License: {finding.resolved_license}")
