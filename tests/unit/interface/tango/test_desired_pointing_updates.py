"""
Test that the DishManager desiredPointing attribute is
in sync with the DSManager desiredPointing attribute.
"""

import pytest
import tango


# pylint: disable=missing-function-docstring, protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_desired_pointing_in_sync_with_dish_structure_pointing(
    dish_manager_resources,
    event_store_class,
):
    """
    Test desired pointing is in sync with dish structure pointing
    """
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    event_store = event_store_class()

    device_proxy.subscribe_event(
        "desiredPointingAz",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    device_proxy.subscribe_event(
        "desiredPointingEl",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    test_coordinates_az = (5000.0, 234.0)
    test_coordinates_el = (5000.0, 45.0)
    assert list(device_proxy.desiredPointingAz) != list(test_coordinates_az)
    assert list(device_proxy.desiredPointingEl) != list(test_coordinates_el)

    ds_cm._update_component_state(desiredpointingaz=test_coordinates_az)
    ds_cm._update_component_state(desiredpointingel=test_coordinates_el)

    event_store.wait_for_value(test_coordinates_az)
    event_store.wait_for_value(test_coordinates_el)

    assert list(device_proxy.desiredPointingAz) == list(test_coordinates_az)
    assert list(device_proxy.desiredPointingEl) == list(test_coordinates_el)
