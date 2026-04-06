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
EU AI Act compliance report generator.

Produces structured JSON and self-contained HTML reports from
:class:`RegulatoryReport` data produced by :class:`EUAIActAssessor`.
Also provides a *compliance pack* generator that bundles all compliance
artefacts into a single directory for audit and record-keeping.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from lcc.models import ComponentFinding, ComponentType
from lcc.regulatory.eu_ai_act import get_training_data_info
from lcc.regulatory.frameworks import RegulatoryReport

# ===================================================================== #
#  RegulatoryReporter                                                    #
# ===================================================================== #


class RegulatoryReporter:
    """Generates EU AI Act compliance reports in JSON and HTML formats."""

    def __init__(self, report: RegulatoryReport) -> None:
        self.report = report

    # ------------------------------------------------------------------ #
    #  Serialisation helpers                                              #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        """Return report as dictionary."""
        return self.report.to_dict()

    # ------------------------------------------------------------------ #
    #  JSON output                                                        #
    # ------------------------------------------------------------------ #

    def to_json(self, output_path: Path) -> None:
        """Write structured JSON report.

        The file contains report metadata, a summary section with
        compliance statistics, and per-component assessment details
        including obligation status, evidence, gaps, and
        recommendations.

        Args:
            output_path: Destination file path for the JSON report.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        output_path.write_text(
            json.dumps(data, indent=2, sort_keys=False, default=str) + "\n",
            encoding="utf-8",
        )

    # ------------------------------------------------------------------ #
    #  HTML output                                                        #
    # ------------------------------------------------------------------ #

    def to_html(self, output_path: Path) -> None:
        """Write branded HTML compliance report.

        Produces a fully self-contained HTML file (inline CSS, no
        external dependencies) suitable for browser viewing or
        archiving.

        Args:
            output_path: Destination file path for the HTML report.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html = self._render_html()
        output_path.write_text(html, encoding="utf-8")

    # ------------------------------------------------------------------ #
    #  HTML rendering internals                                           #
    # ------------------------------------------------------------------ #

    def _render_html(self) -> str:
        """Build the complete HTML document string."""
        summary = self.report.summary
        assessments = self.report.assessments

        total = summary.get("total_ai_components", 0)
        compliant = summary.get("compliant", 0)
        partial = summary.get("partial", 0)
        non_compliant = summary.get("non_compliant", 0)
        compliance_pct = summary.get("compliance_percentage", 0.0)

        pct_color = _compliance_color(compliance_pct)

        parts: list[str] = []
        parts.append(_HTML_HEAD)

        # Header
        parts.append(
            "<header>"
            "<h1>EU AI Act Compliance Report</h1>"
            "<p class=\"subtitle\">License Compliance Checker</p>"
            f"<p class=\"generated\">Generated: {escape(self.report.generated_at)}</p>"
            "</header>"
        )

        # Executive summary
        parts.append("<section class=\"summary\">")
        parts.append("<h2>Executive Summary</h2>")
        parts.append("<div class=\"summary-grid\">")

        parts.append(
            "<div class=\"summary-card\">"
            f"<span class=\"metric\" style=\"color:{pct_color}\">"
            f"{compliance_pct:.1f}%</span>"
            "<span class=\"label\">Overall Compliance</span>"
            "</div>"
        )
        parts.append(
            "<div class=\"summary-card\">"
            f"<span class=\"metric\">{total}</span>"
            "<span class=\"label\">AI Models / Datasets Assessed</span>"
            "</div>"
        )
        parts.append(
            "<div class=\"summary-card\">"
            f"<span class=\"metric\" style=\"color:#1E8449\">{compliant}</span>"
            "<span class=\"label\">Compliant</span>"
            "</div>"
        )
        parts.append(
            "<div class=\"summary-card\">"
            f"<span class=\"metric\" style=\"color:#B7770D\">{partial}</span>"
            "<span class=\"label\">Partial</span>"
            "</div>"
        )
        parts.append(
            "<div class=\"summary-card\">"
            f"<span class=\"metric\" style=\"color:#C0392B\">{non_compliant}</span>"
            "<span class=\"label\">Non-Compliant</span>"
            "</div>"
        )
        parts.append("</div>")  # summary-grid
        parts.append("</section>")

        # Per-component assessments
        if not assessments:
            parts.append(
                "<section class=\"empty\">"
                "<p>No AI models or datasets were detected in this scan.</p>"
                "</section>"
            )
        else:
            parts.append("<section class=\"assessments\">")
            parts.append("<h2>Component Assessments</h2>")
            for assessment in assessments:
                parts.append(self._render_component_card(assessment))
            parts.append("</section>")

        # Footer
        parts.append(
            "<footer>"
            "<p>Generated by LCC &mdash; License Compliance Checker</p>"
            "</footer>"
        )

        parts.append("</div></body></html>")
        return "\n".join(parts)

    def _render_component_card(self, assessment: Any) -> str:
        """Render a single component assessment as an HTML card."""
        name = escape(assessment.component_name)
        comp_type = escape(assessment.component_type)
        risk = assessment.risk_classification
        risk_value = risk.value if risk is not None else "unknown"
        risk_class = _risk_css_class(risk_value)
        overall = assessment.overall_status
        overall_color = _status_color(overall)

        parts: list[str] = []
        parts.append("<div class=\"component-card\">")

        # Card header
        parts.append(
            "<div class=\"card-header\">"
            f"<h3>{name}</h3>"
            "<div class=\"badges\">"
            f"<span class=\"badge type-badge\">{comp_type}</span>"
            f"<span class=\"badge {risk_class}\">{escape(risk_value)}</span>"
            f"<span class=\"badge\" style=\"background:{overall_color};color:#fff\">"
            f"{escape(overall)}</span>"
            "</div>"
            "</div>"
        )

        # Obligations table
        parts.append("<table class=\"obligations\">")
        parts.append(
            "<thead><tr>"
            "<th>Obligation</th>"
            "<th>Status</th>"
            "<th>Evidence</th>"
            "<th>Gaps</th>"
            "</tr></thead>"
        )
        parts.append("<tbody>")
        for obligation in assessment.obligations:
            status = obligation.status
            status_color = _obligation_status_color(status)
            evidence_text = "; ".join(obligation.evidence) if obligation.evidence else "&mdash;"
            gaps_text = "; ".join(obligation.gaps) if obligation.gaps else "&mdash;"
            parts.append(
                "<tr>"
                f"<td><strong>{escape(obligation.article)}</strong><br>"
                f"{escape(obligation.title)}</td>"
                f"<td><span class=\"status-pill\" style=\"background:{status_color}\">"
                f"{escape(status)}</span></td>"
                f"<td>{escape(evidence_text) if evidence_text != '&mdash;' else evidence_text}</td>"
                f"<td>{escape(gaps_text) if gaps_text != '&mdash;' else gaps_text}</td>"
                "</tr>"
            )
        parts.append("</tbody></table>")

        # Recommendations
        if assessment.recommendations:
            parts.append("<div class=\"recommendations\">")
            parts.append("<h4>Recommendations</h4>")
            parts.append("<ul>")
            for rec in assessment.recommendations:
                parts.append(f"<li>{escape(rec)}</li>")
            parts.append("</ul>")
            parts.append("</div>")

        parts.append("</div>")  # component-card
        return "\n".join(parts)


