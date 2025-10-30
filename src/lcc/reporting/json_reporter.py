"""
JSON reporter.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from lcc.models import (
    Component,
    ComponentResult,
    ComponentType,
    LicenseEvidence,
    ScanReport,
    ScanResult,
    Status,
)
from lcc.reporting.base import Reporter


class JSONReporter(Reporter):
    """
    Serializes the ScanReport to JSON, preserving dataclass structure.
    """

    def render(self, report: ScanReport) -> str:
        return json.dumps(asdict(report), indent=2, sort_keys=True, default=str)


def deserialize_scan_result(data: Dict[str, Any]) -> ScanResult:
    """
    Deserialize a ScanResult from JSON data.

    Args:
        data: Dictionary from JSON

    Returns:
        ScanResult object
    """
    # Deserialize components
    components = []
    for comp_data in data.get("components", []):
        comp = Component(
            type=ComponentType(comp_data["type"]),
            name=comp_data["name"],
            version=comp_data["version"],
            namespace=comp_data.get("namespace"),
            path=Path(comp_data["path"]) if comp_data.get("path") else None,
            metadata=comp_data.get("metadata", {}),
        )
        components.append(comp)

    # Deserialize component results
    component_results = []
    for cr_data in data.get("component_results", []):
        # Find matching component
        component = next(
            (
                c
                for c in components
                if c.name == cr_data["component"]["name"]
                and c.version == cr_data["component"]["version"]
            ),
            None,
        )

        if not component:
            continue

        # Deserialize license evidence
        licenses = []
        for lic_data in cr_data.get("licenses", []):
            lic = LicenseEvidence(
                source=lic_data["source"],
                license_expression=lic_data["license_expression"],
                confidence=lic_data["confidence"],
                raw_data=lic_data.get("raw_data", {}),
            )
            licenses.append(lic)

        cr = ComponentResult(
            component=component,
            status=Status(cr_data["status"]),
            licenses=licenses,
            violations=cr_data.get("violations", []),
            warnings=cr_data.get("warnings", []),
        )
        component_results.append(cr)

    # Create ScanResult
    scan_result = ScanResult(
        components=components,
        component_results=component_results,
        scan_id=data.get("scan_id", "unknown"),
        timestamp=datetime.fromisoformat(data["timestamp"])
        if "timestamp" in data
        else datetime.now(),
    )

    return scan_result

