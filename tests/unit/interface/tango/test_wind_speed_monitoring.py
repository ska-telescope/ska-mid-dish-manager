"""Verify the wind stow requirement (L2-3470) for wind speed monitoring."""

import threading
import time
from collections import deque
from unittest import mock

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.constants import (
    MEAN_WIND_SPEED_THRESHOLD_MPS,
    WIND_GUST_THRESHOLD_MPS,
)


@pytest.fixture
def configure_mocks_for_dish_manager():
    """Set up the dish manager device for wind stow tests."""
    with (
        mock.patch("ska_mid_dish_manager.component_managers.spfrx_cm.MonitorPing"),
        mock.patch(
            "ska_mid_dish_manager.component_managers.tango_device_cm."
            "TangoDeviceComponentManager.start_communicating"
        ),
        mock.patch(
            "ska_mid_dish_manager.component_managers.wms_cm."
            "WMSComponentManager.start_communicating"
        ),
        mock.patch(
            "ska_mid_dish_manager.component_managers.dish_manager_cm.TangoPropertyAccessor"
        ),
    ):
        tango_context = DeviceTestContext(DishManager)
        tango_context.start()
        device_proxy = tango_context.device

        class_instance = DishManager.instances.get(device_proxy.name())
        dish_manager_cm = class_instance.component_manager
        wms_cm = dish_manager_cm.sub_component_managers["WMS"]

        # mock _fetch_wind_limits on dish manager component manager
        dish_manager_cm._fetch_wind_limits = mock.Mock(
            return_value={
                "WindGustThreshold": WIND_GUST_THRESHOLD_MPS,
                "MeanWindSpeedThreshold": MEAN_WIND_SPEED_THRESHOLD_MPS,
            }
        )

        # mock execute_command on the ds component manager
        ds_cm = dish_manager_cm.sub_component_managers["DS"]
        ds_cm.execute_command = mock.Mock()

        # update instance variables on the wms component manager
        wms_cm = dish_manager_cm.sub_component_managers["WMS"]
        wms_cm._wms_devices_count = 3
        wms_cm._wind_gust_period = 3
        wms_cm._wind_speed_moving_average_period = 5

        devices_count = wms_cm._wms_devices_count
        mean_avg_period = wms_cm._wind_speed_moving_average_period
        gust_avg_period = wms_cm._wind_gust_period
        polling_period = wms_cm._wms_polling_period

        wms_cm._wind_speed_buffer_length = int(devices_count * (mean_avg_period / polling_period))
        wms_cm._wind_gust_buffer_length = int(gust_avg_period / polling_period)
        wms_cm._wind_speed_buffer = deque(maxlen=wms_cm._wind_speed_buffer_length)
        wms_cm._wind_gust_buffer = deque(maxlen=wms_cm._wind_gust_buffer_length)

        yield device_proxy, wms_cm


