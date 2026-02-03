"""
JavaScript ecosystem detector implementation.
"""

from __future__ import annotations

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple

from lcc.detection.base import Detector
from lcc.models import Component, ComponentType


DependencySpec = Tuple[str, Optional[str], Dict[str, object]]


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
        registry: Dict[Tuple[str, str], Component] = {}

        def register(name: str, version: Optional[str], metadata: MutableMapping[str, object]) -> None:
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

        # package.json
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

        for path in find_files("package-lock.json"):
            if any(part in skip_dirs for part in path.parts): continue
            if self._is_excluded(path, project_root): continue
            for spec in self._parse_package_lock_file(path, project_root):
                register(*spec)

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

        for component in registry.values():
            if isinstance(component.metadata.get("licenses"), set):
                component.metadata["licenses"] = sorted(component.metadata["licenses"])
        return list(registry.values())

    # -------------------------
    # Manifest parsers
    # -------------------------

    def _parse_package_json(self, data: MutableMapping[str, object], source: str) -> Iterable[DependencySpec]:
        results: List[DependencySpec] = []
        for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
            deps = data.get(section, {})
            if isinstance(deps, dict):
                for name, spec in deps.items():
                    metadata: Dict[str, object] = {"section": section, "source": source}
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
        base_metadata: Dict[str, object] = {"source": source}
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
        results: List[DependencySpec] = []
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
                metadata: Dict[str, object] = {"source": "package-lock.json", "path": package_path}
                if isinstance(package_data.get("license"), str):
                    metadata["license"] = package_data["license"]
                results.append((name, version, metadata))
        else:
            # Legacy package-lock structure
            deps = data.get("dependencies", {})
            results.extend(self._collect_lock_dependencies(deps, prefix="package-lock.json"))
        return results

    def _collect_lock_dependencies(self, deps: MutableMapping[str, object], prefix: str) -> Iterable[DependencySpec]:
        results: List[DependencySpec] = []
        for name, data in deps.items():
            if not isinstance(data, dict):
                continue
            version = data.get("version")
            metadata: Dict[str, object] = {"source": prefix}
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
        results: List[DependencySpec] = []
        current_names: List[str] = []
        metadata: Dict[str, object] = {}
        version: Optional[str] = None
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
        results: List[DependencySpec] = []

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

    def _workspace_paths(self, project_root: Path, package_json: MutableMapping[str, object]) -> List[Path]:
        workspaces = package_json.get("workspaces")
        patterns: List[str] = []
        if isinstance(workspaces, list):
            patterns = [str(item) for item in workspaces if isinstance(item, str)]
        elif isinstance(workspaces, dict):
            packages = workspaces.get("packages")
            if isinstance(packages, list):
                patterns = [str(item) for item in packages if isinstance(item, str)]
        paths: List[Path] = []
        for pattern in patterns:
            paths.extend(project_root.glob(pattern))
        return [path for path in paths if path.is_dir()]

    def _parse_modern_yarn_lock(self, content: str) -> Iterable[DependencySpec]:
        results: List[DependencySpec] = []
        in_packages = False
        current_key: Optional[str] = None
        current_meta: Dict[str, object] = {}
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
        results: List[DependencySpec] = []
        in_packages = False
        current_key: Optional[str] = None
        current_meta: Dict[str, object] = {}
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

    def _split_pnpm_key(self, key: str, fallback_version: Optional[object]) -> Tuple[str, Optional[str]]:
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

    def _parse_inline_mapping(self, value: str) -> Dict[str, str]:
        inner = value.strip("{} ")
        result: Dict[str, str] = {}
        for part in inner.split(","):
            if not part.strip():
                continue
            key, _, val = part.partition(":")
            result[key.strip()] = val.strip()
        return result
