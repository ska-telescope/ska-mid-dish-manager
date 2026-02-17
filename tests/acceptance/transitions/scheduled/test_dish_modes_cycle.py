# This test transitions through DishMode values in a loop to stress transitions.

import json

import pytest
from tango import DeviceProxy

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import EventStore, remove_subscriptions, setup_subscriptions


def _make_configure_json(band: str) -> str:
    """Return a DevString JSON payload for ConfigureBand."""
    payload = {
        "dish": {
            "receiver_band": str(band),
            "spfrx_processing_parameters": [{"dishes": ["all"], "sync_pps": True}],
        }
    }
    # Compact + deterministic; Tango expects a DevString
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


# Keep the transition order your senior specified.
# ConfigureBand needs a DevString argument, so we model it as (cmd, expected_mode, arg_factory)
TRANSITIONS = [
    ("SetStandbyFPMode", DishMode.STANDBY_FP, None),
    ("SetStowMode", DishMode.STOW, None),
    ("SetMaintenanceMode", DishMode.MAINTENANCE, None),
    ("SetStowMode", DishMode.STOW, None),
    ("SetStandbyFPMode", DishMode.STANDBY_FP, None),
    ("ConfigureBand", DishMode.CONFIG, _make_configure_json),
    ("SetOperateMode", DishMode.OPERATE, None),
    ("SetStandbyLPMode", DishMode.STANDBY_LP, None),
]


@pytest.mark.acceptance
@pytest.mark.dish_modes
# @pytest.mark.repeat(100)
def test_mode_transitions_cycle(
    event_store_class: EventStore,
    dish_manager_proxy: DeviceProxy,
) -> None:
    mode_event_store = event_store_class()
    status_event_store = event_store_class()

    subscriptions = setup_subscriptions(
        dish_manager_proxy,
        {"dishMode": mode_event_store, "Status": status_event_store},
    )

    current_step = "initialising"
    try:
        # Ensure known start state without issuing an illegal no-op command
        if dish_manager_proxy.dishMode != DishMode.STANDBY_LP:
            current_step = "SetStandbyLPMode -> STANDBY_LP (initial)"
            mode_event_store.clear_queue()
            dish_manager_proxy.command_inout("SetStandbyLPMode")
            mode_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=180, proxy=dish_manager_proxy)

        # Pick a band per pytest-repeat iteration (covers multiple repeats deterministically)
        # 1..5 cycle (adjust if you want 5a/5b etc., but those are typically different commands)
        repeat_i = getattr(request.node, "execution_count", 0) if "request" in globals() else 0  # safe fallback
        band = str((repeat_i % 5) + 1)

        for command_name, expected_mode, arg_factory in TRANSITIONS:
            current_step = f"{command_name} -> {expected_mode.name}"

            # Avoid calling commands that are known to be rejected when already in target mode
            if dish_manager_proxy.dishMode == expected_mode:
                continue

            mode_event_store.clear_queue()

            if arg_factory is None:
                dish_manager_proxy.command_inout(command_name)
            else:
                dish_manager_proxy.command_inout(command_name, arg_factory(band))

            mode_event_store.wait_for_value(expected_mode, timeout=180, proxy=dish_manager_proxy)

    except Exception as e:
        # Keep rich debug for CI failures
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

        raise AssertionError(
            f"Dish modes cycle failed at step: {current_step}\n"
            f"Error: {e}\n"
            f"Current dishMode: {current_mode}\n"
            f"Component states: {component_states}\n"
            f"Recent Status: {status_dump}"
        ) from e

    finally:
        remove_subscriptions(subscriptions)
