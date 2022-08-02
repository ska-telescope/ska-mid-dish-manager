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
    SPFRxOperatingMode,
)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOGGER = logging.getLogger()


class SPFRxDevice(Device):
    """Test device for use to test component manager"""

    green_mode = GreenMode.Asyncio

    def init_device(self):
        super().init_device()
        self._operating_mode = SPFRxOperatingMode.STARTUP
        self._health_state = HealthState.UNKNOWN
        self.set_change_event("operatingMode", True)
        self.set_change_event("healthState", True)

    @attribute(
        dtype=SPFRxOperatingMode,
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

    @command(dtype_in=None, doc_in="Set SPFRXOperatingMode", dtype_out=None)
    async def SetStandbyMode(self):
        LOGGER.info("Called SetStandbyMode")
        self._operating_mode = SPFRxOperatingMode.STANDBY
        self.push_change_event("operatingMode", self._operating_mode)


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
