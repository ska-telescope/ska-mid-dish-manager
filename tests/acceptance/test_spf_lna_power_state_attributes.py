"""SPFCLnaHPowerState checks."""

from typing import Any

import pytest
import tango
from tango import AttrWriteType

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_spf_lna_power_state_attributes_initial_values(
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Test the spf lna attribute initial values are correct."""
    attr_cb_mapping = {}
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    init_value = False
    attributes = dish_manager_proxy.get_attribute_list()
    for powerstate_band in ("b1", "b2", "b3", "b4", "b5a", "b5b"):
        state_name = f"{powerstate_band}LnaHPowerState"
        assert state_name in attributes
        assert dish_manager_proxy.read_attribute(state_name).value == init_value
    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_spf_lna_power_state_attributes_types(dish_manager_proxy: tango.DeviceProxy) -> None:
    """Test the spf lna attribute configurations are read and write."""
    attr_cb_mapping = {}
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    for powerstate_band in ("b1", "b2", "b3", "b4", "b5a", "b5b"):
        state_name = f"{powerstate_band}LnaHPowerState"
        attribute_type = dish_manager_proxy.get_attribute_config(state_name).writable
        assert attribute_type == AttrWriteType.READ_WRITE
    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
@pytest.mark.parametrize(
    "attribute_name",
    [
        "b1lnahpowerstate",
        "b2lnahpowerstate",
        "b3lnahpowerstate",
        "b4lnahpowerstate",
        "b5alnahpowerstate",
        "b5blnahpowerstate",
    ],
)
def test_spf_lna_power_state_rejects_attribute_writes(
    attribute_name: str,
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Test that SPF Lna Power State change is rejected when dishmode either not in operate
    or maintainance.
    """
    attr_cb_mapping = {}
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    err_msg = "Cannot change LNA power state while dish is not in operate or maintanance mode."
    assert dish_manager_proxy.read_attribute("dishMode").value == DishMode.STANDBY_FP
    with pytest.raises(tango.DevFailed) as exc_info:
        dish_manager_proxy.write_attribute(attribute_name, True)
    err_desc = exc_info.value.args[0].desc
    assert err_msg in err_desc
    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
@pytest.mark.parametrize(
    "attribute_name",
    [
        "b1lnahpowerstate",
        "b2lnahpowerstate",
        "b3lnahpowerstate",
        "b4lnahpowerstate",
        "b5alnahpowerstate",
        "b5blnahpowerstate",
    ],
)
def test_spf_lna_power_state_change_on_dishmode_operate(
    attribute_name: str,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test that SPF Lna Power State change updates when dishmode is in operate."""
    dm_event_store = event_store_class()
    spf_lna_power_state_attr_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": dm_event_store,
        attribute_name: spf_lna_power_state_attr_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    if dish_manager_proxy.dishmode != DishMode.OPERATE:
        dish_manager_proxy.ConfigureBand1(True)
    dm_event_store.wait_for_value(DishMode.OPERATE, timeout=30)
    dish_manager_proxy.write_attribute(attribute_name, True)
    spf_lna_power_state_attr_event_store.wait_for_value(True, timeout=30)
    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
@pytest.mark.parametrize(
    "attribute_name",
    [
        "b1lnahpowerstate",
        "b2lnahpowerstate",
        "b3lnahpowerstate",
        "b4lnahpowerstate",
        "b5alnahpowerstate",
        "b5blnahpowerstate",
    ],
)
def test_spf_lna_power_state_change_on_dishmode_maintainance(
    attribute_name: str,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test that SPF Lna Power State change updates when dishmode is in maintainance."""
    dm_event_store = event_store_class()
    spf_lna_power_state_attr_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": dm_event_store,
        attribute_name: spf_lna_power_state_attr_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    if dish_manager_proxy.dishmode != DishMode.MAINTENANCE:
        dish_manager_proxy.SetMaintenanceMode()
    dm_event_store.wait_for_value(DishMode.MAINTENANCE, timeout=90)
    dish_manager_proxy.write_attribute(attribute_name, True)
    spf_lna_power_state_attr_event_store.wait_for_value(True, timeout=30)
    remove_subscriptions(subscriptions)
