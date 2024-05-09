"""Test that the DishManager achievedPointing attribute is in sync
with the DSManager achievedPointing attribute."""

import logging
from unittest.mock import patch

import pytest
import tango
from ska_control_model import CommunicationStatus
from tango import AttrQuality
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestAchievedPointing:
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
        self.tango_context.stop()

    # pylint: disable=missing-function-docstring, protected-access
    def test_achieved_pointing_in_sync_with_dish_structure_pointing(
        self,
        event_store_class,
    ):
        """
        Test achieved pointing is in sync with dish structure pointing
        """
        device_proxy = self.tango_context.device

        main_event_store = event_store_class()
        az_event_store = event_store_class()
        el_event_store = event_store_class()

        device_proxy.subscribe_event(
            "achievedPointing",
            tango.EventType.CHANGE_EVENT,
            main_event_store,
        )
        device_proxy.subscribe_event(
            "achievedPointingaz",
            tango.EventType.CHANGE_EVENT,
            az_event_store,
        )
        device_proxy.subscribe_event(
            "achievedPointingel",
            tango.EventType.CHANGE_EVENT,
            el_event_store,
        )
        test_coordinates = (5000.0, 234.0, 45.0)
        test_coordinates_az = (test_coordinates[0], test_coordinates[1])
        test_coordinates_el = (test_coordinates[0], test_coordinates[2])

        assert list(device_proxy.achievedPointing) != list(test_coordinates)
        assert list(device_proxy.achievedPointingAz) != list(test_coordinates_az)
        assert list(device_proxy.achievedPointingEl) != list(test_coordinates_el)

        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.sub_component_managers["DS"]

        ds_cm._update_component_state(achievedpointing=[test_coordinates, AttrQuality.ATTR_VALID])
        ds_cm._update_component_state(
            achievedpointingaz=[test_coordinates_az, AttrQuality.ATTR_VALID]
        )
        ds_cm._update_component_state(
            achievedpointingel=[test_coordinates_el, AttrQuality.ATTR_VALID]
        )

        main_event_store.wait_for_value(test_coordinates)
        az_event_store.wait_for_value(test_coordinates_az)
        el_event_store.wait_for_value(test_coordinates_el)

        assert list(device_proxy.achievedPointing) == list(test_coordinates)
        assert list(device_proxy.achievedPointingAz) == list(test_coordinates_az)
        assert list(device_proxy.achievedPointingEl) == list(test_coordinates_el)
