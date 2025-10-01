"""Module containing the fanned out command actions."""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional

import tango
from ska_control_model import AdminMode, ResultCode, TaskStatus
from ska_tango_base.base import CommandTracker

from ska_mid_dish_manager.models.constants import DSC_MIN_POWER_LIMIT_KW
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    PointingState,
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from ska_mid_dish_manager.models.fanned_out_command import FannedOutCommand, FannedOutSlowCommand
from ska_mid_dish_manager.utils.action_helpers import (
    check_component_state_matches_awaited,
    convert_enums_to_names,
)


class Action(ABC):
    """Base class for actions. Subclasses should implement execute()."""

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker: CommandTracker,
        dish_manager_cm,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        self.logger = logger
        self.command_tracker = command_tracker
        self.dish_manager_cm = dish_manager_cm
        self.action_on_success = action_on_success
        self.action_on_failure = action_on_failure
        self.waiting_callback = waiting_callback

    @abstractmethod
    def execute(
        self,
        task_callback: Callable,
        task_abort_event: Any,
        completed_response_msg: Optional[str] = None,
    ):
        """Execute the defined action."""
        pass


class ActionHandler:
    """Manages a group of fanned-out commands. It succeeds only if all fanned-out commandss.
    It fails if any fanned out command fails or times out, or if the main action times out.
    """

    def __init__(
        self,
        logger: logging.Logger,
        name: str,
        fanned_out_commands: List[FannedOutCommand],
        component_state: dict,
        awaited_component_state: Optional[dict] = {},
        action_on_success: Optional[Action] = None,
        action_on_failure: Optional[Action] = None,
        waiting_callback: Callable = None,
    ):
        """:param logger: Logger instance
        :type logger: Logger
        :param name: A name for this command action
        :type name: str
        :param fanned_out_commands: A list of FannedOutCommand classes to be executed.
        :type fanned_out_commands: list[FannedOutCommand]
        :param component_state: The component state containing the attributes to wait for updates
            on.
        :type component_state: Optional[dict]
        :param awaited_component_state: The component state containing the attributes and values to
            wait for.
        :type awaited_component_state: Optional[dict]
        :param action_on_success: Optional Action to execute on success.
        :type action_on_success: Callable
        :param action_on_success: Optional Action to execute on failure.
        :type action_on_failure: Callable[str]
        :param waiting_callback: Optional callback to execute on each iteration while waiting on
            commands.
        :type waiting_callback: Callable[str]
        """
        self.logger = logger
        self.name = name
        self.fanned_out_commands = fanned_out_commands
        self.component_state = component_state
        self.awaited_component_state = awaited_component_state
        self.action_on_success: Optional[Action] = action_on_success
        self.action_on_failure: Optional[Action] = action_on_failure
        self.waiting_callback = waiting_callback

    def execute(
        self,
        task_callback: Callable,
        task_abort_event: Any,
        completed_response_msg: Optional[str] = None,
    ):
        """Execute all fan-out commands and track progress across subservient devices."""
        final_message = ""
        if completed_response_msg is not None:
            final_message = completed_response_msg
        else:
            final_message = f"{self.name} completed"

        def trigger_failure(message):
            self.logger.error(message)
            task_callback(progress=message)
            # Execute any chained action on failure
            if self.action_on_failure is not None:
                message = f"Triggering {self.name} on failure action"
                self.logger.debug(message)
                task_callback(progress=message)
                self.action_on_failure.execute(
                    task_callback=task_callback, task_abort_event=task_abort_event
                )
            else:
                # Only update status and result if there is no chained action
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(ResultCode.FAILED, f"{self.name} Failed"),
                )

        def trigger_success():
            self.logger.info(final_message)
            # Execute any chained action on success
            if self.action_on_success is not None:
                message = f"{self.name} complete. Triggering on success action."
                self.logger.debug(message)
                task_callback(progress=message)
                self.action_on_success.execute(
                    task_callback=task_callback,
                    task_abort_event=task_abort_event,
                    completed_response_msg=final_message,
                )
            else:
                # Only update status and result if there is no chained action
                task_callback(
                    progress=final_message,
                    status=TaskStatus.COMPLETED,
                    result=(ResultCode.OK, final_message),
                )

        if task_abort_event.is_set():
            self.logger.warning(f"Action '{self.name}' aborted.")
            task_callback(
                progress=f"{self.name} Aborted",
                status=TaskStatus.ABORTED,
                result=(ResultCode.ABORTED, f"{self.name} Aborted"),
            )
            return

        task_callback(status=TaskStatus.IN_PROGRESS)
        self.logger.debug(
            f"Starting Action '{self.name}' with {len(self.fanned_out_commands)} fanned-out"
            " commands."
        )

        # Fan-out: Dispatch all fanned-out commandss
        for cmd in self.fanned_out_commands:
            cmd.execute(task_callback)
            if cmd.failed:
                trigger_failure(f"{self.name} {cmd.cmd_response}")
                return

        fanned_out_command_ids = [c.id for c in self.fanned_out_commands]
        task_callback(progress=f"Commands: {json.dumps(fanned_out_command_ids)}")

        # If we're not waiting for anything, finish up
        if all([c.timeout_s <= 0 for c in self.fanned_out_commands]):
            trigger_success()
            return

        # In the error case that none of the fanned out commands fail but the action doesn't finish
        # then we need to timeout. Create a timeout for the action which is longer than the longest
        # of the fanned out commands
        max_fanned_out_timeout = max([c.timeout_s for c in self.fanned_out_commands])
        action_timeout_s = max_fanned_out_timeout + 5  # timeout the action after a short buffer

        # Report what we are waiting for
        if self.awaited_component_state:
            awaited_attributes = list(self.awaited_component_state.keys())
            awaited_values_list = list(self.awaited_component_state.values())

            # Report which attribute and value the sub device is waiting for
            # e.g. Awaiting DEVICE attra, attrb change to VALUE_1, VALUE_2
            if awaited_values_list != []:
                values_print_string = convert_enums_to_names(awaited_values_list)
                attributes_print_string = ", ".join(map(str, awaited_attributes))
                values_print_string = ", ".join(map(str, values_print_string))
                task_callback(
                    progress=(
                        f"Awaiting {attributes_print_string} change to {values_print_string}"
                    )
                )

        action_start_time = time.time()

        while True:
            # Handle abort
            if task_abort_event.is_set():
                self.logger.warning(f"Action '{self.name}' aborted.")
                task_callback(
                    progress=f"{self.name} Aborted",
                    status=TaskStatus.ABORTED,
                    result=(ResultCode.ABORTED, f"{self.name} Aborted"),
                )
                return

            # Handle timeout
            if time.time() - action_start_time > action_timeout_s:
                command_statuses = {
                    f"{sc.device} {sc.name} ({sc.id})": sc.status
                    for sc in self.fanned_out_commands
                }
                message = (
                    f"Action '{self.name}' timed out. Fanned out commands: {command_statuses}"
                )
                trigger_failure(message)
                return

            # Update status of all running commands
            for cmd in self.fanned_out_commands:
                cmd.report_progress(task_callback)

            # Handle any failed fanned out command
            if any([cmd.failed for cmd in self.fanned_out_commands]):
                command_statuses = {
                    f"{sc.device} {sc.name} ({sc.id})": sc.status
                    for sc in self.fanned_out_commands
                }
                message = f"Action '{self.name}' failed. Fanned out commands: {command_statuses}"
                trigger_failure(message)
                return

            # Check if all commands have succeeded
            if all([cmd.successful for cmd in self.fanned_out_commands]):
                if check_component_state_matches_awaited(
                    self.component_state, self.awaited_component_state
                ):
                    trigger_success()
                    return

            if self.waiting_callback:
                self.waiting_callback()

            task_abort_event.wait(timeout=1)

            for cmd in self.fanned_out_commands:
                if not cmd.finished:
                    if hasattr(cmd, "device_component_manager"):
                        device_component_manager = getattr(cmd, "device_component_manager")
                        device_component_manager.update_state_from_monitored_attributes(
                            cmd.awaited_component_state.keys()
                        )


