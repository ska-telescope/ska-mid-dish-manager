# pylint: disable=invalid-name,access-member-before-definition
# pylint: disable=C0302,W0212,W0201
"""
This module implements the dish manager device for DishLMC.

It exposes the attributes and commands which control the dish
and the subservient devices
"""

import json
import weakref
from functools import reduce
from typing import List, Optional, Tuple

from ska_control_model import CommunicationStatus, ResultCode
from ska_tango_base import SKAController
from ska_tango_base.commands import SubmittedSlowCommand
from tango import AttrWriteType, DevState, DevULong, DispLevel
from tango.server import attribute, command, device_property, run

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.command_class import (
    AbortCommand,
    AbortCommandsDeprecatedCommand,
    ApplyPointingModelCommand,
    SetKValueCommand,
    StowCommand,
)
from ska_mid_dish_manager.models.constants import (
    BAND_POINTING_MODEL_PARAMS_LENGTH,
    DEFAULT_DISH_ID,
    DEFAULT_DS_MANAGER_TRL,
    DEFAULT_SPFC_TRL,
    DEFAULT_SPFRX_TRL,
    DSC_MAX_POWER_LIMIT_KW,
    DSC_MIN_POWER_LIMIT_KW,
)
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    CapabilityStates,
    DishDevice,
    DishMode,
    NoiseDiodeMode,
    PointingState,
    PowerState,
    TrackInterpolationMode,
    TrackProgramMode,
    TrackTableLoadMode,
)
from ska_mid_dish_manager.release import ReleaseInfo
from ska_mid_dish_manager.utils.command_logger import BaseInfoIt
from ska_mid_dish_manager.utils.decorators import record_mode_change_request
from ska_mid_dish_manager.utils.track_table_input_validation import (
    TrackLoadTableFormatting,
    TrackTableTimestampError,
)

DevVarLongStringArrayType = Tuple[List[ResultCode], List[Optional[str]]]

# Used for input validation. Input samples to tracktable that is less that
# TRACK_LOAD_FUTURE_THRESHOLD_SEC in the future are logged
TRACK_LOAD_FUTURE_THRESHOLD_SEC = 5

# provision same variable from base classes
_MAXIMUM_STATUS_QUEUE_SIZE = 32

