"""HTML report renderer."""

from __future__ import annotations

from collections import defaultdict
from html import escape
from typing import Dict, List, Optional

from lcc.models import ComponentFinding, ScanReport


class HTMLReporter:
    def __init__(
        self,
        include_evidence: bool = False,
        summary_only: bool = False,
        group_by: str = "license",
        comparison: Optional[dict] = None,
    ) -> None:
        self.include_evidence = include_evidence
        self.summary_only = summary_only
        self.group_by = group_by
        self.comparison = comparison or {}

    def render(self, report: ScanReport) -> str:
        summary = report.summary
        rows = []
        rows.append("<h1>License Compliance Report</h1>")
        rows.append("<section>")
        rows.append("<h2>Summary</h2>")
        rows.append("<ul>")
        rows.append(f"<li>Components scanned: {summary.component_count}</li>")
        rows.append(f"<li>Violations: {summary.violations}</li>")
        rows.append(f"<li>Duration: {summary.duration_seconds:.2f}s</li>")
        if summary.context.get("policy"):
            policy = summary.context["policy"]
            rows.append(f"<li>Active policy: {escape(str(policy.get('name')))}</li>")
        if self.comparison:
            delta = self.comparison.get("component_delta")
            rows.append(f"<li>Component delta vs comparison: {delta}</li>")
        rows.append("</ul>")
        rows.append("</section>")

        if self.summary_only:
            return "".join(rows)

        grouped: Dict[str, List[ComponentFinding]] = defaultdict(list)
        if self.group_by == "component":
            for finding in report.findings:
                grouped[finding.component.name].append(finding)
        else:
            for finding in report.findings:
                license_name = finding.resolved_license or "UNKNOWN"
                grouped[license_name].append(finding)

        rows.append("<section>")
        rows.append("<h2>Findings</h2>")
        for key, findings in grouped.items():
            title = "Component" if self.group_by == "component" else "License"
            rows.append(f"<h3>{title}: {escape(key)}</h3>")
            rows.append("<table>")
            rows.append("<thead><tr><th>Component</th><th>License</th><th>Confidence</th><th>Status</th></tr></thead><tbody>")
            for finding in findings:
                status = finding.component.metadata.get("policy", {}).get("status", "pass")
                assumptions = finding.component.metadata.get("assumptions", []) if isinstance(finding.component.metadata, dict) else []
                assumed_version = next((item.get("value") for item in assumptions if item.get("type") == "version"), None)
                component_label = f"{finding.component.name}@{finding.component.version}"
                if assumed_version:
                    component_label += f" (~{assumed_version} assumed)"
                license_text = finding.resolved_license or "UNKNOWN"
                if assumed_version:
                    license_text += " (assumed latest)"
                rows.append(
                    "<tr>"
                    f"<td>{escape(component_label)}</td>"
                    f"<td>{escape(license_text)}</td>"
                    f"<td>{finding.confidence:.2f}</td>"
                    f"<td>{escape(status)}</td>"
                    "</tr>"
                )
                if self.include_evidence and finding.evidences:
                    rows.append("<tr><td colspan='4'><ul>")
                    for evidence in finding.evidences:
                        rows.append(
                            f"<li>{escape(evidence.source)} – {escape(evidence.license_expression)} "
                            f"(confidence {evidence.confidence:.2f})</li>"
                        )
                    rows.append("</ul></td></tr>")
            rows.append("</tbody></table>")
        rows.append("</section>")

        if report.errors:
            rows.append("<section><h2>Errors</h2><ul>")
            for error in report.errors:
                rows.append(f"<li>{escape(error)}</li>")
            rows.append("</ul></section>")

        return "".join(rows)
