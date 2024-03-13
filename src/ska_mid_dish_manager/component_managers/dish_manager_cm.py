# pylint: disable=protected-access
"""Component manager for a DishManager tango device"""
import logging
from functools import partial
from threading import Lock
from typing import Callable, Optional, Tuple

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
from ska_mid_dish_manager.models.dish_mode_model import CommandNotAllowed, DishModeModel
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
        ds_device_fqdn: str,
        spf_device_fqdn: str,
        spfrx_device_fqdn: str,
        *args,
        max_workers: int = 3,
        **kwargs,
    ):
        """"""
        # pylint: disable=useless-super-delegation
        self.sub_component_managers = None
        super().__init__(
            logger,
            *args,
            max_workers=max_workers,
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
            achievedpointing=[0.0, 0.0, 0.0],
            achievedpointingaz=[0.0, 0.0, 0.0],
            achievedpointingel=[0.0, 0.0, 0.0],
            configuredband=Band.NONE,
            attenuationpolh=0.0,
            attenuationpolv=0.0,
            kvalue=0,
            spfconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            spfrxconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            dsconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            band2pointingmodelparams=[],
            trackinterpolationmode=None,
            **kwargs,
        )
        self.logger = logger
        self._connection_state_callback = connection_state_callback
        self._dish_mode_model = DishModeModel()
        self._state_transition = StateTransition()
        self._command_tracker = command_tracker
        self._state_update_lock = Lock()
        self._sub_communication_state_change_lock = Lock()
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
                    self._sub_communication_state_changed, "spfConnectionState"
                ),
                component_state_callback=self._component_state_changed,
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
                achievedpointing=[0.0, 0.0, 0.0],
                achievedpointingaz=[0.0, 0.0, 0.0],
                achievedpointingel=[0.0, 0.0, 0.0],
                band2pointingmodelparams=[],
                trackinterpolationmode=TrackInterpolationMode.SPLINE,
                communication_state_callback=partial(
                    self._sub_communication_state_changed, "dsConnectionState"
                ),
                component_state_callback=self._component_state_changed,
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
                    self._sub_communication_state_changed, "spfrxConnectionState"
                ),
                component_state_callback=self._component_state_changed,
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
            "band2pointingmodelparams": [],
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
        with self._sub_communication_state_change_lock:
            if self.sub_component_managers:
                self._update_component_state(
                    spfconnectionstate=self.sub_component_managers["SPF"].communication_state
                )
                self._update_component_state(
                    spfrxconnectionstate=self.sub_component_managers["SPFRX"].communication_state
                )
                self._update_component_state(
                    dsconnectionstate=self.sub_component_managers["DS"].communication_state
                )

            if self.sub_component_managers:
                if not all(
                    (
                        self.sub_component_managers["DS"].component_state,
                        self.sub_component_managers["SPF"].component_state,
                        self.sub_component_managers["SPFRX"].component_state,
                    )
                ):
                    self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
                    self._update_component_state(healthstate=HealthState.UNKNOWN)
                    return

            if self.sub_component_managers:
                if all(
                    sub_component_manager.communication_state == CommunicationStatus.ESTABLISHED
                    for sub_component_manager in self.sub_component_managers.values()
                ):
                    self._update_communication_state(CommunicationStatus.ESTABLISHED)
                    ds_component_state = self.sub_component_managers["DS"].component_state
                    spf_component_state = self.sub_component_managers["SPF"].component_state
                    spfrx_component_state = self.sub_component_managers["SPFRX"].component_state

                    new_health_state = self._state_transition.compute_dish_health_state(
                        ds_component_state, spfrx_component_state, spf_component_state
                    )
                    new_dish_mode = self._state_transition.compute_dish_mode(
                        ds_component_state, spfrx_component_state, spf_component_state
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
        if not all(
            (
                self.sub_component_managers["DS"].component_state,
                self.sub_component_managers["SPF"].component_state,
                self.sub_component_managers["SPFRX"].component_state,
            )
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
                spfrx_component_state,
                spf_component_state,
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
                spfrx_component_state,
                spf_component_state,
            )
            self._update_component_state(healthstate=new_health_state)

        if "pointingstate" in kwargs:
            self.logger.debug(
                ("Newly calculated pointing state [pointing_state] [%s]"),
                ds_component_state["pointingstate"],
            )
            self._update_component_state(pointingstate=ds_component_state["pointingstate"])

            if ds_component_state["pointingstate"] in [
                PointingState.SLEW,
                PointingState.READY,
            ]:
                self._update_component_state(achievedtargetlock=False)
            elif ds_component_state["pointingstate"] == PointingState.TRACK:
                self._update_component_state(achievedtargetlock=True)

        # spf bandInFocus
        if "indexerposition" in kwargs or "configuredband" in kwargs:
            band_in_focus = self._state_transition.compute_spf_band_in_focus(
                ds_component_state, spfrx_component_state
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
                spfrx_component_state,
                spf_component_state,
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
                    spfrx_component_state,
                    spf_component_state,
                    self.component_state,
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
                    spfrx_component_state,
                    spf_component_state,
                    self.component_state,
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
                    new_value = ds_component_state[attr_lower]

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

    def _track_load_table(
        self, sequence_length: int, table: list[float], load_mode: TrackTableLoadMode
    ) -> None:
        """Load the track table."""
        self.logger.debug("Calling track load table on DSManager.")
        device_proxy = tango.DeviceProxy(self.sub_component_managers["DS"]._tango_device_fqdn)
        float_list = [load_mode, sequence_length]
        float_list.extend(table)

        device_proxy.trackLoadTable(float_list)

    def sync_component_states(self):
        """
        Sync monitored attributes on component managers with their respective sub devices

        Clear the monitored attributes of all subservient device component managers,
        then re-read all the monitored attributes from their respective tango device
        to force dishManager to recalculate its attributes.
        """
        if self.sub_component_managers:
            for component_manager in self.sub_component_managers.values():
                component_manager.clear_monitored_attributes()
                component_manager.update_state_from_monitored_attributes()

    def start_communicating(self):
        """Connect from monitored devices"""
        if self.sub_component_managers:
            for component_manager in self.sub_component_managers.values():
                component_manager.start_communicating()

    def set_standby_lp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_LP mode"""

        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetStandbyLPMode",
            task_callback=task_callback,
        )
        status, response = self.submit_task(
            self._command_map.set_standby_lp_mode, args=[], task_callback=task_callback
        )
        return status, response

    def set_standby_fp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_FP mode"""
        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetStandbyFPMode",
            task_callback=task_callback,
        )
        status, response = self.submit_task(
            self._command_map.set_standby_fp_mode, args=[], task_callback=task_callback
        )

        return status, response

    def set_operate_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to OPERATE mode"""

        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetOperateMode",
            task_callback=task_callback,
        )

        if self.component_state["configuredband"] in [
            Band.NONE,
            Band.UNKNOWN,
        ]:
            ex = CommandNotAllowed(
                "configuredBand can not be in " f"{Band.NONE.name} or {Band.UNKNOWN.name}",
            )
            if task_callback:
                task_callback(status=TaskStatus.REJECTED, exception=(ResultCode.REJECTED, ex))
            raise ex

        status, response = self.submit_task(
            self._command_map.set_operate_mode, args=[], task_callback=task_callback
        )
        return status, response

    def track_cmd(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the pointing state"""
        dish_mode = self.component_state["dishmode"].name
        if dish_mode != "OPERATE":
            ex = CommandNotAllowed(
                f"Track command only allowed in `OPERATE` mode. Current dishMode: {dish_mode}."
            )
            if task_callback:
                task_callback(status=TaskStatus.REJECTED, exception=(ResultCode.REJECTED, ex))
            raise ex

        status, response = self.submit_task(
            self._command_map.track_cmd, args=[], task_callback=task_callback
        )
        return status, response

    def track_stop_cmd(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Stop tracking"""
        dish_mode = self.component_state["dishmode"]
        pointing_state = self.component_state["pointingstate"]
        if dish_mode != DishMode.OPERATE or pointing_state not in [
            PointingState.TRACK,
            PointingState.SLEW,
        ]:
            ex = CommandNotAllowed(
                f"Track Stop command only allowed in `OPERATE` dish mode and in `TRACK` and `SLEW`"
                f"pointing states. Current dishMode: {dish_mode}, pointingState: {pointing_state}"
            )
            if task_callback:
                task_callback(status=TaskStatus.REJECTED, exception=(ResultCode.REJECTED, ex))
            raise ex

        status, response = self.submit_task(
            self._command_map.track_stop_cmd, args=[], task_callback=task_callback
        )
        return status, response

    def configure_band_cmd(
        self,
        band_number,
        synchronise,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Configure frequency band"""
        band_enum = Band[f"B{band_number}"]
        requested_cmd = f"ConfigureBand{band_number}"

        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name=requested_cmd,
            task_callback=task_callback,
        )

        if self.component_state["configuredband"] == band_enum:
            if task_callback:
                task_callback(
                    status=TaskStatus.REJECTED,
                    result=(ResultCode.REJECTED, f"Already in band {band_enum.name}"),
                )
            return TaskStatus.REJECTED, f"Already in band {band_enum.name}"

        status, response = self.submit_task(
            self._command_map.configure_band_cmd,
            args=[band_number, synchronise],
            task_callback=task_callback,
        )
        return status, response

    def set_stow_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STOW mode"""

        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetStowMode",
            task_callback=task_callback,
        )
        status, response = self.submit_task(
            self._command_map.set_stow_mode, args=[], task_callback=task_callback
        )
        return status, response

    def slew(
        self,
        values: list[float],
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Slew the dish."""
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
        status, response = self.submit_task(
            self._command_map.scan, args=[scanid], task_callback=task_callback
        )
        return status, response

    def end_scan(
        self,
        scanid: str,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Unset the scanned target."""
        status, response = self.submit_task(
            self._command_map.end_scan, args=[scanid], task_callback=task_callback
        )
        return status, response

    def track_load_static_off(
        self,
        values: list[float],
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Load the static pointing model offsets."""
        status, response = self.submit_task(
            self._command_map.track_load_static_off, args=[values], task_callback=task_callback
        )
        return status, response

    def set_kvalue(
        self,
        k_value,
    ) -> Tuple[ResultCode, str]:
        """Set the k-value on the SPFRx"""
        spfrx_cm = self.sub_component_managers["SPFRX"]
        try:
            spfrx_cm.write_attribute_value("kvalue", k_value)
        except LostConnection:
            return (ResultCode.REJECTED, "Lost connection to SPFRx")
        return (ResultCode.OK, "SetKValue command completed OK")

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

    # pylint: disable=missing-function-docstring
    def stop_communicating(self):
        """Disconnect from monitored devices"""
        if self.sub_component_managers:
            for component_manager in self.sub_component_managers.values():
                component_manager.stop_communicating()
