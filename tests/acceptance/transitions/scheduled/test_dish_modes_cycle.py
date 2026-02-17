# This test has the purpose of transitioning through each DishMode on a loop. The idea is to
# continue cycling for as long as possible (up to an hour based on Gitlab CI Runner limitations)
# to limit test the transition capability

import pytest
from tango import DeviceProxy

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import EventStore, remove_subscriptions, setup_subscriptions

# Based on observed behaviour:
# - SetStandbyLPMode is rejected if already in STANDBY_LP
# - OPERATE from STOW was rejected; so return to STANDBY_FP before OPERATE

configure_json = """
    {
        "dish": {
            "receiver_band": "2",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """

TRANSITIONS = [
    ("SetStandbyFPMode", DishMode.STANDBY_FP),
    ("SetStowMode", DishMode.STOW),
    ("SetMaintenanceMode", DishMode.MAINTENANCE),
    ("SetStowMode", DishMode.STOW),
    ("SetStandbyFPMode", DishMode.STANDBY_FP),
    ("ConfigureBand", DishMode.CONFIG, configure_json),
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
        dish_manager_proxy, {"dishMode": mode_event_store, "Status": status_event_store}
    )

    current_step = "initialising"
    try:
        # Ensure known start state without issuing an illegal no-op command
        if dish_manager_proxy.dishMode != DishMode.STANDBY_LP:
            current_step = "SetStandbyLPMode -> STANDBY_LP (initial)"
            mode_event_store.clear_queue()
            dish_manager_proxy.command_inout("SetStandbyLPMode")
            mode_event_store.wait_for_value(
                DishMode.STANDBY_LP, timeout=180, proxy=dish_manager_proxy
            )

        for command_name, expected_mode in TRANSITIONS:
            current_step = f"{command_name} -> {expected_mode.name}"

            # Avoid calling commands that are known to be rejected when already in target mode
            if dish_manager_proxy.dishMode == expected_mode:
                continue

            mode_event_store.clear_queue()
            dish_manager_proxy.command_inout(command_name)

            if expected_mode == DishMode.CONFIG:
                try:
                    mode_event_store.wait_for_value(
                        DishMode.CONFIG, timeout=180, proxy=dish_manager_proxy
                    )
                except RuntimeError:
                    if dish_manager_proxy.dishMode not in (DishMode.CONFIG, DishMode.OPERATE):
                        raise
            else:
                mode_event_store.wait_for_value(
                    expected_mode, timeout=180, proxy=dish_manager_proxy
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

        raise AssertionError(
            f"Dish modes cycle failed at step: {current_step}\n"
            f"Error: {e}\n"
            f"Current dishMode: {current_mode}\n"
            f"Component states: {component_states}\n"
            f"Recent Status: {status_dump}"
        ) from e

    finally:
        remove_subscriptions(subscriptions)
