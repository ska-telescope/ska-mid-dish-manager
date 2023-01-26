"""Unit tests verifying model against DS_SetStowMode transition."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestStowMode:
    """Tests for SetStowMode"""

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
    def test_stow_mode(
        self,
        event_store_class,
    ):
        main_event_store = event_store_class()
        progress_event_store = event_store_class()

        device_proxy = self.tango_context.device
        device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            main_event_store,
        )

        device_proxy.subscribe_event(
            "longRunningCommandProgress",
            tango.EventType.CHANGE_EVENT,
            progress_event_store,
        )

        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.component_managers["DS"]

        ds_cm.read_update_component_state = MagicMock()

        device_proxy.SetStowMode()

        # Pretend DS goes into STOW
        ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)
        main_event_store.wait_for_value(DishMode.STOW)

        expected_progress_updates = [
            "Stow called on DS",
            (
                "Awaiting DS operatingmode to change to "
                "[<DSOperatingMode.STOW: 5>]"
            ),
            "Awaiting dishmode change to 5",
            ("DS operatingmode changed to, [<DSOperatingMode.STOW: 5>]"),
            "SetStowMode completed",
        ]

        events = progress_event_store.wait_for_progress_update(
            expected_progress_updates[-1], timeout=6
        )

        events_string = "".join([str(event) for event in events])

        # Check that all the expected progress messages appeared
        # in the event store
        for message in expected_progress_updates:
            assert message in events_string
