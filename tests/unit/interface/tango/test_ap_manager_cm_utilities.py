"""Test AP Manager subcomponent manager method overrides."""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import CommunicationStatus
from ska_control_model.future import ControlMode

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "communication_state",
    [CommunicationStatus.NOT_ESTABLISHED, CommunicationStatus.DISABLED],
)
def test_ap_manager_communication_state_updates_connection_state(
    dish_manager_resources_with_ap_manager,
    communication_state,
):
    """Test APManager comm loss is reflected in the connectionstate comp state entry."""
    _, dish_manager_cm = dish_manager_resources_with_ap_manager
    ap_man_cm = dish_manager_cm.sub_component_managers["DS"]

    ap_man_cm._update_component_state(connectionstate=CommunicationStatus.ESTABLISHED)
    ap_man_cm._update_communication_state(communication_state)

    assert ap_man_cm.component_state["connectionstate"] == communication_state


@pytest.mark.unit
@pytest.mark.forked
def test_ap_manager_stop_communicating(
    dish_manager_resources_with_ap_manager,
):
    """AP stop communicating requests NO_MONITOR_NO_CONTROL before Tango dev cm stop_comms."""
    _, dish_manager_cm = dish_manager_resources_with_ap_manager
    ap_man_cm = dish_manager_cm.sub_component_managers["DS"]

    apm_device_proxy = Mock()

    # Hold all commands called over the test duration
    operations = []
    apm_device_proxy.write_attribute.side_effect = lambda attribute_name, value: operations.append(
        ("write", attribute_name, value)
    )

    with (
        patch.object(
            ap_man_cm._device_proxy_factory,
            "get_cached_proxy",
            return_value=apm_device_proxy,
        ),
        patch.object(
            TangoDeviceComponentManager,
            "stop_communicating",
            autospec=True,
            side_effect=lambda component_manager: operations.append(("tango_dev_cm_stop",)),
        ) as tango_dev_cm_stop_communicating,
    ):
        ap_man_cm.stop_communicating()

    assert operations == [
        ("write", "controlMode", ControlMode.NO_MONITOR_NO_CONTROL),
        ("tango_dev_cm_stop",),
    ]
    tango_dev_cm_stop_communicating.assert_called_once_with(ap_man_cm)


@pytest.mark.unit
@pytest.mark.forked
def test_ap_manager_stop_communicating_without_device_proxy(
    dish_manager_resources_with_ap_manager,
    caplog,
):
    """Test skipping controlMode write and warn when no APManager proxy is available."""
    _, dish_manager_cm = dish_manager_resources_with_ap_manager
    ap_man_cm = dish_manager_cm.sub_component_managers["DS"]

    with (
        patch.object(
            ap_man_cm._device_proxy_factory,
            "get_cached_proxy",
            return_value=None,
        ) as get_cached_proxy,
        patch.object(TangoDeviceComponentManager, "stop_communicating", autospec=True) as stop,
    ):
        ap_man_cm.stop_communicating()

    get_cached_proxy.assert_called_once_with(ap_man_cm._tango_device_fqdn)
    stop.assert_called_once_with(ap_man_cm)
    assert "device proxy is not available" in caplog.text


@pytest.mark.unit
@pytest.mark.forked
def test_ap_manager_stop_communicating_continues_after_write_failure(
    dish_manager_resources_with_ap_manager,
    caplog,
):
    """Test that we continue stop_communication and log when the controlMode write fails."""
    _, dish_manager_cm = dish_manager_resources_with_ap_manager
    ap_man_cm = dish_manager_cm.sub_component_managers["DS"]
    apm_device_proxy = Mock()
    apm_device_proxy.write_attribute.side_effect = RuntimeError("write failed")

    with (
        patch.object(
            ap_man_cm._device_proxy_factory,
            "get_cached_proxy",
            return_value=apm_device_proxy,
        ),
        patch.object(TangoDeviceComponentManager, "stop_communicating", autospec=True) as stop,
    ):
        ap_man_cm.stop_communicating()

    apm_device_proxy.write_attribute.assert_called_once_with(
        "controlMode",
        ControlMode.NO_MONITOR_NO_CONTROL,
    )
    stop.assert_called_once_with(ap_man_cm)
    assert "Failed to set AP Manager controlMode to NO_MONITOR_NO_CONTROL" in caplog.text
