# Contributing to License Compliance Checker

Thank you for your interest in contributing to LCC! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Testing](#testing)
6. [Submitting Changes](#submitting-changes)
7. [Code Standards](#code-standards)
8. [Documentation](#documentation)
9. [Community](#community)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, background, or identity.

### Expected Behavior

- Be respectful and considerate
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Assume good intentions
- Respect differing viewpoints and experiences

### Unacceptable Behavior

- Harassment, discrimination, or hostile behavior
- Personal attacks or trolling
- Publishing private information without consent
- Any conduct that would be inappropriate in a professional setting

### Reporting

If you experience or witness unacceptable behavior, please report it to support@lcc.dev. All reports will be handled confidentially.

---

## Getting Started

### Ways to Contribute

There are many ways to contribute to LCC:

1. **Report Bugs**: Found a bug? [Open an issue](https://github.com/your-org/lcc/issues/new)
2. **Suggest Features**: Have an idea? [Start a discussion](https://github.com/your-org/lcc/discussions)
3. **Improve Documentation**: Fix typos, clarify instructions, add examples
4. **Write Code**: Fix bugs, implement features, add tests
5. **Review Pull Requests**: Provide feedback on open PRs
6. **Help Others**: Answer questions in issues and discussions
7. **Add Detectors**: Support new languages or package managers
8. **Add Resolvers**: Add new license data sources

### Good First Issues

Look for issues labeled [`good-first-issue`](https://github.com/your-org/lcc/labels/good-first-issue) - these are suitable for newcomers.

### Finding Something to Work On

1. Check [open issues](https://github.com/your-org/lcc/issues)
2. Look at [the roadmap](https://github.com/your-org/lcc/projects)
3. Browse [discussions](https://github.com/your-org/lcc/discussions)
4. Read [documentation](https://docs.lcc.dev) and identify gaps

Before starting work on a significant change, please comment on the issue or create a discussion to coordinate with maintainers.

---

## Development Setup

### Prerequisites

- **Python 3.9+** (3.11 recommended)
- **Node.js 18+** (for dashboard)
- **Docker and Docker Compose** (optional, for full stack)
- **Git**

### Clone the Repository

```bash
git clone https://github.com/your-org/lcc.git
cd lcc
```

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (development mode)
pip install -e ".[dev]"

# Or with all optional dependencies
pip install -e ".[dev,ai,all]"

# Install pre-commit hooks
pre-commit install

# Verify installation
lcc --version
```

### Dashboard Setup

```bash
# Navigate to dashboard directory
cd dashboard

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Start development server
npm run dev

# Dashboard available at http://localhost:3000
```

### Database Setup

```bash
# Database is created automatically on first run
lcc server

# Or manually
python -c "from lcc.api.repository import ScanRepository; ScanRepository('~/.lcc/lcc.db')"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/lcc --cov-report=html

# Run specific test file
pytest tests/detection/test_npm.py

# Run with verbose output
pytest -v

# Run fast tests only (skip slow integration tests)
pytest -m "not slow"
```

---

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-dotnet-detector` - New features
- `fix/github-rate-limit-handling` - Bug fixes
- `docs/update-api-guide` - Documentation changes
- `refactor/scanner-architecture` - Code refactoring
- `test/add-policy-tests` - Test additions

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting, missing semicolons, etc. (no code change)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, CI, etc.)

**Examples**:
```bash
feat(detection): add .NET project detector

fix(resolver): handle GitHub rate limit retry-after header

docs(policy): clarify dual-license preference behavior

test(scanner): add integration tests for GitHub scanning

chore(deps): upgrade fastapi to 0.104.0
```

### Code Style

**Python**:
- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://black.readthedocs.io/) for formatting (max line length 100)
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use [mypy](http://mypy-lang.org/) for type checking
- Use [ruff](https://docs.astral.sh/ruff/) for linting

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

**JavaScript/TypeScript**:
- Follow [Airbnb Style Guide](https://github.com/airbnb/javascript)
- Use [Prettier](https://prettier.io/) for formatting
- Use [ESLint](https://eslint.org/) for linting

```bash
cd dashboard/

# Format code
npm run format

# Lint
npm run lint

# Type check
npm run type-check
```

### Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to ensure code quality:

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

Hooks include:
- Black formatting
- isort import sorting
- ruff linting
- mypy type checking
- Trailing whitespace removal
- YAML validation

---

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific directory
pytest tests/detection/

# Specific file
pytest tests/detection/test_npm.py

# Specific test
pytest tests/detection/test_npm.py::test_npm_detector_finds_package_json

# With coverage
pytest --cov=src/lcc --cov-report=html
# View coverage: open htmlcov/index.html
```

### Writing Tests

**Test file structure**:
```python
# tests/detection/test_my_detector.py
import pytest
from pathlib import Path
from lcc.detection.my_detector import MyDetector

class TestMyDetector:
    """Tests for MyDetector."""

    def test_detects_manifest_file(self, tmp_path):
        """Test that detector finds manifest file."""
        # Arrange
        manifest = tmp_path / "my.manifest"
        manifest.write_text("package: my-package\nversion: 1.0.0")
        detector = MyDetector()

        # Act
        components = detector.detect(tmp_path)

        # Assert
        assert len(components) == 1
        assert components[0].name == "my-package"
        assert components[0].version == "1.0.0"

    def test_handles_missing_file(self, tmp_path):
        """Test that detector handles missing manifest gracefully."""
        detector = MyDetector()
        components = detector.detect(tmp_path)
        assert len(components) == 0

    @pytest.mark.slow
    def test_integration_with_real_repo(self):
        """Integration test with real repository."""
        # ... integration test code ...
```

**Test fixtures**:
```python
# conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project structure."""
    project = tmp_path / "project"
    project.mkdir()

    (project / "package.json").write_text('{"name": "test", "version": "1.0.0"}')
    (project / "LICENSE").write_text("MIT License...")

    return project
```

### Test Categories

Mark tests with categories:

```python
import pytest

@pytest.mark.unit
def test_unit():
    """Fast unit test."""
    pass

@pytest.mark.integration
def test_integration():
    """Integration test with external dependencies."""
    pass

@pytest.mark.slow
def test_slow():
    """Slow test (> 1 second)."""
    pass
```

Run specific categories:
```bash
pytest -m "unit"  # Only unit tests
pytest -m "not slow"  # Skip slow tests
```

### Coverage Requirements

- **Minimum coverage**: 80% for new code
- **Goal coverage**: 90%+
- All new features must include tests
- Bug fixes should include regression tests

---

## Submitting Changes

### Pull Request Process

1. **Fork the repository** (if you don't have write access)

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/my-new-feature
   ```

3. **Make your changes**:
   - Write code
   - Add tests
   - Update documentation

4. **Run tests locally**:
   ```bash
   pytest
   black src/ tests/
   ruff check src/ tests/
   mypy src/
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

6. **Push to your fork**:
   ```bash
   git push origin feature/my-new-feature
   ```

7. **Create a Pull Request**:
   - Go to https://github.com/your-org/lcc/pulls
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template
   - Submit!

### Pull Request Guidelines

**Good PR**:
- ✅ Single, focused change
- ✅ Clear description of what and why
- ✅ Tests included
- ✅ Documentation updated
- ✅ Passes CI checks
- ✅ Follows code style
- ✅ Small enough to review (< 500 lines preferred)

**Avoid**:
- ❌ Multiple unrelated changes
- ❌ No tests or documentation
- ❌ Breaking changes without discussion
- ❌ Massive PRs (> 1000 lines)

### PR Description Template

```markdown
## Description
Brief description of the change and why it's needed.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issues
Fixes #123, Related to #456

## How Has This Been Tested?
Describe the tests you ran to verify your changes.

## Checklist
- [ ] My code follows the code style of this project
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] I have updated the documentation accordingly
- [ ] All new and existing tests pass
```

### Review Process

1. **Automated checks**: CI must pass (tests, linting, type checking)
2. **Code review**: At least one maintainer must approve
3. **Testing**: Reviewer may test manually
4. **Feedback**: Address review comments and push updates
5. **Merge**: Maintainer will merge once approved

**Review timeline**:
- Small PRs: 1-3 days
- Medium PRs: 3-7 days
- Large PRs: 1-2 weeks

---

## Code Standards

### Adding a New Detector

To support a new language or package manager:

1. **Create detector class**:
   ```python
   # src/lcc/detection/my_detector.py
   from lcc.detection.base import Detector
   from lcc.models import Component

   class MyDetector(Detector):
       """Detector for MyLanguage package manager."""

       def detect(self, root_path):
           """Detect components in the project."""
           components = []

           # Look for manifest file
           manifest = root_path / "my.manifest"
           if not manifest.exists():
               return components

           # Parse manifest
           data = self._parse_manifest(manifest)

           # Create components
           for dep in data.get("dependencies", []):
               components.append(Component(
                   name=dep["name"],
                   version=dep["version"],
                   type="my-package-manager",
                   metadata={"source": str(manifest)}
               ))

           return components

       def _parse_manifest(self, manifest_path):
           """Parse the manifest file."""
           # Implementation...
   ```

2. **Register in factory**:
   ```python
   # src/lcc/factory.py
   from lcc.detection.my_detector import MyDetector

   def build_detectors():
       return [
           # ... existing detectors ...
           MyDetector(),
       ]
   ```

3. **Add tests**:
   ```python
   # tests/detection/test_my_detector.py
   def test_my_detector():
       # ...
   ```

4. **Update documentation**:
   - Add to supported languages in README.md
   - Add example in USER_GUIDE.md

### Adding a New Resolver

To add a new license data source:

1. **Create resolver class**:
   ```python
   # src/lcc/resolution/my_resolver.py
   from lcc.resolution.base import Resolver

   class MyResolver(Resolver):
       """Resolver using MyService API."""

       def resolve(self, component):
           """Resolve license for component."""
           try:
               # Query API
               response = self._query_api(component.name, component.version)

               # Extract license
               if response and "license" in response:
                   return response["license"]

           except Exception as e:
               logger.debug(f"MyResolver failed for {component.name}: {e}")

           return None

       def _query_api(self, name, version):
           """Query the API."""
           # Implementation...
   ```

2. **Register in factory**:
   ```python
   # src/lcc/factory.py
   from lcc.resolution.my_resolver import MyResolver

   def build_resolvers(config, cache):
       return [
           RegistryResolver(cache),
           MyResolver(),  # Add in appropriate priority order
           ClearlyDefinedResolver(cache),
           # ...
       ]
   ```

3. **Add tests**:
   ```python
   # tests/resolution/test_my_resolver.py
   def test_my_resolver():
       # ...
   ```

---

## Documentation

### Documentation Standards

- **Clear and concise**: Avoid jargon, explain concepts
- **Examples**: Include code examples and CLI commands
- **Up-to-date**: Update docs with code changes
- **Complete**: Cover all features and edge cases

### Where to Document

- **README.md**: Overview, quick start, links
- **docs/USER_GUIDE.md**: Complete CLI usage
- **docs/API_GUIDE.md**: REST API reference
- **docs/POLICY_GUIDE.md**: Policy creation and management
- **Docstrings**: All public functions and classes
- **Code comments**: Complex logic and algorithms

### Docstring Format

Follow [Google Style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings):

```python
def resolve_license(component: Component, resolvers: List[Resolver]) -> str | None:
    """Resolve license for a component using multiple resolvers.

    Tries each resolver in order until one successfully resolves the license.
    Returns None if all resolvers fail.

    Args:
        component: Component to resolve license for
        resolvers: List of resolvers to try, in priority order

    Returns:
        SPDX license identifier, or None if resolution fails

    Raises:
        ValueError: If resolvers list is empty

    Example:
        >>> component = Component(name="requests", version="2.31.0", type="pypi")
        >>> resolvers = [PyPIResolver(), GitHubResolver()]
        >>> license = resolve_license(component, resolvers)
        >>> print(license)
        'Apache-2.0'
    """
    if not resolvers:
        raise ValueError("At least one resolver is required")

    for resolver in resolvers:
        license = resolver.resolve(component)
        if license:
            return license

    return None
```

---

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Q&A, ideas, general discussion
- **Email**: support@lcc.dev for private inquiries

### Getting Help

If you need help:

1. Check [documentation](https://docs.lcc.dev)
2. Search [existing issues](https://github.com/your-org/lcc/issues)
3. Ask in [discussions](https://github.com/your-org/lcc/discussions)
4. Email support@lcc.dev

### Recognition

Contributors are recognized in:
- [CONTRIBUTORS.md](CONTRIBUTORS.md) - All contributors
- Release notes - Feature/fix authors
- GitHub contributors page

---

## Thank You!

Thank you for contributing to License Compliance Checker! Every contribution, no matter how small, helps make LCC better for everyone.

Questions? Email support@lcc.dev or open a [discussion](https://github.com/your-org/lcc/discussions).

---

*This contributing guide is inspired by [Contributing to Open Source](https://github.com/darcyclarke/contributing-to-open-source) and adapted for LCC.*
