"""Tests dish manager component manager configureband command handler."""

import json
import logging
import threading
from typing import cast
from unittest.mock import MagicMock, Mock, call

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.component_managers.spfrx_cm import SPFRxComponentManager
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
def test_configureband_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of ConfigureBand[x] command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: an event used to request task abortion
    """
    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]
    component_manager.reapply_pointing_model = Mock(return_value=(ResultCode.OK, "msg"))
    component_manager.component_state["band2pointingmodelparams"] = [1.8] * 18

    # task is submitted to executor by tango device server, to get the same async execution
    # function should also be spawned in a thread
    threading.Thread(
        target=component_manager.configure_band_cmd,
        args=(Band.B2, True),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    ).start()
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values(timeout=1)

    component_manager.sub_component_managers["SPF"]._update_component_state(
        bandinfocus=SPFBandInFocus.B2,
        operatingmode=SPFOperatingMode.OPERATE,
    )
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        configuredband=Band.B2, operatingmode=SPFRxOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        indexerposition=IndexerPosition.B2, operatingmode=DSOperatingMode.POINT
    )

    # check that the component state reports the requested command
    received_updates = component_state_cb.get_queue_values()
    last_two_updates = received_updates[-2:]
    assert last_two_updates == [{"dishmode": DishMode.OPERATE}, {"configuredband": Band.B2}]
    # Verify apply_pointing_model was called
    component_manager.reapply_pointing_model.assert_called_once()
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=None, progress_info="Awaiting DS indexerposition change to B2"),
        call(
            progress=None,
            progress_info="Awaiting SPFRX configuredband, operatingmode change to B2, OPERATE",
        ),
        call(
            progress=None,
            progress_info="Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand2",
        ),
        call(progress=None, progress_info="Awaiting configuredband change to B2"),
        call(progress=None, progress_info="DS indexerposition changed to B2"),
        call(progress=None, progress_info="DS.SetIndexPosition completed"),
        call(progress=None, progress_info="SPFRX configuredband changed to B2"),
        call(progress=None, progress_info="SPFRX operatingmode changed to OPERATE"),
        call(progress=None, progress_info="SPFRX.ConfigureBand2 completed"),
        call(
            progress=None, progress_info="ConfigureBand2 complete. Triggering on success action."
        ),
        call(
            progress=None,
            progress_info=(
                "SPF operatingmode already OPERATE, not fanning out SetOperateMode command"
            ),
        ),
        call(
            progress=None,
            progress_info="DS operatingmode already POINT, not fanning out SetPointMode command",
        ),
        call(progress=None, progress_info="Fanned out commands: None"),
        call(progress=None, progress_info="Awaiting dishmode change to OPERATE"),
        call(progress=None, progress_info="SetOperateMode completed."),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "SetOperateMode completed.")),
    ]


@pytest.mark.unit
def test_configureband_json_handler_happy(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of ConfigureBand for json happy case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: an event to signal task abortion
    """
    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]
    configure_json = """
    {
        "dish": {
            "receiver_band": "1",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """
    component_manager.reapply_pointing_model = Mock(return_value=(ResultCode.OK, "msg"))
    component_manager.component_state["band1pointingmodelparams"] = [1.8] * 18

    threading.Thread(
        target=component_manager.configure_band_with_json,
        args=(configure_json,),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    ).start()
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values(timeout=1)

    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        configuredband=Band.B1, operatingmode=SPFRxOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        indexerposition=IndexerPosition.B1, operatingmode=DSOperatingMode.POINT
    )

    # check that the component state reports the requested command
    received_updates = component_state_cb.get_queue_values()
    last_two_updates = received_updates[-2:]
    assert last_two_updates == [{"dishmode": DishMode.OPERATE}, {"configuredband": Band.B1}]
    # Verify apply_pointing_model was called
    component_manager.reapply_pointing_model.assert_called_once()
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=None, progress_info="Awaiting DS indexerposition change to B1"),
        call(
            progress=None,
            progress_info="Awaiting SPFRX configuredband, operatingmode change to B1, OPERATE",
        ),
        call(
            progress=None,
            progress_info="Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand",
        ),
        call(progress=None, progress_info="Awaiting configuredband change to B1"),
        call(progress=None, progress_info="DS indexerposition changed to B1"),
        call(progress=None, progress_info="DS.SetIndexPosition completed"),
        call(progress=None, progress_info="SPFRX configuredband changed to B1"),
        call(progress=None, progress_info="SPFRX operatingmode changed to OPERATE"),
        call(progress=None, progress_info="SPFRX.ConfigureBand completed"),
        call(progress=None, progress_info="ConfigureBand complete. Triggering on success action."),
        call(
            progress=None,
            progress_info=(
                "SPF operatingmode already OPERATE, not fanning out SetOperateMode command"
            ),
        ),
        call(
            progress=None,
            progress_info="DS operatingmode already POINT, not fanning out SetPointMode command",
        ),
        call(progress=None, progress_info="Fanned out commands: None"),
        call(progress=None, progress_info="Awaiting dishmode change to OPERATE"),
        call(progress=None, progress_info="SetOperateMode completed."),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "SetOperateMode completed.")),
    ]


