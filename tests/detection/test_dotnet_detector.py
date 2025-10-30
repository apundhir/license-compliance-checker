"""Tests for .NET/NuGet detector."""

from pathlib import Path

import pytest

from lcc.detection.dotnet import DotNetDetector
from lcc.models import ComponentType


@pytest.fixture
def detector():
    return DotNetDetector()


def test_supports_packages_config(detector, tmp_path):
    """Test detector recognizes packages.config."""
    (tmp_path / "packages.config").write_text('<?xml version="1.0"?><packages></packages>')
    assert detector.supports(tmp_path)


def test_supports_csproj(detector, tmp_path):
    """Test detector recognizes .csproj files."""
    (tmp_path / "MyProject.csproj").write_text('<Project></Project>')
    assert detector.supports(tmp_path)


def test_supports_fsproj(detector, tmp_path):
    """Test detector recognizes .fsproj files."""
    (tmp_path / "MyProject.fsproj").write_text('<Project></Project>')
    assert detector.supports(tmp_path)


def test_supports_project_json(detector, tmp_path):
    """Test detector recognizes project.json."""
    (tmp_path / "project.json").write_text('{"dependencies":{}}')
    assert detector.supports(tmp_path)


def test_supports_paket(detector, tmp_path):
    """Test detector recognizes paket.dependencies."""
    (tmp_path / "paket.dependencies").write_text('source https://api.nuget.org/v3/index.json\n')
    assert detector.supports(tmp_path)


def test_does_not_support_empty_dir(detector, tmp_path):
    """Test detector rejects directory without .NET manifests."""
    assert not detector.supports(tmp_path)


def test_parse_packages_config(detector, tmp_path):
    """Test parsing packages.config."""
    packages_config = tmp_path / "packages.config"
    packages_config.write_text("""<?xml version="1.0" encoding="utf-8"?>
<packages>
  <package id="Newtonsoft.Json" version="13.0.1" targetFramework="net472" />
  <package id="Serilog" version="2.10.0" targetFramework="net472" />
  <package id="AutoMapper" version="10.1.1" targetFramework="net472" />
</packages>
""")

    components = detector.discover(tmp_path)
    assert len(components) == 3

    # Check Newtonsoft.Json
    newtonsoft = next((c for c in components if c.name == "Newtonsoft.Json"), None)
    assert newtonsoft is not None
    assert newtonsoft.type == ComponentType.DOTNET
    assert newtonsoft.version == "13.0.1"
    assert newtonsoft.metadata["sources"][0].get("targetFramework") == "net472"


def test_parse_csproj_package_reference(detector, tmp_path):
    """Test parsing .csproj with PackageReference."""
    csproj = tmp_path / "MyApp.csproj"
    csproj.write_text("""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
    <PackageReference Include="Serilog" Version="2.10.0" PrivateAssets="all" />
    <PackageReference Include="Microsoft.Extensions.Logging" Version="6.0.0" />
  </ItemGroup>
</Project>
""")

    components = detector.discover(tmp_path)
    assert len(components) == 3

    # Check Serilog with PrivateAssets
    serilog = next((c for c in components if c.name == "Serilog"), None)
    assert serilog is not None
    assert serilog.version == "2.10.0"
    assert serilog.metadata["sources"][0].get("privateAssets") == "all"


def test_parse_project_json(detector, tmp_path):
    """Test parsing project.json (legacy .NET Core)."""
    project_json = tmp_path / "project.json"
    project_json.write_text("""{
  "version": "1.0.0-*",
  "dependencies": {
    "Microsoft.NETCore.App": {
      "version": "1.0.0",
      "type": "platform"
    },
    "Newtonsoft.Json": "9.0.1",
    "Serilog": "2.3.0"
  },
  "frameworks": {
    "netcoreapp1.0": {
      "imports": "dnxcore50"
    }
  }
}
""")

    components = detector.discover(tmp_path)
    assert len(components) == 3

    # Check Microsoft.NETCore.App with type
    netcore = next((c for c in components if c.name == "Microsoft.NETCore.App"), None)
    assert netcore is not None
    assert netcore.version == "1.0.0"
    assert netcore.metadata["sources"][0].get("type") == "platform"

    # Check simple version string
    newtonsoft = next((c for c in components if c.name == "Newtonsoft.Json"), None)
    assert newtonsoft is not None
    assert newtonsoft.version == "9.0.1"