_DISH_SUB_COMPONENTS_CONTROLLED = 3


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class DishManager(SKAController):
    """
    The Dish Manager of the Dish LMC subsystem
    """

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
    DishId = device_property(dtype=str, default_value=DEFAULT_DISH_ID)

    def _create_lrc_attributes(self) -> None:
        """
        Create attributes for the long running commands.

        This is an override to update the max_dim_x of longRunningCommandInProgress.
        DishManager reports progress from its running command and from the sub devices
        commands were fanned out to.

        :raises AssertionError: if max_queued_tasks or max_executing_tasks is not
            equal to or greater than 0 or 1 respectively.
        """
        assert (
            self.component_manager.max_queued_tasks >= 0
        ), "max_queued_tasks property must be equal to or greater than 0."
        assert (
            self.component_manager.max_executing_tasks >= 1
        ), "max_executing_tasks property must be equal to or greater than 1."
        self._status_queue_size = max(
            self.component_manager.max_queued_tasks * 2
            + self.component_manager.max_executing_tasks,
            _MAXIMUM_STATUS_QUEUE_SIZE,
        )
        self._create_attribute(
            "longRunningCommandStatus",
            self._status_queue_size * 2,  # 2 per command
            self.longRunningCommandStatus,
        )
        self._create_attribute(
            "longRunningCommandsInQueue",
            self._status_queue_size,
            self.longRunningCommandsInQueue,
        )
        self._create_attribute(
            "longRunningCommandIDsInQueue",
            self._status_queue_size,
            self.longRunningCommandIDsInQueue,
        )
        self._create_attribute(
            "longRunningCommandInProgress",
            self.component_manager.max_executing_tasks + _DISH_SUB_COMPONENTS_CONTROLLED,
            self.longRunningCommandInProgress,
        )
        self._create_attribute(
            "longRunningCommandProgress",
            self.component_manager.max_executing_tasks
            * 2,  # cmd name and progress for each command
            self.longRunningCommandProgress,
        )

    def create_component_manager(self) -> DishManagerComponentManager:
        """Create the component manager for DishManager

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
            communication_state_callback=self._communication_state_changed,
            component_state_callback=self._component_state_changed,
        )

    def init_command_objects(self) -> None:
        """Initialise the command handlers"""
        super().init_command_objects()

        for command_name, method_name in [
            ("SetStandbyLPMode", "set_standby_lp_mode"),
            ("SetOperateMode", "set_operate_mode"),
            ("SetStandbyFPMode", "set_standby_fp_mode"),
            ("Track", "track_cmd"),
            ("TrackStop", "track_stop_cmd"),
            ("ConfigureBand1", "configure_band_cmd"),
            ("ConfigureBand2", "configure_band_cmd"),
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

        self.register_command_object(
            "Abort",
            AbortCommand(
                "Abort",
                self._command_tracker,
                self.component_manager,
                "abort",
                callback=None,
                logger=self.logger,
            ),
        )

        self.register_command_object(
            "AbortCommands",
            AbortCommandsDeprecatedCommand(
                "AbortCommands",
                self._command_tracker,
                self.component_manager,
                "abort",
                callback=None,
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

    # ---------
    # Callbacks
    # ---------

    def _update_version_of_subdevice_on_success(self, device: DishDevice, build_state: str):
        """Update the version information of subdevice if connection is successful."""
        try:
            self._build_state = self._release_info.update_build_state(device, build_state)
        except AttributeError:
            self.logger.warning(
                "Failed to update build state information for [%s] device.", device.value
            )

    def _attr_quality_state_changed(self, attribute_name, new_attribute_quality):
        device_attribute_name = self._component_state_attr_map.get(attribute_name, None)
        if device_attribute_name:
            attribute_object = getattr(self, device_attribute_name, None)
            if attribute_object:
                if attribute_object.get_quality() is not new_attribute_quality:
                    attribute_object.set_quality(new_attribute_quality, True)

    def _communication_state_changed(self, communication_state: CommunicationStatus) -> None:
        action_map = {
            CommunicationStatus.NOT_ESTABLISHED: None,
            CommunicationStatus.ESTABLISHED: "component_on",
            CommunicationStatus.DISABLED: "component_disconnected",
        }
        action = action_map[communication_state]
        if action is None:
            status = (
                "Event channel on a sub-device is not responding anymore "
                "or change event subscription is not complete"
            )
            self._update_state(
                DevState.ALARM,
                status,
            )
        else:
            self.op_state_model.perform_action(action)

    # pylint: disable=unused-argument
    def _component_state_changed(self, *args, **kwargs):
        def change_case(attr_name):
            """Convert camel case string to snake case

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
            return f"_{reduce(lambda x, y: x + ('_' if y.isupper() else '') + y, attr_name).lower()}"  # noqa: E501

        for comp_state_name, comp_state_value in kwargs.items():
            attribute_name = self._component_state_attr_map.get(comp_state_name, comp_state_name)
            attribute_variable = change_case(attribute_name)
            setattr(self, attribute_variable, comp_state_value)
            self.push_change_event(attribute_name, comp_state_value)
            self.push_archive_event(attribute_name, comp_state_value)

    class InitCommand(SKAController.InitCommand):  # pylint: disable=too-few-public-methods
        """
        A class for the Dish Manager's init_device() method
        """

        # pylint: disable=invalid-name
        # pylint: disable=too-many-statements
        # pylint: disable=arguments-differ
        def do(self):
            """
            Initializes the attributes and properties of the DishManager
            """
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
            device._last_commanded_mode = ("0.0", "")
            device._last_commanded_pointing_params = ""
            device._release_info = ReleaseInfo(
                ds_manager_address=device.DSDeviceFqdn,
                spfc_address=device.SPFDeviceFqdn,
                spfrx_address=device.SPFRxDeviceFqdn,
            )
            device._build_state = device._release_info.get_build_state()

            # push change events, needed to use testing library

            device._component_state_attr_map = {
                "dishmode": "dishMode",
                "pointingstate": "pointingState",
                "configuredband": "configuredBand",
                "achievedtargetlock": "achievedTargetLock",
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
                "attenuationpolh": "attenuationPolH",
                "attenuationpolv": "attenuationPolV",
                "kvalue": "kValue",
                "trackinterpolationmode": "trackInterpolationMode",
                "scanid": "scanID",
                "ignorespf": "ignoreSpf",
                "ignorespfrx": "ignoreSpfrx",
                "spfconnectionstate": "spfConnectionState",
                "spfrxconnectionstate": "spfrxConnectionState",
                "dsconnectionstate": "dsConnectionState",
                "noisediodemode": "noiseDiodeMode",
                "periodicnoisediodepars": "periodicNoiseDiodePars",
                "pseudorandomnoisediodepars": "pseudoRandomNoiseDiodePars",
                "actstaticoffsetvaluexel": "actStaticOffsetValueXel",
                "actstaticoffsetvalueel": "actStaticOffsetValueEl",
                "dscpowerlimitkw": "dscPowerLimitKw",
                "tracktablecurrentindex": "trackTableCurrentIndex",
                "tracktableendindex": "trackTableEndIndex",
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
                "powerState",
                "trackProgramMode",
                "trackTableLoadMode",
                "lastCommandedMode",
                "lastCommandedPointingParams",
            ):
                device.set_change_event(attr, True, False)
                device.set_archive_event(attr, True, False)

            # Try to connect to DB and update memorized attributes if TANGO_HOST is set
            device.component_manager.try_update_memorized_attributes_from_db()

            device.instances[device.get_name()] = device
            (result_code, message) = super().do()
            device.component_manager.start_communicating()
            device.op_state_model.perform_action("component_on")
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
    def lastCommandedMode(self) -> tuple[str, str]:
        """Return the last commanded mode"""
        return self._last_commanded_mode

    # pylint: disable=invalid-name
    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Displays connection status to SPF device",
    )
    def spfConnectionState(self):
        """Returns the spf connection state"""
        return self.component_manager.component_state.get(
            "spfconnectionstate", CommunicationStatus.NOT_ESTABLISHED
        )

    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Displays connection status to SPFRx device",
    )
    def spfrxConnectionState(self):
        """Returns the spfrx connection state"""
        return self.component_manager.component_state.get(
            "spfrxconnectionstate", CommunicationStatus.NOT_ESTABLISHED
        )

    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Displays connection status to DS device",
    )
    def dsConnectionState(self):
        """Returns the ds connection state"""
        return self.component_manager.component_state.get(
            "dsconnectionstate", CommunicationStatus.NOT_ESTABLISHED
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
        """Returns the achievedTargetLock"""
        return self.component_manager.component_state.get("achievedtargetlock", False)

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
        access=AttrWriteType.READ_WRITE,
        doc="Indicates the SPFRx attenuation in the horizontal "
        "signal chain for the configuredband.",
    )
    def attenuationPolH(self):
        """Returns the attenuationPolH"""
        return self.component_manager.component_state.get("attenuationpolh", 0.0)

    @attenuationPolH.write
    def attenuationPolH(self, value):
        """Set the attenuationPolH"""
        # pylint: disable=attribute-defined-outside-init
        spfrx_cm = self.component_manager.sub_component_managers["SPFRX"]
        spfrx_cm.write_attribute_value("attenuationPolH", value)

    @attribute(
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        doc="Indicates the SPFRx attenuation in the vertical "
        "signal chain for the configuredband.",
    )
    def attenuationPolV(self):
        """Returns the attenuationPolV"""
        return self.component_manager.component_state.get("attenuationpolv", 0.0)

    @attenuationPolV.write
    def attenuationPolV(self, value):
        """Set the attenuationPolV("""
        # pylint: disable=attribute-defined-outside-init
        spfrx_cm = self.component_manager.sub_component_managers["SPFRX"]
        spfrx_cm.write_attribute_value("attenuationPolV", value)

    @attribute(
        dtype=int,
        access=AttrWriteType.READ,
        doc="Returns the kValue for SPFRX",
    )
    def kValue(self):
        """Returns the kValue for SPFRX"""
        return self.component_manager.component_state["kvalue"]

    @attribute(
        dtype=bool,
        doc="Indicates that the Dish has moved beyond an azimuth wrap limit.",
    )
    def azimuthOverWrap(self):
        """Returns the azimuthOverWrap"""
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
        """Returns the band0PointingModelParams"""
        return self.component_manager.component_state.get("band0pointingmodelparams", [])

    @band0PointingModelParams.write
    def band0PointingModelParams(self, value):
        """Set the band0PointingModelParams"""
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
        """Returns the band1PointingModelParams"""
        return self.component_manager.component_state.get("band1pointingmodelparams", [])

    @band1PointingModelParams.write
    def band1PointingModelParams(self, value):
        """Set the band1PointingModelParams"""
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
        """Returns the band2PointingModelParams"""
        return self.component_manager.component_state.get("band2pointingmodelparams", [])

    @band2PointingModelParams.write
    def band2PointingModelParams(self, value):
        """Set the band2PointingModelParams"""
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
        """Returns the band3PointingModelParams"""
        return self.component_manager.component_state.get("band3pointingmodelparams", [])

    @band3PointingModelParams.write
    def band3PointingModelParams(self, value):
        """Set the band3PointingModelParams"""
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
        """Returns the band4PointingModelParams"""
        return self.component_manager.component_state.get("band4pointingmodelparams", [])

    @band4PointingModelParams.write
    def band4PointingModelParams(self, value):
        """Set the band4PointingModelParams"""
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
        """Returns the band5aPointingModelParams"""
        return self._band5a_pointing_model_params

    @band5aPointingModelParams.write
    def band5aPointingModelParams(self, value):
        """Set the band5aPointingModelParams"""
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
        """Returns the band5bPointingModelParams"""
        return self._band5b_pointing_model_params

    @band5bPointingModelParams.write
    def band5bPointingModelParams(self, value):
        """Set the band5bPointingModelParams"""
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
        """Returns the band1SamplerFrequency"""
        return self._band1_sampler_frequency

    @band1SamplerFrequency.write
    def band1SamplerFrequency(self, value):
        """Set the band1SamplerFrequency"""
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
        """Returns the band2SamplerFrequency"""
        return self._band2_sampler_frequency

    @band2SamplerFrequency.write
    def band2SamplerFrequency(self, value):
        """Set the band2SamplerFrequency"""
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
        """Returns the band3SamplerFrequency"""
        return self._band3_sampler_frequency

    @band3SamplerFrequency.write
    def band3SamplerFrequency(self, value):
        """Set the band3SamplerFrequency"""
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
        """Returns the band4SamplerFrequency"""
        return self._band4_sampler_frequency

    @band4SamplerFrequency.write
    def band4SamplerFrequency(self, value):
        """Set the band4SamplerFrequency"""
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
        """Returns the band5aSamplerFrequency"""
        return self._band5a_sampler_frequency

    @band5aSamplerFrequency.write
    def band5aSamplerFrequency(self, value):
        """Set the band5aSamplerFrequency"""
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
        """Returns the band5bSamplerFrequency"""
        return self._band5b_sampler_frequency

    @band5bSamplerFrequency.write
    def band5bSamplerFrequency(self, value):
        """Set the band5bSamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band5b_sampler_frequency = value
        self.push_change_event("band5bSamplerFrequency", value)
        self.push_archive_event("band5bSamplerFrequency", value)

    @attribute(
        dtype=bool,
        doc="Indicates whether Dish is capturing data in the configured band or not.",
    )
    def capturing(self):
        """Returns the capturing"""
        return self.component_manager.component_state.get("capturing", False)

    @attribute(
        dtype=Band,
        doc="The frequency band that the Dish is configured to capture data in.",
    )
    def configuredBand(self):
        """Returns the configuredBand"""
        return self.component_manager.component_state.get("configuredband", Band.UNKNOWN)

    @attribute(
        dtype=(float,),
        max_dim_x=2,
        access=AttrWriteType.WRITE,
        doc="[0] Pointing error\n[1] Time period",
    )
    def configureTargetLock(self):
        """Returns the configureTargetLock"""
        return self._configure_target_lock

    @configureTargetLock.write
    def configureTargetLock(self, value):
        """Set the configureTargetLock"""
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
        """Returns the dishMode"""
        return self.component_manager.component_state.get("dishmode", DishMode.UNKNOWN)

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="Configures the Max Short Term Average Power (5sec‐10min) in "
        "kilowatt that the DSH instance is curtailed to while "
        "dshPowerCurtailment is [TRUE]. The default value is 13.5.",
    )
    def dshMaxShortTermPower(self):
        """Returns the dshMaxShortTermPower"""
        return self._dsh_max_short_term_power

    @dshMaxShortTermPower.write
    def dshMaxShortTermPower(self, value):
        """Set the dshMaxShortTermPower"""
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
        """Returns the dshPowerCurtailment"""
        return self._dsh_power_curtailment

    @dshPowerCurtailment.write
    def dshPowerCurtailment(self, value):
        """Set the dshPowerCurtailment"""
        # pylint: disable=attribute-defined-outside-init
        self._dsh_power_curtailment = value
        self.push_change_event("dshPowerCurtailment", value)
        self.push_archive_event("dshPowerCurtailment", value)

    @attribute(dtype=(((float),),), max_dim_x=1024, max_dim_y=1024)
    def frequencyResponse(self):
        """Returns the frequencyResponse"""
        return self._frequency_response

    @attribute(dtype=(float,), access=AttrWriteType.WRITE)
    def noiseDiodeConfig(self):
        """Returns the noiseDiodeConfig"""
        return self._noise_diode_config

    @noiseDiodeConfig.write
    def noiseDiodeConfig(self, value):
        """Set the noiseDiodeConfig"""
        # pylint: disable=attribute-defined-outside-init
        self._noise_diode_config = value
        self.push_change_event("noiseDiodeConfig", value)
        self.push_archive_event("noiseDiodeConfig", value)

    @attribute(dtype=PointingState)
    def pointingState(self):
        """Returns the pointingState"""
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
        """Returns the programTrackTable"""
        return self._program_track_table

    @programTrackTable.write
    def programTrackTable(self, table):
        """Set the programTrackTable"""
        # pylint: disable=attribute-defined-outside-init
        # Spectrum that is a multiple of 3 values:
        # - (timestamp, azimuth coordinate, elevation coordinate)
        # i.e. [tai_0, az_pos_0, el_pos_0, ..., tai_n, az_pos_n, el_pos_n]
        self.logger.debug("programTrackTable write method called with table %s", table)

        # perform input validation on table
        try:
            TrackLoadTableFormatting().check_track_table_input_valid(
                table, TRACK_LOAD_FUTURE_THRESHOLD_SEC
            )
        except TrackTableTimestampError as te:
            self.logger.warning("Track table timestamp warning: %s", te)
        except ValueError as ve:
            raise ve

        length_of_table = len(table)
        sequence_length = length_of_table / 3
        result_code, result_message = self.component_manager.track_load_table(
            sequence_length, table, self._track_table_load_mode
        )

        result_code = ResultCode(result_code)
        if result_code != ResultCode.OK:
            err_message = (
                f"Write to programTrackTable failed, [{result_code.name}] [{result_message}]"
            )
            raise RuntimeError(err_message)
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
        """Returns the pointingBufferSize"""
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
        """Returns the polyTrack"""
        return self._poly_track

    @polyTrack.write
    def polyTrack(self, value):
        """Set the polyTrack"""
        # pylint: disable=attribute-defined-outside-init
        self._poly_track = value
        self.push_change_event("polyTrack", value)
        self.push_archive_event("polyTrack", value)

    @attribute(dtype=PowerState)
    def powerState(self):
        """Returns the powerState"""
        return self._power_state

    @attribute(
        dtype=TrackInterpolationMode,
        access=AttrWriteType.READ_WRITE,
        doc="Selects the type of interpolation to be used in program tracking.",
    )
    def trackInterpolationMode(self):
        """Returns the trackInterpolationMode"""
        return self._track_interpolation_mode

    @trackInterpolationMode.write
    def trackInterpolationMode(self, value):
        """Set the trackInterpolationMode"""
        self.component_manager.set_track_interpolation_mode(value)

    @attribute(
        dtype=TrackProgramMode,
        access=AttrWriteType.READ_WRITE,
        doc="Selects the track program source (table A, table B, polynomial "
        "stream) used in the ACU for tracking. Coordinates given in the "
        "programTrackTable attribute are loaded in ACU in the selected table.",
    )
    def trackProgramMode(self):
        """Returns the trackProgramMode"""
        return self._track_program_mode

    @trackProgramMode.write
    def trackProgramMode(self, value):
        """Set the trackProgramMode"""
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
        """Returns the trackTableLoadMode"""
        return self._track_table_load_mode

    @trackTableLoadMode.write
    def trackTableLoadMode(self, value):
        """Set the trackTableLoadMode"""
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
        """Returns the b1CapabilityState"""
        return self.component_manager.component_state.get(
            "b1capabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b2CapabilityState",
    )
    def b2CapabilityState(self):
        """Returns the b2CapabilityState"""
        return self.component_manager.component_state.get(
            "b2capabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b3CapabilityState",
    )
    def b3CapabilityState(self):
        """Returns the b3CapabilityState"""
        return self.component_manager.component_state.get(
            "b3capabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b4CapabilityState",
    )
    def b4CapabilityState(self):
        """Returns the b4CapabilityState"""
        return self.component_manager.component_state.get(
            "b4capabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b5aCapabilityState",
    )
    def b5aCapabilityState(self):
        """Returns the b5aCapabilityState"""
        return self.component_manager.component_state.get(
            "b5acapabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b5bCapabilityState",
    )
    def b5bCapabilityState(self):
        """Returns the b5aCapabilityState"""
        return self.component_manager.component_state.get(
            "b5bcapabilitystate", CapabilityStates.UNKNOWN
        )

    @attribute(
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        doc="Report the scanID for Scan",
    )
    def scanID(self):
        """Returns the scanID"""
        return self.component_manager.component_state.get("scanid", "")

    @scanID.write
    def scanID(self, scanid):
        """Sets the scanID"""
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
        """Returns ignoreSpf"""
        return self.component_manager.component_state.get("ignorespf", False)

    @ignoreSpf.write
    def ignoreSpf(self, value):
        """Sets ignoreSpf"""
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
        """Returns ignoreSpfrx"""
        return self.component_manager.component_state.get("ignorespfrx", False)

    @ignoreSpfrx.write
    def ignoreSpfrx(self, value):
        """Sets ignoreSpfrx"""
        self.logger.debug("Write to ignoreSpfrx, %s", value)
        self.component_manager.set_spfrx_device_ignored(value)

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
        dtype=(DevULong,),
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
        dtype=(DevULong,),
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
        dtype=str,
        access=AttrWriteType.READ,
        doc=(
            "Default empty string when not set, and is a JSON string"
            "of the last requested global pointing model when set."
        ),
    )
    def lastCommandedPointingParams(self) -> str:
        """
        Tango string attribute that returns the
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
        """Returns the DSC Power Limit (Kw)"""
        return self.component_manager.component_state.get(
            "dscpowerlimitkw", DSC_MIN_POWER_LIMIT_KW
        )

    @dscPowerLimitKw.write
    def dscPowerLimitKw(self, value):
        """Sets the DSC Power Limit (Kw)"""
        # pylint: disable=attribute-defined-outside-init
        if DSC_MIN_POWER_LIMIT_KW <= value <= DSC_MAX_POWER_LIMIT_KW:
            self.component_manager.set_dsc_power_limit_kw(value)
        else:
            raise ValueError(
                f"Invalid value, {value}, for DSC Power Limit (kW),"
                f" valid range is [{DSC_MIN_POWER_LIMIT_KW}, {DSC_MAX_POWER_LIMIT_KW}]."
            )

    # --------
    # Commands
    # --------

    @command(
        doc_in="Abort currently executing long running command on "
        "DishManager including stopping dish movement and transitioning "
        "dishMode to StandbyFP. For details consult DishManager documentation",
        display_level=DispLevel.OPERATOR,
        dtype_out="DevVarLongStringArray",
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def Abort(self) -> DevVarLongStringArrayType:
        """
        Empty out long running commands in queue.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        handler = self.get_command_object("Abort")
        (return_code, message) = handler()
        return ([return_code], [message])

    @command(
        doc_in="Abort currently executing long running command on "
        "DishManager including stopping dish movement and transitioning "
        "dishMode to StandbyFP. For details consult DishManager documentation",
        display_level=DispLevel.OPERATOR,
        dtype_out="DevVarLongStringArray",
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def AbortCommands(self) -> DevVarLongStringArrayType:
        """
        Empty out long running commands in queue.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        handler = self.get_command_object("AbortCommands")
        (return_code, message) = handler()
        return ([return_code], [message])

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def ConfigureBand1(self, synchronise) -> DevVarLongStringArrayType:
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 1. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("ConfigureBand1")

        result_code, unique_id = handler("1", synchronise)
        return ([result_code], [unique_id])

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def ConfigureBand2(self, synchronise) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 2. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("ConfigureBand2")

        result_code, unique_id = handler("2", synchronise)
        return ([result_code], [unique_id])

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def ConfigureBand3(self, synchronise):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 3. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        raise NotImplementedError

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def ConfigureBand4(self, synchronise):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 4. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        raise NotImplementedError

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False). "
        "Note when ignoring SPFRx, the configuredband on Dish.LMC will always report band B5a "
        "when the DS indexerposition is in B5.",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def ConfigureBand5a(self, synchronise):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 5a. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        raise NotImplementedError

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False). "
        "Note when ignoring SPFRx, the configuredband on Dish.LMC will always report band B5a "
        "when the DS indexerposition is in B5.",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def ConfigureBand5b(self, synchronise):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 5b. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        raise NotImplementedError

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def FlushCommandQueue(self):
        """Flushes the queue of time stamped commands."""
        raise NotImplementedError

    @command(dtype_in=str, dtype_out="DevVarLongStringArray", display_level=DispLevel.OPERATOR)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def Scan(self, scanid) -> DevVarLongStringArrayType:
        """
        The Dish records the scanID for an ongoing scan

        :param args: the scanID in string format
        """
        handler = self.get_command_object("Scan")
        result_code, unique_id = handler(scanid)

        return ([result_code], [unique_id])

    @command(dtype_in=None, dtype_out="DevVarLongStringArray", display_level=DispLevel.OPERATOR)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def EndScan(self) -> DevVarLongStringArrayType:
        """
        This command clears out the scan_id
        """
        handler = self.get_command_object("EndScan")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @record_mode_change_request
    def SetMaintenanceMode(self):
        """
        This command triggers the Dish to transition to the MAINTENANCE
        Dish Element Mode, and returns to the caller. To go into a state
        that is safe to approach the Dish by a maintainer, and to enable the
        Engineering interface to allow direct access to low level control and
        monitoring by engineers and maintainers. This mode will also enable
        engineers and maintainers to upgrade SW and FW. Dish also enters this
        mode when an emergency stop button is pressed.
        """
        raise NotImplementedError

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @record_mode_change_request
    def SetOperateMode(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

        This command triggers the Dish to transition to the OPERATE Dish
        Element Mode, and returns to the caller. This mode fulfils the main
        purpose of the Dish, which is to point to designated directions while
        capturing data and transmitting it to CSP. The Dish will automatically
        start capturing data after entering OPERATE mode.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("SetOperateMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @record_mode_change_request
    def SetStandbyLPMode(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

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

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @record_mode_change_request
    def SetStandbyFPMode(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

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

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    @record_mode_change_request
    def SetStowMode(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

        This command immediately triggers the Dish to transition to STOW Dish Element
        Mode. It subsequently aborts all queued LRC tasks and then returns to the caller.
        It points the dish in a direction that minimises the wind loads on the structure,
        for survival in strong wind conditions. The Dish is able to observe in the STOW
        position, for the purpose of transient detection.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("SetStowMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @command(
        dtype_in="DevVarFloatArray",
        doc_in="[0]: Azimuth\n[1]: Elevation",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def Slew(self, values):  # pylint: disable=unused-argument
        """
        Trigger the Dish to start moving to the commanded (Az,El) position.

        :param argin: the az, el for the pointing in stringified json format

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("Slew")
        result_code, unique_id = handler(values)

        return ([result_code], [unique_id])

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def Synchronise(self):
        """
        Reset configured band sample counters. Command only valid in
        SPFRx OPERATE mode.
        """
        raise NotImplementedError

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def Track(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

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

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def TrackStop(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

        When the TrackStop command Is received the Dish will stop tracking
        but will not apply brakes.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("TrackStop")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

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
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def TrackLoadStaticOff(self, values) -> DevVarLongStringArrayType:
        """
        Loads the given static pointing model offsets.

        :return: A tuple containing a return code and a string
            message indicating status.
        """

        handler = self.get_command_object("TrackLoadStaticOff")
        result_code, unique_id = handler(values)
        return ([result_code], [unique_id])

    @command(
        dtype_in="DevLong64",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def SetKValue(self, value) -> DevVarLongStringArrayType:
        """
        This command sets the kValue on SPFRx.
        Note that it will only take effect after
        SPFRx has been restarted.
        """
        handler = self.get_command_object("SetKValue")
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
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
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

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def StopCommunication(self):
        """Stop communicating with monitored devices"""
        self.component_manager.stop_communicating()

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def StartCommunication(self):
        """Start communicating with monitored devices"""
        self.component_manager.start_communicating()

    @command(
        dtype_in=None,
        dtype_out=str,
        display_level=DispLevel.OPERATOR,
        doc_out=("Retrieve the states of SPF, SPFRx" " and DS as DishManager sees it."),
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def GetComponentStates(self):
        """
        Get the current component states of subservient devices.

        Subservient devices constiture SPF, SPFRx and DS. Used for debugging.
        """
        component_states = {}
        for (
            device,
            component_state,
        ) in self.component_manager.sub_component_managers.items():
            component_states[device] = component_state._component_state
        component_states["DM"] = self.component_manager._component_state
        return json.dumps(str(component_states))

    @command(
        dtype_in=None,
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def SyncComponentStates(self) -> None:
        """
        Sync each subservient device component state with its tango device
        to refresh the dish manager component state.
        """
        if hasattr(self, "component_manager"):
            self.component_manager.sync_component_states()

    @command(dtype_out="DevVarLongStringArray")
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def On(self) -> DevVarLongStringArrayType:
        """The On command inherited from base classes."""
        raise NotImplementedError("DishManager does not implement the On command.")

    @command(dtype_out="DevVarLongStringArray")
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def Off(self) -> DevVarLongStringArrayType:
        """The Off command inherited from base classes."""
        raise NotImplementedError("DishManager does not implement the Off command.")

    @command(dtype_out="DevVarLongStringArray")
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def Standby(self) -> DevVarLongStringArrayType:
        """The Standby command inherited from base classes."""
        raise NotImplementedError("DishManager does not implement the Standby command.")

    @command(dtype_out="DevVarLongStringArray")
    @BaseInfoIt(show_args=True, show_kwargs=True, show_ret=True)
    def Reset(self) -> DevVarLongStringArrayType:
        """The Reset command inherited from base classes."""
        raise NotImplementedError("DishManager does not implement the Reset command.")


def main(args=None, **kwargs):
    """Launch a DishManager device."""
    return run((DishManager,), args=args, **kwargs)


if __name__ == "__main__":
    main()
