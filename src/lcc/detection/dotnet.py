"""
.NET/NuGet ecosystem detector implementation.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from lcc.detection.base import Detector
from lcc.models import Component, ComponentType


RequirementSpec = Tuple[str, Optional[str], Dict[str, object]]


class DotNetDetector(Detector):
    """
    Detects .NET packages from various NuGet manifests.

    Supports:
    - packages.config (legacy)
    - .csproj (PackageReference)
    - .fsproj (F# projects)
    - .vbproj (VB.NET projects)
    - project.json (legacy .NET Core)
    - paket.dependencies (Paket package manager)
    """

    def __init__(self) -> None:
        super().__init__(name="dotnet")

    def supports(self, project_root: Path) -> bool:
        """Check if project has .NET manifests."""
        # Check for NuGet manifests
        if (project_root / "packages.config").exists():
            return True

        # Check for project files
        for pattern in ["*.csproj", "*.fsproj", "*.vbproj"]:
            if list(project_root.glob(pattern)):
                return True

        # Check for .NET Core / Paket manifests
        if (project_root / "project.json").exists():
            return True

        if (project_root / "paket.dependencies").exists():
            return True

        return False

    def discover(self, project_root: Path) -> Sequence[Component]:
        """Discover .NET packages from NuGet manifests."""
        specs: Dict[str, Component] = {}

        def register(name: str, version: Optional[str], source: str, metadata: Optional[Dict[str, object]] = None) -> None:
            # Use name as key to merge different versions
            if name not in specs:
                normalized_version = version or "*"
                specs[name] = Component(
                    type=ComponentType.DOTNET,
                    name=name,
                    version=normalized_version,
                    metadata={"sources": []},
                )
                specs[name].metadata["project_root"] = str(project_root)

            component = specs[name]

            # Update version if we have a specific version and current is not
            if version and version != "*" and component.version == "*":
                component.version = version

            component.metadata.setdefault("sources", [])
            source_entry = {"source": source, "project_root": str(project_root)}
            if metadata:
                source_entry.update(metadata)
            component.metadata["sources"].append(source_entry)

        # Parse packages.config (legacy)
        for requirement in self._parse_packages_config(project_root):
            name, version, metadata = requirement
            register(name, version, "packages.config", metadata)

        # Parse .csproj files
        for requirement in self._parse_project_files(project_root, "*.csproj"):
            name, version, metadata = requirement
            register(name, version, metadata.pop("source", ".csproj"), metadata)

        # Parse .fsproj files
        for requirement in self._parse_project_files(project_root, "*.fsproj"):
            name, version, metadata = requirement
            register(name, version, metadata.pop("source", ".fsproj"), metadata)

        # Parse .vbproj files
        for requirement in self._parse_project_files(project_root, "*.vbproj"):
            name, version, metadata = requirement
            register(name, version, metadata.pop("source", ".vbproj"), metadata)

        # Parse project.json (legacy .NET Core)
        for requirement in self._parse_project_json(project_root):
            name, version, metadata = requirement
            register(name, version, "project.json", metadata)

        # Parse paket.dependencies
        for requirement in self._parse_paket_dependencies(project_root):
            name, version, metadata = requirement
            register(name, version, "paket.dependencies", metadata)

        return list(specs.values())

    def _parse_packages_config(self, project_root: Path) -> Iterable[RequirementSpec]:
        """
        Parse packages.config (legacy NuGet format).

        Example:
        <?xml version="1.0" encoding="utf-8"?>
        <packages>
          <package id="Newtonsoft.Json" version="13.0.1" targetFramework="net472" />
        </packages>
        """
        path = project_root / "packages.config"
        if not path.exists():
            return []

        results: List[RequirementSpec] = []
        try:
            tree = ET.parse(path)
            root = tree.getroot()

            for package in root.findall("package"):
                package_id = package.get("id")
                version = package.get("version")
                target_framework = package.get("targetFramework")

                if not package_id:
                    continue

                metadata: Dict[str, object] = {}
                if target_framework:
                    metadata["targetFramework"] = target_framework

                results.append((package_id, version, metadata))

        except Exception:
            pass

        return results

    def _parse_project_files(self, project_root: Path, pattern: str) -> Iterable[RequirementSpec]:
        """
        Parse .csproj/.fsproj/.vbproj files for PackageReference.

        Example:
        <Project Sdk="Microsoft.NET.Sdk">
          <ItemGroup>
            <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
            <PackageReference Include="Serilog" Version="2.10.0" PrivateAssets="all" />
          </ItemGroup>
        </Project>
        """
        results: List[RequirementSpec] = []

        for project_file in project_root.glob(pattern):
            try:
                tree = ET.parse(project_file)
                root = tree.getroot()

                # Find all PackageReference elements (with or without namespace)
                for item_group in root.findall(".//{*}ItemGroup"):
                    for package_ref in item_group.findall("{*}PackageReference"):
                        package_id = package_ref.get("Include")
                        version = package_ref.get("Version")

                        if not package_id:
                            continue

                        metadata: Dict[str, object] = {"source": project_file.name}

                        # Extract additional attributes
                        private_assets = package_ref.get("PrivateAssets")
                        if private_assets:
                            metadata["privateAssets"] = private_assets

                        include_assets = package_ref.get("IncludeAssets")
                        if include_assets:
                            metadata["includeAssets"] = include_assets

                        exclude_assets = package_ref.get("ExcludeAssets")
                        if exclude_assets:
                            metadata["excludeAssets"] = exclude_assets

                        results.append((package_id, version, metadata))

            except Exception:
                continue

        return results

    def _parse_project_json(self, project_root: Path) -> Iterable[RequirementSpec]:
        """
        Parse project.json (legacy .NET Core format).

        Example:
        {
          "dependencies": {
            "Microsoft.NETCore.App": {
              "version": "1.0.0",
              "type": "platform"
            },
            "Newtonsoft.Json": "9.0.1"
          }
        }
        """
        path = project_root / "project.json"
        if not path.exists():
            return []

        results: List[RequirementSpec] = []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            dependencies = data.get("dependencies", {})

            if not isinstance(dependencies, dict):
                return []

            for name, spec in dependencies.items():
                metadata: Dict[str, object] = {}
                version = None

                if isinstance(spec, str):
                    # Simple version string: "Newtonsoft.Json": "9.0.1"
                    version = spec
                elif isinstance(spec, dict):
                    # Object with version and type
                    version = spec.get("version")
                    dep_type = spec.get("type")
                    if dep_type:
                        metadata["type"] = dep_type

                results.append((name, version, metadata))

        except Exception:
            pass

        return results

    def _parse_paket_dependencies(self, project_root: Path) -> Iterable[RequirementSpec]:
        """
        Parse paket.dependencies (Paket package manager).

        Example:
        source https://api.nuget.org/v3/index.json

        nuget FSharp.Core >= 4.7.2
        nuget Newtonsoft.Json ~> 13.0
        nuget Serilog 2.10.0
        """
        path = project_root / "paket.dependencies"
        if not path.exists():
            return []

        results: List[RequirementSpec] = []
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return []

        for line in content.splitlines():
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#") or line.startswith("//"):
                continue

            # Skip source declarations
            if line.startswith("source ") or line.startswith("framework:") or line.startswith("group "):
                continue

            # Parse nuget lines: nuget PackageName [version_constraint]
            nuget_match = re.match(r"nuget\s+([^\s]+)(?:\s+(.+))?$", line)
            if nuget_match:
                name = nuget_match.group(1)
                constraint = nuget_match.group(2)

                version = None
                metadata: Dict[str, object] = {}

                if constraint:
                    constraint = constraint.strip()
                    metadata["constraint"] = constraint

                    # Try to extract exact version (no operators)
                    if re.match(r"^[0-9.]+$", constraint):
                        version = constraint

                results.append((name, version, metadata))

        return results
