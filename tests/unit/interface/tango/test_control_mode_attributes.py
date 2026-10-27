"""Tango interface regression tests for SPF, SPFRx and B5DC ControlMode attributes."""

import pytest
import tango
from pytest_mock import MockerFixture
from ska_control_model import CommunicationStatus
from ska_control_model.future import ControlMode
from ska_tango_base.base.base_component_manager import BaseComponentManager

from ska_mid_dish_manager.component_managers.dish_manager_cm import (
    DishManagerComponentManager,
)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize("device", ["spf", "spfrx"])
def test_control_mode_is_read_write_tango_enum(dish_manager_resources, device):
    """Both new attributes should be exposed as writable Tango DevEnum."""
    device_proxy, _ = dish_manager_resources
    config = device_proxy.get_attribute_config(f"{device}ControlMode")

    assert config.data_type == tango.DevEnum
    assert config.writable == tango.AttrWriteType.READ_WRITE
    assert tuple(config.enum_labels) == tuple(mode.name for mode in ControlMode)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize("device", ["spf", "spfrx"])
def test_control_mode_is_enabled_by_default(dish_manager_resources, device):
    """Without a memorized override, SPF and SPFRx default to full control."""
    device_proxy, _ = dish_manager_resources
    default_control_mode = device_proxy.read_attribute(f"{device}ControlMode").value

    assert ControlMode(default_control_mode) == ControlMode.MONITOR_AND_CONTROL


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize("device", ["spf", "spfrx"])
def test_control_mode_disables_and_restores_communication(
    dish_manager_resources, event_store_class, mocker, device
):
    """Writing control mode changes both attribute and connection state."""
    device_proxy, component_manager = dish_manager_resources
    attr_name = f"{device}ControlMode"
    connection_attr = f"{device}ConnectionState"
    connection_events = event_store_class()
    default_control_mode = ControlMode(device_proxy.read_attribute(attr_name).value)
    subdevice_cm = component_manager.sub_component_managers[device.upper()]

    def simulate_start_communicating() -> None:
        subdevice_cm._update_communication_state(
            communication_state=CommunicationStatus.ESTABLISHED
        )

    mock_start = mocker.patch.object(
        subdevice_cm,
        "start_communicating",
        side_effect=simulate_start_communicating,
    )
    subscription_id = device_proxy.subscribe_event(
        connection_attr,
        tango.EventType.CHANGE_EVENT,
        connection_events,
    )
    try:
        device_proxy.write_attribute(attr_name, ControlMode.NO_MONITOR_NO_CONTROL)
        assert ControlMode(device_proxy.read_attribute(attr_name).value) == (
            ControlMode.NO_MONITOR_NO_CONTROL
        )
        connection_events.wait_for_value(CommunicationStatus.DISABLED, timeout=10)

        device_proxy.write_attribute(attr_name, ControlMode.MONITOR_AND_CONTROL)
        assert ControlMode(device_proxy.read_attribute(attr_name).value) == (
            ControlMode.MONITOR_AND_CONTROL
        )
        mock_start.assert_called_once()
        connection_events.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=10)
    finally:
        device_proxy.unsubscribe_event(subscription_id)
        # Restore the state even if a readback or event assertion failed.
        device_proxy.write_attribute(attr_name, default_control_mode)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize("device", ["spf", "spfrx"])
