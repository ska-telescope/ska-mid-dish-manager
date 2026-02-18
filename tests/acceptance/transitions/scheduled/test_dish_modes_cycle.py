"""Cycle dish mode transitions for scheduled soak testing."""

import pytest
from tango import DeviceProxy

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import EventStore, remove_subscriptions, setup_subscriptions

STEP_TIMEOUT = 180


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

    subscriptions = setup_subscriptions(
        dish_manager_proxy,
        {
            "dishMode": mode_event_store,
            "Status": status_event_store,
        },
    )

    current_step = "initialising"
    try:
        # The deployed dish starts in STANDBY_LP. If not, force the precondition.
        if dish_manager_proxy.dishMode == DishMode.MAINTENANCE:
            current_step = "SetStowMode -> STOW (exit MAINTENANCE precondition)"
            mode_event_store.clear_queue()
            dish_manager_proxy.SetStowMode()
            _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.STOW)

        if dish_manager_proxy.dishMode != DishMode.STANDBY_LP:
            current_step = "SetStandbyLPMode -> STANDBY_LP (precondition)"
            mode_event_store.clear_queue()
            dish_manager_proxy.SetStandbyLPMode()
            _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.STANDBY_LP)

        current_step = "SetStandbyFPMode -> STANDBY_FP"
        mode_event_store.clear_queue()
        dish_manager_proxy.SetStandbyFPMode()
        _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.STANDBY_FP)

        current_step = "SetStowMode -> STOW"
        mode_event_store.clear_queue()
        dish_manager_proxy.SetStowMode()
        _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.STOW)

        current_step = "SetMaintenanceMode -> MAINTENANCE"
        mode_event_store.clear_queue()
        dish_manager_proxy.SetMaintenanceMode()
        _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.MAINTENANCE)

        current_step = "SetStowMode -> STOW"
        mode_event_store.clear_queue()
        dish_manager_proxy.SetStowMode()
        _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.STOW)

        current_step = "SetStandbyFPMode -> STANDBY_FP"
        mode_event_store.clear_queue()
        dish_manager_proxy.SetStandbyFPMode()
        _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.STANDBY_FP)

        current_step = "ConfigureBand1 -> CONFIG -> OPERATE"
        mode_event_store.clear_queue()
        dish_manager_proxy.ConfigureBand1(True)
        _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.CONFIG)
        _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.OPERATE)

        current_step = "SetStandbyLPMode -> STANDBY_LP"
        mode_event_store.clear_queue()
        dish_manager_proxy.SetStandbyLPMode()
        _wait_for_mode(dish_manager_proxy, mode_event_store, DishMode.STANDBY_LP)

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
