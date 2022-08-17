"""Component manager for a DishManager tango device"""
import json
import logging
from datetime import datetime
from typing import Callable, Optional, Tuple

from ska_tango_base.base.component_manager import TaskExecutorComponentManager
from ska_tango_base.commands import SubmittedSlowCommand
from ska_tango_base.control_model import CommunicationStatus, HealthState
from ska_tango_base.executor import TaskStatus

from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.component_managers.spf_cm import SPFComponentManager
from ska_mid_dish_manager.component_managers.spfrx_cm import (
    SPFRxComponentManager,
)
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    CapabilityStates,
    DishMode,
    IndexerPosition,
    PointingState,
    SPFCapabilityStates,
    SPFPowerState,
    SPFRxCapabilityStates,
)
from ska_mid_dish_manager.models.dish_mode_model import (
    CommandNotAllowed,
    DishModeModel,
)


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
        *args,
        ds_device_fqdn: str = "mid_d0001/lmc/ds_simulator",
        spf_device_fqdn: str = "mid_d0001/spf/simulator",
        spfrx_device_fqdn: str = "mid_d0001/spfrx/simulator",
        max_workers: int = 3,
        **kwargs,
    ):
        """"""
        # pylint: disable=useless-super-delegation
        super().__init__(
            logger,
            *args,
            max_workers=max_workers,
            dish_mode=None,
            health_state=None,
            pointing_state=None,
            b1capabilitystate=None,
            b2capabilitystate=None,
            b3capabilitystate=None,
            b4capabilitystate=None,
            b5acapabilitystate=None,
            b5bcapabilitystate=None,
            achieved_target_lock=None,
            configured_band=Band.NONE,
            **kwargs,
        )
        self._dish_mode_model = DishModeModel()
        self._command_tracker = command_tracker
        self.component_managers = {}
        self.component_managers["DS"] = DSComponentManager(
            ds_device_fqdn,
            logger,
            operatingmode=None,
            pointingstate=None,
            achievedtargetlock=None,
            indexerposition=IndexerPosition.UNKNOWN,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPFRX"] = SPFRxComponentManager(
            spfrx_device_fqdn,
            logger,
            operatingmode=None,
            configuredband=Band.NONE,
            healthstate=HealthState.UNKNOWN,
            b1capabilitystate=SPFRxCapabilityStates.UNKNOWN,
            b2capabilitystate=SPFRxCapabilityStates.UNKNOWN,
            b3capabilitystate=SPFRxCapabilityStates.UNKNOWN,
            b4capabilitystate=SPFRxCapabilityStates.UNKNOWN,
            b5acapabilitystate=SPFRxCapabilityStates.UNKNOWN,
            b5bcapabilitystate=SPFRxCapabilityStates.UNKNOWN,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPF"] = SPFComponentManager(
            spf_device_fqdn,
            logger,
            operatingmode=None,
            powerstate=SPFPowerState.UNKNOWN,
            healthstate=HealthState.UNKNOWN,
            bandinfocus=BandInFocus.UNKNOWN,
            b1capabilitystate=SPFCapabilityStates.UNKNOWN,
            b2capabilitystate=SPFCapabilityStates.UNKNOWN,
            b3capabilitystate=SPFCapabilityStates.UNKNOWN,
            b4capabilitystate=SPFCapabilityStates.UNKNOWN,
            b5acapabilitystate=SPFCapabilityStates.UNKNOWN,
            b5bcapabilitystate=SPFCapabilityStates.UNKNOWN,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self._update_component_state(dish_mode=DishMode.STARTUP)
        self._update_component_state(health_state=HealthState.UNKNOWN)
        self._update_component_state(configured_band=Band.NONE)
        self._update_component_state(
            b1capabilitystate=CapabilityStates.UNKNOWN
        )
        self._update_component_state(
            b2capabilitystate=CapabilityStates.UNKNOWN
        )
        self._update_component_state(
            b3capabilitystate=CapabilityStates.UNKNOWN
        )
        self._update_component_state(
            b4capabilitystate=CapabilityStates.UNKNOWN
        )
        self._update_component_state(
            b5acapabilitystate=CapabilityStates.UNKNOWN
        )
        self._update_component_state(
            b5bcapabilitystate=CapabilityStates.UNKNOWN
        )

    # pylint: disable=unused-argument
    def _communication_state_changed(self, *args, **kwargs):
        # communication state will come from args and kwargs

        # an empty dict will make all condition always pass. check
        # that the dict is not empty before continuing with trigger
        if self.component_managers:
            if all(
                cm.communication_state == CommunicationStatus.ESTABLISHED
                for cm in self.component_managers.values()
            ):
                self._update_communication_state(
                    CommunicationStatus.ESTABLISHED
                )
                # Automatic transition to LP mode on startup should come from
                # operating modes ofsubservient devices. Likewise, any
                # reconnection gained should be accompanied with fresh
                # attribute updates
                self._component_state_changed()
            else:
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                self._update_component_state(health_state=HealthState.FAILED)

    # pylint: disable=unused-argument
    def _component_state_changed(self, *args, **kwargs):

        ds_comp_state = self.component_managers["DS"].component_state
        spf_comp_state = self.component_managers["SPF"].component_state
        spfrx_comp_state = self.component_managers["SPFRX"].component_state

        # Only update dishMode if there are operatingmode changes
        operating_modes = [
            comp_state.get("operatingmode", None)
            for comp_state in [ds_comp_state, spfrx_comp_state, spf_comp_state]
        ]
        if any(operating_modes):
            self.logger.info(
                (
                    "Updating dishMode with operatingModes DS"
                    " [%s], SPF [%s], SPFRX [%s]"
                ),
                str(ds_comp_state["operatingmode"]),
                str(spf_comp_state["operatingmode"]),
                str(spfrx_comp_state["operatingmode"]),
            )
            new_dish_mode = self._dish_mode_model.compute_dish_mode(
                ds_comp_state,
                spfrx_comp_state,
                spf_comp_state,
            )
            self._update_component_state(dish_mode=new_dish_mode)

        if (
            "healthstate" in ds_comp_state
            and "healthstate" in spf_comp_state
            and "healthstate" in spfrx_comp_state
        ):
            new_health_state = self._dish_mode_model.compute_dish_health_state(
                ds_comp_state,
                spfrx_comp_state,
                spf_comp_state,
            )
            self._update_component_state(health_state=new_health_state)

        if ds_comp_state["pointingstate"] is not None:
            self._update_component_state(
                pointing_state=ds_comp_state["pointingstate"]
            )

        if ds_comp_state["pointingstate"] in [
            PointingState.SLEW,
            PointingState.READY,
        ]:
            self._update_component_state(achieved_target_lock=False)
        elif ds_comp_state["pointingstate"] == PointingState.TRACK:
            self._update_component_state(achieved_target_lock=True)

        # spf bandInFocus
        if (
            "indexerposition" in ds_comp_state
            and "configuredband" in spfrx_comp_state
        ):
            band_in_focus = self._dish_mode_model.compute_spf_band_in_focus(
                ds_comp_state, spfrx_comp_state
            )
            # pylint: disable=protected-access
            # update the bandInFocus of SPF before configuredBand
            spf_proxy = self.component_managers["SPF"]._device_proxy
            # component state changed for DS and SPFRx may be triggered while
            # SPF device proxy is not initialised. Write to the bandInFocus
            # only when you have the device proxy
            if spf_proxy:
                spf_proxy.write_attribute("bandInFocus", band_in_focus)

        # configuredBand
        if (
            "indexerposition" in ds_comp_state
            and "bandinfocus" in spf_comp_state
            and "configuredband" in spfrx_comp_state
        ):
            configured_band = self._dish_mode_model.compute_configured_band(
                ds_comp_state,
                spfrx_comp_state,
                spf_comp_state,
            )
            self._update_component_state(configured_band=configured_band)

        # CapabilityStates
        # Update all CapabilityStates when indexerposition, dish_mode
        # or operatingmode changes
        if (
            "indexerposition" in kwargs
            or "dish_mode" in kwargs
            or "operatingmode" in kwargs
        ):
            for band in ["b1", "b2", "b3", "b4", "b5a", "b5b"]:
                cap_state_name = f"{band}capabilitystate"
                new_state = self._dish_mode_model.compute_capability_state(
                    band,
                    ds_comp_state,
                    spfrx_comp_state,
                    spf_comp_state,
                    self.component_state,
                )
                self._update_component_state(**{cap_state_name: new_state})

        # Update individual CapabilityStates if it changes
        for band in ["b1", "b2", "b3", "b4", "b5a", "b5b"]:
            cap_state_name = f"{band}capabilitystate"
            if cap_state_name in kwargs:
                new_state = self._dish_mode_model.compute_capability_state(
                    band,
                    ds_comp_state,
                    spfrx_comp_state,
                    spf_comp_state,
                    self.component_state,
                )
                self._update_component_state(**{cap_state_name: new_state})

    # pylint: disable=missing-function-docstring
    def start_communicating(self):
        for com_man in self.component_managers.values():
            com_man.start_communicating()

    def set_standby_lp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_LP mode"""

        self._dish_mode_model.is_command_allowed(
            dish_mode=DishMode(self.component_state["dish_mode"]).name,
            command_name="SetStandbyLPMode",
        )
        status, response = self.submit_task(
            self._set_standby_lp_mode, args=[], task_callback=task_callback
        )
        return status, response

    def _set_standby_lp_mode(self, task_callback=None, task_abort_event=None):
        assert task_callback, "task_callback has to be defined"
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        subservient_devices = ["DS", "SPF", "SPFRX"]

        if self.component_state["dish_mode"].name == "STANDBY_FP":
            subservient_devices = ["DS", "SPF"]

        for device in subservient_devices:
            command = SubmittedSlowCommand(
                f"{device}_SetStandbyLPMode",
                self._command_tracker,
                self.component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "SPFRX":
                _, command_id = command("SetStandbyMode", None)
                task_callback(
                    progress=f"SetStandbyMode called on SPFRX, ID {command_id}"
                )
            else:
                _, command_id = command("SetStandbyLPMode", None)
                task_callback(
                    progress=(
                        f"SetStandbyLPMode called on {device},"
                        f" ID {command_id}"
                    )
                )

            device_command_ids[device] = command_id

        task_callback(progress=f"Commands: {json.dumps(device_command_ids)}")
        task_callback(progress="Awaiting dishMode change to STANDBY_LP")

        while True:
            if task_abort_event.is_set():
                task_callback(
                    status=TaskStatus.ABORTED,
                    result="SetStandbyLPMode Aborted",
                )
                return

            if self.communication_state == CommunicationStatus.NOT_ESTABLISHED:
                task_callback(
                    status=TaskStatus.ABORTED,
                    result="Lost communication with monitored device",
                )
                return

            current_dish_mode = self.component_state["dish_mode"]
            if current_dish_mode != DishMode.STANDBY_LP:
                task_abort_event.wait(timeout=1)
            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result="SetStandbyLPMode completed",
                )
                return

    def set_standby_fp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_LP mode"""
        self._dish_mode_model.is_command_allowed(
            dish_mode=DishMode(self.component_state["dish_mode"]).name,
            command_name="SetStandbyFPMode",
        )
        status, response = self.submit_task(
            self._set_standby_fp_mode, args=[], task_callback=task_callback
        )
        return status, response

    def _set_standby_fp_mode(self, task_callback=None, task_abort_event=None):
        """Set StandbyFP mode on sub devices as long running commands"""
        assert task_callback, "task_callback has to be defined"
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        subservient_devices = ["DS", "SPF", "SPFRX"]

        if self.component_state["dish_mode"].name == "OPERATE":
            subservient_devices = ["DS"]

        for device in subservient_devices:
            command = SubmittedSlowCommand(
                f"{device}_SetStandbyFPMode",
                self._command_tracker,
                self.component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "DS":
                _, command_id = command("SetStandbyFPMode", None)
                device_command_ids[device] = command_id
                task_callback(
                    progress=f"SetStandbyFPMode called on DS, ID {command_id}"
                )
            elif device == "SPF":
                _, command_id = command("SetOperateMode", None)
                device_command_ids[device] = command_id
                task_callback(
                    progress=f"SetOperateMode called on SPF, ID {command_id}"
                )
            else:
                _, command_id = command("CaptureData", True)
                device_command_ids[device] = command_id
                task_callback(
                    progress=f"CaptureData called on SPFRx, ID {command_id}"
                )

        task_callback(progress=f"Commands: {json.dumps(device_command_ids)}")
        task_callback(progress="Awaiting dishMode change to STANDBY_FP")

        while True:
            if task_abort_event.is_set():
                task_callback(
                    status=TaskStatus.ABORTED,
                    result="SetStandbyFPMode Aborted",
                )
                return

            if self.communication_state == CommunicationStatus.NOT_ESTABLISHED:
                task_callback(
                    status=TaskStatus.ABORTED,
                    result="Lost communication with monitored device",
                )
                return

            current_dish_mode = self.component_state["dish_mode"]
            if current_dish_mode != DishMode.STANDBY_FP:
                task_abort_event.wait(timeout=1)
            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result="SetStandbyFPMode completed",
                )
                return

    def set_operate_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to OPERATE mode"""

        self._dish_mode_model.is_command_allowed(
            dish_mode=DishMode(self.component_state["dish_mode"]).name,
            command_name="SetOperateMode",
        )

        if self.component_state["configured_band"] in [
            Band.NONE,
            Band.UNKNOWN,
        ]:
            raise CommandNotAllowed(
                "configuredBand can not be in "
                f"{Band.NONE.name} or {Band.UNKNOWN.name}",
            )

        status, response = self.submit_task(
            self._set_operate_mode, args=[], task_callback=task_callback
        )
        return status, response

    def _set_operate_mode(self, task_callback=None, task_abort_event=None):
        assert task_callback, "task_callback has to be defined"
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        for device in ["DS", "SPF", "SPFRX"]:
            command = SubmittedSlowCommand(
                f"{device}_SetOperateMode",
                self._command_tracker,
                self.component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "DS":
                _, command_id = command("SetPointMode", None)
                task_callback(
                    progress=f"SetPointMode called on DS, ID {command_id}"
                )
            elif device == "SPF":
                _, command_id = command("SetOperateMode", None)
                task_callback(
                    progress=f"SetOperateMode called on SPF, ID {command_id}"
                )
            else:
                _, command_id = command("CaptureData", True)
                task_callback(
                    progress=f"CaptureData called on SPFRx, ID {command_id}"
                )

            device_command_ids[device] = command_id

        task_callback(progress=f"Commands: {json.dumps(device_command_ids)}")
        task_callback(progress="Awaiting dishMode change to OPERATE")

        while True:
            if task_abort_event.is_set():
                task_callback(
                    status=TaskStatus.ABORTED,
                    result="SetOperateMode Aborted",
                )
                return

            if self.communication_state == CommunicationStatus.NOT_ESTABLISHED:
                task_callback(
                    status=TaskStatus.ABORTED,
                    result="Lost communication with monitored device",
                )
                return

            current_dish_mode = self.component_state["dish_mode"]
            if current_dish_mode != DishMode.OPERATE:
                task_abort_event.wait(timeout=1)
            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result="SetOperateMode completed",
                )
                return

    def track_cmd(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to OPERATE mode"""
        dish_mode = self.component_state["dish_mode"].name
        if dish_mode != "OPERATE":
            raise CommandNotAllowed(
                "Track command only allowed in `OPERATE`"
                f"mode. Current dishMode: {dish_mode}."
            )

        status, response = self.submit_task(
            self._track_cmd, args=[], task_callback=task_callback
        )
        return status, response

    def _track_cmd(self, task_callback=None, task_abort_event=None):
        assert task_callback, "task_callback has to be defined"
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        command = SubmittedSlowCommand(
            "DS_Track",
            self._command_tracker,
            self.component_managers["DS"],
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
                    result="Track Aborted",
                )
                return

            if self.communication_state == CommunicationStatus.NOT_ESTABLISHED:
                task_callback(
                    status=TaskStatus.ABORTED,
                    result="Lost communication with monitored device",
                )
                return

            achieved_target_lock = self.component_state["achieved_target_lock"]
            if not achieved_target_lock:
                task_abort_event.wait(timeout=1)
            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
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
            dish_mode=DishMode(self.component_state["dish_mode"]).name,
            command_name="ConfigureBand2",
        )

        if current_configured_band == Band.B2:
            return TaskStatus.COMPLETED, f"Already in band {Band.B2}"

        # TODO Check if ConfigureBand2 is already running

        # check timestamp is in the future
        try:
            if (
                datetime.fromisoformat(activation_timestamp)
                <= datetime.utcnow()
            ):
                return (
                    TaskStatus.FAILED,
                    f"{activation_timestamp} is not in the future",
                )
        except ValueError as err:
            self.logger.exception(err)
            return TaskStatus.FAILED, str(err)

        status, response = self.submit_task(
            self._configure_band2_cmd,
            args=[],
            task_callback=task_callback,
        )
        return status, response

    def _configure_band2_cmd(self, task_callback=None, task_abort_event=None):
        """configureBand on DS, SPF, SPFRX"""
        assert task_callback, "task_callback has to be defined"
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        for device in ["DS", "SPFRX"]:
            command = SubmittedSlowCommand(
                f"{device}ConfigureBand2",
                self._command_tracker,
                self.component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "DS":
                _, command_id = command("SetIndexPosition", 2)
                task_callback(
                    progress=f"SetIndexPosition called on DS, ID {command_id}"
                )
            else:
                _, command_id = command("ConfigureBand2", None)
                task_callback(
                    progress=f"ConfigureBand2 called on SPFRx, ID {command_id}"
                )

            device_command_ids[device] = command_id

        task_callback(progress="Waiting for band change to B2")

        while True:
            if task_abort_event.is_set():
                task_callback(
                    status=TaskStatus.ABORTED,
                    result="Track Aborted",
                )
                return

            if self.communication_state == CommunicationStatus.NOT_ESTABLISHED:
                task_callback(
                    status=TaskStatus.ABORTED,
                    result="Lost communication with monitored device",
                )
                return

            current_band = self.component_state["configured_band"]
            if current_band != Band.B2:
                task_abort_event.wait(timeout=1)
            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result="ConfigureBand2 completed",
                )
                return

    def set_stow_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STOW mode"""

        self._dish_mode_model.is_command_allowed(
            dish_mode=DishMode(self.component_state["dish_mode"]).name,
            command_name="SetStowMode",
        )
        status, response = self.submit_task(
            self._set_stow_mode, args=[], task_callback=task_callback
        )
        return status, response

    def _set_stow_mode(self, task_callback=None, task_abort_event=None):
        """Call Stow on DS"""
        assert task_callback, "task_callback has to be defined"
        task_callback(status=TaskStatus.IN_PROGRESS)

        command = SubmittedSlowCommand(
            "DS_SetStowMode",
            self._command_tracker,
            self.component_managers["DS"],
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
                    result="Stow Aborted",
                )
                return

            if self.communication_state == CommunicationStatus.NOT_ESTABLISHED:
                task_callback(
                    status=TaskStatus.ABORTED,
                    result="Lost communication with monitored device",
                )
                return

            current_dish_mode = self.component_state["dish_mode"]
            if current_dish_mode != DishMode.STOW:
                task_abort_event.wait(timeout=1)
            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result="Stow completed",
                )
                return

    # pylint: disable=missing-function-docstring
    def stop_communicating(self):
        for com_man in self.component_managers.values():
            com_man.stop_communicating()

    # pylint: disable=missing-function-docstring
    def abort_tasks(self, task_callback: Optional[Callable] = None):
        for com_man in self.component_managers.values():
            com_man.stop_communicating()
        return super().abort_tasks(task_callback)
