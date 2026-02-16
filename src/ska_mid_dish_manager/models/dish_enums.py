import enum


class TrackProgramMode(enum.IntEnum):
    TABLEA = 0
    TABLEB = 1
    POLY = 2


class DishMode(enum.IntEnum):
    """Dish Mode."""

    STARTUP = 0
    SHUTDOWN = 1
    STANDBY_LP = 2
    STANDBY_FP = 3
    MAINTENANCE = 4
    STOW = 5
    CONFIG = 6
    OPERATE = 7
    UNKNOWN = 8


class DSOperatingMode(enum.IntEnum):
    """DS operating mode enums."""

    UNKNOWN = 0
    STARTUP = 1
    STANDBY = 2
    STOW = 3
    LOCKED = 4
    POINT = 5


class DSPowerState(enum.IntEnum):
    """Power state enums."""

    OFF = 0
    UPS = 1
    FULL_POWER = 2
    LOW_POWER = 3
    UNKNOWN = 4
