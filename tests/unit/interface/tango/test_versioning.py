"""Unit tests for the versioning dish manager."""

import json
from unittest.mock import Mock, patch

import pytest
from ska_control_model import CommunicationStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.constants import (
    DEFAULT_DS_MANAGER_TRL,
    DEFAULT_SPFC_TRL,
    DEFAULT_SPFRX_TRL,
)
from ska_mid_dish_manager.release import ReleaseInfo
from tests.utils import generate_random_text


@pytest.fixture
def get_random_version():
    return generate_random_text()


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
        build_state = self._dish_manager_proxy.buildState
        build_state_json = json.loads(build_state)
        assert (
            build_state_json["dish_manager_version"]
            == ReleaseInfo.get_dish_manager_release_version()
        )
        assert build_state_json["ds_manager_device"]["version"] == ""
        assert build_state_json["ds_manager_device"]["address"] == DEFAULT_DS_MANAGER_TRL
        assert build_state_json["spfrx_device"]["version"] == ""
        assert build_state_json["spfrx_device"]["address"] == DEFAULT_SPFRX_TRL
        assert build_state_json["spfc_device"]["version"] == ""
        assert build_state_json["spfc_device"]["address"] == DEFAULT_SPFC_TRL

    @pytest.mark.skip(reason="buildState is calculated on aggregate communication state")
    @pytest.mark.parametrize(
        "device, build_state_key",
        [
            ("SPF", "spfc_device"),
            ("SPFRX", "spfrx_device"),
        ],
    )
    def test_build_state_update_on_subdevice_connection(self, device: str, build_state_key: str):
        """Test that spfc and spfrx build states of subdevices get updated when a the subdevice
        establishes connection."""
        dummy_build_state_version = generate_random_text()
        cm = self.dish_manager_cm.sub_component_managers[device]
        setattr(cm, "read_attribute_value", Mock())
        cm.read_attribute_value.return_value = dummy_build_state_version
        cm._update_communication_state(communication_state=CommunicationStatus.ESTABLISHED)
        build_state = self._dish_manager_proxy.buildState
        build_state_json = json.loads(build_state)
        assert build_state_json[build_state_key]["version"] == dummy_build_state_version

    @pytest.mark.skip(reason="buildState is calculated on aggregate communication state")
    def test_ds_version_update_on_subdevice_connection(self):
        """Test that the ds build state gets updated when a the subdevice establishes
        connection."""
        build_state_update_json = {"version": generate_random_text()}
        build_state_update = json.dumps(build_state_update_json)
        cm = self.dish_manager_cm.sub_component_managers["DS"]
        setattr(cm, "read_attribute_value", Mock())
        cm.read_attribute_value.return_value = build_state_update
        cm._update_communication_state(communication_state=CommunicationStatus.ESTABLISHED)
        build_state = self._dish_manager_proxy.buildState
        build_state_json = json.loads(build_state)
        assert build_state_json["ds_manager_device"]["version"] == build_state_update_json

    def test_build_state_update_on_subdevices_connection(self):
        """Test that the build state gets updated when all the subdevice establish connection."""
        build_states = dict(DS=Mock(), SPF=Mock(), SPFRX=Mock())
        sub_component_managers = self.dish_manager_cm.get_active_sub_component_managers()

        # configure mocks on sub device component managers read_attribute_value method
        for dev, cm in sub_component_managers.items():
            build_state_update_json = {"version": generate_random_text()}
            build_states[dev].value = json.dumps(build_state_update_json)
            setattr(cm, "read_attribute_value", Mock(return_value=build_states[dev]))

        self.dish_manager_cm._update_communication_state(
            communication_state=CommunicationStatus.ESTABLISHED
        )
        build_state = self._dish_manager_proxy.buildState
        build_state_json = json.loads(build_state)
        assert build_state_json["ds_manager_device"]["version"] == json.loads(
            build_states["DS"].value
        )
        assert build_state_json["spfc_device"]["version"] == build_states["SPF"].value
        assert build_state_json["spfrx_device"]["version"] == build_states["SPFRX"].value
