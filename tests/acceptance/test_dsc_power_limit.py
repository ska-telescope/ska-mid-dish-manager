# pylint: disable=too-many-locals

"""Test dscPowerLimtkW Attribute"""
from typing import Any

import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.forked
def test_initial_power_limit(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Tests the dscPowerLimitkW attribute inital value on DS and Dish Manager"""
    initial_value = 10.0
    assert (
        ds_device_proxy.read_attribute("dscPowerLimitkW").value
        == dish_manager_proxy.read_attribute("dscPowerLimitkW").value
        == initial_value
    )


@pytest.mark.acceptance
@pytest.mark.forked
def test_correct_power_limit_change(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Tests the setting of the dscPowerLimitkW attribute (correct)"""
    limit = 12.4
    dm_attribute_event_store = event_store_class()
    ds_attribute_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "dscPowerLimitkW", tango.EventType.CHANGE_EVENT, dm_attribute_event_store
    )
    ds_device_proxy.subscribe_event(
        "dscPowerLimitkW", tango.EventType.CHANGE_EVENT, ds_attribute_event_store
    )
    for proxy in [ds_device_proxy, dish_manager_proxy]:
        proxy.write_attribute("dscPowerLimitkW", limit)
        ds_attribute_event_store.wait_for_value(limit)
        dm_attribute_event_store.wait_for_value(limit)
        limit = 14.3


@pytest.mark.acceptance
@pytest.mark.forked
def test_incorrect_power_limit_change(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Tests the setting of the dscPowerLimitkW attribute (incorrect)"""
    limit = 0.8
    for proxy in [ds_device_proxy, dish_manager_proxy]:
        with pytest.raises(tango.DevFailed):
            proxy.write_attribute("dscPowerLimitkW", limit)  # This should raise ValueError
            ds_value = ds_device_proxy.read_attribute("dscPowerLimitkW").value
            dish_value = dish_manager_proxy.read_attribute("dscPowerLimitkW").value
            assert (
                ds_value == dish_value == 14.3
            ), f"Mismatch: ds_value={ds_value}, dish_value={dish_value}"
            limit = 0.9


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    ("parameter", "allowed"),
    [
        ([1.0, 15.0], True),
        ([0.0, 14.0], True),
        ([1.0, 38.0], False),
        ([0.0, 99.0], False),
    ],
)
def test_power_limit_change_set_power_mode(
    parameter: list[float],
    allowed: bool,
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Tests the limits of the attribute dscPowerLimitkW through the SetPowerMode"""
    ds_attribute_event_store = event_store_class()
    dm_attribute_event_store = event_store_class()

    ds_device_proxy.subscribe_event(
        "dscPowerLimitkW", tango.EventType.CHANGE_EVENT, ds_attribute_event_store
    )

    dish_manager_proxy.subscribe_event(
        "dscPowerLimitkW", tango.EventType.CHANGE_EVENT, dm_attribute_event_store
    )

    ds_device_proxy.SetPowerMode(parameter)
    if allowed:
        ds_attribute_event_store.wait_for_value(parameter[1], timeout=6)
        dm_attribute_event_store.wait_for_value(parameter[1], timeout=6)
    else:
        ds_attribute_event_store.wait_for_value(14.0, timeout=6)
        dm_attribute_event_store.wait_for_value(14.0, timeout=6)


@pytest.mark.acceptance
@pytest.mark.parametrize(
    ("full_power", "expected_progress"),
    [
        (True, "Full Power Mode called using DSC Power Limit: 14.0kW"),
        (False, "Low Power Mode called using DSC Power Limit: 14.0kW"),
    ],
)
def test_fp_lp_power_limit_used(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    full_power: bool,
    expected_progress: str,
    event_store_class: Any,
):
    """Test the dscPowerLimitkW value used when invoking commands (FP and LP)."""
    progress_event_store = event_store_class()
    ds_device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )
    if full_power:
        ds_device_proxy.SetStandbyFPMode()
    else:
        ds_device_proxy.SetStandbyLPMode()
    progress_event_store.wait_for_progress_update(expected_progress, timeout=6)


@pytest.mark.acceptance
def test_dsc_current_limit_used(
    ds_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
):
    """Test the dscPowerLimitkW value used when invoking Slew."""
    progress_event_store = event_store_class()
    ds_device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )
    ds_device_proxy.Slew([80.0, 90.0])
    progress_event_store.wait_for_progress_update(
        (
            "Slew called with Azimuth speed: 3.0 deg/s, Elevation speed: 1.0 deg/s "
            "and DSC Power Limit: 14.0kW"
        ),
        timeout=6,
    )
