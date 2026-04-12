"""Tests for GGUF and ONNX model detection in HuggingFaceDetector."""

from __future__ import annotations

from pathlib import Path

import pytest

from lcc.detection.huggingface import HuggingFaceDetector


@pytest.fixture
def detector() -> HuggingFaceDetector:
    return HuggingFaceDetector()


def test_supports_gguf_directory(tmp_path: Path, detector: HuggingFaceDetector):
    """Detector supports directories with .gguf files."""
    gguf_file = tmp_path / "Meta-Llama-3.1-70B-Q4_K_M.gguf"
    gguf_file.write_bytes(b"GGUF" + b"\x03\x00\x00\x00" + b"\x00" * 100)

    assert detector.supports(tmp_path)


def test_does_not_support_empty_directory(tmp_path: Path, detector: HuggingFaceDetector):
    """Detector returns False for a directory with no model files."""
    assert not detector.supports(tmp_path)


def test_gguf_name_inference_mistral(tmp_path: Path, detector: HuggingFaceDetector):
    """GGUF filename used to infer mistralai model family."""
    gguf_file = tmp_path / "Mistral-7B-Instruct-v0.3.Q8_0.gguf"
    gguf_file.write_bytes(b"GGUF" + b"\x03\x00\x00\x00" + b"\x00" * 100)

    metadata = detector._extract_gguf_metadata(gguf_file)
    assert metadata.get("inferred_source") == "mistralai"


def test_gguf_name_inference_llama(tmp_path: Path, detector: HuggingFaceDetector):
    """GGUF filename used to infer meta-llama model family."""
    gguf_file = tmp_path / "Meta-Llama-3.1-70B-Instruct-Q4_K_M.gguf"
    gguf_file.write_bytes(b"GGUF" + b"\x03\x00\x00\x00" + b"\x00" * 100)

    metadata = detector._extract_gguf_metadata(gguf_file)
    assert metadata.get("inferred_source") == "meta-llama"


def test_gguf_name_inference_qwen(tmp_path: Path, detector: HuggingFaceDetector):
    """GGUF filename used to infer Qwen model family."""
    gguf_file = tmp_path / "Qwen2.5-Coder-32B-Instruct-Q5_K_M.gguf"
    gguf_file.write_bytes(b"GGUF" + b"\x03\x00\x00\x00" + b"\x00" * 100)

    metadata = detector._extract_gguf_metadata(gguf_file)
    assert metadata.get("inferred_source") == "Qwen"


def test_gguf_invalid_magic_returns_empty(tmp_path: Path, detector: HuggingFaceDetector):
    """File with wrong magic bytes returns empty metadata."""
    gguf_file = tmp_path / "fake.gguf"
    gguf_file.write_bytes(b"FAKE" + b"\x00" * 100)

    metadata = detector._extract_gguf_metadata(gguf_file)
    assert metadata == {}


def test_supports_onnx_directory(tmp_path: Path, detector: HuggingFaceDetector):
    """Detector supports directories with .onnx files."""
    onnx_file = tmp_path / "model.onnx"
    onnx_file.write_bytes(b"\x08\x00" + b"\x00" * 50)

    assert detector.supports(tmp_path)


def test_discover_gguf_returns_components(tmp_path: Path, detector: HuggingFaceDetector):
    """discover() returns a Component for each GGUF file found."""
    gguf_file = tmp_path / "Mistral-7B-Instruct-v0.3.Q8_0.gguf"
    gguf_file.write_bytes(b"GGUF" + b"\x03\x00\x00\x00" + b"\x00" * 100)

    components = detector.discover(tmp_path)
    assert len(components) == 1
    comp = components[0]
    assert comp.name == "Mistral-7B-Instruct-v0.3.Q8_0"
    assert comp.namespace == "gguf"
    assert comp.metadata["format"] == "gguf"
    assert comp.metadata["inferred_source"] == "mistralai"


def test_discover_onnx_returns_components(tmp_path: Path, detector: HuggingFaceDetector):
    """discover() returns a Component for each ONNX file found."""
    onnx_file = tmp_path / "encoder.onnx"
    onnx_file.write_bytes(b"\x08\x00" + b"\x00" * 50)

    components = detector.discover(tmp_path)
    assert len(components) == 1
    comp = components[0]
    assert comp.name == "encoder"
    assert comp.namespace == "onnx"
    assert comp.metadata["format"] == "onnx"


def test_discover_multiple_gguf_files(tmp_path: Path, detector: HuggingFaceDetector):
    """discover() returns one Component per GGUF file."""
    for name in ["model-q4.gguf", "model-q8.gguf"]:
        (tmp_path / name).write_bytes(b"GGUF" + b"\x03\x00\x00\x00" + b"\x00" * 100)

    components = detector.discover(tmp_path)
    assert len(components) == 2
    namespaces = {c.namespace for c in components}
    assert namespaces == {"gguf"}
