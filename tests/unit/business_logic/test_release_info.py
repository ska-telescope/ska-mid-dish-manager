"""Unit tests for ReleaseInfo class."""

import json
import time
from importlib.metadata import PackageNotFoundError
from unittest.mock import Mock, patch

import pytest

from ska_mid_dish_manager.models.dish_enums import DishDevice
from ska_mid_dish_manager.release import (
    BAD_JSON_FORMAT_VERSION,
    DISH_MANAGER_PACKAGE_NAME,
    ReleaseInfo,
    get_time_in_human_readable_format,
)
from tests.utils import generate_random_text


@pytest.mark.unit
class TestReleaseInfo:
    """Tests for ReleaseInfo"""

    def setup_method(self):
        """Set up context"""
        self._timestamp = time.time()
        self._ds_manager_add = generate_random_text()
        self._spfc_add = generate_random_text()
        self._spfrx_add = generate_random_text()
        self._release_info = ReleaseInfo(
            timestamp=self._timestamp,
            ds_manager_address=self._ds_manager_add,
            spfc_address=self._spfc_add,
            spfrx_address=self._spfrx_add,
        )

    def test_default_addresses(self):
        """Test address parsing."""
        build_state = self._release_info.get_build_state()
        build_state_json = json.loads(build_state)
        assert build_state_json["last_updated"] == get_time_in_human_readable_format(
            self._timestamp
        )
        assert (
            build_state_json["dish_manager_version"]
            == self._release_info.get_dish_manager_release_version()
        )
        assert build_state_json["ds_manager_device"]["version"] == ""
        assert build_state_json["ds_manager_device"]["address"] == self._ds_manager_add
        assert build_state_json["spfrx_device"]["version"] == ""
        assert build_state_json["spfrx_device"]["address"] == self._spfrx_add
        assert build_state_json["spfc_device"]["version"] == ""
        assert build_state_json["spfc_device"]["address"] == self._spfc_add

    def test_package_not_found(self):
        """Test response when package is not found."""
        with patch("ska_mid_dish_manager.release.version") as patched_version:
            patched_version.return_value = Mock()
            patched_version.side_effect = PackageNotFoundError("Forced Exception")
            release_info = ReleaseInfo(
                ds_manager_address=self._ds_manager_add,
                spfc_address=self._spfc_add,
                spfrx_address=self._spfrx_add,
            )
            dm_release = release_info.get_dish_manager_release_version()
            assert dm_release == f"ERR: parsing {DISH_MANAGER_PACKAGE_NAME} version."

    @pytest.mark.parametrize(
        "device, build_state_key",
        [
            (DishDevice.SPF, "spfc_device"),
            (DishDevice.SPFRX, "spfrx_device"),
        ],
    )
    def test_spf_spfrx_version_update(self, device: DishDevice, build_state_key: str):
        """Test that device versions are updated accordingly."""
        build_state_update = generate_random_text()
        self._release_info.update_build_state(device, build_state_update)
        build_state = self._release_info.get_build_state()
        build_state_json = json.loads(build_state)
        assert build_state_json[build_state_key]["version"] == build_state_update

    def test_ds_version_update(self):
        """Test that device versions are updated accordingly."""
        build_state_update_json = {"version": generate_random_text()}
        build_state_update = json.dumps(build_state_update_json)
        self._release_info.update_build_state(DishDevice.DS, build_state_update)
        build_state = self._release_info.get_build_state()
        build_state_json = json.loads(build_state)
        assert build_state_json["ds_manager_device"]["version"] == build_state_update_json

    def test_ds_manager_version_update_bad_formatting(self):
        """Test that bad json formatting is handled for ds manager version."""
        build_state_update = generate_random_text()
        self._release_info.update_build_state(DishDevice.DS, build_state_update)
        build_state = self._release_info.get_build_state()
        build_state_json = json.loads(build_state)
        assert build_state_json["ds_manager_device"]["version"] == BAD_JSON_FORMAT_VERSION
