"""
Hugging Face Datasets Detector

Detects datasets from Hugging Face in local repositories.
Looks for:
- dataset_infos.json (dataset metadata)
- README.md (dataset card with license info)
- Dataset files (.arrow, .parquet, .csv, .json)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from lcc.detection.base import Detector
from lcc.models import Component, ComponentType


class HuggingFaceDatasetDetector(Detector):
    """
    Detector for Hugging Face datasets.

    Identifies datasets downloaded from Hugging Face by looking for:
    1. dataset_infos.json - Dataset metadata
    2. README.md - Dataset card with license
    3. Dataset files (.arrow, .parquet, .csv, .json)
    """

    def __init__(self) -> None:
        super().__init__(name="huggingface-datasets")

    def supports(self, path: Path) -> bool:
        """
        Check if directory contains a Hugging Face dataset.

        Args:
            path: Directory to check

        Returns:
            True if HF dataset files are present
        """
        if not path.is_dir():
            return False

        # Check for dataset_infos.json (primary indicator)
        if (path / "dataset_infos.json").exists():
            return True

        # Check for README.md with dataset card markers
        readme = path / "README.md"
        if readme.exists():
            try:
                content = readme.read_text(encoding="utf-8")
                # Look for dataset card markers
                if "dataset_info:" in content or "task_categories:" in content:
                    return True
            except Exception:
                pass

        # Check for .arrow files (datasets library format)
        if list(path.glob("**/*.arrow")):
            return True

        return False

    def discover(self, path: Path) -> List[Component]:
        """
        Discover Hugging Face datasets in directory.

        Args:
            path: Directory to scan

        Returns:
            List of Component objects representing datasets
        """
        if not self.supports(path):
            return []

        components = []

        # Parse dataset_infos.json for dataset info
        dataset_infos_file = path / "dataset_infos.json"
        dataset_info = self._parse_dataset_infos(dataset_infos_file)

        # Parse README.md for license and metadata
        readme_file = path / "README.md"
        card_info = self._parse_dataset_card(readme_file)

        # Determine dataset name
        dataset_name = self._get_dataset_name(path, dataset_info, card_info)

        # Determine version
        version = dataset_info.get("version", "unknown")

        # Build metadata
        metadata = {
            "description": f"Hugging Face dataset: {dataset_name}",
            "format": self._detect_format(path),
        }

        # Add license from dataset card
        if card_info and card_info.get("license"):
            metadata["license_from_card"] = card_info["license"]

        # Add size information
        if card_info and card_info.get("size_categories"):
            metadata["size_category"] = card_info["size_categories"]

        # Add languages
        if card_info and card_info.get("languages"):
            metadata["languages"] = card_info["languages"]

        # Add task categories
        if card_info and card_info.get("task_categories"):
            metadata["task_categories"] = card_info["task_categories"]

        # Add dataset info details
        if dataset_info:
            metadata["dataset_size"] = dataset_info.get("dataset_size")
            metadata["splits"] = list(dataset_info.get("splits", {}).keys())
            metadata["features"] = dataset_info.get("features", {})

        # Add repository URL if this looks like a cloned repo
        if (path / ".git").exists():
            metadata["repository_url"] = self._extract_git_url(path)

        component = Component(
            type=ComponentType.DATASET,
            name=dataset_name,
            version=version,
            namespace="huggingface",
            path=path,
            metadata=metadata,
        )

        components.append(component)

        return components

    def _parse_dataset_infos(self, infos_file: Path) -> dict:
        """
        Parse dataset_infos.json file.

        Args:
            infos_file: Path to dataset_infos.json

        Returns:
            Parsed dataset info dict
        """
        if not infos_file.exists():
            return {}

        try:
            with open(infos_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # dataset_infos.json usually has config names as keys
                # Get the first config's info
                if data:
                    first_config = next(iter(data.values()))
                    return first_config
        except Exception:
            pass

        return {}

    def _parse_dataset_card(self, readme_file: Path) -> dict:
        """
        Parse README.md dataset card.

        Args:
            readme_file: Path to README.md

        Returns:
            Parsed dataset card info
        """
        if not readme_file.exists():
            return {}

        try:
            from lcc.ai.dataset_card_parser import parse_dataset_card
            card_info = parse_dataset_card(readme_file)
            if card_info:
                return card_info.to_dict()
        except Exception:
            pass

        return {}

    def _get_dataset_name(self, path: Path, dataset_info: dict, card_info: dict) -> str:
        """
        Determine dataset name from various sources.

        Priority:
        1. Dataset card name
        2. Directory name
        3. Dataset info description
        4. Default to directory name

        Args:
            path: Dataset directory
            dataset_info: Parsed dataset_infos.json
            card_info: Parsed dataset card

        Returns:
            Dataset name
        """
        # Try dataset card
        if card_info and card_info.get("dataset_name"):
            return card_info["dataset_name"]

        # Try directory name (e.g., "squad", "glue")
        dir_name = path.name
        if dir_name and dir_name not in ["data", "datasets", "dataset"]:
            return dir_name

        # Try dataset info
        if dataset_info.get("description"):
            desc = dataset_info["description"]
            # Extract first line as name
            name = desc.split('\n')[0].strip()
            if len(name) < 100:  # Sanity check
                return name

        # Fall back to directory name
        return path.name

    def _detect_format(self, path: Path) -> str:
        """
        Detect dataset file format.

        Args:
            path: Dataset directory

        Returns:
            Format name ("arrow", "parquet", "csv", "json", "mixed")
        """
        formats = set()

        # Check for Arrow files
        if list(path.glob("**/*.arrow")):
            formats.add("arrow")

        # Check for Parquet files
        if list(path.glob("**/*.parquet")):
            formats.add("parquet")

        # Check for CSV files
        if list(path.glob("**/*.csv")):
            formats.add("csv")

        # Check for JSON files
        if list(path.glob("**/*.json")) or list(path.glob("**/*.jsonl")):
            formats.add("json")

        if len(formats) == 0:
            return "unknown"
        elif len(formats) == 1:
            return formats.pop()
        else:
            return "mixed"

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
                match = re.search(r'url\s*=\s*(https://huggingface\.co/datasets/[^\s]+)', content)
                if match:
                    return match.group(1)
        except Exception:
            pass

        return ""
