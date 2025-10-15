"""Tests dish manager component manager setkvalue command handler."""

import pytest
from ska_control_model import ResultCode

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
def test_set_kvalue_handler(
    component_manager: DishManagerComponentManager,
) -> None:
    """Verify behaviour of SetKValue command handler.

    :param component_manager: the component manager under test
    """
    # set_kvalue has no pre-condition.
    result_code, message = component_manager.set_kvalue(5)

    # this is a fast command and returns immediately
    assert (result_code, message) == (ResultCode.OK, "SetKValue successfully executed")
