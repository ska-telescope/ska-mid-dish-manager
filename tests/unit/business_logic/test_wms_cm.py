"""Unit tests checking WMS component manager behaviour."""

import logging
import threading
import time
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

    # Assert all expected device successfully added to device group
    tango_group_device_list = wms._wms_device_group.get_device_list()
    for device_name in test_wms_device_names:
        assert device_name in tango_group_device_list

    wait_event = threading.Event()
    wait_event.wait(timeout=wms._wms_polling_period)

    wms.write_wms_group_attribute_value.assert_called_with("adminMode", AdminMode.ONLINE)
    wms._run_wms_group_polling.assert_called()


@pytest.mark.unit
def test_wms_wind_gust_and_mean_wind_speed_updates():
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
    wait_event.wait(wms._wms_polling_period + COMM_STATE_UPDATE_WAIT)
    assert wms.communication_state == CommunicationStatus.ESTABLISHED

    wait_event.wait(10)

    wms.stop_communicating()
    wait_event.wait(COMM_STATE_UPDATE_WAIT)
    assert wms.communication_state == CommunicationStatus.DISABLED
    wms.write_wms_group_attribute_value.assert_called_with("adminMode", AdminMode.OFFLINE)
    assert wms.read_wms_group_attribute_value.call_count == 10
    assert component_state["windgust"] == 20
    assert component_state["meanwindspeed"] == 15


@pytest.mark.unit
def test_wms_wind_gust_circular_buffer():
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
    for _, (current_max_wind_speed, exp_wind_gust) in enumerate(
        max_inst_wind_speed_and_expected_gust
    ):
        wms._process_wind_gust(current_max_wind_speed)
        if exp_wind_gust is not None:
            comp_state_mock.assert_called_with(windgust=exp_wind_gust)
