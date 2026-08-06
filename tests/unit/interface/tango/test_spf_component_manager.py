"""Regression tests for SPF component-manager state updates."""

import pytest

from ska_mid_dish_manager.models.dish_enums import SPFHealthState


@pytest.mark.unit
@pytest.mark.forked
def test_spf_healthstate_none_is_converted_to_unknown(dish_manager_resources):
    """A None SPF health-state event is converted to the UNKNOWN enum value."""
    _, dish_manager_cm = dish_manager_resources
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]

    spf_cm._update_component_state(healthstate=None)

    assert spf_cm._component_state["healthstate"] == SPFHealthState.UNKNOWN
