"""Unit tests for setstandby_lp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_tango_base.commands import ResultCode
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import DishMode, OperatingMode

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
# pylint:disable=protected-access
@pytest.mark.unit
@pytest.mark.forked
class TestStandByLPModePermissionFail:
    """Tests for TestStandByFPMode failure"""

    def setup_method(self):
        """Set up context"""
        with patch(
            "ska_mid_dish_manager.component_managers.tango_device_cm.tango"
        ) as patched_tango:
            patched_dp = MagicMock()
            patched_dp.command_inout = MagicMock()
            patched_tango.DeviceProxy = MagicMock(return_value=patched_dp)
            self.tango_context = DeviceTestContext(DishManager)
            self.tango_context.start()

    def test_standb_by_lp(self, event_store):
        """Execute tests"""
        device_proxy = self.tango_context.device
        device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        assert event_store.wait_for_value(DishMode.STANDBY_LP)

        with pytest.raises(tango.DevFailed):
            _, _ = device_proxy.SetStandbyLPMode()

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()


# pylint:disable=attribute-defined-outside-init
# pylint:disable=protected-access
@pytest.mark.unit
@pytest.mark.forked
class TestStandByLPModeTest:
    """Tests for TestStandByFPMode"""

    def setup_method(self):
        """Set up context"""
        with patch(
            "ska_mid_dish_manager.component_managers.tango_device_cm.tango"
        ) as patched_tango:
            patched_dp = MagicMock()
            patched_dp.command_inout = MagicMock()
            patched_tango.DeviceProxy = MagicMock(return_value=patched_dp)
            self.tango_context = DeviceTestContext(DishManager)
            self.tango_context.start()

    def test_standb_by_lp(self, event_store):
        """Execute tests"""
        device_proxy = self.tango_context.device
        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.component_managers["DS"]
        spf_cm = class_instance.component_manager.component_managers["SPF"]
        spfrx_cm = class_instance.component_manager.component_managers["SPFRX"]

        device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        device_proxy.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        # Update the operatingMode of the underlying devices
        # This will force dishManager dishMode to go to STANDBY-FP
        for comp_man in [ds_cm, spf_cm, spfrx_cm]:
            comp_man._update_component_state(
                operating_mode=OperatingMode.STANDBY_FP
            )

        assert event_store.wait_for_value(DishMode.STANDBY_FP)

        # Transition DishManager to STANDBY_LP issuing a command
        [[result_code], [unique_id]] = device_proxy.SetStandbyLPMode()
        assert ResultCode(result_code) == ResultCode.QUEUED

        assert event_store.wait_for_command_result(
            unique_id, '"SetStandbyLPMode queued on ds, spf and spfrx"'
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
        assert event_store.wait_for_value(DishMode.STANDBY_LP)

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()
