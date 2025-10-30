"""
AI Model License Registry

Comprehensive registry of AI/ML-specific licenses including:
- RAIL (Responsible AI License)
- OpenRAIL (Open Responsible AI License)
- BigScience BLOOM licenses
- Llama licenses
- Other AI-specific licenses

References:
- https://www.licenses.ai/
- https://huggingface.co/spaces/bigscience/license
- https://ai.meta.com/llama/license/
"""

from __future__ import annotations

from typing import Dict, List, Optional


class AILicenseInfo:
    """Information about an AI-specific license."""

    def __init__(
        self,
        id: str,
        name: str,
        spdx_id: Optional[str] = None,
        url: Optional[str] = None,
        category: str = "proprietary",
        commercial_use: bool = True,
        derivatives_allowed: bool = True,
        attribution_required: bool = True,
        share_alike: bool = False,
        use_restrictions: List[str] = None,
        user_threshold: Optional[str] = None,
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
        self.use_restrictions = use_restrictions or []
        self.user_threshold = user_threshold
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
            "use_restrictions": self.use_restrictions,
            "user_threshold": self.user_threshold,
            "description": self.description,
        }


# AI Model Licenses Registry
AI_LICENSES = {
    # OpenRAIL Family
    "openrail": AILicenseInfo(
        id="openrail",
        name="OpenRAIL",
        spdx_id=None,
        url="https://www.licenses.ai/blog/2022/8/18/naming-convention-of-responsible-ai-licenses",
        category="permissive-with-restrictions",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[
            "no-harm",
            "behavioral-restrictions",
        ],
        description="Open Responsible AI License - permissive with use-based restrictions",
    ),
    "openrail-m": AILicenseInfo(
        id="openrail-m",
        name="OpenRAIL-M",
        spdx_id=None,
        url="https://www.licenses.ai/blog/2022/8/26/bigscience-open-rail-m-license",
        category="permissive-with-restrictions",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[
            "no-illegal-activity",
            "no-harm",
            "no-personal-data-exploitation",
            "no-discrimination",
            "no-misinformation",
        ],
        description="OpenRAIL-M for AI models - allows modification and redistribution with use restrictions",
    ),
    "openrail++": AILicenseInfo(
        id="openrail++",
        name="OpenRAIL++",
        spdx_id=None,
        url="https://www.licenses.ai/",
        category="permissive-with-restrictions",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[
            "no-harm",
            "behavioral-restrictions",
            "enhanced-monitoring",
        ],
        description="Enhanced OpenRAIL with additional safeguards",
    ),
    # BigScience BLOOM Licenses
    "bigscience-bloom-rail-1.0": AILicenseInfo(
        id="bigscience-bloom-rail-1.0",
        name="BigScience BLOOM RAIL 1.0",
        spdx_id=None,
        url="https://huggingface.co/spaces/bigscience/license",
        category="permissive-with-restrictions",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[
            "no-illegal-activity",
            "no-harm",
            "no-personal-data-exploitation",
            "no-discrimination",
            "no-misinformation",
            "no-impersonation",
            "no-automated-legal-advice",
        ],
        description="BigScience BLOOM Responsible AI License",
    ),
    "bigscience-openrail-m": AILicenseInfo(
        id="bigscience-openrail-m",
        name="BigScience OpenRAIL-M",
        spdx_id=None,
        url="https://huggingface.co/spaces/bigscience/license",
        category="permissive-with-restrictions",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[
            "no-illegal-activity",
            "no-harm",
            "no-personal-data-exploitation",
        ],
        description="BigScience variant of OpenRAIL-M",
    ),
    # Llama Licenses
    "llama-2": AILicenseInfo(
        id="llama-2",
        name="Llama 2 Community License",
        spdx_id=None,
        url="https://ai.meta.com/llama/license/",
        category="proprietary-with-conditions",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[
            "user-threshold-700m",
            "no-llama-improvement",
        ],
        user_threshold="700M monthly active users",
        description="Meta Llama 2 license - free for commercial use below 700M MAU threshold",
    ),
    "llama-3": AILicenseInfo(
        id="llama-3",
        name="Llama 3 Community License",
        spdx_id=None,
        url="https://ai.meta.com/llama/license/",
        category="proprietary-with-conditions",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[
            "user-threshold-700m",
            "no-llama-improvement",
            "acceptable-use-policy",
        ],
        user_threshold="700M monthly active users",
        description="Meta Llama 3 license with acceptable use policy",
    ),
    "llama-3.1": AILicenseInfo(
        id="llama-3.1",
        name="Llama 3.1 Community License",
        spdx_id=None,
        url="https://ai.meta.com/llama/license/",
        category="proprietary-with-conditions",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[
            "user-threshold-700m",
            "acceptable-use-policy",
        ],
        user_threshold="700M monthly active users",
        description="Meta Llama 3.1 license",
    ),
    # CreativeML (Stable Diffusion)
    "creativeml-openrail-m": AILicenseInfo(
        id="creativeml-openrail-m",
        name="CreativeML OpenRAIL-M",
        spdx_id=None,
        url="https://huggingface.co/spaces/CompVis/stable-diffusion-license",
        category="permissive-with-restrictions",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[
            "no-illegal-activity",
            "no-harm",
            "no-deception",
            "no-personal-data-exploitation",
        ],
        description="CreativeML OpenRAIL-M for Stable Diffusion models",
    ),
    # Google DeepMind
    "deepmind-gemma": AILicenseInfo(
        id="deepmind-gemma",
        name="Gemma Terms of Use",
        spdx_id=None,
        url="https://ai.google.dev/gemma/terms",
        category="proprietary-with-conditions",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[
            "no-harm",
            "no-impersonation",
            "attribution-required",
        ],
        description="Google DeepMind Gemma model license",
    ),
    # Mistral AI
    "mistral-ai": AILicenseInfo(
        id="mistral-ai",
        name="Mistral AI License",
        spdx_id=None,
        url="https://mistral.ai/licenses/",
        category="permissive",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[],
        description="Mistral AI model license - Apache 2.0 for most models",
    ),
    # Anthropic
    "anthropic-claude": AILicenseInfo(
        id="anthropic-claude",
        name="Anthropic Commercial Terms",
        spdx_id=None,
        url="https://www.anthropic.com/legal/commercial-terms",
        category="proprietary",
        commercial_use=True,
        derivatives_allowed=False,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[
            "api-only",
            "no-distribution",
            "acceptable-use-policy",
        ],
        description="Anthropic Claude API terms - proprietary SaaS",
    ),
    # OpenAI
    "openai-gpt": AILicenseInfo(
        id="openai-gpt",
        name="OpenAI GPT Model License",
        spdx_id=None,
        url="https://openai.com/policies/terms-of-use",
        category="proprietary",
        commercial_use=True,
        derivatives_allowed=False,
        attribution_required=False,
        share_alike=False,
        use_restrictions=[
            "api-only",
            "no-distribution",
            "usage-policies",
        ],
        description="OpenAI GPT models - API only, no redistribution",
    ),
    # Cohere
    "cohere": AILicenseInfo(
        id="cohere",
        name="Cohere Terms of Use",
        spdx_id=None,
        url="https://cohere.com/terms-of-use",
        category="proprietary",
        commercial_use=True,
        derivatives_allowed=False,
        attribution_required=False,
        share_alike=False,
        use_restrictions=[
            "api-only",
            "acceptable-use-policy",
        ],
        description="Cohere API terms",
    ),
    # AI21 Labs
    "ai21-jurassic": AILicenseInfo(
        id="ai21-jurassic",
        name="AI21 Labs Terms",
        spdx_id=None,
        url="https://www.ai21.com/terms-of-use",
        category="proprietary",
        commercial_use=True,
        derivatives_allowed=False,
        attribution_required=False,
        share_alike=False,
        use_restrictions=[
            "api-only",
        ],
        description="AI21 Labs Jurassic model terms",
    ),
    # Standard Open Source Licenses (commonly used for AI models)
    "apache-2.0-ai": AILicenseInfo(
        id="apache-2.0-ai",
        name="Apache 2.0 (AI Models)",
        spdx_id="Apache-2.0",
        url="https://www.apache.org/licenses/LICENSE-2.0",
        category="permissive",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[],
        description="Apache 2.0 license applied to AI models",
    ),
    "mit-ai": AILicenseInfo(
        id="mit-ai",
        name="MIT (AI Models)",
        spdx_id="MIT",
        url="https://opensource.org/licenses/MIT",
        category="permissive",
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        share_alike=False,
        use_restrictions=[],
        description="MIT license applied to AI models",
    ),
}


