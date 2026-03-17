#!/usr/bin/env python3
"""
LCC Benchmark Runner

Orchestrates accuracy, speed, and AI model benchmarks and aggregates results
into the benchmarks/results/ directory and a RESULTS.md summary.

Usage:
    python -m benchmarks.run_benchmarks --all
    python -m benchmarks.run_benchmarks --accuracy --speed
    python -m benchmarks.run_benchmarks --ai-models --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


BENCHMARKS_DIR = Path(__file__).parent
RESULTS_DIR = BENCHMARKS_DIR / "results"


def _ensure_results_dir() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_accuracy(verbose: bool = False, ecosystems: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run the accuracy benchmark and return results dict."""
    from benchmarks.accuracy_benchmark import run_accuracy_benchmark

    print("Running accuracy benchmark ...")
    results = run_accuracy_benchmark(verbose=verbose, ecosystems=ecosystems)

    data = results.to_dict()
    output_path = RESULTS_DIR / "accuracy_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    md_path = RESULTS_DIR / "accuracy_results.md"
    md_path.write_text(results.to_markdown(), encoding="utf-8")

    print(f"  Accuracy: {results.overall_accuracy:.1%}")
    print(f"  Results written to {output_path}")
    return data


def run_speed(verbose: bool = False, ecosystems: Optional[List[str]] = None, iterations: int = 5) -> Dict[str, Any]:
    """Run the speed benchmark and return results dict."""
    from benchmarks.speed_benchmark import run_speed_benchmark

    print("Running speed benchmark ...")
    results = run_speed_benchmark(verbose=verbose, ecosystems=ecosystems, iterations=iterations)

    data = results.to_dict()
    output_path = RESULTS_DIR / "speed_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    md_path = RESULTS_DIR / "speed_results.md"
    md_path.write_text(results.to_markdown(), encoding="utf-8")

    print(f"  Results written to {output_path}")
    return data


def run_ai_models(verbose: bool = False) -> Dict[str, Any]:
    """Run the AI model benchmark and return results dict."""
    from benchmarks.ai_model_benchmark import run_ai_model_benchmark

    print("Running AI model benchmark ...")
    results = run_ai_model_benchmark(verbose=verbose)

    data = results.to_dict()
    output_path = RESULTS_DIR / "ai_model_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    md_path = RESULTS_DIR / "ai_model_results.md"
    md_path.write_text(results.to_markdown(), encoding="utf-8")

    print(f"  License accuracy: {results.license_accuracy:.1%}")
    print(f"  Results written to {output_path}")
    return data


