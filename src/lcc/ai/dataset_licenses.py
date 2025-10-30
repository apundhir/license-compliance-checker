"""
Dataset License Registry

Comprehensive registry of dataset-specific licenses including:
- Creative Commons variants
- ODbL (Open Database License)
- CDLA (Community Data License Agreement)
- Public domain dedications
- Dataset-specific licenses

References:
- https://creativecommons.org/licenses/
- https://opendatacommons.org/licenses/
- https://cdla.dev/
"""

from __future__ import annotations

from typing import Dict, List, Optional


class DatasetLicenseInfo:
    """Information about a dataset license."""

    def __init__(
        self,
        id: str,
        name: str,
        spdx_id: Optional[str] = None,
        url: Optional[str] = None,
        category: str = "permissive",
        commercial_use: bool = True,
        derivatives_allowed: bool = True,
        attribution_required: bool = False,
        share_alike: bool = False,
        restrictions: List[str] = None,
        description: str = "",
    ):
        self.id = id
        self.name = name
        self.spdx_id = spdx_id
        self.url = url
        self.category = category
        self.commercial_use = commercial_use
        self.derivatives_allowed = derivatives_allowed
        self.attribution_required = attribution_required
        self.share_alike = share_alike
        self.restrictions = restrictions or []
        self.description = description

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "spdx_id": self.spdx_id,
            "url": self.url,
            "category": self.category,
            "commercial_use": self.commercial_use,
            "derivatives_allowed": self.derivatives_allowed,
            "attribution_required": self.attribution_required,
            "share_alike": self.share_alike,
            "restrictions": self.restrictions,
            "description": self.description,
        }


