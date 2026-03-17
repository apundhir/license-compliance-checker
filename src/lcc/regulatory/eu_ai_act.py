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
EU AI Act Article 53 mapping engine.

Evaluates scan results against GPAI (General Purpose AI) provider
obligations defined in Article 53 of the EU AI Act.  Each AI model or
dataset discovered during a scan is assessed for compliance with the five
sub-article requirements and assigned a risk classification.

References:
- EU AI Act (Regulation (EU) 2024/1689)
- Article 53 — Obligations for providers of general-purpose AI models
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from lcc.ai.licenses import AI_LICENSES, normalize_ai_license_name
from lcc.models import ComponentFinding, ComponentType
from lcc.regulatory.constants import EU_AI_ACT_ARTICLE_53_OBLIGATIONS
from lcc.regulatory.frameworks import (
    AIRiskClassification,
    Article53Obligation,
    RegulatoryAssessment,
    RegulatoryFramework,
    RegulatoryReport,
)

# -----------------------------------------------------------------------
# Well-known open-source licences that imply a clear copyright policy
# -----------------------------------------------------------------------
_KNOWN_OPEN_LICENSES: set[str] = {
    "apache-2.0",
    "mit",
    "bsd-2-clause",
    "bsd-3-clause",
    "isc",
    "cc0-1.0",
    "cc-by-4.0",
    "cc-by-3.0",
    "unlicense",
    "mpl-2.0",
    "lgpl-2.1",
    "lgpl-3.0",
    "gpl-2.0",
    "gpl-3.0",
    "artistic-2.0",
    "zlib",
    "ofl-1.1",
    "ecl-2.0",
    "postgresql",
}

# Regex pattern matching model-size indicators that suggest systemic risk
# (models >= 10^25 FLOPs, typically > 65 B parameters).
_SYSTEMIC_SIZE_PATTERN: re.Pattern[str] = re.compile(
    r"\b(\d{2,3})\s*[bB]\b"  # e.g. "70B", "175B", "65 B"
)

_SYSTEMIC_SIZE_THRESHOLD = 65  # billion parameters


# ===================================================================== #
#  Helper functions                                                      #
# ===================================================================== #

def get_use_restrictions(finding: ComponentFinding) -> list[str]:
    """Extract use restrictions from the AI license registry.

    Looks up the component's resolved licence (or the licence embedded in
    component metadata) in :data:`AI_LICENSES` and returns any
    ``use_restrictions`` defined there.

    Args:
        finding: A single component finding from a scan.

    Returns:
        List of restriction identifiers (e.g. ``["no-harm",
        "no-illegal-activity"]``).  Empty list when no restrictions are
        found.
    """
    restrictions: list[str] = []

    # Try resolved license first
    license_id = _get_license_key(finding)
    if license_id and license_id in AI_LICENSES:
        restrictions.extend(AI_LICENSES[license_id].use_restrictions)

    # Also check metadata-level use_restrictions (from model card parser)
    meta_restrictions = finding.component.metadata.get("use_restrictions", [])
    if isinstance(meta_restrictions, list):
        for r in meta_restrictions:
            if r not in restrictions:
                restrictions.append(r)

    return restrictions


def is_gpai_model(finding: ComponentFinding) -> bool:
    """Check if the component qualifies as General Purpose AI.

    A component is considered GPAI when it is an AI model or dataset with
    an identified AI-specific licence (especially RAIL variants) or when
    its component type is :attr:`ComponentType.AI_MODEL`.

    Args:
        finding: A single component finding.

    Returns:
        ``True`` if the component should be assessed under GPAI rules.
    """
    if finding.component.type not in (ComponentType.AI_MODEL, ComponentType.DATASET):
        return False

    # Any AI model or dataset is presumed GPAI for assessment purposes
    return True


def get_training_data_info(finding: ComponentFinding) -> dict[str, Any]:
    """Extract training data information from component metadata.

    Pulls ``datasets``, ``training_data_sources``, and
    ``training_data_description`` from the component's metadata dict.

    Args:
        finding: A single component finding.

    Returns:
        Dictionary with keys ``datasets``, ``sources``, and
        ``description`` (each may be empty/None).
    """
    meta = finding.component.metadata

    datasets: list[str] = meta.get("datasets", [])
    if isinstance(datasets, str):
        datasets = [datasets]

    sources: list[str] = meta.get("training_data_sources", [])
    if isinstance(sources, str):
        sources = [sources]

    description: str | None = meta.get("training_data_description")

    return {
        "datasets": datasets,
        "sources": sources,
        "description": description,
    }


