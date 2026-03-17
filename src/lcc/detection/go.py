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

"""
Go ecosystem detector implementation.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from lcc.detection.base import Detector
from lcc.models import Component, ComponentType

ModuleSpec = tuple[str, str | None, dict[str, object]]


class GoDetector(Detector):
    """
    Detects Go modules by inspecting go.mod and go.sum files.
    """

    def __init__(self) -> None:
        super().__init__(name="go")

    def supports(self, project_root: Path) -> bool:  # pragma: no cover - simple predicate
        return (project_root / "go.mod").exists()

    def discover(self, project_root: Path) -> Sequence[Component]:
        registry: dict[tuple[str, str], Component] = {}

        def register(name: str, version: str | None, metadata: dict[str, object]) -> None:
            normalized_version = version or "*"
            key = (name, normalized_version)
            if key not in registry:
                registry[key] = Component(
                    type=ComponentType.GO,
                    name=name,
                    version=normalized_version,
                    metadata={"sources": []},
                )
                registry[key].metadata["project_root"] = str(project_root)
            metadata_copy = dict(metadata)
            source = metadata_copy.pop("source", "go.mod")
            entry = {"source": source}
            entry.update(metadata_copy)
            entry["project_root"] = str(project_root)
            registry[key].metadata["sources"].append(entry)

        go_mod_path = project_root / "go.mod"
        if go_mod_path.exists():
            for name, version, metadata in self._parse_go_mod(go_mod_path):
                register(name, version, metadata)

        go_sum_path = project_root / "go.sum"
        if go_sum_path.exists():
            for name, version, metadata in self._parse_go_sum(go_sum_path):
                register(name, version, metadata)

        vendor_modules = project_root / "vendor" / "modules.txt"
        if vendor_modules.exists():
            for name, version, metadata in self._parse_vendor_modules(vendor_modules):
                register(name, version, metadata)

        go_work_path = project_root / "go.work"
        if go_work_path.exists():
            for module_dir in self._parse_go_work(go_work_path):
                nested_mod = project_root / module_dir / "go.mod"
                if nested_mod.exists():
                    for name, version, metadata in self._parse_go_mod(nested_mod, module_dir):
                        register(name, version, metadata)

        # Assign dependency depth metadata to all components
        for component in registry.values():
            # Go already tracks indirect via metadata["indirect"]
            # Check if any source entry has indirect=True
            is_indirect = False
            for source_entry in component.metadata.get("sources", []):
                if source_entry.get("indirect"):
                    is_indirect = True
                    break
            is_direct = not is_indirect
            component.metadata["is_direct"] = is_direct
            component.metadata["dependency_depth"] = 0 if is_direct else 1
            component.metadata["parent_packages"] = []
            component.metadata["dependency_source"] = "manifest"  # go.mod is both manifest and lock

        return list(registry.values())

    # -------------------------
    # Parsers
    # -------------------------

    def _parse_go_mod(self, path: Path, module_prefix: str | None = None) -> Iterable[ModuleSpec]:
        lines = path.read_text(encoding="utf-8").splitlines()
        results: list[ModuleSpec] = []
        replace_map: dict[str, tuple[str, str | None]] = {}
        current_block: str | None = None
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("//"):
                continue
            if line.startswith("require ("):
                current_block = "require"
                continue
            if line.startswith("replace ("):
                current_block = "replace"
                continue
            if line == ")":
                current_block = None
                continue
            if line.startswith("require "):
                results.extend(self._parse_require_clause(line[len("require ") :], replace_map, module_prefix, path))
            elif line.startswith("replace "):
                from_module, _, rest = line[len("replace ") :].partition("=>")
                from_module = from_module.strip()
                target_parts = rest.strip().split()
                if len(target_parts) == 1:
                    replace_map[from_module] = (target_parts[0], None)
                elif len(target_parts) >= 2:
                    replace_map[from_module] = (target_parts[0], target_parts[1])
            elif current_block == "require":
                results.extend(self._parse_require_clause(line, replace_map, module_prefix, path))
            elif current_block == "replace":
                from_module, _, rest = line.partition("=>")
                from_module = from_module.strip()
                target_parts = rest.strip().split()
                if len(target_parts) == 1:
                    replace_map[from_module] = (target_parts[0], None)
                elif len(target_parts) >= 2:
                    replace_map[from_module] = (target_parts[0], target_parts[1])

        # Apply replace map metadata
        adjusted_results: list[ModuleSpec] = []
        for name, version, meta in results:
            key = name if not module_prefix else f"{module_prefix}/{name}"
            replacement = replace_map.get(name) or replace_map.get(key)
            if replacement:
                target, target_version = replacement
                meta = dict(meta)
                meta["replace"] = {"module": target, "version": target_version}
                if target_version:
                    adjusted_results.append((target, target_version, meta))
                    continue
            adjusted_results.append((name, version, meta))
        return adjusted_results

    def _parse_require_clause(
        self,
        clause: str,
        replace_map: dict[str, tuple[str, str | None]],
        module_prefix: str | None,
        path: Path,
    ) -> Iterable[ModuleSpec]:
        parts = clause.split()
        if not parts:
            return []
        name = parts[0]
        version = parts[1] if len(parts) >= 2 else None
        metadata: dict[str, object] = {"source": str(path.name)}
        if len(parts) > 2 and parts[2] == "//" and "indirect" in parts[3:]:
            metadata["indirect"] = True
        if module_prefix:
            metadata["module_prefix"] = module_prefix
        return [(name, version, metadata)]

    def _parse_go_sum(self, path: Path) -> Iterable[ModuleSpec]:
        results: dict[tuple[str, str], dict[str, object]] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            module, version = parts[0], parts[1]
            if version.endswith("/go.mod"):
                version = version.replace("/go.mod", "")
            metadata = results.setdefault((module, version), {"source": "go.sum"})
            metadata["checksum"] = parts[2] if len(parts) > 2 else None
        return [(name, version, meta) for (name, version), meta in results.items()]

    def _parse_vendor_modules(self, path: Path) -> Iterable[ModuleSpec]:
        results: list[ModuleSpec] = []
        current_index: int | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                parts = line[2:].split()
                if len(parts) >= 2:
                    module = parts[0]
                    version = parts[1]
                    metadata: dict[str, object] = {"source": "vendor/modules.txt", "vendor": True}
                    results.append((module, version, metadata))
                    current_index = len(results) - 1
            elif current_index is not None and line.strip().startswith("## explicit"):
                module, version, metadata = results[current_index]
                metadata = dict(metadata)
                metadata["explicit"] = True
                results[current_index] = (module, version, metadata)
        return results

    def _parse_go_work(self, path: Path) -> Iterable[Path]:
        results: list[Path] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("use "):
                _, _, target = line.partition("use ")
                results.append(Path(target.strip().strip('"')))
        return results
