"""This module implements the dish manager device for DishLMC.

It exposes the attributes and commands which control the dish
and the subservient devices
"""

import json
import weakref
from datetime import datetime
from functools import reduce
from typing import List, Optional, Tuple

from ska_control_model import CommunicationStatus, ResultCode, TaskStatus
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import (
    B5dcPllState,
)
from ska_tango_base import SKAController
from ska_tango_base.commands import SubmittedSlowCommand
from tango import AttrQuality, AttrWriteType, DevLong64, DevState, DevVarStringArray, DispLevel
from tango.server import attribute, command, device_property, run

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.abort_sequence_command_handler import Abort
from ska_mid_dish_manager.models.command_class import (
    AbortCommand,
    ApplyPointingModelCommand,
    ResetTrackTableCommand,
    SetFrequencyCommand,
    SetHPolAttenuationCommand,
    SetKValueCommand,
    SetVPolAttenuationCommand,
    StowCommand,
)
from ska_mid_dish_manager.models.constants import (
    BAND_POINTING_MODEL_PARAMS_LENGTH,
    DEFAULT_ACTION_TIMEOUT_S,
    DEFAULT_B5DC_TRL,
    DEFAULT_DISH_ID,
    DEFAULT_DS_MANAGER_TRL,
    DEFAULT_SPFC_TRL,
    DEFAULT_SPFRX_TRL,
    DEFAULT_WATCHDOG_TIMEOUT,
    DSC_MAX_POWER_LIMIT_KW,
    DSC_MIN_POWER_LIMIT_KW,
    MEAN_WIND_SPEED_THRESHOLD_MPS,
    WIND_GUST_THRESHOLD_MPS,
)
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    CapabilityStates,
    DishDevice,
    DishMode,
    DscCmdAuthType,
    DscCtrlState,
    NoiseDiodeMode,
    PointingState,
    PowerState,
    TrackInterpolationMode,
    TrackProgramMode,
    TrackTableLoadMode,
)
from ska_mid_dish_manager.release import ReleaseInfo
from ska_mid_dish_manager.utils.command_logger import BaseInfoIt
from ska_mid_dish_manager.utils.decorators import record_command, requires_component_manager
from ska_mid_dish_manager.utils.input_validation import (
    TrackLoadTableFormatting,
    TrackTableTimestampError,
)
from ska_mid_dish_manager.utils.schedulers import WatchdogTimerInactiveError

DevVarLongStringArrayType = Tuple[List[ResultCode], List[Optional[str]]]

# Used for input validation. Input samples to tracktable that is less that
# TRACK_LOAD_FUTURE_THRESHOLD_SEC in the future are logged
TRACK_LOAD_FUTURE_THRESHOLD_SEC = 5


