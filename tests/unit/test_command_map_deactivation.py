"""Test that subservient devices can be deactivated in the CommandMap."""
import logging
from threading import Event
from unittest import mock

import pytest

from ska_mid_dish_manager.models.command_map import CommandMap

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.models.command_map.SubmittedSlowCommand")
def test_deactivating_subdevice(patched_slow_command):
    """Test deactivating subservient devices in command map."""
    # pylint: disable=no-member
    mock_command_instance = mock.MagicMock()
    mock_command_instance.return_value = (None, None)

    patched_slow_command.return_value = mock_command_instance

    # Set mocked dishmode to desired value so that the command map doesn't wait forever
    dish_manager_cm_mock = mock.MagicMock(component_state={"dishmode": 2})
    command_tracker_mock = mock.MagicMock()
    task_abort_event = Event()

    # Set up mock for sub_component_managers
    sub_component_managers_mock = {
        "DS": mock.MagicMock(component_state={"operatingmode": 2}),
    }
    dish_manager_cm_mock.sub_component_managers = sub_component_managers_mock

    # pylint: disable=protected-access
    dish_manager_cm_mock._ignore_spf.return_value = True
    dish_manager_cm_mock._ignore_spfrx.return_value = True

    command_map = CommandMap(dish_manager_cm_mock, command_tracker_mock, LOGGER)

    # Save any progress calls
    progress_calls = []

    # pylint: disable=unused-argument
    def my_task_callback(progress=None, status=None, result=None):
        if progress is not None:
            progress_calls.append(progress)

    command_map.set_standby_lp_mode(
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
