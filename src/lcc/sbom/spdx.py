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
SPDX SBOM Generator - Software Package Data Exchange format.

Generates SPDX 2.3 and 3.0 SBOMs in multiple formats (JSON, RDF/XML, Tag-Value, YAML).
Spec: https://spdx.github.io/spdx-spec/
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packageurl import PackageURL
from spdx_tools.spdx.model import (
    Actor,
    ActorType,
    Annotation,
    AnnotationType,
    Checksum,
    ChecksumAlgorithm,
    CreationInfo,
    Document,
    ExternalPackageRef,
    ExternalPackageRefCategory,
    Package,
    Relationship,
    RelationshipType,
    SpdxNoAssertion,
)
from spdx_tools.spdx.writer.write_anything import write_file

from lcc.models import Component, ComponentResult, ComponentType, ScanResult
from lcc.sbom.regulatory_properties import get_regulatory_annotation_text


class SPDXGenerator:
    """
    Generates SPDX 2.3 and 3.0 format SBOMs.

    Features:
    - Document creation information
    - Package information with supplier/originator
    - License information (declared, concluded, detected)
    - Relationship information (DEPENDS_ON, CONTAINS)
    - Multiple output formats (JSON, XML, Tag-Value, YAML)
    """

    def __init__(
        self,
        tool_name: str = "license-compliance-checker",
        tool_version: str = "0.1.0",
        organization: str = "LCC Contributors",
    ) -> None:
        self.tool_name = tool_name
        self.tool_version = tool_version
        self.organization = organization

    def generate(
        self,
        scan_result: ScanResult,
        project_name: str | None = None,
        project_version: str | None = None,
        document_namespace: str | None = None,
        creator: str | None = None,
    ) -> Document:
        """
        Generate an SPDX document from a scan result.

        Args:
            scan_result: The LCC scan result
            project_name: Name of the project
            project_version: Version of the project
            document_namespace: SPDX document namespace URI
            creator: Document creator name

        Returns:
            SPDX Document object
        """
        # Generate document namespace if not provided
        if not document_namespace:
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            doc_name = project_name or "unknown"
            document_namespace = (
                f"https://lcc.example.org/spdx/{doc_name}-{timestamp}"
            )

        # Create creation info
        creation_info = self._create_creation_info(creator)

        # Create document
        doc_name = project_name or "Software Package"
        doc_version = project_version or "unknown"
        spdx_id = "SPDXRef-DOCUMENT"

        document = Document(
            spdx_version="SPDX-2.3",
            spdx_id=spdx_id,
            name=f"{doc_name} {doc_version}",
            document_namespace=document_namespace,
            creation_info=creation_info,
        )

        # Create root package
        root_package = Package(
            spdx_id="SPDXRef-Package",
            name=doc_name,
            version=doc_version,
            download_location=SpdxNoAssertion(),
        )
        document.packages.append(root_package)

        # Add DESCRIBES relationship
        document.relationships.append(
            Relationship(
                spdx_element_id=spdx_id,
                relationship_type=RelationshipType.DESCRIBES,
                related_spdx_element_id="SPDXRef-Package",
            )
        )

        # Convert components to packages
        for idx, component in enumerate(scan_result.components, start=1):
            package = self._convert_component(component, scan_result, idx)
            document.packages.append(package)

            # Add CONTAINS relationship
            document.relationships.append(
                Relationship(
                    spdx_element_id="SPDXRef-Package",
                    relationship_type=RelationshipType.CONTAINS,
                    related_spdx_element_id=package.spdx_id,
                )
            )

            # Add DEPENDS_ON relationship
            document.relationships.append(
                Relationship(
                    spdx_element_id="SPDXRef-Package",
                    relationship_type=RelationshipType.DEPENDS_ON,
                    related_spdx_element_id=package.spdx_id,
                )
            )

            # Add regulatory annotation for AI/ML components
            comp_result = next(
                (
                    cr
                    for cr in scan_result.component_results
                    if cr.component == component
                ),
                None,
            )
            annotation = self._create_regulatory_annotation(
                component, comp_result, package.spdx_id
            )
            if annotation is not None:
                document.annotations.append(annotation)

        return document

    def _create_creation_info(self, creator: str | None) -> CreationInfo:
        """Create SPDX creation info."""
        creators = [
            Actor(
                actor_type=ActorType.TOOL,
                name=f"{self.tool_name}-{self.tool_version}",
            )
        ]

        if creator:
            creators.append(
                Actor(
                    actor_type=ActorType.PERSON,
                    name=creator,
                )
            )
        else:
            creators.append(
                Actor(
                    actor_type=ActorType.ORGANIZATION,
                    name=self.organization,
                )
            )

        return CreationInfo(
            spdx_version="SPDX-2.3",
            spdx_id="SPDXRef-DOCUMENT",
            name="LCC SBOM",
            document_namespace="https://lcc.example.org/temp",
            creators=creators,
            created=datetime.now(UTC),
        )

    def _convert_component(
        self, component: Component, scan_result: ScanResult, index: int
    ) -> Package:
        """Convert LCC Component to SPDX Package."""

        # Create SPDX ID
        spdx_id = f"SPDXRef-Package-{index}"

        # Get licenses
        declared_license = self._get_declared_license(component, scan_result)
        concluded_license = self._get_concluded_license(component, scan_result)

        # Create package
        package = Package(
            spdx_id=spdx_id,
            name=component.name,
            version=component.version if component.version != "*" else None,
            download_location=self._get_download_location(component),
            files_analyzed=False,
            license_concluded=concluded_license or SpdxNoAssertion(),
            license_declared=declared_license or SpdxNoAssertion(),
        )

        # Add description
        if "description" in component.metadata:
            package.description = component.metadata["description"]

        # Add supplier
        if "supplier" in component.metadata:
            package.supplier = Actor(
                actor_type=ActorType.ORGANIZATION,
                name=component.metadata["supplier"],
            )

        # Add originator
        if "originator" in component.metadata:
            package.originator = Actor(
                actor_type=ActorType.PERSON,
                name=component.metadata["originator"],
            )

        # Add checksums
        checksums = self._get_checksums(component)
        if checksums:
            package.checksums = checksums

        # Add external references (including regulatory refs for AI/ML)
        external_refs = self._get_external_refs(component)
        if external_refs:
            package.external_references = external_refs

        return package

    def _get_declared_license(
        self, component: Component, scan_result: ScanResult
    ) -> str | None:
        """Get declared license from component."""
        comp_result = next(
            (cr for cr in scan_result.component_results if cr.component == component),
            None,
        )

        if not comp_result or not comp_result.licenses:
            return None

        # Use the highest confidence license
        licenses = sorted(comp_result.licenses, key=lambda x: x.confidence, reverse=True)
        return licenses[0].license_expression if licenses else None

    def _get_concluded_license(
        self, component: Component, scan_result: ScanResult
    ) -> str | None:
        """Get concluded license (same as declared for now)."""
        return self._get_declared_license(component, scan_result)

    def _get_download_location(self, component: Component) -> str:
        """Get download location for component."""
        if "repository_url" in component.metadata:
            return component.metadata["repository_url"]
        elif "download_url" in component.metadata:
            return component.metadata["download_url"]
        else:
            return str(SpdxNoAssertion())

    def _get_checksums(self, component: Component) -> list[Checksum]:
        """Get checksums for component."""
        checksums = []

        if "sha1" in component.metadata:
            checksums.append(
                Checksum(
                    algorithm=ChecksumAlgorithm.SHA1,
                    value=component.metadata["sha1"],
                )
            )

        if "sha256" in component.metadata:
            checksums.append(
                Checksum(
                    algorithm=ChecksumAlgorithm.SHA256,
                    value=component.metadata["sha256"],
                )
            )

        if "sha512" in component.metadata:
            checksums.append(
                Checksum(
                    algorithm=ChecksumAlgorithm.SHA512,
                    value=component.metadata["sha512"],
                )
            )

        return checksums

    def _get_external_refs(self, component: Component) -> list[ExternalPackageRef]:
        """Get external references for component."""
        refs = []

        # Add PURL if available
        purl = self._create_purl(component)
        if purl:
            refs.append(
                ExternalPackageRef(
                    category=ExternalPackageRefCategory.PACKAGE_MANAGER,
                    reference_type="purl",
                    locator=str(purl),
                )
            )

        # Add model card reference for AI/ML components
        if component.type in (ComponentType.AI_MODEL, ComponentType.DATASET):
            model_card_url = component.metadata.get("model_card_url")
            if model_card_url:
                refs.append(
                    ExternalPackageRef(
                        category=ExternalPackageRefCategory.OTHER,
                        reference_type="model-card",
                        locator=str(model_card_url),
                        comment="Model card or dataset card URL",
                    )
                )

        return refs

    def _create_regulatory_annotation(
        self,
        component: Component,
        component_result: ComponentResult | None,
        spdx_element_id: str,
    ) -> Annotation | None:
        """
        Create a REVIEW annotation with regulatory metadata for AI/ML components.

        Returns ``None`` for non-AI component types.
        """
        annotation_text = get_regulatory_annotation_text(component, component_result)
        if annotation_text is None:
            return None

        return Annotation(
            spdx_id=spdx_element_id,
            annotation_type=AnnotationType.REVIEW,
            annotator=Actor(
                actor_type=ActorType.TOOL,
                name=f"{self.tool_name}-{self.tool_version}",
            ),
            annotation_date=datetime.now(UTC),
            annotation_comment=annotation_text,
        )

    def _create_purl(self, component: Component) -> PackageURL | None:
        """Create Package URL for component."""
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
            return None

    def save(
        self,
        document: Document,
        output_path: Path,
        format: str = "json",
    ) -> None:
        """
        Save SPDX document to file.

        Args:
            document: The SPDX document
            output_path: Path to output file
            format: Output format ("json", "xml", "yaml", "tag-value")
        """
        # Map format names to spdx-tools format identifiers
        format_mapping = {
            "json": "json",
            "xml": "xml",
            "yaml": "yaml",
            "tag-value": "tagvalue",
            "tagvalue": "tagvalue",
            "rdf": "xml",
        }

        spdx_format = format_mapping.get(format.lower())
        if not spdx_format:
            raise ValueError(
                f"Unsupported format: {format}. "
                f"Use 'json', 'xml', 'yaml', or 'tag-value'."
            )

        write_file(document, str(output_path), data_license=True, validate=False)

    def to_json(self, document: Document, pretty: bool = True) -> str:
        """
        Serialize document to SPDX JSON format.

        Args:
            document: The SPDX document
            pretty: Whether to pretty-print the JSON

        Returns:
            JSON string
        """
        from spdx_tools.spdx.writer.json.json_writer import write_document_to_string

        json_str = write_document_to_string(document)

        if pretty:
            data = json.loads(json_str)
            return json.dumps(data, indent=2, sort_keys=False)

        return json_str

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
            format: Output format ("json", "xml", "yaml", "tag-value")
            **metadata: Additional metadata (project_name, project_version, etc.)
        """
        # Load scan result
        with open(scan_result_path, encoding="utf-8") as f:
            data = json.load(f)

        # Deserialize to ScanResult
        from lcc.reporting.json_reporter import deserialize_scan_result

        scan_result = deserialize_scan_result(data)

        # Generate document
        document = self.generate(scan_result, **metadata)

        # Save
        self.save(document, output_path, format=format)
