"""Release information for ska-mid-dish-manager Python Package."""
import json
from dataclasses import asdict
from importlib.metadata import PackageNotFoundError, version

from ska_mid_dish_manager.models.data_classes import DmBuildStateDataClass
from ska_mid_dish_manager.models.dish_enums import Device

PYTHON_PACKAGE = "ska_mid_dish_simulators"
BUILD_STATE_SPACING = 4


def get_release_version():
    """Get release version of package."""
    try:
        release_version = version(PYTHON_PACKAGE)
    except PackageNotFoundError:
        release_version = f"ERR: parsing {PYTHON_PACKAGE} version."
    return release_version


class ReleaseInfo:
    """Class containing version release information."""

    def __init__(
        self, ds_manager_address: str = "", spfc_address: str = "", spfrx_address: str = ""
    ) -> None:
        self._build_state = DmBuildStateDataClass(
            DsManagerAddress=ds_manager_address,
            SPFCAddress=spfc_address,
            SPFRxAddress=spfrx_address,
        )

        self._device_to_update_method_map = {
            Device.DS: self._update_ds_manager_version,
            Device.SPF: self._update_spfc_version,
            Device.SPFRX: self._update_spfrx_version,
        }

    def get_build_state(self) -> str:
        """Get JSON string of build state dataclass."""
        return json.dumps(asdict(self._build_state), indent=BUILD_STATE_SPACING)

    def update_build_state(self, device: Device, build_state: str) -> str:
        """Update relevant subdevice build information and return build state."""
        if device in self._device_to_update_method_map:
            self._device_to_update_method_map[device](build_state)

        return self.get_build_state()

    def _update_ds_manager_version(self, ds_manager_version: str) -> None:
        """Update DS manager version information."""
        self._build_state.DsManagerVersion = ds_manager_version

    def _update_spfc_version(self, spfc_version: str) -> None:
        """Update SPFC version information."""
        self._build_state.SPFCVersion = spfc_version

    def _update_spfrx_version(self, spfrx_version: str) -> None:
        """Update SPFRx version information."""
        self._build_state.SPFRxVersion = spfrx_version
