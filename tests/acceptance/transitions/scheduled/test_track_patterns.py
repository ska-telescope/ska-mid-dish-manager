"""Test tracking with data from a csv file."""

import csv
import os
import pickle
from collections.abc import Generator
from typing import Any

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
)
from tests.data import (
    CORDIODSCAN__CSV_PATH,
    RADIAL_SCAN_CSV_PATH,
    RASTER_SCAN_CSV_PATH,
    SIDEREAL_SCAN_CSV_PATH,
    SPIRAL_SCAN_CSV_PATH,
    UP_DOWN_SCAN_CSV_PATH,
)
from tests.utils import (
    compare_trajectories,
    handle_slew_to_point,
    handle_tracking_table,
    remove_subscriptions,
    save_tracking_test_plots,
    setup_subscriptions,
)

TRACKING_TABLE_CHUNK_SIZE = 50
TRACKING_TABLE_LOAD_LEAD_TIME_S = 5

TRACKING_TIME_THRESHOLD_ERROR_MS = 0.05  # 50ms cadence / tolerance
POINTING_TOLERANCE_DEG = 0.1  # 360 arcsec
POINTING_TOLERANCE_ARCSEC = POINTING_TOLERANCE_DEG * 3600


def load_csv_data(file_path: str) -> list[tuple[float, float, float]]:
    """Loads the entire CSV file into memory."""
    data = []
    with open(file_path, newline="") as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip header if present
        data = [(float(row[0]), float(row[1]), float(row[2])) for row in reader]
    return data


@pytest.mark.forked
@pytest.mark.track_patterns
@pytest.mark.parametrize(
    "track_csv_file",
    [
        (RADIAL_SCAN_CSV_PATH),
        (SPIRAL_SCAN_CSV_PATH),
        (SIDEREAL_SCAN_CSV_PATH),
        (UP_DOWN_SCAN_CSV_PATH),
        (CORDIODSCAN__CSV_PATH),
        (RASTER_SCAN_CSV_PATH),
    ],
)
def test_track_pattern(
    track_csv_file: Any,
    event_store_class: Any,
    request: pytest.FixtureRequest,
    dish_manager_proxy: tango.DeviceProxy,
    ds_device_proxy: tango.DeviceProxy,
    plot_dish_manager_pointing: Generator,
) -> None:
    """Test tracking the points from the given csv file."""
    main_event_store = event_store_class()
    pointing_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": main_event_store,
        "configuredband": main_event_store,
        "achievedPointing": pointing_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # Get the dish ready for tracking
    if dish_manager_proxy.configuredBand != Band.B1:
        dish_manager_proxy.ConfigureBand1(True)
        main_event_store.wait_for_value(Band.B1, timeout=60)
    if dish_manager_proxy.dishMode != DishMode.OPERATE:
        dish_manager_proxy.SetOperateMode()
        main_event_store.wait_for_value(DishMode.OPERATE, timeout=5)

    track_table = load_csv_data(track_csv_file)

    # Slew to the start point
    _, start_point_az, start_point_el = track_table[0]
    handle_slew_to_point(
        ds_device_proxy, dish_manager_proxy, start_point_az, start_point_el, event_store_class
    )

    start_time_tai: float = ds_device_proxy.GetCurrentTAIOffset() + 10
    pointing_event_store.clear_queue()

    try:
        handle_tracking_table(
            ds_manager_proxy=ds_device_proxy,
            dish_manager_proxy=dish_manager_proxy,
            table=track_table,
            start_time_tai=start_time_tai,
            pointing_tolerance_arcsec=POINTING_TOLERANCE_ARCSEC,
            table_load_chunk_size=TRACKING_TABLE_CHUNK_SIZE,
            table_load_lead_time=TRACKING_TABLE_LOAD_LEAD_TIME_S,
            event_store_class=event_store_class,
        )
    finally:
        achieved_pointing = pointing_event_store.get_queue_values_timeout(timeout=10)
        remove_subscriptions(subscriptions)

        # Compare the desired and achieved trajectories
        # Extract achieved values from events from after the start time
        # Add the start point as a change event wont be recorded for it since the test slews there
        achieved_trajectory = [(start_time_tai, start_point_az, start_point_el)]
        achieved_trajectory += [
            (tai, az, el) for _, (tai, az, el) in achieved_pointing if tai >= start_time_tai
        ]

        desired_trajectory = [
            (start_time_tai + offset_tai, az, el) for offset_tai, az, el in track_table
        ]

        mismatches, err_tai_list, err_angular_list = compare_trajectories(
            desired_trajectory=desired_trajectory,
            achieved_trajectory=achieved_trajectory,
            pointing_tolerance_arcsec=POINTING_TOLERANCE_ARCSEC,
        )

        # Plots
        file_storage_dir = request.config.getoption("--pointing-files-path")

        if file_storage_dir is not None:
            if not os.path.exists(file_storage_dir):
                os.makedirs(file_storage_dir)

            file_name = ".".join((f"pointing_trajectories_{request.node.name}", "png"))
            save_file_path = os.path.join(file_storage_dir, file_name)
            save_tracking_test_plots(
                desired_trajectory,
                achieved_trajectory,
                err_tai_list,
                err_angular_list,
                save_file_path,
            )

            # Save achieved trajectory
            file_name = ".".join((f"pointing_trajectory_{request.node.name}", "pickle"))
            save_file_path = os.path.join(file_storage_dir, file_name)
            with open(save_file_path, "wb") as fp:
                pickle.dump(achieved_trajectory, fp)

    assert not mismatches, f"{len(mismatches)} / {len(track_table)} trajectory mismatches."
