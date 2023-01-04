"""Unit tests for subservient device connection states."""
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_tango_base.control_model import CommunicationStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import DeviceConnectionState


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
    def test_spf_connection_state_in_sync_with_spf_cm_communication_status(
        self,
        event_store,
    ):
        device_proxy = self.tango_context.device
        device_proxy.subscribe_event(
            "spfConnectionState",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        class_instance = DishManager.instances.get(device_proxy.name())
        spf_cm = class_instance.component_manager.component_managers["SPF"]

        # We expect the spfConnectionState to be intially be CONNECTED
        assert event_store.wait_for_value(DeviceConnectionState.CONNECTED)

        # Force spf communication_state to NOT_ESTABLISHED
        spf_cm._update_communication_state(
            communication_state=CommunicationStatus.NOT_ESTABLISHED
        )

        # We can now expect spfConnectionState to transition to DISCONNECTED
        assert event_store.wait_for_value(DeviceConnectionState.DISCONNECTED)

    # pylint: disable=missing-function-docstring, protected-access
    def test_spfrx_connection_state_in_sync_with_spfrx_cm_communication_status(
        self,
        event_store,
    ):
        device_proxy = self.tango_context.device
        device_proxy.subscribe_event(
            "spfrxConnectionState",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        class_instance = DishManager.instances.get(device_proxy.name())
        spfrx_cm = class_instance.component_manager.component_managers["SPFRX"]

        # We expect the spfrxConnectionState to be intially be CONNECTED
        assert event_store.wait_for_value(DeviceConnectionState.CONNECTED)

        # Force spfrx communication_state to NOT_ESTABLISHED
        spfrx_cm._update_communication_state(
            communication_state=CommunicationStatus.NOT_ESTABLISHED
        )

        # We can now expect spfrxConnectionState to transition to DISCONNECTED
        assert event_store.wait_for_value(DeviceConnectionState.DISCONNECTED)

    # pylint: disable=missing-function-docstring, protected-access
    def test_ds_connection_state_in_sync_with_ds_cm_communication_status(
        self,
        event_store,
    ):
        device_proxy = self.tango_context.device
        device_proxy.subscribe_event(
            "dsConnectionState",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.component_managers["DS"]

        # We expect the dsConnectionState to be intially be CONNECTED
        assert event_store.wait_for_value(DeviceConnectionState.CONNECTED)

        # Force ds communication_state to NOT_ESTABLISHED
        ds_cm._update_communication_state(
            communication_state=CommunicationStatus.NOT_ESTABLISHED
        )

        # We can now expect dsConnectionState to transition to DISCONNECTED
        assert event_store.wait_for_value(DeviceConnectionState.DISCONNECTED)
