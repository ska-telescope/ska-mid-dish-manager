"""Module containing the fanned out command actions."""

import json
import logging
from typing import Callable, Optional

import tango
from ska_control_model import AdminMode, ResultCode, TaskStatus
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcFrequency

from ska_mid_dish_manager.models.action_handlers import (
    Action,
    ActionHandler,
    SequentialActionHandler,
)
from ska_mid_dish_manager.models.constants import (
    DEFAULT_ACTION_TIMEOUT_S,
    DSC_MIN_POWER_LIMIT_KW,
    OPERATOR_TAG,
)
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
from ska_mid_dish_manager.models.fanned_out_command import (
    DishManagerCMMethod,
    FannedOutSlowCommand,
)
from ska_mid_dish_manager.utils.action_helpers import (
    update_task_status,
)


# -------------------------
# Concrete Actions
# -------------------------
class SetStandbyLPModeAction(Action):
    """Transition the dish to STANDBY_LP mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )

        self.spf_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPF",
            command_name="SetStandbyLPMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPF"],
            command_argument=None,
            awaited_component_state={"operatingmode": SPFOperatingMode.STANDBY_LP},
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPF"),
        )

        self.spfrx_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPFRX",
            command_name="SetStandbyMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPFRX"],
            command_argument=None,
            awaited_component_state={"operatingmode": SPFRxOperatingMode.STANDBY},
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPFRX"),
        )

        self.ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetStandbyMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            command_argument=None,
            awaited_component_state={
                "operatingmode": DSOperatingMode.STANDBY,
                "powerstate": DSPowerState.LOW_POWER,
            },
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
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
            progress_callback=self._progress_callback,
            timeout_s=self.timeout_s,
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        if not self.dish_manager_cm.is_device_ignored("SPFRX"):
            spfrx_cm = self.dish_manager_cm.sub_component_managers["SPFRX"]
            if spfrx_cm._component_state["adminmode"] == AdminMode.ENGINEERING:
                try:
                    spfrx_cm.write_attribute_value("adminmode", AdminMode.ONLINE)
                except tango.DevFailed:
                    self.handler._trigger_failure(
                        task_callback,
                        task_abort_event,
                        "Failed to transition SPFRx from AdminMode ENGINEERING to ONLINE",
                    )
                    return

        return super().execute(task_callback, task_abort_event, completed_response_msg)


class SetStandbyFPModeAction(Action):
    """Transition the dish to STANDBY_FP mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
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
            progress_callback=self._progress_callback,
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
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )

        self._handler = ActionHandler(
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
            progress_callback=self._progress_callback,
            timeout_s=self.timeout_s,
        )


