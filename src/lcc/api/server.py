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

"""FastAPI application exposing the License Compliance Checker services."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import yaml
from arq import create_pool
from arq.connections import ArqRedis
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from redis.asyncio import from_url as redis_from_url
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from lcc.api.auth_routes import create_auth_router
from lcc.api.regulatory_routes import router as regulatory_router
from lcc.api.warnings import WarningsSummary
from lcc.auth.core import User, UserRole, get_current_active_user, require_role
from lcc.auth.repository import UserRepository
from lcc.config import load_config
from lcc.database.models import Scan
from lcc.database.repository import ScanRepository
from lcc.database.session import get_db
from lcc.policy import PolicyError, PolicyManager
from lcc.worker.progress import ScanProgress
from lcc.worker.progress_tracker import get_scan_progress
from lcc.worker.worker import WorkerSettings


# DTOs
class ScanRequest(BaseModel):
    path: str | None = Field(None, description="Filesystem path to analyse")
    repo_url: str | None = Field(None, description="GitHub repository URL to clone and scan")
    project_name: str | None = Field(None, description="Custom project name (defaults to repo name)")
    policy: str | None = Field(None, description="Policy name to enforce")
    context: str | None = Field(None, description="Policy evaluation context")
    recursive: bool = Field(False, description="Reserved for future use")
    exclude: list[str] = Field(default_factory=list, description="Glob patterns to skip")
    check_vulnerabilities: bool = Field(False, description="Check for known vulnerabilities (OSV)")


class ScanSummaryDTO(BaseModel):
    id: str
    project: str
    status: str
    violations: int
    warnings: int
    generatedAt: datetime
    durationSeconds: float | None = 0.0
    reportUrl: str | None = None
    progress_percent: int | None = None
    current_stage: str | None = None


class ScanDetailDTO(BaseModel):
    summary: ScanSummaryDTO
    report: dict[str, object] | None = None


class DashboardSummaryDTO(BaseModel):
    totalProjects: int
    totalScans: int
    totalViolations: int
    totalWarnings: int
    highRiskProjects: int
    pendingScans: int
    licenseDistribution: list[dict[str, object]]
    trend: list[dict[str, object]]


class PolicySummaryDTO(BaseModel):
    name: str
    description: str
    status: str = "active"
    lastUpdated: str | None = None
    disclaimer: str | None = None


class PolicyDetailDTO(PolicySummaryDTO):
    contexts: list[dict[str, object]]


class PolicyCreateRequest(BaseModel):
    name: str = Field(..., description="Unique policy name (alphanumeric and hyphens)", pattern="^[a-zA-Z0-9-]+$")
    content: str = Field(..., description="Policy content in YAML or JSON format")
    format: str = Field("yaml", description="Content format: 'yaml' or 'json'")


class PolicyUpdateRequest(BaseModel):
    content: str = Field(..., description="Updated policy content in YAML or JSON format")
    format: str = Field("yaml", description="Content format: 'yaml' or 'json'")


# App Factory
def create_app(config_path: Path | None = None) -> FastAPI:
    if config_path is None:
        env_config = os.getenv("LCC_CONFIG_PATH")
        if env_config:
            config_path = Path(env_config)
    config = load_config(config_path)

    # Initialize legacy repositories (Auth) - still synchronous for now
    user_repository = UserRepository(config.database_path)
    policy_manager = PolicyManager(config)

    # Initialize rate limiter
    limiter = Limiter(key_func=get_remote_address)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: Create Redis pool
        app.state.redis = await create_pool(WorkerSettings.redis_settings)
        yield
        # Shutdown: Close Redis pool
        await app.state.redis.close()

    app = FastAPI(
        title="License Compliance Checker API",
        version="0.2.0",
        description="REST interface for orchestrating license scans and policy evaluations.",
        lifespan=lifespan
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    allowed_origins = os.getenv("LCC_ALLOWED_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Dependencies
    def get_repository(session: AsyncSession = Depends(get_db)) -> ScanRepository:
        return ScanRepository(session)

    def get_policy_manager() -> PolicyManager:
        return policy_manager

    def get_user_repository() -> UserRepository:
        return user_repository

    # Mount Auth
    auth_router = create_auth_router(user_repository)
    app.include_router(auth_router)

    # Mount Regulatory routes
    app.include_router(regulatory_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/dashboard", response_model=DashboardSummaryDTO)
    @limiter.limit("100/minute")
    async def dashboard(
        request: Request,
        repo: ScanRepository = Depends(get_repository),
        current_user: User = Depends(get_current_active_user)
    ) -> DashboardSummaryDTO:
        summary = await repo.get_dashboard_summary()
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

    @app.delete("/scans", status_code=204)
    async def delete_all_scans(
        repo: ScanRepository = Depends(get_repository),
        current_user: User = Depends(require_role(UserRole.ADMIN))
    ):
        """Delete all scans and associated data."""
        await repo.delete_all_scans()

        # Clear Redis progress keys
        redis = await redis_from_url(config.redis_url)
        keys = await redis.keys("scan:*")
        if keys:
            await redis.delete(*keys)
        await redis.close()

    @app.post("/admin/reset", status_code=204)
    async def reset_application(
        repo: ScanRepository = Depends(get_repository),
        current_user: User = Depends(require_role(UserRole.ADMIN))
    ):
        """Reset application state (delete all scans, clear cache)."""
        # Delete all scans
        await repo.delete_all_scans()

        # Clear Redis (cache and progress)
        redis = await redis_from_url(config.redis_url)
        await redis.flushdb()
        await redis.close()

    @app.get("/scans", response_model=list[ScanSummaryDTO])
    @limiter.limit("100/minute")
    async def get_scans(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        current_user: User = Depends(get_current_active_user),
        scan_repo: ScanRepository = Depends(get_repository)
    ) -> list[ScanSummaryDTO]:
        scans = await scan_repo.list_scans(offset=skip, limit=limit)

        # Enrich running scans with progress data
        redis = await redis_from_url(config.redis_url)
        results = []

        for s in scans:
            dto = ScanSummaryDTO(
                id=s.id,
                project=s.project_name,
                status=s.status,
                violations=s.violations_count,
                warnings=s.warnings_count,
                generatedAt=s.created_at,
                durationSeconds=s.duration_seconds,
                reportUrl=f"/scans/{s.id}",
            )

            if s.status.lower() in ("running", "queued"):
                try:
                    progress_data = await redis.get(f"scan:{s.id}:progress")
                    if progress_data:
                        progress = ScanProgress.model_validate_json(progress_data)
                        dto.progress_percent = progress.progress_percent
                        dto.current_stage = progress.current_stage.value if progress.current_stage else None
                except Exception:
                    # Log the exception if needed, but don't fail the request
                    pass

            results.append(dto)

        await redis.close()
        return results

    @app.post("/scans", response_model=ScanSummaryDTO, status_code=201)
    async def create_scan(
        request: Request,
        payload: ScanRequest,
        repo: ScanRepository = Depends(get_repository),
        current_user: User = Depends(get_current_active_user)
    ) -> ScanSummaryDTO:
        if not payload.path and not payload.repo_url:
            raise HTTPException(status_code=400, detail="Either 'path' or 'repo_url' must be provided")
        if payload.path and payload.repo_url:
            raise HTTPException(status_code=400, detail="Provide only one of 'path' or 'repo_url'")

        # Create Scan record
        project_name = payload.project_name or (payload.repo_url.split("/")[-1].replace(".git", "") if payload.repo_url else Path(payload.path).name)
        scan = Scan(
            project_name=project_name,
            status="queued",
            context={"policy": payload.policy, "context": payload.context}
        )
        created_scan = await repo.create_scan(scan)

        # Enqueue Job
        redis: ArqRedis = request.app.state.redis
        await redis.enqueue_job("run_scan_task",
            scan_id=created_scan.id,
            repo_url=payload.repo_url,
            path=payload.path,
            check_vulnerabilities=payload.check_vulnerabilities
        )

        return ScanSummaryDTO(
            id=created_scan.id,
            project=created_scan.project_name,
            status=created_scan.status,
            violations=0,
            warnings=0,
            generatedAt=created_scan.created_at,
            durationSeconds=0.0,
            reportUrl=f"/scans/{created_scan.id}"
        )

    @app.get("/scans/{scan_id}", response_model=ScanDetailDTO)
    @limiter.limit("100/minute")
    async def get_scan(
        request: Request,
        scan_id: str,
        repo: ScanRepository = Depends(get_repository),
        current_user: User = Depends(get_current_active_user)
    ) -> ScanDetailDTO:
        scan = await repo.get_scan(scan_id)
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")

        summary = ScanSummaryDTO(
            id=scan.id,
            project=scan.project_name,
            status=scan.status,
            violations=scan.violations_count,
            warnings=scan.warnings_count,
            generatedAt=scan.created_at,
            durationSeconds=scan.duration_seconds,
            reportUrl=f"/scans/{scan.id}",
        )
        return ScanDetailDTO(summary=summary, report=scan.report)

    @app.get("/scans/{scan_id}/attribution")
    @limiter.limit("50/minute")
    async def get_scan_attribution(
        request: Request,
        scan_id: str,
        repo: ScanRepository = Depends(get_repository),
        current_user: User = Depends(get_current_active_user)
    ):
        """Download Attribution/NOTICE file for a scan."""
        from fastapi import Response

        from lcc.reporting.attribution import AttributionReporter

        scan = await repo.get_scan(scan_id)
        if not scan or not scan.report:
            raise HTTPException(status_code=404, detail="Scan or report not found")

        # Reconstruct ScanReport from stored JSON
        # Note: Ideally scan.report is a dict matching schema.
        try:
            # Basic reconstruction without full validation for speed
            report_data = scan.report
            for _item in report_data.get("findings", []):
                # ... (Simplified reconstruction or reuse deserialize utility if available)
                # For MVP, we pass the dict if deserializer not easily available,
                # but better to use lcc.cli.main._deserialize_report logic if refactored.
                # Here we will attempt to rely on the stored report structure matching
                # what AttributionReporter expects, or quickly deserialize essential fields.
                pass

            # Use CLI helper to deserialize properly
            from lcc.cli.main import _deserialize_report
            report = _deserialize_report(report_data)

            reporter = AttributionReporter()
            text = reporter.render(report)

            return Response(content=text, media_type="text/plain")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate attribution: {str(e)}")

    @app.get("/scans/{scan_id}/progress", response_model=Optional[ScanProgress])
    @limiter.limit("100/minute")
    async def get_scan_progress_endpoint(
        request: Request,
        scan_id: str,
        current_user: User = Depends(get_current_active_user)
    ) -> ScanProgress | None:
        """Get real-time progress for a running scan."""
        redis = await redis_from_url(config.redis_url)
        try:
            progress = await get_scan_progress(redis, scan_id)
            return progress
        finally:
            await redis.aclose()

    # ... (Policy routes remain largely unchanged, just need to be async compatible if needed,
    # but they use PolicyManager which is sync. FastAPI handles sync routes in threadpool, so it's fine.)

    @app.get("/policies", response_model=list[PolicySummaryDTO])
    @limiter.limit("100/minute")
    def list_policies(
        request: Request,
        manager: PolicyManager = Depends(get_policy_manager),
        current_user: User = Depends(get_current_active_user)
    ) -> list[PolicySummaryDTO]:
        summaries: list[PolicySummaryDTO] = []
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

    # ... (Include other policy routes similarly. For brevity, I'm including the list only,
    # but in a real refactor I'd include all. I will assume the user wants the full file replaced
    # so I should include them.)

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

    @app.post("/policies", response_model=PolicySummaryDTO, status_code=201)
    def create_policy(
        payload: PolicyCreateRequest,
        manager: PolicyManager = Depends(get_policy_manager),
        current_user: User = Depends(require_role(UserRole.ADMIN))
    ) -> PolicySummaryDTO:
        try:
            if payload.format.lower() == "json":
                policy_data = json.loads(payload.content)
            else:
                policy_data = yaml.safe_load(payload.content)

            if policy_data.get("name") != payload.name:
                raise HTTPException(status_code=400, detail="Policy name mismatch")

            existing_policies = manager.list_policies()
            if payload.name in existing_policies:
                raise HTTPException(status_code=409, detail="Policy already exists")

            manager.validate_policy(policy_data)
            policy_path = manager.policy_dir / f"{payload.name}.yaml"
            policy_path.write_text(yaml.dump(policy_data, sort_keys=False))

            policy = manager.load_policy(payload.name)
            return PolicySummaryDTO(
                name=policy.name,
                description=str(policy.data.get("description", "")),
                status=str(policy.data.get("status", "active")),
                lastUpdated=datetime.now(UTC).isoformat(),
                disclaimer=str(policy.data.get("disclaimer", "")) or None,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.put("/policies/{policy_name}", response_model=PolicySummaryDTO)
    def update_policy(
        policy_name: str,
        payload: PolicyUpdateRequest,
        manager: PolicyManager = Depends(get_policy_manager),
        current_user: User = Depends(require_role(UserRole.ADMIN))
    ) -> PolicySummaryDTO:
        try:
            existing_policies = manager.list_policies()
            if policy_name not in existing_policies:
                raise HTTPException(status_code=404, detail="Policy not found")

            if payload.format.lower() == "json":
                policy_data = json.loads(payload.content)
            else:
                policy_data = yaml.safe_load(payload.content)

            manager.validate_policy(policy_data)
            policy_path = manager.policy_dir / f"{policy_name}.yaml"
            policy_path.write_text(yaml.dump(policy_data, sort_keys=False))

            policy = manager.load_policy(policy_name)
            return PolicySummaryDTO(
                name=policy.name,
                description=str(policy.data.get("description", "")),
                status=str(policy.data.get("status", "active")),
                lastUpdated=datetime.now(UTC).isoformat(),
                disclaimer=str(policy.data.get("disclaimer", "")) or None,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/scans/{scan_id}/warnings", response_model=WarningsSummary)
    @limiter.limit("100/minute")
    async def get_scan_warnings(
        request: Request,
        scan_id: str,
        repo: ScanRepository = Depends(get_repository),
        manager: PolicyManager = Depends(get_policy_manager),
        current_user: User = Depends(get_current_active_user)
    ) -> WarningsSummary:
        scan = await repo.get_scan(scan_id)
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")

        # For MVP, returning empty summary as the logic requires re-evaluating policy
        # or extracting from report if stored.
        return WarningsSummary(total_warnings=0, warnings=[])

    return app
