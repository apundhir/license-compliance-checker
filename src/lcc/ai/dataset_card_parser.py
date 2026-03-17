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
Dataset Card Parser

Parses dataset cards to extract license and metadata information.
Supports:
- Hugging Face dataset cards (YAML frontmatter in README.md)
- Dataset metadata files
- Custom dataset card formats

Enhanced to extract provenance and regulatory-relevant information from
markdown sections (data sources, collection methodology, PII/privacy info)
in addition to YAML frontmatter.
"""

from __future__ import annotations

import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def _strip_markdown(text: str) -> str:
    """Strip common markdown formatting from text."""
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'[*_`]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _extract_section(content: str, heading_names: list[str]) -> str | None:
    """Extract the body text of a markdown section by heading name.

    Searches for headings at level 2 (``##``) or level 3 (``###``).
    The section body extends until the next heading of equal or higher
    level or the end of the document.

    Args:
        content: Full markdown content (after frontmatter removal).
        heading_names: List of heading strings to search for (case-insensitive).

    Returns:
        The section body text, or ``None`` if the section is not found.
    """
    for name in heading_names:
        pattern = (
            r'(?:^|\n)'
            r'(#{2,3})\s+'
            + re.escape(name)
            + r'\s*\n'
            r'(.*?)'
            r'(?=\n#{1,3}\s|\Z)'
        )
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            body = match.group(2).strip()
            if body:
                return body
    return None


class DatasetCardInfo:
    """Information extracted from a dataset card."""

    def __init__(
        self,
        license: str | None = None,
        tags: list[str] = None,
        languages: list[str] = None,
        task_categories: list[str] = None,
        size_categories: str | None = None,
        dataset_name: str | None = None,
        creators: list[str] = None,
        annotations_creators: list[str] = None,
        source_datasets: list[str] = None,
        raw_metadata: dict = None,
        # --- Enhanced fields for regulatory compliance ---
        data_sources: list[str] = None,
        collection_method: str | None = None,
        privacy_info: str | None = None,
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
        # Enhanced fields
        self.data_sources = data_sources or []
        self.collection_method = collection_method
        self.privacy_info = privacy_info

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
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
        # Include enhanced fields only when populated for backward compat.
        if self.data_sources:
            result["data_sources"] = self.data_sources
        if self.collection_method:
            result["collection_method"] = self.collection_method
        if self.privacy_info:
            result["privacy_info"] = self.privacy_info
        return result


class DatasetCardParser:
    """Parser for dataset cards."""

    def parse_file(self, file_path: Path) -> DatasetCardInfo | None:
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

    def parse_content(self, content: str) -> DatasetCardInfo | None:
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

    def _extract_yaml_frontmatter(self, content: str) -> dict | None:
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
        self, frontmatter: dict, content: str
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

        # --- Extract enhanced markdown sections ---
        markdown_body = self._get_markdown_body(content)

        data_sources = self._extract_data_sources(markdown_body)
        collection_method = self._extract_collection_method(markdown_body)
        privacy_info = self._extract_privacy_info(markdown_body)

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
            data_sources=data_sources,
            collection_method=collection_method,
            privacy_info=privacy_info,
        )

    def _parse_markdown_format(self, content: str) -> DatasetCardInfo | None:
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

        # --- Extract enhanced markdown sections ---
        data_sources = self._extract_data_sources(content)
        collection_method = self._extract_collection_method(content)
        privacy_info = self._extract_privacy_info(content)

        return DatasetCardInfo(
            license=license_value,
            creators=creators,
            dataset_name=dataset_name,
            data_sources=data_sources,
            collection_method=collection_method,
            privacy_info=privacy_info,
        )

    def _extract_creators(self, content: str) -> list[str]:
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

    def _extract_dataset_name(self, content: str) -> str | None:
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

    # ------------------------------------------------------------------
    # Enhanced markdown section extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _get_markdown_body(content: str) -> str:
        """Return the markdown content after YAML frontmatter."""
        stripped = re.sub(
            r'^---\s*\n.*?\n---\s*\n', '', content, count=1, flags=re.DOTALL
        )
        return stripped

    def _extract_data_sources(self, content: str) -> list[str]:
        """Extract data source / provenance information from markdown.

        Looks for sections describing where the data comes from, and also
        scans for URLs and well-known source references.
        """
        sources: list[str] = []

        section = _extract_section(content, [
            "Data Source",
            "Data Sources",
            "Source Data",
            "Dataset Sources",
            "Data Collection",
            "Data Origin",
            "Provenance",
            "Source",
            "Sources",
        ])

        search_text = section or ""

        # Also look for a "Dataset Description" or "Dataset Summary" section
        # which often mentions sources.
        for alt_heading in ["Dataset Description", "Dataset Summary", "Description"]:
            alt_section = _extract_section(content, [alt_heading])
            if alt_section:
                search_text += "\n" + alt_section

        if not search_text.strip():
            return []

        # Capture markdown links as data sources
        link_urls = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', search_text)
        for _text, url in link_urls:
            sources.append(url)

        # Capture bare URLs
        bare_urls = re.findall(r'https?://[^\s\)>]+', search_text)
        for url in bare_urls:
            if url not in sources:
                sources.append(url)

        # Capture bullet-point items from the source section (if any)
        if section:
            items = re.findall(r'[-*]\s+(.+)', section)
            for item in items:
                cleaned = _strip_markdown(item.strip())
                if cleaned and cleaned not in sources:
                    sources.append(cleaned)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for s in sources:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        return unique

    def _extract_collection_method(self, content: str) -> str | None:
        """Extract data collection methodology description."""
        section = _extract_section(content, [
            "Collection Method",
            "Collection Methodology",
            "Data Collection",
            "Collection Process",
            "Data Collection and Processing",
            "Curation Rationale",
            "Data Gathering",
            "Initial Data Collection",
            "Initial Data Collection and Normalization",
        ])
        if section:
            return _strip_markdown(section)
        return None

    def _extract_privacy_info(self, content: str) -> str | None:
        """Extract PII / privacy information from markdown sections."""
        section = _extract_section(content, [
            "Personal and Sensitive Information",
            "Privacy",
            "PII",
            "Personally Identifiable Information",
            "Privacy Information",
            "Data Privacy",
            "Sensitive Information",
            "Personal Information",
        ])
        if section:
            return _strip_markdown(section)
        return None


def parse_dataset_card(path: Path) -> DatasetCardInfo | None:
    """
    Convenience function to parse a dataset card.

    Args:
        path: Path to dataset card file

    Returns:
        DatasetCardInfo or None
    """
    parser = DatasetCardParser()
    return parser.parse_file(path)