# ===================================================================== #
#  Internal helpers                                                      #
# ===================================================================== #

def _get_license_key(finding: ComponentFinding) -> str | None:
    """Return a normalised AI-licence registry key for *finding*.

    Tries the resolved licence first, then falls back to the licence
    value stored in component metadata (``license_from_card``).  The
    value is normalised via :func:`normalize_ai_license_name` so that
    common aliases map to registry keys.
    """
    candidates: list[str] = []

    if finding.resolved_license:
        candidates.append(finding.resolved_license)

    card_license = finding.component.metadata.get("license_from_card")
    if card_license:
        candidates.append(card_license)

    for candidate in candidates:
        lower = candidate.lower().strip()
        # Direct match
        if lower in AI_LICENSES:
            return lower
        # Alias match
        normalised = normalize_ai_license_name(lower)
        if normalised:
            return normalised

    return None


def _has_license_info(finding: ComponentFinding) -> bool:
    """Return ``True`` if a licence has been resolved or is in metadata."""
    if finding.resolved_license:
        return True
    if finding.component.metadata.get("license_from_card"):
        return True
    return False


def _license_display(finding: ComponentFinding) -> str:
    """Return a human-readable licence string for evidence entries."""
    if finding.resolved_license:
        return finding.resolved_license
    card = finding.component.metadata.get("license_from_card")
    if card:
        return str(card)
    return "unknown"


def _has_metadata_description(finding: ComponentFinding) -> bool:
    """Return ``True`` if the component carries a textual description."""
    desc = finding.component.metadata.get("description", "")
    return bool(desc and str(desc).strip())


def _is_rail_or_restricted_license(finding: ComponentFinding) -> bool:
    """Return ``True`` if the licence is a RAIL variant or has use restrictions."""
    license_key = _get_license_key(finding)
    if not license_key:
        return False
    info = AI_LICENSES.get(license_key)
    if info is None:
        return False
    return bool(info.use_restrictions) or "rail" in license_key.lower()


def _is_known_open_license(finding: ComponentFinding) -> bool:
    """Return ``True`` if the resolved licence is a well-known open licence."""
    lic = _license_display(finding).lower().strip()
    if lic in _KNOWN_OPEN_LICENSES:
        return True
    # Check spdx-style normalisation (e.g. "Apache-2.0" -> "apache-2.0")
    normalised = lic.replace(" ", "-")
    if normalised in _KNOWN_OPEN_LICENSES:
        return True
    # Also accept AI-registry permissive licences with no restrictions
    license_key = _get_license_key(finding)
    if license_key:
        info = AI_LICENSES.get(license_key)
        if info and info.category == "permissive" and not info.use_restrictions:
            return True
    return False


def _detect_systemic_risk(finding: ComponentFinding) -> bool:
    """Heuristically detect whether a model poses systemic risk.

    Checks component name, metadata (description, model_type, tags) for
    indicators of very large model size (>= 65 B parameters).
    """
    texts_to_check: list[str] = [
        finding.component.name,
        str(finding.component.metadata.get("description", "")),
        str(finding.component.metadata.get("model_type", "")),
    ]

    # Also check tags
    tags = finding.component.metadata.get("tags", [])
    if isinstance(tags, list):
        texts_to_check.extend(str(t) for t in tags)

    combined = " ".join(texts_to_check)
    matches = _SYSTEMIC_SIZE_PATTERN.findall(combined)
    for match in matches:
        try:
            size = int(match)
            if size >= _SYSTEMIC_SIZE_THRESHOLD:
                return True
        except ValueError:
            continue

    return False


