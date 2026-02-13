"""dscErrorStatuses checks."""

import pytest
import tango

from ska_mid_dish_manager.models.constants import DS_ERROR_STATUS_ATTRIBUTES


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

    def clear_errors():
        """Set all error status attributes to False."""
        ds_cm._update_component_state(**{key.lower(): False for key in DS_ERROR_STATUS_ATTRIBUTES})
        event_store.wait_for_value("OK")

    # Test individual errors
    for attr, message in DS_ERROR_STATUS_ATTRIBUTES.items():
        clear_errors()
        # Trigger single error
        ds_cm._update_component_state(**{attr.lower(): True})
        event_store.wait_for_value(message)

    # Test multiple errors
    clear_errors()

    error_subset = list(DS_ERROR_STATUS_ATTRIBUTES.keys())[:3]

    ds_cm._update_component_state(**{key.lower(): True for key in error_subset})
    expected = "; ".join(DS_ERROR_STATUS_ATTRIBUTES[key] for key in error_subset)
    event_store.wait_for_value(expected)

    # Mixed on/off
    clear_errors()

    first, second = error_subset[:2]

    # First True
    ds_cm._update_component_state(**{first.lower(): True})
    event_store.wait_for_value(DS_ERROR_STATUS_ATTRIBUTES[first])

    # Second True
    ds_cm._update_component_state(**{second.lower(): True})
    expected = "; ".join(DS_ERROR_STATUS_ATTRIBUTES[key] for key in error_subset[:2])
    event_store.wait_for_value(expected)

    # First False
    ds_cm._update_component_state(**{first.lower(): False})
    event_store.wait_for_value(DS_ERROR_STATUS_ATTRIBUTES[second])

    # Second False
    ds_cm._update_component_state(**{second.lower(): False})
    event_store.wait_for_value("OK")
