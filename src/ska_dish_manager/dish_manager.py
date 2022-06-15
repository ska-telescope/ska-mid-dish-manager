# pylint: disable=abstract-method
import enum
import logging

from ska_tango_base import SKAController
from ska_tango_base.base import TaskExecutorComponentManager
from tango.server import run, attribute


class DishMode(enum.IntEnum):
    UNKNOWN = 0
    OFF = 1
    STARTUP = 2
    SHUTDOWN = 3
    STANDBY_LP = 4
    STANBY_FP = 5
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
    B5a = 5
    B5b = 6
    B5c = 7
    ERROR = 8
    UNDEFINED = 9


class DishManagerComponentManager(TaskExecutorComponentManager):
    def __init__(
        self,
        *args,
        max_workers: Optional[int] = None,
        logger: logging.Logger = None,
        **kwargs,
    ):
        """"""
        super().__init__(*args, max_workers=max_workers, logger=logger, **kwargs)

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

            device = self.target
            device._dish_mode = DishMode.STANDBY_LP
            device._pointing_state = PointingState.NONE
            device._desired_pointing = [0.0, 0.0, 0.0]
            device._achieved_pointing = [0.0, 0.0, 0.0]
            device._azimuthOverWrap = False
            device._achieved_target_lock = False
            device._configured_band = Band.UNKNOWN
            device._capturing = False

    ###### Attributes ######
    dishMode = attribute(
        dtype=DishMode,
        doc="Dish rolled-up operating mode in Dish Control Model (SCM) notation"
    )
    pointingState = attribute(
        dtype=PointingState,
    )
    desiredPointing = attribute(
        max_dim_x=3,
        dtype=(float,),
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

    def read_achievedPointing(self):
        return self._achieved_pointing

    def read_achievedTargetLock(self):
        return self._achieved_target_lock

    def read_configuredBand(self):
        return self._configured_band

    def read_capturing(self):
        return self._capturing


def main(args=None, **kwargs):
    return run((DishManager,), args=args, **kwargs)


if __name__ == "__main__":
    main()
