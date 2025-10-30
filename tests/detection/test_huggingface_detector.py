"""Unit tests for Hugging Face Model Detector."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from lcc.detection.huggingface import HuggingFaceDetector
from lcc.models import ComponentType

if TYPE_CHECKING:
    from pytest import TempPathFactory


@pytest.fixture
def hf_model_dir(tmp_path_factory: TempPathFactory) -> Path:
    """Create a mock Hugging Face model directory."""
    model_dir = tmp_path_factory.mktemp("hf_model")

    # Create config.json
    config = {
        "model_type": "bert",
        "architectures": ["BertForMaskedLM"],
        "transformers_version": "4.30.0"
    }
    (model_dir / "config.json").write_text(json.dumps(config))

    # Create model weights
    (model_dir / "pytorch_model.bin").touch()

    # Create README with model card
    readme = """---
license: apache-2.0
tags:
- bert
- nlp
datasets:
- wikipedia
---

# BERT Model

This is a BERT model.
"""
    (model_dir / "README.md").write_text(readme)

    return model_dir


@pytest.fixture
def hf_detector() -> HuggingFaceDetector:
    """Create HuggingFaceDetector instance."""
    return HuggingFaceDetector()


def test_detector_initialization(hf_detector: HuggingFaceDetector):
    """Test detector initialization."""
    assert hf_detector.name == "huggingface"


def test_supports_valid_model_directory(hf_detector: HuggingFaceDetector, hf_model_dir: Path):
    """Test supports() returns True for valid HF model directory."""
    assert hf_detector.supports(hf_model_dir) is True


def test_supports_missing_config(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test supports() returns False when config.json is missing."""
    assert hf_detector.supports(tmp_path) is False


def test_supports_missing_weights(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test supports() returns False when model weights are missing."""
    # Create config but no weights
    config = {"model_type": "bert"}
    (tmp_path / "config.json").write_text(json.dumps(config))

    assert hf_detector.supports(tmp_path) is False


def test_supports_with_safetensors(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test supports() returns True for safetensors format."""
    config = {"model_type": "bert"}
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "model.safetensors").touch()

    assert hf_detector.supports(tmp_path) is True


def test_supports_with_tensorflow(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test supports() returns True for TensorFlow format."""
    config = {"model_type": "bert"}
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "tf_model.h5").touch()

    assert hf_detector.supports(tmp_path) is True


def test_supports_sharded_model(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test supports() returns True for sharded models."""
    config = {"model_type": "gpt2"}
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "pytorch_model-00001-of-00002.bin").touch()
    (tmp_path / "pytorch_model-00002-of-00002.bin").touch()

    assert hf_detector.supports(tmp_path) is True


def test_discover_returns_component(hf_detector: HuggingFaceDetector, hf_model_dir: Path):
    """Test discover() returns a Component for valid model."""
    components = hf_detector.discover(hf_model_dir)

    assert len(components) == 1
    component = components[0]

    assert component.type == ComponentType.AI_MODEL
    assert component.namespace == "huggingface"
    assert component.name is not None
    assert component.version == "4.30.0"


def test_discover_extracts_model_info(hf_detector: HuggingFaceDetector, hf_model_dir: Path):
    """Test discover() extracts model information from config."""
    components = hf_detector.discover(hf_model_dir)
    component = components[0]

    assert component.metadata["model_type"] == "bert"
    assert "BertForMaskedLM" in component.metadata["architecture"]


def test_discover_extracts_license_from_card(hf_detector: HuggingFaceDetector, hf_model_dir: Path):
    """Test discover() extracts license from model card."""
    components = hf_detector.discover(hf_model_dir)
    component = components[0]

    assert component.metadata.get("license_from_card") == "apache-2.0"


def test_discover_extracts_tags(hf_detector: HuggingFaceDetector, hf_model_dir: Path):
    """Test discover() extracts tags from model card."""
    components = hf_detector.discover(hf_model_dir)
    component = components[0]

    tags = component.metadata.get("tags", [])
    assert "bert" in tags
    assert "nlp" in tags


def test_discover_extracts_datasets(hf_detector: HuggingFaceDetector, hf_model_dir: Path):
    """Test discover() extracts datasets from model card."""
    components = hf_detector.discover(hf_model_dir)
    component = components[0]

    datasets = component.metadata.get("datasets", [])
    assert "wikipedia" in datasets


def test_discover_detects_pytorch_framework(hf_detector: HuggingFaceDetector, hf_model_dir: Path):
    """Test discover() detects PyTorch framework."""
    components = hf_detector.discover(hf_model_dir)
    component = components[0]

    assert component.metadata["framework"] == "pytorch"


def test_discover_detects_safetensors_framework(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test discover() detects safetensors framework."""
    config = {"model_type": "bert"}
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "model.safetensors").touch()

    detector = HuggingFaceDetector()
    components = detector.discover(tmp_path)
    component = components[0]

    assert component.metadata["framework"] == "pytorch/safetensors"


def test_discover_detects_tensorflow_framework(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test discover() detects TensorFlow framework."""
    config = {"model_type": "bert"}
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "tf_model.h5").touch()

    components = hf_detector.discover(tmp_path)
    component = components[0]

    assert component.metadata["framework"] == "tensorflow"


def test_discover_returns_empty_for_unsupported(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test discover() returns empty list for unsupported directory."""
    components = hf_detector.discover(tmp_path)
    assert len(components) == 0


def test_discover_handles_missing_readme(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test discover() handles missing README gracefully."""
    config = {"model_type": "bert"}
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "pytorch_model.bin").touch()

    components = hf_detector.discover(tmp_path)
    assert len(components) == 1


def test_discover_uses_directory_name(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test discover() uses directory name when other info unavailable."""
    model_dir = tmp_path / "bert-base-uncased"
    model_dir.mkdir()

    config = {"model_type": "bert"}
    (model_dir / "config.json").write_text(json.dumps(config))
    (model_dir / "pytorch_model.bin").touch()

    components = hf_detector.discover(model_dir)
    component = components[0]

    assert component.name == "bert-base-uncased"


def test_discover_extracts_git_url(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test discover() extracts git URL from .git/config."""
    config_data = {"model_type": "bert"}
    (tmp_path / "config.json").write_text(json.dumps(config_data))
    (tmp_path / "pytorch_model.bin").touch()

    # Create .git directory with config
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    git_config = """[remote "origin"]
    url = https://huggingface.co/bert-base-uncased
    fetch = +refs/heads/*:refs/remotes/origin/*
"""
    (git_dir / "config").write_text(git_config)

    components = hf_detector.discover(tmp_path)
    component = components[0]

    assert component.metadata.get("repository_url") == "https://huggingface.co/bert-base-uncased"


def test_parse_config_handles_invalid_json(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test _parse_config handles invalid JSON gracefully."""
    config_file = tmp_path / "config.json"
    config_file.write_text("invalid json{")

    result = hf_detector._parse_config(config_file)
    assert result == {}


def test_parse_config_handles_missing_file(hf_detector: HuggingFaceDetector, tmp_path: Path):
    """Test _parse_config handles missing file gracefully."""
    config_file = tmp_path / "nonexistent.json"

    result = hf_detector._parse_config(config_file)
    assert result == {}
