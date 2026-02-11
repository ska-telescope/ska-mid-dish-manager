"""dscErrorStatuses checks."""

import pytest
import tango


@pytest.mark.unit
@pytest.mark.forked
def test_ds_error_status_aggregation(
    dish_manager_resources,
    event_store_class,
):
    """Test dscErrorStatuses."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    event_store = event_store_class()

    device_proxy.subscribe_event(
        "dscErrorStatuses",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    event_store.wait_for_value("OK")

    # Mimic errors from DSC
    ds_cm._update_component_state(errazimuth=True)
    event_store.wait_for_value("Azimuth Axis error")

    ds_cm._update_component_state(errpwr600vdc=True, errstwpin=True)
    event_store.wait_for_value(
        "Azimuth Axis error; Power error on 600 VDC; StowPin Controller error"
    )
