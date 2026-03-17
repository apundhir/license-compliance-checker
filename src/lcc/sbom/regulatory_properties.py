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
Regulatory metadata helpers for SBOM generators.

Centralises the logic for deriving EU AI Act and related regulatory
properties from an LCC Component and its scan result, so that both
CycloneDX and SPDX generators produce consistent metadata.
"""

from __future__ import annotations

from typing import Any

from lcc.models import Component, ComponentResult, ComponentType

# Licenses that indicate minimal regulatory risk (permissive / well-known open)
_PERMISSIVE_LICENSES: frozenset[str] = frozenset(
    {
        "Apache-2.0",
        "MIT",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "Unlicense",
        "CC0-1.0",
        "CC-BY-4.0",
        "ECL-2.0",
        "PostgreSQL",
        "Zlib",
    }
)

# License patterns that signal RAIL / restricted / use-based restrictions
_RAIL_LICENSE_PATTERNS: tuple[str, ...] = (
    "RAIL",
    "OpenRAIL",
    "BigScience",
    "LLAMA",
    "Llama",
    "CC-BY-NC",
    "CC-BY-SA",
    "CC-BY-ND",
    "GPL",
    "AGPL",
    "SSPL",
    "Elastic",
    "BUSL",
    "LicenseRef-",
)


def _is_ai_component(component: Component) -> bool:
    """Return True if the component is an AI_MODEL or DATASET."""
    return component.type in (ComponentType.AI_MODEL, ComponentType.DATASET)


def _classify_risk(license_expression: str | None) -> str:
    """
    Derive an EU AI Act risk classification from the resolved licence.

    Heuristic:
    * Known permissive licences  -> ``minimal_risk``
    * RAIL / restricted licences -> ``general_purpose_ai``
    * Unknown / absent           -> ``unknown``
    """
    if not license_expression:
        return "unknown"

    # Check permissive first
    if license_expression in _PERMISSIVE_LICENSES:
        return "minimal_risk"

    # Check RAIL / restricted patterns
    for pattern in _RAIL_LICENSE_PATTERNS:
        if pattern in license_expression:
            return "general_purpose_ai"

    return "unknown"


def _resolve_license(component_result: ComponentResult | None) -> str | None:
    """Return the highest-confidence licence string from a ComponentResult."""
    if not component_result or not component_result.licenses:
        return None
    sorted_licences = sorted(
        component_result.licenses, key=lambda e: e.confidence, reverse=True
    )
    return sorted_licences[0].license_expression if sorted_licences else None


def _copyright_compliance_status(component: Component) -> str:
    """
    Derive copyright compliance status from component metadata.

    Looks for a ``copyright_compliance`` key in ``component.metadata``.
    Falls back to ``"unknown"`` when absent.
    """
    return str(component.metadata.get("copyright_compliance", "unknown"))


def _training_data_sources(component: Component) -> str:
    """
    Return a comma-separated string of training data sources.

    Looks for ``datasets`` or ``training_data_sources`` in metadata.
    Returns ``"unknown"`` when absent.
    """
    sources: Any = component.metadata.get(
        "training_data_sources",
        component.metadata.get("datasets"),
    )
    if not sources:
        return "unknown"
    if isinstance(sources, list):
        return ", ".join(str(s) for s in sources) if sources else "unknown"
    return str(sources)


def _use_restrictions(component: Component) -> str:
    """
    Return a comma-separated string of use restrictions.

    Looks for ``use_restrictions`` in metadata.
    Returns ``"none"`` when absent.
    """
    restrictions: Any = component.metadata.get("use_restrictions")
    if not restrictions:
        return "none"
    if isinstance(restrictions, list):
        return ", ".join(str(r) for r in restrictions) if restrictions else "none"
    return str(restrictions)


def _eu_ai_act_article_53(risk_classification: str) -> str:
    """
    Return ``"applicable"`` if the risk classification implies
    Article 53 obligations (GPAI or systemic risk), otherwise
    ``"not_applicable"``.
    """
    if risk_classification in ("general_purpose_ai", "gpai_systemic_risk"):
        return "applicable"
    return "not_applicable"


def _transparency_required(risk_classification: str) -> str:
    """
    Return ``"true"`` if the classification requires transparency
    under the EU AI Act, ``"false"`` otherwise.
    """
    if risk_classification in (
        "general_purpose_ai",
        "gpai_systemic_risk",
        "high_risk",
        "limited_risk",
    ):
        return "true"
    return "false"


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def get_regulatory_properties(
    component: Component,
    component_result: ComponentResult | None = None,
) -> dict[str, str]:
    """
    Generate regulatory property key-value pairs for an AI/ML component.

    Returns an empty dict for non-AI component types so callers can
    unconditionally merge the result without extra checks.

    Args:
        component: The LCC component.
        component_result: Optional scan result for the component
            (used to resolve the licence expression).

    Returns:
        Dictionary of ``lcc:regulatory:*`` property names to values.
        Empty when the component is not an AI_MODEL or DATASET.
    """
    if not _is_ai_component(component):
        return {}

    resolved_license = _resolve_license(component_result)
    risk = _classify_risk(resolved_license)

    return {
        "lcc:regulatory:framework": "eu_ai_act",
        "lcc:regulatory:risk_classification": risk,
        "lcc:regulatory:copyright_compliance": _copyright_compliance_status(component),
        "lcc:regulatory:training_data_sources": _training_data_sources(component),
        "lcc:regulatory:use_restrictions": _use_restrictions(component),
        "lcc:regulatory:eu_ai_act_article_53": _eu_ai_act_article_53(risk),
        "lcc:regulatory:transparency_required": _transparency_required(risk),
    }


def get_regulatory_annotation_text(
    component: Component,
    component_result: ComponentResult | None = None,
) -> str | None:
    """
    Build a human-readable annotation summarising regulatory metadata.

    Returns ``None`` for non-AI component types.

    Args:
        component: The LCC component.
        component_result: Optional scan result for the component.

    Returns:
        Annotation text string or ``None``.
    """
    props = get_regulatory_properties(component, component_result)
    if not props:
        return None

    lines = [
        "LCC Regulatory Metadata (EU AI Act)",
        f"  Risk classification: {props['lcc:regulatory:risk_classification']}",
        f"  Copyright compliance: {props['lcc:regulatory:copyright_compliance']}",
        f"  Training data sources: {props['lcc:regulatory:training_data_sources']}",
        f"  Use restrictions: {props['lcc:regulatory:use_restrictions']}",
        f"  Article 53 applicable: {props['lcc:regulatory:eu_ai_act_article_53']}",
        f"  Transparency required: {props['lcc:regulatory:transparency_required']}",
    ]
    return "\n".join(lines)