# Dataset Licenses Registry
DATASET_LICENSES = {
    # Public Domain
    "cc0-1.0": DatasetLicenseInfo(
        id="cc0-1.0",
        name="CC0 1.0 Universal",
        spdx_id="CC0-1.0",
        url="https://creativecommons.org/publicdomain/zero/1.0/",
        category="public-domain",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=False,
        share_alike=False,
        restrictions=[],
        description="Creative Commons Zero - Public domain dedication",
    ),
    "pddl-1.0": DatasetLicenseInfo(
        id="pddl-1.0",
        name="Public Domain Dedication and License 1.0",
        spdx_id="PDDL-1.0",
        url="https://opendatacommons.org/licenses/pddl/1-0/",
        category="public-domain",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=False,
        share_alike=False,
        restrictions=[],
        description="ODC Public Domain Dedication and License",
    ),
    # Creative Commons - Attribution
    "cc-by-4.0": DatasetLicenseInfo(
        id="cc-by-4.0",
        name="Creative Commons Attribution 4.0",
        spdx_id="CC-BY-4.0",
        url="https://creativecommons.org/licenses/by/4.0/",
        category="permissive",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        restrictions=[],
        description="CC BY 4.0 - Permissive with attribution requirement",
    ),
    "cc-by-3.0": DatasetLicenseInfo(
        id="cc-by-3.0",
        name="Creative Commons Attribution 3.0",
        spdx_id="CC-BY-3.0",
        url="https://creativecommons.org/licenses/by/3.0/",
        category="permissive",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        restrictions=[],
        description="CC BY 3.0 - Older version",
    ),
    # Creative Commons - Attribution ShareAlike
    "cc-by-sa-4.0": DatasetLicenseInfo(
        id="cc-by-sa-4.0",
        name="Creative Commons Attribution ShareAlike 4.0",
        spdx_id="CC-BY-SA-4.0",
        url="https://creativecommons.org/licenses/by-sa/4.0/",
        category="copyleft",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=True,
        restrictions=["share-alike"],
        description="CC BY-SA 4.0 - Copyleft, derivatives must use same license",
    ),
    "cc-by-sa-3.0": DatasetLicenseInfo(
        id="cc-by-sa-3.0",
        name="Creative Commons Attribution ShareAlike 3.0",
        spdx_id="CC-BY-SA-3.0",
        url="https://creativecommons.org/licenses/by-sa/3.0/",
        category="copyleft",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=True,
        restrictions=["share-alike"],
        description="CC BY-SA 3.0 - Older version",
    ),
    # Creative Commons - NonCommercial
    "cc-by-nc-4.0": DatasetLicenseInfo(
        id="cc-by-nc-4.0",
        name="Creative Commons Attribution NonCommercial 4.0",
        spdx_id="CC-BY-NC-4.0",
        url="https://creativecommons.org/licenses/by-nc/4.0/",
        category="non-commercial",
        commercial_use=False,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        restrictions=["non-commercial"],
        description="CC BY-NC 4.0 - No commercial use allowed",
    ),
    "cc-by-nc-sa-4.0": DatasetLicenseInfo(
        id="cc-by-nc-sa-4.0",
        name="Creative Commons Attribution NonCommercial ShareAlike 4.0",
        spdx_id="CC-BY-NC-SA-4.0",
        url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
        category="non-commercial",
        commercial_use=False,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=True,
        restrictions=["non-commercial", "share-alike"],
        description="CC BY-NC-SA 4.0 - Non-commercial, share-alike",
    ),
    # Creative Commons - NoDerivatives
    "cc-by-nd-4.0": DatasetLicenseInfo(
        id="cc-by-nd-4.0",
        name="Creative Commons Attribution NoDerivatives 4.0",
        spdx_id="CC-BY-ND-4.0",
        url="https://creativecommons.org/licenses/by-nd/4.0/",
        category="restricted",
        commercial_use=True,
        derivatives_allowed=False,
        attribution_required=True,
        share_alike=False,
        restrictions=["no-derivatives"],
        description="CC BY-ND 4.0 - No derivatives allowed",
    ),
    "cc-by-nc-nd-4.0": DatasetLicenseInfo(
        id="cc-by-nc-nd-4.0",
        name="Creative Commons Attribution NonCommercial NoDerivatives 4.0",
        spdx_id="CC-BY-NC-ND-4.0",
        url="https://creativecommons.org/licenses/by-nc-nd/4.0/",
        category="restricted",
        commercial_use=False,
        derivatives_allowed=False,
        attribution_required=True,
        share_alike=False,
        restrictions=["non-commercial", "no-derivatives"],
        description="CC BY-NC-ND 4.0 - Most restrictive CC license",
    ),
    # Open Database License
    "odbl-1.0": DatasetLicenseInfo(
        id="odbl-1.0",
        name="Open Database License 1.0",
        spdx_id="ODbL-1.0",
        url="https://opendatacommons.org/licenses/odbl/1-0/",
        category="copyleft",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=True,
        restrictions=["share-alike"],
        description="ODbL 1.0 - Database-specific copyleft license",
    ),
    "odc-by-1.0": DatasetLicenseInfo(
        id="odc-by-1.0",
        name="Open Data Commons Attribution License 1.0",
        spdx_id="ODC-By-1.0",
        url="https://opendatacommons.org/licenses/by/1-0/",
        category="permissive",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        restrictions=[],
        description="ODC-By 1.0 - Permissive database license",
    ),
    # Community Data License Agreement
    "cdla-permissive-1.0": DatasetLicenseInfo(
        id="cdla-permissive-1.0",
        name="Community Data License Agreement - Permissive 1.0",
        spdx_id="CDLA-Permissive-1.0",
        url="https://cdla.dev/permissive-1-0/",
        category="permissive",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=False,
        share_alike=False,
        restrictions=[],
        description="CDLA Permissive - Liberal data sharing license",
    ),
    "cdla-sharing-1.0": DatasetLicenseInfo(
        id="cdla-sharing-1.0",
        name="Community Data License Agreement - Sharing 1.0",
        spdx_id="CDLA-Sharing-1.0",
        url="https://cdla.dev/sharing-1-0/",
        category="copyleft",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=False,
        share_alike=True,
        restrictions=["share-alike"],
        description="CDLA Sharing - Copyleft data license",
    ),
    # Dataset-Specific Licenses
    "imagenet": DatasetLicenseInfo(
        id="imagenet",
        name="ImageNet Terms of Access",
        spdx_id=None,
        url="https://www.image-net.org/download.php",
        category="restricted",
        commercial_use=False,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        restrictions=["research-only", "no-redistribution"],
        description="ImageNet dataset - Research use only",
    ),
    "coco": DatasetLicenseInfo(
        id="coco",
        name="COCO Dataset License",
        spdx_id=None,
        url="https://cocodataset.org/#termsofuse",
        category="permissive",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        restrictions=[],
        description="Microsoft COCO dataset",
    ),
    "openimages": DatasetLicenseInfo(
        id="openimages",
        name="Open Images Dataset License",
        spdx_id="CC-BY-4.0",
        url="https://storage.googleapis.com/openimages/web/factsfigures.html",
        category="permissive",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        restrictions=[],
        description="Google Open Images - CC BY 4.0",
    ),
    # Kaggle Competition Licenses
    "kaggle-competition": DatasetLicenseInfo(
        id="kaggle-competition",
        name="Kaggle Competition License",
        spdx_id=None,
        url="https://www.kaggle.com/competitions",
        category="restricted",
        commercial_use=False,
        derivatives_allowed=False,
        attribution_required=True,
        share_alike=False,
        restrictions=["competition-only", "no-redistribution"],
        description="Kaggle competition dataset - Competition use only",
    ),
    # Unknown/Other
    "other": DatasetLicenseInfo(
        id="other",
        name="Other/Unknown Dataset License",
        spdx_id=None,
        url=None,
        category="unknown",
        commercial_use=False,
        derivatives_allowed=False,
        attribution_required=True,
        share_alike=False,
        restrictions=["manual-review-required"],
        description="Unknown or custom dataset license - requires manual review",
    ),
}


