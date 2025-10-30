"""Tests for CycloneDX SBOM generator."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from lcc.models import (
    Component,
    ComponentResult,
    ComponentType,
    LicenseEvidence,
    ScanResult,
    Status,
)
from lcc.sbom.cyclonedx import CycloneDXGenerator


@pytest.fixture
def sample_components():
    """Create sample components for testing."""
    return [
        Component(
            type=ComponentType.PYTHON,
            name="requests",
            version="2.31.0",
            namespace=None,
            metadata={
                "description": "Python HTTP library",
                "repository_url": "https://github.com/psf/requests",
                "sha256": "abc123",
            },
        ),
        Component(
            type=ComponentType.JAVASCRIPT,
            name="react",
            version="18.2.0",
            namespace=None,
            metadata={"description": "React library"},
        ),
        Component(
            type=ComponentType.GO,
            name="gin",
            version="1.9.1",
            namespace="github.com/gin-gonic",
            metadata={},
        ),
    ]


@pytest.fixture
def sample_scan_result(sample_components):
    """Create a sample scan result."""
    component_results = [
        ComponentResult(
            component=sample_components[0],
            status=Status.PASS,
            licenses=[
                LicenseEvidence(
                    source="pypi",
                    license_expression="Apache-2.0",
                    confidence=0.95,
                )
            ],
            violations=[],
            warnings=[],
        ),
        ComponentResult(
            component=sample_components[1],
            status=Status.WARNING,
            licenses=[
                LicenseEvidence(
                    source="npm",
                    license_expression="MIT",
                    confidence=0.99,
                )
            ],
            violations=[],
            warnings=["Deprecated version"],
        ),
        ComponentResult(
            component=sample_components[2],
            status=Status.PASS,
            licenses=[
                LicenseEvidence(
                    source="go.mod",
                    license_expression="BSD-3-Clause",
                    confidence=0.90,
                )
            ],
            violations=[],
            warnings=[],
        ),
    ]

    return ScanResult(
        components=sample_components,
        component_results=component_results,
        scan_id="test-scan-001",
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
    )


def test_cyclonedx_generator_initialization():
    """Test CycloneDX generator initialization."""
    generator = CycloneDXGenerator()
    assert generator.tool_name == "license-compliance-checker"
    assert generator.tool_version == "0.1.0"
    assert generator.tool_vendor == "LCC Contributors"


def test_cyclonedx_generator_custom_metadata():
    """Test CycloneDX generator with custom metadata."""
    generator = CycloneDXGenerator(
        tool_name="custom-lcc",
        tool_version="2.0.0",
        tool_vendor="Custom Vendor",
    )
    assert generator.tool_name == "custom-lcc"
    assert generator.tool_version == "2.0.0"
    assert generator.tool_vendor == "Custom Vendor"


def test_generate_basic_bom(sample_scan_result):
    """Test generating a basic CycloneDX BOM."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    assert bom is not None
    assert bom.metadata is not None
    assert bom.metadata.timestamp is not None
    assert len(bom.metadata.tools) > 0
    assert len(bom.components) == 3


def test_generate_bom_with_metadata(sample_scan_result):
    """Test generating BOM with project metadata."""
    generator = CycloneDXGenerator()
    bom = generator.generate(
        sample_scan_result,
        project_name="TestProject",
        project_version="1.0.0",
        author="Test Author",
        supplier="Test Supplier",
    )

    assert bom is not None
    assert len(bom.metadata.authors) > 0
    assert bom.metadata.supplier is not None
    assert bom.metadata.supplier.name == "Test Supplier"


def test_component_mapping(sample_scan_result):
    """Test component type mapping to CycloneDX types."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    components = list(bom.components)
    assert len(components) == 3

    # Check component properties
    requests_comp = next(c for c in components if c.name == "requests")
    assert requests_comp.version == "2.31.0"
    assert requests_comp.purl is not None
    assert "pypi" in str(requests_comp.purl)


def test_license_extraction(sample_scan_result):
    """Test license extraction from scan result."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    components = list(bom.components)
    requests_comp = next(c for c in components if c.name == "requests")

    assert requests_comp.licenses is not None
    assert len(requests_comp.licenses) > 0


def test_external_references(sample_scan_result):
    """Test external references in components."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    components = list(bom.components)
    requests_comp = next(c for c in components if c.name == "requests")

    assert len(requests_comp.external_references) > 0
    vcs_refs = [
        ref
        for ref in requests_comp.external_references
        if ref.reference_type.name == "VCS"
    ]
    assert len(vcs_refs) > 0


def test_component_hashes(sample_scan_result):
    """Test component hashes in BOM."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    components = list(bom.components)
    requests_comp = next(c for c in components if c.name == "requests")

    # Should have SHA-256 hash from metadata
    assert len(requests_comp.hashes) > 0
    sha256_hashes = [h for h in requests_comp.hashes if h.algorithm.name == "SHA_256"]
    assert len(sha256_hashes) > 0


def test_custom_properties(sample_scan_result):
    """Test custom LCC properties in components."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    components = list(bom.components)
    requests_comp = next(c for c in components if c.name == "requests")

    # Should have LCC-specific properties
    props = list(requests_comp.properties)
    assert len(props) > 0

    # Check for specific properties
    type_props = [p for p in props if p.name == "lcc:component_type"]
    assert len(type_props) > 0
    assert type_props[0].value == "python"

    status_props = [p for p in props if p.name == "lcc:compliance_status"]
    assert len(status_props) > 0
    assert status_props[0].value == "pass"


def test_json_serialization(sample_scan_result, tmp_path):
    """Test JSON serialization of BOM."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    json_output = generator.to_json(bom, pretty=True)
    assert json_output is not None
    assert len(json_output) > 0

    # Verify it's valid JSON
    data = json.loads(json_output)
    assert data["bomFormat"] == "CycloneDX"
    assert "components" in data
    assert len(data["components"]) == 3


