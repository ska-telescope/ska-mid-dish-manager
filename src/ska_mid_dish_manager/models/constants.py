"""File for defining constants."""

DEFAULT_DISH_ID = "SKA001"
DEFAULT_DISH_MANAGER_TRL = "mid-dish/dish-manager/SKA001"
DEFAULT_DS_MANAGER_TRL = "mid-dish/ds-manager/SKA001"
DEFAULT_SPFC_TRL = "mid-dish/simulator-spfc/SKA001"
DEFAULT_SPFRX_TRL = "mid-dish/simulator-spfrx/SKA001"
DEFAULT_B5DC_PROXY_TRL = "mid-dish/b5dc-manager/SKA001"
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
# SPFRx keeps reporting OPERATE for a short while after accepting a band configuration, only
# moving to CONFIGURE once it starts configuring. Its state is not trusted to complete the
# command until this has elapsed, otherwise the command completes against the state SPFRx was
# in before it started configuring.
SPFRX_CONFIGURE_COMPLETION_DELAY_S = 2.0
# Name of the environment variable holding the URL of the TZ data file that is
# downloaded and forwarded to SPFRx by the UpdateTZData command.
TZ_DATA_URL_ENV_VAR = "TZ_DATA_URL"
# Timeout (in seconds) for downloading the TZ data file from TZ_DATA_URL_ENV_VAR.
TZ_DATA_DOWNLOAD_TIMEOUT_S = 60
# Number of characters of a command argument kept in logs when it is truncated.
LOGGED_ARG_MAX_LENGTH = 100
MAX_ELEVATION_SCIENCE = 85.0
MIN_ELEVATION_SCIENCE = 15.0
MAX_AZIMUTH = 270.0
MIN_AZIMUTH = -270.0

OPERATOR_TAG = {"user": "operator"}
