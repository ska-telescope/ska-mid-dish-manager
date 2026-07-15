import logging
import threading

import pytest
from ska_tango_testing.mock import MockCallable

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.constants import (
    DEFAULT_ACTION_TIMEOUT_S,
    DEFAULT_DISH_MANAGER_TRL,
    DEFAULT_DS_MANAGER_TRL,
    DEFAULT_SPFC_TRL,
    DEFAULT_SPFRX_TRL,
    DEFAULT_WATCHDOG_TIMEOUT,
    MEAN_WIND_SPEED_THRESHOLD_MPS,
    WIND_GUST_THRESHOLD_MPS,
)

LOGGER = logging.getLogger(__name__)


@pytest.mark.acceptance
def test_dish_manager_component_manager_threads_management(component_state_store):
    """Test dish manager component mananger clears threads on stop communication."""
    mock_callable = MockCallable(timeout=5)
    cm = DishManagerComponentManager(
        LOGGER,
        command_tracker=mock_callable,
        build_state_callback=mock_callable,
        quality_state_callback=mock_callable,
        tango_device_name=DEFAULT_DISH_MANAGER_TRL,
        ds_device_fqdn=DEFAULT_DS_MANAGER_TRL,
        spf_device_fqdn=DEFAULT_SPFC_TRL,
        spfrx_device_fqdn=DEFAULT_SPFRX_TRL,
        b5dc_device_fqdn="",
        action_timeout_s=DEFAULT_ACTION_TIMEOUT_S,
        communication_state_callback=mock_callable,
        component_state_callback=component_state_store,
        wms_device_names=[],
        wind_stow_callback=mock_callable,
        command_progress_callback=mock_callable,
        default_watchdog_timeout=DEFAULT_WATCHDOG_TIMEOUT,
        default_mean_wind_speed_threshold=MEAN_WIND_SPEED_THRESHOLD_MPS,
        default_wind_gust_threshold=WIND_GUST_THRESHOLD_MPS,
    )

    cm.start_communicating()

    try:
        threads = threading.enumerate()
        # 3x events_monitor thread (CallbackScheduler), MonitorPing thread, main thread
        # and maybe 3x connection thread which might have already returned
        assert len(threads) <= 8

        thread_names = [t.name for t in threads]

        assert "MainThread" in thread_names
        assert "MonitorPingThread" in thread_names
        events_monitor_thread_count = sum(
            1 for name in thread_names if name.startswith("events_monitor")
        )
        assert events_monitor_thread_count == 3
    finally:
        cm.stop_communicating()

    threads = threading.enumerate()
    assert len(threads) == 1
    assert threads[0].name == "MainThread"
