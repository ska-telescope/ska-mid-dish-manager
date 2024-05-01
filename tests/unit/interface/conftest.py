"""Contains pytest fixtures for tango unit tests setup"""

from unittest.mock import MagicMock, patch

import pytest
from ska_control_model import CommunicationStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


# pylint: disable=missing-function-docstring
@pytest.fixture
def dish_manager_resources():
    with patch(
        (
            "ska_mid_dish_manager.component_managers.tango_device_cm."
            "TangoDeviceComponentManager.start_communicating"
        )
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

        # set up mocks for used methods accessing a device in the sub component managers
        ds_cm.write_attribute_value = MagicMock()
        spf_cm.write_attribute_value = MagicMock()
        spfrx_cm.write_attribute_value = MagicMock()
        ds_cm.update_state_from_monitored_attributes = MagicMock()
        spf_cm.update_state_from_monitored_attributes = MagicMock()
        spfrx_cm.update_state_from_monitored_attributes = MagicMock()

        # trigger transition to StandbyLP mode
        ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_LP)
        spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
        spf_cm._update_component_state(operatingmode=SPFOperatingMode.STANDBY_LP)

        yield device_proxy, dish_manager_cm
