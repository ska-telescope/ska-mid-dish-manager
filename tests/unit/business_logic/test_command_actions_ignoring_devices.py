"""Tests for ignoring devices in command Action."""

import logging
from threading import Event
from unittest import mock

import pytest
from ska_control_model import AdminMode
from ska_mid_dish_ds_manager.models.dish_enums import (
    DSOperatingMode,
    DSPowerState,
)
from ska_mid_dish_simulators.sim_enums import (
    SPFOperatingMode,
    SPFRxOperatingMode,
)

from ska_mid_dish_manager.models.command_actions import SetStandbyLPModeAction
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
)
from tests.utils import MethodCallsStore

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
class TestCommandActionsIgnoringDevices:
    """Tests for ignoring devices in command Action."""

    def setup_method(self):
        """Set up context."""
        sub_component_managers_mock = {
            "DS": mock.MagicMock(
                _component_state={
                    "operatingmode": DSOperatingMode.STANDBY,
                    "powerstate": DSPowerState.LOW_POWER,
                },
                execute_command=mock.MagicMock(return_value=(None, None)),
            ),
            "SPF": mock.MagicMock(
                _component_state={"operatingmode": SPFOperatingMode.STANDBY_LP},
                execute_command=mock.MagicMock(return_value=(None, None)),
            ),
            "SPFRX": mock.MagicMock(
                _component_state={
                    "operatingmode": SPFRxOperatingMode.STANDBY,
                    "adminmode": AdminMode.ONLINE,
                },
                execute_command=mock.MagicMock(return_value=(None, None)),
            ),
        }

        self.dish_manager_cm_mock = mock.MagicMock(
            _component_state={"dishmode": DishMode.STANDBY_LP}
        )
        self.dish_manager_cm_mock.sub_component_managers = sub_component_managers_mock

        self.progress_callback = MethodCallsStore()
        self.dish_manager_cm_mock._command_progress_callback = self.progress_callback
        self.dish_manager_cm_mock.sub_component_managers = sub_component_managers_mock

        def is_device_ignored(device: str):
            """Check whether the given device is ignored."""
            if device == "SPF":
                return self.dish_manager_cm_mock._component_state["ignorespf"]
            if device == "SPFRX":
                return self.dish_manager_cm_mock._component_state["ignorespfrx"]
            return False

        self.dish_manager_cm_mock.is_device_ignored = is_device_ignored

        self.dish_manager_cm_mock._component_state["ignorespf"] = False
        self.dish_manager_cm_mock._component_state["ignorespfrx"] = False

    def teardown_method(self):
        """Tear down context."""
        return

    def set_devices_ignored(self, spf_ignored, spfrx_ignored):
        """Set subservient device ignore values."""
        self.dish_manager_cm_mock._component_state["ignorespf"] = spf_ignored
        self.dish_manager_cm_mock._component_state["ignorespfrx"] = spfrx_ignored

    @pytest.mark.unit
    def test_ignoring_spf(self, caplog):
        """Test ignoring SPF device in command map."""
        caplog.set_level(logging.DEBUG)
        task_abort_event = Event()
        # Save any progress calls

        def my_task_callback(**kwargs):
            pass

        self.set_devices_ignored(spf_ignored=True, spfrx_ignored=False)

        SetStandbyLPModeAction(LOGGER, self.dish_manager_cm_mock).execute(
            my_task_callback, task_abort_event
        )

        expected_progress_updates = [
            "Fanned out commands: SPFRX.SetStandbyMode, DS.SetStandbyMode",
            "Awaiting dishmode change to STANDBY_LP",
            "SetStandbyLPMode completed",
        ]

        for msg in expected_progress_updates:
            self.progress_callback.wait_for_args((msg,))

        assert "SPF device is disabled. SetStandbyLPMode call ignored" in caplog.text

    @pytest.mark.unit
    def test_ignoring_spfrx(self, caplog):
        """Test ignoring SPFRx device in command map."""
        caplog.set_level(logging.DEBUG)
        task_abort_event = Event()

        def my_task_callback(**kwargs):
            pass

        self.set_devices_ignored(spf_ignored=False, spfrx_ignored=True)

        SetStandbyLPModeAction(LOGGER, self.dish_manager_cm_mock).execute(
            my_task_callback, task_abort_event
        )

        expected_progress_updates = [
            "Fanned out commands: SPF.SetStandbyLPMode, DS.SetStandbyMode",
            "Awaiting dishmode change to STANDBY_LP",
            "SetStandbyLPMode completed",
        ]

        for msg in expected_progress_updates:
            self.progress_callback.wait_for_args((msg,))

        assert "SPFRX device is disabled. SetStandbyMode call ignored" in caplog.text

    @pytest.mark.unit
    def test_ignoring_both_sub(self, caplog):
        """Test ignoring both subservient devices in command map."""
        caplog.set_level(logging.DEBUG)
        task_abort_event = Event()

        # pylint: disable=unused-argument
        def my_task_callback(progress=None, status=None, result=None):
            pass

        self.set_devices_ignored(spf_ignored=True, spfrx_ignored=True)

        SetStandbyLPModeAction(LOGGER, self.dish_manager_cm_mock).execute(
            my_task_callback, task_abort_event
        )

        expected_progress_updates = [
            "Fanned out commands: DS.SetStandbyMode",
            "Awaiting dishmode change to STANDBY_LP",
            "SetStandbyLPMode completed",
        ]

        for msg in expected_progress_updates:
            self.progress_callback.wait_for_args((msg,))

        assert "SPF device is disabled. SetStandbyLPMode call ignored" in caplog.text
        assert "SPFRX device is disabled. SetStandbyMode call ignored" in caplog.text
