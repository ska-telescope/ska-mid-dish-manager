"""General chart tests."""

import ast
from pathlib import Path

import pytest
import yaml


@pytest.mark.unit
def test_chart_versions():
    """General chart tests."""
    test_path = Path(__file__)
    charts_path = test_path.parent.parent.parent / "charts" / "ska-mid-dish-manager"
    chart_definitiion_path = charts_path / "Chart.yaml"
    values_path = charts_path / "values.yaml"
    docs_conf_path = test_path.parent.parent.parent / "docs" / "src" / "conf.py"
    release_file = test_path.parent.parent.parent / ".release"
    pyproject_file = test_path.parent.parent.parent / "pyproject.toml"

    # Python files
    docs_version = ""
    with open(docs_conf_path.as_posix(), "r") as f:
        source_code = f.read()
    docs_conf_tree = ast.parse(source_code)
    for node in docs_conf_tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.targets[0], ast.Name):
            continue
        if node.targets[0].id != "release":
            continue
        docs_version = node.value.value

    # YAML files
    chart_def_yaml = ""
    values_yaml = ""
    with open(chart_definitiion_path, "r") as f:
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

    if "rc" not in chart_version:
        # docs rc version can be 9.2.1rc1 and chart version 9.2.1-rc.1
        assert docs_version == chart_version, (
            f"Docs version {docs_version} must match chart version {chart_version}."
        )

    # Very rough checks in toml and .release files
    with open(release_file, "r") as f:
        for line in f:
            if line:
                _, version = line.split("=")
                assert version.strip() == chart_version, (
                    f"`.release` version does not match chart version {chart_version}"
                )

    if "rc" not in chart_version:
        # pyproject toml rc version can be 9.2.1rc1 and chart version 9.2.1-rc.1
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
