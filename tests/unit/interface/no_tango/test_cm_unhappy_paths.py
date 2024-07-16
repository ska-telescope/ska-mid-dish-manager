"""Tests dish manager component manager slew and trackloadstaticoff"""
import re

import pytest
from ska_control_model import TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
def test_slew_with_invalid_input(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """
    Verify behaviour of Slew command using invalid input.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    result_code, message = component_manager.slew([22.0], callbacks["task_cb"])
    assert result_code == TaskStatus.REJECTED
    assert message == "Expected 2 arguments (az, el) but got 1 arg(s)."


@pytest.mark.unit
def test_track_load_static_off_with_invalid_input(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """
    Verify behaviour of Trackloadoffstatic command using invalid input.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    result_code, message = component_manager.track_load_static_off(
        [10.0, 20.0, 10.0], callbacks["task_cb"]
    )
    assert result_code == TaskStatus.REJECTED
    assert message == "Expected 2 arguments (off_xel, off_el) but got 3 arg(s)."


@pytest.mark.unit
def test_validate_band_x_pointing_model_params_with_invalid_input(
    component_manager: DishManagerComponentManager,
) -> None:
    """
    Verify behaviour of validate_band_x_pointing_model_params() using invalid input.

    :param component_manager: the component manager under test
    """
    with pytest.raises(
        ValueError, match=re.escape("Expected 2 arguments (off_xel, off_el) but got 3 arg(s).")
    ):
        component_manager._validate_band_x_pointing_model_params(
            [10.0, 20.0, 10.0],
        )
