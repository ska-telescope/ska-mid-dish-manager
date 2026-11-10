"""Tests for ActionHandler class."""

import logging
import threading
import time
from threading import Event

import pytest
from ska_tango_base.executor import TaskAborted

from ska_mid_dish_manager.models.command_actions import ActionHandler
from ska_mid_dish_manager.models.fanned_out_command import FannedOutCommand
from tests.utils import MethodCallsStore

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
class TestActionHandler:
    """Tests for ActionHandler class."""

    def setup_method(self):
        self.component_state = {}

    @pytest.mark.unit
    def test_action_handler_with_fanned_out_command(self):
        self.component_state["attr"] = False

        def mock_command():
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
        handler.execute(task_abort_event)

        assert self.component_state["attr"] is True
        expected_progress_updates = [
            "Awaiting attr change to True",
            "DeviceX.CommandX completed",
            "HandlerX completed.",
        ]
        progress_updates = progress_callback.get_kwargs_queue()
        progress_messages = [update["progress_info"] for update in progress_updates]
        for msg in expected_progress_updates:
            assert msg in progress_messages

    @pytest.mark.unit
    def test_command_timeout_no_action_timeout(self):
        self.component_state["attr"] = False

        progress_callback = MethodCallsStore()

        def mock_command():
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
        handler.execute(task_abort_event)

        expected_progress_updates = [
            "Fanned out commands: DeviceX.CommandX",
            "Awaiting attr change to True",
            # "DeviceX device timed out executing CommandX command",
            "DeviceX.CommandX timed out",
            "Action 'HandlerX' failed. Fanned out commands: {'DeviceX.CommandX': 'TIMED_OUT'}",
        ]
        assert self.component_state["attr"] is False
        progress_updates = progress_callback.get_kwargs_queue()
        progress_messages = [update["progress_info"] for update in progress_updates]
        for msg in expected_progress_updates:
            assert msg in progress_messages

    @pytest.mark.unit
    def test_action_timeout_no_command_timeout(self):
        self.component_state["attr"] = False
        progress_callback = MethodCallsStore()

        def mock_command():
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
        handler.execute(task_abort_event)

        assert self.component_state["attr"] is False
        progress_callback.wait_for_kwargs({"progress_info": "Awaiting attr change to True"})
        progress_callback.wait_for_kwargs(
            {
                "progress_info": "Action 'HandlerX' timed out. Fanned out commands: "
                "{'DeviceX.CommandX': 'IN_PROGRESS'}"
            }
        )

    @pytest.mark.unit
    def test_command_timeout_with_action_timeout(self):
        self.component_state["attr"] = False
        progress_callback = MethodCallsStore()

        def mock_command():
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
        handler.execute(task_abort_event)

        assert self.component_state["attr"] is False
        progress_callback.wait_for_kwargs({"progress_info": "Awaiting attr change to True"})
        progress_callback.wait_for_kwargs(
            {
                "progress_info": (
                    "Action 'HandlerX' failed. Fanned out commands: "
                    "{'DeviceX.CommandX': 'TIMED_OUT'}"
                )
            }
        )

    @pytest.mark.unit
    def test_action_timeout_with_command_timeout(self):
        self.component_state["attr"] = False
        progress_callback = MethodCallsStore()

        def mock_command():
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
        handler.execute(task_abort_event)

        assert self.component_state["attr"] is False
        progress_callback.wait_for_kwargs({"progress_info": "Awaiting attr change to True"})
        progress_callback.wait_for_kwargs(
            {
                "progress_info": (
                    "Action 'HandlerX' timed out. Fanned out commands: "
                    "{'DeviceX.CommandX': 'IN_PROGRESS'}"
                )
            }
        )

    @pytest.mark.unit
    def test_action_no_timeouts(self):
        self.component_state["attr"] = False
        progress_callback = MethodCallsStore()

        def mock_command():
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
        expected_progress_updates = [
            "Fanned out commands: DeviceX.CommandX",
            "Awaiting attr change to True",
            "DeviceX attr changed to True",
            "DeviceX.CommandX completed",
            "HandlerX completed.",
        ]
        task_abort_event = Event()
        handler.execute(task_abort_event)

        assert self.component_state["attr"] is True  # command completed execution
        progress_updates = progress_callback.get_kwargs_queue()
        progress_messages = [update["progress_info"] for update in progress_updates]
        for msg in expected_progress_updates:
            assert msg in progress_messages

    @pytest.mark.unit
    def test_action_abort(self):
        self.component_state["attr"] = False
        progress_callback = MethodCallsStore()

        def mock_command():
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

        with pytest.raises(TaskAborted):
            handler.execute(task_abort_event)

        assert self.component_state["attr"] is False  # command completed execution
        progress_callback.wait_for_kwargs({"progress_info": "Awaiting attr change to True"})
        progress_callback.wait_for_kwargs({"progress_info": "HandlerX aborted"})
