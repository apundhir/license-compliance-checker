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
Background tasks for the LCC worker with progress tracking.
"""
import asyncio
import logging
import shutil
import tempfile
import traceback
from pathlib import Path
from typing import Any

from redis.asyncio import from_url as redis_from_url

from lcc.cache import Cache
from lcc.config import load_config
from lcc.database.models import Component
from lcc.database.repository import ScanRepository
from lcc.database.session import AsyncSessionLocal
from lcc.factory import build_detectors, build_resolvers
from lcc.scanner import Scanner
from lcc.utils.git import clone_github_repo
from lcc.worker.progress import ScanStage
from lcc.worker.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

async def run_scan_task(ctx: dict[str, Any], scan_id: str, repo_url: str | None = None, path: str | None = None, check_vulnerabilities: bool = False) -> None:
    """
    Execute a license scan in the background with real-time progress tracking.
    """
    config = load_config()
    cache = Cache(config)

    # Connect to Redis for progress tracking
    redis = await redis_from_url(config.redis_url)
    progress = ProgressTracker(redis, scan_id)

    try:
        await progress.update(
            ScanStage.INITIALIZING,
            "Initializing scan..."
        )

        # Build scanner
        detectors = build_detectors(config)
        resolvers = build_resolvers(config, cache)
        scanner = Scanner(detectors, resolvers, config)

        async with AsyncSessionLocal() as session:
            repo = ScanRepository(session)
            scan = await repo.get_scan(scan_id)

            if not scan:
                logger.error(f"Scan {scan_id} not found in database.")
                await progress.update(
                    ScanStage.FAILED,
                    "Scan not found in database",
                    error="Scan record not found"
                )
                return

            # Update status to running
            await repo.update_scan(scan_id, status="running")

            temp_dir = None
            project_path = None

            try:
                # Clone repository if needed
                if repo_url:
                    await progress.update(
                        ScanStage.CLONING,
                        f"Cloning repository from {repo_url}..."
                    )
                    temp_dir = tempfile.mkdtemp(prefix="lcc_repo_")

                    # Run blocking git clone in executor
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None,
                        clone_github_repo,
                        repo_url,
                        Path(temp_dir)
                    )
                    project_path = Path(temp_dir)

                    logger.debug(f"Scanned repo_url: {repo_url}")
                    logger.debug(f"Project path: {project_path}")
                    if project_path.exists():
                        logger.debug(f"Project path {project_path} exists. Starting nested scan.")
                    else:
                        logger.debug(f"Project path {project_path} does not exist!")
                elif path:
                    project_path = Path(path)
                    if not project_path.exists():
                        raise FileNotFoundError(f"Path {path} does not exist")
                else:
                    raise ValueError("Neither repo_url nor path provided")

                # Detect components
                await progress.update(
                    ScanStage.DETECTING_COMPONENTS,
                    "Detecting components in project..."
                )

                # Run synchronous scan in a thread pool to avoid blocking the async worker
                loop = asyncio.get_running_loop()

                # Use functools.partial to pass keyword arguments
                from functools import partial
                scan_func = partial(scanner.scan, project_root=project_path, check_vulnerabilities=check_vulnerabilities)
                report = await loop.run_in_executor(None, scan_func)

                # Update progress with component count
                components_found = len(report.findings)
                await progress.update(
                    ScanStage.RESOLVING_LICENSES,
                    f"Resolving licenses for {components_found} components...",
                    components_found=components_found
                )

                # Process results - convert report findings to Component models
                components = []
                components_resolved = 0

                for finding in report.findings:
                    comp = Component(
                        scan_id=scan_id,
                        type=finding.component.type.value,
                        name=finding.component.name,
                        version=finding.component.version,
                        license_expression=finding.resolved_license,
                        license_confidence=finding.confidence,
                        metadata_=finding.component.metadata,
                        evidence=[{
                            "source": e.source,
                            "license": e.license_expression,
                            "confidence": e.confidence
                        } for e in finding.evidences]
                    )
                    components.append(comp)
                    components_resolved += 1

                    # Update progress periodically (every 10 components)
                    if components_resolved % 10 == 0:
                        await progress.update(
                            ScanStage.RESOLVING_LICENSES,
                            f"Resolved {components_resolved}/{components_found} components...",
                            components_found=components_found,
                            components_resolved=components_resolved
                        )

                # Evaluating policy (if applicable)
                await progress.update(
                    ScanStage.EVALUATING_POLICY,
                    "Evaluating compliance policy...",
                    components_found=components_found,
                    components_resolved=components_resolved
                )

                # Generate report
                await progress.update(
                    ScanStage.GENERATING_REPORT,
                    "Generating compliance report...",
                    components_found=components_found,
                    components_resolved=components_resolved
                )

                # Simplified report storage
                report_dict = {
                    "findings": [
                        {
                            "component": {
                                "name": f.component.name,
                                "version": f.component.version,
                                "type": f.component.type.value
                            },
                            "resolved_license": f.resolved_license,
                            "confidence": f.confidence
                        } for f in report.findings
                    ],
                    "summary": {
                        "component_count": report.summary.component_count,
                        "violations": report.summary.violations
                    }
                }

                scan.components = components
                scan.status = "complete"
                scan.components_count = report.summary.component_count
                scan.violations_count = report.summary.violations

                # Check for vulnerabilities in summary context
                vuln_count = report.summary.context.get("vulnerabilities", 0)
                # Store in context if model doesn't have a direct field (assuming it does or we use context)
                scan.context = scan.context or {}
                scan.context["vulnerabilities"] = vuln_count

                scan.report = report_dict
                scan.duration_seconds = report.summary.duration_seconds

                await session.commit()

                # Mark as complete
                await progress.update(
                    ScanStage.COMPLETE,
                    f"Scan completed successfully! Found {components_found} components.",
                    components_found=components_found,
                    components_resolved=components_resolved
                )

            except Exception as e:
                traceback.print_exc()
                error_msg = str(e)
                await repo.update_scan(scan_id, status="failed", report={"error": error_msg})
                await progress.update(
                    ScanStage.FAILED,
                    f"Scan failed: {error_msg}",
                    error=error_msg
                )
            finally:
                if temp_dir and Path(temp_dir).exists():
                    shutil.rmtree(temp_dir)

    finally:
        # Close Redis connection
        await redis.aclose()
