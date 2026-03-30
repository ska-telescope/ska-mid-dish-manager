"""Test verifiying connection logic."""

import logging

import mock
import pytest

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import DishMode

LOGGER = logging.getLogger(__name__)


# --- Helper function to disable threads ---
def disable_threads(cm):
    """Disable all background threads and join them if already started."""
    # Stop the event consumer and monitor threads
    if hasattr(cm, "_start_event_consumer_thread") and cm._start_event_consumer_thread:
        cm._start_event_consumer_thread = mock.MagicMock()
    if hasattr(cm, "_tango_device_monitor") and cm._tango_device_monitor:
        cm._tango_device_monitor = mock.MagicMock()

    # Stop attribute subscription thread if it exists
    if hasattr(cm, "_attribute_subscription_thread") and cm._attribute_subscription_thread:
        if hasattr(cm, "_attribute_subscription_stop_event"):
            cm._attribute_subscription_stop_event.set()
        cm._attribute_subscription_thread.join(timeout=1)

    # Stop event consumer thread if it exists
    if hasattr(cm, "_event_consumer_thread") and cm._event_consumer_thread:
        if hasattr(cm, "_event_consumer_stop_event"):
            cm._event_consumer_stop_event.set()
        cm._event_consumer_thread.join(timeout=1)

    # Stop attribute subscription thread if it exists
    if hasattr(cm, "_verification_thread") and cm._verification_thread:
        if hasattr(cm, "_attribute_subscription_stop_event"):
            cm._stop_verifying_event.set()
        cm._verification_thread.join(timeout=1)
    pass


@pytest.mark.unit
def test_verification_process_starts_once(caplog: pytest.LogCaptureFixture):
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

    # Flag should be set
    assert cm._verifying_connection is True

    # Check log appears
    assert "verifying if Dish Manager is still connected" in caplog.text


@pytest.mark.unit
def test_valid_event_stops_verification(caplog: pytest.LogCaptureFixture):
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
    event.attr_value.quality = "tango.AttrQuality.ATTR_VALID"
    event.attr_value.value = DishMode.OPERATE
    cm._update_component_state = mock.MagicMock()

    # Simulate a valid event coming through
    cm._update_state_from_event(event)

    # Assert that the verification process stops
    assert cm._verifying_connection is False


# @pytest.mark.unit
# def test_verification_success(caplog: pytest.LogCaptureFixture):
#     """Check that verification sets state to ESTABLISHED when device responds."""
#     caplog.set_level(logging.DEBUG)

#     cm = TangoDeviceComponentManager("a/b/c", LOGGER, ())
#     disable_threads(cm)

#     cm._verifying_connection = True
#     cm._update_communication_state = mock.MagicMock()

#     stop_event = mock.MagicMock()
#     stop_event.is_set.side_effect = [False, True]
#     stop_event.set = mock.MagicMock()
#     # mock successful read
#     cm.read_attribute_value = mock.Mock(return_value="DevState.ON")
#     cm._verifying_device_connection(stop_event)

#     cm._update_communication_state.assert_called_with(CommunicationStatus.ESTABLISHED)

#     assert cm._verifying_connection is False


# @pytest.mark.unit
# def test_verification_failure(caplog: pytest.LogCaptureFixture):
#     """Check that verification sets NOT_ESTABLISHED on failure."""
#     caplog.set_level(logging.DEBUG)

#     cm = TangoDeviceComponentManager("a/b/c", LOGGER, ())
#     disable_threads(cm)

#     cm._verifying_connection = True
#     cm._update_communication_state = mock.MagicMock()

#     stop_event = mock.MagicMock()
#     stop_event.is_set.return_value = False

#     cm.read_attribute_value = mock.Mock(
#     side_effect=DevFailed())


#     cm._verifying_device_connection(stop_event)

#     cm._update_communication_state.assert_called_with(CommunicationStatus.NOT_ESTABLISHED)

#     # Flag should remain True because verification never succeeded
#     assert cm._verifying_connection is True
