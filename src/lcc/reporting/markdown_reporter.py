"""Markdown report renderer."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from lcc.models import ComponentFinding, ScanReport


class MarkdownReporter:
    def __init__(self, include_evidence: bool = False, summary_only: bool = False, group_by: str = "license") -> None:
        self.include_evidence = include_evidence
        self.summary_only = summary_only
        self.group_by = group_by

    def render(self, report: ScanReport) -> str:
        lines: List[str] = []
        summary = report.summary
        lines.append(f"# License Compliance Report")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Components scanned: {summary.component_count}")
        lines.append(f"- Violations: {summary.violations}")
        lines.append(f"- Duration: {summary.duration_seconds:.2f}s")
        if summary.context.get("policy"):
            policy = summary.context["policy"]
            lines.append(f"- Active policy: {policy.get('name')}")
        lines.append("")

        if self.summary_only:
            return "\n".join(lines)

        grouped: Dict[str, List[ComponentFinding]] = defaultdict(list)
        if self.group_by == "component":
            for finding in report.findings:
                grouped[finding.component.name].append(finding)
        else:
            for finding in report.findings:
                license_name = finding.resolved_license or "UNKNOWN"
                grouped[license_name].append(finding)

        lines.append("## Findings")
        lines.append("")
        for key, findings in grouped.items():
            if self.group_by == "component":
                lines.append(f"### Component: {key}")
            else:
                lines.append(f"### License: {key}")
            lines.append("")
            for finding in findings:
                status = finding.component.metadata.get("policy", {}).get("status", "pass")
                assumptions = finding.component.metadata.get("assumptions", []) if isinstance(finding.component.metadata, dict) else []
                assumed_version = next((item.get("value") for item in assumptions if item.get("type") == "version"), None)
                component_label = f"`{finding.component.name}` @ `{finding.component.version}`"
                if assumed_version:
                    component_label += f" (~`{assumed_version}` assumed)"
                license_text = finding.resolved_license or "UNKNOWN"
                if assumed_version:
                    license_text += " (assumed latest)"
                lines.append(
                    f"- {component_label} — resolved: `{license_text}` (confidence {finding.confidence:.2f}, status {status})"
                )
                if self.include_evidence and finding.evidences:
                    for evidence in finding.evidences:
                        lines.append(
                            f"  - Evidence from {evidence.source}: {evidence.license_expression} (confidence {evidence.confidence:.2f})"
                        )
            lines.append("")

        if report.errors:
            lines.append("## Errors")
            lines.append("")
            for error in report.errors:
                lines.append(f"- {error}")

        return "\n".join(lines)
