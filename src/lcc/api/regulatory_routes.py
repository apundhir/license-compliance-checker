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
EU AI Act regulatory compliance API endpoints.

Provides endpoints for running EU AI Act assessments on completed scans
and downloading compliance packs as ZIP archives.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from lcc.auth.core import User, get_current_active_user
from lcc.database.repository import ScanRepository
from lcc.database.session import get_db
from lcc.models import (
    Component,
    ComponentFinding,
    ComponentType,
    LicenseEvidence,
)
from lcc.regulatory.eu_ai_act import EUAIActAssessor

router = APIRouter(prefix="/regulatory", tags=["regulatory"])


def _get_repository(session: AsyncSession = Depends(get_db)) -> ScanRepository:
    return ScanRepository(session)


def _deserialize_findings(report_data: dict) -> list[ComponentFinding]:
    """Reconstruct ComponentFinding objects from stored report JSON."""
    findings: list[ComponentFinding] = []
    for item in report_data.get("findings", []):
        component_data = item.get("component", {})
        component_type = component_data.get("type", ComponentType.GENERIC.value)
        try:
            component_type_enum = ComponentType(component_type)
        except ValueError:
            component_type_enum = ComponentType.GENERIC

        component = Component(
            type=component_type_enum,
            name=component_data.get("name", ""),
            version=component_data.get("version", "*"),
            namespace=component_data.get("namespace"),
            path=Path(component_data["path"]) if component_data.get("path") else None,
            metadata=component_data.get("metadata", {}),
        )
        evidences = [
            LicenseEvidence(
                source=evidence.get("source", ""),
                license_expression=evidence.get("license_expression", "UNKNOWN"),
                confidence=float(evidence.get("confidence", 0.0)),
                raw_data=evidence.get("raw_data", {}),
                url=evidence.get("url"),
            )
            for evidence in item.get("evidences", [])
        ]
        finding = ComponentFinding(
            component=component,
            evidences=evidences,
            resolved_license=item.get("resolved_license"),
            confidence=float(item.get("confidence", 0.0)),
        )
        findings.append(finding)
    return findings


def _generate_markdown_report(report_dict: dict) -> str:
    """Generate a human-readable Markdown compliance report."""
    lines: list[str] = []
    lines.append(f"# {report_dict.get('title', 'EU AI Act Compliance Report')}")
    lines.append("")
    lines.append(f"**Framework:** {report_dict.get('framework', 'eu_ai_act')}")
    lines.append(f"**Generated:** {report_dict.get('generated_at', '')}")
    lines.append("")

    summary = report_dict.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total AI Components:** {summary.get('total_ai_components', 0)}")
    lines.append(f"- **Compliant:** {summary.get('compliant', 0)}")
    lines.append(f"- **Partial:** {summary.get('partial', 0)}")
    lines.append(f"- **Non-Compliant:** {summary.get('non_compliant', 0)}")
    lines.append(f"- **Compliance Score:** {summary.get('compliance_percentage', 0)}%")
    lines.append("")

    assessments = report_dict.get("assessments", [])
    if assessments:
        lines.append("## Per-Component Assessments")
        lines.append("")
        for assessment in assessments:
            lines.append(f"### {assessment.get('component_name', 'Unknown')}")
            lines.append("")
            lines.append(f"- **Type:** {assessment.get('component_type', '')}")
            lines.append(f"- **Risk Classification:** {assessment.get('risk_classification', '')}")
            lines.append(f"- **Overall Status:** {assessment.get('overall_status', '')}")
            lines.append("")

            obligations = assessment.get("obligations", [])
            if obligations:
                lines.append("| Article | Title | Status | Evidence | Gaps |")
                lines.append("|---------|-------|--------|----------|------|")
                for ob in obligations:
                    evidence_str = "; ".join(ob.get("evidence", []))
                    gaps_str = "; ".join(ob.get("gaps", []))
                    lines.append(
                        f"| {ob.get('article', '')} "
                        f"| {ob.get('title', '')} "
                        f"| {ob.get('status', '')} "
                        f"| {evidence_str} "
                        f"| {gaps_str} |"
                    )
                lines.append("")

            recommendations = assessment.get("recommendations", [])
            if recommendations:
                lines.append("**Recommendations:**")
                for rec in recommendations:
                    lines.append(f"- {rec}")
                lines.append("")

    return "\n".join(lines)


@router.get("/assess/{scan_id}")
async def assess_scan(
    scan_id: str,
    repo: ScanRepository = Depends(_get_repository),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """Run EU AI Act assessment on a completed scan."""
    scan = await repo.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if not scan.report:
        raise HTTPException(
            status_code=400,
            detail="Scan has no report data. Ensure the scan has completed successfully.",
        )

    # Deserialize findings from the stored report
    findings = _deserialize_findings(scan.report)

    # Run EU AI Act assessment
    assessor = EUAIActAssessor()
    report = assessor.assess_scan(findings)

    return JSONResponse(content=report.to_dict())


@router.get("/compliance-pack/{scan_id}")
async def download_compliance_pack(
    scan_id: str,
    repo: ScanRepository = Depends(_get_repository),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Generate and download EU AI Act Compliance Pack as a ZIP file."""
    scan = await repo.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if not scan.report:
        raise HTTPException(
            status_code=400,
            detail="Scan has no report data. Ensure the scan has completed successfully.",
        )

    # Deserialize findings and run assessment
    findings = _deserialize_findings(scan.report)
    assessor = EUAIActAssessor()
    report = assessor.assess_scan(findings)
    report_dict = report.to_dict()

    # Generate ZIP archive in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. JSON report
        zf.writestr(
            "eu-ai-act-assessment.json",
            json.dumps(report_dict, indent=2, ensure_ascii=False),
        )

        # 2. Markdown report
        markdown_content = _generate_markdown_report(report_dict)
        zf.writestr("eu-ai-act-report.md", markdown_content)

        # 3. Scan metadata
        scan_meta = {
            "scan_id": scan.id,
            "project": scan.project_name,
            "scan_status": scan.status,
            "created_at": scan.created_at.isoformat() if scan.created_at else "",
            "pack_generated_at": datetime.utcnow().isoformat(),
        }
        zf.writestr(
            "scan-metadata.json",
            json.dumps(scan_meta, indent=2, ensure_ascii=False),
        )

    zip_buffer.seek(0)

    filename = f"eu-ai-act-compliance-pack-{scan_id[:8]}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
