# pylint: disable=protected-access,too-many-lines,too-many-public-methods
"""Component manager for a DishManager tango device"""
import json
import logging
import os
from functools import partial
from threading import Event, Lock, Thread
from typing import Callable, Dict, Optional, Tuple

import tango
from ska_control_model import CommunicationStatus, HealthState, ResultCode, TaskStatus
from ska_tango_base.executor import TaskExecutorComponentManager

from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.component_managers.spf_cm import SPFComponentManager
from ska_mid_dish_manager.component_managers.spfrx_cm import SPFRxComponentManager
from ska_mid_dish_manager.component_managers.tango_device_cm import LostConnection
from ska_mid_dish_manager.models.command_map import CommandMap
from ska_mid_dish_manager.models.constants import BAND_POINTING_MODEL_PARAMS_LENGTH
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    CapabilityStates,
    Device,
    DishMode,
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    NoiseDiodeMode,
    PointingState,
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
from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_current_tai_timestamp


# pylint: disable=abstract-method
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments,too-many-public-methods
class DishManagerComponentManager(TaskExecutorComponentManager):
    """A component manager for DishManager

    It watches the component managers of the subservient devices
    (DS, SPF, SPFRX) to reflect the state of the Dish LMC.
    """

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker,
        connection_state_callback,
        quality_state_callback,
        tango_device_name: str,
        ds_device_fqdn: str,
        spf_device_fqdn: str,
        spfrx_device_fqdn: str,
        *args,
        **kwargs,
    ):
        """"""
        # pylint: disable=useless-super-delegation
        self.tango_device_name = tango_device_name
        self.sub_component_managers = None
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
            band1pointingmodelparams=[],
            band2pointingmodelparams=[],
            band3pointingmodelparams=[],
            band4pointingmodelparams=[],
            band5apointingmodelparams=[],
            band5bpointingmodelparams=[],
            ignorespf=False,
            ignorespfrx=False,
            noisediodemode=NoiseDiodeMode.OFF,
            periodicnoisediodepars=[],
            pseudorandomnoisediodepars=[0.0, 0.0, 0.0],
            actstaticoffsetvaluexel=0.0,
            actstaticoffsetvalueel=0.0,
            achievedtargetlock=False,
            desiredpointingaz=[0.0, 0.0],
            desiredpointingel=[0.0, 0.0],
            achievedpointing=[0.0, 0.0, 0.0],
            attenuationpolh=0.0,
            attenuationpolv=0.0,
            kvalue=0,
            scanid="",
            trackinterpolationmode=TrackInterpolationMode.SPLINE,
            **kwargs,
        )
        self.logger = logger
        self._connection_state_callback = connection_state_callback
        self._quality_state_callback = quality_state_callback
        self._dish_mode_model = DishModeModel()
        self._state_transition = StateTransition()
        self._command_tracker = command_tracker
        self._state_update_lock = Lock()
        self._sub_communication_state_change_lock = Lock()
        self._abort_thread: Optional[Thread] = None

        self._device_to_comm_attr_map = {
            Device.DS: "dsConnectionState",
            Device.SPF: "spfConnectionState",
            Device.SPFRX: "spfrxConnectionState",
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
                    self._sub_communication_state_changed, Device.SPF
                ),
                component_state_callback=self._component_state_changed,
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
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.UNKNOWN,
                desiredpointingaz=[0.0, 0.0],
                desiredpointingel=[0.0, 0.0],
                achievedpointing=[0.0, 0.0, 0.0],
                band1pointingmodelparams=[],
                band2pointingmodelparams=[],
                band3pointingmodelparams=[],
                band4pointingmodelparams=[],
                band5apointingmodelparams=[],
                band5bpointingmodelparams=[],
                trackinterpolationmode=TrackInterpolationMode.SPLINE,
                actstaticoffsetvaluexel=None,
                actstaticoffsetvalueel=None,
                communication_state_callback=partial(
                    self._sub_communication_state_changed, Device.DS
                ),
                component_state_callback=self._component_state_changed,
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
                periodicnoisediodepars=[0.0, 0.0, 0.0],
                pseudorandomnoisediodepars=[0.0, 0.0, 0.0],
                communication_state_callback=partial(
                    self._sub_communication_state_changed, Device.SPFRX
                ),
                component_state_callback=self._component_state_changed,
                quality_state_callback=self._quality_state_callback,
            ),
        }
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

        self._command_map = CommandMap(
            self,
            self._command_tracker,
            self.logger,
        )

        self.direct_mapped_attrs = {
            "DS": [
                "achievedPointing",
                "desiredPointingAz",
                "desiredPointingEl",
                "achievedTargetLock",
                "trackInterpolationMode",
                "actStaticOffsetValueXel",
                "actStaticOffsetValueEl",
            ],
            "SPFRX": [
                "noiseDiodeMode",
                "periodicNoiseDiodePars",
                "pseudoRandomNoiseDiodePars",
            ],
        }

    def _get_active_sub_component_managers(self) -> Dict:
        """Get a list of subservient device component managers which are not being ignored."""
        active_component_managers = {"DS": self.sub_component_managers["DS"]}

        if not self.is_device_ignored("SPF"):
            active_component_managers["SPF"] = self.sub_component_managers["SPF"]

        if not self.is_device_ignored("SPFRX"):
            active_component_managers["SPFRX"] = self.sub_component_managers["SPFRX"]

        return active_component_managers

    # pylint: disable=unused-argument
    def _sub_communication_state_changed(
        self, attribute_name: str, communication_state: Optional[CommunicationStatus] = None
    ):
        """
        Callback triggered by the component manager when it establishes
        a connection with the underlying (subservient) device

        The component manager syncs with the device for fresh updates
        everytime connection is established.

        Note: This callback is triggered by the component manangers of
        the subservient devices. DishManager reflects this in its connection
        status attributes.
        """
        # Update the DM component communication states
        self.logger.debug("Sub communication state changed")

        with self._sub_communication_state_change_lock:
            if self.sub_component_managers:
                if not self.is_device_ignored("SPF"):
                    self._update_component_state(
                        spfconnectionstate=self.sub_component_managers["SPF"].communication_state
                    )
                if not self.is_device_ignored("SPFRX"):
                    self._update_component_state(
                        spfrxconnectionstate=self.sub_component_managers[
                            "SPFRX"
                        ].communication_state
                    )
                self._update_component_state(
                    dsconnectionstate=self.sub_component_managers["DS"].communication_state
                )

            if self.sub_component_managers:
                active_sub_component_managers = self._get_active_sub_component_managers()

                self.logger.debug(
                    ("Active component managers [%s]"), active_sub_component_managers
                )

                # Have all the component states been created
                if not all(
                    sub_component_manager.component_state
                    for sub_component_manager in active_sub_component_managers.values()
                ):
                    self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
                    self._update_component_state(healthstate=HealthState.UNKNOWN)
                    return

                # Are all the CommunicationStatus ESTABLISHED
                if all(
                    sub_component_manager.communication_state == CommunicationStatus.ESTABLISHED
                    for sub_component_manager in active_sub_component_managers.values()
                ):
                    self.logger.debug("Calculating new HealthState and DishMode")
                    self._update_communication_state(CommunicationStatus.ESTABLISHED)

                    ds_component_state = self.sub_component_managers["DS"].component_state
                    spf_component_state = self.sub_component_managers["SPF"].component_state
                    spfrx_component_state = self.sub_component_managers["SPFRX"].component_state

                    new_health_state = self._state_transition.compute_dish_health_state(
                        ds_component_state,
                        spfrx_component_state if not self.is_device_ignored("SPFRX") else None,
                        spf_component_state if not self.is_device_ignored("SPF") else None,
                    )
                    new_dish_mode = self._state_transition.compute_dish_mode(
                        ds_component_state,
                        spfrx_component_state if not self.is_device_ignored("SPFRX") else None,
                        spf_component_state if not self.is_device_ignored("SPF") else None,
                    )

                    self._update_component_state(
                        healthstate=new_health_state, dishmode=new_dish_mode
                    )
                else:
                    self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
                    self._update_component_state(
                        healthstate=HealthState.UNKNOWN, dishmode=DishMode.UNKNOWN
                    )

            self._component_state_changed()

            # push change events for the connection state attributes
            self._connection_state_callback(attribute_name)

    # pylint: disable=unused-argument, too-many-branches, too-many-locals, too-many-statements
    def _component_state_changed(self, *args, **kwargs):
        """
        Callback triggered by the component manager of the
        subservient device for component state changes.

        This aggregates the component values and computes the final value
        which will be reported for the respective attribute. The computed
        value is sent to DishManager's component_state callback which pushes
        a change event on the attribute and updates the internal variable.

        Note: This callback is triggered by the component managers of
        the subservient devices only. DishManager also has its own callback.
        """
        if not self.sub_component_managers:
            return
        active_sub_component_managers = self._get_active_sub_component_managers()
        if not all(
            sub_component_manager.component_state
            for sub_component_manager in active_sub_component_managers.values()
        ):
            return

        ds_component_state = self.sub_component_managers["DS"].component_state
        spf_component_state = self.sub_component_managers["SPF"].component_state
        spfrx_component_state = self.sub_component_managers["SPFRX"].component_state

        # Only log non pointing changes
        if not any(
            attr in ["desiredpointingaz", "desiredpointingel", "achievedpointing"]
            for attr in kwargs
        ):
            self.logger.debug(
                (
                    "Component state has changed, kwargs [%s], DS [%s], SPF [%s]"
                    ", SPFRx [%s], DM [%s]"
                ),
                kwargs,
                ds_component_state,
                spf_component_state,
                spfrx_component_state,
                self.component_state,
            )

        # Only update dishMode if there are operatingmode changes
        if "operatingmode" in kwargs or "indexerposition" in kwargs:
            self.logger.debug(
                ("Updating dishMode with operatingModes DS [%s], SPF [%s], SPFRX [%s]"),
                ds_component_state["operatingmode"],
                spf_component_state["operatingmode"],
                spfrx_component_state["operatingmode"],
            )
            new_dish_mode = self._state_transition.compute_dish_mode(
                ds_component_state,
                spfrx_component_state if not self.is_device_ignored("SPFRX") else None,
                spf_component_state if not self.is_device_ignored("SPF") else None,
            )
            self._update_component_state(dishmode=new_dish_mode)

        if (
            "healthstate" in kwargs
            and "healthstate" in ds_component_state
            and "healthstate" in spf_component_state
            and "healthstate" in spfrx_component_state
        ):
            self.logger.debug(
                ("Updating healthState with healthstate DS [%s], SPF [%s], SPFRX [%s]"),
                ds_component_state["healthstate"],
                spf_component_state["healthstate"],
                spfrx_component_state["healthstate"],
            )
            new_health_state = self._state_transition.compute_dish_health_state(
                ds_component_state,
                spfrx_component_state if not self.is_device_ignored("SPFRX") else None,
                spf_component_state if not self.is_device_ignored("SPF") else None,
            )
            self._update_component_state(healthstate=new_health_state)

        if "pointingstate" in kwargs:
            self.logger.debug(
                ("Newly calculated pointing state [pointing_state] [%s]"),
                ds_component_state["pointingstate"],
            )
            self._update_component_state(pointingstate=ds_component_state["pointingstate"])

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
            spf_component_manager.write_attribute_value("bandInFocus", band_in_focus)
            spf_component_state["bandinfocus"] = band_in_focus

        # spfrx attenuation
        if "attenuationpolv" in kwargs or "attenuationpolh" in kwargs:
            attenuation = {
                "attenuationpolv": spfrx_component_state["attenuationpolv"],
                "attenuationpolh": spfrx_component_state["attenuationpolh"],
            }
            self._update_component_state(**attenuation)

        # kvalue
        if "kvalue" in kwargs:
            self._update_component_state(kvalue=spfrx_component_state["kvalue"])

        # configuredBand
        if "indexerposition" in kwargs or "bandinfocus" in kwargs or "configuredband" in kwargs:
            self.logger.debug(
                (
                    "Updating configuredBand on DM from change"
                    " [%s] with DS [%s] SPF [%s] SPFRX [%s]"
                ),
                kwargs,
                ds_component_state,
                spf_component_state,
                spfrx_component_state,
            )

            configured_band = self._state_transition.compute_configured_band(
                ds_component_state,
                spfrx_component_state if not self.is_device_ignored("SPFRX") else None,
                spf_component_state if not self.is_device_ignored("SPF") else None,
            )
            self._update_component_state(configuredband=configured_band)

        # update capturing attribute when SPFRx captures data
        if "capturingdata" in kwargs:
            self.logger.debug(
                ("Updating capturing with SPFRx [%s]"),
                spfrx_component_state,
            )
            self._update_component_state(capturing=spfrx_component_state["capturingdata"])

        # CapabilityStates
        # Update all CapabilityStates when indexerposition, dish_mode
        # or operatingmode changes
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
                self._update_component_state(**{cap_state_name: new_state})

        # Update the pointing model params if they change
        for band in ["1", "2", "3", "4", "5a", "5b"]:
            pointing_param_name = f"band{band}pointingmodelparams"

            if pointing_param_name in kwargs:
                self.logger.debug(
                    ("Updating %s with DS %s %s"),
                    pointing_param_name,
                    pointing_param_name,
                    ds_component_state[pointing_param_name],
                )
                self._update_component_state(
                    **{pointing_param_name: ds_component_state[pointing_param_name]}
                )

        # Update attributes that are mapped directly from subservient devices
        for device, attrs in self.direct_mapped_attrs.items():
            enum_attr_mapping = {
                "trackInterpolationMode": TrackInterpolationMode,
                "noiseDiodeMode": NoiseDiodeMode,
            }
            for attr in attrs:
                attr_lower = attr.lower()

                if attr_lower in kwargs:
                    new_value = None
                    if device == "DS":
                        new_value = ds_component_state[attr_lower]
                    elif device == "SPF":
                        new_value = spf_component_state[attr_lower]
                    elif device == "SPFRX":
                        new_value = spfrx_component_state[attr_lower]
                    if attr_lower not in [
                        "desiredpointingaz",
                        "desiredpointingel",
                        "achievedpointing",
                    ]:
                        self.logger.debug(
                            ("Updating %s with %s %s [%s]"),
                            attr,
                            device,
                            attr,
                            (
                                enum_attr_mapping[attr](new_value)
                                if attr in enum_attr_mapping
                                else new_value
                            ),
                        )

                    self._update_component_state(**{attr_lower: new_value})

    def _update_component_state(self, *args, **kwargs):
        """Log the new component state"""
        if not any(
            attr in ["desiredpointingaz", "desiredpointingel", "achievedpointing"]
            for attr in kwargs
        ):
            self.logger.debug("Updating dish manager component state with [%s]", kwargs)
        super()._update_component_state(*args, **kwargs)

    def sync_component_states(self):
        """
        Sync monitored attributes on component managers with their respective sub devices

        Clear the monitored attributes of all subservient device component managers,
        then re-read all the monitored attributes from their respective tango device
        to force dishManager to recalculate its attributes.
        """
        self.logger.debug("Syncing component states")
        if self.sub_component_managers:
            for device, component_manager in self.sub_component_managers.items():
                if not self.is_device_ignored(device):
                    component_manager.clear_monitored_attributes()
                    component_manager.update_state_from_monitored_attributes()

    def set_spf_device_ignored(self, ignored: bool):
        """Set the SPF device ignored boolean and update device communication."""
        if ignored != self.component_state["ignorespf"]:
            self.logger.debug("Setting ignore SPF device as %s", ignored)
            self._update_component_state(ignorespf=ignored)
            if ignored:
                if "SPF" in self.sub_component_managers:
                    self.sub_component_managers["SPF"].stop_communicating()
                    self.sub_component_managers["SPF"].clear_monitored_attributes()
                self._update_component_state(spfconnectionstate=CommunicationStatus.DISABLED)
            else:
                self._update_component_state(
                    spfconnectionstate=CommunicationStatus.NOT_ESTABLISHED
                )
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
                self._update_component_state(spfrxconnectionstate=CommunicationStatus.DISABLED)
            else:
                self._update_component_state(
                    spfrxconnectionstate=CommunicationStatus.NOT_ESTABLISHED
                )
                self.sub_component_managers["SPFRX"].start_communicating()

            self._update_component_state(ignorespfrx=ignored)

    def is_device_ignored(self, device: str):
        """Check whether the given device is ignored."""
        if device == "SPF":
            return self.component_state["ignorespf"]
        if device == "SPFRX":
            return self.component_state["ignorespfrx"]
        return False

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

    def start_communicating(self):
        """Connect from monitored devices"""
        if self.sub_component_managers:
            for device_name, component_manager in self.sub_component_managers.items():
                if not self.is_device_ignored(device_name):
                    component_manager.start_communicating()

    def abort_commands(self, task_callback: Optional[Callable] = None) -> None:
        """Abort commands on dish manager and its subservient devices

        :param task_callback: callback when the status changes
        """
        self.logger.debug("Aborting long running commands")
        super().abort_commands(task_callback)
        sub_component_mgrs = self._get_active_sub_component_managers()
        for component_mgr in sub_component_mgrs.values():
            # dont use the same taskcallback else we get completed 4x on the same command id
            component_mgr.abort_commands()

    def _track_load_table(
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
        except (LostConnection, tango.DevFailed) as err:
            self.logger.exception("TrackLoadTable on DSManager failed")
            result_code = ResultCode.FAILED
            result_message = str(err)
        return (result_code, result_message)

    def set_standby_lp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_LP mode"""
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

    def set_standby_fp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_FP mode"""
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

    def set_operate_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to OPERATE mode"""

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

    def track_cmd(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Track the commanded pointing position"""

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

    def track_stop_cmd(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Stop tracking"""

        def _is_track_stop_cmd_allowed():
            dish_mode = self.component_state["dishmode"]
            pointing_state = self.component_state["pointingstate"]
            if dish_mode != DishMode.OPERATE and pointing_state != PointingState.TRACK:
                return False
            return True

        status, response = self.submit_task(
            self._command_map.track_stop_cmd,
            args=[],
            is_cmd_allowed=_is_track_stop_cmd_allowed,
            task_callback=task_callback,
        )
        return status, response

    def configure_band_cmd(
        self,
        band_number,
        synchronise,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Configure frequency band"""
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
        """
        Transition the dish to STOW mode
        """
        ds_cm = self.sub_component_managers["DS"]
        try:
            ds_cm.execute_command("Stow", None)
        except (LostConnection, tango.DevFailed) as err:
            task_callback(status=TaskStatus.FAILED, exception=err)
            self.logger.exception("DishManager has failed to execute Stow DSManager")
            return TaskStatus.FAILED, "DishManager has failed to execute Stow DSManager"
        task_callback(
            status=TaskStatus.COMPLETED, progress="Stow called, monitor dishmode for LRC completed"
        )
        # abort queued tasks on the task executor
        self.abort_commands()

        return TaskStatus.COMPLETED, "Stow called, monitor dishmode for LRC completed"

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
        self.logger.debug("Calling SetKValue on SPFRX.")
        try:
            result = spfrx_cm.execute_command("SetKValue", k_value)
            self.logger.debug(
                "Result of the call to [%s] on SPFRx is [%s]",
                "SetKValue",
                result,
            )
        except (LostConnection, tango.DevFailed) as err:
            self.logger.exception("SetKvalue on SPFRx failed")
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

        # Extract the band's value after the underscore
        band_value = data.get("band").split("_")[-1]

        # Write to the appropriate band
        band_map = {
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
        except (LostConnection, tango.DevFailed) as err:
            self.logger.exception("%s. The error response is: %s", (ResultCode.FAILED, err))
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
        except LostConnection:
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
        except (LostConnection, tango.DevFailed):
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

        if spfrx_operating_mode in [SPFRxOperatingMode.STANDBY, SPFRxOperatingMode.MAINTENANCE]:
            spfrx_cm = self.sub_component_managers["SPFRX"]
            try:
                spfrx_cm.write_attribute_value("periodicNoiseDiodePars", values)
                self.logger.debug("Successfully updated periodicNoiseDiodePars on SPFRx.")
            except (LostConnection, tango.DevFailed):
                self.logger.error("Failed to update periodicNoiseDiodePars on SPFRx.")
                raise
        else:
            raise AssertionError(
                "Cannot write to periodicNoiseDiodePars."
                " Device is not in STANDBY or MAINTENANCE state."
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

        if spfrx_operating_mode in [SPFRxOperatingMode.STANDBY, SPFRxOperatingMode.MAINTENANCE]:
            spfrx_cm = self.sub_component_managers["SPFRX"]
            try:
                spfrx_cm.write_attribute_value("pseudoRandomNoiseDiodePars", values)
                self.logger.debug("Successfully updated pseudoRandomNoiseDiodePars on SPFRx.")
            except (LostConnection, tango.DevFailed):
                self.logger.error("Failed to update pseudoRandomNoiseDiodePars on SPFRx.")
                raise
        else:
            raise AssertionError(
                "Cannot write to pseudoRandomNoiseDiodePars."
                " Device is not in STANDBY or MAINTENANCE state."
                f" Current state: {spfrx_operating_mode.name}"
            )

        return (ResultCode.OK, "Successfully updated pseudoRandomNoiseDiodePars on SPFRx")

    def _reset_track_table(self) -> None:
        """
        Write the last achievedPointing back to the trackTable in loadmode NEW

        NOTE: this is a workaround until the RESET mode is implemented on the DSC.
        Remove/re-work this when the RESET mode is available
        """
        current_pointing = self.component_state.get("achievedpointing")
        timestamp = get_current_tai_timestamp()
        current_pointing[0] = timestamp
        sequence_length = 1
        load_mode = TrackTableLoadMode.NEW

        result_code, result_message = self._track_load_table(
            sequence_length, current_pointing, load_mode
        )
        if result_code == ResultCode.OK:
            # need to find a way to bubble up this table
            # to dish manager._program_track_table and _load_mode
            pass
        else:
            self.logger.warning(
                "Failed to reset programTrackTable in Abort sequence: %s", result_message
            )

    def is_dish_moving(self) -> bool:
        """
        Report whether or not the dish is moving

        :returns: boolean dish movement activity
        """
        pointing_state = self.component_state.get("pointingstate")
        if pointing_state in [PointingState.SLEW, PointingState.TRACK]:
            return True
        return False

    def _ensure_transition_to_fp_mode(
        self,
        task_abort_event: Optional[Event] = None,
        task_callback: Optional[Callable] = None,
    ) -> None:
        # get fresh component states from the sub devices
        sub_component_mgrs = self._get_active_sub_component_managers()
        for component_manager in sub_component_mgrs.values():
            component_manager.update_state_from_monitored_attributes()

        # only force the transition if the dish is not in FP already
        current_dish_mode = self.component_state.get("dishmode")
        if current_dish_mode == DishMode.STANDBY_FP:
            if task_callback:
                task_callback(status=TaskStatus.COMPLETED)
            return

        # fan out respective FP command to the sub devices
        self._command_map.set_standby_fp_mode(task_abort_event, task_callback)

    def is_lrc_currently_executing(self) -> bool:
        """
        Report whether or not commands are running or waiting to be executed from the task executor

        :returns: boolean indicating whether or not an lrc is executing
        """
        statuses_to_check = [TaskStatus.STAGING, TaskStatus.QUEUED, TaskStatus.IN_PROGRESS]
        command_statuses = self._command_tracker.command_statuses
        status_idx = 1
        if command_statuses:
            command_statuses = [status_item[status_idx] for status_item in command_statuses]
            # do we have any commands in staging, queued or in progress
            statuses_to_check = set(statuses_to_check)
            if statuses_to_check.intersection(command_statuses) == set():
                return False
            return True
        # there are no commands in staging, queued or in progress
        return False

    def _abort(
        self,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        # the name has to be different, task_callback != task_cb
        # one is a partial with a command id and the other isnt
        task_cb = self._command_tracker.update_command_info

        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        if self.is_lrc_currently_executing():
            self.logger.debug("Aborting LRCs from Abort sequence")
            abort_command_id = self._command_tracker.new_command(
                "abort-sequence:abort-lrc", completed_callback=None
            )
            abort_task_cb = partial(task_cb, abort_command_id)
            self.abort_commands(task_callback=abort_task_cb)
            while (
                not self._command_tracker.get_command_status(abort_command_id)
                != TaskStatus.COMPLETED
            ):
                task_abort_event.wait(0.1)  # sleep a bit to not overwork the CPU

        if self.is_dish_moving():
            # stop the dish
            track_stop_command_id = self._command_tracker.new_command(
                "abort-sequence:trackstop", completed_callback=None
            )
            track_stop_task_cb = partial(task_cb, track_stop_command_id)
            self.logger.debug("Issuing TrackStop from Abort sequence")
            self._command_map.track_stop_cmd(task_abort_event, track_stop_task_cb)

            # clear the scan id
            end_scan_command_id = self._command_tracker.new_command(
                "abort-sequence:endscan", completed_callback=None
            )
            end_scan_task_cb = partial(task_cb, end_scan_command_id)
            self.logger.debug("Issuing EndScan from Abort sequence")
            self._end_scan(task_abort_event, end_scan_task_cb)

        # send the last reported achieved pointing in load mode new
        self.logger.debug("Resetting the programTrackTable from Abort sequence")
        self._reset_track_table()

        # go to the known state: STANDBY-FP
        standby_fp_command_id = self._command_tracker.new_command(
            "abort-sequence:standbyfp", completed_callback=None
        )
        standby_fp_task_cb = partial(task_cb, standby_fp_command_id)
        self.logger.debug("Issuing SetStandbyFPMode from Abort sequence")
        self._ensure_transition_to_fp_mode(task_abort_event, standby_fp_task_cb)

        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED, result=(ResultCode.OK, "Abort sequence completed")
            )

    def abort(
        self, task_callback: Optional[Callable] = None, task_abort_event: Optional[Event] = Event()
    ) -> Tuple[TaskStatus, str]:
        """
        Issue abort sequence

        :param task_callback: Callback for task (default: {None})
        :param task_abort_event: Event holding abort info (default: {Event()})
        """
        # NOTE we dont want to pass the existing abort event object
        # i.e. self._task_executor._abort_event to this function
        # since it might prevent the command from being triggered
        # when the check is performed after abort_commands finishes

        if self._abort_thread is not None and self._abort_thread.is_alive():
            self.logger.info("Abort rejected: there is an ongoing abort sequence.")
            if task_callback:
                task_callback(
                    status=TaskStatus.REJECTED,
                    result=(ResultCode.REJECTED, "Existing Abort sequence ongoing"),
                )
            return TaskStatus.REJECTED, "Existing Abort sequence ongoing"

        if self.component_state.get("dishmode") == DishMode.MAINTENANCE:
            self.logger.info("Abort rejected: command not allowed from MAINTENANCE mode")
            if task_callback:
                task_callback(
                    status=TaskStatus.REJECTED,
                    result=(
                        ResultCode.REJECTED,
                        "Abort not allowed from MAINTENANCE mode",
                    ),
                )
            return TaskStatus.REJECTED, "Abort not allowed from MAINTENANCE mode"

        if self.is_dish_moving() and self.component_state.get("dishmode") == DishMode.STOW:
            self.logger.info("Abort rejected: STOW cannot be aborted")
            if task_callback:
                task_callback(
                    status=TaskStatus.REJECTED,
                    result=(
                        ResultCode.REJECTED,
                        "STOW cannot be aborted",
                    ),
                )
            return TaskStatus.REJECTED, "STOW cannot be aborted"

        self._abort_thread = Thread(
            target=self._abort,
            args=[],
            kwargs={"task_callback": task_callback, "task_abort_event": task_abort_event},
        )
        self._abort_thread.name = "abort_thread"
        self._abort_thread.start()
        return TaskStatus.IN_PROGRESS, "Abort sequence has started"

    def _get_device_attribute_property_value(self, attribute_name) -> Optional[str]:
        """
        Read memorized attributes values from TangoDB.

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
        except tango.DevFailed:
            self.logger.debug(
                "Could not update memorized attributes. Failed to connect to database."
            )

    def stop_communicating(self):
        """Disconnect from monitored devices"""
        if self.sub_component_managers:
            for component_manager in self.sub_component_managers.values():
                component_manager.stop_communicating()
