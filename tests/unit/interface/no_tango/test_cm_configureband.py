"""Tests dish manager component manager configureband command handler."""

import json
import logging
from typing import cast
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.component_managers.spfrx_cm import SPFRxComponentManager
from ska_mid_dish_manager.models.command_actions import apply_pointing_model
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    SPFBandInFocus,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
@patch("ska_mid_dish_manager.models.command_actions.apply_pointing_model")
def test_configureband_handler(
    mock_apply_pointing_model,
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
) -> None:
    """Verify behaviour of ConfigureBand[x] command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_state_cb = callbacks["comp_state_cb"]
    component_manager.component_state["band2pointingmodelparams"] = [1.8] * 18
    mock_apply_pointing_model.return_value = None

    component_manager.configure_band_cmd(Band.B2, True, callbacks["task_cb"])
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    msgs = [
        "ConfigureBand2 started",
        "DS.SetIndexPosition started",
        "Awaiting DS indexerposition change to B2",
        "Running SetIndexPosition on device DS",
        "SetIndexPosition on DS timeout is 0",
        "SPFRX.ConfigureBand2 started",
        "Running ConfigureBand2 on device SPFRX",
        "ConfigureBand2 on SPFRX timeout is 0",
        "Running Wait for operatingMode.CONFIGURE on device SPFRX",
        "SPFRX operatingmode changed to CONFIGURE",
    ]

    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.CONFIGURE
    )

    component_state_cb.wait_for_value("dishmode", DishMode.CONFIG)

    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        operatingmode=DSOperatingMode.POINT
    )
    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE
    )

    component_state_cb.wait_for_value("dishmode", DishMode.OPERATE)

    component_manager.sub_component_managers["DS"]._update_component_state(
        indexerposition=IndexerPosition.B2
    )

    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        configuredband=Band.B2
    )
    component_manager.sub_component_managers["SPF"]._update_component_state(
        bandinfocus=SPFBandInFocus.B2
    )

    component_state_cb.wait_for_value("configuredband", Band.B2, timeout=30)

    component_state_cb.get_queue_values()

    progress_cb = callbacks["progress_cb"]
    for msg in msgs:
        progress_cb.wait_for_args((msg,))

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()
    # check that the updates for the final SetOperate call in the sequence come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "SetOperateMode completed."),
    )
    # progress_cb.wait_for_args(("SetOperateMode completed.",))

    # Verify apply_pointing_model was called
    mock_apply_pointing_model.assert_called_once()


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
@patch("ska_mid_dish_manager.models.command_actions.apply_pointing_model")
def test_configureband_json_handler_happy(
    mock_apply_pointing_model,
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
) -> None:
    """Verify behaviour of ConfigureBand for json happy case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_state_cb = callbacks["comp_state_cb"]
    configure_json = """
    {
        "dish": {
            "receiver_band": "2",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """
    component_manager.component_state["band2pointingmodelparams"] = [1.8] * 18
    mock_apply_pointing_model.return_value = None
    status, response = component_manager.configure_band_with_json(
        configure_json, callbacks["task_cb"]
    )
    assert status == TaskStatus.QUEUED
    assert "Task queued" in response

    # wait a bit for the lrc updates to come through

    component_state_cb.get_queue_values()

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    msgs = [
        "Awaiting DS indexerposition change to B2",
        "Awaiting SPFRX configuredband, operatingmode change to B2, OPERATE",
        "Running ConfigureBand on device SPFRX",
        "Awaiting SPFRX operatingmode change to CONFIGURE",
        "Running Wait for operatingMode.CONFIGURE on device SPFRX",
        "Awaiting SPFRX operatingmode change to CONFIGURE",
    ]
    progress_cb = callbacks["progress_cb"]
    for msg in msgs:
        progress_cb.wait_for_args((msg,))

    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.CONFIGURE
    )

    component_state_cb.wait_for_value("dishmode", DishMode.CONFIG)

    # check that the component state reports the requested command
    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        configuredband=Band.B2, operatingmode=SPFRxOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        indexerposition=IndexerPosition.B2, operatingmode=DSOperatingMode.POINT
    )
    component_state_cb.wait_for_value("configuredband", Band.B2)

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()
    # check that the updates for the final SetOperate call in the sequence come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "SetOperateMode completed."),
    )
    progress_cb.wait_for_args(("SetOperateMode completed.",))

    # Verify apply_pointing_model was called
    mock_apply_pointing_model.assert_called_once()


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_configureband_badly_formatted_json(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
) -> None:
    """Verify behaviour of ConfigureBand for json badly formatted case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    configure_json = """
    {
        "dish": {
            "receiver_band": "2",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
    """

    status, response = component_manager.configure_band_with_json(
        configure_json, callbacks["task_cb"]
    )
    assert status == TaskStatus.FAILED
    assert "Error parsing JSON." in response


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_configureband_b5b_without_subband(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
) -> None:
    """Verify behaviour of ConfigureBand for json missing subband case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    configure_json = """
    {
        "dish": {
            "receiver_band": "5b",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """

    status, response = component_manager.configure_band_with_json(
        configure_json, callbacks["task_cb"]
    )
    assert status == TaskStatus.FAILED
    expected_error_message = (
        "Invalid configuration JSON. sub_band or band5_downconversion_subband"
        " field is required for requested receiver_band [5b]."
    )
    assert expected_error_message in response


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
@pytest.mark.parametrize(
    "configure_json",
    [
        """
        {
            "dish": {
                "receiver_band": "5b",
                "band5_downconversion_subband": "4",
                "spfrx_processing_parameters": [
                    {
                        "dishes": ["all"],
                        "sync_pps": true
                    }
                ]
            }
        }
        """,
        """
        {
            "dish": {
                "receiver_band": "5b",
                "sub_band": "5",
                "spfrx_processing_parameters": [
                    {
                        "dishes": ["all"],
                        "sync_pps": true
                    }
                ]
            }
        }
        """,
    ],
)
def test_configureband_b5b_without_expected_subband_values(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    configure_json: str,
) -> None:
    """Verify behaviour of ConfigureBand for json missing subband case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    :param configure_json: the configuration JSON under test
    """
    status, response = component_manager.configure_band_with_json(
        configure_json, callbacks["task_cb"]
    )

    assert status == TaskStatus.FAILED
    expected_error_message = (
        "Invalid configuration JSON. Valid sub band required"
        " for requested receiver_band [5b]."
        ' Expected "1", "2" or "3".'
    )
    assert expected_error_message in response


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
@pytest.mark.parametrize(
    ("configure_json", "sub_band_frequency"),
    [
        (
            """{
            "dish": {
                "receiver_band": "5b",
                "band5_downconversion_subband": "1",
                "spfrx_processing_parameters": [
                    {
                        "dishes": ["all"],
                        "sync_pps": true
                    }
                ]
            }
        }""",
            11.1,
        ),
        (
            """{
            "dish": {
                "receiver_band": "5b",
                "sub_band": "2",
                "spfrx_processing_parameters": [
                    {
                        "dishes": ["all"],
                        "sync_pps": true
                    }
                ]
            }
        }""",
            13.86,
        ),
        (
            """{
            "dish": {
                "receiver_band": "5b",
                "sub_band": "3",
                "spfrx_processing_parameters": [
                    {
                        "dishes": ["all"],
                        "sync_pps": true
                    }
                ]
            }
        }""",
            13.2,
        ),
    ],
)
def test_configureband_5b_with_subband(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    configure_json: str,
    sub_band_frequency: float,
) -> None:
    """Verify behaviour of ConfigureBand for json with valid subband case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    :param configure_json: the configuration JSON under test
    """
    component_state_cb = callbacks["comp_state_cb"]

    status, response = component_manager.configure_band_with_json(
        configure_json, callbacks["task_cb"]
    )
    assert status == TaskStatus.QUEUED
    assert "Task queued" in response

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    # Build the JSON expected by SPFRX.
    expected_config = json.loads(configure_json)
    dish_config = expected_config["dish"]

    dish_config["receiver_band"] = "1"

    if "band5_downconversion_subband" in dish_config:
        dish_config["sub_band"] = dish_config.pop("band5_downconversion_subband")

    expected_json = json.dumps(expected_config)

    # check that the SPFRX component manager received the expected ConfigureBand command
    spfrx_cm = cast(SPFRxComponentManager, component_manager.sub_component_managers["SPFRX"])
    spfrx_cm_calls = spfrx_cm.execute_command.call_args_list
    assert call("ConfigureBand", expected_json) in spfrx_cm_calls

    msgs = [
        "ConfigureBand started",
        "DS.SetIndexPosition started",
        "Awaiting DS indexerposition change to B5b",
        "Running SetIndexPosition on device DS",
        "SetIndexPosition on DS timeout is 0",
        "SPFRX.ConfigureBand started",
        "Awaiting SPFRX configuredband, operatingmode change to B1, OPERATE",
        "Running ConfigureBand on device SPFRX",
        "ConfigureBand on SPFRX timeout is 0",
        "Awaiting SPFRX operatingmode change to CONFIGURE",
        "Running Wait for operatingMode.CONFIGURE on device SPFRX",
        "Awaiting SPFRX operatingmode change to CONFIGURE",
        "SPFRX operatingmode changed to CONFIGURE",
        "SPFRX.Wait for operatingMode.CONFIGURE completed",
        "ConfigureBand: Wait for operatingMode.CONFIGURE on device SPFRX completed",
        "Awaiting SPFRX operatingmode change to OPERATE",
        "Running Wait for operatingMode.OPERATE on device SPFRX",
        "Awaiting SPFRX operatingmode change to OPERATE",
        "SPFRX operatingmode changed to OPERATE",
        "SPFRX.Wait for operatingMode.OPERATE completed",
        "ConfigureBand: Wait for operatingMode.OPERATE on device SPFRX completed",
        "Awaiting SPFRX configuredband change to B1",
        "Running Wait for configuredband 1 on device SPFRX",
        "Awaiting SPFRX configuredband change to B1",
        "SPFRX configuredband changed to B1",
        "SPFRX.Wait for configuredband 1 completed",
        "ConfigureBand: Wait for configuredband 1 on device SPFRX completed",
        "B5DC.SetFrequency started",
        f"Awaiting B5DC rfcmfrequency change to {sub_band_frequency}",
        "Running SetFrequency on device B5DC",
        "SetFrequency on B5DC timeout is 0",
        "ConfigureBand complete. Triggering on success action.",
        "SetOperateMode started",
        "SPF operatingmode already OPERATE, not fanning out SetOperateMode command",
        "DS operatingmode already POINT, not fanning out SetPointMode command",
        "Fanned out commands: None",
        "Awaiting dishmode change to OPERATE",
        "SetOperateMode completed.",
    ]

    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.CONFIGURE
    )

    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        configuredband=Band.B1
    )

    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.OPERATE
    )

    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["SPF"]._update_component_state(
        bandinfocus=SPFBandInFocus.B5b
    )

    component_manager.sub_component_managers["DS"]._update_component_state(
        indexerposition=IndexerPosition.B5b
    )

    component_manager.sub_component_managers["DS"]._update_component_state(
        operatingmode=DSOperatingMode.POINT
    )

    component_manager.sub_component_managers["B5DC"]._update_component_state(
        rfcmfrequency=sub_band_frequency
    )

    progress_cb = callbacks["progress_cb"]
    for msg in msgs:
        progress_cb.wait_for_args((msg,), timeout=30)

    # wait a bit for the lrc updates to come through
    component_state_cb.wait_for_value("dishmode", DishMode.CONFIG)
    component_state_cb.wait_for_value("configuredband", Band.UNKNOWN)
    component_state_cb.wait_for_value("dishmode", DishMode.UNKNOWN)
    component_state_cb.wait_for_value("configuredband", Band.B5b)
    component_state_cb.wait_for_value("dishmode", DishMode.OPERATE)
    component_state_cb.wait_for_value("rfcmfrequency", sub_band_frequency)

    component_state_cb.get_queue_values()
    # check that the updates for the final SetOperate call in the sequence come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "SetOperateMode completed."),
    )


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
@patch("ska_mid_dish_manager.models.command_actions.apply_pointing_model")
def test_configureband_5b_with_subband_ignore_b5dc(
    mock_apply_pointing_model,
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
) -> None:
    """Verify behaviour of ConfigureBand for Band 5b with sub-band when B5DC is ignored.

    This test checks that the ConfigureBand command succeeds and correctly fans out
    commands to SPFRx and DS, but excludes B5DC because the ignoreb5dc flag is set.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_state_cb = callbacks["comp_state_cb"]
    configure_json = """
    {
        "dish": {
            "receiver_band": "5b",
            "sub_band": "1",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ] }
    }"""
    component_manager._component_state["ignoreb5dc"] = True
    component_manager.component_state["band2pointingmodelparams"] = [1.8] * 18
    mock_apply_pointing_model.return_value = None
    status, response = component_manager.configure_band_with_json(
        configure_json, callbacks["task_cb"]
    )
    assert status == TaskStatus.QUEUED
    assert "Task queued" in response
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]
    msgs = [
        "ConfigureBand started",
        "DS.SetIndexPosition started",
        "Awaiting DS indexerposition change to B5b",
        "Running SetIndexPosition on device DS",
        "SetIndexPosition on DS timeout is 0",
        "SPFRX.ConfigureBand started",
        "Awaiting SPFRX configuredband, operatingmode change to B1, OPERATE",
        "Running ConfigureBand on device SPFRX",
        "ConfigureBand on SPFRX timeout is 0",
        "Awaiting SPFRX operatingmode change to CONFIGURE",
        "Running Wait for operatingMode.CONFIGURE on device SPFRX",
        "Awaiting SPFRX operatingmode change to CONFIGURE",
        "SPFRX operatingmode changed to CONFIGURE",
        "SPFRX.Wait for operatingMode.CONFIGURE completed",
        "ConfigureBand: Wait for operatingMode.CONFIGURE on device SPFRX completed",
        "Awaiting SPFRX operatingmode change to OPERATE",
        "Running Wait for operatingMode.OPERATE on device SPFRX",
        "Awaiting SPFRX operatingmode change to OPERATE",
        "SPFRX.Wait for operatingMode.OPERATE completed",
        "ConfigureBand: Wait for operatingMode.OPERATE on device SPFRX completed",
        "Awaiting SPFRX configuredband change to B1",
        "SPFRX configuredband changed to B1",
        "SPFRX.Wait for configuredband 1 completed",
        "ConfigureBand: Wait for configuredband 1 on device SPFRX completed",
        "Awaiting B5DC rfcmfrequency change to 11.1",
        "B5DC.SetFrequency ignored",
        "ConfigureBand complete. Triggering on success action.",
        "SetOperateMode started",
        "SPF operatingmode already OPERATE, not fanning out SetOperateMode command",
        "DS operatingmode already POINT, not fanning out SetPointMode command",
        "Fanned out commands: None",
        "Awaiting dishmode change to OPERATE",
        "SetOperateMode completed.",
    ]

    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.CONFIGURE
    )

    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        configuredband=Band.B1
    )

    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.OPERATE
    )

    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["SPF"]._update_component_state(
        bandinfocus=SPFBandInFocus.B5b
    )

    component_manager.sub_component_managers["DS"]._update_component_state(
        indexerposition=IndexerPosition.B5b
    )

    component_manager.sub_component_managers["DS"]._update_component_state(
        operatingmode=DSOperatingMode.POINT
    )

    progress_cb = callbacks["progress_cb"]
    for msg in msgs:
        progress_cb.wait_for_args((msg,), timeout=20)

    # check that the component state reports the requested command
    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        configuredband=Band.B1, operatingmode=SPFRxOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        indexerposition=IndexerPosition.B5b, operatingmode=DSOperatingMode.POINT
    )
    component_state_cb.wait_for_value("configuredband", Band.B5b)
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()

    # check that the updates for the final SetOperate call in the sequence come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "SetOperateMode completed."),
    )


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_configureband_bad_root_key(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, Mock],
) -> None:
    """Verify behaviour of ConfigureBand for json missing subband case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    configure_json = """

        {
            "dish1": {
                "receiver_band": "5b",
                "band5_downconversion_subband": "1",
                "spfrx_processing_parameters": [
                    {
                        "dishes": ["SKA001"]
                    }
                ]
            }
        }
        """

    status, response = component_manager.configure_band_with_json(
        configure_json, callbacks["task_cb"]
    )
    assert status == TaskStatus.FAILED
    assert "Error parsing JSON." in response


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_configureband_invalid_receiver_band(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, Mock],
) -> None:
    """Verify behaviour of ConfigureBand for json with invalid receiver band.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    configure_json = """

        {
            "dish": {
                "receiver_band": "7",
                "spfrx_processing_parameters": [
                    {
                        "dishes": ["SKA001"]
                    }
                ]
            }
        }
        """

    status, response = component_manager.configure_band_with_json(
        configure_json, callbacks["task_cb"]
    )
    assert status == TaskStatus.FAILED
    assert "Invalid receiver band in JSON." in response


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_configureband_without_b5dc_component_manager(
    caplog: pytest.LogCaptureFixture,
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, Mock],
) -> None:
    """Verify behaviour when B5DC component manager is not present.

    This test ensures that when the B5DC component manager is absent,
    the ConfigureBand command still succeeds and a message is emitted
    indicating that B5DC operations are skipped.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    caplog.set_level(logging.DEBUG, logger=component_manager.logger.name)
    # kill all attribute monitoring threads on the b5dc component
    # manager to avoid thread check errors on session finish check
    component_manager.set_b5dc_device_ignored(True, sync=False)
    # remove the b5dc component manager to simulate it not being present
    component_manager.sub_component_managers.pop("B5DC")

    # attempt to set ignored state on b5dc and check log message is emitted
    component_manager.set_b5dc_device_ignored(False, sync=False)
    set_b5dc_device_ignored_log_message = "B5DC device is not monitored, cannot set ignored state."
    assert set_b5dc_device_ignored_log_message in caplog.text

    # attempt to configure band 5b with sub-band and check that the
    # expected log message about skipping B5DC configuration is emitted
    configure_json = """
    {
        "dish": {
            "receiver_band": "5b",
            "sub_band": "1",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ] }
    }"""
    component_manager.configure_band_with_json(configure_json, callbacks["task_cb"])

    component_state_cb = callbacks["comp_state_cb"]
    # wait a bit for the log message to come through
    component_state_cb.get_queue_values(timeout=1)

    assert (
        "Monitoring and control not set up for B5DC device, skipping frequency configuration."
        in caplog.text
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "pointing_values, should_skip",
    [
        ([1.1] * 18, False),
        ([0.0] * 18, False),
        ([], True),
    ],
)
def test_apply_pointing_model_behavior(caplog, pointing_values, should_skip):
    """Test apply_pointing_model function directly.

    - skips applying pointing model if values are empty or all zeros
    - applies otherwise
    """
    caplog.set_level("DEBUG")
    mock_logger = Mock()
    mock_cm = Mock()
    mock_task_cb = Mock()
    band_name = "2"
    band_param_name = "band2pointingmodelparams"

    mock_cm.component_state = {band_param_name: pointing_values}

    apply_pointing_model(band_param_name, band_name, mock_task_cb, mock_logger, mock_cm)

    info_msgs = [call.args[0] for call in mock_logger.info.call_args_list]

    if should_skip:
        # nothing applied, logs contain skip message
        assert any("Skipped applying pointing model" in msg for msg in info_msgs)
        mock_cm.update_pointing_model_params.assert_not_called()
    else:
        # update_pointing_model_params called, log contains success
        mock_cm.update_pointing_model_params.assert_called_once_with(
            band_param_name, pointing_values
        )
        assert any("applied successfully" in msg for msg in info_msgs)


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
@patch("ska_mid_dish_manager.models.command_actions.apply_pointing_model")
def test_spfrx_config_timed_out(
    mock_apply_pointing_model,
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
) -> None:
    """Test CONFIG timeout.

    When running configureband and the SPFRx does not change to CONFIG, but:
        - the requested band is as expected
        - the operatingmode is OPERATE
    then the command should still succeed.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_state_cb = callbacks["comp_state_cb"]
    progress_cb = callbacks["progress_cb"]
    mock_apply_pointing_model.return_value = None

    # SPFRx is already configured for the requested band and in OPERATE, so it never
    # reports CONFIGURE when ConfigureBand is fanned out to it
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        configuredband=Band.B2, operatingmode=SPFRxOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE, bandinfocus=SPFBandInFocus.B2
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        indexerposition=IndexerPosition.B2, operatingmode=DSOperatingMode.POINT
    )
    component_state_cb.wait_for_value("dishmode", DishMode.OPERATE)

    configure_json = """
    {
        "dish": {
            "receiver_band": "2",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """
    status, response = component_manager.configure_band_with_json(
        configure_json, callbacks["task_cb"]
    )
    assert status == TaskStatus.QUEUED
    assert "Task queued" in response

    msgs = [
        "ConfigureBand started",
        "SPFRX.ConfigureBand started",
        "Running ConfigureBand on device SPFRX",
        "Awaiting SPFRX operatingmode change to CONFIGURE",
        "Running Wait for operatingMode.CONFIGURE on device SPFRX",
        "SPFRX.Wait for operatingMode.CONFIGURE timed out waiting for operatingmode CONFIGURE,"
        " continuing",
        "SPFRX.Wait for operatingMode.CONFIGURE timed out",
        "ConfigureBand: Wait for operatingMode.CONFIGURE on device SPFRX completed",
        "SPFRX.Wait for operatingMode.OPERATE completed",
        "ConfigureBand: Wait for operatingMode.OPERATE on device SPFRX completed",
        "SPFRX.Wait for configuredband 2 completed",
        "ConfigureBand: Wait for configuredband 2 on device SPFRX completed",
        "ConfigureBand complete. Triggering on success action.",
        "SetOperateMode started",
        "SetOperateMode completed.",
    ]
    for msg in msgs:
        progress_cb.wait_for_args((msg,), timeout=30)

    component_state_cb.get_queue_values()
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "SetOperateMode completed."),
    )


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
@patch("ska_mid_dish_manager.models.command_actions.apply_pointing_model")
def test_spfrx_operate_timed_out(
    mock_apply_pointing_model,
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
) -> None:
    """Test OPERATE timeout.

    When running configureband and the SPFRx does not change to OPERATE from CONFIG
    then the command should fail.

    NOTE: The wait for SPFRx OPERATE has a 20s timeout, so this test takes ~20s.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_state_cb = callbacks["comp_state_cb"]
    progress_cb = callbacks["progress_cb"]
    mock_apply_pointing_model.return_value = None

    # SPFRx is in CONFIGURE before the command runs, so the CONFIGURE wait completes straight
    # away, and it stays there so the OPERATE wait times out
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.CONFIGURE
    )
    component_state_cb.wait_for_value("dishmode", DishMode.CONFIG)

    configure_json = """
    {
        "dish": {
            "receiver_band": "2",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """
    status, response = component_manager.configure_band_with_json(
        configure_json, callbacks["task_cb"]
    )
    assert status == TaskStatus.QUEUED
    assert "Task queued" in response

    msgs = [
        "ConfigureBand started",
        "SPFRX.ConfigureBand started",
        "Running ConfigureBand on device SPFRX",
        "Running Wait for operatingMode.CONFIGURE on device SPFRX",
        "SPFRX.Wait for operatingMode.CONFIGURE completed",
        "ConfigureBand: Wait for operatingMode.CONFIGURE on device SPFRX completed",
        "Awaiting SPFRX operatingmode change to OPERATE",
        "Running Wait for operatingMode.OPERATE on device SPFRX",
        "SPFRX.Wait for operatingMode.OPERATE timed out",
        "Action 'ConfigureBand' failed. Wait for operatingMode.OPERATE on device SPFRX failed.",
    ]
    for msg in msgs:
        progress_cb.wait_for_args((msg,), timeout=30)

    component_state_cb.get_queue_values()
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        status=TaskStatus.FAILED,
        result=(ResultCode.FAILED, "ConfigureBand failed"),
    )

    # The sequence stops at the failed wait, so the band wait and SetOperateMode never run
    progress_msgs = [args[0] for args in progress_cb.get_args_queue(timeout=1) if args]
    assert "Running Wait for configuredband 2 on device SPFRX" not in progress_msgs
    assert "SetOperateMode started" not in progress_msgs
