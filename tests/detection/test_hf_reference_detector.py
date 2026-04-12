"""Unit tests for HuggingFaceReferenceDetector and hf_hub_resolver."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lcc.detection.huggingface import HuggingFaceReferenceDetector
from lcc.models import ComponentType
from lcc.resolution.hf_hub_resolver import (
    HF_CACHE,
    HFModelInfo,
    extract_model_ids_from_source,
    fetch_model_info,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hf_api_response(
    model_id: str,
    license_tag: str = "apache-2.0",
    pipeline_tag: str = "text-generation",
) -> bytes:
    """Build a minimal HF Hub API JSON response."""
    data = {
        "id": model_id,
        "tags": [f"license:{license_tag}", "transformers"],
        "pipeline_tag": pipeline_tag,
        "cardData": {
            "license": license_tag,
            "datasets": ["c4", "pile"],
        },
    }
    return json.dumps(data).encode()


# ---------------------------------------------------------------------------
# extract_model_ids_from_source
# ---------------------------------------------------------------------------


class TestExtractModelIds:
    def test_from_pretrained_double_quotes(self):
        src = 'model = AutoModel.from_pretrained("meta-llama/Llama-3.1-70B-Instruct")'
        ids = extract_model_ids_from_source(src)
        assert "meta-llama/Llama-3.1-70B-Instruct" in ids

    def test_from_pretrained_single_quotes(self):
        src = "tokenizer = AutoTokenizer.from_pretrained('mistralai/Mistral-7B-v0.1')"
        ids = extract_model_ids_from_source(src)
        assert "mistralai/Mistral-7B-v0.1" in ids

    def test_model_name_or_path_yaml_style(self):
        src = "model_name_or_path: 'google/flan-t5-base'"
        ids = extract_model_ids_from_source(src)
        assert "google/flan-t5-base" in ids

    def test_model_equals_assignment(self):
        src = 'model = "openai-community/gpt2"'
        ids = extract_model_ids_from_source(src)
        assert "openai-community/gpt2" in ids

    def test_multiple_ids_deduplicated(self):
        src = (
            'AutoModel.from_pretrained("meta-llama/Llama-3.1-70B-Instruct")\n'
            'AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-70B-Instruct")\n'
            'AutoModel.from_pretrained("mistralai/Mistral-7B-v0.1")\n'
        )
        ids = extract_model_ids_from_source(src)
        assert len(ids) == 2
        assert "meta-llama/Llama-3.1-70B-Instruct" in ids
        assert "mistralai/Mistral-7B-v0.1" in ids

    def test_local_paths_are_excluded(self):
        src = 'AutoModel.from_pretrained("./local_model")'
        ids = extract_model_ids_from_source(src)
        assert ids == []

    def test_empty_source_returns_empty(self):
        assert extract_model_ids_from_source("") == []

    def test_no_model_ids_returns_empty(self):
        src = "import torch\nx = 1 + 1"
        assert extract_model_ids_from_source(src) == []


# ---------------------------------------------------------------------------
# fetch_model_info
# ---------------------------------------------------------------------------


class TestFetchModelInfo:
    def setup_method(self):
        # Clear the in-memory cache before each test to avoid cross-test pollution
        HF_CACHE.clear()

    def test_returns_hf_model_info_on_success(self):
        model_id = "meta-llama/Llama-3.1-70B-Instruct"
        raw = _make_hf_api_response(model_id)

        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = raw

        with patch("lcc.resolution.hf_hub_resolver.urlopen", return_value=mock_resp):
            info = fetch_model_info(model_id)

        assert isinstance(info, HFModelInfo)
        assert info.model_id == model_id
        assert info.license == "apache-2.0"
        assert info.pipeline_tag == "text-generation"
        assert "c4" in info.datasets

    def test_caches_result(self):
        model_id = "google/flan-t5-base"
        raw = _make_hf_api_response(model_id)

        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = raw

        with patch("lcc.resolution.hf_hub_resolver.urlopen", return_value=mock_resp) as mock_open:
            fetch_model_info(model_id)
            fetch_model_info(model_id)  # second call should use cache
            assert mock_open.call_count == 1

    def test_returns_none_on_network_error(self):
        HF_CACHE.clear()
        with patch(
            "lcc.resolution.hf_hub_resolver.urlopen",
            side_effect=OSError("connection refused"),
        ):
            info = fetch_model_info("org/nonexistent-model-xyz")

        assert info is None

    def test_returns_none_on_json_decode_error(self):
        HF_CACHE.clear()
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b"not-json{"

        with patch("lcc.resolution.hf_hub_resolver.urlopen", return_value=mock_resp):
            info = fetch_model_info("org/bad-response")

        assert info is None

    def test_uses_hf_token_in_header(self):
        HF_CACHE.clear()
        model_id = "private/model"
        raw = _make_hf_api_response(model_id)

        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = raw

        captured_requests = []

        def fake_urlopen(req, timeout=None):
            captured_requests.append(req)
            return mock_resp

        with patch("lcc.resolution.hf_hub_resolver.urlopen", side_effect=fake_urlopen):
            fetch_model_info(model_id, hf_token="hf_TESTTOKEN")

        assert len(captured_requests) == 1
        assert captured_requests[0].get_header("Authorization") == "Bearer hf_TESTTOKEN"


# ---------------------------------------------------------------------------
# HuggingFaceReferenceDetector
# ---------------------------------------------------------------------------


class TestHuggingFaceReferenceDetector:
    def setup_method(self):
        HF_CACHE.clear()

    def test_detector_name(self):
        detector = HuggingFaceReferenceDetector()
        assert detector.name == "huggingface-reference"

    def test_supports_directory(self, tmp_path: Path):
        detector = HuggingFaceReferenceDetector()
        assert detector.supports(tmp_path) is True

    def test_supports_returns_false_for_file(self, tmp_path: Path):
        detector = HuggingFaceReferenceDetector()
        f = tmp_path / "file.py"
        f.write_text("pass")
        assert detector.supports(f) is False

    def test_discovers_model_from_python_file(self, tmp_path: Path):
        """Detector finds model IDs in .py files and returns Components."""
        src = 'model = AutoModel.from_pretrained("meta-llama/Llama-3.1-70B-Instruct")\n'
        (tmp_path / "train.py").write_text(src)

        raw = _make_hf_api_response("meta-llama/Llama-3.1-70B-Instruct")
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = raw

        detector = HuggingFaceReferenceDetector()
        with patch("lcc.resolution.hf_hub_resolver.urlopen", return_value=mock_resp):
            components = detector.discover(tmp_path)

        assert len(components) == 1
        comp = components[0]
        assert comp.type == ComponentType.AI_MODEL
        assert comp.name == "Llama-3.1-70B-Instruct"
        assert comp.namespace == "meta-llama"
        assert comp.metadata.get("license_from_card") == "apache-2.0"

    def test_discovers_models_from_yaml_file(self, tmp_path: Path):
        """Detector finds model IDs in .yaml config files."""
        yaml_content = "model_name_or_path: 'google/flan-t5-base'\n"
        (tmp_path / "config.yaml").write_text(yaml_content)

        raw = _make_hf_api_response("google/flan-t5-base")
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = raw

        detector = HuggingFaceReferenceDetector()
        with patch("lcc.resolution.hf_hub_resolver.urlopen", return_value=mock_resp):
            components = detector.discover(tmp_path)

        names = [c.name for c in components]
        assert "flan-t5-base" in names

    def test_deduplicates_same_model_across_files(self, tmp_path: Path):
        """Same model ID referenced in two files produces only one Component."""
        (tmp_path / "a.py").write_text('AutoModel.from_pretrained("openai-community/gpt2")\n')
        (tmp_path / "b.py").write_text('AutoModel.from_pretrained("openai-community/gpt2")\n')

        raw = _make_hf_api_response("openai-community/gpt2")
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = raw

        detector = HuggingFaceReferenceDetector()
        with patch("lcc.resolution.hf_hub_resolver.urlopen", return_value=mock_resp):
            components = detector.discover(tmp_path)

        assert len(components) == 1

    def test_graceful_degradation_when_api_unavailable(self, tmp_path: Path):
        """Detector returns Components even when HF Hub API is unreachable."""
        src = 'AutoModel.from_pretrained("mistralai/Mistral-7B-v0.1")\n'
        (tmp_path / "infer.py").write_text(src)

        detector = HuggingFaceReferenceDetector()
        with patch(
            "lcc.resolution.hf_hub_resolver.urlopen",
            side_effect=OSError("network unavailable"),
        ):
            components = detector.discover(tmp_path)

        # Should still return a component, just without Hub metadata
        assert len(components) == 1
        comp = components[0]
        assert comp.name == "Mistral-7B-v0.1"
        assert comp.metadata.get("hub_api_available") is False
        assert "license_from_card" not in comp.metadata

    def test_returns_empty_for_no_model_references(self, tmp_path: Path):
        """Detector returns empty list when no model IDs are found."""
        (tmp_path / "utils.py").write_text("import os\nprint('hello')\n")

        detector = HuggingFaceReferenceDetector()
        components = detector.discover(tmp_path)
        assert components == []

    def test_skips_venv_directories(self, tmp_path: Path):
        """Detector skips .venv and similar directories."""
        venv_dir = tmp_path / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "site.py").write_text(
            'AutoModel.from_pretrained("some-org/some-model")\n'
        )
        # No files outside venv
        detector = HuggingFaceReferenceDetector()
        components = detector.discover(tmp_path)
        assert components == []

    def test_multiple_models_from_single_file(self, tmp_path: Path):
        """Detector handles multiple model references in one file."""
        src = (
            'AutoModel.from_pretrained("meta-llama/Llama-3.1-70B-Instruct")\n'
            'AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1")\n'
        )
        (tmp_path / "multi.py").write_text(src)

        def fake_urlopen(req, timeout=None):
            # Extract model_id from URL
            url = req.full_url
            model_id = url.split("/api/models/", 1)[-1]
            raw = _make_hf_api_response(model_id)
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.read.return_value = raw
            return mock_resp

        detector = HuggingFaceReferenceDetector()
        with patch("lcc.resolution.hf_hub_resolver.urlopen", side_effect=fake_urlopen):
            components = detector.discover(tmp_path)

        assert len(components) == 2
        names = {c.name for c in components}
        assert "Llama-3.1-70B-Instruct" in names
        assert "Mistral-7B-v0.1" in names
