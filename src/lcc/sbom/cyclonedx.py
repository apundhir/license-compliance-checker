"""
CycloneDX SBOM Generator - Industry standard software bill of materials.

Generates CycloneDX 1.5 SBOMs in JSON and XML formats.
Spec: https://cyclonedx.org/docs/1.5/json/
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from cyclonedx.model import (
    ExternalReference,
    ExternalReferenceType,
    HashAlgorithm,
    HashType,
    Property,
    XsUri,
)
from cyclonedx.model.tool import Tool
from cyclonedx.model.contact import OrganizationalContact, OrganizationalEntity
from cyclonedx.model.license import License, LicenseChoice
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component as CdxComponent
from cyclonedx.model.component import ComponentType as CdxComponentType
from cyclonedx.output.json import JsonV1Dot5
from cyclonedx.output.xml import XmlV1Dot5
from packageurl import PackageURL

from lcc.models import Component, ComponentType, ScanResult


class CycloneDXGenerator:
    """
    Generates CycloneDX 1.5 format SBOMs.

    Features:
    - Component metadata with licenses
    - Dependency graph
    - External references
    - Hashes (SHA-256, SHA-512)
    - BOM metadata (tools, authors, timestamp)
    """

    def __init__(
        self,
        tool_name: str = "license-compliance-checker",
        tool_version: str = "0.1.0",
        tool_vendor: str = "LCC Contributors",
    ) -> None:
        self.tool_name = tool_name
        self.tool_version = tool_version
        self.tool_vendor = tool_vendor

    def generate(
        self,
        scan_result: ScanResult,
        project_name: Optional[str] = None,
        project_version: Optional[str] = None,
        author: Optional[str] = None,
        supplier: Optional[str] = None,
    ) -> Bom:
        """
        Generate a CycloneDX BOM from a scan result.

        Args:
            scan_result: The LCC scan result
            project_name: Name of the project
            project_version: Version of the project
            author: Project author
            supplier: Project supplier/organization

        Returns:
            CycloneDX Bom object
        """
        # Create BOM metadata
        bom = Bom()
        bom.metadata.timestamp = datetime.now(timezone.utc)

        # Add tool information
        tool = Tool(
            vendor=self.tool_vendor,
            name=self.tool_name,
            version=self.tool_version,
        )
        bom.metadata.tools.add(tool)

        # Add authors if provided
        if author:
            contact = OrganizationalContact(name=author)
            bom.metadata.authors.add(contact)

        # Add supplier if provided
        if supplier:
            org = OrganizationalEntity(name=supplier)
            bom.metadata.supplier = org

        # Convert components
        for component in scan_result.components:
            cdx_component = self._convert_component(component, scan_result)
            bom.components.add(cdx_component)

        return bom

    def _convert_component(
        self, component: Component, scan_result: ScanResult
    ) -> CdxComponent:
        """Convert LCC Component to CycloneDX Component."""

        # Map component type
        cdx_type = self._map_component_type(component.type)

        # Create package URL
        purl = self._create_purl(component)

        # Create CycloneDX component
        cdx_component = CdxComponent(
            name=component.name,
            version=component.version if component.version != "*" else "unknown",
            component_type=cdx_type,
            purl=purl,
        )

        # Add licenses
        licenses = self._get_component_licenses(component, scan_result)
        if licenses:
            cdx_component.licenses = licenses

        # Add description from metadata
        if "description" in component.metadata:
            cdx_component.description = component.metadata["description"]

        # Add external references
        external_refs = self._create_external_references(component)
        for ref in external_refs:
            cdx_component.external_references.add(ref)

        # Add hashes if available
        if "sha256" in component.metadata:
            hash_type = HashType(
                algorithm=HashAlgorithm.SHA_256,
                hash_value=component.metadata["sha256"],
            )
            cdx_component.hashes.add(hash_type)

        if "sha512" in component.metadata:
            hash_type = HashType(
                algorithm=HashAlgorithm.SHA_512,
                hash_value=component.metadata["sha512"],
            )
            cdx_component.hashes.add(hash_type)

        # Add custom properties
        properties = self._create_properties(component, scan_result)
        for prop in properties:
            cdx_component.properties.add(prop)

        return cdx_component

    def _map_component_type(self, comp_type: ComponentType) -> CdxComponentType:
        """Map LCC ComponentType to CycloneDX ComponentType."""
        mapping = {
            ComponentType.PYTHON: CdxComponentType.LIBRARY,
            ComponentType.JAVASCRIPT: CdxComponentType.LIBRARY,
            ComponentType.GO: CdxComponentType.LIBRARY,
            ComponentType.JAVA: CdxComponentType.LIBRARY,
            ComponentType.GRADLE: CdxComponentType.LIBRARY,
            ComponentType.RUST: CdxComponentType.LIBRARY,
            ComponentType.RUBY: CdxComponentType.LIBRARY,
            ComponentType.DOTNET: CdxComponentType.LIBRARY,
            ComponentType.PHP: CdxComponentType.LIBRARY,
            ComponentType.AI_MODEL: CdxComponentType.MACHINE_LEARNING_MODEL,
            ComponentType.DATASET: CdxComponentType.DATA,
            ComponentType.GENERIC: CdxComponentType.LIBRARY,
        }
        return mapping.get(comp_type, CdxComponentType.LIBRARY)

    def _create_purl(self, component: Component) -> Optional[PackageURL]:
        """Create Package URL for component."""

        # Map LCC types to PURL types
        type_mapping = {
            ComponentType.PYTHON: "pypi",
            ComponentType.JAVASCRIPT: "npm",
            ComponentType.GO: "golang",
            ComponentType.JAVA: "maven",
            ComponentType.GRADLE: "maven",
            ComponentType.RUST: "cargo",
            ComponentType.RUBY: "gem",
            ComponentType.DOTNET: "nuget",
            ComponentType.PHP: "composer",
            ComponentType.AI_MODEL: "huggingface",
            ComponentType.DATASET: "huggingface",
        }

        purl_type = type_mapping.get(component.type)
        if not purl_type:
            return None

        version = component.version if component.version != "*" else None

        try:
            return PackageURL(
                type=purl_type,
                namespace=component.namespace,
                name=component.name,
                version=version,
            )
        except Exception:
            # Invalid PURL, return None
            return None

    def _get_component_licenses(
        self, component: Component, scan_result: ScanResult
    ) -> Optional[List[LicenseChoice]]:
        """Extract licenses for component from scan result."""

        # Find the component result
        comp_result = next(
            (cr for cr in scan_result.component_results if cr.component == component),
            None,
        )

        if not comp_result or not comp_result.licenses:
            return None

        license_choices = []

        for lic_evidence in comp_result.licenses:
            # Try to parse as SPDX expression first
            try:
                license_choice = LicenseChoice(expression=lic_evidence.license_expression)
                license_choices.append(license_choice)
            except Exception:
                # Fall back to license name
                lic = License(name=lic_evidence.license_expression)
                license_choice = LicenseChoice(license=lic)
                license_choices.append(license_choice)

        return license_choices if license_choices else None

    def _create_external_references(
        self, component: Component
    ) -> List[ExternalReference]:
        """Create external references for component."""
        refs = []

        # Repository URL
        if "repository_url" in component.metadata:
            refs.append(
                ExternalReference(
                    reference_type=ExternalReferenceType.VCS,
                    url=XsUri(component.metadata["repository_url"]),
                )
            )

        # Website URL
        if "website" in component.metadata:
            refs.append(
                ExternalReference(
                    reference_type=ExternalReferenceType.WEBSITE,
                    url=XsUri(component.metadata["website"]),
                )
            )

        # Documentation URL
        if "documentation" in component.metadata:
            refs.append(
                ExternalReference(
                    reference_type=ExternalReferenceType.DOCUMENTATION,
                    url=XsUri(component.metadata["documentation"]),
                )
            )

        return refs

    def _create_properties(
        self, component: Component, scan_result: ScanResult
    ) -> List[Property]:
        """Create custom properties for component."""
        props = []

        # Add LCC-specific metadata
        props.append(
            Property(
                name="lcc:component_type",
                value=component.type.value,
            )
        )

        # Add compliance status
        comp_result = next(
            (cr for cr in scan_result.component_results if cr.component == component),
            None,
        )

        if comp_result:
            props.append(
                Property(
                    name="lcc:compliance_status",
                    value=comp_result.status.value,
                )
            )

            if comp_result.violations:
                props.append(
                    Property(
                        name="lcc:violations",
                        value=str(len(comp_result.violations)),
                    )
                )

            if comp_result.warnings:
                props.append(
                    Property(
                        name="lcc:warnings",
                        value=str(len(comp_result.warnings)),
                    )
                )

        # Add custom metadata
        for key, value in component.metadata.items():
            if key not in [
                "repository_url",
                "website",
                "documentation",
                "description",
                "sha256",
                "sha512",
            ]:
                props.append(
                    Property(
                        name=f"lcc:metadata:{key}",
                        value=str(value),
                    )
                )

        return props

    def to_json(self, bom: Bom, pretty: bool = True) -> str:
        """
        Serialize BOM to CycloneDX JSON format.

        Args:
            bom: The BOM to serialize
            pretty: Whether to pretty-print the JSON

        Returns:
            JSON string
        """
        outputter = JsonV1Dot5(bom)
        json_str = outputter.output_as_string()

        if pretty:
            # Re-parse and pretty print
            data = json.loads(json_str)
            return json.dumps(data, indent=2, sort_keys=False)

        return json_str

    def to_xml(self, bom: Bom) -> str:
        """
        Serialize BOM to CycloneDX XML format.

        Args:
            bom: The BOM to serialize

        Returns:
            XML string
        """
        outputter = XmlV1Dot5(bom)
        return outputter.output_as_string()

    def save(
        self,
        bom: Bom,
        output_path: Path,
        format: str = "json",
        pretty: bool = True,
    ) -> None:
        """
        Save BOM to file.

        Args:
            bom: The BOM to save
            output_path: Path to output file
            format: Output format ("json" or "xml")
            pretty: Whether to pretty-print (JSON only)
        """
        if format.lower() == "json":
            content = self.to_json(bom, pretty=pretty)
        elif format.lower() == "xml":
            content = self.to_xml(bom)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'xml'.")

        output_path.write_text(content, encoding="utf-8")

    def generate_from_file(
        self,
        scan_result_path: Path,
        output_path: Path,
        format: str = "json",
        **metadata,
    ) -> None:
        """
        Generate SBOM from a saved scan result JSON file.

        Args:
            scan_result_path: Path to scan result JSON
            output_path: Path to output SBOM
            format: Output format ("json" or "xml")
            **metadata: Additional metadata (project_name, project_version, etc.)
        """
        # Load scan result
        with open(scan_result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Deserialize to ScanResult
        # Note: This requires proper deserialization logic
        # For now, we'll assume a helper exists
        from lcc.reporting.json_reporter import deserialize_scan_result

        scan_result = deserialize_scan_result(data)

        # Generate BOM
        bom = self.generate(scan_result, **metadata)

        # Save
        self.save(bom, output_path, format=format)
