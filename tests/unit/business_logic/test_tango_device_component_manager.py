"""Unit tests checking generic component manager behaviour."""

import logging
import threading
from functools import partial
from threading import Event
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager

LOGGER = logging.getLogger(__name__)


def comm_state_callback(signal: threading.Event, communication_state: CommunicationStatus):
    pass


def construct_mock_valid_event_data(attr_name: str) -> tango.EventData:
    """Construct a mock valid event data for a given attribute."""
    mock_attr_value = MagicMock(name=f"mock_{attr_name}_value")
    mock_attr_value.name = attr_name

    mock_valid_event_data = tango.EventData()
    mock_valid_event_data.attr_value = mock_attr_value
    mock_valid_event_data.err = False
    return mock_valid_event_data


def construct_mock_invalid_quality_event_data(attr_name: str) -> tango.EventData:
    """Construct a mock attribute with invalid quality for a given attribute."""
    mock_attr_value = MagicMock(name=f"mock_{attr_name}_value")
    mock_attr_value.name = attr_name
    mock_attr_value.quality = tango.AttrQuality.ATTR_INVALID

    mock_valid_event_data = tango.EventData()
    mock_valid_event_data.attr_value = mock_attr_value
    mock_valid_event_data.err = True
    return mock_valid_event_data


def construct_mock_error_event_data(attr_name: str, reason: str) -> tango.EventData:
    """Construct a mock error event data for a given attribute."""
    mock_dev_errors = tango.DevError()
    mock_dev_errors.reason = reason

    mock_error_event_data = tango.EventData(errors=(mock_dev_errors,))
    mock_error_event_data.attr_name = f"tango://1.2.3.4:10000/some/tango/device/{attr_name}"
    mock_error_event_data.err = True
    return mock_error_event_data


@pytest.mark.unit
@patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango")
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
    tc_manager._fetch_build_state_information = MagicMock(name="mock_build_state")
    communication_state_changed = Event()
    tc_manager._communication_state_callback = partial(
        comm_state_callback, communication_state_changed
    )

    # Set up a valid mock event for some_attr
    mock_some_attr_event_data = construct_mock_valid_event_data("some_attr")
    # send valid events to the queue to trigger the valid event callback
    tc_manager.dispatch_event(mock_some_attr_event_data)

    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED


@pytest.mark.unit
@patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango")
def test_connection_with_invalid_attr(patched_tango, caplog):
    """Tango device establishes connection with invalid attribute quality."""
    caplog.set_level(logging.DEBUG)

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_attr",),
    )

    # configure mock and start communication
    tc_manager._fetch_build_state_information = MagicMock(name="mock_build_state")
    communication_state_changed = Event()
    tc_manager._communication_state_callback = partial(
        comm_state_callback, communication_state_changed
    )

    # Set up an attribute with err and quality invalid
    mock_some_attr_event_data = construct_mock_invalid_quality_event_data("some_attr")
    # send valid events to the queue to trigger the valid event callback
    tc_manager.dispatch_event(mock_some_attr_event_data)

    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.component_managers.device_proxy_factory.DeviceProxyManager.get_cached_proxy"
)
def test_device_goes_away(patch_cache_proxy, caplog):
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
    tc_manager._fetch_build_state_information = MagicMock(name="mock_build_state")
    communication_state_changed = Event()
    tc_manager._communication_state_callback = partial(
        comm_state_callback, communication_state_changed
    )

    # Set up a valid mock event for some_attr and some_other_attr
    mock_some_attr_event_data = construct_mock_valid_event_data("some_attr")
    mock_some_other_attr_event_data = construct_mock_valid_event_data("some_other_attr")
    # send valid events to the queue to trigger the valid event callback
    tc_manager.dispatch_event(mock_some_attr_event_data)
    tc_manager.dispatch_event(mock_some_other_attr_event_data)
    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED

    # Set up an error mock event (API_MissedEvent), no action taken
    mock_some_attr_error_event_data = construct_mock_error_event_data(
        "some_attr", "API_MissedEvent"
    )
    # Trigger a failure event
    tc_manager.dispatch_event(mock_some_attr_error_event_data)
    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED

    # Set up a mock device proxy that raises DevFailed on ping
    mock_device_proxy = MagicMock(name="mock_device_proxy")
    mock_device_proxy.ping.side_effect = tango.DevFailed()
    patch_cache_proxy.return_value = mock_device_proxy
    # Set up an error mock event (API_EventTimeout)
    mock_some_attr_error_event_data = construct_mock_error_event_data(
        "some_attr", "API_EventTimeout"
    )
    # Trigger a failure event
    tc_manager.dispatch_event(mock_some_attr_error_event_data)
    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.NOT_ESTABLISHED

    # trigger a valid event
    tc_manager.dispatch_event(mock_some_attr_event_data)
    # wait a bit for the state to change
    communication_state_changed.wait(timeout=1)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED
