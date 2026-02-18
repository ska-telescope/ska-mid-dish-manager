"""Cycle dish mode transitions for scheduled soak testing."""

import json
import time
from typing import Any, Callable

import pytest
from ska_control_model import ResultCode
from tango import DeviceProxy

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import EventStore, remove_subscriptions, setup_subscriptions

STEP_TIMEOUT = 180
LRC_TIMEOUT = 360
MIN_ACTION_TIMEOUT_SECONDS = 300.0
RETRY_DELAY_SECONDS = 5
COMMANDS_WITHOUT_LRC_RESULT = {"SetStowMode"}


def _extract_command_response(command_response: Any, command_name: str) -> tuple[int, str]:
    """Extract immediate result code and response value from Tango command response."""
    if (
        isinstance(command_response, (list, tuple))
        and len(command_response) == 2
        and isinstance(command_response[0], (list, tuple))
        and len(command_response[0]) > 0
        and isinstance(command_response[1], (list, tuple))
        and len(command_response[1]) > 0
    ):
        return int(command_response[0][0]), str(command_response[1][0])

    raise RuntimeError(
        f"Could not parse {command_name} response: {command_response}"
    )


def _assert_initial_command_response_ok(result_code: int, command_name: str) -> None:
    """Validate the command's immediate return code."""
    try:
        result_code_enum = ResultCode(result_code)
    except ValueError as err:
        raise RuntimeError(
            f"{command_name} returned unknown result code [{result_code}]"
        ) from err

    failure_codes = {
        ResultCode.FAILED,
        ResultCode.REJECTED,
    }
    for maybe_failure in ("NOT_ALLOWED", "ABORTED"):
        maybe_value = getattr(ResultCode, maybe_failure, None)
        if maybe_value is not None:
            failure_codes.add(maybe_value)

    if result_code_enum in failure_codes:
        raise RuntimeError(f"{command_name} was not accepted (result={result_code_enum.name})")


def _wait_for_lrc_result(
    result_event_store: EventStore,
    command_id: str,
    command_name: str,
) -> tuple[int, str]:
    """Wait for and parse final long running command result for a command id."""
    events = result_event_store.wait_for_command_id(command_id, timeout=LRC_TIMEOUT)
    result_payload = None
    for event in reversed(events):
        if event.attr_value is None:
            continue
        if event.attr_value.name != "longrunningcommandresult":
            continue
        event_value = event.attr_value.value
        if not isinstance(event_value, tuple) or len(event_value) != 2:
            continue
        if str(event_value[0]) != command_id:
            continue
        result_payload = str(event_value[1])
        break

    if result_payload is None:
        raise RuntimeError(f"No LRC result payload found for {command_name} (id={command_id})")

    try:
        result_code, result_message = json.loads(result_payload)
    except json.JSONDecodeError as err:
        raise RuntimeError(
            f"Failed to parse LRC result for {command_name} (id={command_id}): {result_payload}"
        ) from err

    return int(result_code), str(result_message)


def _wait_for_mode(
    dish_manager_proxy: DeviceProxy,
    mode_event_store: EventStore,
    expected_mode: DishMode,
) -> None:
    mode_event_store.wait_for_value(
        expected_mode,
        timeout=STEP_TIMEOUT,
        proxy=dish_manager_proxy,
    )
    assert dish_manager_proxy.dishMode == expected_mode


def _run_lrc_and_expect_success(
    result_event_store: EventStore,
    command_call: Callable[[], Any],
    command_name: str,
) -> None:
    """Execute an LRC command and require successful completion."""
    result_event_store.clear_queue()
    command_response = command_call()
    result_code, command_value = _extract_command_response(command_response, command_name)
    _assert_initial_command_response_ok(result_code, command_name)

    if command_name in COMMANDS_WITHOUT_LRC_RESULT:
        return

    command_id = command_value
    result_code, result_message = _wait_for_lrc_result(
        result_event_store, command_id, command_name
    )
    if result_code != 0:
        raise RuntimeError(
            f"{command_name} failed (id={command_id}, code={result_code}): {result_message}"
        )


def _run_mode_transition(
    dish_manager_proxy: DeviceProxy,
    mode_event_store: EventStore,
    result_event_store: EventStore,
    command_call: Callable[[], Any],
    command_name: str,
    expected_mode: DishMode,
    retries: int = 0,
) -> None:
    """Run a command, require LRC success, then require target dish mode."""
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            mode_event_store.clear_queue()
            _run_lrc_and_expect_success(result_event_store, command_call, command_name)
            if dish_manager_proxy.dishMode == expected_mode:
                return
            _wait_for_mode(dish_manager_proxy, mode_event_store, expected_mode)
            return
        except Exception as err:  # noqa: BLE001
            last_error = err
            if attempt == retries:
                break
            time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"{command_name} did not reach {expected_mode.name} after {retries + 1} attempt(s)"
    ) from last_error


