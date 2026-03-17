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
Rust ecosystem detector implementation.
"""

from __future__ import annotations

from collections.abc import Iterable, MutableMapping, Sequence
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from lcc.detection.base import Detector
from lcc.models import Component, ComponentType

DependencySpec = tuple[str, str | None, dict[str, object]]


class CargoDetector(Detector):
    """
    Detects Cargo crates from Cargo.toml and Cargo.lock files.
    """

    def __init__(self) -> None:
        super().__init__(name="cargo")

    def supports(self, project_root: Path) -> bool:  # pragma: no cover - simple predicate
        return (project_root / "Cargo.toml").exists() or any(project_root.glob("**/Cargo.toml"))

    def discover(self, project_root: Path) -> Sequence[Component]:
        components: dict[tuple[str, str], Component] = {}
        # Track names declared in Cargo.toml [dependencies] sections (direct deps)
        manifest_direct_names: set[str] = set()

        for manifest in self._collect_manifests(project_root):
            for name, version, metadata in self._parse_manifest(manifest):
                key = (name, version or "*")
                if key not in components:
                    components[key] = Component(
                        type=ComponentType.RUST,
                        name=name,
                        version=version or "*",
                        metadata={"sources": []},
                        path=manifest,
                    )
                    components[key].metadata["project_root"] = str(project_root)
                source_entry = {"source": str(manifest.relative_to(project_root)), **metadata}
                source_entry["project_root"] = str(project_root)
                components[key].metadata.setdefault("sources", []).append(source_entry)
                # Track direct dep names from dependency sections (not package declarations)
                section = metadata.get("section", "")
                if section in ("dependencies", "dev-dependencies", "build-dependencies") or str(section).startswith("target"):
                    manifest_direct_names.add(name)

        # Build Cargo.lock dependency graph for depth calculation
        cargo_dep_graph: dict[str, list[str]] = {}
        lock_file = project_root / "Cargo.lock"
        if lock_file.exists():
            for name, version, metadata in self._parse_lock(lock_file):
                key = (name, version or "*")
                if key not in components:
                    components[key] = Component(
                        type=ComponentType.RUST,
                        name=name,
                        version=version or "*",
                        metadata={"sources": []},
                        path=lock_file,
                    )
                    components[key].metadata["project_root"] = str(project_root)
                source_entry = {"source": str(lock_file.relative_to(project_root)), **metadata}
                source_entry["project_root"] = str(project_root)
                components[key].metadata.setdefault("sources", []).append(source_entry)
            # Build dependency graph from lock file
            cargo_dep_graph = self._build_cargo_dependency_graph(lock_file)

        # Compute depths from the dependency graph
        depth_map: dict[str, int] = {}
        parent_map: dict[str, list[str]] = {}
        if cargo_dep_graph:
            depth_map, parent_map = self._compute_cargo_dependency_depths(
                manifest_direct_names, cargo_dep_graph,
            )

        # Assign dependency depth metadata
        for component in components.values():
            comp_name = component.name
            is_direct = comp_name in manifest_direct_names
            # Determine source type
            source_files = [s.get("source", "") for s in component.metadata.get("sources", [])]
            has_manifest = any(
                "Cargo.toml" in str(s)
                for s in source_files
            )
            has_lockfile = any(
                "Cargo.lock" in str(s)
                for s in source_files
            )
            if has_manifest and has_lockfile:
                dep_source = "both"
            elif has_lockfile:
                dep_source = "lockfile"
            else:
                dep_source = "manifest"

            component.metadata["is_direct"] = is_direct
            component.metadata["dependency_depth"] = depth_map.get(comp_name, 0 if is_direct else 1)
            component.metadata["parent_packages"] = parent_map.get(comp_name, [])
            component.metadata["dependency_source"] = dep_source

        return list(components.values())

    # -------------------------
    # Dependency depth helpers
    # -------------------------

    def _build_cargo_dependency_graph(self, lock_path: Path) -> dict[str, list[str]]:
        """Build a dependency graph from Cargo.lock [[package]] entries.

        Returns a mapping of package name -> list of dependency names.
        """
        graph: dict[str, list[str]] = {}
        try:
            content = tomllib.loads(lock_path.read_text(encoding="utf-8"))
        except Exception:
            return graph
        package_list = content.get("package")
        if not isinstance(package_list, list):
            return graph
        for package in package_list:
            if not isinstance(package, dict):
                continue
            name = package.get("name")
            if not isinstance(name, str):
                continue
            deps: list[str] = []
            dep_list = package.get("dependencies", [])
            if isinstance(dep_list, list):
                for dep_entry in dep_list:
                    if isinstance(dep_entry, str):
                        # Format: "name version" or "name version source"
                        dep_name = dep_entry.split()[0]
                        deps.append(dep_name)
            graph[name] = deps
        return graph

    def _compute_cargo_dependency_depths(
        self,
        direct_names: set[str],
        dep_graph: dict[str, list[str]],
    ) -> tuple[dict[str, int], dict[str, list[str]]]:
        """BFS from direct dependencies to compute depth and parent_packages."""
        from collections import deque

        depth_map: dict[str, int] = {}
        parent_map: dict[str, list[str]] = {}

        queue: deque[str] = deque()
        for name in direct_names:
            depth_map[name] = 0
            parent_map[name] = []
            queue.append(name)

        while queue:
            current = queue.popleft()
            current_depth = depth_map[current]
            for child in dep_graph.get(current, []):
                if child not in depth_map:
                    depth_map[child] = current_depth + 1
                    parent_map[child] = [current]
                    queue.append(child)
                else:
                    if current not in parent_map.get(child, []):
                        parent_map.setdefault(child, []).append(current)

        return depth_map, parent_map

    def _collect_manifests(self, project_root: Path) -> Iterable[Path]:
        manifest = project_root / "Cargo.toml"
        if manifest.exists():
            yield manifest
        yield from project_root.glob("**/Cargo.toml")

    def _parse_manifest(self, path: Path) -> Iterable[DependencySpec]:
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, FileNotFoundError):
            return []
        results: list[DependencySpec] = []

        package = data.get("package", {})
        if isinstance(package, dict):
            name = package.get("name")
            version = package.get("version")
            if isinstance(name, str):
                metadata = {"type": "package"}
                if isinstance(package.get("edition"), str):
                    metadata["edition"] = package["edition"]
                if isinstance(package.get("license"), str):
                    metadata["license"] = package["license"]
                results.append((name, version if isinstance(version, str) else None, metadata))

        for section_name in ("dependencies", "dev-dependencies", "build-dependencies", "target"):
            section = data.get(section_name)
            if isinstance(section, dict):
                results.extend(self._parse_dependencies(section, section_name))

        workspace = data.get("workspace", {})
        if isinstance(workspace, dict):
            members = workspace.get("members")
            if isinstance(members, list):
                for member in members:
                    if isinstance(member, str):
                        metadata = {"workspace_member": member}
                        results.append((member, None, metadata))

        return results

    def _parse_dependencies(self, section: MutableMapping[str, object], label: str) -> Iterable[DependencySpec]:
        results: list[DependencySpec] = []
        for name, value in section.items():
            metadata: dict[str, object] = {"section": label}
            version: str | None = None
            if isinstance(value, str):
                version = value
            elif isinstance(value, dict):
                version_value = value.get("version")
                if isinstance(version_value, str):
                    version = version_value
                if value.get("git"):
                    metadata["git"] = value["git"]
                if value.get("path"):
                    metadata["path"] = value["path"]
                if value.get("features"):
                    metadata["features"] = value["features"]
                if value.get("optional"):
                    metadata["optional"] = value["optional"]
                if value.get("default-features") is not None:
                    metadata["default_features"] = value["default-features"]
                if value.get("registry"):
                    metadata["registry"] = value["registry"]
            results.append((name, version, metadata))
        return results

    def _parse_lock(self, path: Path) -> Iterable[DependencySpec]:
        try:
            content = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, FileNotFoundError):
            return []
        package_list = content.get("package")
        results: list[DependencySpec] = []
        if isinstance(package_list, list):
            for package in package_list:
                if not isinstance(package, dict):
                    continue
                name = package.get("name")
                version = package.get("version")
                if isinstance(name, str) and isinstance(version, str):
                    metadata: dict[str, object] = {"source": "Cargo.lock"}
                    if isinstance(package.get("source"), str):
                        metadata["source_url"] = package["source"]
                    if isinstance(package.get("checksum"), str):
                        metadata["checksum"] = package["checksum"]
                    results.append((name, version, metadata))
        return results
