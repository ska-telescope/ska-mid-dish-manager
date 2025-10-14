"""Tests for ignoring devices in CommandMap"."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from ska_mid_dish_manager.models.dish_enums import DishMode

LOGGER = logging.getLogger(__name__)


@pytest.fixture
@pytest.mark.unit
def mock_cm():
    """Return a mocked component manager for Dish Manager."""

    class MockCompManager:
        def __init__(self):
            self.logger = MagicMock()
            self._dish_manager_cm = MagicMock()
            self._dish_manager_cm.component_state = {"dishMode": DishMode.STANDBY_FP}
            self._dish_manager_cm.sub_component_managers = {"B5DC": MagicMock()}

        def is_device_ignored(self, device):
            return device == "B5DC"  # Only B5DC is ignored

        def _fan_out_cmd(self, *args, **kwargs):
            return "Commands called"  # Should not be called for B5DC since it is ignored

    return MockCompManager()


def test_ignored_device_skips_command(mock_cm):
    task_callback = MagicMock()
    task_abort_event = MagicMock()
    task_abort_event.is_set.return_value = False

    commands_for_sub_devices = {
        "B5DC": {"command": "RandomCommandB5DC"},
        "DS": {"command": "RandomCommandDS"},
    }

    # Use a patch to monitor calls to _fan_out_cmd
    with patch.object(mock_cm, "_fan_out_cmd", return_value="cmd_id") as mock_fanout:
        mock_cm._run_long_running_command(
            task_callback=task_callback,
            task_abort_event=task_abort_event,
            commands_for_sub_devices=commands_for_sub_devices,
            running_command="SetStandbyFPMode",
            awaited_event_attributes=[],
            awaited_event_values=[],
        )

    # The _fan_out_cmd function should only be called for "DS", not "B5DC"
    mock_fanout.assert_called_once()
    assert mock_fanout.call_args[0][1] == "DS"

    # task_callback called with the "ignored" message for B5DC
    task_callback.assert_any_call(
        progress="B5DC device is disabled. RandomCommandB5DC call ignored"
    )
