"""Factory helpers for detectors and resolvers."""

from __future__ import annotations

from typing import List

from lcc.cache import Cache
from lcc.config import LCCConfig
from lcc.detection.go import GoDetector
from lcc.detection.javascript import JavaScriptDetector
from lcc.detection.python import PythonDetector
from lcc.detection.java import MavenDetector
from lcc.detection.gradle import GradleDetector
from lcc.detection.rust import CargoDetector
from lcc.detection.ruby import RubyDetector
from lcc.detection.dotnet import DotNetDetector
from lcc.detection.huggingface import HuggingFaceDetector
from lcc.detection.hf_datasets import HuggingFaceDatasetDetector
from lcc.detection.base import Detector
from lcc.resolution.base import Resolver
from lcc.resolution.clearlydefined import ClearlyDefinedResolver
from lcc.resolution.github import GitHubResolver
from lcc.resolution.filesystem import FileSystemResolver
from lcc.resolution.registries import RegistryResolver
from lcc.resolution.scancode import ScanCodeResolver


def build_detectors() -> List[Detector]:
    """Return the detector set (Phase 1-3)."""

    return [
        # Traditional package detectors (Phase 1-2)
        PythonDetector(),
        JavaScriptDetector(),
        GoDetector(),
        MavenDetector(),
        GradleDetector(),
        CargoDetector(),
        RubyDetector(),
        DotNetDetector(),
        # AI/ML detectors (Phase 3)
        HuggingFaceDetector(),
        HuggingFaceDatasetDetector(),
    ]


def build_resolvers(config: LCCConfig, cache: Cache) -> List[Resolver]:
    """Return the Phase 1 resolver chain."""

    if getattr(config, "offline", False):
        # In offline mode we only include resolvers that do not require network access.
        return [FileSystemResolver(config), ScanCodeResolver(cache, config)]

    return [
        ClearlyDefinedResolver(cache, config),
        RegistryResolver(cache, config),
        GitHubResolver(cache, config),
        FileSystemResolver(config),
        ScanCodeResolver(cache, config),
    ]
