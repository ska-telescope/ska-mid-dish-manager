"""General utils for test devices"""
import random
import time
from functools import wraps


def random_delay_execution(func):
    """Delay a command a bit"""

    @wraps(func)
    def inner(*args, **kwargs):
        time.sleep(round(random.uniform(1.5, 2.5), 2))
        return func(*args, **kwargs)

    return inner
