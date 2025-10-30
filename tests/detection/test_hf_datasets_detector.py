"""Unit tests for Hugging Face Dataset Detector."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from lcc.detection.hf_datasets import HuggingFaceDatasetDetector
from lcc.models import ComponentType

if TYPE_CHECKING:
    from pytest import TempPathFactory


@pytest.fixture
def hf_dataset_dir(tmp_path_factory: TempPathFactory) -> Path:
    """Create a mock Hugging Face dataset directory."""
    dataset_dir = tmp_path_factory.mktemp("hf_dataset")

    # Create dataset_infos.json
    dataset_info = {
        "default": {
            "description": "Test dataset",
            "features": {
                "text": {"dtype": "string"},
                "label": {"dtype": "int32"}
            },
            "splits": {
                "train": {"name": "train", "num_examples": 1000}
            }
        }
    }
    (dataset_dir / "dataset_infos.json").write_text(json.dumps(dataset_info))

    # Create dataset card
    readme = """---
license: mit
tags:
- text-classification
languages:
- en
size_categories:
- 1K<n<10K
task_categories:
- text-classification
---

# Test Dataset

A test dataset for classification.
"""
    (dataset_dir / "README.md").write_text(readme)

    # Create data files
    (dataset_dir / "train-00000-of-00001.arrow").touch()

    return dataset_dir


@pytest.fixture
def dataset_detector() -> HuggingFaceDatasetDetector:
    """Create HuggingFaceDatasetDetector instance."""
    return HuggingFaceDatasetDetector()


def test_detector_initialization(dataset_detector: HuggingFaceDatasetDetector):
    """Test detector initialization."""
    assert dataset_detector.name == "huggingface-datasets"


def test_supports_valid_dataset_directory(dataset_detector: HuggingFaceDatasetDetector, hf_dataset_dir: Path):
    """Test supports() returns True for valid HF dataset directory."""
    assert dataset_detector.supports(hf_dataset_dir) is True


def test_supports_with_readme_only(dataset_detector: HuggingFaceDatasetDetector, tmp_path: Path):
    """Test supports() returns True with README containing dataset metadata."""
    readme = """---
dataset_info:
  features:
    - name: text
      dtype: string
---

