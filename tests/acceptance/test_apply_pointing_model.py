# pylint: disable=too-many-locals

"""Test Apply Pointing Model Command."""
import json
from pathlib import Path
from typing import Any, Optional

import pytest
import tango
from ska_control_model import ResultCode


def read_file_contents(path: str, band: Optional[str] = None) -> tuple[str, dict]:
    """Appy Pointing Model Test - Best Cases"""
    # Ingest the file as JSON string and configure band selection
    # Get the directory where the test file is located
    test_dir = Path(__file__).parent
    # Construct the path to the 'supplementary' directory
    json_file_path = test_dir / "supplementary" / path

    if not json_file_path.exists():
        print("File not found. Stopping test.")
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

    pointing_model_json_str, pointing_model_definition = read_file_contents(
        band_selection[2], band_selection[1]
    )

    # pointing_model_json_str = json.dumps(pointing_model_definition)
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
def test_last_commanded_pointing_params(dish_manager_proxy: tango.DeviceProxy) -> None:
    "Test the Test the `lastCommandedPointingParams` attribute of the dish manager."
    pointing_model_json_str, pointing_model_definition = read_file_contents(
        "global_pointing_model.json", "Band_2"
    )
    # Command execution
    dish_manager_proxy.ApplyPointingModel(pointing_model_json_str)
    last_requested_parameters = dish_manager_proxy.read_attribute(
        "lastCommandedPointingParams"
    ).value
    # print(f"Last commanded parameters: {last_requested_parameters}")
    try:
        last_requested_parameters = json.loads(last_requested_parameters)
    except json.JSONDecodeError as json_error:
        raise ValueError(
            "lastCommandedPointingParams is not valid JSON or it is default value"
        ) from json_error
    # extract list of coefficient from last_requested_params
    applied_coefficient_dict = last_requested_parameters["coefficients"]
    applied_coefficient_list = [
        (key, value_dict["value"]) for key, value_dict in applied_coefficient_dict.items()
    ]
    # Construct list of expected values from the JSON definition
    requested_coefficient_dict = pointing_model_definition.get("coefficients", {})
    requested_coefficient_list = [
        (key, value_dict["value"]) for key, value_dict in requested_coefficient_dict.items()
    ]
    assert applied_coefficient_list == requested_coefficient_list


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
        (
            "incorrect_total_coeff.json",
            "Coefficients are missing. The coefficients found in the JSON object were {coeff}",
        ),
        (
            "coeff_order.json",
            "Successfully wrote the following values {coeff} to band 2 on DS",
        ),
    ],
)
def test_inconsistent_json_apply_pointing_model(
    file_name: str,
    response: str,
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Test ApplyPointingModel command with incorrect JSON inputs."""

    pointing_model_json_str, pointing_model_definition = read_file_contents(file_name, None)

    # Incorrect JSON assessment
    result_code, command_resp = dish_manager_proxy.ApplyPointingModel(pointing_model_json_str)

    if file_name in ["incorrect_total_coeff.json"]:
        coefficients = pointing_model_definition.get("coefficients", {})
        coeff_keys = list(coefficients.keys())
        formatted_response = response.format(coeff=coeff_keys)
        assert formatted_response == command_resp[0]
        assert result_code == ResultCode.REJECTED
    elif file_name in ["coeff_order.json"]:
        coefficients = pointing_model_definition.get("coefficients", {})
        formatted_response = response.format(coeff=coefficients)
        assert formatted_response == command_resp[0]
        assert result_code == ResultCode.OK
    else:
        assert response == command_resp[0]
        assert result_code == ResultCode.REJECTED
