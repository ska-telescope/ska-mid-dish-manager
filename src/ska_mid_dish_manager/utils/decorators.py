"""Utility decorators."""

import functools
import logging
import time
from typing import Any, Callable

from ska_control_model import CommunicationStatus


def time_tango_write(attr_name: str, warn_threshold: float = 0.2) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            try:
                return func(self, *args, **kwargs)
            finally:
                # using a timer that is not affected by system clock changes
                duration = time.monotonic() - start
                if duration > warn_threshold:
                    self.logger.warning(
                        "SLOW WRITE: %s took %.3f s",
                        attr_name,
                        duration,
                    )
                else:
                    self.logger.debug(
                        "WRITE: %s took %.3f s",
                        attr_name,
                        duration,
                    )

        return wrapper

    return decorator


def record_command(record_mode: bool = False) -> Callable:
    """Return a function that records the 'lastcommandinvoked' and or 'lastcommandedmode'
       before calling the command.

    :param record_mode: Flag to update both or only 'lastcommandinvoked', 'lastcommandedmode'.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            device_instance = args[0]
            component_manager = device_instance.component_manager
            command_and_time = (str(time.time()), func.__name__)
            # record both if True
            if record_mode:
                component_manager._update_component_state(
                    lastcommandinvoked=command_and_time,
                    lastcommandedmode=command_and_time,
                )
            else:
                component_manager._update_component_state(lastcommandinvoked=command_and_time)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def check_communicating(func: Any) -> Any:
    """Return a function that checks component communication before calling a function.

    The component manager needs to have established communications with
    the component before the function is called but if there is no communication
    the function will be sent to the component and the client will be informed

    This function is intended to be used as a decorator:

    .. code-block:: python

        @check_communicating
        def slew(self): ...

    :param func: the wrapped function

    :return: the wrapped function
    """

    @functools.wraps(func)
    def _wrapper(
        component_manager: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Check for component communication before calling the function.

        This is a wrapper function that implements the functionality of
        the decorator.

        :param component_manager: the component manager to check
        :param args: positional arguments to the wrapped function
        :param kwargs: keyword arguments to the wrapped function

        :return: whatever the wrapped function returns
        """
        # Don't bother to run the function if the client
        # intentionally severed connection to the component
        if component_manager.communication_state == CommunicationStatus.DISABLED:
            raise ConnectionError(
                "Commmunication with sub-components is disabled, issue `StartCommunication`"
            )

        # If communication is being actively attempted but
        # the status is uncertain, log a warning and proceed
        if component_manager.communication_state == CommunicationStatus.NOT_ESTABLISHED:
            warning_message = (
                "Communication with component is not established: "
                f"'{type(component_manager).__name__}.{func.__name__}' may fail."
            )
            logging.warning(warning_message)
        return func(component_manager, *args, **kwargs)

    return _wrapper


def requires_component_manager(func: Any) -> Any:
    """Decorator that checks if component_manager is available."""

    @functools.wraps(func)
    def _wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        cm = getattr(self, "component_manager", None)
        if cm:
            return func(self, *args, **kwargs)

        msg = "Component manager not initialized."
        logger = getattr(self, "logger", None)
        if logger:
            logger.error(msg)
        raise RuntimeError(msg)

    return _wrapper
