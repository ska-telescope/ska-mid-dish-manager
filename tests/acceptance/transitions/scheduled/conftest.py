import os
from collections.abc import Generator

import pytest
import tango
from matplotlib import pyplot as plt


@pytest.fixture
def plot_dish_manager_pointing(
    request: pytest.FixtureRequest, dish_manager_proxy: tango.DeviceProxy
) -> Generator:
    """Monitor achievedPointing and plot a graph of the values over the test execution."""
    file_storage_dir = request.config.getoption("--pointing-files-path")

    if file_storage_dir is None:
        yield None
        return

    if not os.path.exists(file_storage_dir):
        os.makedirs(file_storage_dir)

    data_rows = []

    def capture_achievedPointing_cb(tango_event: tango.EventData) -> None:
        if tango_event.attr_value:
            val = tango_event.attr_value.value
            data_rows.append(val)

    sub_id = dish_manager_proxy.subscribe_event(
        "achievedpointing", tango.EventType.ARCHIVE_EVENT, capture_achievedPointing_cb, []
    )

    yield

    dish_manager_proxy.unsubscribe_event(sub_id)

    if data_rows:
        plot_name = ".".join((f"pointing_plot_{request.node.name}", "png"))
        plot_file_path = os.path.join(file_storage_dir, plot_name)

        fig, (timestamp_ax, azel_ax) = plt.subplots(2, 1, figsize=(10, 8))

        tai_list, az_list, el_list = zip(*data_rows)

        timestamp_ax.plot(tai_list, az_list, label="Azimuth")
        timestamp_ax.plot(tai_list, el_list, label="Elevation")
        timestamp_ax.set_title("Axis vs Time")
        timestamp_ax.set_ylabel("Position (degrees)")
        timestamp_ax.legend()

        azel_ax.plot(az_list, el_list)
        azel_ax.set_title("Azimuth vs Elevation")
        azel_ax.set_xlabel("Azimuth (degrees)")
        azel_ax.set_ylabel("Elevation (degrees)")

        fig.savefig(plot_file_path)
