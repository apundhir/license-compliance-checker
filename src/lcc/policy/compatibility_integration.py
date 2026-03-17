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
Integration glue between the compatibility engine and the scan/policy workflow.

Reads optional ``compatibility`` settings from policy YAML documents,
creates a :class:`LicenseCompatibilityChecker` with the appropriate
flags, and returns a :class:`CompatibilityReport`.
"""

from __future__ import annotations

from typing import Any, Optional

from lcc.models import ComponentFinding
from lcc.policy.compatibility import (
    CompatibilityIssue,
    CompatibilityReport,
    LicenseCompatibilityChecker,
)


def run_compatibility_check(
    findings: list[ComponentFinding],
    policy: Optional[dict[str, Any]] = None,
    context: Optional[str] = None,
    project_license: Optional[str] = None,
) -> CompatibilityReport:
    """Run compatibility check using policy configuration.

    Parameters
    ----------
    findings:
        Component findings from a completed scan.
    policy:
        Loaded policy document (dict).  If it contains a ``compatibility``
        section the settings therein control which checks are active.
    context:
        Deployment context (``"saas"``, ``"distributed"``, ``"internal"``,
        ``"library"``).  Passed to the checker for context-sensitive
        checks like AGPL-in-SaaS detection.
    project_license:
        SPDX identifier for the project's own license.  Overrides any
        ``project_license`` value found in the policy's compatibility
        section.

    Returns
    -------
    CompatibilityReport
        Aggregated report with all detected issues.
    """
    compat_config = _extract_compat_config(policy)

    # Resolve effective project license (CLI flag takes precedence)
    effective_license = project_license or compat_config.get("project_license")

    checker = LicenseCompatibilityChecker(
        project_license=effective_license,
        context=context,
    )

    # Run all individual checks, filtering by policy configuration
    issues: list[CompatibilityIssue] = []

    if compat_config.get("check_contamination", True):
        issues.extend(checker.check_copyleft_contamination(findings))

    if compat_config.get("check_agpl_saas", True):
        issues.extend(checker.check_agpl_in_saas(findings))
        issues.extend(checker.check_sspl_in_saas(findings))

    # Always check version conflicts (subset of pairwise)
    issues.extend(checker.check_copyleft_version_conflicts(findings))

    if compat_config.get("check_pairwise", True):
        issues.extend(checker.check_pairwise_conflicts(findings))

    if compat_config.get("check_weak_copyleft", True):
        issues.extend(checker.check_weak_copyleft_boundaries(findings))

    # Always check unknown licenses -- low severity, informational
    issues.extend(checker.check_unknown_licenses(findings))

    report = CompatibilityReport(
        project_license=effective_license,
        context=context,
        issues=issues,
    )
    report._recompute()
    return report


def policy_has_compatibility(policy: Optional[dict[str, Any]]) -> bool:
    """Return ``True`` if the policy document contains a ``compatibility`` section."""
    if not policy or not isinstance(policy, dict):
        return False
    return isinstance(policy.get("compatibility"), dict)


def _extract_compat_config(policy: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Extract the ``compatibility`` section from a policy, with defaults."""
    defaults: dict[str, Any] = {
        "project_license": None,
        "check_contamination": True,
        "check_agpl_saas": True,
        "check_pairwise": True,
        "check_weak_copyleft": True,
    }
    if not policy or not isinstance(policy, dict):
        return defaults
    section = policy.get("compatibility")
    if not isinstance(section, dict):
        return defaults
    merged = dict(defaults)
    merged.update(section)
    return merged
