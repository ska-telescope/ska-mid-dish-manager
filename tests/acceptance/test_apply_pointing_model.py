"""Test Apply Pointing Model Command."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

import pytest
import tango
from ska_control_model import ResultCode

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def read_file_contents(
    path: str,
    band: Optional[str] = None,
    unit: Optional[bool] = False,
    value_range: Optional[bool] = False,
    coeff: Optional[str] = None,
) -> tuple[str, dict]:
    """Read out the JSON file. Object used when calling ApplyPointingModel command."""
    # Ingest the file as JSON string and configure band selection
    # Get the directory where the test file is located
    test_dir = Path(__file__).parent
    # Construct the path to the 'data' directory
    json_file_path = test_dir.parent / "data" / path

    if not json_file_path.exists():
        logger.debug("File not found in %s. Stopping test.", json_file_path)
        pointing_model_definition = []

    with open(json_file_path, "r", encoding="UTF-8") as file:
        pointing_model_definition = json.load(file)
        if band is not None:
            pointing_model_definition["band"] = band
        if unit:
            pointing_model_definition["coefficients"]["IA"]["units"] = (
                "deg"  # Change units from arcsec to deg
            )
        if value_range and coeff == "IA":
            pointing_model_definition["coefficients"]["IA"]["value"] = (
                3000  # force out of range value
            )
        if value_range and coeff == "ABphi":
            pointing_model_definition["coefficients"]["ABphi"][
                "value"
            ] = -2500  # force out of range value

    return json.dumps(pointing_model_definition), pointing_model_definition


@pytest.mark.acceptance
@pytest.mark.parametrize(
    "band_selection",
    [
        ("band0PointingModelParams", "Band_0", "global_pointing_model.json"),
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
    """Test that global pointing parameters are applied correctly from incoming JSON definition."""
    pointing_model_param_events = event_store_class()
    attribute, band_number, file_name = band_selection
    sub_id = dish_manager_proxy.subscribe_event(
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

    dish_manager_proxy.unsubscribe_event(sub_id)


@pytest.mark.acceptance
def test_last_commanded_pointing_params(dish_manager_proxy: tango.DeviceProxy) -> None:
    """Test the `lastCommandedPointingParams` attribute of the dish manager."""
    pointing_model_json_str, _ = read_file_contents("global_pointing_model.json", "Band_2")
    # Command execution
    dish_manager_proxy.ApplyPointingModel(pointing_model_json_str)
    last_requested_parameters = dish_manager_proxy.read_attribute(
        "lastCommandedPointingParams"
    ).value
    try:
        last_requested_parameters = json.loads(last_requested_parameters)
    except json.JSONDecodeError as json_error:
        raise ValueError(
            "lastCommandedPointingParams is not valid JSON or it is default empty string"
        ) from json_error
    assert last_requested_parameters == json.loads(pointing_model_json_str), (
        "The JSON strings did not match as expected"
    )


@pytest.mark.acceptance
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
    pointing_model_json_str, _ = read_file_contents(file_name)

    [[result_code], [command_resp]] = dish_manager_proxy.ApplyPointingModel(
        pointing_model_json_str
    )
    assert response == command_resp
    assert result_code == ResultCode.REJECTED


@pytest.mark.acceptance
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


@pytest.mark.acceptance
@pytest.mark.parametrize(
    ("resp", "unit", "value_range", "coeff"),
    [
        ("Unit deg for key 'IA' is not correct. It should be arcsec", True, False, None),
        ("Value 3000 for key 'IA' is out of range [-2000, 2000]", False, True, "IA"),
        ("Value -2500 for key 'ABphi' is out of range [0, 360]", False, True, "ABphi"),
    ],
)
def test_unit_and_range(
    resp, unit, value_range, coeff, dish_manager_proxy: tango.DeviceProxy
) -> None:
    """Test that units and ranges."""
    file_name = "global_pointing_model.json"
    pointing_model_json_str, _ = read_file_contents(
        file_name, unit=unit, value_range=value_range, coeff=coeff
    )

    [[result_code], [command_resp]] = dish_manager_proxy.ApplyPointingModel(
        pointing_model_json_str
    )

    assert command_resp == resp
    assert result_code == ResultCode.REJECTED


@pytest.mark.acceptance
@pytest.mark.parametrize(
    ("file_name, response"),
    [
        (
            "missing_units.json",
            "Missing 'units' for key 'IA'.",
        ),
        ("missing_values.json", "Missing 'value' for key 'IA'."),
    ],
)
def test_missing_units_values(
    file_name: str,
    response: str,
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Test ApplyPointingModel command with missing units and value keys."""
    pointing_model_json_str, _ = read_file_contents(file_name)

    [[result_code], [command_resp]] = dish_manager_proxy.ApplyPointingModel(
        pointing_model_json_str
    )
    assert response == command_resp
    assert result_code == ResultCode.REJECTED
