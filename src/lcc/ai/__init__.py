"""AI/ML subsystem for License Compliance Checker."""

from lcc.ai.licenses import AI_LICENSES, get_ai_license_info
from lcc.ai.dataset_licenses import DATASET_LICENSES, get_dataset_license_info

__all__ = [
    "AI_LICENSES",
    "get_ai_license_info",
    "DATASET_LICENSES",
    "get_dataset_license_info",
]
