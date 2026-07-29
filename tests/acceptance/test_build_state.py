"""Test the DishManager buildState attribute."""

import json

import pytest
import tango


@pytest.mark.acceptance
def test_build_state(
    dish_manager_proxy: tango.DeviceProxy,
):
    """Check that the build state is valid."""
    build_state_json_str = dish_manager_proxy.buildState
    build_state = json.loads(build_state_json_str)

    assert build_state["last_updated"]
    assert build_state["spfrx_device"]["version"] == (
        "serialNumbers - ('SPFRx:1234', 'SPFRx:2345', 'SPFRx:3456'); swVersions -"
        " ('SPFRx:5.11.0', 'SPFRx:5678', 'SPFRx:6789'); fwVersions - "
        "('SPFRx:7890', 'SPFRx:8901', 'SPFRx:9012')"
    )
    assert build_state["spfc_device"]["version"] == (
        "serialNumbers - ('SPFC:1234', 'SPFC:2345', 'SPFC:3456'); swVersions - "
        "('SPFC:5.11.0', 'SPFC:5678', 'SPFC:6789'); fwVersions - ('SPFC:7890',"
        " 'SPFC:8901', 'SPFC:9012')"
    )
