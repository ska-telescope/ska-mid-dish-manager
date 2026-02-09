import enum


class DishDevice(str, enum.Enum):
    DS = "DS"
    SPF = "SPF"
    SPFRX = "SPFRX"
    WMS = "WMS"
    B5DC = "B5DC"


class DishMode(enum.IntEnum):
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
    # enums are from dish lmc
    UNKNOWN = 0
    STARTUP = 1
    STANDBY = 2
    STOW = 3
    LOCKED = 4
    POINT = 5


class PointingState(enum.IntEnum):
    READY = 0
    SLEW = 1
    TRACK = 2
    SCAN = 3
    UNKNOWN = 4


class IndexerPosition(enum.IntEnum):
    OPTICAL = 0
    B1 = 1
    B2 = 2
    B3 = 3
    B4 = 4
    B5a = 5
    B5b = 6
    B6 = 7
    MOVING = 8
    UNKNOWN = 9
    ERROR = 10


class TrackProgramMode(enum.IntEnum):
    TABLEA = 0
    TABLEB = 1
    POLY = 2


class TrackTableLoadMode(enum.IntEnum):
    NEW = 0
    APPEND = 1
    RESET = 2


class PowerState(enum.IntEnum):
    # TODO: Review enumeration, UPS may not be necessary, see DSPowerState
    UPS = 0
    LOW = 1
    FULL = 2


class DSPowerState(enum.IntEnum):
    # TODO: Review enumeration, ICD has only 2 enums
    OFF = 0
    UPS = 1
    FULL_POWER = 2
    LOW_POWER = 3
    UNKNOWN = 4


class CapabilityStates(enum.IntEnum):
    UNAVAILABLE = 0
    STANDBY = 1
    CONFIGURING = 2
    OPERATE_DEGRADED = 3
    OPERATE_FULL = 4
    UNKNOWN = 5


class DscCmdAuthType(enum.IntEnum):
    """Dish structure command authority enums."""

    NO_AUTHORITY = 0
    LMC = 1
    HHP = 2
    EGUI = 3


class DscCtrlState(enum.IntEnum):
    """Dish structure control state enums."""

    # Note LOCKED_STOWED also equates to LOCKED
    LOCKED = 0
    MANUAL_CONTROL = 1
    ENGINEERING_CONTROL = 2
    REMOTE_CONTROL = 3
    NO_AUTHORITY = 4


class FannedOutCommandStatus(enum.IntEnum):
    """Fanned out command status enums."""

    PENDING = 0
    RUNNING = 1
    COMPLETED = 2
    TIMED_OUT = 3
    FAILED = 4
    IGNORED = 5
