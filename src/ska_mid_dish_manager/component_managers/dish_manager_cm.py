# pylint: disable=protected-access
"""Component manager for a DishManager tango device"""
from functools import partial
import json
import logging
from datetime import datetime
from threading import Lock
from typing import Callable, Optional, Tuple

from ska_control_model import CommunicationStatus, HealthState, TaskStatus
from ska_tango_base.commands import SubmittedSlowCommand
from ska_tango_base.executor import TaskExecutorComponentManager

from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.component_managers.spf_cm import SPFComponentManager
from ska_mid_dish_manager.component_managers.spfrx_cm import SPFRxComponentManager
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
)
from ska_mid_dish_manager.models.dish_mode_model import CommandNotAllowed, DishModeModel
from ska_mid_dish_manager.models.dish_state_transition import StateTransition


# pylint: disable=abstract-method
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
        *args,
        ds_device_fqdn: str = "mid_d0001/lmc/ds_simulator",
        spf_device_fqdn: str = "mid_d0001/spf/simulator",
        spfrx_device_fqdn: str = "mid_d0001/spfrx/simulator",
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
            achievedpointing=[0.0, 0.0, 30.0],
            configuredband=Band.NONE,
            spfconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            spfrxconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            dsconnectionstate=CommunicationStatus.NOT_ESTABLISHED,
            **kwargs,
        )
        self.logger = logger
        self._connection_state_callback = connection_state_callback
        self._dish_mode_model = DishModeModel()
        self._state_transition = StateTransition()
        self._command_tracker = command_tracker
        self._state_update_lock = Lock()
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
                operatingmode=DSOperatingMode.UNKNOWN,
                pointingstate=None,
                achievedtargetlock=None,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.UNKNOWN,
                achievedpointing=[0.0, 0.0, 30.0],
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
        }
        self._update_component_state(**initial_component_states)
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

    # pylint: disable=unused-argument
    def _sub_communication_state_changed(
        self, attribute_name: str, communication_state: CommunicationStatus = None
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
                self._update_component_state(healthstate=new_health_state)
            else:
                self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
                self._update_component_state(healthstate=HealthState.UNKNOWN)

        self._component_state_changed()

        # push change events for the connection state attributes
        self._connection_state_callback(attribute_name)

    # pylint: disable=unused-argument, too-many-branches
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

        if "achievedpointing" in kwargs:
            self.logger.debug(
                ("Updating achievedPointing with DS achievedPointing [%s]"),
                ds_component_state["achievedpointing"],
            )
            new_position = ds_component_state["achievedpointing"]
            self._update_component_state(achievedpointing=new_position)

        # Only update dishMode if there are operatingmode changes
        if "operatingmode" in kwargs:
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
            # pylint: disable=protected-access
            # update the bandInFocus of SPF before configuredBand
            # component state changed for DS and SPFRx may be triggered while
            # SPF device proxy is not initialised. Write to the bandInFocus
            # only when you have the device proxy
            spf_component_manager = self.sub_component_managers["SPF"]
            spf_component_manager.write_attribute_value("bandInFocus", band_in_focus)

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
            for band in ["b1", "b2", "b3", "b4", "b5a", "b5b"]:
                cap_state_name = f"{band}capabilitystate"
                new_state = self._state_transition.compute_capability_state(
                    band,
                    ds_component_state,
                    spfrx_component_state,
                    spf_component_state,
                    self.component_state,
                )
                self._update_component_state(**{cap_state_name: new_state})

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
        if self.sub_component_managers:
            for component_manager in self.sub_component_managers.values():
                component_manager.clear_monitored_attributes()
                component_manager.update_state_from_monitored_attributes()

    def start_communicating(self):
        """Connect from monitored devices"""
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
        )
        status, response = self.submit_task(
            self._set_standby_lp_mode, args=[], task_callback=task_callback
        )
        return status, response

    def _set_standby_lp_mode(self, task_callback=None, task_abort_event=None):
        assert task_callback, "task_callback has to be defined"
        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result="SetStandbyLPMode Aborted",
                progress="SetStandbyLPMode Aborted",
            )
            return
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        subservient_devices = [
            ("DS", "SetStandbyLPMode"),
            ("SPF", "SetStandbyLPMode"),
            ("SPFRX", "SetStandbyMode"),
        ]

        # TODO clarify code below, SPFRX stays in DATA_CAPTURE when we dont
        # execute setstandby on it. So going from LP to FP never completes
        # since dishMode does not update.
        #
        # if self.component_state["dishmode"].name == "STANDBY_FP":
        #     subservient_devices = ["DS", "SPF"]

        for device, command_name in subservient_devices:
            command = SubmittedSlowCommand(
                f"{device}_{command_name}",
                self._command_tracker,
                self.sub_component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "SPFRX":
                _, command_id = command(command_name, None)
                task_callback(progress=f"{command_name} called on SPFRX, ID {command_id}")
            else:
                _, command_id = command(command_name, None)
                task_callback(progress=f"{command_name} called on {device}, ID {command_id}")

            device_command_ids[device] = command_id

        task_callback(progress=f"Commands: {json.dumps(device_command_ids)}")
        task_callback(progress="Awaiting dishMode change to STANDBY_LP")

        while True:
            if task_abort_event.is_set():
                task_callback(
                    status=TaskStatus.ABORTED,
                    progress="SetStandbyLPMode Aborted",
                    result="SetStandbyLPMode Aborted",
                )
                return

            current_dish_mode = self.component_state["dishmode"]
            if current_dish_mode != DishMode.STANDBY_LP:
                task_abort_event.wait(timeout=1)
                for component_manager in self.sub_component_managers.values():
                    component_manager.update_state_from_monitored_attributes()

            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    progress="SetStandbyLPMode completed",
                    result="SetStandbyLPMode completed",
                )
                return

    def set_standby_fp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_FP mode"""
        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetStandbyFPMode",
        )
        status, response = self.submit_task(
            self._set_standby_fp_mode, args=[], task_callback=task_callback
        )
        return status, response

    def _set_standby_fp_mode(self, task_callback=None, task_abort_event=None):
        """Set StandbyFP mode on sub devices as long running commands"""
        assert task_callback, "task_callback has to be defined"
        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result="SetStandbyFPMode Aborted",
                progress="SetStandbyFPMode Aborted",
            )
            return
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        subservient_devices = [
            ("DS", "SetStandbyFPMode"),
            ("SPF", "SetOperateMode"),
        ]

        if self.component_state["dishmode"].name == "OPERATE":
            subservient_devices = [("DS", "SetStandbyFPMode")]

        for device, command_name in subservient_devices:
            command = SubmittedSlowCommand(
                f"{device}_{command_name}",
                self._command_tracker,
                self.sub_component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "DS":
                _, command_id = command(command_name, None)
                device_command_ids[device] = command_id
                task_callback(progress=f"{command_name} called on DS, ID {command_id}")
            if device == "SPF":
                _, command_id = command(command_name, None)
                device_command_ids[device] = command_id
                task_callback(progress=f"{command_name} called on SPF, ID {command_id}")

        task_callback(progress=f"Commands: {json.dumps(device_command_ids)}")
        task_callback(progress="Awaiting dishMode change to STANDBY_FP")

        while True:
            if task_abort_event.is_set():
                task_callback(
                    status=TaskStatus.ABORTED,
                    progress="SetStandbyFPMode Aborted",
                    result="SetStandbyFPMode Aborted",
                )
                return

            current_dish_mode = self.component_state["dishmode"]
            if current_dish_mode != DishMode.STANDBY_FP:
                task_abort_event.wait(timeout=1)
                for component_manager in self.sub_component_managers.values():
                    component_manager.update_state_from_monitored_attributes()
            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    progress="SetStandbyFPMode completed",
                    result="SetStandbyFPMode completed",
                )
                return

    def set_operate_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to OPERATE mode"""

        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetOperateMode",
        )

        if self.component_state["configuredband"] in [
            Band.NONE,
            Band.UNKNOWN,
        ]:
            raise CommandNotAllowed(
                "configuredBand can not be in " f"{Band.NONE.name} or {Band.UNKNOWN.name}",
            )

        status, response = self.submit_task(
            self._set_operate_mode, args=[], task_callback=task_callback
        )
        return status, response

    def _set_operate_mode(self, task_callback=None, task_abort_event=None):
        assert task_callback, "task_callback has to be defined"
        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result="SetOperateMode Aborted",
                progress="SetOperateMode Aborted",
            )
            return
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        for device, command_name in [
            ("DS", "SetPointMode"),
            ("SPF", "SetOperateMode"),
            ("SPFRX", "CaptureData"),
        ]:
            command = SubmittedSlowCommand(
                f"{device}_{command_name}",
                self._command_tracker,
                self.sub_component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "DS":
                _, command_id = command(command_name, None)
                task_callback(progress=f"{command_name} called on DS, ID {command_id}")
            elif device == "SPF":
                _, command_id = command(command_name, None)
                task_callback(progress=f"{command_name} called on SPF, ID {command_id}")
            else:
                _, command_id = command(command_name, True)
                task_callback(progress=f"{command_name} called on SPFRx, ID {command_id}")

            device_command_ids[device] = command_id

        task_callback(progress=f"Commands: {json.dumps(device_command_ids)}")
        task_callback(progress="Awaiting dishMode change to OPERATE")

        while True:
            if task_abort_event.is_set():
                task_callback(
                    status=TaskStatus.ABORTED,
                    progress="SetOperateMode Aborted",
                    result="SetOperateMode Aborted",
                )
                return

            current_dish_mode = self.component_state["dishmode"]
            if current_dish_mode != DishMode.OPERATE:
                task_abort_event.wait(timeout=1)
                for component_manager in self.sub_component_managers.values():
                    component_manager.update_state_from_monitored_attributes()
            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    progress="SetOperateMode completed",
                    result="SetOperateMode completed",
                )
                return

    def track_cmd(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the pointing state"""
        dish_mode = self.component_state["dishmode"].name
        if dish_mode != "OPERATE":
            raise CommandNotAllowed(
                "Track command only allowed in `OPERATE`" f"mode. Current dishMode: {dish_mode}."
            )

        status, response = self.submit_task(self._track_cmd, args=[], task_callback=task_callback)
        return status, response

    def _track_cmd(self, task_callback=None, task_abort_event=None):
        assert task_callback, "task_callback has to be defined"
        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result="Track Aborted",
                progress="Track Aborted",
            )
            return
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        command = SubmittedSlowCommand(
            "DS_Track",
            self._command_tracker,
            self.sub_component_managers["DS"],
            "run_device_command",
            callback=None,
            logger=self.logger,
        )
        _, command_id = command("Track", None)
        device_command_ids["DS"] = command_id

        task_callback(progress=f"Track called on DS, ID {command_id}")
        task_callback(progress="Awaiting target lock change")

        while True:
            if task_abort_event.is_set():
                task_callback(
                    status=TaskStatus.ABORTED,
                    progress="Track Aborted",
                    result="Track Aborted",
                )
                return

            achieved_target_lock = self.component_state["achievedtargetlock"]
            if not achieved_target_lock:
                task_abort_event.wait(timeout=1)

                # Read pointingState on DS and update state
                component_manager = self.sub_component_managers["DS"]
                component_manager.update_state_from_monitored_attributes()

            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    progress="Track completed",
                    result="Track completed",
                )
                return

    def configure_band2_cmd(
        self,
        activation_timestamp,
        current_configured_band,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Configure frequency band to band 2"""

        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="ConfigureBand2",
        )

        if current_configured_band == Band.B2:
            return TaskStatus.REJECTED, f"Already in band {Band.B2.name}"

        # TODO Check if ConfigureBand2 is already running

        # check timestamp is in the future
        try:
            if datetime.fromisoformat(activation_timestamp) <= datetime.utcnow():
                return (
                    TaskStatus.REJECTED,
                    f"{activation_timestamp} is not in the future",
                )
        except ValueError as err:
            self.logger.exception(err)
            return TaskStatus.REJECTED, str(err)

        status, response = self.submit_task(
            self._configure_band2_cmd,
            args=[],
            task_callback=task_callback,
        )
        return status, response

    def _configure_band2_cmd(self, task_callback=None, task_abort_event=None):
        """configureBand on DS, SPF, SPFRX"""
        assert task_callback, "task_callback has to be defined"
        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result="ConfigureBand2 Aborted",
                progress="ConfigureBand2 Aborted",
            )
            return
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        for device in ["DS", "SPFRX"]:
            command = SubmittedSlowCommand(
                f"{device}ConfigureBand2",
                self._command_tracker,
                self.sub_component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "DS":
                _, command_id = command("SetIndexPosition", 2)
                task_callback(
                    progress=f"SetIndexPosition called on DS, ID {command_id}"  # noqa: E501
                )
            else:
                _, command_id = command("ConfigureBand2", None)
                task_callback(
                    progress=f"ConfigureBand2 called on SPFRx, ID {command_id}"  # noqa: E501
                )

            device_command_ids[device] = command_id

        task_callback(progress="Awaiting configuredband to transition to [B2]")
        while True:
            if task_abort_event.is_set():
                task_callback(
                    status=TaskStatus.ABORTED,
                    progress="ConfigureBand2 Aborted",
                    result="ConfigureBand2 Aborted",
                )
                return

            current_band = self.component_state["configuredband"]
            if current_band != Band.B2:
                task_abort_event.wait(timeout=1)

                # Read the appropriate attrs and update states.
                # DS indexerposition
                # SPFRx configuredband
                # SPF bandinfocus
                for component_manager in self.sub_component_managers.values():
                    component_manager.update_state_from_monitored_attributes()

            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    progress="ConfigureBand2 completed",
                    result="ConfigureBand2 completed",
                )
                return

    def set_stow_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STOW mode"""

        self._dish_mode_model.is_command_allowed(
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetStowMode",
        )
        status, response = self.submit_task(
            self._set_stow_mode, args=[], task_callback=task_callback
        )
        return status, response

    def _set_stow_mode(self, task_callback=None, task_abort_event=None):
        """Call Stow on DS"""
        assert task_callback, "task_callback has to be defined"
        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result="SetStowMode Aborted",
                progress="SetStowMode Aborted",
            )
            return
        task_callback(status=TaskStatus.IN_PROGRESS)

        command = SubmittedSlowCommand(
            "DS_SetStowMode",
            self._command_tracker,
            self.sub_component_managers["DS"],
            "run_device_command",
            callback=None,
            logger=self.logger,
        )
        _, command_id = command("Stow", None)

        task_callback(progress=f"Stow called on DS, ID {command_id}")
        task_callback(progress="Waiting for dishMode change to STOW")

        while True:
            if task_abort_event.is_set():
                task_callback(
                    status=TaskStatus.ABORTED,
                    progress="Stow Aborted",
                    result="Stow Aborted",
                )
                return

            current_dish_mode = self.component_state["dishmode"]
            if current_dish_mode != DishMode.STOW:
                task_abort_event.wait(timeout=1)
                for component_manager in self.sub_component_managers.values():
                    component_manager.update_state_from_monitored_attributes()
            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    progress="Stow completed",
                    result="Stow completed",
                )
                return

    # pylint: disable=missing-function-docstring
    def stop_communicating(self):
        """Disconnect from monitored devices"""
        for component_manager in self.sub_component_managers.values():
            component_manager.stop_communicating()