class SetOperateModeAction(Action):
    """Transition the dish to OPERATE mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
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
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPF"),
        )
        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetPointMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"operatingmode": DSOperatingMode.POINT},
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
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
            progress_callback=self._progress_callback,
            timeout_s=self.timeout_s,
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        if self.dish_manager_cm._component_state["configuredband"] in [Band.NONE, Band.UNKNOWN]:
            self.handler._trigger_failure(
                task_callback,
                task_abort_event,
                "No configured band: SetOperateMode execution not allowed",
                task_status=TaskStatus.REJECTED,
                result_code=ResultCode.NOT_ALLOWED,
            )
            return
        return super().execute(task_callback, task_abort_event, completed_response_msg)


class SetMaintenanceModeAction(Action):
    """Transition the dish to MAINTENANCE mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
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
            progress_callback=self._progress_callback,
        )
        spfrx_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPFRX",
            command_name="SetStandbyMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPFRX"],
            awaited_component_state={"operatingmode": SPFRxOperatingMode.STANDBY},
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPFRX"),
        )
        spf_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPF",
            command_name="SetMaintenanceMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPF"],
            awaited_component_state={"operatingmode": SPFOperatingMode.MAINTENANCE},
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPF"),
        )

        self._handler = ActionHandler(
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
            progress_callback=self._progress_callback,
            timeout_s=timeout_s,
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        if not self.dish_manager_cm.is_device_ignored("SPFRX"):
            # TODO: Wait for the SPFRx to implement maintenance mode
            self.logger.debug("Nothing done on SPFRx, awaiting implementation on it.")

        return super().execute(task_callback, task_abort_event, completed_response_msg)


class TrackAction(Action):
    """Transition the dish to Track mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        """:param logger: Logger instance.
        :type logger: logging.Logger
        :param dish_manager_cm: The DishManagerComponentManager instance.
        :type dish_manager_cm: DishManagerComponentManager
        :param action_on_success: Optional Action to execute automatically if this action succeeds.
        :type action_on_success: Optional[Action]
        :param action_on_failure: Optional Action to execute automatically if this action fails.
        :type action_on_failure: Optional[Action]
        :param waiting_callback: Optional callback executed periodically while waiting on commands.
        :type waiting_callback: Optional[Callable]
        """
        super().__init__(
            logger,
            dish_manager_cm,
            0,  # no timeout for the track action since there is no awaited_component_state
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="Track",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
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
            progress_callback=self._progress_callback,
        )
        self.completed_message = (
            "Track command has been executed on DS. "
            "Monitor the achievedTargetLock attribute to determine when the dish is on source."
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        return super().execute(
            task_callback, task_abort_event, completed_response_msg=self.completed_message
        )


class TrackStopAction(Action):
    """Stop Tracking."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="TrackStop",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"pointingstate": PointingState.READY},
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
            self.logger,
            "TrackStop",
            [ds_command],
            component_state=self.dish_manager_cm._component_state,
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
        )
        self.completed_message = "TrackStop Completed on DSC"


def apply_pointing_model(
    band_param_name: str,
    band_name: str,
    task_callback,
    logger: logging.Logger,
    dish_manager_cm,
):
    """Apply pointing model parameters for a given band if they exist and are not all zeros.

    Args:
        band_param_name: The key in component_state for this band.
        band_name: Name/identifier of the band (for logging).
        task_callback: Callback to update task status on failure.
        logger: Logger instance for info/debug/error messages.
        dish_manager_cm: Component manager with component_state and update_pointing_model_params().

    Returns:
        TaskStatus.FAILED and error string if an error occurs, otherwise None.

    """
    try:
        values = dish_manager_cm.component_state[band_param_name]

        if values:
            dish_manager_cm.update_pointing_model_params(band_param_name, values)
            logger.info(
                f"Pointing model for band {band_name} applied successfully", extra=OPERATOR_TAG
            )
        else:
            logger.info(
                f"Skipped applying pointing model for band {band_name} due to invalid params: []",
                extra=OPERATOR_TAG,
            )

    except (tango.DevFailed, ValueError) as err:
        logger.error(
            f"Failed to apply pointing model for band {band_name}: {err}", extra=OPERATOR_TAG
        )
        update_task_status(
            task_callback,
            status=TaskStatus.FAILED,
            result=(ResultCode.FAILED, "Apply pointing model failed"),
        )
        return TaskStatus.FAILED, str(err)


