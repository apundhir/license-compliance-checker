"""
Fallback resolution chain controller.
"""

from __future__ import annotations

from typing import Iterable, List, Set, Tuple

from lcc.models import ComponentFinding, LicenseEvidence
from lcc.resolution.base import Resolver


class FallbackResolver:
    """
    Executes resolvers in priority order and aggregates evidence.
    """

    def __init__(self, resolvers: Iterable[Resolver]) -> None:
        self.resolvers = list(resolvers)

    def resolve(self, finding: ComponentFinding) -> None:
        seen: Set[Tuple[str, str]] = set()
        resolution_path: List[str] = []
        for resolver in self.resolvers:
            try:
                evidences = list(resolver.resolve(finding.component))
            except Exception as exc:  # pragma: no cover - safety net
                finding.component.metadata.setdefault("resolver_errors", []).append({
                    "resolver": resolver.name,
                    "error": str(exc),
                })
                continue
            if evidences:
                resolution_path.append(resolver.name)
            for evidence in evidences:
                key = (evidence.source, evidence.license_expression)
                if key in seen:
                    continue
                seen.add(key)
                finding.evidences.append(evidence)
                assumed = evidence.raw_data.get("assumed_version") if isinstance(evidence.raw_data, dict) else None
                if assumed and finding.component.version in (None, "*"):
                    assumption = {"type": "version", "value": assumed, "source": evidence.source}
                    assumptions = finding.component.metadata.setdefault("assumptions", [])
                    if assumption not in assumptions:
                        assumptions.append(assumption)
                    finding.component.metadata.setdefault("assumed_version", assumed)
                    # Actually update the component version with the assumed version
                    finding.component.version = assumed
                    finding.component.metadata["version_source"] = "assumed_from_" + evidence.source
        if resolution_path:
            finding.component.metadata.setdefault("resolution_path", resolution_path)
        if finding.evidences:
            best = max(finding.evidences, key=lambda ev: ev.confidence)
            finding.resolved_license = best.license_expression
            finding.confidence = best.confidence
        else:
            finding.resolved_license = None
            finding.confidence = 0.0
