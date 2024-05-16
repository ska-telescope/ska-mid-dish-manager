"""Unit tests for the Track command."""

import itertools
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
class TestTrack:
    """Tests for Track"""

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
            self.spf_cm = class_instance.component_manager.sub_component_managers["SPF"]
            self.spfrx_cm = class_instance.component_manager.sub_component_managers["SPFRX"]
            self.dish_manager_cm = class_instance.component_manager

            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

    def teardown_method(self):
        """Tear down context"""
        return

    @pytest.mark.parametrize(
        "qual_before,qual_after",
        list(
            itertools.permutations(
                [
                    AttrQuality.ATTR_VALID,
                    AttrQuality.ATTR_INVALID,
                    AttrQuality.ATTR_CHANGING,
                    AttrQuality.ATTR_WARNING,
                    AttrQuality.ATTR_ALARM,
                ],
                2,
            )
        ),  # Just the first 10 for now
    )
    def test_change(self, event_store, qual_before, qual_after):
        """Test the trackInterpolationMode attribute updates on change."""
        device_proxy = self.tango_context.device
        event_store.clear_queue()
        device_proxy.subscribe_event(
            "attenuationPolV",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        self.dish_manager_cm._component_quality_update("attenuationpolv", qual_before)
        event_store.wait_for_quality(qual_before)
        self.dish_manager_cm._component_quality_update("attenuationpolv", qual_after)
        event_store.wait_for_quality(qual_after)
