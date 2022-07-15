# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
import logging
from threading import Event
from typing import Any, AnyStr, Callable, Optional

from ska_tango_base.base.component_manager import TaskExecutorComponentManager
from ska_tango_base.control_model import CommunicationStatus
from ska_tango_base.executor import TaskStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import (
    TangoDeviceComponentManager,
)
from ska_mid_dish_manager.models.dish_enums import DishMode
from ska_mid_dish_manager.models.dish_mode_model import DishModeModel


class DishManagerComponentManager(TaskExecutorComponentManager):
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
            dish_mode=DishMode.STARTUP,
            **kwargs,
        )
        self._dish_mode_model = DishModeModel()
        self.component_managers = {}
        self.component_managers["DS"] = TangoDeviceComponentManager(
            "mid_d0001/lmc/ds_simulator",
            logger,
            component_state_callback=None,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPFRX"] = TangoDeviceComponentManager(
            "mid_d0001/spfrx/simulator",
            logger,
            component_state_callback=None,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPF"] = TangoDeviceComponentManager(
            "mid_d0001/spf/simulator",
            logger,
            component_state_callback=None,
            communication_state_callback=self._communication_state_changed,
        )

    # pylint: disable=unused-argument
    def _communication_state_changed(self, *args, **kwargs):
        # communication state will come from args and kwargs
        if all(
            cm.communication_state == CommunicationStatus.ESTABLISHED
            for cm in self.component_managers.values()
        ):
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
            self._update_component_state(dish_mode=DishMode.STANDBY_LP)
        else:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )

    def start_communicating(self):
        for com_man in self.component_managers.values():
            com_man.start_communicating()

    def _task_callback(
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
        component_manager: TangoDeviceComponentManager,
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

    def set_standby_lp_mode(self):
        if self._dish_mode_model.is_command_allowed(
            dish_mode=DishMode(self.component_state["dish_mode"]).name,
            command_name="SetStandbyLPMode",
        ):
            # commands to call
            # DS -> setstanby-lp
            # SPF -> setstanby-lp
            # SPFRx -> setstandby
            result = self.submit_task(
                self._execute_sub_device_command,
                args=[
                    self.component_managers["DS"],
                    "SetStandbyLPMode",
                ],
                task_callback=self._task_callback,
            )
            self.logger.info(
                "Result of SetStandbyLPMode on ds_component_manager [%s]",
                result,
            )
            result = self.submit_task(
                self._execute_sub_device_command,
                args=[
                    self.logger,
                    self.component_managers["SPF"],
                    "SetStandbyLPMode",
                ],
                task_callback=self._task_callback,
            )
            self.logger.info(
                "Result of SetStandbyLPMode on spf_component_manager [%s]",
                result,
            )
            result = self.submit_task(
                self._execute_sub_device_command,
                args=[
                    self.logger,
                    self.component_managers["SPFRX"],
                    "SetStandbyLPMode",
                ],
                task_callback=self._task_callback,
            )
            self.logger.info(
                "Result of SetStandbyLPMode on spfrx_component_manager [%s]",
                result,
            )
        else:
            raise Exception

    def stop_communicating(self):
        for com_man in self.component_managers.values():
            com_man.stop_communicating()

    def abort_tasks(self, task_callback: Optional[Callable] = None):
        self.stop_communicating()
        for com_man in self.component_managers.values():
            com_man.abort_tasks(task_callback)
        return super().abort_tasks(task_callback)
