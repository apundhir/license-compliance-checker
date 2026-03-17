"""
Accuracy benchmark for LCC license detection.

Measures:
- Overall accuracy (correct license / total components)
- Per-ecosystem accuracy
- False positive rate (wrong license assigned)
- False negative rate (license not detected)
- Unknown rate (license could not be resolved)
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lcc.cache import Cache
from lcc.config import LCCConfig
from lcc.models import ComponentFinding
from lcc.scanner import Scanner


# ---------------------------------------------------------------------------
# Ground truth helpers
# ---------------------------------------------------------------------------

@dataclass
class DetectionResult:
    """Result of comparing a single component detection against ground truth."""
    component_name: str
    expected_license: str
    detected_license: Optional[str]
    confidence: float
    correct: bool
    classification: str  # "true_positive", "false_positive", "false_negative", "unknown"


@dataclass
class EcosystemMetrics:
    """Accuracy metrics for a single ecosystem."""
    ecosystem: str
    total_components: int = 0
    correct: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    unknowns: int = 0
    details: List[DetectionResult] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total_components if self.total_components > 0 else 0.0

    @property
    def false_positive_rate(self) -> float:
        return self.false_positives / self.total_components if self.total_components > 0 else 0.0

    @property
    def false_negative_rate(self) -> float:
        return self.false_negatives / self.total_components if self.total_components > 0 else 0.0

    @property
    def unknown_rate(self) -> float:
        return self.unknowns / self.total_components if self.total_components > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ecosystem": self.ecosystem,
            "total_components": self.total_components,
            "correct": self.correct,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "unknowns": self.unknowns,
            "accuracy": round(self.accuracy, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "false_negative_rate": round(self.false_negative_rate, 4),
            "unknown_rate": round(self.unknown_rate, 4),
        }


@dataclass
class AccuracyResults:
    """Aggregated accuracy benchmark results."""
    timestamp: str = ""
    duration_seconds: float = 0.0
    total_projects: int = 0
    total_components: int = 0
    overall_correct: int = 0
    overall_false_positives: int = 0
    overall_false_negatives: int = 0
    overall_unknowns: int = 0
    per_ecosystem: Dict[str, EcosystemMetrics] = field(default_factory=dict)
    project_results: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def overall_accuracy(self) -> float:
        return self.overall_correct / self.total_components if self.total_components > 0 else 0.0

    @property
    def overall_false_positive_rate(self) -> float:
        return self.overall_false_positives / self.total_components if self.total_components > 0 else 0.0

    @property
    def overall_false_negative_rate(self) -> float:
        return self.overall_false_negatives / self.total_components if self.total_components > 0 else 0.0

    @property
    def overall_unknown_rate(self) -> float:
        return self.overall_unknowns / self.total_components if self.total_components > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "duration_seconds": round(self.duration_seconds, 3),
            "summary": {
                "total_projects": self.total_projects,
                "total_components": self.total_components,
                "overall_accuracy": round(self.overall_accuracy, 4),
                "overall_false_positive_rate": round(self.overall_false_positive_rate, 4),
                "overall_false_negative_rate": round(self.overall_false_negative_rate, 4),
                "overall_unknown_rate": round(self.overall_unknown_rate, 4),
                "correct": self.overall_correct,
                "false_positives": self.overall_false_positives,
                "false_negatives": self.overall_false_negatives,
                "unknowns": self.overall_unknowns,
            },
            "per_ecosystem": {
                name: metrics.to_dict()
                for name, metrics in sorted(self.per_ecosystem.items())
            },
            "project_results": self.project_results,
        }

    def to_markdown(self) -> str:
        lines = [
            "# LCC Accuracy Benchmark Results",
            "",
            f"**Date:** {self.timestamp}",
            f"**Duration:** {self.duration_seconds:.1f}s",
            f"**Projects evaluated:** {self.total_projects}",
            f"**Total components:** {self.total_components}",
            "",
            "## Overall Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Accuracy | {self.overall_accuracy:.1%} |",
            f"| False Positive Rate | {self.overall_false_positive_rate:.1%} |",
            f"| False Negative Rate | {self.overall_false_negative_rate:.1%} |",
            f"| Unknown Rate | {self.overall_unknown_rate:.1%} |",
            "",
            "## Per-Ecosystem Breakdown",
            "",
            "| Ecosystem | Components | Accuracy | FP Rate | FN Rate | Unknown Rate |",
            "|-----------|-----------|----------|---------|---------|--------------|",
        ]
        for name in sorted(self.per_ecosystem):
            m = self.per_ecosystem[name]
            lines.append(
                f"| {name} | {m.total_components} | {m.accuracy:.1%} | "
                f"{m.false_positive_rate:.1%} | {m.false_negative_rate:.1%} | "
                f"{m.unknown_rate:.1%} |"
            )

        lines.extend([
            "",
            "## Per-Project Results",
            "",
            "| Project | Ecosystem | Components | Correct | FP | FN | Unknown |",
            "|---------|-----------|-----------|---------|----|----|---------|",
        ])
        for pr in self.project_results:
            lines.append(
                f"| {pr['name']} | {pr['ecosystem']} | {pr['total']} | "
                f"{pr['correct']} | {pr['false_positives']} | "
                f"{pr['false_negatives']} | {pr['unknowns']} |"
            )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# License normalization
# ---------------------------------------------------------------------------

# Map common license variations to canonical SPDX identifiers for comparison.
LICENSE_ALIASES: Dict[str, str] = {
    "apache license 2.0": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "apache2": "Apache-2.0",
    "mit license": "MIT",
    "mit": "MIT",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd 3-clause": "BSD-3-Clause",
    "bsd-3-clause license": "BSD-3-Clause",
    "new bsd license": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd 2-clause": "BSD-2-Clause",
    "simplified bsd license": "BSD-2-Clause",
    "isc license": "ISC",
    "isc": "ISC",
    "mpl-2.0": "MPL-2.0",
    "mozilla public license 2.0": "MPL-2.0",
    "gpl-2.0": "GPL-2.0",
    "gpl-3.0": "GPL-3.0",
    "gpl": "GPL",
    "lgpl-2.1": "LGPL-2.1",
    "lgpl-3.0": "LGPL-3.0",
    "lgpl": "LGPL",
    "epl-1.0": "EPL-1.0",
    "epl-2.0": "EPL-2.0",
    "unlicense": "Unlicense",
    "psf-2.0": "PSF-2.0",
    "python software foundation license": "PSF-2.0",
}


def normalize_license(license_str: Optional[str]) -> Optional[str]:
    """Normalize a license string to its canonical SPDX form for comparison."""
    if license_str is None:
        return None
    cleaned = license_str.strip()
    if not cleaned or cleaned.upper() == "UNKNOWN":
        return None
    lower = cleaned.lower()
    return LICENSE_ALIASES.get(lower, cleaned)


def licenses_match(detected: Optional[str], expected: str) -> bool:
    """Check if a detected license matches the expected ground truth."""
    norm_detected = normalize_license(detected)
    norm_expected = normalize_license(expected)
    if norm_detected is None or norm_expected is None:
        return False
    # Exact match
    if norm_detected.lower() == norm_expected.lower():
        return True
    # Partial match — the detected expression contains the expected identifier
    if norm_expected.lower() in norm_detected.lower():
        return True
    # Handle compound expressions like "MIT AND Apache-2.0"
    if " AND " in (norm_detected or "") or " OR " in (norm_detected or ""):
        parts = norm_detected.replace(" AND ", "|").replace(" OR ", "|").split("|")
        return any(p.strip().lower() == norm_expected.lower() for p in parts)
    return False


# ---------------------------------------------------------------------------
# Manifest generators — create minimal realistic fixture files
# ---------------------------------------------------------------------------

def _create_python_manifest(project_dir: Path, project: Dict) -> None:
    """Create a requirements.txt file from project dependencies."""
    deps = project.get("dependencies", [])
    lines = []
    for dep in deps:
        name = dep["name"]
        version = dep.get("version")
        if version:
            lines.append(f"{name}=={version}")
        else:
            lines.append(name)
    (project_dir / "requirements.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _create_javascript_manifest(project_dir: Path, project: Dict) -> None:
    """Create a package.json file from project dependencies."""
    deps = project.get("dependencies", [])
    pkg_deps = {}
    pkg_name = project["name"]
    pkg_version = "1.0.0"
    pkg_license = project.get("known_license", "MIT")

    for dep in deps:
        name = dep["name"]
        version = dep.get("version", "*")
        if name == pkg_name:
            pkg_version = version
            continue
        pkg_deps[name] = f"^{version}" if version else "*"

    package_json = {
        "name": pkg_name,
        "version": pkg_version,
        "license": pkg_license,
        "dependencies": pkg_deps,
    }
    (project_dir / "package.json").write_text(
        json.dumps(package_json, indent=2) + "\n", encoding="utf-8"
    )


def _create_go_manifest(project_dir: Path, project: Dict) -> None:
    """Create a go.mod file from project dependencies."""
    deps = project.get("dependencies", [])
    module_name = f"github.com/benchmark/{project['name']}"
    lines = [f"module {module_name}", "", "go 1.22", "", "require ("]
    for dep in deps:
        name = dep["name"]
        version = dep.get("version", "v0.0.0")
        if name == module_name:
            continue
        lines.append(f"\t{name} {version}")
    lines.append(")")
    (project_dir / "go.mod").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _create_java_manifest(project_dir: Path, project: Dict) -> None:
    """Create a pom.xml file from project dependencies."""
    deps = project.get("dependencies", [])
    pom_deps = []
    for dep in deps:
        name = dep["name"]
        version = dep.get("version", "1.0.0")
        parts = name.split(":")
        if len(parts) == 2:
            group_id, artifact_id = parts
        else:
            group_id = name
            artifact_id = name.split(".")[-1]
        pom_deps.append(
            f"    <dependency>\n"
            f"      <groupId>{group_id}</groupId>\n"
            f"      <artifactId>{artifact_id}</artifactId>\n"
            f"      <version>{version}</version>\n"
            f"    </dependency>"
        )
    pom_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<project xmlns="http://maven.apache.org/POM/4.0.0"\n'
        '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        '         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 '
        'http://maven.apache.org/xsd/maven-4.0.0.xsd">\n'
        "  <modelVersion>4.0.0</modelVersion>\n"
        f"  <groupId>com.benchmark</groupId>\n"
        f"  <artifactId>{project['name']}</artifactId>\n"
        f"  <version>1.0.0</version>\n"
        "  <dependencies>\n" +
        "\n".join(pom_deps) + "\n"
        "  </dependencies>\n"
        "</project>\n"
    )
    (project_dir / "pom.xml").write_text(pom_xml, encoding="utf-8")


def _create_rust_manifest(project_dir: Path, project: Dict) -> None:
    """Create a Cargo.toml file from project dependencies."""
    deps = project.get("dependencies", [])
    lines = [
        "[package]",
        f'name = "{project["name"]}"',
        'version = "0.1.0"',
        'edition = "2021"',
        "",
        "[dependencies]",
    ]
    for dep in deps:
        name = dep["name"]
        version = dep.get("version", "0.1.0")
        if name == project["name"]:
            continue
        lines.append(f'{name} = "{version}"')
    (project_dir / "Cargo.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _create_ruby_manifest(project_dir: Path, project: Dict) -> None:
    """Create a Gemfile and Gemfile.lock from project dependencies."""
    deps = project.get("dependencies", [])
    gemfile_lines = ['source "https://rubygems.org"', ""]
    lock_lines = ["GEM", "  remote: https://rubygems.org/", "  specs:"]
    for dep in deps:
        name = dep["name"]
        version = dep.get("version")
        if version:
            gemfile_lines.append(f"gem '{name}', '~> {version}'")
            lock_lines.append(f"    {name} ({version})")
        else:
            gemfile_lines.append(f"gem '{name}'")
    lock_lines.extend(["", "PLATFORMS", "  ruby", "", "DEPENDENCIES"])
    for dep in deps:
        lock_lines.append(f"  {dep['name']}")
    (project_dir / "Gemfile").write_text("\n".join(gemfile_lines) + "\n", encoding="utf-8")
    (project_dir / "Gemfile.lock").write_text("\n".join(lock_lines) + "\n", encoding="utf-8")


def _create_dotnet_manifest(project_dir: Path, project: Dict) -> None:
    """Create a .csproj file from project dependencies."""
    deps = project.get("dependencies", [])
    refs = []
    for dep in deps:
        name = dep["name"]
        version = dep.get("version", "1.0.0")
        refs.append(f'    <PackageReference Include="{name}" Version="{version}" />')
    csproj = (
        '<Project Sdk="Microsoft.NET.Sdk">\n'
        "  <PropertyGroup>\n"
        "    <TargetFramework>net9.0</TargetFramework>\n"
        "  </PropertyGroup>\n"
        "  <ItemGroup>\n" +
        "\n".join(refs) + "\n"
        "  </ItemGroup>\n"
        "</Project>\n"
    )
    manifest_name = project.get("manifest_file", "app.csproj")
    (project_dir / manifest_name).write_text(csproj, encoding="utf-8")


MANIFEST_GENERATORS = {
    "python": _create_python_manifest,
    "javascript": _create_javascript_manifest,
    "go": _create_go_manifest,
    "java": _create_java_manifest,
    "rust": _create_rust_manifest,
    "ruby": _create_ruby_manifest,
    "dotnet": _create_dotnet_manifest,
}


# ---------------------------------------------------------------------------
# Build the Scanner in offline / benchmark mode
# ---------------------------------------------------------------------------

def _build_benchmark_scanner() -> Tuple[Scanner, Path]:
    """
    Build a Scanner configured for offline benchmarking.

    Returns the scanner and a temporary cache directory (caller is responsible
    for cleaning up if desired, though it uses tempdir).
    """
    config = LCCConfig(offline=True)
    cache_dir = Path(tempfile.mkdtemp(prefix="lcc_bench_cache_"))
    config.cache_dir = cache_dir
    cache = Cache(config)

    # Import factory and build components
    from lcc.factory import build_detectors, build_resolvers
    detectors = build_detectors(config)
    resolvers = build_resolvers(config, cache)
    scanner = Scanner(detectors, resolvers, config)
    return scanner, cache_dir


# ---------------------------------------------------------------------------
# Classify a single finding against ground truth
# ---------------------------------------------------------------------------

def _classify_finding(
    finding: ComponentFinding,
    ground_truth: Dict[str, str],
) -> DetectionResult:
    """
    Compare a single ComponentFinding against the ground truth license map.

    ground_truth maps component name -> expected SPDX license.
    """
    component_name = finding.component.name
    detected = finding.resolved_license
    expected = ground_truth.get(component_name)

    if expected is None:
        # Component not in ground truth — we cannot evaluate it, skip
        classification = "unlisted"
        return DetectionResult(
            component_name=component_name,
            expected_license="(not in corpus)",
            detected_license=detected,
            confidence=finding.confidence,
            correct=False,
            classification=classification,
        )

    if detected is None or normalize_license(detected) is None:
        # License was not resolved
        return DetectionResult(
            component_name=component_name,
            expected_license=expected,
            detected_license=detected,
            confidence=finding.confidence,
            correct=False,
            classification="false_negative",
        )

    if licenses_match(detected, expected):
        return DetectionResult(
            component_name=component_name,
            expected_license=expected,
            detected_license=detected,
            confidence=finding.confidence,
            correct=True,
            classification="true_positive",
        )

    # A license was detected but it is wrong
    return DetectionResult(
        component_name=component_name,
        expected_license=expected,
        detected_license=detected,
        confidence=finding.confidence,
        correct=False,
        classification="false_positive",
    )


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------

def load_corpus(corpus_path: Optional[Path] = None) -> List[Dict]:
    """Load the benchmark corpus manifest."""
    if corpus_path is None:
        corpus_path = Path(__file__).parent / "corpus" / "manifest.json"
    with open(corpus_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["projects"]


def run_accuracy_benchmark(
    corpus_path: Optional[Path] = None,
    ecosystems: Optional[List[str]] = None,
    verbose: bool = False,
) -> AccuracyResults:
    """
    Run the full accuracy benchmark.

    Args:
        corpus_path: Path to corpus manifest.json (defaults to bundled corpus).
        ecosystems: If set, only benchmark these ecosystems.
        verbose: Print progress to stdout.

    Returns:
        AccuracyResults with all metrics.
    """
    from datetime import datetime, timezone

    projects = load_corpus(corpus_path)
    if ecosystems:
        projects = [p for p in projects if p["ecosystem"] in ecosystems]

    results = AccuracyResults(
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_projects=len(projects),
    )

    scanner, cache_dir = _build_benchmark_scanner()
    start_time = time.time()

    for project in projects:
        ecosystem = project["ecosystem"]
        project_name = project["name"]

        if verbose:
            print(f"  [{ecosystem}] {project_name} ...", end=" ", flush=True)

        # Ensure ecosystem metrics exist
        if ecosystem not in results.per_ecosystem:
            results.per_ecosystem[ecosystem] = EcosystemMetrics(ecosystem=ecosystem)
        eco_metrics = results.per_ecosystem[ecosystem]

        # Build ground truth for this project
        ground_truth: Dict[str, str] = {}
        for dep in project.get("dependencies", []):
            ground_truth[dep["name"]] = dep["license"]

        # Create temporary project directory with manifest
        with tempfile.TemporaryDirectory(prefix=f"lcc_bench_{project_name}_") as tmp_dir:
            project_dir = Path(tmp_dir)
            generator = MANIFEST_GENERATORS.get(ecosystem)
            if generator is None:
                if verbose:
                    print("SKIP (no generator)")
                continue
            generator(project_dir, project)

            # Run scanner
            try:
                report = scanner.scan(project_dir)
            except Exception as exc:
                if verbose:
                    print(f"ERROR: {exc}")
                results.project_results.append({
                    "name": project_name,
                    "ecosystem": ecosystem,
                    "total": len(ground_truth),
                    "correct": 0,
                    "false_positives": 0,
                    "false_negatives": len(ground_truth),
                    "unknowns": 0,
                    "error": str(exc),
                })
                eco_metrics.total_components += len(ground_truth)
                eco_metrics.false_negatives += len(ground_truth)
                results.total_components += len(ground_truth)
                results.overall_false_negatives += len(ground_truth)
                continue

            # Classify each finding
            project_correct = 0
            project_fp = 0
            project_fn = 0
            project_unknowns = 0
            matched_ground_truth_keys: set = set()

            for finding in report.findings:
                result = _classify_finding(finding, ground_truth)

                if result.classification == "unlisted":
                    # Not in ground truth — ignore for metrics
                    continue

                matched_ground_truth_keys.add(finding.component.name)

                if result.correct:
                    project_correct += 1
                    eco_metrics.correct += 1
                    results.overall_correct += 1
                elif result.classification == "false_positive":
                    project_fp += 1
                    eco_metrics.false_positives += 1
                    results.overall_false_positives += 1
                elif result.classification == "false_negative":
                    project_fn += 1
                    eco_metrics.false_negatives += 1
                    results.overall_false_negatives += 1

                eco_metrics.details.append(result)

            # Count components in ground truth that were never detected at all
            for dep_name in ground_truth:
                if dep_name not in matched_ground_truth_keys:
                    project_unknowns += 1
                    eco_metrics.unknowns += 1
                    results.overall_unknowns += 1

            total_evaluated = project_correct + project_fp + project_fn + project_unknowns
            eco_metrics.total_components += total_evaluated
            results.total_components += total_evaluated

            results.project_results.append({
                "name": project_name,
                "ecosystem": ecosystem,
                "total": total_evaluated,
                "correct": project_correct,
                "false_positives": project_fp,
                "false_negatives": project_fn,
                "unknowns": project_unknowns,
            })

            if verbose:
                acc_pct = project_correct / total_evaluated * 100 if total_evaluated else 0
                print(f"{project_correct}/{total_evaluated} ({acc_pct:.0f}%)")

    results.duration_seconds = time.time() - start_time
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="LCC Accuracy Benchmark")
    parser.add_argument("--corpus", type=Path, help="Path to corpus manifest.json")
    parser.add_argument("--ecosystem", action="append", dest="ecosystems", help="Filter by ecosystem (repeatable)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress")
    parser.add_argument("--output", type=Path, help="Write JSON results to file")
    parser.add_argument("--markdown", type=Path, help="Write markdown report to file")
    args = parser.parse_args()

    print("=" * 60)
    print("LCC Accuracy Benchmark")
    print("=" * 60)
    print()

    results = run_accuracy_benchmark(
        corpus_path=args.corpus,
        ecosystems=args.ecosystems,
        verbose=args.verbose,
    )

    # Print summary
    print()
    print(f"Completed in {results.duration_seconds:.1f}s")
    print(f"Projects: {results.total_projects}")
    print(f"Components: {results.total_components}")
    print(f"Overall accuracy: {results.overall_accuracy:.1%}")
    print(f"False positive rate: {results.overall_false_positive_rate:.1%}")
    print(f"False negative rate: {results.overall_false_negative_rate:.1%}")
    print(f"Unknown rate: {results.overall_unknown_rate:.1%}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results.to_dict(), f, indent=2)
        print(f"\nJSON results written to {args.output}")

    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(results.to_markdown(), encoding="utf-8")
        print(f"Markdown report written to {args.markdown}")


if __name__ == "__main__":
    main()
