"""
Configuration loading utilities.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    yaml = None
from platformdirs import user_cache_dir

DEFAULT_CONFIG_PATH = Path.home() / ".lcc" / "config.yml"


@dataclass(slots=True)
class LCCConfig:
    """
    High-level configuration model.
    """

    cache_dir: Path = field(
        default_factory=lambda: Path(os.getenv("LCC_CACHE_DIR", user_cache_dir("lcc", "License Compliance Checker")))
    )
    log_level: str = os.getenv("LCC_LOG_LEVEL", "INFO")
    api_tokens: Dict[str, str] = field(default_factory=dict)
    timeouts: Dict[str, float] = field(default_factory=lambda: {"default": 10.0})
    offline: bool = os.getenv("LCC_OFFLINE", "0") in {"1", "true", "TRUE"}
    active_policy: Optional[str] = None
    policy_context: Optional[str] = os.getenv("LCC_POLICY_CONTEXT")
    opa_url: Optional[str] = os.getenv("LCC_OPA_URL")
    opa_token: Optional[str] = os.getenv("LCC_OPA_TOKEN")
    database_path: Path = field(
        default_factory=lambda: Path(os.getenv("LCC_DB_PATH", Path.home() / ".lcc" / "lcc.db"))
    )
    decision_log_path: Path = field(
        default_factory=lambda: Path(os.getenv("LCC_DECISION_LOG", Path.home() / ".lcc" / "decisions.jsonl"))
    )
    redis_url: Optional[str] = os.getenv("LCC_REDIS_URL")
    cache_ttls: Dict[str, int] = field(default_factory=dict)
    template_dir: Path = field(
        default_factory=lambda: Path(os.getenv("LCC_TEMPLATE_DIR", Path.home() / ".lcc" / "template-policies"))
    )
    # Treatment for components with UNKNOWN licenses when no policy is applied
    # Options: "violation" (default), "warning", "pass"
    unknown_license_treatment: str = os.getenv("LCC_UNKNOWN_LICENSE_TREATMENT", "violation")


def load_config(path: Optional[Path] = None) -> LCCConfig:
    """
    Load configuration from disk while honoring environment overrides.
    """

    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return LCCConfig()

    if yaml is None:
        return LCCConfig()

    with config_path.open("r", encoding="utf-8") as handle:
        data: Dict[str, Any] = yaml.safe_load(handle) or {}

    cfg = LCCConfig()
    for key, value in data.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    if isinstance(cfg.decision_log_path, str):
        cfg.decision_log_path = Path(cfg.decision_log_path)
    if isinstance(cfg.template_dir, str):
        cfg.template_dir = Path(cfg.template_dir)
    if isinstance(cfg.cache_dir, str):
        cfg.cache_dir = Path(cfg.cache_dir)
    if isinstance(cfg.database_path, str):
        cfg.database_path = Path(cfg.database_path)
    if isinstance(cfg.cache_ttls, dict):
        cfg.cache_ttls = {str(key): int(value) for key, value in cfg.cache_ttls.items()}
    return cfg
