"""Test Operate"""
import pytest
import tango

from ska_mid_dish_manager.devices.test_devices.utils import set_configuredBand_b1
from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_set_operate(event_store_class):
    """Test transition to OPERATE"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")

    main_event_store = event_store_class()
    progress_event_store = event_store_class()

    for attr in [
        "dishMode",
        "longRunningCommandResult",
    ]:
        dish_manager.subscribe_event(
            attr,
            tango.EventType.CHANGE_EVENT,
            main_event_store,
        )

    dish_manager.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    [[_], [unique_id]] = dish_manager.SetStandbyFPMode()
    main_event_store.wait_for_command_id(unique_id, timeout=8)

    assert dish_manager.dishMode == DishMode.STANDBY_FP

    set_configuredBand_b1()

    dish_manager.SetOperateMode()

    # Wait for the operate command to complete
    assert main_event_store.wait_for_value(DishMode.OPERATE)

    expected_progress_updates = [
        "SetPointMode called on DS",
        ("Awaiting DS operatingmode to change to [<DSOperatingMode.POINT: 7>]"),
        "SetOperateMode called on SPF",
        ("Awaiting SPF operatingmode to change to [<SPFOperatingMode.OPERATE: 3>]"),
        "CaptureData called on SPFRX",
        ("Awaiting SPFRX operatingmode to change to [<SPFRxOperatingMode.DATA_CAPTURE: 3>]"),
        "Awaiting dishmode change to 7",
        ("DS operatingmode changed to, [<DSOperatingMode.POINT: 7>]"),
        ("SPF operatingmode changed to, [<SPFOperatingMode.OPERATE: 3>]"),
        ("SPFRX operatingmode changed to, [<SPFRxOperatingMode.DATA_CAPTURE: 3>]"),
        "SetOperateMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])
    for message in expected_progress_updates:
        assert message in events_string
