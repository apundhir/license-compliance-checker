"""
HuggingFace Hub API resolver — fetches license/metadata for models
referenced by Hub ID without requiring local download.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

HF_API_BASE = "https://huggingface.co/api"
HF_CACHE: dict[str, dict] = {}  # Simple in-memory cache


@dataclass
class HFModelInfo:
    model_id: str
    license: str | None
    datasets: list[str]
    tags: list[str]
    pipeline_tag: str | None
    use_restrictions: list[str]
    card_data: dict


def fetch_model_info(model_id: str, hf_token: str | None = None) -> HFModelInfo | None:
    """Fetch model metadata from HuggingFace Hub API.

    Args:
        model_id: HuggingFace model ID e.g. 'meta-llama/Llama-3.1-70B-Instruct'
        hf_token: Optional HF API token for private models or higher rate limits

    Returns:
        HFModelInfo or None if fetch fails
    """
    if model_id in HF_CACHE:
        return HF_CACHE[model_id]

    url = f"{HF_API_BASE}/models/{model_id}"
    headers = {"Accept": "application/json"}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        logger.warning("HF Hub API fetch failed for %s: %s", model_id, exc)
        return None

    # Extract license from cardData or tags
    card_data = data.get("cardData") or {}
    license_val = (
        card_data.get("license")
        or next((t.replace("license:", "") for t in data.get("tags", []) if t.startswith("license:")), None)
    )

    # Extract datasets used in training
    datasets = card_data.get("datasets") or data.get("datasets") or []
    if isinstance(datasets, list):
        datasets = [d if isinstance(d, str) else d.get("id", str(d)) for d in datasets]

    # Extract use restrictions from card_data
    use_restrictions: list[str] = []
    for field in ("restrictions", "license_restrictions", "use_restrictions"):
        val = card_data.get(field)
        if isinstance(val, list):
            use_restrictions.extend(str(v) for v in val)
        elif isinstance(val, str):
            use_restrictions.append(val)

    info = HFModelInfo(
        model_id=model_id,
        license=license_val,
        datasets=datasets,
        tags=data.get("tags", []),
        pipeline_tag=data.get("pipeline_tag"),
        use_restrictions=use_restrictions,
        card_data=card_data,
    )
    HF_CACHE[model_id] = info
    return info


# Patterns that match HF model ID references in Python source code
_MODEL_ID_PATTERNS = [
    # from_pretrained("org/model") and similar
    re.compile(r"""from_pretrained\s*\(\s*['"]([\w.\-]+/[\w.\-]+)['"]"""),
    # model_name_or_path: "org/model" in YAML/JSON configs
    re.compile(r"""model(?:_name|_name_or_path|_id)["']?\s*[:=]\s*['"]([\w.\-]+/[\w.\-]+)['"]"""),
    # --model org/model CLI args
    re.compile(r"""--model\s+([\w.\-]+/[\w.\-]+)"""),
    # Ollama and vLLM patterns: model="org/model"
    re.compile(r"""model\s*=\s*['"]([\w.\-]+/[\w.\-]+)['"]"""),
]


def extract_model_ids_from_source(source_code: str) -> list[str]:
    """Extract HuggingFace model IDs referenced in Python/config source code."""
    found: set[str] = set()
    for pattern in _MODEL_ID_PATTERNS:
        for match in pattern.finditer(source_code):
            model_id = match.group(1)
            # Filter out local paths and non-HF IDs
            if "/" in model_id and not model_id.startswith(("./", "../", "/")):
                found.add(model_id)
    return sorted(found)
