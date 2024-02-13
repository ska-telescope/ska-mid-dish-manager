"""Module for containing input validation and formatting needed for translation
between DSC and DS manager."""

from time import time
from typing import List

from astropy.time import Time


class TrackTableTimestampError(ValueError):
    """Class that is used to represent timestamp errors in the track load table"""


class TrackLoadTableFormatting:
    """Class that encapsulates related validation and mapping for TrackLoadTable command"""

    def check_track_table_input_valid(self, table: List[float], lead_time: int) -> None:
        """
        Entry point for track table validation.

        :param table: Track table input that is to be validated
        :param lead_time: The amount of time in seconds from the current time timestamps are 
        allowed

        :raises ValueError: table list is not a multiple of 3
        :raises TrackTableTimestampError: when timestamps are less than lead_time seconds into the 
        future

        :return: None
        """
        length_of_table = len(table)
        # length validaton
        if length_of_table > 0:
            # Checks that the table length is a multiple of 3
            if length_of_table % 3 != 0:
                raise ValueError(
                    f"Length of table ({len(table)}) is not a multiple of 3 "
                    "(timestamp, azimuth coordinate, elevation coordinate) as expected."
                )
            try:
                self._check_timestamp(table, length_of_table, lead_time)
            except TrackTableTimestampError as timestamp_error:
                raise timestamp_error

    def get_tai_from_unix_s(self, unix_s: float) -> float:
        """
        Calculate atomic time in seconds from unix time in seconds.

        :param unix_s: Unix time in seconds

        :return: atomic time (tai) in seconds
        """
        astropy_time_utc = Time(unix_s, format="unix")
        return astropy_time_utc.tai

    def _check_timestamp(self, table: List[float], length_of_table: int, lead_time: float) -> None:
        """
        Check that the timestamps are in the future by at least lead_time in seconds.

        :param table: Track table input that is to be validated
        :param length_of_table: Length of the track table
        :param lead_time: Duration in seconds ahead of the current time that table timestamps 
        should be ahead of

        :raises TrackTableTimestampError: when timestamps are less than lead_time seconds into the 
        future

        :return: None
        """
        # use current time as reference for checking all the timestamps in the array
        # as this operation should complete fast in comparison to lead_time
        current_time_tai_s = self.get_tai_from_unix_s(time())
        for i in range(0, length_of_table, 3):
            timestamp_tai_s = table[i]
            if timestamp_tai_s - current_time_tai_s < lead_time:
                raise TrackTableTimestampError(
                    "Check track table parameters."
                    f"Timestamps less than {lead_time}s into the future."
                )
