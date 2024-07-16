""""A submitted slow command with do() overridden"""

import functools
from typing import Any

from ska_control_model import ResultCode, TaskStatus
from ska_tango_base.commands import SubmittedSlowCommand


class ImmediateSlowCommand(SubmittedSlowCommand):
    """A custom class for Dish Manager's Submitted Slow Command"""

    def do(self: SubmittedSlowCommand, *args: Any, **kwargs: Any) -> tuple[ResultCode, str]:
        """
        Stateless hook for command functionality.

        :param args: positional args to the component manager method
        :param kwargs: keyword args to the component manager method

        :return: A tuple containing the task status (e.g. COMPLETED)
            and a string message containing a command_id (if
            the command has been accepted) or an informational message
            (if the command was rejected)
        """
        command_id = self._command_tracker.new_command(
            self._command_name, completed_callback=self._completed
        )
        method = getattr(self._component_manager, self._method_name)
        status, message = method(
            *args,
            functools.partial(self._command_tracker.update_command_info, command_id),
            **kwargs,
        )

        if status == TaskStatus.COMPLETED:
            return ResultCode.STARTED, command_id
        return (
            ResultCode.FAILED,
            f"Expected COMPLETED task status, but {status.name} was returned "
            f"by command method with message: {message}",
        )
