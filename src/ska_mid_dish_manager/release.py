"""Release information for ska-mid-dish-manager Python Package."""

import json
import time
from dataclasses import asdict
from importlib.metadata import PackageNotFoundError, version

from ska_mid_dish_manager.models.data_classes import DeviceInfoDataClass, DmBuildStateDataClass
from ska_mid_dish_manager.models.dish_enums import DishDevice

DISH_MANAGER_PACKAGE_NAME = "ska_mid_dish_manager"
BAD_JSON_FORMAT_VERSION = "Bad JSON formatting."
BUILD_STATE_SPACING = 4


def get_time_in_human_readable_format(timestamp) -> str:
    """Get time in human readable format."""
    return time.strftime("%d-%m-%Y %H:%M:%S", time.localtime(timestamp))


class ReleaseInfo:
    """Class containing version release information."""

    def __init__(
        self,
        timestamp: float = time.time(),
        ds_manager_address: str = "",
        spfc_address: str = "",
        spfrx_address: str = "",
        b5dc_address: str = "",
    ) -> None:
        self._timestamp = get_time_in_human_readable_format(timestamp)
        self._ds_manager_device_info = DeviceInfoDataClass(ds_manager_address)
        self._spfrx_device_info = DeviceInfoDataClass(spfrx_address)
        self._spfc_device_info = DeviceInfoDataClass(spfc_address)
        self.b5dc_device_info = DeviceInfoDataClass(b5dc_address)
        self._build_state = DmBuildStateDataClass(
            last_updated=self._timestamp,
            dish_manager_version=self.get_dish_manager_release_version(),
            ds_manager_device=self._ds_manager_device_info,
            spfrx_device=self._spfrx_device_info,
            spfc_device=self._spfc_device_info,
            b5dc_device=self.b5dc_device_info,
        )

        self._device_to_update_method_map = {
            DishDevice.DS: self._update_ds_manager_version,
            DishDevice.SPF: self._update_spfc_version,
            DishDevice.SPFRX: self._update_spfrx_version,
            DishDevice.B5DC: self._update_b5dc_version,
        }

    def get_build_state(self) -> str:
        """Get JSON string of build state dataclass."""
        return json.dumps(asdict(self._build_state), indent=BUILD_STATE_SPACING)

    def update_build_state(self, device: DishDevice, build_state: str) -> str:
        """Update relevant subdevice build information and return build state."""
        if device in self._device_to_update_method_map:
            self._device_to_update_method_map[device](build_state)

        return self.get_build_state()

    def _update_ds_manager_version(self, ds_manager_version: str) -> None:
        """Update DS manager version information."""
        try:
            version_info = json.loads(ds_manager_version)
        except (json.JSONDecodeError, TypeError):
            version_info = BAD_JSON_FORMAT_VERSION
        self._build_state.ds_manager_device.version = version_info

    def _update_spfc_version(self, spfc_version: str) -> None:
        """Update SPFC version information."""
        self._build_state.spfc_device.version = spfc_version

    def _update_spfrx_version(self, spfrx_version: str) -> None:
        """Update SPFRx version information."""
        self._build_state.spfrx_device.version = spfrx_version

    def _update_b5dc_version(self, b5dc_version: str) -> None:
        """Update B5DC version information."""
        self.b5dc_device_info.version = b5dc_version

    @staticmethod
    def get_dish_manager_release_version() -> str:
        """Get release version of package."""
        try:
            release_version = version(DISH_MANAGER_PACKAGE_NAME)
        except PackageNotFoundError:
            release_version = f"ERR: parsing {DISH_MANAGER_PACKAGE_NAME} version."
        return release_version
