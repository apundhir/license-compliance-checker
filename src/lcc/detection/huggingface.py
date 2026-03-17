# Copyright 2025 Ajay Pundhir
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Hugging Face Model Detector

Detects AI models from Hugging Face Hub in local repositories.
Looks for:
- config.json (model configuration)
- README.md (model card with license info)
- pytorch_model.bin / model.safetensors (model weights)
"""

from __future__ import annotations

from pathlib import Path

from lcc.detection.base import Detector
from lcc.models import Component, ComponentType


class HuggingFaceDetector(Detector):
    """
    Detector for Hugging Face models.

    Identifies models downloaded from Hugging Face Hub by looking for:
    1. config.json - Model configuration
    2. README.md - Model card with metadata
    3. Model weight files (.bin, .safetensors, .h5, .ckpt)
    """

    def __init__(self) -> None:
        super().__init__(name="huggingface")

    def supports(self, path: Path) -> bool:
        """
        Check if directory contains a Hugging Face model.

        Args:
            path: Directory to check

        Returns:
            True if HF model files are present
        """
        if not path.is_dir():
            return False

        # Check for config.json (primary indicator)
        config_file = path / "config.json"
        if config_file.exists():
            # Verify it's likely a model by checking for weight files
            weight_patterns = [
                "pytorch_model.bin",
                "model.safetensors",
                "tf_model.h5",
                "flax_model.msgpack",
                "model.ckpt",
            ]
            for pattern in weight_patterns:
                if (path / pattern).exists():
                    return True

            # Also check for sharded models
            if list(path.glob("pytorch_model-*.bin")):
                return True
            if list(path.glob("model-*.safetensors")):
                return True

        return False

    def discover(self, path: Path) -> list[Component]:
        """
        Discover Hugging Face models in directory.

        Args:
            path: Directory to scan

        Returns:
            List of Component objects representing models
        """
        if not self.supports(path):
            return []

        components = []

        # Parse config.json for model info
        config_file = path / "config.json"
        model_info = self._parse_config(config_file)

        # Parse README.md for license and metadata
        readme_file = path / "README.md"
        card_info = self._parse_model_card(readme_file)

        # Determine model name
        model_name = self._get_model_name(path, model_info, card_info)

        # Determine version (if available)
        version = model_info.get("transformers_version", "unknown")

        # Build metadata
        metadata = {
            "description": f"Hugging Face model: {model_name}",
            "model_type": model_info.get("model_type", "unknown"),
            "architecture": model_info.get("architectures", []),
            "framework": self._detect_framework(path),
        }

        # Add license from model card
        if card_info and card_info.get("license"):
            metadata["license_from_card"] = card_info["license"]

        # Add tags
        if card_info and card_info.get("tags"):
            metadata["tags"] = card_info["tags"]

        # Add datasets
        if card_info and card_info.get("datasets"):
            metadata["datasets"] = card_info["datasets"]

        # Add enhanced model card fields (regulatory/EU AI Act relevant)
        if card_info and card_info.get("training_data_sources"):
            metadata["training_data_sources"] = card_info["training_data_sources"]
        if card_info and card_info.get("training_data_description"):
            metadata["training_data_description"] = card_info["training_data_description"]
        if card_info and card_info.get("limitations"):
            metadata["limitations"] = card_info["limitations"]
        if card_info and card_info.get("evaluation_metrics"):
            metadata["evaluation_metrics"] = card_info["evaluation_metrics"]
        if card_info and card_info.get("intended_uses"):
            metadata["intended_uses"] = card_info["intended_uses"]
        if card_info and card_info.get("out_of_scope_uses"):
            metadata["out_of_scope_uses"] = card_info["out_of_scope_uses"]
        if card_info and card_info.get("environmental_impact"):
            metadata["environmental_impact"] = card_info["environmental_impact"]
        if card_info and card_info.get("use_restrictions"):
            metadata["use_restrictions"] = card_info["use_restrictions"]

        # Add repository URL if this looks like a cloned repo
        if (path / ".git").exists():
            metadata["repository_url"] = self._extract_git_url(path)

        component = Component(
            type=ComponentType.AI_MODEL,
            name=model_name,
            version=version,
            namespace="huggingface",
            path=path,
            metadata=metadata,
        )

        components.append(component)

        return components

    def _parse_config(self, config_file: Path) -> dict:
        """
        Parse config.json file.

        Args:
            config_file: Path to config.json

        Returns:
            Parsed configuration dict
        """
        if not config_file.exists():
            return {}

        try:
            import json
            with open(config_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _parse_model_card(self, readme_file: Path) -> dict:
        """
        Parse README.md model card.

        Args:
            readme_file: Path to README.md

        Returns:
            Parsed model card info
        """
        if not readme_file.exists():
            return {}

        try:
            from lcc.ai.model_card_parser import parse_model_card
            card_info = parse_model_card(readme_file)
            if card_info:
                return card_info.to_dict()
        except Exception:
            pass

        return {}

    def _get_model_name(self, path: Path, config: dict, card_info: dict) -> str:
        """
        Determine model name from various sources.

        Priority:
        1. Model card name
        2. Directory name (if looks like a HF repo path)
        3. Config architecture
        4. Default to directory name

        Args:
            path: Model directory
            config: Parsed config.json
            card_info: Parsed model card

        Returns:
            Model name
        """
        # Try model card
        if card_info and card_info.get("model_name"):
            return card_info["model_name"]

        # Try directory name (e.g., "bert-base-uncased")
        dir_name = path.name
        if "-" in dir_name or "_" in dir_name:
            return dir_name

        # Try architecture from config
        architectures = config.get("architectures", [])
        if architectures:
            return architectures[0]

        # Fall back to directory name
        return dir_name

    def _detect_framework(self, path: Path) -> str:
        """
        Detect ML framework used by model.

        Args:
            path: Model directory

        Returns:
            Framework name ("pytorch", "tensorflow", "jax", "unknown")
        """
        # Check for PyTorch files
        if (path / "pytorch_model.bin").exists() or list(path.glob("pytorch_model-*.bin")):
            return "pytorch"

        # Check for safetensors (can be PyTorch or others)
        if (path / "model.safetensors").exists() or list(path.glob("model-*.safetensors")):
            return "pytorch/safetensors"

        # Check for TensorFlow files
        if (path / "tf_model.h5").exists() or (path / "saved_model.pb").exists():
            return "tensorflow"

        # Check for JAX/Flax files
        if (path / "flax_model.msgpack").exists():
            return "jax/flax"

        # Check for ONNX
        if (path / "model.onnx").exists():
            return "onnx"

        return "unknown"

    def _extract_git_url(self, path: Path) -> str:
        """
        Extract git remote URL from .git directory.

        Args:
            path: Repository path

        Returns:
            Git remote URL or empty string
        """
        try:
            git_config = path / ".git" / "config"
            if git_config.exists():
                content = git_config.read_text(encoding="utf-8")
                # Look for Hugging Face URL
                import re
                match = re.search(r'url\s*=\s*(https://huggingface\.co/[^\s]+)', content)
                if match:
                    return match.group(1)
        except Exception:
            pass

        return ""
