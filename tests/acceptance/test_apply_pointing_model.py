# pylint: disable=too-many-locals

"""Test Apply Pointing Model Command"""
import json
import logging
from pathlib import Path
from typing import Any, Optional

import pytest
import tango
from ska_control_model import ResultCode

logging.basicConfig(level=logging.DEBUG)


def read_file_contents(path: str, band: Optional[str] = None) -> tuple[str, dict]:
    """Read out the JSON file. Object used when calling ApplyPointingModel command"""
    # Ingest the file as JSON string and configure band selection
    # Get the directory where the test file is located
    test_dir = Path(__file__).parent
    # Construct the path to the 'data' directory
    json_file_path = test_dir.parent / "data" / path

    if not json_file_path.exists():
        logging.debug(f"File not found in {json_file_path}. Stopping test.")
        pointing_model_definition = []

    with open(json_file_path, "r", encoding="UTF-8") as file:
        pointing_model_definition = json.load(file)
        if band is not None:
            pointing_model_definition["band"] = band

    return json.dumps(pointing_model_definition), pointing_model_definition


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "band_selection",
    [
        ("band1PointingModelParams", "Band_1", "global_pointing_model.json"),
        ("band2PointingModelParams", "Band_2", "global_pointing_model.json"),
        ("band3PointingModelParams", "Band_3", "global_pointing_model.json"),
        ("band4PointingModelParams", "Band_4", "global_pointing_model.json"),
        ("band5aPointingModelParams", "Band_5a", "global_pointing_model.json"),
        ("band5bPointingModelParams", "Band_5b", "global_pointing_model.json"),
    ],
)
def test_best_case_json(
    band_selection: tuple[str, str], dish_manager_proxy: tango.DeviceProxy, event_store_class: Any
) -> None:
    """Test that global pointing parameters are applied correctly from incoming JSON defintion"""
    pointing_model_param_events = event_store_class()
    attribute, band_number, file_name = band_selection
    dish_manager_proxy.subscribe_event(
        attribute,
        tango.EventType.CHANGE_EVENT,
        pointing_model_param_events,
    )

    pointing_model_json_str, pointing_model_definition = read_file_contents(file_name, band_number)

    dish_manager_proxy.ApplyPointingModel(pointing_model_json_str)

    # Construct list of expected values from the JSON definition
    coeffient_dictionary = pointing_model_definition["coefficients"]
    pointing_model_params_keys = coeffient_dictionary.keys()

    expected_pointing_model_param_values = []
    for coeffient_key in pointing_model_params_keys:
        pointing_model_value = coeffient_dictionary[coeffient_key]["value"]
        expected_pointing_model_param_values.append(pointing_model_value)

    pointing_model_param_events.wait_for_value(expected_pointing_model_param_values, timeout=7)


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    ("file_name, response"),
    [
        (
            "incorrect_antenna.json",
            "Command rejected. The Dish id SKA001 and the Antenna's value SKA053 are not equal.",
        ),
        ("incorrect_band.json", "Unsupported Band: b6"),
    ],
)
def test_inconsistent_json(
    file_name: str,
    response: str,
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Test ApplyPointingModel command with incorrect (Wrong antenna and band) JSON inputs."""

    pointing_model_json_str, _ = read_file_contents(file_name, None)

    [[result_code], [command_resp]] = dish_manager_proxy.ApplyPointingModel(
        pointing_model_json_str
    )
    assert response == command_resp
    assert result_code == ResultCode.REJECTED


@pytest.mark.acceptance
@pytest.mark.forked
def test_missing_coeffs_json(
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Test ApplyPointingModel command with missing pointing coefficients."""

    file_name = "incorrect_total_coeff.json"
    response = "Coefficients are missing. The coefficients found in the JSON object were {coeff}"

    pointing_model_json_str, pointing_model_definition = read_file_contents(file_name, None)

    [[result_code], [command_resp]] = dish_manager_proxy.ApplyPointingModel(
        pointing_model_json_str
    )
    coefficients = pointing_model_definition.get("coefficients", {})
    coeff_keys = list(coefficients.keys())
    formatted_response = response.format(coeff=coeff_keys)
    assert formatted_response == command_resp
    assert result_code == ResultCode.REJECTED


@pytest.mark.acceptance
@pytest.mark.forked
def test_out_of_order_pointing_coeff_json(
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Test ApplyPointingModel command with coefficients in a non-standard order."""

    file_name = "coeff_order.json"
    response = "Successfully wrote the following values {coeff} to band 2 on DS"

    pointing_model_json_str, pointing_model_definition = read_file_contents(file_name, None)

    [[result_code], [command_resp]] = dish_manager_proxy.ApplyPointingModel(
        pointing_model_json_str
    )

    coefficients = pointing_model_definition.get("coefficients", {})
    formatted_response = response.format(coeff=coefficients)
    assert formatted_response == command_resp
    assert result_code == ResultCode.OK