# -------------------------
# Concrete Actions
# -------------------------
class SetStandbyLPModeAction(Action):
    """Transition the dish to STANDBY_LP mode."""

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker: CommandTracker,
        dish_manager_cm,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Callable = None,
    ):
        super().__init__(
            logger,
            command_tracker,
            dish_manager_cm,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )

        # TODO: Follow up on:
        # Set all SPF feed default startup attributes to STANDBY_LP. On exiting Dish STANDBY_LP
        # mode, restore all SPF default startup attributes to OPERATE mode
        self.spf_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPF",
            command_name="SetStandbyLPMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPF"],
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            command_argument=None,
            awaited_component_state={"operatingmode": SPFOperatingMode.STANDBY_LP},
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPF"),
        )

        self.spfrx_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPFRX",
            command_name="SetStandbyMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPFRX"],
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            command_argument=None,
            awaited_component_state={"operatingmode": SPFRxOperatingMode.STANDBY},
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPFRX"),
        )

        self.ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetStandbyMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            command_argument=None,
            awaited_component_state={
                "operatingmode": DSOperatingMode.STANDBY,
                "powerstate": DSPowerState.LOW_POWER,
            },
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )

        self.handler = ActionHandler(
            self.logger,
            "SetStandbyLPMode",
            [self.spf_command, self.spfrx_command, self.ds_command],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"dishmode": DishMode.STANDBY_LP},
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
        )

    def execute(
        self, task_callback, task_abort_event, completed_response_msg: Optional[str] = None
    ):
        if not self.dish_manager_cm.is_device_ignored("SPFRX"):
            spfrx_cm = self.dish_manager_cm.sub_component_managers["SPFRX"]
            if spfrx_cm._component_state["adminmode"] == AdminMode.ENGINEERING:
                try:
                    spfrx_cm.write_attribute_value("adminmode", AdminMode.ONLINE)
                except tango.DevFailed:
                    task_callback(
                        status=TaskStatus.FAILED,
                        result=(
                            ResultCode.FAILED,
                            "Failed to transition SPFRx from AdminMode ENGINEERING to ONLINE",
                        ),
                    )
                    return

        return self.handler.execute(task_callback, task_abort_event, completed_response_msg)


