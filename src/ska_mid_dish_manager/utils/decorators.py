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
