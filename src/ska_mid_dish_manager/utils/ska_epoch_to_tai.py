"""Shared methods handling timestamp conversion to tai."""

import datetime
import time

from astropy.time import Time

SKA_EPOCH = "1999-12-31T23:59:28Z"


def get_tai_timestamp_from_unix_s(unix_s: float) -> float:
    """
    Calculate atomic time in seconds from unix time in seconds.

    :param unix_s: Unix time in seconds

    :return: atomic time (tai) in seconds
    """
    unix_time = Time(unix_s, format="unix")
    ska_epoch_tai = Time(SKA_EPOCH, scale="utc").unix_tai
    return unix_time.unix_tai - ska_epoch_tai


def get_tai_timestamp_from_datetime(datetime_obj: datetime.datetime) -> float:
    """Convert a datetime object into a TAI timestamp."""
    source_timestamp_unix = datetime_obj.timestamp()
    source_timestamp_tai = Time(source_timestamp_unix, format="unix").unix_tai
    ska_epoch_tai = Time(SKA_EPOCH, scale="utc").unix_tai

    return source_timestamp_tai - ska_epoch_tai


def get_current_tai_timestamp() -> float:
    """Get the current time as a TAI timestamp."""
    return get_tai_timestamp_from_unix_s(time.time())