class SetStandbyFPModeAction(Action):
    """Transition the dish to STANDBY_FP mode."""

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker: CommandTracker,
        dish_manager_cm,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Callable = None,
    ):
        super().__init__(
            logger,
            command_tracker,
            dish_manager_cm,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        ds_set_standby_mode = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetStandbyMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"operatingmode": DSOperatingMode.STANDBY},
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )
        # Action to set the power mode of DS to Full Power
        dsc_power_limit = dish_manager_cm._component_state.get(
            "dscpowerlimitkw", DSC_MIN_POWER_LIMIT_KW
        )
        ds_set_full_power_mode = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetPowerMode",
            command_argument=[False, dsc_power_limit],
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"powerstate": DSPowerState.FULL_POWER},
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )

        self.handler = ActionHandler(
            self.logger,
            "SetStandbyFPMode",
            [ds_set_standby_mode, ds_set_full_power_mode],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"dishmode": DishMode.STANDBY_FP},
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
        )

    def execute(
        self, task_callback, task_abort_event, completed_response_msg: Optional[str] = None
    ):
        return self.handler.execute(task_callback, task_abort_event, completed_response_msg)


class SetOperateModeAction(Action):
    """Transition the dish to OPERATE mode."""

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker: CommandTracker,
        dish_manager_cm,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Callable = None,
    ):
        super().__init__(
            logger,
            command_tracker,
            dish_manager_cm,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )

        spf_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPF",
            command_name="SetOperateMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPF"],
            awaited_component_state={"operatingmode": SPFOperatingMode.OPERATE},
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPF"),
        )
        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetPointMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"operatingmode": DSOperatingMode.POINT},
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )

        self.handler = ActionHandler(
            self.logger,
            "SetOperateMode",
            [spf_command, ds_command],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"dishmode": DishMode.OPERATE},
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
        )

    def execute(
        self, task_callback, task_abort_event, completed_response_msg: Optional[str] = None
    ):
        if self.dish_manager_cm._component_state["configuredband"] in [Band.NONE, Band.UNKNOWN]:
            task_callback(
                progress="No configured band: SetOperateMode execution not allowed",
                status=TaskStatus.REJECTED,
                result=(ResultCode.NOT_ALLOWED, "SetOperateMode requires a configured band"),
            )
            return
        return self.handler.execute(task_callback, task_abort_event, completed_response_msg)


