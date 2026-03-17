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
JavaScript ecosystem detector implementation.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, MutableMapping, Sequence
from pathlib import Path

from lcc.detection.base import Detector
from lcc.models import Component, ComponentType

DependencySpec = tuple[str, str | None, dict[str, object]]


class JavaScriptDetector(Detector):
    """
    Detects npm, Yarn, and pnpm dependencies.
    """

    def __init__(self) -> None:
        super().__init__(name="javascript")

    def supports(self, project_root: Path) -> bool:  # pragma: no cover - simple predicate
        manifests = ["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"]
        if any((project_root / manifest).exists() for manifest in manifests):
            return True
        # Recursive check
        for manifest in manifests:
             try:
                 if next(project_root.rglob(f"**/{manifest}"), None):
                     return True
             except (OSError, PermissionError):
                 continue
        return False

    def discover(self, project_root: Path) -> Sequence[Component]:
        registry: dict[tuple[str, str], Component] = {}
        # Track direct dependency names from package.json manifests
        manifest_direct_names: set[str] = set()

        def register(name: str, version: str | None, metadata: MutableMapping[str, object]) -> None:
            source = metadata.pop("source", "unknown")
            normalized_version = version or "*"
            key = (name, normalized_version)
            if key not in registry:
                registry[key] = Component(
                    type=ComponentType.JAVASCRIPT,
                    name=name,
                    version=normalized_version,
                    metadata={"sources": []},
                )
                registry[key].metadata["project_root"] = str(project_root)
            component = registry[key]
            source_entry = {"source": source}
            if metadata:
                source_entry.update(metadata)
                licenses = component.metadata.setdefault("licenses", set())
                if isinstance(licenses, set):
                    license_value = metadata.get("license")
                    if isinstance(license_value, str):
                        licenses.add(license_value)
                    for extra in metadata.get("licenses", []) if isinstance(metadata.get("licenses"), list) else []:
                        if isinstance(extra, str):
                            licenses.add(extra)
            source_entry["project_root"] = str(project_root)
            component.metadata["sources"].append(source_entry)

        # Helper to find files recursively, excluding common ignored dirs
        skip_dirs = {".git", "node_modules", "dist", "build", "coverage"}
        def find_files(filename: str) -> Iterable[Path]:
            # Simple rglob includes ignored dirs, we should filter
            # But detectors usually do robust checking. For now rglob is fine, we filter in loop
            return project_root.rglob(filename)

        # package.json — collect direct dependency names
        for path in find_files("package.json"):
            if any(part in skip_dirs for part in path.parts):
                 continue
            if self._is_excluded(path, project_root):
                 continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            relative_source = str(path.relative_to(project_root))
            for spec in self._parse_package_json(data, relative_source):
                register(*spec)
            # Collect direct dep names from manifest sections
            for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
                deps = data.get(section, {})
                if isinstance(deps, dict):
                    manifest_direct_names.update(deps.keys())

        # package-lock.json — parse and build dep graph
        lock_dep_graph: dict[str, list[str]] = {}
        lock_root_deps: set[str] = set()
        for path in find_files("package-lock.json"):
            if any(part in skip_dirs for part in path.parts): continue
            if self._is_excluded(path, project_root): continue
            for spec in self._parse_package_lock_file(path, project_root):
                register(*spec)
            # Build dependency graph from lock file
            root_deps, dep_graph = self._build_npm_dependency_graph(path)
            lock_root_deps.update(root_deps)
            lock_dep_graph.update(dep_graph)

        for path in find_files("yarn.lock"):
            if any(part in skip_dirs for part in path.parts): continue
            if self._is_excluded(path, project_root): continue
            for spec in self._parse_yarn_lock_file(path, project_root):
                register(*spec)

        for path in find_files("pnpm-lock.yaml"):
            if any(part in skip_dirs for part in path.parts): continue
            if self._is_excluded(path, project_root): continue
            for spec in self._parse_pnpm_lock_file(path, project_root):
                 register(*spec)

        # Merge lock root deps into manifest direct names
        manifest_direct_names.update(lock_root_deps)

        # Compute depths from the npm dependency graph
        depth_map: dict[str, int] = {}
        parent_map: dict[str, list[str]] = {}
        if lock_dep_graph:
            depth_map, parent_map = self._compute_npm_dependency_depths(
                manifest_direct_names, lock_dep_graph,
            )

        # Assign dependency depth metadata to all components
        for (_name, _version), component in registry.items():
            name = _name
            is_direct = name in manifest_direct_names
            # Determine source type
            source_files = [s.get("source", "") for s in component.metadata.get("sources", [])]
            has_manifest = any(
                "package.json" in str(s) and "lock" not in str(s)
                for s in source_files
            )
            has_lockfile = any(
                "lock" in str(s).lower() or "yarn.lock" in str(s)
                for s in source_files
            )
            if has_manifest and has_lockfile:
                dep_source = "both"
            elif has_lockfile:
                dep_source = "lockfile"
            else:
                dep_source = "manifest"

            component.metadata["is_direct"] = is_direct
            component.metadata["dependency_depth"] = depth_map.get(name, 0 if is_direct else 1)
            component.metadata["parent_packages"] = parent_map.get(name, [])
            component.metadata["dependency_source"] = dep_source

        for component in registry.values():
            if isinstance(component.metadata.get("licenses"), set):
                component.metadata["licenses"] = sorted(component.metadata["licenses"])
        return list(registry.values())

    # -------------------------
    # Dependency depth helpers
    # -------------------------

    def _build_npm_dependency_graph(self, lock_path: Path) -> tuple[set[str], dict[str, list[str]]]:
        """Build a dependency graph from package-lock.json v3 (packages format).

        Returns (root_direct_deps, dependency_graph).
        """
        root_deps: set[str] = set()
        dep_graph: dict[str, list[str]] = {}
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return root_deps, dep_graph

        packages = data.get("packages")
        if not isinstance(packages, dict):
            return root_deps, dep_graph

        # The root entry "" lists its dependencies
        root_entry = packages.get("", {})
        if isinstance(root_entry, dict):
            for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
                deps = root_entry.get(section, {})
                if isinstance(deps, dict):
                    root_deps.update(deps.keys())

        # Build graph from each package entry
        for package_path, package_data in packages.items():
            if package_path in ("", ".") or not isinstance(package_data, dict):
                continue
            # Extract package name
            name = package_data.get("name")
            if not isinstance(name, str):
                parts = package_path.split("node_modules/")
                if len(parts) > 1:
                    name = parts[-1]
            if not isinstance(name, str):
                continue
            # Collect this package's dependencies
            children: list[str] = []
            for dep_section in ("dependencies", "optionalDependencies", "peerDependencies"):
                dep_data = package_data.get(dep_section, {})
                if isinstance(dep_data, dict):
                    children.extend(dep_data.keys())
            if children:
                dep_graph[name] = children

        return root_deps, dep_graph

    def _compute_npm_dependency_depths(
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

    # -------------------------
    # Manifest parsers
    # -------------------------

    def _parse_package_json(self, data: MutableMapping[str, object], source: str) -> Iterable[DependencySpec]:
        results: list[DependencySpec] = []
        for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
            deps = data.get(section, {})
            if isinstance(deps, dict):
                for name, spec in deps.items():
                    metadata: dict[str, object] = {"section": section, "source": source}
                    if isinstance(spec, str):
                        entry_metadata = dict(metadata)
                        entry_metadata["specifier"] = spec
                        results.append((name, spec if spec.startswith("file:") else None, entry_metadata))
                    elif isinstance(spec, dict):
                        version = spec.get("version")
                        entry_metadata = dict(metadata)
                        for key, value in spec.items():
                            if key != "version":
                                entry_metadata[key] = value
                        results.append((name, version if isinstance(version, str) else None, entry_metadata))

        base_name = data.get("name")
        base_version = data.get("version") if isinstance(data.get("version"), str) else None
        license_value = data.get("license")
        base_metadata: dict[str, object] = {"source": source}
        if isinstance(license_value, str):
            base_metadata["license"] = license_value
        elif isinstance(license_value, dict):
            license_type = license_value.get("type")
            if isinstance(license_type, str):
                base_metadata["license"] = license_type
        elif isinstance(license_value, list):
            license_entries = [entry.get("type") for entry in license_value if isinstance(entry, dict)]
            license_entries = [entry for entry in license_entries if isinstance(entry, str)]
            if license_entries:
                base_metadata["licenses"] = license_entries
        if isinstance(base_name, str):
            results.append((base_name, base_version, base_metadata))
        return results

    def _parse_package_lock_file(self, path: Path, project_root: Path) -> Iterable[DependencySpec]:
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        results: list[DependencySpec] = []
        packages = data.get("packages")
        if isinstance(packages, dict):
            for package_path, package_data in packages.items():
                if package_path in ("", ".") or not isinstance(package_data, dict):
                    continue
                name = package_data.get("name")
                version = package_data.get("version")
                if not isinstance(name, str):
                    # Some package-lock entries omit name but include key like node_modules/pkg
                    parts = package_path.split("node_modules/")
                    if len(parts) > 1:
                        name = parts[-1]
                if not isinstance(name, str) or not isinstance(version, str):
                    continue
                metadata: dict[str, object] = {"source": "package-lock.json", "path": package_path}
                if isinstance(package_data.get("license"), str):
                    metadata["license"] = package_data["license"]
                results.append((name, version, metadata))
        else:
            # Legacy package-lock structure
            deps = data.get("dependencies", {})
            results.extend(self._collect_lock_dependencies(deps, prefix="package-lock.json"))
        return results

    def _collect_lock_dependencies(self, deps: MutableMapping[str, object], prefix: str) -> Iterable[DependencySpec]:
        results: list[DependencySpec] = []
        for name, data in deps.items():
            if not isinstance(data, dict):
                continue
            version = data.get("version")
            metadata: dict[str, object] = {"source": prefix}
            if isinstance(data.get("resolved"), str):
                metadata["resolved"] = data["resolved"]
            if isinstance(data.get("integrity"), str):
                metadata["integrity"] = data["integrity"]
            if isinstance(data.get("license"), str):
                metadata["license"] = data["license"]
            results.append((name, version if isinstance(version, str) else None, metadata))
            if isinstance(data.get("dependencies"), dict):
                results.extend(self._collect_lock_dependencies(data["dependencies"], prefix))
        return results

    def _parse_yarn_lock_file(self, path: Path, project_root: Path) -> Iterable[DependencySpec]:
        if not path.exists():
            return []
        content = path.read_text(encoding="utf-8")
        if content.lstrip().startswith("__metadata:"):
            return self._parse_modern_yarn_lock(content)
        return self._parse_legacy_yarn_lock(content)

    def _parse_legacy_yarn_lock(self, content: str) -> Iterable[DependencySpec]:
        results: list[DependencySpec] = []
        current_names: list[str] = []
        metadata: dict[str, object] = {}
        version: str | None = None
        for line in content.splitlines():
            if not line.strip():
                if current_names:
                    for entry in current_names:
                        clean_name = entry.split("@", 1)[0].strip('"')
                        results.append((clean_name, version, metadata.copy()))
                current_names = []
                metadata = {}
                version = None
                continue
            if not line.startswith(" "):
                current_names = [name.strip() for name in line.rstrip(":").split(",")]
                metadata = {"source": "yarn.lock"}
            else:
                key, _, value = line.strip().partition(" ")
                value = value.strip('"')
                if key == "version":
                    version = value
                elif key == "resolved":
                    metadata["resolved"] = value
                elif key == "integrity":
                    metadata["integrity"] = value
        if current_names:
            for entry in current_names:
                clean_name = entry.split("@", 1)[0].strip('"')
                entry_metadata = dict(metadata)
                entry_metadata["source"] = "yarn.lock"
                results.append((clean_name, version, entry_metadata))
        return results

    def _parse_pnpm_lock_file(self, path: Path, project_root: Path) -> Iterable[DependencySpec]:
        if not path.exists():
            return []
        return self._parse_pnpm_lock_text(path.read_text(encoding="utf-8"))

    def _parse_node_modules(self, project_root: Path) -> Iterable[DependencySpec]:
        """
        Parse installed packages from node_modules directory.

        NOTE: This scans installed packages in node_modules/.
        For source code scans (GitHub repos), these are typically unwanted as they
        represent installed dependencies, not declarations.

        This method now skips node_modules scanning by default to avoid scanning
        installed libraries in source repos.
        """
        results: list[DependencySpec] = []

        # Skip scanning node_modules for source code scans
        # Uncomment the lines below if you need to scan installed packages
        # (e.g., for Docker images or deployed code)

        # node_modules = project_root / "node_modules"
        # if not node_modules.exists():
        #     return []
        # for package_json in node_modules.glob("**/package.json"):
        #     try:
        #         data = json.loads(package_json.read_text(encoding="utf-8"))
        #     except json.JSONDecodeError:
        #         continue
        #     name = data.get("name")
        #     version = data.get("version")
        #     if not isinstance(name, str) or not isinstance(version, str):
        #         continue
        #     metadata: Dict[str, object] = {"source": f"node_modules/{package_json.relative_to(node_modules)}"}
        #     if isinstance(data.get("license"), str):
        #         metadata["license"] = data["license"]
        #     if isinstance(data.get("licenses"), list):
        #         metadata["licenses"] = data["licenses"]
        #     if isinstance(data.get("bundledDependencies"), list):
        #         metadata["bundledDependencies"] = data["bundledDependencies"]
        #     results.append((name, version, metadata))

        return results

    # -------------------------
    # Helpers
    # -------------------------

    def _workspace_paths(self, project_root: Path, package_json: MutableMapping[str, object]) -> list[Path]:
        workspaces = package_json.get("workspaces")
        patterns: list[str] = []
        if isinstance(workspaces, list):
            patterns = [str(item) for item in workspaces if isinstance(item, str)]
        elif isinstance(workspaces, dict):
            packages = workspaces.get("packages")
            if isinstance(packages, list):
                patterns = [str(item) for item in packages if isinstance(item, str)]
        paths: list[Path] = []
        for pattern in patterns:
            paths.extend(project_root.glob(pattern))
        return [path for path in paths if path.is_dir()]

    def _parse_modern_yarn_lock(self, content: str) -> Iterable[DependencySpec]:
        results: list[DependencySpec] = []
        in_packages = False
        current_key: str | None = None
        current_meta: dict[str, object] = {}
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(stripped)
            if stripped == "packages:":
                in_packages = True
                if current_key and "version" in current_meta:
                    name = self._extract_name(current_key)
                    results.append((name, str(current_meta["version"]), current_meta))
                current_key = None
                current_meta = {}
                continue
            if not in_packages:
                continue
            if indent == 2 and stripped.endswith(":"):
                if current_key and "version" in current_meta:
                    name = self._extract_name(current_key)
                    results.append((name, str(current_meta["version"]), current_meta))
                current_key = stripped[:-1].strip().strip('"')
                current_meta = {"source": "yarn.lock", "specifier": current_key}
            elif current_key and indent >= 4 and ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"')
                if key == "version":
                    current_meta["version"] = value
                else:
                    current_meta[key] = value
        if current_key and "version" in current_meta:
            name = self._extract_name(current_key)
            results.append((name, str(current_meta["version"]), current_meta))
        return results

    def _parse_pnpm_lock_text(self, content: str) -> Iterable[DependencySpec]:
        results: list[DependencySpec] = []
        in_packages = False
        current_key: str | None = None
        current_meta: dict[str, object] = {}
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(stripped)
            if stripped == "packages:":
                in_packages = True
                current_key = None
                current_meta = {}
                continue
            if not in_packages:
                continue
            if indent == 2 and stripped.endswith(":"):
                if current_key and "version" in current_meta:
                    name, version = self._split_pnpm_key(current_key, current_meta.get("version"))
                    results.append((name, version, current_meta))
                current_key = stripped[:-1]
                current_meta = {"source": "pnpm-lock.yaml", "path": current_key}
            elif current_key and indent >= 4 and ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()
                if value.startswith("{") and value.endswith("}"):
                    current_meta[key] = self._parse_inline_mapping(value)
                else:
                    current_meta[key] = value.strip('"')
        if current_key and "version" in current_meta:
            name, version = self._split_pnpm_key(current_key, current_meta.get("version"))
            results.append((name, version, current_meta))
        else:
            # Some pnpm entries encode version in key without explicit field
            if current_key and "version" not in current_meta:
                name, version = self._split_pnpm_key(current_key, None)
                results.append((name, version, current_meta))
        return results

    def _extract_name(self, package_key: str) -> str:
        name, _, _ = package_key.rpartition("@")
        return name or package_key

    def _split_pnpm_key(self, key: str, fallback_version: object | None) -> tuple[str, str | None]:
        segments = key.split("/")
        if len(segments) < 2:
            return key, str(fallback_version) if isinstance(fallback_version, str) else None
        if segments[0] == "":
            name_segments = segments[1:-1] or segments[1:2]
            name = "/".join(name_segments)
            version = segments[-1]
        else:
            name = segments[0]
            version = segments[-1]
        if isinstance(fallback_version, str):
            version = fallback_version
        return name, version

    def _parse_inline_mapping(self, value: str) -> dict[str, str]:
        inner = value.strip("{} ")
        result: dict[str, str] = {}
        for part in inner.split(","):
            if not part.strip():
                continue
            key, _, val = part.partition(":")
            result[key.strip()] = val.strip()
        return result
