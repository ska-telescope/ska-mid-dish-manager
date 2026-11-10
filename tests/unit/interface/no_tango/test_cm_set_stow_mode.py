"""Tests dish manager component manager setstow command handler."""

import pytest
from ska_control_model import ResultCode

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
def test_set_stow_mode_handler(
    component_manager: DishManagerComponentManager,
) -> None:
    """Verify behaviour of SetStowMode command handler.

    :param component_manager: the component manager under test
    """
    result_code, msg = component_manager.set_stow_mode()

    assert result_code == ResultCode.OK
    assert msg == "Stow called, monitor achievedPointing and dishmode"
