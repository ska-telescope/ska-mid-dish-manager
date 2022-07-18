# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
import logging
from threading import Event, Lock
from typing import Any, AnyStr, Callable, Optional, Tuple

import tango
from ska_tango_base.base.component_manager import TaskExecutorComponentManager
from ska_tango_base.control_model import CommunicationStatus, HealthState
from ska_tango_base.executor import TaskStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import (
    TangoDeviceComponentManager,
)
from ska_mid_dish_manager.models.dish_enums import DishMode
from ska_mid_dish_manager.models.dish_mode_model import DishModeModel


class TangoGuard:
    """We have several threads interacting with Tango devices.

    In an effort to prevent Tango segfaults, we found that
    limiting any interaction helps.
    """

    def __init__(self, tango_interaction_lock: Lock) -> None:
        self.tango_interaction_lock = tango_interaction_lock

    def __enter__(self):
        self.tango_interaction_lock.acquire(timeout=30)
        with tango.EnsureOmniThread():
            yield

    def __exit__(self, atype, value, traceback):
        if self.tango_interaction_lock.locked():
            self.tango_interaction_lock.release()
        return False  # Re raise any exception


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
            dish_mode=None,
            health_state=None,
            **kwargs,
        )
        self._dish_mode_model = DishModeModel()
        self.component_managers = {}
        self.tango_guard = TangoGuard(Lock())
        self.component_managers["DS"] = TangoDeviceComponentManager(
            "mid_d0001/lmc/ds_simulator",
            logger,
            self.tango_guard,
            component_state_callback=None,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPFRX"] = TangoDeviceComponentManager(
            "mid_d0001/spfrx/simulator",
            logger,
            self.tango_guard,
            component_state_callback=None,
            communication_state_callback=self._communication_state_changed,
        )
        self.component_managers["SPF"] = TangoDeviceComponentManager(
            "mid_d0001/spf/simulator",
            logger,
            self.tango_guard,
            component_state_callback=None,
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

    def set_standby_lp_mode(
        self,
        task_callback: Optional[Callable] = None,
    ) -> Tuple[TaskStatus, str]:

        return self.submit_task(
            self._set_standby_lp_mode,
            task_callback=task_callback,
        )

    def _set_standby_lp_mode(self, task_callback=None, task_abort_event=None):
        if task_callback is not None:
            task_callback(status=TaskStatus.IN_PROGRESS)

        try:

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

        # We dont know what exceptions may be raised
        except Exception as err:  # pylint:disable=broad-except
            task_callback(status=TaskStatus.FAILED, exception=err)

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
