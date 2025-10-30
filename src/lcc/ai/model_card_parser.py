"""
Model Card Parser

Parses AI model cards to extract license and metadata information.
Supports:
- Hugging Face model cards (YAML frontmatter in README.md)
- Papers with Code model cards
- Custom model card formats
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


class ModelCardInfo:
    """Information extracted from a model card."""

    def __init__(
        self,
        license: Optional[str] = None,
        tags: List[str] = None,
        datasets: List[str] = None,
        language: Optional[str] = None,
        pipeline_tag: Optional[str] = None,
        library_name: Optional[str] = None,
        model_name: Optional[str] = None,
        authors: List[str] = None,
        raw_metadata: Dict = None,
    ):
        self.license = license
        self.tags = tags or []
        self.datasets = datasets or []
        self.language = language
        self.pipeline_tag = pipeline_tag
        self.library_name = library_name
        self.model_name = model_name
        self.authors = authors or []
        self.raw_metadata = raw_metadata or {}

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "license": self.license,
            "tags": self.tags,
            "datasets": self.datasets,
            "language": self.language,
            "pipeline_tag": self.pipeline_tag,
            "library_name": self.library_name,
            "model_name": self.model_name,
            "authors": self.authors,
            "raw_metadata": self.raw_metadata,
        }


class ModelCardParser:
    """Parser for AI model cards."""

    def parse_file(self, file_path: Path) -> Optional[ModelCardInfo]:
        """
        Parse a model card file.

        Args:
            file_path: Path to README.md or model card file

        Returns:
            ModelCardInfo or None if parsing fails
        """
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            return self.parse_content(content)
        except Exception:
            return None

    def parse_content(self, content: str) -> Optional[ModelCardInfo]:
        """
        Parse model card content.

        Args:
            content: Raw model card content

        Returns:
            ModelCardInfo or None if parsing fails
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

        Hugging Face model cards use YAML frontmatter between --- delimiters.

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
    ) -> ModelCardInfo:
        """
        Parse Hugging Face model card format.

        Args:
            frontmatter: Parsed YAML frontmatter
            content: Full markdown content

        Returns:
            ModelCardInfo
        """
        # Extract license
        license_value = frontmatter.get("license")
        if isinstance(license_value, list):
            # Multiple licenses
            license_str = " OR ".join(license_value)
        else:
            license_str = license_value

        # Extract tags
        tags = frontmatter.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        # Extract datasets
        datasets = frontmatter.get("datasets", [])
        if isinstance(datasets, str):
            datasets = [datasets]

        # Extract language
        language = frontmatter.get("language")
        if isinstance(language, list) and language:
            language = language[0]

        # Extract pipeline tag
        pipeline_tag = frontmatter.get("pipeline_tag")

        # Extract library
        library_name = frontmatter.get("library_name")

        # Extract model name
        model_name = frontmatter.get("model_name") or frontmatter.get("model-index", [{}])[0].get("name")

        # Try to extract authors from content
        authors = self._extract_authors(content)

        return ModelCardInfo(
            license=license_str,
            tags=tags,
            datasets=datasets,
            language=language,
            pipeline_tag=pipeline_tag,
            library_name=library_name,
            model_name=model_name,
            authors=authors,
            raw_metadata=frontmatter,
        )

    def _parse_markdown_format(self, content: str) -> Optional[ModelCardInfo]:
        """
        Parse plain markdown model card.

        Looks for license information in common sections.

        Args:
            content: Markdown content

        Returns:
            ModelCardInfo or None
        """
        # Try to find license in common patterns
        license_patterns = [
            r'##?\s*License\s*\n+(.*?)(?:\n##|$)',
            r'License:\s*([^\n]+)',
            r'\*\*License\*\*:\s*([^\n]+)',
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

        # Extract authors
        authors = self._extract_authors(content)

        return ModelCardInfo(
            license=license_value,
            authors=authors,
        )

    def _extract_authors(self, content: str) -> List[str]:
        """
        Extract author names from model card content.

        Args:
            content: Model card content

        Returns:
            List of author names
        """
        authors = []

        # Look for common author patterns
        author_patterns = [
            r'##?\s*Authors?\s*\n+(.*?)(?:\n##|$)',
            r'Authors?:\s*([^\n]+)',
            r'\*\*Authors?\*\*:\s*([^\n]+)',
            r'by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]

        for pattern in author_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                author_text = match.group(1).strip()
                # Clean up markdown
                author_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', author_text)
                author_text = re.sub(r'[*_`]', '', author_text)
                # Split by common delimiters
                author_list = re.split(r'[,;&]|\band\b|\n', author_text)
                authors.extend([a.strip() for a in author_list if a.strip()])
                break

        return authors[:5]  # Limit to 5 authors


def parse_model_card(path: Path) -> Optional[ModelCardInfo]:
    """
    Convenience function to parse a model card.

    Args:
        path: Path to model card file

    Returns:
        ModelCardInfo or None
    """
    parser = ModelCardParser()
    return parser.parse_file(path)