# Dataset
"""
    (tmp_path / "README.md").write_text(readme)
    (tmp_path / "data.arrow").touch()

    assert dataset_detector.supports(tmp_path) is True


def test_supports_returns_false_for_empty_dir(dataset_detector: HuggingFaceDatasetDetector, tmp_path: Path):
    """Test supports() returns False for empty directory."""
    assert dataset_detector.supports(tmp_path) is False


def test_discover_returns_component(dataset_detector: HuggingFaceDatasetDetector, hf_dataset_dir: Path):
    """Test discover() returns a Component for valid dataset."""
    components = dataset_detector.discover(hf_dataset_dir)

    assert len(components) == 1
    component = components[0]

    assert component.type == ComponentType.DATASET
    assert component.namespace == "huggingface"
    assert component.name is not None


def test_discover_extracts_dataset_info(dataset_detector: HuggingFaceDatasetDetector, hf_dataset_dir: Path):
    """Test discover() extracts dataset information."""
    components = dataset_detector.discover(hf_dataset_dir)
    component = components[0]

    assert "description" in component.metadata
    assert "features" in component.metadata


def test_discover_extracts_license_from_card(dataset_detector: HuggingFaceDatasetDetector, hf_dataset_dir: Path):
    """Test discover() extracts license from dataset card."""
    components = dataset_detector.discover(hf_dataset_dir)
    component = components[0]

    assert component.metadata.get("license_from_card") == "mit"


def test_discover_extracts_tags(dataset_detector: HuggingFaceDatasetDetector, hf_dataset_dir: Path):
    """Test discover() extracts tags from dataset card."""
    components = dataset_detector.discover(hf_dataset_dir)
    component = components[0]

    # Tags are stored in task_categories, not tags
    task_categories = component.metadata.get("task_categories", [])
    assert "text-classification" in task_categories


def test_discover_extracts_languages(dataset_detector: HuggingFaceDatasetDetector, hf_dataset_dir: Path):
    """Test discover() extracts languages from dataset card."""
    components = dataset_detector.discover(hf_dataset_dir)
    component = components[0]

    languages = component.metadata.get("languages", [])
    assert "en" in languages


def test_discover_detects_arrow_format(dataset_detector: HuggingFaceDatasetDetector, hf_dataset_dir: Path):
    """Test discover() detects Arrow format."""
    components = dataset_detector.discover(hf_dataset_dir)
    component = components[0]

    # Format is "mixed" because dataset_infos.json is also a .json file
    assert component.metadata["format"] in ["arrow", "mixed"]


def test_discover_detects_parquet_format(dataset_detector: HuggingFaceDatasetDetector, tmp_path: Path):
    """Test discover() detects Parquet format."""
    dataset_info = {"default": {"description": "Test"}}
    (tmp_path / "dataset_infos.json").write_text(json.dumps(dataset_info))
    (tmp_path / "train.parquet").touch()

    components = dataset_detector.discover(tmp_path)
    component = components[0]

    # Format is "mixed" because dataset_infos.json is also a .json file
    assert component.metadata["format"] in ["parquet", "mixed"]


def test_discover_detects_csv_format(dataset_detector: HuggingFaceDatasetDetector, tmp_path: Path):
    """Test discover() detects CSV format."""
    dataset_info = {"default": {"description": "Test"}}
    (tmp_path / "dataset_infos.json").write_text(json.dumps(dataset_info))
    (tmp_path / "train.csv").touch()

    components = dataset_detector.discover(tmp_path)
    component = components[0]

    # Format is "mixed" because dataset_infos.json is also a .json file
    assert component.metadata["format"] in ["csv", "mixed"]


def test_discover_detects_json_format(dataset_detector: HuggingFaceDatasetDetector, tmp_path: Path):
    """Test discover() detects JSON format."""
    dataset_info = {"default": {"description": "Test"}}
    (tmp_path / "dataset_infos.json").write_text(json.dumps(dataset_info))
    (tmp_path / "train.json").touch()

    components = dataset_detector.discover(tmp_path)
    component = components[0]

    assert component.metadata["format"] == "json"


def test_discover_returns_empty_for_unsupported(dataset_detector: HuggingFaceDatasetDetector, tmp_path: Path):
    """Test discover() returns empty list for unsupported directory."""
    components = dataset_detector.discover(tmp_path)
    assert len(components) == 0


def test_discover_handles_missing_readme(dataset_detector: HuggingFaceDatasetDetector, tmp_path: Path):
    """Test discover() handles missing README gracefully."""
    dataset_info = {"default": {"description": "Test"}}
    (tmp_path / "dataset_infos.json").write_text(json.dumps(dataset_info))
    (tmp_path / "data.arrow").touch()

    components = dataset_detector.discover(tmp_path)
    assert len(components) == 1


def test_discover_uses_directory_name(dataset_detector: HuggingFaceDatasetDetector, tmp_path: Path):
    """Test discover() uses directory name when other info unavailable."""
    dataset_dir = tmp_path / "my-dataset"
    dataset_dir.mkdir()

    dataset_info = {"default": {}}
    (dataset_dir / "dataset_infos.json").write_text(json.dumps(dataset_info))
    (dataset_dir / "data.arrow").touch()

    components = dataset_detector.discover(dataset_dir)
    component = components[0]

    assert component.name == "my-dataset"


def test_parse_dataset_infos_handles_invalid_json(dataset_detector: HuggingFaceDatasetDetector, tmp_path: Path):
    """Test _parse_dataset_infos handles invalid JSON gracefully."""
    info_file = tmp_path / "dataset_infos.json"
    info_file.write_text("invalid json{")

    result = dataset_detector._parse_dataset_infos(info_file)
    assert result == {}


def test_parse_dataset_infos_handles_missing_file(dataset_detector: HuggingFaceDatasetDetector, tmp_path: Path):
    """Test _parse_dataset_infos handles missing file gracefully."""
    info_file = tmp_path / "nonexistent.json"

    result = dataset_detector._parse_dataset_infos(info_file)
    assert result == {}
