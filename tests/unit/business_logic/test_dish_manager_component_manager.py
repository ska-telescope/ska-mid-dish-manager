import gc
import logging
import threading
from unittest import mock

import pytest

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
def test_component_manager_gracefully_cleans_up_resources(patch_dp, caplog):
    """
    Test that the DishManagerComponentManager can be created,
    started and destroyed without resource leaks or errors.
    """
    caplog.set_level(logging.WARNING)

    for _ in range(100):
        component_manager = DishManagerComponentManager(
            LOGGER,
            mock.MagicMock(name="mock_command_tracker"),
            mock.MagicMock(name="mock_build_state_callback"),
            mock.MagicMock(name="mock_attr_quality_callback"),
            "device-1",
            "sub-device-1",
            "sub-device-2",
            "sub-device-3",
        )
        component_manager.start_communicating()
        component_manager.stop_communicating()
        # explicitly remove this reference to make the object eligible for collection sooner
        del component_manager

    # Force garbage collection to help ensure cleanup
    gc.collect()

    # Ensure there are no thread leaks
    # the assertion allows a difference of up to 2 threads because some background threads
    # (e.g.main thread or test framework) may be started during the test run and not cleaned up
    assert len(threading.enumerate()) <= 2, f"Thread leak detected: {threading.enumerate()}"

    # Ensure there are no memory leaks
    # check that no DishManagerComponentManager instances remain in memory
    for obj in gc.get_objects():
        if isinstance(obj, DishManagerComponentManager):
            raise AssertionError("DishManagerComponentManager instance still exists in memory")
