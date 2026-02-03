"""
Detection subsystem interfaces.
"""

from __future__ import annotations

import abc
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, Sequence

from lcc.models import Component

if TYPE_CHECKING:
    from lcc.config import LCCConfig


class DetectorError(RuntimeError):
    """Raised when a detector encounters an unrecoverable error."""


class Detector(abc.ABC):
    """
    Base class for language-specific detectors.
    """

    name: str
    config: Optional["LCCConfig"]

    def __init__(self, name: str) -> None:
        self.name = name
        self.config = None

    def set_config(self, config: "LCCConfig") -> None:
        """Set the configuration for this detector."""
        self.config = config

    def _is_excluded(self, path: Path, project_root: Path) -> bool:
        """Check if a path should be excluded based on config patterns."""
        if not self.config or not self.config.exclude_patterns:
            return False
        try:
            rel_path = path.relative_to(project_root)
        except ValueError:
            return False
        for pattern in self.config.exclude_patterns:
            # Check if any part of the path matches the pattern
            if rel_path.match(pattern):
                return True
            # Also check if any parent directory matches
            for parent in rel_path.parents:
                if parent.match(pattern):
                    return True
        return False

    @abc.abstractmethod
    def supports(self, project_root: Path) -> bool:
        """
        Return True if the detector can operate on the project root.
        """

    @abc.abstractmethod
    def discover(self, project_root: Path) -> Sequence[Component]:
        """
        Discover components managed by the ecosystem.
        """


DetectorCollection = Iterable[Detector]

