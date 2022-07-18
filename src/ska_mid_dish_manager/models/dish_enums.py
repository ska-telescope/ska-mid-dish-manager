# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
import enum


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
    READY = 0
    SLEW = 1
    TRACK = 2
    SCAN = 3
    UNKNOWN = 4


class Band(enum.IntEnum):
    NONE = 0
    B1 = 1
    B2 = 2
    B3 = 3
    B4 = 4
    # pylint: disable=invalid-name
    B5a = 5
    B5b = 6


class UsageStatus(enum.IntEnum):
    BUSY = 0
    ANY = 1
    IDLE = 2
    ACTIVE = 3


class PowerState(enum.IntEnum):
    OFF = 0
    UPS = 1
    LOW = 2
    FULL = 3


class TrackInterpolationMode(enum.IntEnum):
    NEWTON = 0
    SPLINE = 1


class TrackProgramMode(enum.IntEnum):
    TABLEA = 0
    TABLEB = 1
    POLY = 2


class TrackTableLoadMode(enum.IntEnum):
    ADD = 0
    NEW = 1


class OperatingMode(enum.IntEnum):
    STANDBY_LP = 0
    STANDBY_FP = 1
