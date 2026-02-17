# A test that cycles through the dish mode transitions up to one hundred times
import itertools
import json

import pytest
from tango import DeviceProxy

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import EventStore, remove_subscriptions, setup_subscriptions

WAIT_SECONDS = 180

# Band rotation across pytest-repeat iterations (within the same job / process)
BANDS = ["1", "2", "3", "4", "5"]
_BAND_ITER = itertools.cycle(BANDS)

CONFIG_TEMPLATE = {
    "dish": {
        "receiver_band": None,  # injected each repeat
        "spfrx_processing_parameters": [
            {"dishes": ["all"], "sync_pps": True}
        ],
    }
}


def _configureband_json_next() -> str:
    """Return ConfigureBand DevString JSON with receiver_band rotated each test repeat."""
    band = next(_BAND_ITER)
    payload = {
        **CONFIG_TEMPLATE,
        "dish": {**CONFIG_TEMPLATE["dish"], "receiver_band": band},
    }
    return json.dumps(payload)


# TRANSITIONS stays the source of truth.
# 2-tuple: (command, expected_mode) => no args
# 3-tuple: (command, expected_mode, arg_factory) => arg_factory() called per repeat
TRANSITIONS = [
    ("SetStandbyFPMode", DishMode.STANDBY_FP),
    ("SetStowMode", DishMode.STOW),
    ("SetMaintenanceMode", DishMode.MAINTENANCE),
    ("SetStowMode", DishMode.STOW),
    ("SetStandbyFPMode", DishMode.STANDBY_FP),
    ("ConfigureBand", DishMode.CONFIG, _configureband_json_next),
    ("SetOperateMode", DishMode.OPERATE),
    ("SetStandbyLPMode", DishMode.STANDBY_LP),
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
        # Ensure start state once per repeat (no illegal no-op)
        if dish_manager_proxy.dishMode != DishMode.STANDBY_LP:
            current_step = "SetStandbyLPMode -> STANDBY_LP (initial)"
            mode_event_store.clear_queue()
            dish_manager_proxy.command_inout("SetStandbyLPMode")
            mode_event_store.wait_for_value(
                DishMode.STANDBY_LP, timeout=WAIT_SECONDS, proxy=dish_manager_proxy
            )

        for item in TRANSITIONS:
            if len(item) == 2:
                command_name, expected_mode = item
                arg = None
            else:
                command_name, expected_mode, arg_factory = item
                arg = arg_factory()  # IMPORTANT: called each repeat

            # If this is ConfigureBand, include band in step name for debugging
            if command_name == "ConfigureBand" and arg is not None:
                try:
                    band = json.loads(arg)["dish"]["receiver_band"]
                except Exception:
                    band = "<?>"
                current_step = f"{command_name}(receiver_band={band}) -> {expected_mode.name}"
            else:
                current_step = f"{command_name} -> {expected_mode.name}"

            # Avoid rejected no-ops
            if dish_manager_proxy.dishMode == expected_mode:
                continue

            mode_event_store.clear_queue()

            if arg is None:
                dish_manager_proxy.command_inout(command_name)
            else:
                dish_manager_proxy.command_inout(command_name, arg)

            # CONFIG can be transient; accept CONFIG or already-OPERATE
            if expected_mode == DishMode.CONFIG:
                try:
                    mode_event_store.wait_for_value(
                        DishMode.CONFIG, timeout=WAIT_SECONDS, proxy=dish_manager_proxy
                    )
                except RuntimeError:
                    if dish_manager_proxy.dishMode not in (DishMode.CONFIG, DishMode.OPERATE):
                        raise
            else:
                mode_event_store.wait_for_value(
                    expected_mode, timeout=WAIT_SECONDS, proxy=dish_manager_proxy
                )

    except Exception as e:
        # Keep failures actionable
        try:
            current_mode = dish_manager_proxy.dishMode
        except Exception:
            current_mode = "<failed to read DishMode>"

        try:
            component_states = dish_manager_proxy.GetComponentStates()
        except Exception:
            component_states = "<failed to GetComponentStates()>"

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
