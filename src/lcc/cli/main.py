"""Command line interface for License Compliance Checker."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import uvicorn
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from lcc.cache import Cache
from lcc.config import LCCConfig, load_config
from lcc.factory import build_detectors, build_resolvers
from lcc.models import Component, ComponentFinding, ComponentType, LicenseEvidence, ScanReport, ScanSummary
from lcc.reporting.console_reporter import ConsoleReporter
from lcc.reporting.json_reporter import JSONReporter
from lcc.reporting.markdown_reporter import MarkdownReporter
from lcc.reporting.html_reporter import HTMLReporter
from lcc.reporting.csv_reporter import CSVReporter
from lcc.api.server import create_app
from lcc.policy import PolicyAlternative, PolicyDecision, PolicyError, PolicyManager, evaluate_policy
from lcc.policy.opa_client import OPAClient, OPAClientError
from lcc.policy.decision_recorder import DecisionRecorder
from lcc.jobs.queue import JobQueue, JobQueueWorker, QueueError, Job
from lcc.scanner import Scanner
from lcc.utils.git import GitError, cleanup_repository, clone_repository

try:  # pragma: no cover - platform dependent
    import readline
except ImportError:  # pragma: no cover - Windows fallback
    readline = None


INTERACTIVE_COMMANDS = [
    "help",
    "menu",
    "summary",
    "list",
    "list violations",
    "show",
    "search",
    "filter",
    "clear",
    "export",
    "quit",
    "exit",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("lcc", description="License Compliance Checker")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--quiet", action="store_true", help="Reduce output to violations only")
    parser.add_argument("--version", action="store_true", help="Show version and exit")

    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan a project directory")
    scan_parser.add_argument("path", nargs="?", default=".", help="Project directory to scan")
    scan_parser.add_argument("--manifest", action="append", default=[], help="Specific manifest file to target")
    scan_parser.add_argument("--recursive", action="store_true", help="Recursively scan subdirectories")
    scan_parser.add_argument("--exclude", action="append", default=[], help="Glob pattern to exclude")
    scan_parser.add_argument("--format", choices=["console", "json"], default="console", help="Output format")
    scan_parser.add_argument("--output", type=str, help="Output file path (when using json format)")
    scan_parser.add_argument("--policy", type=str, help="Policy file to apply (future use)")
    scan_parser.add_argument(
        "--context",
        type=str,
        help="Usage context for policy evaluation (e.g. internal, saas, distribution)",
    )
    scan_parser.add_argument("--threshold", type=float, default=0.5, help="Confidence threshold for violations")
    scan_parser.add_argument("--timeout", type=float, help="Override resolver timeout (seconds)")
    scan_parser.add_argument("--parallel", type=int, default=0, help="Worker count for future parallel execution")
    scan_parser.add_argument("--offline", action="store_true", help="Use cached results only; skip network calls")
    scan_parser.add_argument("--cache-ttl", type=int, default=3600, help="Cache TTL in seconds")
    scan_parser.add_argument("--git", action="append", default=[], help="Clone git repository url[@ref] and scan")
    scan_parser.add_argument("--git-depth", type=int, default=1, help="Depth when cloning git repositories")
    scan_parser.set_defaults(func=handle_scan)

    interactive_parser = subparsers.add_parser("interactive", help="Interactive scan exploration")
    interactive_parser.add_argument("path", nargs="?", default=".", help="Project directory to scan")
    interactive_parser.add_argument("--report", help="Path to existing JSON report")
    interactive_parser.add_argument("--commands", nargs="*", help="Predefined commands (for automation/tests)")
    interactive_parser.add_argument("--policy", help="Policy to apply during scan")
    interactive_parser.add_argument("--context", help="Usage context for policy evaluation")
    interactive_parser.add_argument("--threshold", type=float, default=0.5)
    interactive_parser.add_argument("--offline", action="store_true")
    interactive_parser.add_argument("--git", action="append", default=[])
    interactive_parser.add_argument("--git-depth", type=int, default=1)
    interactive_parser.add_argument("--cache-ttl", type=int, default=3600)
    interactive_parser.add_argument("--config", help="Configuration path")
    interactive_parser.set_defaults(func=handle_interactive)
    interactive_parser.epilog = "Tip: generate a JSON report with `lcc scan --format json --output report.json` before launching."
    queue_parser = subparsers.add_parser("queue", help="Manage background scan jobs")
    queue_parser.add_argument("--config", help="Path to config file")
    queue_sub = queue_parser.add_subparsers(dest="queue_command")

    submit_parser = queue_sub.add_parser("submit", help="Submit a scan job")
    submit_parser.add_argument("path", help="Project path to scan")
    submit_parser.add_argument("--output", help="Write JSON report to path")
    submit_parser.add_argument("--policy", help="Policy name to apply")
    submit_parser.add_argument("--context", help="Usage context for policy evaluation")
    submit_parser.add_argument("--priority", type=int, default=0)
    submit_parser.add_argument("--max-retries", type=int, default=3)
    submit_parser.add_argument("--cache-ttl", type=int, default=3600)
    submit_parser.add_argument("--threshold", type=float, default=0.5)
    submit_parser.set_defaults(func=handle_queue_submit)

    worker_parser = queue_sub.add_parser("worker", help="Start a queue worker")
    worker_parser.add_argument("--poll-interval", type=float, default=1.0)
    worker_parser.add_argument("--once", action="store_true", help="Process a single job and exit")
    worker_parser.set_defaults(func=handle_queue_worker)

    status_parser = queue_sub.add_parser("status", help="Show queue statistics")
    status_parser.set_defaults(func=handle_queue_status)
    interactive_parser.epilog = "Tip: generate a JSON report with `lcc scan` before launching interactive mode."

    policy_parser = subparsers.add_parser("policy", help="Manage policy definitions")
    policy_sub = policy_parser.add_subparsers(dest="policy_command")

    list_parser = policy_sub.add_parser("list", help="List available policies")
    list_parser.set_defaults(func=handle_policy_list)

    show_parser = policy_sub.add_parser("show", help="Show policy contents")
    show_parser.add_argument("name", help="Policy name")
    show_parser.set_defaults(func=handle_policy_show)

    apply_parser = policy_sub.add_parser("apply", help="Activate a policy")
    apply_parser.add_argument("name", help="Policy name")
    apply_parser.set_defaults(func=handle_policy_apply)

    validate_parser = policy_sub.add_parser("validate", help="Validate a policy file")
    validate_parser.add_argument("file", help="Path to policy file")
    validate_parser.set_defaults(func=handle_policy_validate)

    create_parser = policy_sub.add_parser("create", help="Create a new policy")
    create_parser.add_argument("--name", required=True, help="Policy name")
    create_parser.add_argument("--description", help="Policy description")
    create_parser.set_defaults(func=handle_policy_create)

    edit_parser = policy_sub.add_parser("edit", help="Edit an existing policy")
    edit_parser.add_argument("name", help="Policy name")
    edit_parser.set_defaults(func=handle_policy_edit)

    delete_parser = policy_sub.add_parser("delete", help="Delete a policy")
    delete_parser.add_argument("name", help="Policy name")
    delete_parser.add_argument("--yes", action="store_true", help="Confirm deletion")
    delete_parser.set_defaults(func=handle_policy_delete)

    import_parser = policy_sub.add_parser("import", help="Import a policy file")
    import_parser.add_argument("path", help="Policy file to import")
    import_parser.set_defaults(func=handle_policy_import)

    export_parser = policy_sub.add_parser("export", help="Export a policy")
    export_parser.add_argument("name", help="Policy name")
    export_parser.add_argument("destination", help="Destination directory or file")
    export_parser.set_defaults(func=handle_policy_export)

    test_parser = policy_sub.add_parser("test", help="Evaluate a policy against a report")
    test_parser.add_argument("name", help="Policy name")
    test_parser.add_argument("report", help="Path to JSON report")
    test_parser.add_argument("--context", help="Usage context for policy evaluation")
    test_parser.set_defaults(func=handle_policy_test)

    report_parser = subparsers.add_parser("report", help="Generate reports")
    report_sub = report_parser.add_subparsers(dest="report_command")

    generate_parser = report_sub.add_parser("generate", help="Generate a compliance report")
    generate_parser.add_argument("path", help="Project directory to scan or existing JSON report")
    generate_parser.add_argument("--format", choices=["json", "markdown", "html", "csv"], default="markdown")
    generate_parser.add_argument("--output", help="Output file path")
    generate_parser.add_argument("--include-evidence", action="store_true", help="Include evidence details")
    generate_parser.add_argument("--summary-only", action="store_true", help="Only include summary information")
    generate_parser.add_argument("--group-by", choices=["license", "component"], default="license")
    generate_parser.add_argument("--filter", help="Filter expression license=MIT")
    generate_parser.add_argument("--compare", help="Compare against another JSON report")
    generate_parser.add_argument("--sign", action="store_true", help="Attach a SHA256 signature")
    generate_parser.set_defaults(func=handle_report_generate)

    server_parser = subparsers.add_parser("server", help="Run the REST API service")
    server_parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    server_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    server_parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development only)")
    server_parser.add_argument("--config", help="Path to configuration file")
    server_parser.set_defaults(func=handle_server)

    # SBOM commands
    sbom_parser = subparsers.add_parser("sbom", help="SBOM generation, validation, and signing")
    sbom_sub = sbom_parser.add_subparsers(dest="sbom_command")

    sbom_generate_parser = sbom_sub.add_parser("generate", help="Generate SBOM from scan result")
    sbom_generate_parser.add_argument("scan_result", help="Path to scan result JSON file")
    sbom_generate_parser.add_argument("--output", "-o", required=True, help="Output SBOM file path")
    sbom_generate_parser.add_argument("--format", "-f", choices=["cyclonedx", "spdx"], default="cyclonedx", help="SBOM format")
    sbom_generate_parser.add_argument("--sbom-format", choices=["json", "xml", "yaml", "tag-value"], default="json", help="Output file format")
    sbom_generate_parser.add_argument("--project-name", help="Project name")
    sbom_generate_parser.add_argument("--project-version", help="Project version")
    sbom_generate_parser.add_argument("--author", help="Author/creator name")
    sbom_generate_parser.add_argument("--supplier", help="Supplier/organization name")
    sbom_generate_parser.set_defaults(func=handle_sbom_generate)

    sbom_validate_parser = sbom_sub.add_parser("validate", help="Validate an SBOM file")
    sbom_validate_parser.add_argument("sbom_file", help="Path to SBOM file")
    sbom_validate_parser.add_argument("--format", "-f", choices=["cyclonedx", "spdx", "auto"], default="auto", help="SBOM format")
    sbom_validate_parser.add_argument("--check-licenses", action="store_true", help="Also validate license expressions")
    sbom_validate_parser.set_defaults(func=handle_sbom_validate)

    sbom_sign_parser = sbom_sub.add_parser("sign", help="Sign an SBOM file with GPG")
    sbom_sign_parser.add_argument("sbom_file", help="Path to SBOM file")
    sbom_sign_parser.add_argument("--key", "-k", required=True, help="GPG key ID or email")
    sbom_sign_parser.add_argument("--passphrase", "-p", help="Key passphrase")
    sbom_sign_parser.add_argument("--output", "-o", help="Output path")
    sbom_sign_parser.add_argument("--detached", action="store_true", help="Create detached signature")
    sbom_sign_parser.add_argument("--gpg-home", help="GPG home directory")
    sbom_sign_parser.set_defaults(func=handle_sbom_sign)

    sbom_verify_parser = sbom_sub.add_parser("verify", help="Verify an SBOM signature")
    sbom_verify_parser.add_argument("sbom_file", help="Path to SBOM file")
    sbom_verify_parser.add_argument("--signature", "-s", help="Path to detached signature file")
    sbom_verify_parser.add_argument("--gpg-home", help="GPG home directory")
    sbom_verify_parser.set_defaults(func=handle_sbom_verify)

    sbom_hash_parser = sbom_sub.add_parser("hash", help="Generate cryptographic hash of SBOM")
    sbom_hash_parser.add_argument("sbom_file", help="Path to SBOM file")
    sbom_hash_parser.add_argument("--algorithm", "-a", choices=["sha256", "sha512", "sha1"], default="sha256", help="Hash algorithm")
    sbom_hash_parser.set_defaults(func=handle_sbom_hash)

    sbom_keys_parser = sbom_sub.add_parser("list-keys", help="List available GPG keys")
    sbom_keys_parser.add_argument("--gpg-home", help="GPG home directory")
    sbom_keys_parser.set_defaults(func=handle_sbom_list_keys)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.version:
        from lcc import __version__

        print(f"License Compliance Checker v{__version__}")
        return 0

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


def handle_unimplemented(args: argparse.Namespace) -> int:  # pragma: no cover - simple stub
    Console().print("[yellow]Command not yet implemented in Phase 1.[/yellow]")
    return 0


def handle_scan(args: argparse.Namespace) -> int:
    console = Console()
    config_path = Path(args.config) if getattr(args, "config", None) else None
    config = load_config(config_path)
    if args.timeout:
        config.timeouts["default"] = float(args.timeout)
    if args.offline:
        config.offline = True
    if args.verbose:
        config.log_level = "DEBUG"
    if args.quiet:
        config.log_level = "ERROR"

    logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))

    cache = Cache(config, ttl_seconds=args.cache_ttl)
    detectors = build_detectors()
    resolvers = build_resolvers(config, cache)
    scanner = Scanner(detectors, resolvers, config)

    targets = determine_targets(Path(args.path), args.manifest, args.recursive, args.exclude)
    total_errors: List[str] = []
    cloned_repos: List[Path] = []
    for spec in args.git:
        repo, ref = (spec.split("@", 1) + [None])[:2]
        try:
            repo_path = clone_repository(repo, ref, depth=args.git_depth)
            cloned_repos.append(repo_path)
            targets.append(repo_path)
        except GitError as exc:
            total_errors.append(f"git:{repo}:{exc}")
    findings: List[ComponentFinding] = []
    start = time.time()

    with Progress(console=console, transient=not args.verbose) as progress:
        detection_task = progress.add_task("Detecting", total=len(detectors))
        resolution_task = progress.add_task("Resolving", total=0)

        def progress_callback(stage: str, name: str, index: int, total: int) -> None:
            if stage == "detector":
                progress.update(detection_task, total=len(detectors), completed=index)
            elif stage == "resolver":
                progress.update(resolution_task, total=total, completed=index)

        for target in targets:
            progress.reset(detection_task)
            progress.reset(resolution_task)
            report = scanner.scan(target, progress_callback=progress_callback)
            for finding in report.findings:
                finding.component.metadata.setdefault("project_root", str(target))
                findings.append(finding)
            total_errors.extend(report.errors)

    duration = time.time() - start
    summary = ScanSummary(
        component_count=len(findings),
        violations=0,
        duration_seconds=duration,
        context={
            "detectors": [detector.name for detector in detectors],
            "resolvers": [resolver.name for resolver in resolvers],
            "targets": [str(target) for target in targets],
        },
    )
    report = ScanReport(findings=findings, summary=summary, errors=total_errors)

    if getattr(args, "context", None):
        config.policy_context = args.context

    try:
        policy_violations, policy_context = apply_policy_to_report(
            report,
            config,
            supplied_policy=getattr(args, "policy", None),
            context=getattr(args, "context", None),
        )
    except PolicyError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    if policy_context:
        report.summary.context["policy"] = policy_context

    threshold = max(0.0, min(1.0, float(args.threshold)))
    violations = [finding for finding in report.findings if finding.confidence < threshold or not finding.resolved_license]
    report.summary.violations = len(violations) + policy_violations

    exit_code = 2 if (violations or policy_violations) else 0

    if args.format == "json":
        payload = JSONReporter().render(report)
        if args.output:
            Path(args.output).write_text(payload, encoding="utf-8")
        else:
            console.print(payload)
    else:
        reporter = ConsoleReporter(console=console, threshold=threshold, quiet=args.quiet)
        reporter.write(report)

    if args.parallel:
        console.print("[yellow]Parallel execution is planned for a future release.[/yellow]")

    for repo_path in cloned_repos:
        cleanup_repository(repo_path)

    return exit_code


def determine_targets(base_path: Path, manifests: List[str], recursive: bool, exclude_patterns: List[str]) -> List[Path]:
    if manifests:
        parents = {Path(manifest).resolve().parent for manifest in manifests}
        targets = sorted(parents)
    else:
        targets = [base_path.resolve()]

    filtered: List[Path] = []
    for target in targets:
        if any(target.match(pattern) for pattern in exclude_patterns):
            continue
        filtered.append(target)
    filtered = list(dict.fromkeys(filtered))

    if recursive and not manifests:
        manifest_names = {
            "requirements.txt",
            "setup.py",
            "pyproject.toml",
            "Pipfile",
            "poetry.lock",
            "environment.yml",
            "package.json",
            "go.mod",
        }
        discovered: List[Path] = []
        for target in filtered:
            for manifest_name in manifest_names:
                for manifest_path in target.rglob(manifest_name):
                    parent = manifest_path.parent
                    if any(parent.match(pattern) for pattern in exclude_patterns):
                        continue
                    if parent not in discovered and parent not in filtered:
                        discovered.append(parent)
        return filtered + discovered

    return filtered


def _policy_manager(args: argparse.Namespace) -> tuple[PolicyManager, LCCConfig]:
    config_path = Path(args.config) if getattr(args, "config", None) else None
    config = load_config(config_path)
    manager = PolicyManager(config)
    return manager, config


def handle_policy_list(args: argparse.Namespace) -> int:
    console = Console()
    manager, config = _policy_manager(args)
    policies = manager.list_policies()
    active = manager.active_policy()
    if not policies:
        console.print("[yellow]No policies available.[/yellow]")
        return 0
    for policy_name in policies:
        marker = "*" if policy_name == active else "-"
        console.print(f"{marker} {policy_name}")
    return 0


def handle_policy_show(args: argparse.Namespace) -> int:
    console = Console()
    manager, _ = _policy_manager(args)
    try:
        policy = manager.load_policy(args.name)
    except PolicyError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(json.dumps(policy.data, indent=2))
    console.print(f"Stored at: {policy.path}")
    return 0


def handle_policy_apply(args: argparse.Namespace) -> int:
    console = Console()
    manager, _ = _policy_manager(args)
    try:
        manager.set_active_policy(args.name)
    except PolicyError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(f"[green]Policy '{args.name}' applied.[/green]")
    return 0


def handle_policy_validate(args: argparse.Namespace) -> int:
    console = Console()
    manager, _ = _policy_manager(args)
    try:
        data = manager.read_policy_file(Path(args.file))
    except PolicyError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    errors = manager.validate_policy(data)
    if errors:
        for error in errors:
            console.print(f"[red]{error}[/red]")
        return 1
    console.print("[green]Policy is valid.[/green]")
    return 0


def handle_policy_create(args: argparse.Namespace) -> int:
    console = Console()
    manager, _ = _policy_manager(args)
    data = {
        "name": args.name,
        "version": "1.0",
        "description": args.description or "",
        "disclaimer": "Consult legal counsel for authoritative guidance",
        "default_context": "internal",
        "contexts": {
            "internal": {
                "description": "Default internal usage context",
                "allow": ["MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ISC"],
                "deny": ["SSPL-1.0"],
                "review": ["GPL-*", "AGPL-*", "LGPL-*"],
                "deny_reasons": {
                    "SSPL-1.0": "Not approved for internal distribution without legal review.",
                },
                "review_reasons": {
                    "GPL-*": "Assess copyleft obligations before use.",
                    "AGPL-*": "Network copyleft terms to be reviewed.",
                    "LGPL-*": "Ensure dynamic linking guidelines are met.",
                },
                "dual_license_preference": "most_permissive",
            }
        },
    }
    errors = manager.validate_policy(data)
    if errors:
        for error in errors:
            console.print(f"[red]{error}[/red]")
        return 1
    path = manager.save_policy(args.name, data)
    console.print(f"[green]Policy created at {path}[/green]")
    return 0


def handle_policy_edit(args: argparse.Namespace) -> int:
    console = Console()
    manager, _ = _policy_manager(args)
    try:
        policy = manager.load_policy(args.name)
    except PolicyError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    editor = os.getenv("EDITOR")
    if editor:
        subprocess.run([editor, str(policy.path)])
    else:
        console.print(f"Set the EDITOR environment variable or manually edit: {policy.path}")
    return 0


def handle_policy_delete(args: argparse.Namespace) -> int:
    console = Console()
    manager, _ = _policy_manager(args)
    if not args.yes:
        console.print("[yellow]Re-run with --yes to confirm deletion.[/yellow]")
        return 1
    manager.delete_policy(args.name)
    console.print(f"[green]Policy '{args.name}' deleted.[/green]")
    return 0


def handle_policy_import(args: argparse.Namespace) -> int:
    console = Console()
    manager, _ = _policy_manager(args)
    try:
        dest = manager.import_policy(Path(args.path))
    except PolicyError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(f"[green]Policy imported to {dest}[/green]")
    return 0


def handle_policy_export(args: argparse.Namespace) -> int:
    console = Console()
    manager, _ = _policy_manager(args)
    try:
        dest = manager.export_policy(args.name, Path(args.destination))
    except PolicyError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(f"[green]Policy exported to {dest}[/green]")
    return 0


def handle_policy_test(args: argparse.Namespace) -> int:
    console = Console()
    manager, _ = _policy_manager(args)
    try:
        policy = manager.load_policy(args.name)
    except PolicyError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    report_path = Path(args.report)
    if not report_path.exists():
        console.print(f"[red]Report file not found: {report_path}[/red]")
        return 1
    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    context = getattr(args, "context", None)
    decisions: List[Dict[str, object]] = []
    violations: List[Dict[str, object]] = []
    warnings: List[Dict[str, object]] = []

    for finding in report_data.get("findings", []):
        component = finding.get("component", {}).get("name", "<unknown>")
        licenses = []
        resolved = finding.get("resolved_license")
        if resolved:
            licenses.append(resolved)
        for evidence in finding.get("evidences", []):
            expression = evidence.get("license_expression")
            if expression:
                licenses.append(expression)
        decision = evaluate_policy(
            policy.data,
            licenses or ["UNKNOWN"],
            context=context,
            component_name=component,
        )
        decision_dict = decision.to_dict()
        decision_dict["component"] = component
        decisions.append(decision_dict)
        if decision.status == "violation":
            violations.append(decision_dict)
        elif decision.status == "warning":
            warnings.append(decision_dict)

    payload = {
        "policy": policy.name,
        "context": context or policy.data.get("default_context"),
        "decisions": decisions,
        "violations": violations,
        "warnings": warnings,
    }
    console.print(json.dumps(payload, indent=2))
    if violations:
        return 2
    if warnings:
        return 3
    return 0


def _deserialize_report(data: Dict[str, object]) -> ScanReport:
    findings: List[ComponentFinding] = []
    for item in data.get("findings", []):
        component_data = item.get("component", {})
        component_type = component_data.get("type", ComponentType.GENERIC.value)
        try:
            component_type_enum = ComponentType(component_type)
        except ValueError:
            component_type_enum = ComponentType.GENERIC
        component = Component(
            type=component_type_enum,
            name=component_data.get("name", ""),
            version=component_data.get("version", "*"),
            namespace=component_data.get("namespace"),
            path=Path(component_data["path"]) if component_data.get("path") else None,
            metadata=component_data.get("metadata", {}),
        )
        evidences = [
            LicenseEvidence(
                source=evidence.get("source", ""),
                license_expression=evidence.get("license_expression", "UNKNOWN"),
                confidence=float(evidence.get("confidence", 0.0)),
                raw_data=evidence.get("raw_data", {}),
                url=evidence.get("url"),
            )
            for evidence in item.get("evidences", [])
        ]
        finding = ComponentFinding(
            component=component,
            evidences=evidences,
            resolved_license=item.get("resolved_license"),
            confidence=float(item.get("confidence", 0.0)),
        )
        findings.append(finding)

    summary_data = data.get("summary", {})
    generated_at_raw = summary_data.get("generated_at")
    if isinstance(generated_at_raw, str):
        try:
            generated_at = datetime.fromisoformat(generated_at_raw)
        except ValueError:
            generated_at = datetime.utcnow()
    else:
        generated_at = datetime.utcnow()
    summary = ScanSummary(
        component_count=int(summary_data.get("component_count", len(findings))),
        violations=int(summary_data.get("violations", 0)),
        generated_at=generated_at,
        duration_seconds=float(summary_data.get("duration_seconds", 0.0)),
        context=summary_data.get("context", {}),
    )
    return ScanReport(findings=findings, summary=summary, errors=data.get("errors", []))


def handle_interactive(args: argparse.Namespace) -> int:
    console = Console()
    if not args.report:
        console.print(
            "[red]Interactive mode currently requires a JSON report generated via `lcc scan --format json --output <path>`."
            " Use --report to provide the file.[/red]"
        )
        return 1

    report_path = Path(args.report)
    if not report_path.exists():
        console.print(f"[red]Report file not found: {report_path}[/red]")
        return 1

    try:
        report_data = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        console.print(f"[red]Unable to parse report JSON: {exc}[/red]")
        return 1

    report = _deserialize_report(report_data)

    if args.policy or args.context:
        config_path = Path(args.config) if getattr(args, "config", None) else None
        config = load_config(config_path)
        if getattr(args, "context", None):
            config.policy_context = args.context
        try:
            apply_policy_to_report(
                report,
                config,
                supplied_policy=getattr(args, "policy", None),
                context=getattr(args, "context", None),
            )
        except PolicyError as exc:
            console.print(f"[red]{exc}[/red]")
            return 1
    command_list: Optional[Sequence[str]] = args.commands
    interactive_session(
        console,
        report,
        commands=command_list,
        output_dir=report_path.parent,
    )
    return 0


def interactive_session(
    console: Console,
    report: ScanReport,
    *,
    commands: Optional[Sequence[str]] = None,
    output_dir: Optional[Path] = None,
) -> None:
    output_dir = output_dir or Path.cwd()
    _configure_readline()
    command_iter = iter(commands or [])
    scripted_mode = commands is not None
    current_indices = list(range(len(report.findings)))
    console.print("[cyan]Interactive mode: type 'menu' to list commands, 'quit' to exit.[/cyan]")

    while True:
        if scripted_mode:
            try:
                raw_command = next(command_iter)
            except StopIteration:
                break
            console.print(f"lcc> {raw_command}")
        else:
            try:
                raw_command = input("lcc> ")
            except EOFError:  # pragma: no cover - user triggered
                console.print()
                break

        command = raw_command.strip()
        if not command:
            continue

        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in {"quit", "exit"}:
            break
        elif cmd in {"help", "menu"}:
            _print_interactive_menu(console)
        elif cmd == "summary":
            _print_summary(console, report, current_indices)
        elif cmd == "list":
            violations_only = len(args) == 1 and args[0].lower() in {"violations", "viol"}
            _render_component_table(console, report, current_indices, violations_only)
        elif cmd == "show":
            if not args:
                console.print("[yellow]Usage: show <index>[/yellow]")
                continue
            try:
                index = int(args[0])
            except ValueError:
                console.print("[red]Index must be an integer.[/red]")
                continue
            _render_component_detail(console, report, current_indices, index)
        elif cmd == "search":
            if not args:
                console.print("[yellow]Usage: search <term>[/yellow]")
                continue
            term = " ".join(args).lower()
            current_indices = _filter_indices(report, lambda f: _matches_term(f, term))
            console.print(f"[green]{len(current_indices)} result(s) after search.[/green]")
        elif cmd == "filter":
            if len(args) < 2:
                console.print("[yellow]Usage: filter <license|status> <value>[/yellow]")
                continue
            category = args[0].lower()
            value = " ".join(args[1:]).lower()
            if category == "license":
                current_indices = _filter_indices(
                    report,
                    lambda f: (f.resolved_license or "UNKNOWN").lower() == value,
                )
                console.print(f"[green]{len(current_indices)} result(s) after license filter.[/green]")
            elif category == "status":
                current_indices = _filter_indices(report, lambda f: _matches_status(f, value))
                console.print(f"[green]{len(current_indices)} result(s) after status filter.[/green]")
            else:
                console.print("[red]Unknown filter type. Use 'license' or 'status'.[/red]")
        elif cmd == "clear":
            current_indices = list(range(len(report.findings)))
            console.print("[green]Filters cleared.[/green]")
        elif cmd == "export":
            if len(args) < 2:
                console.print("[yellow]Usage: export <json|markdown|html|csv> <path> [--all] [--include-evidence][/yellow]")
                continue
            format_name = args[0].lower()
            target_path = args[1]
            flags = {item.lower() for item in args[2:]}
            subset = list(range(len(report.findings))) if "--all" in flags else current_indices
            include_evidence = "--include-evidence" in flags or format_name in {"json", "markdown", "html", "csv"}
            try:
                export_path = Path(target_path)
                if not export_path.is_absolute():
                    export_path = output_dir / export_path
                export_path.parent.mkdir(parents=True, exist_ok=True)
                _export_subset(report, subset, format_name, export_path, include_evidence)
                console.print(f"[green]Exported report to {export_path}[/green]")
            except Exception as exc:  # pragma: no cover - file system issues
                console.print(f"[red]Failed to export report: {exc}[/red]")
        else:
            console.print("[yellow]Unknown command. Type 'menu' for options.[/yellow]")


def _configure_readline() -> None:
    if not readline:  # pragma: no cover - platform dependent
        return
    try:
        readline.parse_and_bind("tab: complete")
        commands = sorted({cmd.split()[0] for cmd in INTERACTIVE_COMMANDS})

        def completer(text: str, state: int) -> Optional[str]:
            matches = [cmd for cmd in commands if cmd.startswith(text)]
            if state < len(matches):
                return matches[state]
            return None

        readline.set_completer(completer)
        readline.set_history_length(1000)
    except Exception:  # pragma: no cover - readline edge case
        pass


def _print_interactive_menu(console: Console) -> None:
    console.print(
        "\n[bold]Commands:[/bold]\n"
        "  summary                 - show overall statistics\n"
        "  list [violations]       - list components (optionally violations only)\n"
        "  show <index>            - show details for a component\n"
        "  search <term>           - search by name/license/project root\n"
        "  filter license <value>  - filter by resolved license\n"
        "  filter status <value>   - filter by policy status (pass, warning, violation, unresolved)\n"
        "  clear                   - clear filters\n"
        "  export <fmt> <path>     - export filtered results (json, markdown, html, csv)\n"
        "  menu / help             - show this menu\n"
        "  quit                    - exit interactive mode\n"
    )


def _print_summary(console: Console, report: ScanReport, indices: List[int]) -> None:
    subset = [report.findings[i] for i in indices]
    violations = sum(1 for finding in subset if _is_violation(finding))
    console.print(
        f"[bold]Summary:[/bold] components={len(subset)} violations={violations}"
    )


def _render_component_table(
    console: Console,
    report: ScanReport,
    indices: List[int],
    violations_only: bool = False,
) -> None:
    if violations_only:
        indices = [idx for idx in indices if _is_violation(report.findings[idx])]
    if not indices:
        console.print("[yellow]No components to display.[/yellow]")
        return
    table = Table(title="Components", expand=True)
    table.add_column("#", justify="right")
    table.add_column("Component")
    table.add_column("License")
    table.add_column("Confidence", justify="right")
    table.add_column("Status")
    table.add_column("Project Root")

    for display_idx, idx in enumerate(indices, start=1):
        finding = report.findings[idx]
        label = _format_component_label(finding)
        license_text = _format_license_label(finding)
        status = finding.component.metadata.get("policy", {}).get("status", "") if isinstance(
            finding.component.metadata, dict
        ) else ""
        project_root = finding.component.metadata.get("project_root", "-") if isinstance(
            finding.component.metadata, dict
        ) else "-"
        table.add_row(
            str(display_idx),
            label,
            license_text,
            f"{finding.confidence:.2f}",
            status,
            project_root,
        )
    console.print(table)


def _render_component_detail(console: Console, report: ScanReport, indices: List[int], display_index: int) -> None:
    if display_index < 1 or display_index > len(indices):
        console.print("[red]Invalid index.[/red]")
        return
    finding = report.findings[indices[display_index - 1]]
    component = finding.component
    console.rule(_format_component_label(finding))
    console.print(f"Type: {component.type.value}")
    console.print(f"Version: {component.version}")
    metadata = component.metadata if isinstance(component.metadata, dict) else {}
    if metadata:
        console.print("[bold]Metadata:[/bold]")
        for key, value in metadata.items():
            console.print(f"  {key}: {value}")
    console.print(f"Resolved license: {finding.resolved_license or 'UNKNOWN'}")
    console.print(f"Confidence: {finding.confidence:.2f}")
    if finding.evidences:
        console.print("[bold]Evidence:[/bold]")
        for evidence in finding.evidences:
            console.print(
                f"  - {evidence.source}: {evidence.license_expression} (confidence {evidence.confidence:.2f})"
            )


def _format_component_label(finding: ComponentFinding) -> str:
    component = finding.component
    metadata = component.metadata if isinstance(component.metadata, dict) else {}
    assumed = ""
    for assumption in metadata.get("assumptions", []) or []:
        if assumption.get("type") == "version":
            assumed = assumption.get("value", "")
            break
    label = f"{component.name}@{component.version}"
    if assumed and component.version in (None, "*"):
        label += f" (~{assumed})"
    return label


def _format_license_label(finding: ComponentFinding) -> str:
    license_text = finding.resolved_license or "UNKNOWN"
    metadata = finding.component.metadata if isinstance(finding.component.metadata, dict) else {}
    assumed = ""
    for assumption in metadata.get("assumptions", []) or []:
        if assumption.get("type") == "version":
            assumed = assumption.get("value", "")
            break
    if assumed and finding.component.version in (None, "*"):
        license_text += " (assumed latest)"
    return license_text


def _matches_term(finding: ComponentFinding, term: str) -> bool:
    component = finding.component
    metadata = component.metadata if isinstance(component.metadata, dict) else {}
    fields = [
        component.name.lower(),
        (component.version or "").lower(),
        (finding.resolved_license or "UNKNOWN").lower(),
        metadata.get("project_root", "").lower(),
    ]
    return any(term in field for field in fields)


def _matches_status(finding: ComponentFinding, value: str) -> bool:
    metadata = finding.component.metadata if isinstance(finding.component.metadata, dict) else {}
    status = metadata.get("policy", {}).get("status") if isinstance(metadata.get("policy"), dict) else None
    if value in {"unresolved", "unknown"}:
        return finding.resolved_license in (None, "UNKNOWN")
    return (status or "").lower() == value


def _is_violation(finding: ComponentFinding) -> bool:
    if finding.resolved_license in (None, "UNKNOWN"):
        return True
    metadata = finding.component.metadata if isinstance(finding.component.metadata, dict) else {}
    status = metadata.get("policy", {}).get("status") if isinstance(metadata.get("policy"), dict) else None
    return (status or "").lower() == "violation"


def _filter_indices(report: ScanReport, predicate) -> List[int]:
    return [idx for idx, finding in enumerate(report.findings) if predicate(finding)]


def _export_subset(
    report: ScanReport,
    indices: List[int],
    format_name: str,
    path: Path,
    include_evidence: bool,
) -> None:
    subset_findings = [report.findings[i] for i in indices]
    summary = ScanSummary(
        component_count=len(subset_findings),
        violations=sum(1 for finding in subset_findings if _is_violation(finding)),
        generated_at=report.summary.generated_at,
        duration_seconds=report.summary.duration_seconds,
        context=report.summary.context,
    )
    subset_report = ScanReport(findings=subset_findings, summary=summary, errors=report.errors)

    if format_name == "json":
        payload = JSONReporter().render(subset_report)
    elif format_name == "markdown":
        payload = MarkdownReporter(include_evidence=include_evidence).render(subset_report)
    elif format_name == "html":
        payload = HTMLReporter(
            include_evidence=include_evidence,
            comparison=subset_report.summary.context.get("comparison"),
        ).render(subset_report)
    elif format_name == "csv":
        payload = CSVReporter(include_evidence=include_evidence).render(subset_report)
    else:
        raise ValueError(f"Unsupported export format: {format_name}")

    mode = "w"
    encoding = "utf-8"
    if isinstance(payload, bytes):  # pragma: no cover - safeguard
        mode = "wb"
        encoding = None
    with open(path, mode, encoding=encoding) as handle:
        handle.write(payload)

def handle_report_generate(args: argparse.Namespace) -> int:
    console = Console()
    config_path = Path(args.config) if getattr(args, "config", None) else None
    config = load_config(config_path)
    cache = Cache(config, ttl_seconds=3600)
    scanner = Scanner(build_detectors(), build_resolvers(config, cache), config)

    path = Path(args.path)
    if path.exists() and path.suffix.lower() == ".json":
        report = _deserialize_report(json.loads(path.read_text(encoding="utf-8")))
    else:
        report = scanner.scan(path)

    if args.filter:
        key, _, value = args.filter.partition("=")
        if key == "license":
            report.findings = [
                finding for finding in report.findings if (finding.resolved_license or "UNKNOWN") == value
            ]

    if not args.include_evidence:
        for finding in report.findings:
            finding.evidences = []

    if args.summary_only:
        report.findings = []

    if args.compare:
        other_data = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        other_report = _deserialize_report(other_data)
        diff = len(report.findings) - len(other_report.findings)
        report.summary.context.setdefault("comparison", {})["component_delta"] = diff

    if args.format == "json":
        payload = JSONReporter().render(report)
    elif args.format == "markdown":
        payload = MarkdownReporter(
            include_evidence=args.include_evidence,
            summary_only=args.summary_only,
            group_by=args.group_by,
        ).render(report)
    elif args.format == "html":
        payload = HTMLReporter(
            include_evidence=args.include_evidence,
            summary_only=args.summary_only,
            group_by=args.group_by,
            comparison=report.summary.context.get("comparison"),
        ).render(report)
    else:  # csv
        payload = CSVReporter(include_evidence=args.include_evidence).render(report)

    if args.sign:
        import hashlib

        signature = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        payload += f"\n\nSignature: {signature}\n"

    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
        console.print(f"[green]Report written to {args.output}[/green]")
    else:
        console.print(payload)
    return 0


def handle_server(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser() if getattr(args, "config", None) else None
    if args.reload:
        if config_path:
            os.environ["LCC_CONFIG_PATH"] = str(config_path)
        uvicorn.run(
            "lcc.api.server:create_app",
            host=args.host,
            port=args.port,
            reload=True,
            factory=True,
        )
    else:
        app = create_app(config_path)
        uvicorn.run(app, host=args.host, port=args.port, reload=False)
    return 0


def apply_policy_to_report(
    report: ScanReport,
    config: LCCConfig,
    supplied_policy: Optional[str] = None,
    context: Optional[str] = None,
) -> tuple[int, Optional[Dict[str, Any]]]:
    manager = PolicyManager(config)
    policy_payload, policy_name = _resolve_policy_definition(manager, supplied_policy)
    opa_client = None
    if config.opa_url:
        try:
            opa_client = OPAClient(config)
        except ValueError:
            opa_client = None

    effective_context = context or getattr(config, "policy_context", None)

    if not policy_payload and not opa_client:
        return 0, None

    recorder = DecisionRecorder(config)
    policy_context: Dict[str, object] = {
        "name": policy_name or ("opa" if opa_client else ""),
        "context": effective_context,
        "violations": [],
        "warnings": [],
        "disclaimer": policy_payload.get("disclaimer") if policy_payload else None,
        "decisions": [],
    }
    violation_count = 0

    for finding in report.findings:
        decision: Optional[PolicyDecision] = None
        license_candidates = _collect_license_candidates(finding)

        if opa_client:
            try:
                opa_result = opa_client.evaluate(
                    finding,
                    policy_name,
                    context=effective_context,
                    licenses=license_candidates,
                )
                decision = _convert_decision_from_mapping(opa_result, effective_context, policy_payload)
            except OPAClientError as exc:
                decision = PolicyDecision(
                    status="warning",
                    context=effective_context or "default",
                    chosen_license=None,
                    reasons=[str(exc)],
                    disclaimer=policy_payload.get("disclaimer") if policy_payload else None,
                )

        if decision is None and policy_payload:
            decision = evaluate_policy(
                policy_payload,
                license_candidates or [finding.resolved_license or "UNKNOWN"],
                context=effective_context,
                component_name=finding.component.name,
            )

        if decision is None:
            decision = PolicyDecision(
                status="pass",
                context=effective_context or "default",
                chosen_license=finding.resolved_license,
                disclaimer=policy_payload.get("disclaimer") if policy_payload else None,
            )

        if decision.status == "violation":
            violation_count += 1
        component_metadata = finding.component.metadata if isinstance(finding.component.metadata, dict) else {}
        policy_metadata = component_metadata.setdefault("policy", {})
        policy_metadata.update(
            {
                "status": decision.status,
                "context": decision.context,
                "chosen_license": decision.chosen_license,
                "reasons": decision.reasons,
                "alternatives": [asdict(item) for item in decision.alternatives],
                "disclaimer": decision.disclaimer,
            }
        )
        if decision.explanation:
            policy_metadata["explanation"] = decision.explanation
        if decision.override:
            policy_metadata["override"] = decision.override

        summary_entry = {
            "component": finding.component.name,
            "status": decision.status,
            "chosen_license": decision.chosen_license,
            "reasons": decision.reasons,
        }
        policy_context["decisions"].append(summary_entry)

        license_name = decision.chosen_license or finding.resolved_license or "UNKNOWN"
        if decision.status == "violation":
            policy_context["violations"].append({"component": finding.component.name, "license": license_name})
        elif decision.status == "warning":
            policy_context["warnings"].append({"component": finding.component.name, "license": license_name})

        recorder.record(finding, decision)

    return violation_count, policy_context


def _resolve_policy_definition(
    manager: PolicyManager, supplied: Optional[str]
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    if supplied:
        path = Path(supplied)
        if path.exists():
            data = manager.read_policy_file(path)
            return data, path.stem
        policy = manager.load_policy(supplied)
        return policy.data, policy.name
    active = manager.active_policy()
    if active:
        policy = manager.load_policy(active)
        return policy.data, policy.name
    return None, None


def _collect_license_candidates(finding: ComponentFinding) -> List[str]:
    candidates: List[str] = []
    if finding.resolved_license:
        candidates.append(finding.resolved_license)
    for evidence in finding.evidences:
        if evidence.license_expression and evidence.license_expression not in candidates:
            candidates.append(evidence.license_expression)
    if not candidates:
        candidates.append("UNKNOWN")
    return candidates


def _convert_decision_from_mapping(
    payload: Optional[Dict[str, Any]],
    fallback_context: Optional[str],
    policy_payload: Optional[Dict[str, Any]],
) -> Optional[PolicyDecision]:
    if not isinstance(payload, dict):
        return None
    status = str(payload.get("status", "pass"))
    context = payload.get("context") or fallback_context or "default"
    chosen = payload.get("chosen_license")
    reasons_raw = payload.get("reasons", [])
    reasons = [str(item) for item in reasons_raw] if isinstance(reasons_raw, list) else [str(reasons_raw)]
    alternatives_payload = payload.get("alternatives", [])
    alternatives: List[PolicyAlternative] = []
    if isinstance(alternatives_payload, list):
        for item in alternatives_payload:
            if isinstance(item, dict):
                alternatives.append(
                    PolicyAlternative(
                        license=str(item.get("license", "UNKNOWN")),
                        disposition=str(item.get("disposition", "unknown")),
                        reason=item.get("reason") if isinstance(item.get("reason"), str) else None,
                    )
                )
            elif isinstance(item, str):
                alternatives.append(PolicyAlternative(license=item, disposition="unknown"))
    explanation = payload.get("explanation")
    override = payload.get("override") if isinstance(payload.get("override"), str) else None
    return PolicyDecision(
        status=status,
        context=str(context),
        chosen_license=chosen,
        reasons=reasons,
        alternatives=alternatives,
        disclaimer=policy_payload.get("disclaimer") if policy_payload else None,
        explanation=str(explanation) if isinstance(explanation, str) else None,
        override=override,
    )


def process_scan_job(job: Job, config: LCCConfig) -> Dict[str, Any]:
    payload = job.payload or {}
    path = Path(payload["path"]).resolve()
    cache_ttl = int(payload.get("cache_ttl", 3600))
    threshold = float(payload.get("threshold", 0.5))
    cache = Cache(config, ttl_seconds=cache_ttl)
    scanner = Scanner(build_detectors(), build_resolvers(config, cache), config)
    report = scanner.scan(path)
    job_context = payload.get("context")
    if job_context:
        config.policy_context = job_context
    policy_violations, policy_context = apply_policy_to_report(
        report,
        config,
        payload.get("policy"),
        context=job_context,
    )
    if policy_context:
        report.summary.context["policy"] = policy_context
    violations = [finding for finding in report.findings if finding.confidence < threshold or not finding.resolved_license]
    report.summary.violations = len(violations) + policy_violations

    output_path = payload.get("output")
    if output_path:
        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(JSONReporter().render(report), encoding="utf-8")

    return {
        "component_count": report.summary.component_count,
        "violations": report.summary.violations,
    }


def handle_queue_submit(args: argparse.Namespace) -> int:
    console = Console()
    config_path = Path(args.config) if getattr(args, "config", None) else None
    config = load_config(config_path)
    if not config.redis_url:
        console.print("[red]Set LCC_REDIS_URL to use the job queue.[/red]")
        return 1
    try:
        queue = JobQueue(config)
    except QueueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    payload: Dict[str, Any] = {
        "path": args.path,
        "output": args.output,
        "policy": args.policy,
        "cache_ttl": args.cache_ttl,
        "threshold": args.threshold,
    }
    if args.context:
        payload["context"] = args.context
    job = queue.enqueue(
        "scan",
        payload,
        priority=args.priority,
        max_retries=args.max_retries,
    )
    console.print(f"[green]Job {job.id} enqueued (priority {args.priority}).[/green]")
    return 0


def handle_queue_worker(args: argparse.Namespace) -> int:
    console = Console()
    config_path = Path(args.config) if getattr(args, "config", None) else None
    config = load_config(config_path)
    if not config.redis_url:
        console.print("[red]Set LCC_REDIS_URL to use the job queue.[/red]")
        return 1
    try:
        queue = JobQueue(config)
    except QueueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    def handler(job: Job) -> Dict[str, Any]:
        return process_scan_job(job, config)

    if args.once:
        job = queue.fetch()
        if job is None:
            console.print("[yellow]No jobs available.[/yellow]")
            return 0
        try:
            result = handler(job)
            queue.complete(job, result=result)
            console.print(f"[green]Job {job.id} completed.[/green]")
            return 0
        except Exception as exc:  # pragma: no cover - runtime failure
            queue.fail(job, str(exc))
            console.print(f"[red]Job {job.id} failed: {exc}[/red]")
            return 1

    worker = JobQueueWorker(queue, handler, poll_interval=args.poll_interval)
    try:
        worker.run()
    except KeyboardInterrupt:  # pragma: no cover - manual stop
        worker.stop()
        console.print("\n[yellow]Worker stopped.[/yellow]")
    return 0


def handle_queue_status(args: argparse.Namespace) -> int:
    console = Console()
    config_path = Path(args.config) if getattr(args, "config", None) else None
    config = load_config(config_path)
    if not config.redis_url:
        console.print("[red]Set LCC_REDIS_URL to use the job queue.[/red]")
        return 1
    try:
        queue = JobQueue(config)
    except QueueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    stats = queue.stats()
    console.print(
        f"Queued: [bold]{stats['queued']}[/bold]    Dead letter: [bold]{stats['dead']}[/bold]"
    )
    return 0


def handle_sbom_generate(args, console: Console) -> int:
    """Handle SBOM generation command."""
    from lcc.sbom import CycloneDXGenerator, SPDXGenerator
    from rich.panel import Panel

    try:
        console.print(f"[cyan]Generating {args.format.upper()} SBOM...[/cyan]")

        scan_result_path = Path(args.scan_result)
        output_path = Path(args.output)

        if args.format == "cyclonedx":
            generator = CycloneDXGenerator()
            generator.generate_from_file(
                scan_result_path=scan_result_path,
                output_path=output_path,
                format=args.sbom_format,
                project_name=args.project_name,
                project_version=args.project_version,
                author=args.author,
                supplier=args.supplier,
            )
        else:  # spdx
            generator = SPDXGenerator()
            generator.generate_from_file(
                scan_result_path=scan_result_path,
                output_path=output_path,
                format=args.sbom_format,
                project_name=args.project_name,
                project_version=args.project_version,
                creator=args.author,
            )

        console.print(
            Panel(
                f"[green]✓[/green] SBOM generated successfully\n"
                f"Format: {args.format.upper()} ({args.sbom_format})\n"
                f"Output: {output_path}",
                title="Success",
                border_style="green",
            )
        )
        return 0

    except Exception as e:
        console.print(f"[red]Error generating SBOM: {e}[/red]")
        return 1


def handle_sbom_validate(args, console: Console) -> int:
    """Handle SBOM validation command."""
    from lcc.sbom import SBOMValidator

    try:
        sbom_file = Path(args.sbom_file)
        console.print(f"[cyan]Validating SBOM: {sbom_file}[/cyan]")

        validator = SBOMValidator()

        # Validate structure
        is_valid, errors = validator.validate(sbom_file, sbom_type=args.format)

        if is_valid:
            console.print("[green]✓ SBOM structure is valid[/green]")
        else:
            console.print("[red]✗ SBOM validation failed:[/red]")
            for error in errors:
                console.print(f"  [red]- {error}[/red]")

        # Validate licenses if requested
        if args.check_licenses:
            console.print("\n[cyan]Validating license expressions...[/cyan]")
            licenses_valid, warnings = validator.validate_licenses(sbom_file)

            if licenses_valid:
                console.print("[green]✓ All licenses are valid[/green]")
            else:
                console.print("[yellow]⚠ License validation warnings:[/yellow]")
                for warning in warnings:
                    console.print(f"  [yellow]- {warning}[/yellow]")

        return 0 if is_valid else 1

    except Exception as e:
        console.print(f"[red]Error validating SBOM: {e}[/red]")
        return 1


def handle_sbom_sign(args, console: Console) -> int:
    """Handle SBOM signing command."""
    from lcc.sbom import SBOMSigner
    from rich.panel import Panel
    import getpass

    try:
        sbom_file = Path(args.sbom_file)

        # Prompt for passphrase if not provided
        passphrase = args.passphrase
        if not passphrase:
            passphrase = getpass.getpass("Enter key passphrase: ")

        console.print(f"[cyan]Signing SBOM with key: {args.key}[/cyan]")

        gpg_home = Path(args.gpg_home) if args.gpg_home else None
        signer = SBOMSigner(gpg_home=gpg_home)

        output_path = Path(args.output) if args.output else None
        output = signer.sign(
            sbom_path=sbom_file,
            key_id=args.key,
            passphrase=passphrase or None,
            detached=args.detached,
            output_path=output_path,
        )

        sig_type = "Detached signature" if args.detached else "Signed SBOM"
        console.print(
            Panel(
                f"[green]✓[/green] SBOM signed successfully\n"
                f"Type: {sig_type}\n"
                f"Output: {output}",
                title="Success",
                border_style="green",
            )
        )
        return 0

    except Exception as e:
        console.print(f"[red]Error signing SBOM: {e}[/red]")
        return 1


def handle_sbom_verify(args, console: Console) -> int:
    """Handle SBOM verification command."""
    from lcc.sbom import SBOMSigner
    from rich.panel import Panel

    try:
        sbom_file = Path(args.sbom_file)
        signature_path = Path(args.signature) if args.signature else None

        console.print(f"[cyan]Verifying SBOM signature...[/cyan]")

        gpg_home = Path(args.gpg_home) if args.gpg_home else None
        signer = SBOMSigner(gpg_home=gpg_home)

        is_valid, info = signer.verify(sbom_path=sbom_file, signature_path=signature_path)

        if is_valid:
            console.print(
                Panel(
                    f"[green]✓[/green] Signature is valid\n{info}",
                    title="Verified",
                    border_style="green",
                )
            )
            return 0
        else:
            console.print(
                Panel(
                    f"[red]✗[/red] {info}",
                    title="Verification Failed",
                    border_style="red",
                )
            )
            return 1

    except Exception as e:
        console.print(f"[red]Error verifying signature: {e}[/red]")
        return 1


def handle_sbom_hash(args, console: Console) -> int:
    """Handle SBOM hashing command."""
    from lcc.sbom import SBOMSigner
    from rich.panel import Panel

    try:
        sbom_file = Path(args.sbom_file)
        signer = SBOMSigner()
        hash_value = signer.hash_sbom(sbom_file, algorithm=args.algorithm)

        console.print(
            Panel(
                f"[cyan]{args.algorithm.upper()}:[/cyan] {hash_value}",
                title=f"SBOM Hash ({sbom_file.name})",
                border_style="cyan",
            )
        )
        return 0

    except Exception as e:
        console.print(f"[red]Error generating hash: {e}[/red]")
        return 1


def handle_sbom_list_keys(args, console: Console) -> int:
    """Handle listing GPG keys command."""
    from lcc.sbom import SBOMSigner

    try:
        gpg_home = Path(args.gpg_home) if args.gpg_home else None
        signer = SBOMSigner(gpg_home=gpg_home)
        keys = signer.list_keys()

        if not keys:
            console.print("[yellow]No GPG keys found[/yellow]")
            return 0

        table = Table(title="Available GPG Keys")
        table.add_column("Key ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Length", style="blue")
        table.add_column("User IDs", style="green")

        for key in keys:
            table.add_row(
                key["keyid"],
                key["type"],
                str(key["length"]),
                "\n".join(key["uids"]),
            )

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[red]Error listing keys: {e}[/red]")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
