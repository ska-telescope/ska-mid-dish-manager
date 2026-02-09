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


class PowerState(enum.IntEnum):
    # TODO: Review enumeration, UPS may not be necessary, see DSPowerState
    UPS = 0
    LOW = 1
    FULL = 2


class CapabilityStates(enum.IntEnum):
    UNAVAILABLE = 0
    STANDBY = 1
    CONFIGURING = 2
    OPERATE_DEGRADED = 3
    OPERATE_FULL = 4
    UNKNOWN = 5


class FannedOutCommandStatus(enum.IntEnum):
    """Fanned out command status enums."""

    PENDING = 0
    RUNNING = 1
    COMPLETED = 2
    TIMED_OUT = 3
    FAILED = 4
    IGNORED = 5
