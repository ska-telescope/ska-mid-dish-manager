"""Module to manage the mapping of commands to subservient devices"""

import enum
import json
from typing import Any, Callable, Optional
from tango import DeviceProxy

from ska_control_model import ResultCode, TaskStatus
from ska_tango_base.commands import SubmittedSlowCommand
from ska_tango_base.long_running_commands_api import *

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
        self.lrc_commands_results = {}

    # pylint: disable=protected-access
    def is_device_ignored(self, device: str):
        """Check whether the given device is ignored."""
        return self._dish_manager_cm.is_device_ignored(device)

    def set_standby_lp_mode(self, task_callback: Optional[Callable] = None, task_abort_event=None):
        """Transition the dish to STANDBY_LP mode"""
        commands_for_sub_devices = {
            "SPF": {
                "command": "SetStandbyLPMode",
                "awaitedAttributes": ["operatingmode"],
                "awaitedValuesList": [SPFOperatingMode.STANDBY_LP],
            },
            "SPFRX": {
                "command": "SetStandbyMode",
                "awaitedAttributes": ["operatingmode"],
                "awaitedValuesList": [SPFRxOperatingMode.STANDBY],
            },
            "DS": {
                "command": "SetStandbyLPMode",
                "awaitedAttributes": ["operatingmode"],
                "awaitedValuesList": [DSOperatingMode.STANDBY_LP],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "SetStandbyLPMode",
            ["dishmode"],
            [DishMode.STANDBY_LP],
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
                    "awaitedAttributes": ["operatingmode"],
                    "awaitedValuesList": [DSOperatingMode.STANDBY_FP],
                }
            }
        else:
            commands_for_sub_devices = {
                "SPF": {
                    "command": "SetOperateMode",
                    "awaitedAttributes": ["operatingmode"],
                    "awaitedValuesList": [SPFOperatingMode.OPERATE],
                },
                "DS": {
                    "command": "SetStandbyFPMode",
                    "awaitedAttributes": ["operatingmode"],
                    "awaitedValuesList": [DSOperatingMode.STANDBY_FP],
                },
            }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "SetStandbyFPMode",
            ["dishmode"],
            [DishMode.STANDBY_FP],
        )

    def set_operate_mode(
        self,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Transition the dish to OPERATE mode"""
        if self._dish_manager_cm.component_state["configuredband"] in [Band.NONE, Band.UNKNOWN]:
            task_callback(
                progress="No configured band: SetOperateMode execution not allowed",
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, "SetOperateMode requires a configured band"),
            )
            return

        commands_for_sub_devices = {
            "SPF": {
                "command": "SetOperateMode",
                "awaitedAttributes": ["operatingmode"],
                "awaitedValuesList": [SPFOperatingMode.OPERATE],
            },
            "DS": {
                "command": "SetPointMode",
                "awaitedAttributes": ["operatingmode"],
                "awaitedValuesList": [DSOperatingMode.POINT],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "SetOperateMode",
            ["dishmode"],
            [DishMode.OPERATE],
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
                "awaitedAttributes": ["pointingstate"],
                "awaitedValuesList": [PointingState.TRACK],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "Track",
            ["pointingstate"],
            [PointingState.TRACK],
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
                "awaitedAttributes": ["pointingstate"],
                "awaitedValuesList": [PointingState.READY],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "TrackStop",
            ["pointingstate"],
            [PointingState.READY],
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

        if self._dish_manager_cm.component_state["configuredband"] == band_enum:
            task_callback(
                progress=f"Already in band {band_enum}",
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, f"{requested_cmd} completed"),
            )
            return

        self.logger.info(f"{requested_cmd} called with synchronise = {synchronise}")

        commands_for_sub_devices = {
            "DS": {
                "command": "SetIndexPosition",
                "commandArgument": int(band_number),
                "awaitedAttributes": ["indexerposition"],
                "awaitedValuesList": [indexer_enum],
            },
            "SPFRX": {
                "command": requested_cmd,
                "commandArgument": synchronise,
                "awaitedAttributes": ["configuredband"],
                "awaitedValuesList": [band_enum],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            requested_cmd,
            ["configuredband"],
            [band_enum],
        )

    def slew(
        self, argin: list[float], task_abort_event=None, task_callback: Optional[Callable] = None
    ):
        """Transition the dish to Slew mode"""
        commands_for_sub_devices = {
            "DS": {
                "command": "Slew",
                "commandArgument": argin,
                "awaitedAttributes": ["pointingstate"],
                "awaitedValuesList": [PointingState.SLEW],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "Slew",
            ["pointingstate"],
            [PointingState.SLEW],
        )

    # pylint: disable=unused-argument
    def scan(self, task_abort_event=None, task_callback: Optional[Callable] = None):
        """Transition the dish to Scan mode"""
        # TODO: This is a temporary workaround (Pending further implementation details)
        # to support TMC integration.
        self.logger.info("Scan command called")

        if task_callback is not None:
            task_callback(
                progress="Scan completed",
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, "Scan completed"),
            )

    def track_load_static_off(
        self, off_xel, off_el, task_abort_event=None, task_callback: Optional[Callable] = None
    ):
        """Transition the dish to Track Load Static Off mode"""
        commands_for_sub_devices = {
            "DS": {
                "command": "TrackLoadStaticOff",
                "commandArgument": [off_xel, off_el],
                "awaitedAttributes": ["actstaticoffsetvaluexel", "actstaticoffsetvalueel"],
                "awaitedValuesList": [off_xel, off_el],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "TrackLoadStaticOff",
            ["actstaticoffsetvaluexel", "actstaticoffsetvalueel"],
            [off_xel, off_el],
        )

    def _lrc_callback(self, result: list[Any] | None = None,**kwargs):
        if result is not None:
            for r in result:
                self.logger.info(f"Result from subdevice is {r}")
                

    def _fan_out_cmd(self, task_callback, device, fan_out_args):
        """Fan out the respective command to the subservient devices"""
        command_name = fan_out_args["command"]
        command_argument = fan_out_args.get("commandArgument")

        # command = SubmittedSlowCommand(
        #     f"{device}_{command_name}",
        #     self._command_tracker,
        #     self._dish_manager_cm.sub_component_managers[device],
        #     "run_device_command",
        #     callback=None,
        #     logger=self.logger,
        # )

        # response, command_id = command(command_name, command_argument)
        # Report that the command has been called on the subservient device
        device_fqdns = {"DS":"mid-dish/ds-manager/SKA001", "SPF":"mid-dish/simulator-spfc/SKA001","SPF":"mid-dish/simulator-spfrx/SKA001"}
        if device in device_fqdns:
            try:
                dp = DeviceProxy(device_fqdns[device])
                lrc_subscriptions = invoke_lrc(self._lrc_callback, dp,command_name,command_args=command_argument)
            except Exception as err:
                self.logger.info(f"SOMETHING WENT WRONG WITH INVOKE_LRC : {err}")

        task_callback(progress=f"{fan_out_args['command']} called on {device} and with the command response {response} , ID {command_id}")

        # fail the command immediately, if the subservient device fails
        if response == TaskStatus.FAILED:
            raise RuntimeError(command_id)

        awaited_attributes = fan_out_args["awaitedAttributes"]
        awaited_values_list = fan_out_args["awaitedValuesList"]

        # Report which attribute and value the sub device is waiting for
        # e.g. Awaiting DEVICE attra, attrb change to VALUE_1, VALUE_2
        if awaited_values_list is not None:
            values_print_string = self.convert_enums_to_names(awaited_values_list)
            attributes_print_string = ", ".join(map(str, awaited_attributes))
            values_print_string = ", ".join(map(str, values_print_string))

            task_callback(
                progress=(
                    f"Awaiting {device} {attributes_print_string} change to {values_print_string}"
                )
            )
        return command_id

    def _fanout_command_has_failed(self, command_id):
        """Check the status of the fanned out command on the subservient device"""
        current_status = self._command_tracker.get_command_status(command_id)
        if current_status == TaskStatus.FAILED:
            return True
        return False

    def _report_fan_out_cmd_progress(self, task_callback, device, fan_out_args):
        """Report and update the progress of the fanned out command"""
        awaited_attributes = fan_out_args["awaitedAttributes"]
        awaited_values_list = fan_out_args["awaitedValuesList"]
        device_cm_component_state = self._dish_manager_cm.sub_component_managers[
            device
        ].component_state

        got_all_awaited_values = True
        for awaited_attribute, expected_val in zip(awaited_attributes, awaited_values_list):
            component_state_attr_value = device_cm_component_state[awaited_attribute]

            if component_state_attr_value == expected_val:
                task_callback(progress=f"{device} {awaited_attribute} changed to {expected_val}")
            else:
                got_all_awaited_values = False
        return got_all_awaited_values

    def convert_enums_to_names(self, values) -> list[str]:
        """Convert any enums in the given list to their names."""
        enum_labels = []
        for val in values:
            if isinstance(val, enum.IntEnum):
                enum_labels.append(val.name)
            else:
                enum_labels.append(val)
        return enum_labels

    # pylint: disable=too-many-locals, too-many-branches
    def _run_long_running_command(
        self,
        task_callback: Callable,
        task_abort_event: Any,
        commands_for_sub_devices: dict,
        running_command: str,
        awaited_event_attributes: list[str],
        awaited_event_values: list[Any],
    ):
        """Run the long running command and track progress"""
        assert task_callback, "task_callback has to be defined"

        if task_abort_event.is_set():
            task_callback(
                progress=f"{running_command} Aborted",
                status=TaskStatus.ABORTED,
                result=(ResultCode.ABORTED, f"{running_command} Aborted"),
            )
            return
        task_callback(status=TaskStatus.IN_PROGRESS)

        device_command_ids = {}

        for device, fan_out_args in commands_for_sub_devices.items():
            cmd_name = fan_out_args["command"]
            if self.is_device_ignored(device):
                task_callback(progress=f"{device} device is disabled. {cmd_name} call ignored")
            else:
                try:
                    device_command_ids[device] = self._fan_out_cmd(
                        task_callback, device, fan_out_args
                    )
                except RuntimeError as ex:
                    device_command_ids[device] = ex.args[0]
                    task_callback(
                        progress=(
                            f"{device} device failed to execute {cmd_name} command with"
                            f" ID {device_command_ids[device]}"
                        )
                    )

        task_callback(progress=f"Commands: {json.dumps(device_command_ids)}")

        # If we're not waiting for anything, finish up
        if awaited_event_values is None:
            task_callback(
                progress=f"{running_command} completed",
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, f"{running_command} completed"),
            )
            return

        # Report which attribute and value the dish manager is waiting for
        # e.g. Awaiting dishmode change to STANDBY_LP
        awaited_event_values_print = self.convert_enums_to_names(awaited_event_values)

        attributes_print_string = ", ".join(map(str, awaited_event_attributes))
        values_print_string = ", ".join(map(str, awaited_event_values_print))
        task_callback(
            progress=(f"Awaiting {attributes_print_string} change to {values_print_string}")
        )

        for fan_out_args in commands_for_sub_devices.values():
            fan_out_args["progress_updated"] = False
            fan_out_args["command_has_failed"] = False

        while True:
            if task_abort_event.is_set():
                task_callback(
                    progress=f"{running_command} Aborted",
                    status=TaskStatus.ABORTED,
                    result=(ResultCode.ABORTED, f"{running_command} Aborted"),
                )
                return

            for device, fan_out_args in commands_for_sub_devices.items():
                if not self.is_device_ignored(device):
                    # Check each device and report attribute values that are in the expected state
                    if not fan_out_args["progress_updated"]:
                        fan_out_args["progress_updated"] = self._report_fan_out_cmd_progress(
                            task_callback, device, fan_out_args
                        )

                    command_in_progress = fan_out_args["command"]
                    if not fan_out_args["command_has_failed"]:
                        if self._fanout_command_has_failed(device_command_ids[device]):
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
            #         status=TaskStatus.FAILED,
            #         result=(ResultCode.OK, f"{running_command} completed"),
            #     )
            #     return

            # Check on dishmanager to see whether the LRC has completed
            dm_cm_component_state = self._dish_manager_cm.component_state

            got_all_awaited_values = True
            for awaited_attribute, expected_val in zip(
                awaited_event_attributes, awaited_event_values
            ):
                component_state_attr_value = dm_cm_component_state[awaited_attribute]

                if component_state_attr_value != expected_val:
                    got_all_awaited_values = False
                    break

            if not got_all_awaited_values:
                task_abort_event.wait(timeout=1)
                for device in commands_for_sub_devices.keys():
                    if not self.is_device_ignored(device):
                        component_manager = self._dish_manager_cm.sub_component_managers[device]
                        component_manager.update_state_from_monitored_attributes()
            else:
                task_callback(
                    progress=f"{running_command} completed",
                    status=TaskStatus.COMPLETED,
                    result=(ResultCode.OK, f"{running_command} completed"),
                )
                return
