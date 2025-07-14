"""Unit tests checking WMS component manager behaviour."""

import logging
import random
import threading
import time
from collections import deque
from functools import partial
from unittest.mock import MagicMock, Mock

import pytest
from ska_control_model import AdminMode, CommunicationStatus

from ska_mid_dish_manager.component_managers.wms_cm import WMSComponentManager

WMS_POLLING_PERIOD = 1.0
WIND_GUST_PERIOD = 3.0
MEAN_WIND_SPEED_PERIOD = 10.0
COMM_STATE_UPDATE_WAIT = 0.3
LOGGER = logging.getLogger(__name__)


def comm_state_callback(signal: threading.Event, communication_state: CommunicationStatus):
    pass


@pytest.mark.forked
@pytest.mark.unit
def test_wms_group_activation_and_polling_starts():
    test_wms_device_names = ["mid/wms/1", "mid/wms/2", "mid/wms/3"]

    wms = WMSComponentManager(
        test_wms_device_names,
        logger=LOGGER,
        component_state_callback=MagicMock(),
        wms_polling_period=WMS_POLLING_PERIOD,
        wind_speed_moving_average_period=MEAN_WIND_SPEED_PERIOD,
        wind_gust_average_period=WIND_GUST_PERIOD,
    )

    wms.write_wms_group_attribute_value = Mock()
    wms._run_wms_group_polling = Mock()

    wms.start_communicating()

    tango_group_device_list = wms._wms_device_group.get_device_list()
    for device_name in test_wms_device_names:
        assert device_name in tango_group_device_list

    wait_event = threading.Event()
    wait_event.wait(timeout=wms._wms_polling_period)

    wms.write_wms_group_attribute_value.assert_called_with("adminMode", AdminMode.ONLINE)
    wms._run_wms_group_polling.assert_called()


@pytest.mark.unit
def test_wms_cm_wind_gust_and_mean_wind_speed_updates():
    component_state = {}

    def component_state_callback(**incoming_comp_state_change):
        component_state.update(incoming_comp_state_change)

    wms = WMSComponentManager(
        ["mid/wms/1", "mid/wms/2", "mid/wms/3"],
        logger=LOGGER,
        component_state_callback=component_state_callback,
        wms_polling_period=WMS_POLLING_PERIOD,
        wind_speed_moving_average_period=MEAN_WIND_SPEED_PERIOD,
        wind_gust_average_period=WIND_GUST_PERIOD,
        meanwindspeed=-1,
        windgust=-1,
    )
    wait_event = threading.Event()
    wms._communication_state_callback = partial(comm_state_callback, wait_event)

    wms.write_wms_group_attribute_value = Mock()
    wms.read_wms_group_attribute_value = Mock()

    def current_time():
        return time.time()

    wms.read_wms_group_attribute_value.side_effect = lambda *args, **kwargs: [
        [current_time(), 10],
        [current_time(), 20],
        [current_time(), 15],
    ]

    wms.start_communicating()
    wait_event.wait(timeout=(wms._wms_polling_period + COMM_STATE_UPDATE_WAIT))
    assert wms.communication_state == CommunicationStatus.ESTABLISHED

    wait_event.wait(timeout=MEAN_WIND_SPEED_PERIOD)

    wms.stop_communicating()
    wait_event.wait(timeout=COMM_STATE_UPDATE_WAIT)
    assert wms.communication_state == CommunicationStatus.DISABLED
    wms.write_wms_group_attribute_value.assert_called_with("adminMode", AdminMode.OFFLINE)
    assert wms.read_wms_group_attribute_value.call_count == 10
    assert component_state["windgust"] == 20
    assert component_state["meanwindspeed"] == 15


@pytest.mark.unit
def test_wms_cm_wind_gust_reports_expected_max_windspeed():
    comp_state_mock = MagicMock()
    wms = WMSComponentManager(
        ["mid/wms/1"],
        logger=LOGGER,
        component_state_callback=comp_state_mock,
        wms_polling_period=WMS_POLLING_PERIOD,
        wind_speed_moving_average_period=MEAN_WIND_SPEED_PERIOD,
        wind_gust_average_period=WIND_GUST_PERIOD,
        meanwindspeed=-1,
        windgust=-1,
    )

    test_start_time = time.time()

    # The wms component manager initially waits for the "polling period" amount
    # of time before the WMS devices are actually polled. This wait will later
    # be added to the elapsed time with each polling period/increment
    initial_wait_time_before_polling = wms._wms_polling_period

    max_inst_wind_speed_and_expected_gust = [
        (10, None),
        (10, None),
        (10, 10),
        (15, 15),
        (20, 20),
        (30, 30),
        (15, 30),
        (15, 30),
        (15, 15),
    ]
    for polling_time, (current_max_wind_speed, exp_wind_gust) in enumerate(
        max_inst_wind_speed_and_expected_gust
    ):
        # polling_time, the current list index, is used to simulate the
        # 1 second that passed each time the WMS Devices are polled
        elapsed_time = polling_time + initial_wait_time_before_polling

        current_wind_speed_data_time = test_start_time + elapsed_time
        computed_wind_gust = wms._process_wind_gust(
            [[current_wind_speed_data_time, current_max_wind_speed]],
            test_start_time,
            elapsed_time,
        )
        assert computed_wind_gust == exp_wind_gust


@pytest.mark.unit
def test_wms_cm_flushes_expired_wind_speed_readings():
    comp_state_mock = MagicMock()
    wms = WMSComponentManager(
        ["mid/wms/1"],
        logger=LOGGER,
        component_state_callback=comp_state_mock,
        wms_polling_period=WMS_POLLING_PERIOD,
        wind_speed_moving_average_period=MEAN_WIND_SPEED_PERIOD,
        wind_gust_average_period=WIND_GUST_PERIOD,
        meanwindspeed=-1,
        windgust=-1,
    )

    test_start_time = time.time()
    sample_windspeed_buffer = deque()

    # Create a buffer of valid and invalid windspeed values.
    # Store the valid windspeeds in a separate list to validate
    # later that invalid windspeeds were removed from the buffer
    expected_valid_windspeeds = []
    for time_decrement in range(20):
        ws_timestamp = test_start_time - time_decrement
        sample_windspeed = random.uniform(10, 40)
        # Append left (opposite to wms_cm normal operation)
        # as we are populating the buffer with the oldest values first
        sample_windspeed_buffer.appendleft([ws_timestamp, sample_windspeed])
        if time_decrement <= MEAN_WIND_SPEED_PERIOD:
            expected_valid_windspeeds.append(sample_windspeed)

    wms._prune_stale_windspeed_data(
        test_start_time,
        MEAN_WIND_SPEED_PERIOD,
        sample_windspeed_buffer,
    )

    # Validate that only valid windspeed values remain in the buffer
    assert len(sample_windspeed_buffer) == len(expected_valid_windspeeds)
    expected_valid_windspeeds.reverse()
    for index, ws in enumerate(expected_valid_windspeeds):
        assert sample_windspeed_buffer[index][1] == ws
