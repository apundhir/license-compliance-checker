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
Regulatory compliance framework data models.

Enums, dataclasses, and types for tracking compliance with:
- EU AI Act (including GPAI provider obligations under Article 53)
- NIST AI Risk Management Framework (AI RMF 1.0)
- ISO/IEC 42001 AI Management System
- US Executive Order 14110 on Safe, Secure, and Trustworthy AI
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class RegulatoryFramework(StrEnum):
    """Supported regulatory and standards frameworks."""

    EU_AI_ACT = "eu_ai_act"
    NIST_AI_RMF = "nist_ai_rmf"
    ISO_42001 = "iso_42001"
    US_EO_14110 = "us_eo_14110"


class AIRiskClassification(StrEnum):
    """EU AI Act risk classification tiers."""

    PROHIBITED = "prohibited"
    HIGH_RISK = "high_risk"
    LIMITED_RISK = "limited_risk"
    MINIMAL_RISK = "minimal_risk"
    GPAI = "general_purpose_ai"
    GPAI_SYSTEMIC = "gpai_systemic_risk"


class CopyrightComplianceStatus(StrEnum):
    """Status of copyright compliance verification for training data."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class TransparencyRequirement(StrEnum):
    """Types of transparency obligations under the EU AI Act."""

    MODEL_CARD = "model_card"
    TRAINING_DATA_SUMMARY = "training_data_summary"
    COPYRIGHT_POLICY = "copyright_policy"
    TECHNICAL_DOCUMENTATION = "technical_documentation"
    SBOM = "sbom"


@dataclass(slots=True)
class RegulatoryMetadata:
    """
    Regulatory metadata attached to an AI component (model or dataset).

    Captures compliance-relevant information across multiple frameworks.
    All fields are optional or defaulted so that partial metadata can be
    represented without requiring data that might not be available.
    """

    # EU AI Act
    risk_classification: AIRiskClassification | None = None
    applicable_articles: list[str] = field(default_factory=list)
    transparency_requirements: list[TransparencyRequirement] = field(default_factory=list)
    copyright_compliance: CopyrightComplianceStatus = CopyrightComplianceStatus.UNKNOWN

    # Training data
    training_data_sources: list[str] = field(default_factory=list)
    training_data_licenses: list[str] = field(default_factory=list)
    training_data_summary: str | None = None

    # Model info
    use_restrictions: list[str] = field(default_factory=list)
    known_limitations: str | None = None
    evaluation_metrics: dict[str, Any] = field(default_factory=dict)
    environmental_impact: dict[str, str] | None = None

    # Compliance status
    frameworks: list[RegulatoryFramework] = field(default_factory=list)
    compliance_gaps: list[str] = field(default_factory=list)
    compliance_score: float | None = None  # 0.0-1.0

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dictionary."""
        data = asdict(self)
        # Convert enum values to their string representations
        if self.risk_classification is not None:
            data["risk_classification"] = str(self.risk_classification.value)
        data["copyright_compliance"] = str(self.copyright_compliance.value)
        data["transparency_requirements"] = [
            str(r.value) for r in self.transparency_requirements
        ]
        data["frameworks"] = [str(f.value) for f in self.frameworks]
        return data


@dataclass(slots=True)
class Article53Obligation:
    """
    A single GPAI provider obligation under EU AI Act Article 53.

    Each instance tracks whether a specific sub-article requirement has
    been met, what evidence supports compliance, and what gaps remain.
    """

    article: str  # e.g. "Art.53(1)(a)"
    title: str  # e.g. "Technical documentation"
    description: str  # What this obligation requires
    status: str = "not_met"  # "met", "partial", "not_met", "not_applicable"
    evidence: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dictionary."""
        return asdict(self)


@dataclass(slots=True)
class RegulatoryAssessment:
    """
    Result of evaluating a single component against a regulatory framework.

    Produced by framework-specific assessors and consumed by reporters
    and the CLI to display compliance status.
    """

    framework: RegulatoryFramework
    component_name: str
    component_type: str
    risk_classification: AIRiskClassification | None = None
    obligations: list[Article53Obligation] = field(default_factory=list)
    overall_status: str = "non_compliant"  # "compliant", "partial", "non_compliant"
    recommendations: list[str] = field(default_factory=list)
    assessed_at: str = ""  # ISO 8601 datetime
    scope_note: str = ""  # Disclaimer / scoping note for the assessment

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dictionary."""
        data: dict[str, Any] = {
            "framework": str(self.framework.value),
            "component_name": self.component_name,
            "component_type": self.component_type,
            "risk_classification": (
                str(self.risk_classification.value)
                if self.risk_classification is not None
                else None
            ),
            "obligations": [o.to_dict() for o in self.obligations],
            "overall_status": self.overall_status,
            "recommendations": list(self.recommendations),
            "assessed_at": self.assessed_at,
            "scope_note": self.scope_note,
        }
        return data


@dataclass(slots=True)
class RegulatoryReport:
    """
    Aggregate regulatory compliance report across one or more components.

    Groups :class:`RegulatoryAssessment` instances under a single
    framework and provides summary statistics.
    """

    title: str
    framework: RegulatoryFramework
    generated_at: str = ""  # ISO 8601 datetime
    assessments: list[RegulatoryAssessment] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dictionary."""
        return {
            "title": self.title,
            "framework": str(self.framework.value),
            "generated_at": self.generated_at,
            "assessments": [a.to_dict() for a in self.assessments],
            "summary": dict(self.summary),
        }
