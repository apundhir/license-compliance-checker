"""
SBOM Signer - Digital signature support for SBOM documents.

Supports GPG/PGP signing for authenticity and integrity verification.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

try:
    import gnupg
except ImportError:
    gnupg = None


class SigningError(Exception):
    """SBOM signing error."""

    pass


class SBOMSigner:
    """
    Signs and verifies SBOM documents using GPG.

    Features:
    - GPG/PGP signature generation
    - Signature verification
    - Embedded or detached signatures
    - Timestamp support
    """

    def __init__(self, gpg_home: Optional[Path] = None) -> None:
        """
        Initialize the signer.

        Args:
            gpg_home: Path to GPG home directory (defaults to ~/.gnupg)
        """
        if gnupg is None:
            raise ImportError(
                "python-gnupg is required for signing. "
                "Install it with: pip install python-gnupg"
            )

        self.gpg = gnupg.GPG(gnupghome=str(gpg_home) if gpg_home else None)

    def sign(
        self,
        sbom_path: Path,
        key_id: str,
        passphrase: Optional[str] = None,
        detached: bool = False,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Sign an SBOM document.

        Args:
            sbom_path: Path to SBOM file
            key_id: GPG key ID or email to sign with
            passphrase: Key passphrase (if required)
            detached: Create detached signature (.sig file)
            output_path: Output path (defaults to sbom_path + .signed or .sig)

        Returns:
            Path to signed SBOM or signature file
        """
        # Read SBOM content
        with open(sbom_path, "rb") as f:
            content = f.read()

        if detached:
            # Create detached signature
            signature = self.gpg.sign(
                content,
                keyid=key_id,
                passphrase=passphrase,
                detach=True,
            )

            if not signature:
                raise SigningError(f"Failed to sign SBOM: {signature.stderr}")

            # Save signature
            if not output_path:
                output_path = sbom_path.with_suffix(sbom_path.suffix + ".sig")

            with open(output_path, "wb") as f:
                f.write(str(signature).encode("utf-8"))

            return output_path

        else:
            # Create embedded signature
            signature = self.gpg.sign(
                content,
                keyid=key_id,
                passphrase=passphrase,
                detach=False,
            )

            if not signature:
                raise SigningError(f"Failed to sign SBOM: {signature.stderr}")

            # For JSON, embed signature in document
            if sbom_path.suffix.lower() == ".json":
                signed_sbom = self._embed_json_signature(
                    sbom_path, str(signature), key_id
                )

                if not output_path:
                    stem = sbom_path.stem
                    output_path = sbom_path.with_name(f"{stem}.signed.json")

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(signed_sbom, f, indent=2)

            else:
                # For other formats, save signed content
                if not output_path:
                    stem = sbom_path.stem
                    suffix = sbom_path.suffix
                    output_path = sbom_path.with_name(f"{stem}.signed{suffix}")

                with open(output_path, "wb") as f:
                    f.write(str(signature).encode("utf-8"))

            return output_path

    def verify(
        self,
        sbom_path: Path,
        signature_path: Optional[Path] = None,
    ) -> Tuple[bool, str]:
        """
        Verify an SBOM signature.

        Args:
            sbom_path: Path to SBOM file
            signature_path: Path to detached signature (if applicable)

        Returns:
            Tuple of (is_valid, signer_info)
        """
        if signature_path:
            # Verify detached signature
            with open(sbom_path, "rb") as f:
                content = f.read()

            with open(signature_path, "rb") as f:
                signature = f.read()

            verified = self.gpg.verify_data(signature, content)

            if verified:
                signer = verified.username or verified.key_id
                return True, f"Signed by: {signer}"
            else:
                return False, f"Verification failed: {verified.stderr}"

        else:
            # Verify embedded signature
            if sbom_path.suffix.lower() == ".json":
                # Check for embedded signature in JSON
                with open(sbom_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if "signature" in data:
                    signature = data["signature"].get("value", "")
                    # Extract original content (remove signature field)
                    original_data = {k: v for k, v in data.items() if k != "signature"}
                    original_content = json.dumps(
                        original_data, indent=2, sort_keys=True
                    ).encode("utf-8")

                    verified = self.gpg.verify_data(
                        signature.encode("utf-8"), original_content
                    )

                    if verified:
                        signer = verified.username or verified.key_id
                        return True, f"Signed by: {signer}"
                    else:
                        return False, f"Verification failed: {verified.stderr}"

            # Try to verify as signed file
            with open(sbom_path, "rb") as f:
                content = f.read()

            verified = self.gpg.verify_data(content, None)

            if verified:
                signer = verified.username or verified.key_id
                return True, f"Signed by: {signer}"
            else:
                return False, "No signature found or verification failed"

    def _embed_json_signature(
        self, sbom_path: Path, signature: str, signer: str
    ) -> dict:
        """
        Embed signature in JSON SBOM.

        Args:
            sbom_path: Path to SBOM file
            signature: PGP signature
            signer: Signer identifier

        Returns:
            SBOM with embedded signature
        """
        with open(sbom_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Add signature metadata
        data["signature"] = {
            "algorithm": "PGP",
            "value": signature,
            "signer": signer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return data

    def hash_sbom(self, sbom_path: Path, algorithm: str = "sha256") -> str:
        """
        Generate cryptographic hash of SBOM.

        Args:
            sbom_path: Path to SBOM file
            algorithm: Hash algorithm ("sha256", "sha512", "sha1")

        Returns:
            Hexadecimal hash value
        """
        hash_func = {
            "sha1": hashlib.sha1,
            "sha256": hashlib.sha256,
            "sha512": hashlib.sha512,
        }.get(algorithm.lower())

        if not hash_func:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        with open(sbom_path, "rb") as f:
            content = f.read()

        return hash_func(content).hexdigest()

    def list_keys(self) -> list:
        """
        List available GPG keys.

        Returns:
            List of key information dicts
        """
        keys = self.gpg.list_keys()
        return [
            {
                "keyid": key["keyid"],
                "fingerprint": key["fingerprint"],
                "uids": key["uids"],
                "length": key["length"],
                "type": key["type"],
            }
            for key in keys
        ]

    def import_key(self, key_data: str) -> bool:
        """
        Import a GPG key.

        Args:
            key_data: ASCII-armored key data

        Returns:
            True if successful
        """
        result = self.gpg.import_keys(key_data)
        return result.count > 0

    def export_public_key(self, key_id: str) -> str:
        """
        Export public key in ASCII-armored format.

        Args:
            key_id: Key ID or email

        Returns:
            ASCII-armored public key
        """
        return self.gpg.export_keys(key_id)
