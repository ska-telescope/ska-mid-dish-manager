"""Component manager for a DishManager tango device"""
import json
import logging
from threading import Event
from typing import Any, AnyStr, Callable, Optional, Tuple

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
    DishMode,
    DSOperatingMode,
    PointingState,
    SPFOperatingMode,
    SPFRxOperatingMode,
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
            **kwargs,
        )
        self._dish_mode_model = DishModeModel()
        self._command_tracker = command_tracker
        self.component_managers = {}
        self.component_managers["DS"] = DSComponentManager(
            ds_device_fqdn,
            logger,
            operating_mode=None,
            pointing_state=None,
            achieved_target_lock=None,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPFRX"] = SPFRxComponentManager(
            spfrx_device_fqdn,
            logger,
            operating_mode=None,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPF"] = SPFComponentManager(
            spf_device_fqdn,
            logger,
            operating_mode=None,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self._update_component_state(dish_mode=DishMode.STARTUP)
        self._update_component_state(health_state=HealthState.UNKNOWN)

    # pylint: disable=unused-argument
    def _communication_state_changed(self, *args, **kwargs):
        # communication state will come from args and kwargs
        if all(
            cm.communication_state == CommunicationStatus.ESTABLISHED
            for cm in self.component_managers.values()
        ):
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
            # TODO: The component state transition will be determined by the
            # operatingMode of the subservient devices. That will be based on
            # the builtin rules for determining the dishMode based on the
            # aggregation of the operatingModes. Builtin rules yet to be added
            self._update_component_state(dish_mode=DishMode.STANDBY_LP)
            self._update_component_state(health_state=HealthState.OK)
        else:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self._update_component_state(health_state=HealthState.FAILED)

    # pylint: disable=unused-argument
    def _component_state_changed(self, *args, **kwargs):
        # component state will come from args and kwargs
        # TODO: same as TODO comment in _communication_state_changed
        ds_comp_state = self.component_managers["DS"].component_state
        spf_comp_state = self.component_managers["SPF"].component_state
        spfrx_comp_state = self.component_managers["SPFRX"].component_state

        # PointingState rules for TRACK, SCAN, SLEW & SetOperateMode
        def _update_pointing_state():
            if ds_comp_state["pointing_state"] is not None:
                self._update_component_state(
                    pointing_state=ds_comp_state["pointing_state"]
                )

                if ds_comp_state["pointing_state"] in [
                    PointingState.SLEW,
                    PointingState.READY,
                ]:
                    self._update_component_state(achieved_target_lock=False)
                elif ds_comp_state["pointing_state"] == PointingState.TRACK:
                    self._update_component_state(achieved_target_lock=True)

        _update_pointing_state()

        # STANDBY_LP rules
        if (
            ds_comp_state["operating_mode"] == DSOperatingMode.STANDBY_LP
            and spf_comp_state["operating_mode"] == SPFOperatingMode.STANDBY_LP
            and spfrx_comp_state["operating_mode"]
            == SPFRxOperatingMode.STANDBY
        ):
            self._update_component_state(dish_mode=DishMode.STANDBY_LP)

        # STANDBY_FP rules
        if (
            ds_comp_state["operating_mode"] == DSOperatingMode.STANDBY_FP
            and spf_comp_state["operating_mode"] == SPFOperatingMode.OPERATE
            and spfrx_comp_state["operating_mode"]
            in (SPFRxOperatingMode.STANDBY, SPFRxOperatingMode.DATA_CAPTURE)
        ):
            self._update_component_state(dish_mode=DishMode.STANDBY_FP)

        # OPERATE rules
        if (
            ds_comp_state["operating_mode"] == DSOperatingMode.POINT
            and spf_comp_state["operating_mode"] == SPFOperatingMode.OPERATE
            and spfrx_comp_state["operating_mode"]
            == SPFRxOperatingMode.DATA_CAPTURE
        ):
            self._update_component_state(dish_mode=DishMode.OPERATE)
            # pointingState should come from DS
            _update_pointing_state()

    def start_communicating(self):
        for com_man in self.component_managers.values():
            com_man.start_communicating()

    def _cm_task_callback(
        self,
        status: TaskStatus,
        result: Optional[Any] = None,
        message: Optional[Any] = None,
        exception: Optional[Any] = None,
    ):
        if exception:
            self.logger.info(
                "Command execution task callback [%s, %s, %s]",
                status,
                result,
                message,
                exception,
            )
        else:
            self.logger.info(
                "Command execution task callback [%s, %s, %s]",
                status,
                result,
                message,
            )

    # pylint:disable=protected-access
    @classmethod
    def _execute_sub_device_command(  # pylint:disable=too-many-arguments
        cls,
        logger,
        component_manager,
        command_name: AnyStr,
        task_abort_event: Event = None,
        task_callback: Callable = None,
    ):
        logger.info("About to execute command [%s]", command_name)
        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                result=f"From {component_manager._tango_device_fqdn}",
            )
            return
        try:
            task_callback(
                status=TaskStatus.IN_PROGRESS,
                result=f"From {component_manager._tango_device_fqdn}",
            )
            command_result = component_manager.run_device_command(command_name)
            task_callback(
                status=TaskStatus.COMPLETED,
                result=(
                    f"From {component_manager._tango_device_fqdn} "
                    f"result [{command_result}]"
                ),
            )
        except Exception as err:  # pylint: disable=W0703
            task_callback(
                status=TaskStatus.FAILED,
                exception=err,
                result=f"From {component_manager._tango_device_fqdn}",
            )

    def set_standby_lp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:
        """Transition the dish to STANDBY_LP mode"""

        self._dish_mode_model.is_command_allowed(
            dish_mode=DishMode(self.component_state["dish_mode"]).name,
            command_name="SetStandbyLPMode",
        )
        return self.submit_task(
            self._set_standby_lp_mode,
            task_callback=task_callback,
        )

    def _set_standby_lp_mode(self, task_callback=None, task_abort_event=None):
        if task_callback is not None:
            task_callback(status=TaskStatus.IN_PROGRESS)

        result = self.submit_task(
            self._execute_sub_device_command,
            args=[
                self.logger,
                self.component_managers["DS"],
                "SetStandbyLPMode",
            ],
            task_callback=self._cm_task_callback,
        )
        self.logger.info(
            "Result of SetStandbyLPMode on ds_cm [%s]",
            result,
        )
        result = self.submit_task(
            self._execute_sub_device_command,
            args=[
                self.logger,
                self.component_managers["SPF"],
                "SetStandbyLPMode",
            ],
            task_callback=self._cm_task_callback,
        )
        self.logger.info(
            "Result of SetStandbyLPMode on spf_cm [%s]",
            result,
        )
        result = self.submit_task(
            self._execute_sub_device_command,
            args=[
                self.logger,
                self.component_managers["SPFRX"],
                "SetStandbyLPMode",
            ],
            task_callback=self._cm_task_callback,
        )
        self.logger.info(
            "Result of SetStandbyLPMode on spfrx_cm [%s]",
            result,
        )

        if task_callback is not None:
            task_callback(
                status=TaskStatus.COMPLETED,
                result="SetStandbyLPMode queued on ds, spf and spfrx",
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
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}
        for device in ["DS", "SPF", "SPFRX"]:
            command = NestedSubmittedSlowCommand(
                f"{device}_SetStandbyFPMode",
                self._command_tracker,
                self.component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )
            _, command_id = command("SetStandbyFPMode", None)
            device_command_ids[device] = command_id

        task_callback(
            status=TaskStatus.COMPLETED, result=json.dumps(device_command_ids)
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
        return self.submit_task(
            self._set_operate_mode,
            task_callback=task_callback,
        )

    def _set_operate_mode(self, task_callback=None, task_abort_event=None):
        if task_callback is not None:
            task_callback(status=TaskStatus.IN_PROGRESS)

        result = self.submit_task(
            self._execute_sub_device_command,
            args=[
                self.logger,
                self.component_managers["DS"],
                "SetOperateMode",
            ],
            task_callback=self._cm_task_callback,
        )
        self.logger.info(
            "Result of SetOperateMode on ds_cm [%s]",
            result,
        )
        result = self.submit_task(
            self._execute_sub_device_command,
            args=[
                self.logger,
                self.component_managers["SPF"],
                "SetOperateMode",
            ],
            task_callback=self._cm_task_callback,
        )
        self.logger.info(
            "Result of SetOperateMode on spf_cm [%s]",
            result,
        )
        result = self.submit_task(
            self._execute_sub_device_command,
            args=[
                self.logger,
                self.component_managers["SPFRX"],
                "SetOperateMode",
            ],
            task_callback=self._cm_task_callback,
        )
        self.logger.info(
            "Result of SetOperateMode on spfrx_cm [%s]",
            result,
        )

        if task_callback is not None:
            task_callback(
                status=TaskStatus.COMPLETED,
                result="SetOperateMode queued on ds, spf and spfrx",
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

        return self.submit_task(
            self._track_cmd,
            task_callback=task_callback,
        )

    def _track_cmd(self, task_callback=None, task_abort_event=None):
        if task_callback is not None:
            task_callback(status=TaskStatus.IN_PROGRESS)

        result = self.submit_task(
            self._execute_sub_device_command,
            args=[
                self.logger,
                self.component_managers["DS"],
                "Track",
            ],
            task_callback=self._cm_task_callback,
        )
        self.logger.info(
            "Result of Track on ds_cm [%s]",
            result,
        )

        if task_callback is not None:
            task_callback(
                status=TaskStatus.COMPLETED,
                result="Track command queued on ds",
            )

    def stop_communicating(self):
        for com_man in self.component_managers.values():
            com_man.stop_communicating()

    def abort_tasks(self, task_callback: Optional[Callable] = None):
        for com_man in self.component_managers.values():
            com_man.stop_communicating()
        return super().abort_tasks(task_callback)
