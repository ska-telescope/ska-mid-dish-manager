"""Test verifiying connection logic."""

import logging
import threading

import mock
import pytest
import tango
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import DishMode

LOGGER = logging.getLogger(__name__)


def disable_threads(self, cm):
    # Disable threads
    cm._start_event_consumer_thread = mock.MagicMock()
    cm._tango_device_monitor = mock.MagicMock()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
def test_verification_process_starts_once(patched_dp, caplog: pytest.LogCaptureFixture):
    """Check that verification process starts only once on multiple timeouts."""
    caplog.set_level(logging.DEBUG)

    # Create component manager
    cm = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        (),
    )
    disable_threads(cm)

    # Set the initial state to a known value
    cm._verifying_connection = False

    # Mock event data
    event = mock.MagicMock()
    event.attr_name = "mock_attr"

    # Mock an error = "API_EventTimeout"
    dev_error = mock.MagicMock()
    dev_error.reason = "API_EventTimeout"

    # Include error in event data
    event.errors = [dev_error]
    cm._active_attr_event_subscriptions = {"mock_attr"}

    # Simulate two errors coming through (multiple timeouts)
    cm._handle_error_events(event)
    cm._handle_error_events(event)

    # Only verification process should start
    assert cm._executor.submit.call_count == 1

    # Flag should be set
    assert cm._verifying_connection is True

    # Check log appears
    assert "verifying if Dish Manager is still connected" in caplog.text


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
def test_valid_event_stops_verification(patched_dp, caplog: pytest.LogCaptureFixture):
    """Check that valid event stops verification process."""
    caplog.set_level(logging.DEBUG)

    # Create component manager
    cm = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        (),
    )

    disable_threads(cm)
    # Set the initial state to a known value
    cm._verifying_connection = True

    # Mock event data
    event = mock.MagicMock()
    event.attr_value.name = "dishmode"
    event.attr_value.quality = tango.AttrQuality.ATTR_VALID
    event.attr_value.value = DishMode.OPERATE
    cm._update_component_state = mock.MagicMock()

    # Simulate a valid event coming through
    cm._update_state_from_event(event)

    # Assert that the verification process stops
    assert cm._verifying_connection is False


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
def test_verification_success(patched_dp, caplog: pytest.LogCaptureFixture):
    """Check that verification sets state to ESTABLISHED when device responds."""
    caplog.set_level(logging.DEBUG)

    # Create component manager
    cm = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        (),
    )

    disable_threads(cm)

    # Set the initial state to a known value
    cm._verifying_connection = True

    # Mock successful read and update_comm_state
    cm.read_attribute_value = mock.Mock(return_value=tango.DevState.ON)
    cm._update_communication_state = mock.MagicMock()

    # Forces an exception so the loop stops when time.sleep is hit
    # during verification check.
    with mock.patch("time.sleep", return_value=None):
        stop_event = threading.Event()
        cm._verifying_device_connection(stop_event)

    # Assert that the _update_communication_state was called once
    cm._update_communication_state.assert_called_with(CommunicationStatus.ESTABLISHED)

    assert cm._verifying_connection is False

    # Clean up.
    if hasattr(cm, "_verification_stop_event"):
        cm._verification_stop_event.set()
    if hasattr(cm, "_verification_thread"):
        cm._verification_thread.join()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
def test_verification_failure(patched_dp, caplog: pytest.LogCaptureFixture):
    """Check that verification sets NOT_ESTABLISHED on failure."""
    caplog.set_level(logging.DEBUG)

    # Create component manager
    cm = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        (),
    )

    disable_threads(cm)

    # Set to True so that the loop can run in
    cm._verifying_connection = True

    # Mock unsuccessful read and update_comm_state
    cm.read_attribute_value = mock.Mock(side_effect=tango.DevFailed(tango.DevError()))
    cm._update_communication_state = mock.MagicMock()

    # Forces an exception so the loop stops when time.sleep is hit
    # during verification check.
    with mock.patch("time.sleep", side_effect=Exception("stop")):
        try:
            stop_event = threading.Event()
            cm._verifying_device_connection(stop_event)
        except Exception:
            pass

    # Assert that the _update_communication_state was called once
    cm._update_communication_state.assert_called_with(CommunicationStatus.NOT_ESTABLISHED)

    assert cm._verifying_connection is True

    # Clean up
    if hasattr(cm, "_verification_stop_event"):
        cm._verification_stop_event.set()
    if hasattr(cm, "_verification_thread"):
        cm._verification_thread.join()
