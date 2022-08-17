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

from ska_mid_dish_manager.devices.test_devices.utils import (
    random_delay_execution,
)
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    HealthState,
    SPFCapabilityStates,
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
        self._operating_mode = SPFOperatingMode.STANDBY_LP
        self._power_state = SPFPowerState.UNKNOWN
        self._health_state = HealthState.UNKNOWN
        self._band_in_focus = Band.NONE
        self._b1_capability_state = SPFCapabilityStates.UNKNOWN
        self._b2_capability_state = SPFCapabilityStates.UNKNOWN
        self._b3_capability_state = SPFCapabilityStates.UNKNOWN
        self._b4_capability_state = SPFCapabilityStates.UNKNOWN
        self._b5_capability_state = SPFCapabilityStates.UNKNOWN

        change_event_attributes = (
            "operatingMode",
            "powerState",
            "healthState",
            "bandInFocus",
            "b1CapabilityState",
            "b2CapabilityState",
            "b3CapabilityState",
            "b4CapabilityState",
            "b5CapabilityState",
        )
        for attr in change_event_attributes:
            self.set_change_event(attr, True, False)

    # -----------
    # Attributes
    # -----------

    @attribute(
        dtype=SPFCapabilityStates,
        access=AttrWriteType.READ_WRITE,
        doc="Report the device b1CapabilityState",
    )
    async def b1CapabilityState(self):
        """Returns the b1CapabilityState"""
        return self._b1_capability_state

    @b1CapabilityState.write
    async def b1CapabilityState(self, value):
        """Set the b1CapabilityState"""
        # pylint: disable=attribute-defined-outside-init
        self._b1_capability_state = SPFCapabilityStates(value)
        self.push_change_event("b1CapabilityState", self._b1_capability_state)

    @attribute(
        dtype=SPFCapabilityStates,
        access=AttrWriteType.READ_WRITE,
        doc="Report the device b2CapabilityState",
    )
    async def b2CapabilityState(self):
        """Returns the b2CapabilityState"""
        return self._b2_capability_state

    @b2CapabilityState.write
    async def b2CapabilityState(self, value):
        """Set the b2CapabilityState"""
        # pylint: disable=attribute-defined-outside-init
        self._b2_capability_state = SPFCapabilityStates(value)
        self.push_change_event("b2CapabilityState", self._b2_capability_state)

    @attribute(
        dtype=SPFCapabilityStates,
        access=AttrWriteType.READ_WRITE,
        doc="Report the device b3CapabilityState",
    )
    async def b3CapabilityState(self):
        """Returns the b3CapabilityState"""
        return self._b3_capability_state

    @b3CapabilityState.write
    async def b3CapabilityState(self, value):
        """Set the b3CapabilityState"""
        # pylint: disable=attribute-defined-outside-init
        self._b3_capability_state = SPFCapabilityStates(value)
        self.push_change_event("b3CapabilityState", self._b3_capability_state)

    @attribute(
        dtype=SPFCapabilityStates,
        access=AttrWriteType.READ_WRITE,
        doc="Report the device b4CapabilityState",
    )
    async def b4CapabilityState(self):
        """Returns the b4CapabilityState"""
        return self._b4_capability_state

    @b4CapabilityState.write
    async def b4CapabilityState(self, value):
        """Set the b4CapabilityState"""
        # pylint: disable=attribute-defined-outside-init
        self._b4_capability_state = SPFCapabilityStates(value)
        self.push_change_event("b4CapabilityState", self._b4_capability_state)

    @attribute(
        dtype=SPFCapabilityStates,
        access=AttrWriteType.READ_WRITE,
        doc="Report the device b5CapabilityState",
    )
    async def b5CapabilityState(self):
        """Returns the b5CapabilityState"""
        return self._b5_capability_state

    @b5CapabilityState.write
    async def b5CapabilityState(self, value):
        """Set the b5CapabilityState"""
        # pylint: disable=attribute-defined-outside-init
        self._b5_capability_state = SPFCapabilityStates(value)
        self.push_change_event("b5CapabilityState", self._b5_capability_state)

    @attribute(
        dtype=SPFOperatingMode,
        access=AttrWriteType.READ_WRITE,
    )
    async def operatingMode(self):
        return self._operating_mode

    @operatingMode.write
    async def write_operatingMode(self, op_mode: SPFOperatingMode):
        self._operating_mode = op_mode
        self.push_change_event("operatingMode", self._operating_mode)

    @attribute(
        dtype=Band,
        access=AttrWriteType.READ_WRITE,
    )
    async def bandInFocus(self):
        return self._band_in_focus

    @bandInFocus.write
    async def bandInFocus(self, band_number: Band):
        self._band_in_focus = band_number

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
        dtype=SPFPowerState,
        access=AttrWriteType.READ_WRITE,
    )
    async def powerState(self):
        return self._power_state

    @powerState.write
    async def powerState(self, pwr_state: SPFPowerState):
        self._power_state = pwr_state
        self.push_change_event("powerState", self._power_state)

    # --------
    # Commands
    # --------

    @random_delay_execution
    @command(dtype_in=None, doc_in="Set SPFOperatingMode", dtype_out=None)
    async def SetStandbyLPMode(self):
        LOGGER.info("Called SetStandbyMode")
        self._operating_mode = SPFOperatingMode.STANDBY_LP
        self.push_change_event("operatingMode", self._operating_mode)

    @random_delay_execution
    @command(dtype_in=None, doc_in="Set SPFOperatingMode", dtype_out=None)
    async def SetOperateMode(self):
        LOGGER.info("Called SetOperateMode")
        self._operating_mode = SPFOperatingMode.OPERATE
        self.push_change_event("operatingMode", self._operating_mode)

    @random_delay_execution
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