# ===================================================================== #
#  Compliance Pack generator                                             #
# ===================================================================== #


def generate_compliance_pack(
    report: RegulatoryReport,
    scan_findings: list[ComponentFinding],
    output_dir: Path,
) -> Path:
    """Generate a complete EU AI Act Compliance Pack as a directory.

    Creates a timestamped directory containing:

    - ``eu_ai_act_report.json`` -- structured regulatory assessment
    - ``eu_ai_act_report.html`` -- human-readable HTML report
    - ``training_data_summary.json`` -- extracted training data info
      for all AI models
    - ``copyright_policy_template.md`` -- template for Art.53(1)(c)
      copyright policy

    Args:
        report: The :class:`RegulatoryReport` produced by
            :class:`EUAIActAssessor`.
        scan_findings: The full list of :class:`ComponentFinding`
            objects from the scan.
        output_dir: Parent directory in which the compliance pack
            directory will be created.

    Returns:
        Path to the created compliance pack directory.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    pack_dir = output_dir / f"eu-ai-act-compliance-pack-{timestamp}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    reporter = RegulatoryReporter(report)

    # 1. JSON report
    reporter.to_json(pack_dir / "eu_ai_act_report.json")

    # 2. HTML report
    reporter.to_html(pack_dir / "eu_ai_act_report.html")

    # 3. Training data summary
    training_summary = _build_training_data_summary(scan_findings)
    (pack_dir / "training_data_summary.json").write_text(
        json.dumps(training_summary, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    # 4. Copyright policy template
    copyright_md = _build_copyright_policy_template(report, scan_findings)
    (pack_dir / "copyright_policy_template.md").write_text(
        copyright_md, encoding="utf-8",
    )

    return pack_dir


# ===================================================================== #
#  Internal helpers — training data summary                              #
# ===================================================================== #


def _build_training_data_summary(
    findings: list[ComponentFinding],
) -> dict[str, Any]:
    """Extract training data information from all AI model findings.

    Returns a JSON-serialisable dictionary with per-model training
    data details.
    """
    ai_findings = [
        f for f in findings
        if f.component.type in (ComponentType.AI_MODEL, ComponentType.DATASET)
    ]

    if not ai_findings:
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "total_ai_components": 0,
            "models": [],
        }

    models: list[dict[str, Any]] = []
    for finding in ai_findings:
        training_info = get_training_data_info(finding)
        models.append({
            "name": finding.component.name,
            "version": finding.component.version,
            "type": finding.component.type.value,
            "license": finding.resolved_license or "unknown",
            "training_data": {
                "datasets": training_info["datasets"],
                "sources": training_info["sources"],
                "description": training_info["description"],
            },
        })

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_ai_components": len(models),
        "models": models,
    }


# ===================================================================== #
#  Internal helpers — copyright policy template                          #
# ===================================================================== #


def _build_copyright_policy_template(
    report: RegulatoryReport,
    findings: list[ComponentFinding],
) -> str:
    """Build a Markdown copyright policy template populated with scan data."""
    generated_date = report.generated_at or datetime.now(UTC).isoformat()

    ai_findings = [
        f for f in findings
        if f.component.type in (ComponentType.AI_MODEL, ComponentType.DATASET)
    ]

    # Section 1: AI Models in Use
    if ai_findings:
        model_lines: list[str] = []
        for f in ai_findings:
            lic = f.resolved_license or "unknown"
            model_lines.append(f"- **{f.component.name}** (v{f.component.version}): {lic}")
        models_section = "\n".join(model_lines)
    else:
        models_section = "_No AI models or datasets detected in this scan._"

    # Section 2: Training Data Sources
    all_sources: list[str] = []
    all_datasets: list[str] = []
    for f in ai_findings:
        training_info = get_training_data_info(f)
        for src in training_info["sources"]:
            if src not in all_sources:
                all_sources.append(src)
        for ds in training_info["datasets"]:
            if ds not in all_datasets:
                all_datasets.append(ds)

    source_lines: list[str] = []
    if all_datasets:
        source_lines.append("### Datasets")
        for ds in all_datasets:
            source_lines.append(f"- {ds}")
    if all_sources:
        source_lines.append("### Sources")
        for src in all_sources:
            source_lines.append(f"- {src}")
    if not source_lines:
        source_lines.append(
            "_No training data sources documented in model metadata. "
            "Manual documentation required._"
        )
    training_section = "\n".join(source_lines)

    # Section 3: Copyright Compliance Status
    if report.assessments:
        status_lines: list[str] = []
        for assessment in report.assessments:
            copyright_obligations = [
                o for o in assessment.obligations
                if "copyright" in o.title.lower()
            ]
            if copyright_obligations:
                ob = copyright_obligations[0]
                status_lines.append(
                    f"- **{assessment.component_name}**: {ob.status}"
                )
                if ob.gaps:
                    for gap in ob.gaps:
                        status_lines.append(f"  - Gap: {gap}")
            else:
                status_lines.append(
                    f"- **{assessment.component_name}**: {assessment.overall_status}"
                )
        copyright_section = "\n".join(status_lines)
    else:
        copyright_section = "_No AI components assessed._"

    # Section 4: Remediation Actions
    all_recommendations: list[str] = []
    for assessment in report.assessments:
        for rec in assessment.recommendations:
            if rec not in all_recommendations:
                all_recommendations.append(rec)

    if all_recommendations:
        remediation_lines = [f"- {rec}" for rec in all_recommendations]
        remediation_section = "\n".join(remediation_lines)
    else:
        remediation_section = "_No remediation actions required. All components are compliant._"

    return (
        f"# Copyright Policy for AI Training Data\n"
        f"\n"
        f"## Organisation: [To be filled]\n"
        f"\n"
        f"## Date: {generated_date}\n"
        f"\n"
        f"## 1. AI Models in Use\n"
        f"\n"
        f"{models_section}\n"
        f"\n"
        f"## 2. Training Data Sources\n"
        f"\n"
        f"{training_section}\n"
        f"\n"
        f"## 3. Copyright Compliance Status\n"
        f"\n"
        f"{copyright_section}\n"
        f"\n"
        f"## 4. Remediation Actions\n"
        f"\n"
        f"{remediation_section}\n"
    )


# ===================================================================== #
#  Colour / CSS helpers                                                  #
# ===================================================================== #


def _compliance_color(pct: float) -> str:
    """Return a CSS colour for the overall compliance percentage."""
    if pct > 80:
        return "#1E8449"
    if pct > 50:
        return "#B7770D"
    return "#C0392B"


def _status_color(status: str) -> str:
    """Return a CSS colour for an overall component status."""
    mapping = {
        "compliant": "#1E8449",
        "partial": "#B7770D",
        "non_compliant": "#C0392B",
    }
    return mapping.get(status, "#7F8C8D")


def _obligation_status_color(status: str) -> str:
    """Return a CSS colour for an obligation status pill."""
    mapping = {
        "met": "#1E8449",
        "partial": "#B7770D",
        "not_met": "#C0392B",
        "not_applicable": "#7F8C8D",
    }
    return mapping.get(status, "#7F8C8D")


def _risk_css_class(risk_value: str) -> str:
    """Return a CSS class name for a risk classification badge."""
    mapping = {
        "prohibited": "risk-prohibited",
        "high_risk": "risk-high",
        "limited_risk": "risk-limited",
        "minimal_risk": "risk-minimal",
        "general_purpose_ai": "risk-gpai",
        "gpai_systemic_risk": "risk-systemic",
    }
    return mapping.get(risk_value, "risk-unknown")


# ===================================================================== #
#  HTML template (inline CSS)                                            #
# ===================================================================== #

_HTML_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EU AI Act Compliance Report &mdash; License Compliance Checker</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 Helvetica, Arial, sans-serif;
    background: #F8F9FA;
    color: #333;
    line-height: 1.6;
  }

  .container {
    max-width: 1100px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
  }

  /* Header */
  header {
    background: #0A1628;
    color: #fff;
    padding: 2rem 2.5rem;
    border-radius: 8px 8px 0 0;
    margin-bottom: 0;
  }
  header h1 { font-size: 1.75rem; font-weight: 700; }
  header .subtitle { font-size: 1rem; opacity: 0.85; margin-top: 0.25rem; }
  header .generated { font-size: 0.85rem; opacity: 0.65; margin-top: 0.5rem; }

  /* Executive summary */
  .summary {
    background: #fff;
    padding: 2rem 2.5rem;
    border: 1px solid #dee2e6;
    border-top: none;
  }
  .summary h2 { color: #0A1628; margin-bottom: 1.25rem; font-size: 1.35rem; }
  .summary-grid {
    display: flex;
    gap: 1.25rem;
    flex-wrap: wrap;
  }
  .summary-card {
    flex: 1 1 150px;
    background: #F8F9FA;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 1.25rem;
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  .summary-card .metric { font-size: 2rem; font-weight: 700; }
  .summary-card .label { font-size: 0.8rem; color: #555; text-transform: uppercase; letter-spacing: 0.04em; }

  /* Component cards */
  .assessments { margin-top: 1.5rem; }
  .assessments h2 { color: #0A1628; margin-bottom: 1rem; font-size: 1.35rem; }
  .component-card {
    background: #FFFFFF;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    margin-bottom: 1.5rem;
    overflow: hidden;
  }
  .card-header {
    background: #0A1628;
    color: #fff;
    padding: 1rem 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .card-header h3 { font-size: 1.1rem; font-weight: 600; }
  .badges { display: flex; gap: 0.5rem; flex-wrap: wrap; }
  .badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .type-badge { background: #2C3E50; color: #fff; }
  .risk-prohibited { background: #C0392B; color: #fff; }
  .risk-high { background: #E74C3C; color: #fff; }
  .risk-limited { background: #F39C12; color: #fff; }
  .risk-minimal { background: #27AE60; color: #fff; }
  .risk-gpai { background: #2980B9; color: #fff; }
  .risk-systemic { background: #8E44AD; color: #fff; }
  .risk-unknown { background: #7F8C8D; color: #fff; }

  /* Obligations table */
  .obligations {
    width: 100%;
    border-collapse: collapse;
  }
  .obligations th {
    background: #F1F3F5;
    color: #0A1628;
    text-align: left;
    padding: 0.75rem 1rem;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 2px solid #dee2e6;
  }
  .obligations td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #eee;
    font-size: 0.9rem;
    vertical-align: top;
  }
  .obligations tr:last-child td { border-bottom: none; }
  .status-pill {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 3px;
    color: #fff;
    font-size: 0.8rem;
    font-weight: 600;
    white-space: nowrap;
  }

  /* Recommendations */
  .recommendations {
    padding: 1rem 1.5rem 1.25rem;
    border-top: 1px solid #eee;
  }
  .recommendations h4 { color: #0A1628; margin-bottom: 0.5rem; font-size: 0.95rem; }
  .recommendations ul { margin-left: 1.25rem; }
  .recommendations li { margin-bottom: 0.35rem; font-size: 0.9rem; }

  /* Empty state */
  .empty {
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 3rem 2rem;
    text-align: center;
    color: #7F8C8D;
    margin-top: 1.5rem;
  }

  /* Footer */
  footer {
    text-align: center;
    padding: 2rem 1rem;
    font-size: 0.85rem;
    color: #7F8C8D;
  }
</style>
</head>
<body>
<div class="container">"""
