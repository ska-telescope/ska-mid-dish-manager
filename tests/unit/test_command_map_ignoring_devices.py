"""Tests for ignoring devices in CommandMap"."""

import logging
from threading import Event
from unittest import mock

import pytest

from ska_mid_dish_manager.models.command_map import CommandMap
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
@pytest.mark.forked
class TestCommandMapIgnoringDevices:
    """Tests for ignoring devices in CommandMap"""

    # pylint: disable=protected-access,attribute-defined-outside-init
    def setup_method(self):
        """Set up context"""
        sub_component_managers_mock = {
            "DS": mock.MagicMock(component_state={"operatingmode": DSOperatingMode.STANDBY_LP}),
            "SPF": mock.MagicMock(component_state={"operatingmode": SPFOperatingMode.STANDBY_LP}),
            "SPFRX": mock.MagicMock(component_state={"operatingmode": SPFRxOperatingMode.STANDBY}),
        }

        self.dish_manager_cm_mock = mock.MagicMock(
            component_state={"dishmode": DishMode.STANDBY_LP}
        )
        self.dish_manager_cm_mock.sub_component_managers = sub_component_managers_mock

        def is_device_ignored(device: str):
            """Check whether the given device is ignored."""
            if device == "SPF":
                return self.dish_manager_cm_mock.component_state["ignorespf"]
            if device == "SPFRX":
                return self.dish_manager_cm_mock.component_state["ignorespfrx"]
            return False

        self.dish_manager_cm_mock.is_device_ignored = is_device_ignored

        self.dish_manager_cm_mock.component_state["ignorespf"] = False
        self.dish_manager_cm_mock.component_state["ignorespfrx"] = False
        command_tracker_mock = mock.MagicMock()

        self.command_map = CommandMap(self.dish_manager_cm_mock, command_tracker_mock, LOGGER)

    def teardown_method(self):
        """Tear down context"""
        return

    def set_devices_ignored(self, spf_ignored, spfrx_ignored):
        """Set subservient device ignore values."""
        self.dish_manager_cm_mock.component_state["ignorespf"] = spf_ignored
        self.dish_manager_cm_mock.component_state["ignorespfrx"] = spfrx_ignored

    @pytest.mark.unit
    @mock.patch("ska_mid_dish_manager.models.command_map.SubmittedSlowCommand")
    def test_ignoring_spf(self, patched_slow_command):
        """Test ignoring SPF device in command map."""
        mock_command_instance = mock.MagicMock()
        mock_command_instance.return_value = (None, None)

        patched_slow_command.return_value = mock_command_instance

        # Set mocked dishmode to desired value so that the command map doesn't wait forever
        task_abort_event = Event()

        # Save any progress calls
        progress_calls = []

        # pylint: disable=unused-argument
        def my_task_callback(progress=None, status=None, result=None):
            if progress is not None:
                progress_calls.append(progress)

        self.set_devices_ignored(spf_ignored=True, spfrx_ignored=False)

        assert self.command_map.is_device_ignored("SPF")
        assert not self.command_map.is_device_ignored("SPFRX")

        self.command_map.set_standby_lp_mode(
            task_callback=my_task_callback, task_abort_event=task_abort_event
        )

        expected_progress_updates = [
            "SetStandbyLPMode called on DS",
            "SPF device is disabled. SetStandbyLPMode call ignored",
            "SetStandbyMode called on SPFRx",
            "Awaiting dishMode change to STANDBY_LP",
            "SetStandbyLPMode completed",
        ]

        progress_string = "".join([str(event) for event in progress_calls])

        for progress_update in expected_progress_updates:
            assert progress_update in progress_string

    @pytest.mark.unit
    @mock.patch("ska_mid_dish_manager.models.command_map.SubmittedSlowCommand")
    def test_ignoring_spfrx(self, patched_slow_command):
        """Test ignoring SPFRx device in command map."""
        mock_command_instance = mock.MagicMock()
        mock_command_instance.return_value = (None, None)

        patched_slow_command.return_value = mock_command_instance

        # Set mocked dishmode to desired value so that the command map doesn't wait forever
        task_abort_event = Event()

        # Save any progress calls
        progress_calls = []

        # pylint: disable=unused-argument
        def my_task_callback(progress=None, status=None, result=None):
            if progress is not None:
                progress_calls.append(progress)

        self.set_devices_ignored(spf_ignored=False, spfrx_ignored=True)

        assert not self.command_map.is_device_ignored("SPF")
        assert self.command_map.is_device_ignored("SPFRX")

        self.command_map.set_standby_lp_mode(
            task_callback=my_task_callback, task_abort_event=task_abort_event
        )

        expected_progress_updates = [
            "SetStandbyLPMode called on DS",
            "SetStandbyLPMode called on SPF",
            "SPFRX device is disabled. SetStandbyMode call ignored",
            "Awaiting dishMode change to STANDBY_LP",
            "SetStandbyLPMode completed",
        ]

        progress_string = "".join([str(event) for event in progress_calls])

        for progress_update in expected_progress_updates:
            assert progress_update in progress_string

    @pytest.mark.unit
    @mock.patch("ska_mid_dish_manager.models.command_map.SubmittedSlowCommand")
    def test_ignoring_both_sub(self, patched_slow_command):
        """Test ignoring both subservient devices in command map."""
        mock_command_instance = mock.MagicMock()
        mock_command_instance.return_value = (None, None)

        patched_slow_command.return_value = mock_command_instance

        # Set mocked dishmode to desired value so that the command map doesn't wait forever
        task_abort_event = Event()

        # Save any progress calls
        progress_calls = []

        # pylint: disable=unused-argument
        def my_task_callback(progress=None, status=None, result=None):
            if progress is not None:
                progress_calls.append(progress)

        self.set_devices_ignored(spf_ignored=True, spfrx_ignored=True)

        assert self.command_map.is_device_ignored("SPF")
        assert self.command_map.is_device_ignored("SPFRX")

        self.command_map.set_standby_lp_mode(
            task_callback=my_task_callback, task_abort_event=task_abort_event
        )

        expected_progress_updates = [
            "SetStandbyLPMode called on DS",
            "SPF device is disabled. SetStandbyLPMode call ignored",
            "SPFRX device is disabled. SetStandbyMode call ignored",
            "Awaiting dishMode change to STANDBY_LP",
            "SetStandbyLPMode completed",
        ]

        progress_string = "".join([str(event) for event in progress_calls])

        for progress_update in expected_progress_updates:
            assert progress_update in progress_string
