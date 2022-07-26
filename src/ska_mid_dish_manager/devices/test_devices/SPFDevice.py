"""Adapted from ska-tango-examples TestDevice.py"""
# pylint: disable=invalid-name
# pylint: disable=too-many-instance-attributes
# pylint: disable=missing-function-docstring
# pylint: disable=no-self-use
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods
# pylint: disable=attribute-defined-outside-init
import asyncio
import json
import os
import random

from tango import (
    AttrWriteType,
    Database,
    DbDevInfo,
    DevState,
    ErrSeverity,
    Except,
    GreenMode,
)
from tango.server import Device, attribute, command

from ska_mid_dish_manager.devices.test_devices.LMCDevice import LMCDevice
from ska_mid_dish_manager.models.dish_enums import (
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


class SPFDevice(LMCDevice):
    """Test device for use to test component manager"""

    def init_device(self):
        super().init_device()
        self._operating_mode = SPFOperatingMode.STARTUP

    @attribute(
        dtype=SPFOperatingMode,
        access=AttrWriteType.READ_WRITE,
        polling_period=1000,
    )
    def operatingMode(self):
        return self._operating_mode

    def write_operatingMode(self, new_value):
        self._operating_mode = new_value

    @command(dtype_in=None, doc_in="Set SPFOperatingMode", dtype_out=None)
    async def SetStandbyLPMode(self):
        self._operating_mode = SPFOperatingMode.STANDBY_LP

    @command(dtype_in=None, doc_in="Set SPFOperatingMode", dtype_out=None)
    async def SetStandbyFPMode(self):
        self._operating_mode = SPFOperatingMode.STANDBY_FP


def main():
    """Script entrypoint"""
    SPFDevice.run_server()


if __name__ == "__main__":
    db = Database()
    test_device = DbDevInfo()
    if "DEVICE_NAME" in os.environ:
        # DEVICE_NAME should be in the format domain/family/member
        test_device.name = os.environ["DEVICE_NAME"]
    else:
        # fall back to default name
        test_device.name = "test/spf/1"
    test_device._class = "SPFDevice"
    test_device.server = "SPFDevice/test"
    db.add_server(test_device.server, test_device, with_dserver=True)
    main()
