"""Tests for ActionHandler class."""

import logging
import threading
import time
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
        assert "DeviceX.CommandX completed" in self.progress_calls
        assert "HandlerX completed" in self.progress_calls

    @pytest.mark.unit
    def test_command_timeout_no_action_timeout(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False

        def mock_command(task_callback):
            # Don't do anything so that the command times out
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

        assert self.component_state["attr"] is False
        assert "Awaiting attr change to True" in self.progress_calls
        assert (
            "DeviceX device timed out executing CommandX command with ID command_id"
            in self.progress_calls
        )
        assert (
            "Action 'HandlerX' failed. Fanned out commands: {'DeviceX CommandX (command_id)': "
            "<FannedOutCommandStatus.TIMED_OUT: 3>}"
        ) in self.progress_calls

    @pytest.mark.unit
    def test_action_timeout_no_command_timeout(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False

        def mock_command(task_callback):
            # Don't do anything so that the command times out
            return "OK", "command_id"

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            name="CommandX",
            command=mock_command,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            timeout_s=1,
        )

        task_abort_event = Event()
        handler.execute(self.my_task_callback, task_abort_event)

        assert self.component_state["attr"] is False
        assert "Awaiting attr change to True" in self.progress_calls
        assert (
            "Action 'HandlerX' timed out. Fanned out commands: {'DeviceX CommandX (command_id)': "
            "<FannedOutCommandStatus.RUNNING: 1>}"
        ) in self.progress_calls

    @pytest.mark.unit
    def test_command_timeout_with_action_timeout(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False

        def mock_command(task_callback):
            # Don't do anything so that the command times out
            return "OK", "command_id"

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            name="CommandX",
            command=mock_command,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            timeout_s=1,
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            timeout_s=2,
        )

        task_abort_event = Event()
        handler.execute(self.my_task_callback, task_abort_event)

        assert self.component_state["attr"] is False
        assert "Awaiting attr change to True" in self.progress_calls
        assert (
            "Action 'HandlerX' failed. Fanned out commands: {'DeviceX CommandX (command_id)': "
            "<FannedOutCommandStatus.TIMED_OUT: 3>}"
        ) in self.progress_calls

    @pytest.mark.unit
    def test_action_timeout_with_command_timeout(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False

        def mock_command(task_callback):
            # Don't do anything so that the command times out
            return "OK", "command_id"

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            name="CommandX",
            command=mock_command,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            timeout_s=2,
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            timeout_s=1,
        )

        task_abort_event = Event()
        handler.execute(self.my_task_callback, task_abort_event)

        assert self.component_state["attr"] is False
        assert "Awaiting attr change to True" in self.progress_calls
        assert (
            "Action 'HandlerX' timed out. Fanned out commands: {'DeviceX CommandX (command_id)': "
            "<FannedOutCommandStatus.RUNNING: 1>}"
        ) in self.progress_calls

    @pytest.mark.unit
    def test_action_no_timeouts(self):
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

        assert self.component_state["attr"] is True  # command completed execution
        assert "Awaiting" not in self.progress_calls  # assert we didn't wait for anything
        assert "HandlerX completed" in self.progress_calls  # command completes

    @pytest.mark.unit
    def test_action_abort(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False

        def mock_command(task_callback):
            # Don't do anything so that the command keeps running
            return "OK", "command_id"

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            name="CommandX",
            command=mock_command,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            timeout_s=10,
        )

        task_abort_event = Event()

        def trigger_abort_later(delay: float):
            time.sleep(delay)
            task_abort_event.set()

        # Start a thread which will abort the action after 5 seconds
        abort_thread = threading.Thread(target=trigger_abort_later, args=(5,), daemon=True)
        abort_thread.start()

        handler.execute(self.my_task_callback, task_abort_event)

        assert self.component_state["attr"] is False  # command completed execution
        assert (
            "Awaiting attr change to True" in self.progress_calls
        )  # assert we didn't wait for anything
        assert "HandlerX aborted" in self.progress_calls  # command completes