def get_dataset_license_info(license_id: str) -> Optional[DatasetLicenseInfo]:
    """
    Get dataset license information by ID.

    Args:
        license_id: License identifier (case-insensitive)

    Returns:
        DatasetLicenseInfo object or None if not found
    """
    return DATASET_LICENSES.get(license_id.lower())


def normalize_dataset_license_name(name: str) -> Optional[str]:
    """
    Normalize dataset license name to standard ID.

    Handles common variations and aliases.

    Args:
        name: License name from dataset card or metadata

    Returns:
        Normalized license ID or None
    """
    name_lower = name.lower().strip()

    # Direct matches
    if name_lower in DATASET_LICENSES:
        return name_lower

    # Common aliases
    aliases = {
        "cc0-1.0": ["cc0", "public domain", "cc zero"],
        "cc-by-4.0": ["cc by", "cc-by", "cc attribution"],
        "cc-by-sa-4.0": ["cc by-sa", "cc-by-sa", "cc share-alike"],
        "cc-by-nc-4.0": ["cc by-nc", "cc-by-nc", "cc non-commercial"],
        "cc-by-nc-sa-4.0": ["cc by-nc-sa", "cc-by-nc-sa"],
        "cc-by-nd-4.0": ["cc by-nd", "cc-by-nd", "cc no-derivatives"],
        "cc-by-nc-nd-4.0": ["cc by-nc-nd", "cc-by-nc-nd"],
        "odbl-1.0": ["odbl", "open database license"],
        "odc-by-1.0": ["odc-by", "odc by"],
        "cdla-permissive-1.0": ["cdla permissive", "cdla-permissive"],
        "cdla-sharing-1.0": ["cdla sharing", "cdla-sharing"],
    }

    for license_id, alias_list in aliases.items():
        if name_lower in alias_list:
            return license_id

    return None


def is_dataset_commercial_allowed(license_id: str) -> bool:
    """
    Check if commercial use is allowed for a dataset license.

    Args:
        license_id: License identifier

    Returns:
        True if commercial use is allowed
    """
    info = get_dataset_license_info(license_id)
    if info:
        return info.commercial_use
    return False


def get_dataset_restrictions(license_id: str) -> List[str]:
    """
    Get restrictions for a dataset license.

    Args:
        license_id: License identifier

    Returns:
        List of restriction descriptions
    """
    info = get_dataset_license_info(license_id)
    if info:
        return info.restrictions
    return []
