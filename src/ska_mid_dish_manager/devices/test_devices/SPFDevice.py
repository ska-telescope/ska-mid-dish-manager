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

from tango import AttrWriteType, Database, DbDevInfo, GreenMode
from tango.server import Device, attribute, command

from ska_mid_dish_manager.models.dish_enums import (
    HealthState,
    SPFOperatingMode,
    SPFPowerState,
)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOGGER = logging.getLogger()


class SPFDevice(Device):
    """Test device for LMC"""

    green_mode = GreenMode.Asyncio

    def init_device(self):
        super().init_device()
        self._operating_mode = SPFOperatingMode.STARTUP
        self._power_state = SPFPowerState.UNKNOWN
        self._health_state = HealthState.UNKNOWN
        self.set_change_event("operatingMode", True)
        self.set_change_event("healthState", True)
        self.set_change_event("powerState", True)

    @attribute(
        dtype=SPFOperatingMode,
        access=AttrWriteType.READ_WRITE,
    )
    async def operatingMode(self):
        return self._operating_mode

    def write_operatingMode(self, new_value):
        self._operating_mode = new_value
        self.push_change_event("operatingMode", self._operating_mode)

    @attribute(
        dtype=HealthState,
        access=AttrWriteType.READ_WRITE,
    )
    async def healthState(self):
        return self._health_state

    def write_healthState(self, new_value):
        self._health_state = new_value
        self.push_change_event("healthState", self._health_state)

    @attribute(
        dtype=SPFPowerState,
        access=AttrWriteType.READ_WRITE,
    )
    async def powerState(self):
        return self._power_state

    def write_powerState(self, new_value):
        self._power_state = new_value
        self.push_change_event("powerState", self._power_state)

    @command(dtype_in=None, doc_in="Set SPFOperatingMode", dtype_out=None)
    async def SetStandbyLPMode(self):
        LOGGER.info("Called SetStandbyMode")
        self._operating_mode = SPFOperatingMode.STANDBY_LP
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
