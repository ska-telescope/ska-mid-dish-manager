"""Tests dish manager component manager start/stop communication command handler"""

import pytest
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.unit
def test_start_stop_communication(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """
    Verify behaviour of start_communication/ stop_communication command handler.

    :param component_manager: the component manager under test
    :callbacks
    """
    # Assert that the comm state is ESTABLISHED
    assert component_manager.communication_state == CommunicationStatus.ESTABLISHED

    # Change the DishMode to FP
    component_manager.set_standby_fp_mode(callbacks["task_cb"])

    # Wait a bit for the lrc updates to come through.
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values()

    # Check that the component state reports the Standby FP.
    component_manager._update_component_state(dishmode=DishMode.STANDBY_FP)
    component_state_cb.wait_for_value("dishmode", DishMode.STANDBY_FP)

    # Now we call stop communicating
    component_manager.stop_communicating()
    assert component_manager.communication_state == CommunicationStatus.DISABLED

    # Now we attempt to call a command to see if it will not work
    with pytest.raises(ConnectionError, match="Commmunication with sub-components is disabled"):
        component_manager.set_standby_lp_mode(callbacks["task_cb"])

    # Now we call start communicating
    component_manager.start_communicating()

    # Change the DishMode to LP - to see if it will work now that
    # start_comm was called and the status is established.
    component_manager.set_standby_lp_mode(callbacks["task_cb"])

    # Wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values()

    # Check that the component state reports the Standby LP - indicating
    # that the device can now receive commands.
    component_manager._update_component_state(dishmode=DishMode.STANDBY_LP)
    component_state_cb.wait_for_value("dishmode", DishMode.STANDBY_LP)
