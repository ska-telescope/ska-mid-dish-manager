"""Contains pytest fixtures for tango unit tests setup."""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import CommunicationStatus, ResultCode, TaskStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


@pytest.fixture
def dish_manager_resources():
    with (
        patch("ska_mid_dish_manager.component_managers.spfrx_cm.MonitorPing"),
        patch(
            "ska_mid_dish_manager.component_managers.tango_device_cm."
            "TangoDeviceComponentManager.start_communicating"
        ),
        patch(
            "ska_mid_dish_manager.component_managers.wms_cm."
            "WMSComponentManager.start_communicating"
        ),
    ):
        tango_context = DeviceTestContext(DishManager)
        tango_context.start()
        device_proxy = tango_context.device

        class_instance = DishManager.instances.get(device_proxy.name())
        dish_manager_cm = class_instance.component_manager
        ds_cm = dish_manager_cm.sub_component_managers["DS"]
        spf_cm = dish_manager_cm.sub_component_managers["SPF"]
        spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

        # trigger communication established on all sub components
        for com_man in [ds_cm, spf_cm, spfrx_cm]:
            com_man._update_communication_state(
                communication_state=CommunicationStatus.ESTABLISHED
            )

        # patch run method which spawns a thread
        def _simulate_lrc_callbacks(*args, **kwargs):
            task_callback = args[-1]
            task_callback(status=TaskStatus.IN_PROGRESS)
            task_callback(status=TaskStatus.COMPLETED, result=(ResultCode.OK, str(None)))
            return TaskStatus.QUEUED, "message"

        for com_man in [ds_cm, spf_cm, spfrx_cm]:
            com_man.run_device_command = Mock(side_effect=_simulate_lrc_callbacks)

        # set up mocks for methods creating a device proxy to the sub component
        candidate_stub_methods = [
            "update_state_from_monitored_attributes",
            "write_attribute_value",
            "read_attribute_value",
            "execute_command",
        ]
        for method_name in candidate_stub_methods:
            setattr(ds_cm, method_name, Mock())
            setattr(spf_cm, method_name, Mock())
            setattr(spfrx_cm, method_name, Mock())

        # trigger transition to StandbyLP mode
        ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_LP)
        spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
        spf_cm._update_component_state(operatingmode=SPFOperatingMode.STANDBY_LP)

        yield device_proxy, dish_manager_cm
