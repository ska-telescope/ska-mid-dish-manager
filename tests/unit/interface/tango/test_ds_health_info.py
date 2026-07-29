"""Test that DishManager's healthInfo forwards DS's real healthInfo reasons."""

import pytest
import tango
from ska_control_model import HealthState

from ska_mid_dish_manager.models.dish_enums import SPFHealthState


def _make_baseline_healthy(dish_manager_cm) -> None:
    """Put every sub-device's healthState to a nominal value so healthInfo starts empty."""
    sub_component_managers = dish_manager_cm.sub_component_managers
    sub_component_managers["SPF"]._update_component_state(healthstate=SPFHealthState.NORMAL)
    sub_component_managers["SPFRX"]._update_component_state(healthstate=HealthState.OK)
    sub_component_managers["DS"]._update_component_state(healthstate=HealthState.OK, healthinfo=[])


@pytest.mark.unit
@pytest.mark.forked
def test_healthinfo_reports_ds_reasons(dish_manager_resources, event_store_class):
    """HealthInfo reports DS's real reasons instead of the generic placeholder."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    ds_fqdn = ds_cm._tango_device_fqdn
    _make_baseline_healthy(dish_manager_cm)

    event_store = event_store_class()
    device_proxy.subscribe_event("healthInfo", tango.EventType.CHANGE_EVENT, event_store)
    event_store.wait_for_value(())

    ds_cm._update_component_state(
        healthstate=HealthState.FAILED,
        healthinfo=["DSC error status: General error"],
    )
    event_store.wait_for_value((f'{ds_fqdn}: ["DSC error status: General error"]',))

    ds_cm._update_component_state(healthstate=HealthState.OK, healthinfo=[])
    event_store.wait_for_value(())


@pytest.mark.unit
@pytest.mark.forked
def test_healthinfo_reports_ds_reasons_without_healthstate_change(
    dish_manager_resources, event_store_class
):
    """HealthInfo is kept in sync when DS's healthInfo changes without healthState changing.

    DS's healthState only reflects mode/application state, so DSC errors/safety issues or a
    lost connection can update DS's healthInfo independently of healthState.
    """
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    ds_fqdn = ds_cm._tango_device_fqdn
    _make_baseline_healthy(dish_manager_cm)

    event_store = event_store_class()
    device_proxy.subscribe_event("healthInfo", tango.EventType.CHANGE_EVENT, event_store)
    event_store.wait_for_value(())

    ds_cm._update_component_state(healthinfo=["DSC safety status: E-stop pressed Pedestal"])
    event_store.wait_for_value((f'{ds_fqdn}: ["DSC safety status: E-stop pressed Pedestal"]',))


@pytest.mark.unit
@pytest.mark.forked
def test_healthinfo_reports_multiple_ds_reasons(dish_manager_resources, event_store_class):
    """HealthInfo reports every DS reason as its own entry when DS has multiple at once."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    ds_fqdn = ds_cm._tango_device_fqdn
    _make_baseline_healthy(dish_manager_cm)

    event_store = event_store_class()
    device_proxy.subscribe_event("healthInfo", tango.EventType.CHANGE_EVENT, event_store)
    event_store.wait_for_value(())

    ds_cm._update_component_state(
        healthstate=HealthState.FAILED,
        healthinfo=[
            "Connection to DSC is not established: NOT_ESTABLISHED",
            "General failure: DSC is not in the expected mode and application state for "
            "normal operation",
            "DSC error status: General error; Tracking Controller error",
        ],
    )
    event_store.wait_for_value(
        (
            f'{ds_fqdn}: ["Connection to DSC is not established: NOT_ESTABLISHED"]',
            f'{ds_fqdn}: ["General failure: DSC is not in the expected mode and application '
            'state for normal operation"]',
            f'{ds_fqdn}: ["DSC error status: General error; Tracking Controller error"]',
        )
    )


@pytest.mark.unit
@pytest.mark.forked
def test_healthinfo_falls_back_to_placeholder_when_ds_reports_no_reasons(
    dish_manager_resources, event_store_class
):
    """HealthInfo falls back to the generic placeholder if DS hasn't reported specific reasons."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    ds_fqdn = ds_cm._tango_device_fqdn
    _make_baseline_healthy(dish_manager_cm)

    event_store = event_store_class()
    device_proxy.subscribe_event("healthInfo", tango.EventType.CHANGE_EVENT, event_store)
    event_store.wait_for_value(())

    ds_cm._update_component_state(healthstate=HealthState.FAILED, healthinfo=[])
    event_store.wait_for_value((f'{ds_fqdn}: ["Unknown failure reason"]',))