@pytest.mark.unit
def test_configureband_badly_formatted_json(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of ConfigureBand for json badly formatted case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: an event to signal task abortion

    """
    task_cb = callbacks["task_cb"]
    configure_json = """
    {
        "dish": {
            "receiver_band": "2",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
    """

    component_manager.configure_band_with_json(
        configure_json, task_callback=task_cb, task_abort_event=task_abort_event
    )
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.FAILED, "Error parsing JSON.")),
    ]


@pytest.mark.unit
def test_configureband_b5b_without_subband(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of ConfigureBand for json missing subband case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: an event to signal task abortion

    """
    task_cb = callbacks["task_cb"]
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

    component_manager.configure_band_with_json(
        configure_json, task_callback=task_cb, task_abort_event=task_abort_event
    )
    expected_error_message = (
        "Invalid configuration JSON. sub_band or band5_downconversion_subband"
        " field is required for requested receiver_band [5b]."
    )
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.FAILED, expected_error_message)),
    ]


@pytest.mark.unit
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
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of ConfigureBand for json missing subband case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param configure_json: the configuration JSON under test
    :param task_abort_event: the event to signal task abortion
    """
    component_manager.configure_band_with_json(
        configure_json, task_callback=callbacks["task_cb"], task_abort_event=task_abort_event
    )

    expected_error_message = (
        "Invalid configuration JSON. Valid sub band required"
        " for requested receiver_band [5b]."
        ' Expected "1", "2" or "3".'
    )
    assert callbacks["task_cb"].call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.FAILED, expected_error_message)),
    ]


@pytest.mark.unit
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
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of ConfigureBand for json with valid subband case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param configure_json: the configuration JSON under test
    :param sub_band_frequency: the expected sub-band frequency
    :param task_abort_event: the event to signal task abortion
    """
    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]

    threading.Thread(
        target=component_manager.configure_band_with_json,
        args=(configure_json,),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    ).start()
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values(timeout=1)

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

    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        configuredband=Band.B1, operatingmode=SPFRxOperatingMode.OPERATE
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        indexerposition=IndexerPosition.B5b, operatingmode=DSOperatingMode.POINT
    )
    component_manager.sub_component_managers["B5DC"]._update_component_state(
        rfcmfrequency=sub_band_frequency
    )

    # check that the component state reports the requested command
    received_updates = component_state_cb.get_queue_values()
    last_three_updates = received_updates[-3:]
    assert last_three_updates == [
        {"dishmode": DishMode.OPERATE},
        {"configuredband": Band.B5b},
        {"rfcmfrequency": sub_band_frequency},
    ]

    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=None, progress_info="Awaiting DS indexerposition change to B5b"),
        call(
            progress=None,
            progress_info="Awaiting SPFRX configuredband, operatingmode change to B1, OPERATE",
        ),
        call(
            progress=None,
            progress_info=f"Awaiting B5DC rfcmfrequency change to {sub_band_frequency}",
        ),
        call(
            progress=None,
            progress_info=(
                "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand, B5DC.SetFrequency"
            ),
        ),
        call(progress=None, progress_info="Awaiting configuredband change to B5b"),
        call(progress=None, progress_info="DS indexerposition changed to B5b"),
        call(progress=None, progress_info="DS.SetIndexPosition completed"),
        call(progress=None, progress_info="SPFRX configuredband changed to B1"),
        call(progress=None, progress_info="SPFRX operatingmode changed to OPERATE"),
        call(progress=None, progress_info="SPFRX.ConfigureBand completed"),
        call(progress=None, progress_info=f"B5DC rfcmfrequency changed to {sub_band_frequency}"),
        call(progress=None, progress_info="B5DC.SetFrequency completed"),
        call(progress=None, progress_info="ConfigureBand complete. Triggering on success action."),
        call(
            progress=None,
            progress_info=(
                "SPF operatingmode already OPERATE, not fanning out SetOperateMode command"
            ),
        ),
        call(
            progress=None,
            progress_info="DS operatingmode already POINT, not fanning out SetPointMode command",
        ),
        call(progress=None, progress_info="Fanned out commands: None"),
        call(progress=None, progress_info="Awaiting dishmode change to OPERATE"),
        call(progress=None, progress_info="SetOperateMode completed."),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "SetOperateMode completed.")),
    ]


