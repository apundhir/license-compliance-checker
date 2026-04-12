# Copyright 2025 Ajay Pundhir
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Factory helpers for detectors and resolvers."""

from __future__ import annotations

from lcc.cache import Cache
from lcc.config import LCCConfig
from lcc.detection.base import Detector
from lcc.detection.dotnet import DotNetDetector
from lcc.detection.go import GoDetector
from lcc.detection.gradle import GradleDetector
from lcc.detection.hf_datasets import HuggingFaceDatasetDetector
from lcc.detection.huggingface import HuggingFaceDetector, HuggingFaceReferenceDetector
from lcc.detection.java import MavenDetector
from lcc.detection.javascript import JavaScriptDetector
from lcc.detection.license_file import LicenseFileDetector
from lcc.detection.python import PythonDetector
from lcc.detection.ruby import RubyDetector
from lcc.detection.rust import CargoDetector
from lcc.resolution.ai import AIResolver
from lcc.resolution.base import Resolver
from lcc.resolution.clearlydefined import ClearlyDefinedResolver
from lcc.resolution.filesystem import FileSystemResolver
from lcc.resolution.github import GitHubResolver
from lcc.resolution.registries import RegistryResolver
from lcc.resolution.scancode import ScanCodeResolver


def build_detectors(config: LCCConfig) -> list[Detector]:
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
        HuggingFaceReferenceDetector(),
        # Generic file detectors
        LicenseFileDetector(config),
    ]


def build_resolvers(config: LCCConfig, cache: Cache) -> list[Resolver]:
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
        AIResolver(config),
    ]
