import pytest
from tango import DeviceProxy

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import EventStore, remove_subscriptions, setup_subscriptions

# Based on observed behaviour:
# - SetStandbyLPMode is rejected if already in STANDBY_LP
# - OPERATE from STOW was rejected; so return to STANDBY_FP before OPERATE
TRANSITIONS = [
    ("SetStandbyFPMode", DishMode.STANDBY_FP),
    ("SetStowMode", DishMode.STOW),
    ("SetStandbyFPMode", DishMode.STANDBY_FP),
    ("SetOperateMode", DishMode.OPERATE),
    ("SetStandbyLPMode", DishMode.STANDBY_LP),
]


@pytest.mark.acceptance
@pytest.mark.dish_modes
@pytest.mark.timeout(600)
def test_mode_transitions_cycle(
    event_store_class: EventStore,
    dish_manager_proxy: DeviceProxy,
) -> None:
    mode_event_store = event_store_class()
    status_event_store = event_store_class()

    subscriptions = {}
    subscriptions.update(
        setup_subscriptions(
            dish_manager_proxy,
            {"dishMode": mode_event_store, "Status": status_event_store},
        )
    )

    current_step = "initialising"
    try:
        # Ensure known start state without issuing an illegal no-op command
        if dish_manager_proxy.dishMode != DishMode.STANDBY_LP:
            current_step = "SetStandbyLPMode -> STANDBY_LP (initial)"
            mode_event_store.clear_queue()
            dish_manager_proxy.SetStandbyLPMode()
            mode_event_store.wait_for_value(
                DishMode.STANDBY_LP, timeout=180, proxy=dish_manager_proxy
            )

        for command_name, expected_mode in TRANSITIONS:
            current_step = f"{command_name} -> {expected_mode}"

            # Avoid calling commands that are known to be rejected when already in target mode
            if dish_manager_proxy.dishMode == expected_mode:
                continue

            mode_event_store.clear_queue()
            getattr(dish_manager_proxy, command_name)()

            mode_event_store.wait_for_value(expected_mode, timeout=180, proxy=dish_manager_proxy)

    except Exception as e:
        # Direct reads (events may be missing/late)
        try:
            current_mode = dish_manager_proxy.dishMode
        except Exception:
            current_mode = "<failed to read dishMode>"

        try:
            component_states = dish_manager_proxy.GetComponentStates()
        except Exception:
            component_states = "<failed to GetComponentStates()>"

        events = status_event_store.get_queue_events()
        status_dump = "".join(
            [str(ev.attr_value.value) for ev in events if ev.attr_value is not None]
        )

        raise AssertionError(
            f"Mode cycle iteration failed at step: {current_step}\n"
            f"Error: {e}\n"
            f"Current dishMode: {current_mode}\n"
            f"Component states: {component_states}\n"
            f"Recent Status: {status_dump}"
        ) from e

    finally:
        remove_subscriptions(subscriptions)