class SetMaintenanceModeAction(Action):
    """Transition the dish to MAINTENANCE mode."""

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker: CommandTracker,
        dish_manager_cm,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Callable = None,
    ):
        super().__init__(
            logger,
            command_tracker,
            dish_manager_cm,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="Stow",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"operatingmode": DSOperatingMode.STOW},
            timeout_s=180,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )
        spfrx_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPFRX",
            command_name="SetStandbyMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPFRX"],
            awaited_component_state={"operatingmode": SPFRxOperatingMode.STANDBY},
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPFRX"),
        )
        spf_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPF",
            command_name="SetMaintenanceMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPF"],
            awaited_component_state={"operatingmode": SPFOperatingMode.MAINTENANCE},
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPF"),
        )

        self.handler = ActionHandler(
            self.logger,
            "SetMaintenanceMode",
            [ds_command, spfrx_command, spf_command],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"dishmode": DishMode.STOW},
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
        )

    def execute(
        self, task_callback, task_abort_event, completed_response_msg: Optional[str] = None
    ):
        if not self.dish_manager_cm.is_device_ignored("SPFRX"):
            spfrx_cm = self.dish_manager_cm.sub_component_managers["SPFRX"]  # noqa: F841
            try:
                # TODO: Wait for the SPFRx to implement maintenance mode
                task_callback(
                    progress="Nothing done on SPFRx, awaiting implementation on it.",
                )
                # spfrx_cm.write_attribute_value("adminmode", AdminMode.ENGINEERING)
            except tango.DevFailed as err:
                self.logger.exception(
                    "Failed to configure SPFRx adminMode ENGINEERING"
                    " on call to SetMaintenanceMode."
                )
                task_callback(status=TaskStatus.FAILED, exception=err)
                return

        return self.handler.execute(task_callback, task_abort_event, completed_response_msg)


class TrackAction(Action):
    """Transition the dish to Track mode."""

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker: CommandTracker,
        dish_manager_cm,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Callable = None,
    ):
        super().__init__(
            logger,
            command_tracker,
            dish_manager_cm,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="Track",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )

        self.handler = ActionHandler(
            self.logger,
            "Track",
            [ds_command],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
        )
        self.completed_message = (
            "Track command has been executed on DS. "
            "Monitor the achievedTargetLock attribute to determine when the dish is on source."
        )

    def execute(
        self, task_callback, task_abort_event, completed_response_msg: Optional[str] = None
    ):
        return self.handler.execute(
            task_callback, task_abort_event, completed_response_msg=self.completed_message
        )


class TrackStopAction(Action):
    """Stop Tracking."""

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker: CommandTracker,
        dish_manager_cm,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Callable = None,
    ):
        super().__init__(
            logger,
            command_tracker,
            dish_manager_cm,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="TrackStop",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            awaited_component_state={"pointingstate": PointingState.READY},
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )

        self.handler = ActionHandler(
            self.logger,
            "TrackStop",
            [ds_command],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"pointingstate": PointingState.READY},
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
        )

    def execute(
        self, task_callback, task_abort_event, completed_response_msg: Optional[str] = None
    ):
        return self.handler.execute(task_callback, task_abort_event, completed_response_msg)


class ConfigureBandAction(Action):
    """Configure band on DS and SPFRx."""

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker: CommandTracker,
        dish_manager_cm,
        band_number,
        synchronise,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Callable = None,
    ):
        super().__init__(
            logger,
            command_tracker,
            dish_manager_cm,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        self.band_number = band_number
        self.synchronise = synchronise

        self.band_enum = Band[f"B{band_number}"]
        self.indexer_enum = IndexerPosition[f"B{band_number}"]
        self.requested_cmd = f"ConfigureBand{band_number}"

        spfrx_configure_band_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPFRX",
            command_name=self.requested_cmd,
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPFRX"],
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            command_argument=synchronise,
            awaited_component_state={"configuredband": self.band_enum},
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPFRX"),
        )

        ds_set_index_position_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetIndexPosition",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            timeout_s=120,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            command_argument=self.indexer_enum,
            awaited_component_state={"indexerposition": self.indexer_enum},
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )

        self.handler = ActionHandler(
            logger=self.logger,
            name=self.requested_cmd,
            fanned_out_commands=[ds_set_index_position_command, spfrx_configure_band_command],
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"configuredband": self.band_enum},
            action_on_success=action_on_success,
            action_on_failure=action_on_failure,
            waiting_callback=self.waiting_callback,
        )

    def execute(
        self, task_callback, task_abort_event, completed_response_msg: Optional[str] = None
    ):
        if self.dish_manager_cm._component_state["configuredband"] == self.band_enum:
            task_callback(
                progress=f"Already in band {self.band_enum}",
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, f"{self.requested_cmd} completed"),
            )
            return

        self.logger.info(f"{self.requested_cmd} called with synchronise = {self.synchronise}")
        return self.handler.execute(task_callback, task_abort_event, completed_response_msg)


