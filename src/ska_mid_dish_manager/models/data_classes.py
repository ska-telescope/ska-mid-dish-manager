"""Contains data classes used."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ska_mid_dish_manager.models.dish_enums import DishDevice


@dataclass
class DeviceInfoDataClass:
    """Format of subdevice information."""

    address: Optional[str] = ""
    version: Optional[str] = ""


@dataclass
class DmBuildStateDataClass:
    """Format of build state of dish manager and subcomponents."""

    last_updated: Optional[str] = ""
    dish_manager_version: Optional[str] = ""
    ds_manager_device: Optional[DeviceInfoDataClass] = None
    spfrx_device: Optional[DeviceInfoDataClass] = None
    spfc_device: Optional[DeviceInfoDataClass] = None
    b5dc_device: Optional[DeviceInfoDataClass] = None


@dataclass
class EventDataClass:
    device: DishDevice
    component_state: Dict[str, Any]