class DishManager(SKAController):
    """The Dish Manager of the Dish LMC subsystem."""

    # Access instances for debugging
    instances = weakref.WeakValueDictionary()

    # -----------------
    # Device Properties
    # -----------------
    # these values will be overwritten by values in
    # /charts/ska-mid-dish-manager/data in k8s deployment
    DSDeviceFqdn = device_property(dtype=str, default_value=DEFAULT_DS_MANAGER_TRL)
    SPFDeviceFqdn = device_property(dtype=str, default_value=DEFAULT_SPFC_TRL)
    SPFRxDeviceFqdn = device_property(dtype=str, default_value=DEFAULT_SPFRX_TRL)
    B5DCDeviceFqdn = device_property(dtype=str, default_value=DEFAULT_B5DC_TRL)
    DishId = device_property(dtype=str, default_value=DEFAULT_DISH_ID)
    DefaultWatchdogTimeout = device_property(dtype=float, default_value=DEFAULT_WATCHDOG_TIMEOUT)
    # wms device names (e.g. ska-mid/weather-monitoring/1) to connect to
    WMSDeviceNames = device_property(dtype=DevVarStringArray, default_value=[])
    MeanWindSpeedThreshold = device_property(
        dtype=float,
        doc="Threshold value for mean wind speed (in m/s) used to trigger stow.",
        default_value=MEAN_WIND_SPEED_THRESHOLD_MPS,
    )
    WindGustThreshold = device_property(
        dtype=float,
        doc="Threshold value for wind gust speed (in m/s) used to trigger stow.",
        default_value=WIND_GUST_THRESHOLD_MPS,
    )
    DefaultActionTimeoutSeconds = device_property(
        dtype=float,
        doc="The default timeout value (in seconds) for each fanned out action.",
        default_value=DEFAULT_ACTION_TIMEOUT_S,
    )

    def create_component_manager(self) -> DishManagerComponentManager:
        """Create the component manager for DishManager.

        :return: Instance of DishManagerComponentManager
        :rtype: DishManagerComponentManager
        """
        return DishManagerComponentManager(
            self.logger,
            self._command_tracker,
            self._update_version_of_subdevice_on_success,
            self._attr_quality_state_changed,
            self.get_name(),
            self.DSDeviceFqdn,
            self.SPFDeviceFqdn,
            self.SPFRxDeviceFqdn,
            self.B5DCDeviceFqdn,
            self.DefaultActionTimeoutSeconds,
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
            wms_device_names=self.WMSDeviceNames,
            wind_stow_callback=self._wind_stow_inform,
            command_progress_callback=self._update_status,
            default_watchdog_timeout=self.DefaultWatchdogTimeout,
            default_mean_wind_speed_threshold=self.MeanWindSpeedThreshold,
            default_wind_gust_threshold=self.WindGustThreshold,
        )

    def init_command_objects(self) -> None:
        """Initialise the command handlers."""
        super().init_command_objects()

        for command_name, method_name in [
            ("SetStandbyLPMode", "set_standby_lp_mode"),
            ("SetMaintenanceMode", "set_maintenance_mode"),
            ("SetStandbyFPMode", "set_standby_fp_mode"),
            ("Track", "track_cmd"),
            ("TrackStop", "track_stop_cmd"),
            ("ConfigureBand", "configure_band_with_json"),
            ("ConfigureBand1", "configure_band_cmd"),
            ("ConfigureBand2", "configure_band_cmd"),
            ("ConfigureBand3", "configure_band_cmd"),
            ("ConfigureBand4", "configure_band_cmd"),
            ("ConfigureBand5a", "configure_band_cmd"),
            ("ConfigureBand5b", "configure_band_cmd"),
            ("Slew", "slew"),
            ("Scan", "scan"),
            ("TrackLoadStaticOff", "track_load_static_off"),
            ("EndScan", "end_scan"),
        ]:
            self.register_command_object(
                command_name,
                SubmittedSlowCommand(
                    command_name,
                    self._command_tracker,
                    self.component_manager,
                    method_name,
                    callback=None,
                    logger=self.logger,
                ),
            )

        # SetMaintenanceMode is a special command that is split into two parts, after the
        # initial fan-out of commands to sub-devices, the command waits for the dish to stow
        # then proceeds to set the dish into maintenance mode.
        self.register_command_object(
            "SetMaintenanceMode",
            SubmittedSlowCommand(
                "SetMaintenanceMode",
                self._command_tracker,
                self.component_manager,
                "set_maintenance_mode",
                callback=self.component_manager.stow_to_maintenance_transition_callback,
                logger=self.logger,
            ),
        )

        self.register_command_object(
            "SetStowMode",
            StowCommand(
                "SetStowMode",
                self._command_tracker,
                self.component_manager,
                "set_stow_mode",
                callback=None,
                logger=self.logger,
            ),
        )

        abort_sequence_handler = Abort(self.component_manager, self._command_tracker, self.logger)
        self.register_command_object(
            "Abort",
            AbortCommand(
                self._command_tracker,
                self.component_manager,
                callback=abort_sequence_handler,
                logger=self.logger,
            ),
        )

        self.register_command_object(
            "SetKValue",
            SetKValueCommand(self.component_manager, self.logger),
        )
        self.register_command_object(
            "ApplyPointingModel",
            ApplyPointingModelCommand(self.component_manager, self.logger),
        )
        self.register_command_object(
            "ResetTrackTable",
            ResetTrackTableCommand(self.component_manager, self.logger),
        )
        self.register_command_object(
            "SetFrequency",
            SetFrequencyCommand(self.component_manager, self.logger),
        )
        self.register_command_object(
            "SetHPolAttenuation",
            SetHPolAttenuationCommand(self.component_manager, self.logger),
        )
        self.register_command_object(
            "SetVPolAttenuation",
            SetVPolAttenuationCommand(self.component_manager, self.logger),
        )

    # ---------
    # Callbacks
    # ---------

    def _update_status(self, status: str) -> None:
        """Update the status of the device."""
        self.set_status(status)
        self.logger.debug(status)
        self.push_change_event("status")

    def _update_version_of_subdevice_on_success(self, device: DishDevice, build_state: str):
        """Update the version information of subdevice if connection is successful."""
        try:
            self._build_state = self._release_info.update_build_state(device, build_state)
        except AttributeError:
            self.logger.warning(
                "Failed to update build state information for [%s] device.", device.value
            )

    def _attr_quality_state_changed(
        self, attribute_name: str, new_attribute_quality: AttrQuality
    ) -> None:
        attr_name = self._component_state_attr_map.get(attribute_name)
        attr_value = self.component_manager.component_state.get(attribute_name)
        if attr_name:
            attribute_object = getattr(self, attr_name, None)
            if attribute_object:
                attribute_object.set_value(attr_value)
                attribute_object.set_quality(new_attribute_quality, True)

    def _communication_state_changed(self, communication_state: CommunicationStatus) -> None:
        wind_stow_active = self.component_manager.wind_stow_active
        if wind_stow_active:
            return

        # gets its turn when wind condition is normal
        alarm_status_msg = (
            "Event channel on a sub-device is not responding anymore "
            "or change event subscription is not complete"
        )
        action_map = {
            CommunicationStatus.NOT_ESTABLISHED: (DevState.ALARM, alarm_status_msg),
            CommunicationStatus.ESTABLISHED: (DevState.ON, None),
            CommunicationStatus.DISABLED: (DevState.DISABLE, None),
        }
        dev_state, dev_status = action_map[communication_state]
        self._update_state(dev_state, dev_status)

    # pylint: disable=unused-argument
    def _component_state_changed(self, *args, **kwargs):
        def change_case(attr_name):
            """Convert camel case string to snake case.

            The snake case output is prefixed by an underscore to
            match the naming convention of the attribute variables.

            Example:
            dishMode > _dish_mode
            capture > _capture
            b3CapabilityState > _b3_capability_state

            Source: https://www.geeksforgeeks.org/
            python-program-to-convert-camel-case-string-to-snake-case/

            """
            # pylint: disable=line-too-long
            return (
                f"_{reduce(lambda x, y: x + ('_' if y.isupper() else '') + y, attr_name).lower()}"  # noqa: E501
            )

        for comp_state_name, comp_state_value in kwargs.items():
            attribute_name = self._component_state_attr_map.get(comp_state_name, comp_state_name)
            attribute_variable = change_case(attribute_name)
            setattr(self, attribute_variable, comp_state_value)
            self.push_change_event(attribute_name, comp_state_value)
            self.push_archive_event(attribute_name, comp_state_value)

    def _wind_stow_inform(self, **computed_averages):
        """Updates the device state and status based on wind condition.

        If the dish is stowed due to high wind and the alarm has not been cleared,
        the device enters ALARM state with a message showing the wind data.

        If the dish is stowed but conditions have normalized (alarm reset allowed),
        the device returns to ON state and the stow flag is cleared.
        """
        wind_stow_active = self.component_manager.wind_stow_active
        reset_alarm = self.component_manager.reset_alarm

        if wind_stow_active and not reset_alarm:
            alarm_status_msg = f"Dish stowed due to extreme wind condition: {computed_averages}."
            dev_state, dev_status = DevState.ALARM, alarm_status_msg
            self._update_state(dev_state, dev_status)
        elif wind_stow_active and reset_alarm:
            self._update_state(DevState.ON, None)
            # ensure this runs only once after the conditions return to normal
            self.component_manager.wind_stow_active = False

    class InitCommand(SKAController.InitCommand):  # pylint: disable=too-few-public-methods
        """A class for the Dish Manager's init_device() method."""

        # pylint: disable=invalid-name
        # pylint: disable=too-many-statements
        # pylint: disable=arguments-differ
        def do(self):
            """Initializes the attributes and properties of the DishManager."""
            device: DishManager = self._device
            # pylint: disable=protected-access
            device._achieved_pointing_az = [0.0, 0.0]
            device._achieved_pointing_el = [0.0, 0.0]
            device._azimuth_over_wrap = False
            device._band5a_pointing_model_params = []
            device._band5b_pointing_model_params = []
            device._band1_sampler_frequency = 0.0
            device._band2_sampler_frequency = 0.0
            device._band3_sampler_frequency = 0.0
            device._band4_sampler_frequency = 0.0
            device._band5a_sampler_frequency = 0.0
            device._band5b_sampler_frequency = 0.0
            device._configure_target_lock = []
            device._dsh_max_short_term_power = 13.5
            device._dsh_power_curtailment = True
            device._frequency_response = [[], []]
            device._pointing_buffer_size = 0
            device._poly_track = []
            device._power_state = PowerState.LOW
            device._program_track_table = []
            device._track_interpolation_mode = TrackInterpolationMode.SPLINE
            device._track_program_mode = TrackProgramMode.TABLEA
            device._track_table_load_mode = TrackTableLoadMode.APPEND
            device._last_commanded_pointing_params = ""
            device._release_info = ReleaseInfo(
                ds_manager_address=device.DSDeviceFqdn,
                spfc_address=device.SPFDeviceFqdn,
                spfrx_address=device.SPFRxDeviceFqdn,
                b5dc_address=device.B5DCDeviceFqdn,
            )
            device._build_state = device._release_info.get_build_state()
            device._version_id = device._release_info.get_dish_manager_release_version()
            device._action_timeout_seconds = DEFAULT_ACTION_TIMEOUT_S

            # push change events, needed to use testing library

            device._component_state_attr_map = {
                "dishmode": "dishMode",
                "powerstate": "powerState",
                "pointingstate": "pointingState",
                "configuredband": "configuredBand",
                "achievedtargetlock": "achievedTargetLock",
                "dsccmdauth": "dscCmdAuth",
                "configuretargetlock": "configureTargetLock",
                "healthstate": "healthState",
                "b1capabilitystate": "b1CapabilityState",
                "b2capabilitystate": "b2CapabilityState",
                "b3capabilitystate": "b3CapabilityState",
                "b4capabilitystate": "b4CapabilityState",
                "b5acapabilitystate": "b5aCapabilityState",
                "b5bcapabilitystate": "b5bCapabilityState",
                "desiredpointingaz": "desiredPointingAz",
                "desiredpointingel": "desiredPointingEl",
                "achievedpointing": "achievedPointing",
                "band0pointingmodelparams": "band0PointingModelParams",
                "band1pointingmodelparams": "band1PointingModelParams",
                "band2pointingmodelparams": "band2PointingModelParams",
                "band3pointingmodelparams": "band3PointingModelParams",
                "band4pointingmodelparams": "band4PointingModelParams",
                "band5apointingmodelparams": "band5aPointingModelParams",
                "band5bpointingmodelparams": "band5bPointingModelParams",
                "attenuation1polhx": "attenuation1PolHX",
                "attenuation1polvy": "attenuation1PolVY",
                "attenuation2polhx": "attenuation2PolHX",
                "attenuation2polvy": "attenuation2PolVY",
                "attenuationpolhx": "attenuationPolHX",
                "attenuationpolvy": "attenuationPolVY",
                "kvalue": "kValue",
                "trackinterpolationmode": "trackInterpolationMode",
                "scanid": "scanID",
                "ignorespf": "ignoreSpf",
                "ignorespfrx": "ignoreSpfrx",
                "ignoreb5dc": "ignoreB5dc",
                "spfconnectionstate": "spfConnectionState",
                "spfrxconnectionstate": "spfrxConnectionState",
                "dsconnectionstate": "dsConnectionState",
                "wmsconnectionstate": "wmsConnectionState",
                "b5dcconnectionstate": "b5dcConnectionState",
                "noisediodemode": "noiseDiodeMode",
                "periodicnoisediodepars": "periodicNoiseDiodePars",
                "pseudorandomnoisediodepars": "pseudoRandomNoiseDiodePars",
                "isklocked": "isKLocked",
                "spectralinversion": "spectralInversion",
                "actstaticoffsetvaluexel": "actStaticOffsetValueXel",
                "actstaticoffsetvalueel": "actStaticOffsetValueEl",
                "dscpowerlimitkw": "dscPowerLimitKw",
                "tracktablecurrentindex": "trackTableCurrentIndex",
                "tracktableendindex": "trackTableEndIndex",
                "lastwatchdogreset": "lastWatchdogReset",
                "watchdogtimeout": "watchdogTimeout",
                "meanwindspeed": "meanWindSpeed",
                "windgust": "windGust",
                "autowindstowenabled": "autoWindStowEnabled",
                "lastcommandedmode": "lastCommandedMode",
                "lastcommandinvoked": "lastCommandInvoked",
                "dscctrlstate": "dscCtrlState",
                "actiontimeoutseconds": "actionTimeoutSeconds",
                "b1lnahpowerstate": "b1LnaHPowerState",
                "b2lnahpowerstate": "b2LnaHPowerState",
                "b3lnahpowerstate": "b3LnaHPowerState",
                "b4lnahpowerstate": "b4LnaHPowerState",
                "b5alnahpowerstate": "b5aLnaHPowerState",
                "b5blnahpowerstate": "b5bLnaHPowerState",
                "rfcmfrequency": "rfcmFrequency",
                "rfcmplllock": "rfcmPllLock",
                "rfcmhattenuation": "rfcmHAttenuation",
                "rfcmvattenuation": "rfcmVAttenuation",
                "clkphotodiodecurrent": "clkPhotodiodeCurrent",
                "hpolrfpowerin": "hPolRfPowerIn",
                "vpolrfPowerin": "vPolRfPowerIn",
                "hpolrfpowerout": "hPolRfPowerOut",
                "vpolrfpowerout": "vPolRfPowerOut",
                "rftemperature": "rfTemperature",
                "rfcmpsupcbtemperature": "rfcmPsuPcbTemperature",
            }
            for attr in device._component_state_attr_map.values():
                device.set_change_event(attr, True, False)
                device.set_archive_event(attr, True, False)

            # Configure events for base class attributes. These are not necessary for functionality
            # of Dish Manager but needed to suppress errors in DVS integration
            for attr in (
                "buildState",
                "versionId",
                "loggingLevel",
                "loggingTargets",
                "elementLoggerAddress",
                "elementAlarmAddress",
                "elementTelStateAddress",
                "elementDatabaseAddress",
            ):
                device.set_change_event(attr, True, False)
                device.set_archive_event(attr, True, False)

            # Configure events for attributes. The events for these attributes are not pushed
            # through callback updates
            for attr in (
                "maxCapabilities",
                "availableCapabilities",
                "azimuthOverWrap",
                "band1SamplerFrequency",
                "band2SamplerFrequency",
                "band3SamplerFrequency",
                "band4SamplerFrequency",
                "band5aSamplerFrequency",
                "band5bSamplerFrequency",
                "capturing",
                "dshMaxShortTermPower",
                "dshPowerCurtailment",
                "frequencyResponse",
                "noiseDiodeConfig",
                "programTrackTable",
                "pointingBufferSize",
                "polyTrack",
                "trackProgramMode",
                "trackTableLoadMode",
                "lastCommandedPointingParams",
            ):
                device.set_change_event(attr, True, False)
                device.set_archive_event(attr, True, False)

            # Try to connect to DB and update memorized attributes if TANGO_HOST is set
            device.component_manager.try_update_memorized_attributes_from_db()

            device.instances[device.get_name()] = device
            (result_code, message) = super().do()
            device.op_state_model.perform_action("component_on")
            device.component_manager.start_communicating()
            return (ResultCode(result_code), message)

    # ----------
    # Attributes
    # ----------

    # pylint: disable=invalid-name
    @attribute(
        dtype=(str, str),
        max_dim_x=2,
        access=AttrWriteType.READ,
        doc=(
            "Reports when and which was the last commanded mode change (not when completed). "
            "Time is a UNIX UTC timestamp."
        ),
    )
    @requires_component_manager
    def lastCommandedMode(self) -> tuple[str, str]:
        """Return the last commanded mode."""
        return self.component_manager.component_state["lastcommandedmode"]

    @attribute(
        dtype=(str, str),
        max_dim_x=2,
        access=AttrWriteType.READ,
        doc="Stores the name and timestamp (in UNIX UTC format) of the last invoked command.",
    )
    @requires_component_manager
    def lastCommandInvoked(self) -> tuple[str, str]:
        """Return the last command invoked and its timestamp."""
        return self.component_manager.component_state["lastcommandinvoked"]

    # pylint: disable=invalid-name
    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Displays connection status to SPF device",
    )
    def spfConnectionState(self):
        """Returns the spf connection state."""
        return self.component_manager.component_state.get(
            "spfconnectionstate", CommunicationStatus.NOT_ESTABLISHED
        )

    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Displays connection status to SPFRx device",
    )
    def spfrxConnectionState(self):
        """Returns the spfrx connection state."""
        return self.component_manager.component_state.get(
            "spfrxconnectionstate", CommunicationStatus.NOT_ESTABLISHED
        )

    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Displays connection status to DS device",
    )
    def dsConnectionState(self):
        """Returns the ds connection state."""
        return self.component_manager.component_state.get(
            "dsconnectionstate", CommunicationStatus.NOT_ESTABLISHED
        )

    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Displays connection status to wms device",
    )
    def wmsConnectionState(self):
        """Returns the wms connection state."""
        return self.component_manager.component_state.get(
            "wmsconnectionstate", CommunicationStatus.NOT_ESTABLISHED
        )

    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Return the status of the connection to the B5dc server endpoint",
    )
    def b5dcConnectionState(self) -> CommunicationStatus:
        """Return the status of the connection to the B5dc server endpoint."""
        return self.component_manager.component_state.get(
            "b5dcconnectionstate", CommunicationStatus.NOT_ESTABLISHED
        )

    @attribute(
        max_dim_x=3,
        dtype=(float,),
        doc="[0] Timestamp\n[1] Azimuth\n[2] Elevation",
        access=AttrWriteType.READ,
    )
    def achievedPointing(self):
        """Returns the current achieved pointing for both axis."""
        return self.component_manager.component_state.get("achievedpointing", [0.0, 0.0, 0.0])

    @attribute(
        dtype=bool,
        doc="Indicates whether the Dish is on target or not based on the "
        "pointing error and time period parameters defined in "
        "configureTargetLock.",
        access=AttrWriteType.READ,
    )
    def achievedTargetLock(self):
        """Returns the achievedTargetLock."""
        return self.component_manager.component_state.get("achievedtargetlock", False)

    @attribute(
        dtype=DscCmdAuthType,
        doc="Indicates who has command authority",
        access=AttrWriteType.READ,
    )
    def dscCmdAuth(self) -> DscCmdAuthType:
        """Returns the DSC command authority."""
        return self.component_manager.component_state.get("dsccmdauth", None)

    @attribute(
        dtype=int,
        doc="Actual used index in the track table",
        access=AttrWriteType.READ,
    )
    def trackTableCurrentIndex(self) -> int:
        """Index of current point being tracked in the track table."""
        return self.component_manager.component_state.get("tracktablecurrentindex", 0)

    @attribute(
        dtype=int,
        doc="End index in the track table",
        access=AttrWriteType.READ,
    )
    def trackTableEndIndex(self) -> int:
        """Index of last point in the track table."""
        return self.component_manager.component_state.get("tracktableendindex", 0)

    @attribute(
        dtype=float,
        doc="""The current attenuation value for attenuator 1 on the
        H/X polarization.""",
        access=AttrWriteType.READ_WRITE,
    )
    def attenuation1PolHX(self):
        """Get the attenuation Pol H/X for attenuator 1."""
        return self.component_manager.component_state.get("attenuation1polhx", 0.0)

    @attenuation1PolHX.write
    def attenuation1PolHX(self, value):
        """Set the attenuation Pol H/X for attenuator 1."""
        self.logger.debug("attenuation1PolHX write method called with param %s", value)

        if hasattr(self, "component_manager"):
            spfrx_com_man = self.component_manager.sub_component_managers["SPFRX"]
            spfrx_com_man.write_attribute_value("attenuation1PolHX", value)
        else:
            self.logger.warning("No component manager to write attenuation1PolHX yet")
            raise RuntimeError("Failed to write to attenuation1PolHX on DishManager")

    @attribute(
        dtype=float,
        doc="""The current attenuation value for attenuator 1 on the
        V/Y polarization.""",
        access=AttrWriteType.READ_WRITE,
    )
    def attenuation1PolVY(self):
        """Get the attenuation Pol V/Y for attenuator 1."""
        return self.component_manager.component_state.get("attenuation1polvy", 0.0)

    @attenuation1PolVY.write
    def attenuation1PolVY(self, value):
        """Set the attenuation Pol V/Y for attenuator 1."""
        self.logger.debug("attenuation1PolVY write method called with param %s", value)

        if hasattr(self, "component_manager"):
            spfrx_com_man = self.component_manager.sub_component_managers["SPFRX"]
            spfrx_com_man.write_attribute_value("attenuation1PolVY", value)
        else:
            self.logger.warning("No component manager to write attenuation1PolVY yet")
            raise RuntimeError("Failed to write to attenuation1PolVY on DishManager")

    @attribute(
        dtype=float,
        doc="""The current attenuation value for attenuator 2 on the
        H/X polarization.""",
        access=AttrWriteType.READ_WRITE,
    )
    def attenuation2PolHX(self):
        """Get the attenuation Pol H/X for attenuator 2."""
        return self.component_manager.component_state.get("attenuation2polhx", 0.0)

    @attenuation2PolHX.write
    def attenuation2PolHX(self, value):
        """Set the attenuation Pol H/X for attenuator 2."""
        self.logger.debug("attenuation2PolHX write method called with param %s", value)

        if hasattr(self, "component_manager"):
            spfrx_com_man = self.component_manager.sub_component_managers["SPFRX"]
            spfrx_com_man.write_attribute_value("attenuation2PolHX", value)
        else:
            self.logger.warning("No component manager to write attenuation2PolHX yet")
            raise RuntimeError("Failed to write to attenuation2PolHX on DishManager")

    @attribute(
        dtype=float,
        doc="""The current attenuation value for attenuator 2 on the
        V/Y polarization.""",
        access=AttrWriteType.READ_WRITE,
    )
    def attenuation2PolVY(self):
        """Get the attenuation Pol H/X for attenuator 2."""
        return self.component_manager.component_state.get("attenuation2polvy", 0.0)

    @attenuation2PolVY.write
    def attenuation2PolVY(self, value):
        """Set the attenuation Pol V/Y for attenuator 2."""
        self.logger.debug("attenuation2PolVY write method called with param %s", value)

        if hasattr(self, "component_manager"):
            spfrx_com_man = self.component_manager.sub_component_managers["SPFRX"]
            spfrx_com_man.write_attribute_value("attenuation2PolVY", value)
        else:
            self.logger.warning("No component manager to write attenuation2PolVY yet")
            raise RuntimeError("Failed to write to attenuation2PolVY on DishManager")

    @attribute(
        dtype=float,
        doc="""The current total attenuation value across both attenuators on the
        H/X polarization.""",
        access=AttrWriteType.READ_WRITE,
    )
    def attenuationPolHX(self):
        """Get the total attenuation Pol H/X."""
        return self.component_manager.component_state.get("attenuationpolhx", 0.0)

    @attenuationPolHX.write
    def attenuationPolHX(self, value):
        """Set the total attenuation Pol H/X."""
        self.logger.debug("attenuationPolHX write method called with param %s", value)

        if hasattr(self, "component_manager"):
            spfrx_com_man = self.component_manager.sub_component_managers["SPFRX"]
            spfrx_com_man.write_attribute_value("attenuationPolHX", value)
        else:
            self.logger.warning("No component manager to write attenuationPolHX yet")
            raise RuntimeError("Failed to write to attenuationPolHX on DishManager")

    @attribute(
        dtype=float,
        doc="""The current total attenuation value across both attenuators on the
        V/Y polarization.""",
        access=AttrWriteType.READ_WRITE,
    )
    def attenuationPolVY(self):
        """Get the total attenuation Pol V/Y."""
        return self.component_manager.component_state.get("attenuationpolvy", 0.0)

    @attenuationPolVY.write
    def attenuationPolVY(self, value):
        """Set the total attenuation Pol V/Y."""
        self.logger.debug("attenuationPolVY write method called with param %s", value)

        if hasattr(self, "component_manager"):
            spfrx_com_man = self.component_manager.sub_component_managers["SPFRX"]
            spfrx_com_man.write_attribute_value("attenuationPolVY", value)
        else:
            self.logger.warning("No component manager to write attenuationPolVY yet")
            raise RuntimeError("Failed to write to attenuationPolVY on DishManager")

    @attribute(
        dtype=int,
        access=AttrWriteType.READ,
        doc="Returns the kValue for SPFRX",
    )
    def kValue(self):
        """Returns the kValue for SPFRX."""
        return self.component_manager.component_state["kvalue"]

    @attribute(
        dtype=bool,
        doc="Indicates that the Dish has moved beyond an azimuth wrap limit.",
    )
    def azimuthOverWrap(self):
        """Returns the azimuthOverWrap."""
        return self._azimuth_over_wrap

    @attribute(
        dtype=float,
        doc="Actual cross-elevation static offset (arcsec)",
        access=AttrWriteType.READ,
    )
    def actStaticOffsetValueXel(self) -> float:
        """Indicate actual cross-elevation static offset in arcsec."""
        return self.component_manager.component_state.get("actstaticoffsetvaluexel", 0.0)

    @attribute(
        dtype=float,
        doc="Actual elevation static offset (arcsec)",
        access=AttrWriteType.READ,
    )
    def actStaticOffsetValueEl(self) -> float:
        """Indicate actual elevation static offset in arcsec."""
        return self.component_manager.component_state.get("actstaticoffsetvalueel", 0.0)

    @attribute(
        dtype=(float,),
        max_dim_x=BAND_POINTING_MODEL_PARAMS_LENGTH,
        doc="""
            Parameters for (local) Band 0 pointing models used by Dish to do pointing corrections.

            When writing to this attribute, the selected band for correction will be set to B0.

            Band pointing model parameters are:
            [0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
            [9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
            [15] HESE4, [16] HECE8, [17] HESE8
        """,
        access=AttrWriteType.READ_WRITE,
    )
    def band0PointingModelParams(self):
        """Returns the band0PointingModelParams."""
        return self.component_manager.component_state.get("band0pointingmodelparams", [])

    @band0PointingModelParams.write
    def band0PointingModelParams(self, value):
        """Set the band0PointingModelParams."""
        self.logger.debug("band0PointingModelParams write method called with params %s", value)

        if hasattr(self, "component_manager"):
            self.component_manager.update_pointing_model_params("band0PointingModelParams", value)
        else:
            self.logger.warning("No component manager to write band0PointingModelParams yet")
            raise RuntimeError("Failed to write to band0PointingModelParams on DishManager")

    @attribute(
        dtype=(float,),
        max_dim_x=BAND_POINTING_MODEL_PARAMS_LENGTH,
        doc="""
            Parameters for (local) Band 1 pointing models used by Dish to do pointing corrections.

            When writing to this attribute, the selected band for correction will be set to B1.

            Band pointing model parameters are:
            [0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
            [9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
            [15] HESE4, [16] HECE8, [17] HESE8
        """,
        access=AttrWriteType.READ_WRITE,
    )
    def band1PointingModelParams(self):
        """Returns the band1PointingModelParams."""
        return self.component_manager.component_state.get("band1pointingmodelparams", [])

    @band1PointingModelParams.write
    def band1PointingModelParams(self, value):
        """Set the band1PointingModelParams."""
        self.logger.debug("band1PointingModelParams write method called with params %s", value)

        if hasattr(self, "component_manager"):
            self.component_manager.update_pointing_model_params("band1PointingModelParams", value)
        else:
            self.logger.warning("No component manager to write band1PointingModelParams yet")
            raise RuntimeError("Failed to write to band1PointingModelParams on DishManager")

    @attribute(
        dtype=(float,),
        max_dim_x=BAND_POINTING_MODEL_PARAMS_LENGTH,
        doc="""
            Parameters for (local) Band 2 pointing models used by Dish to do pointing corrections.

            When writing to this attribute, the selected band for correction will be set to B2.

            Band pointing model parameters are:
            [0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
            [9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
            [15] HESE4, [16] HECE8, [17] HESE8
        """,
        access=AttrWriteType.READ_WRITE,
    )
    def band2PointingModelParams(self):
        """Returns the band2PointingModelParams."""
        return self.component_manager.component_state.get("band2pointingmodelparams", [])

    @band2PointingModelParams.write
    def band2PointingModelParams(self, value):
        """Set the band2PointingModelParams."""
        self.logger.debug("band2PointingModelParams write method called with params %s", value)

        if hasattr(self, "component_manager"):
            self.component_manager.update_pointing_model_params("band2PointingModelParams", value)
        else:
            self.logger.warning("No component manager to write band2PointingModelParams yet")
            raise RuntimeError("Failed to write to band2PointingModelParams on DishManager")

    @attribute(
        dtype=(float,),
        max_dim_x=BAND_POINTING_MODEL_PARAMS_LENGTH,
        doc="""
            Parameters for (local) Band 3 pointing models used by Dish to do pointing corrections.

            When writing to this attribute, the selected band for correction will be set to B3.

            Band pointing model parameters are:
            [0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
            [9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
            [15] HESE4, [16] HECE8, [17] HESE8
        """,
        access=AttrWriteType.READ_WRITE,
    )
    def band3PointingModelParams(self):
        """Returns the band3PointingModelParams."""
        return self.component_manager.component_state.get("band3pointingmodelparams", [])

    @band3PointingModelParams.write
    def band3PointingModelParams(self, value):
        """Set the band3PointingModelParams."""
        self.logger.debug("band3PointingModelParams write method called with params %s", value)

        if hasattr(self, "component_manager"):
            self.component_manager.update_pointing_model_params("band3PointingModelParams", value)
        else:
            self.logger.warning("No component manager to write band3PointingModelParams yet")
            raise RuntimeError("Failed to write to band3PointingModelParams on DishManager")

    @attribute(
        dtype=(float,),
        max_dim_x=BAND_POINTING_MODEL_PARAMS_LENGTH,
        doc="""
            Parameters for (local) Band 4 pointing models used by Dish to do pointing corrections.

            When writing to this attribute, the selected band for correction will be set to B4.

            Band pointing model parameters are:
            [0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
            [9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
            [15] HESE4, [16] HECE8, [17] HESE8
        """,
        access=AttrWriteType.READ_WRITE,
    )
    def band4PointingModelParams(self):
        """Returns the band4PointingModelParams."""
        return self.component_manager.component_state.get("band4pointingmodelparams", [])

    @band4PointingModelParams.write
    def band4PointingModelParams(self, value):
        """Set the band4PointingModelParams."""
        self.logger.debug("band4PointingModelParams write method called with params %s", value)

        if hasattr(self, "component_manager"):
            self.component_manager.update_pointing_model_params("band4PointingModelParams", value)
        else:
            self.logger.warning("No component manager to write band4PointingModelParams yet")
            raise RuntimeError("Failed to write to band4PointingModelParams on DishManager")

    @attribute(
        dtype=(float,),
        max_dim_x=18,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 5a pointing models used by Dish to "
        "do pointing corrections.",
    )
    def band5aPointingModelParams(self):
        """Returns the band5aPointingModelParams."""
        return self._band5a_pointing_model_params

    @band5aPointingModelParams.write
    def band5aPointingModelParams(self, value):
        """Set the band5aPointingModelParams."""
        self.logger.debug("band5aPointingModelParams write method called with params %s", value)
        if hasattr(self, "component_manager"):
            self.component_manager.update_pointing_model_params("band5aPointingModelParams", value)
        else:
            self.logger.warning("No component manager to write band5aPointingModelParams yet")
            raise RuntimeError("Failed to write to band5aPointingModelParams on DishManager")

    @attribute(
        dtype=(float,),
        max_dim_x=18,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 5b pointing models used by Dish to "
        "do pointing corrections.",
    )
    def band5bPointingModelParams(self):
        """Returns the band5bPointingModelParams."""
        return self._band5b_pointing_model_params

    @band5bPointingModelParams.write
    def band5bPointingModelParams(self, value):
        """Set the band5bPointingModelParams."""
        self.logger.debug("band5bPointingModelParams write method called with params %s", value)

        if hasattr(self, "component_manager"):
            self.component_manager.update_pointing_model_params("band5bPointingModelParams", value)
        else:
            self.logger.warning("No component manager to write band5bPointingModelParams yet")
            raise RuntimeError("Failed to write to band5bPointingModelParams on DishManager")

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND1 absolute sampler clock frequency (base plus offset).",
    )
    def band1SamplerFrequency(self):
        """Returns the band1SamplerFrequency."""
        return self._band1_sampler_frequency

    @band1SamplerFrequency.write
    def band1SamplerFrequency(self, value):
        """Set the band1SamplerFrequency."""
        # pylint: disable=attribute-defined-outside-init
        self._band1_sampler_frequency = value
        self.push_change_event("band1SamplerFrequency", value)
        self.push_archive_event("band1SamplerFrequency", value)

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND2 absolute sampler clock frequency (base plus offset).",
    )
    def band2SamplerFrequency(self):
        """Returns the band2SamplerFrequency."""
        return self._band2_sampler_frequency

    @band2SamplerFrequency.write
    def band2SamplerFrequency(self, value):
        """Set the band2SamplerFrequency."""
        # pylint: disable=attribute-defined-outside-init
        self._band2_sampler_frequency = value
        self.push_change_event("band2SamplerFrequency", value)
        self.push_archive_event("band2SamplerFrequency", value)

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND3 absolute sampler clock frequency (base plus offset).",
    )
    def band3SamplerFrequency(self):
        """Returns the band3SamplerFrequency."""
        return self._band3_sampler_frequency

    @band3SamplerFrequency.write
    def band3SamplerFrequency(self, value):
        """Set the band3SamplerFrequency."""
        # pylint: disable=attribute-defined-outside-init
        self._band3_sampler_frequency = value
        self.push_change_event("band3SamplerFrequency", value)
        self.push_archive_event("band3SamplerFrequency", value)

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND4 absolute sampler clock frequency (base plus offset).",
    )
    def band4SamplerFrequency(self):
        """Returns the band4SamplerFrequency."""
        return self._band4_sampler_frequency

    @band4SamplerFrequency.write
    def band4SamplerFrequency(self, value):
        """Set the band4SamplerFrequency."""
        # pylint: disable=attribute-defined-outside-init
        self._band4_sampler_frequency = value
        self.push_change_event("band4SamplerFrequency", value)
        self.push_archive_event("band4SamplerFrequency", value)

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND5a absolute sampler clock frequency (base plus offset).",
    )
    def band5aSamplerFrequency(self):
        """Returns the band5aSamplerFrequency."""
        return self._band5a_sampler_frequency

    @band5aSamplerFrequency.write
    def band5aSamplerFrequency(self, value):
        """Set the band5aSamplerFrequency."""
        # pylint: disable=attribute-defined-outside-init
        self._band5a_sampler_frequency = value
        self.push_change_event("band5aSamplerFrequency", value)
        self.push_archive_event("band5aSamplerFrequency", value)

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND5b absolute sampler clock frequency (base plus offset).",
    )
    def band5bSamplerFrequency(self):
        """Returns the band5bSamplerFrequency."""
        return self._band5b_sampler_frequency

    @band5bSamplerFrequency.write
    def band5bSamplerFrequency(self, value):
        """Set the band5bSamplerFrequency."""
        # pylint: disable=attribute-defined-outside-init
        self._band5b_sampler_frequency = value
        self.push_change_event("band5bSamplerFrequency", value)
        self.push_archive_event("band5bSamplerFrequency", value)

    @attribute(
        dtype=bool,
        doc="Indicates whether Dish is capturing data in the configured band or not.",
    )
    def capturing(self):
        """Returns the capturing."""
        return self.component_manager.component_state.get("capturing", False)

    @attribute(
        dtype=Band,
        doc="The frequency band that the Dish is configured to capture data in.",
    )
    def configuredBand(self):
        """Returns the configuredBand."""
        return self.component_manager.component_state.get("configuredband", Band.UNKNOWN)

    @attribute(
        dtype=(float,),
        max_dim_x=2,
        access=AttrWriteType.WRITE,
        doc="[0] Pointing error\n[1] Time period",
    )
    def configureTargetLock(self):
        """Returns the configureTargetLock."""
        return self._configure_target_lock

    @configureTargetLock.write
    def configureTargetLock(self, value):
        """Set the configureTargetLock."""
        # pylint: disable=attribute-defined-outside-init
        self._configure_target_lock = value
        ds_com_man = self.component_manager.sub_component_managers["DS"]
        ds_com_man.write_attribute_value("configureTargetLock", value)

    @attribute(
        max_dim_x=2,
        dtype=(float,),
        access=AttrWriteType.READ,
        doc="Azimuth axis desired pointing as reported by the dish structure controller's"
        " Tracking.TrackStatus.p_desired_Az field.",
    )
    def desiredPointingAz(self) -> list[float]:
        """Returns the azimuth desiredPointing."""
        return self.component_manager.component_state.get("desiredpointingaz", [0.0, 0.0])

    @attribute(
        max_dim_x=2,
        dtype=(float,),
        access=AttrWriteType.READ,
        doc="Elevation axis desired pointing as reported by the dish structure controller's"
        " Tracking.TrackStatus.p_desired_El field.",
    )
    def desiredPointingEl(self) -> list[float]:
        """Returns the elevation desiredPointing."""
        return self.component_manager.component_state.get("desiredpointingel", [0.0, 0.0])

    @attribute(
        dtype=DishMode,
        doc="Dish rolled-up operating mode in Dish Control Model (SCM) notation",
    )
    def dishMode(self):
        """Returns the dishMode."""
        return self.component_manager.component_state.get("dishmode", DishMode.UNKNOWN)

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="Configures the Max Short Term Average Power (5sec‐10min) in "
        "kilowatt that the DSH instance is curtailed to while "
        "dshPowerCurtailment is [TRUE]. The default value is 13.5.",
    )
    def dshMaxShortTermPower(self):
        """Returns the dshMaxShortTermPower."""
        return self._dsh_max_short_term_power

    @dshMaxShortTermPower.write
    def dshMaxShortTermPower(self, value):
        """Set the dshMaxShortTermPower."""
        # pylint: disable=attribute-defined-outside-init
        self._dsh_max_short_term_power = value
        self.push_change_event("dshMaxShortTermPower", value)
        self.push_archive_event("dshMaxShortTermPower", value)

    @attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="The Max Short Term Average Power (5sec‐10min) of each DSH "
        "instance is curtailed to the value configured in "
        "dshMaxShortTermPower. The default condition is [TRUE] ‐ "
        "power curtailment is on. With power curtailment [TRUE], all DSH "
        "functionality is available but at reduced performance (for example "
        "reduced slew rates). With power curtailment [FALSE], all DSH "
        "functionality is available at full performance (for example "
        "maximum slew rates).",
    )
    def dshPowerCurtailment(self):
        """Returns the dshPowerCurtailment."""
        return self._dsh_power_curtailment

    @dshPowerCurtailment.write
    def dshPowerCurtailment(self, value):
        """Set the dshPowerCurtailment."""
        # pylint: disable=attribute-defined-outside-init
        self._dsh_power_curtailment = value
        self.push_change_event("dshPowerCurtailment", value)
        self.push_archive_event("dshPowerCurtailment", value)

    @attribute(dtype=(((float),),), max_dim_x=1024, max_dim_y=1024)
    def frequencyResponse(self):
        """Returns the frequencyResponse."""
        return self._frequency_response

    @attribute(dtype=(float,), access=AttrWriteType.WRITE)
    def noiseDiodeConfig(self):
        """Returns the noiseDiodeConfig."""
        return self._noise_diode_config

    @noiseDiodeConfig.write
    def noiseDiodeConfig(self, value):
        """Set the noiseDiodeConfig."""
        # pylint: disable=attribute-defined-outside-init
        self._noise_diode_config = value
        self.push_change_event("noiseDiodeConfig", value)
        self.push_archive_event("noiseDiodeConfig", value)

    @attribute(dtype=PointingState)
    def pointingState(self):
        """Returns the pointingState."""
        return self.component_manager.component_state.get("pointingstate", PointingState.UNKNOWN)

    @attribute(
        dtype=(float,),
        max_dim_x=150,
        access=AttrWriteType.READ_WRITE,
        doc="Timestamp of i-th coordinate in table (max 50 coordinates) given "
        "in milliseconds since TAI epoch, representing time at which "
        "Dish should track i-th coordinate.\n Azimuth of i-th coordinate in "
        "table (max 50 coordinates) given in degrees.\n Elevation of i-th "
        "coordinate in table (max 50 coordinates) given in degrees",
    )
    def programTrackTable(self):
        """Returns the programTrackTable."""
        return self._program_track_table

    @programTrackTable.write
    def programTrackTable(self, table):
        """Set the programTrackTable."""
        # pylint: disable=attribute-defined-outside-init
        # Spectrum that is a multiple of 3 values:
        # - (timestamp, azimuth coordinate, elevation coordinate)
        # i.e. [tai_0, az_pos_0, el_pos_0, ..., tai_n, az_pos_n, el_pos_n]

        # perform input validation on table
        try:
            TrackLoadTableFormatting().check_track_table_input_valid(
                table,
                TRACK_LOAD_FUTURE_THRESHOLD_SEC,
            )
        except TrackTableTimestampError as te:
            self.logger.warning("Track table timestamp warning: %s", te)
        except ValueError as ve:
            raise ve

        length_of_table = len(table)
        sequence_length = length_of_table / 3
        task_status, msg = self.component_manager.track_load_table(
            sequence_length, table, self._track_table_load_mode
        )

        if task_status == TaskStatus.FAILED:
            raise RuntimeError(f"Write to programTrackTable failed: {msg}")
        self._program_track_table = table
        self.push_change_event("programTrackTable", table)
        self.push_archive_event("programTrackTable", table)

    @attribute(
        dtype=int,
        doc="Number of desiredPointing write values that the buffer has space "
        "for.\nNote: desiredPointing write values are stored by Dish in a "
        "buffer for application at the time specified in each desiredPointing "
        "record.",
    )
    def pointingBufferSize(self):
        """Returns the pointingBufferSize."""
        return self._pointing_buffer_size

    @attribute(
        dtype=(float,),
        max_dim_x=9,
        access=AttrWriteType.WRITE,
        doc="[0] Timestamp\n[1] Azimuth\n[2] Elevation\n[3] Azimuth speed\n"
        "[4] Elevation speed\n[5] Azimuth acceleration\n"
        "[6] Elevation acceleration\n[7] Azimuth jerk\n[8] Elevation jerk",
    )
    def polyTrack(self):
        """Returns the polyTrack."""
        return self._poly_track

    @polyTrack.write
    def polyTrack(self, value):
        """Set the polyTrack."""
        # pylint: disable=attribute-defined-outside-init
        self._poly_track = value
        self.push_change_event("polyTrack", value)
        self.push_archive_event("polyTrack", value)

    @attribute(dtype=PowerState)
    def powerState(self):
        """Returns the powerState."""
        return self._power_state

    @attribute(
        dtype=TrackInterpolationMode,
        access=AttrWriteType.READ_WRITE,
        doc="Selects the type of interpolation to be used in program tracking.",
    )
    def trackInterpolationMode(self):
        """Returns the trackInterpolationMode."""
        return self._track_interpolation_mode

    @trackInterpolationMode.write
    def trackInterpolationMode(self, value):
        """Set the trackInterpolationMode."""
        self.component_manager.set_track_interpolation_mode(value)

    @attribute(
        dtype=TrackProgramMode,
        access=AttrWriteType.READ_WRITE,
        doc="Selects the track program source (table A, table B, polynomial "
        "stream) used in the ACU for tracking. Coordinates given in the "
        "programTrackTable attribute are loaded in ACU in the selected table.",
    )
    def trackProgramMode(self):
        """Returns the trackProgramMode."""
        return self._track_program_mode

    @trackProgramMode.write
    def trackProgramMode(self, value):
        """Set the trackProgramMode."""
        # pylint: disable=attribute-defined-outside-init
        self._track_program_mode = value
        self.push_change_event("trackProgramMode", value)
        self.push_archive_event("trackProgramMode", value)

    @attribute(
        dtype=TrackTableLoadMode,
        access=AttrWriteType.READ_WRITE,
        doc="Selects track table load mode.\nWith ADD selected, Dish will "
        "add the coordinate set given in programTrackTable attribute to the "
        "list of pointing coordinates already loaded in ACU.\nWith NEW "
        "selected, Dish will delete the list of pointing coordinates "
        "previously loaded in ACU when new coordinates are given in the "
        "programTrackTable attribute.",
    )
    def trackTableLoadMode(self):
        """Returns the trackTableLoadMode."""
        return self._track_table_load_mode

    @trackTableLoadMode.write
    def trackTableLoadMode(self, value):
        """Set the trackTableLoadMode."""
        # pylint: disable=attribute-defined-outside-init
        self._track_table_load_mode = value
        self.push_change_event("trackTableLoadMode", value)
        self.push_archive_event("trackTableLoadMode", value)

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b1CapabilityState",
    )
    def b1CapabilityState(self):
        """Returns the b1CapabilityState."""
        return self.component_manager.component_state.get(
            "b1capabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b2CapabilityState",
    )
    def b2CapabilityState(self):
        """Returns the b2CapabilityState."""
        return self.component_manager.component_state.get(
            "b2capabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b3CapabilityState",
    )
    def b3CapabilityState(self):
        """Returns the b3CapabilityState."""
        return self.component_manager.component_state.get(
            "b3capabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b4CapabilityState",
    )
    def b4CapabilityState(self):
        """Returns the b4CapabilityState."""
        return self.component_manager.component_state.get(
            "b4capabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b5aCapabilityState",
    )
    def b5aCapabilityState(self):
        """Returns the b5aCapabilityState."""
        return self.component_manager.component_state.get(
            "b5acapabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b5bCapabilityState",
    )
    def b5bCapabilityState(self):
        """Returns the b5aCapabilityState."""
        return self.component_manager.component_state.get(
            "b5bcapabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="Report the scanID for Scan",
    )
    def scanID(self):
        """Returns the scanID."""
        return self.component_manager.component_state.get("scanid", "")

    @scanID.write
    def scanID(self, scanid):
        """Sets the scanID."""
        self.component_manager._update_component_state(scanid=scanid)

    @attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="Flag to disable SPF device communication. When ignored, no commands will be issued "
        "to the device, it will be excluded from state aggregation, and no device related "
        "attributes will be updated.",
        memorized=True,
    )
    def ignoreSpf(self):
        """Returns ignoreSpf."""
        return self.component_manager.component_state.get("ignorespf", False)

    @ignoreSpf.write
    def ignoreSpf(self, value):
        """Sets ignoreSpf."""
        self.logger.debug("Write to ignoreSpf, %s", value)
        self.component_manager.set_spf_device_ignored(value)

    @attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="Flag to disable SPFRx device communication. When ignored, no commands will be issued "
        "to the device, it will be excluded from state aggregation, and no device related "
        "attributes will be updated.",
        memorized=True,
    )
    def ignoreSpfrx(self):
        """Returns ignoreSpfrx."""
        return self.component_manager.component_state.get("ignorespfrx", False)

    @ignoreSpfrx.write
    def ignoreSpfrx(self, value):
        """Sets ignoreSpfrx."""
        self.logger.debug("Write to ignoreSpfrx, %s", value)
        self.component_manager.set_spfrx_device_ignored(value)

    @attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="Flag to disable B5DC device communication. When ignored, no commands will be issued "
        "to the device, it will be excluded from state aggregation, and no device related "
        "attributes will be updated.",
        memorized=True,
    )
    def ignoreB5dc(self):
        """Returns ignoreB5dc."""
        return self.component_manager.component_state.get("ignoreb5dc", False)

    @ignoreB5dc.write
    def ignoreB5dc(self, value):
        """Sets ignoreB5dc."""
        self.logger.debug("Write to ignoreB5dc, %s", value)
        self.component_manager.set_b5dc_device_ignored(value)

    @attribute(
        dtype=NoiseDiodeMode,
        access=AttrWriteType.READ_WRITE,
        doc="""
            Noise diode mode.

            0: OFF, 1: PERIODIC, 2: PSEUDO-RANDOM

            Note: This attribute does not persist after a power cycle. A default value is included
            as a device property on the SPFRx.
        """,
    )
    def noiseDiodeMode(self):
        """Returns the noise diode mode."""
        self.logger.debug("Read noiseDiodeMode")
        return self.component_manager.component_state.get("noisediodemode", NoiseDiodeMode.OFF)

    @noiseDiodeMode.write
    def noiseDiodeMode(self, mode: NoiseDiodeMode):
        """Set the device noise diode mode."""
        self.component_manager.set_noise_diode_mode(mode)

    @attribute(
        dtype=(DevLong64,),
        max_dim_x=3,
        doc="""
            Periodic noise diode pars (units are in time quanta).

            [0]: period, [1]: duty cycle, [2]: phase shift

            Note: This attribute does not persist after a power cycle. A default value is included
            as a device property on the SPFRx.
        """,
        access=AttrWriteType.READ_WRITE,
    )
    def periodicNoiseDiodePars(self):
        """Returns the device periodic noise diode pars."""
        self.logger.debug("Read periodicNoiseDiodePars")
        return self.component_manager.component_state.get("periodicnoisediodepars", [])

    @periodicNoiseDiodePars.write
    def periodicNoiseDiodePars(self, values):
        """Set the device periodic noise diode pars."""
        self.component_manager.set_periodic_noise_diode_pars(values)

    @attribute(
        dtype=(DevLong64,),
        max_dim_x=3,
        doc="""
            Pseudo random noise diode pars (units are in time quanta).

            [0]: binary polynomial, [1]: seed, [2]: dwell

            Note: This attribute does not persist after a power cycle. A default value is included
            as a device property on the SPFRx.
        """,
        access=AttrWriteType.READ_WRITE,
    )
    def pseudoRandomNoiseDiodePars(self):
        """Returns the device pseudo random noise diode pars."""
        self.logger.debug("Read noiseDiodeMode")
        return self.component_manager.component_state.get("pseudorandomnoisediodepars", [])

    @pseudoRandomNoiseDiodePars.write
    def pseudoRandomNoiseDiodePars(self, values):
        """Set the device pseudo random noise diode pars."""
        self.component_manager.set_pseudo_random_noise_diode_pars(values)

    @attribute(
        dtype=bool,
        doc="""
            Check the SAT.RM module to see if
            the k- value is locked. If not false is returned.
        """,
        access=AttrWriteType.READ,
    )
    def isKLocked(self):
        """Returns the status of the SPFRx isKLocked attribute."""
        self.logger.debug("Read isKLocked")
        return self.component_manager.component_state.get("isklocked", False)

    @attribute(
        dtype=bool,
        doc="""
            Spectral inversion to correct the frequency sense of the currently
            configured band with respect to the RF signal.

            Logic 0: Output signal in the same frequency sense as input.

            Logic 1: Output signal in the opposite frequency sense as input.

            Setting this attribute to true will set the
            spectrum to be flipped.

        """,
        access=AttrWriteType.READ_WRITE,
    )
    def spectralInversion(self):
        """Returns the status of the SPFRx spectralInversion attribute."""
        self.logger.debug("Read spectralInversion")
        return self.component_manager.component_state.get("spectralinversion", False)

    @spectralInversion.write
    def spectralInversion(self, value):
        """Set the status of the SPFRx spectralInversion attribute."""
        self.logger.debug("spectralInversion write method called with param %s", value)

        if hasattr(self, "component_manager"):
            spfrx_com_man = self.component_manager.sub_component_managers["SPFRX"]
            spfrx_com_man.write_attribute_value("spectralInversion", value)
        else:
            self.logger.warning("No component manager to write spectralInversion yet")
            raise RuntimeError("Failed to write to spectralInversion on DishManager")

    @attribute(
        dtype=str,
        access=AttrWriteType.READ,
        doc=(
            "Default empty string when not set, and is a JSON string"
            "of the last requested global pointing model when set."
        ),
    )
    def lastCommandedPointingParams(self) -> str:
        """Tango string attribute that returns the
        last JSON input passed to the ApplyPointingModel command.
        Defaults to an empty string.
        """
        return self._last_commanded_pointing_params

    @attribute(
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        doc="""
            DSC Power Limit (kW). Note that this attribute can also be set by calling
            SetPowerMode. This value does not reflect the power limit in reality because
            the current PowerLimit(kW) is not reported as it cannot be read from the DSC.
            """,
    )
    def dscPowerLimitKw(self):
        """Returns the DSC Power Limit (Kw)."""
        return self.component_manager.component_state.get(
            "dscpowerlimitkw", DSC_MIN_POWER_LIMIT_KW
        )

    @dscPowerLimitKw.write
    def dscPowerLimitKw(self, value):
        """Sets the DSC Power Limit (Kw)."""
        # pylint: disable=attribute-defined-outside-init
        if DSC_MIN_POWER_LIMIT_KW <= value <= DSC_MAX_POWER_LIMIT_KW:
            self.component_manager.set_dsc_power_limit_kw(value)
        else:
            raise ValueError(
                f"Invalid value, {value}, for DSC Power Limit (kW),"
                f" valid range is [{DSC_MIN_POWER_LIMIT_KW}, {DSC_MAX_POWER_LIMIT_KW}]."
            )

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Returns the timestamp of the last watchdog reset in unix seconds.",
    )
    def lastWatchdogReset(self):
        """Returns lastWatchdogReset."""
        return self.component_manager.component_state["lastwatchdogreset"]

    @attribute(
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        doc="Sets dish manager watchdog timeout interval in seconds. "
        "By writing a value greater than 0, the watchdog will be enabled. If the watchdog "
        "is not reset within this interval, the dish will Stow on expiry of the timer. "
        "The watchdog timer can be reset by calling the `ResetWatchdog()` command. "
        "The watchdog can be disabled by writing a value less than or equal to 0.",
    )
    @requires_component_manager
    def watchdogTimeout(self):
        """Returns watchdogTimeout."""
        return self.component_manager.component_state["watchdogtimeout"]

    @watchdogTimeout.write
    @requires_component_manager
    def watchdogTimeout(self, value):
        """Writes watchdogTimeout."""
        self.component_manager._update_component_state(watchdogtimeout=value)
        if value <= 0:
            self.component_manager.watchdog_timer.disable()
        else:
            self.component_manager.watchdog_timer.enable(value)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="""
            The average wind speed in m/s of the last 10 minutes
            calculated from the connected weather stations.
            """,
    )
    def meanWindSpeed(self):
        """Returns the mean wind speed from connected weather stations."""
        return self.component_manager.component_state.get("meanwindspeed", -1)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="""
            The maximum wind speed in m/s of the last 3 seconds
            calculated from the connected weather stations.
            """,
    )
    def windGust(self):
        """Returns the mean wind speed over a short window from the weather stations."""
        return self.component_manager.component_state.get("windgust", -1)

    @attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="""
            Flag to enable or disable auto wind stow on wind speed
            or wind gust for values exeeding the configured threshold.
            """,
    )
    def autoWindStowEnabled(self):
        """Returns the value for the auto wind stow flag."""
        # Ideally, the default should be True (pretty much like auto record on zoom).
        # This will remain False pending decision on which subsystem will monitor WMS
        return self.component_manager.component_state.get("autowindstowenabled", False)

    @autoWindStowEnabled.write
    def autoWindStowEnabled(self, enabled: bool):
        """Flag to toggle the auto wind stow on or off."""
        self.logger.debug("autoWindStowEnabled updated to, %s", enabled)
        self.component_manager._update_component_state(autowindstowenabled=enabled)
        # if flag is disabled mid operation, the device might stay
        # in ALARM forever, the wind_stow_active flag should be unset
        # to allow other functions depending on its value unblocked
        if not enabled:
            self.component_manager.wind_stow_active = enabled

    @attribute(
        dtype=DscCtrlState,
        access=AttrWriteType.READ,
        doc=("DSC Control State - an aggregation of DSC Command Authority and DSC State"),
    )
    def dscCtrlState(self) -> str:
        """Returns DSC Control State."""
        return self.component_manager.component_state.get(
            "dscctrlstate", DscCtrlState.NO_AUTHORITY
        )

    @attribute(
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        doc="""
            Timeout (in seconds) to be used for each action. On each action DishManager will wait
            for the timeout duration for expected subservient device attribute updates. A value
            <= 0 will disable waiting and no monitoring will occur, commands will be fanned out to
            their respective subsevient devices and then the DishManager command will return as
            COMPLETED immediately.
        """,
    )
    def actionTimeoutSeconds(self):
        """Returns actionTimeoutSeconds."""
        return self.component_manager.get_action_timeout()

    @actionTimeoutSeconds.write
    def actionTimeoutSeconds(self, value):
        """Sets actionTimeoutSeconds."""
        self.logger.debug("Write to actionTimeoutSeconds, %s", value)
        self.component_manager.set_action_timeout(value)

    @attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="Status of the SPFC LNA H polarization power state.",
    )
    def b1LnaHPowerState(self):
        """Return the SPFC LNA H polarization power state."""
        return self.component_manager.component_state.get("b1lnahpowerstate", False)

    @b1LnaHPowerState.write
    def b1LnaHPowerState(self, value: bool):
        """Sets b1LnaHPowerState."""
        spf_com_man = self.component_manager.sub_component_managers["SPF"]
        self.logger.debug("Set b1LnaHPowerState to, %s", value)
        self.component_manager.check_dish_mode_for_spfc_lna_power_state()
        spf_com_man.write_attribute_value("b1LnaHPowerState", value)

    @attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="Status of the SPFC LNA H polarization power state.",
    )
    def b2LnaHPowerState(self):
        """Return the SPFC LNA H polarization power state."""
        return self.component_manager.component_state.get("b2lnahpowerstate", False)

    @b2LnaHPowerState.write
    def b2LnaHPowerState(self, value: bool):
        """Sets b2LnaHPowerState."""
        spf_com_man = self.component_manager.sub_component_managers["SPF"]
        self.logger.debug("Set b2LnaHPowerState to, %s", value)
        self.component_manager.check_dish_mode_for_spfc_lna_power_state()
        spf_com_man.write_attribute_value("b2LnaHPowerState", value)

    @attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="Status of the SPFC LNA H polarization power state.",
    )
    def b3LnaHPowerState(self):
        """Return the SPFC LNA H & V polarization power state."""
        return self.component_manager.component_state.get("b3lnahpowerstate", False)

    @b3LnaHPowerState.write
    def b3LnaHPowerState(self, value: bool):
        """Sets b3LnaHPowerState."""
        spf_com_man = self.component_manager.sub_component_managers["SPF"]
        self.logger.debug("Set b3LnaHPowerState to, %s", value)
        self.component_manager.check_dish_mode_for_spfc_lna_power_state()
        spf_com_man.write_attribute_value("b3LnaHPowerState", value)

    @attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="Status of the SPFC LNA H & V polarization power state.",
    )
    def b4LnaHPowerState(self):
        """Return the SPFC LNA H polarization power state."""
        return self.component_manager.component_state.get("b4lnahpowerstate", False)

    @b4LnaHPowerState.write
    def b4LnaHPowerState(self, value: bool):
        """Sets b4LnaHPowerState."""
        spf_com_man = self.component_manager.sub_component_managers["SPF"]
        self.logger.debug("Set b4LnaHPowerState to, %s", value)
        self.component_manager.check_dish_mode_for_spfc_lna_power_state()
        spf_com_man.write_attribute_value("b4LnaHPowerState", value)

    @attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="Status of the SPFC LNA H & V polarization power state.",
    )
    def b5aLnaHPowerState(self):
        """Return the SPFC LNA H polarization power state."""
        return self.component_manager.component_state.get("b5alnahpowerstate", False)

    @b5aLnaHPowerState.write
    def b5aLnaHPowerState(self, value: bool):
        """Sets b5aLnaHPowerState."""
        spf_com_man = self.component_manager.sub_component_managers["SPF"]
        self.logger.debug("Set b5aLnaHPowerState to, %s", value)
        self.component_manager.check_dish_mode_for_spfc_lna_power_state()
        spf_com_man.write_attribute_value("b5aLnaHPowerState", value)

    @attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="Status of the SPFC LNA H & V polarization power state.",
    )
    def b5bLnaHPowerState(self):
        """Return the SPFC LNA H polarization power state."""
        return self.component_manager.component_state.get("b5blnahpowerstate", False)

    @b5bLnaHPowerState.write
    def b5bLnaHPowerState(self, value: bool):
        """Sets b5bLnaHPowerState."""
        spf_com_man = self.component_manager.sub_component_managers["SPF"]
        self.logger.debug("Set b5bLnaHPowerState to, %s", value)
        self.component_manager.check_dish_mode_for_spfc_lna_power_state()
        spf_com_man.write_attribute_value("b5bLnaHPowerState", value)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reports the current output frequency of the B5DC PLL in GHz. "
        "The default value is 11.1 GHz.",
    )
    def rfcmFrequency(self) -> float:
        """Reflect the PLL output frequency in GHz."""
        return self.component_manager.component_state.get("rfcmfrequency", 0.0)

    @attribute(
        dtype=B5dcPllState,
        access=AttrWriteType.READ,
        doc="Reports the lock status of the B5DC RF Control Module (RFCM) PLL."
        "Returns B5dcPllState enum indicating if locked or lock lost.",
    )
    def rfcmPllLock(self):
        """Return the Phase lock loop state."""
        return self.component_manager.component_state.get("rfcmplllock", B5dcPllState.NOT_LOCKED)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reports the current attenuation setting for the Horizontal (H) polarization "
        "on the B5DC RF Control Module (RFCM). Value is in dB.",
    )
    def rfcmHAttenuation(self):
        """Return the rfcmHAttenuation."""
        return self.component_manager.component_state.get("rfcmhattenuation", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reports the current attenuation setting for the Vertical (V) polarization "
        "on the B5DC RF Control Module (RFCM). Value is in dB.",
    )
    def rfcmVAttenuation(self):
        """Return the rfcmVAttenuation."""
        return self.component_manager.component_state.get("rfcmvattenuation", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reports the current flowing through the clock photodiode "
        "in the B5DC. Value is in milliamperes (mA).",
    )
    def clkPhotodiodeCurrent(self):
        """Return the clkPhotodiodeCurrent."""
        return self.component_manager.component_state.get("clkphotodiodecurrent", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reports the input RF power level for the Horizontal (H) polarization "
        "measured at the B5DC RF Control Module (RFCM). Value is in dBm.",
    )
    def hPolRfPowerIn(self):
        """Return the hPolRfPowerIn."""
        return self.component_manager.component_state.get("hpolrfpowerin", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reports the input RF power level for the Vertical (V) polarization "
        "measured at the B5DC RF Control Module (RFCM). Value is in dBm.",
    )
    def vPolRfPowerIn(self):
        """Return the vPolRfPowerIn."""
        return self.component_manager.component_state.get("vpolrfpowerin", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reports the output RF power level for the Horizontal (H) polarization "
        "measured at the B5DC RF Control Module (RFCM). Value is in dBm.",
    )
    def hPolRfPowerOut(self):
        """Return the hPolRfPowerOut."""
        return self.component_manager.component_state.get("hpolrfpowerout", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reports the output RF power level for the Vertical (V) polarization "
        "measured at the B5DC RF Control Module (RFCM). Value is in dBm.",
    )
    def vPolRfPowerOut(self):
        """Return the vPolRfPowerOut sensor value."""
        return self.component_manager.component_state.get("vpolrfpowerout", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reports the temperature of the B5DC RF Control Module (RFCM) "
        "RF Printed Circuit Board (PCB). Value is in degrees Celsius.",
    )
    def rfTemperature(self):
        """Return the of the RFCM RF PCB in deg."""
        return self.component_manager.component_state.get("rftemperature", 0.0)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ,
        doc="Reports the temperature of the B5DC RF Control Module (RFCM) "
        "Power Supply Unit (PSU) PCB. Value is in degrees Celsius.",
    )
    def rfcmPsuPcbTemperature(self):
        """Return the temperature of the RFCM PSU PCB in deg."""
        return self.component_manager.component_state.get("rfcmpsupcbtemperature", 0.0)

    # --------
    # Commands
    # --------
    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        doc_in="Abort currently executing long running command on "
        "DishManager including stopping dish movement and transitioning "
        "dishMode to StandbyFP. For details consult DishManager documentation",
        display_level=DispLevel.OPERATOR,
        dtype_out="DevVarLongStringArray",
    )
    def Abort(self) -> DevVarLongStringArrayType:
        """Empty out long running commands in queue.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        handler = self.get_command_object("Abort")
        (return_code, message) = handler()
        return ([return_code], [message])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in="DevString",
        doc_in="""The command accepts a JSON string containing data to configure the SPFRx.
        The JSON structure is as follows:
        {
            "receiver_band": <string>,
            "sub_band": <string>,
            "spfrx_processing_parameters": {
                "dishes": List[<string>],
                "sync_pps":  <bool>,
                "attenuation_pol_x": <float>,
                "attenuation_pol_y": <float>,
                "attenuation_1_pol_x": <float>,
                "attenuation_1_pol_y": <float>,
                "attenuation_2_pol_x": <float>,
                "attenuation_2_pol_y": <float>,
                "saturation_threshold": <float>,
                "noise_diode": {
                    "pseudo_random": {
                        "binary_polynomial": <long>,
                        "seed": <long>,
                        "dwell": <long>,
                    },
                    "periodic": {
                        "period": <long>,
                        "duty_cycle": <long>,
                        "phase_shift": <long>,
                    }
                }
            }
        }
        where 'receiver_band', 'dishes' and 'sync_pps' are mandatory fields.
        when 'receiver_band' is set to '5b', the 'sub_band' field is mandatory.
        The 'dishes' field is a list of dish names that the SPFRx should be configured for,
        if 'all' is specified in the list, the SPFRx will be configured for all dishes.
        """,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand(self, json_string) -> DevVarLongStringArrayType:
        """Configure band according to JSON string supplied.

        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("ConfigureBand")

        result_code, unique_id = handler(json_string)
        return ([result_code], [unique_id])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand1(self, synchronise) -> DevVarLongStringArrayType:
        """This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 1. On completion of the band
        configuration, Dish will automatically transition to Dish
        mode OPERATE.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("ConfigureBand1")

        result_code, unique_id = handler(Band.B1, synchronise)
        return ([result_code], [unique_id])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand2(self, synchronise) -> DevVarLongStringArrayType:
        """Implemented as a Long Running Command.

        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 2. On completion of the band
        configuration, Dish will automatically transition to Dish
        mode OPERATE.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("ConfigureBand2")

        result_code, unique_id = handler(Band.B2, synchronise)
        return ([result_code], [unique_id])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand3(self, synchronise):  # pylint: disable=unused-argument
        """This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 3. On completion of the band
        configuration, Dish will automatically transition to Dish
        mode OPERATE.
        """
        handler = self.get_command_object("ConfigureBand3")

        result_code, unique_id = handler(Band.B3, synchronise)
        return ([result_code], [unique_id])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand4(self, synchronise):  # pylint: disable=unused-argument
        """This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 4. On completion of the band
        configuration, Dish will automatically transition to Dish
        mode OPERATE.
        """
        handler = self.get_command_object("ConfigureBand4")

        result_code, unique_id = handler(Band.B4, synchronise)
        return ([result_code], [unique_id])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand5a(self, synchronise):  # pylint: disable=unused-argument
        """This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 5a. On completion of the band
        configuration, Dish will automatically transition to Dish
        mode OPERATE.
        """
        handler = self.get_command_object("ConfigureBand5a")

        result_code, unique_id = handler(Band.B5a, synchronise)
        return ([result_code], [unique_id])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand5b(self, synchronise):  # pylint: disable=unused-argument
        """This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 5b. On completion of the band
        configuration, Dish will automatically transition to Dish
        mode OPERATE.
        """
        handler = self.get_command_object("ConfigureBand5b")

        self.logger.warning("ConfigureBand5b called, but we're configuring B1 until 5B is ready.")
        result_code, unique_id = handler(Band.B1, synchronise)

        return ([result_code], [unique_id])

    @record_command(False)
    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def FlushCommandQueue(self):
        """Flushes the queue of time stamped commands."""
        raise NotImplementedError

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(dtype_in=str, dtype_out="DevVarLongStringArray", display_level=DispLevel.OPERATOR)
    def Scan(self, scanid) -> DevVarLongStringArrayType:
        """The Dish records the scanID for an ongoing scan.

        :param args: the scanID in string format
        """
        handler = self.get_command_object("Scan")
        result_code, unique_id = handler(scanid)

        return ([result_code], [unique_id])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(dtype_in=None, dtype_out="DevVarLongStringArray", display_level=DispLevel.OPERATOR)
    def EndScan(self) -> DevVarLongStringArrayType:
        """This command clears out the scan_id."""
        handler = self.get_command_object("EndScan")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @record_command(True)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(dtype_in=None, dtype_out="DevVarLongStringArray", display_level=DispLevel.OPERATOR)
    def SetMaintenanceMode(self) -> DevVarLongStringArrayType:
        """This command triggers the Dish to transition to the MAINTENANCE
        Dish Element Mode, and returns to the caller. To go into a state
        that is safe to approach the Dish by a maintainer, and to enable the
        Engineering interface to allow direct access to low level control and
        monitoring by engineers and maintainers. This mode will also enable
        engineers and maintainers to upgrade SW and FW. Dish also enters this
        mode when an emergency stop button is pressed.
        """
        handler = self.get_command_object("SetMaintenanceMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @record_command(True)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def SetOperateMode(self) -> DevVarLongStringArrayType:
        """Deprecated command.

        This command was previously used to trigger the Dish to transition to the OPERATE Dish
        Element Mode, however, this command has now been deprecated. To transition to OPERATE dish
        mode the ConfigureBand<N> command should be used to configure a band, this will
        automatically transition to OPERATE dish mode on successfull configuration.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        return (
            [ResultCode.REJECTED],
            [
                "SetOperateMode command is deprecated. To transition to OPERATE dish mode use the"
                " ConfigureBand<N> command to configure a band, this will automatically transition"
                " to OPERATE dish mode on successfull configuration."
            ],
        )

    @record_command(True)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def SetStandbyLPMode(self) -> DevVarLongStringArrayType:
        """Implemented as a Long Running Command.

        This command triggers the Dish to transition to the STANDBY‐LP Dish
        Element Mode, and returns to the caller. Standby_LP is the default
        mode when the Dish is configured for low power consumption, and is
        the mode wherein Dish ends after a start-up procedure.
        All subsystems go into a low power state to power only the essential
        equipment. Specifically the Helium compressor will be set to a low
        power consumption, and the drives will be disabled. When issued a
        STOW command while in LOW power, the DS controller should be
        able to turn the drives on, stow the dish and turn the drives off
        again. The purpose of this mode is to enable the observatory to
        perform power management (load curtailment), and also to conserve
        energy for non‐operating dishes.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("SetStandbyLPMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @record_command(True)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def SetStandbyFPMode(self) -> DevVarLongStringArrayType:
        """Implemented as a Long Running Command.

        This command triggers the Dish to transition to the STANDBY‐FP Dish
        Element Mode, and returns to the caller.
        To prepare all subsystems for active observation, once a command is
        received by TM to go to the FULL_POWER mode.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("SetStandbyFPMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @record_command(True)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    @requires_component_manager
    def SetStowMode(self) -> DevVarLongStringArrayType:
        """Implemented as a Long Running Command.

        This command immediately triggers the Dish to transition to STOW Dish Element
        Mode. It subsequently aborts all queued LRC tasks and then returns to the caller.
        It points the dish in a direction that minimises the wind loads on the structure,
        for survival in strong wind conditions. The Dish is able to observe in the STOW
        position, for the purpose of transient detection.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        # Handle the exit from maintenance mode if the dish is in maintenance mode.
        if self.component_manager.component_state["dishmode"] == DishMode.MAINTENANCE:
            self.component_manager.handle_exit_maintenance_mode_transition()

        handler = self.get_command_object("SetStowMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in="DevVarFloatArray",
        doc_in="[0]: Azimuth\n[1]: Elevation",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def Slew(self, values):  # pylint: disable=unused-argument
        """Trigger the Dish to start moving to the commanded (Az,El) position.

        :param argin: the az, el for the pointing in stringified json format

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("Slew")
        result_code, unique_id = handler(values)

        return ([result_code], [unique_id])

    @record_command(False)
    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def Synchronise(self):
        """Reset configured band sample counters. Command only valid in
        SPFRx OPERATE mode.
        """
        raise NotImplementedError

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def Track(self) -> DevVarLongStringArrayType:
        """Implemented as a Long Running Command.

        When the Track command is received the Dish will start tracking the
        commanded positions.
        The pointingState attribute will report SLEW while the Dish is settling
        onto a target and is still not within the specified pointing accuracy.
        As soon as the pointing accuracy is within specifications, the
        pointingState attribute will report TRACK.
        Track data source (TABLE-A, TABLE-B, POLY) used for tracking is pre‐
        configured using trackProgramMode attribute.
        Tracking using program table (A, B) is pre‐configured using the
        following attributes:
        1. trackInterpolationMode: to select type of
        interpolation, Newton (default) or Spline.
        2. programTrackTable: to load program table data
        (Az,El,timestamp sets) on selected ACU table
        3. trackTableLoadMode: to add/append/reset track table data

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("Track")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def TrackStop(self) -> DevVarLongStringArrayType:
        """Implemented as a Long Running Command.

        When the TrackStop command is received the Dish will stop moving
        but will not apply brakes.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("TrackStop")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(  # type: ignore[misc]
        dtype_in=(float,),
        dtype_out="DevVarLongStringArray",
        doc_in="""
            Load (global) static tracking offsets.

            The offset is loaded immediately and is not cancelled
            between tracks. The static offset introduces a positional adjustment to facilitate
            reference pointing and the five-point calibration. The static offsets are added the
            output of the interpolator before the correction of the static pointing model.

            Note: If the static pointing correction is switched off, the static offsets remain as
            an offset to the Azimuth and Elevation positions and need to be set to zero manually.

            Static offset parameters are:
            [0] Off_Xel, [1] Off_El
        """,
    )
    def TrackLoadStaticOff(self, values) -> DevVarLongStringArrayType:
        """Loads the given static pointing model offsets.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("TrackLoadStaticOff")
        result_code, unique_id = handler(values)
        return ([result_code], [unique_id])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in="DevLong64",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def SetKValue(self, value) -> DevVarLongStringArrayType:
        """This command sets the kValue on SPFRx.
        Note that it will only take effect after
        SPFRx has been restarted.
        """
        handler = self.get_command_object("SetKValue")
        return_code, message = handler(value)
        return ([return_code], [message])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=int,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
        doc_in="""Set the frequency on the band 5 down converter.

        :param frequency: frequency to set [B5dcFrequency.F_11_1_GHZ(1),
        B5dcFrequency.F_13_2_GHZ(2) or B5dcFrequency.F_13_86_GHZ(3)]
        """,
    )
    def SetFrequency(self, value) -> DevVarLongStringArrayType:
        """Set the frequency on the band 5 down converter."""
        handler = self.get_command_object("SetFrequency")
        return_code, message = handler(value)
        return ([return_code], [message])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=int,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
        doc_in="""Set the vertical polarization attenuation on the band 5 down converter.

        :param attenuation_db: value to set in dB [0-31dB]
        """,
    )
    def SetVPolAttenuation(self, value) -> DevVarLongStringArrayType:
        """Set the vertical polarization attenuation on the band 5 down converter."""
        handler = self.get_command_object("SetVPolAttenuation")
        return_code, message = handler(value)
        return ([return_code], [message])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=int,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
        doc_in="""Set the horizontal polarization attenuation on the band 5 down converter.

        :param attenuation_db: value to set in dB [0-31dB]
        """,
    )
    def SetHPolAttenuation(self, value) -> DevVarLongStringArrayType:
        """Set the horizontal polarization attenuation on the band 5 down converter."""
        handler = self.get_command_object("SetHPolAttenuation")
        return_code, message = handler(value)
        return ([return_code], [message])

    @command(
        dtype_in="DevString",
        doc_in="""The command accepts a JSON input (value) containing data to update a particular
        band's (b1-b5b). The following 18 coefficients need to be within the JSON object:
            [0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
            [9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
            [15] HESE4, [16] HECE8, [17] HESE8.

        The command only looks for the antenna, band and coefficients
        - everything else is ignored. A typical structure would be:
            "interface": "...",
            "antenna": "....",
            "band": "Band_...",
            "attrs": {...},
            "coefficients": {
                "IA": {...},
                ...
                "HESE8":{...}
            },
            "rms_fits": {
                "xel_rms": {...},
                "el_rms": {...},
                "sky_rms": {...}
            }
        }""",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def ApplyPointingModel(self, value) -> DevVarLongStringArrayType:
        """Updates a band's coefficient parameters with a given JSON input.
        Note, all 18 coefficients need to be present in the JSON object,the Dish ID
        should be correct, the appropriate unit should be present and coefficient values
        should be in range. Each time the command is called all parameters will get
        updated not just the ones that have been modified.
        """
        last_commanded_pointing_params = value
        self._last_commanded_pointing_params = last_commanded_pointing_params
        # Push change and archive events with the recorded value
        self.push_change_event("lastCommandedPointingParams", last_commanded_pointing_params)
        self.push_archive_event("lastCommandedPointingParams", last_commanded_pointing_params)
        handler = self.get_command_object("ApplyPointingModel")
        return_code, message = handler(value)
        return ([return_code], [message])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=None,
        doc_in="Stops communication with subdevices and stops the watchdog timer, "
        "if it is active.",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def StopCommunication(self):
        """Stop communicating with monitored devices."""
        self.component_manager.stop_communicating()

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=None,
        doc_in="Starts communication with subdevices and starts the watchdog timer, "
        "if it is configured via `watchdogTimeout` attribute.",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def StartCommunication(self):
        """Start communicating with monitored devices."""
        self.component_manager.start_communicating()

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=None,
        dtype_out=str,
        display_level=DispLevel.OPERATOR,
        doc_out=("Retrieve the states of SPF, SPFRx and DS as DishManager sees it."),
    )
    def GetComponentStates(self):
        """Get the current component states of subservient devices.

        Subservient devices constiture SPF, SPFRx, DS and WMS. Used for debugging.
        """
        component_states = {}
        for (
            device,
            component_state,
        ) in self.component_manager.sub_component_managers.items():
            component_states[device] = component_state._component_state
        component_states["DM"] = self.component_manager._component_state
        return json.dumps(str(component_states))

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_in=None,
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def SyncComponentStates(self) -> None:
        """Sync each subservient device component state with its tango device
        to refresh the dish manager component state.
        """
        if hasattr(self, "component_manager"):
            self.component_manager.sync_component_states()

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
        doc_in="This command resets the watchdog timer. "
        "`lastWatchdogReset` attribute will be updated with the unix timestamp. "
        "By default, the watchdog timer is disabled and can be enabled by setting the "
        "`watchdogTimeout` attribute to a value greater than 0.",
        doc_out="Returns a DevVarLongStringArray with the return code and message.",
    )
    @requires_component_manager
    def ResetWatchdogTimer(self) -> DevVarLongStringArrayType:
        """This command resets the watchdog timer."""
        value = datetime.now().timestamp()
        try:
            self.component_manager.watchdog_timer.reset()
        except WatchdogTimerInactiveError:
            if (
                self.component_manager.component_state["dishmode"] == DishMode.STOW
                and self.component_manager.component_state["watchdogtimeout"] > 0
            ):
                return (
                    [ResultCode.FAILED],
                    ["Watchdog timer is not active when dish is in STOW mode."],
                )
            else:
                return ([ResultCode.FAILED], ["Watchdog timer is not active."])
        self.component_manager._update_component_state(lastwatchdogreset=value)
        return (
            [ResultCode.OK],
            [f"Watchdog timer reset at {value}s"],
        )

    @record_command(False)
    @BaseInfoIt(show_args=False, show_kwargs=False, show_ret=True)
    @command(
        dtype_in=None,
        doc_in="""This command resets the program track table on the controller""",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def ResetTrackTable(self) -> DevVarLongStringArrayType:
        """Resets the program track table on the controller.

        Track table is cleared on the controller in RESET load mode
        """
        handler = self.get_command_object("ResetTrackTable")
        result_code, message = handler()
        if result_code == ResultCode.FAILED:
            raise RuntimeError(f"{message}")
        assert isinstance(message, list), f"Expected a table from the handler but got: {message}"

        self._program_track_table = message
        self.push_change_event("programTrackTable", message)
        self.push_archive_event("programTrackTable", message)
        return ([result_code], ["programTrackTable successfully reset"])

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(dtype_out="DevVarLongStringArray")
    def On(self) -> DevVarLongStringArrayType:
        """The On command inherited from base classes."""
        raise NotImplementedError("DishManager does not implement the On command.")

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(dtype_out="DevVarLongStringArray")
    def Off(self) -> DevVarLongStringArrayType:
        """The Off command inherited from base classes."""
        raise NotImplementedError("DishManager does not implement the Off command.")

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(dtype_out="DevVarLongStringArray")
    def Standby(self) -> DevVarLongStringArrayType:
        """The Standby command inherited from base classes."""
        raise NotImplementedError("DishManager does not implement the Standby command.")

    @record_command(False)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @command(dtype_out="DevVarLongStringArray")
    def Reset(self) -> DevVarLongStringArrayType:
        """The Reset command inherited from base classes."""
        raise NotImplementedError("DishManager does not implement the Reset command.")


def main(args=None, **kwargs):
    """Launch a DishManager device."""
    return run((DishManager,), args=args, **kwargs)


if __name__ == "__main__":
    main()
