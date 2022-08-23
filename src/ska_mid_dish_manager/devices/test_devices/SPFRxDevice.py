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

from ska_mid_dish_manager.devices.test_devices.utils import (
    random_delay_execution,
)
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    HealthState,
    SPFRxCapabilityStates,
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
        self._b1_capability_state = SPFRxCapabilityStates.UNKNOWN
        self._b2_capability_state = SPFRxCapabilityStates.UNKNOWN
        self._b3_capability_state = SPFRxCapabilityStates.UNKNOWN
        self._b4_capability_state = SPFRxCapabilityStates.UNKNOWN
        self._b5a_capability_state = SPFRxCapabilityStates.UNKNOWN
        self._b5b_capability_state = SPFRxCapabilityStates.UNKNOWN

        change_event_attributes = (
            "operatingMode",
            "healthState",
            "configuredBand",
            "b1CapabilityState",
            "b2CapabilityState",
            "b3CapabilityState",
            "b4CapabilityState",
            "b5aCapabilityState",
            "b5bCapabilityState",
        )
        for attr in change_event_attributes:
            self.set_change_event(attr, True, False)

    # -----------
    # Attributes
    # -----------

    @attribute(
        dtype=SPFRxCapabilityStates,
        access=AttrWriteType.READ_WRITE,
        doc="Report the device b1CapabilityState",
    )
    async def b1CapabilityState(self):
        """Returns the b1CapabilityState"""
        LOGGER.debug("Read b1CapabilityState")
        return self._b1_capability_state

    @b1CapabilityState.write
    async def b1CapabilityState(self, value):
        """Set the b1CapabilityState"""
        # pylint: disable=attribute-defined-outside-init
        self._b1_capability_state = SPFRxCapabilityStates(value)
        self.push_change_event("b1CapabilityState", self._b1_capability_state)
        LOGGER.debug("Wrote b1CapabilityState %s", self._b1_capability_state)

    @attribute(
        dtype=SPFRxCapabilityStates,
        access=AttrWriteType.READ_WRITE,
        doc="Report the device b2CapabilityState",
    )
    async def b2CapabilityState(self):
        """Returns the b2CapabilityState"""
        LOGGER.debug("Read b2CapabilityState")
        return self._b2_capability_state

    @b2CapabilityState.write
    async def b2CapabilityState(self, value):
        """Set the b2CapabilityState"""
        # pylint: disable=attribute-defined-outside-init
        self._b2_capability_state = SPFRxCapabilityStates(value)
        self.push_change_event("b2CapabilityState", self._b2_capability_state)
        LOGGER.debug("Wrote b2CapabilityState %s", self._b2_capability_state)

    @attribute(
        dtype=SPFRxCapabilityStates,
        access=AttrWriteType.READ_WRITE,
        doc="Report the device b3CapabilityState",
    )
    async def b3CapabilityState(self):
        """Returns the b3CapabilityState"""
        LOGGER.debug("Read b3CapabilityState")
        return self._b3_capability_state

    @b3CapabilityState.write
    async def b3CapabilityState(self, value):
        """Set the b3CapabilityState"""
        # pylint: disable=attribute-defined-outside-init
        self._b3_capability_state = SPFRxCapabilityStates(value)
        self.push_change_event("b3CapabilityState", self._b3_capability_state)
        LOGGER.debug("Wrote b3CapabilityState %s", self._b3_capability_state)

    @attribute(
        dtype=SPFRxCapabilityStates,
        access=AttrWriteType.READ_WRITE,
        doc="Report the device b4CapabilityState",
    )
    async def b4CapabilityState(self):
        """Returns the b4CapabilityState"""
        LOGGER.debug("Read b4CapabilityState")
        return self._b4_capability_state

    @b4CapabilityState.write
    async def b4CapabilityState(self, value):
        """Set the b4CapabilityState"""
        # pylint: disable=attribute-defined-outside-init
        self._b4_capability_state = SPFRxCapabilityStates(value)
        self.push_change_event("b4CapabilityState", self._b4_capability_state)
        LOGGER.debug("Wrote b4CapabilityState %s", self._b4_capability_state)

    @attribute(
        dtype=SPFRxCapabilityStates,
        access=AttrWriteType.READ_WRITE,
        doc="Report the device b5CapabilityState",
    )
    async def b5aCapabilityState(self):
        """Returns the b5aCapabilityState"""
        LOGGER.debug("Read b5aCapabilityState")
        return self._b5a_capability_state

    @b5aCapabilityState.write
    async def b5aCapabilityState(self, value):
        """Set the b5aCapabilityState"""
        # pylint: disable=attribute-defined-outside-init
        self._b5a_capability_state = SPFRxCapabilityStates(value)
        self.push_change_event(
            "b5aCapabilityState", self._b5a_capability_state
        )
        LOGGER.debug("Wrote b5aCapabilityState %s", self._b5a_capability_state)

    @attribute(
        dtype=SPFRxCapabilityStates,
        access=AttrWriteType.READ_WRITE,
        doc="Report the device b5bCapabilityState",
    )
    async def b5bCapabilityState(self):
        """Returns the b5bCapabilityState"""
        LOGGER.debug("Read b5bCapabilityState")
        return self._b5b_capability_state

    @b5bCapabilityState.write
    async def b5bCapabilityState(self, value):
        """Set the b5bCapabilityState"""
        # pylint: disable=attribute-defined-outside-init
        self._b5b_capability_state = SPFRxCapabilityStates(value)
        self.push_change_event(
            "b5bCapabilityState", self._b5b_capability_state
        )
        LOGGER.debug("Wrote b5bCapabilityState %s", self._b5b_capability_state)

    @attribute(
        dtype=SPFRxOperatingMode,
        access=AttrWriteType.READ_WRITE,
    )
    async def operatingMode(self):
        LOGGER.debug("Read operatingMode")
        return self._operating_mode

    @operatingMode.write
    async def operatingMode(self, op_mode: SPFRxOperatingMode):
        self._operating_mode = op_mode
        self.push_change_event("operatingMode", self._operating_mode)
        LOGGER.debug("Wrote operatingMode %s", self._operating_mode)

    @attribute(
        dtype=HealthState,
        access=AttrWriteType.READ_WRITE,
    )
    async def healthState(self):
        LOGGER.debug("Read healthState")
        return self._health_state

    @healthState.write
    async def healthState(self, h_state: HealthState):
        self._health_state = h_state
        self.push_change_event("healthState", self._health_state)
        LOGGER.debug("Wrote healthState %s", self._health_state)

    @attribute(
        dtype=Band,
        access=AttrWriteType.READ_WRITE,
    )
    async def configuredBand(self):
        LOGGER.debug("Read configuredBand")
        return self._configured_band

    @configuredBand.write
    async def configuredBand(self, band_number: Band):
        self._configured_band = band_number
        self.push_change_event("configuredBand", self._configured_band)
        LOGGER.debug("Wrote configuredBand %s", self._configured_band)

    # --------
    # Commands
    # --------

    @random_delay_execution
    @command(dtype_in=None, doc_in="Set SPFRXOperatingMode", dtype_out=None)
    async def SetStandbyMode(self):
        LOGGER.info("Called SetStandbyMode")
        self._operating_mode = SPFRxOperatingMode.STANDBY
        self.push_change_event("operatingMode", self._operating_mode)

    @random_delay_execution
    @command(dtype_in=None, doc_in="Set SetStartupMode", dtype_out=None)
    async def SetStartupMode(self):
        LOGGER.info("Called SetStartupMode")
        self._operating_mode = SPFRxOperatingMode.STARTUP
        self.push_change_event("operatingMode", self._operating_mode)

    @random_delay_execution
    @command(dtype_in=DevBoolean, doc_in="CaptureData", dtype_out=None)
    # pylint: disable=unused-argument
    async def CaptureData(self, boolean_value):
        LOGGER.info("Called CaptureData")
        self._operating_mode = SPFRxOperatingMode.DATA_CAPTURE
        self.push_change_event("operatingMode", self._operating_mode)

    @random_delay_execution
    @command(dtype_in=None, doc_in="Set ConfigureBand2", dtype_out=None)
    async def ConfigureBand2(self):
        LOGGER.info("Called ConfigureBand2")
        current_operating_mode = self._operating_mode
        self._operating_mode = SPFRxOperatingMode.CONFIGURE
        self.push_change_event("operatingMode", self._operating_mode)
        self._configured_band = Band.B2
        self.push_change_event("configuredBand", self._configured_band)
        self._operating_mode = current_operating_mode
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
