"""Unit tests verifying model against dishMode transitions."""

# pylint: disable=too-many-lines,missing-function-docstring
import pytest
from ska_control_model import HealthState

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    SPFBandInFocus,
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from ska_mid_dish_manager.models.dish_state_transition import StateTransition


# pylint: disable=redefined-outer-name
@pytest.fixture(scope="module")
def state_transition():
    """Instance of StateTransition"""
    return StateTransition()


# Order DS, SPF, SPFRX
# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_mode"),
    [
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_LP, indexerposition=IndexerPosition.UNKNOWN
            ),
            dict(operatingmode=SPFOperatingMode.STARTUP),
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STARTUP,
        ),
        (
            dict(indexerposition=IndexerPosition.MOVING),
            dict(operatingmode=SPFOperatingMode.STANDBY_LP),
            dict(operatingmode=SPFRxOperatingMode.DATA_CAPTURE),
            DishMode.CONFIG,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW),
            dict(operatingmode=SPFOperatingMode.STANDBY_LP),
            dict(operatingmode=SPFRxOperatingMode.CONFIGURE),
            DishMode.CONFIG,
        ),
        (
            dict(operatingmode=DSOperatingMode.STANDBY_FP, indexerposition=IndexerPosition.MOVING),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.CONFIG,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_LP, indexerposition=IndexerPosition.UNKNOWN
            ),
            dict(operatingmode=SPFOperatingMode.STANDBY_LP),
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STANDBY_LP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_FP, indexerposition=IndexerPosition.UNKNOWN
            ),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STANDBY_FP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_FP, indexerposition=IndexerPosition.UNKNOWN
            ),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            dict(operatingmode=SPFRxOperatingMode.DATA_CAPTURE),
            DishMode.STANDBY_FP,
        ),
        (
            dict(operatingmode=DSOperatingMode.POINT, indexerposition=IndexerPosition.UNKNOWN),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            dict(operatingmode=SPFRxOperatingMode.DATA_CAPTURE),
            DishMode.OPERATE,
        ),
        # Any other random combo goes to UNKNOWN
        (
            dict(operatingmode=DSOperatingMode.UNKNOWN, indexerposition=IndexerPosition.UNKNOWN),
            dict(operatingmode=SPFOperatingMode.ERROR),
            dict(operatingmode=SPFRxOperatingMode.UNKNOWN),
            DishMode.UNKNOWN,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.UNKNOWN),
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
# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_mode"),
    [
        (
            dict(operatingmode=DSOperatingMode.STANDBY_FP, indexerposition=IndexerPosition.MOVING),
            None,
            dict(operatingmode=SPFRxOperatingMode.CONFIGURE),
            DishMode.CONFIG,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.UNKNOWN),
            None,
            dict(operatingmode=SPFRxOperatingMode.MAINTENANCE),
            DishMode.MAINTENANCE,
        ),
        (
            dict(operatingmode=DSOperatingMode.POINT, indexerposition=IndexerPosition.UNKNOWN),
            None,
            dict(operatingmode=SPFRxOperatingMode.DATA_CAPTURE),
            DishMode.OPERATE,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_FP, indexerposition=IndexerPosition.UNKNOWN
            ),
            None,
            dict(operatingmode=SPFRxOperatingMode.DATA_CAPTURE),
            DishMode.STANDBY_FP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_FP, indexerposition=IndexerPosition.UNKNOWN
            ),
            None,
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STANDBY_FP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_LP, indexerposition=IndexerPosition.UNKNOWN
            ),
            None,
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STANDBY_LP,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.UNKNOWN),
            None,
            dict(operatingmode=SPFRxOperatingMode.UNKNOWN),
            DishMode.STOW,
        ),
        (
            dict(operatingmode=DSOperatingMode.STARTUP, indexerposition=IndexerPosition.UNKNOWN),
            None,
            dict(operatingmode=SPFRxOperatingMode.STANDBY),
            DishMode.STARTUP,
        ),
        (
            dict(operatingmode=DSOperatingMode.UNKNOWN, indexerposition=IndexerPosition.UNKNOWN),
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
# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_mode"),
    [
        (
            dict(operatingmode=DSOperatingMode.STANDBY_FP, indexerposition=IndexerPosition.MOVING),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            None,
            DishMode.CONFIG,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.UNKNOWN),
            dict(operatingmode=SPFOperatingMode.MAINTENANCE),
            None,
            DishMode.MAINTENANCE,
        ),
        (
            dict(operatingmode=DSOperatingMode.POINT, indexerposition=IndexerPosition.UNKNOWN),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            None,
            DishMode.OPERATE,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_FP, indexerposition=IndexerPosition.UNKNOWN
            ),
            dict(operatingmode=SPFOperatingMode.OPERATE),
            None,
            DishMode.STANDBY_FP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_LP, indexerposition=IndexerPosition.UNKNOWN
            ),
            dict(operatingmode=SPFOperatingMode.STANDBY_LP),
            None,
            DishMode.STANDBY_LP,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.UNKNOWN),
            dict(operatingmode=SPFOperatingMode.ERROR),
            None,
            DishMode.STOW,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_LP, indexerposition=IndexerPosition.UNKNOWN
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
# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    ("ds_comp_state, spf_comp_state, spfrx_comp_state, expected_dish_mode"),
    [
        (
            dict(indexerposition=IndexerPosition.MOVING),
            None,
            None,
            DishMode.CONFIG,
        ),
        (
            dict(operatingmode=DSOperatingMode.POINT, indexerposition=IndexerPosition.UNKNOWN),
            None,
            None,
            DishMode.OPERATE,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_FP, indexerposition=IndexerPosition.UNKNOWN
            ),
            None,
            None,
            DishMode.STANDBY_FP,
        ),
        (
            dict(
                operatingmode=DSOperatingMode.STANDBY_LP, indexerposition=IndexerPosition.UNKNOWN
            ),
            None,
            None,
            DishMode.STANDBY_LP,
        ),
        (
            dict(operatingmode=DSOperatingMode.STOW, indexerposition=IndexerPosition.UNKNOWN),
            None,
            None,
            DishMode.STOW,
        ),
        (
            dict(operatingmode=DSOperatingMode.STARTUP, indexerposition=IndexerPosition.UNKNOWN),
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


# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
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


# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
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


# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
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


# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
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


# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
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
            dict(indexerposition=IndexerPosition.B5),
            dict(bandinfocus=SPFBandInFocus.B5a),
            dict(configuredband=Band.B5a),
            Band.B5a,
        ),
        (
            dict(indexerposition=IndexerPosition.B5),
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


# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
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
            dict(indexerposition=IndexerPosition.B5),
            None,
            dict(configuredband=Band.B5a),
            Band.B5a,
        ),
        (
            dict(indexerposition=IndexerPosition.B5),
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


# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
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
            dict(indexerposition=IndexerPosition.B5),
            dict(bandinfocus=SPFBandInFocus.B5a),
            None,
            Band.B5a,
        ),
        (
            dict(indexerposition=IndexerPosition.B5),
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


# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
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
        # TODO: Clarify SPF B5a or B5b given only DS.IndexerPosition.B5
        # (
        #     dict(indexerposition=IndexerPosition.B5),
        #     None,
        #     None,
        #     Band.B5a,
        # ),
        # (
        #     dict(indexerposition=IndexerPosition.B5),
        #     None,
        #     None,
        #     Band.B5b,
        # ),
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


# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
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
            dict(indexerposition=IndexerPosition.B5),
            dict(configuredband=Band.B5a),
            SPFBandInFocus.B5a,
        ),
        (
            dict(indexerposition=IndexerPosition.B5),
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


# pylint: disable=use-dict-literal
@pytest.mark.unit
@pytest.mark.forked
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
        # TODO: Clarify SPF B5a or B5b given only DS.IndexerPosition.B5
        # (
        #     dict(indexerposition=IndexerPosition.B5),
        #     None,
        #     SPFBandInFocus.B5a,
        # ),
        # (
        #     dict(indexerposition=IndexerPosition.B5),
        #     None,
        #     SPFBandInFocus.B5b,
        # ),
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