@pytest.mark.unit
@pytest.mark.forked
def test_wind_stow_triggered_on_mean_wind_speed_exceeding_threshold(
    configure_mocks_for_dish_manager, event_store_class
):
    """Verify that the dish stows when the mean wind speed exceeds the threshold."""
    device_proxy, wms_cm = configure_mocks_for_dish_manager
    mean_wind_speed_average_period = wms_cm._wind_speed_moving_average_period
    polling_period = wms_cm._wms_polling_period
    wait_event = threading.Event()

    progress_event_store = event_store_class()
    mean_wind_speed_event_store = event_store_class()
    device_proxy.subscribe_event(
        "meanWindSpeed",
        tango.EventType.CHANGE_EVENT,
        mean_wind_speed_event_store,
    )
    device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    # enable wind stow action for mean wind speed
    device_proxy.autoWindStowEnabled = True

    test_start_time = time.time()

    # simulate wind speed readings
    # the mean wind speed will be calculated after 5 seconds of polling
    # and should be 11.3 m/s based on the sample readings
    time_stamped_wind_speed_readings = [
        [test_start_time, 7],
        [test_start_time, 11],
        [test_start_time, 16],
    ]
    for _ in range(mean_wind_speed_average_period):
        computed_mean = wms_cm._compute_mean_wind_speed(
            time_stamped_wind_speed_readings, test_start_time
        )
        wms_cm._update_component_state(meanwindspeed=computed_mean)
        wait_event.wait(polling_period)

    # the device should push a change event for mean wind speed
    wind_speed_readings = [reading[1] for reading in time_stamped_wind_speed_readings]
    total_samples_sent = wind_speed_readings * mean_wind_speed_average_period
    expected_mean_wind_speed = sum(total_samples_sent) / len(total_samples_sent)
    assert mean_wind_speed_event_store.wait_for_value(expected_mean_wind_speed)

    # the stow trigger will update the lrc progress
    expected_progress_update = "Stow called, monitor dishmode for LRC completed"
    lrc_progress_event_values = progress_event_store.get_queue_values()
    lrc_progress_event_values = "".join([str(event[1]) for event in lrc_progress_event_values])
    assert expected_progress_update in lrc_progress_event_values
    _, requested_action = device_proxy.lastCommandedMode
    assert requested_action == "WindStow"

    # the status attribute will report wind stow action
    computed_averages = {"meanwindspeed": expected_mean_wind_speed}
    alarm_msg = f"Dish stowed due to extreme wind condition: {computed_averages}."
    assert device_proxy.Status() == alarm_msg
    assert device_proxy.State() == tango.DevState.ALARM


@pytest.mark.unit
@pytest.mark.forked
def test_wind_stow_triggered_on_wind_gust_exceeding_threshold(
    configure_mocks_for_dish_manager, event_store_class
):
    """Verify that the dish stows when the wind gust exceeds the threshold."""
    device_proxy, wms_cm = configure_mocks_for_dish_manager
    wind_gust_average_period = wms_cm._wind_gust_period
    polling_period = wms_cm._wms_polling_period
    wait_event = threading.Event()

    progress_event_store = event_store_class()
    wind_gust_event_store = event_store_class()
    device_proxy.subscribe_event(
        "windGust",
        tango.EventType.CHANGE_EVENT,
        wind_gust_event_store,
    )
    device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    # enable wind stow action for wind gust
    device_proxy.autoWindStowEnabled = True

    # simulate wind speed readings
    # the wind gust will be calculated after 3 seconds of polling
    # and should be 17.0 m/s based on the sample readings
    test_start_time = time.time()
    time_stamped_wind_speed_readings = [
        [test_start_time, 17],
        [test_start_time, 12],
        [test_start_time, 15],
    ]
    for _ in range(wind_gust_average_period):
        computed_wind_gust = wms_cm._process_wind_gust(
            time_stamped_wind_speed_readings, test_start_time
        )
        wms_cm._update_component_state(windgust=computed_wind_gust)
        wait_event.wait(polling_period)

    # the device should push a change event for wind gust
    wind_speed_readings = [reading[1] for reading in time_stamped_wind_speed_readings]
    total_samples_sent = wind_speed_readings * wind_gust_average_period
    expected_wind_gust = max(total_samples_sent)
    assert wind_gust_event_store.wait_for_value(expected_wind_gust)

    # the stow trigger will update the lrc progress
    expected_progress_update = "Stow called, monitor dishmode for LRC completed"
    lrc_progress_event_values = progress_event_store.get_queue_values()
    lrc_progress_event_values = "".join([str(event[1]) for event in lrc_progress_event_values])
    assert expected_progress_update in lrc_progress_event_values
    _, requested_action = device_proxy.lastCommandedMode
    assert requested_action == "WindStow"

    # the status attribute will report wind stow action
    computed_averages = {"windgust": expected_wind_gust}
    alarm_msg = f"Dish stowed due to extreme wind condition: {computed_averages}."
    assert device_proxy.Status() == alarm_msg
    assert device_proxy.State() == tango.DevState.ALARM
