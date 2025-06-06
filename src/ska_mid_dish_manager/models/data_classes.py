"""Contains data classes used."""

from dataclasses import dataclass
from typing import Optional


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
