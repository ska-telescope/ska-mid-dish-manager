"""Component manager for a DishManager tango device"""
import json
import logging
from datetime import datetime
from typing import Callable, Optional, Tuple

from ska_tango_base.base.component_manager import TaskExecutorComponentManager
from ska_tango_base.control_model import CommunicationStatus, HealthState
from ska_tango_base.executor import TaskStatus

from ska_mid_dish_manager.commands import NestedSubmittedSlowCommand
from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.component_managers.spf_cm import SPFComponentManager
from ska_mid_dish_manager.component_managers.spfrx_cm import (
    SPFRxComponentManager,
)
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    DishMode,
    IndexerPosition,
    PointingState,
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
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPF"] = SPFComponentManager(
            spf_device_fqdn,
            logger,
            operatingmode=None,
            bandinfocus=BandInFocus.UNKNOWN,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self._update_component_state(dish_mode=DishMode.STARTUP)
        self._update_component_state(health_state=HealthState.UNKNOWN)
        self._update_component_state(configured_band=Band.NONE)

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
        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        if self.component_state["dish_mode"].name == "STANDBY_FP":
            subservient_devices = ["DS", "SPF"]
        if self.component_state["dish_mode"].name in ["MAINTENANCE", "STOW"]:
            subservient_devices.append("SPFRX")

        for device in subservient_devices:
            command = NestedSubmittedSlowCommand(
                f"{device}_SetStandbyLPMode",
                self._command_tracker,
                self.component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "SPFRX":
                _, command_id = command("SetStandbyMode", None)
            else:
                _, command_id = command("SetStandbyLPMode", None)

            device_command_ids[device] = command_id

        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=json.dumps(device_command_ids),
            )

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
        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        if self.component_state["dish_mode"].name == "STANDBY_LP":
            subservient_devices = ["DS", "SPF", "SPFRX"]
        elif self.component_state["dish_mode"].name == "OPERATE":
            subservient_devices = ["DS"]

        for device in subservient_devices:
            command = NestedSubmittedSlowCommand(
                f"{device}_SetStandbyFPMode",
                self._command_tracker,
                self.component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "DS":
                _, command_id = command("SetStandbyFPMode", None)
            elif device == "SPF":
                _, command_id = command("SetOperateMode", None)
            else:
                _, command_id = command("CaptureData", True)

            device_command_ids[device] = command_id

        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=json.dumps(device_command_ids),
            )

    def set_operate_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to OPERATE mode"""

        self._dish_mode_model.is_command_allowed(
            dish_mode=DishMode(self.component_state["dish_mode"]).name,
            command_name="SetOperateMode",
        )
        status, response = self.submit_task(
            self._set_operate_mode, args=[], task_callback=task_callback
        )
        return status, response

    def _set_operate_mode(self, task_callback=None, task_abort_event=None):
        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        for device in ["DS", "SPF", "SPFRX"]:
            command = NestedSubmittedSlowCommand(
                f"{device}_SetOperateMode",
                self._command_tracker,
                self.component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "DS":
                _, command_id = command("SetPointMode", None)
            elif device == "SPF":
                _, command_id = command("SetOperateMode", None)
            else:
                _, command_id = command("CaptureData", True)

            device_command_ids[device] = command_id

        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=json.dumps(device_command_ids),
            )

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
        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        command = NestedSubmittedSlowCommand(
            "DS_Track",
            self._command_tracker,
            self.component_managers["DS"],
            "run_device_command",
            callback=None,
            logger=self.logger,
        )
        _, command_id = command("Track", None)
        device_command_ids["DS"] = command_id

        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=json.dumps(device_command_ids),
            )

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
        if task_callback is not None:
            task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        for device in ["DS", "SPFRX"]:
            command = NestedSubmittedSlowCommand(
                f"{device}ConfigureBand2",
                self._command_tracker,
                self.component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            if device == "DS":
                _, command_id = command("SetIndexPosition", 2)
            else:
                _, command_id = command("ConfigureBand2", None)

            device_command_ids[device] = command_id

        # SPF updates the bandInFocus
        # TODO: provide a function to perform attribute writes
        spf = self.component_managers["SPF"]
        # pylint: disable=protected-access
        spf._device_proxy.bandInFocus = Band.B2

        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED,
                result=json.dumps(device_command_ids),
            )

    # pylint: disable=missing-function-docstring
    def stop_communicating(self):
        for com_man in self.component_managers.values():
            com_man.stop_communicating()

    # pylint: disable=missing-function-docstring
    def abort_tasks(self, task_callback: Optional[Callable] = None):
        for com_man in self.component_managers.values():
            com_man.stop_communicating()
        return super().abort_tasks(task_callback)
