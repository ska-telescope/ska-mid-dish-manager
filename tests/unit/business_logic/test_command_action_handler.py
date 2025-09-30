"""Tests for ActionHandler class."""

import logging
from threading import Event

import pytest

from ska_mid_dish_manager.models.command_actions import (
    ActionHandler,
    FannedOutCommand,
)

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
class TestActionHandler:
    """Tests for ActionHandler class."""

    def setup_method(self):
        self.component_state = {}
        self.progress_calls = []
        self.status_calls = []
        self.result_calls = []

    def my_task_callback(self, progress=None, status=None, result=None):
        if progress is not None:
            self.progress_calls.append(progress)
        if status is not None:
            self.status_calls.append(status)
        if result is not None:
            self.result_calls.append(result)

    def reset_task_callbacks(self):
        self.progress_calls = []
        self.status_calls = []
        self.result_calls = []

    @pytest.mark.unit
    def test_action_handler_with_fanned_out_command(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False

        def mock_command(task_callback):
            self.component_state["attr"] = True
            return "OK", "command_id"

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            name="CommandX",
            command=mock_command,
            timeout_s=1,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
        )

        task_abort_event = Event()
        handler.execute(self.my_task_callback, task_abort_event)

        assert self.component_state["attr"] is True
        assert "Awaiting attr change to True" in self.progress_calls
        assert "CommandX completed" in self.progress_calls
        assert "HandlerX completed" in self.progress_calls
