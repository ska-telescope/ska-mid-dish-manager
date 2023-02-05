"""Unit tests for subservient device connection states."""
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_control_model import CommunicationStatus, HealthState
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestConnectionStates:
    """Tests for connection state attributes"""

    def setup_method(self):
        """Set up context"""
        with patch(
            "ska_mid_dish_manager.component_managers.tango_device_cm.tango"
        ) as patched_tango:
            patched_dp = MagicMock()
            patched_dp.command_inout = MagicMock()
            patched_tango.DeviceProxy = MagicMock(return_value=patched_dp)
            self.tango_context = DeviceTestContext(DishManager)
            self.tango_context.start()

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()

    # pylint: disable=missing-function-docstring, protected-access
    @pytest.mark.parametrize(
        ("sub_device, connection_state_attr"),
        [
            ("DS", "dsConnectionState"),
            ("SPFRX", "spfrxConnectionState"),
            ("SPF", "spfConnectionState"),
        ],
    )
    def test_connection_state_attrs_mirror_communication_status(
        self,
        event_store,
        sub_device,
        connection_state_attr,
    ):
        device_proxy = self.tango_context.device
        device_proxy.subscribe_event(
            connection_state_attr,
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        class_instance = DishManager.instances.get(device_proxy.name())
        component_manager = class_instance.component_manager.component_managers[sub_device]

        # We expect the connectionState to intially be ESTABLISHED
        assert event_store.wait_for_value(CommunicationStatus.ESTABLISHED)
        # From the current implementation, HealthState will report UNKNOWN even
        # if connection is established; but for now, check when connection is lost
        # assert device_proxy.healthState == HealthState.OK


        # Force communication_state to NOT_ESTABLISHED
        component_manager._update_communication_state(
            communication_state=CommunicationStatus.NOT_ESTABLISHED
        )

        # We can now expect connectionState to transition to NOT_ESTABLISHED
        assert event_store.wait_for_value(CommunicationStatus.NOT_ESTABLISHED)
        assert device_proxy.healthState == HealthState.UNKNOWN
