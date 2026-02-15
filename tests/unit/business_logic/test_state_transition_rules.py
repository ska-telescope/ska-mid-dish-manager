"""Unit tests verifying model against dishMode transitions."""

import pytest
from ska_control_model import AdminMode, HealthState
from ska_mid_dish_utils.models.dish_enums import (
    Band,
    CapabilityStates,
    DishMode,
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    PowerState,
    SPFBandInFocus,
    SPFCapabilityStates,
    SPFOperatingMode,
    SPFPowerState,
    SPFRxCapabilityStates,
    SPFRxOperatingMode,
)

from ska_mid_dish_manager.models.dish_state_transition import StateTransition


@pytest.fixture(scope="module")
def state_transition():
    """Instance of StateTransition."""
    return StateTransition()


# Order DS, SPF, SPFRX
@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_mode"),
    [
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.STARTUP),
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STARTUP,
        ),
        (
            dict(
                indexerposition=IndexerPosition.MOVING,
                powerstate=DSPowerState.LOW_POWER,
                operatingmode=DSOperatingMode.STANDBY,
            ),
            dict(operatingmode=SPFOperatingMode.STANDBY_LP),
            dict(operatingmode=SPFRxOperatingMode.OPERATE),
            DishMode.CONFIG,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, powerstate=DSPowerState.LOW_POWER),
            dict(operatingmode=SPFOperatingMode.STANDBY_LP),
            dict(operatingmode=SPFRxOperatingMode.CONFIGURE),
            DishMode.STOW,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.MOVING,
                powerstate=DSPowerState.LOW_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.CONFIG,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.STANDBY_LP),
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STANDBY_LP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.FULL_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STANDBY_FP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.FULL_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STANDBY_FP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.POINT,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.FULL_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            dict(operatingmode=SPFRxOperatingMode.OPERATE),
            DishMode.OPERATE,
        ),
        # Any other random combo goes to UNKNOWN
        (
            dict(
                operatingmode=DSOperatingMode.UNKNOWN,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.ERROR),
            dict(operatingmode=SPFRxOperatingMode.UNKNOWN),
            DishMode.UNKNOWN,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STOW,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.ERROR),
            dict(operatingmode=SPFRxOperatingMode.UNKNOWN),
            DishMode.STOW,
        ),
    ],
)
def test_compute_dish_mode(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_dish_mode,
    state_transition,
):
    actual_dish_mode = state_transition.compute_dish_mode(
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_dish_mode == actual_dish_mode


# Order DS, SPF, SPFRX
@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_mode"),
    [
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.MOVING,
                powerstate=DSPowerState.LOW_POWER,
            ),
            None,
            dict(operatingmode=SPFRxOperatingMode.CONFIGURE),
            DishMode.CONFIG,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.POINT,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.FULL_POWER,
            ),
            None,
            dict(operatingmode=SPFRxOperatingMode.OPERATE),
            DishMode.OPERATE,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.FULL_POWER,
            ),
            None,
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STANDBY_FP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.FULL_POWER,
            ),
            None,
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STANDBY_FP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STOW,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            None,
            dict(operatingmode=SPFRxOperatingMode.UNKNOWN, adminmode=AdminMode.ONLINE),
            DishMode.STOW,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STARTUP,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            None,
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STARTUP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.UNKNOWN,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            None,
            dict(operatingmode=SPFRxOperatingMode.UNKNOWN),
            DishMode.UNKNOWN,
        ),
    ],
)
def test_compute_dish_mode_ignoring_spf(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_dish_mode,
    state_transition,
):
    actual_dish_mode = state_transition.compute_dish_mode(
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_dish_mode == actual_dish_mode


# Order DS, SPF, SPFRX
@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_mode"),
    [
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.MOVING,
                powerstate=DSPowerState.LOW_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            None,
            DishMode.CONFIG,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.POINT,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.FULL_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            None,
            DishMode.OPERATE,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.FULL_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            None,
            DishMode.STANDBY_FP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.STANDBY_LP),
            None,
            DishMode.STANDBY_LP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STOW,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.ERROR),
            None,
            DishMode.STOW,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            dict(operatingmode=SPFOperatingMode.STARTUP),
            None,
            DishMode.STARTUP,
        ),
    ],
)
def test_compute_dish_mode_ignoring_spfrx(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_dish_mode,
    state_transition,
):
    actual_dish_mode = state_transition.compute_dish_mode(
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_dish_mode == actual_dish_mode


# Order DS, SPF, SPFRX
@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_mode"),
    [
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.MOVING,
                powerstate=DSPowerState.LOW_POWER,
            ),
            None,
            None,
            DishMode.CONFIG,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.POINT,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            None,
            None,
            DishMode.OPERATE,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.FULL_POWER,
            ),
            None,
            None,
            DishMode.STANDBY_FP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STOW,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            None,
            None,
            DishMode.STOW,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STARTUP,
                indexerposition=IndexerPosition.UNKNOWN,
                powerstate=DSPowerState.LOW_POWER,
            ),
            None,
            None,
            DishMode.STARTUP,
        ),
    ],
)
def test_compute_dish_mode_ignoring_spf_and_spfrx(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_dish_mode,
    state_transition,
):
    actual_dish_mode = state_transition.compute_dish_mode(
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_dish_mode == actual_dish_mode


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_healthstate"),
    [
        (
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.OK),
            HealthState.OK,
        ),
        (
            dict(healthstate=HealthState.DEGRADED),
            dict(healthstate=HealthState.DEGRADED),
            dict(healthstate=HealthState.DEGRADED),
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.FAILED),
            dict(healthstate=HealthState.FAILED),
            dict(healthstate=HealthState.FAILED),
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN),
            dict(healthstate=HealthState.UNKNOWN),
            dict(healthstate=HealthState.UNKNOWN),
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.DEGRADED),
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.OK),
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.FAILED),
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.OK),
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN),
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.OK),
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.DEGRADED),
            dict(healthstate=HealthState.OK),
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.FAILED),
            dict(healthstate=HealthState.OK),
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.UNKNOWN),
            dict(healthstate=HealthState.OK),
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.DEGRADED),
            dict(healthstate=HealthState.DEGRADED),
            HealthState.DEGRADED,
        ),
    ],
)
def test_compute_dish_healthstate(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_dish_healthstate,
    state_transition,
):
    actual_dish_healthstate = state_transition.compute_dish_health_state(
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_dish_healthstate == actual_dish_healthstate


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_healthstate"),
    [
        (
            dict(healthstate=HealthState.DEGRADED),
            None,
            dict(healthstate=HealthState.OK),
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.DEGRADED),
            None,
            dict(healthstate=HealthState.UNKNOWN),
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.DEGRADED),
            None,
            dict(healthstate=HealthState.DEGRADED),
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.OK),
            None,
            dict(healthstate=HealthState.DEGRADED),
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN),
            None,
            dict(healthstate=HealthState.DEGRADED),
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.OK),
            None,
            dict(healthstate=HealthState.OK),
            HealthState.OK,
        ),
        (
            dict(healthstate=HealthState.FAILED),
            None,
            dict(healthstate=HealthState.OK),
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.FAILED),
            None,
            dict(healthstate=HealthState.FAILED),
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.OK),
            None,
            dict(healthstate=HealthState.FAILED),
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN),
            None,
            dict(healthstate=HealthState.UNKNOWN),
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN),
            None,
            dict(healthstate=HealthState.OK),
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.OK),
            None,
            dict(healthstate=HealthState.UNKNOWN),
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN),
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
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_dish_healthstate == actual_dish_healthstate


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_healthstate"),
    [
        (
            dict(healthstate=HealthState.DEGRADED),
            dict(healthstate=HealthState.OK),
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.DEGRADED),
            dict(healthstate=HealthState.UNKNOWN),
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.DEGRADED),
            dict(healthstate=HealthState.DEGRADED),
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.DEGRADED),
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN),
            dict(healthstate=HealthState.DEGRADED),
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.OK),
            None,
            HealthState.OK,
        ),
        (
            dict(healthstate=HealthState.FAILED),
            dict(healthstate=HealthState.OK),
            None,
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.FAILED),
            dict(healthstate=HealthState.FAILED),
            None,
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.FAILED),
            None,
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN),
            dict(healthstate=HealthState.UNKNOWN),
            None,
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN),
            dict(healthstate=HealthState.OK),
            None,
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.OK),
            dict(healthstate=HealthState.UNKNOWN),
            None,
            HealthState.UNKNOWN,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN),
            dict(healthstate=HealthState.UNKNOWN),
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
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_dish_healthstate == actual_dish_healthstate


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_healthstate"),
    [
        (
            dict(healthstate=HealthState.DEGRADED),
            None,
            None,
            HealthState.DEGRADED,
        ),
        (
            dict(healthstate=HealthState.OK),
            None,
            None,
            HealthState.OK,
        ),
        (
            dict(healthstate=HealthState.FAILED),
            None,
            None,
            HealthState.FAILED,
        ),
        (
            dict(healthstate=HealthState.UNKNOWN),
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
    state_transition,
):
    actual_dish_healthstate = state_transition.compute_dish_health_state(
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_dish_healthstate == actual_dish_healthstate


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_band_number"),
    [
        (
            dict(something="nothing"),
            dict(anything="something"),
            dict(configuredband=Band.NONE),
            Band.NONE,
        ),
        (
            dict(indexerposition=IndexerPosition.B1),
            dict(bandinfocus=SPFBandInFocus.B1),
            dict(configuredband=Band.B1),
            Band.B1,
        ),
        (
            dict(indexerposition=IndexerPosition.B2),
            dict(bandinfocus=SPFBandInFocus.B2),
            dict(configuredband=Band.B2),
            Band.B2,
        ),
        (
            dict(indexerposition=IndexerPosition.B3),
            dict(bandinfocus=SPFBandInFocus.B3),
            dict(configuredband=Band.B3),
            Band.B3,
        ),
        (
            dict(indexerposition=IndexerPosition.B4),
            dict(bandinfocus=SPFBandInFocus.B4),
            dict(configuredband=Band.B4),
            Band.B4,
        ),
        (
            dict(indexerposition=IndexerPosition.B5a),
            dict(bandinfocus=SPFBandInFocus.B5a),
            dict(configuredband=Band.B5a),
            Band.B5a,
        ),
        (
            dict(indexerposition=IndexerPosition.B5b),
            dict(bandinfocus=SPFBandInFocus.B5b),
            dict(configuredband=Band.B5b),
            Band.B5b,
        ),
        (
            dict(indexerposition=IndexerPosition.B1),
            dict(bandinfocus=SPFBandInFocus.B2),
            dict(configuredband=Band.B3),
            Band.UNKNOWN,
        ),
        (
            dict(indexerposition=IndexerPosition.B1),
            dict(bandinfocus=SPFBandInFocus.B5a),
            dict(configuredband=Band.B5a),
            Band.UNKNOWN,
        ),
    ],
)
def test_compute_configured_band(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_band_number,
    state_transition,
):
    actual_band_number = state_transition.compute_configured_band(
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_band_number == actual_band_number


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_band_number"),
    [
        (
            dict(something="nothing"),
            None,
            dict(configuredband=Band.NONE),
            Band.NONE,
        ),
        (
            dict(indexerposition=IndexerPosition.B1),
            None,
            dict(configuredband=Band.B1),
            Band.B1,
        ),
        (
            dict(indexerposition=IndexerPosition.B2),
            None,
            dict(configuredband=Band.B2),
            Band.B2,
        ),
        (
            dict(indexerposition=IndexerPosition.B3),
            None,
            dict(configuredband=Band.B3),
            Band.B3,
        ),
        (
            dict(indexerposition=IndexerPosition.B4),
            None,
            dict(configuredband=Band.B4),
            Band.B4,
        ),
        (
            dict(indexerposition=IndexerPosition.B5a),
            None,
            dict(configuredband=Band.B5a),
            Band.B5a,
        ),
        (
            dict(indexerposition=IndexerPosition.B5b),
            None,
            dict(configuredband=Band.B5b),
            Band.B5b,
        ),
        (
            dict(indexerposition=IndexerPosition.B1),
            None,
            dict(configuredband=Band.B3),
            Band.UNKNOWN,
        ),
        (
            dict(indexerposition=IndexerPosition.B1),
            None,
            dict(configuredband=Band.B5a),
            Band.UNKNOWN,
        ),
    ],
)
def test_compute_configured_band_ignoring_spf(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_band_number,
    state_transition,
):
    actual_band_number = state_transition.compute_configured_band(
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_band_number == actual_band_number


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_band_number"),
    [
        (
            dict(indexerposition=IndexerPosition.B1),
            dict(bandinfocus=SPFBandInFocus.B1),
            None,
            Band.B1,
        ),
        (
            dict(indexerposition=IndexerPosition.B2),
            dict(bandinfocus=SPFBandInFocus.B2),
            None,
            Band.B2,
        ),
        (
            dict(indexerposition=IndexerPosition.B3),
            dict(bandinfocus=SPFBandInFocus.B3),
            None,
            Band.B3,
        ),
        (
            dict(indexerposition=IndexerPosition.B4),
            dict(bandinfocus=SPFBandInFocus.B4),
            None,
            Band.B4,
        ),
        (
            dict(indexerposition=IndexerPosition.B5a),
            dict(bandinfocus=SPFBandInFocus.B5a),
            None,
            Band.B5a,
        ),
        (
            dict(indexerposition=IndexerPosition.B5b),
            dict(bandinfocus=SPFBandInFocus.B5b),
            None,
            Band.B5b,
        ),
        (
            dict(indexerposition=IndexerPosition.B1),
            dict(bandinfocus=SPFBandInFocus.B2),
            None,
            Band.UNKNOWN,
        ),
        (
            dict(indexerposition=IndexerPosition.B1),
            dict(bandinfocus=SPFBandInFocus.B5a),
            None,
            Band.UNKNOWN,
        ),
    ],
)
def test_compute_configured_band_ignoring_spfrx(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_band_number,
    state_transition,
):
    actual_band_number = state_transition.compute_configured_band(
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_band_number == actual_band_number


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_band_number"),
    [
        (
            dict(indexerposition=IndexerPosition.B1),
            None,
            None,
            Band.B1,
        ),
        (
            dict(indexerposition=IndexerPosition.B2),
            None,
            None,
            Band.B2,
        ),
        (
            dict(indexerposition=IndexerPosition.B3),
            None,
            None,
            Band.B3,
        ),
        (
            dict(indexerposition=IndexerPosition.B4),
            None,
            None,
            Band.B4,
        ),
        (
            dict(indexerposition=IndexerPosition.B5a),
            None,
            None,
            Band.B5a,
        ),
        (
            dict(indexerposition=IndexerPosition.B5b),
            None,
            None,
            Band.B5b,
        ),
        (
            dict(indexerposition=IndexerPosition.UNKNOWN),
            None,
            None,
            Band.UNKNOWN,
        ),
    ],
)
def test_compute_configured_band_ignoring_spf_and_spfrx(
    ds_comp_state,
    spf_comp_state,
    spfrx_comp_state,
    expected_band_number,
    state_transition,
):
    actual_band_number = state_transition.compute_configured_band(
        ds_comp_state, spfrx_comp_state, spf_comp_state
    )
    assert expected_band_number == actual_band_number


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spfrx_comp_state, expected_band_number"),
    [
        (
            dict(indexerposition=IndexerPosition.B1),
            dict(configuredband=Band.B1),
            SPFBandInFocus.B1,
        ),
        (
            dict(indexerposition=IndexerPosition.B2),
            dict(configuredband=Band.B2),
            SPFBandInFocus.B2,
        ),
        (
            dict(indexerposition=IndexerPosition.B3),
            dict(configuredband=Band.B3),
            SPFBandInFocus.B3,
        ),
        (
            dict(indexerposition=IndexerPosition.B4),
            dict(configuredband=Band.B4),
            SPFBandInFocus.B4,
        ),
        (
            dict(indexerposition=IndexerPosition.B5a),
            dict(configuredband=Band.B5a),
            SPFBandInFocus.B5a,
        ),
        (
            dict(indexerposition=IndexerPosition.B5b),
            dict(configuredband=Band.B5b),
            SPFBandInFocus.B5b,
        ),
        (
            dict(indexerposition=IndexerPosition.B1),
            dict(configuredband=Band.B3),
            SPFBandInFocus.UNKNOWN,
        ),
        (
            dict(indexerposition=IndexerPosition.B1),
            dict(configuredband=Band.B5a),
            SPFBandInFocus.UNKNOWN,
        ),
    ],
)
def test_compute_spf_band_in_focus(
    ds_comp_state,
    spfrx_comp_state,
    expected_band_number,
    state_transition,
):
    actual_band_number = state_transition.compute_spf_band_in_focus(
        ds_comp_state,
        spfrx_comp_state,
    )
    assert expected_band_number == actual_band_number


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spfrx_comp_state, expected_band_number"),
    [
        (
            dict(indexerposition=IndexerPosition.B1),
            None,
            SPFBandInFocus.B1,
        ),
        (
            dict(indexerposition=IndexerPosition.B2),
            None,
            SPFBandInFocus.B2,
        ),
        (
            dict(indexerposition=IndexerPosition.B3),
            None,
            SPFBandInFocus.B3,
        ),
        (
            dict(indexerposition=IndexerPosition.B4),
            None,
            SPFBandInFocus.B4,
        ),
        (
            dict(indexerposition=IndexerPosition.B5a),
            None,
            SPFBandInFocus.B5a,
        ),
        (
            dict(indexerposition=IndexerPosition.B5b),
            None,
            SPFBandInFocus.B5b,
        ),
    ],
)
def test_compute_spf_band_in_focus_ignoring_spfrx(
    ds_comp_state,
    spfrx_comp_state,
    expected_band_number,
    state_transition,
):
    actual_band_number = state_transition.compute_spf_band_in_focus(
        ds_comp_state,
        spfrx_comp_state,
    )
    assert expected_band_number == actual_band_number


