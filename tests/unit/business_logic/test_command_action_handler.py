"""Tests for ActionHandler class."""

import logging
import threading
import time
from threading import Event

import pytest

from ska_mid_dish_manager.models.command_actions import ActionHandler, FannedOutCommand
from tests.utils import MethodCallsStore

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
class TestActionHandler:
    """Tests for ActionHandler class."""

    def setup_method(self):
        self.component_state = {}
        self.status_calls = []
        self.result_calls = []

    def my_task_callback(self, **kwargs):
        if kwargs.get("status") is not None:
            self.status_calls.append(kwargs["status"])
        if kwargs.get("result") is not None:
            self.result_calls.append(kwargs["result"])

    def reset_task_callbacks(self):
        self.status_calls = []
        self.result_calls = []

    @pytest.mark.unit
    def test_action_handler_with_fanned_out_command(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False

        def mock_command(task_callback=None):
            self.component_state["attr"] = True
            return "OK", "fanned out command msg"

        progress_callback = MethodCallsStore()

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            command_name="CommandX",
            command=mock_command,
            timeout_s=1,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
        )

        task_abort_event = Event()
        handler.execute(self.my_task_callback, task_abort_event)

        assert self.component_state["attr"] is True
        handler.progress_callback.wait_for_args(("Awaiting attr change to True",))
        handler.progress_callback.wait_for_args(("DeviceX.CommandX completed",))
        handler.progress_callback.wait_for_args(("HandlerX completed",))

    @pytest.mark.unit
    def test_command_timeout_no_action_timeout(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False

        progress_callback = MethodCallsStore()

        def mock_command(task_callback=None):
            # Don't do anything so that the command times out
            return "OK", "fanned out command msg"

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            command_name="CommandX",
            command=mock_command,
            timeout_s=1,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
        )

        task_abort_event = Event()
        handler.execute(self.my_task_callback, task_abort_event)

        assert self.component_state["attr"] is False
        handler.progress_callback.wait_for_args(("Fanned out commands: DeviceX.CommandX",))
        handler.progress_callback.wait_for_args(("Awaiting attr change to True",))
        handler.progress_callback.wait_for_args(
            ("DeviceX device timed out executing CommandX command",)
        )
        handler.progress_callback.wait_for_args(("DeviceX.CommandX timed out",))
        handler.progress_callback.wait_for_args(
            ("Action 'HandlerX' failed. Fanned out commands: {'DeviceX.CommandX': 'TIMED_OUT'}",)
        )

    @pytest.mark.unit
    def test_action_timeout_no_command_timeout(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False
        progress_callback = MethodCallsStore()

        def mock_command(task_callback=None):
            # Don't do anything so that the command times out
            return "OK", "fanned out command msg"

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            command_name="CommandX",
            command=mock_command,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
            timeout_s=1,
        )

        task_abort_event = Event()
        handler.execute(self.my_task_callback, task_abort_event)

        assert self.component_state["attr"] is False
        handler.progress_callback.wait_for_args(("Awaiting attr change to True",))
        handler.progress_callback.wait_for_args(
            ("Action 'HandlerX' timed out. Fanned out commands: {'DeviceX.CommandX': 'RUNNING'}",)
        )

    @pytest.mark.unit
    def test_command_timeout_with_action_timeout(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False
        progress_callback = MethodCallsStore()

        def mock_command(task_callback=None):
            # Don't do anything so that the command times out
            return "OK", "fanned out command msg"

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            command_name="CommandX",
            command=mock_command,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
            timeout_s=1,
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
            timeout_s=2,
        )

        task_abort_event = Event()
        handler.execute(self.my_task_callback, task_abort_event)

        assert self.component_state["attr"] is False
        handler.progress_callback.wait_for_args(("Awaiting attr change to True",))
        handler.progress_callback.wait_for_args(
            ("Action 'HandlerX' failed. Fanned out commands: {'DeviceX.CommandX': 'TIMED_OUT'}",)
        )

    @pytest.mark.unit
    def test_action_timeout_with_command_timeout(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False
        progress_callback = MethodCallsStore()

        def mock_command(task_callback=None):
            # Don't do anything so that the command times out
            return "OK", "fanned out command msg"

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            command_name="CommandX",
            command=mock_command,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
            timeout_s=2,
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
            timeout_s=1,
        )

        task_abort_event = Event()
        handler.execute(self.my_task_callback, task_abort_event)

        assert self.component_state["attr"] is False
        handler.progress_callback.wait_for_args(("Awaiting attr change to True",))
        handler.progress_callback.wait_for_args(
            ("Action 'HandlerX' timed out. Fanned out commands: {'DeviceX.CommandX': 'RUNNING'}",)
        )

    @pytest.mark.unit
    def test_action_no_timeouts(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False
        progress_callback = MethodCallsStore()

        def mock_command(task_callback=None):
            self.component_state["attr"] = True
            return "OK", "fanned out command msg"

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            command_name="CommandX",
            command=mock_command,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
        )

        task_abort_event = Event()
        handler.execute(self.my_task_callback, task_abort_event)

        assert self.component_state["attr"] is True  # command completed execution
        handler.progress_callback.wait_for_args(("Fanned out commands: DeviceX.CommandX",))
        handler.progress_callback.wait_for_args(("Awaiting attr change to True",))
        handler.progress_callback.wait_for_args(("DeviceX attr changed to True",))
        handler.progress_callback.wait_for_args(("DeviceX.CommandX completed",))
        handler.progress_callback.wait_for_args(("HandlerX completed",))

    @pytest.mark.unit
    def test_action_abort(self):
        self.reset_task_callbacks()
        self.component_state["attr"] = False
        progress_callback = MethodCallsStore()

        def mock_command(task_callback=None):
            # Don't do anything so that the command keeps running
            return "OK", "fanned out command msg"

        fanned_out = FannedOutCommand(
            LOGGER,
            device="DeviceX",
            command_name="CommandX",
            command=mock_command,
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
        )

        handler = ActionHandler(
            LOGGER,
            "HandlerX",
            [fanned_out],
            component_state=self.component_state,
            awaited_component_state={"attr": True},
            progress_callback=progress_callback,
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
        handler.progress_callback.wait_for_args(("Awaiting attr change to True",))
        handler.progress_callback.wait_for_args(("HandlerX aborted",))
