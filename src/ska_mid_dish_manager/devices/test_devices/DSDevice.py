"""Adapted from ska-tango-examples TestDevice.py"""
# pylint: disable=invalid-name
# pylint: disable=too-many-instance-attributes
# pylint: disable=missing-function-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods
# pylint: disable=attribute-defined-outside-init
import logging
import os
import random
import sys
import time
from functools import wraps

from ska_control_model import HealthState
from tango import AttrWriteType, Database, DbDevInfo, DevShort, DevState
from tango.server import Device, attribute, command

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    PointingState,
)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOGGER = logging.getLogger()


def random_delay_execution(func):
    """Delay a command a bit"""

    @wraps(func)
    def inner(*args, **kwargs):
        time.sleep(round(random.uniform(1.5, 2.5), 2))
        return func(*args, **kwargs)

    return inner


class DSDevice(Device):
    """Test device for LMC"""

    def init_device(self):
        super().init_device()
        self.__non_polled_attr_1 = random.randint(0, 150)
        self.__polled_attr_1 = random.randint(0, 150)
        self._operating_mode = DSOperatingMode.STANDBY_LP
        self._configured_band = Band.NONE
        self._power_state = DSPowerState.OFF
        self._health_state = HealthState.UNKNOWN
        self._indexer_position = IndexerPosition.UNKNOWN
        self._pointing_state = PointingState.UNKNOWN
        self._achieved_pointing = [0.0, 0.0, 30.0]
        self._desired_pointing = [0.0, 0.0, 30.0]
        # set manual change event for double scalars
        attributes = (
            "non_polled_attr_1",
            "operatingMode",
            "healthState",
            "powerState",
            "configuredBand",
            "indexerPosition",
            "pointingState",
            "achievedPointing",
            "desiredPointing",
        )
        for attribute_name in attributes:
            self.set_change_event(attribute_name, True, False)

    # -----------
    # Attributes
    # -----------
    @attribute(
        dtype="double",
    )
    def non_polled_attr_1(self):
        return self.__non_polled_attr_1

    @attribute(
        dtype="int",
        polling_period=2000,
        rel_change="0.5",
        abs_change="1",
    )
    def polled_attr_1(self):
        return self.__polled_attr_1

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
        dtype=PointingState,
        access=AttrWriteType.READ_WRITE,
    )
    def pointingState(self):
        return self._pointing_state

    @pointingState.write
    def pointingState(self, point_state: PointingState):
        self._pointing_state = point_state
        self.push_change_event("pointingState", self._pointing_state)

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
        dtype=IndexerPosition,
        access=AttrWriteType.READ_WRITE,
    )
    def indexerPosition(self):
        return self._indexer_position

    @indexerPosition.write
    def indexerPosition(self, band_number: IndexerPosition):
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

    @attribute(
        dtype=(float,),
        max_dim_x=3,
        access=AttrWriteType.READ_WRITE,
    )
    def achievedPointing(self):
        return self._achieved_pointing

    @achievedPointing.write
    def achievedPointing(self, argin):
        self._achieved_pointing = argin
        self.push_change_event("achievedPointing", self._achieved_pointing)

    @attribute(
        dtype=(float,),
        max_dim_x=3,
        access=AttrWriteType.READ_WRITE,
    )
    def desiredPointing(self):
        return self._desired_pointing

    @desiredPointing.write
    def desiredPointing(self, argin):
        self._desired_pointing = argin
        self.push_change_event("desiredPointing", self._desired_pointing)

    # --------
    # Commands
    # --------

    @command(dtype_in=None, doc_in="Update and push change event", dtype_out=None)
    def IncrementNonPolled1(self):
        next_value = self.__non_polled_attr_1 + 1
        self.__non_polled_attr_1 = next_value
        self.push_change_event("non_polled_attr_1", next_value)

    @command(dtype_in=None, doc_in="Switch On", dtype_out=None)
    def On(self):
        self.set_state(DevState.ON)

    @command(dtype_in=None, doc_in="Switch Off", dtype_out=None)
    def Off(self):
        self.set_state(DevState.OFF)

    @random_delay_execution
    @command(dtype_in=None, doc_in="Set StandbyLPMode", dtype_out=None)
    def SetStandbyLPMode(self):
        LOGGER.info("Called SetStandbyLPMode")
        self._operating_mode = DSOperatingMode.STANDBY_LP
        self.push_change_event("operatingMode", self._operating_mode)

    @random_delay_execution
    @command(dtype_in=None, doc_in="Set StandbyFPMode", dtype_out=None)
    def SetStandbyFPMode(self):
        LOGGER.info("Called SetStandbyFPMode")
        self._operating_mode = DSOperatingMode.STANDBY_FP
        self.push_change_event("operatingMode", self._operating_mode)
        self._power_state = DSPowerState.FULL_POWER
        self.push_change_event("powerState", self._power_state)

    @random_delay_execution
    @command(dtype_in=None, doc_in="Set Point op mode", dtype_out=None)
    def SetPointMode(self):
        LOGGER.info("Called SetPointMode")
        self._operating_mode = DSOperatingMode.POINT
        self.push_change_event("operatingMode", self._operating_mode)

    @random_delay_execution
    @command(dtype_in=None, doc_in="Set SetStartupMode", dtype_out=None)
    def SetStartupMode(self):
        LOGGER.info("Called SetStartupMode")
        self._operating_mode = DSOperatingMode.STARTUP
        self.push_change_event("operatingMode", self._operating_mode)

    @random_delay_execution
    @command(dtype_in=None, doc_in="Track", dtype_out=None)
    def Track(self):
        LOGGER.info("Called Track")
        self._operating_mode = DSOperatingMode.POINT
        self.push_change_event("operatingMode", self._operating_mode)

    @random_delay_execution
    @command(dtype_in=DevShort, doc_in="Update indexerPosition", dtype_out=None)
    def SetIndexPosition(self, band_number):
        LOGGER.info("Called SetIndexPosition")
        self._indexer_position = IndexerPosition(band_number)
        self.push_change_event("indexerPosition", self._indexer_position)

    @random_delay_execution
    @command(dtype_in=None, doc_in="Set ConfigureBand2", dtype_out=None)
    def ConfigureBand2(self):
        LOGGER.info("Called ConfigureBand2")
        self._configured_band = Band.B2
        self.push_change_event("configuredBand", self._configured_band)

    @random_delay_execution
    @command(dtype_in=None, doc_in="Set STOW", dtype_out=None)
    def Stow(self):
        LOGGER.info("Called Stow")
        self._operating_mode = DSOperatingMode.STOW
        self.push_change_event("operatingMode", self._operating_mode)

    @command(
        dtype_in=None,
        doc_in="Used to reset device to default values. Used in testing",
        dtype_out=None,
    )
    def ResetToDefault(self):
        """
        Reset device to default values.

        Used in testing only. Events are pushed, but can be ignored by clients
        Although this command is part of the simulator API, it is not part of
        the API of the actual/prime mission equipment DS Controller.
        """
        LOGGER.info("Called ResetToDefault")

        self._operating_mode = DSOperatingMode.STANDBY_LP
        self.push_change_event(
            "operatingMode",
            self._operating_mode,
        )
        self._configured_band = Band.NONE
        self.push_change_event(
            "configuredBand",
            self._configured_band,
        )
        self._power_state = DSPowerState.OFF
        self.push_change_event(
            "powerState",
            self._power_state,
        )
        self._health_state = HealthState.UNKNOWN
        self.push_change_event(
            "healthState",
            self._health_state,
        )
        self._indexer_position = IndexerPosition.UNKNOWN
        self.push_change_event(
            "indexerPosition",
            self._indexer_position,
        )
        self._pointing_state = PointingState.UNKNOWN
        self.push_change_event(
            "pointingState",
            self._pointing_state,
        )
        self._achieved_pointing = [0.0, 0.0, 30.0]
        self.push_change_event(
            "achievedPointing",
            self._achieved_pointing,
        )
        self._desired_pointing = [0.0, 0.0, 30.0]
        self.push_change_event(
            "desiredPointing",
            self._desired_pointing,
        )


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
