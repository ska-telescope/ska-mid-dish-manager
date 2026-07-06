"""Acceptance test for lastCommandFailure attribute."""

import pytest
import tango


@pytest.mark.acceptance
def test_last_command_failure(
    dish_manager_proxy: tango.DeviceProxy, ds_device_proxy: tango.DeviceProxy
):
    """Test lastCommandFailure attribute."""
    # Get the initial lastCommandFailure value
    dm_last_command_failure_value_1 = dish_manager_proxy.read_attribute("lastCommandFailure").value
    ds_last_command_failure_value_1 = ds_device_proxy.read_attribute("lastCommandFailure").value
    # Happy Path: Run a command that passes - expect no update on DM and
    #  DS lastCommandFailure attrs
    dish_manager_proxy.SetKValue(5)
    dm_last_command_failure_value_2 = dish_manager_proxy.read_attribute("lastCommandFailure").value
    ds_last_command_failure_value_2 = ds_device_proxy.read_attribute("lastCommandFailure").value
    assert dm_last_command_failure_value_1 == dm_last_command_failure_value_2
    assert ds_last_command_failure_value_1 == ds_last_command_failure_value_2

    # Unhappy Path: Run a command that fails - expect an updated DM lastCommandFailure
    #  attr but not change on DS Manager
    dish_manager_proxy.SetStowMode()
    dish_manager_proxy.Slew([45, 45])
    assert (
        "Slew command rejected for current dishMode. Slew command is allowed for dishMode OPERATE"
        in dish_manager_proxy.lastCommandFailure[3]
    )
    dm_last_command_failure_value_3 = dish_manager_proxy.read_attribute("lastCommandFailure").value
    ds_last_command_failure_value_3 = ds_device_proxy.read_attribute("lastCommandFailure").value

    # DM has updated
    assert dm_last_command_failure_value_3 != dm_last_command_failure_value_2
    # DS has not updated because Slew command was not issued on DS (is_allowed fn blocked it)
    assert ds_last_command_failure_value_3 == ds_last_command_failure_value_2
