"""Cycle dish mode transitions for scheduled soak testing."""

import json
import time
from dataclasses import dataclass
from typing import Any

import pytest
from ska_control_model import ResultCode
from tango import DeviceProxy

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import EventStore, remove_subscriptions, setup_subscriptions

STEP_TIMEOUT = 180
LRC_TIMEOUT = 360
MIN_ACTION_TIMEOUT_SECONDS = 300.0
RETRY_DELAY_SECONDS = 5
SUBSCRIPTION_SETUP_TIMEOUT = 120
SUBSCRIPTION_RETRY_DELAY_SECONDS = 2
COMMANDS_WITHOUT_LRC_RESULT = {"SetStowMode"}


@dataclass(frozen=True)
class TransitionStep:
    """Represents a single command step in the dish mode cycle."""

    command_name: str
    command_args: tuple[Any, ...]
    expected_modes: tuple[DishMode, ...]
    retries: int = 0
    wait_modes_before_lrc: bool = False


class TestDishModesCycle:
    """Scheduled soak test for dish mode transitions."""

    TRANSITION_SEQUENCE = (
        TransitionStep("SetStandbyFPMode", (), (DishMode.STANDBY_FP,)),
        TransitionStep("SetStowMode", (), (DishMode.STOW,)),
        TransitionStep("SetMaintenanceMode", (), (DishMode.MAINTENANCE,)),
        TransitionStep("SetStowMode", (), (DishMode.STOW,)),
        TransitionStep("SetStandbyFPMode", (), (DishMode.STANDBY_FP,), retries=1),
        TransitionStep(
            "ConfigureBand1",
            (True,),
            (DishMode.CONFIG, DishMode.OPERATE),
            wait_modes_before_lrc=True,
        ),
        TransitionStep("SetStandbyLPMode", (), (DishMode.STANDBY_LP,)),
    )

    @staticmethod
    def _extract_command_response(command_response: Any, command_name: str) -> tuple[int, str]:
        """Extract immediate result code and response value from Tango command response."""
        if not isinstance(command_response, (list, tuple)) or len(command_response) != 2:
            raise RuntimeError(f"Could not parse {command_name} response: {command_response}")

        code_container, value_container = command_response
        if isinstance(code_container, (str, bytes)) or isinstance(value_container, (str, bytes)):
            raise RuntimeError(f"Could not parse {command_name} response: {command_response}")

        try:
            return int(code_container[0]), str(value_container[0])
        except Exception as err:  # noqa: BLE001
            raise RuntimeError(
                f"Could not parse {command_name} response: {command_response}"
            ) from err

    @staticmethod
    def _assert_initial_command_response_ok(result_code: int, command_name: str) -> None:
        """Validate the command's immediate return code."""
        try:
            result_code_enum = ResultCode(result_code)
        except ValueError as err:
            raise RuntimeError(
                f"{command_name} returned unknown result code [{result_code}]"
            ) from err

        failure_codes = {ResultCode.FAILED, ResultCode.REJECTED}
        for maybe_failure in ("NOT_ALLOWED", "ABORTED"):
            maybe_value = getattr(ResultCode, maybe_failure, None)
            if maybe_value is not None:
                failure_codes.add(maybe_value)

        if result_code_enum in failure_codes:
            raise RuntimeError(f"{command_name} was not accepted (result={result_code_enum.name})")

    @staticmethod
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
                "Failed to parse LRC result for "
                f"{command_name} (id={command_id}): {result_payload}"
            ) from err

        return int(result_code), str(result_message)

    @staticmethod
    def _wait_for_mode(
        dish_manager_proxy: DeviceProxy,
        mode_event_store: EventStore,
        expected_mode: DishMode,
    ) -> None:
        """Wait until dish mode reaches the expected mode."""
        mode_event_store.wait_for_value(
            expected_mode,
            timeout=STEP_TIMEOUT,
            proxy=dish_manager_proxy,
        )
        assert dish_manager_proxy.dishMode == expected_mode

    def _run_step(
        self,
        dish_manager_proxy: DeviceProxy,
        mode_event_store: EventStore,
        result_event_store: EventStore,
        step: TransitionStep,
    ) -> None:
        """Execute a single transition step, with retries if configured."""
        last_error: Exception | None = None
        for attempt in range(step.retries + 1):
            try:
                mode_event_store.clear_queue()
                result_event_store.clear_queue()

                command_fn = getattr(dish_manager_proxy, step.command_name)
                command_response = command_fn(*step.command_args)
                result_code, command_value = self._extract_command_response(
                    command_response, step.command_name
                )
                self._assert_initial_command_response_ok(result_code, step.command_name)

                if step.wait_modes_before_lrc:
                    for expected_mode in step.expected_modes:
                        if dish_manager_proxy.dishMode == expected_mode:
                            continue
                        self._wait_for_mode(dish_manager_proxy, mode_event_store, expected_mode)

                if step.command_name not in COMMANDS_WITHOUT_LRC_RESULT:
                    command_id = command_value
                    lrc_code, lrc_message = self._wait_for_lrc_result(
                        result_event_store,
                        command_id,
                        step.command_name,
                    )
                    if lrc_code != 0:
                        raise RuntimeError(
                            f"{step.command_name} failed (id={command_id}, code={lrc_code}):"
                            f" {lrc_message}"
                        )

                if not step.wait_modes_before_lrc:
                    for expected_mode in step.expected_modes:
                        if dish_manager_proxy.dishMode == expected_mode:
                            continue
                        self._wait_for_mode(dish_manager_proxy, mode_event_store, expected_mode)
                return
            except Exception as err:  # noqa: BLE001
                last_error = err
                if attempt == step.retries:
                    break
                time.sleep(RETRY_DELAY_SECONDS)

        expected_path = " -> ".join(mode.name for mode in step.expected_modes)
        raise RuntimeError(
            f"{step.command_name} did not reach {expected_path} "
            f"after {step.retries + 1} attempt(s)"
        ) from last_error

    @staticmethod
    def _setup_subscriptions_with_retry(
        dish_manager_proxy: DeviceProxy,
        mode_event_store: EventStore,
        status_event_store: EventStore,
        result_event_store: EventStore,
    ) -> dict:
        """Retry event subscriptions while the Tango event channel becomes available."""
        deadline = time.time() + SUBSCRIPTION_SETUP_TIMEOUT
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                _ = dish_manager_proxy.dishMode
                return setup_subscriptions(
                    dish_manager_proxy,
                    {
                        "dishMode": mode_event_store,
                        "Status": status_event_store,
                        "longRunningCommandResult": result_event_store,
                    },
                )
            except Exception as err:  # noqa: BLE001
                last_error = err
                time.sleep(SUBSCRIPTION_RETRY_DELAY_SECONDS)

        raise RuntimeError(
            "Failed to subscribe to dish manager events before timeout"
        ) from last_error

    @pytest.mark.acceptance
    @pytest.mark.dish_modes
    @pytest.mark.repeat(6)
    def test_mode_transitions_cycle(
        self,
        event_store_class: EventStore,
        dish_manager_proxy: DeviceProxy,
    ) -> None:
        """Transition through the scheduled dish mode sequence."""
        mode_event_store = event_store_class()
        status_event_store = event_store_class()
        result_event_store = event_store_class()
        subscriptions = {}

        current_step = "initialising"
        original_action_timeout = None
        try:
            subscriptions = self._setup_subscriptions_with_retry(
                dish_manager_proxy,
                mode_event_store,
                status_event_store,
                result_event_store,
            )

            original_action_timeout = float(dish_manager_proxy.actionTimeoutSeconds)
            if original_action_timeout < MIN_ACTION_TIMEOUT_SECONDS:
                dish_manager_proxy.actionTimeoutSeconds = MIN_ACTION_TIMEOUT_SECONDS

            # Deployed dish starts in STANDBY_LP; normalize state when needed.
            if dish_manager_proxy.dishMode == DishMode.MAINTENANCE:
                current_step = "SetStowMode -> STOW (exit MAINTENANCE precondition)"
                self._run_step(
                    dish_manager_proxy,
                    mode_event_store,
                    result_event_store,
                    TransitionStep("SetStowMode", (), (DishMode.STOW,)),
                )

            if dish_manager_proxy.dishMode != DishMode.STANDBY_LP:
                current_step = "SetStandbyLPMode -> STANDBY_LP (precondition)"
                self._run_step(
                    dish_manager_proxy,
                    mode_event_store,
                    result_event_store,
                    TransitionStep("SetStandbyLPMode", (), (DishMode.STANDBY_LP,)),
                )

            for step in self.TRANSITION_SEQUENCE:
                current_step = f"{step.command_name} -> " + " -> ".join(
                    mode.name for mode in step.expected_modes
                )
                self._run_step(
                    dish_manager_proxy,
                    mode_event_store,
                    result_event_store,
                    step,
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
