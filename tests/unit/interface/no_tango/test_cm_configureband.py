"""Tests dish manager component manager configureband command handler."""

import json
import logging
import threading
from unittest.mock import MagicMock, Mock, call

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    SPFBandInFocus,
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from tests.utils import progress_call, wait_for_progress


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
    spfrx_cm = component_manager.sub_component_managers["SPFRX"]
    ds_cm = component_manager.sub_component_managers["DS"]
    spf_cm = component_manager.sub_component_managers["SPF"]

    # task is submitted to executor by tango device server, to get the same async execution
    # function should also be spawned in a thread
    command_thread = threading.Thread(
        target=component_manager.configure_band_cmd,
        args=(Band.B2, True),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    )
    command_thread.start()

    wait_for_progress(task_cb, "Running Wait for operatingMode.CONFIGURE on device SPFRX")
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.CONFIGURE)
    wait_for_progress(task_cb, "SPFRX operatingmode changed to CONFIGURE")
    component_state_cb.wait_for_value("dishmode", DishMode.CONFIG)

    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.OPERATE)
    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    component_state_cb.wait_for_value("dishmode", DishMode.OPERATE)

    ds_cm._update_component_state(indexerposition=IndexerPosition.B2)
    spfrx_cm._update_component_state(configuredband=Band.B2)
    spf_cm._update_component_state(bandinfocus=SPFBandInFocus.B2)
    component_state_cb.wait_for_value("configuredband", Band.B2)
    # Verify apply_pointing_model was called
    component_manager.reapply_pointing_model.assert_called_once()

    # wait for all the updates to be processed by the command thread
    command_thread.join(timeout=30)
    assert not command_thread.is_alive(), "ConfigureBand did not finish in time"
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        progress_call("ConfigureBand2 started"),
        progress_call("DS.SetIndexPosition started"),
        progress_call("Awaiting DS indexerposition change to B2"),
        progress_call("Running SetIndexPosition on device DS"),
        progress_call("SetIndexPosition on DS timeout is 0"),
        progress_call("SPFRX.ConfigureBand2 started"),
        progress_call("Running ConfigureBand2 on device SPFRX"),
        progress_call("ConfigureBand2 on SPFRX timeout is 0"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call("Running Wait for operatingMode.CONFIGURE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call("SPFRX operatingmode changed to CONFIGURE"),
        progress_call("SPFRX.Wait for operatingMode.CONFIGURE completed"),
        progress_call(
            "ConfigureBand2: Wait for operatingMode.CONFIGURE on device SPFRX completed"
        ),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("Running Wait for operatingMode.OPERATE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("SPFRX operatingmode changed to OPERATE"),
        progress_call("SPFRX.Wait for operatingMode.OPERATE completed"),
        progress_call("ConfigureBand2: Wait for operatingMode.OPERATE on device SPFRX completed"),
        progress_call("Awaiting SPFRX configuredband change to B2"),
        progress_call("Running Wait for configuredband 2 on device SPFRX"),
        progress_call("Awaiting SPFRX configuredband change to B2"),
        progress_call("SPFRX configuredband changed to B2"),
        progress_call("SPFRX.Wait for configuredband 2 completed"),
        progress_call("ConfigureBand2: Wait for configuredband 2 on device SPFRX completed"),
        progress_call("ConfigureBand2 complete. Triggering on success action."),
        progress_call("SetOperateMode started"),
        progress_call("SPF operatingmode already OPERATE, not fanning out SetOperateMode command"),
        progress_call("DS operatingmode already POINT, not fanning out SetPointMode command"),
        progress_call("Fanned out commands: None"),
        progress_call("Awaiting dishmode change to OPERATE"),
        progress_call("SetOperateMode completed."),
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
    spfrx_cm = component_manager.sub_component_managers["SPFRX"]
    ds_cm = component_manager.sub_component_managers["DS"]
    spf_cm = component_manager.sub_component_managers["SPF"]

    command_thread = threading.Thread(
        target=component_manager.configure_band_with_json,
        args=(configure_json,),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    )
    command_thread.start()

    wait_for_progress(task_cb, "Running Wait for operatingMode.CONFIGURE on device SPFRX")
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.CONFIGURE)
    wait_for_progress(task_cb, "SPFRX operatingmode changed to CONFIGURE")
    component_state_cb.wait_for_value("dishmode", DishMode.CONFIG)

    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.OPERATE)
    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    component_state_cb.wait_for_value("dishmode", DishMode.OPERATE)

    ds_cm._update_component_state(indexerposition=IndexerPosition.B1)
    spfrx_cm._update_component_state(configuredband=Band.B1)
    spf_cm._update_component_state(bandinfocus=SPFBandInFocus.B1)
    component_state_cb.wait_for_value("configuredband", Band.B1)
    # Verify apply_pointing_model was called
    component_manager.reapply_pointing_model.assert_called_once()

    # wait for all the updates to be processed by the command thread
    command_thread.join(timeout=30)
    assert not command_thread.is_alive(), "ConfigureBand did not finish in time"
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        progress_call("ConfigureBand started"),
        progress_call("DS.SetIndexPosition started"),
        progress_call("Awaiting DS indexerposition change to B1"),
        progress_call("Running SetIndexPosition on device DS"),
        progress_call("SetIndexPosition on DS timeout is 0"),
        progress_call("SPFRX.ConfigureBand started"),
        progress_call("Awaiting SPFRX configuredband, operatingmode change to B1, OPERATE"),
        progress_call("Running ConfigureBand on device SPFRX"),
        progress_call("ConfigureBand on SPFRX timeout is 0"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call("Running Wait for operatingMode.CONFIGURE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call("SPFRX operatingmode changed to CONFIGURE"),
        progress_call("SPFRX.Wait for operatingMode.CONFIGURE completed"),
        progress_call("ConfigureBand: Wait for operatingMode.CONFIGURE on device SPFRX completed"),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("Running Wait for operatingMode.OPERATE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("SPFRX operatingmode changed to OPERATE"),
        progress_call("SPFRX.Wait for operatingMode.OPERATE completed"),
        progress_call("ConfigureBand: Wait for operatingMode.OPERATE on device SPFRX completed"),
        progress_call("Awaiting SPFRX configuredband change to B1"),
        progress_call("Running Wait for configuredband 1 on device SPFRX"),
        progress_call("Awaiting SPFRX configuredband change to B1"),
        progress_call("SPFRX configuredband changed to B1"),
        progress_call("SPFRX.Wait for configuredband 1 completed"),
        progress_call("ConfigureBand: Wait for configuredband 1 on device SPFRX completed"),
        progress_call("ConfigureBand complete. Triggering on success action."),
        progress_call("SetOperateMode started"),
        progress_call("SPF operatingmode already OPERATE, not fanning out SetOperateMode command"),
        progress_call("DS operatingmode already POINT, not fanning out SetPointMode command"),
        progress_call("Fanned out commands: None"),
        progress_call("Awaiting dishmode change to OPERATE"),
        progress_call("SetOperateMode completed."),
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

    spfrx_cm = component_manager.sub_component_managers["SPFRX"]
    ds_cm = component_manager.sub_component_managers["DS"]
    spf_cm = component_manager.sub_component_managers["SPF"]
    b5dc_cm = component_manager.sub_component_managers["B5DC"]

    command_thread = threading.Thread(
        target=component_manager.configure_band_with_json,
        args=(configure_json,),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    )
    command_thread.start()

    # Build the JSON expected by SPFRX.
    expected_config = json.loads(configure_json)
    dish_config = expected_config["dish"]

    dish_config["receiver_band"] = "1"

    if "band5_downconversion_subband" in dish_config:
        dish_config["sub_band"] = dish_config.pop("band5_downconversion_subband")

    expected_json = json.dumps(expected_config)
    # check that the SPFRX component manager received the expected ConfigureBand command
    spfrx_cm_calls = spfrx_cm.execute_command.call_args_list
    assert call("ConfigureBand", expected_json) in spfrx_cm_calls

    wait_for_progress(task_cb, "Running Wait for operatingMode.CONFIGURE on device SPFRX")
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.CONFIGURE)
    wait_for_progress(task_cb, "SPFRX operatingmode changed to CONFIGURE")
    component_state_cb.wait_for_value("dishmode", DishMode.CONFIG)

    spfrx_cm._update_component_state(configuredband=Band.B1)
    component_state_cb.wait_for_value("configuredband", Band.UNKNOWN)

    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.OPERATE)
    component_state_cb.wait_for_value("dishmode", DishMode.UNKNOWN)

    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spf_cm._update_component_state(bandinfocus=SPFBandInFocus.B5b)

    ds_cm._update_component_state(indexerposition=IndexerPosition.B5b)
    component_state_cb.wait_for_value("configuredband", Band.B5b)

    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
    component_state_cb.wait_for_value("dishmode", DishMode.OPERATE)

    b5dc_cm._update_component_state(rfcmfrequency=sub_band_frequency)
    component_state_cb.wait_for_value("rfcmfrequency", sub_band_frequency)

    # wait for all the updates to be processed by the command thread
    command_thread.join(timeout=30)
    assert not command_thread.is_alive(), "ConfigureBand did not finish in time"
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        progress_call("ConfigureBand started"),
        progress_call("DS.SetIndexPosition started"),
        progress_call("Awaiting DS indexerposition change to B5b"),
        progress_call("Running SetIndexPosition on device DS"),
        progress_call("SetIndexPosition on DS timeout is 0"),
        progress_call("SPFRX.ConfigureBand started"),
        progress_call("Awaiting SPFRX configuredband, operatingmode change to B1, OPERATE"),
        progress_call("Running ConfigureBand on device SPFRX"),
        progress_call("ConfigureBand on SPFRX timeout is 0"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call("Running Wait for operatingMode.CONFIGURE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call("SPFRX operatingmode changed to CONFIGURE"),
        progress_call("SPFRX.Wait for operatingMode.CONFIGURE completed"),
        progress_call("ConfigureBand: Wait for operatingMode.CONFIGURE on device SPFRX completed"),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("Running Wait for operatingMode.OPERATE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("SPFRX operatingmode changed to OPERATE"),
        progress_call("SPFRX.Wait for operatingMode.OPERATE completed"),
        progress_call("ConfigureBand: Wait for operatingMode.OPERATE on device SPFRX completed"),
        progress_call("Awaiting SPFRX configuredband change to B1"),
        progress_call("Running Wait for configuredband 1 on device SPFRX"),
        progress_call("Awaiting SPFRX configuredband change to B1"),
        progress_call("SPFRX configuredband changed to B1"),
        progress_call("SPFRX.Wait for configuredband 1 completed"),
        progress_call("ConfigureBand: Wait for configuredband 1 on device SPFRX completed"),
        progress_call("B5DC.SetFrequency started"),
        progress_call(f"Awaiting B5DC rfcmfrequency change to {sub_band_frequency}"),
        progress_call("Running SetFrequency on device B5DC"),
        progress_call("SetFrequency on B5DC timeout is 0"),
        progress_call("ConfigureBand complete. Triggering on success action."),
        progress_call("SetOperateMode started"),
        progress_call("SPF operatingmode already OPERATE, not fanning out SetOperateMode command"),
        progress_call("DS operatingmode already POINT, not fanning out SetPointMode command"),
        progress_call("Fanned out commands: None"),
        progress_call("Awaiting dishmode change to OPERATE"),
        progress_call("SetOperateMode completed."),
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
    spfrx_cm = component_manager.sub_component_managers["SPFRX"]
    ds_cm = component_manager.sub_component_managers["DS"]
    spf_cm = component_manager.sub_component_managers["SPF"]
    component_manager.reapply_pointing_model = Mock(return_value=(ResultCode.OK, "msg"))

    command_thread = threading.Thread(
        target=component_manager.configure_band_with_json,
        args=(configure_json,),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    )
    command_thread.start()

    wait_for_progress(task_cb, "Running Wait for operatingMode.CONFIGURE on device SPFRX")
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.CONFIGURE)
    wait_for_progress(task_cb, "SPFRX operatingmode changed to CONFIGURE")
    spfrx_cm._update_component_state(configuredband=Band.B1)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.OPERATE)

    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spf_cm._update_component_state(bandinfocus=SPFBandInFocus.B5b)

    ds_cm._update_component_state(indexerposition=IndexerPosition.B5b)
    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)

    # check that the component state reports the requested command
    component_state_cb.wait_for_value("dishmode", DishMode.OPERATE)
    # Verify apply_pointing_model was called
    component_manager.reapply_pointing_model.assert_called_once()

    # wait for all the updates to be processed by the command thread
    command_thread.join(timeout=30)
    assert not command_thread.is_alive(), "ConfigureBand did not finish in time"
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        progress_call("ConfigureBand started"),
        progress_call("DS.SetIndexPosition started"),
        progress_call("Awaiting DS indexerposition change to B5b"),
        progress_call("Running SetIndexPosition on device DS"),
        progress_call("SetIndexPosition on DS timeout is 0"),
        progress_call("SPFRX.ConfigureBand started"),
        progress_call("Awaiting SPFRX configuredband, operatingmode change to B1, OPERATE"),
        progress_call("Running ConfigureBand on device SPFRX"),
        progress_call("ConfigureBand on SPFRX timeout is 0"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call("Running Wait for operatingMode.CONFIGURE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call("SPFRX operatingmode changed to CONFIGURE"),
        progress_call("SPFRX.Wait for operatingMode.CONFIGURE completed"),
        progress_call("ConfigureBand: Wait for operatingMode.CONFIGURE on device SPFRX completed"),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("Running Wait for operatingMode.OPERATE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("SPFRX operatingmode changed to OPERATE"),
        progress_call("SPFRX.Wait for operatingMode.OPERATE completed"),
        progress_call("ConfigureBand: Wait for operatingMode.OPERATE on device SPFRX completed"),
        progress_call("Awaiting SPFRX configuredband change to B1"),
        progress_call("Running Wait for configuredband 1 on device SPFRX"),
        progress_call("Awaiting SPFRX configuredband change to B1"),
        progress_call("SPFRX configuredband changed to B1"),
        progress_call("SPFRX.Wait for configuredband 1 completed"),
        progress_call("ConfigureBand: Wait for configuredband 1 on device SPFRX completed"),
        progress_call("Awaiting B5DC rfcmfrequency change to 11.1"),
        progress_call("B5DC.SetFrequency ignored"),
        progress_call("ConfigureBand complete. Triggering on success action."),
        progress_call("SetOperateMode started"),
        progress_call("SPF operatingmode already OPERATE, not fanning out SetOperateMode command"),
        progress_call("DS operatingmode already POINT, not fanning out SetPointMode command"),
        progress_call("Fanned out commands: None"),
        progress_call("Awaiting dishmode change to OPERATE"),
        progress_call("SetOperateMode completed."),
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


@pytest.mark.unit
def test_spfrx_config_timed_out(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Test CONFIG timeout.

    When running configureband and the SPFRx does not change to CONFIG, but:
        - the requested band is as expected
        - the operatingmode is OPERATE
    then the command should still succeed.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: an event to signal task abortion
    """
    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]
    component_manager.reapply_pointing_model = Mock(return_value=(ResultCode.OK, "msg"))
    spfrx_cm = component_manager.sub_component_managers["SPFRX"]
    ds_cm = component_manager.sub_component_managers["DS"]
    spf_cm = component_manager.sub_component_managers["SPF"]

    # SPFRx is already configured for the requested band and in OPERATE, so it never
    # reports CONFIGURE when ConfigureBand is fanned out to it
    spfrx_cm._update_component_state(
        configuredband=Band.B2, operatingmode=SPFRxOperatingMode.OPERATE
    )
    spf_cm._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE, bandinfocus=SPFBandInFocus.B2
    )
    ds_cm._update_component_state(
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

    command_thread = threading.Thread(
        target=component_manager.configure_band_with_json,
        args=(configure_json,),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    )
    command_thread.start()

    # wait for all the updates to be processed by the command thread
    command_thread.join(timeout=30)
    assert not command_thread.is_alive(), "ConfigureBand did not finish in time"
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        progress_call("ConfigureBand started"),
        progress_call("SPFRX.ConfigureBand started"),
        progress_call("Awaiting SPFRX configuredband, operatingmode change to B2, OPERATE"),
        progress_call("Running ConfigureBand on device SPFRX"),
        progress_call("ConfigureBand on SPFRX timeout is 0"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call("Running Wait for operatingMode.CONFIGURE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call(
            "SPFRX.Wait for operatingMode.CONFIGURE timed out "
            "waiting for operatingmode CONFIGURE, continuing"
        ),
        progress_call("SPFRX.Wait for operatingMode.CONFIGURE timed out"),
        progress_call("ConfigureBand: Wait for operatingMode.CONFIGURE on device SPFRX completed"),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("Running Wait for operatingMode.OPERATE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("SPFRX operatingmode changed to OPERATE"),
        progress_call("SPFRX.Wait for operatingMode.OPERATE completed"),
        progress_call("ConfigureBand: Wait for operatingMode.OPERATE on device SPFRX completed"),
        progress_call("Awaiting SPFRX configuredband change to B2"),
        progress_call("Running Wait for configuredband 2 on device SPFRX"),
        progress_call("Awaiting SPFRX configuredband change to B2"),
        progress_call("SPFRX configuredband changed to B2"),
        progress_call("SPFRX.Wait for configuredband 2 completed"),
        progress_call("ConfigureBand: Wait for configuredband 2 on device SPFRX completed"),
        progress_call("ConfigureBand complete. Triggering on success action."),
        progress_call("SetOperateMode started"),
        progress_call("SPF operatingmode already OPERATE, not fanning out SetOperateMode command"),
        progress_call("DS operatingmode already POINT, not fanning out SetPointMode command"),
        progress_call("Fanned out commands: None"),
        progress_call("Awaiting dishmode change to OPERATE"),
        progress_call("SetOperateMode completed."),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "SetOperateMode completed.")),
    ]


def test_spfrx_operate_timed_out(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test ConfigureBand fails when SPFRx doesn't move from CONFIGURE to OPERATE.

    The 12s SPFRx OPERATE wait is patched to 1s to keep the test fast.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: an event to signal task abortion
    :param monkeypatch: pytest fixture for patching the OPERATE wait time
    """
    # patch the module that reads the constant
    monkeypatch.setattr("ska_mid_dish_manager.models.command_actions.SPFRX_OPERATE_WAIT_TIME", 1)

    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]
    component_manager.reapply_pointing_model = Mock(return_value=(ResultCode.OK, "msg"))
    spfrx_cm = component_manager.sub_component_managers["SPFRX"]

    # SPFRx is in CONFIGURE before the command runs, so the CONFIGURE wait completes
    # straight away, and it stays there so the OPERATE wait times out
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.CONFIGURE)
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

    command_thread = threading.Thread(
        target=component_manager.configure_band_with_json,
        args=(configure_json,),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    )
    command_thread.start()

    # wait for all the updates to be processed by the command thread
    command_thread.join(timeout=30)
    assert not command_thread.is_alive(), "ConfigureBand did not finish in time"

    # The sequence stops at the failed OPERATE wait, so the band wait and SetOperateMode
    # never run
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        progress_call("ConfigureBand started"),
        progress_call("DS.SetIndexPosition started"),
        progress_call("Awaiting DS indexerposition change to B2"),
        progress_call("Running SetIndexPosition on device DS"),
        progress_call("SetIndexPosition on DS timeout is 0"),
        progress_call("SPFRX.ConfigureBand started"),
        progress_call("Awaiting SPFRX configuredband, operatingmode change to B2, OPERATE"),
        progress_call("Running ConfigureBand on device SPFRX"),
        progress_call("ConfigureBand on SPFRX timeout is 0"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call("Running Wait for operatingMode.CONFIGURE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to CONFIGURE"),
        progress_call("SPFRX operatingmode changed to CONFIGURE"),
        progress_call("SPFRX.Wait for operatingMode.CONFIGURE completed"),
        progress_call("ConfigureBand: Wait for operatingMode.CONFIGURE on device SPFRX completed"),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("Running Wait for operatingMode.OPERATE on device SPFRX"),
        progress_call("Awaiting SPFRX operatingmode change to OPERATE"),
        progress_call("SPFRX.Wait for operatingMode.OPERATE timed out"),
        progress_call(
            "Action 'ConfigureBand' failed. Wait for operatingMode.OPERATE on device SPFRX failed."
        ),
        call(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.FAILED,
                "Action 'ConfigureBand' failed. "
                "Wait for operatingMode.OPERATE on device SPFRX failed.",
            ),
        ),
    ]
