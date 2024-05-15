"""Unit tests for subservient device connection states."""

from unittest.mock import patch

import pytest
import tango
from ska_control_model import CommunicationStatus, HealthState
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from tests.utils import EventStore


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestConnectionStates:
    """Tests for connection state attributes"""

    # pylint: disable=protected-access
    def setup_method(self):
        """Set up context"""
        with patch(
            (
                "ska_mid_dish_manager.component_managers.tango_device_cm."
                "TangoDeviceComponentManager.start_communicating"
            )
        ):
            self.tango_context = DeviceTestContext(DishManager)
            self.tango_context.start()
            # Wait for the threads to start otherwise the mocks get
            # returned back to non mock
            event_store = EventStore()
            self.device_proxy = self.tango_context.device

            class_instance = DishManager.instances.get(self.device_proxy.name())
            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

            for conn_attr in ["spfConnectionState", "spfrxConnectionState", "dsConnectionState"]:
                self.device_proxy.subscribe_event(
                    conn_attr,
                    tango.EventType.CHANGE_EVENT,
                    event_store,
                )
                event_store.wait_for_value(CommunicationStatus.ESTABLISHED)

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
        component_manager = class_instance.component_manager.sub_component_managers[sub_device]

        assert event_store.wait_for_value(CommunicationStatus.ESTABLISHED)

        # Force communication_state to NOT_ESTABLISHED
        component_manager._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

        # We can now expect connectionState to transition to NOT_ESTABLISHED
        assert event_store.wait_for_value(CommunicationStatus.NOT_ESTABLISHED)
        assert device_proxy.healthState == HealthState.UNKNOWN
