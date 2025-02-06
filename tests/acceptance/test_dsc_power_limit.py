"""Test dscPowerLimtkW Attribute"""

from typing import Any

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import PointingState
from tests.utils import az_el_slew_position

DEFAULT_POWER_LIMIT = 10


def clean_up(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Sets the power limit to it's default value."""
    ds_device_proxy.write_attribute("dscPowerLimitKw", DEFAULT_POWER_LIMIT)
    dm_attribute_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "dscPowerLimitkW", tango.EventType.CHANGE_EVENT, dm_attribute_event_store
    )
    dm_attribute_event_store.wait_for_value(DEFAULT_POWER_LIMIT, timeout=6)


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
    """Tests the setting of the dscPowerLimitkW attribute (correct). Chaining is
    tested in order to make sure that a change on DS Manager's attribute updates
    the attribute of Dish Manager and Vice versa."""
    dm_attribute_event_store = event_store_class()
    ds_attribute_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "dscPowerLimitkW", tango.EventType.CHANGE_EVENT, dm_attribute_event_store
    )
    ds_device_proxy.subscribe_event(
        "dscPowerLimitkW", tango.EventType.CHANGE_EVENT, ds_attribute_event_store
    )
    power_limit_list = [12.4, 14.3]
    for proxy, power_limit in zip([ds_device_proxy, dish_manager_proxy], power_limit_list):
        proxy.write_attribute("dscPowerLimitkW", power_limit)
        ds_attribute_event_store.wait_for_value(power_limit)
        dm_attribute_event_store.wait_for_value(power_limit)


@pytest.mark.acceptance
@pytest.mark.forked
def test_incorrect_power_limit_change(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Tests the setting of the dscPowerLimitkW attribute (incorrect). Chaining is
    tested in order to make sure that a change on DS Manager's attribute updates the
    attribute of Dish Manager and Vice versa."""
    clean_up(ds_device_proxy, dish_manager_proxy, event_store_class)
    power_limit_list = [0.9, 0.6]
    for proxy, power_limit in zip([ds_device_proxy, dish_manager_proxy], power_limit_list):
        with pytest.raises(tango.DevFailed):
            proxy.write_attribute("dscPowerLimitkW", power_limit)  # This should raise ValueError
            ds_value = ds_device_proxy.read_attribute("dscPowerLimitkW").value
            dish_value = dish_manager_proxy.read_attribute("dscPowerLimitkW").value
            assert ds_value == dish_value == DEFAULT_POWER_LIMIT


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
    """Tests the limits of the attribute dscPowerLimitkW through the SetPowerMode. Chaining is
    tested in order to make sure that a change on DS Manager's attribute updates the attribute
    of Dish Manager and Vice versa."""
    clean_up(ds_device_proxy, dish_manager_proxy, event_store_class)
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
        ds_attribute_event_store.wait_for_value(DEFAULT_POWER_LIMIT, timeout=6)
        dm_attribute_event_store.wait_for_value(DEFAULT_POWER_LIMIT, timeout=6)


# pylint: disable=too-many-arguments
@pytest.mark.acceptance
@pytest.mark.parametrize(
    ("full_power", "expected_progress", "limit_value"),
    [
        (True, "Full Power Mode called using DSC Power Limit: 15.0kW", 15.0),
        (False, "Low Power Mode called using DSC Power Limit: 19.9kW", 19.9),
    ],
)
def test_fp_lp_power_limit_used(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    full_power: bool,
    expected_progress: str,
    limit_value,
    event_store_class: Any,
):
    """Test the dscPowerLimitkW value used when invoking commands (FP and LP)."""
    progress_event_store = event_store_class()
    ds_attribute_event_store = event_store_class()
    ds_device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )
    ds_device_proxy.subscribe_event(
        "dscPowerLimitkW", tango.EventType.CHANGE_EVENT, ds_attribute_event_store
    )
    # Set the value to something other than the default value
    dish_manager_proxy.write_attribute("dscPowerLImitKw", limit_value)
    ds_attribute_event_store.wait_for_value(limit_value, timeout=6)

    # Call command that also makes use of the SetPowerMode command
    if full_power:
        ds_device_proxy.SetStandbyFPMode()
    else:
        ds_device_proxy.SetStandbyLPMode()

    progress_event_store.wait_for_progress_update(expected_progress, timeout=6)


@pytest.mark.acceptance
def test_dsc_current_limit_used(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
):
    """Test the dscPowerLimitkW value used when invoking Slew."""
    progress_event_store = event_store_class()
    pointing_state_events = event_store_class()

    dish_manager_proxy.subscribe_event(
        "pointingState", tango.EventType.CHANGE_EVENT, pointing_state_events
    )
    ds_device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    clean_up(ds_device_proxy, dish_manager_proxy, event_store_class)

    current_az, current_el = dish_manager_proxy.achievedPointing[1:]
    requested_az, requested_el = az_el_slew_position(current_az, current_el, 10.0, 10.0)
    ds_device_proxy.Slew([requested_az, requested_el])
    progress_event_store.wait_for_progress_update(
        (
            "Slew called with Azimuth speed: 3.0 deg/s, Elevation speed: 1.0 deg/s "
            "and DSC Power Limit: 10.0kW"
        ),
        timeout=6,
    )

    # wait for the slew to finish
    estimate_slew_duration = requested_el - current_el
    pointing_state_events.wait_for_value(PointingState.READY, timeout=estimate_slew_duration + 10)
