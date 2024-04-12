"""Test AbortCommands"""
import logging
import time

import pytest
import tango
from ska_control_model import ResultCode

from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.fixture(autouse=True)
def turn_on_spf_attribute_update(request, spf_device_proxy):
    """Ensure that attribute updates on spf is restored"""

    def toggle_attribute_update():
        spf_device_proxy.skipAttributeUpdates = False

    request.addfinalizer(toggle_attribute_update)


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_abort_commands(
    event_store, event_store_class, dish_manager_proxy, spf_device_proxy, ds_device_proxy
):
    """Test AbortCommands aborts the executing long running command"""
    # Set a flag on SPF to skip attribute updates
    # This is useful to ensure that the long running command
    # does not finish executing before AbortCommands is triggered
    spf_device_proxy.skipAttributeUpdates = True
    # Create a logger
    logger = logging.getLogger("example_logger")
    logger.setLevel(logging.INFO)

    for attr in [
        "longRunningCommandResult",
        "longRunningCommandProgress",
    ]:
        dish_manager_proxy.subscribe_event(
            attr,
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

    cmds_in_queue_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        cmds_in_queue_store,
    )

    logger.info(f": {dish_manager_proxy.dishMode}")

    # Transition to FP mode
    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    event_store.wait_for_value((f"{unique_id}", "Awaiting dishMode change to STANDBY_FP"))

    dish_manager_proxy.AbortCommands()

    time.sleep(1)
    logger.info(f"longRunningCommandProgress: {dish_manager_proxy.longRunningCommandProgress}")
    assert dish_manager_proxy.longRunningCommandProgress == (
        f"{unique_id}",
        "SetStandbyFPMode Aborted",
    )
    time.sleep(1)
    logger.info(f"longRunningCommandProgress: {dish_manager_proxy.longRunningCommandProgress}")
    assert dish_manager_proxy.longRunningCommandProgress == (
        f"{unique_id}",
        "SetStandbyFPMode Aborted",
    )
    time.sleep(1)
    logger.info(f"longRunningCommandProgress: {dish_manager_proxy.longRunningCommandProgress}")
    assert dish_manager_proxy.longRunningCommandProgress == (
        f"{unique_id}",
        "SetStandbyFPMode Aborted",
    )
    time.sleep(1)
    logger.info(f"longRunningCommandProgress: {dish_manager_proxy.longRunningCommandProgress}")
    assert dish_manager_proxy.longRunningCommandProgress == (
        f"{unique_id}",
        "SetStandbyFPMode Aborted",
    )
    time.sleep(1)
    logger.info(f"longRunningCommandResult: {dish_manager_proxy.longRunningCommandResult}")

    assert dish_manager_proxy.longRunningCommandResult == (
        f"{unique_id}",
        f'[{ResultCode.ABORTED}, "SetStandbyFPMode Aborted"]',
    )

    # confirm dishmanager aborted the request on lrcResult
    # event_store.wait_for_value(
    #     (f"{unique_id}", f"[{ResultCode.ABORTED}, SetStandbyFPMode Aborted]")
    # )
    assert dish_manager_proxy.dishMode != DishMode.STANDBY_FP
    # logger.info(f": {dish_manager_proxy.dishMode}")
    # # ensure that the queue is cleared out
    earlier_commands_in_queue = cmds_in_queue_store.get_queue_values()
    assert earlier_commands_in_queue

    logger.info(f"Queue Values: {earlier_commands_in_queue}")

    # assert not dish_manager_proxy.longRunningCommandsInQueue
    logger.info(f"longRunningCommandsInQueue: {dish_manager_proxy.longRunningCommandsInQueue}")
