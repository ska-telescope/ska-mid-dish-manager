# pylint: disable=protected-access
"""Component manager for a DishManager tango device"""
import logging
import os
from functools import partial
from threading import Lock
from typing import Callable, List, Optional, Tuple

import tango
from ska_control_model import CommunicationStatus, HealthState, ResultCode, TaskStatus
from ska_tango_base.executor import TaskExecutorComponentManager

from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.component_managers.spf_cm import SPFComponentManager
from ska_mid_dish_manager.component_managers.spfrx_cm import SPFRxComponentManager
from ska_mid_dish_manager.component_managers.tango_device_cm import LostConnection
from ska_mid_dish_manager.models.command_map import CommandMap
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    CapabilityStates,
    Device,
    DishMode,
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
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


# pylint: disable=abstract-method
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
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
            dishmode=None,
            capturing=False,
            healthstate=None,
            pointingstate=None,
            b1capabilitystate=None,
            b2capabilitystate=None,
            b3capabilitystate=None,
            b4capabilitystate=None,
            b5acapabilitystate=None,
            b5bcapabilitystate=None,
            achievedtargetlock=None,
            desiredpointingaz=[0.0, 0.0],
            desiredpointingel=[0.0, 0.0],
            achievedpointing=[0.0, 0.0, 0.0],
            achievedpointingaz=[0.0, 0.0, 0.0],
            achievedpointingel=[0.0, 0.0, 0.0],
            configuredband=Band.NONE,
            attenuationpolh=0.0,
            attenuationpolv=0.0,
            kvalue=0,
            scanid="",
            spfconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            spfrxconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            dsconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            band1pointingmodelparams=[],
            band2pointingmodelparams=[],
            band3pointingmodelparams=[],
            band4pointingmodelparams=[],
            trackinterpolationmode=None,
            ignorespf=None,
            ignorespfrx=None,
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
                    self._sub_communication_state_changed,
                    self._device_to_comm_attr_map[Device.SPF],
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
                pointingstate=None,
                achievedtargetlock=None,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.UNKNOWN,
                desiredpointingaz=[0.0, 0.0],
                desiredpointingel=[0.0, 0.0],
                achievedpointing=[0.0, 0.0, 0.0],
                achievedpointingaz=[0.0, 0.0, 0.0],
                achievedpointingel=[0.0, 0.0, 0.0],
                band1pointingmodelparams=[],
                band2pointingmodelparams=[],
                band3pointingmodelparams=[],
                band4pointingmodelparams=[],
                trackinterpolationmode=TrackInterpolationMode.SPLINE,
                communication_state_callback=partial(
                    self._sub_communication_state_changed, self._device_to_comm_attr_map[Device.DS]
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
                communication_state_callback=partial(
                    self._sub_communication_state_changed,
                    self._device_to_comm_attr_map[Device.SPFRX],
                ),
                component_state_callback=self._component_state_changed,
                quality_state_callback=self._quality_state_callback,
            ),
        }
        initial_component_states = {
            "dishmode": DishMode.UNKNOWN,
            "healthstate": HealthState.UNKNOWN,
            "configuredband": Band.NONE,
            "capturing": False,
            "pointingstate": PointingState.UNKNOWN,
            "b1capabilitystate": CapabilityStates.UNKNOWN,
            "b2capabilitystate": CapabilityStates.UNKNOWN,
            "b3capabilitystate": CapabilityStates.UNKNOWN,
            "b4capabilitystate": CapabilityStates.UNKNOWN,
            "b5acapabilitystate": CapabilityStates.UNKNOWN,
            "b5bcapabilitystate": CapabilityStates.UNKNOWN,
            "spfconnectionstate": CommunicationStatus.NOT_ESTABLISHED,
            "spfrxconnectionstate": CommunicationStatus.NOT_ESTABLISHED,
            "dsconnectionstate": CommunicationStatus.NOT_ESTABLISHED,
            "band1pointingmodelparams": [],
            "band2pointingmodelparams": [],
            "band3pointingmodelparams": [],
            "band4pointingmodelparams": [],
            "ignorespf": False,
            "ignorespfrx": False,
        }
        self._update_component_state(**initial_component_states)
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

        self._command_map = CommandMap(
            self,
            self._command_tracker,
            self.logger,
        )

        self.direct_mapped_attrs = {
            "DS": [
                "achievedPointing",
                "achievedPointingAz",
                "achievedPointingEl",
                "desiredPointingAz",
                "desiredPointingEl",
                "trackInterpolationMode",
            ],
        }

    def _get_active_sub_component_managers(self) -> List:
        """Get a list of subservient device component managers which are not being ignored."""
        active_component_managers = [self.sub_component_managers["DS"]]

        if not self.is_device_ignored("SPF"):
            active_component_managers.append(self.sub_component_managers["SPF"])

        if not self.is_device_ignored("SPFRX"):
            active_component_managers.append(self.sub_component_managers["SPFRX"])

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
                    for sub_component_manager in active_sub_component_managers
                ):
                    self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
                    self._update_component_state(healthstate=HealthState.UNKNOWN)
                    return

                # Are all the CommunicationStatus ESTABLISHED
                if all(
                    sub_component_manager.communication_state == CommunicationStatus.ESTABLISHED
                    for sub_component_manager in active_sub_component_managers
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
            for sub_component_manager in active_sub_component_managers
        ):
            return

        ds_component_state = self.sub_component_managers["DS"].component_state
        spf_component_state = self.sub_component_managers["SPF"].component_state
        spfrx_component_state = self.sub_component_managers["SPFRX"].component_state

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

                    self.logger.debug(
                        ("Updating %s with %s %s [%s]"),
                        attr,
                        device,
                        attr,
                        new_value,
                    )

                    self._update_component_state(**{attr_lower: new_value})

    def _update_component_state(self, *args, **kwargs):
        """Log the new component state"""
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

    def _validate_band_x_pointing_model_params(self, values):
        """Validate the args passed on all bandXPointingModelParams."""
        # The argument value is a list of two floats: [off_xel, off_el]
        if len(values) != 2:
            raise ValueError(
                f"Expected 2 arguments (off_xel, off_el) but got {len(values)} arg(s)."
            )

    def start_communicating(self):
        """Connect from monitored devices"""
        if self.sub_component_managers:
            for device_name, component_manager in self.sub_component_managers.items():
                if not self.is_device_ignored(device_name):
                    component_manager.start_communicating()

    def _track_load_table(
        self, sequence_length: int, table: list[float], load_mode: TrackTableLoadMode
    ) -> None:
        """Load the track table."""
        float_list = [load_mode, sequence_length]
        float_list.extend(table)
        ds_cm = self.sub_component_managers["DS"]
        self.logger.debug("Calling TrackLoadTable on DSManager.")
        try:
            result = ds_cm.execute_command("TrackLoadTable", float_list)
            self.logger.debug(
                "Result of the call to [%s] on DSManager is [%s]",
                "TrackLoadTable",
                result,
            )
        except (LostConnection, tango.DevFailed) as err:
            self.logger.exception("TrackLoadTable on DSManager failed")
            return (ResultCode.FAILED, err)
        return (ResultCode.OK, "Successfully requested TrackLoadTable on DSManager")

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
        """Transition the dish to STOW mode

        Note: To expedite the command, it does not
        implement _is_track_stow_cmd_allowed() because by
        default it is allowed to run at all states.
        """
        ds_cm = self.sub_component_managers["DS"]
        try:
            ds_cm.execute_command("Stow", None)
        except (LostConnection, tango.DevFailed) as err:
            task_callback(status=TaskStatus.FAILED, exception=err)
            self.logger.exception("DishManager has failed to execute Stow DSManager")
            return TaskStatus.FAILED, "DishManager has failed to execute Stow DSManager"
        task_callback(
            progress="Stow called, monitor dishmode for LRC completed", status=TaskStatus.COMPLETED
        )
        # abort queued tasks on the task executor's threadpoolexecutor
        self.abort_commands()
        # abort the task on the subservient devices
        sub_component_mgrs = self._get_active_sub_component_managers()
        for component_mgr in sub_component_mgrs:
            component_mgr.abort_commands()

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

        status, response = self.submit_task(
            self._command_map.slew, args=[values], task_callback=task_callback
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
            self._command_map.track_load_static_off, args=[values], task_callback=task_callback
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
