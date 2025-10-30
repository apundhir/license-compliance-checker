"""
Console reporter leveraging Rich for formatted output.
"""

from __future__ import annotations

from collections import defaultdict

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from lcc.models import ScanReport


class ConsoleReporter:
    """
    Renders scan results to the terminal with color coding.
    """

    def __init__(self, console: Console | None = None, threshold: float = 0.0, quiet: bool = False) -> None:
        self.console = console or Console()
        self.threshold = threshold
        self.quiet = quiet

    def write(self, report: ScanReport) -> None:
        if not self.quiet:
            table = Table(title="License Compliance Findings", expand=True)
            table.add_column("Status")
            table.add_column("Component")
            table.add_column("License")
            table.add_column("Confidence", justify="right")
            table.add_column("Project Root")

            for finding in report.findings:
                component = finding.component
                status, style = self._classify_finding(finding)
                license_text = self._format_license(finding)
                project_root = component.metadata.get("project_root", "-")
                table.add_row(
                    f"[{style}]{status}[/]",
                    self._format_component_label(component),
                    license_text,
                    f"{finding.confidence:.2f}",
                    project_root,
                )

            self.console.print(table)
            self._render_license_tree(report)

        summary_line = (
            f"Scanned {report.summary.component_count} components in "
            f"{report.summary.duration_seconds:.2f}s"
        )
        if report.summary.violations:
            summary_line += f" • [red]{report.summary.violations} potential violations[/red]"
        else:
            summary_line += " • [green]No violations detected[/green]"
        self.console.print(summary_line)

    def _classify_finding(self, finding) -> tuple[str, str]:
        if not finding.resolved_license:
            return "UNRESOLVED", "red"
        if finding.confidence >= self.threshold:
            return "PASS", "green"
        if finding.confidence >= self.threshold * 0.8:
            return "WARN", "yellow"
        return "FAIL", "red"

    def _render_license_tree(self, report: ScanReport) -> None:
        if len(report.findings) > 50:
            return
        grouped = defaultdict(list)
        for finding in report.findings:
            key = finding.resolved_license or "UNRESOLVED"
            grouped[key].append(finding)

        tree = Tree("Licenses")
        for license_name, findings in sorted(grouped.items(), key=lambda item: item[0]):
            branch = tree.add(f"{license_name} ({len(findings)})")
            for finding in findings:
                component = finding.component
                label = self._format_component_label(component)
                branch.add(f"{label} [confidence {finding.confidence:.2f}]")
        self.console.print(tree)

    def _format_component_label(self, component):
        assumptions = component.metadata.get("assumptions", []) if isinstance(component.metadata, dict) else []
        assumed_version = next((item.get("value") for item in assumptions if item.get("type") == "version"), None)
        label = f"{component.type.value}:{component.name}@{component.version}"
        if assumed_version:
            label += f" (~{assumed_version} assumed)"
        return label

    def _format_license(self, finding) -> str:
        license_text = finding.resolved_license or "Unknown"
        assumptions = finding.component.metadata.get("assumptions", []) if isinstance(finding.component.metadata, dict) else []
        assumed_version = next((item.get("value") for item in assumptions if item.get("type") == "version"), None)
        if assumed_version:
            license_text += " (assumed latest)"
        return license_text
