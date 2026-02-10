"""Unit tests for the versioning dish manager."""

import json
from unittest.mock import Mock, patch

import pytest
import tango
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
    """Tests for Dish Manager Versioning."""

    def setup_method(self):
        """Set up context."""
        with (
            patch("ska_mid_dish_manager.component_managers.spfrx_cm.MonitorPing"),
            patch(
                "ska_mid_dish_manager.component_managers.tango_device_cm."
                "TangoDeviceComponentManager.start_communicating"
            ),
            patch("ska_mid_dish_manager.component_managers.dish_manager_cm.TangoDbAccessor"),
        ):

            class PatchedDM(DishManager):
                B5DCDeviceFqdn = tango.server.device_property(
                    dtype=tango.DevVarStringArray, default_value="a/b/c"
                )

            self.tango_context = DeviceTestContext(PatchedDM)
            self.tango_context.start()
            self._dish_manager_proxy = self.tango_context.device
            class_instance = PatchedDM.instances.get(self._dish_manager_proxy.name())
            self.dish_manager_cm = class_instance.component_manager

    def teardown_method(self):
        """Tear down context."""
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
        assert build_state_json["b5dc_device"]["version"] == ""
        assert build_state_json["b5dc_device"]["address"] == "a/b/c"

    @pytest.mark.parametrize(
        "device, build_state_key",
        [
            ("SPF", "spfc_device"),
            ("SPFRX", "spfrx_device"),
            ("B5DC", "b5dc_device"),
        ],
    )
    def test_build_state_update_on_subdevice_connection(self, device: str, build_state_key: str):
        """Test that spfc, spfrx and b5dc build states of subdevices get updated when a subdevice
        establishes connection.
        """
        # configure a mock build state
        dummy_build_state_version = generate_random_text()
        cm = self.dish_manager_cm.sub_component_managers[device]
        setattr(cm, "read_attribute_value", Mock(return_value=dummy_build_state_version))
        # trigger a build state update
        cm._fetch_build_state_information()

        build_state = self._dish_manager_proxy.buildState
        build_state_json = json.loads(build_state)
        assert build_state_json[build_state_key]["version"] == dummy_build_state_version

    @pytest.mark.xfail(reason="fix later")
    def test_ds_version_update_on_subdevice_connection(self):
        """Test that the ds build state gets updated when the subdevice establishes
        connection.
        """
        # configure a mock build state
        build_state_update_json = {"version": generate_random_text()}
        build_state_update = json.dumps(build_state_update_json)
        cm = self.dish_manager_cm.sub_component_managers["DS"]
        setattr(cm, "read_attribute_value", Mock(return_value=build_state_update))
        # trigger a build state update
        cm._fetch_build_state_information()

        build_state = self._dish_manager_proxy.buildState
        build_state_json = json.loads(build_state)
        assert build_state_json["ds_manager_device"]["version"] == build_state_update_json

    def test_version_id_matches_release_version(self):
        """Test that the version ID gets updated with the current release version."""
        version_id = self._dish_manager_proxy.versionId
        assert version_id == ReleaseInfo.get_dish_manager_release_version()
