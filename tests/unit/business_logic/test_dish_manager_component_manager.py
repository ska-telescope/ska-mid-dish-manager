import gc
import logging
import threading
import time
import weakref
from unittest import mock

import pytest

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager

LOGGER = logging.getLogger(__name__)


def force_gc_on_weak_ref(weak_ref: weakref.ref) -> None:
    """Force garbage collection of the component manager referenced by a weak reference."""
    for _ in range(10):
        if weak_ref() is None:
            break
        time.sleep(0.1)
        # Force garbage collection
        gc.collect()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
@mock.patch.multiple(
    "ska_mid_dish_manager.component_managers.wms_cm.WMSComponentManager",
    write_wms_group_attribute_value=mock.MagicMock(),
    _poll_wms_wind_speed_data=mock.MagicMock(),
)
def test_component_manager_gracefully_cleans_up_resources(patch_dp, caplog):
    """Test that the DishManagerComponentManager can be created,
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
        weak_ref = weakref.ref(component_manager)
        component_manager.start_communicating()
        component_manager.stop_communicating()
        # remove strong reference and force garbage collection
        del component_manager
        force_gc_on_weak_ref(weak_ref)

    # Ensure there are no thread leaks
    # the assertion allows a difference of up to 2 threads because some background threads
    # (e.g.main thread or test framework) may be started during the test run and not cleaned up
    assert len(threading.enumerate()) <= 2, f"Thread leak detected: {threading.enumerate()}"

    # Ensure there are no memory leaks
    # check that no DishManagerComponentManager instances remain in memory
    for obj in gc.get_objects():
        if isinstance(obj, DishManagerComponentManager):
            raise AssertionError("DishManagerComponentManager instance still exists in memory")
