"""Test Static Pointing Model."""

import json
from pathlib import Path
from typing import Any

import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.forked
def test_track_load_static_off(
    dish_manager_proxy: tango.DeviceProxy, event_store_class: Any
) -> None:
    """Test TrackLoadStaticOff command."""
    write_values = [20.1, 0.5]

    model_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "actStaticOffsetValueXel", tango.EventType.CHANGE_EVENT, model_event_store
    )
    dish_manager_proxy.subscribe_event(
        "actStaticOffsetValueEl", tango.EventType.CHANGE_EVENT, model_event_store
    )
    dish_manager_proxy.subscribe_event(
        "longrunningCommandProgress", tango.EventType.CHANGE_EVENT, progress_event_store
    )

    dish_manager_proxy.TrackLoadStaticOff(write_values)

    expected_progress_updates = [
        "TrackLoadStaticOff called on DS",
        "Awaiting DS actstaticoffsetvaluexel, actstaticoffsetvalueel change to "
        f"{write_values[0]}, {write_values[1]}",
        "Awaiting actstaticoffsetvaluexel, actstaticoffsetvalueel change to "
        f"{write_values[0]}, {write_values[1]}",
        f"DS actstaticoffsetvaluexel changed to {write_values[0]}",
        f"DS actstaticoffsetvalueel changed to {write_values[1]}",
        "TrackLoadStaticOff completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string

    model_event_store.wait_for_value(write_values[0], timeout=7)
    model_event_store.wait_for_value(write_values[1], timeout=7)


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "band_selection",
    [
        ("band1PointingModelParams", "Band_1"),
        ("band2PointingModelParams", "Band_2"),
        ("band3PointingModelParams", "Band_3"),
        ("band4PointingModelParams", "Band_4"),
        ("band5aPointingModelParams", "Band_5a"),
        ("band5bPointingModelParams", "Band_5b"),
    ],
)
def test_apply_pointing_model_command(
    band_selection: tuple[str, str], dish_manager_proxy: tango.DeviceProxy, event_store_class: Any
) -> None:
    """Test that global pointing parameters are applied correctly from incoming JSON defintion"""
    pointing_model_param_events = event_store_class()

    dish_manager_proxy.subscribe_event(
        band_selection[0],
        tango.EventType.CHANGE_EVENT,
        pointing_model_param_events,
    )

    # NOTE TO SELF: Handle cases where you cant find the file!!!!!!!!
    # Ingest the file as JSON string and configure band selection
    home_dir = Path.home()
    json_file_path = ""
    for path in home_dir.rglob("global_pointing_model.json"):
        json_file_path = path

    pointing_model_definition = ""
    with open(
        json_file_path,
        "r",
        encoding="UTF-8",
    ) as file:
        pointing_model_definition = json.load(file)
        pointing_model_definition["band"] = band_selection[1]
        pointing_model_definition["antenna"] = "SKA001"
    file.close()

    # dish_manager_proxy.ApplyPointingModel(pointing_model_definition)

    # Construct list of expected values from the JSON definition
    coeffient_dictionary = pointing_model_definition["coefficients"]
    pointing_model_params_keys = coeffient_dictionary.keys()

    expected_pointing_model_param_values = []
    for coeffient_key in pointing_model_params_keys:
        pointing_model_value = coeffient_dictionary[coeffient_key]["value"]
        expected_pointing_model_param_values.append(pointing_model_value)

    pointing_model_param_events.wait_for_value(expected_pointing_model_param_values, timeout=7)
