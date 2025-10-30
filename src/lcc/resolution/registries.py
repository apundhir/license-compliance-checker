"""
Package registry resolvers for PyPI, npm, crates.io and others.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional
from urllib.parse import quote

import requests

from lcc.cache import Cache
from lcc.config import LCCConfig
from lcc.models import Component, ComponentType, LicenseEvidence
from lcc.resolution.base import Resolver


class RegistryResolver(Resolver):
    """
    Generic resolver delegating to ecosystem specific handlers.
    """

    PYPI_URL = "https://pypi.org/pypi/{name}/{version}/json"
    PYPI_LATEST_URL = "https://pypi.org/pypi/{name}/json"
    NPM_URL = "https://registry.npmjs.org/{name}"
    NPM_VERSION_URL = "https://registry.npmjs.org/{name}/{version}"
    GOPROXY_INFO_URL = "https://proxy.golang.org/{module}/@v/{version}.info"

    def __init__(self, cache: Cache, config: LCCConfig) -> None:
        super().__init__(name="registry")
        self.cache = cache
        self.config = config

    def resolve(self, component: Component) -> Iterable[LicenseEvidence]:
        if getattr(self.config, "offline", False):
            return []
        if component.type == ComponentType.PYTHON:
            return self._resolve_pypi(component)
        if component.type == ComponentType.JAVASCRIPT:
            return self._resolve_npm(component)
        if component.type == ComponentType.GO:
            return self._resolve_go(component)
        return []

    # ----------------------------
    # PyPI
    # ----------------------------

    def _resolve_pypi(self, component: Component) -> Iterable[LicenseEvidence]:
        name = component.name.replace("_", "-")
        version = component.version or "*"
        assumed_version: Optional[str] = None
        if version == "*" or not version:
            url = self.PYPI_LATEST_URL.format(name=name)
        else:
            url = self.PYPI_URL.format(name=name, version=version)
        cache_key = f"pypi::{name}::{version}"
        data = self._fetch_json(cache_key, url, token=self.config.api_tokens.get("pypi"))
        if not data:
            return []
        info = data.get("info", {})
        if (version in ("*", None)) and isinstance(info, dict):
            assumed_version = info.get("version")
        license_value = info.get("license")
        license_expression = None
        if isinstance(license_value, str) and license_value.strip() and license_value.strip() != "UNKNOWN":
            license_expression = license_value.strip()
        if not license_expression:
            classifiers = info.get("classifiers", [])
            license_expression = self._extract_classifier_license(classifiers)
        if not license_expression:
            # Even if no license found, still return evidence with assumed_version
            # This decouples version resolution from license resolution
            license_expression = "UNKNOWN"
        confidence = 0.6
        home_page = info.get("home_page") if isinstance(info, dict) else None
        raw_data: Dict[str, object] = {}
        if assumed_version:
            raw_data["assumed_version"] = assumed_version
        return [
            LicenseEvidence(
                source="pypi",
                license_expression=license_expression,
                confidence=confidence,
                raw_data=raw_data,
                url=home_page,
            )
        ]

    def _extract_classifier_license(self, classifiers: Iterable[str]) -> Optional[str]:
        for classifier in classifiers or []:
            if classifier.startswith("License ::"):
                parts = classifier.split("::")
                if parts:
                    candidate = parts[-1].strip()
                    if candidate:
                        return candidate
        return None

    # ----------------------------
    # npm
    # ----------------------------

    def _resolve_npm(self, component: Component) -> Iterable[LicenseEvidence]:
        encoded_name = quote(component.name, safe="@")
        version = component.version or "*"
        assumed_version: Optional[str] = None
        if version == "*":
            url = self.NPM_URL.format(name=encoded_name)
        else:
            url = self.NPM_VERSION_URL.format(name=encoded_name, version=version)
        cache_key = f"npm::{component.name}::{version}"
        token = self.config.api_tokens.get("npm")
        headers = {"Accept": "application/vnd.npm.install-v1+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = self._fetch_json(cache_key, url, headers=headers)
        if not data:
            return []

        license_expression = None
        if "license" in data and isinstance(data["license"], str):
            license_expression = data["license"].strip()
        elif isinstance(data.get("licenses"), list):
            licenses = [entry.get("type") for entry in data["licenses"] if isinstance(entry, dict)]
            licenses = [entry for entry in licenses if isinstance(entry, str)]
            if licenses:
                license_expression = licenses[0]
        elif version == "*":
            versions = data.get("versions", {})
            dist_tags = data.get("dist-tags", {})
            latest_tag = dist_tags.get("latest") if isinstance(dist_tags, dict) else None
            version_data = versions.get(latest_tag) if isinstance(versions, dict) else None
            if isinstance(latest_tag, str):
                assumed_version = latest_tag
            if isinstance(version_data, dict) and isinstance(version_data.get("license"), str):
                license_expression = version_data["license"]

        if not license_expression:
            # Even if no license found, still return evidence with assumed_version
            # This decouples version resolution from license resolution
            license_expression = "UNKNOWN"

        homepage = data.get("homepage")
        if version != "*" and not homepage and isinstance(data.get("dist"), dict):
            homepage = data["dist"].get("tarball")
        raw_data: Dict[str, object] = {}
        if assumed_version:
            raw_data["assumed_version"] = assumed_version
        return [
            LicenseEvidence(
                source="npm",
                license_expression=license_expression,
                confidence=0.6,
                raw_data=raw_data,
                url=homepage,
            )
        ]

    # ----------------------------
    # Go modules
    # ----------------------------

    def _resolve_go(self, component: Component) -> Iterable[LicenseEvidence]:
        if component.version in (None, "", "*"):
            return []
        module = quote(component.name, safe="@:/")
        url = self.GOPROXY_INFO_URL.format(module=module, version=component.version)
        cache_key = f"goproxy::{component.name}::{component.version}"
        data = self._fetch_json(cache_key, url)
        if data is None:
            return []
        # Go proxy does not expose license data; return acknowledgement evidence with low confidence
        return [
            LicenseEvidence(
                source="goproxy",
                license_expression="UNKNOWN",
                confidence=0.1,
                raw_data=data,
                url=None,
            )
        ] if data else []

    # ----------------------------
    # Helpers
    # ----------------------------

    def _fetch_json(
        self,
        cache_key: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        token: Optional[str] = None,
    ) -> Optional[dict]:
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        timeout = float(self.config.timeouts.get("registry", self.config.timeouts.get("default", 10.0)))
        request_headers = dict(headers or {})
        if token and "Authorization" not in request_headers:
            request_headers["Authorization"] = f"Bearer {token}"
        try:
            response = requests.get(url, headers=request_headers or None, timeout=timeout)
        except requests.RequestException:
            return None
        if response.status_code == 404:
            data: dict = {}
        elif response.status_code >= 400:
            data = {}
        else:
            try:
                data = response.json()
            except ValueError:
                data = {}
        self.cache.set(cache_key, data)
        return data
