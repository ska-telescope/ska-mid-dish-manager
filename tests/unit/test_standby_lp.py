"""Unit tests for setstandbylp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)

LOGGER = logging.getLogger(__name__)


# pylint: disable=missing-function-docstring
@pytest.mark.unit
@pytest.mark.forked
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_set_standbylp_fails_from_standbylp_dish_mode(patched_tango, caplog):
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
@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.xfail(reason="Intermittent event system failure")
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_set_standbylp_succeeds_from_standbyfp_dish_mode(
    patched_tango, caplog
):
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    patched_dp = MagicMock()
    patched_dp.command_inout = MagicMock()
    patched_tango.DeviceProxy = MagicMock(return_value=patched_dp)

    event_cb = MockTangoEventCallbackGroup(
        "dishMode", "longRunningCommandResult", timeout=5
    )

    with DeviceTestContext(DishManager) as device_proxy:
        sub_id = device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_cb["dishMode"],
        )
        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.component_managers["DS"]
        spf_cm = class_instance.component_manager.component_managers["SPF"]
        spfrx_cm = class_instance.component_manager.component_managers["SPFRX"]
        # Force dishManager dishMode to go to STANDBY-FP
        ds_cm._update_component_state(
            operating_mode=DSOperatingMode.STANDBY_FP
        )
        spf_cm._update_component_state(operating_mode=SPFOperatingMode.OPERATE)
        spfrx_cm._update_component_state(
            operating_mode=SPFRxOperatingMode.STANDBY
        )

        event_cb.assert_change_event("dishMode", DishMode.STANDBY_LP)
        event_cb.assert_change_event("dishMode", DishMode.STANDBY_FP)
        device_proxy.unsubscribe_event(sub_id)

        # Transition DishManager to STANDBY_LP issuing a command
        [[result_code], [unique_id]] = device_proxy.SetStandbyLPMode()
        assert ResultCode(result_code) == ResultCode.QUEUED

        sub_id = device_proxy.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_cb["longRunningCommandResult"],
        )
        # wait for the SetStandbyLPMode to be queued, i.e. the cmd
        # has been submitted to the subservient devices
        event_cb.assert_change_event("longRunningCommandResult", ("", ""))
        event_cb.assert_change_event(
            "longRunningCommandResult",
            (unique_id, '"SetStandbyLPMode queued on ds, spf and spfrx"'),
        )
        device_proxy.unsubscribe_event(sub_id)

        # transition subservient devices to their respective operatingMode
        # and observe that DishManager transitions dishMode to LP mode
        ds_cm._update_component_state(
            operating_mode=DSOperatingMode.STANDBY_LP
        )
        assert device_proxy.dishMode == DishMode.STANDBY_FP

        spf_cm._update_component_state(
            operating_mode=SPFOperatingMode.STANDBY_LP
        )
        # no need to change the component state of SPFRX
        # since it's in theexpected operating mode
        assert device_proxy.dishMode == DishMode.STANDBY_LP
