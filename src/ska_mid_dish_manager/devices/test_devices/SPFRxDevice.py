"""Adapted from ska-tango-examples TestDevice.py"""
# pylint: disable=invalid-name
# pylint: disable=too-many-instance-attributes
# pylint: disable=missing-function-docstring
# pylint: disable=no-self-use
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods
# pylint: disable=attribute-defined-outside-init
import logging
import os
import sys

from tango import AttrWriteType, Database, DbDevInfo, DevBoolean, GreenMode
from tango.server import Device, attribute, command

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    HealthState,
    SPFRxOperatingMode,
)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOGGER = logging.getLogger()


class SPFRxDevice(Device):
    """Test device for LMC"""

    green_mode = GreenMode.Asyncio

    def init_device(self):
        super().init_device()
        self._operating_mode = SPFRxOperatingMode.STANDBY
        self._configured_band = Band.NONE
        self._health_state = HealthState.UNKNOWN
        self.set_change_event("operatingMode", True, False)
        self.set_change_event("healthState", True, False)
        self.set_change_event("configuredBand", True, False)

    # -----------
    # Attributes
    # -----------

    @attribute(
        dtype=SPFRxOperatingMode,
        access=AttrWriteType.READ_WRITE,
    )
    async def operatingMode(self):
        return self._operating_mode

    @operatingMode.write
    async def operatingMode(self, op_mode: SPFRxOperatingMode):
        self._operating_mode = op_mode
        self.push_change_event("operatingMode", self._operating_mode)

    @attribute(
        dtype=HealthState,
        access=AttrWriteType.READ_WRITE,
    )
    async def healthState(self):
        return self._health_state

    @healthState.write
    async def healthState(self, h_state: HealthState):
        self._health_state = h_state
        self.push_change_event("healthState", self._health_state)

    @attribute(
        dtype=Band,
        access=AttrWriteType.READ_WRITE,
    )
    async def configuredBand(self):
        return self._configured_band

    @configuredBand.write
    async def configuredBand(self, band_number: Band):
        self._configured_band = band_number
        self.push_change_event("configuredBand", self._configured_band)

    # --------
    # Commands
    # --------

    @command(dtype_in=None, doc_in="Set SPFRXOperatingMode", dtype_out=None)
    async def SetStandbyMode(self):
        LOGGER.info("Called SetStandbyMode")
        self._operating_mode = SPFRxOperatingMode.STANDBY
        self.push_change_event("operatingMode", self._operating_mode)

    @command(dtype_in=None, doc_in="Set SetStartupMode", dtype_out=None)
    async def SetStartupMode(self):
        LOGGER.info("Called SetStartupMode")
        self._operating_mode = SPFRxOperatingMode.STARTUP
        self.push_change_event("operatingMode", self._operating_mode)

    @command(dtype_in=DevBoolean, doc_in="CaptureData", dtype_out=None)
    # pylint: disable=unused-argument
    async def CaptureData(self, boolean_value):
        LOGGER.info("Called SetStartupMode")
        self._operating_mode = SPFRxOperatingMode.DATA_CAPTURE
        self.push_change_event("operatingMode", self._operating_mode)

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
