"""Tests dish manager component manager trackInterpolation command handler"""

import pytest
from ska_control_model import CommunicationStatus, ResultCode

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
def test_set_track_interpolation_mode_handler(
    component_manager: DishManagerComponentManager,
) -> None:
    """
    Verify behaviour of SetTrackInterpolationMode command handler.

    :param component_manager: the component manager under test
    :param mock_command_tracker: a representing the command tracker class
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    # set_track_interpolation_mode has no pre-condition.
    # It only requires a connection to the ds device
    ds_component_manager = component_manager.sub_component_managers["DS"]
    ds_component_manager._update_communication_state(CommunicationStatus.ESTABLISHED)

    status, message = component_manager.set_track_interpolation_mode("interpolation mode")
    # this is a handler for an attribute write
    assert (status, message) == (
        ResultCode.OK,
        "Successfully updated trackInterpolationMode on DSManager",
    )
