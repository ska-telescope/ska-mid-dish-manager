"""General chart tests."""

# mypy: disable-error-code="union-attr,arg-type"
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml


@pytest.mark.unit
def test_chart_versions() -> None:
    """General chart tests."""
    test_path = Path(__file__)
    charts_path = test_path.parent.parent.parent / "charts" / "ska-mid-dish-manager"
    chart_definition_path = charts_path / "Chart.yaml"
    values_path = charts_path / "values.yaml"
    docs_conf_path = test_path.parent.parent.parent / "docs" / "src" / "conf.py"
    release_file = test_path.parent.parent.parent / ".release"
    pyproject_file = test_path.parent.parent.parent / "pyproject.toml"

    # Python files
    spec = importlib.util.spec_from_file_location("docs", docs_conf_path.as_posix())
    docsmod = importlib.util.module_from_spec(spec)
    sys.modules["docs"] = docsmod
    spec.loader.exec_module(docsmod)

    # YAML files
    chart_def_yaml = ""
    values_yaml = ""
    with open(chart_definition_path, "r") as f:
        chart_def_yaml = yaml.safe_load(f)
    with open(values_path, "r") as f:
        values_yaml = yaml.safe_load(f)

    chart_version = chart_def_yaml["version"]
    chart_app_version = chart_def_yaml["appVersion"]
    image_tag_version = values_yaml["dishmanager"]["image"]["tag"]

    assert chart_version == chart_app_version == image_tag_version, (
        f"Chart version {chart_version}, appVersion {chart_app_version} and image"
        f" tag {image_tag_version}, must be the same."
    )

    assert docsmod.release == chart_version, (
        f"Docs version {docsmod.release} must match chart version {chart_version}."
    )

    # Very rough checks in toml and .release files
    with open(release_file, "r") as f:
        for line in f:
            if line:
                _, version = line.split("=")
                assert version.strip() == chart_version, (
                    f"`.release` version does not match chart version {chart_version}"
                )

    with open(pyproject_file, "r") as f:
        for line in f:
            if line.startswith("version"):
                assert chart_version in line, (
                    "The version line in pyproject.toml does "
                    f"not match chart version {chart_version}"
                )
                break
        else:
            assert False, "No version line found in pyproject.toml"
