"""
Python ecosystem detector implementation.
"""

from __future__ import annotations

from __future__ import annotations

import ast
import json
import re
import zipfile
from collections import defaultdict
from email.parser import Parser
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from lcc.detection.base import Detector
from lcc.models import Component, ComponentType


RequirementSpec = Tuple[str, Optional[str], Dict[str, object]]


class PythonDetector(Detector):
    """
    Detects Python packages from various manifests.
    """

    def __init__(self) -> None:
        super().__init__(name="python")

    def supports(self, project_root: Path) -> bool:  # pragma: no cover - simple predicate
        manifests = ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile", "poetry.lock", "environment.yml"]
        if any((project_root / manifest).exists() for manifest in manifests):
            return True
            
        # Recursive check for nested projects (e.g. monorepos)
        # Check for key manifests in subdirectories
        patterns = ["**/requirements.txt", "**/pyproject.toml", "**/setup.py", "**/Pipfile", "**/poetry.lock"]
        for pattern in patterns:
            try:
                # Use next() to return True as soon as one is found, preventing full traversal
                if next(project_root.rglob(pattern), None):
                    return True
            except (OSError, PermissionError):
                continue
        return False

    def discover(self, project_root: Path) -> Sequence[Component]:
        specs: Dict[Tuple[str, str], Component] = {}

        def register(
            name: str,
            version: Optional[str],
            source: str,
            metadata: Optional[MutableMapping[str, object]] = None,
        ) -> None:
            canonical = canonicalize_name(name)
            normalized_version = version or "*"
            key = (canonical, normalized_version)
            if key not in specs:
                specs[key] = Component(
                    type=ComponentType.PYTHON,
                    name=name,
                    version=normalized_version,
                    metadata={"sources": []},
                )
                specs[key].metadata["project_root"] = str(project_root)
            component = specs[key]
            component.metadata.setdefault("sources", [])
            source_entry = {"source": source}
            source_entry["project_root"] = str(project_root)
            if metadata:
                source_entry.update(metadata)
            component.metadata["sources"].append(source_entry)
            if metadata and metadata.get("license"):
                licenses = component.metadata.setdefault("licenses", set())
                if isinstance(licenses, set):
                    licenses.add(metadata["license"])
                else:  # pragma: no cover - defensive branch
                    licenses = {metadata["license"]}
                    component.metadata["licenses"] = licenses

        # Helper to find files recursively
        def find_files(pattern: str) -> Iterable[Path]:
             return project_root.rglob(pattern)

        # Requirements.txt
        for requirement in self._parse_requirements_txt(project_root):
            name, version, metadata = requirement
            register(name, version, metadata.get("source", "requirements.txt"), metadata)

        # setup.py
        for path in find_files("setup.py"):
            if self._is_excluded(path, project_root): continue
            for requirement in self._parse_setup_py_file(path, project_root):
                name, version, metadata = requirement
                register(name, version, str(path.relative_to(project_root)), metadata)

        # pyproject.toml
        for path in find_files("pyproject.toml"):
            if self._is_excluded(path, project_root): continue
            for requirement in self._parse_pyproject_file(path, project_root):
                 name, version, metadata = requirement
                 register(name, version, metadata.pop("source", str(path.relative_to(project_root))), metadata)

        # Pipfile
        for path in find_files("Pipfile"):
            if self._is_excluded(path, project_root): continue
            for requirement in self._parse_pipfile_file(path, project_root):
                name, version, metadata = requirement
                register(name, version, str(path.relative_to(project_root)), metadata)

        # poetry.lock
        for path in find_files("poetry.lock"):
            if self._is_excluded(path, project_root): continue
            for requirement in self._parse_poetry_lock_file(path, project_root):
                name, version, metadata = requirement
                register(name, version, str(path.relative_to(project_root)), metadata)

        # environment.yml
        for path in find_files("environment.yml"):
            if self._is_excluded(path, project_root): continue
            for requirement in self._parse_environment_yml_file(path, project_root):
                name, version, metadata = requirement
                register(name, version, str(path.relative_to(project_root)), metadata)

        for requirement in self._parse_local_metadata(project_root):
            name, version, metadata = requirement
            register(name, version, metadata.pop("source"), metadata)

        for component in specs.values():
            if isinstance(component.metadata.get("licenses"), set):
                component.metadata["licenses"] = sorted(component.metadata["licenses"])
        return list(specs.values())

    # -------------------------
    # Individual manifest parsers
    # -------------------------

    def _parse_requirements_txt(self, project_root: Path) -> Iterable[RequirementSpec]:
        """
        Parse requirements files from various locations and naming patterns recursively.
        """
        results: List[RequirementSpec] = []
        
        # Collect all requirements files recursively
        requirements_files = set(project_root.rglob("requirements.txt"))
        requirements_files.update(project_root.rglob("requirements/*.txt"))
        requirements_files.update(project_root.rglob("requirements-*.txt"))
        
        # Common skip patterns
        skip_dirs = {".venv", "venv", "site-packages", "node_modules", "__pycache__", ".git"}

        # Parse each file found
        for path in requirements_files:
            # Skip if in ignored directory
            if any(part in skip_dirs for part in path.parts):
                continue
            # Skip if in config-excluded directory
            if self._is_excluded(path, project_root):
                continue

            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Determine source label for metadata
            try:
                relative_path = path.relative_to(project_root)
            except ValueError:
                relative_path = path
            source_label = str(relative_path)

            for line in content.splitlines():
                line = line.strip()
                # Skip empty lines, comments, and -r includes (to avoid duplicates)
                if not line or line.startswith("#") or line.startswith("-r"):
                    continue
                # Skip constraint files (-c) and editable installs (-e) for now
                if line.startswith("-c") or line.startswith("-e"):
                    continue
                try:
                    req = Requirement(line)
                except Exception:
                    continue
                version = None
                specifier = str(req.specifier) if req.specifier else None
                if req.specifier and len(req.specifier) == 1:
                    operator, value = next(iter(req.specifier._specs))._spec
                    if operator == "==":
                        version = value
                metadata: Dict[str, object] = {"requirement": line, "source": source_label}
                if specifier and not version:
                    metadata["specifier"] = specifier
                if req.marker:
                    metadata["marker"] = str(req.marker)
                if req.extras:
                    metadata["extras"] = sorted(req.extras)
                results.append((req.name, version, metadata))

        return results

    def _parse_setup_py_file(self, path: Path, project_root: Path) -> Iterable[RequirementSpec]:
        if not path.exists():
            return []
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            return []

        requirements: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(getattr(node.func, "id", None), "lower", lambda: "")() == "setup":
                for keyword in node.keywords:
                    if keyword.arg == "install_requires":
                        requirements.extend(self._extract_string_list(keyword.value))
                    elif keyword.arg == "extras_require":
                        mapping = self._extract_mapping(keyword.value)
                        for values in mapping.values():
                            requirements.extend(values)
        return [self._requirement_from_string(req, {"section": "setup.py"}) for req in requirements]

    def _parse_pyproject_file(self, path: Path, project_root: Path) -> Iterable[RequirementSpec]:
        if not path.exists():
            return []
        if not path.exists():
            return []
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        results: List[RequirementSpec] = []

        project_data = data.get("project", {})
        if isinstance(project_data, dict):
            for dep in project_data.get("dependencies", []) or []:
                results.append(self._requirement_from_string(dep, {"source": "pyproject.toml[project.dependencies]"}))
            optional = project_data.get("optional-dependencies", {})
            if isinstance(optional, dict):
                for group, deps in optional.items():
                    for dep in deps or []:
                        results.append(
                            self._requirement_from_string(dep, {"source": f"pyproject.toml[optional.{group}]"})
                        )

        poetry_data = data.get("tool", {}).get("poetry", {})
        if isinstance(poetry_data, dict):
            dependencies = poetry_data.get("dependencies", {})
            results.extend(self._parse_poetry_deps(dependencies, "tool.poetry.dependencies"))
            dev = poetry_data.get("dev-dependencies", {})
            results.extend(self._parse_poetry_deps(dev, "tool.poetry.dev-dependencies"))
            for group_name, group_data in poetry_data.get("group", {}).items():
                if isinstance(group_data, dict):
                    results.extend(
                        self._parse_poetry_deps(
                            group_data.get("dependencies", {}),
                            f"tool.poetry.group.{group_name}",
                        )
                    )

        return results

    def _parse_poetry_deps(self, dependencies: MutableMapping[str, object], section: str) -> Iterable[RequirementSpec]:
        results: List[RequirementSpec] = []
        for name, value in (dependencies or {}).items():
            if name.lower() == "python":
                continue
            if isinstance(value, str):
                results.append(self._requirement_from_string(f"{name} {value}", {"source": section}))
            elif isinstance(value, dict):
                version = value.get("version")
                extras = value.get("extras") or []
                markers = value.get("markers")
                metadata: Dict[str, object] = {"source": section}
                if extras:
                    metadata["extras"] = extras
                if markers:
                    metadata["marker"] = markers
                if isinstance(value.get("license"), str):
                    metadata["license"] = value["license"]
                req_str = f"{name} {version}" if isinstance(version, str) else name
                results.append(self._requirement_from_string(req_str, metadata))
        return results

    def _parse_pipfile_file(self, path: Path, project_root: Path) -> Iterable[RequirementSpec]:
        if not path.exists():
            return []
        if not path.exists():
            return []
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        packages = data.get("packages", {})
        dev_packages = data.get("dev-packages", {})
        results: List[RequirementSpec] = []
        for section_name, deps in (("packages", packages), ("dev-packages", dev_packages)):
            for name, value in deps.items():
                metadata: Dict[str, object] = {"section": section_name}
                if isinstance(value, str):
                    results.append(self._requirement_from_string(f"{name} {value}", metadata))
                elif isinstance(value, dict):
                    version = value.get("version")
                    if version:
                        results.append(self._requirement_from_string(f"{name} {version}", metadata))
                    else:
                        results.append((name, None, metadata))
        return results

    def _parse_poetry_lock_file(self, path: Path, project_root: Path) -> Iterable[RequirementSpec]:
        if not path.exists():
            return []
        if not path.exists():
            return []
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        packages = data.get("package", [])
        results: List[RequirementSpec] = []
        for package in packages or []:
            if not isinstance(package, dict):
                continue
            name = package.get("name")
            version = package.get("version")
            if not isinstance(name, str) or not isinstance(version, str):
                continue
            metadata: Dict[str, object] = {"source": "poetry.lock"}
            if isinstance(package.get("license"), str):
                metadata["license"] = package["license"]
            if isinstance(package.get("category"), str):
                metadata["category"] = package["category"]
            results.append((name, version, metadata))
        return results

    def _parse_environment_yml_file(self, path: Path, project_root: Path) -> Iterable[RequirementSpec]:
        if not path.exists():
            return []
        if not path.exists():
            return []
        content = path.read_text(encoding="utf-8")
        results: List[RequirementSpec] = []
        in_dependencies = False
        in_pip = False
        # Skip conda meta-packages that aren't real PyPI packages
        conda_skip = {"python", "pip", "conda", "setuptools", "wheel"}
        for raw_line in content.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(stripped)
            if stripped.startswith("dependencies:"):
                in_dependencies = True
                in_pip = False
                continue
            if not in_dependencies:
                continue
            if stripped.startswith("- "):
                value = stripped[2:].strip()
                if value.endswith(":"):
                    in_pip = value[:-1] == "pip"
                    continue
                if in_pip and indent >= 4:
                    results.append(self._requirement_from_string(value, {"section": "environment.yml[pip]"}))
                else:
                    in_pip = False
                    name, version = self._split_environment_dependency(value)
                    # Skip conda meta-packages
                    if name.lower() in conda_skip:
                        continue
                    results.append((name, version, {"channel": "conda"}))
            elif indent <= 2:
                in_pip = False
        return results

    def _parse_local_metadata(self, project_root: Path) -> Iterable[RequirementSpec]:
        """
        Parse local Python package metadata.

        NOTE: This scans installed packages (.dist-info, .whl, .egg files).
        For source code scans (GitHub repos), these are typically unwanted as they
        represent installed dependencies, not declarations.

        This method now skips common virtual environment and installed package
        directories to avoid scanning installed libraries in source repos.
        """
        results: List[RequirementSpec] = []

        # Common directories to skip (virtual envs, build artifacts, node_modules-like patterns)
        skip_patterns = {
            "venv", ".venv", "env", ".env",  # Virtual environments
            "site-packages", "dist-packages",  # Installed packages
            "__pycache__", ".tox", ".pytest_cache",  # Build/test artifacts
            "build", "dist", ".eggs",  # Build outputs
            "node_modules",  # JS dependencies (sometimes in mixed repos)
        }

        def should_skip_path(path: Path) -> bool:
            """Check if path contains any skip patterns in its parents."""
            for parent in path.parents:
                if parent.name in skip_patterns:
                    return True
            return False

        # Skip scanning .dist-info and PKG-INFO files (they represent installed packages)
        # Uncomment the lines below if you need to scan installed packages
        # (e.g., for Docker images or deployed code)

        # metadata_files = list(project_root.glob("**/*.dist-info/METADATA")) + list(project_root.glob("**/PKG-INFO"))
        # for metadata_path in metadata_files:
        #     if should_skip_path(metadata_path):
        #         continue
        #     metadata = Parser().parsestr(metadata_path.read_text(encoding="utf-8", errors="ignore"))
        #     name = metadata.get("Name")
        #     version = metadata.get("Version")
        #     license_expression = metadata.get("License-Expression") or metadata.get("License")
        #     if not name or not version:
        #         continue
        #     details: Dict[str, object] = {"source": str(metadata_path)}
        #     if license_expression:
        #         details["license"] = license_expression.strip()
        #     classifiers = [value for key, value in metadata.items() if key == "Classifier" and "License" in value]
        #     if classifiers:
        #         details["classifiers"] = classifiers
        #     results.append((name, version, details))

        # Skip scanning .whl and .egg files (they represent packaged/installed code)
        # for archive_path in project_root.glob("**/*.whl"):
        #     if should_skip_path(archive_path):
        #         continue
        #     results.extend(self._extract_archive_metadata(archive_path))
        # for archive_path in project_root.glob("**/*.egg"):
        #     if should_skip_path(archive_path):
        #         continue
        #     results.extend(self._extract_archive_metadata(archive_path))

        return results

    # -------------------------
    # Helpers
    # -------------------------

    def _extract_string_list(self, node: ast.AST) -> List[str]:
        values: List[str] = []
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for element in node.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    values.append(element.value)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.append(node.value)
        return values

    def _extract_mapping(self, node: ast.AST) -> Dict[str, List[str]]:
        mapping: Dict[str, List[str]] = defaultdict(list)
        if not isinstance(node, (ast.Dict,)):
            return mapping
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                mapping[key.value].extend(self._extract_string_list(value))
        return mapping

    def _requirement_from_string(self, requirement: str, metadata: Optional[MutableMapping[str, object]] = None) -> RequirementSpec:
        try:
            req = Requirement(requirement)
        except Exception:
            return (requirement.split()[0], None, metadata or {})
        version = None
        if req.specifier and len(req.specifier) == 1:
            operator, value = next(iter(req.specifier._specs))._spec
            if operator == "==":
                version = value
        elif req.specifier and "==" in str(req.specifier):
            possibilities = [spec for spec in req.specifier if spec.operator == "=="]
            if possibilities:
                version = possibilities[0].version
        data: Dict[str, object] = dict(metadata or {})
        if req.marker:
            data["marker"] = str(req.marker)
        if req.extras:
            data["extras"] = sorted(req.extras)
        if req.specifier and not version:
            data["specifier"] = str(req.specifier)
        return (req.name, version, data)

    def _split_environment_dependency(self, spec: str) -> Tuple[str, Optional[str]]:
        if "=" not in spec:
            return spec, None
        name, _, version = spec.partition("=")
        if version.startswith("="):
            version = version[1:]
        return name, version or None

    def _extract_archive_metadata(self, archive_path: Path) -> Iterable[RequirementSpec]:
        results: List[RequirementSpec] = []
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                metadata_name = next(
                    (name for name in archive.namelist() if name.endswith("METADATA") or name.endswith("PKG-INFO")),
                    None,
                )
                if not metadata_name:
                    return results
                with archive.open(metadata_name) as handle:
                    metadata = Parser().parsestr(handle.read().decode("utf-8", errors="ignore"))
        except zipfile.BadZipFile:
            return results
        name = metadata.get("Name")
        version = metadata.get("Version")
        license_expression = metadata.get("License-Expression") or metadata.get("License")
        if not name or not version:
            return results
        details: Dict[str, object] = {"source": str(archive_path)}
        if license_expression:
            details["license"] = license_expression.strip()
        classifiers = [value for key, value in metadata.items() if key == "Classifier" and "License" in value]
        if classifiers:
            details["classifiers"] = classifiers
        results.append((name, version, details))
        return results
