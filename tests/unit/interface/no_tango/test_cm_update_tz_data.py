"""Tests dish manager component manager UpdateTZData command handler."""

import base64
from unittest.mock import MagicMock, patch

import pytest
import requests
from ska_control_model import ResultCode

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.constants import TZ_DATA_URL_ENV_VAR

TZ_DATA_URL = "http://example.com/tzdata.tar.gz"
TZ_DATA_BYTES = b"some-binary-tz-data"


def _get_result_code(task_callback: MagicMock) -> ResultCode:
    """Return the result code from the last task_callback call carrying a result."""
    for call in reversed(task_callback.call_args_list):
        if "result" in call.kwargs:
            return call.kwargs["result"][0]
    raise AssertionError("task_callback was never called with a result")


def _get_result_message(task_callback: MagicMock) -> str:
    """Return the result message from the last task_callback call carrying a result."""
    for call in reversed(task_callback.call_args_list):
        if "result" in call.kwargs:
            return call.kwargs["result"][1]
    raise AssertionError("task_callback was never called with a result")


@pytest.mark.unit
def test_update_tz_data_success(
    component_manager: DishManagerComponentManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify UpdateTZData downloads, encodes and forwards the data to SPFRx.

    :param component_manager: the component manager under test
    :param monkeypatch: pytest fixture for patching the environment
    """
    monkeypatch.setenv(TZ_DATA_URL_ENV_VAR, TZ_DATA_URL)
    task_callback = MagicMock()

    mock_response = MagicMock()
    mock_response.content = TZ_DATA_BYTES
    mock_response.raise_for_status = MagicMock()

    spfrx_cm = component_manager.sub_component_managers["SPFRX"]

    with patch(
        "ska_mid_dish_manager.component_managers.dish_manager_cm.requests.get",
        return_value=mock_response,
    ) as mock_get:
        component_manager._update_tz_data(task_callback=task_callback)

    mock_get.assert_called_once()
    assert mock_get.call_args.args[0] == TZ_DATA_URL

    expected_encoded = base64.b64encode(TZ_DATA_BYTES).decode("ascii")
    spfrx_cm.execute_command.assert_called_with("UpdateTZData", expected_encoded)
    assert _get_result_code(task_callback) == ResultCode.OK
    assert _get_result_message(task_callback) == (
        "UpdateTZData completed. TZ data successfully uploaded to SPFRx."
    )


@pytest.mark.unit
def test_update_tz_data_missing_env_var(
    component_manager: DishManagerComponentManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify UpdateTZData fails when the URL environment variable is not set.

    :param component_manager: the component manager under test
    :param monkeypatch: pytest fixture for patching the environment
    """
    monkeypatch.delenv(TZ_DATA_URL_ENV_VAR, raising=False)
    task_callback = MagicMock()

    component_manager._update_tz_data(task_callback=task_callback)

    assert _get_result_code(task_callback) == ResultCode.FAILED
    assert _get_result_message(task_callback) == (
        f"UpdateTZData failed. Environment variable '{TZ_DATA_URL_ENV_VAR}' is not "
        "set or is empty; cannot determine where to download the TZ data from."
    )


@pytest.mark.unit
def test_update_tz_data_download_failure(
    component_manager: DishManagerComponentManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify UpdateTZData fails gracefully when the download fails.

    :param component_manager: the component manager under test
    :param monkeypatch: pytest fixture for patching the environment
    """
    monkeypatch.setenv(TZ_DATA_URL_ENV_VAR, TZ_DATA_URL)
    task_callback = MagicMock()

    with patch(
        "ska_mid_dish_manager.component_managers.dish_manager_cm.requests.get",
        side_effect=requests.exceptions.ConnectionError("boom"),
    ):
        component_manager._update_tz_data(task_callback=task_callback)

    assert _get_result_code(task_callback) == ResultCode.FAILED
    assert _get_result_message(task_callback) == (
        f"UpdateTZData failed. Could not download TZ data from {TZ_DATA_URL}."
    )


@pytest.mark.unit
def test_update_tz_data_rejected_when_spfrx_ignored(
    component_manager: DishManagerComponentManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify UpdateTZData fails when SPFRx is ignored.

    :param component_manager: the component manager under test
    :param monkeypatch: pytest fixture for patching the environment
    """
    monkeypatch.setenv(TZ_DATA_URL_ENV_VAR, TZ_DATA_URL)
    component_manager._update_component_state(ignorespfrx=True)
    task_callback = MagicMock()

    with patch("ska_mid_dish_manager.component_managers.dish_manager_cm.requests.get") as mock_get:
        component_manager._update_tz_data(task_callback=task_callback)

    mock_get.assert_not_called()
    assert _get_result_code(task_callback) == ResultCode.FAILED
    assert _get_result_message(task_callback) == (
        "UpdateTZData rejected. SPFRx is ignored, cannot upload TZ data."
    )