def _detect_prohibited_use(finding: ComponentFinding) -> bool:
    """Check for indicators that the model's intended use is prohibited.

    Under the EU AI Act, certain AI applications are outright prohibited
    (e.g. social scoring, real-time biometric identification in public
    spaces).  This function performs a keyword heuristic against
    metadata.
    """
    prohibited_keywords = [
        "social scoring",
        "social credit",
        "real-time biometric identification",
        "subliminal manipulation",
        "exploitation of vulnerabilities",
    ]

    texts_to_check: list[str] = [
        str(finding.component.metadata.get("description", "")),
        str(finding.component.metadata.get("intended_uses", "")),
        str(finding.component.metadata.get("out_of_scope_uses", "")),
    ]

    tags = finding.component.metadata.get("tags", [])
    if isinstance(tags, list):
        texts_to_check.extend(str(t) for t in tags)

    combined = " ".join(texts_to_check).lower()

    return any(kw in combined for kw in prohibited_keywords)


# ===================================================================== #
#  EUAIActAssessor                                                       #
# ===================================================================== #

class EUAIActAssessor:
    """Evaluates scan results against EU AI Act GPAI obligations.

    The assessor maps each AI model or dataset discovered during a
    licence compliance scan to the five sub-article obligations defined
    in :data:`EU_AI_ACT_ARTICLE_53_OBLIGATIONS` and produces structured
    :class:`RegulatoryAssessment` and :class:`RegulatoryReport` objects.
    """

    # ------------------------------------------------------------------ #
    #  Risk classification                                                #
    # ------------------------------------------------------------------ #

    def classify_risk(self, finding: ComponentFinding) -> AIRiskClassification:
        """Determine the EU AI Act risk classification for a component.

        Classification logic:

        * Traditional software packages (non-AI) -> ``MINIMAL_RISK``
        * AI models / datasets with prohibited-use indicators ->
          ``PROHIBITED``
        * AI models / datasets with systemic-risk indicators (very large
          parameter counts) -> ``GPAI_SYSTEMIC``
        * AI models / datasets with RAIL licences or other AI-specific
          licences -> ``GPAI``
        * Default AI models / datasets -> ``GPAI``

        Args:
            finding: A single component finding from a scan.

        Returns:
            The appropriate :class:`AIRiskClassification` value.
        """
        comp_type = finding.component.type

        # Non-AI components are minimal risk
        if comp_type not in (ComponentType.AI_MODEL, ComponentType.DATASET):
            return AIRiskClassification.MINIMAL_RISK

        # Check for prohibited use indicators
        if _detect_prohibited_use(finding):
            return AIRiskClassification.PROHIBITED

        # Check for systemic risk indicators (large models)
        if _detect_systemic_risk(finding):
            return AIRiskClassification.GPAI_SYSTEMIC

        # Default: all AI models and datasets qualify as GPAI
        return AIRiskClassification.GPAI

    # ------------------------------------------------------------------ #
    #  Per-component assessment                                           #
    # ------------------------------------------------------------------ #

    def assess_component(self, finding: ComponentFinding) -> RegulatoryAssessment:
        """Assess a single AI model/dataset against Art. 53 obligations.

        Each of the five obligations in
        :data:`EU_AI_ACT_ARTICLE_53_OBLIGATIONS` is evaluated and an
        overall status is derived:

        * ``"compliant"`` — all applicable obligations are met.
        * ``"partial"`` — at least one obligation is partially met and
          none are fully unmet.
        * ``"non_compliant"`` — at least one applicable obligation is
          not met.

        Args:
            finding: A single component finding from a scan.

        Returns:
            A :class:`RegulatoryAssessment` for the component.
        """
        risk = self.classify_risk(finding)
        obligations = self._evaluate_obligations(finding, risk)
        overall = self._derive_overall_status(obligations)
        recommendations = self._build_recommendations(obligations, risk)

        return RegulatoryAssessment(
            framework=RegulatoryFramework.EU_AI_ACT,
            component_name=finding.component.name,
            component_type=finding.component.type.value,
            risk_classification=risk,
            obligations=obligations,
            overall_status=overall,
            recommendations=recommendations,
            assessed_at=datetime.utcnow().isoformat(),
        )

    # ------------------------------------------------------------------ #
    #  Scan-level assessment                                              #
    # ------------------------------------------------------------------ #

    def assess_scan(self, findings: list[ComponentFinding]) -> RegulatoryReport:
        """Assess all AI/ML components from a scan.

        Filters the findings to :attr:`ComponentType.AI_MODEL` and
        :attr:`ComponentType.DATASET` types, runs
        :meth:`assess_component` on each, and builds a summary report.

        Args:
            findings: All component findings from a scan.

        Returns:
            A :class:`RegulatoryReport` aggregating per-component
            assessments and summary statistics.
        """
        ai_findings = [
            f
            for f in findings
            if f.component.type in (ComponentType.AI_MODEL, ComponentType.DATASET)
        ]

        assessments: list[RegulatoryAssessment] = [
            self.assess_component(f) for f in ai_findings
        ]

        # Compute summary statistics
        total = len(assessments)
        compliant = sum(1 for a in assessments if a.overall_status == "compliant")
        partial = sum(1 for a in assessments if a.overall_status == "partial")
        non_compliant = sum(
            1 for a in assessments if a.overall_status == "non_compliant"
        )

        compliance_pct = (compliant / total * 100.0) if total > 0 else 0.0

        summary: dict[str, Any] = {
            "total_ai_components": total,
            "compliant": compliant,
            "partial": partial,
            "non_compliant": non_compliant,
            "compliance_percentage": round(compliance_pct, 1),
        }

        return RegulatoryReport(
            title="EU AI Act Article 53 GPAI Compliance Report",
            framework=RegulatoryFramework.EU_AI_ACT,
            generated_at=datetime.utcnow().isoformat(),
            assessments=assessments,
            summary=summary,
        )

    # ------------------------------------------------------------------ #
    #  Obligation evaluators                                              #
    # ------------------------------------------------------------------ #

    def _evaluate_obligations(
        self,
        finding: ComponentFinding,
        risk: AIRiskClassification,
    ) -> list[Article53Obligation]:
        """Evaluate all five Art. 53 obligations for *finding*."""
        evaluators = [
            self._assess_technical_documentation,
            self._assess_downstream_info,
            self._assess_copyright_policy,
            self._assess_training_data_summary,
            self._assess_systemic_risk_obligations,
        ]

        obligations: list[Article53Obligation] = []
        for idx, evaluator in enumerate(evaluators):
            template = EU_AI_ACT_ARTICLE_53_OBLIGATIONS[idx]
            obligation = evaluator(finding, risk, template)
            obligations.append(obligation)

        return obligations

    # -- Art. 53(1)(a) Technical documentation --

    def _assess_technical_documentation(
        self,
        finding: ComponentFinding,
        risk: AIRiskClassification,
        template: dict[str, Any],
    ) -> Article53Obligation:
        """Art. 53(1)(a) — Technical documentation.

        * *met* if SBOM data is available (type, name, version, and
          licence are all present).
        * *partial* if name and version are present but licence is
          missing.
        * *not_met* otherwise.
        """
        evidence: list[str] = []
        gaps: list[str] = []

        has_type = bool(finding.component.type)
        has_name = bool(finding.component.name)
        has_version = bool(
            finding.component.version
            and finding.component.version != "unknown"
        )
        has_license = _has_license_info(finding)

        if has_type and has_name:
            evidence.append("SBOM component entry")
        if has_version:
            evidence.append(f"Version: {finding.component.version}")
        if has_license:
            evidence.append(f"License: {_license_display(finding)}")

        if has_type and has_name and has_version and has_license:
            status = "met"
        elif has_name and has_version:
            status = "partial"
            gaps.append("License not resolved — incomplete technical documentation")
        else:
            status = "not_met"
            if not has_name:
                gaps.append("Component name not available")
            if not has_version:
                gaps.append("Component version not available")
            if not has_license:
                gaps.append("License not resolved")

        return Article53Obligation(
            article=template["article"],
            title=template["title"],
            description=template["description"],
            status=status,
            evidence=evidence,
            gaps=gaps,
        )

    # -- Art. 53(1)(b) Info for downstream providers --

    def _assess_downstream_info(
        self,
        finding: ComponentFinding,
        risk: AIRiskClassification,
        template: dict[str, Any],
    ) -> Article53Obligation:
        """Art. 53(1)(b) — Information for downstream providers.

        * *met* if the component has a resolved licence **and** a
          metadata description.
        * *partial* if only the licence is resolved.
        * *not_met* otherwise.
        """
        evidence: list[str] = []
        gaps: list[str] = []

        has_license = _has_license_info(finding)
        has_description = _has_metadata_description(finding)

        if has_license:
            evidence.append(f"License resolved: {_license_display(finding)}")
        if has_description:
            evidence.append("Metadata available")

        if has_license and has_description:
            status = "met"
        elif has_license:
            status = "partial"
            gaps.append(
                "Component description or model card not available for "
                "downstream providers"
            )
        else:
            status = "not_met"
            if not has_license:
                gaps.append("License not resolved")
            if not has_description:
                gaps.append("No component description available")

        return Article53Obligation(
            article=template["article"],
            title=template["title"],
            description=template["description"],
            status=status,
            evidence=evidence,
            gaps=gaps,
        )

    # -- Art. 53(1)(c) Copyright policy --

    def _assess_copyright_policy(
        self,
        finding: ComponentFinding,
        risk: AIRiskClassification,
        template: dict[str, Any],
    ) -> Article53Obligation:
        """Art. 53(1)(c) — Copyright policy compliance.

        * *met* if the component uses a known open-source licence
          (Apache-2.0, MIT, etc.).
        * *partial* if a licence is resolved but carries restrictions
          (RAIL, custom).
        * *not_met* if the licence is unknown or unresolved.
        """
        evidence: list[str] = []
        gaps: list[str] = []

        has_license = _has_license_info(finding)
        lic_display = _license_display(finding)

        if has_license:
            evidence.append(f"License: {lic_display}")

        # Check for dataset-level licence info in metadata
        dataset_license = finding.component.metadata.get("license_from_card")
        if dataset_license and finding.component.type == ComponentType.DATASET:
            evidence.append(f"Training data license: {dataset_license}")

        if has_license and _is_known_open_license(finding):
            status = "met"
        elif has_license and _is_rail_or_restricted_license(finding):
            status = "partial"
            gaps.append(
                "License has use-based restrictions — copyright policy "
                "compliance requires further review"
            )
        elif has_license:
            # Licence resolved but not a well-known open licence
            status = "partial"
            gaps.append(
                "License resolved but is not a well-known open licence — "
                "copyright policy may need additional documentation"
            )
        else:
            status = "not_met"
            gaps.append("License unknown or unresolved")

        # Flag training data copyright concerns for AI models
        if finding.component.type == ComponentType.AI_MODEL:
            training_info = get_training_data_info(finding)
            if not training_info["datasets"] and not training_info["sources"]:
                gaps.append(
                    "Copyright policy for training data not documented"
                )

        return Article53Obligation(
            article=template["article"],
            title=template["title"],
            description=template["description"],
            status=status,
            evidence=evidence,
            gaps=gaps,
        )

    # -- Art. 53(1)(d) Training data summary --

    def _assess_training_data_summary(
        self,
        finding: ComponentFinding,
        risk: AIRiskClassification,
        template: dict[str, Any],
    ) -> Article53Obligation:
        """Art. 53(1)(d) — Training data summary.

        * *met* if metadata contains training data information
          (``datasets``, ``training_data_sources``, or
          ``training_data_description``).
        * *not_met* if no training data information is available.
        """
        evidence: list[str] = []
        gaps: list[str] = []

        training_info = get_training_data_info(finding)
        datasets = training_info["datasets"]
        sources = training_info["sources"]
        description = training_info["description"]

        has_info = bool(datasets or sources or description)

        if datasets:
            evidence.append(f"Training datasets: {', '.join(datasets)}")
        if sources:
            evidence.append(f"Training data sources: {', '.join(sources)}")
        if description:
            # Truncate long descriptions in evidence
            desc_preview = (
                description[:120] + "..."
                if len(description) > 120
                else description
            )
            evidence.append(f"Training data description: {desc_preview}")

        if has_info:
            status = "met"
        else:
            status = "not_met"
            gaps.append("No training data summary available")

        return Article53Obligation(
            article=template["article"],
            title=template["title"],
            description=template["description"],
            status=status,
            evidence=evidence,
            gaps=gaps,
        )

    # -- Art. 53(2) Systemic risk obligations --

    def _assess_systemic_risk_obligations(
        self,
        finding: ComponentFinding,
        risk: AIRiskClassification,
        template: dict[str, Any],
    ) -> Article53Obligation:
        """Art. 53(2) — Systemic risk additional obligations.

        * *not_applicable* if the component is not classified as
          ``GPAI_SYSTEMIC``.
        * *met* if systemic risk model has evaluation metrics, known
          limitations, and environmental impact documented.
        * *partial* if some safety documentation is present.
        * *not_met* if systemic risk model lacks additional safety
          documentation.
        """
        evidence: list[str] = []
        gaps: list[str] = []

        if risk != AIRiskClassification.GPAI_SYSTEMIC:
            return Article53Obligation(
                article=template["article"],
                title=template["title"],
                description=template["description"],
                status="not_applicable",
                evidence=["Component not classified as GPAI with systemic risk"],
                gaps=[],
            )

        # For systemic-risk models, check for additional safety documentation
        meta = finding.component.metadata

        has_eval = bool(meta.get("evaluation_metrics"))
        has_limitations = bool(meta.get("limitations"))
        has_env_impact = bool(meta.get("environmental_impact"))
        has_intended_uses = bool(meta.get("intended_uses"))

        if has_eval:
            evidence.append("Model evaluation metrics documented")
        else:
            gaps.append("No model evaluation or adversarial testing results")

        if has_limitations:
            evidence.append("Known limitations documented")
        else:
            gaps.append("Known limitations not documented")

        if has_env_impact:
            evidence.append("Environmental impact documented")
        else:
            gaps.append("Environmental impact not documented")

        if has_intended_uses:
            evidence.append("Intended uses documented")
        else:
            gaps.append("Intended uses not documented")

        # Determine status based on coverage
        safety_items = [has_eval, has_limitations, has_env_impact, has_intended_uses]
        met_count = sum(safety_items)

        if met_count == len(safety_items):
            status = "met"
        elif met_count > 0:
            status = "partial"
        else:
            status = "not_met"

        return Article53Obligation(
            article=template["article"],
            title=template["title"],
            description=template["description"],
            status=status,
            evidence=evidence,
            gaps=gaps,
        )

    # ------------------------------------------------------------------ #
    #  Overall status derivation                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _derive_overall_status(obligations: list[Article53Obligation]) -> str:
        """Derive an overall compliance status from individual obligations.

        * ``"compliant"`` — all applicable obligations are met.
        * ``"partial"`` — at least one obligation is partial; none are
          fully unmet.
        * ``"non_compliant"`` — at least one applicable obligation is
          not met.
        """
        applicable = [
            o for o in obligations if o.status != "not_applicable"
        ]
        if not applicable:
            return "compliant"

        statuses = {o.status for o in applicable}

        if statuses == {"met"}:
            return "compliant"
        if "not_met" in statuses:
            return "non_compliant"
        # Only "met" and "partial" remain
        return "partial"

    # ------------------------------------------------------------------ #
    #  Recommendations                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_recommendations(
        obligations: list[Article53Obligation],
        risk: AIRiskClassification,
    ) -> list[str]:
        """Build actionable recommendations from unmet/partial obligations."""
        recommendations: list[str] = []

        for obligation in obligations:
            if obligation.status == "not_met":
                recommendations.append(
                    f"[{obligation.article}] {obligation.title}: "
                    f"Action required — {'; '.join(obligation.gaps)}"
                )
            elif obligation.status == "partial":
                recommendations.append(
                    f"[{obligation.article}] {obligation.title}: "
                    f"Improvement needed — {'; '.join(obligation.gaps)}"
                )

        if risk == AIRiskClassification.GPAI_SYSTEMIC:
            recommendations.append(
                "This model is classified as GPAI with systemic risk. "
                "Ensure model evaluations, systemic risk assessments, "
                "incident tracking, and cybersecurity protections are in place."
            )

        if risk == AIRiskClassification.PROHIBITED:
            recommendations.append(
                "WARNING: This component shows indicators of prohibited AI "
                "use under the EU AI Act. Immediate legal review recommended."
            )

        return recommendations
