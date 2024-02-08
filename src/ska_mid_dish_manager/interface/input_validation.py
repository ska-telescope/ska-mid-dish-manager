"""Module for containing input validation and formatting needed for translation
between DSC and DS manager."""

from logging import Logger
from time import time
from typing import List

from astropy.time import Time


class TrackLoadTableFormatting:
    """Class that encapsulates related validation and mapping for TrackLoadTable command"""

    def check_track_table_input_valid(
        self, logger: Logger, table: List[float], future_time_ms: int
    ) -> None:
        """Entry point for track table validation"""
        length_of_table = len(table)
        # length validaton
        if length_of_table > 0:
            # Checks that the table length is a multiple of 3
            if length_of_table % 3 != 0:
                raise ValueError(
                    f"Length of table ({len(table)}) is not a multiple of 3 "
                    "(timestamp, azimuth coordinate, elevation coordinate) as expected."
                )
            # log if samples are not in the future by future_time_ms
            self._check_timestamp(logger, table, length_of_table, future_time_ms)
        else:
            logger.warn("Empty track table provided.")

    def format_track_table_time_unixms_to_tai(self, table: List[float]) -> None:
        """Convert each timestamp from unix millisecond to tai seconds"""
        for i in range(0, len(table), 3):
            tai = self._get_tai_from_unix_ms(table[i])
            table[i] = tai

    def _get_tai_from_unix_ms(self, unix_ms: float) -> float:
        """Calculate atomic time in seconds from unix time in milliseconds"""
        unix_time_in_seconds = unix_ms / 1000.0
        astropy_time_utc = Time(unix_time_in_seconds, format="unix")
        return astropy_time_utc.tai

    def _check_timestamp(
        self, logger: Logger, table: List[float], length_of_table: int, future_time_ms: float
    ) -> None:
        """Check that the timestamps are in the future by at least future_time_ms"""
        for i in range(0, length_of_table, 3):
            timestamp_ms = table[i]
            current_time_ms = time() * 1e3
            if timestamp_ms - current_time_ms < future_time_ms:
                logger.info(
                    "Check track table parameters."
                    f"Timestamps less than {future_time_ms} ms into the future."
                )
