"""Utility decorators."""

import functools
import time
from typing import Any, Callable

from ska_control_model import ResultCode, TaskStatus
from ska_tango_base.long_running_commands import LRCReqType, long_running_command

from ska_mid_dish_manager.models.constants import OPERATOR_TAG

SLOW_WRITE_WARN_THRESHOLD_SECONDS = 0.5


def time_tango_write() -> Callable[[Any], Any]:
    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return func(self, *args, **kwargs)
            finally:
                # using a timer that is not affected by system clock changes
                duration = time.perf_counter() - start
                if duration > SLOW_WRITE_WARN_THRESHOLD_SECONDS:
                    self.logger.warning(
                        "SLOW WRITE: %s took %.3f s",
                        func.__name__,  # ty: ignore[unresolved-attribute]
                        duration,
                    )

        return wrapper

    return decorator


def record_command(record_mode: bool | Callable[..., Any] = False) -> Callable[..., Any]:
    """Record 'lastcommandinvoked' and optionally 'lastcommandedmode' before calling the command.

    Can be used with or without arguments:

        @record_command          # records only 'lastcommandinvoked'
        @record_command(True)    # records both 'lastcommandinvoked' and 'lastcommandedmode'

    :param record_mode: Whether to also record 'lastcommandedmode'. Defaults to False.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            device_instance = args[0]
            component_manager = device_instance.component_manager
            command_and_time = (str(time.time()), func.__name__)  # ty: ignore[unresolved-attribute]
            if record_mode is True:
                component_manager._update_component_state(
                    lastcommandinvoked=command_and_time,
                    lastcommandedmode=command_and_time,
                )
            else:
                component_manager._update_component_state(lastcommandinvoked=command_and_time)
            return func(*args, **kwargs)

        return wrapper

    # Used without parentheses: @record_command
    if callable(record_mode):
        func, record_mode = record_mode, False
        return decorator(func)

    # Used with parentheses: @record_command() or @record_command(True)
    return decorator


def log_tango_command() -> Callable[[Any], Any]:
    """Log Tango command details with operator tag.

    This decorator logs the command name and arguments using the device logger
    so logs can be filtered downstream via the operator tag.
    """

    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            logger = getattr(self, "logger", None)
            if logger:
                if args:
                    logger.info(
                        "Tango command %s called with param %s.",
                        func.__name__,  # ty: ignore[unresolved-attribute]
                        args,
                        extra=OPERATOR_TAG,
                    )
                else:
                    logger.info(
                        "Tango command %s called.",
                        func.__name__,  # ty: ignore[unresolved-attribute]
                        extra=OPERATOR_TAG,
                    )
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def log_tango_attr_write() -> Callable[[Any], Any]:
    """Log Tango attribute write details with operator tag.

    This decorator logs the attribute name and value using the device logger
    so logs can be filtered downstream via the operator tag.
    """

    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            logger = getattr(self, "logger", None)
            if logger:
                logger.info(
                    "Tango attribute write called on %s with param %s.",
                    func.__name__,  # ty: ignore[unresolved-attribute]
                    args,
                    extra=OPERATOR_TAG,
                )
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def last_command_failure_decorator(func: Any) -> Any:
    """Record the last command failure."""

    @functools.wraps(func)
    def last_command_failure_wrapper(*args: Any, **kwargs: Any) -> Any:
        device_instance = args[0]
        try:
            result = func(*args, **kwargs)
            if isinstance(result, tuple):
                status, reason = result
                failure_states: tuple[Any, ...] = ()
                if isinstance(status, TaskStatus):
                    failure_states = (
                        TaskStatus.FAILED,
                        TaskStatus.REJECTED,
                    )
                elif isinstance(status, ResultCode):
                    failure_states = (
                        ResultCode.FAILED,
                        ResultCode.REJECTED,
                        ResultCode.NOT_ALLOWED,
                        ResultCode.ABORTED,
                        ResultCode.UNKNOWN,
                    )
                if status in failure_states:
                    device_instance._update_component_state(
                        lastcommandfailure=(
                            str(time.time()),
                            func.__name__,
                            str(reason),
                        )
                    )
            return result
        except Exception as ex:
            device_instance._update_component_state(
                lastcommandfailure=(
                    str(time.time()),
                    func.__name__,
                    str(ex),
                )
            )
            raise

    return last_command_failure_wrapper


def slow_command(
    *, check_allowed: bool = True, **cmd_kwargs: Any
) -> Callable[[Callable[..., Any]], Any]:
    """Mark a DishManager method as a long running command.

    By default, the command is gated by the dish mode model: the check is built from the
    method's name and runs when the command is queued and again just before it executes.

    :param check_allowed: Whether to gate the command with the dish mode model. Set to False
        for commands the model has no rule for.
    :param cmd_kwargs: Passed on to long_running_command, and from there to tango.server.command.
    """

    def decorator(tango_cmd: Callable[..., Any]) -> Any:
        if not check_allowed:
            return long_running_command(tango_cmd, **cmd_kwargs)

        command_name = tango_cmd.__name__

        def is_allowed(device: Any, request_type: LRCReqType = LRCReqType.ENQUEUE_REQ) -> bool:
            return device.is_command_allowed(command_name)

        # Tango looks up fisallowed by name, so every command's check needs a unique name.
        # Without this, all commands share the check of the last command decorated.
        is_allowed.__name__ = f"is_{command_name}_allowed"
        is_allowed.__qualname__ = is_allowed.__name__

        return long_running_command(tango_cmd, fisallowed=is_allowed, **cmd_kwargs)

    return decorator
