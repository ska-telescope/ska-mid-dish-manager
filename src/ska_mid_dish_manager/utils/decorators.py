"Utility decorators"

import functools
import logging
import time
from typing import Any

from ska_control_model import CommunicationStatus


def record_mode_change_request(func: Any) -> Any:
    """Record a mode change request"""

    @functools.wraps(func)
    def wrapper_record_mode_change_request(*args: Any, **kwargs: Any) -> Any:
        device_instance = args[0]
        last_commanded_mode = (str(time.time()), func.__name__)
        # pylint: disable=protected-access
        device_instance._last_commanded_mode = last_commanded_mode
        device_instance.push_change_event("lastCommandedMode", last_commanded_mode)
        device_instance.push_archive_event("lastCommandedMode", last_commanded_mode)
        return func(*args, **kwargs)

    return wrapper_record_mode_change_request


def check_communicating(func: Any) -> Any:
    """
    Return a function that checks component communication before calling a function.

    The component manager needs to have established communications with
    the component before the function is called but if there is no communication
    the function will be sent to the component and the client will be informed

    This function is intended to be used as a decorator:

    .. code-block:: python

        @check_communicating
        def slew(self):
            ...

    :param func: the wrapped function

    :return: the wrapped function
    """

    @functools.wraps(func)
    def _wrapper(
        component_manager: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Check for component communication before calling the function.

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
