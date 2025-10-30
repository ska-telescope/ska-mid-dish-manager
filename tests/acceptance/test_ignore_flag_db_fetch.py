"""Test ignore flags are persisted in the tango db after device restarts."""

import pytest
import tango

from ska_mid_dish_manager.component_managers.device_proxy_factory import DeviceProxyManager
from ska_mid_dish_manager.utils.helper_module import get_device_attribute_property_value


@pytest.mark.only
@pytest.mark.forked
def test_device_fetches_db_value_on_restart(dish_manager_proxy):
    """Test dish manager fetches db values for ignore flags after device restarts."""
    assert not dish_manager_proxy.ignoreSpf
    assert not dish_manager_proxy.ignoreSpfrx
    # enable the ignore flags
    dish_manager_proxy.ignoreSpf = True
    dish_manager_proxy.ignoreSpfrx = True

    # restart the device
    admin_device_proxy = tango.DeviceProxy(dish_manager_proxy.adm_name())
    admin_device_proxy.RestartServer()

    # wait for the device to come back online
    dp_manager = DeviceProxyManager()
    try:
        dp_manager.wait_for_device(dish_manager_proxy)
    except tango.DevFailed:
        pytest.fail("Dish manager device failed to restart.")

    normal_status_msg = "The device is in ON state."
    # check dish manager reports previous state after the device is restarted
    assert dish_manager_proxy.State() == tango.DevState.ON
    assert dish_manager_proxy.Status() == normal_status_msg

    # check that the flags are still set in the database
    db_spf_ignore_flag = get_device_attribute_property_value(
        "ignoreSpf", dish_manager_proxy.dev_name()
    )
    db_spfrx_ignore_flag = get_device_attribute_property_value(
        "ignoreSpfrx", dish_manager_proxy.dev_name()
    )
    assert db_spf_ignore_flag == "true"
    assert db_spfrx_ignore_flag == "true"

    # check that the ignore flags are persisted by the device after restart
    assert dish_manager_proxy.ignoreSpf
    assert dish_manager_proxy.ignoreSpfrx

    # restore the ignore flags
    dish_manager_proxy.ignoreSpf = False
    dish_manager_proxy.ignoreSpfrx = False
