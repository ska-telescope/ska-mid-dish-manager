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
    PointingState,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


# pylint: disable=too-few-public-methods
class CommandMap:
    """
    Command fan out to handle the mapping of DishManager commands to subservient devices.
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
        commands_for_sub_devices = {
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
            commands_for_sub_devices,
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
            commands_for_sub_devices = {
                "DS": {
                    "command": "SetStandbyFPMode",
                    "awaitedAttribute": "operatingmode",
                    "awaitedValuesList": [DSOperatingMode.STANDBY_LP],
                }
            }
        else:
            commands_for_sub_devices = {
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

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
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
        commands_for_sub_devices = {
            "SPF": {
                "command": "SetOperateMode",
                "awaitedAttribute": "operatingmode",
                "awaitedValuesList": [SPFOperatingMode.OPERATE],
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
            commands_for_sub_devices,
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
        commands_for_sub_devices = {
            "DS": {
                "command": "Track",
                "awaitedAttribute": "operatingmode",
                "awaitedValuesList": [DSOperatingMode.POINT],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "Track",
            "pointingstate",
            PointingState.TRACK,
        )

    def track_stop_cmd(
        self,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Stop Tracking"""
        commands_for_sub_devices = {
            "DS": {
                "command": "TrackStop",
                "awaitedAttribute": "pointingstate",
                "awaitedValuesList": [PointingState.READY],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "TrackStop",
            "pointingstate",
            PointingState.READY,
        )

    def configure_band2_cmd(
        self,
        synchronise,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Configure band 2 on DS and SPF"""
        self.logger.info(f"ConfigureBand2 called with synchronise = {synchronise}")

        commands_for_sub_devices = {
            "DS": {
                "command": "SetIndexPosition",
                "commandArgument": 2,
                "awaitedAttribute": "indexerposition",
                "awaitedValuesList": [IndexerPosition.B2],
            },
            "SPFRX": {
                "command": "ConfigureBand2",
                "commandArgument": synchronise,
                "awaitedAttribute": "configuredband",
                "awaitedValuesList": [Band.B2],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
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
        commands_for_sub_devices = {
            "DS": {
                "command": "Stow",
                "awaitedAttribute": "operatingmode",
                "awaitedValuesList": [DSOperatingMode.STOW],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "Stow",
            "dishmode",
            DishMode.STOW,
        )

    def _fan_out_cmd(self, task_callback, device, fan_out_args, command_ids):
        command_name = fan_out_args["command"]
        command_argument = fan_out_args.get("commandArgument")
        command = SubmittedSlowCommand(
            f"{device}_{command_name}",
            self._command_tracker,
            self._dish_manager_cm.sub_component_managers[device],
            "run_device_command",
            callback=None,
            logger=self.logger,
        )

        # fail the command immediately, if the subservient device fails
        response, command_id = command(command_name, command_argument)
        if response == TaskStatus.FAILED:
            raise RuntimeError

        # Report that the command has been called on the subservient device
        task_callback(
            progress=(
                f"{fan_out_args['command']} called on "
                f"{self._key_to_output(device)}, ID {command_id}"
            )
        )

        awaited_attribute = fan_out_args["awaitedAttribute"]
        awaited_values_list = fan_out_args["awaitedValuesList"]

        # Report which attribute and value the device is waiting for
        task_callback(
            progress=(
                f"Awaiting {self._key_to_output(device)} {awaited_attribute}"
                f" change to {awaited_values_list}"
            )
        )
        # store the command id to track later
        command_ids[device] = command_id

    def _is_fan_out_cmd_executing(self, task_callback, device, command_ids, running_command):
        command_id = command_ids[device]
        current_status = self._command_tracker.get_command_status(command_id)
        if current_status == TaskStatus.FAILED:
            task_callback(
                status=TaskStatus.FAILED,
                result=f"{running_command} failed waiting on {device}",
            )
            return False
        return True

    def _report_fan_out_cmd_progress(self, task_callback, device, fan_out_args, progress_store):
        awaited_attribute = fan_out_args["awaitedAttribute"]
        awaited_values_list = fan_out_args["awaitedValuesList"]

        component_attr_value = self._dish_manager_cm.sub_component_managers[
            device
        ].component_state[awaited_attribute]

        if component_attr_value in awaited_values_list:
            if not progress_store[device]:
                task_callback(
                    progress=f"{device} {awaited_attribute} changed to {awaited_values_list}"
                )

                progress_store[device] = True

    # pylint: disable=too-many-locals
    def _run_long_running_command(
        self,
        task_callback,
        task_abort_event,
        commands_for_sub_devices,
        running_command,
        awaited_event_attribute,
        awaited_event_value,
    ):
        assert task_callback, "task_callback has to be defined"

        if task_abort_event.is_set():
            task_callback(
                progress=f"{running_command} Aborted",
                status=TaskStatus.ABORTED,
                result=f"{running_command} Aborted",
            )
            return
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}

        for device, fan_out_args in commands_for_sub_devices.items():
            try:
                args = (task_callback, device, fan_out_args, device_command_ids)
                self._fan_out_cmd(*args)
            except RuntimeError:
                cmd_name = fan_out_args["command"]
                task_callback(
                    status=TaskStatus.FAILED,
                    result=f"{running_command} failed while executing {cmd_name} on {device}",
                )
                return

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

        success_reported = dict.fromkeys(commands_for_sub_devices.keys(), False)

        while True:
            if task_abort_event.is_set():
                task_callback(
                    progress=f"{running_command} Aborted",
                    status=TaskStatus.ABORTED,
                    result=f"{running_command} Aborted",
                )
                return

            for device, fan_out_args in commands_for_sub_devices.items():
                # stop waiting if the any of the fanned out commands fail
                args = (task_callback, device, device_command_ids, running_command)
                if not self._is_fan_out_cmd_executing(*args):
                    return
                # Check each device and report attribute values that are in the expected state
                args = (task_callback, device, fan_out_args, success_reported)
                self._report_fan_out_cmd_progress(*args)

            # Check on dishmanager to see whether the LRC has completed
            current_awaited_value = self._dish_manager_cm.component_state[awaited_event_attribute]
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
