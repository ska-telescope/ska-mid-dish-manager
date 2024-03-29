"""Test that the DishManager desiredPointing attribute is in sync
with the DSManager desiredPointing attribute."""

import logging
from unittest.mock import patch

import pytest
import tango
from ska_control_model import CommunicationStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestDesiredPointing:
    """Test DishManager reports correct DS pointing coordinates"""

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
            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

    def teardown_method(self):
        """Tear down context"""
        return

    # pylint: disable=missing-function-docstring, protected-access
    def test_desired_pointing_in_sync_with_dish_structure_pointing(
        self,
        event_store,
    ):
        """
        Test desired pointing is in sync with dish structure pointing
        """
        device_proxy = self.tango_context.device
        device_proxy.subscribe_event(
            "desiredPointingAz",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        device_proxy.subscribe_event(
            "desiredPointingEl",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        test_coordinates_az = (5000.0, 234.0)
        test_coordinates_el = (5000.0, 45.0)
        assert list(device_proxy.desiredPointingAz) != list(test_coordinates_az)
        assert list(device_proxy.desiredPointingEl) != list(test_coordinates_el)

        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.sub_component_managers["DS"]

        ds_cm._update_component_state(desiredpointingaz=test_coordinates_az)
        ds_cm._update_component_state(desiredpointingel=test_coordinates_el)

        event_store.wait_for_value(test_coordinates_az)
        event_store.wait_for_value(test_coordinates_el)

        assert list(device_proxy.desiredPointingAz) == list(test_coordinates_az)
        assert list(device_proxy.desiredPointingEl) == list(test_coordinates_el)
