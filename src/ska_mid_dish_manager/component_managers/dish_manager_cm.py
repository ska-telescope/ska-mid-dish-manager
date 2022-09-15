# pylint: disable=protected-access
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
    DSPowerState,
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
            configuredband=Band.NONE,
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
            powerstate=DSPowerState.UNKNOWN,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPFRX"] = SPFRxComponentManager(
            spfrx_device_fqdn,
            logger,
            operatingmode=None,
            configuredband=Band.NONE,
            capturingdata=False,
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
            b1capabilitystate=SPFCapabilityStates.UNAVAILABLE,
            b2capabilitystate=SPFCapabilityStates.UNAVAILABLE,
            b3capabilitystate=SPFCapabilityStates.UNAVAILABLE,
            b4capabilitystate=SPFCapabilityStates.UNAVAILABLE,
            b5capabilitystate=SPFCapabilityStates.UNAVAILABLE,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        initial_component_states = {
            "dishmode": DishMode.STARTUP,
            "healthstate": HealthState.UNKNOWN,
            "configuredband": Band.NONE,
            "capturing": False,
            "pointingState": PointingState.NONE,
            "b1capabilitystate": CapabilityStates.UNKNOWN,
            "b2capabilitystate": CapabilityStates.UNKNOWN,
            "b3capabilitystate": CapabilityStates.UNKNOWN,
            "b4capabilitystate": CapabilityStates.UNKNOWN,
            "b5acapabilitystate": CapabilityStates.UNKNOWN,
            "b5bcapabilitystate": CapabilityStates.UNKNOWN,
        }
        self._update_component_state(**initial_component_states)

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
                # operating modes of subservient devices. Likewise, any
                # reconnection gained should be accompanied by fresh
                # attribute updates
                self._component_state_changed()
            else:
                self._update_communication_state(
                    CommunicationStatus.NOT_ESTABLISHED
                )
                self._update_component_state(healthstate=HealthState.FAILED)

    # pylint: disable=unused-argument
    def _component_state_changed(self, *args, **kwargs):

        ds_comp_state = self.component_managers["DS"].component_state
        spf_comp_state = self.component_managers["SPF"].component_state
        spfrx_comp_state = self.component_managers["SPFRX"].component_state

        self.logger.debug(
            (
                "Component state has changed, kwargs [%s], DS [%s], SPF [%s]"
                ", SPFRx [%s], DM [%s]"
            ),
            kwargs,
            ds_comp_state,
            spf_comp_state,
            spfrx_comp_state,
            self.component_state,
        )

        # Only update dishMode if there are operatingmode changes
        if "operatingmode" in kwargs:
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
            self._update_component_state(dishmode=new_dish_mode)

        if "healthstate" in kwargs:
            self.logger.info(
                (
                    "Updating healthState with healthstate DS"
                    " [%s], SPF [%s], SPFRX [%s]"
                ),
                str(ds_comp_state["healthstate"]),
                str(spf_comp_state["healthstate"]),
                str(spfrx_comp_state["healthstate"]),
            )
            new_health_state = self._dish_mode_model.compute_dish_health_state(
                ds_comp_state,
                spfrx_comp_state,
                spf_comp_state,
            )
            self._update_component_state(healthstate=new_health_state)

        if "pointingstate" in kwargs:
            self.logger.debug(
                ("Newly calculated component state [pointing_state] [%s]"),
                ds_comp_state["pointingstate"],
            )
            self._update_component_state(
                pointingstate=ds_comp_state["pointingstate"]
            )

            if ds_comp_state["pointingstate"] in [
                PointingState.SLEW,
                PointingState.READY,
            ]:
                self._update_component_state(achievedtargetlock=False)
            elif ds_comp_state["pointingstate"] == PointingState.TRACK:
                self._update_component_state(achievedtargetlock=True)

        # spf bandInFocus
        if "indexerposition" in kwargs and "configuredband" in kwargs:
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
            "indexerposition" in kwargs
            or "bandinfocus" in kwargs
            or "configuredband" in kwargs
        ):
            self.logger.info(
                (
                    "Updating configuredBand with DS"
                    " [%s] SPF [%s] SPFRX [%s]"
                ),
                str(ds_comp_state),
                str(spf_comp_state),
                str(spfrx_comp_state),
            )

            configured_band = self._dish_mode_model.compute_configured_band(
                ds_comp_state,
                spfrx_comp_state,
                spf_comp_state,
            )
            self._update_component_state(configuredband=configured_band)

        # update capturing attribute when SPFRx captures data
        if "capturingdata" in kwargs:
            self.logger.info(
                ("Updating capturing with SPFRx [%s]"),
                str(spfrx_comp_state),
            )
            self._update_component_state(
                capturing=spfrx_comp_state["capturingdata"]
            )

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
        # b5 for SPF
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

    def _update_component_state(self, *args, **kwargs):
        """Log the new component state"""
        self.logger.debug(
            "Updating component dish manager component state with [%s]", kwargs
        )
        super()._update_component_state(*args, **kwargs)

    def _update_dishmode_component_states(self):
        """Update the component state required for dishMode changes"""
        for comp_man in self.component_managers.values():
            op_mode = comp_man.read_attribute_value("operatingMode")
            comp_man._update_component_state(operatingmode=op_mode)

    def start_communicating(self):
        """Connect from monitored devices"""
        for com_man in self.component_managers.values():
            com_man.start_communicating()

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
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}

        subservient_devices = ["DS", "SPF", "SPFRX"]

        # TODO clarify code below, SPFRX stays in DATA_CAPTURE when we dont
        # execute setstandby on it. So going from LP to FP never completes
        # since dishMode does not update.
        #
        # if self.component_state["dishmode"].name == "STANDBY_FP":
        #     subservient_devices = ["DS", "SPF"]

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

            current_dish_mode = self.component_state["dishmode"]
            if current_dish_mode != DishMode.STANDBY_LP:
                task_abort_event.wait(timeout=1)
                self._update_dishmode_component_states()

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
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        subservient_devices = ["DS", "SPF", "SPFRX"]

        if self.component_state["dishmode"].name == "OPERATE":
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
                # allow request only when there's a configured band
                if self.component_state["configuredband"] not in [
                    Band.NONE,
                    Band.UNKNOWN,
                ]:
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

            current_dish_mode = self.component_state["dishmode"]
            if current_dish_mode != DishMode.STANDBY_FP:
                task_abort_event.wait(timeout=1)
                self._update_dishmode_component_states()
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
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="SetOperateMode",
        )

        if self.component_state["configuredband"] in [
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

            current_dish_mode = self.component_state["dishmode"]
            if current_dish_mode != DishMode.OPERATE:
                task_abort_event.wait(timeout=1)
                self._update_dishmode_component_states()
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
        dish_mode = self.component_state["dishmode"].name
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

            achieved_target_lock = self.component_state["achievedtargetlock"]
            if not achieved_target_lock:
                task_abort_event.wait(timeout=1)

                # Read pointingState on DS and update state
                comp_man = self.component_managers["DS"]
                pointing_state = comp_man.read_attribute_value("pointingState")
                comp_man._update_component_state(pointingstate=pointing_state)

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
            dishmode=DishMode(self.component_state["dishmode"]).name,
            command_name="ConfigureBand2",
        )

        if current_configured_band == Band.B2:
            return TaskStatus.REJECTED, f"Already in band {Band.B2.name}"

        # TODO Check if ConfigureBand2 is already running

        # check timestamp is in the future
        try:
            if (
                datetime.fromisoformat(activation_timestamp)
                <= datetime.utcnow()
            ):
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

            current_band = self.component_state["configuredband"]
            if current_band != Band.B2:
                task_abort_event.wait(timeout=1)

                # Read the appropriate attrs and update states.
                # DS indexerposition
                # SPFRx configuredband
                # SPF bandinfocus
                for device, attr in zip(
                    ["DS", "SPFRX", "SPF"],
                    ["indexerPosition", "configuredBand", "bandInFocus"],
                ):
                    comp_man = self.component_managers[device]
                    attr_value = comp_man.read_attribute_value(attr)
                    attr_name = attr.lower()
                    comp_man._update_component_state(**{attr_name: attr_value})

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

            current_dish_mode = self.component_state["dishmode"]
            if current_dish_mode != DishMode.STOW:
                task_abort_event.wait(timeout=1)
                self._update_dishmode_component_states()
            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result="Stow completed",
                )
                return

    # pylint: disable=missing-function-docstring
    def stop_communicating(self):
        """Disconnect from monitored devices"""
        for com_man in self.component_managers.values():
            com_man.stop_communicating()
