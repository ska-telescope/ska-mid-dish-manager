"""Unit tests verifying model against DS_SetStowMode transition."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_control_model import CommunicationStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.dish_enums import DSOperatingMode

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestStowMode:
    """Tests for SetStowMode"""

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

            self.device_proxy = self.tango_context.device
            class_instance = DishManager.instances.get(self.device_proxy.name())
            self.ds_cm = class_instance.component_manager.sub_component_managers["DS"]

            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

    def teardown_method(self):
        """Tear down context"""
        pass

    # pylint: disable=missing-function-docstring, protected-access
    def test_stow_mode(self, event_store_class):
        self.ds_cm._update_communication_state(communication_state=CommunicationStatus.ESTABLISHED)
        progress_event_store = event_store_class()
        self.device_proxy.subscribe_event(
            "longRunningCommandProgress",
            tango.EventType.CHANGE_EVENT,
            progress_event_store,
        )

        self.ds_cm.update_state_from_monitored_attributes = MagicMock()
        self.device_proxy.SetStowMode()
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)

        expected_progress_updates = [
            "Stow called on DS",
            "Awaiting dishMode change to STOW",
            "Stow completed",
        ]

        events = progress_event_store.wait_for_progress_update(
            expected_progress_updates[-1], timeout=6
        )
        events_string = "".join([str(event.attr_value.value) for event in events])
        # Check that all the expected progress messages appeared
        # in the event store
        for message in expected_progress_updates:
            assert message in events_string
