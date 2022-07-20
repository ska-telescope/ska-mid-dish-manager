"""Component manager for a DishManager tango device"""
import logging
from threading import Event
from typing import Any, AnyStr, Callable, Optional, Tuple

from ska_tango_base.base.component_manager import TaskExecutorComponentManager
from ska_tango_base.control_model import CommunicationStatus, HealthState
from ska_tango_base.executor import TaskStatus

from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.component_managers.spf_cm import SPFComponentManager
from ska_mid_dish_manager.component_managers.spfrx_cm import (
    SPFRxComponentManager,
)
from ska_mid_dish_manager.models.dish_enums import DishMode, OperatingMode
from ska_mid_dish_manager.models.dish_mode_model import DishModeModel


# pylint: disable=abstract-method
class DishManagerComponentManager(TaskExecutorComponentManager):
    """A component manager for DishManager

    It watches the component managers of the subservient devices
    (DS, SPF, SPFRX) to refect the state of the Dish LMC.
    """

    def __init__(
        self,
        logger: logging.Logger,
        *args,
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
            **kwargs,
        )
        self._dish_mode_model = DishModeModel()
        self.component_managers = {}
        self.component_managers["DS"] = DSComponentManager(
            "mid_d0001/lmc/ds_simulator",
            logger,
            operating_mode=None,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPFRX"] = SPFRxComponentManager(
            "mid_d0001/spfrx/simulator",
            logger,
            operating_mode=None,
            component_state_callback=self._component_state_changed,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPF"] = SPFComponentManager(
            "mid_d0001/spf/simulator",
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
        if all(
            cm.component_state["operating_mode"] == OperatingMode.STANDBY_LP
            for cm in self.component_managers.values()
        ):
            self._update_component_state(dish_mode=DishMode.STANDBY_LP)

        if all(
            cm.component_state["operating_mode"] == OperatingMode.STANDBY_FP
            for cm in self.component_managers.values()
        ):
            self._update_component_state(dish_mode=DishMode.STANDBY_FP)

    def start_communicating(self):
        for com_man in self.component_managers.values():
            com_man.start_communicating()

    def _cm_task_callback(
        self,
        status: TaskStatus,
        result: Optional[Any] = None,
        message: Optional[Any] = None,
    ):
        self.logger.info(
            "Command execution task callback [%s, %s, %s]",
            status,
            result,
            message,
        )

    @classmethod
    def _execute_sub_device_command(
        cls,
        component_manager,
        command_name: AnyStr,
        task_abort_event: Event = None,
        task_callback: Callable = None,
    ):
        if task_abort_event.is_set():
            task_callback(
                status=TaskStatus.ABORTED,
                message=f"From {component_manager.tango_device_fqdn}",
            )
            return
        try:
            task_callback(
                status=TaskStatus.IN_PROGRESS,
                message=f"From {component_manager.tango_device_fqdn}",
            )
            command_result = component_manager.run_device_command(command_name)
            task_callback(
                status=TaskStatus.COMPLETED,
                result=command_result,
                message=f"From {component_manager.tango_device_fqdn}",
            )
        except Exception as err:  # pylint: disable=W0703
            task_callback(
                status=TaskStatus.FAILED,
                result=err,
                message=f"From {component_manager.tango_device_fqdn}",
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

        task_callback(
            status=TaskStatus.COMPLETED,
            result="SetStandbyLPMode queued on ds, spf and spfrx",
        )

    def stop_communicating(self):
        for com_man in self.component_managers.values():
            com_man.stop_communicating()

    def abort_tasks(self, task_callback: Optional[Callable] = None):
        self.stop_communicating()
        for com_man in self.component_managers.values():
            com_man.abort_tasks(task_callback)
        return super().abort_tasks(task_callback)