def test_parse_paket_dependencies(detector, tmp_path):
    """Test parsing paket.dependencies."""
    paket = tmp_path / "paket.dependencies"
    paket.write_text("""source https://api.nuget.org/v3/index.json

framework: net472, netstandard2.0

nuget FSharp.Core >= 4.7.2
nuget Newtonsoft.Json ~> 13.0
nuget Serilog 2.10.0
nuget AutoMapper
""")

    components = detector.discover(tmp_path)
    assert len(components) == 4

    # Check FSharp.Core with constraint
    fsharp = next((c for c in components if c.name == "FSharp.Core"), None)
    assert fsharp is not None
    assert fsharp.metadata["sources"][0].get("constraint") == ">= 4.7.2"

    # Check Serilog with exact version
    serilog = next((c for c in components if c.name == "Serilog"), None)
    assert serilog is not None
    assert serilog.version == "2.10.0"

    # Check AutoMapper without version
    automapper = next((c for c in components if c.name == "AutoMapper"), None)
    assert automapper is not None
    assert automapper.version == "*"


def test_multiple_project_files(detector, tmp_path):
    """Test discovering packages from multiple .csproj files."""
    # Create first project
    (tmp_path / "Project1.csproj").write_text("""<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
  </ItemGroup>
</Project>
""")

    # Create second project
    (tmp_path / "Project2.csproj").write_text("""<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Serilog" Version="2.10.0" />
  </ItemGroup>
</Project>
""")

    components = detector.discover(tmp_path)
    assert len(components) == 2

    component_names = {c.name for c in components}
    assert "Newtonsoft.Json" in component_names
    assert "Serilog" in component_names


def test_merge_from_multiple_sources(detector, tmp_path):
    """Test that packages from multiple sources are merged."""
    # packages.config with version
    (tmp_path / "packages.config").write_text("""<?xml version="1.0"?>
<packages>
  <package id="Newtonsoft.Json" version="13.0.1" targetFramework="net472" />
</packages>
""")

    # .csproj with same package
    (tmp_path / "MyApp.csproj").write_text("""<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
  </ItemGroup>
</Project>
""")

    components = detector.discover(tmp_path)

    # Should merge into one component
    newtonsoft_components = [c for c in components if c.name == "Newtonsoft.Json"]
    assert len(newtonsoft_components) == 1

    newtonsoft = newtonsoft_components[0]
    assert newtonsoft.version == "13.0.1"

    # Should have two sources
    assert len(newtonsoft.metadata["sources"]) == 2
    sources = [s["source"] for s in newtonsoft.metadata["sources"]]
    assert "packages.config" in sources
    assert "MyApp.csproj" in sources


def test_fsproj_and_vbproj_support(detector, tmp_path):
    """Test support for F# and VB.NET projects."""
    # F# project
    (tmp_path / "MyLib.fsproj").write_text("""<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="FSharp.Core" Version="6.0.0" />
  </ItemGroup>
</Project>
""")

    # VB.NET project
    (tmp_path / "MyVBApp.vbproj").write_text("""<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Microsoft.VisualBasic" Version="10.3.0" />
  </ItemGroup>
</Project>
""")

    components = detector.discover(tmp_path)
    assert len(components) == 2

    component_names = {c.name for c in components}
    assert "FSharp.Core" in component_names
    assert "Microsoft.VisualBasic" in component_names
