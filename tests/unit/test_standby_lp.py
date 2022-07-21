"""Unit tests for setstandby_lp command."""

import logging
import time
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_tango_base.commands import ResultCode
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import DishMode, OperatingMode

LOGGER = logging.getLogger(__name__)


def assert_change_events(dev_proxy, attr_name, expected_value, timeout=2):
    """Check the events for expected value"""
    event_cb = tango.utils.EventCallback()
    sub_id = dev_proxy.subscribe_event(
        attr_name,
        tango.EventType.CHANGE_EVENT,
        event_cb,
    )
    future = time.time() + timeout
    now = time.time()
    events = []
    while now < future or expected_value not in events:
        events = [
            evt_data.attr_value.value for evt_data in event_cb.get_events()
        ]
        now = time.time()
    dev_proxy.unsubscribe_event(sub_id)
    assert dev_proxy.read_attribute(attr_name).value == expected_value


# pylint: disable=missing-function-docstring
@pytest.mark.unit
@pytest.mark.forked
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_standby_lp_cmd_fails_from_standby_lp_dish_mode(patched_tango, caplog):
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    mocked_device_proxy = MagicMock()
    patched_tango.DeviceProxy = MagicMock(return_value=mocked_device_proxy)

    with DeviceTestContext(DishManager) as device_proxy:
        # Transition happens almost instantly on a fast machine,
        # even before we can complete event subscription or a MockCallable.
        # Give it a few tries for a slower machine
        for i in range(20):
            LOGGER.info("waiting for STANDBY_LP [%s]", i)
            if device_proxy.dishMode == DishMode.STANDBY_LP:
                break
        assert device_proxy.dishMode == DishMode.STANDBY_LP

        with pytest.raises(tango.DevFailed):
            _, _ = device_proxy.SetStandbyLPMode()


# pylint: disable=missing-function-docstring, protected-access, invalid-name
@pytest.mark.xfail(reason="Intermittent event system down")
@pytest.mark.unit
@pytest.mark.forked
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_standby_lp_cmd_succeeds_from_standby_fp_dish_mode(
    patched_tango, caplog
):
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    patched_dp = MagicMock()
    patched_dp.command_inout = MagicMock()
    patched_tango.DeviceProxy = MagicMock(return_value=patched_dp)

    with DeviceTestContext(DishManager) as device_proxy:
        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.component_managers["DS"]
        spf_cm = class_instance.component_manager.component_managers["SPF"]
        spfrx_cm = class_instance.component_manager.component_managers["SPFRX"]
        # Update the operatingMode of the underlying devices
        # This will force dishManager dishMode to go to STANDBY-FP
        for cm in [ds_cm, spf_cm, spfrx_cm]:
            cm._update_component_state(operating_mode=OperatingMode.STANDBY_FP)

        assert_change_events(
            device_proxy, "dishMode", DishMode.STANDBY_FP.value
        )

        # Transition DishManager to STANDBY_LP issuing a command
        [[result_code], [unique_id]] = device_proxy.SetStandbyLPMode()
        assert ResultCode(result_code) == ResultCode.QUEUED

        # wait for the SetStandbyLPMode to be queued, i.e. the cmd
        # has been submitted to the subservient devices
        lrc_result = (
            unique_id,
            '"SetStandbyLPMode queued on ds, spf and spfrx"',
        )
        assert_change_events(
            device_proxy, "longRunningCommandResult", lrc_result
        )

        # transition subservient devices to LP mode and observe that
        # DishManager transitions dishMode to LP mode after all
        # subservient devices are in LP
        ds_cm._update_component_state(operating_mode=OperatingMode.STANDBY_LP)
        assert device_proxy.dishMode == DishMode.STANDBY_FP

        spf_cm._update_component_state(operating_mode=OperatingMode.STANDBY_LP)
        assert device_proxy.dishMode == DishMode.STANDBY_FP

        spfrx_cm._update_component_state(
            operating_mode=OperatingMode.STANDBY_LP
        )
        assert device_proxy.dishMode == DishMode.STANDBY_LP
