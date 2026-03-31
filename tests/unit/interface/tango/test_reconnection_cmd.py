"""Test that the DishManager ResetSubsconnection attribute."""

import pytest
from ska_control_model import ResultCode

'''

# @pytest.mark.unit
@pytest.mark.xfail(reason="Still working on the command logic")
@pytest.mark.parametrize(
    "device_names",
    "expected_output",
    [
        (
            "SD",
            "PFS",
            "SRRFRX",
            (
                ResultCode.FAILED,
                "Invalid device name: SD. Valid device names are: DS, SPF, SPFRX",
            ),
        ),
        (
            "111",
            (
                ResultCode.FAILED,
                "Invalid device name: 111. Valid device names are: DS, SPF, SPFRX",
            ),
        ),
        (
            "SPFC",
            (
                ResultCode.FAILED,
                "Invalid device name: SPFC. Valid device names are: DS, SPF, SPFRX",
            ),
        ),
        (
            "SPFRx",
            (
                ResultCode.FAILED,
                "Invalid device name: SPFRx. Valid device names are: DS, SPF, SPFRX",
            ),
        ),
        (
            "INVALID_DEVICE",
            (
                ResultCode.FAILED,
                "Invalid device name: INVALID_DEVICE. Valid device names are: DS, SPF, SPFRX",
            ),
        ),
    ],
)
def test_reset_subs_connection_invalid_device_names(
    dish_manager_resources, device_names, expected_output, event_store_class
):
    """Test that ResetSubsConnection command raises an
    exception when invalid device names are passed.
    """
    device_proxy, dish_manager_cm = dish_manager_resources
    result = device_proxy.ResetSubsConnections([device_names])
    assert result == expected_output

'''


@pytest.mark.unit
@pytest.mark.parametrize(
    "valid_dev_names",
    [
        ["DS"],
        ["B5DC"],
        ["SPF"],
        ["SPFRX"],
        ["DS", "SPF"],
        ["SPF", "SPFRX"],
        ["DS", "SPF", "SPFRX", "B5DC"],
    ],
)
def test_reset_subs_connection_valid_device_names(
    dish_manager_resources, event_store_class, valid_dev_names
):
    """Test that ResetSubsConnection command resets the connections
    when valid device names are passed.
    """
    device_proxy, _ = dish_manager_resources

    result = device_proxy.ResetSubsConnections(valid_dev_names)

    assert result == (ResultCode.OK, "Re-connection(s) have been initiated successfully")


@pytest.mark.unit
def test_reset_subs_connection_no_device_names_input(dish_manager_resources, event_store_class):
    """Test that ResetSubsConnection command raises an exception
    when no device names are passed.
    """
    device_proxy, _ = dish_manager_resources

    with pytest.raises(ValueError) as err:
        device_proxy.ResetSubsConnections([])

    assert str(err.value) == "[device_names] cannot be an empty list"


'''
# @pytest.mark.unit
@pytest.mark.xfail(reason="Still working on the command logic")
@pytest.mark.parametrize(
    "device_name, expected_result",
    [
        ("SPF", (ValueError, "Reconnection denied, device SPF is ignored")),
        ("SPFRX", (ValueError, "Reconnection denied, device SPFRX is ignored")),
        ("B5DC", (ValueError, "Reconnection denied, B5DC device is not monitored")),
    ],
)
def test_reset_subs_connection_ignored_devices(
    dish_manager_resources, event_store_class, device_name, expected_result
):
    """Test that ResetSubsConnection command raises an exception
    when a sub device is ignored.
    """
    device_proxy, dish_manager_cm = dish_manager_resources
    device_proxy.ignorespf = True
    device_proxy.ignorespfrx = True
    result = device_proxy.ResetSubsConnections([device_name])
    assert result == expected_result
'''
