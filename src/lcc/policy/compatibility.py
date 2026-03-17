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
License compatibility engine.

Detects conflicts between dependencies including GPL contamination,
copyleft mixing, AGPL in SaaS deployments, and known incompatible
license pairs. This module is additive to the existing policy engine
and works with existing ComponentFinding data.
"""

from __future__ import annotations

import fnmatch
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from lcc.models import ComponentFinding

# ---------------------------------------------------------------------------
# License family sets
# ---------------------------------------------------------------------------

STRONG_COPYLEFT: set[str] = {
    "GPL-2.0",
    "GPL-2.0-only",
    "GPL-2.0-or-later",
    "GPL-3.0",
    "GPL-3.0-only",
    "GPL-3.0-or-later",
}

NETWORK_COPYLEFT: set[str] = {
    "AGPL-3.0",
    "AGPL-3.0-only",
    "AGPL-3.0-or-later",
}

WEAK_COPYLEFT: set[str] = {
    "LGPL-2.0",
    "LGPL-2.1",
    "LGPL-3.0",
    "MPL-2.0",
    "EPL-2.0",
}

SSPL: set[str] = {
    "SSPL-1.0",
}

PERMISSIVE: set[str] = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "Zlib",
    "Unlicense",
    "CC0-1.0",
    "BSL-1.0",
    "PSF-2.0",
}

# Known incompatible license pairs.  Each entry is a tuple of two sets;
# any combination of one license from the first set with one license from
# the second set constitutes a conflict.
INCOMPATIBLE_PAIRS: list[tuple[set[str], set[str]]] = [
    # GPL-2.0 and Apache-2.0 are incompatible (the patent clause in
    # Apache-2.0 creates an "additional restriction" under GPL-2.0).
    ({"GPL-2.0", "GPL-2.0-only"}, {"Apache-2.0"}),
    # The original BSD 4-clause "advertising clause" conflicts with the
    # GPL requirement that no additional restrictions be imposed.
    (STRONG_COPYLEFT, {"BSD-4-Clause"}),
    # Note: GPL-3.0 IS compatible with Apache-2.0 (one-way).
]

# Wildcard patterns used by classify_license for family detection.
_STRONG_COPYLEFT_PATTERNS: list[str] = ["GPL-*"]
_NETWORK_COPYLEFT_PATTERNS: list[str] = ["AGPL-*"]
_WEAK_COPYLEFT_PATTERNS: list[str] = ["LGPL-*", "MPL-*", "EPL-*"]
_SSPL_PATTERNS: list[str] = ["SSPL-*"]
_PERMISSIVE_PATTERNS: list[str] = [
    "MIT",
    "Apache-*",
    "BSD-*",
    "ISC",
    "Zlib",
    "Unlicense",
    "CC0-*",
    "BSL-*",
    "PSF-*",
]

# GPL-2.0-only variants (subset of strong copyleft)
_GPL2_ONLY: set[str] = {"GPL-2.0", "GPL-2.0-only"}
# GPL-3.0 variants (subset of strong copyleft)
_GPL3_VARIANTS: set[str] = {"GPL-3.0", "GPL-3.0-only", "GPL-3.0-or-later"}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class CompatibilityIssue:
    """A single license compatibility problem detected across findings."""

    severity: str  # "critical", "high", "medium", "low"
    issue_type: str  # e.g. "copyleft_contamination", "agpl_saas", ...
    description: str  # Plain-English explanation
    components: list[str]  # Component names involved
    licenses: list[str]  # Licenses involved
    recommendation: str  # Actionable guidance

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompatibilityReport:
    """Aggregated compatibility analysis for a set of findings."""

    project_license: str | None
    context: str | None
    issues: list[CompatibilityIssue] = field(default_factory=list)
    compatible: bool = True  # True if no critical or high issues
    summary: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._recompute()

    def _recompute(self) -> None:
        counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        self.summary = counts
        self.compatible = counts["critical"] == 0 and counts["high"] == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_license": self.project_license,
            "context": self.context,
            "issues": [issue.to_dict() for issue in self.issues],
            "compatible": self.compatible,
            "summary": dict(self.summary),
        }


# ---------------------------------------------------------------------------
# License classification helper
# ---------------------------------------------------------------------------


def classify_license(license_id: str) -> str:
    """Classify a license identifier into a family.

    Returns one of: ``'permissive'``, ``'strong_copyleft'``,
    ``'weak_copyleft'``, ``'network_copyleft'``, ``'sspl'``,
    ``'proprietary'``, or ``'unknown'``.

    Uses :func:`fnmatch.fnmatchcase` for wildcard matching so that
    ``GPL-2.0-only`` matches the ``GPL-*`` pattern, etc.
    """
    if not license_id or license_id.upper() in {"UNKNOWN", "NOASSERTION", "NONE"}:
        return "unknown"

    # Exact-set membership takes priority (fast path).
    if license_id in NETWORK_COPYLEFT:
        return "network_copyleft"
    if license_id in SSPL:
        return "sspl"
    if license_id in STRONG_COPYLEFT:
        return "strong_copyleft"
    if license_id in WEAK_COPYLEFT:
        return "weak_copyleft"
    if license_id in PERMISSIVE:
        return "permissive"

    # Wildcard / pattern matching for identifiers not in the canonical sets.
    # Order matters: network copyleft before strong copyleft because AGPL
    # would also match GPL-*.
    if _matches_any(license_id, _NETWORK_COPYLEFT_PATTERNS):
        return "network_copyleft"
    if _matches_any(license_id, _SSPL_PATTERNS):
        return "sspl"
    # LGPL patterns must be checked before GPL patterns because LGPL-*
    # would also match GPL-* via fnmatch.
    if _matches_any(license_id, _WEAK_COPYLEFT_PATTERNS):
        return "weak_copyleft"
    if _matches_any(license_id, _STRONG_COPYLEFT_PATTERNS):
        return "strong_copyleft"
    if _matches_any(license_id, _PERMISSIVE_PATTERNS):
        return "permissive"

    return "unknown"


# ---------------------------------------------------------------------------
# Compatibility checker
# ---------------------------------------------------------------------------


class LicenseCompatibilityChecker:
    """Detect license compatibility issues across a set of component findings.

    Parameters
    ----------
    project_license:
        The SPDX identifier for the project's own license (e.g. ``"Apache-2.0"``).
        When provided, copyleft contamination checks are performed against it.
    context:
        Deployment context.  One of ``"saas"``, ``"distributed"``,
        ``"internal"``, or ``"library"``.  Affects which checks are active
        (e.g. AGPL-in-SaaS detection).
    """

    def __init__(
        self,
        project_license: Optional[str] = None,
        context: Optional[str] = None,
    ) -> None:
        self.project_license = project_license
        self.context = context

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_compatibility(
        self,
        findings: list[ComponentFinding],
    ) -> CompatibilityReport:
        """Run all compatibility checks and return an aggregated report."""
        issues: list[CompatibilityIssue] = []
        issues.extend(self.check_copyleft_contamination(findings))
        issues.extend(self.check_agpl_in_saas(findings))
        issues.extend(self.check_sspl_in_saas(findings))
        issues.extend(self.check_copyleft_version_conflicts(findings))
        issues.extend(self.check_pairwise_conflicts(findings))
        issues.extend(self.check_weak_copyleft_boundaries(findings))
        issues.extend(self.check_unknown_licenses(findings))

        report = CompatibilityReport(
            project_license=self.project_license,
            context=self.context,
            issues=issues,
        )
        report._recompute()
        return report

    def check_copyleft_contamination(
        self,
        findings: list[ComponentFinding],
    ) -> list[CompatibilityIssue]:
        """Detect strong or network copyleft licenses that would
        contaminate a permissive project."""
        if not self.project_license:
            return []

        project_family = classify_license(self.project_license)
        if project_family not in ("permissive", "weak_copyleft"):
            return []

        issues: list[CompatibilityIssue] = []
        for finding in findings:
            lic = _resolved_license(finding)
            if not lic:
                continue
            family = classify_license(lic)
            if family == "strong_copyleft":
                issues.append(
                    CompatibilityIssue(
                        severity="critical",
                        issue_type="copyleft_contamination",
                        description=(
                            f"{lic} in {finding.component.name} would impose copyleft "
                            f"obligations on your {self.project_license} project. "
                            f"Under {lic}, any work that links to or includes this "
                            f"dependency must be released under the same copyleft terms, "
                            f"which is incompatible with your project's "
                            f"{self.project_license} license."
                        ),
                        components=[finding.component.name],
                        licenses=[lic, self.project_license],
                        recommendation=(
                            f"Replace {finding.component.name} with a permissively "
                            f"licensed alternative, or re-license your project under "
                            f"{lic} to comply with copyleft requirements."
                        ),
                    )
                )
            elif family == "network_copyleft":
                issues.append(
                    CompatibilityIssue(
                        severity="critical",
                        issue_type="copyleft_contamination",
                        description=(
                            f"{lic} in {finding.component.name} would impose network "
                            f"copyleft obligations on your {self.project_license} project. "
                            f"This means any user interacting with the software over a "
                            f"network must be offered the complete source code, which "
                            f"conflicts with your project's {self.project_license} license."
                        ),
                        components=[finding.component.name],
                        licenses=[lic, self.project_license],
                        recommendation=(
                            f"Replace {finding.component.name} with a permissively "
                            f"licensed alternative. AGPL obligations extend to network "
                            f"use, making this incompatible with permissive licensing."
                        ),
                    )
                )
            elif family == "sspl":
                issues.append(
                    CompatibilityIssue(
                        severity="critical",
                        issue_type="copyleft_contamination",
                        description=(
                            f"{lic} in {finding.component.name} imposes service-level "
                            f"copyleft obligations on your {self.project_license} project. "
                            f"SSPL requires that if you offer the software as a service, "
                            f"you must release the complete source code of your entire "
                            f"service stack."
                        ),
                        components=[finding.component.name],
                        licenses=[lic, self.project_license],
                        recommendation=(
                            f"Replace {finding.component.name} with an alternative "
                            f"that uses an OSI-approved license. SSPL is not considered "
                            f"open source by most organisations."
                        ),
                    )
                )
        return issues

    def check_agpl_in_saas(
        self,
        findings: list[ComponentFinding],
    ) -> list[CompatibilityIssue]:
        """Detect AGPL-licensed components in a SaaS deployment context."""
        if self.context != "saas":
            return []

        issues: list[CompatibilityIssue] = []
        for finding in findings:
            lic = _resolved_license(finding)
            if not lic:
                continue
            if classify_license(lic) == "network_copyleft":
                issues.append(
                    CompatibilityIssue(
                        severity="critical",
                        issue_type="agpl_saas",
                        description=(
                            f"{finding.component.name} is licensed under {lic}, which "
                            f"requires that users who interact with the software over "
                            f"a network must be provided with the complete source code. "
                            f"In a SaaS deployment this means you must disclose your "
                            f"entire service source code to all users."
                        ),
                        components=[finding.component.name],
                        licenses=[lic],
                        recommendation=(
                            f"Replace {finding.component.name} with a permissively "
                            f"licensed alternative, or ensure full source code disclosure "
                            f"for your SaaS offering as required by {lic}."
                        ),
                    )
                )
        return issues

    def check_sspl_in_saas(
        self,
        findings: list[ComponentFinding],
    ) -> list[CompatibilityIssue]:
        """Detect SSPL-licensed components in a SaaS deployment context."""
        if self.context != "saas":
            return []

        issues: list[CompatibilityIssue] = []
        for finding in findings:
            lic = _resolved_license(finding)
            if not lic:
                continue
            if classify_license(lic) == "sspl":
                issues.append(
                    CompatibilityIssue(
                        severity="critical",
                        issue_type="sspl_saas",
                        description=(
                            f"{finding.component.name} is licensed under {lic}, which "
                            f"requires you to release the complete source code of your "
                            f"entire service stack if you offer the software as a service. "
                            f"This is incompatible with most SaaS business models."
                        ),
                        components=[finding.component.name],
                        licenses=[lic],
                        recommendation=(
                            f"Replace {finding.component.name} with an OSI-approved "
                            f"alternative. SSPL is specifically designed to restrict "
                            f"service-based deployments."
                        ),
                    )
                )
        return issues

    def check_copyleft_version_conflicts(
        self,
        findings: list[ComponentFinding],
    ) -> list[CompatibilityIssue]:
        """Detect version conflicts among strong copyleft licenses.

        For example, GPL-2.0-only and GPL-3.0-only are not compatible
        because GPL-2.0-only cannot be upgraded to GPL-3.0, and code
        licensed under different GPL versions cannot be combined.
        """
        gpl2_components: list[tuple[str, str]] = []
        gpl3_components: list[tuple[str, str]] = []

        for finding in findings:
            lic = _resolved_license(finding)
            if not lic:
                continue
            if lic in _GPL2_ONLY:
                gpl2_components.append((finding.component.name, lic))
            elif lic in _GPL3_VARIANTS:
                gpl3_components.append((finding.component.name, lic))

        if gpl2_components and gpl3_components:
            all_components = [name for name, _ in gpl2_components + gpl3_components]
            all_licenses = sorted(
                {lic for _, lic in gpl2_components + gpl3_components}
            )
            return [
                CompatibilityIssue(
                    severity="high",
                    issue_type="copyleft_version_conflict",
                    description=(
                        f"Your dependencies include both GPL-2.0 and GPL-3.0 licensed "
                        f"components. GPL-2.0-only code cannot be combined with "
                        f"GPL-3.0 code because the licenses have incompatible "
                        f"additional terms. This conflict prevents legally distributing "
                        f"a combined work."
                    ),
                    components=all_components,
                    licenses=all_licenses,
                    recommendation=(
                        "Check whether the GPL-2.0 components use the "
                        "'or later' clause (GPL-2.0-or-later), which would allow "
                        "upgrading to GPL-3.0. If not, replace one set of "
                        "components to unify GPL versions."
                    ),
                )
            ]
        return []

    def check_pairwise_conflicts(
        self,
        findings: list[ComponentFinding],
    ) -> list[CompatibilityIssue]:
        """Check for known incompatible license pairs among findings."""
        issues: list[CompatibilityIssue] = []

        # Build a mapping from license to the components that use it.
        license_to_components: dict[str, list[str]] = {}
        for finding in findings:
            lic = _resolved_license(finding)
            if lic:
                license_to_components.setdefault(lic, []).append(
                    finding.component.name
                )

        present_licenses = set(license_to_components.keys())

        for set_a, set_b in INCOMPATIBLE_PAIRS:
            matched_a = present_licenses & set_a
            matched_b = present_licenses & set_b
            if matched_a and matched_b:
                components_involved: list[str] = []
                for lic in matched_a | matched_b:
                    components_involved.extend(license_to_components[lic])
                licenses_involved = sorted(matched_a | matched_b)
                issues.append(
                    CompatibilityIssue(
                        severity="high",
                        issue_type="license_conflict",
                        description=(
                            f"Incompatible license combination detected: "
                            f"{', '.join(sorted(matched_a))} cannot be combined with "
                            f"{', '.join(sorted(matched_b))}. These licenses have "
                            f"conflicting terms that prevent legal distribution of a "
                            f"combined work."
                        ),
                        components=components_involved,
                        licenses=licenses_involved,
                        recommendation=(
                            "Replace one of the conflicting components with an "
                            "alternative that uses a compatible license, or consult "
                            "legal counsel to evaluate whether an exception applies."
                        ),
                    )
                )

        # Also check the project license against dependency licenses.
        if self.project_license and self.project_license in present_licenses:
            # Already covered above since project license is in findings.
            pass
        elif self.project_license:
            for set_a, set_b in INCOMPATIBLE_PAIRS:
                if self.project_license in set_a:
                    matched = present_licenses & set_b
                    if matched:
                        components_involved = []
                        for lic in matched:
                            components_involved.extend(license_to_components[lic])
                        issues.append(
                            CompatibilityIssue(
                                severity="high",
                                issue_type="license_conflict",
                                description=(
                                    f"Your project license {self.project_license} is "
                                    f"incompatible with {', '.join(sorted(matched))} "
                                    f"used by your dependencies. These licenses have "
                                    f"conflicting terms that prevent legal distribution."
                                ),
                                components=components_involved,
                                licenses=[self.project_license] + sorted(matched),
                                recommendation=(
                                    "Replace the conflicting dependencies or change "
                                    "your project license to resolve the conflict."
                                ),
                            )
                        )
                elif self.project_license in set_b:
                    matched = present_licenses & set_a
                    if matched:
                        components_involved = []
                        for lic in matched:
                            components_involved.extend(license_to_components[lic])
                        issues.append(
                            CompatibilityIssue(
                                severity="high",
                                issue_type="license_conflict",
                                description=(
                                    f"Your project license {self.project_license} is "
                                    f"incompatible with {', '.join(sorted(matched))} "
                                    f"used by your dependencies. These licenses have "
                                    f"conflicting terms that prevent legal distribution."
                                ),
                                components=components_involved,
                                licenses=[self.project_license] + sorted(matched),
                                recommendation=(
                                    "Replace the conflicting dependencies or change "
                                    "your project license to resolve the conflict."
                                ),
                            )
                        )
        return issues

    def check_weak_copyleft_boundaries(
        self,
        findings: list[ComponentFinding],
    ) -> list[CompatibilityIssue]:
        """Flag weak copyleft dependencies that require boundary awareness."""
        issues: list[CompatibilityIssue] = []
        for finding in findings:
            lic = _resolved_license(finding)
            if not lic:
                continue
            if classify_license(lic) == "weak_copyleft":
                if _matches_any(lic, ["LGPL-*"]):
                    issues.append(
                        CompatibilityIssue(
                            severity="medium",
                            issue_type="weak_copyleft_boundary",
                            description=(
                                f"{finding.component.name} is licensed under {lic}. "
                                f"LGPL allows use in proprietary software only if you "
                                f"link dynamically and allow users to replace the LGPL "
                                f"library. Static linking may trigger full copyleft "
                                f"obligations."
                            ),
                            components=[finding.component.name],
                            licenses=[lic],
                            recommendation=(
                                "Ensure dynamic linking to this component and include "
                                "attribution notices. If statically linking, the LGPL "
                                "requires you to provide object files that allow "
                                "re-linking, or release your code under the LGPL."
                            ),
                        )
                    )
                elif _matches_any(lic, ["MPL-*"]):
                    issues.append(
                        CompatibilityIssue(
                            severity="medium",
                            issue_type="weak_copyleft_boundary",
                            description=(
                                f"{finding.component.name} is licensed under {lic}. "
                                f"MPL requires that modifications to MPL-licensed files "
                                f"must be released under the MPL, but new files in your "
                                f"project can use any license."
                            ),
                            components=[finding.component.name],
                            licenses=[lic],
                            recommendation=(
                                "Do not modify MPL-licensed source files unless you are "
                                "prepared to release those modifications under the MPL. "
                                "Keep MPL-licensed code in separate files from your "
                                "proprietary code."
                            ),
                        )
                    )
                elif _matches_any(lic, ["EPL-*"]):
                    issues.append(
                        CompatibilityIssue(
                            severity="medium",
                            issue_type="weak_copyleft_boundary",
                            description=(
                                f"{finding.component.name} is licensed under {lic}. "
                                f"EPL requires that modifications to EPL-licensed "
                                f"modules must be released under the EPL. Commercial "
                                f"distribution may also trigger patent grant obligations."
                            ),
                            components=[finding.component.name],
                            licenses=[lic],
                            recommendation=(
                                "Keep EPL-licensed code in separate modules. Review "
                                "patent clauses if distributing commercially."
                            ),
                        )
                    )
                else:
                    # Generic weak copyleft fallback
                    issues.append(
                        CompatibilityIssue(
                            severity="medium",
                            issue_type="weak_copyleft_boundary",
                            description=(
                                f"{finding.component.name} is licensed under {lic}, "
                                f"which is a weak copyleft license. Modifications to "
                                f"the licensed code must be released under the same "
                                f"terms, but your own code can remain under a different "
                                f"license if properly separated."
                            ),
                            components=[finding.component.name],
                            licenses=[lic],
                            recommendation=(
                                "Maintain clear boundaries between this component and "
                                "your proprietary code. Consult the specific license "
                                "terms for linking and modification requirements."
                            ),
                        )
                    )
        return issues

    def check_unknown_licenses(
        self,
        findings: list[ComponentFinding],
    ) -> list[CompatibilityIssue]:
        """Flag components with unknown or unresolved licenses."""
        issues: list[CompatibilityIssue] = []
        for finding in findings:
            lic = _resolved_license(finding)
            if not lic:
                issues.append(
                    CompatibilityIssue(
                        severity="low",
                        issue_type="unknown_license",
                        description=(
                            f"{finding.component.name} has no resolved license. "
                            f"Without knowing the license terms, it is impossible to "
                            f"determine compatibility with your project or other "
                            f"dependencies."
                        ),
                        components=[finding.component.name],
                        licenses=["UNKNOWN"],
                        recommendation=(
                            f"Investigate the license for {finding.component.name} by "
                            f"checking its repository, package metadata, or contacting "
                            f"the author. Do not distribute until the license is known."
                        ),
                    )
                )
            elif classify_license(lic) == "unknown":
                issues.append(
                    CompatibilityIssue(
                        severity="low",
                        issue_type="unknown_license",
                        description=(
                            f"{finding.component.name} uses license '{lic}', which is "
                            f"not recognized by the compatibility engine. This may be "
                            f"a custom, proprietary, or non-standard license that "
                            f"requires manual review."
                        ),
                        components=[finding.component.name],
                        licenses=[lic],
                        recommendation=(
                            f"Review the full text of '{lic}' to determine "
                            f"compatibility with your project. Consider consulting "
                            f"legal counsel for non-standard licenses."
                        ),
                    )
                )
        return issues


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def evaluate_license_compatibility(
    findings: list[ComponentFinding],
    project_license: Optional[str] = None,
    context: Optional[str] = None,
) -> CompatibilityReport:
    """Evaluate license compatibility across a set of component findings.

    This is the primary entry point for the compatibility engine.  It
    creates a :class:`LicenseCompatibilityChecker` with the given
    parameters and runs all compatibility checks against the provided
    findings.

    Parameters
    ----------
    findings:
        Component findings from a scan (the same objects used by the
        policy engine).
    project_license:
        SPDX identifier for the project's own license (e.g.
        ``"Apache-2.0"``).
    context:
        Deployment context: ``"saas"``, ``"distributed"``,
        ``"internal"``, or ``"library"``.

    Returns
    -------
    CompatibilityReport
        Aggregated report with all detected issues, a compatibility
        flag, and a severity summary.
    """
    checker = LicenseCompatibilityChecker(
        project_license=project_license,
        context=context,
    )
    return checker.check_compatibility(findings)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _matches_any(value: str, patterns: list[str]) -> bool:
    """Return ``True`` if *value* matches any of the fnmatch *patterns*."""
    return any(fnmatch.fnmatchcase(value, pat) for pat in patterns)


def _resolved_license(finding: ComponentFinding) -> str | None:
    """Extract the resolved license from a finding, returning ``None``
    for empty, unknown, or unresolved values."""
    lic = finding.resolved_license
    if not lic:
        return None
    if lic.upper() in {"UNKNOWN", "NOASSERTION", "NONE"}:
        return None
    return lic