@pytest.mark.acceptance
@pytest.mark.dish_modes
def test_mode_transitions_cycle(
    event_store_class: EventStore,
    dish_manager_proxy: DeviceProxy,
) -> None:
    """Transition through the scheduled dish mode sequence.

    Required sequence:
    STANDBY_LP -> STANDBY_FP -> STOW -> MAINTENANCE -> STOW ->
    STANDBY_FP -> CONFIG -> OPERATE -> STANDBY_LP
    """
    mode_event_store = event_store_class()
    status_event_store = event_store_class()
    result_event_store = event_store_class()

    subscriptions = setup_subscriptions(
        dish_manager_proxy,
        {
            "dishMode": mode_event_store,
            "Status": status_event_store,
            "longRunningCommandResult": result_event_store,
        },
    )

    current_step = "initialising"
    original_action_timeout = None
    try:
        original_action_timeout = float(dish_manager_proxy.actionTimeoutSeconds)
        if original_action_timeout < MIN_ACTION_TIMEOUT_SECONDS:
            dish_manager_proxy.actionTimeoutSeconds = MIN_ACTION_TIMEOUT_SECONDS

        # The deployed dish starts in STANDBY_LP. If not, force the precondition.
        if dish_manager_proxy.dishMode == DishMode.MAINTENANCE:
            current_step = "SetStowMode -> STOW (exit MAINTENANCE precondition)"
            _run_mode_transition(
                dish_manager_proxy,
                mode_event_store,
                result_event_store,
                dish_manager_proxy.SetStowMode,
                "SetStowMode",
                DishMode.STOW,
            )

        if dish_manager_proxy.dishMode != DishMode.STANDBY_LP:
            current_step = "SetStandbyLPMode -> STANDBY_LP (precondition)"
            _run_mode_transition(
                dish_manager_proxy,
                mode_event_store,
                result_event_store,
                dish_manager_proxy.SetStandbyLPMode,
                "SetStandbyLPMode",
                DishMode.STANDBY_LP,
            )

        current_step = "SetStandbyFPMode -> STANDBY_FP"
        _run_mode_transition(
            dish_manager_proxy,
            mode_event_store,
            result_event_store,
            dish_manager_proxy.SetStandbyFPMode,
            "SetStandbyFPMode",
            DishMode.STANDBY_FP,
        )

        current_step = "SetStowMode -> STOW"
        _run_mode_transition(
            dish_manager_proxy,
            mode_event_store,
            result_event_store,
            dish_manager_proxy.SetStowMode,
            "SetStowMode",
            DishMode.STOW,
        )

        current_step = "SetMaintenanceMode -> MAINTENANCE"
        _run_mode_transition(
            dish_manager_proxy,
            mode_event_store,
            result_event_store,
            dish_manager_proxy.SetMaintenanceMode,
            "SetMaintenanceMode",
            DishMode.MAINTENANCE,
        )

        current_step = "SetStowMode -> STOW"
        _run_mode_transition(
            dish_manager_proxy,
            mode_event_store,
            result_event_store,
            dish_manager_proxy.SetStowMode,
            "SetStowMode",
            DishMode.STOW,
        )

        current_step = "SetStandbyFPMode -> STANDBY_FP"
        _run_mode_transition(
            dish_manager_proxy,
            mode_event_store,
            result_event_store,
            dish_manager_proxy.SetStandbyFPMode,
            "SetStandbyFPMode",
            DishMode.STANDBY_FP,
            retries=1,
        )

        current_step = "ConfigureBand1 -> CONFIG -> OPERATE"
        mode_event_store.clear_queue()
        result_event_store.clear_queue()
        configure_response = dish_manager_proxy.ConfigureBand1(True)
        _, configure_id = _extract_command_response(configure_response, "ConfigureBand1")
        _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.CONFIG)
        _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.OPERATE)
        configure_code, configure_message = _wait_for_lrc_result(
            result_event_store,
            configure_id,
            "ConfigureBand1",
        )
        if configure_code != 0:
            raise RuntimeError(
                f"ConfigureBand1 failed (id={configure_id}, code={configure_code}): "
                f"{configure_message}"
            )

        current_step = "SetStandbyLPMode -> STANDBY_LP"
        _run_mode_transition(
            dish_manager_proxy,
            mode_event_store,
            result_event_store,
            dish_manager_proxy.SetStandbyLPMode,
            "SetStandbyLPMode",
            DishMode.STANDBY_LP,
        )

    except Exception as e:
        try:
            current_mode = dish_manager_proxy.dishMode
        except Exception:
            current_mode = "<failed to read DishMode>"

        try:
            component_states = dish_manager_proxy.GetComponentStates()
        except Exception:
            component_states = "<failed to get component states>"

        events = status_event_store.get_queue_events()
        status_dump = "".join(
            [str(ev.attr_value.value) for ev in events if ev.attr_value is not None]
        )
        lrc_dump = result_event_store.get_queue_values(timeout=0)

        raise AssertionError(
            f"Dish modes cycle failed at step: {current_step}\n"
            f"Error: {e}\n"
            f"Current dishMode: {current_mode}\n"
            f"Component states: {component_states}\n"
            f"Recent Status: {status_dump}\n"
            f"Recent LRC results: {lrc_dump}"
        ) from e
    finally:
        if original_action_timeout is not None:
            try:
                dish_manager_proxy.actionTimeoutSeconds = original_action_timeout
            except Exception:
                pass
        remove_subscriptions(subscriptions)
