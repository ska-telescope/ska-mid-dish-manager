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
        *args,
        max_workers: int = 3,
        logger: logging.Logger = None,
        **kwargs,
    ):
        """"""
        # pylint: disable=useless-super-delegation
        super().__init__(
            *args,
            max_workers=max_workers,
            logger=logger,
            dish_mode=DishMode.STARTUP,
            **kwargs,
        )
        self._dish_mode_model = DishModeModel()
        self._ds_component_manager = TangoDeviceComponentManager(
            "mid_d0001/lmc/ds_simulator",
            logger,
            component_state_callback=None,
            communication_state_callback=self._communication_state_changed,
        )
        self._spfrx_component_manager = TangoDeviceComponentManager(
            "mid_d0001/spfrx/simulator",
            logger,
            component_state_callback=None,
            communication_state_callback=self._communication_state_changed,
        )
        self._spf_component_manager = TangoDeviceComponentManager(
            "mid_d0001/spf/simulator",
            logger,
            component_state_callback=None,
            communication_state_callback=self._communication_state_changed,
        )

    # pylint: disable=unused-argument
    def _communication_state_changed(self, *args, **kwargs):
        # communication state will come from args and kwargs
        if not hasattr(self, "_ds_component_manager"):
            # init command hasnt run yet. this will cause init device to fail
            return
        if (
            self._ds_component_manager.communication_state
            == CommunicationStatus.ESTABLISHED
            and self._spfrx_component_manager.communication_state
            == CommunicationStatus.ESTABLISHED
            and self._spf_component_manager.communication_state
            == CommunicationStatus.ESTABLISHED
        ):
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
            self._update_component_state(dish_mode=DishMode.STANDBY_LP)
        else:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )

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
        _task_abort_event: Event = None,
        task_callback: Callable = None,
    ):
        try:
            task_callback(status=TaskStatus.IN_PROGRESS)
            command_result = component_manager.run_device_command(command_name)
            task_callback(status=TaskStatus.COMPLETED, result=command_result)
        except Exception as err:  # pylint: disable=W0703
            task_callback(status=TaskStatus.FAILED, result=err)

    def set_standby_lp_mode(self):
        if self._dish_mode_model.is_command_allowed(
            dish_mode=DishMode(self.component_state["dish_mode"]).name,
            command_name="SetStandbyLPMode",
        ):
            # commands to call
            # DS -> setstanby-lp
            # SPF -> setstanby-lp
            # SPFRx -> setstandby
            self.submit_task(
                self._execute_sub_device_command,
                args=[self._ds_component_manager, "SetStandbyLPMode"],
                task_callback=self._task_callback,
            )
            self.submit_task(
                self._execute_sub_device_command,
                args=[self._spf_component_manager, "SetStandbyLPMode"],
                task_callback=self._task_callback,
            )
            self.submit_task(
                self._execute_sub_device_command,
                args=[self._spfrx_component_manager, "SetStandbyMode"],
                task_callback=self._task_callback,
            )
        else:
            raise Exception
