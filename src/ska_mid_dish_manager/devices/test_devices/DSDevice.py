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

from ska_mid_dish_manager.models.dish_enums import Band, DSOperatingMode


class DSDevice(Device):
    """Test device for use to test component manager"""

    green_mode = GreenMode.Asyncio

    def init_device(self):
        super().init_device()
        # double scalars
        self.__non_polled_attr_1 = random.uniform(0, 150)
        # long scalars
        self.__polled_attr_1 = random.randint(0, 150)
        # set manual change event for double scalars
        self.set_change_event("non_polled_attr_1", True, False)
        self._operating_mode = DSOperatingMode.UNKNOWN
        self._configured_band = Band.NONE

    # ---------------------
    # Non polled attributes
    # ---------------------
    @attribute(
        dtype="double",
    )
    async def non_polled_attr_1(self):
        return self.__non_polled_attr_1

    # -----------------
    # Polled attributes
    # -----------------
    @attribute(
        dtype="int",
        polling_period=2000,
        rel_change="0.5",
        abs_change="1",
    )
    async def polled_attr_1(self):
        return int(self.__polled_attr_1)

    # -------
    # Command
    # --------
    @command()
    async def RaiseException(self):
        Except.throw_exception(
            "TestDevice command failed",
            "Something wrong occured.",
            "Do something else",
            ErrSeverity.ERR,
        )

    @command(
        dtype_in="str",
        doc_in="A json string: "
        "{ 'attribute':'<The name of the attribute'"
        "  'number_of_events':'<Number of events to generate (integer)>'"
        "  'event_delay': '<Time to wait before next event (seconds)>'"
        "}",
    )
    async def PushScalarChangeEvents(self, configuration):
        loop = asyncio.get_event_loop()
        loop.create_task(self.attribute_event_generator(configuration))

    async def attribute_event_generator(self, configuration):
        config = json.loads(configuration)
        attr = config["attribute"]
        number_of_events = int(config["number_of_events"])
        event_delay = config["event_delay"]
        polled = self.is_attribute_polled(attr)
        while number_of_events > 0:
            await asyncio.sleep(event_delay)
            # using _classname in calls to setattr and getattr due to name mangling # noqa E501
            next_value = getattr(self, f"_TestDevice__{attr}") + 1
            setattr(self, f"_TestDevice__{attr}", next_value)
            if not polled:
                self.push_change_event(attr, next_value)
            number_of_events -= 1

    @command(
        dtype_in=None, doc_in="Update and push change event", dtype_out=None
    )
    async def IncrementNonPolled1(self):
        next_value = self.__non_polled_attr_1 + 1
        self.__non_polled_attr_1 = next_value
        self.push_change_event("non_polled_attr_1", next_value)

    @command(dtype_in=None, doc_in="Switch On", dtype_out=None)
    async def On(self):
        self.set_state(DevState.ON)

    @command(dtype_in=None, doc_in="Switch Off", dtype_out=None)
    async def Off(self):
        self.set_state(DevState.OFF)

    @attribute(
        dtype=DSOperatingMode,
        access=AttrWriteType.READ_WRITE,
        polling_period=1000,
    )
    async def operatingMode(self):
        return self._operating_mode

    def write_operatingMode(self, new_value):
        self._operating_mode = new_value

    @command(dtype_in=None, doc_in="Set StandbyLPMode", dtype_out=None)
    async def SetStandbyLPMode(self):
        self._operating_mode = DSOperatingMode.STANDBY_LP

    @command(dtype_in=None, doc_in="Set StandbyFPMode", dtype_out=None)
    async def SetStandbyFPMode(self):
        self._operating_mode = DSOperatingMode.STANDBY_FP

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
