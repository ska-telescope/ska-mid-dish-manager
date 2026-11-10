"""Unit tests verifying model against DS_SetStowMode transition."""

import pytest
from ska_control_model import ResultCode


@pytest.mark.unit
@pytest.mark.forked
def test_stow_mode(dish_manager_resources):
    device_proxy, _ = dish_manager_resources

    [[result_code], [msg]] = device_proxy.SetStowMode()
    assert result_code == ResultCode.OK

    expected_msg = "Stow called, monitor achievedPointing and dishmode"
    assert msg == expected_msg
