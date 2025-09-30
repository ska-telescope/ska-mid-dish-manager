"""Module to manage the mapping of commands to subservient devices."""

import enum
import json
from typing import Any, Callable, List, Optional

import tango
from ska_control_model import AdminMode, ResultCode, TaskStatus
from ska_tango_base.commands import SubmittedSlowCommand

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    PointingState,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


def convert_enums_to_names(values: list[Any]) -> list[str]:
    """Convert any enums in the given list to their names."""
    enum_labels = []
    for val in values:
        if isinstance(val, enum.IntEnum):
            enum_labels.append(val.name)
        else:
            enum_labels.append(val)
    return enum_labels


def update_task_status(task_callback: Optional[Callable], **task_statuses) -> None:
    """Wraps the task callback to report lrc statuses."""
    if task_callback:
        task_callback(**task_statuses)


class CommandMap:
    """Command fan out to handle the mapping of DishManager commands to subservient devices."""

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

    # pylint: disable=protected-access
    def is_device_ignored(self, device: str):
        """Check whether the given device is ignored."""
        return self._dish_manager_cm.is_device_ignored(device)

    def set_standby_lp_mode(self, task_callback: Optional[Callable] = None, task_abort_event=None):
        """Transition the dish to STANDBY_LP mode."""
        if not self._ensure_spfrx_online(task_callback):
            return

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
        """Transition the dish to STANDBY_FP mode."""
        dishmode = self._dish_manager_cm.component_state["dishmode"].name
        if dishmode == "OPERATE":
            commands_for_sub_devices = {
                "DS": {
                    "command": "SetStandbyFPMode",
                    "awaitedAttributes": ["operatingmode"],
                    "awaitedValuesList": [DSOperatingMode.STANDBY_FP],
                },
            }
        elif dishmode == "MAINTENANCE":
            if not self._ensure_spfrx_online(task_callback):
                return
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
                "SPFRX": {
                    "command": "SetStandbyMode",
                    "awaitedAttributes": ["operatingmode"],
                    "awaitedValuesList": [SPFRxOperatingMode.STANDBY],
                },
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
        """Transition the dish to OPERATE mode."""
        if self._dish_manager_cm.component_state["configuredband"] in [Band.NONE, Band.UNKNOWN]:
            update_task_status(
                task_callback,
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

    def set_maintenance_mode(
        self,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Transition the dish to MAINTENANCE mode."""
        if not self._dish_manager_cm.is_device_ignored("SPFRX"):
            try:
                # TODO: Wait for the SPFRx to implement maintenance mode
                self.logger.debug("Nothing done on SPFRx, awaiting implementation on it.")

                # spfrx_cm.write_attribute_value("adminmode", AdminMode.ENGINEERING)
            except tango.DevFailed as err:
                self.logger.exception(
                    "Failed to configure SPFRx adminMode ENGINEERING"
                    " on call to SetMaintenanceMode."
                )
                update_task_status(task_callback, status=TaskStatus.FAILED, exception=err)
                return

        commands_for_sub_devices = {
            "SPF": {
                "command": "SetMaintenanceMode",
                "awaitedAttributes": ["operatingmode"],
                "awaitedValuesList": [SPFOperatingMode.MAINTENANCE],
            },
            "DS": {
                "command": "Stow",
                "awaitedAttributes": ["operatingmode"],
                "awaitedValuesList": [DSOperatingMode.STOW],
            },
        }

        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "SetMaintenanceMode",
            ["dishmode"],
            [DishMode.MAINTENANCE],
        )

    # pylint: disable = no-value-for-parameter
    def track_cmd(
        self,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Transition the dish to Track mode."""
        commands_for_sub_devices = {
            "DS": {
                "command": "Track",
                "awaitedAttributes": [],
                "awaitedValuesList": [],
            },
        }
        status_message = (
            "Track command has been executed on DS. "
            "Monitor the achievedTargetLock attribute to determine when the dish is on source."
        )
        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "Track",
            None,
            None,
            status_message,
        )

    def track_stop_cmd(
        self,
        task_abort_event=None,
        task_callback: Optional[Callable] = None,
    ):
        """Stop Tracking."""
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
        """Configure band on DS and SPFRx."""
        band_enum = Band[f"B{band_number}"]
        indexer_enum = IndexerPosition[f"B{band_number}"]
        requested_cmd = f"ConfigureBand{band_number}"

        if self._dish_manager_cm.component_state["configuredband"] == band_enum:
            update_task_status(
                task_callback,
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

    # pylint: disable = no-value-for-parameter
    def slew(
        self, argin: list[float], task_abort_event=None, task_callback: Optional[Callable] = None
    ):
        """Transition the dish to Slew mode."""
        commands_for_sub_devices = {
            "DS": {
                "command": "Slew",
                "commandArgument": argin,
                "awaitedAttributes": [],
                "awaitedValuesList": [],
            },
        }
        status_message = (
            f"The DS has been commanded to Slew to {argin}. "
            "Monitor the pointing attributes for the completion status of the task."
        )
        self._run_long_running_command(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            "Slew",
            None,
            None,
            status_message,
        )

    # pylint: disable=unused-argument
    def scan(self, task_abort_event=None, task_callback: Optional[Callable] = None):
        """Transition the dish to Scan mode."""
        # TODO: This is a temporary workaround (Pending further implementation details)
        # to support TMC integration.
        self.logger.info("Scan command called")

        if task_callback is not None:
            update_task_status(
                task_callback,
                progress="Scan completed",
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, "Scan completed"),
            )

    def track_load_static_off(
        self, off_xel, off_el, task_abort_event=None, task_callback: Optional[Callable] = None
    ):
        """Transition the dish to Track Load Static Off mode."""
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

    def _ensure_spfrx_online(self, task_callback) -> bool:
        """Ensure SPFRX is ONLINE if not ignored and in ENGINEERING mode."""
        if self._is_device_ignored("SPFRX"):
            return True
        spfrx_cm = self._dish_manager_cm.sub_component_managers["SPFRX"]
        if spfrx_cm.component_state["adminmode"] == AdminMode.ENGINEERING:
            try:
                spfrx_cm.write_attribute_value("adminmode", AdminMode.ONLINE)
            except tango.DevFailed:
                update_task_status(
                    task_callback,
                    status=TaskStatus.FAILED,
                    result=(
                        ResultCode.FAILED,
                        "Failed to transition SPFRx from AdminMode ENGINEERING to ONLINE",
                    ),
                )
                return False
        return True

    def _is_device_ignored(self, device: str) -> bool:
        return self._dish_manager_cm.is_device_ignored(device)

    def _report_awaited_attributes(
        self, task_callback, awaited_attrs, awaited_values, device=None
    ):
        """Report the awaited attributes and their expected values."""
        if awaited_attrs:
            awaited_attrs = ", ".join(map(str, awaited_attrs))
            awaited_values = convert_enums_to_names(awaited_values)
            awaited_values = ", ".join(map(str, awaited_values))
            if device:
                msg = f"Awaiting {device} {awaited_attrs} change to {awaited_values}"
            else:
                msg = f"Awaiting {awaited_attrs} change to {awaited_values}"
            update_task_status(task_callback, progress=msg)

    def _fan_out_cmd(self, task_callback, device, fan_out_args):
        """Fan out the respective command to the subservient devices."""
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

        response, command_id = command(command_name, command_argument)
        # Report that the command has been called on the subservient device
        update_task_status(
            task_callback,
            progress=f"{fan_out_args['command']} called on {device}, ID {command_id}",
        )

        # fail the command immediately, if the subservient device fails
        if response == TaskStatus.FAILED:
            raise RuntimeError(command_id)

        awaited_attributes = fan_out_args["awaitedAttributes"]
        awaited_values_list = fan_out_args["awaitedValuesList"]
        self._report_awaited_attributes(
            task_callback, awaited_attributes, awaited_values_list, device
        )

        return command_id

    def _is_dish_at_commanded_state(self, attributes, expected_values) -> bool:
        """Checks if the dish state matches the commanded state for given attributes."""
        component_state = self._dish_manager_cm.component_state
        for attribute, expected_value in zip(attributes, expected_values):
            if component_state[attribute] != expected_value:
                return False
        return True

    def _refresh_sub_component_states(self, sub_devices: list, task_abort_event):
        """Poll the monitored attributes on each subcomponent manager to update its state."""
        for device in sub_devices:
            if not self._is_device_ignored(device):
                component_manager = self._dish_manager_cm.sub_component_managers[device]
                component_manager.update_state_from_monitored_attributes(task_abort_event)

    def _report_sub_device_command_progress(self, sub_cmds, task_callback):
        """Report progress of awaited attributes from sub-devices."""
        devices_to_remove = []
        for device, fan_out_args in sub_cmds.items():
            if self._is_device_ignored(device):
                continue

            component_manager = self._dish_manager_cm.sub_component_managers[device]
            component_state = component_manager.component_state
            awaited_attrs = fan_out_args["awaitedAttributes"]
            awaited_values = fan_out_args["awaitedValuesList"]
            for attr, expected_val in zip(awaited_attrs, awaited_values):
                if component_state[attr] == expected_val:
                    update_task_status(
                        task_callback,
                        progress=f"{device} {attr} changed to {expected_val}",
                    )
                    devices_to_remove.append(device)

        for device in devices_to_remove:
            sub_cmds.pop(device, None)

    def _wait_for_commanded_dish_state(
        self,
        task_callback: Optional[Callable],
        task_abort_event: Any,
        sub_cmds: dict,
        running_command: str,
        awaited_event_attributes: Optional[List[str]],
        awaited_event_values: Optional[List[Any]],
        ok_msg: str,
    ):
        """Wait for the dish to reach the commanded state."""
        # if we're not waiting for anything, finish up
        if not awaited_event_values:
            update_task_status(
                task_callback,
                progress=ok_msg,
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, ok_msg),
            )
            self.logger.info(ok_msg)
            return

        self._report_awaited_attributes(
            task_callback, awaited_event_attributes, awaited_event_values
        )
        while True:
            if task_abort_event.is_set():
                update_task_status(
                    task_callback,
                    progress=f"{running_command} Aborted",
                    status=TaskStatus.ABORTED,
                    result=(ResultCode.ABORTED, f"{running_command} Aborted"),
                )
                return

            self._refresh_sub_component_states(list(sub_cmds.keys()), task_abort_event)
            self._report_sub_device_command_progress(sub_cmds, task_callback)

            if self._is_dish_at_commanded_state(awaited_event_attributes, awaited_event_values):
                update_task_status(
                    task_callback,
                    progress=ok_msg,
                    status=TaskStatus.COMPLETED,
                    result=(ResultCode.OK, ok_msg),
                )
                self.logger.info(ok_msg)
                return
            task_abort_event.wait(1)

    def _run_long_running_command(
        self,
        task_callback: Optional[Callable],
        task_abort_event: Any,
        commands_for_sub_devices: dict,
        running_command: str,
        awaited_event_attributes: Optional[List[str]] = None,
        awaited_event_values: Optional[List[Any]] = None,
        completed_response_msg: Optional[str] = None,
    ):
        """Executes a long-running command.

        Fans out sub-commands to subservient devices, monitors their
        progress, and reports status updates via the provided callback.

        task_callback: Callback to report progress, status, and result.
        task_abort_event: Event to signal abortion of the ongoing task.
        commands_for_sub_devices: Mapping of device names to their respective command arguments.
        running_command: Name of the command being executed.
        awaited_event_attributes: List of attributes to monitor for completion.
        awaited_event_values: Expected values for the awaited attributes.
        completed_response_msg: Custom completion message for the callback.
        """
        if task_abort_event.is_set():
            update_task_status(
                task_callback,
                progress=f"{running_command} Aborted",
                status=TaskStatus.ABORTED,
                result=(ResultCode.ABORTED, f"{running_command} Aborted"),
            )
            return
        update_task_status(task_callback, status=TaskStatus.IN_PROGRESS)

        error_messages = []
        failed_cmds = {}
        successful_cmds = {}

        for device, fan_out_args in commands_for_sub_devices.items():
            cmd_name = fan_out_args["command"]
            if self._is_device_ignored(device):
                self.logger.debug(
                    f"{device} device is disabled. "
                    f"{device}.{cmd_name} call ignored for DishManager.{running_command}"
                )
                continue
            try:
                successful_cmds[device] = self._fan_out_cmd(task_callback, device, fan_out_args)
            except RuntimeError as ex:
                failed_cmds[device] = ex.args[0]

        if failed_cmds:
            for device, err in failed_cmds.items():
                cmd = commands_for_sub_devices[device]["command"]
                error_messages.append(
                    f"{device} device failed executing {cmd} command with error {err}"
                )
            error_message = "; ".join(error_messages)
            self.logger.error(error_message)
            update_task_status(
                task_callback,
                progress=f"{error_message}",
                status=TaskStatus.FAILED,
                result=(ResultCode.FAILED, f"{running_command} failed"),
            )
            return

        update_task_status(task_callback, progress=f"Commands: {json.dumps(successful_cmds)}")

        final_message = (
            completed_response_msg if completed_response_msg else f"{running_command} completed"
        )

        self._wait_for_commanded_dish_state(
            task_callback,
            task_abort_event,
            commands_for_sub_devices,
            running_command,
            awaited_event_attributes,
            awaited_event_values,
            final_message,
        )
