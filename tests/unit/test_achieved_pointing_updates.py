"""Test that the DishManager achievedPointing attribute is in sync
with the DSManager achievedPointing attribute."""

import logging
from unittest.mock import patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestAchievedPointing:
    """Test DishManager reports correct DS pointing coordinates"""

    def setup_method(self):
        """Set up context"""
        with patch(
            "ska_mid_dish_manager.component_managers.device_monitor.TangoDeviceMonitor.monitor"
        ):
            self.tango_context = DeviceTestContext(DishManager)
            self.tango_context.start()

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()

    # pylint: disable=missing-function-docstring, protected-access
    def test_achieved_pointing_in_sync_with_dish_structure_pointing(
        self,
        event_store,
    ):
        """
        Test achieved pointing is in sync with dish structure pointing
        """
        device_proxy = self.tango_context.device
        device_proxy.subscribe_event(
            "achievedPointing",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        test_coordinates = (5000.0, 45.0, 234.0)
        assert list(device_proxy.achievedPointing) != list(test_coordinates)
        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.sub_component_managers["DS"]
        ds_cm._update_component_state(achievedpointing=test_coordinates)
        event_store.wait_for_value(test_coordinates)
        assert list(device_proxy.achievedPointing) == list(test_coordinates)
