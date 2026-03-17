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
Model Card Parser

Parses AI model cards to extract license and metadata information.
Supports:
- Hugging Face model cards (YAML frontmatter in README.md)
- Papers with Code model cards
- Custom model card formats

Enhanced to extract regulatory-relevant information from markdown sections
(training data, limitations, evaluation results, intended uses,
environmental impact, and use restrictions) in addition to YAML frontmatter.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


def _strip_markdown(text: str) -> str:
    """Strip common markdown formatting from text.

    Converts links ``[text](url)`` to just ``text``, removes bold/italic
    markers and inline code backticks, and collapses excessive whitespace.
    """
    # Convert markdown links to just the link text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove bold/italic/code markers
    text = re.sub(r'[*_`]', '', text)
    # Collapse multiple blank lines into one
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _extract_section(content: str, heading_names: list[str]) -> str | None:
    """Extract the body text of a markdown section by heading name.

    Searches for headings at level 2 (``##``) or level 3 (``###``).  The
    section body extends until the next heading of equal or higher level or
    the end of the document.

    Args:
        content: Full markdown content (after frontmatter removal).
        heading_names: List of heading strings to search for (case-insensitive).

    Returns:
        The section body text (stripped of leading/trailing whitespace), or
        ``None`` if the section is not found.
    """
    for name in heading_names:
        # Match ## or ### headings (with optional trailing whitespace / anchors)
        pattern = (
            r'(?:^|\n)'            # start of string or newline
            r'(#{2,3})\s+'         # heading level (capture to know depth)
            + re.escape(name)      # heading text
            + r'\s*\n'             # optional trailing whitespace + newline
            r'(.*?)'              # body (non-greedy)
            r'(?=\n#{1,3}\s|\Z)'  # stop at next heading of level 1-3 or end
        )
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            body = match.group(2).strip()
            if body:
                return body
    return None


