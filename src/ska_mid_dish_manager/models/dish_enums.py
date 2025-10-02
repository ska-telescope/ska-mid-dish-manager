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


class SPFOperatingMode(enum.IntEnum):
    UNKNOWN = 0
    STARTUP = 1
    STANDBY_LP = 2
    OPERATE = 3
    MAINTENANCE = 4
    ERROR = 5


class SPFRxOperatingMode(enum.IntEnum):
    # enums are from ICD
    UNKNOWN = 0
    STARTUP = 1
    STANDBY = 2
    OPERATE = 3
    CONFIGURE = 4


class DSOperatingMode(enum.IntEnum):
    # enums are from dish lmc
    UNKNOWN = 0
    STARTUP = 1
    STANDBY_LP = 2
    STANDBY_FP = 3
    MAINTENANCE = 4
    STOW = 5
    ESTOP = 6
    POINT = 7


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
    UNKNOWN = 7


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


class BandInFocus(enum.IntEnum):
    UNKNOWN = 0
    B1 = 1
    B2 = 2
    B3 = 3
    B4 = 4
    B5 = 5


class SPFBandInFocus(enum.IntEnum):
    UNKNOWN = 0
    B1 = 1
    B2 = 2
    B3 = 3
    B4 = 4
    B5a = 5
    B5b = 6


class TrackInterpolationMode(enum.IntEnum):
    NEWTON = 0
    SPLINE = 1


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


class SPFPowerState(enum.IntEnum):
    # enums are from ICD
    UNKNOWN = 0
    LOW_POWER = 1
    FULL_POWER = 2


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


class SPFCapabilityStates(enum.IntEnum):
    UNAVAILABLE = 0
    STANDBY = 1
    OPERATE_DEGRADED = 2
    OPERATE_FULL = 3


class SPFRxCapabilityStates(enum.IntEnum):
    UNKNOWN = 0
    UNAVAILABLE = 1
    STANDBY = 2
    CONFIGURE = 3
    OPERATE = 4


class NoiseDiodeMode(enum.IntEnum):
    """SPFRx noise diode mode enums."""

    OFF = 0
    PERIODIC = 1
    PSEUDO_RANDOM = 2


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


class B5dcPllState(enum.IntEnum):
    """Band 5 down-converter Phase lock loop state."""

    LOCKED = 0
    LOCKED_WITH_LOSS_DETECTED = 1
    NOT_LOCKED = 2
    NOT_LOCKED_WITH_LOSS_DETECTED = 3


class B5dcFrequency(enum.IntEnum):
    """Band 5 down-converter frequency options."""

    F_11_1_GHZ = 1
    F_13_2_GHZ = 2
    F_13_86_GHZ = 3

    def frequency_value_ghz(self) -> float:
        """Return the frequency in GHz based on the enum value."""
        frequency_mapping = {
            B5dcFrequency.F_11_1_GHZ: 11.1,
            B5dcFrequency.F_13_2_GHZ: 13.2,
            B5dcFrequency.F_13_86_GHZ: 13.86,
        }
        return frequency_mapping[self]
