"""Unit tests checking WMS component manager behaviour."""

import logging
import threading
from time import sleep
from unittest.mock import Mock
import pytest

from ska_mid_dish_manager.component_managers.wms_cm import WMSComponentManager
from ska_control_model import AdminMode, CommunicationStatus


WMS_POLLING_PERIOD = 1.0
WIND_GUST_PERIOD = 3.0
MEAN_WIND_SPEED_PERIOD = 10.0


@pytest.mark.forked
@pytest.mark.unit
def test_wms_group_activation_and_polling_starts():
    test_weather_station_instances = ["1","2","3"]
    logger = logging.getLogger(__name__)
    
    comp_state_updates = []
    def comp_state_callback(**incoming_comp_state_change):
        comp_state_updates.append(incoming_comp_state_change)

    wms = WMSComponentManager(
        test_weather_station_instances,
        logger=logger,
        component_state_callback=comp_state_callback(),
        wms_polling_period=WMS_POLLING_PERIOD,
        wind_speed_moving_average_period=MEAN_WIND_SPEED_PERIOD,
        wind_gust_average_period=WIND_GUST_PERIOD,
    )
    
    wms.write_wms_group_attribute_value = Mock()
    wms._poll_wms_wind_speed_data = Mock()

    wms.start_communicating()

    expected_devices = []
    for instance in test_weather_station_instances:
        expected_devices.append("mid/wms/" + instance)

    # Assert all expected device successfully added to device group
    for device_name in expected_devices:
        assert device_name in wms._wms_device_group.get_device_list()

    wms.write_wms_group_attribute_value.assert_called_once_with("adminMode", AdminMode.ONLINE)
    wms._poll_wms_wind_speed_data.assert_called()


@pytest.mark.unit
def test_wms_polling_starts():
    test_weather_station_instances = ["1","2","3"]
    logger = logging.getLogger(__name__)
    
    comp_state_updates = []
    def comp_state_callback(**incoming_comp_state_change):
        print(f"Component state callback with: {incoming_comp_state_change}")
        comp_state_updates.append(incoming_comp_state_change)

    comp_state_cb = Mock()

    wms = WMSComponentManager(
        test_weather_station_instances,
        logger=logger,
        component_state_callback=comp_state_cb(),
        wms_polling_period=WMS_POLLING_PERIOD,
        wind_speed_moving_average_period=MEAN_WIND_SPEED_PERIOD,
        wind_gust_average_period=WIND_GUST_PERIOD,
    )
    wms._wms_communication_established = Mock()
    wms.write_wms_group_attribute_value = Mock()
    wms.read_wms_group_attribute_value = Mock()

    wms._compute_mean_wind_speed = Mock()
    wms._process_wind_gust = Mock()

    wms.read_wms_group_attribute_value.return_value = [10, 20, 15]

    # Call start communicating. This won't start the polling
    wms.start_communicating()
    
    # Now explicitly trigger the polling
    wms._poll_wms_wind_speed_data()

    # Assert that the component hasnt been updated until 
    # enough time has elasped to update the wind gust and 
    # mean wind speed values
    wait_event = threading.Event()
    wait_event.wait(0.5)

    wms.read_wms_group_attribute_value.assert_called()
    wms._process_wind_gust.assert_called_once_with(20)
    wms._compute_mean_wind_speed.assert_called_once_with([10, 20, 15])

    # Assert ONLY wind gust computed
    wait_event = threading.Event()
    wait_event.wait(5)

    comp_state_cb.assert_called_with(windgust=20)

    # Wait enough time for the wind gust to be computed
    # sleep(10)

    # assert comp_state_updates
    # print(comp_state_updates)
    # assert False

