"\"\"\"FastAPI application exposing the License Compliance Checker services.\"\"\""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from lcc.api.repository import ScanRepository
from lcc.api.auth_routes import create_auth_router
from lcc.auth.core import User, UserRole, get_current_active_user, require_role
from lcc.auth.repository import UserRepository
from lcc.cache import Cache
from lcc.config import load_config
from lcc.factory import build_detectors, build_resolvers
from lcc.models import ComponentFinding, ScanReport
from lcc.policy import PolicyError, PolicyManager, evaluate_policy
from lcc.reporting.json_reporter import JSONReporter
from lcc.scanner import Scanner


class ScanRequest(BaseModel):
    path: Optional[str] = Field(None, description="Filesystem path to analyse")
    repo_url: Optional[str] = Field(None, description="GitHub repository URL to clone and scan")
    project_name: Optional[str] = Field(None, description="Custom project name (defaults to repo name)")
    policy: Optional[str] = Field(None, description="Policy name to enforce")
    context: Optional[str] = Field(None, description="Policy evaluation context")
    recursive: bool = Field(False, description="Reserved for future use")
    exclude: List[str] = Field(default_factory=list, description="Glob patterns to skip")


class ScanSummaryDTO(BaseModel):
    id: str
    project: str
    status: str
    violations: int
    warnings: int
    generatedAt: datetime
    durationSeconds: float
    reportUrl: Optional[str] = None


class ScanDetailDTO(BaseModel):
    summary: ScanSummaryDTO
    report: Dict[str, object]


class DashboardSummaryDTO(BaseModel):
    totalProjects: int
    totalScans: int
    totalViolations: int
    totalWarnings: int
    highRiskProjects: int
    pendingScans: int
    licenseDistribution: List[Dict[str, object]]
    trend: List[Dict[str, object]]


class PolicySummaryDTO(BaseModel):
    name: str
    description: str
    status: str = "active"
    lastUpdated: Optional[str] = None
    disclaimer: Optional[str] = None


class PolicyDetailDTO(PolicySummaryDTO):
    contexts: List[Dict[str, object]]


def clone_github_repo(repo_url: str, target_dir: Path) -> None:
    """Clone a GitHub repository to the target directory.

    Args:
        repo_url: GitHub repository URL (e.g., https://github.com/user/repo)
        target_dir: Path where the repository will be cloned

    Raises:
        HTTPException: If cloning fails or URL is invalid
    """
    # Validate GitHub URL
    github_pattern = r"^https?://(www\.)?github\.com/[\w-]+/[\w.-]+(\.git)?$"
    if not re.match(github_pattern, repo_url):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid GitHub URL format: {repo_url}. Expected: https://github.com/user/repo"
        )

    try:
        # Clone with depth=1 for faster cloning (shallow clone)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(target_dir)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            check=True
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail=f"Repository cloning timed out after 5 minutes. Repository may be too large."
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to clone repository: {error_msg}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while cloning repository: {str(e)}"
        )


def extract_project_name_from_url(repo_url: str) -> str:
    """Extract project name from GitHub URL.

    Args:
        repo_url: GitHub repository URL

    Returns:
        Project name extracted from URL
    """
    match = re.search(r"github\.com/([\w-]+)/([\w.-]+)", repo_url)
    if match:
        repo_name = match.group(2)
        # Remove .git suffix if present
        return repo_name.replace(".git", "")
    return "unknown-project"


