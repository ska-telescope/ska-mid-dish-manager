"""SPFCLnaHPowerState checks."""

import pytest
import tango
from typing import Any
from tango import AttrWriteType
from ska_mid_dish_manager.models.dish_enums import DishMode, SPFOperatingMode


@pytest.mark.acceptance
@pytest.mark.forked
def test_spf_lna_power_state_attributes_initial_values(dish_manager_resources) -> None:
    """Test cap state present."""
    device_proxy, _ = dish_manager_resources
    attributes = device_proxy.get_attribute_list()
    for powerstate_band in ("b1", "b2", "b3", "b4", "b5a", "b5b"):
        state_name = f"{powerstate_band}LnaHPowerState"
        assert state_name in attributes
        assert device_proxy.read_attribute(state_name).value == False

@pytest.mark.acceptance
@pytest.mark.forked
def test_spf_lna_power_state_attributes_types(dish_manager_resources) -> None:
    """Test the spf lna attribute configurations are read and write."""
    device_proxy, _ =  dish_manager_resources
    for powerstate_band in ("b1", "b2", "b3", "b4", "b5a", "b5b"):
        state_name = f"{powerstate_band}LnaHPowerState"
        attribute_type = device_proxy.get_attribute_config(state_name).writable
        assert attribute_type == AttrWriteType.READ_WRITE

@pytest.mark.acceptance
@pytest.mark.forked
def test_spf_lna_power_state_change_unhappy_path( dish_manager_proxy: tango.DeviceProxy,
    spf_device_proxy: tango.DeviceProxy,
    event_store_class: Any,) -> None:
    """Test that SPF Lna Power State change fails when dishmode either not in operate or maintainance."""
    err_msg = "Cannot change LNA power state while SPF not in operate or maintanance mode."
    assert dish_manager_proxy.read_attribute("dishMode").value == "STANDBY"
    expected_result = dish_manager_proxy.write_attribute("b1LnaHPowerState", True)
    assert expected_result == err_msg


@pytest.mark.acceptance
@pytest.mark.forked
def test_spf_lna_power_state_change_happy_path_dishmode_operate( dish_manager_proxy: tango.DeviceProxy,
    spf_device_proxy: tango.DeviceProxy,
    event_store_class: Any,) -> None:
    dm_event_store = event_store_class()
    spf_event_store = event_store_class()

    dish_manager_proxy.ConfigureBand1(True)

    dm_event_store.wait_for_value("dishMode", DishMode.OPERATE)
    spf_event_store.wait_for_value("spfOperatingMode", SPFOperatingMode.OPERATE)

    dish_manager_proxy.write_attribute("b1LnaHPowerState").value = True

    assert dish_manager_proxy.read_attribute("b1LnaHPowerState").value == True

@pytest.mark.acceptance
@pytest.mark.forked
def test_spf_lna_power_state_change_happy_path_dishmode_maintainance( dish_manager_proxy: tango.DeviceProxy,
    spf_device_proxy: tango.DeviceProxy,
    event_store_class: Any,) -> None:
    dm_event_store = event_store_class()
    spf_event_store = event_store_class()

    dish_manager_proxy.SetMaintenanceMode()

    dm_event_store.wait_for_value(DishMode.MAINTENANCE, timeout=30)
    spf_event_store.wait_for_value(SPFOperatingMode.MAINTENANCE, timeout=30)

    dish_manager_proxy.write_attribute("b1LnaHPowerState").value = True

    assert dish_manager_proxy.read_attribute("b1LnaHPowerState").value == True