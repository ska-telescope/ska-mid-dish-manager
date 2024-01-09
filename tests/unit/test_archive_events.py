"""Test client can subscribe to archive events."""

from unittest.mock import patch

import pytest
import tango
from ska_control_model import CommunicationStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager


# pylint:disable=attribute-defined-outside-init
# pylint:disable=protected-access
@pytest.mark.unit
@pytest.mark.forked
class TestArchiveEvent:
    """Test client can subscribe and receive archive events."""

    def setup_method(self):
        """Set up context."""
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
            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

    def teardown_method(self):
        """Tear down context."""
        self.tango_context.stop()

    def test_client_receives_archive_event(self, event_store):
        """Verify archive events get pushed to the event store."""
        self.device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.ARCHIVE_EVENT,
            event_store,
        )

        assert event_store.get_queue_events()