def test_monitor_no_control_is_rejected(dish_manager_resources, device):
    """Test that we report MONITOR_NO_CONTROL as unsupported by the current implementation."""
    device_proxy, _ = dish_manager_resources
    attr_name = f"{device}ControlMode"
    original = ControlMode(device_proxy.read_attribute(attr_name).value)

    with pytest.raises(tango.DevFailed) as caught:
        device_proxy.write_attribute(attr_name, ControlMode.MONITOR_NO_CONTROL)

    assert "MONITOR_NO_CONTROL" in caught.value.args[0].desc
    assert "not implemented" in caught.value.args[0].desc.lower()
    assert ControlMode(device_proxy.read_attribute(attr_name).value) == original


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize("device,other_device", [("spf", "spfrx"), ("spfrx", "spf")])
def test_changing_one_control_mode_does_not_change_the_other(
    dish_manager_resources, device, other_device
):
    """Testing that device control modes are independently controllable."""
    device_proxy, _ = dish_manager_resources
    attr_name = f"{device}ControlMode"
    other_attr = f"{other_device}ControlMode"
    sub_device_value = ControlMode(device_proxy.read_attribute(attr_name).value)
    sub_device2_value = ControlMode(device_proxy.read_attribute(other_attr).value)

    try:
        device_proxy.write_attribute(attr_name, ControlMode.NO_MONITOR_NO_CONTROL)
        assert ControlMode(device_proxy.read_attribute(attr_name).value) == (
            ControlMode.NO_MONITOR_NO_CONTROL
        )
        assert ControlMode(sub_device2_value) == (ControlMode.MONITOR_AND_CONTROL)
    finally:
        device_proxy.write_attribute(attr_name, sub_device_value)


@pytest.mark.unit
@pytest.mark.parametrize(
    "value, expected",
    [
        ("NO_MONITOR_NO_CONTROL", ControlMode.NO_MONITOR_NO_CONTROL),
        ("MONITOR_NO_CONTROL", ControlMode.MONITOR_NO_CONTROL),
        ("MONITOR_AND_CONTROL", ControlMode.MONITOR_AND_CONTROL),
        ("0", ControlMode.NO_MONITOR_NO_CONTROL),
        ("1", ControlMode.MONITOR_NO_CONTROL),
        ("2", ControlMode.MONITOR_AND_CONTROL),
    ],
)
def test_parse_control_mode_value(value, expected):
    """Test parsing ControlMode names and numeric strings."""
    result = DishManagerComponentManager._parse_control_mode_value(value)

    assert result == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        "INVALID",
        "99",
        "",
        None,
    ],
)
def test_parse_control_mode_value_invalid(value):
    """Test that invalid control mode values are rejected."""
    with pytest.raises(ValueError, match="Invalid control mode value"):
        DishManagerComponentManager._parse_control_mode_value(value)


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_control_mode_disables_and_restores_communication(
    dish_manager_resources_with_b5dc_monitoring, event_store_class, mocker: MockerFixture
) -> None:
    """Verify B5DC communication changes according to its control mode."""
    device_proxy, component_manager = dish_manager_resources_with_b5dc_monitoring

    assert "B5DC" in component_manager.sub_component_managers
    b5dc_cm = component_manager.sub_component_managers["B5DC"]
    attr_name = "b5dcControlMode"
    connection_attr = "b5dcConnectionState"

    connection_events = event_store_class()

    def simulate_start_communicating() -> None:
        BaseComponentManager._update_communication_state(
            b5dc_cm,
            CommunicationStatus.ESTABLISHED,
        )

    mock_start = mocker.patch.object(
        b5dc_cm,
        "start_communicating",
        side_effect=simulate_start_communicating,
    )
    original_mode = ControlMode(device_proxy.read_attribute(attr_name).value)

    subscription_id = device_proxy.subscribe_event(
        connection_attr,
        tango.EventType.CHANGE_EVENT,
        connection_events,
    )

    try:
        device_proxy.write_attribute(
            attr_name,
            ControlMode.NO_MONITOR_NO_CONTROL,
        )

        assert (
            ControlMode(device_proxy.read_attribute(attr_name).value)
            == ControlMode.NO_MONITOR_NO_CONTROL
        )

        connection_events.wait_for_value(
            CommunicationStatus.DISABLED,
            timeout=10,
        )

        device_proxy.write_attribute(
            attr_name,
            ControlMode.MONITOR_AND_CONTROL,
        )

        assert (
            ControlMode(device_proxy.read_attribute(attr_name).value)
            == ControlMode.MONITOR_AND_CONTROL
        )

        mock_start.assert_called_once()

        connection_events.wait_for_value(
            CommunicationStatus.ESTABLISHED,
            timeout=10,
        )

    finally:
        device_proxy.write_attribute(attr_name, original_mode)
        device_proxy.unsubscribe_event(subscription_id)
