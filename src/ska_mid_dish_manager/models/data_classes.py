"""Contains data classes used."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class DmBuildStateDataClass:
    """Format of build state of dish manager and subcomponents."""

    dish_manager_version: Optional[str] = ""
    ds_manager_version: Optional[str] = ""
    spfrx_version: Optional[str] = ""
    spfc_version: Optional[str] = ""
    ds_manager_address: Optional[str] = ""
    spfrx_address: Optional[str] = ""
    spfc_address: Optional[str] = ""
