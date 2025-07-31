"""Test dscPowerLimtkW Attribute."""

from typing import Any

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import PointingState
from tests.utils import calculate_slew_target, remove_subscriptions, setup_subscriptions

DEFAULT_POWER_LIMIT = 10


def clean_up(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Sets the power limit to it's default value."""
    ds_device_proxy.write_attribute("dscPowerLimitKw", DEFAULT_POWER_LIMIT)
    dm_attribute_event_store = event_store_class()
    sub_id = dish_manager_proxy.subscribe_event(
        "dscPowerLimitkW", tango.EventType.CHANGE_EVENT, dm_attribute_event_store
    )
    dm_attribute_event_store.wait_for_value(DEFAULT_POWER_LIMIT, timeout=6)
    dish_manager_proxy.unsubscribe_event(sub_id)


@pytest.mark.acceptance
@pytest.mark.forked
def test_initial_power_limit(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Tests the dscPowerLimitkW attribute inital value on DS and Dish Manager."""
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
    the attribute of Dish Manager and Vice versa.
    """
    subscriptions = {}
    dm_attribute_event_store = event_store_class()
    ds_attribute_event_store = event_store_class()
    subscriptions.update(
        setup_subscriptions(dish_manager_proxy, {"dscPowerLimitkW": dm_attribute_event_store})
    )
    subscriptions.update(
        setup_subscriptions(ds_device_proxy, {"dscPowerLimitkW": ds_attribute_event_store})
    )

    power_limit_list = [12.4, 14.3]
    for proxy, power_limit in zip([ds_device_proxy, dish_manager_proxy], power_limit_list):
        proxy.write_attribute("dscPowerLimitkW", power_limit)
        ds_attribute_event_store.wait_for_value(power_limit)
        dm_attribute_event_store.wait_for_value(power_limit)
    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
@pytest.mark.forked
def test_incorrect_power_limit_change(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Tests the setting of the dscPowerLimitkW attribute (incorrect). Chaining is
    tested in order to make sure that a change on DS Manager's attribute updates the
    attribute of Dish Manager and Vice versa.
    """
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
    of Dish Manager and Vice versa.
    """
    clean_up(ds_device_proxy, dish_manager_proxy, event_store_class)
    subscriptions = {}
    ds_attribute_event_store = event_store_class()
    dm_attribute_event_store = event_store_class()
    subscriptions.update(
        setup_subscriptions(dish_manager_proxy, {"dscPowerLimitkW": dm_attribute_event_store})
    )
    subscriptions.update(
        setup_subscriptions(ds_device_proxy, {"dscPowerLimitkW": ds_attribute_event_store})
    )

    ds_device_proxy.SetPowerMode(parameter)
    if allowed:
        ds_attribute_event_store.wait_for_value(parameter[1], timeout=6)
        dm_attribute_event_store.wait_for_value(parameter[1], timeout=6)
    else:
        ds_device_proxy.dscPowerLimitkW = DEFAULT_POWER_LIMIT
        dish_manager_proxy.dscPowerLimitkW = DEFAULT_POWER_LIMIT
    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_fp_lp_power_limit_used(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
):
    """Test the dscPowerLimitkW value used when invoking commands (LP and FP)."""
    progress_event_store = event_store_class()
    ds_attribute_event_store = event_store_class()
    attr_cb_mapping = {
        "dscPowerLimitkW": ds_attribute_event_store,
        "longRunningCommandProgress": progress_event_store,
    }
    subscriptions = setup_subscriptions(ds_device_proxy, attr_cb_mapping)

    # LP transition
    # Set the value to something other than the default value
    limit_value = 19.9
    dish_manager_proxy.write_attribute("dscPowerLImitKw", limit_value)
    ds_attribute_event_store.wait_for_value(limit_value, timeout=6)
    # Call command that also makes use of the SetPowerMode command
    ds_device_proxy.SetStandbyLPMode()
    progress_event_store.wait_for_progress_update(
        f"Low Power Mode called using DSC Power Limit: {limit_value}kW", timeout=6
    )

    # FP transition
    # Set the value to something other than the default value
    limit_value = 15.0
    dish_manager_proxy.write_attribute("dscPowerLImitKw", limit_value)
    ds_attribute_event_store.wait_for_value(limit_value, timeout=6)
    # Call command that also makes use of the SetPowerMode command
    ds_device_proxy.SetStandbyFPMode()
    progress_event_store.wait_for_progress_update(
        f"Full Power Mode called using DSC Power Limit: {limit_value}kW", timeout=6
    )
    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_dsc_current_limit_used(
    ds_device_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
):
    """Test the dscPowerLimitkW value used when invoking Slew."""
    subscriptions = {}
    progress_event_store = event_store_class()
    pointing_state_events = event_store_class()
    subscriptions.update(
        setup_subscriptions(dish_manager_proxy, {"pointingState": pointing_state_events})
    )
    subscriptions.update(
        setup_subscriptions(ds_device_proxy, {"longRunningCommandProgress": progress_event_store})
    )

    clean_up(ds_device_proxy, dish_manager_proxy, event_store_class)

    current_az, current_el = dish_manager_proxy.achievedPointing[1:]
    requested_az, requested_el = calculate_slew_target(current_az, current_el, 10.0, 10.0)
    ds_device_proxy.Slew([requested_az, requested_el])
    progress_event_store.wait_for_progress_update(
        (
            "Slew called with Azimuth speed: 3.0 deg/s, Elevation speed: 1.0 deg/s "
            "and DSC Power Limit: 10.0kW"
        ),
        timeout=6,
    )

    # wait for the slew to finish
    estimate_slew_duration = abs(requested_el - current_el)
    pointing_state_events.wait_for_value(PointingState.READY, timeout=estimate_slew_duration + 10)

    remove_subscriptions(subscriptions)
