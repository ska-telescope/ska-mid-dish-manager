"""Adapted from ska-tango-examples TestDevice.py"""
# pylint: disable=invalid-name
# pylint: disable=too-many-instance-attributes
# pylint: disable=missing-function-docstring
# pylint: disable=no-self-use
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods
# pylint: disable=attribute-defined-outside-init
import os

from tango import AttrWriteType, Database, DbDevInfo, GreenMode
from tango.server import Device, attribute, command

from ska_mid_dish_manager.models.dish_enums import SPFRxOperatingMode, Band


class SPFRxDevice(Device):
    """Test device for use to test component manager"""

    green_mode = GreenMode.Asyncio

    def init_device(self):
        super().init_device()
        self._operating_mode = SPFRxOperatingMode.STARTUP
        self._configured_band = Band.NONE

    @attribute(
        dtype=SPFRxOperatingMode,
        access=AttrWriteType.READ_WRITE,
        polling_period=1000,
    )
    async def operatingMode(self):
        return self._operating_mode

    def write_operatingMode(self, new_value):
        self._operating_mode = new_value

    @command(dtype_in=None, doc_in="Set SPFRXOperatingMode", dtype_out=None)
    async def SetStandbyMode(self):
        self._operating_mode = SPFRxOperatingMode.STANDBY

    @attribute(
        dtype=Band,
        access=AttrWriteType.READ_WRITE,
        polling_period=1000,
    )
    async def configuredBand(self):
        return self._configured_band

    def write_configuredBand(self, new_value):
        self._configured_band = new_value

    @command(dtype_in=None, doc_in="Set ConfigureBand2", dtype_out=None)
    async def ConfigureBand2(self):
        self._configured_band = Band.B2


def main():
    """Script entrypoint"""
    SPFRxDevice.run_server()


if __name__ == "__main__":
    db = Database()
    test_device = DbDevInfo()
    if "DEVICE_NAME" in os.environ:
        # DEVICE_NAME should be in the format domain/family/member
        test_device.name = os.environ["DEVICE_NAME"]
    else:
        # fall back to default name
        test_device.name = "test/spfrx/1"
    test_device._class = "SPFRxDevice"
    test_device.server = "SPFRxDevice/test"
    db.add_server(test_device.server, test_device, with_dserver=True)
    main()
