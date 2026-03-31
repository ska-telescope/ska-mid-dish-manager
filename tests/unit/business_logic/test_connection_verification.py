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


@pytest.fixture
def cm():
    cm = TangoDeviceComponentManager("a/b/c", LOGGER, ())
    cm._verifying_device_connection = mock.MagicMock()
    yield cm
    cm.stop_communicating()


@pytest.fixture
def cm_no_vdc():
    cm = TangoDeviceComponentManager("a/b/c", LOGGER, ())
    yield cm
    cm.stop_communicating()


def test_verification_process_starts_once(cm, caplog):
    caplog.set_level(logging.DEBUG)

    cm._verifying_connection = False

    event = mock.MagicMock()
    event.attr_name = "mock_attr"

    dev_error = mock.MagicMock()
    dev_error.reason = "API_EventTimeout"
    event.errors = [dev_error]

    cm._active_attr_event_subscriptions = {"mock_attr"}

    cm._handle_error_events(event)
    first_thread = cm._verification_thread

    cm._handle_error_events(event)

    assert cm._verifying_connection is True
    assert cm._verification_thread is first_thread
    assert "verifying if Dish Manager is still connected" in caplog.text


def test_valid_event_stops_verification(cm, caplog):
    caplog.set_level(logging.DEBUG)

    cm._verifying_connection = True
    cm._stop_verifying_event = threading.Event()
    cm._verification_thread = mock.MagicMock()

    event = mock.MagicMock()
    event.attr_value.name = "dishmode"
    event.attr_value.quality = "tango.AttrQuality.ATTR_VALID"
    event.attr_value.value = DishMode.OPERATE

    cm._update_component_state = mock.MagicMock()

    cm._update_state_from_event(event)

    assert cm._verifying_connection is False


@pytest.mark.unit
def test_verification_success(cm_no_vdc, caplog):
    """Check that verification sets state to ESTABLISHED when device responds."""
    caplog.set_level(logging.DEBUG)

    cm_no_vdc = TangoDeviceComponentManager("a/b/c", LOGGER, ())

    cm_no_vdc._verifying_connection = True
    cm_no_vdc._update_communication_state = mock.MagicMock()

    stop_event = mock.MagicMock()
    stop_event.is_set.side_effect = False
    stop_event.set = mock.MagicMock()
    # mock successful read
    cm_no_vdc.read_attribute_value = mock.Mock(return_value="DevState.ON")
    cm_no_vdc._verifying_device_connection(stop_event)

    cm_no_vdc._update_communication_state.assert_called_with(CommunicationStatus.ESTABLISHED)

    assert cm_no_vdc._verifying_connection is False


@pytest.mark.unit
def test_verification_failure(cm_no_vdc, caplog):
    """Check that verification sets NOT_ESTABLISHED on failure."""
    caplog.set_level(logging.DEBUG)

    cm_no_vdc = TangoDeviceComponentManager("a/b/c", LOGGER, ())

    cm_no_vdc._verifying_connection = True
    cm_no_vdc._update_communication_state = mock.MagicMock()

    stop_event = mock.MagicMock()
    stop_event.is_set.return_value = [False, True]
    stop_event.wait = mock.MagicMock()

    cm_no_vdc.read_attribute_value = mock.Mock(side_effect=tango.DevFailed())

    cm_no_vdc._verifying_device_connection(stop_event)

    cm_no_vdc._update_communication_state.assert_called_with(CommunicationStatus.NOT_ESTABLISHED)
