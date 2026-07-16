"""Unit tests verifying healthState aggregation model."""

import pytest
from ska_control_model import CommunicationStatus, HealthState

from ska_mid_dish_manager.models.dish_enums import SPFHealthState
from ska_mid_dish_manager.models.dish_state_transition import StateTransition


@pytest.fixture(scope="module")
def state_transition():
    """Instance of StateTransition."""
    return StateTransition()


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "ds_comms_state, "
        "spfrx_comms_state, "
        "spf_comms_state, "
        "b5dc_comms_state, "
        "ds_comp_state, "
        "spf_comp_state, "
        "spfrx_comp_state, "
        "b5dc_comp_state, "
        "expected_dish_healthstate"
    ),
    [
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(healthstate=HealthState.OK),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.OK,
        ),
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(
                healthstate=HealthState.DEGRADED, connectionstate=CommunicationStatus.ESTABLISHED
            ),
            dict(healthstate=SPFHealthState.DEGRADED),
            dict(healthstate=HealthState.DEGRADED),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.DEGRADED,
        ),
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.FAILED, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.FAILED),
            dict(healthstate=HealthState.FAILED),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.FAILED,
        ),
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.UNKNOWN),
            dict(healthstate=HealthState.UNKNOWN),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.UNKNOWN,
        ),
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(
                healthstate=HealthState.DEGRADED, connectionstate=CommunicationStatus.ESTABLISHED
            ),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(healthstate=HealthState.OK),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.DEGRADED,
        ),
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.FAILED, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(healthstate=HealthState.OK),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.FAILED,
        ),
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(healthstate=HealthState.OK),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.UNKNOWN,
        ),
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.DEGRADED),
            dict(healthstate=HealthState.OK),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.DEGRADED,
        ),
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.FAILED),
            dict(healthstate=HealthState.OK),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.FAILED,
        ),
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.UNKNOWN),
            dict(healthstate=HealthState.OK),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.UNKNOWN,
        ),
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.DEGRADED),
            dict(healthstate=HealthState.DEGRADED),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.DEGRADED,
        ),
    ],
)
def test_compute_dish_healthstate(
    ds_comms_state,
    spfrx_comms_state,
    spf_comms_state,
    b5dc_comms_state,
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    b5dc_comp_state,
    expected_dish_healthstate,
    state_transition,
):
    actual_dish_healthstate = state_transition.compute_dish_health_state(
        ds_communication_state=ds_comms_state,
        spfrx_communication_state=spfrx_comms_state,
        spf_communication_state=spf_comms_state,
        b5dc_communication_state=b5dc_comms_state,
        ds_component_state=ds_comp_state,
        spfrx_component_state=spfrx_comp_state,
        spf_component_state=spf_comp_state,
        b5dc_component_state=b5dc_comp_state,
    )
    assert expected_dish_healthstate == actual_dish_healthstate


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "ds_comms_state, "
        "spfrx_comms_state, "
        "spf_comms_state, "
        "b5dc_comms_state, "
        "ds_comp_state, "
        "spf_comp_state, "
        "spfrx_comp_state, "
        "b5dc_comp_state, "
        "expected_dish_healthstate"
    ),
    [
        # DS controller expected but disabled
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.DISABLED),
            dict(healthstate=HealthState.OK),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.FAILED,
        ),
        # DS controller connection lost
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.NOT_ESTABLISHED),
            dict(healthstate=HealthState.OK),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.FAILED,
        ),
        # DS Manager expected but disabled
        (
            CommunicationStatus.DISABLED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.DISABLED),
            dict(healthstate=HealthState.OK),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.FAILED,
        ),
        # DS Manager connection lost
        (
            CommunicationStatus.NOT_ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(
                healthstate=HealthState.UNKNOWN,
                connectionstate=CommunicationStatus.NOT_ESTABLISHED,
            ),
            dict(healthstate=HealthState.OK),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.FAILED,
        ),
        # SPFRx expected but disabled
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=HealthState.UNKNOWN),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.FAILED,
        ),
        # SPFRx connection lost
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.NOT_ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=HealthState.UNKNOWN),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.FAILED,
        ),
        # SPF expected but disabled
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(healthstate=HealthState.UNKNOWN),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.FAILED,
        ),
        # SPF connection lost
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.NOT_ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(healthstate=HealthState.UNKNOWN),
            dict(connectionstate=CommunicationStatus.ESTABLISHED),
            HealthState.FAILED,
        ),
        # B5dc Proxy expected but disabled
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(healthstate=HealthState.UNKNOWN),
            dict(connectionstate=CommunicationStatus.DISABLED),
            HealthState.FAILED,
        ),
        # B5dc Proxy connection lost
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.NOT_ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(healthstate=HealthState.UNKNOWN),
            dict(connectionstate=CommunicationStatus.NOT_ESTABLISHED),
            HealthState.FAILED,
        ),
        # B5dc Server expected but disabled
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(healthstate=HealthState.UNKNOWN),
            dict(connectionstate=CommunicationStatus.DISABLED),
            HealthState.FAILED,
        ),
        # B5dc Server connection lost
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            dict(healthstate=HealthState.UNKNOWN),
            dict(connectionstate=CommunicationStatus.NOT_ESTABLISHED),
            HealthState.FAILED,
        ),
    ],
)
def test_compute_dish_healthstate_with_component_disconnections(
    ds_comms_state,
    spfrx_comms_state,
    spf_comms_state,
    b5dc_comms_state,
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    b5dc_comp_state,
    expected_dish_healthstate,
    state_transition,
):
    actual_dish_healthstate = state_transition.compute_dish_health_state(
        ds_communication_state=ds_comms_state,
        spfrx_communication_state=spfrx_comms_state,
        spf_communication_state=spf_comms_state,
        b5dc_communication_state=b5dc_comms_state,
        ds_component_state=ds_comp_state,
        spfrx_component_state=spfrx_comp_state,
        spf_component_state=spf_comp_state,
        b5dc_component_state=b5dc_comp_state,
    )
    assert expected_dish_healthstate == actual_dish_healthstate


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_healthstate"),
    [
        (
            dict(
                healthstate=HealthState.DEGRADED, connectionstate=CommunicationStatus.ESTABLISHED
            ),
            None,
            dict(healthstate=HealthState.OK),
            HealthState.DEGRADED,
        ),
        (
            dict(
                healthstate=HealthState.DEGRADED, connectionstate=CommunicationStatus.ESTABLISHED
            ),
            None,
            dict(healthstate=HealthState.UNKNOWN),
            HealthState.DEGRADED,
        ),
        (
            dict(
                healthstate=HealthState.DEGRADED, connectionstate=CommunicationStatus.ESTABLISHED
            ),
            None,
            dict(healthstate=HealthState.DEGRADED),
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=HealthState.DEGRADED),
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=HealthState.DEGRADED),
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=HealthState.OK),
            HealthState.OK,
        ),
        (
            dict(healthstate=HealthState.FAILED, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=HealthState.OK),
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.FAILED, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=HealthState.FAILED),
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=HealthState.FAILED),
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=HealthState.UNKNOWN),
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=HealthState.OK),
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=HealthState.UNKNOWN),
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=HealthState.UNKNOWN),
            HealthState.UNKNOWN,
        ),
    ],
)
def test_compute_dish_healthstate_ignoring_spf(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_dish_healthstate,
    state_transition,
):
    actual_dish_healthstate = state_transition.compute_dish_health_state(
        ds_communication_state=CommunicationStatus.ESTABLISHED,
        spfrx_communication_state=CommunicationStatus.ESTABLISHED,
        spf_communication_state=CommunicationStatus.DISABLED,
        b5dc_communication_state=CommunicationStatus.DISABLED,
        ds_component_state=ds_comp_state,
        spfrx_component_state=spfrx_comp_state,
        spf_component_state=spf_comp_state,
        b5dc_component_state=None,
    )
    assert expected_dish_healthstate == actual_dish_healthstate


