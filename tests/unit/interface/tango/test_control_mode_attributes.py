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

CONTROL_MODE_ATTRIBUTES = (
    "spfControlMode",
    "spfrxControlMode",
    "b5dcControlMode",
)


def _snapshot_other_control_modes(
    device_proxy,
    attr_name: str,
) -> dict[str, ControlMode]:
    """Capture the other subdevices' ControlModes before a write."""
    return {
        other_attr: ControlMode(device_proxy.read_attribute(other_attr).value)
        for other_attr in CONTROL_MODE_ATTRIBUTES
        if other_attr != attr_name
    }


def _assert_other_control_modes_unchanged(
    device_proxy,
    original_modes: dict[str, ControlMode],
) -> None:
    """Verify that unrelated ControlMode attributes remain unchanged."""
    for other_attr, original_mode in original_modes.items():
        current_mode = ControlMode(device_proxy.read_attribute(other_attr).value)

        assert current_mode == original_mode, (
            f"{other_attr} changed unexpectedly: "
            f"expected {original_mode.name}, got {current_mode.name}"
        )


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize("device", ["spf", "spfrx"])
def test_control_mode_is_read_write_tango_enum(
    dish_manager_resources,
    device,
):
    """Both new attributes should be exposed as writable Tango DevEnum."""
    device_proxy, _ = dish_manager_resources

    config = device_proxy.get_attribute_config(f"{device}ControlMode")

    assert config.data_type == tango.DevEnum
    assert config.writable == tango.AttrWriteType.READ_WRITE
    assert tuple(config.enum_labels) == tuple(mode.name for mode in ControlMode)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize("device", ["spf", "spfrx"])
def test_control_mode_is_enabled_by_default(
    dish_manager_resources,
    device,
):
    """Without a memorized override, SPF and SPFRx default to full control."""
    device_proxy, _ = dish_manager_resources

    default_control_mode = device_proxy.read_attribute(f"{device}ControlMode").value

    assert ControlMode(default_control_mode) == ControlMode.MONITOR_AND_CONTROL


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize("device", ["spf", "spfrx"])
def test_control_mode_disables_and_restores_communication(
    dish_manager_resources,
    event_store_class,
    mocker: MockerFixture,
    device,
) -> None:
    """Writing control mode changes communication without affecting other modes."""
    device_proxy, component_manager = dish_manager_resources

    attr_name = f"{device}ControlMode"
    connection_attr = f"{device}ConnectionState"

    connection_events = event_store_class()

    default_control_mode = ControlMode(device_proxy.read_attribute(attr_name).value)

    # Save other ControlModes before modifying the target device.
    original_other_modes = _snapshot_other_control_modes(
        device_proxy,
        attr_name,
    )

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
        # Disable communication.
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

        # Independence: other ControlModes must remain unchanged.
        _assert_other_control_modes_unchanged(
            device_proxy,
            original_other_modes,
        )

        # Restore communication.
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

        # Independence must also hold after communication is restored.
        _assert_other_control_modes_unchanged(
            device_proxy,
            original_other_modes,
        )

    finally:
        try:
            device_proxy.write_attribute(
                attr_name,
                default_control_mode,
            )
        finally:
            device_proxy.unsubscribe_event(subscription_id)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize("device", ["spf", "spfrx"])