def generate_summary(
    accuracy_data: Optional[Dict] = None,
    speed_data: Optional[Dict] = None,
    ai_data: Optional[Dict] = None,
) -> str:
    """Generate the combined RESULTS.md markdown summary."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# LCC Benchmark Results",
        "",
        f"**Generated:** {ts}",
        "",
        "---",
        "",
    ]

    # Accuracy section
    if accuracy_data:
        summary = accuracy_data.get("summary", {})
        lines.extend([
            "## License Detection Accuracy",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Overall Accuracy | {summary.get('overall_accuracy', 0):.1%} |",
            f"| False Positive Rate | {summary.get('overall_false_positive_rate', 0):.1%} |",
            f"| False Negative Rate | {summary.get('overall_false_negative_rate', 0):.1%} |",
            f"| Unknown Rate | {summary.get('overall_unknown_rate', 0):.1%} |",
            f"| Projects Evaluated | {summary.get('total_projects', 0)} |",
            f"| Components Evaluated | {summary.get('total_components', 0)} |",
            "",
        ])

        ecosystems = accuracy_data.get("per_ecosystem", {})
        if ecosystems:
            lines.extend([
                "### Per-Ecosystem Accuracy",
                "",
                "| Ecosystem | Components | Accuracy | FP Rate | FN Rate | Unknown |",
                "|-----------|-----------|----------|---------|---------|---------|",
            ])
            for name in sorted(ecosystems):
                e = ecosystems[name]
                lines.append(
                    f"| {name} | {e.get('total_components', 0)} | "
                    f"{e.get('accuracy', 0):.1%} | {e.get('false_positive_rate', 0):.1%} | "
                    f"{e.get('false_negative_rate', 0):.1%} | {e.get('unknown_rate', 0):.1%} |"
                )
            lines.append("")

    # Speed section
    if speed_data:
        benchmarks = speed_data.get("benchmarks", [])
        lines.extend([
            "## Scan Speed",
            "",
            "| Benchmark | Deps | Mean (s) | Median (s) | P95 (s) |",
            "|-----------|------|----------|------------|---------|",
        ])
        for b in benchmarks:
            total = b.get("total", {})
            lines.append(
                f"| {b['label']} | {b['dependency_count']} | "
                f"{total.get('mean', 0):.4f} | {total.get('median', 0):.4f} | "
                f"{total.get('p95', 0):.4f} |"
            )
        lines.extend([
            "",
            "### Phase Breakdown (mean seconds)",
            "",
            "| Benchmark | Detection | Resolution | Total |",
            "|-----------|-----------|------------|-------|",
        ])
        for b in benchmarks:
            det = b.get("detection", {})
            res = b.get("resolution", {})
            total = b.get("total", {})
            lines.append(
                f"| {b['label']} | {det.get('mean', 0):.4f} | "
                f"{res.get('mean', 0):.4f} | {total.get('mean', 0):.4f} |"
            )
        lines.append("")

    # AI Models section
    if ai_data:
        ai_summary = ai_data.get("summary", {})
        lines.extend([
            "## AI Model Detection",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| License Accuracy | {ai_summary.get('license_accuracy', 0):.1%} |",
            f"| License Type Accuracy | {ai_summary.get('license_type_accuracy', 0):.1%} |",
            f"| Models Evaluated | {ai_summary.get('total_models', 0)} |",
            f"| Target (>=95%) | {'PASS' if ai_summary.get('license_accuracy', 0) >= 0.95 else 'FAIL'} |",
            "",
        ])

        details = ai_data.get("details", [])
        if details:
            lines.extend([
                "### Per-Model Detail",
                "",
                "| Model | Expected | Detected | Correct |",
                "|-------|----------|----------|---------|",
            ])
            for d in details:
                icon = "Y" if d.get("correct") else "N"
                lines.append(
                    f"| {d['model_name']} | {d['expected_license']} | "
                    f"{d.get('detected_license') or '(none)'} | {icon} |"
                )
            lines.append("")

    lines.extend([
        "---",
        "",
        "*Generated by `benchmarks/run_benchmarks.py`*",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LCC Benchmark Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m benchmarks.run_benchmarks --all\n"
            "  python -m benchmarks.run_benchmarks --accuracy --speed -v\n"
            "  python -m benchmarks.run_benchmarks --ai-models\n"
        ),
    )
    parser.add_argument("--accuracy", action="store_true", help="Run accuracy benchmark")
    parser.add_argument("--speed", action="store_true", help="Run speed benchmark")
    parser.add_argument("--ai-models", action="store_true", help="Run AI model benchmark")
    parser.add_argument("--all", action="store_true", help="Run all benchmarks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--ecosystem", action="append", dest="ecosystems", help="Filter ecosystems (repeatable)")
    parser.add_argument("--iterations", "-n", type=int, default=5, help="Speed benchmark iterations")
    args = parser.parse_args()

    if not any([args.accuracy, args.speed, args.ai_models, args.all]):
        parser.print_help()
        sys.exit(1)

    _ensure_results_dir()

    print("=" * 60)
    print("LCC Benchmark Suite")
    print("=" * 60)
    print()

    bench_start = time.time()
    accuracy_data = None
    speed_data = None
    ai_data = None

    if args.accuracy or args.all:
        accuracy_data = run_accuracy(verbose=args.verbose, ecosystems=args.ecosystems)
        print()

    if args.speed or args.all:
        speed_data = run_speed(verbose=args.verbose, ecosystems=args.ecosystems, iterations=args.iterations)
        print()

    if args.ai_models or args.all:
        ai_data = run_ai_models(verbose=args.verbose)
        print()

    # Generate combined summary
    summary_md = generate_summary(accuracy_data, speed_data, ai_data)
    results_path = BENCHMARKS_DIR / "RESULTS.md"
    results_path.write_text(summary_md, encoding="utf-8")

    total_duration = time.time() - bench_start
    print("=" * 60)
    print(f"All benchmarks completed in {total_duration:.1f}s")
    print(f"Results: {RESULTS_DIR}")
    print(f"Summary: {results_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
