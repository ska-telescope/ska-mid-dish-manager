import pytest

from ska_mid_dish_manager.models.constants import WIND_GUST_THRESHOLD_MPS
from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance_mk_lmc_wms_wind_stow
def test_mk_wms_wind_stow(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    wms_device_proxy,
    trigger_weather_sensor,
):
    """Test that the dish stows when the wind speed exceeds the threshold."""
    dish_mode_event_store = event_store_class()
    wind_gust_event_store = event_store_class()

    dm_attr_cb_mapping = {
        "dishMode": dish_mode_event_store,
        "windGust": wind_gust_event_store,
    }

    subscriptions = setup_subscriptions(dish_manager_proxy, dm_attr_cb_mapping)

    try:
        # Set the control mode (control & monitor)
        wms_device_proxy.controlMode = 2

        # Enable automatic wind stow
        dish_manager_proxy.autoWindStowEnabled = True

        # Assert that the dish is not in STOW before the gust
        assert dish_manager_proxy.dishMode != DishMode.STOW

        random_wind_value_before_trigger = wms_device_proxy.read_attribute("windSpeed").value
        assert random_wind_value_before_trigger < WIND_GUST_THRESHOLD_MPS

        # Trigger the simulator to produce a high wind
        trigger_weather_sensor("wind-speed", 25, 5)

        wind_value_after_trigger = wms_device_proxy.read_attribute("windSpeed").value
        assert wind_value_after_trigger == 25
        assert random_wind_value_before_trigger != wind_value_after_trigger

        # Wait for Dish Manager to react
        dish_mode_event_store.wait_for_value(DishMode.STOW, timeout=20)

        # Wait for the gust to finish
        wind_gust_event_store.wait_for_condition(
            lambda value: value < WIND_GUST_THRESHOLD_MPS,
            timeout=10,
        )
    finally:
        try:
            dish_manager_proxy.autoWindStowEnabled = False
        finally:
            remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_mk_wms_no_wind_stow(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    wms_device_proxy,
    trigger_weather_sensor,
):
    """Test that the dish does not stow when auto wind stow is disabled."""
    wind_gust_event_store = event_store_class()

    dm_attr_cb_mapping = {
        "windGust": wind_gust_event_store,
    }

    subscriptions = setup_subscriptions(dish_manager_proxy, dm_attr_cb_mapping)

    try:
        # Set the control mode (control & monitor)
        wms_device_proxy.controlMode = 2

        # Disable automatic wind stow
        dish_manager_proxy.autoWindStowEnabled = False
        assert not dish_manager_proxy.autoWindStowEnabled

        # Assert that the dish is not in STOW before the gust
        assert dish_manager_proxy.dishMode != DishMode.STOW

        # Trigger the simulator to produce a high wind
        trigger_weather_sensor("wind-speed", 35, 5)

        wind_value_after_trigger = wms_device_proxy.read_attribute("windSpeed").value
        assert wind_value_after_trigger == 35

        # Wait for the gust to finish
        wind_gust_event_store.wait_for_condition(
            lambda value: value < WIND_GUST_THRESHOLD_MPS,
            timeout=10,
        )

        assert dish_manager_proxy.dishMode != DishMode.STOW
    finally:
        remove_subscriptions(subscriptions)
