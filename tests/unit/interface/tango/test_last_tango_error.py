"""Unit test for lastTangoError attribute."""

from unittest.mock import MagicMock, patch

import pytest
import tango


def construct_mock_error_event_data(attr_name: str, reason: str) -> tango.EventData:
    """Construct a mock error event data for a given attribute."""
    mock_dev_errors = tango.DevError()
    mock_dev_errors.reason = reason

    mock_error_event_data = tango.EventData(errors=(mock_dev_errors,))
    mock_error_event_data.attr_name = f"tango://1.2.3.4:10000/some/tango/device/{attr_name}"
    mock_error_event_data.err = True
    return mock_error_event_data


@pytest.mark.unit
@pytest.mark.forked
def test_last_tango_error_defaults_to_empty_record(dish_manager_resources):
    """Test that an empty record is reported until an error event is received."""
    device_proxy, _ = dish_manager_resources

    timestamp, device_name, attribute_name, reason = device_proxy.lastTangoError

    assert timestamp == "0.0"
    assert device_name == ""
    assert attribute_name == ""
    assert reason == ""


@pytest.mark.unit
@pytest.mark.forked
@patch(
    "ska_mid_dish_manager.component_managers.device_proxy_factory.DeviceProxyManager.get_cached_proxy"
)
def test_last_tango_error_reports_error_event_details(
    patch_cache_proxy,
    dish_manager_resources,
    event_store_class,
):
    """Test that the details of the last error event on a sub device are reported."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    # keep the device reachable so the error event does not flip communication state
    patch_cache_proxy.return_value = MagicMock(name="mock_device_proxy")

    last_tango_error_event_store = event_store_class()
    device_proxy.subscribe_event(
        "lastTangoError",
        tango.EventType.CHANGE_EVENT,
        last_tango_error_event_store,
    )
    last_tango_error_event_store.clear_queue()

    ds_cm.dispatch_event(construct_mock_error_event_data("operatingMode", "API_EventTimeout"))

    events = last_tango_error_event_store.wait_for_n_events(1)
    timestamp, device_name, attribute_name, reason = events[0].attr_value.value

    assert float(timestamp) > 0.0
    assert device_name == ds_cm._tango_device_fqdn
    assert attribute_name == "operatingmode"
    assert reason == "API_EventTimeout"

    # the attribute read reports the same record as the change event
    assert list(device_proxy.lastTangoError) == [timestamp, device_name, attribute_name, reason]
