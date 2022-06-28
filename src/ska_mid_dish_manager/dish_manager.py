# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
import enum
import logging
from typing import Optional

from ska_tango_base import SKAController
from ska_tango_base.base import TaskExecutorComponentManager
from tango import AttrWriteType, DeviceProxy, DevVarDoubleArray
from tango.server import attribute, command, run


class DishMode(enum.IntEnum):
    UNKNOWN = 0
    OFF = 1
    STARTUP = 2
    SHUTDOWN = 3
    STANDBY_LP = 4
    STANDBY_FP = 5
    STOW = 6
    CONFIG = 7
    OPERATE = 8
    MAINTENANCE = 9
    FORBIDDEN = 10
    ERROR = 11


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
    # pylint: disable=invalid-name
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
        # pylint: disable=useless-super-delegation
        super().__init__(
            *args, max_workers=max_workers, logger=logger, **kwargs
        )


class DishManager(SKAController):  # pylint: disable=too-many-public-methods
    """
    The Dish Manager of the Dish LMC subsystem
    """

    def __init__(self, *args, **kwargs):
        """Define DishManager variables"""
        self._desired_pointing = None
        super().__init__(*args, **kwargs)

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

    class InitCommand(
        SKAController.InitCommand
    ):  # pylint: disable=too-few-public-methods
        """
        A class for the Dish Manager's init_device() method
        """

        def do(self):
            """
            Initializes the attributes and properties of the DishManager
            """
            super().do()
            device = self._device
            # pylint: disable=protected-access

            # dishMode on init to be determined by the aggregation
            # of the modes from the subservient devices
            dish_structure = DeviceProxy("mid_d0001/lmc/ds_simulator")
            spf = DeviceProxy("mid_d0001/spf/simulator")
            spfrx = DeviceProxy("mid_d0001/spfrx/simulator")

            # this will need to be a background thread that runs
            # always checking the values of the underlying devices

            if (
                dish_structure.operatingMode.name == "STANDBY-LP"
                and spf.operatingMode.name == "STANDBY-LP"
                and spfrx.operatingMode.name == "STANDBY"
            ):
                device._dish_mode = DishMode.STANDBY_LP
            else:
                device._dish_mode = DishMode.UNKNOWN

            device._pointing_state = PointingState.UNKNOWN
            device._desired_pointing = [0.0, 0.0, 0.0]
            device._achieved_pointing = [0.0, 0.0, 0.0]
            device._azimuth_over_wrap = False
            device._achieved_target_lock = False
            device._configured_band = Band.NONE
            device._capturing = False
            device.op_state_model.perform_action("component_standby")

    # Attributes

    dishMode = attribute(
        dtype=DishMode,
        doc="Dish rolled-up operating mode in Dish Control Model (SCM) "
        "notation",
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

    # Attribute's methods
    # pylint: disable=invalid-name
    def read_dishMode(self):
        return self._dish_mode

    def read_pointingState(self):
        return self._pointing_state

    def read_desiredPointing(self):
        return self._desired_pointing

    def write_desiredPointing(self, value):
        # pylint: disable=attribute-defined-outside-init
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

    # Commands
    # pylint: disable=no-self-use
    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand1(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand2(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand3(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand4(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand5a(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand5b(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def ConfigureBand5c(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def Scan(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def SetMaintenanceMode(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def SetOperateMode(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def SetStandbyLPMode(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def SetStandbyFPMode(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def SetStowMode(self):
        return

    @command(
        dtype_in=DevVarDoubleArray,
        doc_in="[0]: Azimuth\n[1]: Elevation",
        dtype_out=None,
    )
    def Slew(self, argin):  # pylint: disable=unused-argument
        return

    @command(dtype_in=None, dtype_out=None)
    def StartCapture(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def StopCapture(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def Track(self):
        return

    @command(dtype_in=None, dtype_out=None)
    def TrackStop(self):
        return


def main(args=None, **kwargs):
    return run((DishManager,), args=args, **kwargs)


if __name__ == "__main__":
    main()
