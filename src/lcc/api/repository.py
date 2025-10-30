"\"\"\"Persistence layer for the LCC REST API.\"\"\""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional


class ScanRepository:
    """Simple SQLite-backed repository for scan metadata and reports."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS scans (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    status TEXT NOT NULL,
                    violations INTEGER NOT NULL,
                    generated_at TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    report_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL
                );
                """
            )

    def record_scan(
        self,
        *,
        scan_id: str,
        project: str,
        status: str,
        violations: int,
        generated_at: datetime,
        duration_seconds: float,
        summary: Dict[str, object],
        report: Dict[str, object],
    ) -> None:
        payload = {
            "id": scan_id,
            "project": project,
            "status": status,
            "violations": violations,
            "generated_at": generated_at.astimezone(timezone.utc).isoformat(),
            "duration_seconds": duration_seconds,
            "report_json": json.dumps(report),
            "summary_json": json.dumps(summary),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scans (
                    id, project, status, violations, generated_at, duration_seconds, report_json, summary_json
                ) VALUES (
                    :id, :project, :status, :violations, :generated_at, :duration_seconds, :report_json, :summary_json
                );
                """,
                payload,
            )

    def list_scans(self, *, limit: int = 50) -> List[Dict[str, object]]:
        query = """
            SELECT id, project, status, violations, generated_at, duration_seconds, summary_json
            FROM scans
            ORDER BY datetime(generated_at) DESC
            LIMIT ?;
        """
        with self._connect() as conn:
            rows = conn.execute(query, (limit,)).fetchall()
        results: List[Dict[str, object]] = []
        for row in rows:
            summary = json.loads(row["summary_json"])
            results.append(
                {
                    "id": row["id"],
                    "project": row["project"],
                    "status": row["status"],
                    "violations": row["violations"],
                    "generatedAt": row["generated_at"],
                    "durationSeconds": row["duration_seconds"],
                    "summary": summary,
                }
            )
        return results

    def get_scan(self, scan_id: str) -> Optional[Dict[str, object]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, project, status, violations, generated_at, duration_seconds, report_json, summary_json
                FROM scans
                WHERE id = ?;
                """,
                (scan_id,),
            ).fetchone()
        if row is None:
            return None
        summary = json.loads(row["summary_json"])
        report = json.loads(row["report_json"])
        return {
            "id": row["id"],
            "project": row["project"],
            "status": row["status"],
            "violations": row["violations"],
            "generatedAt": row["generated_at"],
            "durationSeconds": row["duration_seconds"],
            "summary": summary,
            "report": report,
        }

    def get_dashboard_summary(self) -> Dict[str, object]:
        with self._connect() as conn:
            aggregates = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_scans,
                    COUNT(DISTINCT project) AS unique_projects,
                    SUM(CASE WHEN status = 'violation' THEN 1 ELSE 0 END) AS violation_runs,
                    SUM(CASE WHEN status = 'warning' THEN 1 ELSE 0 END) AS warning_runs,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running_runs
                FROM scans;
                """
            ).fetchone()

            trend_rows = conn.execute(
                """
                SELECT substr(generated_at, 1, 7) AS month, SUM(violations) AS violations
                FROM scans
                GROUP BY month
                ORDER BY month DESC
                LIMIT 6;
                """
            ).fetchall()

            latest_rows = conn.execute(
                """
                SELECT project, status, generated_at, summary_json
                FROM scans
                ORDER BY project, datetime(generated_at) DESC;
                """
            ).fetchall()

        latest_per_project: Dict[str, sqlite3.Row] = {}
        for row in latest_rows:
            if row["project"] not in latest_per_project:
                latest_per_project[row["project"]] = row

        high_risk_projects = sum(1 for row in latest_per_project.values() if row["status"] == "violation")
        running_projects = sum(1 for row in latest_per_project.values() if row["status"] == "running")

        license_distribution: Dict[str, int] = {}
        total_violation_count = 0
        total_warning_count = 0
        for row in latest_per_project.values():
            summary = json.loads(row["summary_json"])
            total_violation_count += int(summary.get("violations", 0))
            total_warning_count += int(summary.get("warnings", 0))
            for item in summary.get("licenseDistribution", []):
                license_distribution[item["license"]] = license_distribution.get(item["license"], 0) + item["count"]

        trend = [
            {"month": row["month"], "violations": row["violations"]}
            for row in reversed(trend_rows)
            if row["month"] is not None
        ]
        distribution = [
            {"license": license, "count": count}
            for license, count in sorted(license_distribution.items(), key=lambda item: item[1], reverse=True)
        ]

        return {
            "totalScans": aggregates["total_scans"] or 0,
            "totalProjects": aggregates["unique_projects"] or 0,
            "totalViolations": total_violation_count,
            "totalWarnings": total_warning_count,
            "pendingScans": running_projects,
            "highRiskProjects": high_risk_projects,
            "licenseDistribution": distribution,
            "trend": trend,
        }