class ConfigureBandActionSequence(Action):
    """Sequence to set the dish power, configure a band, and then go to operate mode."""

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker: CommandTracker,
        dish_manager_cm,
        band_number: int,
        synchronise: bool,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger, command_tracker, dish_manager_cm, waiting_callback=waiting_callback
        )
        self.band_number = band_number
        self.synchronise = synchronise
        self.band_enum = Band[f"B{band_number}"]
        self.indexer_enum = IndexerPosition[f"B{band_number}"]

    def execute(
        self, task_callback, task_abort_event, completed_response_msg: Optional[str] = None
    ):
        """Execute the defined action."""
        current_dish_mode = self.dish_manager_cm._component_state["dishmode"]

        # TODO: Configure pointing model?
        # Configure the DS pointing model for the requested band.

        # Step 2: Operate mode action (final step)
        operate_action = SetOperateModeAction(
            logger=self.logger,
            command_tracker=self.command_tracker,
            dish_manager_cm=self.dish_manager_cm,
            waiting_callback=self.waiting_callback,
        )

        # Step 1: Configure band action
        configure_action = ConfigureBandAction(
            logger=self.logger,
            command_tracker=self.command_tracker,
            dish_manager_cm=self.dish_manager_cm,
            band_number=self.band_number,
            synchronise=self.synchronise,
            action_on_success=operate_action,  # chain operate action
            waiting_callback=self.waiting_callback,
        )

        # Step 0: Pre-action if we need LP -> FP
        if current_dish_mode == DishMode.STANDBY_LP:
            pre_action = SetStandbyFPModeAction(
                logger=self.logger,
                command_tracker=self.command_tracker,
                dish_manager_cm=self.dish_manager_cm,
                action_on_success=configure_action,
                waiting_callback=self.waiting_callback,
            )
            return pre_action.execute(task_callback, task_abort_event, completed_response_msg)

        # If no LP -> FP transition is needed, start directly with ConfigureBand
        return configure_action.execute(task_callback, task_abort_event, completed_response_msg)


class SlewAction(Action):
    """Configure band on DS and SPFRx."""

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker: CommandTracker,
        dish_manager_cm,
        target: list[float],
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Callable = None,
    ):
        super().__init__(
            logger,
            command_tracker,
            dish_manager_cm,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )

        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="Slew",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=self.command_tracker,
            command_argument=target,
            awaited_component_state={"pointingstate": PointingState.SLEW},
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )

        self.handler = ActionHandler(
            logger=self.logger,
            name="Slew",
            fanned_out_commands=[ds_command],
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"pointingstate": PointingState.SLEW},
            action_on_success=action_on_success,
            action_on_failure=action_on_failure,
            waiting_callback=self.waiting_callback,
        )
        self.completed_message = (
            "The DS has been commanded to Slew to [20.0, 30.0]. "
            "Monitor the pointing attributes for the completion status of the task."
        )

    def execute(
        self, task_callback, task_abort_event, completed_response_msg: Optional[str] = None
    ):
        return self.handler.execute(
            task_callback, task_abort_event, completed_response_msg=self.completed_message
        )


class TrackLoadStaticOffAction(Action):
    """Configure band on DS and SPFRx."""

    def __init__(
        self,
        logger: logging.Logger,
        command_tracker: CommandTracker,
        dish_manager_cm,
        off_xel,
        off_el,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Callable = None,
    ):
        super().__init__(
            logger,
            command_tracker,
            dish_manager_cm,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )

        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="TrackLoadStaticOff",
            device_component_manager=dish_manager_cm.sub_component_managers["DS"],
            timeout_s=10,  # TODO: Confirm timeout values
            command_tracker=command_tracker,
            command_argument=[off_xel, off_el],
            awaited_component_state={
                "actstaticoffsetvaluexel": off_xel,
                "actstaticoffsetvalueel": off_el,
            },
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )

        self.handler = ActionHandler(
            logger=self.logger,
            name="TrackLoadStaticOff",
            fanned_out_commands=[ds_command],
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={
                "actstaticoffsetvaluexel": off_xel,
                "actstaticoffsetvalueel": off_el,
            },
            action_on_success=action_on_success,
            action_on_failure=action_on_failure,
            waiting_callback=self.waiting_callback,
        )

    def execute(
        self, task_callback, task_abort_event, completed_response_msg: Optional[str] = None
    ):
        return self.handler.execute(task_callback, task_abort_event, completed_response_msg)
