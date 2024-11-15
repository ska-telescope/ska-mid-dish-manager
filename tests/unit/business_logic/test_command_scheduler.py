"""Unit tests for CommandScheduler class."""

import time
from functools import partial

import pytest

from ska_mid_dish_manager.models.command_scheduler import CommandScheduler


@pytest.mark.unit
class TestCommandScheduler:
    """Tests for ReleaseInfo"""

    def setup_method(self):
        """Set up context"""
        self.command_scheduler = CommandScheduler()

    def _counting_command(self, name, command_tracker):
        """Command which will increment a counter in command_tracker at each call."""
        if name in command_tracker:
            command_tracker[name] += 1
        else:
            command_tracker[name] = 1

    def test_submitting_command(self):
        """Test submitting a command."""
        command_tracker = {}

        command_name = "CommandA"
        command_to_submit = partial(self._counting_command, command_name, command_tracker)

        self.command_scheduler.submit_command(command_to_submit, command_name, 0.2)

        time.sleep(1.01)
        self.command_scheduler.stop()

        assert command_tracker[command_name] == 5

    def test_updating_command(self):
        """Test updating a command."""
        command_tracker = {}

        command_name = "CommandA"
        command_to_submit = partial(self._counting_command, command_name, command_tracker)

        self.command_scheduler.submit_command(command_to_submit, command_name, 0.2)

        # Wait (plus a tiny bit to make sure last execution is done) for command to execute 5 times
        time.sleep(1.01)
        assert command_tracker[command_name] == 5

        self.command_scheduler.update_command_period(command_name, 0.1)

        time.sleep(1.01)
        self.command_scheduler.stop()
        assert command_tracker[command_name] == 15

    def test_removing_command(self):
        """Test removing a command."""
        command_tracker = {}

        command_name = "CommandA"
        command_to_submit = partial(self._counting_command, command_name, command_tracker)

        self.command_scheduler.submit_command(command_to_submit, command_name, 0.2)

        time.sleep(1.01)

        assert command_tracker[command_name] == 5
        self.command_scheduler.remove_command(command_name)

        time.sleep(1.01)

        assert len(self.command_scheduler.commands) == 0
        assert command_tracker[command_name] == 5
        self.command_scheduler.stop()

    def test_submitting_multiple_commands(self):
        """Test submitting multiple commands."""
        command_tracker = {}

        command_a_name = "CommandA"
        command_to_submit = partial(self._counting_command, command_a_name, command_tracker)
        self.command_scheduler.submit_command(command_to_submit, command_a_name, 0.1)

        command_b_name = "CommandB"
        command_to_submit = partial(self._counting_command, command_b_name, command_tracker)
        self.command_scheduler.submit_command(command_to_submit, command_b_name, 0.2)

        time.sleep(1.01)
        self.command_scheduler.stop()

        assert command_tracker[command_a_name] == 10
        assert command_tracker[command_b_name] == 5

    def test_updating_with_multiple_commands(self):
        """Test updating with multiple commands."""
        command_tracker = {}

        command_a_name = "CommandA"
        command_to_submit = partial(self._counting_command, command_a_name, command_tracker)
        self.command_scheduler.submit_command(command_to_submit, command_a_name, 0.1)

        command_b_name = "CommandB"
        command_to_submit = partial(self._counting_command, command_b_name, command_tracker)
        self.command_scheduler.submit_command(command_to_submit, command_b_name, 0.2)

        time.sleep(1.01)

        assert command_tracker[command_a_name] == 10
        assert command_tracker[command_b_name] == 5

        self.command_scheduler.update_command_period(command_a_name, 0.5)
        self.command_scheduler.update_command_period(command_b_name, 0.2)

        time.sleep(1.01)
        self.command_scheduler.stop()

        assert command_tracker[command_a_name] == 12
        assert command_tracker[command_b_name] == 10

    def test_removing_with_multiple_commands(self):
        """Test removing with multiple commands."""
        command_tracker = {}

        command_a_name = "CommandA"
        command_to_submit = partial(self._counting_command, command_a_name, command_tracker)
        self.command_scheduler.submit_command(command_to_submit, command_a_name, 0.1)

        command_b_name = "CommandB"
        command_to_submit = partial(self._counting_command, command_b_name, command_tracker)
        self.command_scheduler.submit_command(command_to_submit, command_b_name, 0.2)

        time.sleep(1.01)

        assert command_tracker[command_a_name] == 10
        assert command_tracker[command_b_name] == 5

        self.command_scheduler.remove_command(command_a_name)

        time.sleep(0.41)
        self.command_scheduler.stop()

        assert command_tracker[command_a_name] == 10
        assert command_tracker[command_b_name] == 7