class ModelCardInfo:
    """Information extracted from a model card."""

    def __init__(
        self,
        license: str | None = None,
        tags: list[str] = None,
        datasets: list[str] = None,
        language: str | None = None,
        pipeline_tag: str | None = None,
        library_name: str | None = None,
        model_name: str | None = None,
        authors: list[str] = None,
        raw_metadata: dict = None,
        # --- Enhanced fields for regulatory/EU AI Act compliance ---
        training_data_sources: list[str] = None,
        training_data_description: str | None = None,
        limitations: str | None = None,
        evaluation_metrics: dict[str, Any] = None,
        intended_uses: str | None = None,
        out_of_scope_uses: str | None = None,
        environmental_impact: dict[str, str] = None,
        use_restrictions: list[str] = None,
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
        # Enhanced fields
        self.training_data_sources = training_data_sources or []
        self.training_data_description = training_data_description
        self.limitations = limitations
        self.evaluation_metrics = evaluation_metrics or {}
        self.intended_uses = intended_uses
        self.out_of_scope_uses = out_of_scope_uses
        self.environmental_impact = environmental_impact or {}
        self.use_restrictions = use_restrictions or []

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
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
        # Include enhanced fields only when populated so that callers that
        # rely on the original dict shape are not affected by empty extras.
        if self.training_data_sources:
            result["training_data_sources"] = self.training_data_sources
        if self.training_data_description:
            result["training_data_description"] = self.training_data_description
        if self.limitations:
            result["limitations"] = self.limitations
        if self.evaluation_metrics:
            result["evaluation_metrics"] = self.evaluation_metrics
        if self.intended_uses:
            result["intended_uses"] = self.intended_uses
        if self.out_of_scope_uses:
            result["out_of_scope_uses"] = self.out_of_scope_uses
        if self.environmental_impact:
            result["environmental_impact"] = self.environmental_impact
        if self.use_restrictions:
            result["use_restrictions"] = self.use_restrictions
        return result


class ModelCardParser:
    """Parser for AI model cards."""

    def parse_file(self, file_path: Path) -> ModelCardInfo | None:
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

    def parse_content(self, content: str) -> ModelCardInfo | None:
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

    def _extract_yaml_frontmatter(self, content: str) -> dict | None:
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
        self, frontmatter: dict, content: str
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

        # --- Extract enhanced markdown sections ---
        markdown_body = self._get_markdown_body(content)

        training_data_sources, training_data_description = (
            self._extract_training_data(markdown_body)
        )
        limitations = self._extract_limitations(markdown_body)
        evaluation_metrics = self._extract_evaluation_metrics(markdown_body)
        intended_uses = self._extract_intended_uses(markdown_body)
        out_of_scope_uses = self._extract_out_of_scope_uses(markdown_body)
        environmental_impact = self._extract_environmental_impact(markdown_body)
        use_restrictions = self._extract_use_restrictions(markdown_body)

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
            training_data_sources=training_data_sources,
            training_data_description=training_data_description,
            limitations=limitations,
            evaluation_metrics=evaluation_metrics,
            intended_uses=intended_uses,
            out_of_scope_uses=out_of_scope_uses,
            environmental_impact=environmental_impact,
            use_restrictions=use_restrictions,
        )

    def _parse_markdown_format(self, content: str) -> ModelCardInfo | None:
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

        # --- Extract enhanced markdown sections ---
        training_data_sources, training_data_description = (
            self._extract_training_data(content)
        )
        limitations = self._extract_limitations(content)
        evaluation_metrics = self._extract_evaluation_metrics(content)
        intended_uses = self._extract_intended_uses(content)
        out_of_scope_uses = self._extract_out_of_scope_uses(content)
        environmental_impact = self._extract_environmental_impact(content)
        use_restrictions = self._extract_use_restrictions(content)

        return ModelCardInfo(
            license=license_value,
            authors=authors,
            training_data_sources=training_data_sources,
            training_data_description=training_data_description,
            limitations=limitations,
            evaluation_metrics=evaluation_metrics,
            intended_uses=intended_uses,
            out_of_scope_uses=out_of_scope_uses,
            environmental_impact=environmental_impact,
            use_restrictions=use_restrictions,
        )

    def _extract_authors(self, content: str) -> list[str]:
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

    # ------------------------------------------------------------------
    # Enhanced markdown section extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _get_markdown_body(content: str) -> str:
        """Return the markdown content after YAML frontmatter."""
        # Remove YAML frontmatter
        stripped = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, count=1, flags=re.DOTALL)
        return stripped

    # --- Training Data ---------------------------------------------------

    def _extract_training_data(
        self, content: str
    ) -> tuple[list[str], str | None]:
        """Extract training data information from markdown sections.

        Looks for sections like "Training Data", "Training Details",
        "Training Dataset", "Data", and "Dataset".

        Returns:
            Tuple of (training_data_sources, training_data_description).
        """
        section = _extract_section(content, [
            "Training Data",
            "Training Details",
            "Training Dataset",
            "Training",
            "Data",
            "Dataset",
        ])
        if not section:
            return [], None

        description = _strip_markdown(section)

        # Extract dataset names / references mentioned in the text.
        sources: list[str] = []

        # Capture HuggingFace-style dataset references (org/dataset)
        hf_refs = re.findall(
            r'(?:huggingface\.co/datasets/|datasets/)([A-Za-z0-9_-]+/[A-Za-z0-9_.-]+)',
            section,
        )
        sources.extend(hf_refs)

        # Capture markdown links as data sources (URL form)
        link_urls = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', section)
        for _text, url in link_urls:
            sources.append(url)

        # Capture well-known dataset names mentioned explicitly
        # (e.g., "trained on Wikipedia", "BookCorpus", "CommonCrawl")
        known_datasets = [
            "Wikipedia", "BookCorpus", "CommonCrawl", "C4", "The Pile",
            "OpenWebText", "RedPajama", "LAION", "ImageNet", "COCO",
            "SQuAD", "GLUE", "SuperGLUE", "MNLI", "WMT",
        ]
        for ds in known_datasets:
            if re.search(r'\b' + re.escape(ds) + r'\b', section, re.IGNORECASE):
                sources.append(ds)

        # Capture bare URLs
        bare_urls = re.findall(r'https?://[^\s\)>]+', section)
        for url in bare_urls:
            if url not in sources:
                sources.append(url)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_sources: list[str] = []
        for s in sources:
            if s not in seen:
                seen.add(s)
                unique_sources.append(s)

        return unique_sources, description

    # --- Limitations -----------------------------------------------------

    def _extract_limitations(self, content: str) -> str | None:
        """Extract known limitations from markdown sections."""
        section = _extract_section(content, [
            "Known Limitations",
            "Limitations",
            "Limitations and Biases",
            "Limitations and Bias",
            "Risks, Limitations and Biases",
            "Known Issues",
            "Caveats and Recommendations",
        ])
        if section:
            return _strip_markdown(section)
        return None

    # --- Evaluation Results ----------------------------------------------

    def _extract_evaluation_metrics(self, content: str) -> dict[str, Any]:
        """Extract evaluation/benchmark results from markdown sections.

        Parses patterns like ``MMLU: 79.2%``, ``| HellaSwag | 85.1 |``,
        and ``**Accuracy**: 0.93``.
        """
        section = _extract_section(content, [
            "Evaluation Results",
            "Evaluation",
            "Results",
            "Performance",
            "Metrics",
            "Benchmark Results",
            "Benchmarks",
        ])
        if not section:
            return {}

        metrics: dict[str, Any] = {}

        # Pattern 1: "MetricName: value" or "MetricName: value%"
        kv_pattern = re.findall(
            r'(?:^|\n)\s*[-*]?\s*\**([A-Za-z][\w\s/.-]{1,40}?)\**\s*[:=]\s*'
            r'(\d+(?:\.\d+)?%?)',
            section,
        )
        for key, value in kv_pattern:
            key = key.strip().rstrip(':').strip()
            if key:
                metrics[key] = value

        # Pattern 2: markdown table rows "| MetricName | value |"
        table_pattern = re.findall(
            r'\|\s*([A-Za-z][\w\s/.-]{1,40}?)\s*\|\s*(\d+(?:\.\d+)?%?)\s*\|',
            section,
        )
        for key, value in table_pattern:
            key = key.strip()
            # Skip table separator rows (e.g., "---")
            if key and not re.match(r'^[-:]+$', key):
                metrics[key] = value

        return metrics

    # --- Intended Use ----------------------------------------------------

    def _extract_intended_uses(self, content: str) -> str | None:
        """Extract intended uses from markdown sections."""
        section = _extract_section(content, [
            "Intended Use",
            "Intended Uses",
            "Uses",
            "Direct Use",
            "Intended Use Cases",
            "Use Cases",
            "How to Use",
        ])
        if section:
            return _strip_markdown(section)
        return None

    def _extract_out_of_scope_uses(self, content: str) -> str | None:
        """Extract out-of-scope / misuse warnings from markdown sections."""
        section = _extract_section(content, [
            "Out-of-Scope Use",
            "Out-of-Scope Uses",
            "Out of Scope Use",
            "Out of Scope Uses",
            "Misuse",
            "Misuse and Out-of-scope Use",
            "Out-of-Scope Usage",
            "Not Intended Use",
        ])
        if section:
            return _strip_markdown(section)
        return None

    # --- Environmental Impact --------------------------------------------

    def _extract_environmental_impact(
        self, content: str
    ) -> dict[str, str]:
        """Extract environmental impact / carbon footprint information."""
        section = _extract_section(content, [
            "Environmental Impact",
            "Carbon Footprint",
            "Compute Infrastructure",
            "Carbon Emissions",
            "Hardware",
        ])
        if not section:
            return {}

        impact: dict[str, str] = {}

        # Hardware type
        hw_match = re.search(
            r'(?:hardware|gpu|tpu|accelerator)[\s:]*([^\n]{3,80})',
            section, re.IGNORECASE,
        )
        if hw_match:
            impact["hardware"] = _strip_markdown(hw_match.group(1).strip())

        # Training time / hours
        time_match = re.search(
            r'(?:training time|hours|duration|compute)[\s:]*([^\n]{3,80})',
            section, re.IGNORECASE,
        )
        if time_match:
            impact["training_time"] = _strip_markdown(time_match.group(1).strip())

        # Carbon emissions
        carbon_match = re.search(
            r'(?:carbon|co2|emissions?)[\s:]*([^\n]{3,80})',
            section, re.IGNORECASE,
        )
        if carbon_match:
            impact["carbon_emissions"] = _strip_markdown(carbon_match.group(1).strip())

        # Cloud provider / region
        cloud_match = re.search(
            r'(?:cloud provider|region|provider)[\s:]*([^\n]{3,80})',
            section, re.IGNORECASE,
        )
        if cloud_match:
            impact["cloud_provider"] = _strip_markdown(cloud_match.group(1).strip())

        return impact

    # --- Use Restrictions (RAIL / legal) ---------------------------------

    def _extract_use_restrictions(self, content: str) -> list[str]:
        """Extract use restrictions, especially from RAIL-style licenses.

        Looks for explicit restriction language such as "You may not use",
        "restricted from", "not permitted to", etc., as well as dedicated
        restriction sections.
        """
        restrictions: list[str] = []

        # First, check for a dedicated restrictions section
        section = _extract_section(content, [
            "Use Restrictions",
            "Restrictions",
            "Acceptable Use",
            "Usage Restrictions",
            "Terms of Use",
            "License Restrictions",
        ])
        if section:
            # Each bullet or numbered item is a separate restriction
            items = re.findall(r'[-*]\s+(.+)', section)
            if items:
                restrictions.extend([_strip_markdown(item.strip()) for item in items])
            elif section.strip():
                # No bullet list; treat entire section as a single restriction
                restrictions.append(_strip_markdown(section))

        # Second, scan the entire content for RAIL-style restriction phrases
        restriction_patterns = [
            r'(?:you\s+(?:may\s+not|shall\s+not|must\s+not|cannot|are\s+not\s+(?:allowed|permitted)\s+to))\s+(.+?)(?:\.|$)',
            r'(?:restricted\s+from)\s+(.+?)(?:\.|$)',
            r'(?:not\s+(?:permitted|allowed)\s+to)\s+(.+?)(?:\.|$)',
            r'(?:prohibited\s+from)\s+(.+?)(?:\.|$)',
            r'(?:is\s+not\s+(?:intended|designed)\s+for)\s+(.+?)(?:\.|$)',
        ]

        for pattern in restriction_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for m in matches:
                cleaned = _strip_markdown(m.strip())
                if cleaned and cleaned not in restrictions:
                    restrictions.append(cleaned)

        return restrictions


def parse_model_card(path: Path) -> ModelCardInfo | None:
    """
    Convenience function to parse a model card.

    Args:
        path: Path to model card file

    Returns:
        ModelCardInfo or None
    """
    parser = ModelCardParser()
    return parser.parse_file(path)
