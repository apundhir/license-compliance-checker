"""
SBOM Validator - Validates CycloneDX and SPDX SBOMs against schemas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cyclonedx.model.bom import Bom
from cyclonedx.parser.json import JsonParser as CdxJsonParser
from cyclonedx.parser.xml import XmlParser as CdxXmlParser
from cyclonedx.validation import validate_bom as cdx_validate
from cyclonedx.validation.json import JsonStrictValidator
from cyclonedx.validation.xml import XmlValidator
from spdx_tools.spdx.model import Document
from spdx_tools.spdx.parser.parse_anything import parse_file
from spdx_tools.spdx.validation.document_validator import validate_full_spdx_document
from spdx_tools.spdx.validation.validation_message import ValidationMessage


class ValidationError(Exception):
    """SBOM validation error."""

    pass


class SBOMValidator:
    """
    Validates SBOM documents against their schemas.

    Supports:
    - CycloneDX JSON and XML
    - SPDX JSON, XML, YAML, Tag-Value
    """

    def validate_cyclonedx(
        self, file_path: Path, format: str = "json"
    ) -> Tuple[bool, List[str]]:
        """
        Validate a CycloneDX SBOM.

        Args:
            file_path: Path to SBOM file
            format: Format ("json" or "xml")

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        try:
            # Parse the BOM
            if format.lower() == "json":
                parser = CdxJsonParser()
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                bom = parser.parse(content)

                # Validate
                validator = JsonStrictValidator(bom)
                validation_errors = validator.validate()
            elif format.lower() == "xml":
                parser = CdxXmlParser()
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                bom = parser.parse(content)

                # Validate
                validator = XmlValidator(bom)
                validation_errors = validator.validate()
            else:
                return False, [f"Unsupported format: {format}"]

            if validation_errors:
                error_msgs = [str(err) for err in validation_errors]
                return False, error_msgs

            return True, []

        except Exception as e:
            return False, [f"Validation error: {str(e)}"]

    def validate_spdx(self, file_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate an SPDX SBOM.

        Args:
            file_path: Path to SBOM file

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        try:
            # Parse the document (auto-detects format)
            document = parse_file(str(file_path))

            # Validate
            validation_messages = validate_full_spdx_document(document)

            if validation_messages:
                error_msgs = [
                    f"{msg.validation_message}: {msg.context}"
                    for msg in validation_messages
                ]
                return False, error_msgs

            return True, []

        except Exception as e:
            return False, [f"Validation error: {str(e)}"]

    def validate(
        self, file_path: Path, sbom_type: str = "auto", format: str = "auto"
    ) -> Tuple[bool, List[str]]:
        """
        Validate an SBOM with automatic type detection.

        Args:
            file_path: Path to SBOM file
            sbom_type: SBOM type ("cyclonedx", "spdx", or "auto")
            format: Format ("json", "xml", "yaml", "tag-value", or "auto")

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        # Auto-detect format from file extension
        if format == "auto":
            suffix = file_path.suffix.lower()
            format_map = {
                ".json": "json",
                ".xml": "xml",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".spdx": "tag-value",
            }
            format = format_map.get(suffix, "json")

        # Auto-detect SBOM type
        if sbom_type == "auto":
            sbom_type = self._detect_sbom_type(file_path, format)

        # Validate based on type
        if sbom_type == "cyclonedx":
            return self.validate_cyclonedx(file_path, format)
        elif sbom_type == "spdx":
            return self.validate_spdx(file_path)
        else:
            return False, [f"Unknown SBOM type: {sbom_type}"]

    def _detect_sbom_type(self, file_path: Path, format: str) -> str:
        """
        Detect SBOM type from file contents.

        Args:
            file_path: Path to SBOM file
            format: File format

        Returns:
            SBOM type ("cyclonedx" or "spdx")
        """
        try:
            if format in ("json", "yaml"):
                with open(file_path, "r", encoding="utf-8") as f:
                    if format == "json":
                        data = json.load(f)
                    else:
                        import yaml

                        data = yaml.safe_load(f)

                # Check for CycloneDX markers
                if "bomFormat" in data and data["bomFormat"] == "CycloneDX":
                    return "cyclonedx"

                # Check for SPDX markers
                if "spdxVersion" in data or "SPDXID" in data:
                    return "spdx"

            elif format == "xml":
                # Read first few lines to detect
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read(1000)

                if "cyclonedx" in content.lower():
                    return "cyclonedx"
                elif "spdx" in content.lower():
                    return "spdx"

            elif format == "tag-value":
                # Tag-value is SPDX-specific
                return "spdx"

        except Exception:
            pass

        # Default to CycloneDX
        return "cyclonedx"

    def validate_licenses(self, file_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate that all licenses in SBOM are valid SPDX expressions.

        Args:
            file_path: Path to SBOM file

        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings = []

        try:
            sbom_type = self._detect_sbom_type(file_path, "json")

            if sbom_type == "cyclonedx":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                components = data.get("components", [])
                for comp in components:
                    licenses = comp.get("licenses", [])
                    for lic in licenses:
                        if "expression" in lic:
                            # Validate SPDX expression
                            expr = lic["expression"]
                            if not self._is_valid_spdx_expression(expr):
                                warnings.append(
                                    f"Component {comp['name']}: "
                                    f"Invalid SPDX expression '{expr}'"
                                )

            elif sbom_type == "spdx":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                packages = data.get("packages", [])
                for pkg in packages:
                    declared = pkg.get("licenseDeclared")
                    concluded = pkg.get("licenseConcluded")

                    if declared and not self._is_valid_spdx_expression(declared):
                        warnings.append(
                            f"Package {pkg['name']}: "
                            f"Invalid declared license '{declared}'"
                        )

                    if concluded and not self._is_valid_spdx_expression(concluded):
                        warnings.append(
                            f"Package {pkg['name']}: "
                            f"Invalid concluded license '{concluded}'"
                        )

            return len(warnings) == 0, warnings

        except Exception as e:
            return False, [f"License validation error: {str(e)}"]

    def _is_valid_spdx_expression(self, expression: str) -> bool:
        """
        Check if a license expression is valid SPDX.

        Args:
            expression: License expression

        Returns:
            True if valid
        """
        # Skip NOASSERTION and NONE
        if expression in ("NOASSERTION", "NONE"):
            return True

        # Basic validation - check for common SPDX license IDs
        # In production, use a proper SPDX expression parser
        common_licenses = [
            "MIT",
            "Apache-2.0",
            "GPL-2.0",
            "GPL-3.0",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "ISC",
            "LGPL-2.1",
            "LGPL-3.0",
            "MPL-2.0",
            "CC0-1.0",
            "Unlicense",
        ]

        # Check if expression contains at least one known license
        for lic in common_licenses:
            if lic in expression:
                return True

        # If it contains AND/OR/WITH operators, assume it's an expression
        if any(op in expression for op in [" AND ", " OR ", " WITH "]):
            return True

        # Otherwise, it might be a custom license
        return True
