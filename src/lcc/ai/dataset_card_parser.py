"""
Dataset Card Parser

Parses dataset cards to extract license and metadata information.
Supports:
- Hugging Face dataset cards (YAML frontmatter in README.md)
- Dataset metadata files
- Custom dataset card formats
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


class DatasetCardInfo:
    """Information extracted from a dataset card."""

    def __init__(
        self,
        license: Optional[str] = None,
        tags: List[str] = None,
        languages: List[str] = None,
        task_categories: List[str] = None,
        size_categories: Optional[str] = None,
        dataset_name: Optional[str] = None,
        creators: List[str] = None,
        annotations_creators: List[str] = None,
        source_datasets: List[str] = None,
        raw_metadata: Dict = None,
    ):
        self.license = license
        self.tags = tags or []
        self.languages = languages or []
        self.task_categories = task_categories or []
        self.size_categories = size_categories
        self.dataset_name = dataset_name
        self.creators = creators or []
        self.annotations_creators = annotations_creators or []
        self.source_datasets = source_datasets or []
        self.raw_metadata = raw_metadata or {}

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "license": self.license,
            "tags": self.tags,
            "languages": self.languages,
            "task_categories": self.task_categories,
            "size_categories": self.size_categories,
            "dataset_name": self.dataset_name,
            "creators": self.creators,
            "annotations_creators": self.annotations_creators,
            "source_datasets": self.source_datasets,
            "raw_metadata": self.raw_metadata,
        }


class DatasetCardParser:
    """Parser for dataset cards."""

    def parse_file(self, file_path: Path) -> Optional[DatasetCardInfo]:
        """
        Parse a dataset card file.

        Args:
            file_path: Path to README.md or dataset card file

        Returns:
            DatasetCardInfo or None if parsing fails
        """
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            return self.parse_content(content)
        except Exception:
            return None

    def parse_content(self, content: str) -> Optional[DatasetCardInfo]:
        """
        Parse dataset card content.

        Args:
            content: Raw dataset card content

        Returns:
            DatasetCardInfo or None if parsing fails
        """
        # Try to parse YAML frontmatter first (Hugging Face format)
        frontmatter = self._extract_yaml_frontmatter(content)
        if frontmatter:
            return self._parse_huggingface_format(frontmatter, content)

        # Try to parse structured markdown
        return self._parse_markdown_format(content)

    def _extract_yaml_frontmatter(self, content: str) -> Optional[Dict]:
        """
        Extract YAML frontmatter from markdown.

        Hugging Face dataset cards use YAML frontmatter between --- delimiters.

        Args:
            content: Markdown content

        Returns:
            Parsed YAML dict or None
        """
        if yaml is None:
            return None

        # Match YAML frontmatter pattern
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return None

        try:
            yaml_content = match.group(1)
            return yaml.safe_load(yaml_content)
        except Exception:
            return None

    def _parse_huggingface_format(
        self, frontmatter: Dict, content: str
    ) -> DatasetCardInfo:
        """
        Parse Hugging Face dataset card format.

        Args:
            frontmatter: Parsed YAML frontmatter
            content: Full markdown content

        Returns:
            DatasetCardInfo
        """
        # Extract license
        license_value = frontmatter.get("license") or frontmatter.get("licenses")
        if isinstance(license_value, list):
            # Multiple licenses
            license_str = " OR ".join(license_value)
        else:
            license_str = license_value

        # Extract tags
        tags = frontmatter.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        # Extract languages
        languages = frontmatter.get("language", []) or frontmatter.get("languages", [])
        if isinstance(languages, str):
            languages = [languages]

        # Extract task categories
        task_categories = frontmatter.get("task_categories", [])
        if isinstance(task_categories, str):
            task_categories = [task_categories]

        # Extract size category
        size_categories = frontmatter.get("size_categories")

        # Extract dataset name
        dataset_name = frontmatter.get("dataset_name") or frontmatter.get("pretty_name")

        # Extract creators
        creators = frontmatter.get("creators", [])
        if isinstance(creators, str):
            creators = [creators]

        # Extract annotation creators
        annotations_creators = frontmatter.get("annotations_creators", [])
        if isinstance(annotations_creators, str):
            annotations_creators = [annotations_creators]

        # Extract source datasets
        source_datasets = frontmatter.get("source_datasets", [])
        if isinstance(source_datasets, str):
            source_datasets = [source_datasets]

        # Try to extract additional creators from content
        if not creators:
            creators = self._extract_creators(content)

        return DatasetCardInfo(
            license=license_str,
            tags=tags,
            languages=languages,
            task_categories=task_categories,
            size_categories=size_categories,
            dataset_name=dataset_name,
            creators=creators,
            annotations_creators=annotations_creators,
            source_datasets=source_datasets,
            raw_metadata=frontmatter,
        )

    def _parse_markdown_format(self, content: str) -> Optional[DatasetCardInfo]:
        """
        Parse plain markdown dataset card.

        Looks for license information in common sections.

        Args:
            content: Markdown content

        Returns:
            DatasetCardInfo or None
        """
        # Try to find license in common patterns
        license_patterns = [
            r'##?\s*License\s*\n+(.*?)(?:\n##|$)',
            r'License:\s*([^\n]+)',
            r'\*\*License\*\*:\s*([^\n]+)',
            r'##?\s*Licensing Information\s*\n+(.*?)(?:\n##|$)',
        ]

        license_value = None
        for pattern in license_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                license_text = match.group(1).strip()
                # Clean up markdown formatting
                license_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', license_text)
                license_text = re.sub(r'[*_`]', '', license_text)
                license_value = license_text.split('\n')[0].strip()
                break

        if not license_value:
            return None

        # Extract creators
        creators = self._extract_creators(content)

        # Try to extract dataset name from title
        dataset_name = self._extract_dataset_name(content)

        return DatasetCardInfo(
            license=license_value,
            creators=creators,
            dataset_name=dataset_name,
        )

    def _extract_creators(self, content: str) -> List[str]:
        """
        Extract creator names from dataset card content.

        Args:
            content: Dataset card content

        Returns:
            List of creator names
        """
        creators = []

        # Look for common creator patterns
        creator_patterns = [
            r'##?\s*(?:Creators?|Authors?|Contributors?)\s*\n+(.*?)(?:\n##|$)',
            r'(?:Creators?|Authors?|Contributors?):\s*([^\n]+)',
            r'\*\*(?:Creators?|Authors?|Contributors?)\*\*:\s*([^\n]+)',
        ]

        for pattern in creator_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                creator_text = match.group(1).strip()
                # Clean up markdown
                creator_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', creator_text)
                creator_text = re.sub(r'[*_`]', '', creator_text)
                # Split by common delimiters
                creator_list = re.split(r'[,;&]|\band\b|\n', creator_text)
                creators.extend([c.strip() for c in creator_list if c.strip()])
                break

        return creators[:5]  # Limit to 5 creators

    def _extract_dataset_name(self, content: str) -> Optional[str]:
        """
        Extract dataset name from content.

        Args:
            content: Dataset card content

        Returns:
            Dataset name or None
        """
        # Look for first # heading
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            name = match.group(1).strip()
            # Clean up common suffixes
            name = re.sub(r'\s+Dataset$', '', name, flags=re.IGNORECASE)
            return name

        return None


def parse_dataset_card(path: Path) -> Optional[DatasetCardInfo]:
    """
    Convenience function to parse a dataset card.

    Args:
        path: Path to dataset card file

    Returns:
        DatasetCardInfo or None
    """
    parser = DatasetCardParser()
    return parser.parse_file(path)
