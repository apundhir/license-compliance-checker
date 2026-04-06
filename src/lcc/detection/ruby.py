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
Ruby ecosystem detector implementation.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from pathlib import Path

from lcc.detection.base import Detector
from lcc.models import Component, ComponentType

RequirementSpec = tuple[str, str | None, dict[str, object]]


class RubyDetector(Detector):
    """
    Detects Ruby gems from Gemfile and Gemfile.lock.
    """

    def __init__(self) -> None:
        super().__init__(name="ruby")

    def supports(self, project_root: Path) -> bool:
        """Check if project has Ruby manifests."""
        return (project_root / "Gemfile").exists() or (project_root / "Gemfile.lock").exists()

    def discover(self, project_root: Path) -> Sequence[Component]:
        """Discover Ruby gems from Gemfile and Gemfile.lock."""
        specs: dict[str, Component] = {}
        # Track gem names declared in Gemfile (direct deps)
        gemfile_direct_names: set[str] = set()

        def register(name: str, version: str | None, source: str, metadata: dict[str, object] | None = None) -> None:
            # Use name as key to merge different versions
            if name not in specs:
                # Prefer locked version from Gemfile.lock
                normalized_version = version or "*"
                specs[name] = Component(
                    type=ComponentType.RUBY,
                    name=name,
                    version=normalized_version,
                    metadata={"sources": []},
                )
                specs[name].metadata["project_root"] = str(project_root)

            component = specs[name]

            # Update version if we have a locked version and current is not
            if version and version != "*" and component.version == "*":
                component.version = version

            component.metadata.setdefault("sources", [])
            source_entry = {"source": source, "project_root": str(project_root)}
            if metadata:
                source_entry.update(metadata)
            component.metadata["sources"].append(source_entry)

        # Parse Gemfile.lock first (most accurate)
        for requirement in self._parse_gemfile_lock(project_root):
            name, version, metadata = requirement
            register(name, version, "Gemfile.lock", metadata)

        # Parse Gemfile (may have version constraints) and collect direct names
        for requirement in self._parse_gemfile(project_root):
            name, version, metadata = requirement
            register(name, version, "Gemfile", metadata)
            gemfile_direct_names.add(name)

        # Build Gemfile.lock dependency graph for depth calculation
        lock_dep_graph: dict[str, list[str]] = {}
        lock_dep_graph = self._build_gemfile_lock_dependency_graph(project_root)

        # Compute depths from the dependency graph
        depth_map: dict[str, int] = {}
        parent_map: dict[str, list[str]] = {}
        if lock_dep_graph:
            depth_map, parent_map = self._compute_gem_dependency_depths(
                gemfile_direct_names, lock_dep_graph,
            )

        # Assign dependency depth metadata
        for component in specs.values():
            comp_name = component.name
            is_direct = comp_name in gemfile_direct_names
            # Determine source type
            source_files = [s.get("source", "") for s in component.metadata.get("sources", [])]
            has_manifest = any(str(s) == "Gemfile" for s in source_files)
            has_lockfile = any(str(s) == "Gemfile.lock" for s in source_files)
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

        return list(specs.values())

    # -------------------------
    # Dependency depth helpers
    # -------------------------

    def _build_gemfile_lock_dependency_graph(self, project_root: Path) -> dict[str, list[str]]:
        """Build a dependency graph from Gemfile.lock specs section.

        Parses the indentation-based structure where:
        - 4-space indent = gem definition (parent)
        - 6-space indent = dependency of the gem above (child)

        Returns a mapping of gem name -> list of dependency names.
        """
        path = project_root / "Gemfile.lock"
        if not path.exists():
            return {}
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return {}

        graph: dict[str, list[str]] = {}
        in_specs = False
        current_gem: str | None = None

        for line in content.splitlines():
            line_stripped = line.rstrip()

            if line_stripped == "  specs:":
                in_specs = True
                current_gem = None
                continue

            if in_specs and line and not line.startswith(" "):
                in_specs = False
                current_gem = None
                continue

            if not in_specs:
                continue

            # Gem definition at 4-space indent: "    gem-name (version)"
            if line.startswith("    ") and not line.startswith("      "):
                match = re.match(r"    ([a-zA-Z0-9_.-]+)\s+\(([^)]+)\)", line_stripped)
                if match:
                    current_gem = match.group(1)
                    graph.setdefault(current_gem, [])
            # Dependency at 6+ space indent: "      dep-name (constraint)"
            elif line.startswith("      ") and current_gem:
                match = re.match(r"\s+([a-zA-Z0-9_.-]+)", line_stripped)
                if match:
                    dep_name = match.group(1)
                    graph.setdefault(current_gem, []).append(dep_name)

        return graph

    def _compute_gem_dependency_depths(
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

    def _parse_gemfile_lock(self, project_root: Path) -> Iterable[RequirementSpec]:
        """Parse Gemfile.lock for exact gem versions."""
        path = project_root / "Gemfile.lock"
        if not path.exists():
            return []

        results: list[RequirementSpec] = []
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return []

        # Gemfile.lock structure:
        # GEM
        #   remote: https://rubygems.org/
        #   specs:
        #     gem-name (version)
        #       dependency (>= version)

        in_specs = False
        for line in content.splitlines():
            line_stripped = line.rstrip()

            # Check if we're entering the specs section
            if line_stripped == "  specs:":
                in_specs = True
                continue

            # Exit specs section when we hit a new top-level section
            if in_specs and line and not line.startswith(" "):
                in_specs = False
                continue

            if not in_specs:
                continue

            # Parse gem entry: "    gem-name (version)"
            # Specs are indented with 4 spaces, dependencies with 6+
            if line.startswith("    ") and not line.startswith("      "):
                match = re.match(r"    ([a-zA-Z0-9_-]+)\s+\(([^)]+)\)", line_stripped)
                if match:
                    name, version = match.groups()
                    results.append((name, version, {"locked": True}))

        return results

    def _parse_gemfile(self, project_root: Path) -> Iterable[RequirementSpec]:
        """Parse Gemfile for gem declarations."""
        path = project_root / "Gemfile"
        if not path.exists():
            return []

        results: list[RequirementSpec] = []
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return []

        # Parse gem declarations:
        # gem 'name'
        # gem 'name', 'version'
        # gem 'name', '~> version'
        # gem 'name', '>= version', '< version'
        # gem "name", require: false, group: :development

        for line in content.splitlines():
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Match gem declarations
            # Pattern: gem 'name' or gem "name"
            gem_match = re.match(r"gem\s+['\"]([^'\"]+)['\"](.*)$", line)
            if not gem_match:
                continue

            name = gem_match.group(1)
            rest = gem_match.group(2).strip()

            version = None
            metadata: dict[str, object] = {}

            # Extract version constraints
            # Look for quoted version strings after the gem name
            version_matches = re.findall(r"['\"]([~>=<!\s0-9.]+)['\"]", rest)
            if version_matches:
                # If there's an exact version (just numbers and dots)
                for ver in version_matches:
                    ver = ver.strip()
                    if re.match(r"^[0-9.]+$", ver):
                        version = ver
                        break
                # Store all constraints
                if version_matches:
                    metadata["constraints"] = version_matches

            # Extract group information
            if "group:" in rest:
                group_match = re.search(r"group:\s*:(\w+)", rest)
                if group_match:
                    metadata["group"] = group_match.group(1)
                # Handle array of groups: group: [:development, :test]
                group_array_match = re.search(r"group:\s*\[([^\]]+)\]", rest)
                if group_array_match:
                    groups = [g.strip().strip(":") for g in group_array_match.group(1).split(",")]
                    metadata["groups"] = groups

            # Extract require information
            if "require:" in rest:
                if "require: false" in rest or 'require: "false"' in rest or "require: 'false'" in rest:
                    metadata["require"] = False

            # Extract git information
            if "git:" in rest:
                git_match = re.search(r"git:\s*['\"]([^'\"]+)['\"]", rest)
                if git_match:
                    metadata["git"] = git_match.group(1)

            # Extract branch/tag/ref
            if "branch:" in rest:
                branch_match = re.search(r"branch:\s*['\"]([^'\"]+)['\"]", rest)
                if branch_match:
                    metadata["branch"] = branch_match.group(1)

            if "tag:" in rest:
                tag_match = re.search(r"tag:\s*['\"]([^'\"]+)['\"]", rest)
                if tag_match:
                    metadata["tag"] = tag_match.group(1)

            results.append((name, version, metadata))

        return results