def test_json_serialization_not_pretty(sample_scan_result):
    """Test non-pretty JSON serialization."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    json_output = generator.to_json(bom, pretty=False)
    assert json_output is not None

    # Should not have excessive whitespace
    data = json.loads(json_output)
    assert data["bomFormat"] == "CycloneDX"


def test_xml_serialization(sample_scan_result):
    """Test XML serialization of BOM."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    xml_output = generator.to_xml(bom)
    assert xml_output is not None
    assert len(xml_output) > 0
    assert "<?xml" in xml_output
    assert "cyclonedx" in xml_output.lower()


def test_save_json(sample_scan_result, tmp_path):
    """Test saving BOM to JSON file."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    output_file = tmp_path / "test_bom.json"
    generator.save(bom, output_file, format="json", pretty=True)

    assert output_file.exists()

    # Verify content
    with open(output_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["bomFormat"] == "CycloneDX"


def test_save_xml(sample_scan_result, tmp_path):
    """Test saving BOM to XML file."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    output_file = tmp_path / "test_bom.xml"
    generator.save(bom, output_file, format="xml")

    assert output_file.exists()

    # Verify content
    content = output_file.read_text(encoding="utf-8")
    assert "<?xml" in content
    assert "cyclonedx" in content.lower()


def test_save_invalid_format(sample_scan_result, tmp_path):
    """Test saving with invalid format raises error."""
    generator = CycloneDXGenerator()
    bom = generator.generate(sample_scan_result)

    output_file = tmp_path / "test_bom.invalid"

    with pytest.raises(ValueError, match="Unsupported format"):
        generator.save(bom, output_file, format="invalid")


def test_purl_generation():
    """Test PURL generation for different component types."""
    generator = CycloneDXGenerator()

    test_cases = [
        (ComponentType.PYTHON, "requests", "2.0.0", "pypi"),
        (ComponentType.JAVASCRIPT, "react", "18.0.0", "npm"),
        (ComponentType.GO, "gin", "1.0.0", "golang"),
        (ComponentType.JAVA, "junit", "5.0.0", "maven"),
        (ComponentType.RUST, "serde", "1.0.0", "cargo"),
        (ComponentType.RUBY, "rails", "7.0.0", "gem"),
        (ComponentType.DOTNET, "Newtonsoft.Json", "13.0.0", "nuget"),
    ]

    for comp_type, name, version, expected_type in test_cases:
        component = Component(
            type=comp_type,
            name=name,
            version=version,
        )
        purl = generator._create_purl(component)
        assert purl is not None
        assert purl.type == expected_type
        assert purl.name == name
        assert purl.version == version


def test_ai_model_component_type():
    """Test AI model component type mapping."""
    generator = CycloneDXGenerator()

    component = Component(
        type=ComponentType.AI_MODEL,
        name="bert-base-uncased",
        version="1.0.0",
    )

    scan_result = ScanResult(
        components=[component],
        component_results=[
            ComponentResult(
                component=component,
                status=Status.PASS,
                licenses=[],
                violations=[],
                warnings=[],
            )
        ],
        scan_id="test-ai",
        timestamp=datetime.now(),
    )

    bom = generator.generate(scan_result)
    components = list(bom.components)
    assert len(components) == 1

    ai_comp = components[0]
    assert ai_comp.component_type.name == "MACHINE_LEARNING_MODEL"


def test_dataset_component_type():
    """Test dataset component type mapping."""
    generator = CycloneDXGenerator()

    component = Component(
        type=ComponentType.DATASET,
        name="imagenet",
        version="2012",
    )

    scan_result = ScanResult(
        components=[component],
        component_results=[
            ComponentResult(
                component=component,
                status=Status.PASS,
                licenses=[],
                violations=[],
                warnings=[],
            )
        ],
        scan_id="test-dataset",
        timestamp=datetime.now(),
    )

    bom = generator.generate(scan_result)
    components = list(bom.components)
    assert len(components) == 1

    dataset_comp = components[0]
    assert dataset_comp.component_type.name == "DATA"


def test_component_with_violations(sample_components):
    """Test component with violations in properties."""
    component = sample_components[0]
    scan_result = ScanResult(
        components=[component],
        component_results=[
            ComponentResult(
                component=component,
                status=Status.VIOLATION,
                licenses=[
                    LicenseEvidence(
                        source="test",
                        license_expression="GPL-3.0",
                        confidence=0.95,
                    )
                ],
                violations=["Copyleft license not allowed"],
                warnings=["Consider alternative"],
            )
        ],
        scan_id="test-violations",
        timestamp=datetime.now(),
    )

    generator = CycloneDXGenerator()
    bom = generator.generate(scan_result)

    components = list(bom.components)
    comp = components[0]

    # Check properties
    props = list(comp.properties)
    violation_props = [p for p in props if p.name == "lcc:violations"]
    assert len(violation_props) > 0
    assert violation_props[0].value == "1"

    warning_props = [p for p in props if p.name == "lcc:warnings"]
    assert len(warning_props) > 0
    assert warning_props[0].value == "1"
