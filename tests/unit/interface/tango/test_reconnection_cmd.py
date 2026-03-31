"""Test that the DishManager ResetSubsconnection attribute."""

import pytest
import tango
from ska_control_model import ResultCode


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "invalid_dev_names",
    [
        ["SD"],
        ["PFS"],
        ["SRRFRX", "WQ1FS"],
        ["111"],
        ["SPF", "SPFRXWP"],
    ],
)
def test_reset_subs_connection_invalid_device_names(dish_manager_resources, invalid_dev_names):
    """Test that ResetSubsConnection command raises an
    exception when invalid device names are passed.
    """
    device_proxy, _ = dish_manager_resources

    with pytest.raises(tango.DevFailed) as err:
        device_proxy.ResetSubsConnections(invalid_dev_names)
    assert "Incorrect input, list only accept SPF, SPFRX, DS, B5DC" in str(err.value)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "valid_dev_names",
    [
        ["DS"],
        ["SPF"],
        ["SPFRX"],
        ["DS", "SPF"],
        ["SPF", "SPFRX"],
        ["DS", "SPF", "SPFRX"],
    ],
)
def test_reset_subs_connection_valid_device_names(
    dish_manager_resources, event_store_class, valid_dev_names
):
    """Test that ResetSubsConnection command resets the connections
    when valid device names are passed.
    """
    device_proxy, _ = dish_manager_resources

    [[result_code], [message]] = device_proxy.ResetSubsConnections(valid_dev_names)

    assert result_code == ResultCode.OK
    assert message == "Re-connection(s) have been initiated successfully"


@pytest.mark.unit
@pytest.mark.forked
def test_reset_subs_connection_no_device_names_input(dish_manager_resources, event_store_class):
    """Test that ResetSubsConnection command raises an exception
    when no device names are passed.
    """
    device_proxy, _ = dish_manager_resources

    with pytest.raises(tango.DevFailed) as err:
        device_proxy.ResetSubsConnections([])

    assert "[device_names] cannot be an empty list" in str(err.value)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "device_name, expected_result",
    [
        ("SPF", (ResultCode.FAILED, "Reconnection denied, device SPF is ignored")),
        ("SPFRX", (ResultCode.FAILED, "Reconnection denied, device SPFRX is ignored")),
    ],
)
def test_reset_subs_connection_ignored_devices(
    dish_manager_resources, event_store_class, device_name, expected_result
):
    """Test that ResetSubsConnection command raises an exception
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
    [[result_code], [message]] = device_proxy.ResetSubsConnections([device_name])
    assert result_code == expected_result[0]
    assert message == expected_result[1]
    device_proxy.write_attribute(ignore_attr_name, False)
    ignore_dev_event_store.wait_for_value(False)
    device_proxy.unsubscribe_event(event_id)
