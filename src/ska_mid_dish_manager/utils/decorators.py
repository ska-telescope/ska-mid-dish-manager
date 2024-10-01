"Utility decorators"

import functools
import time


def record_mode_change_request(func):
    """Record a mode change request"""

    @functools.wraps(func)
    def wrapper_record_mode_change_request(*args, **kwargs):
        device_instance = args[0]
        last_commanded_mode = (str(time.time()), func.__name__)
        # pylint: disable=protected-access
        device_instance._last_commanded_mode = last_commanded_mode
        device_instance.push_change_event("lastCommandedMode", last_commanded_mode)
        device_instance.push_archive_event("lastCommandedMode", last_commanded_mode)
        return func(*args, **kwargs)

    return wrapper_record_mode_change_request


def record_applied_pointing_value(func):
    """Decorator to record the value passed into a command method"""

    @functools.wraps(func)
    def wrapper_record_applied_pointing_value(*args, **kwargs):
        device_instance = args[0]
        value = args[1]  # The JSON object is the second positional argument
        last_commanded_pointing_params = value
        # Store the value passed into the command
        device_instance._last_commanded_pointing_params = last_commanded_pointing_params
        # Push change and archive events with the recorded value and timestamp
        device_instance.push_change_event(
            "lastCommandedPointingParams", last_commanded_pointing_params
        )
        device_instance.push_archive_event(
            "lastCommandedPointingParams", last_commanded_pointing_params
        )
        # Call the original function
        return func(*args, **kwargs)

    return wrapper_record_applied_pointing_value