def get_ai_license_info(license_id: str) -> Optional[AILicenseInfo]:
    """
    Get AI license information by ID.

    Args:
        license_id: License identifier (case-insensitive)

    Returns:
        AILicenseInfo object or None if not found
    """
    return AI_LICENSES.get(license_id.lower())


def normalize_ai_license_name(name: str) -> Optional[str]:
    """
    Normalize AI license name to standard ID.

    Handles common variations and aliases.

    Args:
        name: License name from model card or metadata

    Returns:
        Normalized license ID or None
    """
    name_lower = name.lower().strip()

    # Direct matches
    if name_lower in AI_LICENSES:
        return name_lower

    # Common aliases and variations
    aliases = {
        "openrail-m": ["open-rail-m", "openrailm", "open rail m"],
        "bigscience-bloom-rail-1.0": [
            "bloom rail",
            "bloom-rail",
            "bigscience rail",
            "bigscience-rail",
        ],
        "llama-2": ["llama2", "llama 2", "llama2 community license"],
        "llama-3": ["llama3", "llama 3", "llama3 community license"],
        "llama-3.1": ["llama3.1", "llama 3.1"],
        "creativeml-openrail-m": [
            "creativeml",
            "stable diffusion license",
            "sd license",
        ],
        "deepmind-gemma": ["gemma", "gemma license", "gemma terms"],
        "apache-2.0-ai": ["apache-2.0", "apache 2.0", "apache2"],
        "mit-ai": ["mit", "mit license"],
    }

    for license_id, alias_list in aliases.items():
        if name_lower in alias_list:
            return license_id

    return None


def is_commercial_allowed(license_id: str) -> bool:
    """
    Check if commercial use is allowed for a license.

    Args:
        license_id: License identifier

    Returns:
        True if commercial use is allowed
    """
    info = get_ai_license_info(license_id)
    if info:
        return info.commercial_use
    return False


def get_license_restrictions(license_id: str) -> List[str]:
    """
    Get use restrictions for a license.

    Args:
        license_id: License identifier

    Returns:
        List of restriction descriptions
    """
    info = get_ai_license_info(license_id)
    if info:
        return info.use_restrictions
    return []


def has_user_threshold(license_id: str) -> Optional[str]:
    """
    Check if license has a user threshold restriction.

    Args:
        license_id: License identifier

    Returns:
        User threshold description or None
    """
    info = get_ai_license_info(license_id)
    if info:
        return info.user_threshold
    return None
