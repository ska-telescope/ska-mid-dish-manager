"""File for defining constants."""

DEFAULT_DISH_ID = "SKA001"
DEFAULT_DISH_MANAGER_TRL = "mid-dish/dish-manager/SKA001"
DEFAULT_DS_MANAGER_TRL = "mid-dish/ds-manager/SKA001"
DEFAULT_SPFC_TRL = "mid-dish/simulator-spfc/SKA001"
DEFAULT_SPFRX_TRL = "mid-dish/simulator-spfrx/SKA001"
DEFAULT_WMS_TRL = "ska-mid/weather-monitoring/1"
DEFAULT_B5DC_TRL = "mid-dish/b5dc-manager/SKA001"
DEFAULT_WATCHDOG_TIMEOUT = 0.0
MAINTENANCE_MODE_ACTIVE_PROPERTY = "MaintenanceModeActive"
MAINTENANCE_MODE_TRUE_VALUE = "true"
MAINTENANCE_MODE_FALSE_VALUE = "false"
BAND_POINTING_MODEL_PARAMS_LENGTH = 18
DSC_MAX_POWER_LIMIT_KW = 20.0
DSC_MIN_POWER_LIMIT_KW = 10.0
MEAN_WIND_SPEED_THRESHOLD_MPS = 11.1
WIND_GUST_THRESHOLD_MPS = 16.9
# TODO make configurable helm parameter on device property
DEVICE_PROXY_TIMEOUT_MS = 5000
STOW_ELEVATION_DEGREES = 90.2
ELEVATION_SPEED_DEGREES_PER_SECOND = 1.0
DEFAULT_ACTION_TIMEOUT_S = 120
MAX_ELEVATION_SCIENCE = 85.0
MIN_ELEVATION_SCIENCE = 15.0
MAX_AZIMUTH = 270.0
MIN_AZIMUTH = -270.0

DS_ERROR_STATUS_ATTRIBUTES = {
    "errAuthLost": "The actual control authority is not communicating",
    "errAzimuth": "Azimuth Axis error",
    "errCmd": "Command Arbiter error",
    "errElevation": "Elevation Axis error",
    "errFeedindexer": "FeedIndexer Axis error",
    "errGeneral": "General error",
    "errMngmnt": "Dish Management Controller error",
    "errPoint": "Pointing Controller error",
    "errPwr24VDC": "Power error on 24 VDC",
    "errPwr400VAC": "Power error on 400 VAC",
    "errPwr600VDC": "Power error on 600 VDC",
    "errPwrMeterComms": "Comms lost to Power meter",
    "errSafety": "Safety System Controller error",
    "errStwPin": "StowPin Controller error",
    "errTiltOneComms": "Comms lost to Tiltmeter One",
    "errTiltOneIoUnit": "IO unit error Tiltmeter One",
    "errTiltTwoComms": "Comms lost to Tiltmeter Two",
    "errTiltTwoIounit": "IO unit error Tiltmeter Two",
    "errTime": "Time Controller error",
    "errTrack": "Tracking Controller error",
}