@pytest.mark.unit
def test_configureband_5b_with_subband_ignore_b5dc(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of ConfigureBand for Band 5b with sub-band when B5DC is ignored.

    This test checks that the ConfigureBand command succeeds and correctly fans out
    commands to SPFRx and DS, but excludes B5DC because the ignoreb5dc flag is set.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: an event to signal task abortion
    """
    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]
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
    component_manager.component_state["band5bpointingmodelparams"] = [1.8] * 18
    component_manager.reapply_pointing_model = Mock(return_value=(ResultCode.OK, "msg"))

    threading.Thread(
        target=component_manager.configure_band_with_json,
        args=(configure_json,),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    ).start()
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values(timeout=1)

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

    # check that the component state reports the requested command
    received_updates = component_state_cb.get_queue_values()
    last_two_updates = received_updates[-2:]
    assert last_two_updates == [{"dishmode": DishMode.OPERATE}, {"configuredband": Band.B5b}]
    # Verify apply_pointing_model was called
    component_manager.reapply_pointing_model.assert_called_once()

    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=None, progress_info="Awaiting DS indexerposition change to B5b"),
        call(
            progress=None,
            progress_info="Awaiting SPFRX configuredband, operatingmode change to B1, OPERATE",
        ),
        call(progress=None, progress_info="Awaiting B5DC rfcmfrequency change to 11.1"),
        call(
            progress=None,
            progress_info="Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand",
        ),
        call(progress=None, progress_info="Awaiting configuredband change to B5b"),
        call(progress=None, progress_info="B5DC.SetFrequency ignored"),
        call(progress=None, progress_info="DS indexerposition changed to B5b"),
        call(progress=None, progress_info="DS.SetIndexPosition completed"),
        call(progress=None, progress_info="SPFRX configuredband changed to B1"),
        call(progress=None, progress_info="SPFRX operatingmode changed to OPERATE"),
        call(progress=None, progress_info="SPFRX.ConfigureBand completed"),
        call(progress=None, progress_info="ConfigureBand complete. Triggering on success action."),
        call(
            progress=None,
            progress_info=(
                "SPF operatingmode already OPERATE, not fanning out SetOperateMode command"
            ),
        ),
        call(
            progress=None,
            progress_info="DS operatingmode already POINT, not fanning out SetPointMode command",
        ),
        call(progress=None, progress_info="Fanned out commands: None"),
        call(progress=None, progress_info="Awaiting dishmode change to OPERATE"),
        call(progress=None, progress_info="SetOperateMode completed."),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "SetOperateMode completed.")),
    ]


@pytest.mark.unit
def test_configureband_bad_root_key(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, Mock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of ConfigureBand for json missing subband case.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: the threading event used to signal task abortion
    """
    task_cb = callbacks["task_cb"]
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

    component_manager.configure_band_with_json(
        configure_json, task_callback=task_cb, task_abort_event=task_abort_event
    )
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.FAILED, "Error parsing JSON.")),
    ]


@pytest.mark.unit
def test_configureband_invalid_receiver_band(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, Mock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of ConfigureBand for json with invalid receiver band.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: the threading event used to signal task abortion
    """
    task_cb = callbacks["task_cb"]
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

    component_manager.configure_band_with_json(
        configure_json, task_callback=task_cb, task_abort_event=task_abort_event
    )
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(
            status=TaskStatus.COMPLETED,
            result=(ResultCode.FAILED, "Invalid receiver band in JSON."),
        ),
    ]


@pytest.mark.unit
def test_configureband_without_b5dc_component_manager(
    caplog: pytest.LogCaptureFixture,
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, Mock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour when B5DC component manager is not present.

    This test ensures that when the B5DC component manager is absent,
    the ConfigureBand command still succeeds and a message is emitted
    indicating that B5DC operations are skipped.

    :param caplog: the pytest log capture fixture
    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: the threading event used to signal task abortion
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
    component_manager.configure_band_with_json(
        configure_json, task_callback=callbacks["task_cb"], task_abort_event=task_abort_event
    )

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
    reapply_pointing_model = DishManagerComponentManager.reapply_pointing_model
    caplog.set_level("DEBUG")
    mock_cm = Mock()
    band_name = "2"
    band_param_name = "band2pointingmodelparams"

    mock_cm.component_state = {band_param_name: pointing_values}

    reapply_pointing_model(mock_cm, band_param_name, band_name)

    info_msgs = [call.args[0] for call in mock_cm.logger.info.call_args_list]

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
