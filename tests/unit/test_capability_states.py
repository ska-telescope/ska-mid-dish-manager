"""CapabilityState checks"""
import pytest
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    CapabilityStates,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    SPFCapabilityStates,
    SPFRxCapabilityStates,
)
from ska_mid_dish_manager.models.dish_mode_model import DishModeModel


# pylint: disable=redefined-outer-name
@pytest.fixture(scope="module")
def dish_mode_model():
    """Instance of DishModeModel"""
    return DishModeModel()


@pytest.mark.unit
@pytest.mark.forked
def test_capability_states_available():
    """Test capability states"""
    with DeviceTestContext(DishManager) as proxy:
        attributes = proxy.get_attribute_list()
        for capability in ("b1", "b2", "b3", "b4", "b5a", "b5b"):
            state_name = f"{capability}CapabilityState"
            assert state_name in attributes
            assert getattr(proxy, state_name, None) == CapabilityStates.UNKNOWN


@pytest.mark.unit
@pytest.mark.forked
def test_capability_states_settings():
    """Test capability state settings"""
    with DeviceTestContext(DishManager) as proxy:
        for capability in ("b1", "b2", "b3", "b4", "b5a", "b5b"):
            state_name = f"{capability}CapabilityState"
            setattr(proxy, state_name, CapabilityStates.OPERATE_FULL)
            assert (
                getattr(proxy, state_name, None)
                == CapabilityStates.OPERATE_FULL
            )


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_unavailable(dish_mode_model):
    """Test the capabilityState rules"""

    ds_component_state = {}
    ds_component_state["operatingmode"] = DSOperatingMode.STARTUP
    ds_component_state["indexerposition"] = None
    spf_component_state = {}
    spf_component_state["b5bcapabilitystate"] = SPFCapabilityStates.UNAVAILABLE
    spfrx_component_state = {}
    spfrx_component_state[
        "b5bcapabilitystate"
    ] = SPFRxCapabilityStates.UNAVAILABLE
    dish_manager_component_state = {}
    dish_manager_component_state["dishmode"] = None

    assert (
        dish_mode_model.compute_capability_state(
            "b5b",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.UNAVAILABLE
    )


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_standby(dish_mode_model):
    """Test the capabilityState rules"""

    ds_component_state = {}
    ds_component_state["operatingmode"] = None
    ds_component_state["indexerposition"] = None
    spf_component_state = {}
    spf_component_state["b5acapabilitystate"] = SPFCapabilityStates.STANDBY
    spfrx_component_state = {}
    spfrx_component_state["b5acapabilitystate"] = SPFRxCapabilityStates.STANDBY
    dish_manager_component_state = {}
    dish_manager_component_state["dishmode"] = DishMode.STANDBY_LP

    assert (
        dish_mode_model.compute_capability_state(
            "b5a",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.STANDBY
    )


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_configuring(dish_mode_model):
    """Test the capabilityState rules"""

    ds_component_state = {}
    ds_component_state["operatingmode"] = None
    ds_component_state["indexerposition"] = None
    spf_component_state = {}
    spf_component_state[
        "b4capabilitystate"
    ] = SPFCapabilityStates.OPERATE_DEGRADED
    spfrx_component_state = {}
    spfrx_component_state[
        "b4capabilitystate"
    ] = SPFRxCapabilityStates.CONFIGURE
    dish_manager_component_state = {}
    dish_manager_component_state["dishmode"] = DishMode.CONFIG

    assert (
        dish_mode_model.compute_capability_state(
            "b4",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.CONFIGURING
    )


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_degraded(dish_mode_model):
    """Test the capabilityState rules"""

    ds_component_state = {}
    ds_component_state["indexerposition"] = IndexerPosition.MOVING
    ds_component_state["operatingmode"] = None
    spf_component_state = {}
    spf_component_state["b3capabilitystate"] = SPFCapabilityStates.STANDBY
    spfrx_component_state = {}
    spfrx_component_state["b3capabilitystate"] = SPFRxCapabilityStates.OPERATE
    dish_manager_component_state = {}
    dish_manager_component_state["dishmode"] = DishMode.STOW

    assert (
        dish_mode_model.compute_capability_state(
            "b3",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.OPERATE_DEGRADED
    )


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_operate(dish_mode_model):
    """Test the capabilityState rules"""

    ds_component_state = {}
    ds_component_state["indexerposition"] = IndexerPosition.MOVING
    ds_component_state["operatingmode"] = None
    spf_component_state = {}
    spf_component_state["b1capabilitystate"] = SPFCapabilityStates.OPERATE_FULL
    spfrx_component_state = {}
    spfrx_component_state["b1capabilitystate"] = SPFRxCapabilityStates.OPERATE
    dish_manager_component_state = {}
    dish_manager_component_state["dishmode"] = DishMode.STOW

    assert (
        dish_mode_model.compute_capability_state(
            "b1",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.OPERATE_FULL
    )


@pytest.mark.unit
@pytest.mark.forked
def test_capability_state_rule_unknown(dish_mode_model):
    """Test the capabilityState rules"""

    ds_component_state = {}
    ds_component_state["operatingmode"] = None
    ds_component_state["indexerposition"] = None
    spf_component_state = {}
    spf_component_state["b2capabilitystate"] = None
    spfrx_component_state = {}
    spfrx_component_state["b2capabilitystate"] = None
    dish_manager_component_state = {}
    dish_manager_component_state["dishmode"] = None

    assert (
        dish_mode_model.compute_capability_state(
            "b2",
            ds_component_state,
            spfrx_component_state,
            spf_component_state,
            dish_manager_component_state,
        )
        == CapabilityStates.UNKNOWN
    )