class ConfigureBandAction(Action):
    """Configure band on DS and SPFRx."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        requested_cmd: str,
        band: Optional[Band] = None,
        synchronise: Optional[bool] = None,
        data: Optional[str] = None,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        self.band = band
        self.synchronise = synchronise
        self.data = data
        # If data is provided then band and synchronise are ignored
        assert (self.data is not None) or (
            self.band is not None and self.synchronise is not None
        ), "Either data or both band and synchronise must be provided"

        self.indexer_enum = IndexerPosition(int(band)) if band is not None else None
        self.requested_cmd = requested_cmd
        b5dc_set_frequency_command = None

        if self.data is not None:
            data_json = json.loads(self.data)
            dish_data = data_json.get("dish")
            receiver_band = dish_data.get("receiver_band")
            sub_band = dish_data.get("sub_band")
            # Override band and indexer_enum if json data is provided
            self.band = Band[f"B{receiver_band}"]
            spfrx_awaited_band = self.band
            self.indexer_enum = IndexerPosition[f"B{receiver_band}"]

            if receiver_band == "5b":
                # NOTE according to ADR-102 dish lmc should send B1 to SPFRx if the receiver band
                # is B5b. SPFRx firmware is handling this mapping internally, so no need to send B1
                # to SPFRx from dish manager. Keep an eye on SPFRx firmware releases in case this
                # changes and we need to add mapping in dish manager as well.

                # await for B1 band to be configured on SPFRx if the requested band is B5b
                spfrx_awaited_band = Band.B1

                b5dc_manager = self.dish_manager_cm.sub_component_managers.get("B5DC")
                if not b5dc_manager:
                    self.logger.info(
                        "Monitoring and control not set up for B5DC device,"
                        " skipping frequency configuration.",
                        extra=OPERATOR_TAG,
                    )
                else:
                    b5dc_freq_enum = B5dcFrequency(int(sub_band))
                    b5dc_set_frequency_command = FannedOutSlowCommand(
                        logger=self.logger,
                        device="B5DC",
                        command_name="SetFrequency",
                        device_component_manager=b5dc_manager,
                        command_argument=b5dc_freq_enum,
                        awaited_component_state={
                            "rfcmfrequency": b5dc_freq_enum.frequency_value_ghz()
                        },
                        progress_callback=self._progress_callback,
                        is_device_ignored=self.dish_manager_cm.is_device_ignored("B5DC"),
                    )

            spfrx_configure_band_command = FannedOutSlowCommand(
                logger=self.logger,
                device="SPFRX",
                command_name=self.requested_cmd,
                device_component_manager=self.dish_manager_cm.sub_component_managers["SPFRX"],
                command_argument=self.data,
                awaited_component_state={"configuredband": spfrx_awaited_band},
                progress_callback=self._progress_callback,
                is_device_ignored=self.dish_manager_cm.is_device_ignored("SPFRX"),
            )

        else:
            spfrx_awaited_band = self.band
            spfrx_requested_cmd = self.requested_cmd
            if self.band == Band.B5b:
                # send B1 to SPFRx if the requested band is B5b for the old interface
                spfrx_requested_cmd = "ConfigureBand1"
                # await for band B1 to be configured on SPFRx if the requested band is B5b
                spfrx_awaited_band = Band.B1

            spfrx_configure_band_command = FannedOutSlowCommand(
                logger=self.logger,
                device="SPFRX",
                command_name=spfrx_requested_cmd,
                device_component_manager=self.dish_manager_cm.sub_component_managers["SPFRX"],
                command_argument=self.synchronise,
                awaited_component_state={"configuredband": spfrx_awaited_band},
                progress_callback=self._progress_callback,
                is_device_ignored=self.dish_manager_cm.is_device_ignored("SPFRX"),
            )

        fanned_out_commands = [spfrx_configure_band_command]
        # Only fan out the DS SetIndexPosition command if the band is changing
        if self.dish_manager_cm._component_state["configuredband"] != self.band:
            ds_set_index_position_command = FannedOutSlowCommand(
                logger=self.logger,
                device="DS",
                command_name="SetIndexPosition",
                device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
                command_argument=self.indexer_enum,
                awaited_component_state={"indexerposition": self.indexer_enum},
                progress_callback=self._progress_callback,
            )
            fanned_out_commands.insert(0, ds_set_index_position_command)

        if b5dc_set_frequency_command:
            fanned_out_commands.append(b5dc_set_frequency_command)

        self._handler = ActionHandler(
            logger=self.logger,
            action_name=self.requested_cmd,
            fanned_out_commands=fanned_out_commands,
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"configuredband": self.band},
            action_on_success=action_on_success,
            action_on_failure=action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
            timeout_s=timeout_s,
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        self.logger.info(f"{self.requested_cmd} called")
        return super().execute(task_callback, task_abort_event, completed_response_msg)


class ConfigureBandActionSequence(Action):
    """Sequence to set the dish power, configure a band, and then go to operate mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        requested_cmd: str,
        band: Optional[Band] = None,
        synchronise: Optional[bool] = None,
        data: Optional[str] = None,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        self.band = band
        self.synchronise = synchronise
        self.data = data
        self.indexer_enum = IndexerPosition(int(band)) if band is not None else None
        self.requested_cmd = requested_cmd

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        """Execute the defined action."""
        current_dish_mode = self.dish_manager_cm._component_state["dishmode"]

        # Step 3: Operate mode action (final step)
        operate_action = SetOperateModeAction(
            logger=self.logger,
            dish_manager_cm=self.dish_manager_cm,
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
            timeout_s=self.timeout_s,
        )

        final_action = operate_action if current_dish_mode != DishMode.STOW else None

        # Step 2: Configure band action
        configure_action = ConfigureBandAction(
            logger=self.logger,
            dish_manager_cm=self.dish_manager_cm,
            band=self.band,
            synchronise=self.synchronise,
            data=self.data,
            requested_cmd=self.requested_cmd,
            action_on_success=final_action,  # chain operate action if we aren't in STOW
            waiting_callback=self.waiting_callback,
            timeout_s=self.timeout_s,
        )

        # Step 0 :apply appropriate pointing models before configuring the band
        # Case for Json arg configureband command
        if self.data:
            try:
                data_json = json.loads(self.data)
                dish_data = data_json.get("dish", {})
                band_name = dish_data.get("receiver_band")
                band_param_name = f"band{band_name}pointingmodelparams"

                result = apply_pointing_model(
                    band_param_name, band_name, task_callback, self.logger, self.dish_manager_cm
                )
                if result:
                    return result

            except (json.JSONDecodeError, ValueError) as err:
                self.logger.error(f"Invalid JSON: {err}", extra=OPERATOR_TAG)
                update_task_status(
                    task_callback,
                    status=TaskStatus.FAILED,
                    result=(ResultCode.FAILED, "Invalid JSON in configureband command"),
                )
                return TaskStatus.FAILED, str(err)

        else:
            # Case for Non json arg configureband commands
            if self.band in [Band.B5a, Band.B5b]:
                enum_name = self.band.name
                # Band name becomes '5a' or '5b'
                band_name = enum_name[1:]
            else:
                band_name = str(self.band.value)
            band_param_name = f"band{band_name}pointingmodelparams"

            result = apply_pointing_model(
                band_param_name, band_name, task_callback, self.logger, self.dish_manager_cm
            )
            if result:
                return result

        # Step 1: Pre-action if we need LP -> FP
        if current_dish_mode == DishMode.STANDBY_LP:
            pre_action = SetStandbyFPModeAction(
                logger=self.logger,
                dish_manager_cm=self.dish_manager_cm,
                action_on_success=configure_action,  # chain configure action
                waiting_callback=self.waiting_callback,
                timeout_s=self.timeout_s,
            )
            return pre_action.execute(task_callback, task_abort_event, completed_response_msg)
        # If no LP -> FP transition is needed then start with ConfigureBand
        return configure_action.execute(task_callback, task_abort_event, completed_response_msg)


