"""Component manager for a DishManager tango device."""

import json
import logging
import os
import threading
import time
from functools import partial
from threading import Event, Lock, Thread
from typing import Callable, Dict, List, Optional, Tuple

import tango
from ska_control_model import AdminMode, CommunicationStatus, HealthState, ResultCode, TaskStatus
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import (  # noqa: F401
    B5dcFrequency,
    B5dcPllState,
)
from ska_tango_base.executor import TaskExecutorComponentManager

from ska_mid_dish_manager.component_managers.b5dc_cm import B5DCComponentManager
from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.component_managers.spf_cm import SPFComponentManager
from ska_mid_dish_manager.component_managers.spfrx_cm import SPFRxComponentManager
from ska_mid_dish_manager.component_managers.wms_cm import WMSComponentManager
from ska_mid_dish_manager.models.command_handlers import Abort
from ska_mid_dish_manager.models.command_map import CommandMap
from ska_mid_dish_manager.models.constants import (
    BAND_POINTING_MODEL_PARAMS_LENGTH,
    DSC_MIN_POWER_LIMIT_KW,
    MEAN_WIND_SPEED_THRESHOLD_MPS,
    WIND_GUST_THRESHOLD_MPS,
)
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    CapabilityStates,
    DishDevice,
    DishMode,
    DscCmdAuthType,
    DscCtrlState,
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    NoiseDiodeMode,
    PointingState,
    PowerState,
    SPFCapabilityStates,
    SPFOperatingMode,
    SPFPowerState,
    SPFRxCapabilityStates,
    SPFRxOperatingMode,
    TrackInterpolationMode,
    TrackTableLoadMode,
)
from ska_mid_dish_manager.models.dish_mode_model import DishModeModel
from ska_mid_dish_manager.models.dish_state_transition import StateTransition
from ska_mid_dish_manager.models.is_allowed_rules import CommandAllowedChecks
from ska_mid_dish_manager.utils.decorators import check_communicating
from ska_mid_dish_manager.utils.schedulers import WatchdogTimer
from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_current_tai_timestamp_from_unix_time


