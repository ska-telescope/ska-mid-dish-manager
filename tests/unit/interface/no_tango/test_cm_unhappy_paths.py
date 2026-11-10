"""Tests dish manager component manager unhappy paths for command handlers."""

import pytest

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
def test_periodic_noise_diode_pars_with_invalid_input(
    component_manager: DishManagerComponentManager,
) -> None:
    """Verify behaviour of set_periodic_noise_diode_pars command using invalid input.

    :param component_manager: the component manager under test
    """
    with pytest.raises(ValueError, match="Expected value of length 3 but got 2."):
        component_manager.set_periodic_noise_diode_pars([1.0, 2.0])


@pytest.mark.unit
def test_periodic_noise_diode_pars_with_invalid_states(
    component_manager: DishManagerComponentManager,
) -> None:
    """Verify behaviour of set_periodic_noise_diode_pars command with invalid states.

    :param component_manager: the component manager under test
    """
    with pytest.raises(
        AssertionError,
        match="Cannot write to periodicNoiseDiodePars."
        " Device is not in STANDBY state."
        " Current state: UNKNOWN",
    ):
        component_manager.set_periodic_noise_diode_pars([1, 2, 3])


@pytest.mark.unit
def test_pseudo_random_noise_diode_pars_with_invalid_input(
    component_manager: DishManagerComponentManager,
) -> None:
    """Verify behaviour of set_pseudo_random_noise_diode_pars command using invalid input.

    :param component_manager: the component manager under test
    """
    with pytest.raises(ValueError, match="Expected value of length 3 but got 2."):
        component_manager.set_pseudo_random_noise_diode_pars([1.0, 2.0])


@pytest.mark.unit
def test_pseudo_random_noise_diode_pars_with_invalid_states(
    component_manager: DishManagerComponentManager,
) -> None:
    """Verify behaviour of set_pseudo_random_noise_diode_pars command with invalid states.

    :param component_manager: the component manager under test
    """
    with pytest.raises(
        AssertionError,
        match="Cannot write to pseudoRandomNoiseDiodePars."
        " Device is not in STANDBY state."
        " Current state: UNKNOWN",
    ):
        component_manager.set_pseudo_random_noise_diode_pars([1, 2, 3])