def test_monitor_no_control_is_rejected(
    dish_manager_resources,
    device,
):
    """Verify unsupported MONITOR_NO_CONTROL does not change device modes."""
    device_proxy, _ = dish_manager_resources

    attr_name = f"{device}ControlMode"

    original = ControlMode(device_proxy.read_attribute(attr_name).value)

    # Save unrelated ControlModes before attempting an invalid write.
    original_other_modes = _snapshot_other_control_modes(
        device_proxy,
        attr_name,
    )

    with pytest.raises(tango.DevFailed) as caught:
        device_proxy.write_attribute(
            attr_name,
            ControlMode.MONITOR_NO_CONTROL,
        )

    assert "MONITOR_NO_CONTROL" in caught.value.args[0].desc
    assert "not implemented" in caught.value.args[0].desc.lower()

    # Target attribute should remain unchanged.
    assert ControlMode(device_proxy.read_attribute(attr_name).value) == original

    # Independence: a rejected write must not change other modes.
    _assert_other_control_modes_unchanged(
        device_proxy,
        original_other_modes,
    )


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "device,other_device",
    [
        ("spf", "spfrx"),
        ("spfrx", "spf"),
    ],
)
def test_changing_one_control_mode_does_not_change_the_other(
    dish_manager_resources,
    device,
    other_device,
):
    """Verify SPF and SPFRx modes remain independently controllable."""
    device_proxy, _ = dish_manager_resources

    attr_name = f"{device}ControlMode"
    other_attr = f"{other_device}ControlMode"

    original_mode = ControlMode(device_proxy.read_attribute(attr_name).value)

    # Save both other modes, including B5DC.
    original_other_modes = _snapshot_other_control_modes(
        device_proxy,
        attr_name,
    )

    sub_device2_value = original_other_modes[other_attr]

    try:
        device_proxy.write_attribute(
            attr_name,
            ControlMode.NO_MONITOR_NO_CONTROL,
        )

        # Verify that the requested mode changed.
        assert (
            ControlMode(device_proxy.read_attribute(attr_name).value)
            == ControlMode.NO_MONITOR_NO_CONTROL
        )

        # Reviewer fix: reread the other Tango attribute after the write.
        assert ControlMode(device_proxy.read_attribute(other_attr).value) == sub_device2_value

        # Also verify that every other ControlMode remains unchanged.
        _assert_other_control_modes_unchanged(
            device_proxy,
            original_other_modes,
        )

    finally:
        device_proxy.write_attribute(
            attr_name,
            original_mode,
        )

    # Verify independence after restoring the original mode.
    _assert_other_control_modes_unchanged(
        device_proxy,
        original_other_modes,
    )


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
    with pytest.raises(
        ValueError,
        match="Invalid control mode value",
    ):
        DishManagerComponentManager._parse_control_mode_value(value)


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_control_mode_disables_and_restores_communication(
    dish_manager_resources_with_b5dc_monitoring,
    event_store_class,
    mocker: MockerFixture,
) -> None:
    """Verify B5DC communication changes without affecting SPF or SPFRx."""
    device_proxy, component_manager = dish_manager_resources_with_b5dc_monitoring

    assert "B5DC" in component_manager.sub_component_managers

    b5dc_cm = component_manager.sub_component_managers["B5DC"]

    attr_name = "b5dcControlMode"
    connection_attr = "b5dcConnectionState"

    # Save B5DC's original ControlMode.
    original_mode = ControlMode(device_proxy.read_attribute(attr_name).value)

    # Save SPF and SPFRx ControlModes before modifying B5DC.
    original_other_modes = _snapshot_other_control_modes(
        device_proxy,
        attr_name,
    )

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

    subscription_id = device_proxy.subscribe_event(
        connection_attr,
        tango.EventType.CHANGE_EVENT,
        connection_events,
    )

    try:
        # Disable B5DC communication.
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

        # Independence: SPF and SPFRx must remain unchanged.
        _assert_other_control_modes_unchanged(
            device_proxy,
            original_other_modes,
        )

        # Restore B5DC communication.
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

        # Independence must also hold after restoring B5DC.
        _assert_other_control_modes_unchanged(
            device_proxy,
            original_other_modes,
        )

    finally:
        try:
            device_proxy.write_attribute(
                attr_name,
                original_mode,
            )
        finally:
            device_proxy.unsubscribe_event(subscription_id)


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_control_mode_syncs_component_states(
    dish_manager_resources_with_b5dc_monitoring,
    mocker: MockerFixture,
) -> None:
    """Verify B5DC synchronization does not modify other ControlModes."""
    _, component_manager = dish_manager_resources_with_b5dc_monitoring

    original_spf_mode = component_manager.check_device_control_mode("SPF")
    original_spfrx_mode = component_manager.check_device_control_mode("SPFRX")

    mock_sync = mocker.patch.object(
        component_manager,
        "sync_component_states",
    )

    component_manager.set_b5dc_control_mode(
        ControlMode.NO_MONITOR_NO_CONTROL,
        sync=True,
    )

    mock_sync.assert_called_once()

    assert component_manager.check_device_control_mode("B5DC") == ControlMode.NO_MONITOR_NO_CONTROL

    assert component_manager.check_device_control_mode("SPF") == original_spf_mode

    assert component_manager.check_device_control_mode("SPFRX") == original_spfrx_mode
