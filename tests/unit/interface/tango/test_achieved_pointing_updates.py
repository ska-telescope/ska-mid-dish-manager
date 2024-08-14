"""Test that the DishManager achievedPointing attribute is in sync
with the DSManager achievedPointing attribute."""

import pytest
import tango


# pylint: disable=missing-function-docstring, protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_achieved_pointing_in_sync_with_dish_structure_pointing(
    dish_manager_resources,
    event_store_class,
):
    """
    Test achieved pointing is in sync with dish structure pointing
    """
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    main_event_store = event_store_class()
    az_event_store = event_store_class()
    el_event_store = event_store_class()

    device_proxy.subscribe_event(
        "achievedPointing",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    test_coordinates = (5000.0, 234.0, 45.0)

    assert list(device_proxy.achievedPointing) != list(test_coordinates)

    ds_cm._update_component_state(achievedpointing=test_coordinates)

    main_event_store.wait_for_value(test_coordinates)

    assert list(device_proxy.achievedPointing) == list(test_coordinates)
