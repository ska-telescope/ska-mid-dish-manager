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

from tango import AttrWriteType, Database, DbDevInfo
from tango.server import Device, attribute, command

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    HealthState,
    SPFOperatingMode,
    SPFPowerState,
)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOGGER = logging.getLogger()


class SPFDevice(Device):
    """Test device for LMC"""

    def init_device(self):
        super().init_device()
        self._operating_mode = SPFOperatingMode.STANDBY_LP
        self._power_state = SPFPowerState.UNKNOWN
        self._health_state = HealthState.UNKNOWN
        self._band_in_focus = Band.NONE
        self.set_change_event("operatingMode", True, False)
        self.set_change_event("healthState", True, False)
        self.set_change_event("powerState", True, False)
        self.set_change_event("bandInFocus", True, False)

    # -----------
    # Attributes
    # -----------

    @attribute(
        dtype=SPFOperatingMode,
        access=AttrWriteType.READ_WRITE,
    )
    def operatingMode(self):
        return self._operating_mode

    @operatingMode.write
    def write_operatingMode(self, op_mode: SPFOperatingMode):
        self._operating_mode = op_mode
        self.push_change_event("operatingMode", self._operating_mode)

    @attribute(
        dtype=Band,
        access=AttrWriteType.READ_WRITE,
    )
    def bandInFocus(self):
        return self._band_in_focus

    @bandInFocus.write
    def bandInFocus(self, band_number: Band):
        self._band_in_focus = band_number

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
        dtype=SPFPowerState,
        access=AttrWriteType.READ_WRITE,
    )
    def powerState(self):
        return self._power_state

    @powerState.write
    def powerState(self, pwr_state: SPFPowerState):
        self._power_state = pwr_state
        self.push_change_event("powerState", self._power_state)

    # --------
    # Commands
    # --------

    @command(dtype_in=None, doc_in="Set SPFOperatingMode", dtype_out=None)
    async def SetStandbyLPMode(self):
        LOGGER.info("Called SetStandbyMode")
        self._operating_mode = SPFOperatingMode.STANDBY_LP
        self.push_change_event("operatingMode", self._operating_mode)

    @command(dtype_in=None, doc_in="Set SPFOperatingMode", dtype_out=None)
    async def SetOperateMode(self):
        LOGGER.info("Called SetOperateMode")
        self._operating_mode = SPFOperatingMode.OPERATE
        self.push_change_event("operatingMode", self._operating_mode)

    @command(dtype_in=None, doc_in="Set SetStartupMode", dtype_out=None)
    async def SetStartupMode(self):
        LOGGER.info("Called SetStartupMode")
        self._operating_mode = SPFOperatingMode.STARTUP
        self.push_change_event("operatingMode", self._operating_mode)


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
