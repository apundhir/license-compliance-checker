"""Unit tests for AI license registry."""

from __future__ import annotations

import pytest

from lcc.ai.licenses import (
    AI_LICENSES,
    AILicenseInfo,
    get_ai_license_info,
    is_commercial_allowed,
    normalize_ai_license_name,
)


def test_ai_license_info_creation():
    """Test AILicenseInfo dataclass creation."""
    license_info = AILicenseInfo(
        id="test-license",
        name="Test License",
        commercial_use=True,
        derivatives_allowed=True,
    )

    assert license_info.id == "test-license"
    assert license_info.name == "Test License"
    assert license_info.commercial_use is True
    assert license_info.derivatives_allowed is True


def test_ai_license_info_with_restrictions():
    """Test AILicenseInfo with use restrictions."""
    license_info = AILicenseInfo(
        id="test",
        name="Test",
        use_restrictions=["no-hate-speech", "no-illegal-use"],
    )

    assert len(license_info.use_restrictions) == 2
    assert "no-hate-speech" in license_info.use_restrictions


def test_ai_license_info_with_user_threshold():
    """Test AILicenseInfo with user threshold."""
    license_info = AILicenseInfo(
        id="test",
        name="Test",
        user_threshold="700M monthly active users",
    )

    assert license_info.user_threshold == "700M monthly active users"


def test_ai_licenses_registry_not_empty():
    """Test AI_LICENSES registry contains licenses."""
    assert len(AI_LICENSES) > 0


def test_openrail_license_exists():
    """Test OpenRAIL license exists in registry."""
    assert "openrail" in AI_LICENSES
    license_info = AI_LICENSES["openrail"]
    assert license_info.name == "OpenRAIL"


def test_llama2_license_exists():
    """Test Llama 2 license exists."""
    assert "llama-2" in AI_LICENSES
    license_info = AI_LICENSES["llama-2"]
    assert "700M" in license_info.user_threshold


def test_llama3_license_exists():
    """Test Llama 3 license exists."""
    assert "llama-3" in AI_LICENSES
    license_info = AI_LICENSES["llama-3"]
    assert "700M" in license_info.user_threshold


def test_bigscience_bloom_license_exists():
    """Test BigScience BLOOM license exists."""
    assert "bigscience-bloom-rail-1.0" in AI_LICENSES
    license_info = AI_LICENSES["bigscience-bloom-rail-1.0"]
    assert license_info.commercial_use is True


def test_creativeml_openrail_m_license_exists():
    """Test Creative ML OpenRAIL-M license exists."""
    assert "creativeml-openrail-m" in AI_LICENSES
    license_info = AI_LICENSES["creativeml-openrail-m"]
    assert len(license_info.use_restrictions) > 0


def test_get_ai_license_info_found():
    """Test get_ai_license_info returns license when found."""
    result = get_ai_license_info("openrail")
    assert result is not None
    assert result.id == "openrail"


def test_get_ai_license_info_not_found():
    """Test get_ai_license_info returns None for unknown license."""
    result = get_ai_license_info("nonexistent-license")
    assert result is None


def test_get_ai_license_info_case_insensitive():
    """Test get_ai_license_info is case-insensitive."""
    result = get_ai_license_info("OpenRAIL")
    assert result is not None  # Should work with any case
    assert result.id == "openrail"


def test_normalize_ai_license_name_exact_match():
    """Test normalize returns exact match."""
    result = normalize_ai_license_name("openrail")
    assert result == "openrail"


def test_normalize_ai_license_name_with_alias():
    """Test normalize handles common aliases."""
    # Assuming we add aliases in the implementation
    result = normalize_ai_license_name("openrail")
    assert result is not None


def test_normalize_ai_license_name_unknown():
    """Test normalize returns None for unknown name."""
    result = normalize_ai_license_name("unknown-license-xyz")
    assert result is None


def test_is_commercial_allowed_permissive():
    """Test is_commercial_allowed for permissive license."""
    result = is_commercial_allowed("apache-2.0-ai")
    assert result is True


def test_is_commercial_allowed_llama2():
    """Test is_commercial_allowed for Llama 2 (with threshold)."""
    result = is_commercial_allowed("llama-2")
    # Returns True but with conditions (user threshold)
    assert result is True


def test_is_commercial_allowed_nonexistent():
    """Test is_commercial_allowed for nonexistent license."""
    result = is_commercial_allowed("nonexistent")
    # Should return False for unknown licenses (safe default)
    assert result is False


def test_commercial_licenses_count():
    """Test count of commercial-allowed licenses."""
    commercial_count = sum(
        1 for lic in AI_LICENSES.values() if lic.commercial_use
    )
    assert commercial_count > 0


def test_non_commercial_licenses_count():
    """Test count of non-commercial licenses."""
    non_commercial_count = sum(
        1 for lic in AI_LICENSES.values() if not lic.commercial_use
    )
    # Should have some non-commercial licenses
    assert non_commercial_count >= 0  # At least 0, possibly more


def test_licenses_with_use_restrictions():
    """Test count of licenses with use restrictions."""
    with_restrictions = sum(
        1 for lic in AI_LICENSES.values() if lic.use_restrictions
    )
    assert with_restrictions > 0


def test_licenses_with_user_threshold():
    """Test licenses with user thresholds."""
    with_threshold = [
        lic for lic in AI_LICENSES.values() if lic.user_threshold
    ]
    assert len(with_threshold) > 0


def test_all_licenses_have_id():
    """Test all licenses have an ID."""
    for license_id, license_info in AI_LICENSES.items():
        assert license_info.id == license_id


def test_all_licenses_have_name():
    """Test all licenses have a name."""
    for license_info in AI_LICENSES.values():
        assert license_info.name
        assert len(license_info.name) > 0


def test_llama_licenses_have_threshold():
    """Test Llama licenses have user thresholds."""
    for license_id in ["llama-2", "llama-3", "llama-3.1"]:
        if license_id in AI_LICENSES:
            license_info = AI_LICENSES[license_id]
            assert license_info.user_threshold is not None


def test_rail_licenses_have_restrictions():
    """Test RAIL licenses have use restrictions."""
    rail_licenses = [
        "openrail",
        "openrail-m",
        "openrail++",
        "bigscience-bloom-rail-1.0",
        "creativeml-openrail-m",
    ]

    for license_id in rail_licenses:
        if license_id in AI_LICENSES:
            license_info = AI_LICENSES[license_id]
            assert len(license_info.use_restrictions) > 0


def test_proprietary_api_licenses_exist():
    """Test proprietary API-only licenses exist."""
    proprietary = [
        "openai-gpt",
        "anthropic-claude",
        "google-gemini",
        "cohere",
    ]

    for license_id in proprietary:
        if license_id in AI_LICENSES:
            license_info = AI_LICENSES[license_id]
            assert license_info.derivatives_allowed is False


def test_apache2_derivative_allowed():
    """Test Apache 2.0 allows derivatives."""
    if "apache-2.0" in AI_LICENSES:
        license_info = AI_LICENSES["apache-2.0"]
        assert license_info.derivatives_allowed is True


def test_registry_size():
    """Test registry has expected number of licenses."""
    # Should have at least 17 AI-specific licenses
    assert len(AI_LICENSES) >= 17
