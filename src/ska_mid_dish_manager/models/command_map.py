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
                "awaitedAttribute": "pointingstate",
                "awaitedValuesList": [PointingState.TRACK],
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

    def configure_band_cmd(
        self,
        band_number,
        synchronise,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Configure band on DS and SPFRx"""
        band_enum = Band[f"B{band_number}"]
        indexer_enum = IndexerPosition[f"B{band_number}"]
        requested_cmd = f"ConfigureBand{band_number}"
        self.logger.info(f"{requested_cmd} called with synchronise = {synchronise}")

        commands_for_sub_devices = {
            "DS": {
                "command": "SetIndexPosition",
                "commandArgument": int(band_number),
                "awaitedAttribute": "indexerposition",
                "awaitedValuesList": [indexer_enum],
            },
            "SPFRX": {
                "command": requested_cmd,
                "commandArgument": synchronise,
                "awaitedAttribute": "configuredband",
                "awaitedValuesList": [band_enum],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            requested_cmd,
            "configuredband",
            band_enum,
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

    def slew(
        self, argin: list[float], task_abort_event=None, task_callback: Optional[Callable] = None
    ):
        """Transition the dish to Stow mode"""
        commands_for_sub_devices = {
            "DS": {
                "command": "Slew",
                "commandArgument": argin,
                "awaitedAttribute": "pointingState",
                "awaitedValuesList": [PointingState.SLEW],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "Slew",
            "pointingstate",
            PointingState.SLEW,
        )

    def track_load_static_off(
        self, argin: list[float], task_abort_event=None, task_callback: Optional[Callable] = None
    ):
        """Transition the dish to Stow mode"""
        commands_for_sub_devices = {
            "DS": {
                "command": "TrackLoadStaticOff",
                "commandArgument": argin,
                "awaitedAttribute": "",
                "awaitedValuesList": [],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "TrackLoadStaticOff",
            "",
            None,
        )

    def _fan_out_cmd(self, task_callback, device, fan_out_args, skip_progress_updates=False):
        """Fan out the respective command to the subservient devices"""
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
        # Report that the command has been called on the subservient device
        task_callback(
            progress=(
                f"{fan_out_args['command']} called on "
                f"{self._key_to_output(device)}, ID {command_id}"
            )
        )

        if response == TaskStatus.FAILED:
            raise RuntimeError(command_id)

        awaited_attribute = fan_out_args["awaitedAttribute"]
        awaited_values_list = fan_out_args["awaitedValuesList"]

        # Report which attribute and value the device is waiting for
        if not skip_progress_updates:
            task_callback(
                progress=(
                    f"Awaiting {self._key_to_output(device)} {awaited_attribute}"
                    f" change to {awaited_values_list}"
                )
            )
        return command_id

    def _fanout_command_has_failed(self, device, command_ids):
        """Check the status of the fanned out command on the subservient device"""
        command_id = command_ids[device]
        current_status = self._command_tracker.get_command_status(command_id)
        if current_status == TaskStatus.FAILED:
            return True
        return False

    def _report_fan_out_cmd_progress(self, task_callback, device, fan_out_args):
        """Report and update the progress of the fanned out command"""
        awaited_attribute = fan_out_args["awaitedAttribute"]
        awaited_values_list = fan_out_args["awaitedValuesList"]

        component_attr_value = self._dish_manager_cm.sub_component_managers[
            device
        ].component_state[awaited_attribute]

        if component_attr_value in awaited_values_list:
            task_callback(
                progress=f"{device} {awaited_attribute} changed to {awaited_values_list}"
            )
            return True
        return False

    # pylint: disable=too-many-locals, too-many-branches
    def _run_long_running_command(
        self,
        task_callback,
        task_abort_event,
        commands_for_sub_devices,
        running_command,
        awaited_event_attribute,
        awaited_event_value,
    ):
        """Run the long running command and track progress"""
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
                device_command_ids[device] = self._fan_out_cmd(task_callback, device, fan_out_args)
            except RuntimeError as ex:
                device_command_ids[device] = ex.args[0]
                cmd_name = fan_out_args["command"]
                task_callback(
                    progress=(
                        f"{device} device failed to execute {cmd_name} command with"
                        f" ID {device_command_ids[device]}"
                    )
                )

        task_callback(progress=f"Commands: {json.dumps(device_command_ids)}")

        awaited_event_value_print = awaited_event_value
        if isinstance(awaited_event_value, enum.IntEnum):
            awaited_event_value_print = awaited_event_value.name

        # If we're not waiting for anything, finish up
        if not awaited_event_value:
            task_callback(
                progress=f"{running_command} completed",
            )
            task_callback(
                status=TaskStatus.COMPLETED,
                result=f"{running_command} completed",
            )
            return

        task_callback(
            progress=(
                f"Awaiting {self._key_to_output(awaited_event_attribute)}"
                f" change to {awaited_event_value_print}"
            )
        )

        for fan_out_args in commands_for_sub_devices.values():
            fan_out_args["progress_updated"] = False
            fan_out_args["command_has_failed"] = False

        while True:
            if task_abort_event.is_set():
                task_callback(
                    progress=f"{running_command} Aborted",
                    status=TaskStatus.ABORTED,
                    result=f"{running_command} Aborted",
                )
                return

            for device, fan_out_args in commands_for_sub_devices.items():
                # Check each device and report attribute values that are in the expected state
                if not fan_out_args["progress_updated"]:
                    fan_out_args["progress_updated"] = self._report_fan_out_cmd_progress(
                        task_callback, device, fan_out_args
                    )

                command_in_progress = fan_out_args["command"]
                if not fan_out_args["command_has_failed"]:
                    if self._fanout_command_has_failed(device, device_command_ids):
                        task_callback(
                            progress=(
                                f"{device} device failed executing {command_in_progress} "
                                f"command with ID {device_command_ids[device]}"
                            )
                        )
                        fan_out_args["command_has_failed"] = True

            # TODO: If all three commands have failed, then bail
            # if all(
            #     sub_device_command["command_has_failed"]
            #     for sub_device_command in commands_for_sub_devices.values()
            # ):
            #     task_callback(
            #         progress=f"{running_command} completed",
            #     )
            #     task_callback(
            #         status=TaskStatus.FAILED,
            #         result=f"{running_command} completed",
            #     )
            #     return

            # Check on dishmanager to see whether the LRC has completed
            current_awaited_value = self._dish_manager_cm.component_state[awaited_event_attribute]

            if current_awaited_value != awaited_event_value:
                task_abort_event.wait(timeout=1)
                for device in commands_for_sub_devices.keys():
                    component_manager = self._dish_manager_cm.sub_component_managers[device]
                    component_manager.update_state_from_monitored_attributes()
            else:
                task_callback(
                    progress=f"{running_command} completed",
                )
                task_callback(
                    status=TaskStatus.COMPLETED,
                    result=f"{running_command} completed",
                )
                return
