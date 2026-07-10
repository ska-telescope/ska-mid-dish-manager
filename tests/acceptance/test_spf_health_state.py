import pytest
import tango
from ska_control_model import HealthState

from ska_mid_dish_manager.models.dish_enums import SPFHealthState


@pytest.mark.fixture
def reset_band_health_states_to_normal(
    event_store_class, dish_manager_proxy: tango.DeviceProxy, spf_device_proxy: tango.DeviceProxy
):
    """Ensure that the Dish Manager healthState is returned to OK."""
    yield
    health_state_events = event_store_class()
    dish_manager_proxy.subscribe_event(
        "healthState", tango.EventType.CHANGE_EVENT, health_state_events
    )

    band_health_states = [
        "b1HealthState",
        "b2HealthState",
        "b3HealthState",
        "b4HealthState",
        "b5aHealthState",
        "b5bHealthState",
    ]

    for band in band_health_states:
        spf_device_proxy.write_attribute(band, SPFHealthState.NORMAL)

    health_state_events.wait_for_value(HealthState.OK, timeout=7)


@pytest.mark.acceptance
@pytest.mark.parametrize(
    "attribute_name",
    [
        "b1HealthState",
        "b2HealthState",
        "b3HealthState",
        "b4HealthState",
        "b5aHealthState",
        "b5bHealthState",
    ],
)
def test_spf_per_band_health_state_monitoring(
    dish_manager_proxy: tango.DeviceProxy,
    spf_device_proxy: tango.DeviceProxy,
    event_store_class,
    attribute_name: str,
) -> None:
    """Test that dish manager correctly mirrors the SPF band healthState."""
    spf_health_state_events = event_store_class()
    sub_id = dish_manager_proxy.subscribe_event(
        attribute_name, tango.EventType.CHANGE_EVENT, spf_health_state_events
    )

    possible_band_health_states = [
        SPFHealthState.UNKNOWN,
        SPFHealthState.NORMAL,
        SPFHealthState.DEGRADED,
        SPFHealthState.FAILED,
    ]

    for current_health_state in possible_band_health_states:
        # NOTE: The following attribute write is only possible against the SPF simulator
        spf_device_proxy.write_attribute(attribute_name, current_health_state)

        spf_health_state_events.wait_for_value(current_health_state, timeout=7)

        # Reset SPF back to healthState NORMAL before the next check
        spf_device_proxy.ResetToDefault()

    dish_manager_proxy.unsubscribe_event(sub_id)
