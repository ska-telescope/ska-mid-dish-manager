"""Unit tests checking generic component manager behaviour."""

import logging
import threading
from functools import partial
from threading import Event
from unittest import mock

import pytest
import tango
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager

LOGGER = logging.getLogger(__name__)


def comm_state_callback(signal: threading.Event, communication_state: CommunicationStatus):
    pass


def construct_mock_valid_event_data(attr_name: str) -> tango.EventData:
    """Construct a mock valid event data for a given attribute."""
    mock_attr_value = mock.MagicMock(name=f"mock_{attr_name}_value")
    mock_attr_value.name = attr_name

    mock_valid_event_data = mock.MagicMock(name=f"mock_{attr_name}valid_event")
    mock_valid_event_data.attr_value = mock_attr_value
    mock_valid_event_data.err = False
    return mock_valid_event_data


def construct_mock_invalid_quality_event_data(attr_name: str) -> tango.EventData:
    """Construct a mock attribute with invalid quality for a given attribute."""
    mock_attr_value = mock.MagicMock(name=f"mock_{attr_name}_value")
    mock_attr_value.name = attr_name
    mock_attr_value.quality = tango.AttrQuality.ATTR_INVALID

    mock_valid_event_data = mock.MagicMock(name=f"mock_{attr_name}valid_event")
    mock_valid_event_data.attr_value = mock_attr_value
    mock_valid_event_data.err = True
    return mock_valid_event_data


def construct_mock_error_event_data(attr_name: str, reason: str) -> tango.EventData:
    """Construct a mock error event data for a given attribute."""
    mock_dev_errors = mock.MagicMock(name=f"mock{attr_name}_dev_errors")
    mock_dev_errors.reason = reason

    mock_error_event_data = mock.MagicMock(name=f"mock_{attr_name}_error_event")
    mock_error_event_data.attr_name = f"tango://1.2.3.4:10000/some/tango/device/{attr_name}"
    mock_error_event_data.err = True
    mock_error_event_data.errors = (mock_dev_errors,)
    return mock_error_event_data


@pytest.mark.unit
def test_component_manager_continues_reconnecting_when_device_is_unreachable(caplog):
    caplog.set_level(logging.DEBUG)
    tc_manager = TangoDeviceComponentManager("fake/fqdn/1", LOGGER, ("fake_attr",))
    tc_manager.start_communicating()
    signal = Event()
    retry_log = "An error occurred creating a device proxy to fake/fqdn/1, retrying in"
    while retry_log not in caplog.text:
        signal.wait(0.1)

    assert tc_manager.communication_state == CommunicationStatus.NOT_ESTABLISHED
    # clean up afterwards
    tc_manager.stop_communicating()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango")
def test_happy_path(patched_tango, caplog):
    """Tango device is reachable and communicates with component manager.

    Tango layer is mocked and checks are made on the mock for expected
    calls made when communication is established and component is
    updated accordingly
    """
    caplog.set_level(logging.DEBUG)

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_attr",),
    )

    # configure mock and start communication
    tc_manager._fetch_build_state_information = mock.MagicMock(name="mock_build_state")
    communication_state_changed = Event()
    tc_manager._communication_state_callback = partial(
        comm_state_callback, communication_state_changed
    )
    tc_manager.start_communicating()

    # Set up a valid mock event for some_attr
    mock_some_attr_event_data = construct_mock_valid_event_data("some_attr")
    # send valid events to the queue to trigger the valid event callback
    tc_manager._events_queue.put(mock_some_attr_event_data)

    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED

    # clean up afterwards
    tc_manager.stop_communicating()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango")
def test_connection_with_invalid_attr(patched_tango, caplog):
    """Tango device establishes connection with invalid attribute quality."""
    caplog.set_level(logging.DEBUG)

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_attr",),
    )

    # configure mock and start communication
    tc_manager._fetch_build_state_information = mock.MagicMock(name="mock_build_state")
    communication_state_changed = Event()
    tc_manager._communication_state_callback = partial(
        comm_state_callback, communication_state_changed
    )
    tc_manager.start_communicating()

    # Set up an attribute with err and quality invalid
    mock_some_attr_event_data = construct_mock_invalid_quality_event_data("some_attr")
    # send valid events to the queue to trigger the valid event callback
    tc_manager._events_queue.put(mock_some_attr_event_data)

    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED

    # clean up afterwards
    tc_manager.stop_communicating()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
def test_unhappy_path(patched_dp, caplog):
    """Tango device is unreachable and can't communicate with component manager.

    Similar to `test_component_manager_continues_reconnecting_...` except
    Tango layer is mocked here. Checks are made on the mock for expected
    calls and logs when communication is attempted by component manager
    on mocked device
    """
    caplog.set_level(logging.DEBUG)

    # configure mock
    patched_dp.side_effect = tango.DevFailed("FAIL")

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_attr", "some_other_attr"),
    )

    tc_manager.start_communicating()

    default_retry_times = [1, 2, 3, 4, 6]
    # wait a bit
    signal = Event()
    signal.wait(sum(default_retry_times))

    logs = [record.message for record in caplog.records]
    for count, retry_time in enumerate(default_retry_times, start=1):
        assert (
            f"Try number {count}: An error occurred creating a device "
            f"proxy to a/b/c, retrying in {retry_time}s" in logs
        )
    # clean up afterwards
    tc_manager.stop_communicating()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
def test_device_goes_away(patch_dp, caplog):
    """Start up the component_manager.
    Signal a lost connection via an event
    Check for updated communication state.
    """
    caplog.set_level(logging.DEBUG)

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_Attr", "some_other_attr"),
    )

    # configure mock and start communication
    tc_manager._fetch_build_state_information = mock.MagicMock(name="mock_build_state")
    communication_state_changed = Event()
    tc_manager._communication_state_callback = partial(
        comm_state_callback, communication_state_changed
    )
    tc_manager.start_communicating()

    # Set up a valid mock event for some_attr and some_other_attr
    mock_some_attr_event_data = construct_mock_valid_event_data("some_attr")
    mock_some_other_attr_event_data = construct_mock_valid_event_data("some_other_attr")
    # send valid events to the queue to trigger the valid event callback
    tc_manager._events_queue.put(mock_some_attr_event_data)
    tc_manager._events_queue.put(mock_some_other_attr_event_data)
    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED

    # Set up an error mock event (API_MissedEvent), no action taken
    mock_some_attr_error_event_data = construct_mock_error_event_data(
        "some_attr", "API_MissedEvent"
    )
    # Trigger a failure event
    tc_manager._events_queue.put(mock_some_attr_error_event_data)
    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED

    # Set up an error mock event (API_EventTimeout)
    mock_some_attr_error_event_data = construct_mock_error_event_data(
        "some_attr", "API_EventTimeout"
    )
    # Trigger a failure event
    tc_manager._events_queue.put(mock_some_attr_error_event_data)
    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.NOT_ESTABLISHED

    # trigger a valid event
    tc_manager._events_queue.put(mock_some_attr_event_data)
    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED

    # clean up afterwards
    # TODO this should be a finalizer
    tc_manager.stop_communicating()
