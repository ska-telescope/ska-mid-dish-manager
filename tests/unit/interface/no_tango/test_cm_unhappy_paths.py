"""Tests dish manager component manager slew command handler"""

from unittest.mock import Mock

import pytest
from ska_control_model import ResultCode

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
    [[result_code], [message]] = component_manager.slew([22.0], callbacks["task_cb"])
    assert result_code == ResultCode.REJECTED
    assert message == "Length of argument (1) is not as expected (2)."


@pytest.mark.unit
def test_track_load_static_off_with_invalid_input(
    band: IndexerPosition,
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """
    Verify behaviour of Trackloadoffstatic command using invalid input.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    [[result_code], [message]] = component_manager.track_load_static_off(
        [10.0, 20.0, 10.0], callbacks["task_cb"]
    )
    assert result_code == ResultCode.REJECTED
    assert message == "Length of argument (3) is not as expected (2)."
