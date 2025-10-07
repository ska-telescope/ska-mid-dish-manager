"""Input validation and formatting."""

import json
from typing import List

from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_current_tai_timestamp_from_unix_time


class TrackTableTimestampError(ValueError):
    """Class that is used to represent timestamp errors in the track load table."""


class ConfigureBandValidationError(Exception):
    """Exception raised for errors in the configure band input validation."""


def validate_configure_band_input(data: str) -> dict:
    """Validate the input JSON for configure_band command.

    :param data: JSON string containing the configure band parameters.
    :raises ConfigureBandValidationError: If the input JSON is invalid.
    :return: Parsed JSON as a dictionary if valid.
    """
    try:
        data_json = json.loads(data)
        dish_data = data_json.get("dish")
        receiver_band = dish_data.get("receiver_band")
        if receiver_band not in ["1", "2", "3", "4", "5a", "5b"]:
            raise ConfigureBandValidationError("Invalid receiver band in JSON.")
        if receiver_band == "5b":
            sub_band = dish_data.get("sub_band")
            if sub_band not in [1, 2, 3]:
                raise ConfigureBandValidationError("Invalid sub-band in JSON.")
    except (json.JSONDecodeError, AttributeError) as err:
        raise ConfigureBandValidationError("Error parsing JSON.") from err

    return data_json


class TrackLoadTableFormatting:
    """Class that encapsulates related validation and mapping for TrackLoadTable command."""

    def check_track_table_input_valid(self, table: List[float], lead_time: int) -> None:
        """Entry point for track table validation.

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

    def _check_timestamp(
        self,
        table: List[float],
        length_of_table: int,
        lead_time: float,
    ) -> None:
        """Check that the timestamps are in the future by at least lead_time in seconds and that
        they are monotonically increasing.

        :param table: Track table input that is to be validated
        :param length_of_table: Length of the track table
        :param lead_time: Duration in seconds ahead of the current time that table timestamps
        should be ahead of

        :raises TrackTableTimestampError: when timestamps are less than lead_time seconds into the
        future, or if the timestamps are not monotonically increasing.

        :return: None
        """
        current_tai_timestamp = get_current_tai_timestamp_from_unix_time()
        prev_timestamp = -1
        for i in range(0, length_of_table, 3):
            timestamp_tai_s = table[i]
            # check for lead_time violation
            delta = timestamp_tai_s - current_tai_timestamp
            if delta < lead_time:
                raise TrackTableTimestampError(
                    "Check track table parameters."
                    f" Timestamps less than {lead_time}s into the future."
                    f" Violation detected for timestamp ({timestamp_tai_s}) which is less than "
                    f" {lead_time}s ahead of current time ({current_tai_timestamp})."
                )
            # check for monotonically increasing
            if i != 0:
                row_time_delta = timestamp_tai_s - prev_timestamp
                if row_time_delta < 0:
                    raise TrackTableTimestampError(
                        "Check track table parameters."
                        "Timestamps are not monotonically increasing."
                        f"Last two timestamps (tai) {timestamp_tai_s},{prev_timestamp},..."
                    )

            prev_timestamp = timestamp_tai_s
