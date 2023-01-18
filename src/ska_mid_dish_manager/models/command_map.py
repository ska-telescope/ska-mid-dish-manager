"""Module to manage the mapping of commands to subservient devices"""
import json
from typing import Callable, Optional

from ska_tango_base.commands import SubmittedSlowCommand
from ska_tango_base.executor import TaskStatus

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


# pylint: disable=too-few-public-methods
class CommandMap:
    """
    A module to handle the mapping of commands to subservient devices.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        dish_manager_cm,
        dish_mode_model,
        command_tracker,
        logger,
        update_dishmode_component_states,
    ):
        self._dish_manager_cm = dish_manager_cm
        self._dish_mode_model = dish_mode_model
        self._command_tracker = command_tracker
        self.logger = logger
        self._update_dishmode_component_states = (
            update_dishmode_component_states
        )

    def set_standby_lp_mode(
        self, task_callback: Optional[Callable] = None, task_abort_event=None
    ):
        """Transition the dish to STANDBY_LP mode"""

        # TODO clarify code below, SPFRX stays in DATA_CAPTURE when we dont
        # execute setstandby on it. So going from LP to FP never completes
        # since dishMode does not update.
        #
        # if self._dish_manager_cm.component_state["dishmode"].name
        #  == "STANDBY_FP":
        #     subservient_devices = ["DS", "SPF"]

        commands_for_device = {
            "SPF": {
                "command": "SetStandbyLPMode",
                "awaitedAttribute": "operatingmode",
                "awaitedValue": SPFOperatingMode.STANDBY_LP,
            },
            "SPFRX": {
                "command": "SetStandbyMode",
                "awaitedAttribute": "operatingmode",
                "awaitedValue": SPFRxOperatingMode.STANDBY,
            },
            "DS": {
                "command": "SetStandbyLPMode",
                "awaitedAttribute": "operatingmode",
                "awaitedValue": DSOperatingMode.STANDBY_LP,
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_device,
            "SetStandbyLPMode",
            "dishmode",
            DishMode.STANDBY_LP,
        )

    # pylint: disable=too-many-locals
    def _run_long_running_command(
        self,
        task_callback=None,
        task_abort_event=None,
        commands_for_device=None,
        running_command="",
        awaited_event_attribute=None,
        awaited_event_value=None,
    ):
        device_command_ids = {}

        for device in commands_for_device:
            command = SubmittedSlowCommand(
                f"{device}_{commands_for_device[device]['command']}",
                self._command_tracker,
                self._dish_manager_cm.component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )

            _, command_id = command(
                commands_for_device[device]["command"], None
            )

            # Report that the command has been called on the subservient device
            task_callback(
                progress=(
                    f"{commands_for_device[device]['command']}"
                    f" called on {device}, ID {command_id}"
                )
            )

            awaited_attribute = commands_for_device[device]["awaitedAttribute"]
            awaited_value = commands_for_device[device]["awaitedValue"]

            # Report which attribute and value we the device is waiting for
            task_callback(
                progress=(
                    f"Awaiting {device} {awaited_attribute}"
                    f" to change to {awaited_value}"
                )
            )

            device_command_ids[device] = command_id

        task_callback(progress=f"Commands: {json.dumps(device_command_ids)}")
        task_callback(
            progress=(
                f"Awaiting {awaited_event_attribute}"
                f" change to {awaited_event_value}"
            )
        )

        success_reported = dict.fromkeys(commands_for_device.keys(), False)

        while True:
            if task_abort_event.is_set():
                task_callback(
                    status=TaskStatus.ABORTED,
                    result=f"{running_command} Aborted",
                    progress=f"{running_command} Aborted",
                )
                return

            # Check on dishmanager CMs attribute to see whether
            # the LRC has completed
            current_awaited_value = self._dish_manager_cm.component_state[
                awaited_event_attribute
            ]

            # Check each devices to see if their operatingmode
            # attributes are in the correct state
            for device in commands_for_device:
                awaited_attribute = commands_for_device[device][
                    "awaitedAttribute"
                ]
                awaited_value = commands_for_device[device]["awaitedValue"]

                awaited_attribute_value = (
                    self._dish_manager_cm.component_managers[
                        device
                    ].component_state[awaited_attribute]
                )

                if awaited_attribute_value == awaited_value:
                    if not success_reported[device]:
                        task_callback(
                            progress=(
                                f"{device} {awaited_attribute} changed to, "
                                f"{awaited_value}"
                            )
                        )

                        success_reported[device] = True

            if current_awaited_value != awaited_event_value:
                task_abort_event.wait(timeout=1)
                for (
                    comp_man
                ) in self._dish_manager_cm.component_managers.values():
                    comp_man.read_update_component_state()
                self._update_dishmode_component_states()

            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result=f"{running_command} completed",
                    progress=f"{running_command} completed",
                )
                return
