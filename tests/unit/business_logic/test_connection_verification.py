"""Test verifiying connection logic."""

import logging
import threading

import mock
import pytest

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import DishMode

LOGGER = logging.getLogger(__name__)


@pytest.fixture
def cm():
    cm = TangoDeviceComponentManager("a/b/c", LOGGER, ())
    yield cm
    cm.stop_communicating()


@pytest.mark.unit
def test_verification_process_starts_once(cm, caplog):
    caplog.set_level(logging.DEBUG)

    cm._verifying_connection = False
    cm._verifying_device_connection = mock.MagicMock()

    event = mock.MagicMock()
    event.attr_name = "mock_attr"

    dev_error = mock.MagicMock()
    dev_error.reason = "API_EventTimeout"
    event.errors = [dev_error]

    cm._active_attr_event_subscriptions = {"mock_attr"}

    cm._handle_error_events(event)
    cm._handle_error_events(event)

    assert cm._verifying_connection is True
    assert "verifying if Dish Manager is still connected" in caplog.text


@pytest.mark.unit
def test_valid_event_stops_verification(cm, caplog):
    caplog.set_level(logging.DEBUG)

    cm._verifying_connection = True
    cm._stop_verifying_event = threading.Event()  # 👈 important fix

    event = mock.MagicMock()
    event.attr_value.name = "dishmode"
    event.attr_value.quality = "tango.AttrQuality.ATTR_VALID"
    event.attr_value.value = DishMode.OPERATE

    cm._update_component_state = mock.MagicMock()

    cm._update_state_from_event(event)

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
