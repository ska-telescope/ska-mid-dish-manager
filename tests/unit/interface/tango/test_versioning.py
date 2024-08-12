"""Unit tests for the versioning dish manager."""

import json
from unittest.mock import Mock, patch

import pytest
from ska_control_model import CommunicationStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.constants import (
    DEFAULT_DISH_MANAGER_TRL,
    DEFAULT_SPFC_TRL,
    DEFAULT_SPFRX_TRL,
)
from ska_mid_dish_manager.release import ReleaseInfo
from tests.utils import generate_random_text


@pytest.mark.unit
@pytest.mark.forked
class TestDishManagerVersioning:
    """Tests for Dish Manager Versioning"""

    def setup_method(self):
        """Set up context."""
        with patch(
            (
                "ska_mid_dish_manager.component_managers.tango_device_cm."
                "TangoDeviceComponentManager.start_communicating"
            )
        ):
            self.tango_context = DeviceTestContext(DishManager)
            self.tango_context.start()
            self._dish_manager_proxy = self.tango_context.device
            class_instance = DishManager.instances.get(self._dish_manager_proxy.name())
            self.dish_manager_cm = class_instance.component_manager

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()

    def test_versioning_before_subdevice_connection(self):
        """Read build state on startup before subdevices connect to dish manager."""
        buildState = self._dish_manager_proxy.buildState
        build_state_json = json.loads(buildState)
        build_state_json["dish_manager_version"] = ReleaseInfo.get_dish_manager_release_version()
        build_state_json["ds_manager_version"] = ""
        build_state_json["spfrx_version"] = ""
        build_state_json["spfc_version"] = ""
        build_state_json["ds_manager_address"] = DEFAULT_DISH_MANAGER_TRL
        build_state_json["spfrx_address"] = DEFAULT_SPFRX_TRL
        build_state_json["spfc_address"] = DEFAULT_SPFC_TRL

    @pytest.mark.parametrize(
        "device, build_state_key",
        [
            ("DS", "ds_manager_version"),
            ("SPF", "spfc_version"),
            ("SPFRX", "spfrx_version"),
        ],
    )
    def test_build_state_update_on_subdevice_connection(self, device: str, build_state_key: str):
        """Test that the associated build states of subdevices get updated when a the subdevice
        establishes connection."""
        cm = self.dish_manager_cm.sub_component_managers[device]
        setattr(cm, "read_attribute_value", Mock())
        dummy_build_state_version = generate_random_text()
        cm.read_attribute_value.return_value = dummy_build_state_version
        cm._update_communication_state(communication_state=CommunicationStatus.ESTABLISHED)
        buildState = self._dish_manager_proxy.buildState
        build_state_json = json.loads(buildState)
        assert build_state_json[build_state_key] == dummy_build_state_version