def create_app(config_path: Optional[Path] = None) -> FastAPI:
    if config_path is None:
        env_config = os.getenv("LCC_CONFIG_PATH")
        if env_config:
            config_path = Path(env_config)
    config = load_config(config_path)
    cache = Cache(config)
    repository = ScanRepository(config.database_path)
    policy_manager = PolicyManager(config)
    user_repository = UserRepository(config.database_path)

    # Initialize rate limiter
    limiter = Limiter(key_func=get_remote_address)

    app = FastAPI(
        title="License Compliance Checker API",
        version="0.1.0",
        description="REST interface for orchestrating license scans and policy evaluations.",
    )

    # Add rate limiter to app state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Configure CORS - restrict in production
    allowed_origins = os.getenv("LCC_ALLOWED_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    def get_scanner() -> Scanner:
        return Scanner(build_detectors(), build_resolvers(config, cache), config)

    def get_repository() -> ScanRepository:
        return repository

    def get_policy_manager() -> PolicyManager:
        return policy_manager

    def get_user_repository() -> UserRepository:
        return user_repository

    # Mount authentication routes
    auth_router = create_auth_router(user_repository)
    app.include_router(auth_router)

    # Include SBOM routes
    # NOTE: SBOM CLI commands work perfectly. API routes disabled due to cyclonedx-python-lib v11.x API changes
    # The library restructured imports - needs update to match new API
    # Workaround: Use `lcc sbom` CLI commands which are fully functional
    # from lcc.api.sbom_routes import router as sbom_router, set_repository as set_sbom_repository
    # app.include_router(sbom_router)
    # set_sbom_repository(repository)

    @app.get("/health")
    def health() -> Dict[str, str]:
        """Health check endpoint (no auth required)."""
        return {"status": "ok"}

    @app.get("/dashboard", response_model=DashboardSummaryDTO)
    @limiter.limit("100/minute")
    def dashboard(
        request: Request,
        repo: ScanRepository = Depends(get_repository),
        current_user: User = Depends(get_current_active_user)
    ) -> DashboardSummaryDTO:
        """Get dashboard summary (requires authentication)."""
        summary = repo.get_dashboard_summary()
        return DashboardSummaryDTO(
            totalProjects=summary["totalProjects"],
            totalScans=summary["totalScans"],
            totalViolations=summary["totalViolations"],
            totalWarnings=summary["totalWarnings"],
            highRiskProjects=summary["highRiskProjects"],
            pendingScans=summary["pendingScans"],
            licenseDistribution=summary["licenseDistribution"],
            trend=summary["trend"],
        )

    @app.get("/scans", response_model=List[ScanSummaryDTO])
    @limiter.limit("100/minute")
    def list_scans(
        request: Request,
        repo: ScanRepository = Depends(get_repository),
        current_user: User = Depends(get_current_active_user)
    ) -> List[ScanSummaryDTO]:
        entries = repo.list_scans(limit=100)
        return [
            ScanSummaryDTO(
                id=entry["id"],
                project=entry["project"],
                status=entry["status"],
                violations=entry["violations"],
                warnings=entry["summary"].get("warnings", 0),
                generatedAt=datetime.fromisoformat(entry["generatedAt"]),
                durationSeconds=entry["durationSeconds"],
                reportUrl=f"/scans/{entry['id']}",
            )
            for entry in entries
        ]

    @app.get("/scans/{scan_id}", response_model=ScanDetailDTO)
    @limiter.limit("100/minute")
    def get_scan(
        request: Request,
        scan_id: str,
        repo: ScanRepository = Depends(get_repository),
        current_user: User = Depends(get_current_active_user)
    ) -> ScanDetailDTO:
        record = repo.get_scan(scan_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Scan not found")
        summary = ScanSummaryDTO(
            id=record["id"],
            project=record["project"],
            status=record["status"],
            violations=record["violations"],
            warnings=record["summary"].get("warnings", 0),
            generatedAt=datetime.fromisoformat(record["generatedAt"]),
            durationSeconds=record["durationSeconds"],
            reportUrl=f"/scans/{record['id']}",
        )
        return ScanDetailDTO(summary=summary, report=record["report"])

    @app.post("/scans", response_model=ScanSummaryDTO, status_code=201)
    def create_scan(
        payload: ScanRequest,
        current_user: User = Depends(get_current_active_user),
        scanner: Scanner = Depends(get_scanner),
        repo: ScanRepository = Depends(get_repository),
        manager: PolicyManager = Depends(get_policy_manager)
    ) -> ScanSummaryDTO:
        # Validate that either path or repo_url is provided
        if not payload.path and not payload.repo_url:
            raise HTTPException(
                status_code=400,
                detail="Either 'path' or 'repo_url' must be provided"
            )

        if payload.path and payload.repo_url:
            raise HTTPException(
                status_code=400,
                detail="Provide only one of 'path' or 'repo_url', not both"
            )

        temp_dir = None
        project_name = None

        try:
            # Handle GitHub repository URL
            if payload.repo_url:
                temp_dir = tempfile.mkdtemp(prefix="lcc_repo_")
                clone_github_repo(payload.repo_url, Path(temp_dir))
                project_path = Path(temp_dir)
                # Use custom project name or extract from URL
                project_name = payload.project_name or extract_project_name_from_url(payload.repo_url)
            else:
                # Handle local filesystem path
                project_path = Path(payload.path).expanduser().resolve()
                if not project_path.exists():
                    raise HTTPException(status_code=400, detail=f"Path does not exist: {project_path}")
                project_name = project_path.name

            report = scanner.scan(project_path)
            report.summary.context.setdefault("project_root", str(project_path))
            report.summary.context.setdefault("project", project_name)
            if payload.repo_url:
                report.summary.context.setdefault("repo_url", payload.repo_url)

            policy_payload: Optional[Dict[str, object]] = None
            policy_name: Optional[str] = None
            if payload.policy:
                try:
                    policy = manager.load_policy(payload.policy)
                    policy_payload = policy.data
                    policy_name = policy.name
                except PolicyError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc
            elif manager.active_policy():
                policy = manager.load_policy(manager.active_policy())
                policy_payload = policy.data
                policy_name = policy.name

            analysis = _analyse_report(
                report,
                project_name=project_name,
                policy_payload=policy_payload,
                context=payload.context or config.policy_context,
                unknown_license_treatment=config.unknown_license_treatment,
            )

            report_payload = _serialize_report(report, policy_name=policy_name, analysis=analysis)
            repo.record_scan(
                scan_id=analysis["id"],
                project=analysis["project"],
                status=analysis["status"],
                violations=analysis["violations"],
                generated_at=analysis["generated_at"],
                duration_seconds=analysis["duration_seconds"],
                summary=analysis["summary"],
                report=report_payload,
            )

            return ScanSummaryDTO(
                id=analysis["id"],
                project=analysis["project"],
                status=analysis["status"],
                violations=analysis["violations"],
                warnings=analysis["summary"].get("warnings", 0),
                generatedAt=analysis["generated_at"],
                durationSeconds=analysis["duration_seconds"],
                reportUrl=f"/scans/{analysis['id']}",
            )
        finally:
            # Clean up temporary directory if it was created
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    # Log but don't fail the request if cleanup fails
                    print(f"Warning: Failed to clean up temporary directory {temp_dir}: {e}")

    @app.get("/policies", response_model=List[PolicySummaryDTO])
    @limiter.limit("100/minute")
    def list_policies(
        request: Request,
        manager: PolicyManager = Depends(get_policy_manager),
        current_user: User = Depends(get_current_active_user)
    ) -> List[PolicySummaryDTO]:
        summaries: List[PolicySummaryDTO] = []
        for name in manager.list_policies():
            try:
                policy = manager.load_policy(name)
            except PolicyError:
                continue
            data = policy.data
            summaries.append(
                PolicySummaryDTO(
                    name=policy.name,
                    description=str(data.get("description", "")),
                    status=str(data.get("status", "active")),
                    lastUpdated=str(data.get("last_updated", "")) or None,
                    disclaimer=str(data.get("disclaimer", "")) or None,
                )
            )
        return sorted(summaries, key=lambda item: item.name)

    @app.get("/policies/{policy_name}", response_model=PolicyDetailDTO)
    @limiter.limit("100/minute")
    def get_policy(
        request: Request,
        policy_name: str,
        manager: PolicyManager = Depends(get_policy_manager),
        current_user: User = Depends(get_current_active_user)
    ) -> PolicyDetailDTO:
        try:
            policy = manager.load_policy(policy_name)
        except PolicyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        data = policy.data
        contexts = []
        for context_name, payload in (data.get("contexts") or {}).items():
            context_summary = {"name": context_name}
            if isinstance(payload, dict):
                context_summary.update(
                    {
                        "description": payload.get("description"),
                        "allow": payload.get("allow", []),
                        "review": payload.get("review", []),
                        "deny": payload.get("deny", []),
                        "dualLicensePreference": payload.get("dual_license_preference", "most_permissive"),
                        "overrides": payload.get("overrides", {}),
                    }
                )
            contexts.append(context_summary)

        return PolicyDetailDTO(
            name=policy.name,
            description=str(data.get("description", "")),
            status=str(data.get("status", "active")),
            lastUpdated=str(data.get("last_updated", "")) or None,
            disclaimer=str(data.get("disclaimer", "")) or None,
            contexts=contexts,
        )

    return app


def _collect_license_candidates(finding: ComponentFinding) -> List[str]:
    licenses: List[str] = []
    if finding.resolved_license:
        licenses.append(finding.resolved_license)
    metadata = finding.component.metadata if isinstance(finding.component.metadata, dict) else {}
    meta_licenses = metadata.get("licenses")
    if isinstance(meta_licenses, list):
        licenses.extend(str(item) for item in meta_licenses)
    licenses = [item for item in licenses if item]
    return licenses or ["UNKNOWN"]


def _analyse_report(
    report: ScanReport,
    *,
    project_name: str,
    policy_payload: Optional[Dict[str, object]] = None,
    context: Optional[str] = None,
    unknown_license_treatment: str = "violation",
) -> Dict[str, object]:
    scan_id = str(uuid.uuid4())
    generated_at = report.summary.generated_at.replace(tzinfo=timezone.utc)
    license_distribution: Dict[str, int] = {}
    violations = 0
    warnings = 0

    for finding in report.findings:
        licenses = _collect_license_candidates(finding)
        for expression in licenses:
            license_distribution[expression] = license_distribution.get(expression, 0) + 1

        status = "pass"
        if policy_payload:
            decision = evaluate_policy(
                policy_payload,
                licenses,
                context=context,
                component_name=finding.component.name,
            )
            status = decision.status
        elif finding.resolved_license in (None, "UNKNOWN"):
            # Use configured treatment for unknown licenses
            status = unknown_license_treatment

        if status == "violation":
            violations += 1
        elif status == "warning":
            warnings += 1

    overall_status = "pass"
    if violations > 0:
        overall_status = "violation"
    elif warnings > 0:
        overall_status = "warning"

    summary = {
        "componentCount": report.summary.component_count,
        "durationSeconds": report.summary.duration_seconds,
        "generatedAt": generated_at.isoformat(),
        "violations": violations,
        "warnings": warnings,
        "licenseDistribution": [
            {"license": license, "count": count}
            for license, count in sorted(license_distribution.items(), key=lambda item: item[1], reverse=True)
        ],
    }

    return {
        "id": scan_id,
        "project": project_name,
        "status": overall_status,
        "violations": violations,
        "summary": summary,
        "generated_at": generated_at,
        "duration_seconds": report.summary.duration_seconds,
    }


def _serialize_report(
    report: ScanReport,
    *,
    policy_name: Optional[str],
    analysis: Dict[str, object],
) -> Dict[str, object]:
    import json

    reporter = JSONReporter()
    raw = json.loads(reporter.render(report))
    raw.setdefault("meta", {})
    if policy_name:
        raw["meta"]["policy"] = {"name": policy_name}
    raw["meta"]["analysis"] = {
        "status": analysis["status"],
        "violations": analysis["violations"],
        "warnings": analysis["summary"].get("warnings", 0),
    }
    summary = raw.get("summary", {})
    summary["warnings"] = analysis["summary"].get("warnings", 0)
    summary["violations"] = analysis["violations"]
    summary["generatedAt"] = analysis["summary"]["generatedAt"]
    summary["componentCount"] = analysis["summary"]["componentCount"]
    summary["durationSeconds"] = analysis["summary"]["durationSeconds"]
    summary["licenseDistribution"] = analysis["summary"]["licenseDistribution"]
    raw["summary"] = summary
    return raw
