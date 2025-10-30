"""
Ruby ecosystem detector implementation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from lcc.detection.base import Detector
from lcc.models import Component, ComponentType


RequirementSpec = Tuple[str, Optional[str], Dict[str, object]]


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
        specs: Dict[str, Component] = {}

        def register(name: str, version: Optional[str], source: str, metadata: Optional[Dict[str, object]] = None) -> None:
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

        # Parse Gemfile (may have version constraints)
        for requirement in self._parse_gemfile(project_root):
            name, version, metadata = requirement
            register(name, version, "Gemfile", metadata)

        return list(specs.values())

    def _parse_gemfile_lock(self, project_root: Path) -> Iterable[RequirementSpec]:
        """Parse Gemfile.lock for exact gem versions."""
        path = project_root / "Gemfile.lock"
        if not path.exists():
            return []

        results: List[RequirementSpec] = []
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

        results: List[RequirementSpec] = []
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
            metadata: Dict[str, object] = {}

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
