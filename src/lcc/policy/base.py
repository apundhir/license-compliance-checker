"""Policy management helpers."""

from __future__ import annotations

import fnmatch
import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from importlib import resources as importlib_resources

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None  # type: ignore

from lcc.config import LCCConfig


class PolicyError(RuntimeError):
    """Raised for invalid policy operations."""


@dataclass
class Policy:
    name: str
    data: Dict[str, object]
    path: Path


@dataclass
class PolicyAlternative:
    license: str
    disposition: str  # allow | deny | review | unknown
    reason: Optional[str] = None


@dataclass
class PolicyDecision:
    status: str  # pass | warning | violation
    context: str
    chosen_license: Optional[str]
    reasons: List[str] = field(default_factory=list)
    alternatives: List[PolicyAlternative] = field(default_factory=list)
    disclaimer: Optional[str] = None
    explanation: Optional[str] = None
    override: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "context": self.context,
            "chosen_license": self.chosen_license,
            "reasons": list(self.reasons),
            "alternatives": [asdict(item) for item in self.alternatives],
            "disclaimer": self.disclaimer,
            "explanation": self.explanation,
            "override": self.override,
        }


class PolicyManager:
    """Loads, validates, and stores policy documents."""

    def __init__(self, config: LCCConfig) -> None:
        self.config = config
        base_dir = Path(os.getenv("LCC_POLICY_DIR", Path.home() / ".lcc" / "policies"))
        base_dir.mkdir(parents=True, exist_ok=True)
        self.policy_dir = base_dir
        self._seed_templates()
        template_output = getattr(config, "template_dir", None)
        if template_output:
            template_output.mkdir(parents=True, exist_ok=True)

    def _seed_templates(self) -> None:
        """Populate the policy directory with bundled templates."""

        def _copy_payload(name: str, payload: str) -> None:
            destination = self.policy_dir / name
            if not destination.exists():
                destination.write_text(payload, encoding="utf-8")

        # Bundled resources inside the package
        try:
            package_root = importlib_resources.files("lcc.data.policies")
            for resource in package_root.iterdir():
                if resource.is_file() and resource.suffix in {".yml", ".yaml"}:
                    _copy_payload(resource.name, resource.read_text(encoding="utf-8"))
        except (ModuleNotFoundError, FileNotFoundError):  # pragma: no cover - defensive
            pass

        # Repository-mounted fallbacks to support editable installs
        fallback_dirs = [
            Path(__file__).resolve().parent.parent.parent / "policies",
            Path(__file__).resolve().parent.parent.parent.parent / "policies",
            Path(__file__).resolve().parent.parent.parent.parent / "policy" / "templates",
        ]
        for directory in fallback_dirs:
            if not directory.exists():
                continue
            for pattern in ("*.yml", "*.yaml"):
                for template in directory.glob(pattern):
                    destination = self.policy_dir / template.name
                    if not destination.exists():
                        shutil.copy(template, destination)

    def list_policies(self) -> List[str]:
        return sorted({policy_path.stem for policy_path in self._iter_policy_files()})

    def load_policy(self, name: str) -> Policy:
        path = self._policy_path(name)
        if not path.exists():
            raise PolicyError(f"Policy '{name}' not found")
        data = self._read_policy(path)
        errors = self.validate_policy(data)
        if errors:
            joined = "\n".join(errors)
            raise PolicyError(f"Policy '{name}' is invalid:\n{joined}")
        return Policy(name=name, data=data, path=path)

    def save_policy(self, name: str, data: Dict[str, object]) -> Path:
        errors = self.validate_policy(data)
        if errors:
            raise PolicyError(f"Policy is invalid: {', '.join(errors)}")
        path = self._policy_path(name)
        self._write_policy(path, data)
        return path

    def delete_policy(self, name: str) -> None:
        path = self._policy_path(name)
        if path.exists():
            path.unlink()

    def import_policy(self, source: Path) -> Path:
        if not source.exists():
            raise PolicyError("Source policy not found")
        data = self._read_policy(source)
        errors = self.validate_policy(data)
        if errors:
            raise PolicyError(f"Imported policy invalid: {', '.join(errors)}")
        name = data.get("name") or source.stem
        dest = self._policy_path(str(name))
        shutil.copy(source, dest)
        return dest

    def read_policy_file(self, path: Path) -> Dict[str, object]:
        if not path.exists():
            raise PolicyError("Policy file not found")
        return self._read_policy(path)

    def export_policy(self, name: str, destination: Path) -> Path:
        policy = self.load_policy(name)
        if destination.is_dir():
            destination = destination / policy.path.name
        shutil.copy(policy.path, destination)
        return destination

    def validate_policy(self, data: Dict[str, object]) -> List[str]:
        errors: List[str] = []
        if not isinstance(data, dict):
            return ["Policy must be a mapping."]
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append("Policy must define a non-empty 'name'.")
        if not isinstance(data.get("disclaimer"), str):
            errors.append("Policy must include a 'disclaimer' string.")
        contexts = data.get("contexts")
        if not isinstance(contexts, dict) or not contexts:
            errors.append("Policy must define at least one context under 'contexts'.")
        else:
            for context_name, context_data in contexts.items():
                if not isinstance(context_data, dict):
                    errors.append(f"Context '{context_name}' must be a mapping.")
                    continue
                for key in ("allow", "deny", "review"):
                    value = context_data.get(key, [])
                    if value and not isinstance(value, list):
                        errors.append(f"Context '{context_name}' key '{key}' must be a list when present.")
                for reason_key in ("deny_reasons", "review_reasons"):
                    reasons = context_data.get(reason_key, {})
                    if reasons and not isinstance(reasons, dict):
                        errors.append(f"Context '{context_name}' key '{reason_key}' must be a mapping.")
                overrides = context_data.get("overrides", {})
                if overrides and not isinstance(overrides, dict):
                    errors.append(f"Context '{context_name}' overrides must be a mapping.")
                preference = context_data.get("dual_license_preference", "most_permissive")
                if preference not in {"most_permissive", "avoid_copyleft", "prefer_order"}:
                    errors.append(
                        f"Context '{context_name}' dual_license_preference must be one of "
                        "'most_permissive', 'avoid_copyleft', 'prefer_order'."
                    )
                if preference == "prefer_order":
                    order = context_data.get("preferred_order")
                    if not isinstance(order, list) or not order:
                        errors.append(
                            f"Context '{context_name}' must define non-empty 'preferred_order' when using "
                            "'prefer_order' preference."
                        )
        return errors

    def active_policy(self) -> Optional[str]:
        return getattr(self.config, "active_policy", None)

    def set_active_policy(self, name: str) -> None:
        policy = self.load_policy(name)  # ensure exists
        config_path = Path.home() / ".lcc" / "config.yml"
        fallback_path = self.policy_dir / "config.yml"
        target_path = config_path
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            target_path = fallback_path
        config = {}
        if target_path.exists() and yaml:
            config = yaml.safe_load(target_path.read_text(encoding="utf-8")) or {}
        elif target_path.exists():
            config = json.loads(target_path.read_text(encoding="utf-8"))
        config["active_policy"] = policy.name
        if yaml:
            target_path.write_text(yaml.safe_dump(config), encoding="utf-8")
        else:  # pragma: no cover - rare branch
            target_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        self.config.active_policy = policy.name

    # ----------------------------
    # Internal helpers
    # ----------------------------

    def _policy_path(self, name: str) -> Path:
        for suffix in (".yml", ".yaml", ".json"):
            candidate = self.policy_dir / f"{name}{suffix}"
            if candidate.exists():
                return candidate
        return self.policy_dir / f"{name}.yaml"

    def _iter_policy_files(self) -> Iterable[Path]:
        for suffix in ("*.yml", "*.yaml", "*.json"):
            yield from self.policy_dir.glob(suffix)

    def _read_policy(self, path: Path) -> Dict[str, object]:
        content = path.read_text(encoding="utf-8")
        if path.suffix in {".yml", ".yaml"} and yaml:
            return yaml.safe_load(content) or {}
        return json.loads(content)

    def _write_policy(self, path: Path, data: Dict[str, object]) -> None:
        if path.suffix in {".yml", ".yaml"} and yaml:
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        else:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def evaluate_policy(
    policy: Dict[str, object],
    licenses: Iterable[str],
    *,
    context: Optional[str] = None,
    component_name: Optional[str] = None,
) -> PolicyDecision:
    """
    Evaluate resolved licenses against a policy definition.

    Parameters
    ----------
    policy:
        Loaded policy document.
    licenses:
        Iterable of SPDX expressions or license identifiers discovered for a component.
    context:
        Usage context (e.g. "internal", "saas", "distribution"). When omitted the first
        context defined by the policy is used.
    component_name:
        Optional component identifier used when checking overrides.
    """

    contexts = policy.get("contexts") or {}
    if not contexts:
        return PolicyDecision(status="pass", context=context or "default", chosen_license=None)

    if context and context in contexts:
        context_name = context
    else:
        context_name = policy.get("default_context")
        if not context_name or context_name not in contexts:
            context_name = next(iter(contexts.keys()))
    context_data: Dict[str, object] = contexts.get(context_name, {})

    overrides = context_data.get("overrides", {}) if isinstance(context_data, dict) else {}
    if isinstance(overrides, dict) and component_name and component_name in overrides:
        override_entry = overrides[component_name]
        return PolicyDecision(
            status=str(override_entry.get("decision", "warning")),
            context=context_name,
            chosen_license=override_entry.get("license"),
            reasons=[override_entry.get("reason", "Component-level override applied.")],
            disclaimer=policy.get("disclaimer"),
            explanation=override_entry.get("explanation"),
            override="component",
        )

    expressions = [license_expression for license_expression in licenses if license_expression]
    expanded = _expand_licenses(expressions)
    if not expanded:
        expanded = ["UNKNOWN"]
    allow_patterns = _ensure_list(context_data.get("allow"))
    deny_patterns = _ensure_list(context_data.get("deny"))
    review_patterns = _ensure_list(context_data.get("review"))
    deny_reasons = _ensure_mapping(context_data.get("deny_reasons"))
    review_reasons = _ensure_mapping(context_data.get("review_reasons"))
    preference = context_data.get("dual_license_preference", "most_permissive")
    preferred_order = _ensure_list(context_data.get("preferred_order"))

    # Determine disposition for every candidate
    alternatives: List[PolicyAlternative] = []
    status = "pass"
    reasons: List[str] = []
    allowed_candidates: List[str] = []

    for candidate in expanded:
        disposition = _classify_candidate(candidate, allow_patterns, deny_patterns, review_patterns)
        reason = None
        if disposition == "deny":
            status = "violation"
            reason = deny_reasons.get(candidate) or _match_reason(candidate, deny_reasons)
            if reason:
                reasons.append(reason)
            else:
                reasons.append(f"{candidate} denied by policy.")
        elif disposition == "review":
            if status != "violation":
                status = "warning"
            reason = review_reasons.get(candidate) or _match_reason(candidate, review_reasons)
            if reason:
                reasons.append(reason)
            else:
                reasons.append(f"{candidate} requires manual review.")
        alternatives.append(PolicyAlternative(license=candidate, disposition=disposition, reason=reason))
        if disposition != "deny":
            allowed_candidates.append(candidate)

    if status == "pass":
        reasons.append("All discovered licenses are permitted.")

    chosen_license, selection_reason = _choose_license(allowed_candidates, preference, preferred_order)
    if selection_reason:
        reasons.append(selection_reason)

    # If all candidates denied fallback to first for reporting context
    if not chosen_license and expanded:
        chosen_license = expanded[0]

    return PolicyDecision(
        status=status,
        context=context_name,
        chosen_license=chosen_license,
        reasons=reasons,
        alternatives=alternatives,
        disclaimer=policy.get("disclaimer"),
        explanation=_resolve_context_explanation(context_data),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_list(value: object) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _ensure_mapping(value: object) -> Dict[str, str]:
    if isinstance(value, dict):
        return {str(key): str(val) for key, val in value.items()}
    return {}


def _expand_licenses(expressions: Sequence[str]) -> List[str]:
    expanded: List[str] = []
    for expression in expressions:
        expanded.extend(_split_expression(expression))
    result: List[str] = []
    seen = set()
    for license_id in expanded:
        if license_id not in seen:
            seen.add(license_id)
            result.append(license_id)
    return result


def _split_expression(expression: str) -> List[str]:
    expression = expression.strip().strip("()")
    if not expression:
        return []

    parts: List[str] = []
    buffer: List[str] = []
    depth = 0
    index = 0
    while index < len(expression):
        token = expression[index]
        if token == "(":
            depth += 1
            buffer.append(token)
            index += 1
            continue
        if token == ")":
            depth = max(0, depth - 1)
            buffer.append(token)
            index += 1
            continue
        if depth == 0 and expression.startswith(" OR ", index):
            part = "".join(buffer).strip().strip("()")
            if part:
                parts.append(part)
            buffer = []
            index += 4
            continue
        buffer.append(token)
        index += 1

    trailing = "".join(buffer).strip().strip("()")
    if trailing:
        parts.append(trailing)

    if not parts:
        return [expression]
    return [part for part in parts if part]


def _classify_candidate(
    license_id: str,
    allow_patterns: Sequence[str],
    deny_patterns: Sequence[str],
    review_patterns: Sequence[str],
) -> str:
    if _matches_any(license_id, deny_patterns):
        return "deny"
    if _matches_any(license_id, allow_patterns):
        return "allow"
    if _matches_any(license_id, review_patterns):
        return "review"
    if allow_patterns:
        # When allow-list is defined anything outside falls back to review.
        return "review"
    return "unknown"


def _matches_any(value: str, patterns: Sequence[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatchcase(value, pattern):
            return True
    return False


def _match_reason(license_id: str, reasons: Dict[str, str]) -> Optional[str]:
    for pattern, message in reasons.items():
        if fnmatch.fnmatchcase(license_id, pattern):
            return message
    return None


def _choose_license(
    candidates: Sequence[str],
    preference: str,
    preferred_order: Sequence[str],
) -> Tuple[Optional[str], Optional[str]]:
    if not candidates:
        return None, None
    if len(candidates) == 1:
        return candidates[0], "Single license available; selected by default."

    if preference == "prefer_order" and preferred_order:
        for pattern in preferred_order:
            for candidate in candidates:
                if fnmatch.fnmatchcase(candidate, pattern):
                    return candidate, f"Preferred order matched {pattern}."

    if preference == "avoid_copyleft":
        non_copyleft = [candidate for candidate in candidates if _license_category(candidate) != "strong_copyleft"]
        if non_copyleft:
            return non_copyleft[0], "Selected non-copyleft option based on preference."

    ranked = sorted(candidates, key=lambda item: _license_rank(_license_category(item)))
    chosen = ranked[0]
    return chosen, "Selected most permissive option available."


def _license_category(license_id: str) -> str:
    normalized = license_id.upper()
    copyleft_strong = ("AGPL", "GPL", "CC-BY-SA", "SSPL", "CDDL", "EPL")
    copyleft_weak = ("LGPL", "MPL", "CPL")
    restrictive = ("NONCOMMERCIAL", "NC-", "-NC", "RAIL", "PROPRIETARY")
    if any(token in normalized for token in copyleft_strong):
        return "strong_copyleft"
    if any(token in normalized for token in copyleft_weak):
        return "weak_copyleft"
    if any(token in normalized for token in restrictive):
        return "restricted"
    permissive = ("MIT", "APACHE", "BSD", "ISC", "CC0")
    if any(token in normalized for token in permissive):
        return "permissive"
    return "unknown"


def _license_rank(category: str) -> int:
    return {
        "permissive": 0,
        "weak_copyleft": 1,
        "unknown": 2,
        "restricted": 3,
        "strong_copyleft": 4,
    }.get(category, 2)


def _resolve_context_explanation(context_data: Dict[str, object]) -> Optional[str]:
    explanation = context_data.get("explanation")
    if isinstance(explanation, str):
        return explanation
    if isinstance(explanation, list):
        return " ".join(str(item) for item in explanation)
    return None
