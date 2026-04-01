"""Test that the DishManager ResetComponentConnection command."""

import pytest
import tango
from ska_control_model import ResultCode


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "invalid_dev_names",
    [
        "SD",
        "PFS",
        "WQ1FS",
        "111",
        "SPFrXW!#P",
    ],
)
def test_reset_subs_connection_invalid_device_names(dish_manager_resources, invalid_dev_names):
    """Test that ResetComponentConnection command raises an
    exception when invalid device names are passed.
    """
    device_proxy, _ = dish_manager_resources

    with pytest.raises(tango.DevFailed) as err:
        device_proxy.ResetComponentConnection(invalid_dev_names)
        assert "Incorrect input, command only accept SPF, SPFRX, DS, B5DC" in str(err.value)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "valid_dev_names",
    [
        "DS",
        "SPF",
        "SPFRX",
        "spf",
        "spfrx",
        "ds",
    ],
)
# B5DC, b5dc is also a valid dev name but is not monitored in this test
def test_reset_subs_connection_valid_device_names(dish_manager_resources, valid_dev_names):
    """Test that ResetComponentConnection command resets the connections
    when valid device names are passed.
    """
    device_proxy, _ = dish_manager_resources

    [[result_code], [message]] = device_proxy.ResetComponentConnection(valid_dev_names)

    assert result_code == ResultCode.OK
    assert message == "Resetting connection is successful"


@pytest.mark.unit
@pytest.mark.forked
def test_reset_subs_connection_no_device_names_input(dish_manager_resources):
    """Test that ResetComponentConnection command raises an exception
    when no device names are passed.
    """
    device_proxy, _ = dish_manager_resources

    with pytest.raises(tango.DevFailed) as err:
        device_proxy.ResetComponentConnection("")
        assert "device name cannot be an empty string" in str(err.value)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "device_name",
    [
        "SPF",
        "SPFRX",
    ],
)
def test_reset_subs_connection_ignored_devices(
    dish_manager_resources,
    event_store_class,
    device_name,
):
    """Test that ResetComponentConnection command fails
    when a sub device is ignored.
    """
    ignore_dev_event_store = event_store_class()
    device_proxy, _ = dish_manager_resources
    ignore_attr_name = f"ignore{device_name.lower()}"

    device_proxy.write_attribute(ignore_attr_name, True)
    event_id = device_proxy.subscribe_event(
        ignore_attr_name,
        tango.EventType.CHANGE_EVENT,
        ignore_dev_event_store,
    )
    ignore_dev_event_store.wait_for_value(True)

    with pytest.raises(tango.DevFailed) as err:
        device_proxy.ResetComponentConnection(device_name)
    assert f"Reconnection denied, device {device_name} is ignored" in str(err.value)
    device_proxy.write_attribute(ignore_attr_name, False)
    ignore_dev_event_store.wait_for_value(False)
    device_proxy.unsubscribe_event(event_id)


@pytest.mark.unit
@pytest.mark.forked
def test_reset_subs_connection_ignore_b5dc_when_not_monitored(
    dish_manager_resources,
):
    """Test that ResetComponentConnection command raises an exception
    when B5DC is not monitored.
    """
    device_proxy, _ = dish_manager_resources

    with pytest.raises(tango.DevFailed) as err:
        device_proxy.ResetComponentConnection("B5DC")

        assert "Reconnection denied, B5DC device is not monitored" in str(err.value)
