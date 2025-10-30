"""
SBOM API endpoints for generating and downloading SBOMs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from lcc.api.repository import ScanRepository
from lcc.auth.core import User, get_current_active_user
from lcc.sbom import CycloneDXGenerator, SPDXGenerator

router = APIRouter(prefix="/sbom", tags=["sbom"])

# This will be injected by the server module
_repository: Optional[ScanRepository] = None


def set_repository(repo: ScanRepository) -> None:
    """Set the repository instance (called by server module)."""
    global _repository
    _repository = repo


def get_repository() -> ScanRepository:
    """Get the repository instance for dependency injection."""
    if _repository is None:
        raise RuntimeError("Repository not initialized")
    return _repository


class SBOMGenerateRequest(BaseModel):
    """Request to generate SBOM."""

    scan_id: str
    format: str = "cyclonedx"  # cyclonedx or spdx
    output_format: str = "json"  # json, xml, yaml, tag-value
    project_name: Optional[str] = None
    project_version: Optional[str] = None
    author: Optional[str] = None
    supplier: Optional[str] = None


class SBOMResponse(BaseModel):
    """SBOM generation response."""

    scan_id: str
    format: str
    output_format: str
    download_url: str


@router.get("/scans/{scan_id}")
async def get_sbom(
    scan_id: str,
    format: str = Query("cyclonedx", regex="^(cyclonedx|spdx)$"),
    output_format: str = Query("json", regex="^(json|xml|yaml|tag-value)$"),
    project_name: Optional[str] = None,
    project_version: Optional[str] = None,
    author: Optional[str] = None,
    supplier: Optional[str] = None,
    repo: ScanRepository = Depends(get_repository),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """
    Generate and download SBOM for a scan.

    Parameters:
    - scan_id: ID of the scan
    - format: SBOM format (cyclonedx or spdx)
    - output_format: File format (json, xml, yaml, tag-value)
    - project_name: Optional project name
    - project_version: Optional project version
    - author: Optional author name
    - supplier: Optional supplier name

    Returns:
    - SBOM file
    """
    # Get scan result
    scan = repo.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

    try:
        # Generate SBOM
        temp_dir = Path("/tmp/lcc-sboms")
        temp_dir.mkdir(exist_ok=True)

        extension_map = {
            "json": ".json",
            "xml": ".xml",
            "yaml": ".yaml",
            "tag-value": ".spdx",
        }
        ext = extension_map.get(output_format, ".json")
        output_path = temp_dir / f"{scan_id}-{format}{ext}"

        if format == "cyclonedx":
            generator = CycloneDXGenerator()

            # Convert scan to ScanResult format
            from lcc.models import ComponentResult, ScanResult, Status
            from datetime import datetime

            # Create ScanResult from scan data
            scan_result = ScanResult(
                components=scan.get("components", []),
                component_results=[
                    ComponentResult(
                        component=comp,
                        status=Status.PASS,  # Default, should come from policy eval
                        licenses=comp.get("licenses", []),
                        violations=[],
                        warnings=[],
                    )
                    for comp in scan.get("components", [])
                ],
                scan_id=scan_id,
                timestamp=datetime.fromisoformat(scan["generated_at"]),
            )

            bom = generator.generate(
                scan_result=scan_result,
                project_name=project_name,
                project_version=project_version,
                author=author,
                supplier=supplier,
            )
            generator.save(bom, output_path, format=output_format)

        else:  # spdx
            generator = SPDXGenerator()

            # Convert scan to ScanResult format
            from lcc.models import ComponentResult, ScanResult, Status
            from datetime import datetime

            scan_result = ScanResult(
                components=scan.get("components", []),
                component_results=[
                    ComponentResult(
                        component=comp,
                        status=Status.PASS,
                        licenses=comp.get("licenses", []),
                        violations=[],
                        warnings=[],
                    )
                    for comp in scan.get("components", [])
                ],
                scan_id=scan_id,
                timestamp=datetime.fromisoformat(scan["generated_at"]),
            )

            document = generator.generate(
                scan_result=scan_result,
                project_name=project_name,
                project_version=project_version,
                creator=author,
            )
            generator.save(document, output_path, format=output_format)

        # Return file
        media_type_map = {
            "json": "application/json",
            "xml": "application/xml",
            "yaml": "application/x-yaml",
            "tag-value": "text/plain",
        }
        media_type = media_type_map.get(output_format, "application/octet-stream")

        return FileResponse(
            path=str(output_path),
            media_type=media_type,
            filename=f"{scan_id}-{format}{ext}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate SBOM: {str(e)}"
        )


@router.post("/generate", response_model=SBOMResponse)
async def generate_sbom(
    request: SBOMGenerateRequest,
    repo: ScanRepository = Depends(get_repository),
    current_user: User = Depends(get_current_active_user),
) -> SBOMResponse:
    """
    Generate SBOM for a scan (async, returns download URL).

    This endpoint generates an SBOM and returns a URL to download it.
    Use the GET endpoint for direct download.
    """
    # Verify scan exists
    scan = repo.get_scan(request.scan_id)
    if not scan:
        raise HTTPException(
            status_code=404, detail=f"Scan {request.scan_id} not found"
        )

    # Build download URL
    download_url = (
        f"/sbom/scans/{request.scan_id}"
        f"?format={request.format}"
        f"&output_format={request.output_format}"
    )

    if request.project_name:
        download_url += f"&project_name={request.project_name}"
    if request.project_version:
        download_url += f"&project_version={request.project_version}"
    if request.author:
        download_url += f"&author={request.author}"
    if request.supplier:
        download_url += f"&supplier={request.supplier}"

    return SBOMResponse(
        scan_id=request.scan_id,
        format=request.format,
        output_format=request.output_format,
        download_url=download_url,
    )
