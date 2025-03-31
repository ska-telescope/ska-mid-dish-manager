""""Custom command classes for commands requiring overrides to do()."""

import functools
import logging
import warnings
from typing import Any, Optional

from ska_control_model import ResultCode, TaskStatus
from ska_tango_base.commands import FastCommand, SubmittedSlowCommand


class AbortCommand(SubmittedSlowCommand):
    """A custom class for Abort Command."""

    def do(self: SubmittedSlowCommand, *args: Any, **kwargs: Any) -> tuple[ResultCode, str]:
        """
        Stateless hook for command functionality.

        :param args: positional args to the component manager method
        :param kwargs: keyword args to the component manager method

        :return: A tuple containing the result code (e.g. STARTED)
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

        if status == TaskStatus.IN_PROGRESS:
            return ResultCode.STARTED, command_id
        if status == TaskStatus.REJECTED:
            return ResultCode.REJECTED, command_id
        return (
            ResultCode.FAILED,
            f"{status.name} was returned by command method with message: {message}",
        )


class AbortCommandsDeprecatedCommand(SubmittedSlowCommand):
    """A custom class for AbortCommands Command."""

    def do(self: SubmittedSlowCommand, *args: Any, **kwargs: Any) -> tuple[ResultCode, str]:
        """
        Stateless hook for command functionality.

        :param args: positional args to the component manager method
        :param kwargs: keyword args to the component manager method

        :return: A tuple containing the result code (e.g. STARTED)
            and a string message containing a command_id (if
            the command has been accepted) or an informational message
            (if the command was rejected)
        """
        warnings.warn(
            "AbortCommands is deprecated, use Abort instead. "
            "Issuing Abort sequence for requested command.",
            DeprecationWarning,
        )
        command_id = self._command_tracker.new_command(
            self._command_name, completed_callback=self._completed
        )
        method = getattr(self._component_manager, self._method_name)
        status, message = method(
            *args,
            functools.partial(self._command_tracker.update_command_info, command_id),
            **kwargs,
        )

        if status == TaskStatus.IN_PROGRESS:
            return ResultCode.STARTED, command_id
        if status == TaskStatus.REJECTED:
            return ResultCode.REJECTED, command_id
        return (
            ResultCode.FAILED,
            f"{status.name} was returned by command method with message: {message}",
        )


class ApplyPointingModelCommand(FastCommand):
    """Class for handling band pointing parameters given a JSON input."""

    def __init__(self, component_manager, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialise a new ApplyPointingModelCommand instance.

        :param component_manager: the device to which this command belongs.
        :param logger: a logger for this command to use.
        """
        self._component_manager = component_manager
        super().__init__(logger)

    def do(self, *args: Any, **kwargs: Any) -> tuple[ResultCode, str]:
        """
        Implement ApplyPointingModel command functionality.

        :param args: JSON object with a schema similar to this::

            {
                "interface": "...",
                "antenna": "....",
                "band": "`Band_`...",
                "attrs": {...},
                "coefficients": {
                    "IA": {...},
                    ...
                    ...
                    "HESE8":{...}
                },
                "rms_fits":
                {
                    "xel_rms": {...},
                    "el_rms": {...},
                    "sky_rms": {...}
                }
            }

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        return self._component_manager.apply_pointing_model(*args)


class SetKValueCommand(FastCommand):
    """Class for handling the SetKValue command."""

    def __init__(self, component_manager, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialise a new SetKValueCommand instance.

        :param component_manager: the device to which this command belongs.
        :param logger: a logger for this command to use.
        """
        self._component_manager = component_manager
        super().__init__(logger)

    def do(self, *args: Any, **kwargs: Any) -> tuple[ResultCode, str]:
        """
        Implement SetKValue command functionality.

        :param args: k value.
        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return self._component_manager.set_kvalue(*args)


class StowCommand(SubmittedSlowCommand):
    """A custom class for Stow Command."""

    def do(self: SubmittedSlowCommand, *args: Any, **kwargs: Any) -> tuple[ResultCode, str]:
        """
        Stateless hook for command functionality.

        :param args: positional args to the component manager method
        :param kwargs: keyword args to the component manager method

        :return: A tuple containing the result code (e.g. STARTED)
            and a string message if the command has been accepted or failed
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

        # the stow command is not tracked from this point
        # dont return the command id to the client
        if status == TaskStatus.COMPLETED:
            return ResultCode.STARTED, "Stow called on Dish Structure, monitor dishmode for STOW"
        return (
            ResultCode.FAILED,
            f"{status.name} was returned by command method with message: {message}",
        )
