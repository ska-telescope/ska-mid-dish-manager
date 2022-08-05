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

from tango import AttrWriteType, Database, DbDevInfo, DevShort, DevState
from tango.server import Device, attribute, command

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DSOperatingMode,
    DSPowerState,
    HealthState,
)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOGGER = logging.getLogger()


class DSDevice(Device):
    """Test device for use to test component manager"""

    def init_device(self):
        super().init_device()
        self._operating_mode = DSOperatingMode.STANDBY_LP
        self._configured_band = Band.NONE
        self._power_state = DSPowerState.OFF
        self._health_state = HealthState.UNKNOWN
        self._indexer_position = Band.NONE
        self.set_change_event("operatingMode", True, False)
        self.set_change_event("healthState", True, False)
        self.set_change_event("powerState", True, False)
        self.set_change_event("configuredBand", True, False)
        self.set_change_event("indexerPosition", True, False)

    # -----------
    # Attributes
    # -----------
    @attribute(
        dtype=DSOperatingMode,
        access=AttrWriteType.READ_WRITE,
    )
    def operatingMode(self):
        return self._operating_mode

    @operatingMode.write
    def operatingMode(self, op_mode: DSOperatingMode):
        self._operating_mode = op_mode
        self.push_change_event("operatingMode", self._operating_mode)

    @attribute(
        dtype=HealthState,
        access=AttrWriteType.READ_WRITE,
    )
    def healthState(self):
        return self._health_state

    @healthState.write
    def healthState(self, h_state: HealthState):
        self._health_state = h_state
        self.push_change_event("healthState", self._health_state)

    @attribute(
        dtype=DSPowerState,
        access=AttrWriteType.READ_WRITE,
    )
    def powerState(self):
        return self._power_state

    @powerState.write
    def powerState(self, pwr_state: DSPowerState):
        self._power_state = pwr_state
        self.push_change_event("powerState", self._power_state)

    @attribute(
        dtype=Band,
        access=AttrWriteType.READ_WRITE,
    )
    def indexerPosition(self):
        return self._power_state

    @indexerPosition.write
    def indexerPosition(self, band_number: Band):
        self._indexer_position = band_number
        self.push_change_event("indexerPosition", self._indexer_position)

    @attribute(
        dtype=Band,
        access=AttrWriteType.READ_WRITE,
    )
    def configuredBand(self):
        return self._configured_band

    @configuredBand.write
    def configuredBand(self, band_number: Band):
        self._configured_band = band_number
        self.push_change_event("configuredBand", self._configured_band)

    # --------
    # Commands
    # --------

    @command(dtype_in=None, doc_in="Switch On", dtype_out=None)
    def On(self):
        self.set_state(DevState.ON)

    @command(dtype_in=None, doc_in="Switch Off", dtype_out=None)
    def Off(self):
        self.set_state(DevState.OFF)

    @command(dtype_in=None, doc_in="Set StandbyLPMode", dtype_out=None)
    def SetStandbyLPMode(self):
        self._operating_mode = DSOperatingMode.STANDBY_LP
        self.push_change_event("operatingMode", self._operating_mode)

    @command(dtype_in=None, doc_in="Set StandbyFPMode", dtype_out=None)
    def SetStandbyFPMode(self):
        LOGGER.info("Called SetStandbyMode")
        self._operating_mode = DSOperatingMode.STANDBY_FP
        self.push_change_event("operatingMode", self._operating_mode)

    @command(dtype_in=None, doc_in="Set Point op mode", dtype_out=None)
    def SetPointMode(self):
        LOGGER.info("Called SetPointMode")
        self._operating_mode = DSOperatingMode.POINT
        self.push_change_event("operatingMode", self._operating_mode)

    @command(dtype_in=None, doc_in="Set SetStartupMode", dtype_out=None)
    def SetStartupMode(self):
        LOGGER.info("Called SetStartupMode")
        self._operating_mode = DSOperatingMode.STARTUP
        self.push_change_event("operatingMode", self._operating_mode)

    @command(dtype_in=None, doc_in="Track", dtype_out=None)
    def Track(self):
        LOGGER.info("Called Track")
        self._operating_mode = DSOperatingMode.POINT
        self.push_change_event("operatingMode", self._operating_mode)

    @command(
        dtype_in=DevShort, doc_in="Update indexerPosition", dtype_out=None
    )
    def SetIndexPosition(self, band_number):
        LOGGER.info("Called SetIndexPosition")
        self._indexer_position = Band(band_number)
        self.push_change_event("indexerPostion", self._indexer_position)

    @command(dtype_in=None, doc_in="Set ConfigureBand2", dtype_out=None)
    def ConfigureBand2(self):
        LOGGER.info("Called ConfigureBand2")
        self._configured_band = Band.B2
        self.push_change_event("configuredBand", self._configured_band)


def main():
    """Script entrypoint"""
    DSDevice.run_server()


if __name__ == "__main__":
    db = Database()
    test_device = DbDevInfo()
    if "DEVICE_NAME" in os.environ:
        # DEVICE_NAME should be in the format domain/family/member
        test_device.name = os.environ["DEVICE_NAME"]
    else:
        # fall back to default name
        test_device.name = "test/ds/1"
    test_device._class = "DSDevice"
    test_device.server = "DSDevice/test"
    db.add_server(test_device.server, test_device, with_dserver=True)
    main()
