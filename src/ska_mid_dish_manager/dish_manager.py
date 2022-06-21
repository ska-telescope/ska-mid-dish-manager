# pylint: disable=abstract-method
import enum
import logging

from typing import Optional

from ska_tango_base import SKAController
from ska_tango_base.base import TaskExecutorComponentManager
from tango import DevVarDoubleArray, AttrWriteType
from tango.server import run, attribute, command


class DishMode(enum.IntEnum):
    OFF = 0
    STARTUP = 1
    SHUTDOWN = 2
    STANDBY_LP = 3
    STANDBY_FP = 4
    MAINTENANCE = 5
    STOW = 6
    CONFIG = 7
    OPERATE = 8


class PointingState(enum.IntEnum):
    NONE = 0
    READY = 1
    SLEW = 2
    TRACK = 3
    SCAN = 4
    UNKNOWN = 5


class Band(enum.IntEnum):
    UNKNOWN = 0
    B1 = 1
    B2 = 2
    B3 = 3
    B4 = 4
    B5a = 5
    B5b = 6
    B5c = 7
    NONE = 8
    ERROR = 9
    UNDEFINED = 10


class DishManagerComponentManager(TaskExecutorComponentManager):
    def __init__(
        self,
        *args,
        max_workers: Optional[int] = None,
        logger: logging.Logger = None,
        **kwargs,
    ):
        """"""
        super().__init__(
            *args, max_workers=max_workers, logger=logger, **kwargs
        )


class DishManager(SKAController):
    """"""

    def create_component_manager(self):
        """Create the component manager for DishManager

        :return: Instance of DishManagerComponentManager
        :rtype: DishManagerComponentManager
        """
        return DishManagerComponentManager(
            max_workers=1,
            logger=self.logger,
            communication_state_callback=None,
            component_state_callback=None,
        )

    class InitCommand(SKAController.InitCommand):
        """"""

        def do(self):
            """"""
            super().do()
            device = self._device
            device._dish_mode = DishMode.STARTUP
            device._pointing_state = PointingState.NONE
            device._desired_pointing = [0.0, 0.0, 0.0]
            device._achieved_pointing = [0.0, 0.0, 0.0]
            device._azimuth_over_wrap = False
            device._achieved_target_lock = False
            device._configured_band = Band.UNKNOWN
            device._capturing = False
            device.op_state_model.perform_action("component_standby")

    ###### Attributes ######

    dishMode = attribute(
        dtype=DishMode,
        doc="Dish rolled-up operating mode in Dish Control Model (SCM) notation",
    )
    pointingState = attribute(
        dtype=PointingState,
    )
    desiredPointing = attribute(
        max_dim_x=3,
        dtype=(float,),
        access=AttrWriteType.READ_WRITE,
    )
    achievedPointing = attribute(
        max_dim_x=3,
        dtype=(float,),
    )
    azimuthOverWrap = attribute(
        dtype=bool,
    )
    achievedTargetLock = attribute(
        dtype=bool,
    )
    configuredBand = attribute(
        dtype=Band,
    )
    capturing = attribute(
        dtype=bool,
    )

    ###### Attribute's methods ######

    def read_dishMode(self):
        return self._dish_mode

    def read_pointingState(self):
        return self._pointing_state

    def read_desiredPointing(self):
        return self._desired_pointing

    def write_desiredPointing(self, value):
        self._desired_pointing = value

    def read_achievedPointing(self):
        return self._achieved_pointing

    def read_azimuthOverWrap(self):
        return self._azimuth_over_wrap

    def read_achievedTargetLock(self):
        return self._achieved_target_lock

    def read_configuredBand(self):
        return self._configured_band

    def read_capturing(self):
        return self._capturing

    ###### Commands ######

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand1():
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand2():
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand3():
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand4():
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand5a():
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand5b():
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand5c():
        return

    @command(dtype_in=None, dtype_out=None)
    def Scan():
        return

    @command(dtype_in=None, dtype_out=None)
    def SetMaintenanceMode():
        return

    @command(dtype_in=None, dtype_out=None)
    def SetOperateMode():
        return

    @command(dtype_in=None, dtype_out=None)
    def SetStandbyLPMode():
        return

    @command(dtype_in=None, dtype_out=None)
    def SetStandbyFPMode():
        return

    @command(dtype_in=None, dtype_out=None)
    def SetStowMode():
        return

    @command(
        dtype_in=DevVarDoubleArray,
        doc_in="[0]: Azimuth\n[1]: Elevation",
        dtype_out=None,
    )
    def Slew():
        return

    @command(dtype_in=None, dtype_out=None)
    def StartCapture():
        return

    @command(dtype_in=None, dtype_out=None)
    def StopCapture():
        return

    @command(dtype_in=None, dtype_out=None)
    def Track():
        return

    @command(dtype_in=None, dtype_out=None)
    def TrackStop():
        return


def main(args=None, **kwargs):
    return run((DishManager,), args=args, **kwargs)


if __name__ == "__main__":
    main()
