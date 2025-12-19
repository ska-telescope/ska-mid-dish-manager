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
def test_spf_lna_power_state_change_unhappy_path(
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Test that SPF Lna Power State change fails when dishmode either not in operate
    or maintainance.
    """
    attr_cb_mapping = {}
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    err_msg = "Cannot change LNA power state while dish is not in operate or maintanance mode."
    assert dish_manager_proxy.read_attribute("dishMode").value == DishMode.STANDBY_FP
    with pytest.raises(tango.DevFailed) as exc_info:
        dish_manager_proxy.write_attribute("b1LnaHPowerState", True)
    err_desc = exc_info.value.args[0].desc
    assert err_msg in err_desc
    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_spf_lna_power_state_change_happy_path_dishmode_operate(
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test that SPF Lna Power State change works when dishmode is in operate."""
    dm_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": dm_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    attr_change_value = True
    dish_manager_proxy.ConfigureBand1(True)
    dm_event_store.wait_for_value(DishMode.OPERATE, timeout=30)
    dish_manager_proxy.write_attribute("b1LnaHPowerState", attr_change_value)

    assert dish_manager_proxy.read_attribute("b1LnaHPowerState").value == attr_change_value
    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_spf_lna_power_state_change_happy_path_dishmode_maintainance(
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test that SPF Lna Power State change works when dishmode is in maintainance."""
    dm_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": dm_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    attr_change_value = True

    dish_manager_proxy.SetMaintenanceMode()

    dm_event_store.wait_for_value(DishMode.MAINTENANCE, timeout=90)
    dish_manager_proxy.write_attribute("b1LnaHPowerState", attr_change_value)

    assert dish_manager_proxy.read_attribute("b1LnaHPowerState").value == attr_change_value
    remove_subscriptions(subscriptions)
