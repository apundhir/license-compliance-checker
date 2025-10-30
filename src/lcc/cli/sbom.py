"""
SBOM CLI commands for generating, validating, and signing SBOMs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lcc.sbom import CycloneDXGenerator, SPDXGenerator, SBOMSigner, SBOMValidator

console = Console()


@click.group()
def sbom():
    """SBOM generation, validation, and signing commands."""
    pass


@sbom.command()
@click.option(
    "--scan-result",
    "-s",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to scan result JSON file",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output SBOM file path",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["cyclonedx", "spdx"], case_sensitive=False),
    default="cyclonedx",
    help="SBOM format (cyclonedx or spdx)",
)
@click.option(
    "--sbom-format",
    type=click.Choice(["json", "xml", "yaml", "tag-value"], case_sensitive=False),
    default="json",
    help="Output file format",
)
@click.option(
    "--project-name",
    type=str,
    help="Project name",
)
@click.option(
    "--project-version",
    type=str,
    help="Project version",
)
@click.option(
    "--author",
    type=str,
    help="Author/creator name",
)
@click.option(
    "--supplier",
    type=str,
    help="Supplier/organization name",
)
def generate(
    scan_result: Path,
    output: Path,
    format: str,
    sbom_format: str,
    project_name: Optional[str],
    project_version: Optional[str],
    author: Optional[str],
    supplier: Optional[str],
):
    """Generate SBOM from scan result."""
    try:
        console.print(f"[cyan]Generating {format.upper()} SBOM...[/cyan]")

        if format.lower() == "cyclonedx":
            generator = CycloneDXGenerator()
            generator.generate_from_file(
                scan_result_path=scan_result,
                output_path=output,
                format=sbom_format,
                project_name=project_name,
                project_version=project_version,
                author=author,
                supplier=supplier,
            )
        else:  # spdx
            generator = SPDXGenerator()
            generator.generate_from_file(
                scan_result_path=scan_result,
                output_path=output,
                format=sbom_format,
                project_name=project_name,
                project_version=project_version,
                creator=author,
            )

        console.print(
            Panel(
                f"[green]✓[/green] SBOM generated successfully\n"
                f"Format: {format.upper()} ({sbom_format})\n"
                f"Output: {output}",
                title="Success",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]Error generating SBOM: {e}[/red]")
        sys.exit(1)


@sbom.command()
@click.argument("sbom-file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["cyclonedx", "spdx", "auto"], case_sensitive=False),
    default="auto",
    help="SBOM format (auto-detects if not specified)",
)
@click.option(
    "--check-licenses",
    is_flag=True,
    help="Also validate license expressions",
)
def validate(sbom_file: Path, format: str, check_licenses: bool):
    """Validate an SBOM file."""
    try:
        console.print(f"[cyan]Validating SBOM: {sbom_file}[/cyan]")

        validator = SBOMValidator()

        # Validate structure
        is_valid, errors = validator.validate(sbom_file, sbom_type=format)

        if is_valid:
            console.print("[green]✓ SBOM structure is valid[/green]")
        else:
            console.print("[red]✗ SBOM validation failed:[/red]")
            for error in errors:
                console.print(f"  [red]- {error}[/red]")

        # Validate licenses if requested
        if check_licenses:
            console.print("\n[cyan]Validating license expressions...[/cyan]")
            licenses_valid, warnings = validator.validate_licenses(sbom_file)

            if licenses_valid:
                console.print("[green]✓ All licenses are valid[/green]")
            else:
                console.print("[yellow]⚠ License validation warnings:[/yellow]")
                for warning in warnings:
                    console.print(f"  [yellow]- {warning}[/yellow]")

        if not is_valid:
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error validating SBOM: {e}[/red]")
        sys.exit(1)


@sbom.command()
@click.argument("sbom-file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--key",
    "-k",
    type=str,
    required=True,
    help="GPG key ID or email to sign with",
)
@click.option(
    "--passphrase",
    "-p",
    type=str,
    help="Key passphrase (prompted if not provided)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output path (defaults to <sbom>.signed.<ext>)",
)
@click.option(
    "--detached",
    is_flag=True,
    help="Create detached signature (.sig file)",
)
@click.option(
    "--gpg-home",
    type=click.Path(path_type=Path),
    help="GPG home directory (defaults to ~/.gnupg)",
)
def sign(
    sbom_file: Path,
    key: str,
    passphrase: Optional[str],
    output: Optional[Path],
    detached: bool,
    gpg_home: Optional[Path],
):
    """Sign an SBOM file with GPG."""
    try:
        # Prompt for passphrase if not provided
        if not passphrase:
            passphrase = click.prompt(
                "Enter key passphrase", hide_input=True, default="", show_default=False
            )

        console.print(f"[cyan]Signing SBOM with key: {key}[/cyan]")

        signer = SBOMSigner(gpg_home=gpg_home)
        output_path = signer.sign(
            sbom_path=sbom_file,
            key_id=key,
            passphrase=passphrase or None,
            detached=detached,
            output_path=output,
        )

        sig_type = "Detached signature" if detached else "Signed SBOM"
        console.print(
            Panel(
                f"[green]✓[/green] SBOM signed successfully\n"
                f"Type: {sig_type}\n"
                f"Output: {output_path}",
                title="Success",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]Error signing SBOM: {e}[/red]")
        sys.exit(1)


@sbom.command()
@click.argument("sbom-file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--signature",
    "-s",
    type=click.Path(exists=True, path_type=Path),
    help="Path to detached signature file",
)
@click.option(
    "--gpg-home",
    type=click.Path(path_type=Path),
    help="GPG home directory (defaults to ~/.gnupg)",
)
def verify(sbom_file: Path, signature: Optional[Path], gpg_home: Optional[Path]):
    """Verify an SBOM signature."""
    try:
        console.print(f"[cyan]Verifying SBOM signature...[/cyan]")

        signer = SBOMSigner(gpg_home=gpg_home)
        is_valid, info = signer.verify(sbom_path=sbom_file, signature_path=signature)

        if is_valid:
            console.print(
                Panel(
                    f"[green]✓[/green] Signature is valid\n{info}",
                    title="Verified",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[red]✗[/red] {info}",
                    title="Verification Failed",
                    border_style="red",
                )
            )
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error verifying signature: {e}[/red]")
        sys.exit(1)


@sbom.command()
@click.argument("sbom-file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--algorithm",
    "-a",
    type=click.Choice(["sha256", "sha512", "sha1"], case_sensitive=False),
    default="sha256",
    help="Hash algorithm",
)
def hash(sbom_file: Path, algorithm: str):
    """Generate cryptographic hash of SBOM."""
    try:
        signer = SBOMSigner()
        hash_value = signer.hash_sbom(sbom_file, algorithm=algorithm)

        console.print(
            Panel(
                f"[cyan]{algorithm.upper()}:[/cyan] {hash_value}",
                title=f"SBOM Hash ({sbom_file.name})",
                border_style="cyan",
            )
        )

    except Exception as e:
        console.print(f"[red]Error generating hash: {e}[/red]")
        sys.exit(1)


@sbom.command(name="list-keys")
@click.option(
    "--gpg-home",
    type=click.Path(path_type=Path),
    help="GPG home directory (defaults to ~/.gnupg)",
)
def list_keys(gpg_home: Optional[Path]):
    """List available GPG keys for signing."""
    try:
        signer = SBOMSigner(gpg_home=gpg_home)
        keys = signer.list_keys()

        if not keys:
            console.print("[yellow]No GPG keys found[/yellow]")
            return

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

    except Exception as e:
        console.print(f"[red]Error listing keys: {e}[/red]")
        sys.exit(1)
