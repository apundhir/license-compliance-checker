"""Tests for Ruby/Bundler detector."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from lcc.detection.ruby import RubyDetector
from lcc.models import ComponentType


@pytest.fixture
def detector():
    return RubyDetector()


def test_supports_gemfile(detector, tmp_path):
    """Test detector recognizes Gemfile."""
    (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'\n")
    assert detector.supports(tmp_path)


def test_supports_gemfile_lock(detector, tmp_path):
    """Test detector recognizes Gemfile.lock."""
    (tmp_path / "Gemfile.lock").write_text("GEM\n")
    assert detector.supports(tmp_path)


def test_does_not_support_empty_dir(detector, tmp_path):
    """Test detector rejects directory without Ruby manifests."""
    assert not detector.supports(tmp_path)


def test_parse_gemfile_simple(detector, tmp_path):
    """Test parsing simple Gemfile."""
    gemfile = tmp_path / "Gemfile"
    gemfile.write_text("""
source 'https://rubygems.org'

gem 'rails', '7.0.4'
gem 'pg', '~> 1.4'
gem 'puma'
""")

    components = detector.discover(tmp_path)
    assert len(components) == 3

    # Check rails
    rails = next((c for c in components if c.name == "rails"), None)
    assert rails is not None
    assert rails.type == ComponentType.RUBY
    assert rails.version == "7.0.4"

    # Check pg
    pg = next((c for c in components if c.name == "pg"), None)
    assert pg is not None
    assert pg.version == "*"  # No exact version, only constraint
    assert "~> 1.4" in pg.metadata.get("sources", [{}])[0].get("constraints", [])

    # Check puma
    puma = next((c for c in components if c.name == "puma"), None)
    assert puma is not None
    assert puma.version == "*"


def test_parse_gemfile_lock(detector, tmp_path):
    """Test parsing Gemfile.lock."""
    lockfile = tmp_path / "Gemfile.lock"
    lockfile.write_text("""GEM
  remote: https://rubygems.org/
  specs:
    actioncable (7.0.4)
      actionpack (= 7.0.4)
      activesupport (= 7.0.4)
    actionpack (7.0.4)
      actionview (= 7.0.4)
      activesupport (= 7.0.4)
    rails (7.0.4)
      actioncable (= 7.0.4)
      actionpack (= 7.0.4)

PLATFORMS
  ruby
  x86_64-darwin-21

DEPENDENCIES
  rails (~> 7.0.4)

BUNDLED WITH
   2.3.26
""")

    components = detector.discover(tmp_path)
    assert len(components) >= 3

    # Check actioncable
    actioncable = next((c for c in components if c.name == "actioncable"), None)
    assert actioncable is not None
    assert actioncable.version == "7.0.4"
    assert actioncable.metadata["sources"][0]["locked"] is True

    # Check rails
    rails = next((c for c in components if c.name == "rails"), None)
    assert rails is not None
    assert rails.version == "7.0.4"


def test_parse_gemfile_with_groups(detector, tmp_path):
    """Test parsing Gemfile with groups."""
    gemfile = tmp_path / "Gemfile"
    gemfile.write_text("""
source 'https://rubygems.org'

gem 'rails', '7.0.4'
gem 'rspec', group: :test
gem 'pry', group: :development
gem 'factory_bot', group: [:development, :test]
""")

    components = detector.discover(tmp_path)

    # Check rspec
    rspec = next((c for c in components if c.name == "rspec"), None)
    assert rspec is not None
    assert rspec.metadata["sources"][0].get("group") == "test"

    # Check factory_bot
    factory_bot = next((c for c in components if c.name == "factory_bot"), None)
    assert factory_bot is not None
    assert "development" in factory_bot.metadata["sources"][0].get("groups", [])
    assert "test" in factory_bot.metadata["sources"][0].get("groups", [])


def test_parse_gemfile_with_git(detector, tmp_path):
    """Test parsing Gemfile with git sources."""
    gemfile = tmp_path / "Gemfile"
    gemfile.write_text("""
source 'https://rubygems.org'

gem 'rails', git: 'https://github.com/rails/rails.git', branch: 'main'
gem 'my_gem', git: 'https://github.com/user/my_gem.git', tag: 'v1.0.0'
""")

    components = detector.discover(tmp_path)

    # Check rails
    rails = next((c for c in components if c.name == "rails"), None)
    assert rails is not None
    assert rails.metadata["sources"][0].get("git") == "https://github.com/rails/rails.git"
    assert rails.metadata["sources"][0].get("branch") == "main"

    # Check my_gem
    my_gem = next((c for c in components if c.name == "my_gem"), None)
    assert my_gem is not None
    assert my_gem.metadata["sources"][0].get("tag") == "v1.0.0"


def test_parse_gemfile_with_require_false(detector, tmp_path):
    """Test parsing Gemfile with require: false."""
    gemfile = tmp_path / "Gemfile"
    gemfile.write_text("""
source 'https://rubygems.org'

gem 'bootsnap', require: false
""")

    components = detector.discover(tmp_path)

    bootsnap = next((c for c in components if c.name == "bootsnap"), None)
    assert bootsnap is not None
    assert bootsnap.metadata["sources"][0].get("require") is False


def test_gemfile_and_lockfile_merge(detector, tmp_path):
    """Test that Gemfile and Gemfile.lock data is merged."""
    gemfile = tmp_path / "Gemfile"
    gemfile.write_text("""
source 'https://rubygems.org'

gem 'rails', '~> 7.0'
""")

    lockfile = tmp_path / "Gemfile.lock"
    lockfile.write_text("""GEM
  remote: https://rubygems.org/
  specs:
    rails (7.0.4)

DEPENDENCIES
  rails (~> 7.0)
""")

    components = detector.discover(tmp_path)

    # Should have one rails component with merged data
    rails_components = [c for c in components if c.name == "rails"]
    assert len(rails_components) == 1

    rails = rails_components[0]
    assert rails.version == "7.0.4"  # From lockfile

    # Should have two sources
    assert len(rails.metadata["sources"]) == 2
    sources = [s["source"] for s in rails.metadata["sources"]]
    assert "Gemfile.lock" in sources
    assert "Gemfile" in sources