class SlewAction(Action):
    """Slew the dish to the specified target coordinates."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        target: list[float],
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        """:param logger: Logger instance.
        :type logger: logging.Logger
        :param dish_manager_cm: The DishManagerComponentManager instance.
        :type dish_manager_cm: DishManagerComponentManager
        :target: The target coordinates to slew to.
        :type target: list[float]
        :param action_on_success: Optional Action to execute automatically if this action succeeds.
        :type action_on_success: Optional[Action]
        :param action_on_failure: Optional Action to execute automatically if this action fails.
        :type action_on_failure: Optional[Action]
        :param waiting_callback: Optional callback executed periodically while waiting on commands.
        :type waiting_callback: Optional[Callable]
        """
        super().__init__(
            logger,
            dish_manager_cm,
            0,  # no timeout for the slew action since there is no awaited_component_state
            action_on_success,
            action_on_failure,
            waiting_callback,
        )

        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="Slew",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            command_argument=target,
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
            logger=self.logger,
            action_name="Slew",
            fanned_out_commands=[ds_command],
            component_state=self.dish_manager_cm._component_state,
            action_on_success=action_on_success,
            action_on_failure=action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
        )
        self.completed_message = (
            f"The DS has been commanded to Slew to {target}. "
            "Monitor the pointing attributes for the completion status of the task."
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        return super().execute(
            task_callback, task_abort_event, completed_response_msg=self.completed_message
        )


class TrackLoadStaticOffAction(Action):
    """TrackLoadStaticOff action."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        off_xel,
        off_el,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )

        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="TrackLoadStaticOff",
            device_component_manager=dish_manager_cm.sub_component_managers["DS"],
            command_argument=[off_xel, off_el],
            awaited_component_state={
                "actstaticoffsetvaluexel": off_xel,
                "actstaticoffsetvalueel": off_el,
            },
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
            logger=self.logger,
            action_name="TrackLoadStaticOff",
            fanned_out_commands=[ds_command],
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={
                "actstaticoffsetvaluexel": off_xel,
                "actstaticoffsetvalueel": off_el,
            },
            action_on_success=action_on_success,
            action_on_failure=action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
            timeout_s=timeout_s,
        )


