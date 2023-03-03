"""Module to manage the mapping of commands to subservient devices"""
import enum
import json
from typing import Callable, Optional

from ska_tango_base.commands import SubmittedSlowCommand
from ska_tango_base.executor import TaskStatus

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
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
        command_tracker,
        logger,
    ):
        self._dish_manager_cm = dish_manager_cm
        self._command_tracker = command_tracker
        self.logger = logger

        self._keys_to_output_map = {
            "dishmode": "dishMode",
            "SPFRX": "SPFRx",
        }

    def _key_to_output(self, key):
        output = self._keys_to_output_map.get(key)

        if not output:
            output = key

        return output

    def set_standby_lp_mode(self, task_callback: Optional[Callable] = None, task_abort_event=None):
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
                "awaitedValuesList": [SPFOperatingMode.STANDBY_LP],
            },
            "SPFRX": {
                "command": "SetStandbyMode",
                "awaitedAttribute": "operatingmode",
                "awaitedValuesList": [SPFRxOperatingMode.STANDBY],
            },
            "DS": {
                "command": "SetStandbyLPMode",
                "awaitedAttribute": "operatingmode",
                "awaitedValuesList": [DSOperatingMode.STANDBY_LP],
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

    def set_standby_fp_mode(
        self,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Transition the dish to STANDBY_FP mode"""
        if self._dish_manager_cm.component_state["dishmode"].name == "OPERATE":
            commands_for_device = {
                "DS": {
                    "command": "SetStandbyFPMode",
                    "awaitedAttribute": "operatingmode",
                    "awaitedValuesList": [DSOperatingMode.STANDBY_LP],
                }
            }
        else:
            commands_for_device = {
                "SPF": {
                    "command": "SetOperateMode",
                    "awaitedAttribute": "operatingmode",
                    "awaitedValuesList": [SPFOperatingMode.OPERATE],
                },
                "DS": {
                    "command": "SetStandbyFPMode",
                    "awaitedAttribute": "operatingmode",
                    "awaitedValuesList": [DSOperatingMode.STANDBY_LP],
                },
            }

            if self._dish_manager_cm.component_state["configuredband"] not in [
                Band.NONE,
                Band.UNKNOWN,
            ]:
                commands_for_device["SPFRX"] = {
                    "command": "SetStandbyMode",
                    "awaitedAttribute": "operatingmode",
                    "awaitedValuesList": [
                        SPFRxOperatingMode.STANDBY,
                        SPFRxOperatingMode.DATA_CAPTURE,
                    ],
                }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_device,
            "SetStandbyFPMode",
            "dishmode",
            DishMode.STANDBY_FP,
        )

    def set_operate_mode(
        self,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Transition the dish to OPERATE mode"""
        commands_for_device = {
            "SPF": {
                "command": "SetOperateMode",
                "awaitedAttribute": "operatingmode",
                "awaitedValuesList": [SPFOperatingMode.OPERATE],
            },
            "SPFRX": {
                "command": "CaptureData",
                "commandValue": True,
                "awaitedAttribute": "operatingmode",
                "awaitedValuesList": [SPFRxOperatingMode.DATA_CAPTURE],
            },
            "DS": {
                "command": "SetPointMode",
                "awaitedAttribute": "operatingmode",
                "awaitedValuesList": [DSOperatingMode.POINT],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_device,
            "SetOperateMode",
            "dishmode",
            DishMode.OPERATE,
        )

    def track_cmd(
        self,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Transition the dish to Track mode"""
        commands_for_device = {
            "DS": {
                "command": "Track",
                "awaitedAttribute": "operatingmode",
                "awaitedValuesList": [DSOperatingMode.POINT],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_device,
            "Track",
            "achievedtargetlock",
            True,
        )

    def configure_band2_cmd(
        self,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Configure band 2 on DS and SPF"""
        commands_for_device = {
            "DS": {
                "command": "SetIndexPosition",
                "commandValue": 2,
                "awaitedAttribute": "indexerposition",
                "awaitedValuesList": [IndexerPosition.B2],
            },
            "SPFRX": {
                "command": "ConfigureBand2",
                "awaitedAttribute": "configuredband",
                "awaitedValuesList": [Band.B2],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_device,
            "ConfigureBand2",
            "configuredband",
            Band.B2,
        )

    def set_stow_mode(
        self,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Transition the dish to Stow mode"""
        commands_for_device = {
            "DS": {
                "command": "Stow",
                "awaitedAttribute": "operatingmode",
                "awaitedValuesList": [DSOperatingMode.STOW],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_device,
            "Stow",
            "dishmode",
            DishMode.STOW,
        )

    # pylint: disable=too-many-locals
    def _run_long_running_command(
        self,
        task_callback,
        task_abort_event,
        commands_for_device,
        running_command,
        awaited_event_attribute,
        awaited_event_value,
    ):
        assert task_callback, "task_callback has to be defined"

        if task_abort_event.is_set():
            task_callback(progress=f"{running_command} Aborted")
            task_callback(
                status=TaskStatus.ABORTED,
                result=f"{running_command} Aborted",
            )
            return

        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}

        for device in commands_for_device:
            command = SubmittedSlowCommand(
                f"{device}_{commands_for_device[device]['command']}",
                self._command_tracker,
                self._dish_manager_cm.sub_component_managers[device],
                "run_device_command",
                callback=None,
                logger=self.logger,
            )

            command_value = commands_for_device[device].get("commandValue")

            _, command_id = command(commands_for_device[device]["command"], command_value)

            # Report that the command has been called on the subservient device
            task_callback(
                progress=(
                    f"{commands_for_device[device]['command']}"
                    f" called on {self._key_to_output(device)}, ID {command_id}"
                )
            )

            awaited_attribute = commands_for_device[device]["awaitedAttribute"]
            awaited_values_list = commands_for_device[device]["awaitedValuesList"]

            # Report which attribute and value we the device is waiting for
            task_callback(
                progress=(
                    f"Awaiting {self._key_to_output(device)} {awaited_attribute}"
                    f" change to {awaited_values_list}"
                )
            )

            device_command_ids[device] = command_id

        task_callback(progress=f"Commands: {json.dumps(device_command_ids)}")

        awaited_event_value_print = awaited_event_value

        if isinstance(awaited_event_value, enum.IntEnum):
            awaited_event_value_print = awaited_event_value.name

        task_callback(
            progress=(
                f"Awaiting {self._key_to_output(awaited_event_attribute)}"
                f" change to {awaited_event_value_print}"
            )
        )

        success_reported = dict.fromkeys(commands_for_device.keys(), False)

        while True:
            if task_abort_event.is_set():
                task_callback(
                    progress=f"{running_command} Aborted",
                )
                task_callback(
                    status=TaskStatus.ABORTED,
                    result=f"{running_command} Aborted",
                )
                return

            # Check on dishmanager CMs attribute to see whether
            # the LRC has completed
            current_awaited_value = self._dish_manager_cm.component_state[awaited_event_attribute]

            # Check each devices to see if their operatingmode
            # attributes are in the correct state
            for device in commands_for_device:
                awaited_attribute = commands_for_device[device]["awaitedAttribute"]
                awaited_values_list = commands_for_device[device]["awaitedValuesList"]

                awaited_attribute_value = self._dish_manager_cm.sub_component_managers[
                    device
                ].component_state[awaited_attribute]

                if awaited_attribute_value in awaited_values_list:
                    if not success_reported[device]:
                        task_callback(
                            progress=(
                                f"{device} {awaited_attribute} changed to, "
                                f"{awaited_values_list}"
                            )
                        )

                        success_reported[device] = True

            if current_awaited_value != awaited_event_value:
                task_abort_event.wait(timeout=1)
                for component_manager in self._dish_manager_cm.sub_component_managers.values():
                    component_manager.update_state_from_monitored_attributes()
            else:
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result=f"{running_command} completed",
                    progress=f"{running_command} completed",
                )
                return