class DishManagerComponentManager(TaskExecutorComponentManager):
    """A component manager for DishManager.

    It watches the component managers of the subservient devices
    (DS, SPF, SPFRX, WMS) to aggregate the state of Dish LMC.
    """

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker,
        build_state_callback,
        quality_state_callback,
        tango_device_name: str,
        ds_device_fqdn: str,
        spf_device_fqdn: str,
        spfrx_device_fqdn: str,
        b5dc_device_fqdn: str,
        *args,
        wms_device_names: Optional[List[str]] = [],
        wind_stow_callback: Optional[Callable] = None,
        **kwargs,
    ):
        # pylint: disable=useless-super-delegation
        self.tango_device_name = tango_device_name
        self.sub_component_managers = None
        wms_device_names = list(wms_device_names)
        default_watchdog_timeout = kwargs.pop("default_watchdog_timeout", 0.0)
        default_mean_wind_speed_threshold = kwargs.pop(
            "default_mean_wind_speed_threshold", MEAN_WIND_SPEED_THRESHOLD_MPS
        )
        default_wind_gust_threshold = kwargs.pop(
            "default_wind_gust_threshold", WIND_GUST_THRESHOLD_MPS
        )
        super().__init__(
            logger,
            *args,
            dishmode=DishMode.UNKNOWN,
            healthstate=HealthState.UNKNOWN,
            configuredband=Band.NONE,
            capturing=False,
            pointingstate=PointingState.UNKNOWN,
            b1capabilitystate=CapabilityStates.UNKNOWN,
            b2capabilitystate=CapabilityStates.UNKNOWN,
            b3capabilitystate=CapabilityStates.UNKNOWN,
            b4capabilitystate=CapabilityStates.UNKNOWN,
            b5acapabilitystate=CapabilityStates.UNKNOWN,
            b5bcapabilitystate=CapabilityStates.UNKNOWN,
            spfconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            spfrxconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            dsconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            wmsconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            b5dcconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            band0pointingmodelparams=[],
            band1pointingmodelparams=[],
            band2pointingmodelparams=[],
            band3pointingmodelparams=[],
            band4pointingmodelparams=[],
            band5apointingmodelparams=[],
            band5bpointingmodelparams=[],
            ignorespf=False,
            ignorespfrx=False,
            ignoreb5dc=False,
            noisediodemode=NoiseDiodeMode.OFF,
            periodicnoisediodepars=[],
            pseudorandomnoisediodepars=[0, 0, 0],
            actstaticoffsetvaluexel=0.0,
            actstaticoffsetvalueel=0.0,
            tracktablecurrentindex=0,
            tracktableendindex=0,
            achievedtargetlock=False,
            dsccmdauth=DscCmdAuthType.NO_AUTHORITY,
            desiredpointingaz=[0.0, 0.0],
            desiredpointingel=[0.0, 0.0],
            achievedpointing=[0.0, 0.0, 0.0],
            attenuationpolh=0.0,
            attenuationpolv=0.0,
            dscpowerlimitkw=DSC_MIN_POWER_LIMIT_KW,
            powerstate=PowerState.LOW,
            kvalue=0,
            scanid="",
            trackinterpolationmode=TrackInterpolationMode.SPLINE,
            lastwatchdogreset=0.0,
            watchdogtimeout=default_watchdog_timeout,
            autowindstowenabled=False,
            meanwindspeed=-1,
            windgust=-1,
            lastcommandedmode=("0.0", ""),
            dscctrlstate=DscCtrlState.NO_AUTHORITY,
            rfcmplllock=B5dcPllState.NOT_LOCKED,
            rfcmhattenuation=0.0,
            rfcmvattenuation=0.0,
            rftemperature=0.0,
            rfcmpsupcbtemperature=0.0,
            hpolrfpowerin=0.0,
            hpolrfpowerout=0.0,
            vpolrfpowerin=0.0,
            vpolrfpowerout=0.0,
            rfcmfrequency=0.0,
            **kwargs,
        )
        self.logger = logger
        self._build_state_callback = build_state_callback
        self._quality_state_callback = quality_state_callback
        self._wind_stow_callback = wind_stow_callback
        self._dish_mode_model = DishModeModel()
        self._state_transition = StateTransition()
        self._command_tracker = command_tracker
        self._state_update_lock = Lock()
        self._abort_thread: Optional[Thread] = None
        self._stop_event = threading.Event()
        self.watchdog_timer = WatchdogTimer(
            callback_on_timeout=self._stow_on_watchdog_expiry,
        )
        self._wind_stow_active = False
        self._reset_alarm = False
        self._wind_limits = {
            "WindGustThreshold": default_wind_gust_threshold,
            "MeanWindSpeedThreshold": default_mean_wind_speed_threshold,
        }

        # SPF has to go first
        self.sub_component_managers = {
            "SPF": SPFComponentManager(
                spf_device_fqdn,
                logger,
                self._state_update_lock,
                operatingmode=SPFOperatingMode.UNKNOWN,
                powerstate=SPFPowerState.UNKNOWN,
                healthstate=HealthState.UNKNOWN,
                bandinfocus=BandInFocus.UNKNOWN,
                b1capabilitystate=SPFCapabilityStates.UNAVAILABLE,
                b2capabilitystate=SPFCapabilityStates.UNAVAILABLE,
                b3capabilitystate=SPFCapabilityStates.UNAVAILABLE,
                b4capabilitystate=SPFCapabilityStates.UNAVAILABLE,
                b5acapabilitystate=SPFCapabilityStates.UNAVAILABLE,
                b5bcapabilitystate=SPFCapabilityStates.UNAVAILABLE,
                communication_state_callback=partial(
                    self._sub_device_communication_state_changed, DishDevice.SPF
                ),
                component_state_callback=partial(
                    self._sub_device_component_state_changed, DishDevice.SPF
                ),
                quality_state_callback=self._quality_state_callback,
            ),
            "DS": DSComponentManager(
                ds_device_fqdn,
                logger,
                self._state_update_lock,
                healthstate=HealthState.UNKNOWN,
                operatingmode=DSOperatingMode.UNKNOWN,
                pointingstate=PointingState.UNKNOWN,
                achievedtargetlock=None,
                dsccmdauth=DscCmdAuthType.NO_AUTHORITY,
                configuretargetlock=None,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.UNKNOWN,
                desiredpointingaz=[0.0, 0.0],
                desiredpointingel=[0.0, 0.0],
                achievedpointing=[0.0, 0.0, 0.0],
                band0pointingmodelparams=[],
                band1pointingmodelparams=[],
                band2pointingmodelparams=[],
                band3pointingmodelparams=[],
                band4pointingmodelparams=[],
                band5apointingmodelparams=[],
                band5bpointingmodelparams=[],
                dscpowerlimitkw=DSC_MIN_POWER_LIMIT_KW,
                trackinterpolationmode=TrackInterpolationMode.SPLINE,
                actstaticoffsetvaluexel=None,
                actstaticoffsetvalueel=None,
                tracktablecurrentindex=0,
                tracktableendindex=0,
                dscctrlstate=DscCtrlState.NO_AUTHORITY,
                communication_state_callback=partial(
                    self._sub_device_communication_state_changed, DishDevice.DS
                ),
                component_state_callback=partial(
                    self._sub_device_component_state_changed, DishDevice.DS
                ),
                quality_state_callback=self._quality_state_callback,
            ),
            "SPFRX": SPFRxComponentManager(
                spfrx_device_fqdn,
                logger,
                self._state_update_lock,
                operatingmode=SPFRxOperatingMode.UNKNOWN,
                configuredband=Band.NONE,
                capturingdata=False,
                healthstate=HealthState.UNKNOWN,
                attenuationpolh=0.0,
                attenuationpolv=0.0,
                kvalue=0,
                b1capabilitystate=SPFRxCapabilityStates.UNKNOWN,
                b2capabilitystate=SPFRxCapabilityStates.UNKNOWN,
                b3capabilitystate=SPFRxCapabilityStates.UNKNOWN,
                b4capabilitystate=SPFRxCapabilityStates.UNKNOWN,
                b5acapabilitystate=SPFRxCapabilityStates.UNKNOWN,
                b5bcapabilitystate=SPFRxCapabilityStates.UNKNOWN,
                noisediodemode=NoiseDiodeMode.OFF,
                periodicnoisediodepars=[0, 0, 0],
                pseudorandomnoisediodepars=[0, 0, 0],
                adminmode=AdminMode.OFFLINE,
                communication_state_callback=partial(
                    self._sub_device_communication_state_changed, DishDevice.SPFRX
                ),
                component_state_callback=partial(
                    self._sub_device_component_state_changed, DishDevice.SPFRX
                ),
                quality_state_callback=self._quality_state_callback,
            ),
            "WMS": WMSComponentManager(
                wms_device_names,
                logger=logger,
                component_state_callback=self._evaluate_wind_speed_averages,
                communication_state_callback=partial(
                    self._update_connection_state_attribute, DishDevice.WMS
                ),
                state_update_lock=self._state_update_lock,
                meanwindspeed=-1,
                windgust=-1,
            ),
            "B5DC": B5DCComponentManager(
                b5dc_device_fqdn,
                logger=logger,
                state_update_lock=self._state_update_lock,
                communication_state_callback=partial(
                    self._sub_device_communication_state_changed, DishDevice.B5DC
                ),
                component_state_callback=partial(
                    self._sub_device_component_state_changed, DishDevice.B5DC
                ),
                rfcmHAttenuation=0.0,
                rfcmVAttenuation=0.0,
                rfcmPllLock=B5dcPllState.NOT_LOCKED,
                rfTemperature=0.0,
                rfcmPsuPcbTemperature=0.0,
                hPolRfPowerIn=0.0,
                hPolRfPowerOut=0.0,
                vPolRfPowerIn=0.0,
                vPolRfPowerOut=0.0,
                rfcmFrequency=0.0,
            ),
        }

        self._command_map = CommandMap(
            self,
            self._command_tracker,
            self.logger,
        )
        self._cmd_allowed_checks = CommandAllowedChecks(self)

        self.direct_mapped_attrs = {
            "DS": [
                "achievedPointing",
                "desiredPointingAz",
                "desiredPointingEl",
                "achievedTargetLock",
                "dscCmdAuth",
                "trackInterpolationMode",
                "actStaticOffsetValueXel",
                "actStaticOffsetValueEl",
                "trackTableCurrentIndex",
                "trackTableEndIndex",
                "dscCtrlState",
            ],
            "SPFRX": [
                "noiseDiodeMode",
                "periodicNoiseDiodePars",
                "pseudoRandomNoiseDiodePars",
            ],
            "B5DC": [
                "rfcmPllLock",
                "rfcmHAttenuation",
                "rfcmVAttenuation",
                "clkPhotodiodeCurrent",
                "rfcmFrequency",
                "rfTemperature",
                "rfcmPsuPcbTemperature",
                "hPolRfPowerIn",
                "hPolRfPowerOut",
                "vPolRfPowerIn",
                "vPolRfPowerOut",
            ],
        }

        # ----------------
        # Command Handlers
        # ----------------
        self._abort_handler = Abort(self, self._command_map, self._command_tracker, logger=logger)

    @property
    def wind_stow_active(self) -> bool:
        """Indicates whether the dish has been automatically stowed due to strong winds."""
        return self._wind_stow_active

    @wind_stow_active.setter
    def wind_stow_active(self, value):
        """Sets the wind stow active state.

        When True, it means the dish is stowed due to strong wind and prevents repeated stow
        commands while wind remains high. The device sets it back to False after the wind
        alarm is cleared.
        """
        self._wind_stow_active = value

    @property
    def reset_alarm(self) -> bool:
        """Indicates whether the wind stow alarm can be cleared."""
        return self._reset_alarm

    @reset_alarm.setter
    def reset_alarm(self, value):
        """Sets the flag to indicate whether the wind stow alarm can be cleared.

        This should be set to True only after wind speeds have dropped back to safe levels.
        """
        self._reset_alarm = value

    # --------------
    # Helper methods
    # --------------
    def get_current_tai_offset_from_dsc_with_manual_fallback(self) -> float:
        """Try and get the TAI offset from the DSManager device.
        Or calulate it manually if that fails.
        """
        try:
            ds_cm = self.sub_component_managers["DS"]
            return ds_cm.execute_command("GetCurrentTAIOffset", None)
        except (tango.DevFailed, ConnectionError, KeyError):
            self.logger.debug("Calculating TAI offset manually.")
            return get_current_tai_timestamp_from_unix_time()

    def is_dish_moving(self) -> bool:
        """Report whether or not the dish is moving.

        :returns: boolean dish movement activity
        """
        pointing_state = self.component_state.get("pointingstate")
        if pointing_state in [PointingState.SLEW, PointingState.TRACK]:
            return True
        return False

    def get_currently_executing_lrcs(
        self,
        statuses_to_check: Tuple[TaskStatus] = (
            TaskStatus.STAGING,
            TaskStatus.QUEUED,
            TaskStatus.IN_PROGRESS,
        ),
    ) -> List[str]:
        """Report command ids that are running or waiting to be executed from the task executor.

        :param statuses_to_check: TaskStatuses which count as lrc is executing
        :returns: a list of all lrcs currently executing or queued
        """
        command_idx = 0
        status_idx = 1
        cmd_ids = []

        command_statuses = self._command_tracker.command_statuses
        filtered_command_statuses = [
            cmd_status
            for cmd_status in command_statuses
            if cmd_status[status_idx] in statuses_to_check
        ]

        if filtered_command_statuses:
            cmd_ids = [cmd_status[command_idx] for cmd_status in filtered_command_statuses]
            return cmd_ids
        # there are no commands in statuses_to_check
        return cmd_ids

    def is_device_ignored(self, device: str):
        """Check whether the given device is ignored."""
        if device == "SPF":
            return self.component_state["ignorespf"]
        if device == "SPFRX":
            return self.component_state["ignorespfrx"]
        if device == "B5DC":
            return self.component_state["ignoreb5dc"]
        return False

    def get_active_sub_component_managers(self) -> Dict:
        """Get a list of subservient device component managers which are not being ignored."""
        active_component_managers = {"DS": self.sub_component_managers["DS"]}

        if not self.is_device_ignored("SPF"):
            active_component_managers["SPF"] = self.sub_component_managers["SPF"]

        if not self.is_device_ignored("SPFRX"):
            active_component_managers["SPFRX"] = self.sub_component_managers["SPFRX"]

        return active_component_managers

    def _get_device_attribute_property_value(self, attribute_name) -> Optional[str]:
        """Read memorized attributes values from TangoDB.

        :param: attribute_name: Tango attribute name
        :type attribute_name: str
        :return: value for the given attribute
        :rtype: Optional[str]
        """
        self.logger.debug("Getting attribute property value for %s.", attribute_name)
        database = tango.Database()
        attr_property = database.get_device_attribute_property(
            self.tango_device_name, attribute_name
        )
        attr_property_value = attr_property[attribute_name]
        if len(attr_property_value) > 0:  # If the returned dict is not empty
            return attr_property_value["__value"][0]
        return None

    def try_update_memorized_attributes_from_db(self):
        """Read memorized attributes values from TangoDB and update device attributes."""
        if "TANGO_HOST" not in os.environ:
            self.logger.debug("Not updating memorized attributes. TANGO_HOST is not set.")
            return

        self.logger.debug("Updating memorized attributes. Trying to read from database.")
        try:
            # ignoreSpf
            ignore_spf_value = self._get_device_attribute_property_value("ignoreSpf")

            if ignore_spf_value is not None:
                self.logger.debug(
                    "Updating ignoreSpf value with value from database %s.",
                    ignore_spf_value,
                )
                ignore_spf = ignore_spf_value.lower() == "true"
                self.set_spf_device_ignored(ignore_spf)

            # ignoreSpfrx
            ignore_spfrx_value = self._get_device_attribute_property_value("ignoreSpfrx")

            if ignore_spfrx_value is not None:
                self.logger.debug(
                    "Updating ignoreSpfrx value with value from database %s.",
                    ignore_spfrx_value,
                )
                ignore_spfrx = ignore_spfrx_value.lower() == "true"
                self.set_spfrx_device_ignored(ignore_spfrx)

            # ignoreB5dc
            ignore_b5dc_value = self._get_device_attribute_property_value("ignoreB5dc")

            if ignore_b5dc_value is not None:
                self.logger.debug(
                    "Updating ignoreB5dc value with value from database %s.",
                    ignore_b5dc_value,
                )
                ignore_b5dc = ignore_b5dc_value.lower() == "true"
                self.set_b5dc_device_ignored(ignore_b5dc)
        except tango.DevFailed:
            self.logger.debug(
                "Could not update memorized attributes. Failed to connect to database."
            )

    def _execute_stow_command(self, trigger_source: str) -> None:
        """Handle automatic stow command execution.

        :param: trigger_source: The event requesting the dish to stow.
                 It can be due to either a wind condition or communication loss from client.
        """
        if self.component_state["dishmode"] == DishMode.STOW:
            # remove any queued tasks on the task executor
            self.abort_commands()
            self.logger.info(f"{trigger_source}: Dish is already in STOW mode, no action taken.")
            return

        retry_interval = 0.1
        self.logger.info(f"{trigger_source} transitioning dish to STOW.")

        while not self._stop_event.is_set():
            wind_stow_id = self._command_tracker.new_command(
                f"{trigger_source}", completed_callback=None
            )
            wind_stow_task_cb = partial(self._command_tracker.update_command_info, wind_stow_id)
            task_status, _ = self.set_stow_mode(wind_stow_task_cb)

            if task_status == TaskStatus.COMPLETED:
                break
            self._stop_event.wait(retry_interval)

        last_commanded_mode = (str(time.time()), trigger_source)
        self._update_component_state(lastcommandedmode=last_commanded_mode)

    # ---------
    # Callbacks
    # ---------

    def _update_connection_state_attribute(
        self, device: str, connection_state: CommunicationStatus
    ):
        state_name = f"{device.lower()}connectionstate"
        self._update_component_state(**{state_name: connection_state})

    def _evaluate_wind_speed_averages(self, **computed_averages):
        """Evaluate wind speed averages and trigger auto stow if necessary."""
        auto_wind_stow_enabled = self.component_state.get("autowindstowenabled")

        if auto_wind_stow_enabled:
            # determine if any computed average exceeds its configured threshold
            mean_wind_speed = computed_averages.get("meanwindspeed", -1)
            mean_threshold = self._wind_limits.get("MeanWindSpeedThreshold")
            mean_wind_speed_exceeded = mean_wind_speed > mean_threshold

            wind_gust = computed_averages.get("windgust", -1)
            gust_threshold = self._wind_limits.get("WindGustThreshold")
            wind_gust_exceeded = wind_gust > gust_threshold

            if mean_wind_speed_exceeded or wind_gust_exceeded:
                # trigger stow only once over the duration of an extreme condition
                if not self.wind_stow_active:
                    self._execute_stow_command("WindStow")
                self.wind_stow_active = True
                self.reset_alarm = False
            else:
                self.reset_alarm = True

            if self._wind_stow_callback is not None:
                self._wind_stow_callback(**computed_averages)

        # update the attributes with the computed averages
        self._update_component_state(**computed_averages)

    def _sub_device_communication_state_changed(
        self, device: DishDevice, communication_state: CommunicationStatus
    ):
        """Callback triggered by the component manager when it establishes
        a connection with the underlying (subservient) device.

        Note: This callback is triggered by the component manangers of
        the subservient devices. DishManager reflects this in its connection
        status attributes.
        """
        self.logger.debug(
            "Communication state changed on %s device: %s.", device.name, communication_state
        )

        # report the communication state of the sub device on the connectionState attribute
        self._update_connection_state_attribute(device.name, communication_state)

        active_sub_component_managers = self.get_active_sub_component_managers()
        sub_devices_communication_states = [
            sub_component_manager.communication_state
            for sub_component_manager in active_sub_component_managers.values()
        ]

        if all(
            communication_state == CommunicationStatus.ESTABLISHED
            for communication_state in sub_devices_communication_states
        ):
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
        elif any(
            communication_state == CommunicationStatus.NOT_ESTABLISHED
            for communication_state in sub_devices_communication_states
        ):
            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        else:
            self._update_communication_state(CommunicationStatus.DISABLED)

    # pylint: disable=unused-argument, too-many-branches, too-many-locals, too-many-statements
    def _sub_device_component_state_changed(self, device: DishDevice, *args, **kwargs):
        """Callback triggered by the component manager of the
        subservient device for component state changes.

        This aggregates the component values and computes the final value
        which will be reported for the respective attribute. The computed
        value is sent to DishManager's component_state callback which pushes
        a change event on the attribute and updates the internal variable.

        Note: This callback is triggered by the component managers of
        the subservient devices only. DishManager also has its own callback.
        """
        ds_component_state = self.sub_component_managers["DS"].component_state
        spf_component_state = self.sub_component_managers["SPF"].component_state
        spfrx_component_state = self.sub_component_managers["SPFRX"].component_state

        # Only log non pointing changes
        pointing_related_attrs = set(
            [
                "desiredpointingaz",
                "desiredpointingel",
                "achievedpointing",
                "tracktablecurrentindex",
                "tracktableendindex",
            ]
        )
        no_pointing_updates = set()
        if pointing_related_attrs.intersection(kwargs) == no_pointing_updates:
            self.logger.debug(
                "%s component state has changed \nnew value: [%s]"
                "\ncurrent dish manager component state: [%s]",
                device.value,
                kwargs,
                self.component_state,
            )

        if "powerstate" in kwargs:
            new_power_state = self._state_transition.compute_power_state(
                ds_component_state,
                spf_component_state if not self.is_device_ignored("SPF") else None,
            )
            self.logger.debug(
                (
                    "Updating dish manager powerState with: [%s]. "
                    "Sub-components powerState DS [%s], SPF [%s]"
                ),
                new_power_state,
                ds_component_state["powerstate"],
                spf_component_state["powerstate"],
            )
            self._update_component_state(powerstate=new_power_state)

        if "buildstate" in kwargs:
            self._build_state_callback(device, kwargs["buildstate"])

        previous_dish_mode = self.component_state["dishmode"]
        # Update dishMode if there are operatingmode, indexerposition or adminmode changes
        if "operatingmode" in kwargs or "indexerposition" in kwargs or "adminmode" in kwargs:
            new_dish_mode = self._state_transition.compute_dish_mode(
                ds_component_state,
                spfrx_component_state if not self.is_device_ignored("SPFRX") else None,
                spf_component_state if not self.is_device_ignored("SPF") else None,
            )

            # If the dish is transitioning out of STOW mode, reenable the watchdog timer if
            # the watchdog timeout is set
            if previous_dish_mode == DishMode.STOW and new_dish_mode != DishMode.STOW:
                self._reenable_watchdog_timer()

            self.logger.debug(
                (
                    "Updating dish manager dishMode with: [%s]. "
                    "Sub-components operatingMode DS [%s], SPF [%s], SPFRX [%s], "
                    "SPFRX adminMode [%s]."
                ),
                new_dish_mode,
                ds_component_state["operatingmode"],
                spf_component_state["operatingmode"],
                spfrx_component_state["operatingmode"],
                spfrx_component_state["adminmode"],
            )
            self._update_component_state(dishmode=new_dish_mode)

        if "healthstate" in kwargs:
            new_health_state = self._state_transition.compute_dish_health_state(
                ds_component_state,
                spfrx_component_state if not self.is_device_ignored("SPFRX") else None,
                spf_component_state if not self.is_device_ignored("SPF") else None,
            )
            self.logger.debug(
                (
                    "Updating dish manager healthState with: [%s]. "
                    "Sub-components healthState DS [%s], SPF [%s], SPFRX [%s]"
                ),
                new_health_state,
                ds_component_state["healthstate"],
                spf_component_state["healthstate"],
                spfrx_component_state["healthstate"],
            )
            self._update_component_state(healthstate=new_health_state)

        if "pointingstate" in kwargs:
            pointing_state = ds_component_state["pointingstate"]
            self.logger.debug(
                (
                    "Updating dish manager pointingState with: [%s]. "
                    "Sub-components pointingState DS [%s]"
                ),
                pointing_state,
                pointing_state,
            )
            self._update_component_state(pointingstate=ds_component_state["pointingstate"])

        if "dscpowerlimitkw" in kwargs:
            dsc_power_limit = ds_component_state["dscpowerlimitkw"]
            self.logger.debug(
                (
                    "Updating dish manager dscPowerLimitKw with: [%s]. "
                    "Sub-component dscPowerLimitKw DS [%s]"
                ),
                dsc_power_limit,
                dsc_power_limit,
            )
            self._update_component_state(dscpowerlimitkw=ds_component_state["dscpowerlimitkw"])

        if "dscctrlstate" in kwargs:
            dsc_ctrl_state = ds_component_state["dscctrlstate"]
            self.logger.debug(
                (
                    "Updating dish manager dscCtrlState with: [%s]. "
                    "Sub-component dscCtrlState DS [%s]"
                ),
                dsc_ctrl_state,
                dsc_ctrl_state,
            )
            self._update_component_state(dscctrlstate=ds_component_state["dscctrlstate"])

        # spf bandInFocus
        if not self.is_device_ignored("SPF") and (
            "indexerposition" in kwargs or "configuredband" in kwargs
        ):
            band_in_focus = self._state_transition.compute_spf_band_in_focus(
                ds_component_state,
                spfrx_component_state if not self.is_device_ignored("SPFRX") else None,
            )
            self.logger.debug("Setting bandInFocus to %s on SPF", band_in_focus)
            # update the bandInFocus of SPF before configuredBand
            spf_component_manager = self.sub_component_managers["SPF"]
            try:
                spf_component_manager.write_attribute_value("bandInFocus", band_in_focus)
            except tango.DevFailed:
                # this will impact configuredBand calculation on dish manager
                self.logger.warning(
                    "Encountered an error writing bandInFocus %s on SPF", band_in_focus
                )
            else:
                spf_component_state["bandinfocus"] = band_in_focus

        # spfrx attenuation
        if "attenuationpolv" in kwargs or "attenuationpolh" in kwargs:
            attenuation = {
                "attenuationpolv": spfrx_component_state["attenuationpolv"],
                "attenuationpolh": spfrx_component_state["attenuationpolh"],
            }
            self.logger.debug(
                (
                    "Updating dish manager attenuationpolv and attenuationpolh "
                    "with: SPFRX attenuation [%s]"
                ),
                attenuation,
            )
            self._update_component_state(**attenuation)

        # kvalue
        if "kvalue" in kwargs:
            k_value = spfrx_component_state["kvalue"]
            self.logger.debug(
                ("Updating dish manager kvalue with: SPFRX kValue [%s]"),
                k_value,
            )
            self._update_component_state(kvalue=k_value)

        # configuredBand
        if "indexerposition" in kwargs or "bandinfocus" in kwargs or "configuredband" in kwargs:
            configured_band = self._state_transition.compute_configured_band(
                ds_component_state,
                spfrx_component_state if not self.is_device_ignored("SPFRX") else None,
                spf_component_state if not self.is_device_ignored("SPF") else None,
            )
            self.logger.debug(
                (
                    "Updating dish manager configuredBand with: [%s]. "
                    "Sub-component bands DS [%s] SPF [%s] SPFRX [%s]"
                ),
                configured_band,
                ds_component_state["indexerposition"],
                spf_component_state["bandinfocus"],
                spfrx_component_state["configuredband"],
            )
            self._update_component_state(configuredband=configured_band)

        # update capturing attribute when SPFRx captures data
        if "capturingdata" in kwargs:
            capturing_data = spfrx_component_state["capturingdata"]
            self.logger.debug(
                ("Updating dish manager capturing with: SPFRx [%s]"),
                capturing_data,
            )
            self._update_component_state(capturing=capturing_data)

        # CapabilityStates
        # Update all CapabilityStates when indexerposition, dish_mode or operatingmode changes
        if "indexerposition" in kwargs or "dish_mode" in kwargs or "operatingmode" in kwargs:
            cap_state_updates = {}
            for band in ["b1", "b2", "b3", "b4", "b5a", "b5b"]:
                cap_state_name = f"{band}capabilitystate"
                new_state = self._state_transition.compute_capability_state(
                    band,
                    ds_component_state,
                    self.component_state,
                    spfrx_component_state if not self.is_device_ignored("SPFRX") else None,
                    spf_component_state if not self.is_device_ignored("SPF") else None,
                )
                cap_state_updates[cap_state_name] = new_state
            self.logger.debug(
                "Updating dish manager capability states for %s with: [%s]",
                list(cap_state_updates.keys()),
                cap_state_updates,
            )
            self._update_component_state(**cap_state_updates)

        # Update individual CapabilityStates if it changes
        # b5 for SPF
        for band in ["b1", "b2", "b3", "b4", "b5a", "b5b"]:
            cap_state_name = f"{band}capabilitystate"
            if cap_state_name in kwargs:
                new_state = self._state_transition.compute_capability_state(
                    band,
                    ds_component_state,
                    self.component_state,
                    spfrx_component_state if not self.is_device_ignored("SPFRX") else None,
                    spf_component_state if not self.is_device_ignored("SPF") else None,
                )
                self.logger.debug(
                    "Updating dish manager %s with: [%s]",
                    cap_state_name,
                    new_state,
                )
                self._update_component_state(**{cap_state_name: new_state})

        # Update the pointing model params if they change
        for band in ["0", "1", "2", "3", "4", "5a", "5b"]:
            pointing_param_name = f"band{band}pointingmodelparams"

            if pointing_param_name in kwargs:
                self.logger.debug(
                    ("Updating dish manager %s with: DS %s [%s]"),
                    pointing_param_name,
                    pointing_param_name,
                    ds_component_state[pointing_param_name],
                )
                self._update_component_state(
                    **{pointing_param_name: ds_component_state[pointing_param_name]}
                )

        # Update attributes that are mapped directly from subservient devices
        if device == "SPF":
            # there's no SPF in the mapped dict
            return
        attrs = self.direct_mapped_attrs[device]
        cm_state = self.sub_component_managers[device.value].component_state

        enum_attr_mapping = {
            "trackInterpolationMode": TrackInterpolationMode,
            "noiseDiodeMode": NoiseDiodeMode,
        }
        for attr in attrs:
            attr_lower = attr.lower()

            if attr_lower in kwargs:
                new_value = None
                new_value = cm_state[attr_lower]
                mapped_enum = enum_attr_mapping.get(attr)
                new_value = mapped_enum(new_value) if mapped_enum is not None else new_value
                if attr_lower not in pointing_related_attrs:
                    self.logger.debug(
                        ("Updating dish manager %s with: %s %s [%s]"),
                        attr,
                        device,
                        attr,
                        new_value,
                    )

                self._update_component_state(**{attr_lower: new_value})

    # ----------------------------------------
    # Command object/ attribute write handlers
    # ----------------------------------------

    def start_communicating(self):
        """Connect to monitored devices and start watchdog timer."""
        self._stop_event.clear()
        # Enable the watchdog timer if configured
        if self.component_state["watchdogtimeout"] > 0:
            self.watchdog_timer.enable(timeout=self.component_state["watchdogtimeout"])

        if self.sub_component_managers:
            for device_name, component_manager in self.sub_component_managers.items():
                if not self.is_device_ignored(device_name):
                    component_manager.start_communicating()

    def stop_communicating(self):
        """Disconnect from monitored devices and stop watchdog timer."""
        # Disable watchdog timer
        self.logger.debug("Disabling the watchdog timer.")
        self.watchdog_timer.disable()
        self._update_component_state(watchdogtimeout=0.0)

        # TODO: update attribute read callbacks to indicate attribute
        # reads cannot be trusted after communication is stopped
        self._stop_event.set()
        if self.sub_component_managers:
            for component_manager in self.sub_component_managers.values():
                component_manager.stop_communicating()

    def set_spf_device_ignored(self, ignored: bool):
        """Set the SPF device ignored boolean and update device communication."""
        if ignored != self.component_state["ignorespf"]:
            self.logger.debug("Setting ignore SPF device as %s", ignored)
            self._update_component_state(ignorespf=ignored)
            if ignored:
                if "SPF" in self.sub_component_managers:
                    self.sub_component_managers["SPF"].stop_communicating()
                    self.sub_component_managers["SPF"].clear_monitored_attributes()
            else:
                self.sub_component_managers["SPF"].start_communicating()

    def set_spfrx_device_ignored(self, ignored: bool):
        """Set the SPFRxdevice ignored boolean and update device communication."""
        if ignored != self.component_state["ignorespfrx"]:
            self.logger.debug("Setting ignore SPFRx device as %s", ignored)
            self._update_component_state(ignorespfrx=ignored)
            if ignored:
                if "SPFRX" in self.sub_component_managers:
                    self.sub_component_managers["SPFRX"].stop_communicating()
                    self.sub_component_managers["SPFRX"].clear_monitored_attributes()
            else:
                self.sub_component_managers["SPFRX"].start_communicating()

            self._update_component_state(ignorespfrx=ignored)

    def set_b5dc_device_ignored(self, ignored: bool):
        """Set the B5DC device ignored boolean and update device communication."""
        if ignored != self.component_state["ignoreb5dc"]:
            self.logger.debug("Setting ignore B5DC device as %s", ignored)
            self._update_component_state(ignoreb5dc=ignored)
            if ignored:
                if "B5DC" in self.sub_component_managers:
                    self.sub_component_managers["B5DC"].stop_communicating()
                    self.sub_component_managers["B5DC"].clear_monitored_attributes()
            else:
                self.sub_component_managers["B5DC"].start_communicating()

            self._update_component_state(ignoreb5dc=ignored)

    def sync_component_states(self):
        """Sync monitored attributes on component managers with their respective sub devices.

        Clear the monitored attributes of all subservient device component managers,
        then re-read all the monitored attributes from their respective tango device
        to force dishManager to recalculate its attributes.
        """
        self.logger.debug("Syncing component states")
        if self.sub_component_managers:
            for device, component_manager in self.sub_component_managers.items():
                if not self.is_device_ignored(device) and device != "WMS":
                    component_manager.clear_monitored_attributes()
                    component_manager.update_state_from_monitored_attributes()

    def update_pointing_model_params(self, attr: str, values: list[float]) -> None:
        """Update band pointing model parameters for the given attribute."""
        try:
            if len(values) != BAND_POINTING_MODEL_PARAMS_LENGTH:
                raise ValueError(
                    f"Expected {BAND_POINTING_MODEL_PARAMS_LENGTH} arguments but got"
                    f" {len(values)} arg(s)."
                )
            ds_com_man = self.sub_component_managers["DS"]
            ds_com_man.write_attribute_value(attr, values)
        except tango.DevFailed:
            self.logger.exception("Failed to write to %s on DSManager", attr)
            raise
        except ValueError:
            self.logger.exception("Failed to update %s", attr)
            raise

    def abort_commands(self, task_callback: Optional[Callable] = None) -> None:
        """Abort commands on dish manager and its subservient devices.

        :param task_callback: callback when the status changes
        """
        self.logger.debug("Aborting long running commands")
        super().abort_commands(task_callback)
        sub_component_mgrs = self.get_active_sub_component_managers()
        for component_mgr in sub_component_mgrs.values():
            # dont use the same taskcallback else we get completed 4x on the same command id
            component_mgr.abort_commands()

    def track_load_table(
        self, sequence_length: int, table: list[float], load_mode: TrackTableLoadMode
    ) -> Tuple[ResultCode, str]:
        """Load the track table."""
        float_list = [load_mode, sequence_length]
        float_list.extend(table)
        ds_cm = self.sub_component_managers["DS"]
        result_code = ResultCode.UNKNOWN
        result_message = ""
        try:
            [[result_code], [result_message]] = ds_cm.execute_command("TrackLoadTable", float_list)
        except tango.DevFailed as err:
            self.logger.exception("TrackLoadTable on DSManager failed")
            result_code = ResultCode.FAILED
            result_message = str(err)
        return (result_code, result_message)

    @check_communicating
    def set_standby_lp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_LP mode."""
        _is_set_standby_lp_allowed = partial(
            self._dish_mode_model.is_command_allowed,
            "SetStandbyLPMode",
            component_manager=self,
            task_callback=task_callback,
        )

        status, response = self.submit_task(
            self._command_map.set_standby_lp_mode,
            args=[],
            is_cmd_allowed=_is_set_standby_lp_allowed,
            task_callback=task_callback,
        )
        return status, response

    @check_communicating
    def set_standby_fp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_FP mode."""
        _is_set_standby_fp_allowed = partial(
            self._dish_mode_model.is_command_allowed,
            "SetStandbyFPMode",
            component_manager=self,
            task_callback=task_callback,
        )

        status, response = self.submit_task(
            self._command_map.set_standby_fp_mode,
            args=[],
            is_cmd_allowed=_is_set_standby_fp_allowed,
            task_callback=task_callback,
        )
        return status, response

    @check_communicating
    def set_operate_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to OPERATE mode."""
        _is_set_operate_mode_allowed = partial(
            self._dish_mode_model.is_command_allowed,
            "SetOperateMode",
            component_manager=self,
            task_callback=task_callback,
        )
        status, response = self.submit_task(
            self._command_map.set_operate_mode,
            args=[],
            is_cmd_allowed=_is_set_operate_mode_allowed,
            task_callback=task_callback,
        )
        return status, response

    @check_communicating
    def set_maintenance_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to MAINTENANCE mode."""
        _is_set_maintenance_mode_allowed = partial(
            self._dish_mode_model.is_command_allowed,
            "SetMaintenanceMode",
            component_manager=self,
            task_callback=task_callback,
        )

        status, response = self.submit_task(
            self._command_map.set_maintenance_mode,
            args=[],
            is_cmd_allowed=_is_set_maintenance_mode_allowed,
            task_callback=task_callback,
        )
        return status, response

    @check_communicating
    def track_cmd(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Track the commanded pointing position."""

        def _is_track_cmd_allowed():
            if self.component_state["dishmode"] != DishMode.OPERATE:
                task_callback(
                    progress="Track command rejected for current dishMode. "
                    "Track command is allowed for dishMode OPERATE"
                )
                return False
            if self.component_state["pointingstate"] != PointingState.READY:
                task_callback(
                    progress="Track command rejected for current pointingState. "
                    "Track command is allowed for pointingState READY"
                )
                return False
            return True

        status, response = self.submit_task(
            self._command_map.track_cmd,
            args=[],
            is_cmd_allowed=_is_track_cmd_allowed,
            task_callback=task_callback,
        )
        return status, response

    @check_communicating
    def track_stop_cmd(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Stop tracking."""

        def _is_track_stop_cmd_allowed():
            dish_mode = self.component_state["dishmode"]
            pointing_state = self.component_state["pointingstate"]
            if dish_mode != DishMode.OPERATE and pointing_state not in [
                PointingState.TRACK,
                PointingState.SLEW,
            ]:
                return False
            return True

        status, response = self.submit_task(
            self._command_map.track_stop_cmd,
            args=[],
            is_cmd_allowed=_is_track_stop_cmd_allowed,
            task_callback=task_callback,
        )
        return status, response

    @check_communicating
    def configure_band_cmd(
        self,
        band_number,
        synchronise,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Configure frequency band."""
        req_cmd = f"ConfigureBand{band_number}"

        _is_configure_band_cmd_allowed = partial(
            self._dish_mode_model.is_command_allowed,
            req_cmd,
            component_manager=self,
            task_callback=task_callback,
        )

        status, response = self.submit_task(
            self._command_map.configure_band_cmd,
            args=[band_number, synchronise],
            is_cmd_allowed=_is_configure_band_cmd_allowed,
            task_callback=task_callback,
        )
        return status, response

    def set_stow_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STOW mode."""
        ds_cm = self.sub_component_managers["DS"]
        try:
            ds_cm.execute_command("Stow", None)
        except tango.DevFailed as err:
            if task_callback:
                task_callback(status=TaskStatus.FAILED, exception=err)
            return TaskStatus.FAILED, "DishManager has failed to execute Stow DSManager"
        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED,
                progress="Stow called, monitor dishmode for LRC completed",
            )
        # abort queued tasks on the task executor
        self.abort_commands()

        return TaskStatus.COMPLETED, "Stow called, monitor dishmode for LRC completed"

    def _stow_on_watchdog_expiry(self) -> None:
        """Stow the dish on watchdog expiry and restart timer if still enabled."""
        self.logger.info("Watchdog timer has expired.")
        self._execute_stow_command("HeartbeatStow")

    def _reenable_watchdog_timer(self) -> None:
        """Re-enable the watchdog timer if it was disabled."""
        if not self.watchdog_timer.is_enabled() and self.component_state["watchdogtimeout"] > 0:
            self.logger.debug(
                "Re-enabling watchdog timer with timeout %s seconds.",
                self.component_state["watchdogtimeout"],
            )
            self.watchdog_timer.enable(timeout=self.component_state["watchdogtimeout"])

    @check_communicating
    def slew(
        self,
        values: list[float],
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Slew the dish."""
        if len(values) != 2:
            return (
                TaskStatus.REJECTED,
                f"Expected 2 arguments (az, el) but got {len(values)} arg(s).",
            )

        def _is_slew_cmd_allowed():
            if self.component_state["dishmode"] != DishMode.OPERATE:
                task_callback(
                    progress="Slew command rejected for current dishMode. "
                    "Slew command is allowed for dishMode OPERATE"
                )
                return False
            if self.component_state["pointingstate"] != PointingState.READY:
                task_callback(
                    progress="Slew command rejected for current pointingState. "
                    "Slew command is allowed for pointingState READY"
                )
                return False
            return True

        status, response = self.submit_task(
            self._command_map.slew,
            args=[values],
            is_cmd_allowed=_is_slew_cmd_allowed,
            task_callback=task_callback,
        )
        return status, response

    def scan(
        self,
        scanid: str,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Scan a target."""
        status, response = self.submit_task(self._scan, args=[scanid], task_callback=task_callback)
        return status, response

    def _scan(
        self,
        scanid: str,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Scan a target."""
        task_callback(progress="Setting scanID", status=TaskStatus.IN_PROGRESS)
        self._update_component_state(scanid=scanid)
        task_callback(
            progress="Scan completed",
            status=TaskStatus.COMPLETED,
            result=(ResultCode.OK, "Scan completed"),
        )

    def end_scan(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Clear the scanid."""
        status, response = self.submit_task(self._end_scan, args=[], task_callback=task_callback)
        return status, response

    def _end_scan(
        self,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Clear the scanid."""
        task_callback(progress="Clearing scanID", status=TaskStatus.IN_PROGRESS)
        self._update_component_state(scanid="")
        task_callback(
            progress="EndScan completed",
            status=TaskStatus.COMPLETED,
            result=(ResultCode.OK, "EndScan completed"),
        )

    @check_communicating
    def track_load_static_off(
        self,
        values: list[float],
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Load the static pointing model offsets."""
        if len(values) != 2:
            return (
                TaskStatus.REJECTED,
                f"Expected 2 arguments (off_xel, off_el) but got {len(values)} arg(s).",
            )

        status, response = self.submit_task(
            self._command_map.track_load_static_off,
            args=[values[0], values[1]],
            task_callback=task_callback,
        )
        return status, response

    def set_kvalue(
        self,
        k_value,
    ) -> Tuple[ResultCode, str]:
        """Set the k-value on the SPFRx.
        Note that it will only take effect after
        SPFRx has been restarted.
        """
        spfrx_cm = self.sub_component_managers["SPFRX"]
        try:
            spfrx_cm.execute_command("SetKValue", k_value)
        except tango.DevFailed as err:
            return (ResultCode.FAILED, err)
        return (ResultCode.OK, "Successfully requested SetKValue on SPFRx")

    def apply_pointing_model(self, json_object) -> Tuple[ResultCode, str]:
        # pylint: disable=R0911
        """Updates a band's coefficient parameters with a given JSON input.
        Note, all 18 coefficients need to be present in the JSON object,the Dish ID
        should be correct, the appropriate unit should be present and coefficient values
        should be in range. Each time the command is called all parameters will get
        updated not just the ones that have been modified.
        """
        # A list of expected coefficients (The order in which they are written)
        min_value = -2000
        max_value = 2000
        expected_coefficients = {
            "IA": {"unit": "arcsec"},
            "CA": {"unit": "arcsec"},
            "NPAE": {"unit": "arcsec"},
            "AN": {"unit": "arcsec"},
            "AN0": {"unit": "arcsec"},
            "AW": {"unit": "arcsec"},
            "AW0": {"unit": "arcsec"},
            "ACEC": {"unit": "arcsec"},
            "ACES": {"unit": "arcsec"},
            "ABA": {"unit": "arcsec"},
            "ABphi": {"unit": "deg"},
            "IE": {"unit": "arcsec"},
            "ECEC": {"unit": "arcsec"},
            "ECES": {"unit": "arcsec"},
            "HECE4": {"unit": "arcsec"},
            "HESE4": {"unit": "arcsec"},
            "HECE8": {"unit": "arcsec"},
            "HESE8": {"unit": "arcsec"},
        }

        ds_cm = self.sub_component_managers["DS"]
        coeff_keys = []
        band_coeffs_values = []
        result_code = ResultCode.REJECTED
        message = "Unknown error."

        # Process the JSON data
        try:
            data = json.loads(json_object)
        except json.JSONDecodeError as err:
            self.logger.exception("Invalid json supplied")
            message = str(err)
            return result_code, message

        # Validate the Dish ID
        antenna_id = data.get("antenna")
        dish_id = self.tango_device_name.split("/")[-1]

        if dish_id != antenna_id:
            self.logger.debug(
                "Command rejected. The Dish id %s and the Antenna's value %s are not equal.",
                dish_id,
                antenna_id,
            )
            message = (
                f"Command rejected. The Dish id {dish_id} and the Antenna's "
                f"value {antenna_id} are not equal."
            )
            return result_code, message

        # Validate the coefficients
        coefficients = data.get("coefficients", {})
        coeff_keys = coefficients.keys()

        # Verify that all expected coefficients are available
        if set(coeff_keys) != set(expected_coefficients.keys()):
            self.logger.debug(
                "Coefficients are missing. The coefficients found in the JSON object were %s.",
                coeff_keys,
            )
            message = (
                "Coefficients are missing. The coefficients found in the JSON object "
                f"were {list(coeff_keys)}"
            )
            return result_code, message

        # Reorder `coeff_keys` to match the order in `expected_coefficients`
        expected_coeff_keys = list(expected_coefficients.keys())
        expected_coeff_units = [
            expected_coefficients[coeff]["unit"] for coeff in expected_coeff_keys
        ]

        self.logger.debug(f"All 18 coefficients {coeff_keys} are present.")

        # Get all coefficient values
        for key, expected_unit in zip(expected_coeff_keys, expected_coeff_units):
            value = coefficients[key].get("value")
            unit = coefficients[key].get("units")

            min_value, max_value = (0, 360) if key == "ABphi" else (-2000, 2000)
            # Check if value is None
            if value is not None:
                if not min_value <= value <= max_value:
                    self.logger.debug(
                        "Value %s for key '%s' is out of range [%s, %s]",
                        value,
                        key,
                        min_value,
                        max_value,
                    )
                    message = (
                        f"Value {value} for key '{key}' is out of range [{min_value}, {max_value}]"
                    )
                    return result_code, message
            else:
                message = f"Missing 'value' for key '{key}'."
                self.logger.debug(message)
                return result_code, message

            # Check if unit is None
            if unit is not None:
                if unit.strip().lower() != expected_unit.strip().lower():
                    self.logger.debug(
                        "Unit %s for key '%s' is not correct. It should be %s",
                        unit,
                        key,
                        expected_unit,
                    )
                    message = (
                        f"Unit {unit} for key '{key}' is not correct. It should be {expected_unit}"
                    )
                    return result_code, message

                band_coeffs_values.append(value)
            else:
                message = f"Missing 'units' for key '{key}'."
                self.logger.debug(message)
                return result_code, message

        # Extract the band's value after the underscore
        band_value = data.get("band").split("_")[-1]

        # Write to the appropriate band
        band_map = {
            "0": "band0PointingModelParams",
            "1": "band1PointingModelParams",
            "2": "band2PointingModelParams",
            "3": "band3PointingModelParams",
            "4": "band4PointingModelParams",
            "5a": "band5aPointingModelParams",
            "5b": "band5bPointingModelParams",
        }

        attribute_name = band_map.get(band_value)
        if attribute_name is None:
            self.logger.debug("Unsupported Band: b%s", band_value)
            message = f"Unsupported Band: b{band_value}"
            return result_code, message

        try:
            ds_cm.write_attribute_value(attribute_name, band_coeffs_values)
            result_code = ResultCode.OK
            message = (
                f"Successfully wrote the following values {coefficients} "
                f"to band {band_value} on DS"
            )
        except tango.DevFailed as err:
            self.logger.exception("%s. The error response is: %s", ResultCode.FAILED, err)
            result_code = ResultCode.FAILED
            message = str(err)

        return result_code, message

    def set_track_interpolation_mode(
        self,
        interpolation_mode,
    ) -> None:
        """Set the trackInterpolationMode on the DS."""
        ds_cm = self.sub_component_managers["DS"]
        try:
            ds_cm.write_attribute_value("trackInterpolationMode", interpolation_mode)
            self.logger.debug("Successfully updated trackInterpolationMode on DSManager.")
        except tango.DevFailed:
            self.logger.error("Failed to update trackInterpolationMode on DSManager.")
            raise
        return (ResultCode.OK, "Successfully updated trackInterpolationMode on DSManager")

    def set_noise_diode_mode(
        self,
        noise_diode_mode,
    ) -> None:
        """Set the noiseDiodeMode on the SPFRx."""
        spfrx_cm = self.sub_component_managers["SPFRX"]
        try:
            spfrx_cm.write_attribute_value("noiseDiodeMode", noise_diode_mode)
            self.logger.debug("Successfully updated noiseDiodeMode on SPFRx.")
        except tango.DevFailed:
            self.logger.error("Failed to update noiseDiodeMode on SPFRx.")
            raise
        return (ResultCode.OK, "Successfully updated noiseDiodeMode on SPFRx")

    def set_periodic_noise_diode_pars(
        self,
        values,
    ) -> None:
        """Set the periodicNoiseDiodePars on the SPFRx."""
        if len(values) != 3:
            raise ValueError(
                f"Expected value of length 3 but got {len(values)}.",
            )

        spfrx_operating_mode = self.sub_component_managers["SPFRX"].component_state[
            "operatingmode"
        ]

        if spfrx_operating_mode == SPFRxOperatingMode.STANDBY:
            spfrx_cm = self.sub_component_managers["SPFRX"]
            try:
                spfrx_cm.write_attribute_value("periodicNoiseDiodePars", values)
                self.logger.debug("Successfully updated periodicNoiseDiodePars on SPFRx.")
            except tango.DevFailed:
                self.logger.error("Failed to update periodicNoiseDiodePars on SPFRx.")
                raise
        else:
            raise AssertionError(
                "Cannot write to periodicNoiseDiodePars."
                " Device is not in STANDBY state."
                f" Current state: {spfrx_operating_mode.name}"
            )

        return (ResultCode.OK, "Successfully updated periodicNoiseDiodePars on SPFRx")

    def set_pseudo_random_noise_diode_pars(
        self,
        values,
    ) -> None:
        """Set the pseudoRandomNoiseDiodePars on the SPFRx."""
        if len(values) != 3:
            raise ValueError(
                f"Expected value of length 3 but got {len(values)}.",
            )

        spfrx_operating_mode = self.sub_component_managers["SPFRX"].component_state[
            "operatingmode"
        ]

        if spfrx_operating_mode == SPFRxOperatingMode.STANDBY:
            spfrx_cm = self.sub_component_managers["SPFRX"]
            try:
                spfrx_cm.write_attribute_value("pseudoRandomNoiseDiodePars", values)
                self.logger.debug("Successfully updated pseudoRandomNoiseDiodePars on SPFRx.")
            except tango.DevFailed:
                self.logger.error("Failed to update pseudoRandomNoiseDiodePars on SPFRx.")
                raise
        else:
            raise AssertionError(
                "Cannot write to pseudoRandomNoiseDiodePars."
                " Device is not in STANDBY state."
                f" Current state: {spfrx_operating_mode.name}"
            )

        return (ResultCode.OK, "Successfully updated pseudoRandomNoiseDiodePars on SPFRx")

    @check_communicating
    def abort(
        self, task_callback: Optional[Callable] = None, task_abort_event: Optional[Event] = Event()
    ) -> Tuple[TaskStatus, str]:
        """Issue abort sequence.

        :param task_callback: Callback for task (default: {None})
        :param task_abort_event: Event holding abort info (default: {Event()})
        """
        # NOTE we dont want to pass the existing abort event object
        # i.e. self._task_executor._abort_event to this function
        # since it might prevent the sequence from being continued
        # when event.is_set() is performed after abort_commands finishes

        # This will be a short lived thread. It hands over the work to the
        # executor to do the heavy lifting. But perform the check nonetheless
        if self._abort_thread is not None and self._abort_thread.is_alive():
            self.logger.info("Abort rejected: there is an ongoing abort sequence.")
            if task_callback:
                task_callback(
                    status=TaskStatus.REJECTED,
                    result=(ResultCode.REJECTED, "Existing Abort sequence ongoing"),
                )
            return TaskStatus.REJECTED, "Existing Abort sequence ongoing"

        if not self._cmd_allowed_checks.is_abort_allowed():
            self.logger.info("Abort rejected: command not allowed in MAINTENANCE mode")
            if task_callback:
                task_callback(
                    status=TaskStatus.REJECTED,
                    result=(
                        ResultCode.REJECTED,
                        "Command not allowed during in MAINTENANCE mode",
                    ),
                )
            return TaskStatus.REJECTED, "Command not allowed during MAINTENANCE mode"

        cmds_in_progress = self.get_currently_executing_lrcs(
            statuses_to_check=(TaskStatus.QUEUED, TaskStatus.IN_PROGRESS)
        )
        abort_command_id = None
        if cmds_in_progress:
            if any("abort" in cmd_id.lower() for cmd_id in cmds_in_progress):
                self.logger.info("Abort rejected: there is an ongoing abort sequence.")
                if task_callback:
                    task_callback(
                        status=TaskStatus.REJECTED,
                        result=(ResultCode.REJECTED, "Existing Abort sequence ongoing"),
                    )
                return TaskStatus.REJECTED, "Existing Abort sequence ongoing"

            self.logger.debug("Aborting LRCs from Abort sequence")
            abort_command_id = self._command_tracker.new_command(
                "abort-sequence:abort-lrc", completed_callback=None
            )
            abort_task_cb = partial(self._command_tracker.update_command_info, abort_command_id)
            self.abort_commands(task_callback=abort_task_cb)

        self._abort_thread = Thread(
            target=self._abort_handler,
            args=[
                abort_command_id,
                task_abort_event,
            ],
            kwargs={
                "task_callback": task_callback,
            },
        )
        self._abort_thread.name = "abort_thread"
        self._abort_thread.start()
        return TaskStatus.IN_PROGRESS, "Abort sequence has started"

    def set_dsc_power_limit_kw(
        self,
        power_limit: float,
    ) -> None:
        """Set the DSC Power Limit kW on the DS."""
        ds_cm = self.sub_component_managers["DS"]
        try:
            ds_cm.write_attribute_value("dscPowerLimitKw", power_limit)
            self.logger.debug("Successfully updated dscPowerLimitKw on DS.")
            self._update_component_state(dscpowerlimitkw=power_limit)
        except tango.DevFailed:
            self.logger.error("Failed to update dscPowerLimitKw on DS.")
            raise
        return (ResultCode.OK, "Successfully updated dscPowerLimitKw on DS")

    def set_h_attenuation(
        self, value: int, task_callback: Optional[Callable] = None
    ) -> Tuple[ResultCode, str]:
        b5dc_cm = self.sub_component_managers["B5DC"]
        try:
            b5dc_cm.execute_command("SetHPolAttenuation", value)
        except tango.DevFailed as err:
            if task_callback:
                self.logger.error("Failed to update HPolAttenuation on the B5DC proxy.")
                task_callback(status=TaskStatus.FAILED, exception=err)
            return TaskStatus.FAILED, "DishManager has failed to execute SetHPolAttenuation"
        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED,
                progress="SetHPolAttenuation called",
            )
        return (ResultCode.OK, "Successfully updated HPolAttenuation on the B5DC proxy.")

    def set_v_attenuation(
        self, value: int, task_callback: Optional[Callable] = None
    ) -> Tuple[ResultCode, str]:
        b5dc_cm = self.sub_component_managers["B5DC"]
        try:
            b5dc_cm.execute_command("SetVPolAttenuation", value)
        except tango.DevFailed as err:
            if task_callback:
                self.logger.error("Failed to update VPolAttenuation on the B5DC proxy.")
                task_callback(status=TaskStatus.FAILED, exception=err)
            return TaskStatus.FAILED, "DishManager has failed to execute SetVPolAttenuation"
        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED,
                progress="SetVPolAttenuation called",
            )
        return (ResultCode.OK, "Successfully updated VPolAttenuation on the B5DC proxy.")

    def set_frequency(
        self, frequency: int, task_callback: Optional[Callable] = None
    ) -> Tuple[ResultCode, str]:
        b5dc_cm = self.sub_component_managers["B5DC"]
        try:
            b5dc_cm.execute_command("SetFrequency", frequency)
        except tango.DevFailed as err:
            if task_callback:
                self.logger.error("Failed to update Frequency on the B5DC proxy.")
                task_callback(status=TaskStatus.FAILED, exception=err)
            return TaskStatus.FAILED, "DishManager has failed to execute SetFrequency"
        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED,
                progress="SetVPolAttenuation called",
            )
        return (ResultCode.OK, "Successfully updated Frequency on the B5DC proxy.")