class EndScanAction(Action):
    """Reset the scan ID."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        """:param logger: Logger instance.
        :type logger: logging.Logger
        :param dish_manager_cm: The DishManagerComponentManager instance.
        :type dish_manager_cm: DishManagerComponentManager
        :param action_on_success: Optional Action to execute automatically if this action succeeds.
        :type action_on_success: Optional[Action]
        :param action_on_failure: Optional Action to execute automatically if this action fails.
        :type action_on_failure: Optional[Action]
        :param waiting_callback: Optional callback executed periodically while waiting on commands.
        :type waiting_callback: Optional[Callable]
        """
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        self.completed_message = "The scan ID has been cleared."

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        if not task_abort_event.is_set():
            self.logger.info("Resetting the Scan ID")
            self.dish_manager_cm._update_component_state(scanid="")
            if self.action_on_success:
                self.action_on_success.execute(task_callback, task_abort_event)


class ResetTrackTableAction(Action):
    """Reset the DSC track table."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        """:param logger: Logger instance.
        :type logger: logging.Logger
        :param dish_manager_cm: The DishManagerComponentManager instance.
        :type dish_manager_cm: DishManagerComponentManager
        :param action_on_success: Optional Action to execute automatically if this action succeeds.
        :type action_on_success: Optional[Action]
        :param action_on_failure: Optional Action to execute automatically if this action fails.
        :type action_on_failure: Optional[Action]
        :param waiting_callback: Optional callback executed periodically while waiting on commands.
        :type waiting_callback: Optional[Callable]
        """
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        self.completed_message = "The DSC track table has been reset."

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        if not task_abort_event.is_set():
            self.logger.info("Clearing the track table.")
            result_code, msg = self.dish_manager_cm.reset_track_table()
            if result_code == ResultCode.FAILED:
                self.logger.error(f"abort-sequence: ResetTrackTable failed: {msg}")
                update_task_status(
                    task_callback,
                    status=TaskStatus.FAILED,
                    result=(ResultCode.FAILED, f"Resetting the track table failed: {msg}"),
                )
            else:
                self.logger.info(f"Clearing the track table OK {result_code}, {msg}")
            if self.action_on_success:
                self.action_on_success.execute(task_callback, task_abort_event)


class AbortScanSequence(Action):
    """Sequence to stop dish movement.

    Reset the track table and then clear the scan_id
    """

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        self.completed_message = "Abort sequence completed."

        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="TrackStop",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"pointingstate": PointingState.READY},
            progress_callback=self._progress_callback,
        )

        reset_track_table = DishManagerCMMethod(
            logger,
            dish_manager_cm.reset_track_table,
            self.dish_manager_cm._component_state,
        )

        abort_lrc_command = DishManagerCMMethod(
            logger,
            dish_manager_cm.abort_tasks,
            self.dish_manager_cm._component_state,
        )

        self._handler = SequentialActionHandler(
            logger=self.logger,
            action_name="Abort LRC Tasks",
            fanned_out_commands=[abort_lrc_command, reset_track_table, ds_command],
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={},
            action_on_success=action_on_success,
            action_on_failure=action_on_failure,
            waiting_callback=waiting_callback,
            progress_callback=self._progress_callback,
            timeout_s=timeout_s,
        )