# TODO add ignored scenarios for capability state
@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=DSOperatingMode.STARTUP, indexerposition=None),
            dict(dishmode=None),
            dict(b5bcapabilitystate=SPFRxCapabilityStates.UNAVAILABLE),
            dict(b5bcapabilitystate=SPFCapabilityStates.UNAVAILABLE),
            CapabilityStates.UNAVAILABLE,
        ),
        (
            dict(operatingmode=DSOperatingMode.STARTUP, indexerposition=None),
            dict(dishmode=None),
            None,
            dict(b5bcapabilitystate=SPFCapabilityStates.UNAVAILABLE),
            CapabilityStates.UNAVAILABLE,
        ),
        (
            dict(operatingmode=DSOperatingMode.STARTUP, indexerposition=None),
            dict(dishmode=None),
            dict(b5bcapabilitystate=SPFRxCapabilityStates.UNAVAILABLE),
            None,
            CapabilityStates.UNAVAILABLE,
        ),
        (
            dict(operatingmode=DSOperatingMode.STARTUP, indexerposition=None),
            dict(dishmode=None),
            None,
            None,
            CapabilityStates.UNAVAILABLE,
        ),
    ],
)
def test_capability_state_rules_unavailable(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b5b",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.STANDBY_LP),
            dict(b5bcapabilitystate=SPFRxCapabilityStates.STANDBY),
            dict(b5bcapabilitystate=SPFCapabilityStates.STANDBY),
            CapabilityStates.STANDBY,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.STANDBY_LP),
            None,
            dict(b5bcapabilitystate=SPFCapabilityStates.STANDBY),
            CapabilityStates.STANDBY,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.STANDBY_LP),
            dict(b5bcapabilitystate=SPFRxCapabilityStates.STANDBY),
            None,
            CapabilityStates.STANDBY,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.STANDBY_LP),
            None,
            None,
            CapabilityStates.STANDBY,
        ),
    ],
)
def test_capability_state_rules_standby(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b5b",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.CONFIG),
            dict(b4capabilitystate=SPFRxCapabilityStates.CONFIGURE),
            dict(b4capabilitystate=SPFCapabilityStates.OPERATE_DEGRADED),
            CapabilityStates.CONFIGURING,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.CONFIG),
            None,
            dict(b4capabilitystate=SPFCapabilityStates.OPERATE_DEGRADED),
            CapabilityStates.CONFIGURING,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.CONFIG),
            dict(b4capabilitystate=SPFRxCapabilityStates.CONFIGURE),
            None,
            CapabilityStates.CONFIGURING,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=DishMode.CONFIG),
            None,
            None,
            CapabilityStates.CONFIGURING,
        ),
    ],
)
def test_capability_state_rules_configuring(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b4",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.B1),
            dict(dishmode=None),
            dict(b3capabilitystate=SPFRxCapabilityStates.OPERATE),
            dict(b3capabilitystate=SPFCapabilityStates.OPERATE_DEGRADED),
            CapabilityStates.OPERATE_DEGRADED,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.B1),
            dict(dishmode=None),
            None,
            dict(b3capabilitystate=SPFCapabilityStates.OPERATE_DEGRADED),
            CapabilityStates.OPERATE_DEGRADED,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.B1),
            dict(dishmode=None),
            dict(b3capabilitystate=SPFRxCapabilityStates.OPERATE),
            None,
            CapabilityStates.OPERATE_DEGRADED,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.B1),
            dict(dishmode=None),
            None,
            None,
            CapabilityStates.OPERATE_DEGRADED,
        ),
    ],
)
def test_capability_state_rules_degraded(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b3",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=None, indexerposition=IndexerPosition.MOVING),
            dict(dishmode=DishMode.STOW),
            dict(b1capabilitystate=SPFRxCapabilityStates.OPERATE),
            dict(b1capabilitystate=SPFCapabilityStates.OPERATE_FULL),
            CapabilityStates.OPERATE_FULL,
        ),
        (
            dict(operatingmode=None, indexerposition=IndexerPosition.MOVING),
            dict(dishmode=DishMode.STOW),
            None,
            dict(b1capabilitystate=SPFCapabilityStates.OPERATE_FULL),
            CapabilityStates.OPERATE_FULL,
        ),
        (
            dict(operatingmode=None, indexerposition=IndexerPosition.MOVING),
            dict(dishmode=DishMode.STOW),
            dict(b1capabilitystate=SPFRxCapabilityStates.OPERATE),
            None,
            CapabilityStates.OPERATE_FULL,
        ),
        (
            dict(operatingmode=None, indexerposition=IndexerPosition.MOVING),
            dict(dishmode=DishMode.STOW),
            None,
            None,
            CapabilityStates.OPERATE_FULL,
        ),
    ],
)
def test_capability_state_rules_operate(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b1",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    (
        "ds_comp_state",
        "dish_manager_comp_state",
        "spfrx_comp_state",
        "spf_comp_state",
        "cap_state",
    ),
    [
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=None),
            dict(b1capabilitystate=None),
            dict(b1capabilitystate=None),
            CapabilityStates.UNKNOWN,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=None),
            None,
            dict(b1capabilitystate=None),
            CapabilityStates.UNKNOWN,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=None),
            dict(b1capabilitystate=None),
            None,
            CapabilityStates.UNKNOWN,
        ),
        (
            dict(operatingmode=None, indexerposition=None),
            dict(dishmode=None),
            None,
            None,
            CapabilityStates.UNKNOWN,
        ),
    ],
)
def test_capability_state_rules_unknown(
    ds_comp_state,
    dish_manager_comp_state,
    spfrx_comp_state,
    spf_comp_state,
    cap_state,
    state_transition,
):
    assert (
        state_transition.compute_capability_state(
            "b1",
            ds_comp_state,
            dish_manager_comp_state,
            spfrx_comp_state,
            spf_comp_state,
        )
        == cap_state
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, expected_power_state"),
    [
        (
            dict(powerstate=DSPowerState.UPS),
            dict(powerstate=SPFPowerState.UNKNOWN),
            PowerState.UPS,
        ),
        (
            dict(powerstate=DSPowerState.OFF),
            dict(powerstate=SPFPowerState.UNKNOWN),
            PowerState.UPS,
        ),
        (
            dict(powerstate=DSPowerState.LOW_POWER),
            dict(powerstate=SPFPowerState.LOW_POWER),
            PowerState.LOW,
        ),
        (
            dict(powerstate=DSPowerState.UNKNOWN),
            dict(powerstate=SPFPowerState.UNKNOWN),
            PowerState.LOW,
        ),
        (
            dict(powerstate=DSPowerState.LOW_POWER),
            dict(powerstate=SPFPowerState.FULL_POWER),
            PowerState.LOW,
        ),
        (
            dict(powerstate=DSPowerState.FULL_POWER),
            dict(powerstate=SPFPowerState.LOW_POWER),
            PowerState.FULL,
        ),
        (
            dict(powerstate=DSPowerState.FULL_POWER),
            dict(powerstate=SPFPowerState.FULL_POWER),
            PowerState.FULL,
        ),
    ],
)
def test_compute_power_state(
    ds_comp_state,
    spf_comp_state,
    expected_power_state,
    state_transition,
):
    actual_power_state = state_transition.compute_power_state(
        ds_comp_state,
        spf_comp_state,
    )
    assert expected_power_state == actual_power_state


@pytest.mark.unit
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, expected_power_state"),
    [
        (
            dict(powerstate=DSPowerState.UPS),
            None,
            PowerState.UPS,
        ),
        (
            dict(powerstate=DSPowerState.OFF),
            None,
            PowerState.UPS,
        ),
        (
            dict(powerstate=DSPowerState.LOW_POWER),
            None,
            PowerState.LOW,
        ),
        (
            dict(powerstate=DSPowerState.UNKNOWN),
            None,
            PowerState.LOW,
        ),
        (
            dict(powerstate=DSPowerState.FULL_POWER),
            None,
            PowerState.FULL,
        ),
    ],
)
def test_compute_power_state_ignoring_spf(
    ds_comp_state,
    spf_comp_state,
    expected_power_state,
    state_transition,
):
    actual_power_state = state_transition.compute_power_state(
        ds_comp_state,
        spf_comp_state,
    )
    assert expected_power_state == actual_power_state
