"""Tests dish manager component manager configureband command handler."""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DSOperatingMode,
    IndexerPosition,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_configureband_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """Verify behaviour of ConfigureBand[x] command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_state_cb = callbacks["comp_state_cb"]
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
        "Awaiting DS indexerposition change to B2",
        "Awaiting SPFRX configuredband change to B2",
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand2",
        "Awaiting configuredband change to B2",
    ]
    progress_cb = callbacks["progress_cb"]
    for msg in msgs:
        progress_cb.wait_for_args((msg,))

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
    # component_manager._update_component_state(configuredband=Band.B2)
    component_state_cb.wait_for_value("configuredband", Band.B2)

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()
    # check that the updates for the final SetOperate call in the sequence come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "SetOperateMode completed"),
    )
    progress_cb.wait_for_args(("SetOperateMode completed",))


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_configureband_json_handler_happy(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
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
        "Awaiting SPFRX configuredband change to B2",
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand",
        "Awaiting configuredband change to B2",
    ]
    progress_cb = callbacks["progress_cb"]
    for msg in msgs:
        progress_cb.wait_for_args((msg,))

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
        result=(ResultCode.OK, "SetOperateMode completed"),
    )
    progress_cb.wait_for_args(("SetOperateMode completed",))


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_configureband_badly_formatted_json(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
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
    callbacks: dict,
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
    callbacks: dict,
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
            13.2,
        ),
    ],
)
def test_configureband_5b_with_subband(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
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

    msgs = [
        "Awaiting DS indexerposition change to B5b",
        "Awaiting SPFRX configuredband change to B5b",
        f"Awaiting B5DC rfcmfrequency change to {sub_band_frequency}",
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand, B5DC.SetFrequency",
        "Awaiting configuredband change to B5b",
    ]
    progress_cb = callbacks["progress_cb"]
    for msg in msgs:
        progress_cb.wait_for_args((msg,))

    # check that the component state reports the requested command
    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        configuredband=Band.B5b, operatingmode=SPFRxOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        indexerposition=IndexerPosition.B5b, operatingmode=DSOperatingMode.POINT
    )

    component_manager.sub_component_managers["B5DC"]._update_component_state(
        rfcmfrequency=sub_band_frequency
    )
    # wait a bit for the lrc updates to come through
    component_state_cb.wait_for_value("configuredband", Band.B5b)
    component_state_cb.wait_for_value("rfcmfrequency", sub_band_frequency, timeout=6)

    component_state_cb.get_queue_values()
    # check that the updates for the final SetOperate call in the sequence come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "SetOperateMode completed"),
    )
    progress_cb.wait_for_args(("SetOperateMode completed",))


def test_configureband_5b_with_subband_ignore_b5dc(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
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
        "Awaiting DS indexerposition change to B5b",
        "Awaiting SPFRX configuredband change to B5b",
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand",
        "B5DC.SetFrequency ignored",
        "Awaiting configuredband change to B5b",
    ]
    progress_cb = callbacks["progress_cb"]
    for msg in msgs:
        progress_cb.wait_for_args((msg,))

    # check that the component state reports the requested command
    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        configuredband=Band.B5b, operatingmode=SPFRxOperatingMode.OPERATE
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
        result=(ResultCode.OK, "SetOperateMode completed"),
    )
    progress_cb.wait_for_args(("SetOperateMode completed",))


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_configureband_bad_root_key(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
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
    callbacks: dict,
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
