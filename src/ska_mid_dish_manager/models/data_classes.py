"""Contains data classes used."""
# pylint: disable=invalid-name
from dataclasses import dataclass
from typing import Optional


@dataclass
class DmBuildStateDataClass:
    """Format of build state of dish manager and subcomponents."""

    DishManagerVersion: Optional[str] = ""
    DsManagerVersion: Optional[str] = ""
    SPFRxVersion: Optional[str] = ""
    SPFCVersion: Optional[str] = ""
    DsManagerAddress: Optional[str] = ""
    SPFRxAddress: Optional[str] = ""
    SPFCAddress: Optional[str] = ""
