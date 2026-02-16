import pytest
from tango import DeviceProxy

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import EventStore, remove_subscriptions, setup_subscriptions

TRANSITIONS = [
    ("SetStandbyLPMode", DishMode.STANDBY_LP),
    ("SetStandbyFPMode", DishMode.STANDBY_FP),
    ("SetStowMode", DishMode.STOW),
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
    """Loop dish modes one hundred times to exercise transitions thoroughly."""
    mode_event_store = event_store_class()
    status_event_store = event_store_class()

    subscriptions = {}
    subscriptions.update(
        setup_subscriptions(
            dish_manager_proxy,
            {"dishMode": mode_event_store, "Status": status_event_store},
        )
    )

    try:
        if dish_manager_proxy.dishMode != DishMode.STANDBY_LP:
            mode_event_store.clear_queue()
            dish_manager_proxy.SetStandbyLPMode()
            mode_event_store.wait_for_value(
                DishMode.STANDBY_LP,
                timeout=300,
                proxy=dish_manager_proxy,
            )

        for command_name, expected_mode in TRANSITIONS:
            if dish_manager_proxy.dishMode == expected_mode:
                continue

            mode_event_store.clear_queue()
            getattr(dish_manager_proxy, command_name)()

            mode_event_store.wait_for_value(
                expected_mode,
                timeout=300,
                proxy=dish_manager_proxy,
            )

    except Exception as e:
        events = status_event_store.get_queue_events()
        status_dump = "".join(
            [str(e.attr_value.value) for e in events if e.attr_value is not None]
        )
        pytest.fail(f"Mode cycle iteration failed: {e}. Recent status: {status_dump}")
        raise

    finally:
        remove_subscriptions(subscriptions)
