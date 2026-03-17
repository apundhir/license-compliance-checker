"""
AI Model benchmark for LCC HuggingFace model/dataset detection.

Creates mock model card directories with known licenses and measures:
- Detection accuracy vs ground truth
- License type classification accuracy (open, restricted, RAIL)
- RAIL restriction detection

Target: >=95% accuracy for license field detection.
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
from lcc.detection.huggingface import HuggingFaceDetector
from lcc.models import Component, ComponentFinding, ComponentType
from lcc.resolution.fallback import FallbackResolver


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AIModelResult:
    """Result of evaluating a single AI model detection."""
    model_name: str
    expected_license: str
    detected_license: Optional[str]
    license_type: str
    license_type_detected: Optional[str]
    correct: bool
    license_type_correct: bool
    confidence: float


@dataclass
class AIModelBenchmarkResults:
    """Aggregated AI model benchmark results."""
    timestamp: str = ""
    duration_seconds: float = 0.0
    total_models: int = 0
    license_correct: int = 0
    license_type_correct: int = 0
    details: List[AIModelResult] = field(default_factory=list)

    @property
    def license_accuracy(self) -> float:
        return self.license_correct / self.total_models if self.total_models > 0 else 0.0

    @property
    def license_type_accuracy(self) -> float:
        return self.license_type_correct / self.total_models if self.total_models > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "duration_seconds": round(self.duration_seconds, 3),
            "summary": {
                "total_models": self.total_models,
                "license_accuracy": round(self.license_accuracy, 4),
                "license_type_accuracy": round(self.license_type_accuracy, 4),
                "license_correct": self.license_correct,
                "license_type_correct": self.license_type_correct,
            },
            "details": [
                {
                    "model_name": d.model_name,
                    "expected_license": d.expected_license,
                    "detected_license": d.detected_license,
                    "license_type": d.license_type,
                    "license_type_detected": d.license_type_detected,
                    "correct": d.correct,
                    "license_type_correct": d.license_type_correct,
                    "confidence": round(d.confidence, 4),
                }
                for d in self.details
            ],
        }

    def to_markdown(self) -> str:
        lines = [
            "# LCC AI Model Benchmark Results",
            "",
            f"**Date:** {self.timestamp}",
            f"**Duration:** {self.duration_seconds:.1f}s",
            f"**Total models:** {self.total_models}",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| License Detection Accuracy | {self.license_accuracy:.1%} |",
            f"| License Type Accuracy | {self.license_type_accuracy:.1%} |",
            f"| Target (>=95%) | {'PASS' if self.license_accuracy >= 0.95 else 'FAIL'} |",
            "",
            "## Per-Model Results",
            "",
            "| Model | Expected | Detected | Type | Correct |",
            "|-------|----------|----------|------|---------|",
        ]
        for d in self.details:
            icon = "Y" if d.correct else "N"
            lines.append(
                f"| {d.model_name} | {d.expected_license} | "
                f"{d.detected_license or '(none)'} | {d.license_type} | {icon} |"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mock model card directory creation
# ---------------------------------------------------------------------------

def _create_model_card_yaml(license_id: str, model_name: str, tags: Optional[List[str]] = None) -> str:
    """Generate YAML front-matter for a model card README.md."""
    tag_lines = ""
    if tags:
        tag_lines = "tags:\n" + "".join(f"  - {t}\n" for t in tags)
    return (
        "---\n"
        f"license: {license_id}\n"
        f"model_name: {model_name}\n"
        f"{tag_lines}"
        "---\n"
        f"\n# {model_name}\n\n"
        f"This is a benchmark mock for {model_name}.\n"
    )


def _create_config_json(model_type: str, framework: str) -> Dict[str, Any]:
    """Generate a minimal HuggingFace config.json."""
    return {
        "model_type": model_type.lower().replace("forcausallm", "").replace("for", ""),
        "architectures": [model_type],
        "transformers_version": "4.47.0",
        "torch_dtype": "float16",
    }


def _create_mock_model_dir(
    parent: Path,
    model_name: str,
    license_id: str,
    model_type: str,
    framework: str,
    rail_restrictions: Optional[List[str]] = None,
) -> Path:
    """
    Create a mock model directory that mimics a HuggingFace model checkout.

    Structure:
        model_dir/
            config.json
            README.md (model card with YAML front-matter)
            model.safetensors (empty placeholder)
    """
    # Sanitize directory name
    safe_name = model_name.replace("/", "--")
    model_dir = parent / safe_name
    model_dir.mkdir(parents=True, exist_ok=True)

    # config.json
    config = _create_config_json(model_type, framework)
    (model_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    # README.md with YAML front-matter
    tags = ["text-generation"]
    if rail_restrictions:
        tags.append("license:rail")
    readme = _create_model_card_yaml(license_id, model_name, tags)
    if rail_restrictions:
        readme += "\n## License Restrictions\n\n"
        for restriction in rail_restrictions:
            readme += f"- {restriction}\n"
    (model_dir / "README.md").write_text(readme, encoding="utf-8")

    # Model weight placeholder
    (model_dir / "model.safetensors").write_bytes(b"\x00" * 64)

    return model_dir


# ---------------------------------------------------------------------------
# License matching helpers
# ---------------------------------------------------------------------------

# License type classification heuristics
OPEN_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense"}
RAIL_LICENSES = {"openrail", "openrail++", "bigscience-bloom-rail-1.0"}
RESTRICTED_LICENSES = {"llama3.1", "gemma", "deepseek", "glm-4", "other"}


def classify_license_type(license_id: str) -> str:
    """Classify a license string as open, restricted, RAIL, or commercial."""
    if license_id in OPEN_LICENSES:
        return "open"
    if license_id.lower() in {l.lower() for l in RAIL_LICENSES}:
        return "RAIL"
    if license_id.lower() in {l.lower() for l in RESTRICTED_LICENSES}:
        return "restricted"
    # Fallback heuristics
    if "rail" in license_id.lower():
        return "RAIL"
    if "apache" in license_id.lower() or "mit" in license_id.lower():
        return "open"
    return "restricted"


def _license_matches(detected: Optional[str], expected: str) -> bool:
    """Check if detected license matches expected (case insensitive, flexible)."""
    if detected is None:
        return False
    det = detected.strip().lower()
    exp = expected.strip().lower()
    if det == exp:
        return True
    if exp in det:
        return True
    return False


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------

def load_ai_corpus(corpus_path: Optional[Path] = None) -> List[Dict]:
    """Load the AI model benchmark corpus."""
    if corpus_path is None:
        corpus_path = Path(__file__).parent / "corpus" / "ai_models.json"
    with open(corpus_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["models"]


def run_ai_model_benchmark(
    corpus_path: Optional[Path] = None,
    verbose: bool = False,
) -> AIModelBenchmarkResults:
    """
    Run the AI model detection benchmark.

    Creates mock model directories, runs the HuggingFace detector, and
    compares detected licenses against ground truth.

    Args:
        corpus_path: Path to ai_models.json corpus.
        verbose: Print progress.

    Returns:
        AIModelBenchmarkResults with all metrics.
    """
    from datetime import datetime, timezone

    models = load_ai_corpus(corpus_path)
    results = AIModelBenchmarkResults(
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_models=len(models),
    )

    detector = HuggingFaceDetector()

    # Build offline resolvers for license resolution
    config = LCCConfig(offline=True)
    cache_dir = Path(tempfile.mkdtemp(prefix="lcc_ai_bench_cache_"))
    config.cache_dir = cache_dir
    cache = Cache(config)

    from lcc.factory import build_resolvers
    resolvers = build_resolvers(config, cache)
    fallback = FallbackResolver(resolvers)

    start_time = time.time()

    with tempfile.TemporaryDirectory(prefix="lcc_ai_bench_") as tmp_dir:
        bench_dir = Path(tmp_dir)

        for model_spec in models:
            model_name = model_spec["name"]
            expected_license = model_spec["known_license"]
            license_type = model_spec["license_type"]
            model_type = model_spec.get("model_type", "Unknown")
            framework = model_spec.get("framework", "pytorch")
            rail = model_spec.get("rail_restrictions")

            if verbose:
                print(f"  {model_name} ...", end=" ", flush=True)

            # Create mock directory
            model_dir = _create_mock_model_dir(
                bench_dir, model_name, expected_license, model_type, framework, rail
            )

            # Run detector
            detected_license: Optional[str] = None
            confidence = 0.0

            try:
                if detector.supports(model_dir):
                    components = detector.discover(model_dir)
                    if components:
                        # Try resolution on the first component
                        finding = ComponentFinding(component=components[0])
                        fallback.resolve(finding)
                        detected_license = finding.resolved_license
                        confidence = finding.confidence

                        # If resolver did not find it, check metadata
                        if not detected_license:
                            card_license = components[0].metadata.get("license_from_card")
                            if card_license:
                                detected_license = card_license
                                confidence = 0.8
            except Exception as exc:
                if verbose:
                    print(f"ERROR: {exc}")
                detected_license = None

            # Evaluate
            license_correct = _license_matches(detected_license, expected_license)
            detected_type = classify_license_type(detected_license) if detected_license else None
            type_correct = detected_type == license_type if detected_type else False

            if license_correct:
                results.license_correct += 1
            if type_correct:
                results.license_type_correct += 1

            result = AIModelResult(
                model_name=model_name,
                expected_license=expected_license,
                detected_license=detected_license,
                license_type=license_type,
                license_type_detected=detected_type,
                correct=license_correct,
                license_type_correct=type_correct,
                confidence=confidence,
            )
            results.details.append(result)

            if verbose:
                status = "OK" if license_correct else "MISS"
                print(f"{status} (detected={detected_license})")

    results.duration_seconds = time.time() - start_time
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LCC AI Model Benchmark")
    parser.add_argument("--corpus", type=Path, help="Path to ai_models.json")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--output", type=Path, help="Write JSON results")
    parser.add_argument("--markdown", type=Path, help="Write markdown report")
    args = parser.parse_args()

    print("=" * 60)
    print("LCC AI Model Benchmark")
    print("=" * 60)
    print()

    results = run_ai_model_benchmark(
        corpus_path=args.corpus,
        verbose=args.verbose,
    )

    print()
    print(f"Completed in {results.duration_seconds:.1f}s")
    print(f"Models: {results.total_models}")
    print(f"License accuracy: {results.license_accuracy:.1%}")
    print(f"License type accuracy: {results.license_type_accuracy:.1%}")
    print(f"Target (>=95%): {'PASS' if results.license_accuracy >= 0.95 else 'FAIL'}")

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