"""
@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "ds_comms_state, "
        "spfrx_comms_state, "
        "spf_comms_state, "
        "ds_comp_state, "
        "spfrx_comp_state, "
        "spf_comp_state, "
        "expected_dish_healthstate"
    ),
    [
        # DS Controller expected but disabled
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.DISABLED),
            dict(healthstate=HealthState.DEGRADED),
            None,
            HealthState.FAILED,
        ),
        # DS Controller disconnected
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.NOT_ESTABLISHED),
            dict(healthstate=HealthState.OK),
            None,
            HealthState.FAILED,
        ),
        # DS Manager expected but disabled
        (
            CommunicationStatus.DISABLED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.DISABLED),
            dict(healthstate=HealthState.OK),
            None,
            HealthState.FAILED,
        ),
        # DS Manager disconnected
        (
            CommunicationStatus.NOT_ESTABLISHED,
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.DISABLED),
            dict(healthstate=HealthState.OK),
            None,
            HealthState.FAILED,
        ),
        # SPFRx expected but disabled
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=HealthState.UNKNOWN),
            None,
            HealthState.FAILED,
        ),
        # SPFRx disconnected
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.NOT_ESTABLISHED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=HealthState.UNKNOWN),
            None,
            HealthState.FAILED,
        ),
    ],
)
def test_compute_dish_healthstate_ignoring_spf_with_component_disconnections(
    ds_comms_state,
    spfrx_comms_state,
    spf_comms_state,
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_dish_healthstate,
    state_transition,
):
    actual_dish_healthstate = state_transition.compute_dish_health_state(
        ds_communication_state=ds_comms_state,
        spfrx_communication_state=spfrx_comms_state,
        spf_communication_state=spf_comms_state,
        ds_component_state=ds_comp_state,
        spfrx_component_state=spfrx_comp_state,
        spf_component_state=spf_comp_state,
    )
    assert expected_dish_healthstate == actual_dish_healthstate


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_healthstate"),
    [
        (
            dict(
                healthstate=HealthState.DEGRADED, connectionstate=CommunicationStatus.ESTABLISHED
            ),
            dict(healthstate=SPFHealthState.NORMAL),
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(
                healthstate=HealthState.DEGRADED, connectionstate=CommunicationStatus.ESTABLISHED
            ),
            dict(healthstate=SPFHealthState.UNKNOWN),
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(
                healthstate=HealthState.DEGRADED, connectionstate=CommunicationStatus.ESTABLISHED
            ),
            dict(healthstate=SPFHealthState.DEGRADED),
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.DEGRADED),
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.DEGRADED),
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            None,
            HealthState.OK,
        ),
        (
            dict(healthstate=HealthState.FAILED, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            None,
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.FAILED, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.FAILED),
            None,
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.FAILED),
            None,
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.UNKNOWN),
            None,
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.NORMAL),
            None,
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.UNKNOWN),
            None,
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.ESTABLISHED),
            dict(healthstate=SPFHealthState.UNKNOWN),
            None,
            HealthState.UNKNOWN,
        ),
    ],
)
def test_compute_dish_healthstate_ignoring_spfrx(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_dish_healthstate,
    state_transition,
):
    actual_dish_healthstate = state_transition.compute_dish_health_state(
        ds_communication_state=CommunicationStatus.ESTABLISHED,
        spfrx_communication_state=CommunicationStatus.DISABLED,
        spf_communication_state=CommunicationStatus.ESTABLISHED,
        ds_component_state=ds_comp_state,
        spfrx_component_state=spfrx_comp_state,
        spf_component_state=spf_comp_state,
    )
    assert expected_dish_healthstate == actual_dish_healthstate


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "ds_comms_state, "
        "spfrx_comms_state, "
        "spf_comms_state, "
        "ds_comp_state, "
        "spfrx_comp_state, "
        "spf_comp_state, "
        "expected_dish_healthstate"
    ),
    [
        # DS Controller expected but disabled
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.DISABLED),
            None,
            dict(healthstate=SPFHealthState.NORMAL),
            HealthState.FAILED,
        ),
        # DS Controller disconnected
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.NOT_ESTABLISHED),
            None,
            dict(healthstate=SPFHealthState.NORMAL),
            HealthState.FAILED,
        ),
        # DS Manager expected but disabled
        (
            CommunicationStatus.DISABLED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.DISABLED),
            None,
            dict(healthstate=SPFHealthState.NORMAL),
            HealthState.FAILED,
        ),
        # DS Manager disconnected
        (
            CommunicationStatus.NOT_ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.ESTABLISHED,
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.DISABLED),
            None,
            dict(healthstate=SPFHealthState.NORMAL),
            HealthState.FAILED,
        ),
        # SPF expected but disabled
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=SPFHealthState.UNKNOWN),
            HealthState.FAILED,
        ),
        # SPF disconnected
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.NOT_ESTABLISHED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            dict(healthstate=SPFHealthState.UNKNOWN),
            HealthState.FAILED,
        ),
    ],
)
def test_compute_dish_healthstate_ignoring_spfrx_with_component_disconnections(
    ds_comms_state,
    spfrx_comms_state,
    spf_comms_state,
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_dish_healthstate,
    state_transition,
):
    actual_dish_healthstate = state_transition.compute_dish_health_state(
        ds_communication_state=ds_comms_state,
        spfrx_communication_state=spfrx_comms_state,
        spf_communication_state=spf_comms_state,
        ds_component_state=ds_comp_state,
        spfrx_component_state=spfrx_comp_state,
        spf_component_state=spf_comp_state,
    )
    assert expected_dish_healthstate == actual_dish_healthstate


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_healthstate"),
    [
        (
            dict(
                healthstate=HealthState.DEGRADED, connectionstate=CommunicationStatus.ESTABLISHED
            ),
            None,
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            None,
            HealthState.OK,
        ),
        (
            dict(healthstate=HealthState.FAILED, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            None,
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.ESTABLISHED),
            None,
            None,
            HealthState.UNKNOWN,
        ),
    ],
)
def test_compute_dish_healthstate_ignoring_spf_and_spfrx(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_dish_healthstate,
    state_transition: StateTransition,
):
    actual_dish_healthstate = state_transition.compute_dish_health_state(
        ds_communication_state=CommunicationStatus.ESTABLISHED,
        spfrx_communication_state=CommunicationStatus.DISABLED,
        spf_communication_state=CommunicationStatus.DISABLED,
        ds_component_state=ds_comp_state,
        spfrx_component_state=spfrx_comp_state,
        spf_component_state=spf_comp_state,
    )
    assert expected_dish_healthstate == actual_dish_healthstate


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "ds_comms_state, "
        "spfrx_comms_state, "
        "spf_comms_state, "
        "ds_comp_state, "
        "spfrx_comp_state, "
        "spf_comp_state, "
        "expected_dish_healthstate"
    ),
    [
        # DS Controller expected but disabled
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.DISABLED),
            None,
            None,
            HealthState.FAILED,
        ),
        # DS Controller disconnected
        (
            CommunicationStatus.ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.OK, connectionstate=CommunicationStatus.NOT_ESTABLISHED),
            None,
            None,
            HealthState.FAILED,
        ),
        # DS Manager expected but disabled
        (
            CommunicationStatus.DISABLED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.DISABLED),
            None,
            None,
            HealthState.FAILED,
        ),
        # DS Manager disconnected
        (
            CommunicationStatus.NOT_ESTABLISHED,
            CommunicationStatus.DISABLED,
            CommunicationStatus.DISABLED,
            dict(healthstate=HealthState.UNKNOWN, connectionstate=CommunicationStatus.DISABLED),
            None,
            None,
            HealthState.FAILED,
        ),
    ],
)
def test_compute_dish_healthstate_ignoring_spf_and_spfrx_with_component_disconnections(
    ds_comms_state,
    spfrx_comms_state,
    spf_comms_state,
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_dish_healthstate,
    state_transition,
):
    actual_dish_healthstate = state_transition.compute_dish_health_state(
        ds_communication_state=ds_comms_state,
        spfrx_communication_state=spfrx_comms_state,
        spf_communication_state=spf_comms_state,
        ds_component_state=ds_comp_state,
        spfrx_component_state=spfrx_comp_state,
        spf_component_state=spf_comp_state,
    )
    assert expected_dish_healthstate == actual_dish_healthstate
"""
