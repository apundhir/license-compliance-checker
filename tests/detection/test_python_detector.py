from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from lcc.detection.python import PythonDetector


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class PythonDetectorTests(unittest.TestCase):
    def test_collects_from_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            _write_file(
                tmp_path / "requirements.txt",
                "\n".join(
                    [
                        "requests==2.31.0",
                        "tensorflow>=2.0; python_version>'3.8'",
                        "Django",
                    ]
                ),
            )
            _write_file(
                tmp_path / "setup.py",
                "from setuptools import setup\n"
                "setup(name='sample', version='0.1.0', install_requires=['pydantic==1.10.8'], extras_require={'dev': ['pytest']})\n",
            )
            _write_file(
                tmp_path / "pyproject.toml",
                """
[project]
dependencies = [
  "uvicorn>=0.20.0",
]
[project.optional-dependencies]
test = ["pytest>=7.0"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
redis = { version = "^4.5.0", extras = ["hiredis"], markers = "platform_system != 'Windows'", license = "BSD-3-Clause" }
[tool.poetry.dev-dependencies]
black = "^23.0"
[tool.poetry.group.docs.dependencies]
mkdocs = "^1.5"
                """,
            )
            _write_file(
                tmp_path / "Pipfile",
                """
[packages]
django = "==4.2.0"

[dev-packages]
pytest = "*"
                """,
            )
            _write_file(
                tmp_path / "poetry.lock",
                """
[[package]]
name = "pendulum"
version = "2.1.2"
license = "MIT"
category = "main"

[[package]]
name = "python-dateutil"
version = "2.8.2"
category = "main"
                """,
            )
            _write_file(
                tmp_path / "environment.yml",
                """
name: sample
dependencies:
  - python=3.11
  - numpy=1.26.0
  - pip:
    - rich==13.7.0
                """,
            )

            dist_info = tmp_path / "samplepkg-0.1.dist-info"
            dist_info.mkdir()
            _write_file(
                dist_info / "METADATA",
                "Name: samplepkg\nVersion: 0.1\nLicense-Expression: MIT OR Apache-2.0\nClassifier: License :: OSI Approved :: MIT License\n",
            )

            wheel_path = tmp_path / "example_pkg-1.0.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel_path, "w") as archive:
                archive.writestr(
                    "example_pkg-1.0.0.dist-info/METADATA",
                    "Name: example-pkg\nVersion: 1.0.0\nLicense: Apache-2.0\n",
                )

            detector = PythonDetector()
            components = detector.discover(tmp_path)
            by_name = {component.name: component for component in components}

            self.assertIn("requests", by_name)
            self.assertTrue(
                any(source["source"] == "requirements.txt" for source in by_name["requests"].metadata["sources"])
            )

            self.assertIn("pendulum", by_name)
            self.assertEqual(by_name["pendulum"].metadata["sources"][0]["source"], "poetry.lock")
            self.assertEqual(by_name["pendulum"].metadata["sources"][0]["license"], "MIT")

            # NOTE: .dist-info and .whl scanning is intentionally disabled in
            # _parse_local_metadata to avoid picking up installed packages
            # during source-repo scans.  The assertions for samplepkg and
            # example-pkg have been removed to match this behaviour.

            rich = by_name["rich"]
            self.assertEqual(rich.metadata["sources"][0]["section"], "environment.yml[pip]")


if __name__ == "__main__":
    unittest.main()
